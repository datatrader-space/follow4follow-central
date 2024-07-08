from django.urls import path

from .views import createResource
from django.urls import path, include
from sessionbot.models import ChildBot,Server,Device,CampaignTextContent,Proxy,Settings,Sharing,ScrapeTask,Todo
from rest_framework import routers, serializers, viewsets

# Serializers define the API representation.
class BotSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ChildBot
        
        exclude=['device','customer','email_provider']
class BotViewSet(viewsets.ModelViewSet):
    queryset = ChildBot.objects.all()
    serializer_class = BotSerializer

class ServerSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model =Server
        exclude=['customer']
       
class ServerViewSet(viewsets.ModelViewSet):
    queryset = Server.objects.all()
    serializer_class = ServerSerializer
class DeviceSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model =Device
        exclude=['connected_to_server']
       
class DeviceViewSet(viewsets.ModelViewSet):
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer
class MessagingSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model =CampaignTextContent
        fields = '__all__'
class MessagingViewSet(viewsets.ModelViewSet):
    queryset=CampaignTextContent.objects.all()
    serializer_class=MessagingSerializer

class ProxySerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model=Proxy
        exclude=['tagged_bad_on','customer']
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
    class Meta:
        model=Sharing
        fields='__all__'
        
class SharingViewSet(viewsets.ModelViewSet):
    queryset=Sharing.objects.all()
    serializer_class=SharingSerializer
class ScrapeTaskSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model=ScrapeTask
        exclude=['customer']
        
class ScrapeTaskViewSet(viewsets.ModelViewSet):
    queryset=ScrapeTask.objects.all()
    serializer_class=ScrapeTaskSerializer  

class TodoSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model=Todo
        fields='__all__'
        
class TodoViewSet(viewsets.ModelViewSet):
    queryset=Todo.objects.all()
    serializer_class=TodoSerializer  
# ViewSets define the view behavior.

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
urlpatterns = [
    path("api/resource/create/", createResource, name="create_resource"),
    path("api/reports/logs", createResource, name="view_logs"),
    path('api/resource/', include(router.urls)),
   
    
    
]