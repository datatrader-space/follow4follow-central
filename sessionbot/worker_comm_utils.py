from django.forms import model_to_dict
from sessionbot.models import BulkCampaign
import requests
import json
def communicate_todo_with_worker(todo):
    for bot in todo.bots.all():    
        if bot.device==None:       
            continue
        else:
            print(bot.device.connected_to_server)
            r=requests.session()
            worker=bot.device.connected_to_server.public_ip
            worker+='crawl/api/workflow/'
            _bot=model_to_dict(bot)
            _bot.pop('created_on')
            _bot.pop('cookie')
            _bot['device']=bot.device.__str__()
            b=BulkCampaign.objects.all().filter(childbots=bot)
            if len(b)>0:
                b=b[0]
                print(b.name)
            else:
                continue
            data={'id': todo.id,'name':b.name,'service': bot.service,'childbots':[_bot],'os':'android','activity_to_perform':'feed_post',
                  'todo':{'action':'create', 'name': todo.name, 
            'media':todo.file.url,
            'caption':todo.caption,'location':todo.location, 
            'music':todo.music}
            }
                    
        r.post(worker,data=json.dumps(data))
def communicate_bulk_campaign_update_with(bulkcampaign):
    print(model_to_dict(bulkcampaign))
    r=requests.session()
    worker=bulkcampaign.server.public_ip
    worker+='crawl/api/workflow/'
    print(worker)
    print()
    bots=[]
    for bot in bulkcampaign.childbots.all():
        print
        if bulkcampaign.os=='android':
     
             if bot.device==None:
                
                continue
        print(bot.device)
        _bot=model_to_dict(bot)
        _bot.pop('created_on')
        _bot.pop('cookie')
        _bot['device']=bot.device.__str__()
        bots.append(_bot)
    print(bots)
    devices=[]
    for device in bulkcampaign.devices.all():
        device=(model_to_dict(device))
        """ profiles=[]
        for profile in device['profiles']:
            profile=(model_to_dict(profile))
            profile.pop('created_on')
            profile.pop('cookie')
            profiles.append(profile)

        device['profiles']=profiles """
        devices.append(device)
    scrape_tasks=[]
    for task in bulkcampaign.scrape_tasks.all():
        #bots=[]
        scrape_task=model_to_dict(task)
        _=[]
        for bot in scrape_task['childbots']:
            bot=model_to_dict(bot)
            bot.pop('created_on')
            bot.pop('cookie')
            _.append(bot)
        scrape_task['childbots']=bots
        scrape_tasks.append(scrape_task)


    messaging=[]
    for messag in bulkcampaign.messaging.all():
        messaging.append(model_to_dict(messag))
    sharing=[]
    for shar in bulkcampaign.sharing.all():
        sharing.append(model_to_dict(shar))
    settings=[]
    for sett in bulkcampaign.settings.all():
        sett=(model_to_dict(sett))
        sett.pop('created_on')
        settings.append(sett)
    data={'action':'create','id': bulkcampaign.id, 'name': bulkcampaign.name, 
    'service': bulkcampaign.service, 'customer': bulkcampaign.customer.user.id, 'activity_to_perform': bulkcampaign.activity_to_perform, 
    'os': bulkcampaign.os, 'localstore': bulkcampaign.localstore, 'proxy_disable': bulkcampaign.proxy_disable,  'blacklist': '', 
    'required_interactions': 10000, 'launch_datetime': None, 'stop_datetime': None,
   'internal_state': 'active', 'campaign_state': 'launched', 'is_completed': False,
     'is_deleted': False, 'media_id': None, 'comment_id': None, 'childbots':bots,
     'devices':devices,'scrape_tasks':scrape_tasks,'messaging':messaging,
     'sharing':sharing,'settings':settings}


    print(data)                       
    r.post(worker,data=json.dumps(data))
    
   