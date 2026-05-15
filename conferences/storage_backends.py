import os
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional

import requests
from django.conf import settings
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible
from cloudinary_storage.storage import RawMediaCloudinaryStorage


@dataclass
class StorageUsage:
    used_bytes: int = 0
    file_count: int = 0
    error: str = ""

    @property
    def used_mb(self) -> float:
        return round(self.used_bytes / (1024 * 1024), 2)

    @property
    def used_gb(self) -> float:
        return round(self.used_bytes / (1024 * 1024 * 1024), 3)

    @property
    def percent_of_free_gb(self) -> float:
        return round((self.used_bytes / (1024 * 1024 * 1024)) * 100, 1)


def _clean_path(name: str) -> str:
    return str(name).replace('\\', '/').lstrip('/')


@deconstructible
class HybridDocumentStorage(Storage):
    """Primary Supabase Storage with Cloudinary fallback.

    Env vars needed for Supabase:
    - SUPABASE_URL, e.g. https://xxxx.supabase.co
    - SUPABASE_SERVICE_ROLE_KEY, preferably service role key for server-side uploads
      or SUPABASE_KEY as fallback
    - SUPABASE_STORAGE_BUCKET, default: conference-papers
    - SUPABASE_STORAGE_PUBLIC=True/False, default False

    If Supabase upload fails because quota is full or credentials are missing,
    this storage falls back to Cloudinary raw storage so user upload is not lost.
    """

    def __init__(self, *args, **kwargs):
        self.cloudinary_storage = RawMediaCloudinaryStorage()

    @property
    def supabase_enabled(self) -> bool:
        return os.environ.get('SUPABASE_STORAGE_ENABLED', 'True') == 'True'

    @property
    def supabase_url(self) -> str:
        return os.environ.get('SUPABASE_URL', '').rstrip('/')

    @property
    def supabase_key(self) -> str:
        return os.environ.get('SUPABASE_SERVICE_ROLE_KEY') or os.environ.get('SUPABASE_KEY', '')

    @property
    def bucket(self) -> str:
        return os.environ.get('SUPABASE_STORAGE_BUCKET', 'conference-papers')

    @property
    def public_bucket(self) -> bool:
        return os.environ.get('SUPABASE_STORAGE_PUBLIC', 'False') == 'True'

    @property
    def signed_url_expires(self) -> int:
        try:
            return int(os.environ.get('SUPABASE_SIGNED_URL_EXPIRES', '3600'))
        except ValueError:
            return 3600

    def _headers(self, content_type: Optional[str] = None) -> Dict[str, str]:
        headers = {
            'apikey': self.supabase_key,
            'Authorization': f'Bearer {self.supabase_key}',
        }
        if content_type:
            headers['Content-Type'] = content_type
        return headers

    def _can_use_supabase(self) -> bool:
        return bool(self.supabase_enabled and self.supabase_url and self.supabase_key and self.bucket)

    def _open(self, name, mode='rb'):
        # Django rarely needs to open remote paper files directly in this project.
        # Use the signed/public URL for downloads instead.
        raise NotImplementedError('HybridDocumentStorage does not support direct open(). Use .url instead.')

    def _save(self, name, content):
        name = _clean_path(name)

        if self._can_use_supabase():
            try:
                content.seek(0)
            except Exception:
                pass

            data = content.read()
            content_type = getattr(content, 'content_type', None) or 'application/octet-stream'
            endpoint = f'{self.supabase_url}/storage/v1/object/{self.bucket}/{name}'

            try:
                response = requests.post(
                    endpoint,
                    headers={**self._headers(content_type), 'x-upsert': 'true'},
                    data=data,
                    timeout=60,
                )

                if 200 <= response.status_code < 300:
                    return f'supabase:{name}'

                # If quota is exceeded or any Supabase error occurs, fall back to Cloudinary.
                print('Supabase upload failed, using Cloudinary fallback:', response.status_code, response.text[:500])
            except Exception as exc:
                print('Supabase upload exception, using Cloudinary fallback:', exc)

            try:
                content.seek(0)
            except Exception:
                pass

        return self.cloudinary_storage.save(name, content)

    def exists(self, name):
        # We use upsert for Supabase and Cloudinary can handle overwrite-like names.
        return False

    def url(self, name):
        name = str(name)

        if name.startswith('http://') or name.startswith('https://'):
            return name

        if name.startswith('supabase:'):
            path = name.replace('supabase:', '', 1)
            if not self._can_use_supabase():
                return ''

            if self.public_bucket:
                return f'{self.supabase_url}/storage/v1/object/public/{self.bucket}/{path}'

            endpoint = f'{self.supabase_url}/storage/v1/object/sign/{self.bucket}/{path}'
            try:
                response = requests.post(
                    endpoint,
                    headers=self._headers('application/json'),
                    json={'expiresIn': self.signed_url_expires},
                    timeout=20,
                )
                if 200 <= response.status_code < 300:
                    signed = response.json().get('signedURL') or response.json().get('signedUrl')
                    if signed:
                        if signed.startswith('http'):
                            return signed
                        return f'{self.supabase_url}{signed}'
                print('Supabase signed URL failed:', response.status_code, response.text[:500])
            except Exception as exc:
                print('Supabase signed URL exception:', exc)
            return ''

        return self.cloudinary_storage.url(name)

    def delete(self, name):
        name = str(name)
        if not name:
            return

        if name.startswith('supabase:') and self._can_use_supabase():
            path = name.replace('supabase:', '', 1)
            endpoint = f'{self.supabase_url}/storage/v1/object/{self.bucket}'
            try:
                requests.delete(
                    endpoint,
                    headers=self._headers('application/json'),
                    json={'prefixes': [path]},
                    timeout=30,
                )
                return
            except Exception as exc:
                print('Supabase delete exception:', exc)

        try:
            self.cloudinary_storage.delete(name)
        except Exception as exc:
            print('Cloudinary fallback delete exception:', exc)


def get_supabase_storage_usage(prefix: str = '') -> StorageUsage:
    storage = HybridDocumentStorage()
    usage = StorageUsage()

    if not storage._can_use_supabase():
        usage.error = 'Supabase environment variables are not configured.'
        return usage

    def scan(folder: str = ''):
        endpoint = f'{storage.supabase_url}/storage/v1/object/list/{storage.bucket}'
        payload = {
            'prefix': folder,
            'limit': 1000,
            'offset': 0,
            'sortBy': {'column': 'name', 'order': 'asc'},
        }
        response = requests.post(
            endpoint,
            headers=storage._headers('application/json'),
            json=payload,
            timeout=30,
        )
        response.raise_for_status()

        for item in response.json():
            name = item.get('name', '')
            metadata = item.get('metadata') or {}
            size = metadata.get('size')

            if size is None and item.get('id') is None:
                next_folder = f'{folder.rstrip("/")}/{name}'.strip('/')
                scan(next_folder)
            elif size is not None:
                usage.file_count += 1
                usage.used_bytes += int(size or 0)

    try:
        scan(prefix)
    except Exception as exc:
        usage.error = str(exc)

    return usage
