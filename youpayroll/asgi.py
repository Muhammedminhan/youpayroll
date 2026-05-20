import os
from django.core.exceptions import ImproperlyConfigured
from django.core.asgi import get_asgi_application

# No default settings configured in ASGI context; forcing an explicit DJANGO_SETTINGS_MODULE 
# environment variable for ASGI server processes.
if not os.environ.get('DJANGO_SETTINGS_MODULE'):
    raise ImproperlyConfigured("DJANGO_SETTINGS_MODULE environment variable must be explicitly set in ASGI context.")

application = get_asgi_application()
