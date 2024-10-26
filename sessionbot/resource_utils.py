from django_celery_results.models import TaskResult
from celery import shared_task
from celery.utils.log import get_task_logger
from django.forms.models import model_to_dict
import requests

def read_googlesheet_data(**kwargs):
    print("Entering read_googlesheet_data with kwargs:", kwargs)
    pass


@shared_task()
def create_resources_from_google_sheets(**kwargs):
    print("Entering create_resources_from_google_sheets with kwargs:", kwargs)
    from google_api import GoogleSheet

    g = GoogleSheet()
    g.initialize_connection()
    print("i was initialized")
    resource_types = ["email_providers", "profiles", "servers", "devices"]
    print(kwargs)
    if kwargs.get("spreadsheet_url"):
        g.spreadsheet_url = kwargs.get("spreadsheet_url")
        print("Spreadsheet URL:", kwargs["spreadsheet_url"])

    if kwargs.get("resource_type"):
        resource_types = [kwargs.get("resource_type")]

    request_id = kwargs.get("request_id")
    response = []

    for resource_type in resource_types:
        print(f"Processing resource type: {resource_type}")
        g.open_google_sheet().find_worksheet(resource_type).read_worksheet()
        data = g.worksheet_data
        print(f"Data read from worksheet: {data}")

        for row in data:
            print(f"Processing row: {row}")
            kwargs.update({"row": row})
            resp = None
            if resource_type == "profiles":
                if not row.get("service"):
                    print("Service Not Found. Skipping Profile. Add report here.")
                    continue

                resp = profile(**row)
                resp.update({"resource_type": "profile"})
                resp.update({"request_id": request_id})
            elif resource_type == "email_providers":
                resp = email_provider(**row)
                resp.update({"resource_type": "email_provider"})
                resp.update({"request_id": request_id})
                print("Email provider response:", resp)
            elif resource_type == "devices":
                resp = device(**row)
                resp.update({"request_id": request_id})
                print("Device response:", resp)
            elif resource_type == "servers":
                resp = server(**row)
                resp.update({"resource_type": "server"})
                resp.update({"request_id": request_id})
            elif resource_type == "proxies":
                kwargs.update({"resource_type": resource_type})
                kwargs.update({"data_point": "proxy"})
                resp.update({"request_id": request_id})

            if resp:
                response.append(resp)

        print("Final response for resource type {}: {}".format(resource_type, response))

    return response


