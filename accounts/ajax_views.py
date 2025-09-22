from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db import transaction
import json

from accounts.decorators import jobseeker_required
from applications.models import Application, ApplicationStatus, Notification, Message, Interview
from accounts.models import JobSeekerProfile

@jobseeker_required
def get_application_status_updates(request):
    """AJAX endpoint to get real-time application status updates for job seekers"""
    try:
        user_profile = request.user.userprofile
        try:
            job_seeker_profile = JobSeekerProfile.objects.get(user_profile=user_profile)
        except JobSeekerProfile.DoesNotExist:
            job_seeker_profile = JobSeekerProfile.objects.create(user_profile=user_profile)
        
        # Get applications with latest status
        applications = Application.objects.filter(
            applicant=job_seeker_profile
        ).select_related(
            'job__company', 'employer__user_profile__user'
        ).prefetch_related('status_history').order_by('-applied_at')
        
        applications_data = []
        for app in applications:
            # Get latest status from history
            latest_status = app.status_history.first()
            
            applications_data.append({
                'id': app.id,
                'job_title': app.job.title,
                'company_name': app.job.company.name,
                'status': app.status,
                'status_display': app.get_status_display(),
                'applied_at': app.applied_at.strftime('%Y-%m-%d %H:%M'),
                'updated_at': app.updated_at.strftime('%Y-%m-%d %H:%M'),
                'latest_status_notes': latest_status.notes if latest_status else '',
                'latest_status_date': latest_status.changed_at.strftime('%Y-%m-%d %H:%M') if latest_status else '',
                'employer_name': app.employer.user_profile.user.get_full_name(),
                'has_messages': app.messages.exists(),
                'unread_messages': app.messages.filter(is_read=False, recipient=request.user).count(),
                'has_interviews': app.interviews.exists(),
                'next_interview': None,
                'shortlist_instructions': app.shortlist_instructions if hasattr(app, 'shortlist_instructions') else None
            })
            
            # Get next interview if exists
            next_interview = app.interviews.filter(
                scheduled_date__gte=timezone.now(),
                status__in=['scheduled', 'confirmed']
            ).order_by('scheduled_date').first()
            
            if next_interview:
                applications_data[-1]['next_interview'] = {
                    'id': next_interview.id,
                    'type': next_interview.get_interview_type_display(),
                    'date': next_interview.scheduled_date.strftime('%Y-%m-%d %H:%M'),
                    'status': next_interview.get_status_display()
                }
        
        return JsonResponse({
            'success': True,
            'applications': applications_data,
            'total_count': len(applications_data)
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@jobseeker_required
def get_notifications(request):
    """AJAX endpoint to get notifications for job seekers"""
    try:
        notifications = Notification.objects.filter(
            user=request.user
        ).order_by('-created_at')[:20]
        
        notifications_data = []
        for notif in notifications:
            notifications_data.append({
                'id': notif.id,
                'type': notif.notification_type,
                'title': notif.title,
                'message': notif.message,
                'is_read': notif.is_read,
                'created_at': notif.created_at.strftime('%Y-%m-%d %H:%M'),
                'application_id': notif.application.id if notif.application else None,
                'job_title': notif.job.title if notif.job else None,
            })
        
        unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
        
        return JsonResponse({
            'success': True,
            'notifications': notifications_data,
            'unread_count': unread_count
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@jobseeker_required
@require_POST
@csrf_exempt
def mark_notification_read(request):
    """AJAX endpoint to mark notification as read"""
    try:
        data = json.loads(request.body)
        notification_id = data.get('notification_id')
        
        notification = get_object_or_404(Notification, id=notification_id, user=request.user)
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save()
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@jobseeker_required
@require_POST
@csrf_exempt
def respond_to_interview(request):
    """AJAX endpoint for job seekers to respond to interview invitations"""
    try:
        data = json.loads(request.body)
        interview_id = data.get('interview_id')
        response = data.get('response')  # 'confirmed' or 'declined'
        notes = data.get('notes', '')
        
        interview = get_object_or_404(Interview, id=interview_id)
        
        # Verify job seeker owns this interview
        user_profile = request.user.userprofile
        try:
            job_seeker_profile = JobSeekerProfile.objects.get(user_profile=user_profile)
        except JobSeekerProfile.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Job seeker profile not found'})
        if interview.application.applicant != job_seeker_profile:
            return JsonResponse({'success': False, 'error': 'Access denied'})
        
        with transaction.atomic():
            # Update interview status
            if response == 'confirmed':
                interview.status = 'confirmed'
                interview.notes = f"Confirmed by candidate. {notes}".strip()
            elif response == 'declined':
                interview.status = 'cancelled'
                interview.notes = f"Declined by candidate. {notes}".strip()
            
            interview.save()
            
            # Create notification for employer
            Notification.objects.create(
                user=interview.application.employer.user_profile.user,
                notification_type='interview_scheduled',
                title=f'Interview Response - {interview.application.job.title}',
                message=f'{request.user.get_full_name()} has {response} the interview scheduled for {interview.scheduled_date.strftime("%B %d, %Y at %I:%M %p")}',
                application=interview.application,
                interview=interview
            )
        
        return JsonResponse({
            'success': True,
            'message': f'Interview {response} successfully'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@jobseeker_required
def get_application_messages(request, application_id):
    """AJAX endpoint to get messages for a specific application"""
    try:
        application = get_object_or_404(Application, id=application_id)
        
        # Verify job seeker owns this application
        user_profile = request.user.userprofile
        try:
            job_seeker_profile = JobSeekerProfile.objects.get(user_profile=user_profile)
        except JobSeekerProfile.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Job seeker profile not found'})
        if application.applicant != job_seeker_profile:
            return JsonResponse({'success': False, 'error': 'Access denied'})
        
        messages = Message.objects.filter(application=application).order_by('-sent_at')
        
        messages_data = []
        for msg in messages:
            messages_data.append({
                'id': msg.id,
                'sender_name': msg.sender.get_full_name(),
                'sender_is_employer': msg.sender != request.user,
                'subject': msg.subject,
                'content': msg.content,
                'sent_at': msg.sent_at.strftime('%Y-%m-%d %H:%M'),
                'is_read': msg.is_read,
                'attachment_url': msg.attachment.url if msg.attachment else None
            })
        
        # Mark messages as read
        Message.objects.filter(
            application=application,
            recipient=request.user,
            is_read=False
        ).update(is_read=True, read_at=timezone.now())
        
        return JsonResponse({
            'success': True,
            'messages': messages_data,
            'application': {
                'job_title': application.job.title,
                'company_name': application.job.company.name,
                'status': application.get_status_display()
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@jobseeker_required
@require_POST
@csrf_exempt
def send_message_to_employer(request):
    """AJAX endpoint for job seekers to send messages to employers"""
    try:
        data = json.loads(request.body)
        application_id = data.get('application_id')
        subject = data.get('subject')
        content = data.get('content')
        
        application = get_object_or_404(Application, id=application_id)
        
        # Verify job seeker owns this application
        user_profile = request.user.userprofile
        try:
            job_seeker_profile = JobSeekerProfile.objects.get(user_profile=user_profile)
        except JobSeekerProfile.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Job seeker profile not found'})
        if application.applicant != job_seeker_profile:
            return JsonResponse({'success': False, 'error': 'Access denied'})
        
        with transaction.atomic():
            # Create message
            message = Message.objects.create(
                application=application,
                sender=request.user,
                recipient=application.employer.user_profile.user,
                message_type='application',
                subject=subject,
                content=content
            )
            
            # Create notification for employer
            Notification.objects.create(
                user=application.employer.user_profile.user,
                notification_type='message_received',
                title=f'New Message: {subject}',
                message=f'You have received a new message from {request.user.get_full_name()}',
                application=application
            )
        
        return JsonResponse({
            'success': True,
            'message': 'Message sent successfully'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
