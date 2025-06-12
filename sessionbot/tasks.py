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
@shared_task()
def sync_with_data_house_and_workers():
    """
    Celery task to sync with Data House and Workers (Data House is default).
    """
    data_house_url=False
    datahouse_server=Server.objects.all().filter(instance_type='data_server')
    if datahouse_server:
        data_house_url=datahouse_server[0].public_ip+'datahouse/api/sync/'
   
    if not data_house_url:
        print("Error: DATA_HOUSE_URL setting is not defined.")
        return

    target_payloads = {data_house_url: []}
    unique_object_ids = DataHouseSyncStatus.objects.values_list('object_id', flat=True).distinct()

    for object_id in unique_object_ids:
        with transaction.atomic():
            statuses = DataHouseSyncStatus.objects.filter(object_id=object_id).order_by('created_at')

            final_operation = None
            object_body = None
            model_instance = None
            model_class = None

            for i,status in enumerate(statuses):
                final_operation = status.operation
                model_class_name = status.model_name
                try:
                    model_class = apps.get_model('sessionbot', model_class_name)  # Replace 'your_app_name'
                    print(object_id)
                    model_instance = model_class.objects.get(uuid=object_id)
                    if not model_instance:
                        status.delete()
                        continue
                    object_body = model_instance.__dict__.copy()
                    if '_state' in object_body:
                        del object_body['_state']
                    print(object_body)
                    for key, value in object_body.items():
                        
                        print( isinstance(value, datetime.datetime))
                        if isinstance(value, models.Model):
                            print('m')
                            object_body[key] = str(value)
                        elif isinstance(value, datetime.datetime):
                            print('dt')
                            object_body[key] = value.isoformat()
                        elif isinstance(value, uuid.UUID):
                            print('t')
                            object_body[key] = str(value)
                        elif isinstance(value, bool):
                            object_body[key] = str(value).lower()

                except model_class.DoesNotExist:
                    print('model class not exist'+str(model_class))
                    object_body = None
                    model_instance = None
                    continue
                except Exception as e:
                    print(f"Error retrieving object {object_id}: {e}")
                    object_body = None
                    model_instance = None
                   
               
                   
                    status.delete()
                    continue
        
       
            if not model_instance and not final_operation=='DELETE':
                print(final_operation)
                print('continuing')
            
                continue
            from sessionbot.utils import convert_uuid_datetime_for_json
            if final_operation=='DELETE':
                object_body={}
            else:
                object_body=convert_uuid_datetime_for_json(model_instance)
            message = {
                "uuid": str(object_id),
                "operation": final_operation,
                "object_body": object_body,
                "object_type": model_class_name if model_class else None,
                "sync_id":status.id
            }

              # Default: Data House

            if model_class and issubclass(model_class, (Task, ChildBot, Proxy,Device)):
                try:
                    if model_class==Task:
                        server = model_instance.server
                    if model_class==ChildBot:
                        server=model_instance.logged_in_on_servers
                    if model_class==Device:
                        server=model_instance.connected_to_server
                    worker_url = f"{server.public_ip}crawl/api/sync/"
                    if worker_url not in target_payloads:
                        target_payloads[worker_url] = []
                    target_payloads[worker_url].append(message)
                except AttributeError:
                    print(f"Object {object_id} has no server assigned, syncing with datahouse.")
                except Exception as e:
                    print(f"Error getting worker URL: {e}. Syncing with datahouse.")

            target_payloads[data_house_url].append(message) # Always send to datahouse

    all_successful_uuids = {}
    if len(target_payloads)==0:
        return True

    for target_url, payloads in target_payloads.items():
        if len(payloads)==0:
            continue
        headers = {"Content-Type": "application/json"}
        try:
            response = requests.post(target_url, data=json.dumps({'data':payloads}), headers=headers)
            response.raise_for_status()
            data = response.json()

            if data.get("error"):
                print(f"{target_url} returned an error: {data['error']}")
                continue

            successful_uuids = data.get("successful_sync_ids", {})
            for object_type, uuids in successful_uuids.items():
                all_successful_uuids.setdefault(object_type, []).extend(uuids)

        except requests.exceptions.RequestException as e:
            print(f"Error sending sync payload to {target_url}: {e}")
            continue
    print(all_successful_uuids)
    for object_type, sync_id in all_successful_uuids.items():
        try:
            DataHouseSyncStatus.objects.filter(id__in=sync_id).delete()
            print(f"DataHouseSyncStatus records for {object_type} with UUIDs {uuids} deleted.")
        except Exception as e:
            print(f"Error deleting DataHouseSyncStatus records: {e}")

    print("Data house sync task completed.")
    return# ... (rest of the code)
