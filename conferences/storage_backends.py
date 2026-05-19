import os
from storages.backends.s3boto3 import S3Boto3Storage


class HybridDocumentStorage(S3Boto3Storage):
    bucket_name = os.environ.get("R2_BUCKET_NAME", "gaf-conference-papers")
    access_key = os.environ.get("R2_ACCESS_KEY_ID")
    secret_key = os.environ.get("R2_SECRET_ACCESS_KEY")
    endpoint_url = os.environ.get("R2_ENDPOINT_URL")
    region_name = "auto"

    file_overwrite = False
    default_acl = None
    querystring_auth = True
    custom_domain = False
