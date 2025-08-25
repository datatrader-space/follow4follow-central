import datetime as dt
import time
import uuid
from datetime import datetime, timedelta
from typing import Tuple

#from cloud.models import EC2Instance
from customer.models import Customer
from django.contrib.auth import get_user_model
from django.core.cache import cache
#from tools.model import ConcurrentModificationError, LockedModel
from django.db import IntegrityError, models, transaction
from django.db.models import (Count, ExpressionWrapper, F, Max,
                              ObjectDoesNotExist, OuterRef, Q, Subquery)
from django.db.models.fields import Field
from django.db.models.signals import post_save
from django.utils import timezone
from django.contrib.postgres.fields import ArrayField
#from django_celery_beat.models import CrontabSchedule, IntervalSchedule
from jsonfield.fields import JSONField
from django import forms


User = get_user_model()
from typing import Tuple, Dict

EMAIL_SERVICES: Tuple[Tuple[str]] = (
    ('rediff', 'Rediff Email'),
)

SERVICES: Tuple[Tuple[str]] = (
    ('instagram', 'Instagram'),
    ('attendance','attendance'),
    ('twitter','twitter'),
    ('tiktok','tiktok'),
    ('cleaner','cleaner'),
    ('data_enricher','Data Enricher'),
    ('openai','OpenAI'),
    ('audience','Audience'),
    ('datahouse','DataHouse')
)

OPERATIONS: Dict[str, Tuple[Tuple[str]]] = {
    'instagram': (
        ('login', 'Instagram Login'),
    )
}
ACTIVITY_CHOICES = (
    ('comment', 'comment'),
    ('like', 'like'),
    ('dm', 'dm'),
    ('like_comment', 'like_comment'),
    ('reply_to_comment', 'reply_to_comment'),
    ('follow', 'follow'),
    ('login', 'login'),
    ('retweet','retweet'),
    ('share_post','share post')

)

DM_CHOICES=(
    ('welcome_message','welcome message'),
    ('followup_message','followup_message'),
    ('reachout_message','reachout message'),
    ('response_to_reachout_message','response to reachout message'),
)
OPERATIONS_CHOICES = []
INSTANCE_TYPES = (
    ('main', 'Main'),
    ('data_server', 'DataServer'),
    ('storage_server', 'StorageServer'),
    ('central_server', 'CentralServer'),
    ('worker_server', 'WorkerServer'),
    ('dev_server', 'DevelopmentServer'),
    ('reporting_and_analytics_server','Reporting and Analytics Server'),
)

TM_STATES = (
    ('ACTIVE', 'Runing'),
    ('IN_ACTIVE', 'Restarting'),
    ('RESTART', 'Restarting')
)

INSTANCE_STATE_CHOICES = (
    ('running', 'running'),
    ('stopped', 'stopped'),
    ('pending', 'pending'),
    ('shutting-down', 'shutting-down'),
    ('terminated', 'terminated'),
    ('stopping', 'stopping'),
    ('starting', 'starting'),
    ('backing_up', 'backing_up'),
    ('rebooting', 'Rebooting'),
    ('service_offline', 'Service Offline')
)

INSTANCE_ONLINE_STATUS_CHOICES = (
    ('offline', 'offline'),
    ('online', 'online'),
)
for service, operations in OPERATIONS.items():
    for op, op_name in operations:
        OPERATIONS_CHOICES.append(('%s.%s' % (service, op), op_name))
internal_states = (
        ('active', 'Active'),
        ('in_active', 'In-Active'),
        ('expired', 'Expired'),
        ('complete', 'Complete')
    )
campaign_states = (
        ('launched', 'Launched'),
        ('stopping', 'Stopping'),
        ('stopped', 'Stopped'),
        ('paused', 'Paused'),
        ('deleted', 'Deleted'),
        ('draft', 'Draft')
    )
RElATION_TAG_CHOICES=(
    ('positive_welcome_responder','POSITIVE WELCOME RESPONDER'),
    ('positive_offer_responder','POSITIVE OFFER RESPONDER'),
    ('email_granter','EMAIL GRANTER'),
    ('no_follow_back','NO FOLLOW BACKER'),
    ('no_response_follower','NO RESPONSE FOLLOWER'),
    ('negative_response_followers','NEGATIVE RESPONSE FOLLOWERS'),
    ('target','TARGET'),
    ('self_follower','SELF FOLLOWER'),
    ('new_follower','NEW FOLLOWER'),
    
    
)

DM_TAG_CHOICES=(
            ('reachout','Reachout'),
            ('welcome','Welcome'),
            ('offer','Offer'),
            ('email_request','Email Request'),
            ('subscription_request','Subscription Request'),
            ('followup','Follow Up'),
            ('share_code','Share Discount Code')
    
    
)




class ModifiedArrayField(ArrayField):
    def formfield(self, **kwargs):
        defaults = {
            "form_class": forms.MultipleChoiceField,
            "choices": self.base_field.choices,
            "widget": forms.CheckboxSelectMultiple,
            **kwargs
        }
        return super(ArrayField, self).formfield(**defaults)

def default_timestamp():
    return timezone.now().timestamp()
starting_point_choices=(
    ('profile_page','Profile Page'),
    ('search_page','Search Page'),
    ('home_page','Home Page'),
    ('post_page','Post Page'),
    ('explore_page','Explore Page'),
    ('messenger','Messenger'),
)
scrapper_type_choices=(
                ('followers','Followers'),
                ('profile','Profile'),
                ('post','Post'),
                ('followings','Followings'),
                ('comments','Comments'),
                )
class BaseModel(models.Model):
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.pk:  # Ensure object has been saved
            if not self.uuid:
                self.uuid=uuid.uuid1()
                self.save()
            DataHouseSyncStatus.objects.create(
                model_name=self.__class__.__name__,
                object_id=str(self.uuid),
                operation='UPDATE' if self.pk else 'CREATE'
            )
            

    def delete(self, *args, **kwargs):
        original_uuid= self.uuid
        class_name=self.__class__.__name__
        worker=None
        if hasattr(self,'server'):
            worker=self.server
        super().delete(*args, **kwargs)
        DataHouseSyncStatus.objects.create(
                model_name=class_name,
                object_id=original_uuid,
                operation='DELETE',
                worker=worker
            )
        
        
