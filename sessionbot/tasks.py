from celery import chain, shared_task
from sessionbot.models import Task,ChildBot,DataHouseSyncStatus,Audience,Device,ScrapeTask,Proxy



from celery import shared_task
from django.apps import apps
from django.db import transaction
from datetime import datetime
import uuid
from django.db import models
import requests
import json
from django.conf import settings
from .models import DataHouseSyncStatus,ChildBot,Server
from sessionbot.utils import DataHouseClient
from services.slack.run_bot import Slack



from sessionbot.utils import convert_uuid_datetime_for_json
from sessionbot.models import Task, ChildBot, Device, Proxy, DataHouseSyncStatus, Server
import sessionbot.handlers.bots as bot_handler
import sessionbot.handlers.device as device_handler
from sessionbot.utils import convert_uuid_datetime_for_json
from django.forms import model_to_dict
@shared_task()
def sync_with_data_house_and_workers():
    """
    Unified sync with Data House and Workers.
    - Preserves real task statuses ('running', 'completed', etc.).
    - Sends ChildBot + Device resources first.
    - Tasks marked _delete are cleaned after successful sync.
    - Prevents resending tasks already registered.
    """

    # -----------------------
    # 1. Determine Data House URL
    # -----------------------
    datahouse_server = Server.objects.filter(instance_type='data_server').first()
    if not datahouse_server:
        print("Error: No Data House server configured.")
        return
    datahouse_url = f"{datahouse_server.public_ip}datahouse/api/sync/"
    target_payloads = {datahouse_url: []}
    all_successful_sync_ids = {}

    # -----------------------
    # 2. Collect objects to sync
    # -----------------------
    object_ids = DataHouseSyncStatus.objects.values_list('object_id', flat=True).distinct()
    for object_id in object_ids:
        statuses = DataHouseSyncStatus.objects.filter(object_id=object_id).order_by("created_at")
        if not statuses.exists():
            continue
        final_status = statuses.last()
        model_class_name = final_status.model_name
        try:
            model_class = apps.get_model("sessionbot", model_class_name)
            instance = model_class.objects.get(uuid=object_id)
        except model_class.DoesNotExist:
            DataHouseSyncStatus.objects.filter(object_id=object_id).delete()
            continue
        except Exception as e:
            print(f"Error retrieving object {object_id}: {e}")
            continue

        object_body = {} if final_status.operation == "DELETE" else convert_uuid_datetime_for_json(instance)
        message = {
            "uuid": str(object_id),
            "operation": final_status.operation,
            "object_body": object_body,
            "object_type": model_class_name,
            "sync_id": final_status.id,
        }
        target_payloads[datahouse_url].append(message)

        # -----------------------
        # 2a. Send to worker if applicable
        # -----------------------
        worker_url = None
        try:
            if isinstance(instance, Task) and instance.server:
                worker_url = f"{instance.server.public_ip}crawl/api/sync/"
            elif isinstance(instance, ChildBot) and instance.logged_in_on_servers:
                worker_url = f"{instance.logged_in_on_servers.public_ip}crawl/api/sync/"
            elif isinstance(instance, Device) and instance.connected_to_server:
                worker_url = f"{instance.connected_to_server.public_ip}crawl/api/sync/"
            if worker_url:
                target_payloads.setdefault(worker_url, []).append(message)
        except Exception as e:
            print(f"Error resolving worker URL for {object_id}: {e}")

    # -----------------------
    # 3. Send sync payloads to Data House & Workers
    # -----------------------
    for target_url, payloads in target_payloads.items():
        if not payloads:
            continue
        try:
            resp = requests.post(
                target_url,
                data=json.dumps({"data": payloads}),
                headers={"Content-Type": "application/json"}
            )
            resp.raise_for_status()
            data = resp.json()
            successful_ids = data.get("successful_sync_ids", {})
            for obj_type, sync_ids in successful_ids.items():
                all_successful_sync_ids.setdefault(obj_type, []).extend(sync_ids)
        except Exception as e:
            print(f"Error syncing with {target_url}: {e}")

    # -----------------------
    # 4. Cleanup successfully synced entries
    # -----------------------
    for obj_type, sync_ids in all_successful_sync_ids.items():
        DataHouseSyncStatus.objects.filter(id__in=sync_ids).delete()
        print(f"✅ Synced and cleaned {obj_type} → {sync_ids}")

    # -----------------------
    # 5. Prepare Worker Tasks and Resources
    # -----------------------
    active_tasks = Task.objects.filter(_delete=False, registered=False)  # skip already registered
    delete_tasks = Task.objects.filter(_delete=True)  # include deletes
    workers_payload = {}

    for task in active_tasks.union(delete_tasks):
        if not task.server:
            continue
        worker_ip = task.server.public_ip
        workers_payload.setdefault(worker_ip, {"tasks": [], "resources": {"bots": [], "devices": []}})

        # Attach bot + device resources first
        _bot = None
        if task.profile:
            _bot = bot_handler.formatify_for_server(task.profile)
        elif task.alloted_bots:
            for username in task.alloted_bots.split(","):
                _bot = bot_handler.formatify_for_server(username)

        if _bot:
            if _bot not in workers_payload[worker_ip]["resources"]["bots"]:
                workers_payload[worker_ip]["resources"]["bots"].append({"type": "bot", "data": _bot, "method": "create"})
            if _bot.get("device"):
                _device = device_handler.formatify_for_worker(_bot["device"])
                if _device not in workers_payload[worker_ip]["resources"]["devices"]:
                    workers_payload[worker_ip]["resources"]["devices"].append({"type": "device", "data": _device, "method": "create"})

        # Convert task to dict
        task_dict = model_to_dict(task)
        if task.dependent_on:
            task_dict["dependent_on"] = str(task.dependent_on.uuid)
        task_dict.update({
            "method": "delete" if task._delete else "create",
            "ref_id": str(task_dict.get("ref_id")),
            "created_at": str(task_dict.get("created_at")),
            "registered": True,
            "status": task.status
        })
        workers_payload[worker_ip]["tasks"].append(task_dict)

    # -----------------------
    # 6. Send resources first, then tasks atomically
    # -----------------------
    for worker_ip, payload in workers_payload.items():
        try:
            resources_url = f"{worker_ip}crawl/api/resources/"
            tasks_url = f"{worker_ip}crawl/api/tasks/"

            # Send resources first
            r = requests.post(
                resources_url,
                data=json.dumps({"resources": payload["resources"]}),
                headers={"Content-Type": "application/json"}
            )
            r.raise_for_status()

            # Send tasks second
            t = requests.post(
                tasks_url,
                data=json.dumps(payload["tasks"]),
                headers={"Content-Type": "application/json"}
            )
            t.raise_for_status()

            # Mark sent tasks as registered
            active_tasks.filter(server__public_ip=worker_ip).update(registered=True)
            delete_tasks.filter(server__public_ip=worker_ip).delete()
            print(f"✅ Worker {worker_ip} tasks & resources synced successfully")

        except Exception as e:
            print(f"Error sending resources/tasks to worker {worker_ip}: {e}")
        
        
