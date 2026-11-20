
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),
    path('card/', include("carts.urls")),
    path('accounts/', include("accounts.urls")),
    path('', include("store_app.urls")),
]

# Локал дээр media/ хавтсын зургийг үйлчилнэ (Vercel дээр зураг Blob-оос шууд ачаалагдана)
if settings.DEBUG or not settings.STORAGES['default']['BACKEND'].endswith('VercelBlobStorage'):
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


# if settings.DEBUG:
#     urlpatterns += static(settings.MEDIA_URL,
#                           document_root=settings.MEDIA_ROOT)
