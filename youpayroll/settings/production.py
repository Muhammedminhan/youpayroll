from django.core.exceptions import ImproperlyConfigured
from decouple import config
from .base import *

# Enforce production mode
DEBUG = False
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Django SECRET_KEY (REQUIRED in production, must be strong)
SECRET_KEY = config('SECRET_KEY', default=None)
if not SECRET_KEY or SECRET_KEY == 'django-insecure-default-key-for-dev-and-test':
    raise ImproperlyConfigured('SECRET_KEY environment variable must be explicitly set and secure in production.')

# Explicitly read from environment to avoid NameErrors and coupling to base.py
GOOGLE_CLIENT_ID = config('GOOGLE_CLIENT_ID', default=None)
if not GOOGLE_CLIENT_ID:
    raise ImproperlyConfigured('GOOGLE_CLIENT_ID must be set in production.')

# Fernet key for django-encrypted-model-fields (REQUIRED in production)
FIELD_ENCRYPTION_KEY = config('FIELD_ENCRYPTION_KEY', default=None)
if not FIELD_ENCRYPTION_KEY:
    raise ImproperlyConfigured('FIELD_ENCRYPTION_KEY must be set in production.')

AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME', default=None)
AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME', default=None)
AWS_LOCATION = config('AWS_LOCATION', default=None)
missing_aws_settings = [
    name
    for name, value in {
        'AWS_STORAGE_BUCKET_NAME': AWS_STORAGE_BUCKET_NAME,
        'AWS_S3_REGION_NAME': AWS_S3_REGION_NAME,
        'AWS_LOCATION': AWS_LOCATION,
    }.items()
    if not value
]
if missing_aws_settings:
    raise ImproperlyConfigured(
        f"Missing required production AWS setting(s): {', '.join(missing_aws_settings)}"
    )

AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com'
STATIC_URL = 'https://%s/%s/' % (AWS_S3_CUSTOM_DOMAIN, AWS_LOCATION)
STATICFILES_STORAGE = 'payees.storage_backends.StaticStorage'
DEFAULT_FILE_STORAGE = 'payees.storage_backends.MediaStorage'
MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/{MEDIAFILES_LOCATION}/"
CELERY_TASK_ALWAYS_EAGER = False

# Add any production-specific overrides here
ENABLE_GRAPHIQL = False
