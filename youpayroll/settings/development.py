from decouple import config
from .base import *
from .utils import require_aws_s3_settings

DEBUG = config('DEBUG', cast=bool, default=True)
SECURE_PROXY_SSL_HEADER = None if DEBUG else ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=not DEBUG, cast=bool)
SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=not DEBUG, cast=bool)
CSRF_COOKIE_SECURE = config('CSRF_COOKIE_SECURE', default=not DEBUG, cast=bool)
SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default=31536000 if not DEBUG else 0, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = config('SECURE_HSTS_INCLUDE_SUBDOMAINS', default=not DEBUG, cast=bool)
SECURE_HSTS_PRELOAD = config('SECURE_HSTS_PRELOAD', default=not DEBUG, cast=bool)

if DEBUG:
    STATIC_URL = '/static/'
    STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
    MEDIA_URL = '/media/'
    CELERY_TASK_ALWAYS_EAGER = True
else:
    aws_settings = require_aws_s3_settings('development')
    AWS_STORAGE_BUCKET_NAME = aws_settings['AWS_STORAGE_BUCKET_NAME']
    AWS_S3_REGION_NAME = aws_settings['AWS_S3_REGION_NAME']
    AWS_LOCATION = aws_settings['AWS_LOCATION']
    AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com'
    STATIC_URL = 'https://%s/%s/' % (AWS_S3_CUSTOM_DOMAIN, AWS_LOCATION)
    STATICFILES_STORAGE = 'payees.storage_backends.StaticStorage'
    DEFAULT_FILE_STORAGE = 'payees.storage_backends.MediaStorage'
    MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/{MEDIAFILES_LOCATION}/"
    CELERY_TASK_ALWAYS_EAGER = False
