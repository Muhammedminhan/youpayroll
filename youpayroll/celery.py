import os
from celery import Celery

# No default settings; forcing explicit DJANGO_SETTINGS_MODULE.
app = Celery('youpayroll')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
