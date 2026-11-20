"""Барааны каталогийг (ангилал, бараа, зураг, үзүүлэлт) fixture-ээс ачаална.

Өгөгдлийн санд бараа байхгүй үед л ачаална — дахин deploy хийхэд давхардахгүй.
  py manage.py load_catalog            # хоосон бол ачаална
  py manage.py load_catalog --export   # одоогийн өгөгдлийн сангаас fixture үүсгэнэ
"""
import os

from django.conf import settings
from django.core import serializers
from django.core.management import call_command
from django.core.management.base import BaseCommand

from store_app.models import Category, Product, ProductImage, ProductSpec

FIXTURE = os.path.join(settings.BASE_DIR, 'store_app', 'fixtures', 'catalog.json')


class Command(BaseCommand):
    help = 'Барааны каталогийг fixture-ээс ачаална (эсвэл --export)'

    def add_arguments(self, parser):
        parser.add_argument('--export', action='store_true', help='Одоогийн каталогийг fixture болгож хадгална')

    def handle(self, *args, export=False, **options):
        if export:
            os.makedirs(os.path.dirname(FIXTURE), exist_ok=True)
            # Эцэг ангилал эхэлж орохын тулд parent-гүйгээс нь эхлүүлнэ
            cats = sorted(Category.objects.all(), key=lambda c: len(c.get_ancestors()))
            objects = cats + list(Product.objects.all().order_by('id')) + \
                list(ProductImage.objects.all().order_by('id')) + list(ProductSpec.objects.all().order_by('id'))
            with open(FIXTURE, 'w', encoding='utf-8') as fh:
                serializers.serialize('json', objects, stream=fh, indent=2, ensure_ascii=False)
            self.stdout.write(self.style.SUCCESS(f'{len(objects)} объект хадгалагдлаа: {FIXTURE}'))
            return

        if Product.objects.exists():
            self.stdout.write('Каталог аль хэдийн байна — алгаслаа.')
            return
        if not os.path.exists(FIXTURE):
            self.stdout.write(self.style.WARNING('catalog.json олдсонгүй — алгаслаа.'))
            return
        call_command('loaddata', FIXTURE, verbosity=1)
        self.stdout.write(self.style.SUCCESS('Каталог ачааллаа.'))
