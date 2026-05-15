from .base import DEBUG, GOOGLE_CLIENT_ID, SECRET_KEY
from django.core.exceptions import ImproperlyConfigured
from decouple import config

# Enforce GOOGLE_CLIENT_ID in production when DEBUG is False
if not DEBUG and not GOOGLE_CLIENT_ID:
    raise ImproperlyConfigured('GOOGLE_CLIENT_ID must be set in production when DEBUG is False.')

# Fernet key for django-encrypted-model-fields
FIELD_ENCRYPTION_KEY = config('FIELD_ENCRYPTION_KEY', default=SECRET_KEY[:32])

# Add any production-specific overrides here