class EmailProvider( models.Model):
    customer = models.ForeignKey(
        Customer,
        on_delete=models.deletion.CASCADE
    )
    name = models.CharField(
        max_length=100
    )
    imap_email_host = models.CharField(
        max_length=200,unique=True
    )
    imap_email_port = models.PositiveIntegerField(
    )
    imap_email_username = models.EmailField(
        max_length=100,unique=True
    )
    imap_email_password = models.CharField(
        max_length=100,
    )

    def __str__(self):
        return f'{self.imap_email_host}:{self.imap_email_port}/{self.imap_email_username}@*****'

    class Meta:
        unique_together = ('customer', 'name')
        verbose_name = "Email Provider"

    
    
    
    def __str__(self):
        return self.name
class Server(BaseModel):
    class Meta:
        verbose_name = "server"
    
    name = models.CharField(
        max_length=5000,
        blank=True,
        null=True
    )
    customer = models.ForeignKey(Customer,
                                 blank=True,
                                 null=True,
                                 on_delete=models.deletion.SET_NULL
                                 )
    instance_id = models.CharField(
        max_length=500,
        null=True
    )
    public_ip = models.URLField(
        max_length=100,
        null=True,
        blank=True
    )

    instance_type = models.CharField(choices=INSTANCE_TYPES,
                                     max_length=500
                                     )

    state = models.CharField(choices=INSTANCE_STATE_CHOICES,
                             max_length=500,
                             default='pending'
                             )
    health=models.CharField(choices=(('healthy','Healthy'),('unhealthy','UnHealthy')),max_length=50,blank=False,default='healthy')
    online_status = models.CharField(choices=INSTANCE_ONLINE_STATUS_CHOICES,
                                     max_length=500,
                                     default='offline'
                                     ) 
    running_process_count = models.IntegerField(default=0)
    task_queue_count = models.IntegerField(default=0)
    last_heart_beat = models.DateTimeField(blank=True, null=True)
    ram_percent = models.IntegerField(default=0)
    disk_percent = models.IntegerField(default=0)
    cpu_percent=models.IntegerField(default=0)
    localstore_active=models.BooleanField(default=False)
    access_secret_key=models.CharField(unique=True,max_length=5000,null=True,blank=True)
    maximum_parallel_tasks_allowed = models.IntegerField(default=1)
    created_on = models.DateTimeField(default=timezone.now)
    uuid = models.UUIDField(
        default=uuid.uuid1,
        unique=True,
        editable=False
    )

    def __str__(self):
        return self.name
    
    def get_server_url(self):
        return self.public_ip

    def update_instance_information(self): pass

    def change_instance_ip(self): pass

    def start_instance(self): pass

    def stop_instance(self): pass

    def terminate_instance(self): pass

class Device(BaseModel):
    uuid=models.UUIDField(blank=False,null=True,unique=True)
    name=models.CharField(max_length=500,blank=False,unique=True,null=False)
    serial_number=models.CharField(max_length=500,blank=False,unique=True,null=False)
    info=models.JSONField(null=True,blank=True)
   
    connected_to_server=models.ForeignKey(Server,on_delete=models.SET_NULL,null=True)

    def __str__(self):
        return self.serial_number

class ChildBot(BaseModel):
    """[summary]

    Args:
        models ([type]): [description]

    Returns:
        [type]: [description]
    """
    uuid=models.UUIDField(blank=False,null=True,unique=True)
    display_name = models.CharField(max_length=100,
                                    null=True,
                                    blank=True
                                    )



    device=models.ForeignKey(Device,on_delete=models.CASCADE,null=True,blank=True)
    editable_attributes = ['dob',
                           'sex',
                           'first_name',
                           'last_name',
                           'bio',
                           'email_address',
                           'email_password',

                           'imap_email_host',
                           'imap_email_username',
                           'imap_email_password',
                           'imap_email_port'
                           ]

    service = models.CharField(choices=SERVICES,
                               default='instagram',
                               max_length=50,
                               db_index=True
                               )
    auth_code = models.CharField(max_length=255, blank=True, null=True)
    customer = models.ForeignKey(Customer,
                                 null=True,
                                 blank=False,
                                 on_delete=models.deletion.CASCADE
                                 )

    username = models.CharField(max_length=50,
                                blank=False,
                                null=False,
                                db_index=True
                                )

    password = models.CharField(max_length=50,
                                blank=False,
                                null=False
                                )
    phone_number=models.IntegerField(blank=True,null=True, default=00000000000)
    proxy_url=models.CharField(max_length=600,blank=True,null=True)
    email_address = models.EmailField(max_length=254,
                                      blank=True,
                                      null=True,
                                      db_index=True,
                                      default='none@gmail.com'
                                      )

    email_password = models.CharField(max_length=100,
                                      blank=True,
                                      null=True
                                      )

    recovery_email = models.EmailField(
        max_length=254,
        blank=True,
        null=True,
        default='none@gmail.com'
    )
    logged_in_on_servers=models.ForeignKey(Server,on_delete=models.SET_NULL,null=True)
    imap_email_host = models.CharField(max_length=100,
                                       blank=True,
                                       null=True
                                       )

    imap_email_username = models.CharField(max_length=100,
                                           blank=True,
                                           null=True
                                           )

    imap_email_password = models.CharField(max_length=100,
                                           blank=True,
                                           null=True
                                           )

    imap_email_port = models.CharField(max_length=6,
                                       blank=True,
                                       null=True
                                       )

    followers = models.PositiveIntegerField(default=0)

    following = models.PositiveIntegerField(default=0)

    post_count = models.PositiveIntegerField(default=0)



    bio = models.TextField(blank=True, null=True, max_length=500)

    first_name = models.CharField(blank=True, null=True, max_length=100)

    last_name = models.CharField(blank=True, null=True, max_length=100)

    

    created_on = models.DateTimeField(default=timezone.now)

    # TODO create a default storage class to use for cookies
    
    email_provider = models.ForeignKey(EmailProvider,
                                       blank=True,
                                       null=True,
                                       related_name='login_profiles',
                                       on_delete=models.SET_NULL
                                       )

    
    state = models.CharField(
        choices=(
            ('active', 'Active'),
            ('disabled', 'Disablled')
        ),
        default='active',
        max_length=50
    )
    
    last_run_at = models.DateTimeField(
        auto_now=False, auto_now_add=False,
        editable=False, blank=True, null=True,
    )
    
    challenged = models.BooleanField(default=False, help_text="Indicates if the bot is currently challenged.")
    logged_in = models.BooleanField(default=False)
    is_challenged = models.BooleanField(default=False)
    is_scraper = models.BooleanField(default=False)
    scraped_so_far = models.IntegerField(default=0)
    interactions_so_far = models.IntegerField(default=0)
    successful_api_requests = models.IntegerField(default=0)
    failed_api_requests = models.IntegerField(default=0)

    class Meta:
        unique_together = ('customer', 'username')
        unique_together = ('customer', 'username')
        verbose_name = "Bot"

    def should_run(self, request_type='campaign'):
        """_summary_

        Args:
            request_type (str, optional): _description_. Defaults to 'campaign'.

        Returns:
            _type_: _description_
        """
        if not self.last_run_at:
            last_run_at = timezone.now()
            self.last_run_at = last_run_at
            self.save()
        else:
            last_run_at = self.last_run_at
        if hasattr(self, 'op_session') and self.op_session.state == 'running':
            return False
        if self.schedule:
            return self.schedule.is_due(last_run_at).is_due
        return False

    @property
    def schedule(self):
        if self.interval:
            return self.interval.schedule
        if self.crontab:
            return self.crontab.schedule



    def has_device(self): pass

    def assign_device(self): pass  
    def start(self, task: str):
        """_summary_

        Args:
            task (str): _description_

        Returns:
            _type_: _description_
        """
        if task == 'start_campaign' and self.campaign:
            pass
            #from operationsession.tasks import start_campaign_bot
            #return start_campaign_bot.delay(self.campaign.id, self.id)
        return True

    """ def stop(self, notify=False):
        _summary_

        Args:
            notify (bool, optional): _description_. Defaults to False.
        
        #from operationsession.tasks import stop_bots
        #stop_bots.delay([self.id])
        if notify:
            Notification.add_user_notification(self.campaign.customer.user,
                                               "Processing request to stop profile %s" % self.login_profile.username,
                                               ) """

    @classmethod
    def get_good_bots(cls, **kwargs):
        """_summary_

        Returns:
            _type_: _description_
        """
        query = {
            'login_profile__isnull': False,
            'login_profile__account_disabled': False,
            'login_profile__under_review': False
        }
        query.update(kwargs)
        return cls.objects.filter(**query)

    def __str__(self):
        name = self.username or self.display_name
        if name:
            return name 
        if self.login_profile:
            return self.login_profile.username 
        
        return f'ChildBot::{self.id}'


