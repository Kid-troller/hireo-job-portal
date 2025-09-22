"""
Celery tasks for accounts app
"""
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger('hireo')

@shared_task
def send_welcome_email(user_id, user_type):
    """Send welcome email to new users"""
    try:
        from django.contrib.auth.models import User
        user = User.objects.get(id=user_id)
        
        subject = f"Welcome to Hireo - Your {user_type.title()} Journey Begins!"
        
        if user_type == 'jobseeker':
            message = f"""
            Hi {user.first_name or user.username},
            
            Welcome to Hireo! We're excited to help you find your dream job.
            
            Get started by:
            - Completing your profile
            - Uploading your resume
            - Browsing available positions
            
            Best regards,
            The Hireo Team
            """
        else:
            message = f"""
            Hi {user.first_name or user.username},
            
            Welcome to Hireo! We're excited to help you find the perfect candidates.
            
            Get started by:
            - Setting up your company profile
            - Posting your first job
            - Reviewing applications
            
            Best regards,
            The Hireo Team
            """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        logger.info(f"Welcome email sent to {user.email}")
        
    except Exception as e:
        logger.error(f"Failed to send welcome email to user {user_id}: {e}")

@shared_task
def send_notification_email(user_id, notification_type, subject, message):
    """Send notification emails"""
    try:
        from django.contrib.auth.models import User
        user = User.objects.get(id=user_id)
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        logger.info(f"Notification email sent to {user.email}: {notification_type}")
        
    except Exception as e:
        logger.error(f"Failed to send notification email to user {user_id}: {e}")

@shared_task
def cleanup_expired_tokens():
    """Clean up expired email verification tokens"""
    try:
        from .models import EmailVerificationToken
        from django.utils import timezone
        from datetime import timedelta
        
        expired_tokens = EmailVerificationToken.objects.filter(
            created_at__lt=timezone.now() - timedelta(hours=24)
        )
        count = expired_tokens.count()
        expired_tokens.delete()
        
        logger.info(f"Cleaned up {count} expired verification tokens")
        
    except Exception as e:
        logger.error(f"Failed to cleanup expired tokens: {e}")
