"""
URL configuration for hireo project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from accounts.views import home

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),  # Home page
    path('accounts/', include('accounts.urls')),
    path('accounts/', include('allauth.urls')),  # Django Allauth URLs
    path('jobs/', include('jobs.urls')),
    path('employer/', include('employers.urls')),
    path('applications/', include('applications.urls')),
    path('analytics/', include('analytics.urls')),
    path('admin-panel/', include('admin_panel.urls')),
    # API Routes
    path('api/v1/auth/', include('accounts.api_urls')),
    path('api/v1/jobs/', include('jobs.api_urls')),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
