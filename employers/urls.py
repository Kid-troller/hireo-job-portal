from django.urls import path
from . import views, ajax_views

app_name = 'employer'

urlpatterns = [
    # Dashboard and main views
    path('dashboard/', views.employer_dashboard, name='dashboard'),
    path('setup/', views.setup_company, name='setup_company'),
    
    # Company profile management
    path('profile/', views.company_profile, name='profile'),
    path('profile/edit/', views.edit_company, name='edit_company'),
    path('analytics/', views.company_analytics, name='analytics'),
    
    # Job management
    path('post-job/', views.post_job, name='post_job'),
    path('jobs/', views.job_list, name='job_list'),
    path('posted-jobs/', views.posted_jobs, name='posted_jobs'),
    path('jobs/<int:job_id>/edit/', views.edit_job, name='edit_job'),
    path('jobs/<int:job_id>/delete/', views.delete_job, name='delete_job'),
    path('jobs/<int:job_id>/duplicate/', views.duplicate_job, name='duplicate_job'),
    
    # Application management
    path('applications/', views.applications_list, name='applications'),
    path('applications/manage/', views.manage_applications, name='manage_applications'),
    path('applications/<int:application_id>/', views.application_detail, name='application_detail'),
    path('applications/<int:application_id>/status/', views.update_application_status, name='update_application_status'),
    path('applications/<int:application_id>/cover-letter/', views.get_cover_letter, name='get_cover_letter'),
    path('applications/<int:application_id>/schedule-interview/', views.schedule_interview, name='schedule_interview'),
    path('applications/<int:application_id>/download-resume/', views.download_resume, name='download_resume'),
    path('applications/<int:application_id>/message/', views.send_application_message, name='send_application_message'),
    path('bulk-application-action/', views.bulk_application_action, name='bulk_application_action'),
    
    # Messages
    path('messages/', views.messages_view, name='messages'),
    
    # Candidate management
    # path('find-candidates/', views.find_candidates, name='find_candidates'),  # Removed job search from employer side
    path('candidate/<int:candidate_id>/', views.candidate_detail, name='candidate_detail'),
    path('candidate/<int:candidate_id>/download-pdf/', views.download_candidate_pdf, name='download_candidate_pdf'),
    path('applications/download-pdf/', views.download_applications_pdf, name='download_applications_pdf'),
    path('candidates/<int:candidate_id>/save/', views.save_candidate, name='save_candidate'),
    path('candidates/<int:candidate_id>/message/', views.send_candidate_message, name='send_candidate_message'),
    path('candidates/<int:candidate_id>/status/', views.update_candidate_status, name='update_candidate_status'),
    path('candidates/<int:candidate_id>/interview/', views.schedule_candidate_interview, name='schedule_candidate_interview'),
    path('candidates/<int:candidate_id>/notes/', views.add_candidate_note, name='add_candidate_note'),
    path('candidates/<int:candidate_id>/resume/', views.download_candidate_resume, name='download_candidate_resume'),
    path('download-resume/<int:candidate_id>/', views.download_candidate_resume, name='download_resume_direct'),
    
    # Settings and preferences
    path('settings/', views.employer_settings, name='settings'),
    path('update-settings/', views.update_settings, name='update_settings'),
    path('delete-account/', views.delete_account, name='delete_account'),
    path('delete-company/', views.delete_company, name='delete_company'),
    
    # Analytics and data
    path('analytics-data/', views.analytics_data, name='analytics_data'),
    path('export-analytics/<str:format>/', views.export_analytics, name='export_analytics'),
    
    # Talent management tools
    path('skill-assessment/', views.skill_assessment, name='skill_assessment'),
    path('career-guidance/', views.career_guidance, name='career_guidance'),
    path('networking/', views.networking, name='networking'),
    
    # Smart matching system
    path('smart-matching/', views.smart_matching, name='smart_matching'),
    path('smart-matching/results/', views.smart_matching_results, name='smart_matching_results'),
    path('smart-matching/candidate/<int:candidate_id>/', views.smart_matching_candidate_detail, name='smart_matching_candidate_detail'),
    path('smart-matching/preferences/', views.smart_matching_preferences, name='smart_matching_preferences'),
    path('smart-matching/analytics/', views.smart_matching_analytics, name='smart_matching_analytics'),
    path('smart-matching/run/', views.run_smart_matching, name='run_smart_matching'),
    path('smart-matching/download-pdf/', views.download_matching_results_pdf, name='download_matching_results_pdf'),
    
    # AJAX endpoints for real-time updates
    path('ajax/update-status/', ajax_views.update_application_status, name='ajax_update_status'),
    path('ajax/send-message/', ajax_views.send_message_to_applicant, name='ajax_send_message'),
    path('ajax/schedule-interview/', ajax_views.schedule_interview, name='ajax_schedule_interview'),
    path('ajax/application/<int:application_id>/', ajax_views.get_application_details, name='ajax_application_details'),
    path('ajax/job/<int:job_id>/applications/', ajax_views.get_applications_for_job, name='ajax_job_applications'),
    
    # Public company profile
    path('company/<int:company_id>/', views.company_public_profile, name='company_public_profile'),
    # path('companies/', views.company_list, name='company_list'),  # Removed from employer side
    
    # Temporary redirect for old URL pattern
    path('application-detail/<int:application_id>/', views.redirect_application_detail, name='redirect_application_detail'),
    
    # Redirect for old schedule-interview URL pattern
    path('schedule-interview/<int:application_id>/', views.redirect_schedule_interview, name='redirect_schedule_interview'),
]