class Proxy(BaseModel):
    uuid=models.UUIDField(blank=False,null=True,unique=True)
    type = models.CharField(max_length=20, choices=[('static', 'Static'), ('rotating', 'Rotating')], default='static')
    provider = models.CharField(max_length=50,null=True)  # No choices, free text input
    proxy_url = models.CharField(max_length=200)  # Store in username:password:ip:port or ip:port format

    def __str__(self):
        return f"{self.provider} - {self.type} - {self.masked_ip()}"

    def masked_ip(self):
        """Masks the IP address for display purposes (security)."""
        parts = self.proxy_url.split(":")
        if len(parts) > 2:  # Contains username/password
            return f"{parts[-2]}:{parts[-1]}"  # Return only IP and port
        else:
            return self.proxy_url  # No username and password, return IP:port

    def get_ip_port(self):
        """Returns the ip:port part of ip_address"""
        parts = self.proxy_url.split(":")
        if len(parts) > 2:  # Contains username/password
            return f"{parts[-2]}:{parts[-1]}"
        else:
            return self.proxy_url

    def get_credentials(self):
        """Returns username and password as a tuple or None, None if not present"""
        parts = self.proxy_url.split(":")
        if len(parts) > 2:  # username:password:ip:port
            return parts[0], parts[1]
        return None, None

    class Meta:
        
        verbose_name_plural = "proxies"

    @classmethod
    def calculate_lock_duration(cls, proxy):
        import random
        if proxy.proxy_type == "rotating_proxy":
            return (random.randint(3, 5) * 60)
        return cls.LOCK_DURATION

    @classmethod
    def get_proxy_by_location(cls, location: str, **kwargs):
        """[summary]

        Args:
            location (str): [description]

        Returns:
            [type]: [description]
        """
        kwargs.update(
            {
                'proxy_blacklisted': False,
                'proxy_country': location
            }
        )
        return cls.objects.filter(
            **kwargs
        ).annotate(
            proxy_pk=F('pk')
        ).values('proxy_url', 'pk', 'proxy_pk', 'proxy_country', 'proxy_city')

    @classmethod
    def get_proxy_by_config(cls, customer: Customer, config: Dict[str, str]):
        """[summary]

        Args:
            customer (Customer): [description]
            config (Dict[str, str]): [description]

        Returns:
            [type]: [description]
        """
        proxy_type = config.get('type', None)
        if not proxy_type:
            return []

        query = {
            "proxy_blacklisted": False,
            "proxy_type": proxy_type,
            "customer": customer
        }

        location = config.get('location', None)
        if location is not None:
            query['proxy_country'] = location

        provider = config.get("provider", None)
        if provider is not None:
            query['provider'] = provider

        proxy_protocol = config.get("proxy_protocol", None)
        if proxy_protocol is not None:
            query['proxy_protocol'] = proxy_protocol

        return cls.objects.filter(
            **query
        ).annotate(
            proxy_pk=F('pk')
        ).values('proxy_url',
                 'pk',
                 'proxy_pk',
                 'proxy_country',
                 'proxy_city'
                 )

    
    def use_count(self,service):
        """[summary]

        Returns:
            [type]: [description]
        """
        return self.login_profiles.filter(service=service).count()

    @property
    def available(self):
        """[summary]

        Returns:
            [type]: [description]
        """
        if self.is_locked():
            return False
        if not self.last_used_at:  # hasn't ran
            return True
        return (timezone.now() - self.last_used_at).total_seconds() > self.LOCK_DURATION

    def __str__(self):
        return f'{self.proxy_url}'  
from django.db import models

class SyncedSheet(models.Model):
    google_spreadsheet_url = models.URLField(max_length=200, unique=True)
    spreadsheet_name = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    details = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"Sync at {self.created_at} - {self.spreadsheet_name or self.shortened_link()}"

    def shortened_link(self):
        try:
            parts = self.google_sheet_link.split('/d/')
            if len(parts) > 1:
                spreadsheet_id = parts[1].split('/')[0]
                return f".../{spreadsheet_id}/..."
            return self.google_sheet_link
        except IndexError:
            return self.google_sheet_link

    class Meta:
        ordering = ['-created_at']
