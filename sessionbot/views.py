from django.http import HttpResponse, JsonResponse, HttpRequest
from django.views.decorators.csrf import csrf_exempt
from django.db import IntegrityError

from sessionbot.resource_utils import create_resources_from_google_sheets
from .models import BulkCampaign, ChildBot, Device, Server, Proxy, Task, Todo
import json
import requests
import logging

@csrf_exempt
def createResource(request: HttpRequest) -> JsonResponse:
    print('yes')
    if request.method == 'POST':
        try:
            payload = json.loads(request.body.decode("utf-8"))
            print("Payload received:", payload)
            
            r = create_resources_from_google_sheets(**payload)
            print("Response from create_resources_from_google_sheets:", r)
            
            response = {'status': 'success', 'data': r}
        except json.JSONDecodeError:
            response = {'status': 'error', 'message': 'Invalid JSON payload'}
        except Exception as e:
            response = {'status': 'error', 'message': str(e)}
    else:
        response = {'status': 'bad_request_type'}
    
    return JsonResponse(response)

@csrf_exempt
def createDeviceResource(request: HttpRequest) -> JsonResponse:
    response = {} 
    
    if request.method == 'POST':
        try:
            payload = json.loads(request.body.decode("utf-8"))
            name = payload.get('name')
            serial_number = payload.get('serial_number')
            info = payload.get('info')
            connected_to_server_id = payload.get('connected_to_server')

            if Device.objects.filter(name=name).exists():
                return JsonResponse({'status': 'error', 'message': 'Device with this name already exists.'}, status=400)

            device = Device.objects.create(
                name=name,
                serial_number=serial_number,
                info=info,
                connected_to_server_id=connected_to_server_id
            )

            crawl_payload = {
                'name': device.name,
                'serial_number': device.serial_number,
                'info': device.info,
            }

            try:
                connected_server = Server.objects.get(id=connected_to_server_id)
                crawl_url = connected_server.public_ip + 'crawl/devices/'
            except Server.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Connected server does not exist.'}, status=404)

            crawl_response = requests.post(crawl_url, json=crawl_payload)

            if crawl_response.status_code != 200:
                print(f"Error sending data to crawl URL: {crawl_response.text}")

            response_data = {
                'name': device.name,
                'serial_number': device.serial_number,
                'info': device.info
            }
            response = {
                'status': 'success',
                'data': response_data
            }
        except json.JSONDecodeError:
            response = {'status': 'error', 'message': 'Invalid JSON payload'}
        except IntegrityError:
            response = {'status': 'error', 'message': 'Device with this name already exists.'}
        except Exception as e:
            response = {'status': 'error', 'message': str(e)}
    else:
        response = {'status': 'bad_request_type'}

    return JsonResponse(response)
from .worker_comm_utils import communicate_bulk_campaign_update_with

@csrf_exempt
def bulk_campaign(request):
    if request.method == 'GET':
        campaigns = BulkCampaign.objects.all().values()
        return JsonResponse(list(campaigns), safe=False)

    elif request.method == 'POST':
        data = json.loads(request.body)
        #print(data)

        if data.get('campaigns', []):
            for campaign in data['campaigns']:
                method = campaign.get('method')
                campaign_data = campaign.get('data', {})
                print(campaign_data)
                
                campaign_id = campaign_data.get('id')
                servers_id = campaign_data.get('servers', None)
                bots = campaign_data.get('childbots', None)
                devices = campaign_data.get('devices', None)
                scrape_tasks = campaign_data.get('scrape_tasks', None)
                proxies = campaign_data.get('proxies', None)
                messaging = campaign_data.get('messaging', None)
                sharing = campaign_data.get('sharing', None)

                #print(campaign_data)

                campaign_data.update({'servers_id': servers_id})
                campaign_data.pop('servers', None)
                campaign_data.pop('childbots', None)
                campaign_data.pop('devices', None)
                campaign_data.pop('scrape_tasks', None)
                campaign_data.pop('proxies', None)
                campaign_data.pop('messaging', None)
                campaign_data.pop('sharing', None)

                if method in ['create', 'update']:
                    if method == 'create':
                        campaign_instance = BulkCampaign.objects.create(**campaign_data)
                    elif method == 'update':
                        try:
                            campaign_instance = BulkCampaign.objects.get(id=campaign_id)
                            for key, value in campaign_data.items():
                                setattr(campaign_instance, key, value)
                            campaign_instance.save()
                        except BulkCampaign.DoesNotExist:
                            return JsonResponse({'error': 'Campaign not found'}, status=404)

                    if bots:
                        campaign_instance.childbots.set(bots)
                    if devices:
                        campaign_instance.devices.set(devices)
                    if scrape_tasks:
                        campaign_instance.scrape_tasks.set(scrape_tasks)
                    if proxies:
                        campaign_instance.proxies.set(proxies)
                    if messaging:
                        campaign_instance.messaging.set(messaging)
                    if sharing:
                        campaign_instance.sharing.set(sharing)

                    
                    communicate_bulk_campaign_update_with(campaign_instance)

                elif method == 'delete':
                    try:
                        campaign_instance = BulkCampaign.objects.get(id=campaign_id)
                        campaign_instance.delete()
                    except BulkCampaign.DoesNotExist:
                        return JsonResponse({'error': 'Campaign not found'}, status=404)

        return JsonResponse({'status': 'success'}, status=200)

    return HttpResponse('Method not allowed', status=405)

