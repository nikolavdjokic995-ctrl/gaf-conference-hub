import os
from botocore.config import Config
from storages.backends.s3 import S3Storage


class HybridDocumentStorage(S3Storage):
    bucket_name = os.environ.get("R2_BUCKET_NAME", "gaf-conference-papers")
    access_key = os.environ.get("R2_ACCESS_KEY_ID")
    secret_key = os.environ.get("R2_SECRET_ACCESS_KEY")
    endpoint_url = os.environ.get("R2_ENDPOINT_URL")
    region_name = "auto"

    default_acl = None
    file_overwrite = False
    querystring_auth = True
    custom_domain = False

    config = Config(
        signature_version="s3v4",
        s3={"addressing_style": "path"},
    )