def send_comand_to_instance(instance_id, data, model_config=None):
    """Send a command to an Instance.

    Current implement uses  http to send 
    commands to the http client on the Instance.
    Ideas for Future improvement
    is directly sending messages using a message broker
    (This is currently being used by Darrxscale Scrap Engine) 

    Args:
        instance_id ([type]): [description]
        data ([type]): [description]
        model_config ([type], optional): [description]. Defaults to None.

    Returns:
        [type]: [description]
    """
    task_model = _get_task_model_from_config(model_config)
    instance_object = EC2Instance.objects.get(instance_id=instance_id)
    main_server = EC2Instance.objects.filter(instance_type='main').first()
    if not main_server:
        return (
            "Failed to send request master node not found",
        )
    url = instance_object.public_ip+'/operation/child_server/'
    print(url)
    data.update({
        'main_ip': main_server.public_ip,
        'server_ip': instance_object.public_ip,
        'instance_id': instance_object.instance_id,
    })

    response = requests.post(url, data=json.dumps(data), timeout=REQUEST_TTL)
    print(response)
    response = response.json() if response.ok else response.reason
    result = (
        response,
        'CommandSent',
        'Successfully sent command to worker instance:%s' % instance_object.instance_id,
        'Successfully sent command'
    )

    if task_model:
        output = Output(text={
            'message': result[1],
            'display': result[3],
            'info': result[2],
            'server_response': result[0]
        })
        output.save()
        task_model.outputs.add(output)
        task_model.save()

    return result



@shared_task
def update_childbot_statuses():
    import datetime
    import requests
    from django_redis import get_redis_connection
    from sessionbot.utils import DataHouseClient
    from sessionbot.models import Task, Server, ChildBot

    logger.info("🚀 Starting Childbot status update process.")
    redis_conn = get_redis_connection("default")

    reporting_house = Server.objects.filter(instance_type="reporting_and_analytics_server").first()
    data_server = Server.objects.filter(instance_type="data_server").first()
    if not reporting_house or not reporting_house.public_ip:
        logger.error("❌ Reporting House server not configured properly. Aborting update.")
        return False
    if not data_server:
        logger.error("❌ Data server not found. Aborting update.")
        return False

    base_url = reporting_house.public_ip.rstrip("/") + "/reporting/task-summaries/"
    d = DataHouseClient()
    d.base_url = data_server.public_ip

    updated_count = 0

    # ✅ 1. Iterate over all ChildBots
    for bot in ChildBot.objects.all():
        # 2. Find latest task for this bot
        latest_task = Task.objects.filter(profile=bot.username).order_by("-created_at").first()
        if not latest_task:
            continue

        task_uuid = str(latest_task.uuid)

        # 3. Fetch latest report
        try:
            response = requests.get(f"{base_url}{task_uuid}/", timeout=10)
            response.raise_for_status()
            summary = response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Failed to fetch report for task {task_uuid}: {e}")
            continue

        latest_dt_str = summary.get("latest_report_end_datetime")
        login_status = summary.get("latest_login_status")
        if not latest_dt_str or not login_status:
            continue

        try:
            latest_dt = datetime.datetime.fromisoformat(latest_dt_str.replace("Z", "+00:00"))
        except ValueError:
            continue

        # 4. Check Redis (per bot)
        redis_key = f"last_notified_bot_status:{bot.username}"
        last_notified_bytes = redis_conn.get(redis_key)
        last_notified_dt = None
        if last_notified_bytes:
            try:
                last_notified_dt = datetime.datetime.fromisoformat(
                    last_notified_bytes.decode("utf-8").replace("Z", "+00:00")
                )
            except ValueError:
                pass

        # ✅ Skip if no new report
        if last_notified_dt is not None and latest_dt <= last_notified_dt:
            continue

        # --- Update bot fields ---
        bot.logged_in = login_status.lower() == "success"

        last_run_str = summary.get("last_report_datetime")
        if last_run_str:
            try:
                bot.last_run_at = datetime.datetime.fromisoformat(last_run_str.replace("Z", "+00:00"))
            except ValueError:
                pass

        scraped_so_far = summary.get("total_users_scraped")
        if scraped_so_far is not None:
            bot.scraped_so_far = scraped_so_far

        data_point = latest_task.data_point
        if data_point and data_point.lower() != "login":
            bot.is_scraper = True

        # --- Count API requests ---
        bot_task_uuids = list(Task.objects.filter(profile=bot.username).values_list("uuid", flat=True))

        if bot_task_uuids:
            successful_payload = {
                "object_type": "requestlog",
                "filters": {"task__uuid.in": bot_task_uuids, "status_code.in": [200]},
                "count": True,
            }
            failed_payload = {
                "object_type": "requestlog",
                "filters": {"task__uuid.in": bot_task_uuids, "status_code.in": [400, 401, 500]},
                "count": True,
            }

            successful_api_requests = d.retrieve(**successful_payload)
            failed_api_requests = d.retrieve(**failed_payload)

            if isinstance(successful_api_requests, dict):
                bot.successful_api_requests = successful_api_requests.get("count", 0)
            if isinstance(failed_api_requests, dict):
                bot.failed_api_requests = failed_api_requests.get("count", 0)

        # Save updates to DB
        bot.save(
            update_fields=[
                "logged_in",
                "last_run_at",
                "scraped_so_far",
                "is_scraper",
                "successful_api_requests",
                "failed_api_requests",
            ]
        )

        # 5. Only send Slack if login was SUCCESS
        if login_status.lower() == "success":
            slack_blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"✅ Bot *{bot.username}* just logged in successfully!",
                    },
                }
            ]
            send_slack_message(slack_blocks, channel="Client")
            redis_conn.set(redis_key, latest_dt_str)  # remember last notification time
            logger.info(f"🔔 Sent login notification for bot {bot.username}")

        updated_count += 1

    logger.info(f"✅ Childbot status update complete. {updated_count} bots processed.")