class CampaignTextContent(models.Model):
    name=models.CharField(blank=True,null=True,max_length=5000)
    comment_list = models.TextField(blank=True, null=True)
    influencer_profile = models.TextField(blank=True,null=True)
    welcome_message=models.TextField(blank=True,null=True)
    followup_message=models.TextField(blank=True,null=True)
    reachout_message=models.TextField(blank=True,null=True)
    response_to_reachout_message=models.TextField(blank=True,null=True)
    target_hashtag=models.TextField(blank=True,null=True)
    target_location=models.JSONField(blank=True,null=True)
    message_list = models.TextField(blank=True, null=True)

    def __str__(self) -> str:
        return self.name if self.name else ''
class TargetSettings(models.Model):
    name=models.CharField(unique=True,max_length=5000)
    should_have_highlights=models.BooleanField(default=False)
    should_be_public=models.BooleanField(default=True)
    min_followers=models.IntegerField(blank=True,null=True)
    max_followers=models.IntegerField(blank=True,null=True)
    should_have_post_in_period=models.IntegerField(blank=True,null=True)

    def __str__(self):
        return self.name

class Settings(BaseModel):
    uuid=models.UUIDField(blank=False,null=True,unique=True)
    name=models.CharField(unique=True,max_length=5000)
    start_time = models.DateTimeField('start_time', blank=True, null=True)

    expires = models.DateTimeField('expires', blank=True, null=True)
    delay_range = models.CharField(max_length=20, blank=True, null=True)
    max_interactions_per_runtask=models.IntegerField(default=5,null=False,blank=False)
    delay_between_runtasks=models.IntegerField(default=1,null=False,blank=False)
    created_on = models.DateTimeField(default=timezone.now, null=True)
    behavior = models.JSONField(default={
    'with_new_followers': 'welcome_message,like_3,comment_3,share_post',
    'with_target': 'follow',
    'with_liker': 'like',
    'with_commenter': 'like_comment',
    'follow_per_session': 10,
    })
    max_scrape_bots=models.IntegerField(default=2)

    def __str__(self):
        return self.name
class Sharing(models.Model):
    name=models.CharField(unique=True,max_length=5000)
    link=models.URLField(blank=True,null=True)
    target_posts=models.CharField(max_length=5000,blank=True,null=True)

    def __str__(self):
        return self.name
class ScrapeTask(BaseModel):

    service=models.CharField(choices=SERVICES,max_length=5000,blank=False,null=False)
    customer = models.ForeignKey(Customer,
                                 null=True,
                                 blank=True,
                                 on_delete=models.deletion.CASCADE
                                 )
    
    name=models.CharField(blank=True,null=True,max_length=5000)
   
    internal_state=models.CharField(choices=internal_states,max_length=500,blank=True,null=True)
    input=models.TextField(blank=False,null=False)
    os=models.CharField(choices=(('android','Android'),('browser','Browser')),max_length=5000,blank=False,null=False,default='android')
    childbots=models.ManyToManyField(ChildBot,related_name='scrape_task')
    localstore=models.BooleanField(default=False)
    threading=models.BooleanField(default=False)
    max_threads=models.IntegerField(default=5)
    max_requests_per_day=models.IntegerField(default=100)
    uuid=models.UUIDField(unique=True,blank=True,null=True)
    requests_sent = models.IntegerField(default=0)
    media_downloaded = models.IntegerField(default=0)
    media_stored = models.IntegerField(default=0)
    failed_request_count = models.IntegerField(default=0)
    successful_request_count = models.IntegerField(default=0)
    scraped_so_far=models.IntegerField(default=0)
    bot_status=models.JSONField(blank=True,null=True,default={})
    def __str__(self):
        return self.name
    
class DemoGraphic(models.Model):
    name=models.CharField(unique=True,max_length=5000)
    scrape_tasks=models.ManyToManyField(ScrapeTask)

    def __str__(self):
        return self.name
