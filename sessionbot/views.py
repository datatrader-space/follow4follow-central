from django.http import HttpResponse, JsonResponse, HttpRequest
from django.views.decorators.csrf import csrf_exempt
from django.db import IntegrityError

from sessionbot.resource_utils import create_resources_from_google_sheets
from .models import BulkCampaign, ChildBot, Device, Server, Proxy, Task,ScrapeTask,Logs
import json
import requests
import logging
import sessionbot.handlers.scrapetask as scrapetask

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
                monitor=campaign_data.get('monitor',False)
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
                    if monitor:
                        campaign_instance.monitor=monitor
                        campaign_instance.save()
                        
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
   

    if request.method == 'POST':
        data = json.loads(request.body)    
        print(data)  
        method=data.get('method')

        if method =='get':
            results=[]
            if data.get('ids'):
                for _id in data.get('ids',[]):
                    obj=ScrapeTask.objects.all().filter(id=_id)
                    if obj:
                        obj=obj[0]
                        res=model_to_dict(obj)
                        vals=[]
                        for input in res.input.split(','):
                            if 'followers' in input:
                                scrape_type='by_username'
                            elif 'location' in input:
                                scrape_type='by_location'
                            elif 'keyword' in input:
                                scrape_type='by_keyword'
                            elif 'hashtag' in input:
                                scrape_type='by_hashtag'
                            vals.append(input.split('__')[1])
                            res.pop('input')
                            res.pop('customer')
                        res.pop('childbots')
                        res.update({'childbot_ids':list(obj.childbots.values_list('id','name'))})
                        res.update({'scrape_type':scrape_type,'scrape_value':','.join(vals)})
                        
                    else:
                        res=False
                    results.append({_id:res})
            else:
                from django.forms import model_to_dict
                vals=[]
                for obj in ScrapeTask.objects.all():
                    res=model_to_dict(obj)
                    for input in obj.input.split(','):
                            if 'followers' in input:
                                scrape_type='by_username'
                            elif 'location' in input:
                                scrape_type='by_location'
                            elif 'keyword' in input:
                                scrape_type='by_keyword'
                            elif 'hashtag' in input:
                                scrape_type='by_hashtag'
                            vals.append(input.split('__')[1])
                    res.pop('input')
                    res.pop('customer')
                    res.pop('childbots')
                    res.update({'childbot_ids':list(obj.childbots.values_list('id','display_name'))})
                    res.update({'scrape_type':scrape_type,'scrape_value':','.join(vals)})
                    results.append({obj.id:res})
                    
            print(results)
            return JsonResponse(results,safe=False)
        elif method=='create':
            for task in data['data']:
                print(task)
                inputs=[]
                
                if method == 'create':                     
                    task_data = task
                    if not task.get('childbot_ids'):
                        l=Logs(end_point='scrapetask',label='ERROR',message='Create Scrape task missing childbots. Ignoring the row. Data: '+str(task))
                        l.save()
                    task=scrapetask.handle_scrapetask_form_from_frontend(task)          
                    if ScrapeTask.objects.filter(name=task.get('name')):
                        print('Dup')
                        l=Logs(end_point='scrapetask',label='ERROR',message='A Scrape task with the same name exists, Either Edit existing task or create new with similar name')
                        l.save()
                        return JsonResponse({'error': 'A Scrape task with the same name exists, Either Edit existing task or create new with similar name'}, status=404)
                
                    s=ScrapeTask(**task)

                    s.save()
                    childbot_ids = task_data.get('childbot_ids', [])
                    s.childbots.set(childbot_ids)
                    print(childbot_ids)
                    s.save()
                    print(s.childbots.all())
                    from sessionbot.handlers.scrapetask import handle_scrape_task
                    try:
                        handle_scrape_task(s)
                    except Exception as e:
                        import traceback
                        l=Logs(message=traceback.format_exc(),label='ERROR',end_point='scrapetask')
                        l.save()
                        s.delete()
        elif method == 'update':            
                tasks = data.get('data',{})
                for task in tasks:
                    for key, value in task.items():
                        obj=ScrapeTask.objects.filter(id=key)
                        if obj:
                            obj=obj[0]
                            childbot_ids = value.get('childbot_ids', [])
                            obj.childbots.set(childbot_ids)
                            obj.save()
                            print(obj.childbots.all())
                            scrapetask.handle_scrape_task_creation(obj)
                            l=Logs(message='New bots added to Scrape Task '+str(obj.name),end_point='scrapetask',label='WARNING')

                        else:
                            l=Logs(message='Failed to Update Scrape Task. Object with Id doesnt exist. Data: '+str(value),end_point='scrapetask',label='WARNING')
                            l.save()
                            continue
                return JsonResponse(status=200,data={'status':'success'})


        elif method == 'delete':
            ids = data.get('data',{}).get('ids')
            for id in ids:
                
                    obj=ScrapeTask.objects.filter(id=id)
                    if obj:
                        obj=obj[0]
                        scrapetask.handle_scrape_task_deletion(obj)
        elif method =='change_state':
            tasks = data.get('data',{})
            for task in tasks:
                for key, value in task.items():
                    obj=ScrapeTask.objects.filter(id=key)
                    if obj:
                        obj=obj[0]
                        scrapetask.handle_scrapetask_state_change(obj)

           

        return JsonResponse({'status': 'success'}, status=200)

    return HttpResponse('Method not allowed', status=405)


