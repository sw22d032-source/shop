from django.urls import path

from . import views

urlpatterns = [
    path('', views.cart, name='cart'),
    path('add/<int:product_id>/', views.add_cart, name='add_cart'),
    path('remove/<int:product_id>/', views.remove_cart_item, name='remove_cart_item'),
    path('reduce/<int:product_id>/', views.reduce_cart_item, name='reduce_cart_item'),
    path('checkout/', views.checkout, name='checkout'),
    path('order-complete/<str:order_number>/', views.order_complete, name='order_complete'),
    path('pay/<str:order_number>/', views.qpay_pay, name='qpay_pay'),
    path('pay/<str:order_number>/check/', views.qpay_check, name='qpay_check'),
    path('pay/<str:order_number>/cancel/', views.qpay_cancel, name='qpay_cancel'),
    path('pay/<str:order_number>/simulate/', views.qpay_simulate, name='qpay_simulate'),
    path('qpay/callback/<str:order_number>/', views.qpay_callback, name='qpay_callback'),
]
