from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    # Main dashboard
    path('', views.analytics_dashboard, name='dashboard'),
    
    # API endpoints
    path('api/trending-jobs/', views.trending_jobs_api, name='trending_jobs_api'),
    path('api/skill-demand/', views.skill_demand_api, name='skill_demand_api'),
    path('api/salary-trends/', views.salary_trends_api, name='salary_trends_api'),
    path('api/live-feed/', views.live_job_feed_api, name='live_job_feed_api'),
    
    # Tracking endpoints
    path('track/view/<int:job_id>/', views.track_job_view, name='track_job_view'),
    path('track/click/<int:job_id>/', views.track_job_click, name='track_job_click'),
    
    # Export functionality
    path('export/', views.export_analytics_data, name='export_data'),
]
