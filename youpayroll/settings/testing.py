import os
from cryptography.fernet import Fernet

# Generate a non-secret key for each test process so tests do not depend on a
# committed fallback. This is stable within one process, but encrypted fixtures
# that need to survive across test runs should set FIELD_ENCRYPTION_KEY instead.
os.environ.setdefault('FIELD_ENCRYPTION_KEY', Fernet.generate_key().decode())

from .base import *

DEBUG = False
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Keep tests independent of S3 settings even though base.py computes storage
# backends before this module overrides DEBUG.
STATIC_URL = '/static/'
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
MEDIA_URL = '/media/'

# Blazing-fast in-memory SQLite database configuration for isolated test environments
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Ensure Celery tasks run synchronously during test suite runs
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Disable non-critical logging during test runs
import logging
logging.disable(logging.CRITICAL)
