from django.urls import path
from . import views

app_name = 'jobs'

urlpatterns = [
    # Job listing and search
    path('', views.job_list, name='job_list'),
    path('statistics/', views.job_statistics, name='statistics'),
    
    # Job details and actions
    path('<int:job_id>/', views.job_detail, name='job_detail'),
    path('<int:job_id>/apply/', views.apply_job, name='apply_job'),
    path('<int:job_id>/save/', views.save_job, name='save_job'),
    
    # Job posting (employers)
    path('post/', views.post_job, name='post_job'),
    path('<int:job_id>/edit/', views.edit_job, name='edit_job'),
    path('<int:job_id>/delete/', views.delete_job, name='delete_job'),
    
    # Job alerts
    path('alerts/create/', views.create_job_alert, name='create_job_alert'),
    path('alerts/create-ajax/', views.create_job_alert_ajax, name='create_job_alert_ajax'),
    
    
    # Advanced search
    path('search/advanced/', views.advanced_job_search, name='advanced_search'),
    
    # Category and location based listings
    path('category/<int:category_id>/', views.category_jobs, name='category_jobs'),
    path('location/<int:location_id>/', views.location_jobs, name='location_jobs'),
    
    # AI-powered endpoints
    path('api/ai-suggestions/', views.ai_search_suggestions, name='ai_suggestions'),
    path('api/market-trends/', views.market_trends_api, name='market_trends'),
    path('api/personalized-suggestions/', views.personalized_suggestions, name='personalized_suggestions'),
    path('api/salary-insights/', views.salary_insights_api, name='salary_insights'),
    
    # Advanced AI/ML endpoints
    path('api/intelligent-recommendations/', views.intelligent_job_recommendations, name='intelligent_recommendations'),
    path('api/job-fit-analysis/<int:job_id>/', views.job_fit_analysis, name='job_fit_analysis'),
    path('api/semantic-search/', views.semantic_job_search, name='semantic_search'),
    path('api/candidate-recommendations/<int:job_id>/', views.candidate_recommendations_api, name='candidate_recommendations'),
]