@shared_task()
def analyze_and_create_update_metrics_for_scrapetask():
    import requests
    from django.db.models import Q
    from sessionbot.models import ScrapeTask, Task, Server

    # --- Data Server Metrics ---
    d = DataHouseClient()
    data_server = Server.objects.filter(instance_type='data_server').first()
    if not data_server:
        print("❌ Data server not found.")
        return
    d.base_url = data_server.public_ip

    # Reporting Server
    reporting_server = Server.objects.filter(instance_type="reporting_and_analytics_server").first()
    if not reporting_server:
        print("❌ Reporting server not found.")
        return
    analytics_base_url = reporting_server.public_ip

    for scrapetask in ScrapeTask.objects.all():
        scraping_tasks = Task.objects.filter(ref_id=scrapetask.uuid)
        task_uuids = list(scraping_tasks.values_list('uuid', flat=True))

        if not task_uuids:
            continue

        # --- Existing Data Server Counts ---
        scraped_so_far_payload = {
            "object_type": "profile",
            "filters": {"tasks__uuid.in": task_uuids},
            "count": True
        }
        scraped_so_far = d.retrieve(**scraped_so_far_payload)
        if isinstance(scraped_so_far, dict):
            scrapetask.scraped_so_far = scraped_so_far.get('count', 0)

        successful_payload = {
            "object_type": "requestlog",
            "filters": {"task__uuid.in": task_uuids, "status_code.in": [200]},
            "count": True
        }
        successful_api_requests = d.retrieve(**successful_payload)
        if isinstance(successful_api_requests, dict):
            scrapetask.successful_request_count = successful_api_requests.get('count', 0)

        failed_payload = {
            "object_type": "requestlog",
            "filters": {"task__uuid.in": task_uuids, "status_code.in": [400, 500, 401]},
            "count": True
        }
        failed_api_requests = d.retrieve(**failed_payload)
        if isinstance(failed_api_requests, dict):
            scrapetask.failed_request_count = failed_api_requests.get('count', 0)

        block_payload = {
            "object_type": "requestlog",
            "filters": {"task__uuid.in": task_uuids, "data__status": "fail"},
            "count": True
        }
        block_api_requests = d.retrieve(**block_payload)
        if isinstance(block_api_requests, dict):
            scrapetask.blocks_encountered = block_api_requests.get('count', 0)

        # --- New Reporting Server Metrics ---
        total_downloaded_files = 0
        total_storage_uploads = 0
        missing_summaries = []

        bot_status = {}

        for task_uuid in task_uuids:
            try:
                summary_url = analytics_base_url + f"reporting/task-summaries/{task_uuid}/"
                resp = requests.get(summary_url, timeout=10)

                if resp.status_code != 200:
                    print(f"⚠ Failed to fetch summary for task {task_uuid} - {resp.status_code}")
                    missing_summaries.append(task_uuid)
                    continue

                summary = resp.json()
                total_downloaded_files += summary.get("total_downloaded_files", 0)
                total_storage_uploads += summary.get("total_storage_uploads", 0)

                task_obj = scraping_tasks.filter(uuid=task_uuid).first()
                if task_obj:
                    bot_name = task_obj.profile
                    latest_login_status = summary.get("latest_login_status", "unknown")

                    if latest_login_status == "success":
                        status_to_store = "Logged In"
                    else:
                        status_to_store = latest_login_status

                    bot_status[bot_name] = status_to_store

            except Exception as e:
                print(f"❌ Error fetching summary for {task_uuid}: {e}")
                missing_summaries.append(task_uuid)
                continue

        scrapetask.media_downloaded = total_downloaded_files
        scrapetask.media_stored = total_storage_uploads

        if bot_status:
            scrapetask.bot_status = bot_status

        scrapetask.save()

        print(f"✅ Updated metrics for ScrapeTask {scrapetask.uuid}")
        if missing_summaries:
            print(f"❌ Missing summaries for UUIDs: {missing_summaries}")
            
    # --- Update all Tasks status based on their summary ---
    all_tasks = Task.objects.all()
    missing_summaries_for_tasks = []

    for task in all_tasks:
        try:
            summary_url = f"{analytics_base_url}reporting/task-summaries/{task.uuid}/"
            resp = requests.get(summary_url, timeout=10)

            if resp.status_code != 200:
                print(f"⚠ Failed to fetch summary for task {task.uuid} - {resp.status_code}")
                missing_summaries_for_tasks.append(task.uuid)
                continue

            summary = resp.json()

            # Determine which status to use based on task.data_point
            if task.data_point == "login":
                raw_status = summary.get("latest_task_status")
            else:
                raw_status = summary.get("task_completion_status")

            if raw_status:
                # Normalize status mapping
                normalized_status = raw_status.strip().lower()
                if normalized_status in ["success", "completed successfully"]:
                    mapped_status = "completed"
                else:
                    mapped_status = "failed"

                if mapped_status != task.status:
                    task.status = mapped_status
                    task.save(update_fields=["status"])

        except Exception as e:
            print(f"❌ Error fetching summary for task {task.uuid}: {e}")
            missing_summaries_for_tasks.append(task.uuid)
            continue

    if missing_summaries_for_tasks:
        print(f"❌ Missing summaries for task UUIDs: {missing_summaries_for_tasks}")

# central/tasks.py (or similar path in your Django project)

import logging
import requests
import uuid
from datetime import datetime, timezone
from collections import defaultdict

from celery import shared_task
from django.conf import settings

# Import your Django models
from sessionbot.models import ScrapeTask, Task
# Assuming your Slack utility is here
from sessionbot.slack_utils import send_structured_slack_message as send_slack_message


