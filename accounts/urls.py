from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    path('signin/', views.signin, name='signin'),
    path('register/', views.register, name='register'),
    path('signout/', views.signout, name='signout'),
    path('social/<str:provider>/', views.social_login, name='social_login'),
    path('profile/', views.profile, name='profile'),
    path('profile/info/', views.profile_info, name='profile_info'),
    path('profile/password/', views.profile_password, name='profile_password'),
    path('profile/phone/', views.profile_phone, name='profile_phone'),
    path('profile/avatar/', views.profile_avatar, name='profile_avatar'),
    path('profile/email/', views.profile_email, name='profile_email'),
]
