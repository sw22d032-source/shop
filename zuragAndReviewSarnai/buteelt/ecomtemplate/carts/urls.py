from django.urls import path
from . import views

urlpatterns = [
    path('', views.cart, name='cart'),  # Сагсны хуудас
    path('add_cart/<int:product_id>/', views.add_cart, name='add_cart'),  # Сагсанд нэмэх
    path('remove_cart/<int:product_id>/', views.remove_cart, name='remove_cart'),  # Нэг quantity-г хасах
    path('remove_cart_item/<int:product_id>/', views.remove_cart_item, name='remove_cart_item'),  # Item-ийг устгах
]