ITEMS_SCHEMA ={
    'type': 'array',
    'title': 'Player Configuration',
    'items': {
        'type': 'object',
        "properties": {
    "Page": {
      "oneOf": [
        {
          "type": "object",
          "title": "HomePage",
          "properties": {
            "max_swipes": {
              "type": "number",
              
            },

            "delay_between_each_swipe":{
              "type": "integer",
              "value":100,
              "help_text":'Enter value in seconds'

            },

            "like_posts_randomly":{
              "type": "boolean",
              "value":100,
              

            },
            "comment_on_posts_randomly":{
              "type": "boolean",
              "value":100,
              

            },
            "open_comments_and_scroll":{
              "type": "boolean",
              "value":100,
              

            },
            "max_comments_to_read":{
              "type": "integer",
              "value":100,
              

            },
            "bookmark_posts":{
                "type":"boolean",


            },

            "share_posts":{
                "type":"boolean"

            },
            "like_posts_of": {
              "type": "string",
              "value":100,
            },
            "repeat_after": {
              "type": "string",
              "value":100,
              "help_text":'Enter value in hours. leave empty for one time task'
            },
          "data_point": {
              "type": "string",
             
                'default': 'explore_home_page', # default value for new items
                
            },
            "end_point": {
              "type": "string",
             
                'default': 'interact', # default value for new items
               
            },
          }
        },
        {
          "type": "object",
          "title": "Explore Page",
          "properties": {
             "max_swipes": {
              "type": "number",
              
            },
            "max_open_posts": {
              "type": "number",
              "value":100,
              "help_text":"Max Number of Post clicks after opening Explore Page"
            },

             "max_swipes_in_open_posts": {
              "type": "number",
              "value":10,
              "help_text":"Max number of swipes after opening Post"
            },
             "max_swipes": {
              "type": "number",
              "value":10,
              "help_text":"Max number of swipes in Explore Page"
            },
            "max_likes": {
              "type": "number",
              "value":10,
            },
             "max_follows": {
              "type": "number",
              "value":10,
            },
             "repeat_after": {
              "type": "string",
              "value":100,
              "help_text":'Enter value in hours. leave empty for one time task'
            },
          "data_point": {
              "type": "string",
             
                'default': 'explore_explore_page', # default value for new items
                'readonly': False
            },
            "end_point": {
              "type": "string",
             
                'default': 'interact', # default value for new items
                'readonly': False
            },
          }
        },
        {
          "type": "object",
          "title": "Story Page",
          "properties": {
            "max_swipes": {
              "type": "number",
              
            },
            "max_likes": {
              "type": "number",
              "value":100,
            },
            "like_stories_of": {
              "type": "string",
              "value":100,
              "help_text":"Enter Username separated by comma"
            },
          "data_point": {
              "type": "string",
             
                'default': 'watch_story', # default value for new items
                'readonly': False
            },
            "end_point": {
              "type": "string",
             
                'default': 'interact', # default value for new items
                'readonly': False
            },
          }
        },
         {
          "type": "object",
          "title": "Reels Page",
          "properties": {
            "max_swipes": {
              "type": "number",
              
            },

            "delay_between_each_swipe":{
              "type": "integer",
              "value":100,
              "help_text":'Enter value in seconds'

            },

            "like_posts_randomly":{
              "type": "boolean",
              "value":100,
              

            },
            "comment_on_posts_randomly":{
              "type": "boolean",
              "value":100,
              

            },
            "open_comments_and_scroll":{
              "type": "boolean",
              "value":100,
              

            },
            "max_comments_to_read":{
              "type": "integer",
              "value":100,
              

            },
            "bookmark_posts":{
                "type":"boolean",


            },

            "share_posts":{
                "type":"boolean"

            },
            "like_posts_of": {
              "type": "string",
              "value":100,
            },
            "repeat_after": {
              "type": "string",
              "value":100,
              "help_text":'Enter value in hours. leave empty for one time task'
            },
             "check_audio": {
              "type": "string",
              "value":100,
              "help_text":'Enter value in hours. leave empty for one time task'
            },
           "data_point": {
              "type": "string",
             
                'default': 'watch_reels', # default value for new items
                'readonly': False
            },
            "end_point": {
              "type": "string",
             
                'default': 'interact', # default value for new items
                'readonly': False
            },
          }
        },
        {
          "type": "object",
          "title": "Messenger Page",
          "properties": {
           

            "open_messenger_on_new_messages_only":{
              "type": "boolean",
              #"value":100,


            },

            "reply_to_messages":{
              "type": "boolean",
              #"value":100,
              

            },
           
            "check_requests":{
              "type": "boolean",
              #"value":100,
              

            },
            
            "repeat_after": {
              "type": "string",
              "value":100,
              "help_text":'Enter value in hours. leave empty for one time task'
            },
            
           "data_point": {
              "type": "string",
             
                'default': 'check_messenger', # default value for new items
                'readonly': False
            },
            "end_point": {
              "type": "string",
             
                'default': 'interact', # default value for new items
                'readonly': False
            },
          }
        },
        {
          "type": "object",
          "title": "Search User and Interact",
          "properties": {
            "max_interactions_per_day": {
              "type": "number",
              
            },
            "open_posts_of_targets_and_like": {
              "type": "boolean",
            
            },

            "share_latest_post_of_target": {
              "type": "boolean",
              "help_text":"Share Latest Post of Target as story"
             
              
            },
            "send_reachout_message": {
              "type": "boolean",
              "help_text":"Send Reachout Message to Target",
              
             
              
            },

            "open_highlights_of_target": {
              "type": "boolean",
              "help_text":"Send Reachout Message to Target",            
            },
            'follow_target':
            {
                "type": "boolean",
              "help_text":"Check to Follow Each Target",

            },
         "data_point": {
              "type": "string",
             
                'default': 'search_user_and_interact', # default value for new items
                'readonly': False
            },
            "end_point": {
              "type": "string",
             
                'default': 'interact', # default value for new items
                'readonly': False
            },
          }
        },
        {
          "type": "object",
          "title": "Cold Outreach ",
          "properties": {
            "max_dms_per_day_per_bot": {
              "type": "number",
              
            },
            "open_profile_and_send_dm": {
              "type": "boolean",
            
            },
            "open_posts_of_targets_and_like": {
              "type": "boolean",
            
            },
            "max_follow_ups": {
              "type": "number",
            
            },
            "gap_between_each_follow_up": {
              "type": "number",
              "help_text":"Enter the gap between each followup in hours"
            
            },
            "should_reply": {
              "type": "boolean",
            
            },
            "obtain_targets_from_file":
            {
                "type":"string",
                "help_text":"Enter the link to Google Spreadsheet containing targets.It should only contain 1 column. Share the file to 'testo-1@eng-electron-326810.iam.gserviceaccount.com'"

            },

           
        

           "data_point": {
              "type": "string",
             
                'default': 'send_dm', # default value for new items
                'readonly': False
            },
            "end_point": {
              "type": "string",
             
                'default': 'interact', # default value for new items
                'readonly': False
            },
          }
        },
        
         {
          "type": "object",
          "title": "Bulk Task (SMM) ",
          "properties": {
            "activity_to_perform": {
              "type": "string",
              "help_text":"follow,dm,like"
              
            },
            "target_profile": {
              "type": "string",
              "help_text":"username of the recipient"
            
            },
            "target_post": {
              "type": "string",
              "help_text":"link of the post"
            
            },
            "os": {
              "type": "string",
              "help_text":"android,browser"
            
            },
            "quantity": {
              "type": "number",
            
            },
           
           

           
        

           "data_point": {
              "type": "string",
             
                'default': 'bulk_task', # default value for new items
                'readonly': False
            },
            "end_point": {
              "type": "string",
             
                'default': 'interact', # default value for new items
                'readonly': False
            },
          }
        },
         
        {
          "type": "object",
          "title": "Unfollow",
          "properties": {
            "unfollow_after": {
              "type": "number",
              "help_text":"Enter the max number of followings after which to start unfollowing"
              
            },
            "max_unfollows_per_run": {
              "type": "number",
              "value":100,
              "help_text":"The standard number of following count after which to stop unfollowing"
             
            },
            "repeat_after": {
              "type": "number",
              "value":100,
              "help_text":"Enter the duration in hours after which to repeat the task every day."
             
            },
          "name": {
              "type": "string",
             
                'default': 'unfollow', # default value for new items
                'readonly': False
            },
             "data_point": {
              "type": "string",
             
                'default': 'unfollow_users', # default value for new items
                'readonly': False
            },
            "end_point": {
              "type": "string",
             
                'default': 'interact', # default value for new items
                'readonly': False
            },
          }
        },
      ]
    },

  }
    }
}

