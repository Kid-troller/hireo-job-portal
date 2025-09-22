from django.urls import path
from . import views, ajax_views
from . import resume_views

app_name = 'accounts'

urlpatterns = [
    # Verification
    path('verify-email/<str:token>/', views.verify_email, name='verify_email'),
    path('resend-verification/', views.resend_verification, name='resend_verification'),
    # Authentication
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('password-reset/', views.password_reset, name='password_reset'),
    path('password-reset/<str:token>/', views.password_reset_confirm, name='password_reset_confirm'),
    path('select-user-type/', views.select_user_type, name='select_user_type'),
    
    # Dashboard and Profile
    path('dashboard/', views.dashboard, name='dashboard'),
    # Profile management
    path('profile/', views.profile_detail, name='profile_detail'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('profile/complete/', views.complete_profile, name='complete_profile'),
    path('profile/skills/', views.profile_skills, name='profile_skills'),
    path('profile/experience/', views.profile_experience, name='profile_experience'),
    path('profile/education/', views.profile_education, name='profile_education'),
    path('profile/certifications/', views.profile_certifications, name='profile_certifications'),
    path('profile/portfolio/', views.profile_portfolio, name='profile_portfolio'),
    path('profile/preferences/', views.profile_preferences, name='profile_preferences'),
    
    # Profile Components
    path('education/add/', views.add_education, name='add_education'),
    path('experience/add/', views.add_experience, name='add_experience'),
    path('skill/add/', views.add_skill, name='add_skill'),
    path('certification/add/', views.add_certification, name='add_certification'),
    
    # Delete Profile Components
    path('education/<int:education_id>/delete/', views.delete_education, name='delete_education'),
    path('experience/<int:experience_id>/delete/', views.delete_experience, name='delete_experience'),
    path('skill/<int:skill_id>/delete/', views.delete_skill, name='delete_skill'),
    path('certification/<int:certification_id>/delete/', views.delete_certification, name='delete_certification'),
    
    # Lists
    path('applications/', views.applications_list, name='applications_list'),
    path('job-alerts/', views.job_alerts_list, name='job_alerts_list'),
    
    # Job Alerts API
    path('job-alerts/create/', views.create_job_alert, name='create_job_alert'),
    path('job-alerts/<int:alert_id>/update/', views.update_job_alert, name='update_job_alert'),
    path('job-alerts/<int:alert_id>/delete/', views.delete_job_alert, name='delete_job_alert'),
    path('job-alerts/<int:alert_id>/toggle/', views.toggle_job_alert, name='toggle_job_alert'),
    path('job-alerts/<int:alert_id>/get/', views.get_job_alert, name='get_job_alert'),
    
    # Actions
    path('save-job/<int:job_id>/', views.save_job, name='save_job'),
    path('change-password/', views.change_password, name='change_password'),
    
    # Tools
    path('cover-letter/', views.cover_letter, name='cover_letter'),
    path('cover-letter/templates/', views.cover_letter_templates, name='cover_letter_templates'),
    path('interview-prep/', views.interview_prep, name='interview_prep'),
    path('interview-prep/practice/', views.interview_practice, name='interview_practice'),
    path('interview-prep/mock-interview/', views.mock_interview, name='mock_interview'),
    path('interview-prep/voice-practice/', views.voice_practice, name='voice_practice'),
    path('gamification/', views.gamification, name='gamification'),
    path('skill-assessment/', views.skill_assessment, name='skill_assessment'),
    path('resume-templates/', views.resume_templates, name='resume_templates'),
    path('resume-builder/', views.resume_builder, name='resume_builder'),
    path('resume-builder/generate-pdf/', views.generate_resume_pdf, name='generate_resume_pdf'),
    path('resume-builder/generate-docx/', views.generate_resume_docx, name='generate_resume_docx'),
    
    # Next-Generation Resume Builder URLs
    path('resume-builder/dashboard/', resume_views.resume_builder_dashboard, name='resume_builder_dashboard'),
    path('resume-builder/wizard/', resume_views.resume_wizard, name='resume_wizard'),
    path('resume-builder/wizard/<int:resume_id>/', resume_views.resume_wizard, name='resume_wizard_edit'),
    path('resume-builder/create/', resume_views.create_resume, name='create_resume'),
    
    # ATS Optimization URLs
    path('resume-builder/job-analyzer/', resume_views.job_description_analyzer, name='job_description_analyzer'),
    path('resume-builder/ats-optimization/<int:resume_id>/', resume_views.ats_optimization, name='ats_optimization'),
    path('resume-builder/ai-enhancer/<int:resume_id>/', resume_views.ai_bullet_enhancer, name='ai_bullet_enhancer'),
    
    # Resume Management URLs
    path('resume-builder/versions/<int:resume_id>/', resume_views.resume_versions, name='resume_versions'),
    path('resume-builder/comparison/', resume_views.resume_comparison, name='resume_comparison'),
    path('resume-builder/tracker/', resume_views.job_application_tracker, name='job_application_tracker'),
    path('resume-builder/cover-letter/', resume_views.cover_letter_builder, name='cover_letter_builder'),
    
    # Export URLs
    path('resume-builder/export/<int:resume_id>/', resume_views.export_resume, name='export_resume'),
    path('resume-builder/export-history/', resume_views.export_history, name='export_history'),
    path('resume-builder/bulk-export/', resume_views.bulk_export, name='bulk_export'),
    
    # Analytics URLs
    path('resume-builder/analytics/', resume_views.resume_analytics_dashboard, name='resume_analytics_dashboard'),
    path('resume-builder/<int:resume_id>/', views.resume_builder, name='resume_builder_edit'),
    path('career-roadmap/', views.career_roadmap, name='career_roadmap'),
    path('career-guidance/', views.career_roadmap, name='career_guidance'),
    path('career-progress/<int:career_id>/', views.career_progress, name='career_progress'),
    
    # Custom Career Roadmap URLs
    path('roadmap/create/', views.create_custom_roadmap, name='create_custom_roadmap'),
    path('roadmap/<int:roadmap_id>/', views.roadmap_detail, name='roadmap_detail'),
    path('roadmap/<int:roadmap_id>/edit/', views.edit_custom_roadmap, name='edit_custom_roadmap'),
    path('roadmap/<int:roadmap_id>/delete/', views.delete_custom_roadmap, name='delete_custom_roadmap'),
    path('roadmap/<int:roadmap_id>/add-step/', views.add_roadmap_step, name='add_roadmap_step'),
    path('roadmap/<int:roadmap_id>/update-order/', views.update_step_order, name='update_step_order'),
    path('roadmap/step/<int:step_id>/data/', views.get_step_data, name='get_step_data'),
    path('roadmap/step/<int:step_id>/edit/', views.edit_roadmap_step, name='edit_roadmap_step'),
    path('roadmap/step/<int:step_id>/delete/', views.delete_roadmap_step, name='delete_roadmap_step'),
    path('roadmap/step/<int:step_id>/update-progress/', views.update_step_progress, name='update_roadmap_step_progress'),
    path('roadmap/step/<int:step_id>/complete/', views.complete_roadmap_step, name='complete_roadmap_step'),
    path('take-assessment/<int:career_id>/', views.take_assessment, name='take_assessment'),
    path('take-assessment/<int:career_id>/<int:milestone_id>/', views.take_assessment, name='take_assessment_milestone'),
    path('career-roadmap/skills-gap/', views.skills_gap_analysis, name='skills_gap_analysis'),
    path('salary-negotiation/', views.nepal_salary_guide, name='salary_negotiation'),
    path('salary-comparison-result/', views.salary_comparison_result, name='salary_comparison_result'),
    
    # AJAX endpoints for real-time updates
    path('ajax/application-status/', ajax_views.get_application_status_updates, name='ajax_application_status'),
    path('ajax/notifications/', ajax_views.get_notifications, name='ajax_notifications'),
    path('ajax/mark-notification-read/', ajax_views.mark_notification_read, name='ajax_mark_notification_read'),
    path('ajax/respond-interview/', ajax_views.respond_to_interview, name='ajax_respond_interview'),
    path('ajax/application/<int:application_id>/messages/', ajax_views.get_application_messages, name='ajax_application_messages'),
    path('ajax/send-message/', ajax_views.send_message_to_employer, name='ajax_send_message'),
    path('salary-negotiation/calculator/', views.salary_calculator, name='salary_calculator'),
    path('salary-negotiation/guides/', views.negotiation_guides, name='negotiation_guides'),
    path('achievements/', views.gamification, name='achievements'),
    
    # Applications management
    path('applications/tracking/', views.application_tracking, name='application_tracking'),
    path('applications/analytics/', views.application_analytics, name='application_analytics'),
    path('applications/tracker/', views.application_tracker, name='application_tracker'),
    path('applications/<int:application_id>/withdraw/', views.withdraw_application, name='withdraw_application'),
    path('applications/<int:application_id>/delete/', views.delete_application, name='delete_application'),
    path('applications/<int:application_id>/message/', views.send_jobseeker_message, name='send_jobseeker_message'),
    path('api/applications/check-updates/', views.check_application_updates, name='check_application_updates'),
    
    # Job management
    path('job-alerts/manage/', views.manage_job_alerts, name='manage_job_alerts'),
    
    # Notifications
    path('notifications/', views.notification_center, name='notification_center'),
    
    # AI-Powered Interview Preparation
    path('interview-prep/', views.interview_prep, name='interview_prep'),
    path('interview-prep/start/', views.start_interview_session, name='start_interview_session'),
    path('interview-session/<int:session_id>/', views.interview_session, name='interview_session'),
    path('submit-answer/<int:session_id>/', views.submit_answer, name='submit_answer'),
    path('interview-results/<int:session_id>/', views.interview_results, name='interview_results'),
    path('interview-analytics/', views.interview_analytics, name='interview_analytics'),
    
    # Delete functionality
    path('delete-account/', views.delete_account, name='delete_account'),
    
    # Security Questions and Forgot Password
    path('forgot-password/', views.forgot_password_request, name='forgot_password_request'),
    path('forgot-password/questions/<str:token>/', views.forgot_password_questions, name='forgot_password_questions'),
    path('forgot-password/reset/<str:token>/', views.forgot_password_reset, name='forgot_password_reset'),
    path('security-questions/setup/', views.security_questions_setup, name='security_questions_setup'),
    path('security-questions/manage/', views.security_questions_manage, name='security_questions_manage'),
    
]