def profile(**kwargs):
    logs = []

    def log_message(message):
        logs.append(message)

    log_message(f"Entering profile with kwargs: {kwargs}")
    username = kwargs.get("username")
    if not username:
        log_message("Username is missing.")
        return {
            "response": "failed",
            "message": "ProfileCreationFailed Username Missing",
            "object": None,
            "label": "UserNameNotFound",
            "logs": logs,
        }

    service = kwargs.get("service")
    if not service:
        log_message(f"Service is missing for {username}.")
        return {
            "response": "failed",
            "message": f"ProfileCreationFailed for {username} Service Missing",
            "object": None,
            "label": "ServiceNotFound",
            "logs": logs,
        }

    password = kwargs.get("password")
    if not password:
        log_message(f"Password is missing for {username}.")
        return {
            "response": "failed",
            "message": f"ProfileCreationFailed for {username} Password Missing",
            "object": None,
            "label": "PasswordNotFound",
            "logs": logs,
        }

    email_address = kwargs.get("email_address")
    if not email_address:
        log_message(f"Email address is missing for {username}.")
        return {
            "response": "failed",
            "message": f"ProfileCreationFailed for {username} Email Address Missing",
            "object": None,
            "label": "EmailNotFound",
            "logs": logs,
        }

    # Handle optional logged_in_on_servers field
    logged_in_on_servers = kwargs.get("logged_in_on_servers")
    server = None
    if logged_in_on_servers:
        log_message(f"Received Logged Value: {logged_in_on_servers}")
        from sessionbot.models import Server
        server = Server.objects.filter(name=logged_in_on_servers).first()
        if not server or not server.public_ip:
            log_message(f"Server details are missing or public IP is not found.")
            server = None  # Server is optional, so no need to fail here
    else:
        log_message("Logged_in_on_servers is missing.")

    # Handle optional device field
    device_serial_number = kwargs.get("device")
    device = None
    if device_serial_number:
        log_message(f"Received device serial number: {device_serial_number}")
        from sessionbot.models import Device
        device = Device.objects.filter(serial_number=device_serial_number).first()
        if device:
            log_message(f"Device with serial number {device_serial_number} found.")
        else:
            log_message(f"Failed to find device with serial number {device_serial_number}.")
    else:
        log_message("Device is missing.")

    from sessionbot.models import ChildBot, EmailProvider

    # Check if the profile already exists
    c = ChildBot.objects.filter(service=service, username=username).first()
    if c:
        c.password = password
        c.email_address = email_address
        c.display_name = username
        if server:
            c.logged_in_on_servers = server
        if device:
            c.device = device
        c.save()

        _c = model_to_dict(c)
        _c.pop("cookie")
        _c.pop("created_on")
        resp = {
            "response": "success",
            "message": f"Profile Already Exists for {username} Duplicate",
            "object": _c,
            "label": "ProfileAlreadyExists",
        }
        log_message(f"Profile already exists for {username}.")
    else:
        log_message(f"Creating a new profile for {username}.")
        c = ChildBot(
            username=username,
            display_name=username,
            password=password,
            service=service,
            email_address=email_address,
        )
        if server:
            c.logged_in_on_servers = server
        if device:
            c.device = device
        c.save()

        _c = model_to_dict(c)
        _c.pop("cookie")
        _c.pop("created_on")

        # Handle optional email provider
        email_provider = kwargs.get("email_provider")
        email_password = kwargs.get("email_password")

        if not email_password:
            if email_provider:
                e = EmailProvider.objects.filter(imap_email_host=email_provider).first()
                if e:
                    c.email_provider = e
                    log_message(f"Email provider found and assigned for {username}.")
                else:
                    resp = {
                        "response": "success",
                        "message": f"Profile {username} Created without Email Provider",
                        "object": _c,
                        "label": "EmailProviderNotExists",
                    }
                    log_message(f"Email provider not found for {username}.")
            else:
                resp = {
                    "response": "success",
                    "message": f"Profile {username} Created without Email Provider/Password",
                    "object": _c,
                    "label": "IncompleteEmailSettings",
                }
                log_message(f"Email provider and password missing for {username}.")
        else:
            c.email_password = email_password
            log_message(f"Email password set for {username}.")
        c.save()

        resp = {
            "response": "success",
            "message": f"Profile {username} Created Successfully",
            "object": _c,
            "label": "NewProfileCreated",
        }
        log_message(f"New profile created for {username}.")

    # Send the payload to the worker URL
    try:
        worker_payload = {
            "username": username,
            "service": service,
            "password": password,
            "email_address": email_address,
        }
        log_message(f"Sending payload to worker: {worker_payload}")
        worker_url = f"{server.public_ip}crawl/childbots/" if server else "default_worker_url"
        response = requests.post(worker_url, json=worker_payload)
        response.raise_for_status()  # Raise exception if the request failed
        log_message(f"Successfully sent payload to worker: {response.json()}")
    except requests.exceptions.RequestException as e:
        log_message(f"Error sending payload to worker: {str(e)}")

    resp["logs"] = logs
    return resp

def email_provider(**kwargs):
    print("Entering email_provider with kwargs:", kwargs)
    from sessionbot.models import EmailProvider

    imap_email_host = kwargs.get("imap_host")
    if not imap_email_host:
        return {
            "response": "failed",
            "message": "EmailProviderCreationFailed ImapEmailHost Missing",
            "object": None,
            "label": "ImapEmailHostMissing",
        }

    imap_email_username = kwargs.get("imap_username")
    if not imap_email_username:
        return {
            "response": "failed",
            "message": "EmailProviderCreationFailed ImapEmailUsernName Missing",
            "object": None,
            "label": "ImapEmailUsernameMissing",
        }

    imap_email_password = kwargs.get("imap_password")
    if not imap_email_password:
        return {
            "response": "failed",
            "message": "EmailProviderCreationFailed ImapEmailPassword Missing",
            "object": None,
            "label": "ImapEmailPasswordMissing",
        }

    imap_email_port = kwargs.get("imap_port", 0)
    name = kwargs.get("name", imap_email_host)
    e = EmailProvider.objects.all().filter(imap_email_username=imap_email_username)
    if e:
        return {
            "response": "success",
            "message": f"Email Provider Already Exists for {imap_email_username} Duplicate",
            "object": e,
            "label": "EmailProviderAlreadyExists",
        }
    else:
        from customer.models import Customer

        c = Customer.objects.all().filter(user__id=1).first()
        e = EmailProvider(
            imap_email_username=imap_email_username,
            imap_email_host=imap_email_host,
            imap_email_password=imap_email_password,
            imap_email_port=imap_email_port,
            name=name,
            customer=c,
        )
        e.save()
        return {
            "response": "success",
            "message": f"Email Provider {imap_email_host} Created Successfully",
            "object": e,
            "label": "NewEmailProviderCreated",
        }


