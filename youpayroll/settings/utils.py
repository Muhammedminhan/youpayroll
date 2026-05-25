from django.core.exceptions import ImproperlyConfigured
from decouple import config


def require_aws_s3_settings(environment_name):
    required_settings = {
        'AWS_STORAGE_BUCKET_NAME': config('AWS_STORAGE_BUCKET_NAME', default=None),
        'AWS_S3_REGION_NAME': config('AWS_S3_REGION_NAME', default=None),
        'AWS_LOCATION': config('AWS_LOCATION', default=None),
    }
    missing_settings = [
        name
        for name, value in required_settings.items()
        if not value
    ]
    if missing_settings:
        raise ImproperlyConfigured(
            f"Missing required {environment_name} AWS setting(s): {', '.join(missing_settings)}"
        )
    return required_settings
