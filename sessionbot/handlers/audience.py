# import uuid
# def handle_audience_deletion(a):
#     from sessionbot.models import Task, Log
#     st_tasks=Task.objects.all().filter(ref_id=a.uuid)
#     unregistered_tasks=st_tasks.filter(registered=False)
#     unregistered_tasks.delete()
#     registered_tasks=st_tasks.filter(registered=True)
#     registered_tasks.update(delete=True)
#     l=Log(message='Deleted '+str(len(unregistered_tasks))+' UnRegistered Tasks for '+a.name,label='INFO',end_point='audience')
#     l.save()        
#     l=Log(message='Queued '+str(len(registered_tasks))+' Registered Tasks  to Delete for '+a.name,label='INFO',end_point='audience')
#     l.save()
#     a.delete()
# def handle_audience_creation(a,payload):
#     from sessionbot.models import Audience, ScrapeTask, Task, Log
#     import uuid

#     # Step 1: Safely extract values from the payload
#     general_config = payload.get('generalConfig', {})
#     settings = general_config.get('settings', {})

#     name = settings.get('name')
#     service = settings.get('service')
#     scrape_task_ids = settings.get('scrapeTasks', [])
#     storage_config = settings.get('storage', {})
#     save_to_googlesheet = storage_config.get('save_to_googlesheet', False)
#     google_sheet_url = storage_config.get('google_sheet_url', '')

#     scrape_tasks = []
#     logs = []

#     print(name)
#     print(payload)
    
#     for id in scrape_task_ids:
#         print(id)
#         s = ScrapeTask.objects.filter(id=id).first()
#         if s:
#             scrape_tasks.append(s)


#             tasks_for_scrape_task = Task.objects.filter(ref_id=s.uuid).exclude(data_point='send_update_to_client')
#             print(tasks_for_scrape_task)
            
#         if save_to_googlesheet:
#             storage_configuration = {
#                 'save_to_googlesheet': True,
#                 'google_sheet_url': google_sheet_url,
#                 'local': True
#             }
#         else:
#             storage_configuration = {
#                 'local': True,
#                 'save_to_googlesheet': False
#             }
#         a.storage_configuration = storage_configuration

#         a.workflow_steps = payload  
#         a.prompt = payload.get('prompt', '')

#         a.name = name
#         a.service = service
#         a.uuid = uuid.uuid1()
#         a.save()
#         a.scrape_tasks.set(scrape_tasks)
        
        
#         from sessionbot.handlers.scrapetask import handle_filter_creation_for_scrapetask
#         for task in tasks_for_scrape_task:
            
#             uuids=[]
#             filters=handle_filter_creation_for_scrapetask(s)

            
#             print(a.uuid)
            
#             _filters={}
#             if a.enrichment_configuration.get('userInfoEnrichment'):
             
#                 _filters.update({"tasks__uuid.in":[task.uuid],"service.equal":s.service,"info__is_private":False,"or_conditions":[{"info__country.isnull":False},{"info__gender.isnull":False}],"or_conditions":[{"info__posts_count.isnull":True},{"profile_picture.isnull":True}]})

#                 _={
#                     "service": a.service,
#                     "ref_id": str(a.uuid),  
#                     "end_point": "user",
#                     "data_point": "user_info",
#                     "profile":task.profile,
#                     "add_data": {
#                         "data_source": [{
#                         "type": "data_house",
#                         "object_type": "profile",
                        
#                         "filters":_filters,
#                          "size":30,
#                         "lock_results": True #// Signal to lock the results for the audience (REQUIRED)
#                         }],
                        
#                         #"save_to_googlesheet": False, #// Save to Google Sheets?
#                         #"spreadsheet_url": "your_spreadsheet_url", #// Google Sheet URL
#                         #"worksheet_name": "your_worksheet_name" #// Worksheet name
#                         #// ... other enrichment parameters ...
#                     },
#                     "repeat": True, #// Repeat the task?
#                     "repeat_duration": "1m", #// Repeat duration (e.g., "1m", "1h", "1d")
#                     "uuid": str(uuid.uuid1()) #// Unique task ID (optional, auto-generated if absent)
#                     }
#                 print(_)
#                 t=Task(**_)
#                 t.server=task.server
                
