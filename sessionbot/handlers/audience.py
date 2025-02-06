import uuid
def handle_audience_deletion(a):
    from sessionbot.models import Task, Log
    st_tasks=Task.objects.all().filter(ref_id=a.uuid)
    unregistered_tasks=st_tasks.filter(registered=False)
    unregistered_tasks.delete()
    registered_tasks=st_tasks.filter(registered=True)
    registered_tasks.update(delete=True)
    l=Log(message='Deleted '+str(len(unregistered_tasks))+' UnRegistered Tasks for '+a.name,label='INFO',end_point='audience')
    l.save()        
    l=Log(message='Queued '+str(len(registered_tasks))+' Registered Tasks  to Delete for '+a.name,label='INFO',end_point='audience')
    l.save()
    a.delete()
def handle_audience_creation(a,payload):
    from sessionbot.models import Audience,ScrapeTask,Task,Log
    import uuid
    scrape_tasks=[]
    name=payload.get('name')
    scrape_tasks=[]
    print(name)
    print(payload)
    logs=[]
    for id in payload.get('scrapetask',[]):
        print(id)
        s=ScrapeTask.objects.all().filter(id=id)            
        if len(s)>0:
            s=s[0]
            scrape_tasks.append(s)
            if 'followers' in s.input:
                data_point='user_followers'
                end_point='user'
            elif 'keyword' in s.input:
                data_point='search_keyword'
                end_point='search'
            
            tasks_for_scrape_task=Task.objects.all().filter(ref_id=s.uuid)
            print(tasks_for_scrape_task)
            fields_to_compare=[]
            check_for_presence_ofs=[]
            for field_to_compare in payload.get('fields_to_compare',[]):
                    print(field_to_compare.get('value'))
                    if field_to_compare.get('type')=='str' and not field_to_compare.get('value'):
                        _={'key':field_to_compare.get('key'),'value':'str'}
                    elif field_to_compare.get('type')=='int' and field_to_compare.get('value')==None:
                        _={'key':field_to_compare.get('key'),'value':'int'}
                    elif field_to_compare.get('type')=='boolean':
                        _={'key':field_to_compare.get('key'),'value':field_to_compare.get('value')}
                    else:
                        continue
                    fields_to_compare.append(_)
            
            for check_for_presence_of in payload.get('check_for_presence_of',[]):
                _={'key':check_for_presence_of.get('key'),'value':check_for_presence_of.get('value')}
                check_for_presence_ofs.append(_)

        a.cleaning_configuration={'fields_to_compare':payload.get('fields_to_compare'),'check_for_presence_of':payload.get('check_for_presence_of')}
        data_enrichments=payload.get('data_enrichments')
        data_enrichments.update({'ai_Service':payload.get('ai_service')})
        a.enrichment_configuration=data_enrichments

        if payload.get('save_to_googlesheet'):
            storage_configuration={'save_to_googlesheet':True,'google_sheet_url':payload.get('google_sheet_url'),'local':True}
        else:
            storage_configuration={'local':True,'save_to_googlesheet':False}
        a.storage_configuration=storage_configuration
        a.name=name
        a.service=payload.get('service')
        a.uuid=uuid.uuid1()
        a.save()
        a.scrape_tasks.set(scrape_tasks)
        
        for task in tasks_for_scrape_task:
            
            uuids=[]
            """_={'service':'cleaner',
             'ref_id':a.uuid,
            'end_point':'clean',
            'data_point':'clean_data',
            'add_data':{'data_source':[{'type':'task','identifier':task.uuid},
                                        #{'type':'storage_block','identifier':'dancingtheearth','service':'instagram'},
                                        #{'type':'data_point','service':'instagram','identifier':'user_followers','end_point':'user',
                                        # 'input':'dancingtheearth'},
                                        #{'type':'google_sheet','link':'somelink'}                         
                                        ],
                'repeat':True,
                'repeat_duration':'1m',
                'fields_to_compare':fields_to_compare,
                'check_for_presence_of':check_for_presence_ofs,
                'save_to_googlesheet':False#'https:#//docs.google.com/spreadsheets/d/1wTVLDWlmfTTnkrltx1iBUppJ5J_9EBYuCVXa59mhaVM/edit?gid=0#gid=0'
                
                                            

            },
            'repeat':True,
            'repeat_duration':'1m',
            'uuid':str(uuid.uuid1())
            } """

            
            print(a.uuid)
            if a.enrichment_configuration.get('nationalityEnrichment'):
                _={
                    "service": "data_enricher",
                    "ref_id": str(a.uuid),  
                    "end_point": "enrich",
                    "data_point": "enrich",
                    "add_data": {
                        "data_source": [{
                        "type": "data_house",
                        "object_type": "profile",
                        "internal_filters": {
                            "info__gender.isnull": True, #// Example internal filter
                            "info__country.isnull": True, #// Example internal filter
                             #// Example internal filter
                            #// ... more internal filters as needed ...
                        },
                        "external_filters": {
                            "task.equal": str(task.uuid) #// Filter by audience (REQUIRED)
                            #// ... more external filters as needed ...
                        },
                        
                        "lock_results": True #// Signal to lock the results for the audience (REQUIRED)
                        }],
                        'service':'openai',
                        'columns':['name'],
                        'prompt': "For the name {name}, provide the following details:\n" \
                        "1. Type (e.g., Person, Brand, etc.)\n" \
                        "2. Gender (if it's a person's name)\n" \
                        "3. Country of origin or association\n\n\
                        and follow this strictly."\
                        "Try to provide the details based on their names and also don't focus on any special characters or icons in the name"\
                        "Try to provide the details regarding country and gender while focusing on the name and not focusing on icons in the name."\
                        "If you don't have any information, just keep the fields empty, please.",
                        'output_column_names':['country','gender','type'],
                        #"save_to_googlesheet": False, #// Save to Google Sheets?
                        #"spreadsheet_url": "your_spreadsheet_url", #// Google Sheet URL
                        #"worksheet_name": "your_worksheet_name" #// Worksheet name
                        #// ... other enrichment parameters ...
                    },
                    "repeat": True, #// Repeat the task?
                    "repeat_duration": "1m", #// Repeat duration (e.g., "1m", "1h", "1d")
                    "uuid": str(uuid.uuid1()) #// Unique task ID (optional, auto-generated if absent)
                    }
                print(_)
                t=Task(**_)
                t.server=task.server
                print(t)
                t.save()
                uuids.append([str(t.uuid)])
            if a.enrichment_configuration.get('userInfoEnrichment'):
                _={
                    "service": a.service,
                    "ref_id": str(a.uuid),  
                    "end_point": "user",
                    "data_point": "user_info",
                    "add_data": {
                        "data_source": [{
                        "type": "data_house",
                        "object_type": "profile",
                        "internal_filters": {
                            "info__followers_count.isnull": True, 
                            "info__is_private":False
                            #// Example internal filter
                            #// Example internal filter
                             #// Example internal filter
                            #// ... more internal filters as needed ...
                        },
                        "external_filters": {
                            "task.equal": str(task.uuid) #// Filter by audience (REQUIRED)
                            #// ... more external filters as needed ...
                        },
                        
                        "lock_results": True #// Signal to lock the results for the audience (REQUIRED)
                        }],
                        
                        #"save_to_googlesheet": False, #// Save to Google Sheets?
                        #"spreadsheet_url": "your_spreadsheet_url", #// Google Sheet URL
                        #"worksheet_name": "your_worksheet_name" #// Worksheet name
                        #// ... other enrichment parameters ...
                    },
                    "repeat": True, #// Repeat the task?
                    "repeat_duration": "1m", #// Repeat duration (e.g., "1m", "1h", "1d")
                    "uuid": str(uuid.uuid1()) #// Unique task ID (optional, auto-generated if absent)
                    }
                print(_)
                t=Task(**_)
                t.server=task.server
                
                t.save()
                print(str(t.uuid))
                uuids.append([str(t.uuid)])
            if a.enrichment_configuration.get('userPostsEnrichment'):
                _={
                    "service": a.service,
                    "ref_id": str(a.uuid),  
                    "end_point": "user",
                    "data_point": "user_posts",
                    "profile":task.profile,
                    "add_data": {
                        "data_source": {
                        "type": "data_house",
                        "object_type": "profile",
                        "internal_filters": {
                            "info__is_private":False,
                            "info__rest_id.isnull":False,
                            "posts__count.isnull": False, #// Example internal filter
                            #// Example internal filter
                             #// Example internal filter
                            #// ... more internal filters as needed ...
                        },
                        "external_filters": {
                            "task.equal": str(task.uuid) #// Filter by audience (REQUIRED)
                            #// ... more external filters as needed ...
                        },
                        
                        "lock_results": True #// Signal to lock the results for the audience (REQUIRED)
                        },
                        
                        #"save_to_googlesheet": False, #// Save to Google Sheets?
                        #"spreadsheet_url": "your_spreadsheet_url", #// Google Sheet URL
                        #"worksheet_name": "your_worksheet_name" #// Worksheet name
                        #// ... other enrichment parameters ...
                    },
                    "repeat": True, #// Repeat the task?
                    "repeat_duration": "1m", #// Repeat duration (e.g., "1m", "1h", "1d")
                    "uuid": str(uuid.uuid1()) #// Unique task ID (optional, auto-generated if absent)
                    }      
                t=Task(**_)
                t.server=task.server
                
                t.save()  
                uuids.append([str(t.uuid)])      
            
            _={'service':'datahouse',
                        'ref_id':str(a.uuid),
                        'end_point':"update",
                        'data_point':'send_update_to_client',
                        'add_data':{'data_source':[{'type':'task','identifier':uuid}for uuid in uuids],
                                    

                            'save_to_googlesheet':True,
                            'spreadsheet_url':'https:#//docs.google.com/spreadsheets/d/1wTVLDWlmfTTnkrltx1iBUppJ5J_9EBYuCVXa59mhaVM/edit?gid=0#gid=0',
                            'worksheet_name':'audience-update',
                            'client_url':'',
                            'client_id':'central-v1',
                            'audience_id':str(a.uuid)
                                                        

                        },
                        'repeat':True,
                        'repeat_duration':'1m',
                        'uuid':str(uuid.uuid1())
                                        }
                    
            _t=Task(**_)
            _t.server=t.server 
            _t.save()        
            uuids.append([str(_t.uuid)])
    for uuid in uuids:
        logs.append({'created_task':uuid})
    return logs
       