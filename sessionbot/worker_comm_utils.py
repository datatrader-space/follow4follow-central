import uuid
from django.forms import model_to_dict
from sessionbot.models import BulkCampaign, Task
import requests
import json


def communicate_todo_with_worker(todo):
    for bot in todo.bots.all():
        if bot.device == None:
            continue
        else:
            print(bot.device.connected_to_server)
            r = requests.session()
            worker = bot.device.connected_to_server.public_ip
            worker += "crawl/api/workflow/"
            _bot = model_to_dict(bot)
            _bot.pop("created_on", None)
            _bot.pop("cookie", None)
            _bot["device"] = bot.device.__str__()
            b = BulkCampaign.objects.all().filter(childbots=bot)
            if len(b) > 0:
                b = b[0]
                print(b.name)
            else:
                continue
            data = {
                "id": todo.id,
                "name": b.name,
                "service": bot.service,
                "childbots": [_bot],
                "os": "android",
                "activity_to_perform": "feed_post",
                "todo": {
                    "action": "create",
                    "name": todo.name,
                    "media": todo.file.url,
                    "caption": todo.caption,
                    "location": todo.location,
                    "music": todo.music,
                },
            }

        r.post(worker, data=json.dumps(data))


import requests
import uuid


def convert_bulk_campaign_to_worker_tasks(bulk_campaign):
    # print("Processing Bulk Campaign:", bulk_campaign)

    if not bulk_campaign.servers:
        # print("NO SERVER FOUND")
        return

    worker_url = f"{bulk_campaign.servers.public_ip}crawl/tasks/"
    # print(f"Connected server: ID: {bulk_campaign.servers.id}, Public IP: {bulk_campaign.servers.public_ip}")

    scrape_tasks = bulk_campaign.scrape_tasks.all()
    # print("Scrape Tasks:", scrape_tasks)

    _targets = ",".join(scrape_task.input for scrape_task in scrape_tasks)

    if not bulk_campaign.activity_to_perform:
        # print("No activities to perform found.")
        return

    tasks = []  # This will hold all the task dictionaries to send

    from django.forms import model_to_dict
    import uuid
    automation_task=bulk_campaign
    print(bulk_campaign.childbots)
    scrape_tasks=automation_task.scrape_tasks.all()
    _targets=[]
    jobs=[]
    for scrape_task in scrape_tasks:
        _targets.append(scrape_task.input)
    _targets=','.join(_targets)
  

    for i,activity in enumerate(automation_task.activity_to_perform):
        task={'service':automation_task.service,
          'ref_id':automation_task.id,
          'os':automation_task.os
                        
        }
        
        if not activity.get('end_point'):
            print(activity)
            continue
        repeat=False
        repeat_duration=None
        inp=activity['Page']
        if inp.get('repeat_after'):
            repeat=True
            repeat_duration=str(inp.get('repeat_after'))+'h'
            inp.pop('repeat_after')
         
        task.update({'end_point':inp['end_point'],'data_point':inp['data_point']})  
        inp.pop('end_point')
        inp.pop('data_point')
        task.update({'add_data':inp})
        
        if task['data_point']=='search_user_and_interact':
            task.update({'targets':_targets})
            task['add_data'].update({'messaging':automation_task.messaging.all().values_list(flat=True)})
        if task['data_point']=='bulk_task':
            
            activity_to_perform=inp['activity_to_perform'].split(',')
            print(activity_to_perform)
            for act in activity_to_perform:
                print(activity)
                if act=='follow':
                    t=task.copy()
                    t['data_point']='search_user_and_interact'
                    t['bulkaction']=True
                    t['targets']=inp['target_profile']
                    t['os']=inp['os']
                    t['activity_to_perform']='follow'
                    task=t
                elif act=='like':
                    t=task.copy()
                    t['data_point']='search_post_and_interact'
                    t['bulkaction']=True
                    t['targets']=inp['target_profile']
                    t['os']=inp['os']
                    t['activity_to_perform']='like'
                    task=t
                elif act=='dm':
                    t=task.copy()
                    t['data_point']='send_dm'
                    t['bulkaction']=True
                    t['targets']=inp['target_profile']
                    t['os']=inp['os']
                    t['activity_to_perform']='like'
                    task=t
                elif act=='share_post_as_story':
                    t=task.copy()
                    t['data_point']='share_post_as_story'
                    t['bulkaction']=True
                    t['targets']=inp['target_profile']
                    t['os']=inp['os']
                    t['activity_to_perform']='like'
                    task=t

        
                        
                        
                            

            
    
             

        if repeat:
            task.update({'repeat':True,'repeat_duration':repeat_duration})
        jobs.append(task)


    
     

    
    if automation_task.monitor:
        for monitor_dict in automation_task.monitor:
          
            for event in monitor_dict['onEvent']:
                if event['event']=='on_new_post':
                    condition='has_new_post'
                    for username in monitor_dict['usernames'].split(','):
                        exstn_task=Task.objects.all().filter(end_point=monitor_dict['type'],data_point='condition_handler',condition=condition,input=username,ref_id=automation_task.id)
                        if len(exstn_task)>=1:
                            monitor_task=exstn_task[0]
                        else:
                            
                            task={'service':automation_task.service,
                                'interact':False,
                                'end_point':monitor_dict['type'],
                                'data_point':'condition_handler',
                                'condition':condition,
                                'os':'browser',
                                'input':username,
                                'repeat':True if event['monitor_after'] else False,
                                'repeat_duration':event['monitor_after'],
                                'uuid':str(uuid.uuid1()),
                                'ref_id':automation_task.id
                            }
                            monitor_task=Task(**task)
                            monitor_task.save()
                        share_latest_post_as_story=False
                        if event['share_as_story']:
                            share_latest_post_as_story=True
                        like=False
                        if event['like']:
                            like=True
                        comment=False
                        if event.get('comment'):
                            comment=event.get('comments')
                        task={'service':automation_task.service,
                            'interact':False,
                            'end_point':'interact',
                            'data_point':'search_user_and_interact',                               
                            'os':'android',                              
                            'repeat':False,
                            'repeat_duration':event['monitor_after'],
                            'uuid':str(uuid.uuid1()),
                            'add_data':{'messaging':{'type':'reachout_message','values':[]},
                                        'follow':True,
                                        'open_latest_post':True,
                                        'share_latest_post_as_story':share_latest_post_as_story,
                                        'like':like,
                                        'comment':comment

                                        },
                            'dependent_on_id':monitor_task.id,                               
                            'targets':{'type':'user','username':username},
                            'ref_id':automation_task.id,
                            'status':'completed',
                        }
                        jobs.append(task)
                        
    tasks=[]
    from sessionbot.models import ChildBot
    print(bulk_campaign.id)
    print(ChildBot.objects.all().filter(campaign=bulk_campaign))
    print('no')
    for bot in automation_task.childbots.all():
        for job in jobs:
            print('**')
            """             exstn_tasks=Task.objects.all().filter(ref_id=automation_task.id).filter(end_point='interact').filter(data_point=job['data_point']).filter(profile=bot.username).filter(add_data=task['add_data'])
            if len(exstn_tasks)>0:
                if task.get('dependent_on_id'):
                    if exstn_tasks.filter(dependent_on=task['dependent_on_id']):
                        continue
                else:
                    continue
            """
            """             if job['data_point']=='search_user_and_interact':
                if not _targets:
                    dup_check=exstn_tasks.filter(targets='')
                else:
                    dup_check=exstn_tasks.filter(targets=_targets)
                if len(dup_check)>0:
                    
                    print('Excluding Duplicate Task Creation')
                    continue
            else: 
                if len(exstn_tasks)>0:
                    continue"""
            import uuid
            job.update({'profile':bot.username,'uuid':str(uuid.uuid1()),})
            tasks.append(job)
            print(tasks)
    return tasks

