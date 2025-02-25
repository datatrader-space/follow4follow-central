def formatify_for_worker(serial_number):
    from sessionbot.models import Device
    from django.forms import model_to_dict
    device=Device.objects.all().filter(serial_number=serial_number)
    if device:
        device=model_to_dict(device[0])
        device['uuid']=str(device.get('uuid'))
        device.pop('connected_to_server', None)
        return device