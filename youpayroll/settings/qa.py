from django.core.exceptions import ImproperlyConfigured
from decouple import config
from .base import *
from .utils import require_aws_s3_settings

# Enforce QA mode
DEBUG = False
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
aws_settings = require_aws_s3_settings('QA')
AWS_STORAGE_BUCKET_NAME = aws_settings['AWS_STORAGE_BUCKET_NAME']
AWS_S3_REGION_NAME = aws_settings['AWS_S3_REGION_NAME']
AWS_LOCATION = aws_settings['AWS_LOCATION']
AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com'
STATIC_URL = 'https://%s/%s/' % (AWS_S3_CUSTOM_DOMAIN, AWS_LOCATION)
STATICFILES_STORAGE = 'payees.storage_backends.StaticStorage'
DEFAULT_FILE_STORAGE = 'payees.storage_backends.MediaStorage'
MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/{MEDIAFILES_LOCATION}/"
CELERY_TASK_ALWAYS_EAGER = False
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)
SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=True, cast=bool)
CSRF_COOKIE_SECURE = config('CSRF_COOKIE_SECURE', default=True, cast=bool)
SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default=31536000, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = config('SECURE_HSTS_INCLUDE_SUBDOMAINS', default=True, cast=bool)
SECURE_HSTS_PRELOAD = config('SECURE_HSTS_PRELOAD', default=True, cast=bool)

# Explicitly validate critical environment variables
GOOGLE_CLIENT_ID = config('GOOGLE_CLIENT_ID', default=None)
if not GOOGLE_CLIENT_ID:
    raise ImproperlyConfigured('GOOGLE_CLIENT_ID must be set in QA.')

# Required in QA
FIELD_ENCRYPTION_KEY = config('FIELD_ENCRYPTION_KEY', default=None)
if not FIELD_ENCRYPTION_KEY:
    raise ImproperlyConfigured('FIELD_ENCRYPTION_KEY must be set in QA.')

SECRET_KEY = config('SECRET_KEY', default=None)
if not SECRET_KEY:
    raise ImproperlyConfigured('SECRET_KEY must be set in QA.')

# Add any QA-specific overrides here
ENABLE_GRAPHIQL = False
