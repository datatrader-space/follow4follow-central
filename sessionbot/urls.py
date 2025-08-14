from django.urls import path

from .views import  update_task_status,fetch_task_summaries_view,EventView,task_actions,sync_sheet,todo,log,audience, bulk_campaign,scrape_task, createProxyResource, createResource, createDeviceResource, deleteDeviceResource, deleteProxyResource, attendance_task
from django.urls import path, include
from sessionbot.models import Issue,Audience,ChildBot,Server,Device,CampaignTextContent,Proxy,Settings,Sharing,ScrapeTask, Task,Todo,BulkCampaign,INSTANCE_TYPES  
from rest_framework import routers, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
# Serializers define the API representation.
class BulkCampaignSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.IntegerField(read_only=True)
    devices = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    childbots = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    servers = serializers.PrimaryKeyRelatedField(read_only=True)
    scrape_tasks = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    sharing = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    messaging = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    proxies = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = BulkCampaign
        exclude = ['customer', 'target_settings']

class BulkCampaignViewSet(viewsets.ModelViewSet):
    queryset = BulkCampaign.objects.all()
    serializer_class = BulkCampaignSerializer

class ServerSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.IntegerField(read_only=True)
    class Meta:
        model =Server
        field=['name']
        exclude=['customer']
       
class ServerViewSet(viewsets.ModelViewSet):
    queryset = Server.objects.all()
    serializer_class = ServerSerializer

    @action(detail=False, methods=['get'])
    def choices(self, request):
        return Response({
            'instance_type_choices': dict(INSTANCE_TYPES)
        })
        
class BotSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.IntegerField(read_only=True)
    logged_in_on_servers = serializers.SlugRelatedField(
        queryset=Server.objects.all(),
        slug_field='name',  
    )

    device = serializers.SlugRelatedField(
        queryset=Device.objects.all(),
        slug_field='serial_number',  
    )

    cookie = serializers.CharField(required=False, allow_null=True)
    
    class Meta:
        model = ChildBot
        exclude = ['customer', 'email_provider']
        
class BotViewSet(viewsets.ModelViewSet):
    queryset = ChildBot.objects.all()
    serializer_class = BotSerializer


class DeviceSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.IntegerField(read_only=True)
    connected_to_server = serializers.SlugRelatedField(
        queryset=Server.objects.all(),
        slug_field='name',  
    )

    class Meta:
        model = Device
        fields = '__all__' 
       
class DeviceViewSet(viewsets.ModelViewSet):
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer

class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = '__all__'
        
class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer

class TaskissueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Issue
        fields = '__all__'

class TaskissueSummaryViewSet(viewsets.ModelViewSet):
    queryset = Issue.objects.all()
    serializer_class = TaskissueSerializer
    
class MessagingSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.IntegerField(read_only=True)
    class Meta:
        model =CampaignTextContent
        fields = '__all__'
class MessagingViewSet(viewsets.ModelViewSet):
    queryset=CampaignTextContent.objects.all()
    serializer_class=MessagingSerializer

class ProxySerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.IntegerField(read_only=True)
    class Meta:
        model=Proxy
        fields = '__all__'
        
class ProxyViewSet(viewsets.ModelViewSet):
    queryset=Proxy.objects.all()
    serializer_class=ProxySerializer

class SettingsSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model=Settings
        fields='__all__'
        
class SettingsViewSet(viewsets.ModelViewSet):
    queryset=Settings.objects.all()
    serializer_class=SettingsSerializer
class SharingSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.IntegerField(read_only=True)
    class Meta:
        model=Sharing
        fields='__all__'
        
class SharingViewSet(viewsets.ModelViewSet):
    queryset=Sharing.objects.all()
    serializer_class=SharingSerializer

class ScrapeTaskSerializer(serializers.HyperlinkedModelSerializer):    
    id = serializers.IntegerField(read_only=True)
    childbots = BotSerializer(many=True, read_only=True)
    class Meta:
        model=ScrapeTask
        exclude=['customer']
class AudienceSerializer(serializers.HyperlinkedModelSerializer):    
    id = serializers.IntegerField(read_only=True)
    campaigns = BulkCampaignSerializer(many=True, read_only=True)
    class Meta:
        model=Audience
        fields = '__all__'
class AudienceViewSet(viewsets.ModelViewSet):    
    queryset=Audience.objects.all()
    serializer_class=AudienceSerializer 
class ScrapeTaskViewSet(viewsets.ModelViewSet):
    queryset=ScrapeTask.objects.all()
    serializer_class=ScrapeTaskSerializer  

class TodoSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.IntegerField(read_only=True)
    bots = BotSerializer(many=True, read_only=True)

    class Meta:
        model=Todo
        fields='__all__'
        
class TodoViewSet(viewsets.ModelViewSet):
    queryset=Todo.objects.all()
    serializer_class=TodoSerializer  
# ViewSets define the view behavior.

        # If you want to allow sending server_name and have the serializer handle
        # finding or creating the Server, you'd need a more complex implementation
        # involving overriding the create method. For this basic integration,
        # we'll expect the client to send the server's primary key.
# Routers provide an easy way of automatically determining the URL conf.

router = routers.DefaultRouter()
router.register(r'profile', BotViewSet)
router.register(r'server',ServerViewSet)
router.register(r'device',DeviceViewSet)
router.register(r'messaging',MessagingViewSet)
router.register(r'proxy',ProxyViewSet)
router.register(r'settings',SettingsViewSet)
router.register(r'sharing',SharingViewSet)
router.register(r'scrapetask',ScrapeTaskViewSet)
router.register(r'todo',TodoViewSet)
router.register(r'bulkcampaign', BulkCampaignViewSet)
router.register(r'audience',AudienceViewSet)
router.register(r'tasks', TaskViewSet)
router.register(r'issues',TaskissueSummaryViewSet)



urlpatterns = [
    path("api/resource/bulk-campaign/", bulk_campaign, name='bulk_campaign'),
    path("api/resource/create/", createResource, name="create_resource"),
    path("api/resource/sync_sheet/", sync_sheet, name="sync_sheet"),
    path("api/reports/logs", createResource, name="view_logs"),
    path('api/resource/', include(router.urls)),
    path('api/devices/create/', createDeviceResource, name='create_device'),
    path("api/proxies/create/", createProxyResource, name='create_proxy'),
    path("api/devices/delete/<str:serial_number>/", deleteDeviceResource, name='deleteDeviceResource'),
    path('api/proxy/delete/<str:proxy_url>/', deleteProxyResource, name='delete_proxy_resource'),
    path('api/attendance/attendance-task/', attendance_task, name='attendance_task'),
    path('api/scrapetask/', scrape_task, name='scrape_task'),
    path('api/todo/', todo, name='todo_view'),
    path('api/logs/',log,name='logs'),
    path('api/tasks/action/',task_actions,name='task_actions'),
    path('api/audience/',audience,name='audience'),
    path('api/event/', EventView.as_view(), name='receive_event'),
    path('api/resource/reporting/',fetch_task_summaries_view,name='fetch_summ'),
    
    path("api/task-errors-resolved/", update_task_status, name="task-errors-resolved"),
    
    
]