from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db import transaction
import json

from accounts.decorators import employer_required
from applications.models import Application, ApplicationStatus, Notification, Message, Interview
from .models import EmployerProfile

@employer_required
@require_POST
@csrf_exempt
def update_application_status(request):
    """AJAX endpoint to update application status"""
    try:
        data = json.loads(request.body)
        application_id = data.get('application_id')
        new_status = data.get('status')
        notes = data.get('notes', '')
        
        application = get_object_or_404(Application, id=application_id)
        
        # Verify employer owns this application
        try:
            employer_profile = EmployerProfile.objects.get(user_profile__user=request.user)
        except EmployerProfile.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Employer profile not found'})
        if application.employer != employer_profile:
            return JsonResponse({'success': False, 'error': 'Access denied'})
        
        with transaction.atomic():
            # Update application status
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
            Notification.objects.create(
                user=application.applicant.user_profile.user,
                notification_type='application_status',
                title=f'Application Status Updated - {application.job.title}',
                message=f'Your application status has been updated to: {application.get_status_display()}',
                application=application,
                job=application.job
            )
        
        return JsonResponse({
            'success': True,
            'new_status': application.get_status_display(),
            'status_value': new_status
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@employer_required
@require_POST
@csrf_exempt
def send_message_to_applicant(request):
    """AJAX endpoint to send message to applicant"""
    try:
        data = json.loads(request.body)
        application_id = data.get('application_id')
        subject = data.get('subject')
        content = data.get('content')
        
        application = get_object_or_404(Application, id=application_id)
        
        # Verify employer owns this application
        try:
            employer_profile = EmployerProfile.objects.get(user_profile__user=request.user)
        except EmployerProfile.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Employer profile not found'})
        if application.employer != employer_profile:
            return JsonResponse({'success': False, 'error': 'Access denied'})
        
        with transaction.atomic():
            # Create message
            message = Message.objects.create(
                application=application,
                sender=request.user,
                recipient=application.applicant.user_profile.user,
                message_type='application',
                subject=subject,
                content=content
            )
            
            # Create notification
            Notification.objects.create(
                user=application.applicant.user_profile.user,
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

@employer_required
@require_POST
@csrf_exempt
def schedule_interview(request):
    """AJAX endpoint to schedule interview"""
    try:
        data = json.loads(request.body)
        application_id = data.get('application_id')
        interview_type = data.get('interview_type')
        scheduled_date = data.get('scheduled_date')
        duration = data.get('duration', 60)
        instructions = data.get('instructions', '')
        
        application = get_object_or_404(Application, id=application_id)
        
        # Verify employer owns this application
        try:
            employer_profile = EmployerProfile.objects.get(user_profile__user=request.user)
        except EmployerProfile.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Employer profile not found'})
        if application.employer != employer_profile:
            return JsonResponse({'success': False, 'error': 'Access denied'})
        
        with transaction.atomic():
            # Create interview
            interview = Interview.objects.create(
                application=application,
                interview_type=interview_type,
                scheduled_date=scheduled_date,
                duration=duration,
                interviewer_name=request.user.get_full_name(),
                interviewer_email=request.user.email,
                instructions=instructions
            )
            
            # Update application status
            application.status = 'interviewing'
            application.save()
            
            # Create status history
            ApplicationStatus.objects.create(
                application=application,
                status='interviewing',
                notes=f'Interview scheduled for {scheduled_date}',
                changed_by=request.user
            )
            
            # Create notification
            Notification.objects.create(
                user=application.applicant.user_profile.user,
                notification_type='interview_scheduled',
                title=f'Interview Scheduled - {application.job.title}',
                message=f'Your interview has been scheduled for {scheduled_date}',
                application=application,
                interview=interview
            )
        
        return JsonResponse({
            'success': True,
            'message': 'Interview scheduled successfully'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@employer_required
def get_application_details(request, application_id):
    """AJAX endpoint to get application details"""
    try:
        application = get_object_or_404(Application, id=application_id)
        
        # Verify employer owns this application
        try:
            employer_profile = EmployerProfile.objects.get(user_profile__user=request.user)
        except EmployerProfile.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Employer profile not found'})
        if application.employer != employer_profile:
            return JsonResponse({'success': False, 'error': 'Access denied'})
        
        applicant = application.applicant
        user = applicant.user_profile.user
        
        data = {
            'success': True,
            'application': {
                'id': application.id,
                'status': application.status,
                'status_display': application.get_status_display(),
                'applied_at': application.applied_at.strftime('%Y-%m-%d %H:%M'),
                'cover_letter': application.cover_letter,
                'resume_url': application.resume.url if application.resume else None,
            },
            'applicant': {
                'name': user.get_full_name(),
                'email': user.email,
                'phone': getattr(user, 'phone', ''),
                'skills': applicant.skills,
                'experience_years': applicant.experience_years,
                'current_position': applicant.current_position,
                'expected_salary_min': applicant.expected_salary_min,
                'expected_salary_max': applicant.expected_salary_max,
            },
            'job': {
                'title': application.job.title,
                'company': application.job.company.name,
            }
        }
        
        return JsonResponse(data)
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@employer_required
def get_applications_for_job(request, job_id):
    """AJAX endpoint to get applications for a specific job"""
    try:
        from jobs.models import JobPost
        job = get_object_or_404(JobPost, id=job_id)
        
        # Verify employer owns this job
        try:
            employer_profile = EmployerProfile.objects.get(user_profile__user=request.user)
        except EmployerProfile.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Employer profile not found'})
        if job.company != employer_profile.company:
            return JsonResponse({'success': False, 'error': 'Access denied'})
        
        applications = Application.objects.filter(job=job).select_related(
            'applicant__user_profile__user'
        ).order_by('-applied_at')
        
        applications_data = []
        for app in applications:
            user = app.applicant.user_profile.user
            applications_data.append({
                'id': app.id,
                'applicant_name': user.get_full_name(),
                'applicant_email': user.email,
                'status': app.status,
                'status_display': app.get_status_display(),
                'applied_at': app.applied_at.strftime('%Y-%m-%d %H:%M'),
                'skills': app.applicant.skills,
                'experience_years': app.applicant.experience_years,
            })
        
        return JsonResponse({
            'success': True,
            'applications': applications_data,
            'job_title': job.title
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