#                 t.save()
#                 print(str(t.uuid))
#                 uuids.append([str(t.uuid)])
                
                
                
#             if a.enrichment_configuration.get('userPostsEnrichment'):
                
#                 _filters={"tasks__uuid.in":[t.uuid],"service.equal":s.service,"info__is_private":False,"or_conditions":[{"info__country.isnull":False},{"info__gender.isnull":False}],"or_conditions":[{"posts.lte":0}]}

#                 _={
#                     "service": a.service,
#                     "ref_id": str(a.uuid),  
#                     "end_point": "user",
#                     "data_point": "user_posts",
#                     "profile":task.profile,
#                     "add_data": {
#                         "data_source": {
#                         "type": "data_house",
#                         "object_type": "profile",
#                         "filters":_filters,
#                          "size":30,
#                         "lock_results": True #// Signal to lock the results for the audience (REQUIRED)
#                         },
                        
#                         #"save_to_googlesheet": False, #// Save to Google Sheets?
#                         #"spreadsheet_url": "your_spreadsheet_url", #// Google Sheet URL
#                         #"worksheet_name": "your_worksheet_name" #// Worksheet name
#                         #// ... other enrichment parameters ...
#                     },
#                     "repeat": True, #// Repeat the task?
#                     "repeat_duration": "1m", #// Repeat duration (e.g., "1m", "1h", "1d")
#                     "uuid": str(uuid.uuid1()) #// Unique task ID (optional, auto-generated if absent)
#                     }      
#                 t=Task(**_)
#                 t.server=task.server
                
#                 t.save()  
#                 uuids.append([str(t.uuid)])      
#                 if a.enrichment_configuration.get('nationalityEnrichment') or a.enrichment_configuration.get('genderEnrichment'):
                
#                     _filters={"tasks__uuid.in":[t.uuid],"service.equal":s.service, "posts.get":3,"info__is_private":False,"or_conditions":[{"info__country.isnull":True},{"info__gender.isnull":True}]}
#                     _={
#                         "service": "data_enricher",
#                         "ref_id": str(a.uuid),  
#                         "end_point": "enrich",
#                         "data_point": "enrich_social_media_profile",
#                         "add_data": {
#                             "data_source": [{
#                             "type": "data_house",
#                             "object_type": "profile",
#                             "filters":_filters,
#                             "size":30,
                        
                            
#                             "lock_results": True #// Signal to lock the results for the audience (REQUIRED)
#                             }],
#                             'service':'openai',
                            
#                             #"save_to_googlesheet": False, #// Save to Google Sheets?
#                             #"spreadsheet_url": "your_spreadsheet_url", #// Google Sheet URL
#                             #"worksheet_name": "your_worksheet_name" #// Worksheet name
#                             #// ... other enrichment parameters ...
#                         },
#                         "repeat": True, #// Repeat the task?
#                         "repeat_duration": "1m", #// Repeat duration (e.g., "1m", "1h", "1d")
#                         "uuid": str(uuid.uuid1()) #// Unique task ID (optional, auto-generated if absent)
#                         }
#                 print(_)
#                 t=Task(**_)
#                 t.server=task.server
#                 print(t)
#                 t.save()
#                 uuids.append([str(t.uuid)])
#                 """  if a.enrichment_configuration.get('nationalityEnrichment') or a.enrichment_configuration.get('genderEnrichment'):
                
