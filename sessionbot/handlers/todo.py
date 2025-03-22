def handle_todo_creation(todo):
    from sessionbot.models import Task,Log
    import uuid
    for bot in todo.childbots.all():
        if not bot.logged_in_on_servers:
                l=Log(end_point='todo',label='INFO',message=bot.username+' doesnt have a server assigned. Ignoring the bot, please assign server to the bot, and edit/save Todo'+str(todo.name) +' again')
                l.save()
                continue
        elif not bot.device:
            l=Log(end_point='todo',label='INFO',message=bot.username+' doesnt have a device assigned. Ignoring the bot, please assign server to the bot, and edit/save Todo'+str(todo.name) +' again')
            l.save()
            
            continue
        task={'ref_id': todo.id,'service': bot.service,'profile':bot.username,'os':'android','end_point':'interact','data_point':'feed_post',             
                    'add_data':{ 
                    'caption':todo.caption,#'location':todo.location, 
                    'google_drive_root_folder_name':todo.google_drive_root_folder_name,
                    'music':todo.music,
                },
                'device': bot.device.serial_number if bot.device else False,
                'server_id':bot.logged_in_on_servers.id,
                'uuid':str(uuid.uuid1())
                }   
        exstn_tasks=Task.objects.all().filter(service=bot.service).filter(profile=bot.username).filter(end_point='interact').filter(data_point='feed_post')
        
        add_data=task.get('add_data',{})
       
        if todo.target_location:
            location=todo.target_location
            add_data['target_location'].update({'city_info':{'id':location['city_id']},'country_info':{'slug':location['country_slug']}})
       
        task.update({'add_data':add_data})      
        
        if todo.repeat:
            if todo.repeat_after:
                repeat_duration=todo.repeat_after*60*60
                task.update({'repeat':True,'repeat_duration':repeat_duration})
        t=Task(**task)
        t.save()
        l=Log(message='Successfully created task for Todo. Data: '+str(task),end_point='todo',label='INFO')
        l.save()

def handle_todo_deletion(todo):
    from sessionbot.models import Task,Log
    st_tasks=Task.objects.all().filter(ref_id=todo.id).filter(service='instagram').filter(end_point='interact').filter(data_point='feed_post')
    unregistered_tasks=st_tasks.filter(registered=False)
    unregistered_tasks.delete()
    registered_tasks=st_tasks.filter(registered=True)
    registered_tasks.update(_delete=True)
    l=Log(message='Deleted '+str(len(unregistered_tasks))+' UnRegistered Tasks for '+todo.name,label='INFO',end_point='todo')
    l.save()        
    l=Log(message='Queued '+str(len(registered_tasks))+' Registered Tasks  to Delete for '+todo.name,label='INFO',end_point='todo')
    l.save()
    todo.delete()

def handle_todo_state_change(todo,state=False):
    from sessionbot.models import Task, Log
    st_tasks=Task.objects.all().filter(ref_id=todo.id).filter(service=todo.service).filter(end_point='interact').filter(data_point='feed_post')
    if state and state=='start':
        st_tasks.update(state='pending')
        st_tasks.update(paused=False)
        l=Log(message='Changed State to Pending for '+str(len(st_tasks))+' Tasks for Todo '+todo.name,label='INFO',end_point='todo')
        l.save()  
    if state and state=='start':
        st_tasks.update(state='stop')
        st_tasks.update(paused=False)
        l=Log(message='Changed State to Paused/Stopped for '+str(len(st_tasks))+' Tasks for Todo '+todo.name,label='INFO',end_point='todo')
        l.save()        