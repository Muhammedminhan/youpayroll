import os
from celery import Celery
import logging
import celery


# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'youpayroll.settings.development')

# For creating a new Celery application instance with the project name.
app = Celery('youpayroll')

# To read configuration from Django’s settings using the 'CELERY_' namespace.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()
