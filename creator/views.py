from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets,filters
from .models import (
    EmailProvider, 
    ProxyProvider, 
    PhoneNumberProvider, 
    AIServiceProvider,
    AppClone
)
from .serializers import (
    EmailProviderSerializer,
    ProxyProviderSerializer,
    PhoneNumberProviderSerializer,
    AIServiceProviderSerializer,
    AppCloneSerializer
)

class EmailProviderViewSet(viewsets.ModelViewSet):
    queryset = EmailProvider.objects.all()
    serializer_class = EmailProviderSerializer
    filterset_fields = ['name']
    search_fields = ['name', 'imap_email_host', 'imap_email_username']

class ProxyProviderViewSet(viewsets.ModelViewSet):
    queryset = ProxyProvider.objects.all()
    serializer_class = ProxyProviderSerializer
    filterset_fields = [ 'name']
    search_fields = ['name', 'provider_name']

class PhoneNumberProviderViewSet(viewsets.ModelViewSet):
    queryset = PhoneNumberProvider.objects.all()
    serializer_class = PhoneNumberProviderSerializer
    filterset_fields = [ 'name']
    search_fields = ['name', 'provider_name']

class AIServiceProviderViewSet(viewsets.ModelViewSet):
    queryset = AIServiceProvider.objects.all()
    serializer_class = AIServiceProviderSerializer
    filterset_fields = [ 'name']
    search_fields = ['name', 'provider_name']

class AppCloneViewSet(viewsets.ModelViewSet):
    queryset = AppClone.objects.select_related('device').all()
    serializer_class = AppCloneSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'package_name', 'device__name']
    ordering_fields = ['name', 'created_on', 'package_name']
    ordering = ['-created_on']

    def get_queryset(self):
        queryset = super().get_queryset()
        device_id = self.request.query_params.get('device_id')
        if device_id:
            queryset = queryset.filter(device_id=device_id)
        return queryset
from rest_framework import viewsets
from .models import AccountCreationJob
from .serializers import AccountCreationJobSerializer

class AccountCreationJobViewSet(viewsets.ModelViewSet):
    queryset = AccountCreationJob.objects.select_related(
   
        'email_provider',
        'phone_provider',
        'proxy_provider'
    ).all()
    serializer_class = AccountCreationJobSerializer
    filterset_fields = ['status', 'two_fa_live_support']
    search_fields = ['name', 'creator_config', 'profiling', 'posting', 'warmup']
    ordering_fields = ['created_on', 'name']
    ordering = ['-created_on']