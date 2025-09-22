"""
Celery tasks for jobs app
"""
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
import logging

logger = logging.getLogger('hireo')

@shared_task
def send_job_alert_emails():
    """Send job alert emails to job seekers"""
    try:
        from .models import JobPost
        from accounts.models import JobSeekerProfile
        from datetime import timedelta
        
        # Get jobs posted in the last 24 hours
        recent_jobs = JobPost.objects.filter(
            status='active',
            created_at__gte=timezone.now() - timedelta(hours=24)
        )
        
        if not recent_jobs.exists():
            return
        
        # Get job seekers who want alerts
        job_seekers = JobSeekerProfile.objects.filter(
            user_profile__user__is_active=True
        )
        
        for job_seeker in job_seekers:
            matching_jobs = []
            for job in recent_jobs:
                # Simple matching based on skills or category
                if (job_seeker.skills and job.required_skills and 
                    any(skill.lower() in job.required_skills.lower() 
                        for skill in job_seeker.skills.split(','))):
                    matching_jobs.append(job)
            
            if matching_jobs:
                send_job_matches_email.delay(job_seeker.id, [job.id for job in matching_jobs])
        
        logger.info(f"Processed job alerts for {recent_jobs.count()} new jobs")
        
    except Exception as e:
        logger.error(f"Failed to send job alert emails: {e}")

@shared_task
def send_job_matches_email(job_seeker_id, job_ids):
    """Send job matches email to a specific job seeker"""
    try:
        from accounts.models import JobSeekerProfile
        from .models import JobPost
        
        try:
            job_seeker = JobSeekerProfile.objects.get(id=job_seeker_id)
        except JobSeekerProfile.DoesNotExist:
            logger.error(f"JobSeekerProfile with id {job_seeker_id} not found")
            return
        jobs = JobPost.objects.filter(id__in=job_ids)
        
        if not jobs.exists():
            return
        
        subject = f"New Job Matches Found - {jobs.count()} Opportunities"
        
        job_list = "\n".join([
            f"• {job.title} at {job.company.name} - {job.location.city}"
            for job in jobs
        ])
        
        message = f"""
        Hi {job_seeker.user_profile.user.first_name or job_seeker.user_profile.user.username},
        
        We found {jobs.count()} new job(s) that match your profile:
        
        {job_list}
        
        Visit Hireo to view details and apply!
        
        Best regards,
        The Hireo Team
        """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [job_seeker.user_profile.user.email],
            fail_silently=False,
        )
        
        logger.info(f"Job matches email sent to {job_seeker.user_profile.user.email}")
        
    except Exception as e:
        logger.error(f"Failed to send job matches email: {e}")

@shared_task
def update_job_analytics():
    """Update job analytics and statistics"""
    try:
        from .models import JobPost
        from applications.models import Application
        from django.db.models import Count, Avg
        
        # Update view counts, application rates, etc.
        jobs = JobPost.objects.filter(status='active')
        
        for job in jobs:
            app_count = Application.objects.filter(job=job).count()
            # Update job analytics here
            
        logger.info(f"Updated analytics for {jobs.count()} jobs")
        
    except Exception as e:
        logger.error(f"Failed to update job analytics: {e}")

@shared_task
def cleanup_expired_jobs():
    """Clean up expired job postings"""
    try:
        from .models import JobPost
        from datetime import timedelta
        
        # Mark jobs as expired after 90 days
        expired_jobs = JobPost.objects.filter(
            status='active',
            created_at__lt=timezone.now() - timedelta(days=90)
        )
        
        count = expired_jobs.count()
        expired_jobs.update(status='expired')
        
        logger.info(f"Marked {count} jobs as expired")
        
    except Exception as e:
        logger.error(f"Failed to cleanup expired jobs: {e}")