MONITOR_SCHEMA=   {
    'type': 'array',
    'items':{
    'oneOf': [
        {
            "type": "object",
          "title": "User Profile",
            'properties': {
               "type": {
              "type": "string",
             
                'default': 'user', # default value for new items
                'readonly': False
              
            },
                "usernames":{"type":"string"},
                'onEvent': {'type': 'array','items': {
                'oneOf':[{"type":"object","title":"On New Post","properties":{"share_as_story":{"type":"boolean"},
                          "like":{"type":"boolean"},"monitor_after":{"type":"integer","help_text":"Enter value in hours"},
                          "event":{ "type": "string",
             
                                  'default': 'on_new_post', # default value for new items
                                  'readonly': False}}
                          },
                         
                         
                         {"type":"object","title":"On New Follower","properties":{"send_welcome_message":{"type":"boolean"},"message":{"type":"text"},
                      "monitor_after":{"type":"integer","help_text":"Enter value in hours"},
                      "event":{ "type": "string",
             
                                  'default': 'on_new_follower', # default value for new items
                                  'readonly': False}
                      }
                          
                         }
                          
                          ]
            }},
            

            },
            'required': ['usernames']
            
        },

        
    ],
    
    }
    
}

from django_jsonform.models.fields import JSONField
class Audience(BaseModel):
    service=models.CharField(choices=SERVICES,blank=False,null=False,default='instagram',max_length=500)
    name=models.CharField(blank=False,null=False,unique=True,max_length=500)
    scrape_tasks=models.ManyToManyField(ScrapeTask,blank=False,null=False)
    # cleaning_configuration=models.JSONField(default={},blank=False,null=False)
    # enrichment_configuration=models.JSONField(default={},blank=False,null=False)
    workflow_steps = models.JSONField(default={},blank=False,null=False)
    prompt = models.TextField(blank=True,null=True)
    storage_configuration=models.JSONField(default={},blank=False,null=False)
    uuid=models.UUIDField(unique=True,default=uuid.uuid1())
    
    def __str__(self):
        return self.name
    
    
class BulkCampaign(BaseModel):
    """_summary_

    Args:
        UpdateMixin (_type_): _description_
        RuntimeStatusMixin (_type_): _description_
        models (_type_): _description_

    Returns:
        _type_: _description_
    """

    class Meta:
        verbose_name = "AutomationTask"
    
 
       
       
    
    
         
    internal_states = (
        ('active', 'Active'),
        ('in_active', 'In-Active'),
        ('expired', 'Expired'),
        ('complete', 'Complete')
    )
    campaign_states = (
        ('launched', 'Launched'),
        ('stopping', 'Stopping'),
        ('stopped', 'Stopped'),
        ('paused', 'Paused'),
        ('deleted', 'Deleted'),
        ('draft', 'Draft')
    )
    uuid=models.CharField(default=str(uuid.uuid1()),unique=True,max_length=50000)
    name = models.CharField(max_length=5000,
                            blank=False,
                            null=False,
                            db_index=True,
                            
                            )
    service = models.CharField(
        max_length=100,
        default='instagram',
        choices=SERVICES,
        db_index=True
    )

    customer = models.ForeignKey(
        Customer,
        blank=True,
        null=True,
        on_delete=models.deletion.CASCADE
    )

    activity_to_perform=JSONField(schema=ITEMS_SCHEMA,        
        )    
    monitor=JSONField(schema=MONITOR_SCHEMA,
            #choices=ACTIVITY_CHOICES,
            #max_length=1000,
            blank=True,
            null=True
           
        )
    os=models.CharField(choices=(('android','Android'),('browser','Browser')),max_length=5000,blank=False,null=False,default='android')
    childbots=models.ManyToManyField(ChildBot,related_name='campaign')
    devices=models.ManyToManyField(Device,blank=True)
    audience=models.ForeignKey(Audience,blank=True,null=True,on_delete=models.SET_NULL)
    filters=models.JSONField(blank=True,null=True,default={})
    scrape_tasks=models.ManyToManyField(ScrapeTask,blank=True,related_name='campaign')
    proxies=models.ManyToManyField(Proxy,related_name='proxies',null=True,blank=True)
    #localstore=models.BooleanField(default=False)
    messaging=models.ManyToManyField(CampaignTextContent)
    #demographic=models.ManyToManyField(DemoGraphic)
    proxy_disable=models.BooleanField(default=False)
    target_settings=models.ForeignKey(TargetSettings,on_delete=models.CASCADE,null=True,blank=True)
    sharing=models.ManyToManyField(Sharing,blank=True)
    #settings=models.ManyToManyField(Settings)
    servers = models.ForeignKey(Server, blank=True, null=True, on_delete=models.SET_NULL)
    

    
    blacklist=models.TextField(blank=True,null=True)
    required_interactions=models.IntegerField(default=10000)
    launch_datetime = models.DateTimeField(blank=True, null=True)
    stop_datetime = models.DateTimeField(blank=True, null=True)
    
    internal_state = models.CharField(
        choices=internal_states,
        max_length=100,
        default='in_active'
    )
    
    campaign_state = models.CharField(
        choices=campaign_states,
        max_length=100,
        default='draft'
    )

    is_completed = models.BooleanField(default=False)

    is_deleted = models.BooleanField(default=False)

    

    last_run_at = models.DateTimeField(
        auto_now=False,
        auto_now_add=False,
        editable=False,
        blank=True,
        null=True,
    )

    total_run_count = models.PositiveIntegerField(
        default=0,
        editable=False,
    )

    

    media_id = models.CharField(max_length=100, blank=True, null=True)

    comment_id = models.CharField(max_length=100, blank=True, null=True)

    
    
    # Add Field tracking
    '''state_tracker = FieldTracker(
        fields=[
            'internal_state',
            'is_deleted',
            'campaign_state',
        ]
    )'''

    @property
    def state(self):
        if self.is_completed:
            return 'COMPLETE'
        if self.campaign_state == 'launched':
            return 'LAUNCHED'
        if self.campaign_state == 'paused':
            return 'PAUSED'
        if self.campaign_state in ['stopped', 'stopping']:
            return 'STOPPED'
        return 'DRAFT'

    @property
    def schedule(self):
        if self.interval:
            return self.interval.schedule
        if self.crontab:
            return self.crontab.schedule

    def should_run(self) -> bool:
        """_summary_

        Returns:
            bool: _description_
        """
        if not self.last_run_at:
            last_run_at = timezone.now()
            self.last_run_at = last_run_at
            self.save()
        else:
            last_run_at = self.last_run_at
        if (
            not self.campaign_state in ['launched', 'stopping']
            or  self.internal_state in ['in_active', 'expired']
        ):
            return False

        if self.start_time is not None:
            if timezone.now() < self.start_time:
                return False

        if self.expires is not None:
            if timezone.now() > self.expires:
                self.internal_state = 'expired'
                self.save()
                return False

        interaction_count = self.interactions.count()
        
        if interaction_count < self.quantity:
            quota = self.get_quota()
            now = timezone.now()
            end = now - timedelta(hours=quota[1])
            interactions_by_quota = self.interactions.filter(
                interaction_time__range=[end, now]
            ).count()
            
            if interactions_by_quota >= quota[0]:
                return False

        elif interaction_count >= self.quantity:
            self.is_completed = True
            self.save()
            self.stop()
            return False

        return True

    def get_quota(self) -> Tuple[int]:
        # should return the max number of interactions
        # this campaign should receive within a certain period of
        # time in hours
        # returns (amount,time)
        return (250, 24)

    def max_bots_per_run(self):
        # return the maximum number of bots to be used
        # during each run
        return 50

    def max_concurrent_instances(self):
        # return the max  number of instances
        # that can run this campaign at the same
        # time

        return 1

    def max_interaction_by_bot(self):
        """_summary_

        Returns:
            _type_: _description_
        """
        if self.activity_to_perform == "dm":
            return 10
        
        return 1

    def max_auto_tasks(self):
        # return the total number of allowed  autotasks (pending+running)
        quantity = self.quantity or 0
        if quantity == 0 or quantity <= 10:
            return 1
        return quantity/10

    def launch(self, notify=False):
        """_summary_

        Args:
            notify (bool, optional): _description_. Defaults to False.
        """
        self.campaign_state = 'launched'
        self.internal_state = 'active'
        self.launch_datetime = timezone.now()
        #from operationsession.tasks import process_lunch_bulkcampaign
        #process_lunch_bulkcampaign.delay(self.id, notify=notify)
        self.save()

    def stop(self):
        """_summary_
        """
        if self.campaign_state == 'stopping':
            return
        self.campaign_state = 'stopping'
        self.stop_datetime = timezone.now()
        #from operationsession.tasks import process_stop_bulkcampaign
        #process_stop_bulkcampaign.delay(self.id)
        self.save()

    def pause(self):
        """[summary]
        """
        self.campaign_state = 'paused'
        self.save()

    def lock_target(self, target: str):
        """_summary_

        Args:
            target (str): _description_

        Returns:
            _type_: _description_
        """
        response = {
            'locked': False,
            'duration': 0
        }
        try:
            duration = (30*60)
            self.lock()
            
            _cache_key = f'targets.{self.id}.{target}'
            #cache.delete(_cache_key)
            _cache_value = {
                'locked_at': time.monotonic()
            }
            if cache.add(_cache_key, _cache_value, duration):
                response = {'duration': duration,
                            'locked': True
                            }
            
        except Exception as exc:#ConcurrentModificationError as exc:
            print(exc)
        finally:
            if self.is_locked():
                self.unlock()
        return response

    @classmethod
    def get_launched_campaigns(cls):
        """_summary_

        Returns:
            _type_: _description_
        """
        campaigns = cls.objects.annotate(
            runtask_count=Count(
                "runtasks",
                filter=Q(
                    runtasks__is_deleted=False
                )
            ),
            interaction_count=Count(
                "interactions"
            )
        ).filter(
            internal_state='active',
            campaign_state__in=('launched','stopping'),
            is_deleted=False,
            is_completed=False
        ).order_by('created_on', '-runtask_count')
        return campaigns
    
    def __str__(self):
        return self.name 

