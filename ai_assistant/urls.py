from django.urls import path
from . import views

app_name = 'ai_assistant'

urlpatterns = [
    # Main AI assistant interface
    path('', views.AIAssistantView.as_view(), name='assistant'),
    
    # API endpoints for AI functionality
    path('api/chat/', views.chatbot_api, name='chatbot_api'),
    path('api/suggestions/', views.smart_suggestions_api, name='suggestions_api'),
    path('api/recommendations/', views.personalized_recommendations_api, name='recommendations_api'),
    path('api/insights/', views.page_insights_api, name='insights_api'),
    path('api/enhance-search/', views.enhanced_search_api, name='enhance_search_api'),
    path('api/preferences/', views.update_preferences_api, name='preferences_api'),
    path('api/feedback/', views.feedback_api, name='feedback_api'),
    path('api/conversation-history/', views.conversation_history_api, name='conversation_history_api'),
    path('api/analytics/', views.user_analytics_api, name='analytics_api'),
]
