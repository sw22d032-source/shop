"""Зургийг Vercel Blob-д хадгалах Django storage.

Vercel дээр файлын систем зөвхөн уншигддаг тул admin-аас оруулсан барааны зураг,
профайл зураг зэргийг Vercel Blob (public store) руу хадгална.

Өгөгдлийн санд файлын замыг (pathname) хадгалдаг, жишээ нь
  photos/products/3f9a1c2b7d4e.jpg
URL нь https://<store_id>.public.blob.vercel-storage.com/<pathname> болно.
Тиймээс локал дээрх хуучин зургуудыг ижил замаар Blob руу хуулахад
(`py manage.py sync_media_to_blob`) өгөгдлийн санг өөрчлөх шаардлагагүй.
"""
import mimetypes
import os
import posixpath
import uuid
from urllib.parse import quote

from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible

RW_PREFIX = 'vercel_blob_rw_'


def blob_configured():
    return bool(os.environ.get('BLOB_READ_WRITE_TOKEN') or os.environ.get('BLOB_STORE_ID'))


def blob_store_id():
    store = os.environ.get('BLOB_STORE_ID', '').strip()
    if not store:
        token = os.environ.get('BLOB_READ_WRITE_TOKEN', '').strip()
        if token.startswith(RW_PREFIX):
            store = token[len(RW_PREFIX):].partition('_')[0]
    return store.removeprefix('store_').strip().lower()


def _sdk():
    from vercel.blob import sync as blob   # зөвхөн хэрэгтэй үед import хийнэ
    return blob


@deconstructible
class VercelBlobStorage(Storage):
    access = 'public'

    def __init__(self, base_url=None):
        self._base_url = base_url

    # ---- URL ----
    @property
    def base_url(self):
        if self._base_url:
            return self._base_url.rstrip('/')
        env = os.environ.get('BLOB_PUBLIC_BASE_URL', '').strip()
        if env:
            return env.rstrip('/')
        return f'https://{blob_store_id()}.{self.access}.blob.vercel-storage.com'

    def url(self, name):
        if not name:
            return ''
        if name.startswith(('http://', 'https://')):
            return name
        return f'{self.base_url}/{quote(name.lstrip("/"), safe="/")}'

    # ---- Нэр ----
    def get_available_name(self, name, max_length=None):
        """Нэр давхцахгүй, богино (DB-ийн 100 тэмдэгтийн хязгаарт багтах) болгоно."""
        directory, filename = posixpath.split(name.replace('\\', '/'))
        ext = os.path.splitext(filename)[1].lower()[:10]
        return posixpath.join(directory, f'{uuid.uuid4().hex[:16]}{ext}')

    def generate_filename(self, filename):
        return filename.replace('\\', '/')

    # ---- Үйлдлүүд ----
    def _save(self, name, content):
        if hasattr(content, 'seek'):
            try:
                content.seek(0)
            except Exception:
                pass
        data = content.read()
        if isinstance(data, str):
            data = data.encode()
        content_type = (getattr(content, 'content_type', None)
                        or mimetypes.guess_type(name)[0] or 'application/octet-stream')
        result = _sdk().put_blob(name, data, access=self.access, content_type=content_type,
                                 allow_overwrite=True)
        return result.pathname

    def _open(self, name, mode='rb'):
        result = _sdk().get_blob(name, access=self.access)
        return ContentFile(result.body, name=name)

    def delete(self, name):
        if name:
            _sdk().delete_blob(name)

    def exists(self, name):
        blob = _sdk()
        try:
            blob.head_blob(name)
            return True
        except blob.BlobNotFoundError:
            return False

    def size(self, name):
        return _sdk().head_blob(name).size

    def path(self, name):
        raise NotImplementedError('Vercel Blob файлд локал зам байхгүй.')
