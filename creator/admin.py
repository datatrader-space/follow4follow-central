from django.contrib import admin
import json
# Register your models here.
from django.contrib import admin
from django.contrib import messages
from django.utils.html import format_html
from .models import (
    EmailProvider,
    ProxyProvider,
    PhoneNumberProvider,
    AIServiceProvider,
    AppClone,
    AccountCreationJob
)

class ProviderAdminBase(admin.ModelAdmin):
    list_display = ('name',  'provider_name', 'api_key_preview')
    search_fields = ('name', 'provider_name')

    
    def api_key_preview(self, obj):
        if obj.api_key:
            return format_html('<code>{}</code>', f'{obj.api_key[:10]}...')
        return '-'
    api_key_preview.short_description = 'API Key Preview'

@admin.register(EmailProvider)
class EmailProviderAdmin(admin.ModelAdmin):
    list_display = ('name',  'imap_email_host', 'imap_email_username')
    search_fields = ('name', 'imap_email_host', 'imap_email_username')



@admin.register(ProxyProvider)
class ProxyProviderAdmin(ProviderAdminBase):
    pass

@admin.register(PhoneNumberProvider)
class PhoneNumberProviderAdmin(ProviderAdminBase):
    pass

@admin.register(AIServiceProvider)
class AIServiceProviderAdmin(ProviderAdminBase):
    pass

@admin.register(AppClone)
class AppCloneAdmin(admin.ModelAdmin):
    search_fields = ('name', 'package_name', 'device__name')
    list_display = ('name', 'device_link', 'package_name', 'created_on')
    
    list_filter = ('created_on',)
    date_hierarchy = 'created_on'
    readonly_fields = ('created_on',)
    
    
    fieldsets = (
        (None, {
            'fields': ('name', 'device', 'package_name')
        }),
        ('Metadata', {
            'fields': ('created_on',),
            'classes': ('collapse',)
        })
    )
    
    def device_link(self, obj):
        url = f"/admin/sessionbot/device/{obj.device.id}/change/"
        return format_html('<a href="{}">{}</a>', url, obj.device.name)
    device_link.short_description = 'Device'
    device_link.admin_order_field = 'device__name'

    class Media:
        js = ('admin/js/jquery.init.js',)
@admin.register(AccountCreationJob)
class AccountCreationJobAdmin(admin.ModelAdmin):
    list_display = ('name',  'status', 'created_on', 'two_fa_live_support')
    list_filter = ('status', 'created_on',  'two_fa_live_support')
    search_fields = ('name', 'creator_config', 'profiling', 'posting', 'warmup')
    readonly_fields = ('created_on',)
    autocomplete_fields = ('email_provider', 'phone_provider', 'proxy_provider')
    
    fieldsets = (
        (None, {
            'fields': ( 'name', 'status')
        }),
        ('Providers', {
            'fields': ('email_provider', 'phone_provider','phone_config', 'proxy_provider','proxy_config')
        }),
        ('Configuration', {
            'fields': (
                'settings',
                'device',
                'app_clones',
                'after_creation_logic',
                
                'two_fa_live_support',
                
            )
        }),
        ('Metadata', {
            'fields': ('created_on',),
            'classes': ('collapse',)
        })
    )
    
    def view_config(self, obj):
        return format_html("<pre>{}</pre>", json.dumps({
            'creator_config': obj.creator_config,
            'profiling': obj.profiling,
            'posting': obj.posting,
            'warmup': obj.warmup
        }, indent=2))
    view_config.short_description = 'Configuration Preview'