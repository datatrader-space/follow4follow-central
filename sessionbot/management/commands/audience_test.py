# central/management/commands/test_audience_alert.py
import requests
import uuid
from datetime import datetime, timezone
from collections import defaultdict

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db.models import Q

# Adjust these imports to your actual app structure
from sessionbot.models import Audience, ScrapeTask, Task
# Assuming send_structured_slack_message is in central/utils.py or sessionbot/slack_utils.py
from sessionbot.slack_utils import send_structured_slack_message as send_slack_message

# Configuration for the Reporting App API
# Make sure REPORTING_API_BASE_URL is defined in your Central app's settings.py
REPORTING_API_BASE_URL = getattr(settings, 'REPORTING_API_BASE_URL', 'http://localhost:81/reporting/')

class Command(BaseCommand):
    help = 'Generates and sends client alerts for all Audiences, aggregating data from associated tasks and the Reporting House.'

    def handle(self, *args, **options):
        # 1. Flow: Make Django ORM query for all Audiences
        all_audiences = Audience.objects.all()

        if not all_audiences.exists():
            self.stdout.write(self.style.WARNING("No Audience objects found in the database. Exiting."))
            return

        self.stdout.write(self.style.HTTP_INFO("\n--- Starting Audience Alert Generation for ALL Audiences ---"))

        # Pre-fetch scrape tasks and their associated tasks to build a quick lookup
        # This helps in inferring 'scrape' task type
        scrape_task_to_audience_map = defaultdict(list)
        all_scrape_task_uuids = set()

        for audience in all_audiences:
            for st in audience.scrape_tasks.all():
                scrape_task_to_audience_map[str(st.uuid)].append(str(audience.uuid))
                all_scrape_task_uuids.add(str(st.uuid))

        for audience in all_audiences:
            self.stdout.write(self.style.SUCCESS(f"\nProcessing Audience: {audience.name} ({audience.uuid})"))

            # Get all relevant Central Tasks (linked to this Audience directly or via its ScrapeTasks)
            all_relevant_task_uuids = set()
            central_tasks_map = {} # Map UUID (str) to Task object

            # Tasks directly linked to the Audience (enrichment, cleaning tasks)
            # These have ref_id = Audience.uuid
            direct_audience_tasks_query = Task.objects.filter(ref_id=audience.uuid)
            for task in direct_audience_tasks_query:
                all_relevant_task_uuids.add(str(task.uuid))
                central_tasks_map[str(task.uuid)] = task
            
            # Tasks linked via ScrapeTasks associated with this Audience
            # These have ref_id = ScrapeTask.uuid, where ScrapeTask is associated with this Audience
            scrape_tasks_for_this_audience = audience.scrape_tasks.all()
            for st in scrape_tasks_for_this_audience:
                tasks_for_scrape_task = Task.objects.filter(ref_id=st.uuid)
                for task in tasks_for_scrape_task:
                    all_relevant_task_uuids.add(str(task.uuid))
                    central_tasks_map[str(task.uuid)] = task
            
            if not all_relevant_task_uuids:
                self.stdout.write(self.style.WARNING(f"  No associated tasks found for Audience: {audience.name}. Skipping alert."))
                continue

            # Retrieve Reporting Summaries from Reporting App for all relevant tasks
            all_reports_data = {}
            for task_uuid in all_relevant_task_uuids:
                report_url = f"{REPORTING_API_BASE_URL}task-summaries/{task_uuid}/"
                try:
                    self.stdout.write(f"    Fetching report for task: {task_uuid} from {report_url}")
                    response = requests.get(report_url, timeout=15)
                    response.raise_for_status()
                    report_data = response.json()
                    all_reports_data[task_uuid] = report_data
                except requests.exceptions.RequestException as e:
                    self.stdout.write(self.style.ERROR(f"    Error fetching report for task {task_uuid[:8]}... from Reporting App: {e}"))
                    continue

            if not all_reports_data:
                self.stdout.write(self.style.WARNING(f"  No successful reports fetched for Audience: {audience.name}. Skipping alert."))
                continue

            # Aggregate Data for the Audience
            aggregated_audience_metrics = {
                'overall_status': 'Completed',
                'scraping': {'total_posts_scraped': 0, 'total_users_scraped': 0},
                'enrichment': {
                    'emails_enriched': 0, 
                    'phone_numbers_enriched': 0, 
                    'profiles_analyzed': 0, # New
                    'geo_enriched_records': 0, # New
                    'total_rows_processed': 0 # From Reporting House's 'total_rows_processed'
                }, 
                'cleaning': {'duplicates_removed': 0, 'invalid_records_fixed': 0, 'total_rows_processed': 0},
                'operational': {
                    'total_requests_sent': 0,
                    'total_files_downloaded': 0,
                    'total_storage_house_requests': 0,
                    'total_data_uploaded_mb': 0.0,
                    'total_data_downloaded_mb': 0.0,
                    'total_runs_completed': 0,
                    'total_saved_file_count': 0,
                    'total_failed_download_count': 0,
                }
            }
            individual_bot_metrics = defaultdict(lambda: {
                'status': 'N/A',
                'latest_report_end_datetime': datetime.fromtimestamp(0, tz=timezone.utc),
                'metrics': defaultdict(int), # To hold various metrics like posts_scraped, emails_enriched etc.
                'associated_task_uuids': []
            })
            critical_issues = []

            for task_uuid, report_summary in all_reports_data.items():
                central_task = central_tasks_map.get(task_uuid)
                if not central_task:
                    continue

                # Infer task type based on ref_id and service field
                inferred_task_type = 'unknown'
                if str(central_task.ref_id) in all_scrape_task_uuids:
                    inferred_task_type = 'scrape'
                elif central_task.service == 'data_enricher':
                    inferred_task_type = 'enrichment'
                elif central_task.service == 'cleaner':
                    inferred_task_type = 'cleaning'

                # --- Aggregate overall Audience status ---
                task_overall_status = report_summary.get('overall_task_status')
                if task_overall_status == 'Failed':
                    aggregated_audience_metrics['overall_status'] = 'Failed'
                elif task_overall_status == 'Incomplete' and aggregated_audience_metrics['overall_status'] not in ['Failed', 'Running']:
                    aggregated_audience_metrics['overall_status'] = 'Incomplete'
                elif task_overall_status == 'Running' and aggregated_audience_metrics['overall_status'] not in ['Failed', 'Incomplete']:
                    aggregated_audience_metrics['overall_status'] = 'Running'

                # --- Aggregate metrics by inferred task type for Audience summary ---
                if inferred_task_type == 'scrape':
                    scraped_data = report_summary.get('aggregated_scraped_data', {})
                    aggregated_audience_metrics['scraping']['total_posts_scraped'] += scraped_data.get('total_posts_scraped', 0)
                    aggregated_audience_metrics['scraping']['total_users_scraped'] += scraped_data.get('total_users_scraped', 0)
                elif inferred_task_type == 'enrichment':
                    enriched_data = report_summary.get('aggregated_data_enrichment', {})
                    aggregated_audience_metrics['enrichment']['emails_enriched'] += enriched_data.get('emails_enriched', 0)
                    aggregated_audience_metrics['enrichment']['phone_numbers_enriched'] += enriched_data.get('phone_numbers_enriched', 0)
                    aggregated_audience_metrics['enrichment']['profiles_analyzed'] += enriched_data.get('profiles_analyzed', 0) # New
                    aggregated_audience_metrics['enrichment']['geo_enriched_records'] += enriched_data.get('geo_enriched_records', 0) # New
                    # For total_rows_processed, it's generally a top-level field for enrichment/cleaning
                    aggregated_audience_metrics['enrichment']['total_rows_processed'] += report_summary.get('total_rows_processed', 0)
                elif inferred_task_type == 'cleaning':
                    cleaning_data = report_summary.get('aggregated_data_cleaning', {})
                    aggregated_audience_metrics['cleaning']['duplicates_removed'] += cleaning_data.get('duplicates_removed', 0)
                    aggregated_audience_metrics['cleaning']['invalid_records_fixed'] += cleaning_data.get('invalid_records_fixed', 0)
                    aggregated_audience_metrics['cleaning']['total_rows_processed'] += report_summary.get('total_rows_processed', 0)

                # --- Aggregate operational metrics for Audience summary ---
                aggregated_audience_metrics['operational']['total_requests_sent'] += report_summary.get('total_requests_sent', 0)
                aggregated_audience_metrics['operational']['total_files_downloaded'] += report_summary.get('total_files_downloaded', 0)
                aggregated_audience_metrics['operational']['total_storage_house_requests'] += report_summary.get('total_storage_house_requests', 0)
                aggregated_audience_metrics['operational']['total_data_uploaded_mb'] += report_summary.get('total_data_uploaded_mb', 0.0)
                aggregated_audience_metrics['operational']['total_data_downloaded_mb'] += report_summary.get('total_data_downloaded_mb', 0.0)
                aggregated_audience_metrics['operational']['total_runs_completed'] += report_summary.get('total_runs_completed', 0)
                aggregated_audience_metrics['operational']['total_saved_file_count'] += report_summary.get('total_saved_file_count', 0)
                aggregated_audience_metrics['operational']['total_failed_download_count'] += report_summary.get('total_failed_download_count', 0)

                # --- Individual Bot Metrics ---
                username = central_task.profile
                if username:
                    current_report_end_dt_str = report_summary.get('report_end_datetime')
                    current_report_end_dt = datetime.min.replace(tzinfo=timezone.utc)
                    if current_report_end_dt_str:
                        try:
                            current_report_end_dt = datetime.fromisoformat(current_report_end_dt_str.replace('Z', '+00:00'))
                        except ValueError:
                            self.stdout.write(self.style.WARNING(f"    Could not parse datetime '{current_report_end_dt_str}' for task {task_uuid[:8]}."))

                    bot_entry = individual_bot_metrics[username]

                    if current_report_end_dt > bot_entry['latest_report_end_datetime']:
                        bot_entry['status'] = report_summary.get('bot_login_status', 'N/A')
                        bot_entry['latest_report_end_datetime'] = current_report_end_dt
                    elif current_report_end_dt == bot_entry['latest_report_end_datetime']:
                        if report_summary.get('bot_login_status') == 'Logged Out':
                            bot_entry['status'] = 'Logged Out'
                    
                    # Sum all relevant metrics into the generic 'metrics' sub-dictionary
                    if inferred_task_type == 'scrape':
                        for metric, value in report_summary.get('aggregated_scraped_data', {}).items():
                            if isinstance(value, (int, float)):
                                bot_entry['metrics'][metric] += value
                    elif inferred_task_type == 'enrichment':
                        for metric, value in report_summary.get('aggregated_data_enrichment', {}).items():
                            if isinstance(value, (int, float)):
                                bot_entry['metrics'][metric] += value
                        bot_entry['metrics']['total_rows_processed'] += report_summary.get('total_rows_processed', 0)
                    elif inferred_task_type == 'cleaning':
                        for metric, value in report_summary.get('aggregated_data_cleaning', {}).items():
                            if isinstance(value, (int, float)):
                                bot_entry['metrics'][metric] += value
                        bot_entry['metrics']['total_rows_processed'] += report_summary.get('total_rows_processed', 0)
                    
                    # Add common operational metrics to bot's metrics as well
                    bot_entry['metrics']['total_runs_completed'] += report_summary.get('total_runs_completed', 0)
                    bot_entry['metrics']['total_saved_file_count'] += report_summary.get('total_saved_file_count', 0)
                    bot_entry['metrics']['total_failed_download_count'] += report_summary.get('total_failed_download_count', 0)
                    
                    bot_entry['associated_task_uuids'].append(task_uuid)

                # --- Critical Issues detection ---
                if report_summary.get('bot_login_status') == 'Logged Out':
                    critical_issues.append(f"Bot for task `{task_uuid[:8]}`... (Service: {central_task.service or 'N/A'}, Type: {inferred_task_type}) is LOGGED OUT.")
                if 'exception(s) detected' in str(report_summary.get('all_exceptions')).lower():
                    critical_issues.append(f"Exception detected in task `{task_uuid[:8]}`... (Service: {central_task.service or 'N/A'}, Type: {inferred_task_type}).")
                if 'billing issues' in str(report_summary.get('billing_issue_resolution_status')).lower() and \
                   'N/A' not in str(report_summary.get('billing_issue_resolution_status')):
                    critical_issues.append(f"Billing issue for task `{task_uuid[:8]}`... (Service: {central_task.service or 'N/A'}, Type: {inferred_task_type}).")
                if report_summary.get('total_failed_download_count', 0) > 0:
                    critical_issues.append(f"Failed downloads in task `{task_uuid[:8]}`... (Service: {central_task.service or 'N/A'}, Type: {inferred_task_type}).")
            
            # Generate Slack Message
            slack_blocks = self._build_slack_message_blocks(
                audience=audience,
                aggregated_audience_metrics=aggregated_audience_metrics,
                individual_bot_metrics=individual_bot_metrics,
                critical_issues=critical_issues
            )

            # Send the message
            try:
                slack_channel = getattr(settings, 'SLACK_CLIENT_CHANNEL', '#general')
                send_slack_message(slack_blocks, channel='Client')
                self.stdout.write(self.style.SUCCESS(f"  Successfully sent Slack alert for Audience: {audience.name} to channel {slack_channel}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  Failed to send Slack message for Audience {audience.name}: {e}"))
                self.stdout.write(self.style.ERROR("  Ensure SLACK_CLIENT_CHANNEL is correctly configured in settings.py and the bot has permissions."))
                
        self.stdout.write(self.style.SUCCESS('\nAudience alerts command finished for all audiences.'))

    def _build_slack_message_blocks(self, audience, aggregated_audience_metrics,
                                     individual_bot_metrics, critical_issues):
        """
        Helper method to construct the Slack message blocks for an Audience report.
        """
        blocks = []

        # Header Section
        blocks.append({
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"📊 Audience Performance Report: {audience.name}",
                "emoji": True
            }
        })
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Audience ID: `{audience.uuid}` | Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
                }
            ]
        })
        blocks.append({"type": "divider"})

        # Overall Status
        status_emoji = "✅" if aggregated_audience_metrics['overall_status'] == "Completed" else \
                       "🟡" if aggregated_audience_metrics['overall_status'] == "Running" else \
                       "⚠️" if aggregated_audience_metrics['overall_status'] == "Incomplete" else \
                       "❌"
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Overall Audience Status:* {status_emoji} {aggregated_audience_metrics['overall_status']}"
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
            for issue in sorted(list(set(critical_issues))): 
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"• {issue}"
                    }
                })
            blocks.append({"type": "divider"})

        # --- Aggregated Metrics Sections ---
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": "*📈 Aggregated Metrics Summary*:"}})

        # Scraping Metrics
        if aggregated_audience_metrics['scraping']['total_posts_scraped'] > 0 or \
           aggregated_audience_metrics['scraping']['total_users_scraped'] > 0:
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": "*• Scraping Metrics*:"},
                "fields": [
                    {"type": "mrkdwn", "text": f"Posts Scraped: *{aggregated_audience_metrics['scraping']['total_posts_scraped']:,}*"},
                    {"type": "mrkdwn", "text": f"Users Scraped: *{aggregated_audience_metrics['scraping']['total_users_scraped']:,}*"},
                ]
            })

        # Enrichment Metrics
        # Only show this section if any enrichment metrics are present
        if any(v > 0 for k, v in aggregated_audience_metrics['enrichment'].items()):
            enrichment_fields = []
            if aggregated_audience_metrics['enrichment']['profiles_analyzed'] > 0:
                enrichment_fields.append({"type": "mrkdwn", "text": f"Profiles Analyzed: *{aggregated_audience_metrics['enrichment']['profiles_analyzed']:,}*"})
            if aggregated_audience_metrics['enrichment']['emails_enriched'] > 0:
                enrichment_fields.append({"type": "mrkdwn", "text": f"Emails Enriched: *{aggregated_audience_metrics['enrichment']['emails_enriched']:,}*"})
            if aggregated_audience_metrics['enrichment']['phone_numbers_enriched'] > 0:
                enrichment_fields.append({"type": "mrkdwn", "text": f"Phones Enriched: *{aggregated_audience_metrics['enrichment']['phone_numbers_enriched']:,}*"})
            if aggregated_audience_metrics['enrichment']['geo_enriched_records'] > 0:
                # Calculate Geo Enrichment Coverage Percentage if total_rows_processed is available
                total_processed_for_geo = aggregated_audience_metrics['enrichment']['total_rows_processed']
                geo_coverage_percent = 0.0
                if total_processed_for_geo > 0:
                    geo_coverage_percent = (aggregated_audience_metrics['enrichment']['geo_enriched_records'] / total_processed_for_geo) * 100
                enrichment_fields.append({"type": "mrkdwn", "text": f"Geo-enriched Records: *{aggregated_audience_metrics['enrichment']['geo_enriched_records']:,}*"})
                enrichment_fields.append({"type": "mrkdwn", "text": f"Geo Enrichment Coverage: *{geo_coverage_percent:.2f}%*"})
            if aggregated_audience_metrics['enrichment']['total_rows_processed'] > 0:
                enrichment_fields.append({"type": "mrkdwn", "text": f"Total Rows Processed (Enrichment): *{aggregated_audience_metrics['enrichment']['total_rows_processed']:,}*"})

            if enrichment_fields: # Only add the block if there are fields to display
                blocks.append({
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "*• Enrichment Metrics*:"},
                    "fields": enrichment_fields
                })

        # Cleaning Metrics
        if aggregated_audience_metrics['cleaning']['duplicates_removed'] > 0 or \
           aggregated_audience_metrics['cleaning']['invalid_records_fixed'] > 0 or \
           aggregated_audience_metrics['cleaning']['total_rows_processed'] > 0:
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": "*• Cleaning Metrics*:"},
                "fields": [
                    {"type": "mrkdwn", "text": f"Duplicates Removed: *{aggregated_audience_metrics['cleaning']['duplicates_removed']:,}*"},
                    {"type": "mrkdwn", "text": f"Invalid Records Fixed: *{aggregated_audience_metrics['cleaning']['invalid_records_fixed']:,}*"},
                    {"type": "mrkdwn", "text": f"Rows Processed (Cleaning): *{aggregated_audience_metrics['cleaning']['total_rows_processed']:,}*"},
                ]
            })

        # Operational/Infrastructure Metrics
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*⚙️ Operational Metrics*:"},
            "fields": [
                {"type": "mrkdwn", "text": f"Requests Sent: *{aggregated_audience_metrics['operational']['total_requests_sent']:,}*"},
                {"type": "mrkdwn", "text": f"Files Downloaded: *{aggregated_audience_metrics['operational']['total_files_downloaded']:,}*"},
                {"type": "mrkdwn", "text": f"Storage House Requests: *{aggregated_audience_metrics['operational']['total_storage_house_requests']:,}*"},
                {"type": "mrkdwn", "text": f"Data Uploaded: *{aggregated_audience_metrics['operational']['total_data_uploaded_mb']:.2f} MB*"},
                {"type": "mrkdwn", "text": f"Data Downloaded: *{aggregated_audience_metrics['operational']['total_data_downloaded_mb']:.2f} MB*"},
                {"type": "mrkdwn", "text": f"Runs Completed: *{aggregated_audience_metrics['operational']['total_runs_completed']:,}*"},
                {"type": "mrkdwn", "text": f"Files Saved: *{aggregated_audience_metrics['operational']['total_saved_file_count']:,}*"},
                {"type": "mrkdwn", "text": f"Failed Downloads: *{aggregated_audience_metrics['operational']['total_failed_download_count']:,}*"},
            ]
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
            sorted_bot_metrics = sorted(individual_bot_metrics.items(), key=lambda item: item[0])
            for username, bot_info in sorted_bot_metrics:
                bot_status_emoji = "✅" if bot_info['status'] == "Logged In" else "❌"
                
                display_metrics = []
                # Iterate through the 'metrics' sub-dictionary
                for metric_key in sorted(bot_info['metrics'].keys()):
                    value = bot_info['metrics'][metric_key]
                    if value: 
                        display_metric = metric_key.replace('_', ' ').title()
                        # Specific display names for metrics
                        if display_metric == 'Total Posts Scraped':
                            display_metric = 'Posts Scraped'
                        elif display_metric == 'Total Users Scraped':
                            display_metric = 'Users Scraped'
                        elif display_metric == 'Total Rows Processed':
                            display_metric = 'Rows Processed'
                        elif display_metric == 'Emails Enriched':
                            display_metric = 'Emails Enriched'
                        elif display_metric == 'Phone Numbers Enriched':
                            display_metric = 'Phones Enriched'
                        elif display_metric == 'Profiles Analyzed': # New
                            display_metric = 'Profiles Analyzed'
                        elif display_metric == 'Geo Enriched Records': # New
                            display_metric = 'Geo-enriched Records'
                        elif display_metric == 'Duplicates Removed':
                            display_metric = 'Duplicates Removed'
                        elif display_metric == 'Invalid Records Fixed':
                            display_metric = 'Invalid Records Fixed'
                        elif display_metric == 'Total Runs Completed':
                            display_metric = 'Runs Completed'
                        elif display_metric == 'Total Saved File Count':
                            display_metric = 'Files Saved'
                        elif display_metric == 'Total Failed Download Count':
                            display_metric = 'Failed Downloads'

                        display_metrics.append(f"{display_metric}: *{value}*")
                
                tasks_info = ", ".join([f"`{t[:4]}`" for t in bot_info['associated_task_uuids']])
                tasks_string = f" (Tasks: {tasks_info})" if tasks_info else ""

                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"• *Bot: {username}* Status: {bot_status_emoji} {bot_info['status']}{tasks_string}\n  " + ", ".join(display_metrics)
                    }
                })
            blocks.append({"type": "divider"})
        else:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "No individual bot metrics available for this Audience."
                }
            })
            blocks.append({"type": "divider"})

        # Footer
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Generated for Audience ID: `{audience.uuid}` at {datetime.now().strftime('%Y-%m-%d %H:%M:%S %Z')}"
                }
            ]
        })

        return blocks