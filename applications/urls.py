from django.urls import path
from . import views

app_name = 'applications'

urlpatterns = [
    # Application management
    path('', views.application_list, name='list'),
    path('history/', views.application_list, name='history'),
    path('<int:application_id>/', views.application_detail, name='detail'),
    path('<int:application_id>/update-status/', views.update_status, name='update_status'),
    path('<int:application_id>/send-message/', views.send_message, name='send_message'),
    path('<int:application_id>/schedule-interview/', views.schedule_interview, name='schedule_interview'),
    path('<int:application_id>/view-messages/', views.view_messages, name='view_messages'),
    path('<int:application_id>/messages/', views.view_messages, name='message_thread'),
    path('<int:application_id>/view-history/', views.view_history, name='view_history'),
    path('<int:application_id>/withdraw/', views.withdraw_application, name='withdraw'),
    path('messages/', views.message_list, name='message_list'),
    path('messages/<int:message_id>/', views.message_detail, name='message_detail'),
    path('interviews/', views.interview_list, name='interview_list'),
    path('interviews/<int:interview_id>/', views.interview_detail, name='interview_detail'),
    
    # Notification endpoints
    path('notifications/', views.get_notifications, name='get_notifications'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('applications/<int:application_id>/update-status/', views.update_application_status, name='update_application_status'),
    # Enhanced Notifications
    path('notifications/', views.notification_list, name='notifications'),
    path('notifications/mark-read/', views.mark_notifications_read, name='mark_read'),
    path('notifications/<int:notification_id>/mark-read/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_read'),

    # Utility functions
    path('<int:application_id>/download-resume/', views.download_resume, name='download_resume'),
    path('<int:application_id>/view-resume/', views.view_resume, name='view_resume'),
]
