from django.core.wsgi import get_wsgi_application

# No default settings configured in WSGI context; forcing an explicit DJANGO_SETTINGS_MODULE 
# environment variable for WSGI server processes. This prevents silent accidental boots.
application = get_wsgi_application()