@csrf_exempt
def scrape_task(request):
    if request.method == 'GET':
        scrape_tasks = ScrapeTask.objects.all().values()
        return JsonResponse(list(scrape_tasks), safe=False)

    elif request.method == 'POST':
        data = json.loads(request.body)

        if not data.get('tasks'):
            return JsonResponse({'error': 'No tasks provided'}, status=400)

        for task in data['tasks']:
            method = task.get('method')
            task_data = task.get('data', {})

            if method not in ['create', 'update', 'delete']:
                continue 

            task_id = task_data.get('id')
            scrape_type = task_data.get('scrape_type')
            scrape_value = task_data.get('scrape_value')
            os = task_data.get('os')
            storage = task_data.get('storage')
            profile_ids = task_data.get('profile_ids', [])
            max_threads = task_data.get('max_threads')
            max_requests_per_day = task_data.get('max_requests_per_day')
            start_scraping = task_data.get('start_scraping', False)
            server_id = task_data.get('server_id')

            task_data.update({
                'scrape_type': scrape_type,
                'scrape_value': scrape_value,
                'os': os,
                'storage': storage,
                'max_threads': max_threads,
                'max_requests_per_day': max_requests_per_day,
                'start_scraping': start_scraping,
                'server_id': server_id
            })

            task_instance = None

            if method == 'create':
                task_instance = ScrapeTask.objects.create(**task_data)
                if profile_ids:
                    task_instance.profiles.set(profile_ids)

            elif method == 'update':
                try:
                    task_instance = ScrapeTask.objects.get(id=task_id)
                    for key, value in task_data.items():
                        setattr(task_instance, key, value)
                    task_instance.save()
                    if profile_ids:
                        task_instance.profiles.set(profile_ids)
                except ScrapeTask.DoesNotExist:
                    return JsonResponse({'error': 'Scrape task not found'}, status=404)

            elif method == 'delete':
                try:
                    task_instance = ScrapeTask.objects.get(id=task_id)
                    task_instance.delete()
                except ScrapeTask.DoesNotExist:
                    return JsonResponse({'error': 'Scrape task not found'}, status=404)

            if task_instance and method in ['create', 'update']:
                handle_scrape_task_creation(task_instance)

        return JsonResponse({'status': 'success'}, status=200)

    return HttpResponse('Method not allowed', status=405)

logger = logging.getLogger(__name__)
@csrf_exempt
def deleteDeviceResource(request, serial_number: str) -> JsonResponse:
    if request.method == 'DELETE':
        logger.debug(f"Received DELETE request for serial_number: {serial_number}")

        try:
            # Retrieve the device by serial number
            device = Device.objects.get(serial_number=serial_number)
            device.delete()

            connected_to_server_id = device.connected_to_server_id

            if connected_to_server_id:
                try:
                    connected_server = Server.objects.get(id=connected_to_server_id)
                    delete_url = f"{connected_server.public_ip}crawl/devices/{device.serial_number}/"

                    delete_response = requests.delete(delete_url)

                    if delete_response.status_code != 204:
                        return JsonResponse({'status': 'error', 'message': 'Failed to delete from worker.'}, status=500)

                except Server.DoesNotExist:
                    logger.error(f"Connected server with ID {connected_to_server_id} does not exist.")
                    return JsonResponse({'status': 'error', 'message': 'Connected server does not exist.'}, status=404)

            response = {
                'status': 'success',
                'message': 'Device deleted successfully from central and worker.'
            }

        except Device.DoesNotExist:
            logger.error(f"Device with serial number {serial_number} not found.")
            return JsonResponse({'status': 'error', 'message': 'Device not found.'}, status=404)

        except Exception as e:
            logger.error(f"An unexpected error occurred: {str(e)}")
            return JsonResponse({'status': 'error', 'message': 'An internal error occurred while processing your request.'}, status=500)
    else:
        logger.warning(f"Invalid request method: {request.method}")
        return JsonResponse({'status': 'bad_request_type'}, status=400)

    return JsonResponse(response)

logger = logging.getLogger(__name__)

