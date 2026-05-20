from django.core.asgi import get_asgi_application

# No default settings configured in ASGI context; forcing an explicit DJANGO_SETTINGS_MODULE 
# environment variable for ASGI server processes.
application = get_asgi_application()
