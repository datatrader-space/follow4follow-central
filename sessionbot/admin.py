from django.contrib import admin
from sessionbot.models import TargetSettings,BulkCampaign,Sharing,ChildBot,EmailProvider,Device,ScrapeTask,Server,Proxy,DemoGraphic,CampaignTextContent,Settings,Todo
import json
admin.site.register(EmailProvider)
admin.site.register(TargetSettings)

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
admin.site.register(Server)

    
admin.site.register(Device)

class BulkCampaignAdmin(admin.ModelAdmin):
    filter_horizontal = ('childbots','devices','scrape_tasks','proxies','demographic','messaging','settings','sharing')

# Register your models here.
class ScrapeTaskAdmin(admin.ModelAdmin):
    filter_horizontal =('childbots',)
admin.site.register(ScrapeTask,ScrapeTaskAdmin)
admin.site.register(BulkCampaign,BulkCampaignAdmin)
admin.site.register(Proxy)
admin.site.register(DemoGraphic)
admin.site.register(CampaignTextContent)
admin.site.register(Settings)
admin.site.register(Sharing)
admin.site.register(Todo)