logger = logging.getLogger(__name__)

# Ensure REPORTING_API_BASE_URL is defined in your Django settings.py
# Example: REPORTING_API_BASE_URL = 'http://192.168.1.30:81/'



# central/tasks.py

import logging
import requests
import uuid
from datetime import datetime, timezone # Correct import for datetime and timezone
from collections import defaultdict
import json # Useful for general Redis operations, though not strictly needed for simple string sets

from celery import shared_task
from django.conf import settings
from django_redis import get_redis_connection # Import for Redis connection

# Import your Django models (ensure these paths are correct for your project)
from sessionbot.models import ScrapeTask, Task, Server # Assuming Server model is in central.models
# Assuming your Slack utility is here
from sessionbot.slack_utils import send_structured_slack_message as send_slack_message


logger = logging.getLogger(__name__)

# --- Configuration Notes ---
# Ensure your Redis CACHES are configured in settings.py, e.g.:
# CACHES = {
#     "default": {
#         "BACKEND": "django_redis.cache.RedisCache",
#         "LOCATION": "redis://127.0.0.1:6379/1", # Or your Redis URL. Use a dedicated DB for notifications if possible.
#         "OPTIONS": {
#             "CLIENT_CLASS": "django_redis.client.DefaultClient",
#         }
#     }
# }
# --- End Configuration Notes ---




@shared_task
def process_scrape_task_alerts(scrape_task_uuid: str = None):
    logger.info(f"Starting scrape task alerts processing for UUID: {scrape_task_uuid or 'all'}.")

    redis_conn = get_redis_connection("default")

    query_set = ScrapeTask.objects.all()
    if scrape_task_uuid:
        try:
            uuid.UUID(scrape_task_uuid)
            query_set = query_set.filter(uuid=scrape_task_uuid)
        except ValueError:
            logger.error(f"Invalid UUID format: {scrape_task_uuid}")
            return

    if not query_set.exists():
        logger.warning(f"No ScrapeTask found for UUID: {scrape_task_uuid or 'all'}. Exiting.")
        return

    reporting_server = Server.objects.filter(instance_type="reporting_and_analytics_server").first()
    if not reporting_server:
        print("❌ Reporting server not found.")
        return
    analytics_base_url = reporting_server.public_ip

    for scrape_task in query_set:
        logger.info(f"Processing ScrapeTask: {scrape_task.name} ({scrape_task.uuid})")

        central_tasks = Task.objects.filter(ref_id=scrape_task.uuid)
        if not central_tasks.exists():
            logger.warning(f"No tasks found for ScrapeTask: {scrape_task.name}. Skipping alert.")
            continue

        should_send_notification = False
        newly_processed_task_timestamps = {}

        aggregated_by_data_input = defaultdict(lambda: {
            'total_users_scraped': 0,
            'total_downloaded_files': 0,
            'total_storage_uploads': 0,
            'failed_to_download_file_count': 0,
            'critical_events': 0,
            "total_runs_completed": 0,
        })
        individual_bot_metrics = defaultdict(dict)
        critical_issues = []
        overall_scrape_task_status = "Completed"

        for task in central_tasks:
            report_url = f"{analytics_base_url}reporting/task-summaries/{task.uuid}/"
            try:
                response = requests.get(report_url, timeout=10)
                response.raise_for_status()
                summary = response.json()
            except Exception as e:
                logger.error(f"Failed to fetch summary from {report_url}: {e}")
                continue

            # Redis logic for last notified
            redis_key = f"last_notified_task_summary:{task.uuid}"
            last_notified_bytes = redis_conn.get(redis_key)
            last_notified_dt = None
            if last_notified_bytes:
                try:
                    last_notified_dt = datetime.datetime.fromisoformat(
                        last_notified_bytes.decode("utf-8").replace("Z", "+00:00")
                    )
                except ValueError:
                    should_send_notification = True

            last_report_datetime = summary.get("last_report_datetime")
            if last_report_datetime:
                last_report_dt = datetime.datetime.fromisoformat(last_report_datetime.replace("Z", "+00:00"))
                if last_notified_dt is None or last_report_dt > last_notified_dt:
                    should_send_notification = True
                    newly_processed_task_timestamps[task.uuid] = last_report_dt.isoformat()

            # Aggregate metrics
            key = (task.data_point, task.input)
            aggregated_by_data_input[key]['total_users_scraped'] += summary.get("total_users_scraped", 0)
            aggregated_by_data_input[key]['total_downloaded_files'] += summary.get("total_downloaded_files", 0)
            aggregated_by_data_input[key]['total_storage_uploads'] += summary.get("total_storage_uploads", 0)
            aggregated_by_data_input[key]['failed_to_download_file_count'] += summary.get("failed_to_download_file_count", 0)
            aggregated_by_data_input[key]['critical_events'] += summary.get("total_critical_events", 0)
            aggregated_by_data_input[key]['total_runs_completed'] += summary.get("total_reports_considered", 0)
            

            # Individual bot metrics
            username = task.profile
            if username:
                individual_bot_metrics[username] = {
                    "status": summary.get("latest_login_status", "N/A"),
                    "total_users_scraped": summary.get("total_users_scraped", 0),
                    "failed_downloads_details": summary.get("failed_downloads_details"),
                    "critical_events_summary": summary.get("critical_events_summary"),
                    "total_runs_completed": summary.get("total_reports_considered",0)

                }

            # Overall status & critical issues
            latest_task_status = summary.get("latest_task_status")
            if "Failed" in latest_task_status:
                overall_scrape_task_status = "Failed"
            elif latest_task_status == "Incomplete" and overall_scrape_task_status != "Failed":
                overall_scrape_task_status = "Incomplete"

            if summary.get("failed_downloads_details"):
                critical_issues.append(f"Task {task.uuid[:8]} has failed downloads.")
            if summary.get("total_critical_events", 0) > 0:
                critical_issues.append(f"Task {task.uuid[:8]} has {summary['total_critical_events']} critical events.")

        # Send Slack alert if needed
        if should_send_notification:
            slack_blocks = _build_slack_message_blocks(
                scrape_task=scrape_task,
                overall_scrape_task_status=overall_scrape_task_status,
                aggregated_by_data_input=aggregated_by_data_input,
                individual_bot_metrics=individual_bot_metrics,
                critical_issues=critical_issues,
            )

            try:
                send_slack_message(slack_blocks, channel="Client")
                logger.info(f"Slack alert sent for ScrapeTask: {scrape_task.name}")

                # Update Redis keys
                for task_uuid_to_update, timestamp_str in newly_processed_task_timestamps.items():
                    redis_conn.set(f"last_notified_task_summary:{task_uuid_to_update}", timestamp_str)
                    logger.debug(f"Updated Redis {task_uuid_to_update} -> {timestamp_str}")

            except Exception as e:
                logger.error(f"Failed to send Slack message for ScrapeTask {scrape_task.name}: {e}")
        else:
            logger.info(f"No new data for ScrapeTask: {scrape_task.name}. Skipping Slack notification.")

    logger.info("Scrape task alerts processing finished.")