#                 _filters={"tasks__uuid.in":[t.uuid],"service.equal":s.service,"info__is_private":False,"or_conditions":[{"info__country.isnull":True},{"info__gender.isnull":True}]}
#                 _={
#                     "service": "data_enricher",
#                     "ref_id": str(a.uuid),  
#                     "end_point": "enrich",
#                     "data_point": "enrich_social_media_profile",
#                     "add_data": {
#                         "data_source": [{
#                         "type": "data_house",
#                         "object_type": "profile",
#                         "filters":_filters,
#                         "size":30,
                       
                        
#                         "lock_results": True #// Signal to lock the results for the audience (REQUIRED)
#                         }],
#                         'service':'openai',
#                         'columns':['name'],
#                         'prompt': "For the name {name}, provide the following details:\n" \
#                         "1. Type (e.g., Person, Brand, etc.)\n" \
#                         "2. Gender (if it's a person's name)\n" \
#                         "3. Country of origin or association\n\n\
#                         and follow this strictly."\
#                         "Try to provide the details based on their names and also don't focus on any special characters or icons in the name"\
#                         "Try to provide the details regarding country and gender while focusing on the name and not focusing on icons in the name."\
#                         "If you don't have any information, just keep the fields empty, please.",
#                         'output_column_names':['country','gender','type'],
#                         #"save_to_googlesheet": False, #// Save to Google Sheets?
#                         #"spreadsheet_url": "your_spreadsheet_url", #// Google Sheet URL
#                         #"worksheet_name": "your_worksheet_name" #// Worksheet name
#                         #// ... other enrichment parameters ...
#                     },
#                     "repeat": True, #// Repeat the task?
#                     "repeat_duration": "1m", #// Repeat duration (e.g., "1m", "1h", "1d")
#                     "uuid": str(uuid.uuid1()) #// Unique task ID (optional, auto-generated if absent)
#                     }
#                 print(_)
#                 t=Task(**_)
#                 t.server=task.server
#                 print(t)
#                 t.save()
#                 uuids.append([str(t.uuid)]) """
#             _={'service':'datahouse',
#                         'ref_id':str(a.uuid),
#                         'end_point':"update",
#                         'data_point':'send_update_to_client',
#                         'add_data':{'data_source':[{'type':'task','identifier':uuid}for uuid in uuids],
                                    

#                             'save_to_googlesheet':True,
#                             'spreadsheet_url':'https:#//docs.google.com/spreadsheets/d/1wTVLDWlmfTTnkrltx1iBUppJ5J_9EBYuCVXa59mhaVM/edit?gid=0#gid=0',
#                             'worksheet_name':'audience-update',
#                             'client_url':'',
#                             'client_id':'central-v1',
#                             'audience_id':str(a.uuid)
                                                        

#                         },
#                         'repeat':True,
#                         'repeat_duration':'1m',
#                         'uuid':str(uuid.uuid1())
#                                         }
                    
