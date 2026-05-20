import os
from django.core.exceptions import ImproperlyConfigured
from django.core.wsgi import get_wsgi_application

# No default settings configured in WSGI context; forcing an explicit DJANGO_SETTINGS_MODULE 
# environment variable for WSGI server processes. This prevents silent accidental boots.
if not os.environ.get('DJANGO_SETTINGS_MODULE'):
    raise ImproperlyConfigured("DJANGO_SETTINGS_MODULE environment variable must be explicitly set in WSGI context.")

application = get_wsgi_application()
