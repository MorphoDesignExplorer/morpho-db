from storages.backends.s3boto3 import S3Boto3Storage
from backend.production_settings import MEDIA_URL


class StaticStorage(S3Boto3Storage):
    location = 'static'
    default_acl = 'public-read'


class PublicMediaStorage(S3Boto3Storage):
    location = 'media'
    default_acl = 'public-read'
    file_overwrite = False

    def get_prefix(self):
        return MEDIA_URL