@shared_task()
def communicate_tasks_with_worker():
    import json
    import requests as r
    from django.forms import model_to_dict
    unregistered_tasks=Task.objects.all().filter(registered=False)
    delete_tasks=Task.objects.all().filter(_delete=True)
    
    unregistered_task=unregistered_tasks.union(delete_tasks)
    print(unregistered_task)
    _={}
    for task in unregistered_task:
        if task.server:
   
            if task.server.public_ip in _.keys():
                pass
            else:
                _.update({task.server.public_ip:{'tasks':[],'resources':{'devices':[],'bots':[]}}})
        else:
            continue
        if task._delete:
            method='delete'
        else:
            method='create'
        active_dict=_[task.server.public_ip]
        _task=model_to_dict(task)
        if task.dependent_on:        
            _task.update({'dependent_on':str(task.dependent_on.uuid)})
        _task.update({'method':method,'ref_id':str(_task['ref_id'])})
        _task.update({'created_at':str(_task['created_at'])})
        active_dict['tasks'].append(_task)
        
      
        import sessionbot.handlers.bots as bot
        import sessionbot.handlers.device as device
        _bot=None
        if task.profile:
            _bot=bot.formatify_for_server(task.profile)   
            if _bot:   
                active_dict['resources']['bots'].append( {'type':'bot','data':_bot
                                   ,'method':'create'})  
            else:
                continue
        elif task.alloted_bots:
            for username in task.alloted_bots.split(','):
                _bot=bot.formatify_for_server(username)    
                if _bot:

                    active_dict['resources']['bots'].append( {'type':'bot','data':_bot
                                        ,'method':'create'}) 
                else:
                    continue
        if _bot:
            if _bot['device']:
                _device=device.formatify_for_worker(_bot['device'])

                active_dict['resources']['devices'].append( {'type':'device','data':_device,'method':'create'})
        
      
  
    import time
    
    for key, value in _.items():
        
        resources_url=key+'crawl/api/resources/'
        worker_tasks_url=key+'crawl/api/tasks/'
        resp=r.post(resources_url,data=json.dumps({'resources':value['resources']}))
        resp=r.post(worker_tasks_url,data=json.dumps(value['tasks']))
        print(value['tasks'])
        if resp.status_code==200:
            unregistered_tasks.update(registered=True)
            delete_tasks.delete()
            

        import datetime as dt
        print('sent request to worker at'+worker_tasks_url +str(dt.datetime.now()))
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
@shared_task()
def analyze_and_create_update_metrics_for_bots():
    from django.db.models import Q
    for bot in ChildBot.objects.all().filter(service='instagram'):
        scraped_so_far=0
        successful_api_requests=0
        block_api_requests=0
        failed_api_requests=0
        scraped_so_far=0
        print(bot.username)
        tasks=Task.objects.all().filter(profile=bot.username).filter(service=bot.service)
        scraping_tasks=tasks.filter(interact=False)
        automation_tasks=tasks.filter(interact=True)
        login_tasks=tasks.filter(Q(data_point='login')|Q(data_point='open_browser_profile'))
        from sessionbot.utils import DataHouseClient
        d=DataHouseClient()
        if len(scraping_tasks.filter(paused=False))>0:
            bot.is_scraper=True
        print(list(tasks.values_list('uuid',flat=True)))
        failed_login_logs_with_datetime=d.retrieve(object_type='log',filters={'task__uuid.in':list(tasks.values_list('uuid',flat=True)),'type.equal':'failed_login'},required_fields=['datetime','bot_username','type'])
        print(failed_login_logs_with_datetime)
        sucessful_login_logs_with_datetime=d.retrieve(object_type='log',filters={'task__uuid.in':list(tasks.values_list('uuid',flat=True)),'type.equal':'successful_login'},required_fields=['datetime','bot_username','type'])
        print(sucessful_login_logs_with_datetime)
        import pandas as pd
        df1=pd.DataFrame(data=failed_login_logs_with_datetime['data'])
        df2=pd.DataFrame(data=sucessful_login_logs_with_datetime['data'])
  
        if df1.empty and not df2.empty:
            bot.logged_in=True
            bot.save()
        elif df2.empty and not df1.empty:
            bot.logged_in=False
            bot.save()
        elif df1.empty and df2.empty:
            pass
        else:
            latest_fail = pd.to_datetime(df1['datetime'], errors='coerce').max()
            latest_success = pd.to_datetime(df2['datetime'], errors='coerce').max()
            if pd.isnull(latest_fail) and not(pd.isnull(latest_success)):
                bot.logged_in=True
                bot.save()
            elif pd.isnull(latest_success) and not (pd.isnull(latest_fail)):
                bot.logged_in=False
                bot.save()
            elif pd.isnull(latest_fail):
                bot.logged_in=True
            elif pd.isnull(latest_success):
                bot.logged_in=False
            elif latest_fail > latest_success:
                bot.logged_in=False
            else:
                bot.logged_in=True
            bot.save()
        scraped_so_far_by_bot_payload = {
        "object_type": "profile",  # Replace with your object type
        "filters": {"tasks__uuid.in":list(scraping_tasks.values_list('uuid',flat=True))}, # Correct sum syntax
       
         "count":True # Optional
}       
        scraped_so_far=d.retrieve(**scraped_so_far_by_bot_payload)
        if type(scraped_so_far)==dict:
            bot.scraped_so_far=scraped_so_far.get('count',0)
            bot.save()
        successful_api_requests= {
        "object_type": "requestlog",  # Replace with your object type
        "filters": {"task__uuid.in":list(scraping_tasks.values_list('uuid',flat=True)),"status_code.in":[200]}, # Correct sum syntax
       
         "count":True # Optional
}   
        successful_api_requests=d.retrieve(**successful_api_requests)
        if type(successful_api_requests)==dict:
            bot.successful_api_requests=successful_api_requests['count']
            bot.save()
        failed_api_requests= {
        "object_type": "requestlog",  # Replace with your object type
        "filters": {"task__uuid.in":list(scraping_tasks.values_list('uuid',flat=True)),"status_code.in":[400,500,401]}, # Correct sum syntax
       
         "count":True # Optional
}   
        failed_api_requests=d.retrieve(**failed_api_requests)
        if type(failed_api_requests)==dict:
            bot.failed_api_requests=failed_api_requests['count']
            bot.save()
        block_api_requests= {
        "object_type": "requestlog",  # Replace with your object type
        "filters": {"task__uuid.in":list(scraping_tasks.values_list('uuid',flat=True)),"data__status":"fail"}, # Correct sum syntax
        
         "count":True # Optional
}   
        block_api_requests=d.retrieve(**block_api_requests)
        if type(block_api_requests)==dict:
            if block_api_requests.get('count',0)>0:
                
                bot.is_challenged=True 
            else:
                bot.is_challenged=False
            bot.save()

    for scrapetask in ScrapeTask.objects.all():
        successful_api_requests=0
        failed_api_requests=0
        blocks_encountered=0
        scraped_so_far=0
        bot_status={}
        for bot in scrapetask.childbots.all():
         
            scraped_so_far+=bot.scraped_so_far
            failed_api_requests+=bot.failed_api_requests
            successful_api_requests+=bot.successful_api_requests
            bot_status.update({bot.username+'_is_challenged':bot.is_challenged})
      
        scrapetask.successful_request_count=successful_api_requests
        scrapetask.failed_request_count=failed_api_requests
        scrapetask.scraped_so_far=scraped_so_far
        scrapetask.requests_sent=successful_api_requests+failed_api_requests
        scrapetask.bot_status=bot_status
        scrapetask.save()
        pass



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


