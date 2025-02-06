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
from .models import DataHouseSyncStatus,ChildBot
@shared_task()
def sync_with_data_house_and_workers():
    """
    Celery task to sync with Data House and Workers (Data House is default).
    """

    data_house_url = getattr(settings, "DATA_HOUSE_URL", None)
    data_house_url+='datahouse/api/sync/'
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
                    print(model_class)
                    model_instance = model_class.objects.get(uuid=object_id)
                    if not model_instance:
                        status.delete()
                        continue
                    object_body = model_instance.__dict__.copy()
                    if '_state' in object_body:
                        del object_body['_state']

                    for key, value in object_body.items():
                        if isinstance(value, models.Model):
                            object_body[key] = str(value)
                        elif isinstance(value, datetime):
                            object_body[key] = value.isoformat()
                        elif isinstance(value, uuid.UUID):
                            object_body[key] = str(value)
                        elif isinstance(value, bool):
                            object_body[key] = str(value).lower()

                except model_class.DoesNotExist:
                    object_body = None
                    model_instance = None
                    continue
                except Exception as e:
                    print(f"Error retrieving object {object_id}: {e}")
                    object_body = None
                    model_instance = None
                    continue
                if (len(statuses)-i)>1:
                   
                    status.delete()
            print(i)
            print(status.id)
            
            if not model_instance and not final_operation=='DELETE':
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
    print(target_payloads)
    for target_url, payloads in target_payloads.items():
        print(target_url)
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
    unregistered_tasks=Task.objects.all()
    delete_tasks=Task.objects.all().filter(_delete=True)
    
    unregistered_task=unregistered_tasks.union(delete_tasks)
    print(unregistered_task)
    _={}
    for task in unregistered_task:
        
   
        if task.server.public_ip in _.keys():
            pass
        else:
            _.update({task.server.public_ip:{'tasks':[],'resources':{'devices':[],'bots':[]}}})
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
    print('sent request to worker at'+str(dt.datetime.now()))
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

