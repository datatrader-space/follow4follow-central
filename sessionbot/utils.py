from django.db import models
def convert_uuid_datetime_for_json(model_instance):
    """
    Converts UUIDField and DateTimeField values to JSON-compliant types.

    Args:
        model_instance: An instance of a Django model.

    Returns:
        A dictionary containing the converted field values, or None if model_instance is None.
    """
    if model_instance is None:
        return None

    converted_data = {}
    for field in model_instance._meta.fields:
        field_name = field.name
        field_value = getattr(model_instance, field_name)

        if field_value is None:
            converted_data[field_name] = None
            continue

        if isinstance(field, models.DateTimeField) or isinstance(field,models.DateField):
            converted_data[field_name] =field_value.timestamp() if field_value else None
        elif isinstance(field, models.UUIDField):
            converted_data[field_name] = str(field_value) if field_value else None
        elif isinstance(field, models.ForeignKey):
            related_model_name = field.related_model._meta.model_name # get model name
            if field_value:
                # Use _id convention (most common and usually preferred):
                converted_data[f"{related_model_name}_id"] = field_value.pk  # or str(field_value.pk) if pk is not json compliant
            else:
                converted_data[f"{related_model_name}_id"] = None  # Handle null FKs
        else:
             converted_data[field_name] = field_value
       

    return converted_data
import requests
import json
import uuid
import requests
from django.conf import settings
import requests
import json
import uuid

from django.conf import settings
class DataHouseClient:
    def __init__(self):
        self.base_url = settings.DATA_HOUSE_URL
        self.request_maker=requests
        

    def retrieve(self, object_type, internal_filters=None, external_filters=None, locking_filters=None, lock_results=False, ref_id=None, **kwargs):
        url = f"{self.base_url}datahouse/api/provide/"  # Construct the URL

        payload = {
            "object_type":object_type,
            "filters":{
            "internal_key_filters": internal_filters or [],
            "external_key_filters": external_filters or [],

            "locking_filters": locking_filters or {},
            },
            "lock_results": lock_results,
            "ref_id": ref_id or str(uuid.uuid4()) # Generate ref_id if not provided
        }
        

        try:
            response = self.request_maker.post(url=url,json={'data':payload}) 
            return response.text
            

        except Exception as e:
            print(f"Error in provide: {e}")
            return None  # Or raise the exception if you prefer

    def consume(self, payload):
        url = f"{self.base_url}/datahouse/api/consume"

       
        try:
            response = self.request_maker.post(url=url,json=payload) 
            if response['status']=='success':
                return response['data']
            else:
                return False
            

        except Exception as e:
            print(f"Error in provide: {e}")
            return None  # Or raise the exception if you prefer

