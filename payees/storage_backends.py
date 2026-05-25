from storages.backends.s3boto3 import S3Boto3Storage
from django.conf import settings


class StaticStorage(S3Boto3Storage):
    """
    Custom storage backend to handle static files with S3.
    """
    location = settings.AWS_LOCATION
    custom_domain = settings.AWS_S3_CUSTOM_DOMAIN


class MediaStorage(S3Boto3Storage):
    """
    Custom storage backend to handle media files with S3.
    """
    location = settings.MEDIAFILES_LOCATION
    file_overwrite = False
    default_acl = 'private'
    custom_domain = None
    querystring_auth = True