#             _t=Task(**_)
#             _t.server=task.server 
#             _t.save()        
#             uuids.append([str(_t.uuid)])
#     for uuid in uuids:
#         logs.append({'created_task':uuid})
#     return logs
       
       
       
       
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
def handle_audience_creation(a, payload):
    from sessionbot.models import Audience, ScrapeTask, Task, Log
    from sessionbot.handlers.scrapetask import handle_filter_creation_for_scrapetask
    import uuid

    general_config = payload.get('generalConfig', {})
    settings = general_config.get('settings', {})
    workflow_steps = payload.get('steps', [])
    prompt_text = payload.get("prompt", {}).get("prompt", "N/A")
    api_key = general_config.get("settings", {}).get("api_key", "N/A")

    name = settings.get('name')
    service = settings.get('service')
    scrape_task_ids = settings.get('scrapeTasks', [])
    storage_config = settings.get('storage', {})
    save_to_googlesheet = storage_config.get('save_to_googlesheet', False)
    google_sheet_url = storage_config.get('google_sheet_url', '')

    scrape_tasks = []
    scraped_task_uuids = []
    logs = []

    # Step 1: Fetch all scrape tasks and their internal task UUIDs
    for scrape_id in scrape_task_ids:
        s = ScrapeTask.objects.filter(id=scrape_id).first()
        if s:
            scrape_tasks.append(s)
            internal_tasks = Task.objects.filter(ref_id=s.uuid).exclude(data_point='send_update_to_client')
            for task in internal_tasks:
                scraped_task_uuids.append(task.uuid)

    # Step 2: Create and save Audience
    a.name = name
    a.service = service
    a.uuid = uuid.uuid1()
    a.prompt = payload.get('prompt', '')
    a.workflow_steps = payload
    a.storage_configuration = {
        'save_to_googlesheet': save_to_googlesheet,
        'google_sheet_url': google_sheet_url,
        'local': True
    }
    a.save()
    a.scrape_tasks.set(scrape_tasks)

    # Step 3: Get a reference task for server (if needed)
    reference_task = Task.objects.filter(uuid__in=scraped_task_uuids).first()
    if not reference_task:
        return [{'error': 'No internal tasks found for scrape tasks.'}]

    # Step 4: Create tasks from workflow steps
    uuids = []
    for idx, step in enumerate(workflow_steps): 
        step_type = step.get('type')
        step_data = step.get('data')

        print(f"Creating {step_type} task...")

        if idx == 0:
            # First task pulls from all scraped task UUIDs
            filters = convert_frontend_cleaning_data_to_q_payload(step_data) if step_type == 'cleaning' else step_data.copy()
            filters.update({
                "service.equal": service,
                "tasks__uuid.in": scraped_task_uuids,
            })
            task_service = "datahouse"
            task_end_point = "retrieve"
            task_data_point = "retrieve_from_datahouse"
        else:
            previous_task_uuid = uuids[-1]
            filters = convert_frontend_cleaning_data_to_q_payload(step_data) if step_type == 'cleaning' else {}
            filters.update({
                "service.equal": service,
                "tasks__uuid.in": [previous_task_uuid],
            })

            # Set service and endpoint
            task_service = "datahouse" if step_type == "cleaning" else "data_enricher"
            task_end_point = "retrieve" if step_type == "cleaning" else "enrich"

            # Conditionally set data_point
            if step_type == "enrichments" and step_data.get("enrichments_type") == "gender_nationality_enrichment":
                task_data_point = "enrich"
            else:
                task_data_point = "retrieve_from_datahouse" if step_type == "cleaning" else "enrich_social_media_profile"
        lock_results = True

        # Modify lock_results conditionally
        if task_data_point == "retrieve_from_datahouse":
            lock_results = False
        
        # Default service
        if step_type == "enrichments" and step_data.get("enrichments_type") == "user_info_enrichment":
            task_service ="instagram"
            task_end_point = "user"
            task_data_point = "bulk_user_info_scraper"
        
        service_value = "openai" if step_type == "enrichments" else ""
        from ..models import Server  
        datahouse = Server.objects.all().filter(instance_type='data_server')
        datahouse = datahouse[0].public_ip
        storagehouse = Server.objects.all().filter(instance_type='storage_server')
        storagehouse =storagehouse[0].public_ip
        analytics = Server.objects.all().filter(instance_type='reporting_and_analytics_server')
        analytics = analytics[0].public_ip
        task_data = {
            "service": task_service, # Use the determined service
            "ref_id": str(a.uuid),
            "end_point": task_end_point, # Use the determined end_point
            "data_point": task_data_point, # Use the determined data_point
            "add_data": {
                
                "data_source": [{
                    "type": "data_house",
                    "object_type": "profile",
                    "filters": filters,
                    "size": 30,
                    "lock_results": lock_results,
                    "datahouse_url": datahouse + "datahouse/api/consume/",
                    "reporting_house_url": analytics + "reporting/task-reports/",
                    "storage_house_url" : storagehouse + "storagehouse/api/upload",
                    "save_to_storage_house": True
                }],
                
                "save_to_googlesheet": save_to_googlesheet,
                "spreadsheet_url": google_sheet_url,
                "worksheet_name": f"audience-{step_type}",
            },
            "repeat": True,
            "repeat_duration": "1m",
            "uuid": str(uuid.uuid1())
        }
        # Add enrichment-specific fields if data_point is 'gender_nationality_enrichment'
        if task_data_point == "enrich":
            task_data["add_data"].update({
                "prompt": (
                    "For the name {name}, provide the following details:\n"
                    "1. Type (e.g., Person, Brand,continent etc.)\n"
                    "2. Gender (if it's a person's name)\n"
                    "3. Country of origin or association\n\n"
                    "and follow this strictly."
                    "Try to provide the details based on their names and also don't focus on any special characters or icons in the name."
                    "Try to provide the details regarding country and gender while focusing on the name and not focusing on icons in the name."
                    "If you don't have any information, just keep the fields empty, please."
                ),
                "columns": ["name"],
                "output_column_names": ["country", "gender", "type","continent"],
                "api_key": api_key,
                "service": service_value,
                
                
            })
            
        elif task_data_point in ("enrich_social_media_profile", "bulk_user_info_scraper"):
            task_data["add_data"].update({
                "api_key": api_key,
                "service": service_value,
            })
        
        if task_data_point != "retrieve_from_datahouse":
            task_data["add_data"].update({
                "lock_type": "data_point"
            })
    
        if task_data_point in [
            "enrich",
            "enrich_social_media_profile",
            "bulk_user_info_scraper"
            ]:
            task_data["add_data"].update({
                "datahouse_blocks": ["users"]
            })

        _t = Task(**task_data)
        _t.server = reference_task.server
        _t.save()

        task_uuid = str(_t.uuid)
        uuids.append(task_uuid)
        print(f"{step_type} task created with UUID: {task_uuid}")
        logs.append({'created_task': task_uuid})

    return logs








