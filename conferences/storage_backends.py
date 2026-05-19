import os
from botocore.client import Config
from storages.backends.s3boto3 import S3Boto3Storage


class R2Storage(S3Boto3Storage):
    bucket_name = os.getenv("R2_BUCKET_NAME", "gaf-conference-papers")
    access_key = os.getenv("R2_ACCESS_KEY_ID")
    secret_key = os.getenv("R2_SECRET_ACCESS_KEY")
    region_name = "auto"

    endpoint_url = (
        os.getenv("R2_ENDPOINT_URL", "").strip()
        or f"https://{os.getenv('R2_ACCOUNT_ID', '').strip()}.r2.cloudflarestorage.com"
    )

    if endpoint_url and not endpoint_url.startswith(("http://", "https://")):
        endpoint_url = "https://" + endpoint_url

    default_acl = None
    file_overwrite = False
    querystring_auth = True
    custom_domain = False

    config = Config(
        signature_version="s3v4",
        s3={"addressing_style": "path"},
    )


class HybridDocumentStorage(R2Storage):
    location = ""
