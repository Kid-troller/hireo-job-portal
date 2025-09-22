"""
API URLs for jobs app
"""
from django.urls import path
from . import api_views

app_name = 'jobs_api'

urlpatterns = [
    path('', api_views.JobListAPIView.as_view(), name='job_list'),
    path('<int:pk>/', api_views.JobDetailAPIView.as_view(), name='job_detail'),
    path('search/', api_views.JobSearchAPIView.as_view(), name='job_search'),
    path('categories/', api_views.JobCategoryListAPIView.as_view(), name='job_categories'),
]
