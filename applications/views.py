from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from django.db import transaction
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.contrib.auth.models import User
from datetime import datetime, timedelta
import json

from .models import (
    Application, ApplicationStatus, Interview, Message, 
    Notification, ApplicationAnalytics, ApplicationView
)
from accounts.models import JobSeekerProfile, UserProfile
from employers.models import EmployerProfile
from jobs.models import JobPost
from accounts.decorators import jobseeker_required
from accounts.decorators import employer_required
from .notification_utils import NotificationManager

@login_required
def application_list(request):
    """List of user's job applications"""
    if request.user.userprofile.user_type == 'jobseeker':
        applications = Application.objects.filter(applicant__user_profile__user=request.user)
    else:
        applications = Application.objects.filter(employer__user_profile__user=request.user)

    context = {
        'applications': applications
    }
    return render(request, 'applications/application_list.html', context)

@login_required
def application_detail(request, application_id):
    """Detail view of a job application"""
    application = get_object_or_404(Application, id=application_id)

    # Check if user has permission to view this application
    if (request.user.userprofile.user_type == 'jobseeker' and
        application.applicant.user_profile.user != request.user):
        messages.error(request, 'Access denied.')
        return redirect('applications:list')

    if (request.user.userprofile.user_type == 'employer' and
        application.employer.user_profile.user != request.user):
        messages.error(request, 'Access denied.')
        return redirect('applications:list')

    # Get application messages (not Django framework messages)
    from applications.models import Message
    application_messages = Message.objects.filter(
        application=application
    ).order_by('-sent_at')[:5]
    
    # Get interviews and status history
    interviews = application.interviews.all()[:5] if hasattr(application, 'interviews') else []
    status_history = application.status_history.all().order_by('-changed_at')
    
    # If no status history exists, create an initial one for the current status
    if not status_history.exists():
        from applications.models import ApplicationStatus
        ApplicationStatus.objects.create(
            application=application,
            status=application.status,
            notes=f'Application submitted for {application.job.title}',
            changed_by=application.applicant.user_profile.user
        )
        status_history = application.status_history.all().order_by('-changed_at')
    
    # Determine user type for template
    is_employer = hasattr(request.user, 'userprofile') and request.user.userprofile.user_type == 'employer'
    is_applicant = hasattr(request.user, 'userprofile') and request.user.userprofile.user_type == 'job_seeker'
    
    # Calculate progress percentage based on status
    status_progress = {
        'applied': 20,
        'reviewing': 40,
        'shortlisted': 60,
        'interviewing': 80,
        'hired': 100,
        'rejected': 100,
        'withdrawn': 100,
    }
    progress_percentage = status_progress.get(application.status, 20)
    
    context = {
        'application': application,
        'application_messages': application_messages,
        'interviews': interviews,
        'status_history': status_history,
        'is_employer': is_employer,
        'is_applicant': is_applicant,
        'progress_percentage': progress_percentage,
    }
    return render(request, 'applications/application_detail.html', context)

@login_required
@require_POST
def mark_notification_read(request, notification_id):
    """Mark a notification as read"""
    success = NotificationManager.mark_notification_read(notification_id, request.user)
    return JsonResponse({'success': success})

@login_required
def get_notifications(request):
    """Get user notifications via AJAX"""
    notifications = NotificationManager.get_user_notifications(request.user, limit=10)
    notification_counts = NotificationManager.get_notification_counts(request.user)
    
    notifications_data = []
    for notification in notifications:
        notifications_data.append({
            'id': notification.id,
            'type': notification.notification_type,
            'title': notification.title,
            'message': notification.message,
            'is_read': notification.is_read,
            'created_at': notification.created_at.isoformat(),
            'application_id': notification.application.id if notification.application else None,
            'job_title': notification.application.job.title if notification.application else None,
        })
    
    return JsonResponse({
        'notifications': notifications_data,
        'counts': notification_counts
    })

