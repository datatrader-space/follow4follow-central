import os
import json
import time
#pip install slackclient == 2.9.4 
#pip install python-dotenv == 1.0.0
#The above given modules have been added in requirements.txt 
import slack
import requests
from services.slack.data_house_client import DataHouseClient
from pathlib import Path
# from slack.errors import SlackApiError
# from dotenv import load_dotenv
import datetime
# from services.instagram.parsers import Parser
# from base.storage_sense import Saver
# from services.instagram.register_assistant import RegisterAssistant
# from base.browser import Browser
# from base.googlesheets import GoogleSheet
from datetime import timedelta
token = 'xoxb-5438973802307-6106741338295-eQZnRCMyZnJAEU9gf2IVnEYm'

class EndPoints:
    def __init__(self, data_house_client):
        self.end_point=''
        self.data_point=''
        self.make_request=''
        self.request_maker=''
        self.database=''
        # self.parsers=Parser() 
        # self.register_assistant=RegisterAssistant()
        # self.storage_sense=Saver()
        # self.browser=Browser()
        
    def get_required_data_point(self,**kwargs):
        #self.output.write('Fetching Data for the End-Point'+kwargs.get('end_point')+'data_point'+kwargs.get('data_point'))
        end_point=getattr(self,kwargs.get('end_point'))
        data_point=getattr(end_point,kwargs.get('data_point'))
        return data_point(self,**kwargs)
    
    def internal_get_required_data_point(self,**kwargs):
    
        end_point=getattr(self,kwargs.get('end_point'))
        data_point=getattr(end_point,kwargs.get('data_point'))
        return data_point(self,**kwargs)
    
    class Authorize:
        def __init__(self):
      
            # self.storage_sense = Saver()
            pass
        def load_env_file(self, **kwargs):
            env_path = Path('.') / '.env'
            # load_dotenv(dotenv_path = env_path)
        def web_client(self, **kwargs):
            add_data = kwargs.get('add_data')
            client = slack.WebClient(token = add_data.get('slack_token'))
            return {'web client':client}
    class Channel:
        def __init__(self):
            super().__init__()
            # self.storage_sense=Saver()  
            # self.register_assistant=RegisterAssistant()
        def channel_name(self, **kwargs):
            add_data = kwargs.get('add_data')
            channel_info = client.conversations_info(channel = add_data.get('channel_id'))
            channel_name = channel_info['channel']['name']
            # print(f"Channel Name: {channel_name}\n")
            return {"channel name":channel_name}

        def add_channel(self, **kwargs):
            add_data = kwargs.get('add_data')
            try:
                response = client.conversations_create(name = add_data.get('name'),is_private = add_data.get('is_private'))
                print(response)
                id = response.get('channel').get('id')
                return {"New Channel name":add_data.get('name'),
                        "New Channel ID":id}
            except Exception as e:
                print(e)
        def all_channels(self, **kwargs):
            try:
                response = client.conversations_list(types='public_channel,private_channel')
                if response.get('ok'):
                    channels = response.get('channels')
                    return 'success',channels
            except Exception as e:
                print(e)
        def delete_channel(self, **kwargs):
            add_data = kwargs.get('add_data')
            try:
                response = client.admin_conversations_delete(channel_id=add_data.get('channel_id'))
                return {'Deleted Channel ID':add_data.get('channel_id')}
            except Exception as e:
                print(e)        
        def all_users(self, **kwargs):
            add_data = kwargs.get('add_data')
            e = EndPoints(data_house_client)
            task = {
                'service':'slack',
                'end_point':'Channel',
                'data_point':'channel_name',
                'add_data':{
                    'channel_id':add_data.get('channel_id')
                }
            }
            channel_name = e.internal_get_required_data_point(**task).get('channel name')
            users_data = []
            all_data = []
            response = client.conversations_members(channel = add_data.get('channel_id'))
            # print(response)
            for user in response.get('members'):
                user_ = client.users_info(user = user)
                user_info = user_.get('user')
                all_data.append(user_info)
                users_data.append({
                    'user_name':user_info.get('real_name'),
                    'user_id':user_info.get('id')
                })
            return {'Channel name':channel_name,
                    'channel users':users_data}
            
        def add_user_to_channel(self, **kwargs):
            add_data = kwargs.get('add_data')
            try:
                response = client.conversations_invite(channel = add_data.get('channel_id'),users = add_data.get('user_id'))
                print(response)
                return {'user added':response}
            except Exception as e:
                print(e)
        def remove_user_from_channel(self, **kwargs):
            add_data = kwargs.get('add_data')
            try:
                response = client.conversations_kick(channel = add_data.get('channel_id'), user = add_data.get('user_id'))
                user = add_data.get('user_id')
                if response.get('ok'):
                    return {'user removed':user}
            except Exception as e:
                print(str(e))
        def channel_info(self, **kwargs):
            add_data = kwargs.get('add_data')
            response = client.conversations_info(channel=add_data.get('channel_id'))
            return {'channel info':response.get('channel')}
        def active_channel_users(self, **kwargs):
            add_data = kwargs.get('add_data')
            print(add_data.get('channel_id'))
            e = EndPoints(data_house_client)
            task = {
                'service':'slack',
                'end_point':'Channel',
                'data_point':'channel_name',
                'add_data':{
                    'channel_id':add_data.get('channel_id')
                }
            }
            channel_name = e.internal_get_required_data_point(**task).get('channel name')
            active_users = []
            response = client.conversations_members(channel=add_data.get('channel_id'))
            for user in response.get('members'):
                user_info = client.users_info(user=user)
                info = user_info.get('user')
                if info.get('deleted') == False and info.get('is_bot') == False:
                    active_users.append({
                        'user_name':info.get('real_name'),
                        'user_id':info.get('id')
                    })
            return {"channel name":channel_name,
                    'active users':active_users}            
        def bots_in_channel(self, **kwargs):
            add_data = kwargs.get('add_data')
            e = EndPoints(data_house_client)
            task = {
                'service':'slack',
                'end_point':'Channel',
                'data_point':'channel_name',
                'add_data':{
                    'channel_id':add_data.get('channel_id')
                }
            }
            channel_name = e.internal_get_required_data_point(**task).get('channel name')
            bots = []
            response = client.conversations_members(channel=add_data.get('channel_id'))
            for user in response.get('members'):
                user_info = client.users_info(user=user)
                info = user_info.get('user')
                if info.get('is_bot') == True:
                    bots.append({
                        'user_name':info.get('real_name'),
                        'user_id':info.get('id')
                    })
            return {'channel name':channel_name,
                    'bots':bots}
    class Messenger:
        def __init__(self):
            # super.__init__()
            pass
        def channel_messages(self, **kwargs):
            add_data = kwargs.get('add_data')
            all_messages = []
            latest = add_data.get('latest')
            while True:
                try:
                    result = client.conversations_history(channel=add_data.get('channel_id'), limit = add_data.get('limit'),latest= latest)
                    messages = result.get('messages')
                    if not messages:
                        break
                    all_messages.extend(messages)
                    latest = messages[-1].get('ts')
                except Exception as e:
                    print(e)
                    break
            return {'channel messages':all_messages}
        def search_messages(self, **kwargs):
            add_data = kwargs.get('add_data')
            latest = add_data.get('latest')
            try:
                result = client.search_messages(
                    query=add_data.get('query')
                )
                
                messages = result.get('messages', {}).get('matches', [])
                return {'search results': messages}
            except Exception as e:
                print(e)
                return {'search results': []}
        def dms_to_users(self, **kwargs):
            add_data = kwargs.get('add_data')
            try:
                messages = []
                result = client.conversations_open(users = [add_data.get('user_id')])
                channel_id = result.get('channel').get('id')
                result = client.conversations_history(channel=channel_id, limit = add_data.get('limit'))
                dms = result.get('messages')
                for dm in dms:
                    messages.append((dm.get('text'),dm.get('ts')))
                return {'user dms':messages}
            except Exception as e:
                print(e)
        def send_dm_to_channel(self, **kwargs):
            add_data = kwargs.get('add_data')
            break_limit_post_msg = client.chat_postMessage(channel=add_data.get('channel_id'),text = add_data.get('message'))
            return {"Message to the Chanel":"success"}
        def send_dm_to_user(self, **kwargs):
            add_data = kwargs.get('add_data')
            break_limit_post_msg = client.chat_postMessage(channel=add_data.get('user_id'),
                                                                  text = add_data.get('message'))
            return {'message sent to user':'success'}
        def delete_message(self, **kwargs):
            add_data = kwargs.get('add_data')
            e= EndPoints(data_house_client)
            task = {
                'service':'slack',
                'end_point':'Messenger',
                'data_point':'dms_to_users',
                'add_data':{
                    'user_id':add_data.get('user_id'),
                    'limit':100, 
                }
            }
            user_dms = e.internal_get_required_data_point(**task).get('user dms')
            for msg in user_dms:
                response = client.chat_delete(channel=add_data.get('user_id'),ts=msg[1])

    
data_house_client = DataHouseClient("","http://208.109.241.136:8080/datahouse/api")
e=EndPoints(data_house_client)
t = {
    'service':'slack',
    'end_point':'Authorize',
    'data_point':'web_client',
    'add_data':{
        'slack_token':'xoxb-5438973802307-6106741338295-eQZnRCMyZnJAEU9gf2IVnEYm'
    }
}
client = e.internal_get_required_data_point(**t).get('web client')
# client=e.Authorize().web_client(**{'slack_token':'xoxb-5438973802307-6106741338295-eQZnRCMyZnJAEU9gf2IVnEYm'}).get('web client')
print(client)
channel=e.Channel()
channel.client=client