def convert_frontend_cleaning_data_to_q_payload(cleaning_data):
    """
    Converts frontend cleaning step (with 'fields_to_compare' only)
    into a payload for json_to_django_q.
    """

    FRONTEND_OPERATOR_TO_BACKEND_LOOKUP = { 
    "eq": "exact",           # exact match
    "gt": "gt",
    "gte": "gte",
    "lt": "lt",
    "lte": "lte",
    "contains": "icontains",
    "starts with": "istartswith",
    "ends with": "iendswith",
    "neq": "exact",          # handled in 'exclude'
    "does not contain": "icontains",  # handled in 'exclude'
    "is_empty": "isnull",
    "is_not_empty": "isnull",
    "is_one_of": "in",
    "range": "range"
    }


    q_payload = {
        "and_conditions": [],
        "exclude": []
    }

    and_group = {}

    for condition in cleaning_data.get("fields_to_compare", []):
        field = condition.get("key")
        value = condition.get("value")
        operator = condition.get("operator", "eq")

        if not field or operator is None:
            print(f"[!] Skipping invalid condition: {condition}")
            continue

        if operator == "range":
            if isinstance(value, dict) and "min" in value and "max" in value:
                min_val = value["min"]
                max_val = value["max"]
                # Auto-fix if min > max
                if min_val > max_val:
                    min_val, max_val = max_val, min_val
                and_group[f"{field}.gte"] = min_val
                and_group[f"{field}.lte"] = max_val
            else:
                print(f"[!] Invalid range format for field '{field}'")

        elif operator == "is_empty":
            and_group[f"{field}.isnull"] = True

        elif operator == "is_not_empty":
            q_payload["exclude"].append({f"{field}.isnull": True})

        elif operator in ["neq", "does not contain"]:
            lookup = FRONTEND_OPERATOR_TO_BACKEND_LOOKUP[operator]
            q_payload["exclude"].append({f"{field}.{lookup}": value})

        elif operator == "is_one_of":
            and_group[f"{field}.in"] = value

        else:
            lookup = FRONTEND_OPERATOR_TO_BACKEND_LOOKUP.get(operator, "")
            key = f"{field}.{lookup}" if lookup else field
            and_group[key] = value

    if and_group:
        q_payload["and_conditions"].append(and_group)
   
    
    return q_payload