from django.http import HttpResponse, JsonResponse, HttpRequest
from django.views.decorators.csrf import csrf_exempt
from django.db import IntegrityError

from sessionbot.resource_utils import create_resources_from_google_sheets,analyze_bot_responses
from .models import TaskErrorSummary,BulkCampaign, ChildBot, Device, Server, Proxy, Task,ScrapeTask,Log,Audience
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
            operation_counts = analyze_bot_responses(r)
            # Print the results
            results = []
            for status, count in operation_counts.items():
                results.append((f"{status.replace('_', ' ').title()}: {count}"))
            
            # print("Response from create_resources_from_google_sheets:", r)
            
            response = {'status': 'success', 'data': results}
        except json.JSONDecodeError:
            response = {'status': 'error', 'message': 'Invalid JSON payload'}
        except Exception as e:
            print(e)
            response = {'status': 'error', 'message': str(e)}
    else:
        response = {'status': 'bad_request_type'}
    
    return JsonResponse(response)




from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import SyncedSheet
# Your helper function

@api_view(['GET', 'POST'])  # Both GET and POST handled by this view
def sync_sheet(request):
    if request.method == 'GET':
        synced_sheets = SyncedSheet.objects.all()
        data = [
            {
                "id": sheet.id,
                "google_sheet_link": sheet.google_sheet_link,
                "spreadsheet_name": sheet.spreadsheet_name,
                "created_at": sheet.created_at,
            }
            for sheet in synced_sheets
        ]
        return Response(data, status=status.HTTP_200_OK)

    elif request.method == 'POST':
        google_sheet_link = request.data.get("google_sheet_link")

        if not google_sheet_link:
            return Response(
                {"error": "Google sheet link is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            synced_sheet, created = SyncedSheet.objects.get_or_create(
                google_sheet_link=google_sheet_link
            )

            payload = {"google_spreadsheet_url": google_sheet_link}

            r = create_resources_from_google_sheets(**payload)

            if r.get('status') == 'success':
                return Response(
                    {"status": "success", "data": r},
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {"status": "error", "message": r.get("message"), "details": r.get("logs")},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
# @csrf_exempt
# def audience(request):
#     if request.method == 'POST':
#         from django.forms import model_to_dict
        
#         data = json.loads(request.body)      
#         method=data.get('method')
#         print(data)
#         print(method)
#         #print(data)
#         if method =='get':
#             from sessionbot.models import Audience
#             results=[]
#             data=data.get('data')
#             if data.get('ids'):
#                 for _id in data.get('ids',[]):
#                     scrape_task_ids=[]
#                     obj=Audience.objects.all().filter(id=_id)
#                     if obj:
#                         obj=obj[0]
#                         res=model_to_dict(obj)
#                         res.pop('scrape_tasks')
#                         for s in obj.scrape_tasks.all():
#                             scrape_task_ids.append(s.id)
#                         res.update({'scrape_task_ids':scrape_task_ids})
#                         vals=[]
                        
                        
#                     else:
#                         res=False
#                     results.append({_id:res})
#             else:
                
#                 vals=[]
#                 scrape_task_ids=[]
#                 for obj in Audience.objects.all():
#                     res=model_to_dict(obj)
#                     res.pop('scrape_tasks')
#                     for s in obj.scrape_tasks.all():
#                         scrape_task_ids.append({s.id:s.name})
#                     res.update({'scrape_tasks':scrape_task_ids})
#                     results.append({obj.id:res})
                    
#             print(results)
#             return JsonResponse(results,safe=False)

#         elif method=='create':
#            logs=[]
#            from sessionbot.models import Audience
#            from sessionbot.handlers.audience import handle_audience_creation
#            for row in data.get('data'):
#             print(row)
#             a=Audience.objects.all().filter(name=row['name'])
#             if len(a)>0:
#                 a=a[0]
#                 l=Log(message='Failed to create Audience. An Audience with name '+str(row['name'])+' already exists',end_point='audience')
#                 l.save()
#                 logs.append('Failed to create Audience. An Audience with name '+str(row['name'])+' already exists''')
#                 return JsonResponse({'status': 'failed','logs':logs}, status=200)
#             else:
#                 a=Audience()
#                 try:
#                     outs=handle_audience_creation(a,row)
#                     if outs:
#                         logs.extend(outs) 
#                 except Exception as e:
#                     import traceback
#                     print(traceback.format_exc())
#                     logs.append({'error':e,'row':row})
#                     print(e)
#                     a.delete()
#                     return JsonResponse({'status': 'failed'}, status=400)
#                 else:
#                     logs.append({'success':row})
#                     return JsonResponse(status=200,data={'status':'success','logs':logs})


                    

#         elif method == 'update':            
#                 pass
#                 l=Log(message='Failed to Update Todo. Object with Id doesnt exist. Data: '+str(value),end_point='todo',label='WARNING')
#                 l.save()
           
#                 return JsonResponse(status=200,data={'status':'success'})
#         elif method=='visualize':
#             data=data.get('data')
#             audience_id=data.get('ids')[0]
#             session_id=data.get('session_id')
#             from sessionbot.saver import Saver
#             s=Saver()
#             print(session_id)
#             exclude_blocks=s.get_consumed_blocks_for_audience_for_session(audience_id=audience_id,session_id=session_id)
#             resp=s.retrieve_audience_outputs_for_session(session_id,audience_id=audience_id,keys=True,size=50)
#             print(resp)
#             print('audience has data')
#             if not resp:           
#                 from sessionbot.utils import DataHouseClient
#                 from django.conf import settings
#                 from sessionbot.models import Audience,Task
#                 d=DataHouseClient()
#                 a=Audience.objects.all().filter(id=audience_id)
#                 datahouse=Server.objects.all().filter(instance_type='data_server')
#                 if datahouse:
#                     datahouse_url=datahouse[0].public_ip
#                     d.base_url=datahouse_url
#                 else:
#                     print('datahouse not found')
#                     return JsonResponse({'status': 'failed. Datahouse not found','data':[]}, status=200)   
#                 print(a)
#                 if a:
#                     a=a[0]
#                     a.scrape_tasks                
#                     tasks=Task.objects.all().filter(ref_id__in=list(a.scrape_tasks.values_list('uuid',flat=True)))
#                     #tasks=Task.objects.all().filter(ref_id=a.uuid).values_list('uuid',flat=True)
#                 if tasks:
#                     filters={'tasks__uuid.in':list(tasks.values_list('uuid',flat=True)),}        
#                     required_fields=['username','info__full_name','info__gender','info__country','info__followers_count','profile_picture']     
#                     resp=d.retrieve(object_type='profile',  filters=filters, locking_filters=None, lock_results=False,task_uuid=tasks[0].uuid)
#                 else:
#                     return JsonResponse({'status': 'failed. No Scrape Tasks found for Audience','data':[]}, status=200)     
#                 results=[]
       
#                 unique_usernames=[]
#                 storagehouse=Server.objects.all().filter(instance_type='storage_house')
#                 if storagehouse:
#                     storagehouse_url=storagehouse[0].public_ip
#                     storagehouse_ngrok_url=storagehouse[0].instance_id
#                 for row in resp['data']:
#                     if row['username'] in unique_usernames:
#                             continue
#                     else:
#                         if row.get('profile_picture'):
                            
#                             url=storagehouse_ngrok_url+row['profile_picture']
#                             import urllib
#                             import re
#                             cleaned_url = url.replace("\\", "/")
#                             # 2. Parse the URL to handle encoding issues
#                             parsed_url = urllib.parse.urlparse(cleaned_url)
#                             # 3. Reconstruct the URL with proper encoding
#                             cleaned_url = urllib.parse.urlunparse(parsed_url)
#                             cleaned_url = re.sub(r"(?<!:)/{2,}", "/", cleaned_url)              
#                             row['profile_picture']=cleaned_url
#                         unique_usernames.append(row['username'])             
#                         results.append(row)
#                 for i in range(0, len(results), 50):
#                     chunk = results[i:i + 50]
#                     s.save_audience_outputs_for_session(session_id=session_id,audience_id=audience_id,data=chunk)
#                 resp=s.retrieve_audience_outputs_for_session(session_id,audience_id=audience_id,size=50,keys=True)   
#                 results=[]
#                 for key,value in resp.items():          
#                     if len(results)>=50:
#                         break          
#                     s.add_output_block_to_consumed_blocks_for_audience_for_session(session_id=session_id,audience_id=audience_id,output_block=key)  
#                     results.extend(value)
                
#                 return JsonResponse({'status': 'success','data':results}, status=200) 
#             else:
#                 exclude_blocks=s.get_consumed_blocks_for_audience_for_session(audience_id=audience_id,session_id=session_id)
#                 resp=s.retrieve_audience_outputs_for_session(session_id,audience_id=audience_id,size=50,keys=True,exclude_blocks=exclude_blocks) 
#                 if not resp:
#                     return JsonResponse({'status': 'success','data':[]}, status=200) 
#                 serve=[]
#                 for key,value in resp.items():
#                     if len(serve)>=50:
#                         break
#                     print('Request recieve')
#                     if len(value)==1:
#                         serve.append(value[0])
#                         value[0].pop('profile_pic',False)
#                         value[0].pop('full_name',False)
#                     else:
#                         for row in value:
#                             serve.append(row)
#                             row.pop('profile_pic',False)
#                             row.pop('full_name',False)
                        
#                     s.add_output_block_to_consumed_blocks_for_audience_for_session(session_id=session_id,audience_id=audience_id,output_block=key)
                    
                        

#                 print(session_id)
#                 print(serve[0])
#                 return JsonResponse({'status': 'success','data':serve}, status=200)                              
                                    

#         elif method=='save':
#             from sessionbot.saver import Saver
#             import base64
#             from io import BytesIO
#             from django.core.files import File
#             from uuid import uuid4
#             from django.conf import settings
#             import os
#             s=Saver()
#             audience_data=data.get('data')
#             audience_id=data.get('audience_id')
            
#             for row in audience_data:
#                 print(row.get('profile_pic').keys())
#                 file_content_b64 =row.get('profile_pic').get('file_content')

#             if not file_content_b64:
#                print('file content not found')
#             else:
#                 file_content = base64.b64decode(file_content_b64)
#                 file_object = BytesIO(file_content)

#                 # Generate a unique filename
                
#                 filename = str(uuid4()) + '.jpg'  # Assuming JPG format, adjust as needed

#                 # Save the file to the media folder
#                 file_path = os.path.join(settings.MEDIA_ROOT, filename)
#                 print(file_path)
#                 with open(file_path, 'wb') as f:
#                     f.write(file_object.getvalue())
#                     row.update({'profile_picture':filename})
#             s.save_audience_outputs(audience_id,audience_data)
#             return JsonResponse({'status': 'success'}, status=200)
#         elif method == 'delete':
#             ids = data.get('data',{}).get('ids',[])
#             return JsonResponse({'status': 'success'}, status=200)
#         elif method =='change_state':
#             tasks = data.get('data',{})
#             for task in tasks:
#                 for key, value in task.items():
#                     obj=Todo.objects.filter(id=key)
#                     if obj:
#                         obj=obj[0]
#                         todo.handle_state_change(obj)
           
#         else:
#             return JsonResponse({'status': 'failed'}, status=400)

#     return HttpResponse('Method not allowed', status=405)



@csrf_exempt
def audience(request):
    if request.method == 'POST':
        from django.forms import model_to_dict
        import json
        
        data = json.loads(request.body)      
        method=data.get('method')
        print(data)
        print(method)
        
        #print(data)
        if method =='get':
            from sessionbot.models import Audience
            results=[]
            data=data.get('data')
            if data.get('ids'):
                for _id in data.get('ids',[]):
                    scrape_task_ids=[]
                    obj=Audience.objects.all().filter(id=_id)
                    if obj:
                        obj=obj[0]
                        res=model_to_dict(obj)
                        res.pop('scrape_tasks')
                        for s in obj.scrape_tasks.all():
                            scrape_task_ids.append(s.id)
                        res.update({'scrape_task_ids':scrape_task_ids})
                        vals=[]
                        
                        
                    else:
                        res=False
                    results.append({_id:res})
            else:
                
                vals=[]
                scrape_task_ids=[]
                for obj in Audience.objects.all():
                    res=model_to_dict(obj)
                    res.pop('scrape_tasks')
                    for s in obj.scrape_tasks.all():
                        scrape_task_ids.append({s.id:s.name})
                    res.update({'scrape_tasks':scrape_task_ids})
                    results.append({obj.id:res})
                    
            print(results)
            return JsonResponse(results,safe=False)

        elif method == 'create':
            logs = []
            from sessionbot.models import Audience, Log
            from sessionbot.handlers.audience import handle_audience_creation

            # since your payload is a single object
            general_config = data.get('generalConfig', {})
            settings = general_config.get('settings', {})
            name = settings.get('name')
            
            # Check if an Audience with this name already exists
            existing = Audience.objects.filter(name=name)
            if existing.exists():
                log_msg = f"Failed to create Audience. An Audience with name {name} already exists"
                Log(message=log_msg, end_point='audience').save()
                logs.append(log_msg)
                return JsonResponse({'status': 'failed', 'logs': logs}, status=200)
            
            # Create new Audience
            a = Audience()
            try:
                outs = handle_audience_creation(a, data)
                if outs:
                    logs.extend(outs)
            except Exception as e:
                import traceback
                error_trace = traceback.format_exc()
                print(error_trace)
                logs.append({'error': str(e)})
                # Delete partial Audience if created
                try:
                    a.delete()
                except Exception:
                    pass
                return JsonResponse({'status': 'failed', 'logs': logs}, status=400)

            logs.append({'success': f"Audience '{name}' created successfully."})
            return JsonResponse({'status': 'success', 'logs': logs}, status=200)
        elif method == 'update':
            from sessionbot.models import Audience, ScrapeTask, Task, Log
            value = data.get('data', [])
            
            for data_dict in value:
                for audience_id_str, audience_data in data_dict.items():
                    try:
                        audience_id = int(audience_id_str)
                        audience = Audience.objects.get(pk=audience_id)
                    except (Audience.DoesNotExist, ValueError):
                        Log(
                            message=f'Failed to update Audience with id {audience_id_str}: does not exist.',
                            end_point='audience_update',
                            label='WARNING'
                        ).save()
                        continue

                    # Update prompt field from ai_prompt in payload
                    if 'ai_prompt' in audience_data:
                        audience.prompt = audience_data['ai_prompt']

                    # Update scrape_tasks many-to-many
                    if 'scrapetask' in audience_data:
                        try:
                            task_ids = [int(tid) for tid in audience_data['scrapetask']]
                            tasks = ScrapeTask.objects.filter(id__in=task_ids)
                            audience.scrape_tasks.set(tasks)
                        except ValueError:
                            Log(
                                message=f'Invalid scrapetask IDs: {audience_data["scrapetask"]}',
                                end_point='audience_update',
                                label='ERROR'
                            ).save()
                            continue

                    audience.save()

            return JsonResponse({'status': 'success'}, status=200)
        
        elif method == 'visualize':
            data = data.get('data')
            audience_id = data.get('ids')[0]
            session_id = data.get('session_id')

            from sessionbot.saver import Saver
            s = Saver()
            print(session_id)

            exclude_blocks = s.get_consumed_blocks_for_audience_for_session(
                audience_id=audience_id, session_id=session_id
            )

            resp = s.retrieve_audience_outputs_for_session(
                session_id, audience_id=audience_id, keys=True, size=50
            )
            print(resp)
            print('audience has data')

            if not resp:
                from sessionbot.utils import DataHouseClient
                from django.conf import settings
                from sessionbot.models import Audience, Task, Server

                d = DataHouseClient()
                print("DataHouseClient created:", d)
                print("DataHouseClient base_url:", getattr(d, 'base_url', 'NO URL SET'))

                a = Audience.objects.all().filter(id=audience_id)
                datahouse = Server.objects.all().filter(instance_type='data_server')
                if datahouse:
                    d.base_url = datahouse[0].public_ip
                else:
                    print('datahouse not found')
                    return JsonResponse({'status': 'failed. Datahouse not found', 'data': []}, status=200)

                print(a)
                if a:
                    a = a[0]
                    tasks = Task.objects.all().filter(ref_id__in=list(
                        a.scrape_tasks.values_list('uuid', flat=True)
                    ))

                if tasks:
                    filters = {
                        'tasks__uuid.in': list(tasks.values_list('uuid', flat=True))
                    }
                    required_fields = [
                        'username',
                        'info__full_name',
                        'info__gender',
                        'info__country',
                        'info__followers_count',
                        'profile_picture'
                    ]
                    resp = d.retrieve(
                        object_type='profile',
                        filters=filters,
                        locking_filters=None,
                        lock_results=False,
                        task_uuid=tasks[0].uuid
                    )
                    data_list = resp.get('data', [])

                    # ✅ BYPASS if data_list is empty
                    if not data_list:
                        return JsonResponse({'status': 'success', 'data': []}, status=200)

                else:
                    return JsonResponse({'status': 'failed. No Scrape Tasks found for Audience', 'data': []}, status=200)

                results = []
                unique_usernames = []
                storagehouse = Server.objects.all().filter(instance_type='storage_server')
                if storagehouse:
                    storagehouse_ngrok_url = storagehouse[0].public_ip
                    #storagehouse_ngrok_url = storagehouse[0].instance_id

                for row in data_list:
                    if row['username'] in unique_usernames:
                        continue
                    else:
                        if row.get('profile_picture'):
                            url = storagehouse_ngrok_url + row['profile_picture']
                            import urllib
                            import re
                            cleaned_url = url.replace("\\", "/")
                            parsed_url = urllib.parse.urlparse(cleaned_url)
                            cleaned_url = urllib.parse.urlunparse(parsed_url)
                            cleaned_url = re.sub(r"(?<!:)/{2,}", "/", cleaned_url)
                            row['profile_picture'] = cleaned_url

                        unique_usernames.append(row['username'])
                        results.append(row)

                for i in range(0, len(results), 50):
                    chunk = results[i:i + 50]
                    s.save_audience_outputs_for_session(
                        session_id=session_id, audience_id=audience_id, data=chunk
                    )

                resp = s.retrieve_audience_outputs_for_session(
                    session_id, audience_id=audience_id, size=50, keys=True
                )
                results = []
                for key, value in resp.items():
                    if len(results) >= 50:
                        break
                    s.add_output_block_to_consumed_blocks_for_audience_for_session(
                        session_id=session_id, audience_id=audience_id, output_block=key
                    )
                    results.extend(value)

                return JsonResponse({'status': 'success', 'data': results}, status=200)

            else:
                exclude_blocks = s.get_consumed_blocks_for_audience_for_session(
                    audience_id=audience_id, session_id=session_id
                )

                resp = s.retrieve_audience_outputs_for_session(
                    session_id, audience_id=audience_id, size=50, keys=True, exclude_blocks=exclude_blocks
                )

                if not resp:
                    return JsonResponse({'status': 'success', 'data': []}, status=200)

                serve = []
                for key, value in resp.items():
                    if len(serve) >= 50:
                        break
                    print('Request receive')

                    if len(value) == 1:
                        serve.append(value[0])
                        value[0].pop('profile_pic', False)
                        value[0].pop('full_name', False)
                    else:
                        for row in value:
                            serve.append(row)
                            row.pop('profile_pic', False)
                            row.pop('full_name', False)

                    s.add_output_block_to_consumed_blocks_for_audience_for_session(
                        session_id=session_id, audience_id=audience_id, output_block=key
                    )

                print(session_id)
                print(serve[0])
                return JsonResponse({'status': 'success', 'data': serve}, status=200)                               
                                    

        elif method=='save':
            from sessionbot.saver import Saver
            import base64
            from io import BytesIO
            from django.core.files import File
            from uuid import uuid4
            from django.conf import settings
            import os
            s=Saver()
            audience_data=data.get('data')
            audience_id=data.get('audience_id')
            
            for row in audience_data:
                print(row.get('profile_pic').keys())
                file_content_b64 =row.get('profile_pic').get('file_content')

            if not file_content_b64:
               print('file content not found')
            else:
                file_content = base64.b64decode(file_content_b64)
                file_object = BytesIO(file_content)

                # Generate a unique filename
                
                filename = str(uuid4()) + '.jpg'  # Assuming JPG format, adjust as needed

                # Save the file to the media folder
                file_path = os.path.join(settings.MEDIA_ROOT, filename)
                print(file_path)
                with open(file_path, 'wb') as f:
                    f.write(file_object.getvalue())
                    row.update({'profile_picture':filename})
            s.save_audience_outputs(audience_id,audience_data)
            return JsonResponse({'status': 'success'}, status=200)
        elif method == 'delete':
            ids = data.get('data',{}).get('ids',[])
            return JsonResponse({'status': 'success'}, status=200)
        elif method =='change_state':
            tasks = data.get('data',{})
            for task in tasks:
                for key, value in task.items():
                    obj=Todo.objects.filter(id=key)
                    if obj:
                        obj=obj[0]
                        todo.handle_state_change(obj)
           
        else:
            return JsonResponse({'status': 'failed'}, status=400)

    return HttpResponse('Method not allowed', status=405)






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
                audience=campaign_data.get('audiences',[])
                if audience:
                    campaign_data.update({'audience_id':audience[0]})
                campaign_data.pop('audiences')

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
                        Task.objects.all().filter(end_point='interact').filter(ref_id=campaign_instance.id).update(delete=True)
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
            from django.forms import model_to_dict
            results=[]
            data=data.get('data')
            if data.get('ids'):
                for _id in data.get('ids',[]):
                    obj=ScrapeTask.objects.all().filter(id=_id)
                    if obj:
                        obj=obj[0]
                        res=model_to_dict(obj)
                        print(res)
                        vals=[]
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
                            print(res)
                        res.pop('input')
                        res.pop('customer')
                        res.pop('childbots')
                        res.update({'childbot_ids':list(obj.childbots.values_list('id','username'))})
                        res.update({'scrape_type':scrape_type,'scrape_value':','.join(vals)})
                        
                    else:
                        res=False
                    results.append({_id:res})
            else:
                
                
                for obj in ScrapeTask.objects.all():
                    vals=[]
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
                        l=Log(end_point='scrapetask',label='ERROR',message='Create Scrape task missing childbots. Ignoring the row. Data: '+str(task))
                        l.save()
                    task=scrapetask.handle_scrapetask_form_from_frontend(task)          
                    if ScrapeTask.objects.filter(name=task.get('name')):
                        print('Dup')
                        l=Log(end_point='scrapetask',label='ERROR',message='A Scrape task with the same name exists, Either Edit existing task or create new with similar name')
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
                        l=Log(message=traceback.format_exc(),label='ERROR',end_point='scrapetask')
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
                            l=Log(message='New bots added to Scrape Task '+str(obj.name),end_point='scrapetask',label='WARNING')

                        else:
                            l=Log(message='Failed to Update Scrape Task. Object with Id doesnt exist. Data: '+str(value),end_point='scrapetask',label='WARNING')
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
            from django.forms import model_to_dict
            results=[]
            data=data.get('data')
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
                    if task['repeat_after']:
                        task['repeat_after']=int(task['repeat_after'])
                    else:
                        task.pop('repeat_after',False)  
                    if Todo.objects.filter(name=task.get('name')):
                        print('Dup')
                        l=Log(end_point='todo',label='ERROR',message='A TODO with the same name exists, Either Edit existing TODO or create new with similar name')
                        l.save()
                        return JsonResponse({'error': 'A TODO with the same name exists, Either Edit existing task or create new with similar name'}, status=404)
                    else:
                        existing_todos=Todo.objects.filter(google_drive_root_folder_name=task.get('google_drive_root_folder_name')).filter(childbots=task.get('bots'))                      
                        if len(existing_todos)>0:
                            l=Log(end_point='todo',label='ERROR',message='A TODO with the same name google driver root folder and selected bot exists, We dont recommend creating duplicates')
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
                            l=Log(message=traceback.format_exc(),label='ERROR',end_point='todo')
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
                            

                            l=Log(message='New bots added to Todo '+str(obj.name),end_point='todo',label='INFO')

                        else:
                            l=Log(message='Failed to Update Todo. Object with Id doesnt exist. Data: '+str(value),end_point='todo',label='WARNING')
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
def log(request):
    if request.method == 'POST':
        from sessionbot.models import Log
        data = json.loads(request.body)
        print(f"here end point : {data}")
       
        Log=Log.objects.all().filter(end_point=data.get('end_point')).order_by('-timestamp').values()
        print(f"logs:{Log}")
        return JsonResponse(list(Log),safe=False)
    return HttpResponse('Method not allowed', status=405)


import json
from django.http import JsonResponse
from .models import ChildBot, Task, Log

from django.db.models import Q
from datetime import datetime
import uuid
from rest_framework import viewsets, views, status
from rest_framework.response import Response

from sessionbot.models import Event, Server
from django.utils.decorators import method_decorator
from rest_framework.permissions import DjangoModelPermissionsOrAnonReadOnly
from rest_framework.permissions import AllowAny
@method_decorator(csrf_exempt, name='dispatch')
class EventView(views.APIView):
    permission_classes = [AllowAny]
    queryset = Event.objects.all()  # Associate with the Event model
    def post(self, request):
        from sessionbot.serializers import EventSerializer
        from sessionbot.tasks import process_event_for_servers,process_task_event
        serializer = EventSerializer(data=request.data)
        print(request.data)
        if serializer.is_valid():
            event = serializer.save()
            event_type = event.event_type

            if event_type == 'heartbeat':
                process_event_for_servers.delay(event.id)
            elif event_type == 'resource':
                process_event_for_servers.delay(event.id)
            elif event_type=='task_started' or event_type =='task_failed' or event_type =='task_completed':
                process_task_event(event.id)
                
           
            else:
                print(f"Unknown event type received: {event_type}")

            return Response({"message": "Event received and is being processed."}, status=status.HTTP_202_ACCEPTED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
def task_actions(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            print(data)
            childbot_ids = data.get('childbot_ids')
            action = data.get('action')

            if not childbot_ids or not action:
                return JsonResponse({"error": "childbot_ids and action are required"}, status=400)

            childbots = ChildBot.objects.filter(id__in=childbot_ids)

            if not childbots.exists():
                return JsonResponse({"error": "ChildBots not found"}, status=404)

            response_data = []

            for childbot in childbots:
                if not childbot.logged_in_on_servers:
                    message = f"ChildBot {childbot.username} doesn't have server assigned. Skipping"
                    Log.objects.create(message=message, label="Task Running Check", end_point=request.path)
                    response_data.append({"message": message, "status": "warning"})
                    continue

                existing_task = Task.objects.filter(
                    service=childbot.service,
                    data_point=action,
                    profile=childbot.username
                ).first()

                if existing_task and existing_task.status == 'running':
                    message = f"ChildBot {childbot.id} already running for task {existing_task.data_point}"
                    Log.objects.create(message=message, label="Task Running Check", end_point=request.path)
                    response_data.append({"message": message, "status": "warning"})
                    continue

                if existing_task and existing_task.status == 'paused':
                    existing_task.status = 'pending'
                    existing_task.save()
                    message = f"Task {existing_task.data_point} for ChildBot {childbot.id} resumed."
                    Log.objects.create(message=message, label="Task Resumed", end_point=request.path)
                    response_data.append({"message": message, "status": "info"})
                    task = existing_task
                elif not existing_task:
                    task = Task.objects.create(
                        service=childbot.service,
                        end_point='interact',
                        os='browser',
                        interact=True,
                        data_point=action,
                        profile=childbot.username,
                        uuid=uuid.uuid1(),
                        server=childbot.logged_in_on_servers,
                        server_id=childbot.logged_in_on_servers.id,
                        status="pending",
                        registered=False
                    )
                    message = f"Task {action} created for ChildBot {childbot.id}."
                    Log.objects.create(message=message, label="Task Created", end_point=request.path)
                    response_data.append({"message": message, "status": "success"})
                else:
                    task = existing_task
                    task.data_point = action
                    task.status = "pending"
                    message = f"Task {action} updated for ChildBot {childbot.id}."

                # Attach reporting house info
                add_data = task.add_data or {}
                reporting_house_server = Server.objects.filter(instance_type='reporting_and_analytics_server').first()
                if reporting_house_server:
                    reporting_house_url = reporting_house_server.public_ip + 'reporting/task-reports/'
                    add_data['reporting_house_url'] = reporting_house_url

                # Attach datahouse info
                datahouse_server = Server.objects.filter(instance_type='data_server').first()
                if datahouse_server:
                    datahouse_url = datahouse_server.public_ip + 'datahouse/api/consume/'
                    add_data['datahouse_url'] = datahouse_url
                    
                # Attach Storagehouse info
                storage_server = Server.objects.filter(instance_type='storage_server').first()
                if storage_server:
                    storage_url = storage_server.public_ip + 'storagehouse/api/upload'
                    add_data['storage_house_url'] = storage_url
             

                task.add_data = add_data

                if task.server != childbot.logged_in_on_servers:
                    task.server = childbot.logged_in_on_servers

                task.registered = False
                task.save()

                log_message = f"ChildBot {childbot.username} started on {childbot.logged_in_on_servers.name} for task {action}"
                Log.objects.create(message=log_message, label="Task Updated", end_point=request.path)
                response_data.append({"message": log_message, "status": "info"})

                # Trigger background sync
                from .tasks import sync_with_data_house_and_workers
                sync_with_data_house_and_workers.delay()

                start_log_message = f"ChildBot {childbot.id} started on {childbot.logged_in_on_servers.name} for task {action}"
                Log.objects.create(message=start_log_message, label="Task Started", end_point=request.path)

            print(response_data)
            return JsonResponse({"messages": response_data}, status=200)

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        except Exception as e:
            print(e)
            return JsonResponse({"error": str(e)}, status=500)
    else:
        return JsonResponse({"error": "Method Not Allowed"}, status=405)
    

import os
import uuid
import json
import requests

from io import StringIO
from django.conf import settings
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from collections import defaultdict
from .models import Task, Server


@csrf_exempt
def fetch_task_summaries_view(request):
    if request.method != "POST":
        return HttpResponseBadRequest("Only POST method is allowed")

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON payload"}, status=400)

    object_type = payload.get("object_type")
    bot_type = payload.get("bot_type")
    selected_objects = payload.get("selected_objects", [])

    if not selected_objects:
        return JsonResponse({"error": "No selected_objects provided"}, status=400)

    task_map = {}

    if object_type == "scrape_task":
        from sessionbot.models import ScrapeTask
        scrape_qs = ScrapeTask.objects.filter(id__in=selected_objects)
        for scrape_task in scrape_qs:
            task_map[str(scrape_task.uuid)] = scrape_task.name or str(scrape_task.uuid)

    elif object_type == "bots":
        from sessionbot.models import ChildBot, Task

        if bot_type == "browser_profile":
            childbots = ChildBot.objects.filter(id__in=selected_objects)
            for childbot in childbots:
                username = childbot.username
                task = (
                    Task.objects
                    .filter(profile=username, os="browser")
                    .exclude(status="pending")
                    .order_by("-created_at")
                    .first()
                )
                if task:
                    task_map[str(task.uuid)] = username

        elif bot_type == "android":
            from sessionbot.models import Task
            task_qs = Task.objects.filter(id__in=selected_objects)
            for task in task_qs:
                bot_name = getattr(task, 'profile', None) or str(task.uuid)
                task_map[str(task.uuid)] = bot_name
        else:
            return JsonResponse({"error": "Unsupported bot_type"}, status=400)
    else:
        return JsonResponse({"error": "Unsupported object_type"}, status=400)

    from sessionbot.models import Server, Task

    reporting_server = Server.objects.filter(instance_type="reporting_and_analytics_server").first()
    if not reporting_server:
        return JsonResponse({"error": "Reporting server not found"}, status=500)
    analytics = reporting_server.public_ip

    if object_type == "scrape_task":
        from collections import defaultdict
        input_wise = defaultdict(lambda: {
            "Total Users Scraped": 0,
            "Total Downloaded Files": 0,
            "Total Storage Uploads": 0,
            "Failed to Download File Count": 0,
            "Found Next Page Info Count": 0,
            "Next Page Info Not Found Count": 0,
            "Has Next Page Info": None,
            "Failed Downloads Details": [],
            "Storage Upload Failed": False,
            "Task Completion Status": "Unknown",
        })

        bot_wise = defaultdict(lambda: {
            "Total Challenges Encountered": 0,
            "Current Login Status": "Unknown",
            "Total Login Attempts": 0,
            "Total Scrapes": 0,
            "Total Api Requests": 0,
        })

        for task_uuid, task_name in task_map.items():
            tasks = Task.objects.filter(ref_id=task_uuid)
            for task in tasks:
                try:
                    url = analytics + f"reporting/task-summaries/{task.uuid}/"
                    response = requests.get(url, timeout=10)
                    if response.status_code != 200:
                        print(f"Warning: Got status {response.status_code} from {url}")
                        continue

                    summary = response.json()

                    input_name = getattr(task, "input", "Unknown Input")
                    bot_name = getattr(task, "profile", "Unknown Bot")

                    input_report = input_wise[input_name]
                    input_report["Total Users Scraped"] += summary.get("total_users_scraped", 0)
                    input_report["Total Downloaded Files"] += summary.get("total_downloaded_files", 0)
                    input_report["Total Storage Uploads"] += summary.get("total_storage_uploads", 0)
                    input_report["Failed to Download File Count"] += summary.get("failed_to_download_file_count", 0)
                    input_report["Found Next Page Info Count"] += summary.get("found_next_page_info_count", 0)
                    input_report["Next Page Info Not Found Count"] += summary.get("next_page_info_not_found_count", 0)
                    input_report["Failed Downloads Details"].extend(summary.get("failed_downloads_details", []))
                    input_report["Storage Upload Failed"] = input_report["Storage Upload Failed"] or summary.get("storage_upload_failed", False)

                    current_status = input_report["Task Completion Status"]
                    new_status = summary.get("task_completion_status", current_status)
                    if current_status == "Unknown" or current_status == "Completed Successfully":
                        input_report["Task Completion Status"] = new_status

                    if input_report["Has Next Page Info"] is None:
                        input_report["Has Next Page Info"] = summary.get("has_next_page_info", None)

                    bot_report = bot_wise[bot_name]
                    bot_report["Total Challenges Encountered"] += summary.get("challenges_encountered", 0)
                    bot_report["Total Login Attempts"] += summary.get("total_login_attempts", 0)
                    bot_report["Total Scrapes"] += summary.get("total_users_scraped", 0)
                    bot_report["Total Api Requests"] += summary.get("total_api_requests", 0)

                except requests.RequestException as e:
                    print(f"RequestException for task {task.uuid}: {e}")
                    continue

        # Gather all scrape_task UUIDs selected (as strings) once for filtering
        selected_scrape_uuids = set(task_map.keys())

        for bot_name in bot_wise:
            try:
                # Filter Tasks with profile=bot_name AND ref_id in selected scrape task UUIDs
                latest_task = Task.objects.filter(
                    profile=bot_name,
                    ref_id__in=selected_scrape_uuids
                ).order_by("-created_at").first()

                if not latest_task:
                    print(f"No latest task found for bot '{bot_name}' with selected scrape tasks")
                    continue

                url = analytics + f"reporting/task-summaries/{latest_task.uuid}/"
                response = requests.get(url, timeout=10)
                if response.status_code != 200:
                    print(f"Failed to fetch summary for latest task {latest_task.uuid} with status {response.status_code}")
                    continue

                summary = response.json()
                print(f"Summary for bot '{bot_name}' from task {latest_task.uuid}: {summary}")

                new_login_status = summary.get("latest_login_status", "Unknown")
                if new_login_status == "success":
                    bot_wise[bot_name]["Current Login Status"] = "Logged In"
                else:
                    bot_wise[bot_name]["Current Login Status"] = new_login_status
            except requests.RequestException as e:
                print(f"RequestException fetching login status for bot '{bot_name}': {e}")
            except Exception as e:
                print(f"Unexpected error updating login status for bot '{bot_name}': {e}")
        return JsonResponse({
            "InputWiseReporting": dict(input_wise),
            "BotWiseReporting": dict(bot_wise),
        })

    elif object_type == "bots":
        summaries = []
        for task_uuid, task_name in task_map.items():
            tasks = Task.objects.filter(uuid=task_uuid)
            if not tasks.exists():
                # Task not found case
                summaries.append({
                    "Bot Name": task_name,
                    "Error": "Task Not Found"
                })
                continue

            for task in tasks:
                try:
                    url = analytics + f"reporting/task-summaries/{task.uuid}/"
                    response = requests.get(url, timeout=10)
                    if response.status_code != 200:
                        summaries.append({
                            "Bot Name": task_name,
                            "Error": "Report Not Found"
                        })
                        continue

                    summary = response.json()
                    if not summary:
                        summaries.append({
                            "Bot Name": task_name,
                            "Error": "Report Not Found"
                        })
                        continue

                    summaries.append({
                        "Bot Name": task_name,
                        "Failed Logins": summary.get("failed_logins", 0),
                        "Total Reports Considered": summary.get("total_reports_considered", 0),
                        "Latest Login Status": summary.get("latest_login_status", ""),
                        "Total Login Time": summary.get("total_login_time", 0.0),
                        "Total Login Attempts": summary.get("total_login_attempts", 0),
                        "Total 2FA Attempts": summary.get("total_2fa_attempts", 0),
                        "Total 2FA Failures": summary.get("total_2fa_failures", 0),
                        "Total 2FA Success": summary.get("total_2fa_successes", 0),
                        "Attempt Failed Reason": summary.get("attempt_failed_errors", []),
                        "Critical Events": [event.get("type") for event in summary.get("critical_events_summary", [])],
                    })
                except requests.RequestException:
                    summaries.append({
                        "Bot Name": task_name,
                        "Error": "Report Not Found"
                    })

        return JsonResponse({
            "Summaries": summaries
        })

    else:
        return JsonResponse({"error": "Unsupported object_type"}, status=400)
    
    
    
    
    
    
    
from django.db import transaction

@csrf_exempt
def update_task_status(request):
    """
    Updates the status of a single bot task based on its UUID.
    This view now exclusively uses 'task_uuid' for identification.
    """
    if request.method != "POST":
        return HttpResponseBadRequest("Only POST method is allowed.")

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON payload."}, status=400)

    task_uuid = data.get("task_uuid")
    status = data.get("status")
    print(status)
    print(f"here is the Task uuid: {task_uuid}")

    if not task_uuid or not status:
        return JsonResponse(
            {"error": "Request must include both 'task_uuid' and 'status'."},
            status=400
        )
    
    if status.lower() not in ['pending', 'resolved']:
        return JsonResponse(
            {"error": "Status must be either 'pending' or 'resolved'."},
            status=400
        )

    tasks_updated = 0
    errors_updated = 0

    try:
        with transaction.atomic():
            if status.lower() == "resolved":
                tasks_updated = Task.objects.filter(uuid=task_uuid).update(status="pending")
            else:
                tasks_updated = Task.objects.filter(uuid=task_uuid).update(status="failed")
            errors_updated = TaskErrorSummary.objects.filter(task_uuid=task_uuid).update(issue_status=status)

            if tasks_updated == 0:
                return JsonResponse(
                    {"error": f"No task found with UUID: {task_uuid}"},
                    status=404
                )
    except Exception as e:
        return JsonResponse({"error": f"A server error occurred: {str(e)}"}, status=500)

    print(tasks_updated)
    # --- Send POST request to reporting server here ---

    # Get reporting server IP
    reporting_server = Server.objects.filter(instance_type="reporting_and_analytics_server").first()
    if reporting_server:
        analytics_base = reporting_server.public_ip
 
        summary_url = analytics_base + "reporting/task-summaries/update/"

        payload = {
            "task_uuid": str(task_uuid),
            "status": status.lower()
        }
        headers = {"Content-Type": "application/json"}

        try:
            response = requests.post(summary_url, headers=headers, data=json.dumps(payload), timeout=10)
            response.raise_for_status()
            print(f"Reported status update to external server: {response.json()}")
        except requests.exceptions.RequestException as e:
            # You may want to log this error properly instead of print
            print(f"Failed to notify reporting server: {e}")

    else:
        print("Reporting server not configured or found.")

    return JsonResponse({
        "message": "Status updated successfully.",
        "task_uuid": task_uuid,
        "tasks_updated_count": tasks_updated,
        "error_summaries_updated_count": errors_updated,
    })