def server(**kwargs):
    logs = []

    def log_message(message):
        logs.append(message)

    log_message(f"Entering server with kwargs: {kwargs}")
    from sessionbot.models import Server

    server_id = kwargs.get("server_id")
    name = kwargs.get("name")
    max_tasks_allowed = kwargs.get("max_tasks_allowed")

    if not server_id or len(server_id) < 1:
        log_message('Mandatory Key "Id" missing for row')
        return {
            "status": "failed",
            "message": 'Mandatory Key "Id" missing for row',
            "object": None,
            "label": "IdMissing",
            "logs": logs,
        }

    s = Server.objects.all().filter(instance_id=server_id)
    if s:
        s = s[0]
        s.name = name
        s.maximum_parallel_tasks_allowed = max_tasks_allowed
        s.save()
        resp = {
            "status": "success",
            "message": f"Update Server {name}",
            "object": model_to_dict(s),
            "label": "ServerUpdated",
        }
        log_message(f"Updated server with ID: {server_id} and Name: {name}")
    else:
        s = Server(
            instance_id=server_id,
            name=name,
            maximum_parallel_tasks_allowed=max_tasks_allowed,
        )
        s.save()
        resp = {
            "status": "success",
            "message": f"Created Server {name}",
            "object": model_to_dict(s),
            "label": "ServerCreated",
        }
        log_message(f"Created new server with ID: {server_id} and Name: {name}")

    resp["logs"] = logs
    return resp


def device(**kwargs):
    logs = []

    def log_message(message):
        logs.append(message)

    log_message(f"Entering device with kwargs: {kwargs}")

    name = kwargs.get("name")
    serial_number = kwargs.get("serial_number")
    connected_to_server = kwargs.get("connected_to_server")

    # Check mandatory fields
    if not serial_number:
        log_message("Serial Number Missing.")
        return {
            "response": "failed",
            "message": "Device Creation Failed! Serial Number Missing",
            "object": None,
            "label": "SerialNumberMissing",
            "logs": logs,
        }
    if not connected_to_server:
        log_message("Connected to Server Missing.")
        return {
            "response": "failed",
            "message": "Device Creation Failed! Connected to Server Missing",
            "object": None,
            "label": "ConnectedToServerMissing",
            "logs": logs,
        }
    if not name:
        log_message("Name Missing.")
        return {
            "response": "failed",
            "message": "Device Creation Failed! Name Missing",
            "object": None,
            "label": "NameMissing",
            "logs": logs,
        }
    from sessionbot.models import Server, Device
    # Fetch the server instance by name
    server = Server.objects.filter(name=connected_to_server).first()

    if not server:
        log_message("Server Not Found.")
        return {
            "response": "failed",
            "message": "Device Creation Failed! Server Not Found",
            "object": None,
            "label": "ConnectedServerNotFound",
            "logs": logs,
        }

    # Check if device exists and update or create accordingly
    device_queryset = Device.objects.filter(serial_number=serial_number)

    if device_queryset.exists():
        device_instance = device_queryset.first()
        device_instance.connected_to_server = server
        device_instance.name = name
        device_instance.save()
        log_message(f"Device {serial_number} updated successfully.")
        return {
            "response": "success",
            "message": f"Device {serial_number} Updated Successfully",
            "object": model_to_dict(device_instance),
            "label": "DeviceUpdated",
            "logs": logs,
        }
    else:
        device_instance = Device(name=name, serial_number=serial_number, connected_to_server=server)
        device_instance.save()
        log_message(f"Device {serial_number} created successfully.")
        return {
            "response": "success",
            "message": f"Device {serial_number} Created Successfully",
            "object": model_to_dict(device_instance),
            "label": "DeviceCreated",
            "logs": logs,
        }

@shared_task()
def convert_bulk_campaign_to_workflow_for_vivide_mind_worker(**kwargs):
    print(
        "Entering convert_bulk_campaign_to_workflow_for_vivide_mind_worker with kwargs:",
        kwargs,
    )
    max_bot_reservation_by_service_campaigns = 3
    from sessionbot.models import BulkCampaign

    b = BulkCampaign.objects.all().filter(id=1).first()
    if not b:
        print("BulkCampaign with id=1 not found")
        return

    bot_campaigns = []
    for bot in b.childbots.all():
        current_reservation_by_campaigns = bot.campaign.all()
        campaigns = current_reservation_by_campaigns.filter(service=b.service)
        bot_campaigns.extend(campaigns)
        if (
            len(current_reservation_by_campaigns)
            > max_bot_reservation_by_service_campaigns
        ):
            print(
                "Bot assignment failed. Max Number of Allowed Campaigns in General Settings exceeded. Removing the Bot from Campaign (Implement)"
            )
            b.childbots.remove(bot)

    campaigns = list(set(bot_campaigns))
    b.save()

    bot_campaigns_servers = list(set(campaign.server for campaign in campaigns))
    print("Bot campaign servers:", bot_campaigns_servers)

    if bot_campaigns_servers:
        if len(bot_campaigns_servers) == 1:
            prob = False
            for device in b.devies.all():
                if device.connected_to_server != bot_campaigns_servers[0]:
                    prob = True
                    break
            if not prob:
                b.server = bot_campaigns_servers[0]
                b.save()
                print(f"Assigned server {b.server} to BulkCampaign")