@shared_task
def process_scrape_task_alerts(scrape_task_uuid: str = None):
    """
    Celery task to:
    1. Fetch ScrapeTasks (either a specific one or all).
    2. Find related generic operational Tasks.
    3. Retrieve aggregated summaries from the Reporting House for these tasks.
    4. Consolidate all relevant data for the ScrapeTask.
    5. Format and send a comprehensive performance alert to Slack.

    Args:
        scrape_task_uuid (str, optional): The UUID of a specific ScrapeTask
                                          to process. If None, processes all ScrapeTasks.
    """
    logger.info(f"Starting scrape task alerts processing for UUID: {scrape_task_uuid or 'all'}.")

    query_set = ScrapeTask.objects.all()
    reportinghouse=Server.objects.all().filter(instance_type='reporting_and_analytics_server')
    if not reportinghouse:
        return False
    reportinghouse=reportinghouse[0]
    reportinghouse_url=reportinghouse.public_ip
    if scrape_task_uuid:
        try:
            # Validate UUID format
            uuid.UUID(scrape_task_uuid)
            query_set = query_set.filter(uuid=scrape_task_uuid)
        except ValueError:
            logger.error(f"Invalid UUID format provided: {scrape_task_uuid}. Aborting task.")
            return

    if not query_set.exists():
        logger.warning(f"No ScrapeTask found for UUID: {scrape_task_uuid or 'all'}. Exiting.")
        return

    for scrape_task in query_set:
        logger.info(f"Processing ScrapeTask: {scrape_task.name} ({scrape_task.uuid})")

        # Step 1 & 2: Get associated Central Tasks and their details
        central_tasks = Task.objects.filter(ref_id=scrape_task.uuid)
        if not central_tasks.exists():
            logger.warning(f"No individual tasks found for ScrapeTask: {scrape_task.name}. Skipping alert.")
            continue

        task_uuids_to_fetch = [str(t.uuid) for t in central_tasks]
        central_tasks_by_uuid = {str(t.uuid): t for t in central_tasks}

        # Step 3: Retrieve Reporting Summaries from Reporting App
        all_reports_data = {}
        for task_uuid in task_uuids_to_fetch:
            # Construct the URL using settings.REPORTING_API_BASE_URL
            report_url = f"{reportinghouse_url}reporting/task-summaries/{task_uuid}/"
            try:
                response = requests.get(report_url, timeout=10)
                response.raise_for_status()
                report_data = response.json()
                all_reports_data[task_uuid] = report_data
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching report for task {task_uuid} from Reporting App: {e}")
                continue # Skip this specific task's data if fetch fails

        if not all_reports_data:
            logger.warning(f"No successful reports fetched for ScrapeTask: {scrape_task.name}. Skipping alert.")
            continue

        # Step 4: Aggregate Data
        aggregated_by_data_input = defaultdict(lambda: {
            'total_posts_scraped': 0,
            'total_users_scraped': 0,
            'total_rows': 0,
            'total_runs_completed': 0,
            'total_saved_file_count': 0,
            'total_failed_download_count': 0,
        })
        individual_bot_metrics = defaultdict(lambda: {
            'status': 'N/A',
            'latest_report_end_datetime': datetime.datetime.fromtimestamp(0, tz=timezone.utc),
            'total_posts_scraped': 0,
            'total_users_scraped': 0,
            'total_rows': 0,
            'total_runs_completed': 0,
            'total_saved_file_count': 0,
            'total_failed_download_count': 0,
            'associated_task_uuids': []
        })

        overall_scrape_task_status = "Completed"
        critical_issues = []

        for task_uuid, report_summary in all_reports_data.items():
            central_task = central_tasks_by_uuid.get(task_uuid)
            if not central_task:
                continue # Should not happen if central_tasks_by_uuid was built correctly

            # --- Aggregate by (data_point, input) ---
            key = (central_task.data_point, central_task.input)

            # Handling aggregated_scraped_data
            if isinstance(report_summary.get('aggregated_scraped_data'), dict):
                for metric, value in report_summary['aggregated_scraped_data'].items():
                    if isinstance(value, (int, float)):
                        aggregated_by_data_input[key][metric] += value

            # Handling aggregated_data_enrichment
            if isinstance(report_summary.get('aggregated_data_enrichment'), dict):
                for metric, value in report_summary['aggregated_data_enrichment'].items():
                    if isinstance(value, (int, float)):
                        aggregated_by_data_input[key][metric] += value

            aggregated_by_data_input[key]['total_runs_completed'] += report_summary.get('total_runs_completed', 0)
            aggregated_by_data_input[key]['total_saved_file_count'] += report_summary.get('total_saved_file_count', 0)
            aggregated_by_data_input[key]['total_failed_download_count'] += report_summary.get('total_failed_download_count', 0)

            # --- Individual Bot Metrics ---
            from datetime import timezone
            username = central_task.profile
            if username:
                current_report_end_dt_str = report_summary.get('latest_report_end_datetime')
                current_report_end_dt = datetime.datetime.min.replace(tzinfo=timezone.utc) # Ensure timezone-aware comparison
                if current_report_end_dt_str:
                    try:
                        current_report_end_dt = datetime.datetime.fromisoformat(current_report_end_dt_str.replace('Z', '+00:00'))
                    except ValueError:
                        logger.warning(f"Could not parse datetime '{current_report_end_dt_str}' for task {task_uuid[:8]}.")

                bot_entry = individual_bot_metrics[username]

                # Determine bot status based on latest task
                if current_report_end_dt > bot_entry['latest_report_end_datetime']:
                    bot_entry['status'] = report_summary.get('latest_overall_bot_login_status', 'N/A')
                    bot_entry['latest_report_end_datetime'] = current_report_end_dt
                elif current_report_end_dt == bot_entry['latest_report_end_datetime']:
                    if report_summary.get('latest_overall_bot_login_status') == 'Logged Out':
                        bot_entry['status'] = 'Logged Out'
                
                # Sum metrics for the bot
                if isinstance(report_summary.get('aggregated_scraped_data'), dict):
                   for metric, value in report_summary['aggregated_scraped_data'].items():
                       if isinstance(value, (int, float)):
                           bot_entry[metric] = bot_entry.get(metric, 0) + value
                
                if isinstance(report_summary.get('aggregated_data_enrichment'), dict):
                   for metric, value in report_summary['aggregated_data_enrichment'].items():
                       if isinstance(value, (int, float)):
                           bot_entry[metric] = bot_entry.get(metric, 0) + value

                bot_entry['total_runs_completed'] += report_summary.get('total_runs_completed', 0)
                bot_entry['total_saved_file_count'] += report_summary.get('total_saved_file_count', 0)
                bot_entry['total_failed_download_count'] += report_summary.get('total_failed_download_count', 0)
                bot_entry['associated_task_uuids'].append(task_uuid)

            # --- Overall ScrapeTask Status & Critical Issues ---
            task_status = report_summary.get('latest_overall_task_status')
            if task_status == 'Failed':
                overall_scrape_task_status = 'Failed'
            elif task_status == 'Incomplete' and overall_scrape_task_status != 'Failed':
                overall_scrape_task_status = 'Incomplete'
            elif task_status == 'Running' and overall_scrape_task_status not in ['Failed', 'Incomplete']:
                overall_scrape_task_status = 'Running'

            if report_summary.get('latest_overall_bot_login_status') == 'Logged Out':
                critical_issues.append(f"Bot for task `{task_uuid[:8]}` (Service: {central_task.service or 'N/A'}) is LOGGED OUT.")
            if 'exception(s) detected' in str(report_summary.get('all_exceptions')).lower():
                critical_issues.append(f"Exception detected in task `{task_uuid[:8]}` (Service: {central_task.service or 'N/A'}).")
            if 'billing issues' in str(report_summary.get('latest_billing_issue_resolution_status')).lower() and \
               'n/a' not in str(report_summary.get('latest_billing_issue_resolution_status')).lower():
                critical_issues.append(f"Billing issue for task `{task_uuid[:8]}` (Service: {central_task.service or 'N/A'}).")
            if report_summary.get('total_failed_download_count', 0) > 0:
                critical_issues.append(f"Failed downloads in task `{task_uuid[:8]}` (Service: {central_task.service or 'N/A'}).")
            
        # Step 5: Generate Slack Message
        slack_blocks = _build_slack_message_blocks(
            scrape_task=scrape_task,
            overall_scrape_task_status=overall_scrape_task_status,
            aggregated_by_data_input=aggregated_by_data_input,
            individual_bot_metrics=individual_bot_metrics,
            critical_issues=critical_issues
        )

        # Send the message
        try:
            # Using a hardcoded channel as in your original snippet. Consider making this configurable.
            send_slack_message(slack_blocks, channel='Client') 
            logger.info(f"Successfully sent Slack alert for ScrapeTask: {scrape_task.name}")
        except Exception as e:
            logger.error(f"Failed to send Slack message for ScrapeTask {scrape_task.name}: {e}")
            logger.error("Ensure Slack integration is correctly configured and bot has permissions.")
            
    logger.info('Scrape task alerts processing finished.')


