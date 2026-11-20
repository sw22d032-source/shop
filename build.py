"""Vercel build скрипт (pyproject.toml → [tool.vercel.scripts] build).

1. Өгөгдлийн сангийн migration
2. Өгөгдлийн сан хоосон бол барааны каталогийг store_app/fixtures/catalog.json-оос ачаална
3. media/ доторх зургуудыг Vercel Blob руу хуулна (байхгүйг нь л)
4. DJANGO_SUPERUSER_USERNAME / _EMAIL / _PASSWORD тохируулсан бол admin үүсгэнэ (байхгүй бол)
collectstatic-ийг Vercel өөрөө ажиллуулдаг.
"""
import os
import subprocess
import sys


def manage(*args):
    print('>>> manage.py', *args, flush=True)
    subprocess.run([sys.executable, 'manage.py', *args], check=True)


def main():
    if os.environ.get('DATABASE_URL'):
        manage('migrate', '--noinput')
        manage('load_catalog')
        if os.environ.get('DJANGO_SUPERUSER_PASSWORD') and os.environ.get('DJANGO_SUPERUSER_USERNAME'):
            # Аль хэдийн байвал алдаа өгдөг тул check=False
            print('>>> admin хэрэглэгч шалгаж байна', flush=True)
            subprocess.run([sys.executable, 'manage.py', 'createsuperuser', '--noinput'], check=False)
    else:
        print('АНХААР: DATABASE_URL алга — Vercel → Storage хэсгээс Postgres өгөгдлийн сан нэмнэ үү.', flush=True)

    if os.environ.get('BLOB_READ_WRITE_TOKEN'):
        manage('sync_media_to_blob')
    else:
        print('АНХААР: BLOB_READ_WRITE_TOKEN алга — Vercel → Storage хэсгээс Blob store нэмнэ үү.', flush=True)


if __name__ == '__main__':
    main()
