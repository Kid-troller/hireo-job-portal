from django.contrib.auth.models import User
from django.utils import timezone
from .models import Notification, Application, Interview, Message
import logging

logger = logging.getLogger('hireo')

class NotificationManager:
    """Utility class for managing notifications"""
    
    @staticmethod
    def create_application_status_notification(application, old_status, new_status, changed_by):
        """Create notification when application status changes"""
        try:
            # Notification for job seeker
            job_seeker_user = application.applicant.user_profile.user
            
            status_messages = {
                'reviewing': f"Your application for '{application.job.title}' is now under review",
                'shortlisted': f"Congratulations! You've been shortlisted for '{application.job.title}'",
                'interviewing': f"Interview scheduled for '{application.job.title}' position",
                'offered': f"Job offer received for '{application.job.title}' position!",
                'hired': f"Congratulations! You've been hired for '{application.job.title}'",
                'rejected': f"Application for '{application.job.title}' was not successful"
            }
            
            message = status_messages.get(new_status, f"Application status updated to {new_status}")
            
            Notification.objects.create(
                user=job_seeker_user,
                notification_type='application_status',
                title=f"Application Status Update",
                message=message,
                application=application
            )
            
            logger.info(f"Created status notification for user {job_seeker_user.username}: {new_status}")
            
        except Exception as e:
            logger.error(f"Error creating application status notification: {e}")
    
    @staticmethod
    def create_new_application_notification(application):
        """Create notification when new application is submitted"""
        try:
            # Notification for employer
            employer_user = application.employer.user_profile.user
            
            Notification.objects.create(
                user=employer_user,
                notification_type='application_viewed',
                title="New Job Application",
                message=f"New application received for '{application.job.title}' from {application.applicant.user_profile.user.get_full_name()}",
                application=application
            )
            
            logger.info(f"Created new application notification for employer {employer_user.username}")
            
        except Exception as e:
            logger.error(f"Error creating new application notification: {e}")
    
    @staticmethod
    def create_message_notification(message):
        """Create notification when message is sent"""
        try:
            Notification.objects.create(
                user=message.recipient,
                notification_type='message_received',
                title=f"New Message from {message.sender.get_full_name()}",
                message=f"Subject: {message.subject}",
                application=message.application
            )
            
            logger.info(f"Created message notification for user {message.recipient.username}")
            
        except Exception as e:
            logger.error(f"Error creating message notification: {e}")
    
    @staticmethod
    def create_interview_notification(interview):
        """Create notification when interview is scheduled"""
        try:
            # Notification for job seeker
            job_seeker_user = interview.application.applicant.user_profile.user
            
            Notification.objects.create(
                user=job_seeker_user,
                notification_type='interview_scheduled',
                title="Interview Scheduled",
                message=f"Interview scheduled for '{interview.application.job.title}' on {interview.scheduled_date.strftime('%B %d, %Y at %I:%M %p')}",
                application=interview.application,
                interview=interview
            )
            
            logger.info(f"Created interview notification for user {job_seeker_user.username}")
            
        except Exception as e:
            logger.error(f"Error creating interview notification: {e}")
    
    @staticmethod
    def get_user_notifications(user, limit=10, unread_only=False):
        """Get notifications for a user"""
        try:
            notifications = Notification.objects.filter(user=user)
            
            if unread_only:
                notifications = notifications.filter(is_read=False)
            
            return notifications.order_by('-created_at')[:limit]
            
        except Exception as e:
            logger.error(f"Error getting user notifications: {e}")
            return []
    
    @staticmethod
    def mark_notification_read(notification_id, user):
        """Mark notification as read"""
        try:
            notification = Notification.objects.get(id=notification_id, user=user)
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save()
            
            logger.info(f"Marked notification {notification_id} as read for user {user.username}")
            return True
            
        except Notification.DoesNotExist:
            logger.warning(f"Notification {notification_id} not found for user {user.username}")
            return False
        except Exception as e:
            logger.error(f"Error marking notification as read: {e}")
            return False
    
    @staticmethod
    def get_notification_counts(user):
        """Get notification counts for a user"""
        try:
            total = Notification.objects.filter(user=user).count()
            unread = Notification.objects.filter(user=user, is_read=False).count()
            
            return {
                'total': total,
                'unread': unread
            }
            
        except Exception as e:
            logger.error(f"Error getting notification counts: {e}")
            return {'total': 0, 'unread': 0}
