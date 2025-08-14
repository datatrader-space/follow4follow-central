import requests
import uuid
from services.slack.data_house_client import DataHouseClient
from services.slack.end_points import EndPoints
import json

class Slack:
  def run_bot(self, task):
      data_house_client = DataHouseClient(task.get("api_key"),"http://208.109.241.136:8080/datahouse/api")
      try:
          e = EndPoints(data_house_client)
          
          output_data = e.get_required_data_point(**task)
          print(output_data)
          try:
              json_string = json.dumps(output_data)  # Convert to JSON string
          except TypeError as e:
              print(f"Error serializing output data: {e}")
        #   print(json.loads(json_string))
          task_uuid = task.get('uuid')
          payload = {
              "service":"slack",
              "task_uuid":task_uuid,
              "output_data":json.loads(json_string),
              "method":"create",
              "object_type":"output",
              "run_id":str(uuid.uuid1())
          }
        #   print([payload])
        #   result = data_house_client.consume([payload])
        #   print(result)
      except requests.exceptions.RequestException as e:
          print(f"Data House Error: {e}")
task = {
                "service":"slack",
                "end_point":"Messenger",
                "data_point":"send_dm_to_user",
                "api_key":"",
                "ref_id": str(uuid.uuid1()),
                
                "add_data":{
                    "data_source":{
                        "type":"data_house",
                        "object_type":"output",
                        "lock_results":True,
                    },
                    "name":"test",
                    "is_private":True,
                    "channel_id":"C05CX2WU9MY",
                    "user_id":"U098VMEG552",
                    'limit':100,
                    'query':'Arqam',
                    "message":"Hey, you have exceeded time limit for break, today.",
                    "save_data_to_data_house":True,
                    "save_output_as_output":True
                    },
                "repeat":False,
                "repeat_duration":"1m",
                "uuid":str(uuid.uuid1())
            }
# salary = Slack()
# salary.run_bot(task)