class Task(BaseModel):
    
    uuid=models.CharField(default=str(uuid.uuid1()),unique=True,max_length=50000)
    ref_id=models.CharField(verbose_name='reference id of the job i.e. campaign or audience or scrape task',blank=True,null=True,max_length=500)
    service = models.CharField(choices=SERVICES,
                               default='instagram',
                               max_length=50,
                               db_index=True
                               )
    dependent_on=models.ForeignKey('self',blank=True,related_name='dependents',on_delete=models.CASCADE,null=True)
    interact=models.BooleanField(default=False)
    os=models.CharField(max_length=500,blank=False,null=False,choices=(('android','android'),('browser','browser')))
    data_point = models.CharField(blank=False,
                                null=False,
                                max_length=500
                               )
    end_point = models.CharField(blank=False,
                                null=False,
                                max_length=500
                               )
    input=models.CharField(blank=True,
                                null=True,
                                max_length=500
                               )
    targets=models.JSONField(blank=True,null=True)
    condition=models.CharField(blank=True,null=True,max_length=500) 
    profile=models.TextField(blank=True,
                          null=True)
    alloted_bots=models.TextField(blank=True,
                          null=True)
    device=models.TextField(blank=True,
                          null=True)
    targets=models.TextField(blank=True,null=True)
    add_data=models.JSONField(blank=True,null=True)
    server=models.ForeignKey(Server,blank=True,null=True,on_delete=models.SET_NULL)
    repeat=models.BooleanField(default=False)
    repeat_duration=models.CharField(max_length=20,blank=True,null=True)
    status=models.CharField(max_length=100,default='pending',choices=(('pending','pending'),('running','running'),('failed','failed'),('completed','completed')))
    last_state_changed_at=models.FloatField(blank=True,null=True)
    report=models.BooleanField(default=False)
    retries_count=models.IntegerField(default=0)
    paused=models.BooleanField(default=False)
    _delete=models.BooleanField(default=False)
    registered=models.BooleanField(default=False)
    created_at = models.DateTimeField(default=dt.datetime.now())
    

    def __str__(self):
        return self.ref_id                

    
    def __str__(self):
        return str(self.id)

        return self.name
class Job(models.Model):
    name = models.CharField(max_length=255)
    tasks = models.ManyToManyField(Task)
    depends_on = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='dependencies')
    status = models.CharField(max_length=20, default="PENDING", choices=[
        ("PENDING", "Pending"),
        ("RUNNING", "Running"),
        ("COMPLETED", "Completed"),
        ("FAILED", "Failed"),
    ])
    # ... other job fields

    def __str__(self):
        return self.name

    def check_tasks_completed(self):
        """Checks if all associated tasks are completed and updates job status."""
        all_completed = all(task.status == "COMPLETED" for task in self.tasks.all())
        if all_completed:
            self.status = "COMPLETED"
            self.save()
            return True
        return False

class Workflow(models.Model):
    name = models.CharField(max_length=255)
    jobs = models.ManyToManyField(Job)
    # ... other workflow fields

    def __str__(self):
        return self.name

    def run_next_jobs(self, completed_job):
        """Triggers the execution of jobs that depend on the completed job."""
        dependent_jobs = completed_job.dependencies.filter(status="PENDING")
        for job in dependent_jobs:
            job.status = "RUNNING"
            job.save()
            # Trigger job execution here (e.g., with Celery)
            print(f"Triggering job: {job.name} (dependent on {completed_job.name})")  # Replace with actual execution logic

    def job_completed(self, job):
        """Called when a job within this workflow completes."""
        if job.check_tasks_completed():
            self.run_next_jobs(job)
        else:
            print(f"Job {job.name} has some tasks pending.")  # Log pending tasks

