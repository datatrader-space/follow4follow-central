from django.contrib import admin
from sessionbot.models import Issue,TaskErrorSummary,SyncedSheet,Workflow,Job,DataHouseSyncStatus,Audience,Log,TargetSettings,BulkCampaign,Sharing,ChildBot,EmailProvider,Device,ScrapeTask,Server,Proxy,DemoGraphic,CampaignTextContent,Settings, Task,Todo
import json
admin.site.register(Workflow)
admin.site.register(TaskErrorSummary)
admin.site.register(Issue)
admin.site.register(Job)
admin.site.register(EmailProvider)
admin.site.register(TargetSettings)
admin.site.register(Log)
admin.site.register(Audience)
admin.site.register(SyncedSheet)
from django_admin_relation_links import AdminChangeLinksMixin

from sessionbot.resource_utils import convert_bulk_campaign_to_workflow_for_vivide_mind_worker
class SessionBotAdmin(AdminChangeLinksMixin,
                     
                        admin.ModelAdmin
                        ):
    change_list_template = 'admin/sessionbot/change_list.html'
    list_select_related = True

    search_fields = (
                     'username',

                     )
    list_display=['username','password','device','followers','following']
   

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        print('hey')
        if request.method=='POST':
            print('hey')
            body_unicode = request.POST.get('googlesheet_link',None)
            print(body_unicode)
            convert_bulk_campaign_to_workflow_for_vivide_mind_worker.delay(**{'spreadsheet_url':body_unicode})
            print(body_unicode)
            print(' the task was executed asynchronously')
           
        return super().changelist_view(
            request,  extra_context=extra_context,
        )
    actions = ['assign_selected_profiles_to_campaign']
    @admin.action(description='Assign selected Profiles as target to Campaign')
    def assign_selected_profiles_to_campaign(self, request, queryset):
        print(request)
admin.site.register(ChildBot,SessionBotAdmin)

admin.site.register(DataHouseSyncStatus)
class TaskAdmin(admin.ModelAdmin):
    list_filter=['ref_id','status','os','server','end_point','data_point','device']
    list_display=['uuid','ref_id','service','server','end_point','data_point','created_at','input','os','repeat','profile','device','status','retries_count']
    actions = ['start_tasks','stop_tasks','resume_tasks','pause_tasks']
    search_fields = (
                     'profile',

                     )
    @admin.action(description='Pause Seleted Tasks')
    def pause_tasks(self, request, queryset):
        queryset.update(paused=True)
    @admin.action(description='Start Seleted Tasks')
    def start_tasks(self,request,queryset):
        queryset.update(status='pending')
    @admin.action(description='Stop Seleted Tasks')
    def stop_tasks(self,request,queryset):
        queryset.update(status='completed')
    @admin.action(description='Resume Seleted Tasks')
    def resume_tasks(self,request,queryset):
        queryset.update(status='pending').update(paused=False)
admin.site.register(Task,TaskAdmin) 



    
admin.site.register(Device)

class BulkCampaignAdmin(admin.ModelAdmin):
    filter_horizontal = ('childbots','devices','scrape_tasks','proxies')

# Register your models here.
# class ScrapeTaskAdmin(admin.ModelAdmin):
#     filter_horizontal =('childbots',)
# admin.site.register(ScrapeTask,ScrapeTaskAdmin)
@admin.register(ScrapeTask)
class ScrapeTaskAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'uuid',  
        'service',
        'customer',
        'internal_state',
        'os',
        
    )
    filter_horizontal = ('childbots',)

admin.site.register(BulkCampaign,BulkCampaignAdmin)
admin.site.register(Proxy)
admin.site.register(DemoGraphic)
admin.site.register(CampaignTextContent)
admin.site.register(Settings)
admin.site.register(Sharing)
admin.site.register(Todo)

from django.contrib import admin
from .models import Server, Event, Heartbeat, ResourceUsage

@admin.register(Server)
class ServerAdmin(admin.ModelAdmin):
    list_display = ('name', 'public_ip')
  
    search_fields = ('name', 'public_ip')

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'server', 'timestamp', 'received_at')
    list_filter = ('event_type', 'server')
    date_hierarchy = 'received_at'
    search_fields = ('server__name',)

@admin.register(Heartbeat)
class HeartbeatAdmin(admin.ModelAdmin):
    list_display = ('server', 'timestamp', 'received_at')
    list_filter = ('server',)
    date_hierarchy = 'received_at'
    search_fields = ('server__name',)

@admin.register(ResourceUsage)
class ResourceUsageAdmin(admin.ModelAdmin):
    list_display = ('server', 'timestamp', 'cpu_percent', 'memory_percent', 'disk_percent', 'received_at')
    list_filter = ('server',)
    date_hierarchy = 'received_at'
    search_fields = ('server__name',)