def communicate_bulk_campaign_update_with(bulkcampaign):

    # print('MODEL TO DICT: ', model_to_dict(bulkcampaign))
    r = requests.session()
    workers = []

    bots = []
    devices = []
    tasks = convert_bulk_campaign_to_worker_tasks(bulkcampaign)
    print('yeah')
    # print('CONVERTING AUTOMATION TASK TO WORKER TASK: ', tasks)

    for bot in bulkcampaign.childbots.all():

        if bulkcampaign.os == "android":

            if bot.device == None:

                continue
        # print(bot.device)
        _bot = model_to_dict(bot)
        _bot.pop("created_on", None)
        _bot.pop("cookie")
        _bot["device"] = bot.device.__str__()
    # print(bots)
    if bulkcampaign.os == "android":
        for device in bulkcampaign.devices.all():
            device = model_to_dict(device)
            profiles = []
            for profile in device["profiles"]:
                profile = model_to_dict(profile)
                profile.pop("created_on")
                profile.pop("cookie")
                profiles.append(profile)

            device["profiles"] = profiles
            devices.append(device)
    scrape_tasks = []
    for task in bulkcampaign.scrape_tasks.all():
        # bots=[]
        scrape_task = model_to_dict(task)
        _ = []
        for bot in scrape_task["childbots"]:
            bot = model_to_dict(bot)
            bot.pop("created_on")
            bot.pop("cookie")
            _.append(bot)
        scrape_task["childbots"] = bots
        scrape_tasks.append(scrape_task)

    messaging = []
    for messag in bulkcampaign.messaging.all():
        messaging.append(model_to_dict(messag))
    sharing = []
    for shar in bulkcampaign.sharing.all():
        sharing.append(model_to_dict(shar))
    settings = []
    proxies = bulkcampaign.proxies.all()
    data = {
        "action": "create",
        "id": bulkcampaign.id,
        "name": bulkcampaign.name,
        "service": bulkcampaign.service,
        "activity_to_perform": bulkcampaign.activity_to_perform,
        "os": bulkcampaign.os,
        "proxy_disable": bulkcampaign.proxy_disable,
        "blacklist": "",
        "required_interactions": 10000,
        "launch_datetime": None,
        "stop_datetime": None,
        "internal_state": "active",
        "campaign_state": "launched",
        "is_completed": False,
        "is_deleted": False,
        "media_id": None,
        "comment_id": None,
        "childbots": bots,
        "devices": devices,
        "scrape_tasks": scrape_tasks,
        "messaging": messaging,
        "sharing": sharing,
    }
    worker_url = f"{bulkcampaign.servers.public_ip}"
    worker_tasks_url=worker_url+'/crawl/api/tasks'
    worker_devices_url=worker_url+'/crawl/devices/'
    worker_bots_url=worker_url+'/crawl/childbots/'
    print(tasks)
    print(worker_url)
    r.post(worker_devices_url,data=json.dumps(tasks))
    r.post(worker_bots_url,data=json.dumps(bots))
    

    r.post(worker_tasks_url,data=json.dumps(tasks))