def _build_slack_message_blocks(scrape_task, overall_scrape_task_status,
                                 aggregated_by_data_input, individual_bot_metrics,
                                 critical_issues):
    """
    Helper function to construct the Slack message blocks.
    This is extracted as a standalone function for use by the Celery task.
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

    # Critical Issues Section
    if critical_issues:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "🚨 *Critical Issues Detected:*"
            }
        })
        for issue in sorted(list(set(critical_issues))): # Use set to avoid duplicate issue messages, then sort
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"• {issue}"
                }
            })
        blocks.append({"type": "divider"})

    # Aggregated by Data Point and Input
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "*🔬 Aggregated Data by Target:*"
        }
    })
    if aggregated_by_data_input:
        # Sort by data_point and input for consistent output
        sorted_aggregated_data = sorted(aggregated_by_data_input.items(), key=lambda item: (item[0][0], item[0][1]))
        for (data_point, input_value), metrics in sorted_aggregated_data:
            metrics_text = []
            # Sort metrics alphabetically for consistent display
            for metric_key in sorted(metrics.keys()):
                value = metrics[metric_key]
                if value:
                    display_metric = metric_key.replace('_', ' ').title()
                    if display_metric == 'Total Posts Scraped':
                        display_metric = 'Posts Scraped'
                    elif display_metric == 'Total Users Scraped':
                        display_metric = 'Users Scraped'
                    elif display_metric == 'Total Rows':
                        display_metric = 'Rows Scraped/Enriched'
                    elif display_metric == 'Total Runs Completed':
                        display_metric = 'Runs Completed'
                    elif display_metric == 'Total Saved File Count':
                        display_metric = 'Files Saved'
                    elif display_metric == 'Total Failed Download Count':
                        display_metric = 'Failed Downloads'

                    metrics_text.append(f"{display_metric}: *{value}*")

            if metrics_text:
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{data_point.replace('_', ' ').title()} - Input: `{input_value}`*\n" + ", ".join(metrics_text)
                    }
                })
        blocks.append({"type": "divider"})
    else:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "No aggregated data metrics available for this ScrapeTask."
            }
        })
        blocks.append({"type": "divider"})


    # Individual Bot Statuses
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "*🤖 Individual Bot Statuses:*"
        }
    })
    if individual_bot_metrics:
        # Sort by username for consistent output
        sorted_bot_metrics = sorted(individual_bot_metrics.items(), key=lambda item: item[0])
        for username, bot_info in sorted_bot_metrics:
            bot_status_emoji = "✅" if bot_info['status'] == "Logged In" else "❌"
            
            # Filter and sort metrics for display
            display_metrics = []
            for metric_key in sorted(bot_info.keys()):
                if metric_key not in ['status', 'latest_report_end_datetime', 'associated_task_uuids']:
                    value = bot_info[metric_key]
                    if value:
                        display_metric = metric_key.replace('_', ' ').title()
                        if display_metric == 'Total Posts Scraped':
                            display_metric = 'Posts Scraped'
                        elif display_metric == 'Total Users Scraped':
                            display_metric = 'Users Scraped'
                        elif display_metric == 'Total Rows':
                            display_metric = 'Rows Scraped/Enriched'
                        elif display_metric == 'Total Runs Completed':
                            display_metric = 'Runs Completed'
                        elif display_metric == 'Total Saved File Count':
                            display_metric = 'Files Saved'
                        elif display_metric == 'Total Failed Download Count':
                            display_metric = 'Failed Downloads'
                        display_metrics.append(f"{display_metric}: *{value}*")
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"• *Bot: {username}* Status: {bot_status_emoji} {bot_info['status']}\n  " + ", ".join(display_metrics)
                }
            })
        blocks.append({"type": "divider"})
    else:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "No individual bot metrics available for this ScrapeTask."
            }
        })
        blocks.append({"type": "divider"})

    # Footer
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": f"Generated for ScrapeTask ID: `{scrape_task.uuid}` at {datetime.datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
            }
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