def _build_slack_message_blocks(scrape_task, overall_scrape_task_status,
                                 aggregated_by_data_input, individual_bot_metrics,
                                 critical_issues):
    """
    Helper function to construct the Slack message blocks with new TaskSummaryReportNew fields.
    """
    from datetime import timezone
    blocks = []

    # Header Section
    blocks.append({
        "type": "header",
        "text": {
            "type": "plain_text",
            "text": f"📊 ScrapeTask Performance Alert: {scrape_task.name}",
            "emoji": True
        }
    })
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": f"Scrape Task ID: `{scrape_task.uuid}` | Generated: {datetime.datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
            }
        ]
    })
    blocks.append({"type": "divider"})

    # Overall Status
    status_emoji = "✅" if overall_scrape_task_status == "Completed" else \
                   "🟡" if overall_scrape_task_status == "Running" else \
                   "⚠️" if overall_scrape_task_status == "Incomplete" else \
                   "❌"
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"*Overall ScrapeTask Status:* {status_emoji} {overall_scrape_task_status}"
        }
    })
    blocks.append({"type": "divider"})

    # Critical Issues
    if critical_issues:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "🚨 *Critical Issues Detected:*"}
        })
        for issue in sorted(set(critical_issues)):
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"• {issue}"}
            })
        blocks.append({"type": "divider"})

    # Aggregated Data
    blocks.append({
        "type": "section",
        "text": {"type": "mrkdwn", "text": "*🔬 Aggregated Data by Target:*"}
    })
    if aggregated_by_data_input:
        sorted_aggregated = sorted(aggregated_by_data_input.items(), key=lambda item: (item[0][0], item[0][1]))
        for (data_point, input_value), metrics in sorted_aggregated:
            metrics_text = []
            for key, value in sorted(metrics.items()):
                if not value:
                    continue
                display_key = key.replace('_', ' ').title()
                if key == "total_users_scraped":
                    display_key = "Users Scraped"
                elif key == "total_downloaded_files":
                    display_key = "Files Downloaded"
                elif key == "total_storage_uploads":
                    display_key = "Files Uploaded"
                elif key == "failed_to_download_file_count":
                    display_key = "Failed Downloads"
                elif key == "critical_events":
                    display_key = "Critical Events"
                elif key == "total_runs_completed":
                    display_key = "Total Runs Completed"

                metrics_text.append(f"{display_key}: *{value}*")

            if metrics_text:
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{data_point}* (Input: `{input_value}`)\n" + ", ".join(metrics_text)
                    }
                })
        blocks.append({"type": "divider"})
    else:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "No aggregated data available for this ScrapeTask."}
        })
        blocks.append({"type": "divider"})

    # Individual Bot Metrics
    blocks.append({
        "type": "section",
        "text": {"type": "mrkdwn", "text": "*🤖 Individual Bot Statuses:*"}
    })
    if individual_bot_metrics:
        for username, bot_info in sorted(individual_bot_metrics.items(), key=lambda item: item[0]):
            status = bot_info.get("status", "N/A")
            emoji = "✅" if status.lower() == "success" else "❌"

            metrics_lines = []
            for key, value in bot_info.items():
                if key in ['status', 'latest_report_end_datetime', 'associated_task_uuids']:
                    continue
                if not value:
                    continue

                display_key = key.replace('_', ' ').title()
                if key == "total_users_scraped":
                    display_key = "Users Scraped"
                elif key == "total_downloaded_files":
                    display_key = "Files Downloaded"
                elif key == "total_storage_uploads":
                    display_key = "Files Uploaded"
                elif key == "failed_to_download_file_count":
                    display_key = "Failed Downloads"
                elif key == "critical_events_summary":
                    display_key = "Critical Events"
                elif key == "total_runs_completed":
                    display_key = "Total Runs Completed"

                # 👇 Pretty formatting
                if isinstance(value, list):
                    # Show first 2 items nicely, then "and N more..."
                    if len(value) > 0:
                        formatted_items = []
                        for item in value[:2]:  # limit output
                            if isinstance(item, dict):
                                formatted_items.append("> " + ", ".join(f"*{k}*: {v}" for k, v in item.items() if v))
                            else:
                                formatted_items.append(f"> {item}")
                        if len(value) > 2:
                            formatted_items.append(f"> …and {len(value)-2} more")
                        metrics_lines.append(f"*{display_key}:*\n" + "\n".join(formatted_items))
                elif isinstance(value, dict):
                    formatted_items = [f"*{k}*: {v}" for k, v in value.items() if v]
                    metrics_lines.append(f"*{display_key}:*\n" + "\n".join(["> " + line for line in formatted_items]))
                else:
                    metrics_lines.append(f"*{display_key}:* {value}")

            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"• *Bot:* `{username}`  Status: {emoji} {status}\n" + "\n".join(metrics_lines)
                }
            })


        blocks.append({"type": "divider"})
    else:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "No individual bot metrics available."}
        })
        blocks.append({"type": "divider"})

    # Footer
    blocks.append({
        "type": "context",
        "elements": [
            {"type": "mrkdwn", "text": f"Generated at {datetime.datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"}
        ]
    })

    return blocks




from celery import shared_task
import requests
import datetime
from .models import Server, Event, Heartbeat, ResourceUsage
from django.conf import settings
from django.core.mail import send_mail

