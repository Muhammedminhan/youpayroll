import os
from django.core.wsgi import get_wsgi_application

# No default settings; forcing explicit DJANGO_SETTINGS_MODULE in all environments.
# This prevents silent accidental boots with 'production' or 'development' settings.
application = get_wsgi_application()
