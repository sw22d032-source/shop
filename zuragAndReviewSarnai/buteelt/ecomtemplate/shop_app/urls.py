from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name="index"),
    path('dashboard/', views.dashboard, name="dashboard"),
    path('order/', views.order_complete, name="order_complete"),
    path('search/', views.search, name="search"),
    path('place/', views.place_order, name='place_order'),
    path('store/', views.store, name="store"),
    
    path('<slug:category_slug>/<slug:product_slug>/', views.product_detail, name='product_detail'),
    path('<slug:category_slug>/', views.store, name='store'),
    path('product/<int:product_id>/review/', views.submit_review, name='submit_review'),
    path('review/<int:review_id>/<str:action>/', views.review_react, name="review_react"),
]