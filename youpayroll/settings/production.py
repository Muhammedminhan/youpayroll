from django.core.exceptions import ImproperlyConfigured
from decouple import config
from .base import *

# Enforce production mode
DEBUG = False

# Django SECRET_KEY (REQUIRED in production, must be strong)
SECRET_KEY = config('SECRET_KEY', default=None)
if not SECRET_KEY:
    raise ImproperlyConfigured('SECRET_KEY environment variable must be set in production.')

# Explicitly read from environment to avoid NameErrors and coupling to base.py
GOOGLE_CLIENT_ID = config('GOOGLE_CLIENT_ID', default=None)
if not GOOGLE_CLIENT_ID:
    raise ImproperlyConfigured('GOOGLE_CLIENT_ID must be set in production.')

# Fernet key for django-encrypted-model-fields (REQUIRED in production)
FIELD_ENCRYPTION_KEY = config('FIELD_ENCRYPTION_KEY', default=None)
if not FIELD_ENCRYPTION_KEY:
    raise ImproperlyConfigured('FIELD_ENCRYPTION_KEY must be set in production.')

# Add any production-specific overrides here
ENABLE_GRAPHIQL = False
