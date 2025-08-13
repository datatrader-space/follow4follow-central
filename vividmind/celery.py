import os

from celery import Celery
from django.conf import settings
import eventlet
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vividmind.settings")

celery_app = Celery('vividmind')
celery_app.config_from_object('django.conf:settings', namespace='CELERY')
celery_app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


