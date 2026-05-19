import os

from storages.backends.s3 import S3Storage


class HybridDocumentStorage(S3Storage):
    access_key = os.environ.get("R2_ACCESS_KEY_ID")
    secret_key = os.environ.get("R2_SECRET_ACCESS_KEY")
    bucket_name = os.environ.get("R2_BUCKET_NAME")

    endpoint_url = os.environ.get("R2_ENDPOINT_URL")

    region_name = "auto"

    default_acl = None
    file_overwrite = False

    querystring_auth = False

    addressing_style = "path"