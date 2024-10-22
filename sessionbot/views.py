from django.http import JsonResponse, HttpRequest
from django.views.decorators.csrf import csrf_exempt
from django.db import IntegrityError

from sessionbot.resource_utils import create_resources_from_google_sheets
from .models import Device, Server, Proxy
import json
import requests
import logging

@csrf_exempt
def createResource(request: HttpRequest) -> JsonResponse:
    print('yes')
    if request.method == 'POST':
        try:
            payload = json.loads(request.body.decode("utf-8"))
            print("Payload received:", payload)
            
            r = create_resources_from_google_sheets(**payload)
            print("Response from create_resources_from_google_sheets:", r)
            
            response = {'status': 'success', 'data': r}
        except json.JSONDecodeError:
            response = {'status': 'error', 'message': 'Invalid JSON payload'}
        except Exception as e:
            response = {'status': 'error', 'message': str(e)}
    else:
        response = {'status': 'bad_request_type'}
    
    return JsonResponse(response)

@csrf_exempt
def createDeviceResource(request: HttpRequest) -> JsonResponse:
    if request.method == 'POST':
        try:
            payload = json.loads(request.body.decode("utf-8"))
            name = payload.get('name')
            serial_number = payload.get('serial_number')
            info = payload.get('info')
            connected_to_server_id = payload.get('connected_to_server')

            if Device.objects.filter(name=name).exists():
                return JsonResponse({'status': 'error', 'message': 'Device with this name already exists.'}, status=400)

            device = Device.objects.create(
                name=name,
                serial_number=serial_number,
                info=info,
                connected_to_server_id=connected_to_server_id
            )

            crawl_payload = {
                'name': device.name,
                'serial_number': device.serial_number,
                'info': device.info,
            }

            try:
                connected_server = Server.objects.get(id=connected_to_server_id)
                crawl_url = connected_server.public_ip + 'crawl/devices/'
            except Server.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Connected server does not exist.'}, status=404)

            crawl_response = requests.post(crawl_url, json=crawl_payload)

            if crawl_response.status_code != 200:
                print(f"Error sending data to crawl URL: {crawl_response.text}")

            response_data = {
                'name': device.name,
                'serial_number': device.serial_number,
                'info': device.info
            }
            response = {
                'status': 'success',
                'data': response_data
            }
        except Exception as e:
            print(e)
        except json.JSONDecodeError:
            response = {'status': 'error', 'message': 'Invalid JSON payload'}
        except IntegrityError:
            response = {'status': 'error', 'message': 'Device with this name already exists.'}
        except Exception as e:
            response = {'status': 'error', 'message': str(e)}
    else:
        response = {'status': 'bad_request_type'}

    return JsonResponse(response)

logger = logging.getLogger(__name__)
@csrf_exempt
def deleteDeviceResource(request, serial_number: str) -> JsonResponse:
    if request.method == 'DELETE':
        logger.debug(f"Received DELETE request for serial_number: {serial_number}")

        try:
            # Retrieve the device by serial number
            device = Device.objects.get(serial_number=serial_number)
            device.delete()

            connected_to_server_id = device.connected_to_server_id

            if connected_to_server_id:
                try:
                    connected_server = Server.objects.get(id=connected_to_server_id)
                    delete_url = f"{connected_server.public_ip}crawl/devices/{device.serial_number}/"

                    delete_response = requests.delete(delete_url)

                    if delete_response.status_code != 204:
                        return JsonResponse({'status': 'error', 'message': 'Failed to delete from worker.'}, status=500)

                except Server.DoesNotExist:
                    logger.error(f"Connected server with ID {connected_to_server_id} does not exist.")
                    return JsonResponse({'status': 'error', 'message': 'Connected server does not exist.'}, status=404)

            response = {
                'status': 'success',
                'message': 'Device deleted successfully from central and worker.'
            }

        except Device.DoesNotExist:
            logger.error(f"Device with serial number {serial_number} not found.")
            return JsonResponse({'status': 'error', 'message': 'Device not found.'}, status=404)

        except Exception as e:
            logger.error(f"An unexpected error occurred: {str(e)}")
            return JsonResponse({'status': 'error', 'message': 'An internal error occurred while processing your request.'}, status=500)
    else:
        logger.warning(f"Invalid request method: {request.method}")
        return JsonResponse({'status': 'bad_request_type'}, status=400)

    return JsonResponse(response)

logger = logging.getLogger(__name__)

