from django.core.exceptions import ImproperlyConfigured
from decouple import config
from .base import *

# Enforce production mode
DEBUG = False

# Explicitly read from environment to avoid NameErrors and coupling to base.py
GOOGLE_CLIENT_ID = config('GOOGLE_CLIENT_ID', default=None)
if not GOOGLE_CLIENT_ID:
    raise ImproperlyConfigured('GOOGLE_CLIENT_ID must be set in production.')

# Fernet key for django-encrypted-model-fields (REQUIRED in production)
FIELD_ENCRYPTION_KEY = config('FIELD_ENCRYPTION_KEY')

# Add any production-specific overrides here
