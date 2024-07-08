from celery import shared_task
from celery.utils.log import get_task_logger
from django_celery_results.models import TaskResult
from django.forms.models import model_to_dict
def read_googlesheet_data(**kwargs):
    pass
@shared_task()
def create_resources_from_google_sheets(**kwargs):   
    from google_api import GoogleSheet
    g=GoogleSheet()
    g.initialize_connection()   
    resource_types=['email_providers','profiles','servers','devices']     
    if kwargs.get('spreadsheet_url'):
        g.spreadsheet_url=kwargs.get('spreadsheet_url')   
        print(kwargs['spreadsheet_url'])      
    if kwargs.get('resource_type'):
        resource_types=[kwargs.get('resource_type')]
    request_id=kwargs.get('request_id')  
    response=[]
    for resource_type in resource_types:
        g.open_google_sheet().find_worksheet(resource_type).read_worksheet()  
        data=g.worksheet_data    
        #print(data) 
        
        for row in data:
            #print(row)
            kwargs.update({'row':row})
            resp=None
            if resource_type=='profiles':
                if not row.get('service'):
                    print('Service Not Found.Skipping Profile.Add report here')
                    continue
                
                resp=profile(**row)
                resp.update({'resource_type':'profile'})
                resp.update({'request_id':request_id})
            elif resource_type=='email_providers':
                resp=email_provider(**row)
                resp.update({'resource_type':'email_provider'})
                resp.update({'request_id':request_id})
                print(resp)
            elif resource_type=='devices':
                resp=device(**row)
                resp.update({'request_id':request_id})
                print(resp)
            elif resource_type=='servers':
                resp=server(**row)
                resp.update({'resource_type':'server'})
                resp.update({'request_id':request_id})
            elif resource_type=='proxies':
                kwargs.update({'resource_type':resource_type})
                kwargs.update({'data_point':'proxy'})
                resp.update({'request_id':request_id})
            if resp:
                response.append(resp)
        return response

def profile(**kwargs):
    #Takes a single row and returns a success response with object, or error respons with message
    from sessionbot.models import ChildBot
    from sessionbot.models import EmailProvider
    username=kwargs.get('username')
    if not username:
        return {'response':'failed','message':'ProfileCreationFailed Username Missing','object':None,'label':'UserNameNotFound'}
    service=kwargs.get('service')
    if not service:
        return {'response':'failed','message':'ProfileCreationFailed for '+username+' Service Missing','object':None,'label':'ServiceNotFound'}
    password=kwargs.get('password')
    if not password:
        return {'response':'failed','message':'ProfileCreationFailed for '+username+' Password Missing','object':None,'label':'PasswordNotFound'}
    email_address=kwargs.get('email_address')
    if not email_address:
        return {'response':'failed','message':'ProfileCreationFailed for '+username+' Email Address Missing','object':None,'label':'EmailNotFound'}
    c=ChildBot.objects.all().filter(service=service).filter(username=username)
    if c:
        c=c[0]
        c.password=password
        c.email_address=email_address
        c.display_name=username
        _c=model_to_dict(c)
        _c.pop('cookie')
        _c.pop('created_on')
        resp= {'response':'success','message':'Profile Already Exists for '+username+' Duplicate','object':_c,'label':'ProfileAlreadyExists'}
    else:
        c=ChildBot(
                username=username,
                display_name=username,
                password=password,
                service=service,
                email_address=email_address
                    )
        _c=model_to_dict(c)
        _c.pop('cookie')
        _c.pop('created_on')
    email_provider=kwargs.get('email_provider')
    email_password=kwargs.get('email_password')
    if not email_password:
        if email_provider:
            e=EmailProvider()
            e=EmailProvider.objects.all().filter(imap_email_host=email_provider)
            if e:
                c.email_provider=e[0]
            else:
                resp={'response':'success','message':'Profile '+username+' Created without Email Provider','object':_c,'label':'EmailProviderNotExists'}
        else:
            resp= {'response':'success','message':'Profile '+username+' Created without Email Provider/Password','object':_c,'label':'IncompelteEmailSettings'}
    else:
        c.email_password=email_password
    c.save()
   
    return resp