@csrf_exempt
def deleteProxyResource(request, proxy_url: str) -> JsonResponse:
    if request.method == 'DELETE':
        logger.debug(f"Received DELETE request for proxy_url: {proxy_url}")

        try:
            proxy = Proxy.objects.get(proxy_url=proxy_url)
            proxy.delete()

            connected_to_server_id = proxy.connected_to_server_id

            if connected_to_server_id:
                try:
                    connected_server = Server.objects.get(id=connected_to_server_id)
                    delete_url = f"{connected_server.public_ip}crawl/proxies/{proxy.proxy_url}/"

                    delete_response = requests.delete(delete_url)

                    if delete_response.status_code != 204:
                        return JsonResponse({'status': 'error', 'message': 'Failed to delete from worker.'}, status=500)

                except Server.DoesNotExist:
                    logger.error(f"Connected server with ID {connected_to_server_id} does not exist.")
                    return JsonResponse({'status': 'error', 'message': 'Connected server does not exist.'}, status=404)

            response = {
                'status': 'success',
                'message': 'Proxy deleted successfully from central and worker.'
            }

        except Proxy.DoesNotExist:
            logger.error(f"Proxy with proxy URL {proxy_url} not found.")
            return JsonResponse({'status': 'error', 'message': 'Proxy not found.'}, status=404)

        except Exception as e:
            logger.error(f"An unexpected error occurred: {str(e)}")
            return JsonResponse({'status': 'error', 'message': 'An internal error occurred while processing your request.'}, status=500)
    else:
        logger.warning(f"Invalid request method: {request.method}")
        return JsonResponse({'status': 'bad_request_type'}, status=400)

    return JsonResponse(response)

@csrf_exempt
def createProxyResource(request: HttpRequest) -> JsonResponse:
    if request.method == 'POST':
        try:
            payload = json.loads(request.body.decode("utf-8"))
            max_threads = payload.get('max_threads')
            proxy_url = payload.get('proxy_url')
            ua_string = payload.get('ua_string')
            connected_to_server_id = payload.get('connected_to_server')
            is_available = payload.get('is_available')
            proxy_blacklisted = payload.get('proxy_blacklisted')
            provider = payload.get('provider')
            verified = payload.get('verified')
            proxy_type = payload.get('proxy_type')
            proxy_protocol = payload.get('proxy_protocol')

            if Proxy.objects.filter(proxy_url=proxy_url).exists():
                return JsonResponse({'status': 'error', 'message': 'Proxy with this URL already exists.'}, status=400)

            proxy = Proxy.objects.create(
                max_threads=max_threads,
                proxy_url=proxy_url,
                ua_string=ua_string,
                connected_to_server_id=connected_to_server_id,
                is_available=is_available,
                proxy_blacklisted=proxy_blacklisted,
                provider=provider,
                verified=verified,
                proxy_type=proxy_type,
                proxy_protocol=proxy_protocol
            )

            crawl_payload = {
                'max_threads': proxy.max_threads,
                'proxy_url': proxy.proxy_url,
                'ua_string': proxy.ua_string,
                'is_available': proxy.is_available,
                'proxy_blacklisted': proxy.proxy_blacklisted,
                'provider': proxy.provider,
                'verified': proxy.verified,
                'proxy_type': proxy.proxy_type,
                'proxy_protocol': proxy.proxy_protocol,
            }
            
           # print(crawl_payload)

            try:
                connected_server = Server.objects.get(id=connected_to_server_id)
                crawl_url = connected_server.public_ip + 'crawl/proxies/'
            except Server.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Connected server does not exist.'}, status=404)

            crawl_response = requests.post(crawl_url, json=crawl_payload)

            if crawl_response.status_code != 200:
                print(f"Error sending data to crawl URL: {crawl_response.text}")

            response_data = {
                'max_threads': proxy.max_threads,
                'proxy_url': proxy.proxy_url,
                'ua_string': proxy.ua_string,
                'is_available': proxy.is_available,
                'proxy_blacklisted': proxy.proxy_blacklisted,
                'provider': proxy.provider,
                'verified': proxy.verified,
                'proxy_type': proxy.proxy_type,
                'proxy_protocol': proxy.proxy_protocol,
            }
            response = {
                'status': 'success',
                'data': response_data
            }

        except json.JSONDecodeError:
            response = {'status': 'error', 'message': 'Invalid JSON payload'}
        except IntegrityError:
            response = {'status': 'error', 'message': 'Proxy with this URL already exists.'}
        except Exception as e:
            response = {'status': 'error', 'message': str(e)}
    else:
        response = {'status': 'bad_request_type'}

    return JsonResponse(response)