from django.db.models.signals import post_save,m2m_changed ,post_delete # Signal for post-save operations
from django.dispatch import receiver

@receiver(post_delete, sender=BulkCampaign)
def handle_mymodel_delete(sender, instance, **kwargs):
    Task.objects.all().filter(end_point='interact').filter(ref_id=instance.uuid).update(_delete=True)
    Task.objects.all().filter(data_point='condition_handler').filter(ref_id=instance.uuid).update(_delete=True)
@receiver(post_delete, sender=Audience)
def handle_mymodel_delete(sender, instance, **kwargs):
    Task.objects.all().filter(ref_id=instance.uuid).update(_delete=True)
    
@receiver(post_delete, sender=ChildBot)
def handle_mymodel_delete(sender, instance, **kwargs):
    Task.objects.all().filter(profile=instance.username).update(_delete=True)
    
        
#m2m_changed.connect(post_save_handler, sender=BulkCampaign.childbots.through)    
s={
    'type': 'dict', # or 'object'
    'keys': { # or 'properties'
        'country_slug': {
            'type': 'string'
        },
        'city_id': {
            'type': 'string'
        },
        
    },
    'required': ['country_slug','city_id']
}
class Todo(BaseModel):
    uuid=models.UUIDField(blank=True,null=True,max_length=500,unique=True)
    service=models.CharField(choices=SERVICES,blank=False,null=False,default='instagram',max_length=500)
    name = models.CharField(max_length=255)
    #os=models.CharField(choices=(('android','android'),('browser','browser')))
    caption = models.TextField(blank=True)
    type=models.CharField(choices=(('post','Post'),('edit_profile','edit_profile')),max_length=500,default='post')
    target_location=JSONField(schema=s,
            #choices=ACTIVITY_CHOICES,
            #max_length=1000,
            blank=True,
            null=True
           
        )
    music = models.CharField(max_length=2550, blank=True)  # Store music URL  
    file = models.FileField(upload_to='media/todos/')
    google_drive_root_folder_name=models.CharField(blank=True,null=True,max_length=500)
    repeat=models.BooleanField(default=False)
    repeat_after=models.IntegerField(help_text='Enter the number of hours to repeat the task after',blank=True,null=True)
    childbots=models.ManyToManyField(ChildBot)
    
    def __str__(self):
        return self.name

class Log(models.Model):
    uuid=models.UUIDField(blank=True,null=True,default=uuid.uuid1())
    
    timestamp=models.DateTimeField(default=datetime.now())
    message=models.TextField()
    label=models.CharField(max_length=5000)
    end_point=models.CharField(max_length=500)


    def __str__(self):
        return self.message

class DataHouseSyncStatus(models.Model):
    model_name = models.CharField(max_length=255)
    object_id = models.UUIDField(null=True)
    operation = models.CharField(max_length=50, choices=[('CREATE', 'CREATE'), ('UPDATE', 'UPDATE'), ('DELETE', 'DELETE')])
    created_at = models.DateTimeField(auto_now_add=True)
    registered=models.BooleanField(default=False)
    worker=models.ForeignKey(Server,blank=True,null=True,on_delete=models.SET_NULL)


class AnalysisResult(models.Model):
    name = models.CharField(max_length=255, db_index=True)  # Name of the analysis (unique if needed)
    datetime = models.DateTimeField(auto_now_add=True, db_index=True)  # When the analysis was run
    data = models.JSONField()  # The analysis results as JSON
    range_start = models.DateTimeField(null=True, blank=True, db_index=True) # Start of the time range analyzed
    range_end = models.DateTimeField(null=True, blank=True, db_index=True)  # End of the time range analyzed

    class Meta:
        ordering = ['-datetime'] # Order by latest analysis first

class Event(models.Model):
    EVENT_TYPES = (
        ('heartbeat', 'Heartbeat'),
        ('resource', 'Resource Usage'),
        # Add other event types as needed
    )
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    server = models.ForeignKey(Server, on_delete=models.CASCADE, related_name='events')
    timestamp = models.DateTimeField()
    payload = models.JSONField()  # Store the actual data as JSON
    received_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.event_type} from {self.server.name} at {self.timestamp}"
    
class Heartbeat(models.Model):
    server = models.ForeignKey(Server, on_delete=models.CASCADE, related_name='heartbeats',null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    hostname = models.CharField(max_length=255)
    os = models.CharField(max_length=255)
    received_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.server.name} - {self.timestamp}"

class ResourceUsage(models.Model):
    server = models.ForeignKey(Server, on_delete=models.CASCADE, related_name='resource_usage',null=True)
    timestamp = models.DateTimeField()
    cpu_percent = models.FloatField()
    memory_percent = models.FloatField()
    disk_percent = models.FloatField()
    received_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.server.name} - {self.timestamp}"
    

class TaskErrorSummary(models.Model):
    task_uuid = models.UUIDField(primary_key=True)
    task_name = models.CharField(max_length=255)
    bot_name = models.CharField(max_length=255, null=True, blank=True)  # new, e.g. profile or bot name
    scrape_task_name = models.CharField(max_length=255, null=True, blank=True)  # new scrape task name
    ref_id = models.UUIDField(null=True, blank=True)
    critical_errors = models.JSONField(default=list)  # List of strings
    attempt_failed_errors = models.JSONField(default=list)
    current_status = models.CharField(max_length=50, default="unknown")  # e.g. running, paused, failed
    issue_status = models.CharField(max_length=50, default="pendding")  # e.g. running, paused, failed
    last_updated = models.DateTimeField(auto_now=True)
    def __str__(self):
        return f"{self.task_name} ({self.current_status}) - {self.task_uuid}"
    
    
    
class Issue(models.Model):
    ISSUE_STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    affected_tasks = models.ManyToManyField('Task', blank=True, related_name='issues')
    
    resolution_data = models.JSONField(blank=True, default=dict, help_text="Data related to the resolution")
    
    resolution_date = models.DateTimeField(null=True, blank=True, help_text="Date and time when issue was resolved")
    
    status = models.CharField(
        max_length=20,
        choices=ISSUE_STATUS_CHOICES,
        default='open',
        help_text="Current status of the issue"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"