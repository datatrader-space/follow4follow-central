from django.db import models
from django.core.validators import MinValueValidator

from django.core.exceptions import ValidationError
import re
from sessionbot.models import SERVICES
class ProviderBaseModel(models.Model):
    """Abstract base model for common provider fields"""
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique name for the provider"
    )
    provider_name = models.CharField(
        max_length=100, 
        verbose_name="Provider Name",
        help_text="Name of the service provider"
    )
    api_key = models.CharField(
        max_length=255,
        help_text="API key for the provider service"
    )

    class Meta:
        abstract = True
        
    def __str__(self):
        return self.name

class EmailProvider(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique name for the email provider"
    )
    imap_email_host = models.CharField(
        max_length=200,
        unique=True,
        help_text="IMAP server hostname"
    )
    imap_email_port = models.PositiveIntegerField(
        help_text="IMAP server port number"
    )
    imap_email_username = models.EmailField(
        max_length=100,
        unique=True,
        help_text="Email address for authentication"
    )
    imap_email_password = models.CharField(
        max_length=100,
        help_text="Password for authentication"
    )

    class Meta:
        verbose_name = "Email Provider"
        
    def __str__(self):
        return self.name

class ProxyProvider(ProviderBaseModel):
    class Meta(ProviderBaseModel.Meta):
        verbose_name = "Proxy Provider"

class PhoneNumberProvider(ProviderBaseModel):
    class Meta(ProviderBaseModel.Meta):
        verbose_name = "Phone Number Provider"

class AIServiceProvider(ProviderBaseModel):
    class Meta(ProviderBaseModel.Meta):
        verbose_name = "AI Service Provider"

class AppClone(models.Model):
    name = models.CharField(
        max_length=255,
        help_text="The name of the app clone"
    )
    device = models.ForeignKey(
        'sessionbot.Device',
        on_delete=models.CASCADE,
        related_name='app_clones',
        help_text="The device this app clone is installed on"
    )
    package_name = models.CharField(
        max_length=255,
        unique=True,
        help_text="Unique package name of the cloned app"
    )
    created_on = models.DateTimeField(
        auto_now_add=True,
        help_text="Creation timestamp"
    )

    class Meta:
        verbose_name = "App Clone"
        verbose_name_plural = "App Clones"
        ordering = ['-created_on', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['device', 'package_name'],
                name='unique_device_package'
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.package_name})"
    def validate_app_clones_device(self):
        """Ensure all app clones are associated with the selected device"""
        if not self.device_id:
            return
            
        for app_clone in self.app_clones.all():
            if app_clone.device_id != self.device_id:
                raise ValidationError(
                    f"App clone '{app_clone.name}' is not associated with selected device"
                )

# Validation functions
def validate_phone_config(value):
    required_keys = ['country', 'city']
    for key in required_keys:
        if key not in value:
            raise ValidationError(f"Missing required key in phone config: {key}")
    
    if not isinstance(value.get('country'), str) or len(value['country']) != 2:
        raise ValidationError("Country must be a 2-letter country code")
    
    if not isinstance(value.get('city'), str):
        raise ValidationError("City must be a string")

def validate_proxy_config(value):
    required_keys = ['country', 'city']
    for key in required_keys:
        if key not in value:
            raise ValidationError(f"Missing required key in proxy config: {key}")
    
    if not isinstance(value.get('country'), str) or len(value['country']) != 2:
        raise ValidationError("Country must be a 2-letter country code")
    
    if not isinstance(value.get('city'), str):
        raise ValidationError("City must be a string")

def validate_after_creation_logic(value):
    if not isinstance(value, list):
        raise ValidationError("after_creation_logic must be a list of operations")
    
    valid_operation_types = ['profiling', 'posting', 'warmup']
    
    for index, operation in enumerate(value):
        if not isinstance(operation, dict):
            raise ValidationError(f"Operation at index {index} must be a dictionary")
        
        # Validate operation type
        operation_type = next(iter(operation.keys()), None)
        if operation_type not in valid_operation_types:
            raise ValidationError(
                f"Invalid operation type '{operation_type}' at index {index}. "
                f"Valid types: {', '.join(valid_operation_types)}"
            )
        
        # Validate operation configuration
        config = operation[operation_type]
        
        if operation_type == 'profiling':
            validate_profiling_config(config)
        elif operation_type == 'posting':
            validate_posting_config(config)
        elif operation_type == 'warmup':
            validate_warmup_config(config)

def validate_profiling_config(value):
    required_keys = ['datasource', 'folder_name']
    for key in required_keys:
        if key not in value:
            raise ValidationError(f"Missing required key in profiling config: {key}")
    
    if value.get('datasource') not in ['googledrive', 'dropbox', 's3']:
        raise ValidationError("Invalid datasource value in profiling config")

