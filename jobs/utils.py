"""
Job portal utility functions for enhanced workflow management
"""
import logging
from django.utils import timezone
from django.db.models import Q, F
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from datetime import datetime, timedelta
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)

def validate_job_posting(job_data):
    """
    Comprehensive validation for job posting data
    Returns tuple (is_valid, errors)
    """
    errors = []
    
    # Required field validation
    required_fields = {
        'title': 'Job title',
        'description': 'Job description', 
        'requirements': 'Job requirements',
        'responsibilities': 'Job responsibilities',
        'category': 'Job category',
        'location': 'Job location',
        'employment_type': 'Employment type',
        'experience_level': 'Experience level',
        'application_deadline': 'Application deadline'
    }
    
    for field, label in required_fields.items():
        if not job_data.get(field):
            errors.append(f'{label} is required')
    
    # Content length validation
    if job_data.get('title') and len(job_data['title'].strip()) < 5:
        errors.append('Job title must be at least 5 characters long')
    
    if job_data.get('description') and len(job_data['description'].strip()) < 100:
        errors.append('Job description must be at least 100 characters long')
    
    # Salary validation
    min_salary = job_data.get('min_salary')
    max_salary = job_data.get('max_salary')
    
    if min_salary and max_salary and min_salary > max_salary:
        errors.append('Maximum salary cannot be less than minimum salary')
    
    # Deadline validation
    deadline = job_data.get('application_deadline')
    if deadline:
        if isinstance(deadline, str):
            try:
                deadline = datetime.strptime(deadline, '%Y-%m-%d').date()
            except ValueError:
                errors.append('Invalid date format for application deadline')
        
        if deadline and deadline <= timezone.now().date():
            errors.append('Application deadline must be in the future')
    
    return len(errors) == 0, errors

def send_application_notification(application):
    """
    Send comprehensive notification for new job application
    """
    try:
        # Email notification to employer
        employer_email = application.employer.user_profile.user.email
        job_title = application.job.title
        company_name = application.job.company.name
        applicant_name = application.applicant.user_profile.user.get_full_name() or application.applicant.user_profile.user.username
        
        subject = f'New Application for {job_title} at {company_name}'
        
        email_context = {
            'employer_name': application.employer.user_profile.user.get_full_name(),
            'job_title': job_title,
            'company_name': company_name,
            'applicant_name': applicant_name,
            'application_date': application.applied_at,
            'application_id': application.id,
            'dashboard_url': f'{settings.SITE_URL}/employer/applications/{application.id}/'
        }
        
        html_message = render_to_string('emails/new_application_notification.html', email_context)
        text_message = render_to_string('emails/new_application_notification.txt', email_context)
        
        send_mail(
            subject=subject,
            message=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[employer_email],
            html_message=html_message,
            fail_silently=False
        )
        
        # Real-time WebSocket notification
        send_realtime_notification(
            user_id=application.employer.user_profile.user.id,
            notification_type='application_received',
            title='New Job Application',
            message=f'{applicant_name} applied for {job_title}',
            data={
                'application_id': application.id,
                'job_id': application.job.id,
                'applicant_name': applicant_name
            }
        )
        
        return True
        
    except Exception as e:
        logger.error(f'Failed to send application notification: {e}')
        return False

def send_realtime_notification(user_id, notification_type, title, message, data=None):
    """
    Send real-time notification via WebSocket
    """
    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f'notifications_{user_id}',
                {
                    'type': 'notification_message',
                    'notification': {
                        'type': notification_type,
                        'title': title,
                        'message': message,
                        'timestamp': timezone.now().isoformat(),
                        'data': data or {}
                    }
                }
            )
    except Exception as e:
        logger.warning(f'Failed to send real-time notification: {e}')

def update_application_status(application, new_status, notes=None, changed_by=None):
    """
    Update application status with proper tracking and notifications
    """
    from applications.models import ApplicationStatus, Notification
    
    try:
        # Create status history record
        ApplicationStatus.objects.create(
            application=application,
            status=new_status,
            notes=notes or f'Status changed to {new_status}',
            changed_by=changed_by
        )
        
        # Update application status
        old_status = application.status
        application.status = new_status
        application.save()
        
        # Send notification to job seeker
        status_messages = {
            'reviewing': 'Your application is now under review',
            'shortlisted': 'Congratulations! You have been shortlisted',
            'interviewing': 'You have been selected for an interview',
            'offered': 'Congratulations! You have received a job offer',
            'hired': 'Congratulations! You have been hired',
            'rejected': 'Thank you for your interest. Unfortunately, we will not be moving forward with your application'
        }
        
        if new_status in status_messages:
            Notification.objects.create(
                user=application.applicant.user_profile.user,
                notification_type='application_status',
                title=f'Application Status Update - {application.job.title}',
                message=status_messages[new_status],
                application=application,
                job=application.job
            )
            
            # Send real-time notification
            send_realtime_notification(
                user_id=application.applicant.user_profile.user.id,
                notification_type='application_status',
                title='Application Status Update',
                message=f'{application.job.title}: {status_messages[new_status]}',
                data={
                    'application_id': application.id,
                    'job_id': application.job.id,
                    'new_status': new_status,
                    'old_status': old_status
                }
            )
        
        return True
        
    except Exception as e:
        logger.error(f'Failed to update application status: {e}')
        return False

