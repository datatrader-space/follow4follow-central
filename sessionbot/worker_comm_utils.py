import uuid
from django.forms import model_to_dict
from sessionbot.models import BulkCampaign, Device, Task,ScrapeTask
import requests
import json
from sessionbot.models import Logs

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
    print("Processing Bulk Campaign:", bulk_campaign)

    if not bulk_campaign.servers:
        print("NO SERVER FOUND")
        return

    worker_url = f"{bulk_campaign.servers.public_ip}crawl/tasks/"
    print(f"Connected server: ID: {bulk_campaign.servers.id}, Public IP: {bulk_campaign.servers.public_ip}")

    scrape_tasks = bulk_campaign.scrape_tasks.all()
    _targets = ",".join(scrape_task.input for scrape_task in scrape_tasks)
    print("Targets:", _targets)

    if not bulk_campaign.activity_to_perform:
        print("No activities to perform found.")
        

    tasks = []  # This will hold all the task dictionaries to send

    from django.forms import model_to_dict
    import uuid
    automation_task=bulk_campaign
   
    scrape_tasks=automation_task.scrape_tasks.all()
    _targets=[]
    jobs=[]
    for scrape_task in scrape_tasks:
        _targets.append(scrape_task.input)
    _targets=','.join(_targets)
  
    acts=automation_task.activity_to_perform

    print("Activities to Performed", acts)
    
    for activity in acts:
        end_point = activity.get('Page',{}).get('end_point')
        print(f"Processing Activity with End_Point: {end_point}")
        
        #print(activity['Page'].get('end_point'))
        #task={}
        task={'service':automation_task.service,
          'ref_id':automation_task.id,
          'os':automation_task.os,
                        
        }

        #if not activity['Page'].get('end_point'):
        if not end_point:
            print('no endpoint specified for activity, skipping.')
           
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
            task['add_data'].update({'messaging':list(automation_task.messaging.all().values())})
        if task['data_point']=='bulk_task':
            #print('bulk task')
            activity_to_perform=inp['activity_to_perform'].split(',')
            #print(activity_to_perform)
            for act in activity_to_perform:
                
                if act=='follow':
                    t=task.copy()
                    t['data_point']='search_user_and_interact'
                    
                    t['targets']=inp['target_profile']
                    t['os']=inp['os']
                    t['activity_to_perform']='follow'
                    task=t
                elif act=='like':
                    t=task.copy()
                    t['data_point']='search_post_and_interact'
                    
                    t['targets']=inp['target_profile']
                    t['os']=inp['os']
                    t['activity_to_perform']='like'
                    task=t
                elif act=='dm':
                    t=task.copy()
                    t['data_point']='send_dm'
                    
                    t['targets']=inp['target_profile']
                    t['os']=inp['os']
                    t['activity_to_perform']='like'
                    task=t
                elif act=='share_post_as_story':
                    t=task.copy()
                    t['data_point']='share_post_as_story'
                
                    t['targets']=inp['target_profile']
                    t['os']=inp['os']
                    t['activity_to_perform']='like'
                    task=t

        
                        
                        
                            

            
    
             

        if repeat:
            task.update({'repeat':True,'repeat_duration':repeat_duration})
      
        jobs.append(task)
        

    
     

    print(model_to_dict(automation_task))
    if automation_task.monitor:

        for monitor_dict in automation_task.monitor:
            print(monitor_dict)
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
                                'ref_id':automation_task.id,
                                'server_id':automation_task.servers.id

                            }
                            alloted_bots=[]
                            for bot in automation_task.childbots.all():
                                alloted_bots.append(bot.username)
                            task.update({'alloted_bots':','.join(alloted_bots)})
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
                        _={'service':automation_task.service,
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
                        jobs.append(_)
                        
    tasks=[]
    
    from sessionbot.models import ChildBot
   
  
    for bot in automation_task.childbots.all():
        if not bot.logged_in_on_servers:
            l=Logs(end_point='bulkcampaign',label='INFO',message=bot.username+' doesnt have a server assigned. Ignoring the bot, please assign server to the bot, and edit/save bulkcampaign '+str(automation_task.name) +' again')
            l.save()
            continue
        for job in jobs:
            _={}
            exstn_tasks=Task.objects.all().filter(ref_id=automation_task.id).filter(end_point='interact').filter(data_point=job['data_point']).filter(profile=bot.username).filter(add_data=job.get('add_data',{}))
            if len(exstn_tasks)>0:
                print('found extn task')
                if job.get('dependent_on_id'):
                    if exstn_tasks.filter(dependent_on=job['dependent_on_id']):
                        exstn_tasks.update(repeat=job['repeat'])
                        exstn_tasks.update(repeat_duration=job['repeat_duration'])
                        exstn_tasks.update(registered=False)
                else:
                    exstn_tasks.update(repeat=job['repeat'])
                    exstn_tasks.update(repeat_duration=job['repeat_duration'])
                    exstn_tasks.update(registered=False)

                    print('passed duplicate ')
                    continue

            if job['data_point']=='search_user_and_interact':
                if not _targets:
                    dup_check=exstn_tasks.filter(targets='')
                else:
                    dup_check=exstn_tasks.filter(targets=_targets)
                if len(dup_check)>0:
                    
                    print('Excluding Duplicate Task Creation')
                    continue
            else:
                if len(exstn_tasks)>0:
                    continue

            job.update({'profile':bot.username,'device':bot.device.serial_number if bot.device else False,'uuid':str(uuid.uuid1()),'server':bot.logged_in_on_servers})
            
            t=Task(**job)
            t.save()
            _=job.copy()
            _.update({'uuid':t.uuid})
            tasks.append(_)

    print("Final Task Generated: ", tasks)
             
    
    return tasks
def communicate_bulk_campaign_update_with(bulkcampaign):

    #print('MODEL TO DICT: ', model_to_dict(bulkcampaign))
    r = requests.session()
    workers = []

    bots = []
    devices = []
    tasks = convert_bulk_campaign_to_worker_tasks(bulkcampaign)
    #print(tasks)
    #print('CONVERTING AUTOMATION TASK TO WORKER TASK: ', tasks)

    for bot in bulkcampaign.childbots.all():
        
        if bulkcampaign.os == "android":

            if bot.device == None:

                continue
        # print(bot.device)
        _bot = model_to_dict(bot)
        _bot.pop("created_on", None)
        _bot.pop("cookie")
        _bot.pop("profile_picture")
        _bot.pop("dob")
        _bot.pop('followers')
        _bot.pop('following')
        _bot.pop('post_count')
        _bot.pop('first_name')
        _bot.pop('last_name')
        _bot.pop('state')
        _bot.pop('challenged')
        _bot.pop('logged_in_on_servers')
        _bot.pop('customer')
        _bot.pop('bio')
        _bot["device"] = bot.device.serial_number if bot.device else False
        _bot.pop('email_provider')
        _bot.pop('id')
        bots.append(_bot)
    if bulkcampaign.os == "android":
        for device in bulkcampaign.devices.all():
            device_data = model_to_dict(device)

            connected_to_server = device_data.pop('connected_to_server', None)
            profiles = []


            devices.append(device_data)

            for device in devices:
                serial_number = device.get('serial_number')
                if serial_number:
                    Device.objects.update_or_create(
                        serial_number=serial_number,
                        defaults=device
                    )
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



    worker_url = f"{bulkcampaign.servers.public_ip}"
    worker_tasks_url=worker_url+'crawl/api/tasks/'
    resources_url=worker_url+'crawl/api/resources/'
    print("WORKER_URL: ", worker_tasks_url)   
    
    
