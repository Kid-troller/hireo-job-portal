from django.urls import path
from . import views

app_name = 'admin_panel'

urlpatterns = [
    # Main dashboard
    path('', views.admin_dashboard, name='dashboard'),
    
    # User management
    path('users/', views.user_management, name='user_management'),
    path('users/<int:user_id>/toggle-status/', views.toggle_user_status, name='toggle_user_status'),
    
    # Job management
    path('jobs/', views.job_management, name='job_management'),
    path('jobs/<int:job_id>/update-status/', views.update_job_status, name='update_job_status'),
    
    # Application management
    path('applications/', views.application_management, name='application_management'),
    
    # Reports management
    path('reports/', views.reports_management, name='reports_management'),
    
    # System settings
    path('settings/', views.system_settings, name='system_settings'),
    path('settings/save/', views.save_system_settings, name='save_system_settings'),
    path('settings/reset/', views.reset_system_settings, name='reset_system_settings'),
    path('settings/test-email/', views.test_email_settings, name='test_email_settings'),
    path('settings/maintenance/', views.run_maintenance_tasks, name='run_maintenance_tasks'),
    path('settings/backup/', views.create_system_backup, name='create_system_backup'),
    
    # Analytics
    path('analytics/', views.analytics_dashboard, name='analytics_dashboard'),
    
    # Data export
    path('export/', views.export_data, name='export_data'),
    
    # Enhanced user management
    path('users/jobseeker/<int:user_id>/', views.jobseeker_detail, name='jobseeker_detail'),
    path('users/employer/<int:user_id>/', views.employer_detail, name='employer_detail'),
    
    # User impersonation
    path('users/<int:user_id>/impersonate/', views.impersonate_user, name='impersonate_user'),
    path('stop-impersonation/', views.stop_impersonation, name='stop_impersonation'),
    
    # Enhanced job and application management
    path('jobs/admin/', views.admin_job_management, name='admin_job_management'),
    path('jobs/<int:job_id>/toggle-featured/', views.toggle_job_featured, name='toggle_job_featured'),
    path('applications/admin/', views.admin_application_management, name='admin_application_management'),
    path('applications/<int:application_id>/update-status/', views.admin_update_application_status, name='admin_update_application_status'),
    
    # Reports management actions
    path('reports/<int:report_id>/update-status/', views.update_report_status, name='update_report_status'),
    path('reports/<int:report_id>/assign/', views.assign_report, name='assign_report'),
    
    # Advanced analytics endpoints
    path('analytics/data/', views.analytics_data_api, name='analytics_data_api'),
    path('analytics/export/', views.export_analytics_data, name='export_analytics_data'),
    
    # Password management
    path('users/<int:user_id>/view-password/', views.view_user_password, name='view_user_password'),
    path('users/<int:user_id>/reset-password/', views.reset_user_password, name='reset_user_password'),
]
