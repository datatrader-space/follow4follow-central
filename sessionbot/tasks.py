from celery import chain, shared_task
from sessionbot.models import Task,ChildBot

@shared_task()
def communicate_tasks_with_worker():
    import json
    import requests as r
    from django.forms import model_to_dict
    unregistered_tasks=Task.objects.all().filter(registered=False)
    delete_tasks=Task.objects.all().filter(delete=True)
    print(delete_tasks)
    unregistered_task=unregistered_tasks.union(delete_tasks)
    print(unregistered_task)
    _={}
    for task in unregistered_task:
        
   
        if task.server.public_ip in _.keys():
            pass
        else:
            _.update({task.server.public_ip:{'tasks':[],'resources':{'devices':[],'bots':[]}}})
        if task.delete:
            method='delete'
        else:
            method='create'
        active_dict=_[task.server.public_ip]
        _task=model_to_dict(task)
        if task.dependent_on:        
            _task.update({'dependent_on':task.dependent_on.uuid})
        _task.update({'method':method})
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
        print(resp)
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