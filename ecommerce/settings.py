
from pathlib import Path
import os


BASE_DIR = Path(__file__).resolve().parent.parent

# Vercel дээр ажиллаж байгаа эсэх (Vercel өөрөө VERCEL=1 гэж тохируулдаг)
ON_VERCEL = bool(os.environ.get('VERCEL'))

# Нууц түлхүүр: Vercel дээр DJANGO_SECRET_KEY орчны хувьсагч заавал байх ёстой
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', '')
if not SECRET_KEY:
    if ON_VERCEL:
        from django.core.exceptions import ImproperlyConfigured
        raise ImproperlyConfigured('Vercel дээр DJANGO_SECRET_KEY орчны хувьсагчийг тохируулна уу.')
    SECRET_KEY = 'django-insecure-sfa#qhul$l&)5ko!4linh&khm@#6d*h_be)6_2$xe=#_cbf6^n'  # зөвхөн локал

# Локал дээр DEBUG=True, Vercel дээр False (DJANGO_DEBUG=1 гэж хүчээр асааж болно)
DEBUG = os.environ.get('DJANGO_DEBUG', '' if ON_VERCEL else '1').lower() in ('1', 'true', 'yes')

ALLOWED_HOSTS = ['127.0.0.1', 'localhost', '.vercel.app'] + [
    h.strip() for h in os.environ.get('DJANGO_ALLOWED_HOSTS', '').split(',') if h.strip()]
CSRF_TRUSTED_ORIGINS = ['https://*.vercel.app'] + [
    o.strip() for o in os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS', '').split(',') if o.strip()]

# Vercel HTTPS proxy-ийн ард ажилладаг тул https гэж зөв танина (QPay callback-д хэрэгтэй)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
if ON_VERCEL:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'store_app',
    'carts',
    'accounts',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'ecommerce.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'store_app.context_processors.category_data',
                'store_app.context_processors.counter',
                'store_app.context_processors.user_lists',
            ],
        },
    },
]

WSGI_APPLICATION = 'ecommerce.wsgi.application'


# Локал: SQLite.  Vercel: DATABASE_URL (Postgres — Vercel Storage-оос нэмэхэд автоматаар үүснэ)
if os.environ.get('DATABASE_URL'):
    import urllib.parse
    _db = urllib.parse.urlparse(os.environ['DATABASE_URL'])
    _db_options = dict(urllib.parse.parse_qsl(_db.query))
    _db_options.setdefault('sslmode', 'require')
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': urllib.parse.unquote(_db.path.lstrip('/')),
            'USER': urllib.parse.unquote(_db.username or ''),
            'PASSWORD': urllib.parse.unquote(_db.password or ''),
            'HOST': _db.hostname,
            'PORT': _db.port or 5432,
            'OPTIONS': _db_options,
            'CONN_MAX_AGE': 0,
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Ulaanbaatar'

USE_I18N = True

USE_TZ = True


STATIC_URL = 'static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")]
# Vercel build үед collectstatic энд цуглуулж CDN-ээр үйлчилнэ
STATIC_ROOT = BASE_DIR / 'staticfiles'


MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Зураг хадгалах газар: Vercel Blob тохируулсан бол Blob, үгүй бол локал media/ хавтас
from ecommerce.blob_storage import blob_configured  # noqa: E402
STORAGES = {
    'default': {
        'BACKEND': 'ecommerce.blob_storage.VercelBlobStorage' if blob_configured()
        else 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Нэвтрээгүй хэрэглэгч checkout/dashboard руу ороход энд шилжүүлнэ
LOGIN_URL = 'accounts:signin'

# Bootstrap-ийн alert class-уудтай тааруулах
from django.contrib.messages import constants as message_constants  # noqa: E402
MESSAGE_TAGS = {message_constants.ERROR: 'danger'}

# ---------------------------------------------------------------------------
# Google / Facebook-ээр нэвтрэх
# Утгуудыг энд шууд бичих эсвэл орчны хувьсагчаар (environment variable) өгнө.
#   Google:   https://console.cloud.google.com/apis/credentials → OAuth client ID (Web)
#             Authorized JavaScript origins: http://127.0.0.1:8000, http://localhost:8000
#   Facebook: https://developers.facebook.com/apps → Facebook Login
# ---------------------------------------------------------------------------
GOOGLE_CLIENT_ID = os.environ.get(
    'GOOGLE_CLIENT_ID',
    '1035766409380-otomu614oq93nv5oe6vo1u5rerovs0o3.apps.googleusercontent.com',
)
FACEBOOK_APP_ID = os.environ.get('FACEBOOK_APP_ID', '')
FACEBOOK_APP_SECRET = os.environ.get('FACEBOOK_APP_SECRET', '')

# Google/Facebook-ийн popup цонх буцаж мэдээлэл дамжуулахад шаардлагатай
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin-allow-popups'
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'


# ---------------------------------------------------------------------------
# Имэйл илгээх (баталгаажуулах код)
# EMAIL_HOST_USER тохируулаагүй бол код имэйлээр биш, runserver ажиллаж буй
# PowerShell цонхонд хэвлэгдэнэ (хөгжүүлэлтийн горим).
# Gmail-ээр илгээх бол: Google бүртгэл → Security → 2-Step Verification → App passwords
# ---------------------------------------------------------------------------
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
if EMAIL_HOST_USER:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
    EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
    EMAIL_USE_TLS = True
    DEFAULT_FROM_EMAIL = f'BlueCart <{EMAIL_HOST_USER}>'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    DEFAULT_FROM_EMAIL = 'BlueCart <noreply@bluecart.local>'


# ---------------------------------------------------------------------------
# QPay төлбөр
# Анхдагч нь QPay-ийн туршилтын (sandbox) орчин — жинхэнэ мөнгө татахгүй.
# Жинхэнэ дэлгүүрт: QPay-тэй гэрээ байгуулж авсан утгуудаа орчны хувьсагчаар өгнө.
#   QPAY_BASE_URL=https://merchant.qpay.mn
# QPAY_CALLBACK_BASE: QPay таны серверийг дуудах нийтийн хаяг (жишээ нь https://shop.mn).
# Хоосон бол хуудас 3 секунд тутам QPay-аас төлбөрийг өөрөө шалгана.
# ---------------------------------------------------------------------------
QPAY_BASE_URL = os.environ.get('QPAY_BASE_URL', 'https://merchant-sandbox.qpay.mn')
QPAY_USERNAME = os.environ.get('QPAY_USERNAME', 'TEST_MERCHANT')
QPAY_PASSWORD = os.environ.get('QPAY_PASSWORD', '123456')
QPAY_INVOICE_CODE = os.environ.get('QPAY_INVOICE_CODE', 'TEST_INVOICE')
QPAY_CALLBACK_BASE = os.environ.get('QPAY_CALLBACK_BASE', '')
# Sandbox үед "Тест: төлбөр төлсөн болгох" товч харуулах эсэх.
# Хоосон бол DEBUG-ийг дагана. Vercel дээр найздаа үзүүлэх бол QPAY_TEST_BUTTON=1 гэж тохируулна.
QPAY_TEST_BUTTON = {'1': True, 'true': True, '0': False, 'false': False}.get(
    os.environ.get('QPAY_TEST_BUTTON', '').lower())