@csrf_exempt
def deleteProxyResource(request, proxy_url: str) -> JsonResponse:
    if request.method == 'DELETE':
        logger.debug(f"Received DELETE request for proxy_url: {proxy_url}")

        try:
            proxy = Proxy.objects.get(proxy_url=proxy_url)
            proxy.delete()

            connected_to_server_id = proxy.connected_to_server_id

            if connected_to_server_id:
                try:
                    connected_server = Server.objects.get(id=connected_to_server_id)
                    delete_url = f"{connected_server.public_ip}crawl/proxies/{proxy.proxy_url}/"

                    delete_response = requests.delete(delete_url)

                    if delete_response.status_code != 204:
                        return JsonResponse({'status': 'error', 'message': 'Failed to delete from worker.'}, status=500)

                except Server.DoesNotExist:
                    logger.error(f"Connected server with ID {connected_to_server_id} does not exist.")
                    return JsonResponse({'status': 'error', 'message': 'Connected server does not exist.'}, status=404)

            response = {
                'status': 'success',
                'message': 'Proxy deleted successfully from central and worker.'
            }

        except Proxy.DoesNotExist:
            logger.error(f"Proxy with proxy URL {proxy_url} not found.")
            return JsonResponse({'status': 'error', 'message': 'Proxy not found.'}, status=404)

        except Exception as e:
            logger.error(f"An unexpected error occurred: {str(e)}")
            return JsonResponse({'status': 'error', 'message': 'An internal error occurred while processing your request.'}, status=500)
    else:
        logger.warning(f"Invalid request method: {request.method}")
        return JsonResponse({'status': 'bad_request_type'}, status=400)

    return JsonResponse(response)

@csrf_exempt
def createProxyResource(request: HttpRequest) -> JsonResponse:
    if request.method == 'POST':
        try:
            payload = json.loads(request.body.decode("utf-8"))
            max_threads = payload.get('max_threads')
            proxy_url = payload.get('proxy_url')
            ua_string = payload.get('ua_string')
            connected_to_server_id = payload.get('connected_to_server')
            is_available = payload.get('is_available')
            proxy_blacklisted = payload.get('proxy_blacklisted')
            provider = payload.get('provider')
            verified = payload.get('verified')
            proxy_type = payload.get('proxy_type')
            proxy_protocol = payload.get('proxy_protocol')

            if Proxy.objects.filter(proxy_url=proxy_url).exists():
                return JsonResponse({'status': 'error', 'message': 'Proxy with this URL already exists.'}, status=400)

            proxy = Proxy.objects.create(
                max_threads=max_threads,
                proxy_url=proxy_url,
                ua_string=ua_string,
                connected_to_server_id=connected_to_server_id,
                is_available=is_available,
                proxy_blacklisted=proxy_blacklisted,
                provider=provider,
                verified=verified,
                proxy_type=proxy_type,
                proxy_protocol=proxy_protocol
            )

            crawl_payload = {
                'max_threads': proxy.max_threads,
                'proxy_url': proxy.proxy_url,
                'ua_string': proxy.ua_string,
                'is_available': proxy.is_available,
                'proxy_blacklisted': proxy.proxy_blacklisted,
                'provider': proxy.provider,
                'verified': proxy.verified,
                'proxy_type': proxy.proxy_type,
                'proxy_protocol': proxy.proxy_protocol,
            }
            
           # print(crawl_payload)

            try:
                connected_server = Server.objects.get(id=connected_to_server_id)
                crawl_url = connected_server.public_ip + 'crawl/proxies/'
            except Server.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Connected server does not exist.'}, status=404)

            crawl_response = requests.post(crawl_url, json=crawl_payload)

            if crawl_response.status_code != 200:
                print(f"Error sending data to crawl URL: {crawl_response.text}")

            response_data = {
                'max_threads': proxy.max_threads,
                'proxy_url': proxy.proxy_url,
                'ua_string': proxy.ua_string,
                'is_available': proxy.is_available,
                'proxy_blacklisted': proxy.proxy_blacklisted,
                'provider': proxy.provider,
                'verified': proxy.verified,
                'proxy_type': proxy.proxy_type,
                'proxy_protocol': proxy.proxy_protocol,
            }
            response = {
                'status': 'success',
                'data': response_data
            }

        except json.JSONDecodeError:
            response = {'status': 'error', 'message': 'Invalid JSON payload'}
        except IntegrityError:
            response = {'status': 'error', 'message': 'Proxy with this URL already exists.'}
        except Exception as e:
            response = {'status': 'error', 'message': str(e)}
    else:
        response = {'status': 'bad_request_type'}

    return JsonResponse(response)