@shared_task
def collect_system_status():
    servers = Server.objects.filter(poll_for_status=True)  # Only poll servers marked for polling

    for server in servers:
        status_url = f"http://{server.ip_address}/api/monitor/system-status/"

        try:
            response = requests.get(status_url)
            response.raise_for_status()
            status_data = response.json()
            timestamp = status_data.get('timestamp')
            heartbeat_data = status_data.get('heartbeat', {})
            resource_data = status_data.get('resources', {})

            if timestamp:
                Event.objects.create(
                    server=server,
                    event_type='heartbeat',
                    timestamp=timestamp,
                    payload={'timestamp': timestamp, **heartbeat_data}
                )
                Event.objects.create(
                    server=server,
                    event_type='resource',
                    timestamp=timestamp,
                    payload={'timestamp': timestamp, **resource_data}
                )
                print(f"[{datetime.datetime.now()}] System status collected from {server.name} at {timestamp}")
            else:
                print(f"[{datetime.datetime.now()}] Timestamp missing in response from {server.name}")

        except requests.exceptions.RequestException as e:
            print(f"[{datetime.datetime.now()}] Error collecting system status from {server.name}: {e}")
        except ValueError:
            print(f"[{datetime.datetime.now()}] Error decoding JSON from {server.name}")


@shared_task
def process_event_for_servers(event_id):
   
    try:
        event = Event.objects.get(id=event_id)

        if event.event_type == 'heartbeat':
            timestamp_str = event.payload.get('timestamp')
            if timestamp_str:
                    # Assuming the client sends the timestamp as a string,
                    # parse it and make it UTC-aware
                    naive_dt = datetime.datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    utc_aware_dt = timezone.make_aware(naive_dt, timezone=timezone.utc)
            else:
                utc_aware_dt = timezone.now()  # Or handle the missing timestamp appropriately

            Heartbeat.objects.create(
                server=event.server,
                timestamp=utc_aware_dt,
                hostname=event.payload.get('hostname'),
                os=event.payload.get('os'),
            )
        elif event.event_type == 'resource':
            ResourceUsage.objects.create(
                server=event.server,
                timestamp=event.timestamp,
                cpu_percent=event.payload.get('cpu_percent'),
                memory_percent=event.payload.get('memory_percent'),
                disk_percent=event.payload.get('disk_percent'),
                received_at=event.received_at
            )
    except Event.DoesNotExist:
        print(f"Event with ID {event_id} not found.")
    except Exception as e:
        print(f"Error processing event for models {event_id}: {e}")



@shared_task
def check_resource_alerts():
    now = datetime.datetime.now()
    latest_resources = ResourceUsage.objects.filter(
        received_at__gte=now - datetime.timedelta(minutes=5)  # Check recent events
    ).order_by('server', '-received_at').distinct('server')

    CPU_THRESHOLD_PERCENT = settings.CPU_THRESHOLD_PERCENT
    MEMORY_THRESHOLD_PERCENT = settings.MEMORY_THRESHOLD_PERCENT
    DISK_THRESHOLD_PERCENT = settings.DISK_THRESHOLD_PERCENT
    ALERT_RECIPIENTS = settings.ALERT_RECIPIENTS
    ALERT_SUBJECT_PREFIX = settings.ALERT_SUBJECT_PREFIX
    SMTP_SERVER = settings.EMAIL_HOST
    SMTP_PORT = settings.EMAIL_PORT
    SMTP_USERNAME = settings.EMAIL_HOST_USER
    SMTP_PASSWORD = settings.EMAIL_HOST_PASSWORD

    for resource in latest_resources:
        if resource.cpu_percent is not None and resource.cpu_percent > CPU_THRESHOLD_PERCENT:
            send_alert_email.delay("CPU Usage Alert", f"[{resource.timestamp}] High CPU on {resource.server.name}: {resource.cpu_percent}%", ALERT_RECIPIENTS, SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD)

        if resource.memory_percent is not None and resource.memory_percent > MEMORY_THRESHOLD_PERCENT:
            send_alert_email.delay("Memory Usage Alert", f"[{resource.timestamp}] High Memory on {resource.server.name}: {resource.memory_percent}%", ALERT_RECIPIENTS, SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD)

        if resource.disk_percent is not None and resource.disk_percent > DISK_THRESHOLD_PERCENT:
            send_alert_email.delay("Disk Usage Alert", f"[{resource.timestamp}] High Disk on {resource.server.name}: {resource.disk_percent}%", ALERT_RECIPIENTS, SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD)

@shared_task
def send_alert_email(subject, body, recipients, smtp_server, smtp_port, smtp_username, smtp_password):
    try:
        send_mail(
           '' + subject,
            body,
            smtp_username,  # From address
            recipients,
            fail_silently=False,
        )
        print(f"[{datetime.datetime.now()}] Central server alert email sent: {subject} to {recipients}")
    except Exception as e:
        print(f"[{datetime.datetime.now()}] Central server error sending email: {e}")




from celery import shared_task
import datetime as dt
from django.utils import timezone
from .models import Server, Heartbeat, ResourceUsage
from django.conf import settings
from django.core.mail import send_mail
import pytz


