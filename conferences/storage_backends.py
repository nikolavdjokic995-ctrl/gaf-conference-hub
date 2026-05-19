import os
from storages.backends.s3boto3 import S3Boto3Storage
from botocore.client import Config


class R2Storage(S3Boto3Storage):
    bucket_name = os.getenv("R2_BUCKET_NAME")
    endpoint_url = f"https://{os.getenv('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com"

    access_key = os.getenv("R2_ACCESS_KEY_ID")
    secret_key = os.getenv("R2_SECRET_ACCESS_KEY")
    region_name = "auto"
    verify = False

    file_overwrite = False
    default_acl = None
    querystring_auth = False

    config = Config(
        signature_version="s3v4",
        s3={"addressing_style": "path"},
    )


class HybridDocumentStorage(R2Storage):
    location = ""