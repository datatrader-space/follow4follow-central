from sessionbot.models import ScrapeTask,Log,Task,Server
import uuid
from django.conf import settings
def handle_scrape_task(scrapetask,event='created',form={}):

    if event=='created': 
        handle_scrape_task_creation(scrapetask,start_scraping=True)
    if event =='deleted':
        handle_scrape_task_deletion(scrapetask)

def handle_scrape_task_deletion(scrapetask):
    if 'user' in scrapetask.input:
        end_point='user'
    elif 'location' in scrapetask.input:
        end_point='location'
    elif 'hashtag' in scrapetask.input:
        end_point='hashtag'
    elif 'keyword' in scrapetask.input:
        end_point='search'
    st_tasks=Task.objects.all().filter(ref_id=scrapetask.uuid)
    unregistered_tasks=st_tasks.filter(registered=False)
    unregistered_tasks.delete()
    registered_tasks=st_tasks.filter(registered=True)
    registered_tasks.update(_delete=True)
    l=Log(message='Deleted '+str(len(unregistered_tasks))+' UnRegistered Tasks for '+scrapetask.name,label='INFO',end_point='scrapetask')
    l.save()        
    l=Log(message='Queued '+str(len(registered_tasks))+' Registered Tasks  to Delete for '+scrapetask.name,label='INFO',end_point='scrapetask')
    l.save()
    scrapetask.delete()
def handle_scrape_task_creation(scrapetask,start_scraping=True):

    tasks=[]
    for input in scrapetask.input.split(','):
            if 'location' in input:
                end_point='location'
                if 'posts' in input:
                    data_point='location_posts'
            elif 'follower' in input:
                end_point='user'
                data_point='user_followers'
                print(data_point)
            elif 'marketplace' in input:
                end_point='marketplace'
                data_point='search'
            elif 'keyword' in input or 'keywords' in input:
                end_point='search'
                data_point='search_keyword'
            elif 'hashtag' in input:
                end_point='hashtag'
                data_point='hastag_posts'
            else:
                continue
            task={'service':scrapetask.service,
                'interact':False,
                'end_point':end_point,
                'data_point':data_point,
                'os':scrapetask.os,
                'input':input.split('__')[1].strip(),
                'repeat':True,
                'repeat_duration':'1h',
                'add_data':{
                'max_threads':int(scrapetask.max_threads),
                'max_requests_per_bot':scrapetask.max_requests_per_day,
                'max_requests_per_day':200,
                'max_requests_per_run':5,
                'save_to_storage_house':True,
               
                },   
                'ref_id':scrapetask.uuid,
                'paused':False if start_scraping else True,
                 
                            }
            
           
                    


            tasks.append(task)
            
    print(data_point)
    print(end_point)
    
    alloted_bots=scrapetask.childbots.all()
    _=[]
    for bot in alloted_bots:
        _.append(bot.username)
    for task in tasks:
        for bot in alloted_bots:
            print(bot.username)
            if not bot.logged_in_on_servers:
                l=Log(end_point='scrapetask',label='INFO',message=bot.username+' doesnt have a server assigned. Ignoring the bot, please assign server to the bot, and edit/save scrapetask '+str(scrapetask.name) +' again')
                l.save()
            else:
                t=Task.objects.all().filter(end_point=end_point).filter(data_point=data_point).filter(input=task['input']).filter(profile=bot.username)
            
                if len(t)>0:
                    message='Excluding Duplicate Scrape Task Creation.Data: ' +str(task)
                    l=Log(end_point='scrapetask',label='INFO',message=message)
                    l.save()
                    t=t[0]
                    

                else:
                    task.update({'os':'browser','profile':bot.username,'uuid':str(uuid.uuid1()),'server_id':bot.logged_in_on_servers.id,'registered':False})
                    t=Task(**task)
                    t.save()
                add_data=task['add_data']
                reporting_house_server=Server.objects.all().filter(instance_type='reporting_and_analytics_server')
                if reporting_house_server:
                    reporting_house_server=reporting_house_server[0]
                    reporting_house_url=reporting_house_server.public_ip+'reporting/task-reports'
                    add_data.update({'reporting_house_url':reporting_house_url})
                datahouse_server=Server.objects.all().filter(instance_type='data_server')
                if datahouse_server:
                    datahouse_server=datahouse_server[0]
                    datahouse_url=datahouse_server.public_ip+'datahouse/api/consume/'
                    add_data.update({'datahouse_blocks':["users","posts"],"datahouse_url":datahouse_url})
                t.add_data=add_data
                t.save()

                message='Successfully Created a scraping task for '+str(data_point)+' for '+str(bot.username)
                l=Log(end_point='scrapetask',label='INFO',message=message)
                l.save()
                print(task)
                
            