@shared_task
def monitor_server_health():
    print(timezone.now())
    print(settings.HEARTBEAT_TIMEOUT_MINUTES)
    import pytz
    ak=pytz.timezone('Asia/Karachi')
    offline_threshold =timezone.now() - dt.timedelta(minutes=settings.HEARTBEAT_TIMEOUT_MINUTES,hours=0)
    cpu_threshold = settings.RESOURCE_THRESHOLD_PERCENT
    memory_threshold = settings.RESOURCE_THRESHOLD_PERCENT
    disk_threshold = settings.RESOURCE_THRESHOLD_PERCENT
    alert_recipients = settings.ALERT_RECIPIENTS
    alert_subject_prefix = settings.ALERT_SUBJECT_PREFIX
    smtp_server = settings.EMAIL_HOST
    smtp_port = settings.EMAIL_PORT
    smtp_username = settings.EMAIL_HOST_USER
    smtp_password = settings.EMAIL_HOST_PASSWORD

    servers = Server.objects.all()
    import pytz
    local_tz=pytz.timezone(settings.TIME_ZONE)
    for server in servers:
        print(server)
        # Check for Heartbeat

        latest_heartbeat = Heartbeat.objects.filter(server=server).order_by('-timestamp').first()
        if latest_heartbeat:
            aware_timestamp_utc=latest_heartbeat.timestamp
        else:
            aware_timestamp_utc=False
        print(aware_timestamp_utc)
        print(offline_threshold)
       
        if not aware_timestamp_utc or aware_timestamp_utc < offline_threshold:
            print(server.online_status)
            if server.online_status != 'offline':
                server.online_status = 'offline'
                server.save()
                notification_message = f"Server '{server.name}' ({server.public_ip}) is offline - No recent heartbeat."
                send_server_status_notification.delay(server.name, notification_message, alert_recipients, smtp_server, smtp_port, smtp_username, smtp_password)
                print(f"[{timezone.now()}] Server '{server.name}' marked as offline.")
        elif server.state == 'offline':
            server.online_status = 'online'
            server.save()
            notification_message = f"Server '{server.name}' ({server.public}) is back online - Heartbeat received."
            send_server_status_notification.delay(server.name, notification_message, alert_recipients, smtp_server, smtp_port, smtp_username, smtp_password)
            print(f"[{timezone.now()}] Server '{server.name}' marked as online.")

        # Check for Resource Usage
        latest_resource = ResourceUsage.objects.filter(server=server).order_by('-timestamp').first()
        if latest_resource:
            health_status = 'healthy'
            reason = []
            if latest_resource.cpu_percent is not None and latest_resource.cpu_percent > cpu_threshold:
                health_status = 'unhealthy'
                reason.append(f"CPU usage: {latest_resource.cpu_percent}% > {cpu_threshold}%")
            if latest_resource.memory_percent is not None and latest_resource.memory_percent > memory_threshold:
                if health_status == 'healthy':
                    health_status = 'unhealthy'
                reason.append(f"Memory usage: {latest_resource.memory_percent}% > {memory_threshold}%")
            if latest_resource.disk_percent is not None and latest_resource.disk_percent > disk_threshold:
                if health_status == 'healthy':
                    health_status = 'unhealthy'
                reason.append(f"Disk usage: {latest_resource.disk_percent}% > {disk_threshold}%")

            if health_status == 'unhealthy' and server.health != 'unhealthy':
                server.health = 'unhealthy'
                #server.health_reason = ", ".join(reason)
                server.save()
                notification_message = f"Server '{server.name}' ({server.ip_address}) is unhealthy - {server.health_reason}."
                send_server_health_notification.delay(server.name, notification_message, alert_recipients, smtp_server, smtp_port, smtp_username, smtp_password)
                print(f"[{timezone.now()}] Server '{server.name}' marked as unhealthy: {server.health_reason}")
            elif health_status == 'healthy' and server.health != 'healthy':
                server.health = 'healthy'
                #server.health_reason = ''
                server.save()
                print(f"[{timezone.now()}] Server '{server.name}' marked as healthy.")

@shared_task
def send_server_status_notification(server_name, message, recipients, smtp_server, smtp_port, smtp_username, smtp_password):
    try:
        send_mail(
            f"{settings.ALERT_SUBJECT_PREFIX} Server Status Change: {server_name}",
            message,
            smtp_username,  # From address
            recipients,
            fail_silently=False,
        )
        print(f"[{timezone.now()}] Server status notification sent: {message} to {recipients}")
    except Exception as e:
        print(f"[{timezone.now()}] Error sending server status notification: {e}")

@shared_task
def send_server_health_notification(server_name, message, recipients, smtp_server, smtp_port, smtp_username, smtp_password):
    try:
        send_mail(
            f"{settings.ALERT_SUBJECT_PREFIX} Server Health Alert: {server_name}",
            message,
            smtp_username,  # From address
            recipients,
            fail_silently=False,
        )
        print(f"[{timezone.now()}] Server health notification sent: {message} to {recipients}")
    except Exception as e:
        print(f"[{timezone.now()}] Error sending server health notification: {e}")

@shared_task
def process_task_event(event_data):
    event_type = event_data.get('event_type')
    task_data = event_data.get('payload', {})
    uuid = task_data.get('uuid')

    if not uuid:
        print(f"[{timezone.now()}] Received task event without UUID. Ignoring.")
        return

    try:
        task = Task.objects.get(uuid=uuid)
        print(f"[{timezone.now()}] Found existing task with UUID: {uuid}, status: {task.status}")

        if event_type == 'task_started':
            if task.status != 'started':
                task.status = 'started'
                task.last_state_changed_at = timezone.now()
                task.save()
                print(f"[{timezone.now()}] Task {uuid} status updated to started.")
        elif event_type == 'task_completed':
            task.status = 'completed'
            task.last_state_changed_at = timezone.now()
            task.save()
            print(f"[{timezone.now()}] Task {uuid} status updated to completed.")
        elif event_type == 'task_failed':
            task.status = 'failed'
            task.last_state_changed_at = timezone.now()
            task.save()
            print(f"[{timezone.now()}] Task {uuid} status updated to failed.")
        elif event_type == 'task_stopped':
            task.status = 'stopped'
            task.last_state_changed_at = timezone.now()
            task.save()
            print(f"[{timezone.now()}] Task {uuid} status updated to stopped.")
            add_data = task_data.get('add_data', {})
            data_source = add_data.get('data_source', [])
            for source in data_source:
                if source.get('lock_results'):
                    # In a real scenario, you would have logic to release the lock
                    # For this example, we are just commenting it out.
                    print(f"[{timezone.now()}] Task {uuid}: Lock for data source {source} would be released (commented out).")
                    # Logic to release the lock on the data source would go here
                    pass
        else:
            print(f"[{timezone.now()}] Received unknown task event type: {event_type} for UUID: {uuid}")

    except Task.DoesNotExist:
        if event_type == 'task_started':
            # Potential Security Flaw Highlighted:
            # Creating a task on the central system based solely on a 'task_started' event
            # from an external source without proper authentication and authorization
            # is a significant security vulnerability. Malicious actors could potentially
            # create arbitrary tasks on your central system by sending crafted events.
            #
            # In a production environment, you MUST have robust authentication and
            # authorization mechanisms in your EventView to verify the source and
            # legitimacy of 'task_started' events before creating tasks.

            Task.objects.create(
                uuid=uuid,
                service=task_data.get('service'),
                os=task_data.get('os'),
                interact=task_data.get('interact', False),
                end_point=task_data.get('end_point'),
                data_point=task_data.get('data_point'),
                input=task_data.get('input'),
                add_data=task_data.get('add_data'),
                run_id=task_data.get('run_id'),
                last_state_changed_at=timezone.now(),
                status='started',  # Assuming if we receive 'started' and don't find it, it's just started
                device=task_data.get('device'),
                ref_id=task_data.get('ref_id'),
                # Potentially map other relevant fields from the event
            )
            print(f"[{timezone.now()}] Task with UUID: {uuid} not found, created and set to started.")
        else:
            print(f"[{timezone.now()}] Task with UUID: {uuid} not found, and event type is not 'task_started'. Ignoring.")


        
        