@csrf_exempt
def todo_view(request):
    if request.method == 'GET':
        todos = Todo.objects.all().values()
        return JsonResponse(list(todos), safe=False)

    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON format'}, status=400)

        if not data.get('todo'):
            return JsonResponse({'error': 'No todo tasks provided'}, status=400)

        for task in data['todo']:
            method = task.get('method')
            task_data = task.get('data', {})

            if method not in ['create', 'update', 'delete']:
                return JsonResponse({'error': 'Invalid method provided'}, status=400)

            task_id = task_data.get('id')
            name = task_data.get('name')
            caption = task_data.get('caption')
            target_location = task_data.get('target_location')
            google_drive_root_folder_name = task_data.get('google_drive_root_folder_name')
            bots = task_data.get('bots', [])
            files = task_data.get('files', [])

            task_data.update({
                'name': name,
                'caption': caption,
                'target_location': target_location,
                'google_drive_root_folder_name': google_drive_root_folder_name,
                'files': files,
            })

            task_instance = None

            if method == 'create':
                task_instance = Todo.objects.create(**task_data)
                if bots:
                    task_instance.bots.set(bots)

            elif method == 'update':
                try:
                    task_instance = Todo.objects.get(id=task_id)
                    for key, value in task_data.items():
                        setattr(task_instance, key, value)
                    task_instance.save()
                    if bots:
                        task_instance.bots.set(bots)
                except Todo.DoesNotExist:
                    return JsonResponse({'error': 'Todo task not found'}, status=404)

            elif method == 'delete':
                try:
                    task_instance = Todo.objects.get(id=task_id)
                    task_instance.delete()
                except Todo.DoesNotExist:
                    return JsonResponse({'error': 'Todo task not found'}, status=404)

        return JsonResponse({'status': 'success'}, status=200)

    return HttpResponse('Method not allowed', status=405)
    

import uuid

@csrf_exempt
def attendance_task(request):
    if request.method == 'POST':
        data = json.loads(request.body)

        print("Received Payload:", json.dumps(data, indent=2))

        if data.get('end_point') == 'Attendance' and data.get('data_point') == 'complete_attendance':
            
            end_point = data['end_point']
            data_point = data['data_point']
            service = data.get('service', 'attendance')
            repeat = data.get('repeat')
            repeat_duration = data.get('repeat_duration')

            add_data = {
                'slack_token': data.get('slack_token'),
                'slack_channel_id': data.get('slack_channel_id'),
                'response_email': data.get('response_email'),
                'attendance_type': data.get('attendance_type'),
            }

            if data['attendance_type'] == 'monthly':
                add_data['select_month'] = data.get('select_month')
            elif data['attendance_type'] == 'weekly':
                add_data['weekly_start_date'] = data.get('weekly_start_date')
                add_data['weekly_end_date'] = data.get('weekly_end_date')
            elif data['attendance_type'] == 'timeframe':
                add_data['start_date'] = data.get('start_date')
                add_data['end_date'] = data.get('end_date')

            server_id = data.get('servers') 
            task_instance = Task.objects.create(
                uuid=uuid.uuid4(),
                end_point=end_point,
                data_point=data_point,
                service=service,
                repeat=repeat,
                repeat_duration=repeat_duration,
                add_data=add_data
            )

            print("Created Task:", task_instance)

            if server_id:
                try:
                    
                    server = Server.objects.get(id=server_id)
                    worker_url = f"{server.public_ip}crawl/tasks/"
                    print(f"Connected server: ID: {server.id}, Public IP: {server.public_ip}")

                    
                    payload = {
                        'end_point': data['end_point'],
                        'data_point': data['data_point'],
                        'service': data.get('service', 'attendance'),
                        'repeat': data.get('repeat'),
                        'repeat_duration': data.get('repeat_duration'),
                        'add_data': add_data
                    }

                    print('Worker_payload', payload)

                   
                    if data['attendance_type'] == 'monthly':
                        payload['select_month'] = data.get('select_month')
                    elif data['attendance_type'] == 'weekly':
                        payload['weekly_start_date'] = data.get('weekly_start_date')
                        payload['weekly_end_date'] = data.get('weekly_end_date')
                    elif data['attendance_type'] == 'timeframe':
                        payload['start_date'] = data.get('start_date')
                        payload['end_date'] = data.get('end_date')

                   
                    response = requests.post(worker_url, json=payload)
                    if response.status_code == 200:
                        print(f"Payload successfully posted to {worker_url}")
                    else:
                        print(f"Failed to post payload to {worker_url}. Status Code: {response.status_code}")
                except Server.DoesNotExist:
                    print(f"Server with ID {server_id} does not exist")
                    return JsonResponse({'error': f"Server with ID {server_id} not found"}, status=404)

            return JsonResponse({'status': 'success', 'task_id': task_instance.id}, status=201)

        return JsonResponse({'error': 'Invalid payload'}, status=400)

    return HttpResponse('Method not allowed', status=405)