def email_provider(**kwargs):
    from sessionbot.models import EmailProvider
    print(kwargs)
    imap_email_host=kwargs.get('imap_host')
    if not imap_email_host:
        return {'response':'failed','message':'EmailProviderCreationFailed ImapEmailHost Missing','object':None,'label':'ImapEmailHostMissing'}
    
    imap_email_username=kwargs.get('imap_username')
    if not imap_email_username:
        return {'response':'failed','message':'EmailProviderCreationFailed ImapEmailUsernName Missing','object':None,'label':'ImapEmailUsernameMissing'}

    imap_email_password=kwargs.get('imap_password')
    if not imap_email_password:
        return {'response':'failed','message':'EmailProviderCreationFailed ImapEmailPassword Missing','object':None,'label':'ImapEmailPasswordMissing'}
    
    imap_email_port=kwargs.get('imap_port')
    if not imap_email_port:
        imap_email_port=0
    name=kwargs.get('name')
    if not name:
        name=imap_email_host
    e=EmailProvider.objects.all().filter(imap_email_username=imap_email_username)
    if e:
        return {'response':'success','message':'Email Provider Already Exists for '+imap_email_username+' Duplicate','object':e,'label':'EmailProviderAlreadyExists'}

    else:
        from customer.models import Customer
        c=Customer.objects.all().filter(user__id=1)
        c=c[0]
        e=EmailProvider(
                    imap_email_username=imap_email_username,
                    imap_email_host=imap_email_host,
                    imap_email_password=imap_email_password,
                    imap_email_port=imap_email_port,
                    name=name,
                    customer=c
                        )
        e.save()
        return {'response':'success','message':'Email Provider '+imap_email_host+'Created Successfully','object':e,'label':'NewEmailProviderCreated'}

def server(**kwargs):
    from sessionbot.models import Server
    server_id=kwargs.get('server_id')
    name=kwargs.get('name')
    max_tasks_allowed=kwargs.get('max_tasks_allowed')
    
    if not id or len(server_id)<1:
        return {'status':'failed','message':'Mandatory Key "Id" missing for row','object':None,'label':'IdMissing'}
    s=Server.objects.all().filter(instance_id=server_id)
    if s:
        s=s[0]
    
        s.name=name
        s.maximum_parallel_tasks_allowed=kwargs.get('max_tasks_allowed')
        s.save()
        resp={'status':'success','message':'Update Server '+name+'','object':model_to_dict(s),'label':'ServerUpdated'}
    else:
        s=Server(
                    instance_id=server_id,
                    name=name,
                    maximum_parallel_tasks_allowed=max_tasks_allowed

                )
        s.save()
        resp={'status':'success','message':'Created Server '+name+'','object':model_to_dict(s),'label':'ServerCreated'}

    return resp

def device(**kwargs):
    from sessionbot.models import Device
    from sessionbot.models import Server
    name=kwargs.get('name')
    serial_number=kwargs.get('serial_number')
    connected_to_server=kwargs.get('connected_to_server')
    if not serial_number:
        return {'response':'failed','message':'Device Creation Failed! Serial Number Missing','object':None,'label':'SerialNumberMissing'}
    else:
        if not connected_to_server:
            return {'response':'failed','message':'Device Creation Failed! Connected to Server Missing','object':None,'label':'ConnectedToServerMissing'}

        else:
            if not name:
                return {'response':'failed','message':'Device Creation Failed! Name Missing','object':None,'label':'NameMissing'}

            else:
                from sessionbot.models import Device
                from sessionbot.models import Server
                d=Device.objects.all().filter(serial_number=serial_number)
                c=Server.objects.all().filter(instance_id=connected_to_server)
                if c:
                    c=c[0]
                else:
                    return {'response':'failed','message':'Device Creation Failed! Server Not Found','object':None,'label':'ConnectedServerNotFound'}

                if d:
                    d=d[0]
                    d.connected_to_server=c
                    d.name=name
                    d.save()
                    resp= {'response':'success','message':'Device '+serial_number+' Updated Successfully ','object':model_to_dict(d),'label':'DeviceUpdated'}

                else:
                    d=Device(
                            name=name,
                            serial_number=serial_number,
                            connected_to_server=c

                            )
                    d.save()
                    resp= {'response':'success','message':'Device '+serial_number+' Created Successfully ','object':model_to_dict(d),'label':'DeviceUpdated'}
                return resp

@shared_task()
def convert_bulk_campaign_to_workflow_for_vivide_mind_worker(**kwargs):
    max_bot_reservation_by_service_campaigns=3
    from sessionbot.models import BulkCampaign
    b=BulkCampaign.objects.all().filter(id=1)
    b=b[0]
    bot_campaigns=[]
    for bot in b.childbots.all():
        current_reservation_by_campaigns=bot.campaign.all()
        campaigns=current_reservation_by_campaigns.filter(service=b.service)
        for campaign in campaigns:
            bot_campaigns.append(campaign)
        if current_reservation_by_campaigns>max_bot_reservation_by_service_campaigns:
            print('bot assignment failed. Max Number of Allowed Campaigns in General Settings exceed. Removing the Bot from Campaign (Implement)')
            b.childbots.remove(bot)
    campaigns=list(set(campaigns))
    b.save()
    bot_campaigns_servers=[]
    for campaign in campaigns:
        bot_campaigns_servers.append(campaign.server)
    bot_campaigns_servers=list(set(bot_campaigns_servers))
    if bot_campaigns_servers:
        if len(bot_campaigns_servers)==1:
            prob=False
            for device in b.devies.all():
                if device.connected_to_server==bot_campaigns_servers[0]:
                    pass
                else:
                    prob=True
            if not prob:
                b.server=bot_campaigns_servers[0]
                b.save()
    


