from django.urls import path

from carts.views import dashboard
from . import views

urlpatterns = [
    path('', views.index, name="index"),
    path('dashboard/', dashboard, name="dashboard"),
    path('search/', views.search_result, name="search_result"),
    path('store/<slug:cat_slug>/', views.store, name="products_by_category"),
    path('store/', views.store, name="store"),
    path('review/<int:product_id>/', views.submit_review, name="submit_review"),
    path('wishlist/', views.wishlist, name="wishlist"),
    path('wishlist/toggle/<int:product_id>/', views.wishlist_toggle, name="wishlist_toggle"),
    path('compare/', views.compare, name="compare"),
    path('compare/toggle/<int:product_id>/', views.compare_toggle, name="compare_toggle"),
    path('compare/clear/', views.compare_clear, name="compare_clear"),
    path('lab3/', views.lab3, name="lab3"),

    # Энэ мөр хамгийн сүүлд байх ёстой: хоёр хэсэгтэй бүх замыг барьдаг
    path('<slug:cat_slug>/<slug:product_slug>/',
         views.product_detail, name="product_detail"),
]
