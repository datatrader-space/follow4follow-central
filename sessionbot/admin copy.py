

from django.contrib import admin
from django_admin_relation_links import AdminChangeLinksMixin
from mptt.admin import DraggableMPTTAdmin
from sessionbot.models import BulkCampaign

from django.template.response import TemplateResponse
from django.urls import path
from django.urls import reverse

        #queryset.update(status='p')
class PostAdmin(AdminChangeLinksMixin,
                     
                        admin.ModelAdmin
                        ):
    
    list_select_related = True
    list_display = (
                    'post_link',
                    'caption',
                    'likes_count',
                    'comments_count',
                    'retweets_count',
                    'images',
                    'videos',
                
                    'post_link',
                    'owner',                   
   
                    )
    search_fields = ('caption',
                     'owner__username',
                     )
    list_filter = (
        'service',
        'likes_count',
        'comments_count',

        
    )
class CommentAdmin(AdminChangeLinksMixin,
                     
                        admin.ModelAdmin
                        ):
    
    list_select_related = True
    list_display = (
                    'comment',
                    'post',  
                    'comment_by'       
   
                    )
    search_fields = ('comment',
                     'comment_by',
                     'post__post_link',
                     )
    list_filter = (
        'service',
    )
class FollowAdmin(AdminChangeLinksMixin,
                     
                        admin.ModelAdmin
                        ):
    
    list_select_related = True
    list_display = (
                    'follower_of',
                    'followed_by',  
                           
   
                    )
 
    '''list_filter = (
        'follower_of',
    )'''
    search_fields = ('follower_of__username',
                     
                     )
admin.site.register(Profile,ProfileAdmin)
admin.site.register(ScrapeProgress)
admin.site.register(CommentText)
admin.site.register(Email)
admin.site.register(Post,PostAdmin)
admin.site.register(Location)
admin.site.register(LikeActivity)
admin.site.register(CommentActivity,CommentAdmin)
admin.site.register(SharePostActivity)
admin.site.register(FollowActivity,FollowAdmin)
