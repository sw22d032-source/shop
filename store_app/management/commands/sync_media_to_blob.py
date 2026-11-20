"""Локал media/ хавтас дахь зургуудыг Vercel Blob руу ижил замаар хуулна.

  py manage.py sync_media_to_blob            # Blob-д байхгүйг л хуулна
  py manage.py sync_media_to_blob --force    # бүгдийг дахин хуулна

BLOB_READ_WRITE_TOKEN орчны хувьсагч шаардлагатай (Vercel build үед автоматаар байна).
"""
import mimetypes
import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from accounts.models import Account
from ecommerce.blob_storage import blob_configured
from store_app.models import Category, Product, ProductImage


def referenced_files():
    names = set()
    names.update(Product.objects.exclude(images='').values_list('images', flat=True))
    names.update(ProductImage.objects.exclude(image='').values_list('image', flat=True))
    names.update(Category.objects.exclude(cat_image='').values_list('cat_image', flat=True))
    names.update(Account.objects.exclude(pro_image='').values_list('pro_image', flat=True))
    return sorted(n for n in names if n and not n.startswith('http'))


class Command(BaseCommand):
    help = 'media/ доторх зургуудыг Vercel Blob руу хуулна'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Blob-д байгаа ч дахин хуулна')

    def handle(self, *args, force=False, **options):
        if not blob_configured():
            raise CommandError('BLOB_READ_WRITE_TOKEN тохируулагдаагүй байна.')
        from vercel.blob import sync as blob

        uploaded = skipped = missing = 0
        for name in referenced_files():
            local = os.path.join(settings.MEDIA_ROOT, *name.split('/'))
            if not os.path.isfile(local):
                missing += 1
                self.stdout.write(self.style.WARNING(f'  олдсонгүй: {name}'))
                continue
            if not force:
                try:
                    blob.head_blob(name)
                    skipped += 1
                    continue
                except blob.BlobNotFoundError:
                    pass
            with open(local, 'rb') as fh:
                blob.put_blob(name, fh.read(), access='public', allow_overwrite=True,
                              content_type=mimetypes.guess_type(name)[0] or 'application/octet-stream')
            uploaded += 1
            self.stdout.write(f'  хуулсан: {name}')

        self.stdout.write(self.style.SUCCESS(
            f'Дууслаа: {uploaded} хуулсан, {skipped} аль хэдийн байсан, {missing} файл олдоогүй.'))
