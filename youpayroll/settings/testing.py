from .base import *

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