from .models import  Task, ScrapeTask, Server,Issue
import traceback
@shared_task()
def fetch_and_update_task_errors():
    logger.info("Starting fetch_and_update_task_errors task...")

    reporting_server = Server.objects.filter(instance_type="reporting_and_analytics_server").first()
    if not reporting_server:
        logger.error("No reporting server found with instance_type='reporting_and_analytics_server'. Task aborted.")
        return

    analytics_base = reporting_server.public_ip


    logger.info(f"Using analytics base URL: {analytics_base}")

    all_tasks = Task.objects.all().order_by("-created_at")
    logger.info(f"Fetched {all_tasks.count()} tasks for processing.")

    for task in all_tasks:
        task_uuid = str(task.uuid)
        profile_name = getattr(task, "profile", None)

        if not profile_name:
            logger.warning(f"Task {task_uuid} has no associated profile. Skipping.")
            continue

        summary_url = analytics_base + f"reporting/task-summaries/{task_uuid}/"
        logger.debug(f"Fetching summary for Task UUID={task_uuid} (Profile={profile_name}) from {summary_url}")

        try:
            resp = requests.get(summary_url, timeout=10)
            if resp.status_code != 200:
                logger.error(f"Failed to fetch summary for Task {task_uuid}. Status code: {resp.status_code}")
                continue

            summary = resp.json()
            if not summary:
                logger.warning(f"No summary data returned for Task {task_uuid}.")
                continue

            # ---------- Condition 1: Incorrect Password ----------
            critical_events = summary.get("critical_events_summary", [])
            critical_errors_lower = [
                (e.get("type") if isinstance(e, dict) else str(e)).lower()
                for e in critical_events
            ]
            if any("incorrect_password" in err for err in critical_errors_lower):
                logger.info(f"Incorrect password detected for bot '{profile_name}'. Checking if issue already exists...")
                if not Issue.objects.filter(
                    name="Incorrect Password",
                    status__in=["open", "in_progress"],
                    affected_tasks__profile=profile_name
                ).exists():
                    with transaction.atomic():
                        affected_tasks = Task.objects.filter(profile=profile_name)
                        affected_tasks.update(status="failed")

                        issue = Issue.objects.create(
                            name="Incorrect Password",
                            description=f"Tasks failed due to incorrect password for bot '{profile_name}'.",
                            status="open"
                        )
                        issue.affected_tasks.add(*affected_tasks)
                        logger.info(f"Issue created: Incorrect Password for profile '{profile_name}'. {affected_tasks.count()} tasks updated.")
                        slack_blocks = [
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": f"Issue created: Incorrect Password for profile '{profile_name}'. {affected_tasks.count()} tasks updated.",
                                },
                            }
                        ]
                        send_slack_message(slack_blocks, channel="Client")

            # ---------- Condition 2: Login Attempt Failed > 10 ----------
            login_attempt_failed = summary.get("total_attempt_failed", 0)
            if login_attempt_failed and login_attempt_failed > 10:
                logger.info(f"Excessive login attempts ({login_attempt_failed}) for bot '{profile_name}'.")
                if not Issue.objects.filter(
                    name="Login Attempts Failed",
                    status__in=["open", "in_progress"],
                    affected_tasks__profile=profile_name
                ).exists():
                    with transaction.atomic():
                        affected_tasks = Task.objects.filter(profile=profile_name)
                        affected_tasks.exclude(status="failed").update(status="failed")

                        issue = Issue.objects.create(
                            name="Login Attempts Failed",
                            description=f"Tasks failed due to excessive login attempts for bot '{profile_name}'.",
                            status="open"
                        )
                        issue.affected_tasks.add(*affected_tasks)
                        logger.info(f"Issue created: Login Attempts Failed for '{profile_name}'. {affected_tasks.count()} tasks updated.")
                        slack_blocks = [
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": f"Issue created: Login Attempts Failed for '{profile_name}'. {affected_tasks.count()} tasks updated.",
                                },
                            }
                        ]
                        send_slack_message(slack_blocks, channel="Client")

            # ---------- Condition 3: Storage Upload Failed ----------
            storage_upload_failed = summary.get("storage_upload_failed", 0)
            if storage_upload_failed:
                logger.info(f"Storage upload failures detected ({storage_upload_failed}).")
                if not Issue.objects.filter(
                    name="Storage House Down",
                    status__in=["open", "in_progress"]
                ).exists():
                    with transaction.atomic():
                        affected_tasks = Task.objects.all()
                        affected_tasks.update(status="failed")

                        issue = Issue.objects.create(
                            name="Storage House Down",
                            description="Storage upload failed; all tasks stopped.",
                            status="open"
                        )
                        issue.affected_tasks.add(*affected_tasks)
                        logger.info(f"Issue created: Storage House Down. {affected_tasks.count()} tasks updated.")
                        slack_blocks = [
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": f"Issue created: Storage House Down. {affected_tasks.count()} tasks updated.",
                                },
                            }
                        ]
                        send_slack_message(slack_blocks, channel="Client")
        except requests.RequestException as e:
            logger.error(f"Network error fetching summary for Task {task_uuid}: {e}")
            logger.debug(traceback.format_exc())
        except Exception as e:
            logger.error(f"Unexpected error processing Task {task_uuid}: {e}")
            logger.debug(traceback.format_exc())
        
    logger.info("fetch_and_update_task_errors task completed.")



