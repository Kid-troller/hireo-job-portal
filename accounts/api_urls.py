"""
API URLs for accounts app
"""
from django.urls import path
from . import api_views

app_name = 'accounts_api'

urlpatterns = [
    path('login/', api_views.api_login, name='api_login'),
    path('logout/', api_views.api_logout, name='api_logout'),
    path('register/', api_views.APIRegisterView.as_view(), name='api_register'),
    path('profile/', api_views.api_user_profile, name='api_profile'),
]