def validate_posting_config(value):
    required_keys = ['datasource', 'folder_name', 'repeat_after']
    for key in required_keys:
        if key not in value:
            raise ValidationError(f"Missing required key in posting config: {key}")
    
    if not isinstance(value.get('max_media_per_post'), int) or value['max_media_per_post'] < 1:
        raise ValidationError("max_media_per_post must be a positive integer")
    
    if not isinstance(value.get('max_posts'), int) or value['max_posts'] < 1:
        raise ValidationError("max_posts must be a positive integer")
    
    # Validate time format (HH:MM:SS)
    if not re.match(r'^\d{2}:\d{2}:\d{2}$', value.get('repeat_after', '')):
        raise ValidationError("repeat_after must be in HH:MM:SS format")

def validate_warmup_config(value):
    required_keys = ['max_follow', 'max_likes']
    for key in required_keys:
        if key not in value:
            raise ValidationError(f"Missing required key in warmup config: {key}")
    
    time_keys = ['max_time_per_day', 'max_time_per_week', 'max_time_per_month']
    for key in time_keys:
        if key in value and not re.match(r'^\d{2}:\d{2}:\d{2}$', value[key]):
            raise ValidationError(f"{key} must be in HH:MM:SS format")

def validate_settings_config(value):
    required_keys = [
        'stop_on_failure_count',
        'stop_on_success_count',
        'delete_clone',
        'max_proxy_retries',
        'max_accounts_per_phone_number',
        'wait_time_between_each_phone_number_or_email_procurement'
    ]
    for key in required_keys:
        if key not in value:
            raise ValidationError(f"Missing required key in settings: {key}")
    
    # Validate integer values
    int_keys = [
        'stop_on_failure_count',
        'stop_on_success_count',
        'max_proxy_retries',
        'max_accounts_per_phone_number'
    ]
    for key in int_keys:
        if not isinstance(value.get(key), int) or value[key] < 0:
            raise ValidationError(f"{key} must be a non-negative integer")
    
    # Validate boolean
    if not isinstance(value.get('delete_clone'), bool):
        raise ValidationError("delete_clone must be a boolean")
    
    # Validate time format
    time_key = 'wait_time_between_each_phone_number_or_email_procur ement'
    if not re.match(r'^\d{2}:\d{2}:\d{2}$', value.get(time_key, '')):
        raise ValidationError(f"{time_key} must be in HH:MM:SS format")
     
class AccountCreationJob(models.Model):
    STATUS_CHOICES = [ 
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),  
        ('failed', 'Failed'),
        ('paused', 'Paused'),
    ]
    service = models.CharField(choices=SERVICES,
                               default='instagram',
                               max_length=50,
                               db_index=True
                               )
    name = models.CharField(
        max_length=255,
        unique=True,
        help_text="Unique name for the account creation job"
    )
    created_on = models.DateTimeField(
        auto_now_add=True,
        help_text="Creation timestamp"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Current job status"
    )
    
    # Device and App Clones relationship
    device = models.ForeignKey(
        'sessionbot.Device',
        on_delete=models.CASCADE,
        related_name='account_jobs',
        help_text="Device used for account creation",
        null=True
    )
    app_clones = models.ManyToManyField(
        AppClone,
        related_name='account_jobs',
        help_text="App clones used for account creation"
    )
    
    # Provider references
    email_provider = models.ForeignKey(
        EmailProvider,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Email provider for account creation"
    )
    phone_provider = models.ForeignKey(
        PhoneNumberProvider,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Phone provider for verification"
    )
    proxy_provider = models.ForeignKey(
        ProxyProvider,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Proxy provider for network routing"
    )
    
    # Provider-specific configurations
    phone_config = models.JSONField(
        default=dict,
        help_text="Phone provider configuration (country, city, etc.)",
        blank=True,
        # validators=[validate_phone_config]
    )
    proxy_config = models.JSONField(
        default=dict,
        help_text="Proxy provider configuration (country, city, etc.)",
        blank=True,
        #validators=[validate_proxy_config]
    )
    
    # After-creation logic (sequence of operations)
    after_creation_logic = models.JSONField(
        default=list,
        help_text="Sequence of operations to perform after account creation",
        blank=True,
        #validators=[validate_after_creation_logic]
    )

    settings = models.JSONField(
        default=dict,
        help_text="Job execution settings",
        blank=True,
        #validators=[validate_settings_config]
    )
    two_fa_live_support = models.BooleanField(
        default=False,
        help_text="Enable live 2FA support"
    )

    class Meta:
        verbose_name = "Account Creation Job"
        verbose_name_plural = "Account Creation Jobs"
        ordering = ['-created_on']

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"
    
    def clean(self):
        super().clean()
        self.validate_app_clones_device()

