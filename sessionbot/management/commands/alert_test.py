# central/management/commands/send_scrape_task_alerts.py

import requests
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from collections import defaultdict
from datetime import datetime
import uuid
from datetime import datetime, timezone
# Assuming these models are in your central/models.py
from sessionbot.models import ScrapeTask, Task
# Assuming send_slack_message is in central/utils.py
from sessionbot.slack_utils import send_structured_slack_message as send_slack_message

# Configuration for the Reporting App API
# Make sure REPORTING_API_BASE_URL is defined in your Central app's settings.py
REPORTING_API_BASE_URL = getattr(settings, 'REPORTING_API_BASE_URL', 'http://192.168.1.30:81//api/')

class Command(BaseCommand):
    help = 'Generates and sends client alerts for ScrapeTasks, aggregating data by (data_point, input) and providing individual bot statuses.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--scrape_task_uuid',
            type=str,
            help='Optional: Specify a ScrapeTask UUID to process only that specific task.',
            nargs='?', # Makes the argument optional
        )

    def handle(self, *args, **options):
        scrape_task_uuid = options['scrape_task_uuid']

        query_set = ScrapeTask.objects.all()
        if scrape_task_uuid:
            try:
                # Validate UUID format
                uuid.UUID(scrape_task_uuid)
                query_set = query_set.filter(uuid=scrape_task_uuid)
            except ValueError:
                raise CommandError(f"Invalid UUID format provided: {scrape_task_uuid}")

        if not query_set.exists():
            self.stdout.write(self.style.WARNING(f"No ScrapeTask found for UUID: {scrape_task_uuid or 'all'}. Exiting."))
            return

        for scrape_task in query_set:
            self.stdout.write(self.style.SUCCESS(f"Processing ScrapeTask: {scrape_task.name} ({scrape_task.uuid})"))

            # Step 1 & 2: Get associated Central Tasks and their details
            print(scrape_task)
            central_tasks = Task.objects.filter(ref_id=scrape_task.uuid)
            if not central_tasks.exists():
                self.stdout.write(self.style.WARNING(f"No individual tasks found for ScrapeTask: {scrape_task.name}. Skipping alert."))
                continue

            task_uuids_to_fetch = [str(t.uuid) for t in central_tasks]
            central_tasks_by_uuid = {str(t.uuid): t for t in central_tasks}

            # Step 3: Retrieve Reporting Summaries from Reporting App
            all_reports_data = {}
            for task_uuid in task_uuids_to_fetch:
                report_url = f"http://192.168.1.30:81/task-summaries/{task_uuid}/"
                try:
                    response = requests.get(report_url, timeout=10) # Add timeout
                    response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
                    report_data = response.json()
                    all_reports_data[task_uuid] = report_data
                except requests.exceptions.RequestException as e:
                    self.stdout.write(self.style.ERROR(f"Error fetching report for task {task_uuid} from Reporting App: {e}"))
                    continue # Skip this specific task's data if fetch fails

            if not all_reports_data:
                self.stdout.write(self.style.WARNING(f"No successful reports fetched for ScrapeTask: {scrape_task.name}. Skipping alert."))
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
                'latest_report_end_datetime': datetime.fromtimestamp(0, tz=timezone.utc),
              
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
                    continue # Should not happen

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
                username = central_task.profile
                if username:
                    current_report_end_dt_str = report_summary.get('latest_report_end_datetime')
                    current_report_end_dt = datetime.min
                    if current_report_end_dt_str:
                        try:
                            current_report_end_dt = datetime.fromisoformat(current_report_end_dt_str.replace('Z', '+00:00'))
                        except ValueError:
                            self.stdout.write(self.style.WARNING(f"Could not parse datetime '{current_report_end_dt_str}' for task {task_uuid[:8]}."))

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
                    critical_issues.append(f"Bot for task {central_task.uuid} ({task_uuid[:8]}...) is LOGGED OUT.")
                if 'exception(s) detected' in str(report_summary.get('all_exceptions')):
                     critical_issues.append(f"Exception detected in task {central_task.uuid} ({task_uuid[:8]}...).")
                if 'billing issues' in str(report_summary.get('latest_billing_issue_resolution_status')).lower() and \
                    'N/A' not in str(report_summary.get('latest_billing_issue_resolution_status')):
                    critical_issues.append(f"Billing issue for task {central_task.uuid} ({task_uuid[:8]}...).")
                if report_summary.get('total_failed_download_count', 0) > 0:
                    critical_issues.append(f"Failed downloads in task {central_task.uuid} ({task_uuid[:8]}...).")
            
            # Step 5: Generate Slack Message
            print(overall_scrape_task_status)
            print(aggregated_by_data_input)
            print(individual_bot_metrics)
            slack_blocks = self._build_slack_message_blocks(
                scrape_task=scrape_task,
                overall_scrape_task_status=overall_scrape_task_status,
                aggregated_by_data_input=aggregated_by_data_input,
                individual_bot_metrics=individual_bot_metrics,
                critical_issues=critical_issues
            )

            # Send the message
            try:
                send_slack_message(slack_blocks, channel='Client')
                self.stdout.write(self.style.SUCCESS(f"Successfully sent Slack alert for ScrapeTask: {scrape_task.name}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to send Slack message for ScrapeTask {scrape_task.name}: {e}"))
                
        self.stdout.write(self.style.SUCCESS('Scrape task alerts command finished.'))

    def _build_slack_message_blocks(self, scrape_task, overall_scrape_task_status,
                                   aggregated_by_data_input, individual_bot_metrics,
                                   critical_issues):
        """
        Helper method to construct the Slack message blocks.
        Moved inside the Command class for self-containment.
        """
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
                bot_metrics_text = []
                
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
                            display_metrics.append(f"{display_metric}: *{value}*")
                
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"• *Bot: {username}* Status: {bot_status_emoji} {bot_info['status']}\n  " + ", ".join(display_metrics)
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
                    "text": f"Generated for ScrapeTask ID: `{scrape_task.uuid}` at {datetime.now().strftime('%Y-%m-%d %H:%M:%S %Z')}"
                }
            ]
        })

        return blocks