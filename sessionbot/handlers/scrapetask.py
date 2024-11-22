from sessionbot.models import ScrapeTask,Logs,Task
import uuid
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
    st_tasks=Task.objects.all().filter(ref_id=scrapetask.id).filter(service=scrapetask.service).filter(end_point=end_point)
    unregistered_tasks=st_tasks.filter(registered=False)
    unregistered_tasks.delete()
    registered_tasks=st_tasks.filter(registered=True)
    registered_tasks.update(delete=True)
    l=Logs(message='Deleted '+str(len(unregistered_tasks))+' UnRegistered Tasks for '+scrapetask.name,label='INFO',end_point='scrapetask')
    l.save()        
    l=Logs(message='Queued '+str(len(registered_tasks))+' Registered Tasks  to Delete for '+scrapetask.name,label='INFO',end_point='scrapetask')
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
                data_point='keyword'
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
                'input':input.split('__')[1],
                'repeat':True,
                'repeat_duration':'1h',
                'add_data':{
                'max_threads':scrapetask.max_threads,
                'max_requests_per_day':scrapetask.max_requests_per_day 
                },   
                'ref_id':scrapetask.id,
                'paused':False if start_scraping else True,
                 
                            }

            tasks.append(task)
       
    alloted_bots=scrapetask.childbots.all()
    _=[]
    for bot in alloted_bots:
        _.append(bot.username)
    for task in tasks:
        for bot in alloted_bots:
            if not bot.logged_in_on_servers:
                l=Logs(end_point='scrapetask',label='INFO',message=bot.username+' doesnt have a server assigned. Ignoring the bot, please assign server to the bot, and edit/save scrapetask '+str(scrapetask.name) +' again')
                l.save()
            else:
                dup_check=Task.objects.all().filter(end_point=end_point).filter(data_point=data_point).filter(input=input).filter(profile=bot.username)
            
                if len(dup_check)>0:
                    message='Excluding Duplicate Scrape Task Creation.Data: ' +str(task)
                    l=Logs(end_point='scrapetask',label='INFO',message=message)
                    l.save()
                    
                    continue
                else:
                    task.update({'os':'browser','profile':bot.username,'uuid':str(uuid.uuid1()),'server_id':bot.logged_in_on_servers.id,'registered':False})
                    t=Task(**task)
                    t.save()
                    message='Successfully Created a scraping task for '+str(data_point)+' for '+str(bot.username)
                    l=Logs(end_point='scrapetask',label='INFO',message=message)
                    l.save()
                    print(task)
            

def handle_scrapetask_state_change(scrapetask,state=False):
    from sessionbot.models import Task, Logs
    if 'user' in scrapetask.input:
        end_point='user'
    elif 'location' in scrapetask.input:
        end_point='location'
    elif 'hashtag' in scrapetask.input:
        end_point='hashtag'
    elif 'keyword' in scrapetask.input:
        end_point='search'
    st_tasks=Task.objects.all().filter(ref_id=scrapetask.id).filter(service=scrapetask.service).filter(end_point=end_point)
    if state and state=='start':
        st_tasks.update(state='pending')
        st_tasks.update(paused=False)
        l=Logs(message='Changed State to Pending for '+str(len(st_tasks))+' Tasks for scrapetask '+scrapetask.name,label='INFO',end_point='scrapetask')
        l.save()  
    if state and state=='start':
        st_tasks.update(state='stop')
        st_tasks.update(paused=False)
        l=Logs(message='Changed State to Paused/Stopped for '+str(len(st_tasks))+' Tasks for scrapetask '+scrapetask.name,label='INFO',end_point='scrapetask')
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