def handle_scrapetask_state_change(scrapetask,state=False):
    from sessionbot.models import Task, Log
    if 'user' in scrapetask.input:
        end_point='user'
    elif 'location' in scrapetask.input:
        end_point='location'
    elif 'hashtag' in scrapetask.input:
        end_point='hashtag'
    elif 'keyword' in scrapetask.input:
        end_point='search'
    st_tasks=Task.objects.all().filter(ref_id=scrapetask.uuid).filter(service=scrapetask.service).filter(end_point=end_point)
    if state and state=='start':
        st_tasks.update(state='pending')
        st_tasks.update(paused=False)
        l=Log(message='Changed State to Pending for '+str(len(st_tasks))+' Tasks for scrapetask '+scrapetask.name,label='INFO',end_point='scrapetask')
        l.save()  
    if state and state=='start':
        st_tasks.update(state='stop')
        st_tasks.update(paused=False)
        l=Log(message='Changed State to Paused/Stopped for '+str(len(st_tasks))+' Tasks for scrapetask '+scrapetask.name,label='INFO',end_point='scrapetask')
        l.save()  
def handle_scrapetask_form_from_frontend(task):
    inputs=[]
    _={'service':'instagram','name':task.get('name'),'max_threads':task.get('max_threads'),'max_requests_per_day':task.get('max_requests_per_day')}
                        
    scrape_value = task.get('scrape_value')
    if task['scrape_type']=='by_location':
        for value in scrape_value.split(','):
            inputs.append('location_posts__'+str(value))
    if task['scrape_type']=='by_username':
        for value in scrape_value.split(','):
            inputs.append('user_followers__'+value)

    if task['scrape_type']=='by_hashtag':
        for value in scrape_value.split(','):
            inputs.append('hashtag__'+value)
    if task['scrape_type']=='by_keyword':
        for value in scrape_value.split(','):
            inputs.append('keyword__'+value)
    _.update({'input':','.join(inputs)
                })
    return _


def handle_filter_creation_for_scrapetask(scrapetask):
    filters={}
    input='someval__location__posts','someval__user_followers','someval__'
    location_ids=[]
    usernames=[]
    keywords=[]
    print(scrapetask)
    for input in scrapetask.input.split(','):
            print(input)
            if 'location' in input:
                end_point='location'
                if 'posts' in input:
                    data_point='location_posts'
                    filters['posts__location__rest_id.in']=[]
                
                location_ids.append(input.split('__')[1])
            elif 'follower' in input:
                end_point='user'
                data_point='user_followers'
                usernames.append(input.split('__')[1])
            elif 'marketplace' in input:
                end_point='marketplace'
                data_point='search'
            elif 'keyword' in input or 'keywords' in input:
                end_point='search'
                data_point='search_keyword'
                keywords.append(input.split('__')[1])
            elif 'hashtag' in input:
                end_point='hashtag'
                data_point='hastag_posts'
                keywords.append(input.split('__')[1])
            else:
                continue
            

    if location_ids:
        filters['posts__location__rest_id.in']=location_ids
    if usernames:
        filters['following__following__username.in']=usernames
    if keywords:
        filters['posts__text__content.contains']=keywords
    print(filters)    
    return filters