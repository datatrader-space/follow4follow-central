from django.shortcuts import render
from django.forms.models import model_to_dict
from django.http import JsonResponse,HttpResponse
from django.http.request import HttpRequest
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from sessionbot.resource_utils import create_resources_from_google_sheets
import ast
import json
# Create your views here.
@csrf_exempt
def createResource(request: HttpRequest) -> JsonResponse:
 
    if request.method == 'POST':
        payload = json.loads(request.body.decode("utf-8"))
        print(payload)
        
            
        r=create_resources_from_google_sheets(**payload)
        print(r)
        response={'status':'success','r':r}
           
    else:
        response = {'status': 'bad_request_type'}
    return HttpResponse(JsonResponse(response, safe=False))
