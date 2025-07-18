from rest_framework import serializers
from .models import (
    EmailProvider, 
    ProxyProvider, 
    PhoneNumberProvider, 
    AIServiceProvider,
    AppClone,
    AccountCreationJob
)
from sessionbot.models import Device
from sessionbot.serializers import DeviceSerializer
class EmailProviderSerializer(serializers.ModelSerializer):

    class Meta:
        model = EmailProvider
        fields = '__all__'
        extra_kwargs = {
            'imap_email_password': {'write_only': True}
        }

class ProviderBaseSerializer(serializers.ModelSerializer):
    class Meta:
        fields = '__all__'
        abstract = True
        extra_kwargs = {
            'api_key': {'write_only': True}
        }

class ProxyProviderSerializer(ProviderBaseSerializer):
    class Meta(ProviderBaseSerializer.Meta):
        model = ProxyProvider

class PhoneNumberProviderSerializer(ProviderBaseSerializer):
    class Meta(ProviderBaseSerializer.Meta):
        model = PhoneNumberProvider

class AIServiceProviderSerializer(ProviderBaseSerializer):
    class Meta(ProviderBaseSerializer.Meta):
        model = AIServiceProvider

class AppCloneSerializer(serializers.ModelSerializer):
    device = DeviceSerializer(read_only=True)
    device_id = serializers.PrimaryKeyRelatedField(
        queryset=Device.objects.all(),
        source='device',
        write_only=True,
        help_text="ID of the device this app clone is installed on"
    )

    class Meta:
        model = AppClone
        fields = '__all__'
        extra_kwargs = {
            'package_name': {
                'help_text': "Unique package name (e.g. 'com.whatsapp.clone1')"
            },
            'created_on': {'read_only': True}
        }


class AccountCreationJobSerializer(serializers.ModelSerializer):
   

    settings = serializers.JSONField(
        help_text="Job settings: {stop_on_failure_count: int, stop_on_success_count: int, delete_clone: bool, max_proxy_retries: int, max_accounts_per_phone_number: int, wait_time_between_each_phone_number_or_email_procurement: 'HH:MM:SS'}"
    )

    

    class Meta:
        model = AccountCreationJob
        fields = '__all__'
        read_only_fields = ('created_on', 'status')
        extra_kwargs = {
            'email_provider': {'help_text': "ID of email provider"},
            'phone_provider': {'help_text': "ID of phone number provider"},
            'proxy_provider': {'help_text': "ID of proxy provider"},
            'two_fa_live_support': {'help_text': "Enable live 2FA assistance"}
        }

    def validate_creator_config(self, value):
        # Validation logic same as model validators
        return value

    def validate_profiling(self, value):
        # Validation logic same as model validators
        return value

    def validate_posting(self, value):
        # Validation logic same as model validators
        return value

    def validate_warmup(self, value):
        # Validation logic same as model validators
        return value
    def validate_settings(self, value):
        # Validation logic same as model validator
        return value

    