@login_required
def update_application_status(request, application_id):
    """Update application status and create notification"""
    if request.method == 'POST':
        try:
            application = get_object_or_404(Application, id=application_id)
            
            # Check permission - only employer can update status
            if (request.user.userprofile.user_type != 'employer' or
                application.employer.user_profile.user != request.user):
                return JsonResponse({'success': False, 'error': 'Permission denied'})
            
            new_status = request.POST.get('status')
            notes = request.POST.get('notes', '')
            
            if new_status not in dict(Application.STATUS_CHOICES):
                return JsonResponse({'success': False, 'error': 'Invalid status'})
            
            old_status = application.status
            application.status = new_status
            application.save()
            
            # Create status history
            ApplicationStatus.objects.create(
                application=application,
                status=new_status,
                notes=notes,
                changed_by=request.user
            )
            
            # Create notification for job seeker
            NotificationManager.create_application_status_notification(
                application, old_status, new_status, request.user
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Application status updated to {new_status}'
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
def notification_list(request):
    """Display all notifications for user"""
    notifications = NotificationManager.get_user_notifications(request.user, limit=50)
    notification_counts = NotificationManager.get_notification_counts(request.user)
    
    context = {
        'notifications': notifications,
        'notification_counts': notification_counts,
    }
    return render(request, 'applications/notifications.html', context)

@login_required
@require_POST
def mark_notifications_read(request):
    """Mark multiple notifications as read"""
    notification_ids = request.POST.getlist('notification_ids')
    success_count = 0
    
    for notification_id in notification_ids:
        if NotificationManager.mark_notification_read(notification_id, request.user):
            success_count += 1
    
    return JsonResponse({
        'success': success_count > 0,
        'marked_count': success_count
    })

@login_required
@require_POST
def mark_all_notifications_read(request):
    """Mark all notifications as read for user"""
    try:
        notifications = Notification.objects.filter(user=request.user, is_read=False)
        count = notifications.count()
        notifications.update(is_read=True, read_at=timezone.now())
        
        return JsonResponse({
            'success': True,
            'marked_count': count
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

# Missing view functions for URL patterns
@login_required
def send_message(request, application_id):
    """Send message related to application"""
    application = get_object_or_404(Application, id=application_id)
    
    if request.method == 'POST':
        subject = request.POST.get('subject')
        content = request.POST.get('content')
        
        # Determine sender and recipient
        if request.user.userprofile.user_type == 'employer':
            recipient = application.applicant.user_profile.user
        else:
            recipient = application.employer.user_profile.user
        
        # Create message
        message = Message.objects.create(
            application=application,
            sender=request.user,
            recipient=recipient,
            subject=subject,
            content=content
        )
        
        # Create notification
        NotificationManager.create_message_notification(message)
        
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
def view_messages(request, application_id):
    """View messages for application"""
    application = get_object_or_404(Application, id=application_id)
    messages_list = Message.objects.filter(application=application).order_by('-sent_at')
    
    context = {
        'application': application,
        'messages': messages_list,
    }
    return render(request, 'applications/messages.html', context)

@login_required
def schedule_interview(request, application_id):
    """Schedule interview for application"""
    application = get_object_or_404(Application, id=application_id)
    
    if request.method == 'POST':
        # Create interview
        interview = Interview.objects.create(
            application=application,
            interview_type=request.POST.get('interview_type'),
            scheduled_date=request.POST.get('scheduled_date'),
            interviewer_name=request.POST.get('interviewer_name'),
            interviewer_email=request.POST.get('interviewer_email'),
            instructions=request.POST.get('instructions', '')
        )
        
        # Create notification
        NotificationManager.create_interview_notification(interview)
        
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
def view_history(request, application_id):
    """View application status history"""
    application = get_object_or_404(Application, id=application_id)
    status_history = ApplicationStatus.objects.filter(application=application).order_by('-changed_at')
    
    context = {
        'application': application,
        'status_history': status_history,
    }
    return render(request, 'applications/history.html', context)

@login_required
def withdraw_application(request, application_id):
    """Withdraw job application"""
    application = get_object_or_404(Application, id=application_id)
    
    # Check permission
    if application.applicant.user_profile.user != request.user:
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    if request.method == 'POST':
        application.status = 'withdrawn'
        application.save()
        
        # Create status history
        ApplicationStatus.objects.create(
            application=application,
            status='withdrawn',
            notes='Application withdrawn by job seeker',
            changed_by=request.user
        )
        
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
def message_list(request):
    """List all messages for user"""
    messages_list = Message.objects.filter(
        Q(sender=request.user) | Q(recipient=request.user)
    ).order_by('-sent_at')
    
    context = {'messages': messages_list}
    return render(request, 'applications/message_list.html', context)

@login_required
def message_detail(request, message_id):
    """View message detail"""
    message = get_object_or_404(Message, id=message_id)
    
    # Check permission
    if message.sender != request.user and message.recipient != request.user:
        messages.error(request, 'Access denied.')
        return redirect('applications:message_list')
    
    # Mark as read if recipient
    if message.recipient == request.user and not message.is_read:
        message.is_read = True
        message.read_at = timezone.now()
        message.save()
    
    context = {'message': message}
    return render(request, 'applications/message_detail.html', context)

@login_required
def interview_list(request):
    """List interviews for user"""
    if request.user.userprofile.user_type == 'jobseeker':
        interviews = Interview.objects.filter(
            application__applicant__user_profile__user=request.user
        ).order_by('-scheduled_date')
    else:
        interviews = Interview.objects.filter(
            application__employer__user_profile__user=request.user
        ).order_by('-scheduled_date')
    
    context = {'interviews': interviews}
    return render(request, 'applications/interview_list.html', context)

@login_required
def interview_detail(request, interview_id):
    """View interview detail"""
    interview = get_object_or_404(Interview, id=interview_id)
    
    context = {'interview': interview}
    return render(request, 'applications/interview_detail.html', context)

@login_required
def download_resume(request, application_id):
    """Download resume for application"""
    application = get_object_or_404(Application, id=application_id)
    
    if application.resume:
        response = HttpResponse(application.resume.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{application.applicant.user_profile.user.get_full_name()}_resume.pdf"'
        return response
    
    return HttpResponse('Resume not found', status=404)

@login_required
def view_resume(request, application_id):
    """View resume for application"""
    application = get_object_or_404(Application, id=application_id)
    
    if application.resume:
        response = HttpResponse(application.resume.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{application.applicant.user_profile.user.get_full_name()}_resume.pdf"'
        return response
    
    return HttpResponse('Resume not found', status=404)

@login_required
def update_status(request, application_id):
    """Update application status (employers only)"""
    if request.method == 'POST':
        application = get_object_or_404(Application, id=application_id)
        new_status = request.POST.get('status')

        if request.user.userprofile.user_type == 'employer':
            application.status = new_status
            application.save()
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'message': 'Access denied'})

    return JsonResponse({'success': False, 'message': 'Invalid request'})

@employer_required
def enhanced_schedule_interview(request, application_id):
    """Enhanced interview scheduling with comprehensive features"""
    if request.method == 'POST':
        try:
            user_profile = request.user.userprofile
            try:
                employer_profile = EmployerProfile.objects.get(user_profile=user_profile)
            except EmployerProfile.DoesNotExist:
                messages.error(request, 'Employer profile not found. Please complete your company profile first.')
                return redirect('employer:dashboard')
            
            application = get_object_or_404(
                Application, 
                id=application_id, 
                job__company=employer_profile.company
            )
            
            # Extract form data
            interview_type = request.POST.get('interview_type')
            scheduled_date = request.POST.get('scheduled_date')
            scheduled_time = request.POST.get('scheduled_time')
            duration = int(request.POST.get('duration', 60))
            interviewer_name = request.POST.get('interviewer_name')
            interviewer_email = request.POST.get('interviewer_email')
            interviewer_phone = request.POST.get('interviewer_phone', '')
            location = request.POST.get('location', '')
            video_platform = request.POST.get('video_platform', '')
            meeting_link = request.POST.get('meeting_link', '')
            instructions = request.POST.get('instructions', '')
            
            # Combine date and time
            scheduled_datetime = datetime.strptime(
                f"{scheduled_date} {scheduled_time}", 
                "%Y-%m-%d %H:%M"
            )
            
            # Create interview with transaction safety
            with transaction.atomic():
                interview = Interview.objects.create(
                    application=application,
                    interview_type=interview_type,
                    scheduled_date=scheduled_datetime,
                    duration=duration,
                    interviewer_name=interviewer_name,
                    interviewer_email=interviewer_email,
                    interviewer_phone=interviewer_phone,
                    location=location,
                    video_platform=video_platform,
                    meeting_link=meeting_link,
                    instructions=instructions
                )
                
                # Update application status to interviewing
                if application.status != 'interviewing':
                    old_status = application.status
                    application.status = 'interviewing'
                    application.save()
                    
                    # Create status history
                    ApplicationStatus.objects.create(
                        application=application,
                        status='interviewing',
                        notes=f'Interview scheduled for {scheduled_datetime.strftime("%B %d, %Y at %I:%M %p")}',
                        changed_by=request.user
                    )
                
                # Create notification for job seeker
                Notification.objects.create(
                    user=application.applicant.user_profile.user,
                    notification_type='interview_scheduled',
                    title=f'Interview Scheduled - {application.job.title}',
                    message=f'Your interview has been scheduled for {scheduled_datetime.strftime("%B %d, %Y at %I:%M %p")}',
                    application=application,
                    interview=interview
                )
            
            messages.success(
                request, 
                f'Interview scheduled successfully for {scheduled_datetime.strftime("%B %d, %Y at %I:%M %p")}!'
            )
            
        except Exception as e:
            messages.error(request, f'Error scheduling interview: {str(e)}')
    
    return redirect('employer:application_detail', application_id=application_id)

@login_required
def schedule_interview(request, application_id):
    """Schedule interview for an application"""
    application = get_object_or_404(Application, id=application_id)

    if request.method == 'POST':
        # Handle interview scheduling
        pass

    context = {
        'application': application
    }
    return render(request, 'applications/schedule_interview.html', context)

@login_required
def interview_detail(request, interview_id):
    """Detail view of an interview"""
    interview = get_object_or_404(Interview, id=interview_id)

    context = {
        'interview': interview
    }
    return render(request, 'applications/interview_detail.html', context)

@login_required
def update_interview(request, interview_id):
    """Update interview details"""
    interview = get_object_or_404(Interview, id=interview_id)

    if request.method == 'POST':
        # Handle interview updates
        pass

    context = {
        'interview': interview
    }
    return render(request, 'applications/update_interview.html', context)

@login_required
def message_list(request, application_id):
    """List of messages for an application"""
    application = get_object_or_404(Application, id=application_id)
    messages_list = Message.objects.filter(application=application)

    context = {
        'application': application,
        'messages': messages_list
    }
    return render(request, 'applications/message_list.html', context)

@login_required
def enhanced_send_message(request, application_id):
    """Enhanced message sending with comprehensive features"""
    if request.method == 'POST':
        try:
            application = get_object_or_404(Application, id=application_id)
            
            # Check authorization
            user_profile = request.user.userprofile
            is_employer = (user_profile.user_type == 'employer' and 
                          application.job.company == user_profile.employerprofile.company)
            is_applicant = (user_profile.user_type == 'jobseeker' and 
                           application.applicant == user_profile.jobseekerprofile)
            
            if not (is_employer or is_applicant):
                messages.error(request, 'You are not authorized to send messages for this application.')
                return redirect('accounts:dashboard')
            
            subject = request.POST.get('subject', '').strip()
            content = request.POST.get('content', '').strip()
            message_type = request.POST.get('message_type', 'general')
            
            if not subject or not content:
                messages.error(request, 'Subject and message content are required.')
                return redirect(request.META.get('HTTP_REFERER', 'accounts:dashboard'))
            
            # Determine recipient
            if is_employer:
                recipient = application.applicant.user_profile.user
            else:
                recipient = application.employer.user_profile.user
            
            # Create message with transaction safety
            with transaction.atomic():
                message = Message.objects.create(
                    application=application,
                    sender=request.user,
                    recipient=recipient,
                    message_type=message_type,
                    subject=subject,
                    content=content
                )
                
                # Handle file attachment if provided
                if 'attachment' in request.FILES:
                    message.attachment = request.FILES['attachment']
                    message.save()
                
                # Create notification for recipient
                Notification.objects.create(
                    user=recipient,
                    notification_type='message_received',
                    title=f'New Message: {subject}',
                    message=f'You have received a new message from {request.user.get_full_name() or request.user.username}',
                    application=application
                )
            
            messages.success(request, 'Message sent successfully!')
            
        except Exception as e:
            messages.error(request, f'Error sending message: {str(e)}')
    
    return redirect(request.META.get('HTTP_REFERER', 'accounts:dashboard'))

@login_required
def send_message(request, application_id):
    """Send a message for an application"""
    if request.method == 'POST':
        try:
            application = get_object_or_404(Application, id=application_id)
            
            # Check user permissions
            user_profile = request.user.userprofile
            is_employer = (user_profile.user_type == 'employer' and 
                          application.employer.user_profile.user == request.user)
            is_applicant = (user_profile.user_type == 'jobseeker' and 
                           application.applicant.user_profile.user == request.user)
            
            if not (is_employer or is_applicant):
                return JsonResponse({'success': False, 'error': 'Permission denied'})
            
            subject = request.POST.get('subject', '').strip()
            content = request.POST.get('content', '').strip()

            if not subject or not content:
                return JsonResponse({'success': False, 'error': 'Subject and content are required'})
            
            # Determine recipient
            if is_employer:
                recipient = application.applicant.user_profile.user
            else:
                recipient = application.employer.user_profile.user
            
            # Create message with transaction safety
            with transaction.atomic():
                message = Message.objects.create(
                    application=application,
                    sender=request.user,
                    recipient=recipient,
                    subject=subject,
                    content=content
                )
                
                # Create notification for real-time updates
                Notification.objects.create(
                    user=recipient,
                    notification_type='message_received',
                    title=f'New Message: {subject}',
                    message=f'You have received a new message from {request.user.get_full_name() or request.user.username}',
                    application=application
                )
            
            return JsonResponse({'success': True, 'message_id': message.id})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
def notification_list(request):
    """List of user notifications"""
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')

    context = {
        'notifications': notifications
    }
    return render(request, 'applications/notification_list.html', context)

@login_required
def mark_notifications_read(request):
    """Mark notifications as read"""
    if request.method == 'POST':
        notification_ids = request.POST.getlist('notification_ids')
        Notification.objects.filter(id__in=notification_ids, user=request.user).update(is_read=True)
        return JsonResponse({'success': True})

    return JsonResponse({'success': False})

# ============================================================================
# ENHANCED APPLICATION WORKFLOW VIEWS
# ============================================================================

@login_required
def interview_response(request, interview_id):
    """Job seeker response to interview invitation"""
    if request.method == 'POST':
        try:
            interview = get_object_or_404(Interview, id=interview_id)
            
            # Check if user is the applicant
            user_profile = request.user.userprofile
            if (user_profile.user_type != 'jobseeker' or 
                interview.application.applicant != user_profile.jobseekerprofile):
                messages.error(request, 'You are not authorized to respond to this interview.')
                return redirect('accounts:dashboard')
            
            response = request.POST.get('response')  # 'accept' or 'decline'
            notes = request.POST.get('notes', '')
            
            with transaction.atomic():
                if response == 'accept':
                    interview.status = 'confirmed'
                    interview.notes = f"Accepted by applicant. {notes}".strip()
                    interview.save()
                    
                    # Create notification for employer
                    Notification.objects.create(
                        user=interview.application.employer.user_profile.user,
                        notification_type='interview_scheduled',
                        title=f'Interview Confirmed - {interview.application.job.title}',
                        message=f'{request.user.get_full_name()} has confirmed the interview scheduled for {interview.scheduled_date.strftime("%B %d, %Y at %I:%M %p")}',
                        application=interview.application,
                        interview=interview
                    )
                    
                    messages.success(request, 'Interview confirmed successfully!')
                    
                elif response == 'decline':
                    interview.status = 'cancelled'
                    interview.notes = f"Declined by applicant. Reason: {notes}".strip()
                    interview.save()
                    
                    # Create notification for employer
                    Notification.objects.create(
                        user=interview.application.employer.user_profile.user,
                        notification_type='interview_scheduled',
                        title=f'Interview Declined - {interview.application.job.title}',
                        message=f'{request.user.get_full_name()} has declined the interview. Reason: {notes}',
                        application=interview.application,
                        interview=interview
                    )
                    
                    messages.info(request, 'Interview declined. The employer has been notified.')
            
        except Exception as e:
            messages.error(request, f'Error responding to interview: {str(e)}')
    
    return redirect('accounts:applications')

@jobseeker_required
def application_history(request):
    """Comprehensive application history for job seekers"""
    try:
        user_profile = request.user.userprofile
        job_seeker_profile = user_profile.jobseekerprofile
        
        # Get all applications with related data
        applications = Application.objects.filter(
            applicant=job_seeker_profile
        ).select_related(
            'job', 'job__company', 'job__category', 'job__location'
        ).prefetch_related(
            'status_history', 'interviews', 'messages'
        ).order_by('-applied_at')
        
        # Filter by status if provided
        status_filter = request.GET.get('status')
        if status_filter:
            applications = applications.filter(status=status_filter)
        
        # Search by job title or company
        search = request.GET.get('search')
        if search:
            applications = applications.filter(
                Q(job__title__icontains=search) |
                Q(job__company__name__icontains=search)
            )
        
        # Pagination
        paginator = Paginator(applications, 10)
        page_number = request.GET.get('page')
        applications_page = paginator.get_page(page_number)
        
        # Application statistics
        total_applications = applications.count()
        status_stats = {}
        for status_code, status_name in Application.STATUS_CHOICES:
            count = applications.filter(status=status_code).count()
            status_stats[status_code] = {
                'name': status_name,
                'count': count,
                'percentage': (count / total_applications * 100) if total_applications > 0 else 0
            }
        
        context = {
            'applications': applications_page,
            'status_choices': Application.STATUS_CHOICES,
            'current_status': status_filter,
            'search_query': search,
            'status_stats': status_stats,
            'total_applications': total_applications,
        }
        
        return render(request, 'applications/application_history.html', context)
        
    except Exception as e:
        messages.error(request, f'Error loading application history: {str(e)}')
        return redirect('accounts:dashboard')

@login_required
def application_detail_view(request, application_id):
    """Detailed view of a single application for both employers and job seekers"""
    try:
        user_profile = request.user.userprofile
        
        if user_profile.user_type == 'jobseeker':
            application = get_object_or_404(
                Application, 
                id=application_id, 
                applicant=user_profile.jobseekerprofile
            )
        elif user_profile.user_type == 'employer':
            employer_profile = user_profile.employerprofile
            application = get_object_or_404(
                Application, 
                id=application_id, 
                job__company=employer_profile.company
            )
        else:
            messages.error(request, 'You are not authorized to view this application.')
            return redirect('accounts:dashboard')
        
        # Get status history
        status_history = ApplicationStatus.objects.filter(
            application=application
        ).order_by('-changed_at')
        
        # Get interviews
        interviews = Interview.objects.filter(
            application=application
        ).order_by('-scheduled_date')
        
        # Get messages
        message_list = Message.objects.filter(
            application=application
        ).order_by('sent_at')
        
        # Mark messages as read for current user
        Message.objects.filter(
            application=application,
            recipient=request.user,
            is_read=False
        ).update(is_read=True, read_at=timezone.now())
        
        # Track application view (for analytics)
        if user_profile.user_type == 'employer':
            ApplicationView.objects.create(
                application=application,
                viewer=request.user,
                ip_address=request.META.get('REMOTE_ADDR', ''),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            # Update analytics
            analytics, created = ApplicationAnalytics.objects.get_or_create(
                application=application
            )
            analytics.employer_views += 1
            analytics.last_viewed = timezone.now()
            analytics.save()
        
        context = {
            'application': application,
            'status_history': status_history,
            'interviews': interviews,
            'messages': message_list,
            'is_employer': user_profile.user_type == 'employer',
            'is_applicant': user_profile.user_type == 'jobseeker',
        }
        
        return render(request, 'applications/application_detail_view.html', context)
        
    except Exception as e:
        messages.error(request, f'Error loading application details: {str(e)}')
        return redirect('accounts:dashboard')

@login_required
def message_thread(request, application_id):
    """View message thread for an application"""
    try:
        application = get_object_or_404(Application, id=application_id)
        
        # Check authorization
        user_profile = request.user.userprofile
        is_employer = (user_profile.user_type == 'employer' and 
                      application.job.company == user_profile.employerprofile.company)
        is_applicant = (user_profile.user_type == 'jobseeker' and 
                       application.applicant == user_profile.jobseekerprofile)
        
        if not (is_employer or is_applicant):
            messages.error(request, 'You are not authorized to view this conversation.')
            return redirect('accounts:dashboard')
        
        # Get all messages for this application
        message_list = Message.objects.filter(
            application=application
        ).order_by('sent_at')
        
        # Mark messages as read for current user
        Message.objects.filter(
            application=application,
            recipient=request.user,
            is_read=False
        ).update(is_read=True, read_at=timezone.now())
        
        context = {
            'application': application,
            'messages': message_list,
            'is_employer': is_employer,
            'is_applicant': is_applicant,
        }
        
        return render(request, 'applications/message_thread.html', context)
        
    except Exception as e:
        messages.error(request, f'Error loading messages: {str(e)}')
        return redirect('accounts:dashboard')

@login_required
@require_POST
def mark_notification_read(request, notification_id):
    """Mark a notification as read"""
    try:
        notification = get_object_or_404(
            Notification, 
            id=notification_id, 
            user=request.user
        )
        
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save()
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@require_POST
def mark_all_notifications_read(request):
    """Mark all notifications as read for the user"""
    try:
        Notification.objects.filter(
            user=request.user,
            is_read=False
        ).update(is_read=True, read_at=timezone.now())
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def download_resume(request, application_id):
    """Download resume from an application"""
    import os
    try:
        user_profile = request.user.userprofile
        
        if user_profile.user_type == 'employer':
            employer_profile = user_profile.employerprofile
            application = get_object_or_404(
                Application, 
                id=application_id, 
                job__company=employer_profile.company
            )
        else:
            messages.error(request, 'You are not authorized to download this resume.')
            return redirect('accounts:dashboard')
        
        if application.resume:
            # Check if file actually exists
            if not os.path.exists(application.resume.path):
                messages.error(request, 'Resume file not found on server. The file may have been moved or deleted.')
                return redirect('applications:detail', application_id=application_id)
            
            try:
                # Get file extension and set appropriate content type
                file_extension = application.resume.name.split('.')[-1].lower()
                
                if file_extension == 'pdf':
                    content_type = 'application/pdf'
                elif file_extension in ['doc', 'docx']:
                    content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                else:
                    content_type = 'application/octet-stream'
                
                # Read file content
                with open(application.resume.path, 'rb') as f:
                    file_content = f.read()
                
                response = HttpResponse(file_content, content_type=content_type)
                
                # Set proper filename with extension
                filename = f"{application.applicant.user_profile.user.get_full_name()}_resume.{file_extension}"
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                return response
                
            except IOError as e:
                messages.error(request, f'Error reading resume file: {str(e)}')
                return redirect('applications:detail', application_id=application_id)
        else:
            messages.error(request, 'No resume found for this application.')
            return redirect('applications:detail', application_id=application_id)
            
    except Exception as e:
        messages.error(request, f'Error downloading resume: {str(e)}')
        return redirect('applications:detail', application_id=application_id)

@login_required
def view_resume(request, application_id):
    """View resume inline in browser"""
    try:
        application = get_object_or_404(Application, id=application_id)
        
        # Check permissions - both employer and applicant can view
        user_profile = request.user.userprofile
        
        if user_profile.user_type == 'employer':
            # Employer can view if application is for their company
            employer_profile = user_profile.employerprofile
            if application.job.company != employer_profile.company:
                messages.error(request, 'You are not authorized to view this resume.')
                return redirect('employer:manage_applications')
        elif user_profile.user_type == 'jobseeker':
            # Job seeker can view their own resume
            if application.applicant.user_profile.user != request.user:
                messages.error(request, 'You are not authorized to view this resume.')
                return redirect('accounts:applications')
        else:
            messages.error(request, 'You are not authorized to view this resume.')
            return redirect('accounts:dashboard')
        
        if application.resume:
            # Get file extension to determine content type
            file_extension = application.resume.name.split('.')[-1].lower()
            
            if file_extension == 'pdf':
                content_type = 'application/pdf'
            elif file_extension in ['doc', 'docx']:
                content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            else:
                content_type = 'application/octet-stream'
            
            # For PDF files, display inline
            if file_extension == 'pdf':
                response = HttpResponse(
                    application.resume.read(), 
                    content_type=content_type
                )
                response['Content-Disposition'] = f'inline; filename="{application.applicant.user_profile.user.get_full_name()}_resume.pdf"'
                return response
            else:
                # For DOCX files, serve directly for download or show preview page
                if file_extension in ['doc', 'docx']:
                    # Build absolute URL for external viewers
                    resume_url = request.build_absolute_uri(application.resume.url)
                    context = {
                        'application': application,
                        'resume_url': resume_url,
                        'file_extension': file_extension,
                        'is_employer': user_profile.user_type == 'employer'
                    }
                    return render(request, 'applications/resume_viewer.html', context)
                else:
                    # For other files, just show download option
                    context = {
                        'application': application,
                        'resume_url': application.resume.url,
                        'file_extension': file_extension,
                        'is_employer': user_profile.user_type == 'employer'
                    }
                    return render(request, 'applications/resume_viewer.html', context)
        else:
            messages.error(request, 'No resume found for this application.')
            return redirect('applications:detail', application_id=application_id)
            
    except Exception as e:
        messages.error(request, f'Error viewing resume: {str(e)}')
        return redirect('applications:detail', application_id=application_id)