@csrf_exempt
def todo(request):
    import sessionbot.handlers.todo as todo
    from sessionbot.models import Todo
    if request.method == 'POST':
        data = json.loads(request.body)      
        method=data.get('method')
        print(data)
        if method =='get':
            results=[]
            if data.get('ids'):
                for _id in data.get('ids',[]):
                    obj=Todo.objects.all().filter(id=_id)
                    
                    if obj:
                        obj=obj[0]
                        res=model_to_dict(obj)
                        res.pop('childbots')
                        res.pop('file')
                        res.update({'childbot_ids':list(obj.childbots.values_list('id','display_name'))})
                        
                    else:
                        res=False
                    results.append({_id:res})
                    
            else:
                from django.forms import model_to_dict
                vals=[]
                for obj in Todo.objects.all():
                    res=model_to_dict(obj)
                    res.pop('childbots')
                    res.update({'childbot_ids':list(obj.childbots.values_list('id','display_name'))})
                    res.pop('file')
                    results.append({obj.id:res})
                    
            print(results)
            return JsonResponse(results,safe=False)
        elif method=='create':
            for task in data['data']:
                print(task)

                
                if method == 'create':                     
                       
                    if Todo.objects.filter(name=task.get('name')):
                        print('Dup')
                        l=Logs(end_point='todo',label='ERROR',message='A TODO with the same name exists, Either Edit existing TODO or create new with similar name')
                        l.save()
                        return JsonResponse({'error': 'A TODO with the same name exists, Either Edit existing task or create new with similar name'}, status=404)
                    else:
                        existing_todos=Todo.objects.filter(google_drive_root_folder_name=task.get('google_drive_root_folder_name')).filter(childbots=task.get('bots'))                      
                        if len(existing_todos)>0:
                            l=Logs(end_point='todo',label='ERROR',message='A TODO with the same name google driver root folder and selected bot exists, We dont recommend creating duplicates')
                            l.save()
                        else:
                            childbot_ids=task.pop('childbot_ids',False)
                            task.pop('file',False)
                            t=Todo(**task)
                            t.save()
                            
                            if childbot_ids:
                                t.childbots.set(childbot_ids)
                
                        import sessionbot.handlers.todo as todo
                        try:
                            todo.handle_todo_creation(t)
                        except Exception as e:
                            import traceback
                            l=Logs(message=traceback.format_exc(),label='ERROR',end_point='todo')
                            l.save()
                            t.delete()   
        elif method == 'update':            
                tasks = data.get('data',{})
                for task in tasks:
                    print(task)
                    for key, value in task.items():
                        print(key)
                        obj=Todo.objects.filter(id=int(key))
                        print(obj)
                        if obj:
                            obj=obj[0]
                            childbot_ids=value.pop('childbot_ids',False)
                            if childbot_ids:
                                obj.childbots.set(childbot_ids)
                                obj.save()
                                obj.childbots.all()
                            todo.handle_todo_creation(obj)
                            

                            l=Logs(message='New bots added to Todo '+str(obj.name),end_point='todo',label='INFO')

                        else:
                            l=Logs(message='Failed to Update Todo. Object with Id doesnt exist. Data: '+str(value),end_point='todo',label='WARNING')
                            l.save()
                            continue
                return JsonResponse(status=200,data={'status':'success'})


        elif method == 'delete':
            ids = data.get('data',{}).get('ids',[])
            for id in ids:
              
                    obj=Todo.objects.filter(id=id)
                    if obj:
                        obj=obj[0]
                        todo.handle_todo_deletion(obj)
        elif method =='change_state':
            tasks = data.get('data',{})
            for task in tasks:
                for key, value in task.items():
                    obj=Todo.objects.filter(id=key)
                    if obj:
                        obj=obj[0]
                        todo.handle_state_change(obj)
           

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

@csrf_exempt
def logs(request):
    if request.method == 'POST':
        from sessionbot.models import Logs
        data = json.loads(request.body)
        print(data)
       
        logs=Logs.objects.all().filter(end_point=data.get('end_point')).order_by('-timestamp').values()
        return JsonResponse(list(logs),safe=False)
    return HttpResponse('Method not allowed', status=405)
    