def get_job_recommendations(user_profile, limit=10):
    """
    Get personalized job recommendations based on user profile and activity
    """
    from jobs.models import JobPost
    from accounts.models import JobSeekerProfile
    
    try:
        if user_profile.user_type != 'jobseeker':
            return JobPost.objects.none()
        
        try:
            job_seeker = JobSeekerProfile.objects.get(user_profile=user_profile)
        except JobSeekerProfile.DoesNotExist:
            logger.error(f"JobSeekerProfile not found for user {user_profile.user.username}")
            return JobPost.objects.none()
        
        # Get user preferences
        user_skills = job_seeker.skills.lower().split(',') if job_seeker.skills else []
        preferred_location = job_seeker.preferred_location
        experience_years = job_seeker.experience_years or 0
        
        # Build recommendation query
        jobs = JobPost.objects.filter(
            status='active',
            application_deadline__gt=timezone.now().date()
        )
        
        # Exclude jobs already applied to
        from applications.models import Application
        applied_jobs = Application.objects.filter(
            applicant=job_seeker
        ).values_list('job_id', flat=True)
        
        jobs = jobs.exclude(id__in=applied_jobs)
        
        # Score jobs based on relevance
        scoring_conditions = []
        
        # Skills matching
        for skill in user_skills[:5]:  # Top 5 skills
            if skill.strip():
                scoring_conditions.append(
                    Q(required_skills__icontains=skill.strip()) |
                    Q(preferred_skills__icontains=skill.strip()) |
                    Q(description__icontains=skill.strip())
                )
        
        # Location preference
        if preferred_location:
            scoring_conditions.append(
                Q(location__city__icontains=preferred_location) |
                Q(is_remote=True)
            )
        
        # Experience level matching
        experience_mapping = {
            0: 'entry',
            1: 'entry', 
            2: 'junior',
            3: 'junior',
            5: 'mid',
            8: 'senior',
            12: 'lead'
        }
        
        suitable_levels = []
        for years, level in experience_mapping.items():
            if experience_years >= years:
                suitable_levels.append(level)
        
        if suitable_levels:
            jobs = jobs.filter(experience_level__in=suitable_levels)
        
        # Apply scoring and return top recommendations
        if scoring_conditions:
            query = scoring_conditions[0]
            for condition in scoring_conditions[1:]:
                query |= condition
            jobs = jobs.filter(query)
        
        return jobs.distinct().order_by('-created_at')[:limit]
        
    except Exception as e:
        logger.error(f'Failed to get job recommendations: {e}')
        return JobPost.objects.none()

def track_job_view(job, user, request=None):
    """
    Track job view for analytics and recommendations
    """
    from jobs.models import JobView
    
    try:
        # Get IP address
        ip_address = '127.0.0.1'
        if request:
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip_address = x_forwarded_for.split(',')[0]
            else:
                ip_address = request.META.get('REMOTE_ADDR', '127.0.0.1')
        
        # Create or update view record
        job_view, created = JobView.objects.get_or_create(
            job=job,
            user=user,
            defaults={
                'ip_address': ip_address,
                'user_agent': request.META.get('HTTP_USER_AGENT', '') if request else ''
            }
        )
        
        if not created:
            # Update existing view
            job_view.viewed_at = timezone.now()
            job_view.view_count = F('view_count') + 1
            job_view.save()
        
        # Update job view count
        JobPost.objects.filter(id=job.id).update(
            views_count=F('views_count') + 1
        )
        
        return True
        
    except Exception as e:
        logger.error(f'Failed to track job view: {e}')
        return False

def generate_application_analytics(application):
    """
    Generate comprehensive analytics for an application
    """
    from applications.models import ApplicationAnalytics
    
    try:
        analytics, created = ApplicationAnalytics.objects.get_or_create(
            application=application
        )
        
        # Calculate metrics
        time_since_application = timezone.now() - application.applied_at
        
        # Update analytics
        analytics.time_to_first_response = time_since_application
        
        if application.status in ['hired', 'rejected']:
            analytics.time_to_decision = time_since_application
        
        # Count interviews
        interview_count = application.interviews.count()
        analytics.interviews_count = interview_count
        
        # Calculate success rate
        if interview_count > 0:
            completed_interviews = application.interviews.filter(status='completed').count()
            analytics.interview_success_rate = (completed_interviews / interview_count) * 100
        
        # Count messages
        analytics.messages_count = application.messages.count()
        
        if application.messages.exists():
            analytics.last_communication = application.messages.latest('sent_at').sent_at
        
        analytics.save()
        
        return analytics
        
    except Exception as e:
        logger.error(f'Failed to generate application analytics: {e}')
        return None

def cleanup_expired_jobs():
    """
    Cleanup and update expired job postings
    """
    try:
        # Mark jobs as expired if deadline has passed
        expired_count = JobPost.objects.filter(
            status='active',
            application_deadline__lt=timezone.now().date()
        ).update(status='expired')
        
        logger.info(f'Marked {expired_count} jobs as expired')
        
        return expired_count
        
    except Exception as e:
        logger.error(f'Failed to cleanup expired jobs: {e}')
        return 0
