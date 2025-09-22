"""
Enhanced application management system for employers
"""
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Count, Avg, F
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from datetime import datetime, timedelta
import json

from accounts.decorators import employer_required
from applications.models import Application, ApplicationStatus, Notification, Interview, ApplicationAnalytics
from jobs.models import JobPost
from jobs.utils import update_application_status, send_realtime_notification

logger = logging.getLogger(__name__)

@employer_required
def applications_list(request):
    """
    Enhanced applications list with filtering, sorting, and bulk actions
    """
    try:
        employer_profile = request.user.userprofile.employerprofile
        
        # Get all applications for this employer
        applications = Application.objects.filter(
            employer=employer_profile
        ).select_related(
            'job', 'applicant__user_profile__user', 'applicant__user_profile'
        ).prefetch_related('status_history', 'interviews')
        
        # Apply filters
        status_filter = request.GET.get('status')
        if status_filter and status_filter != 'all':
            applications = applications.filter(status=status_filter)
        
        job_filter = request.GET.get('job')
        if job_filter:
            applications = applications.filter(job_id=job_filter)
        
        date_filter = request.GET.get('date_range')
        if date_filter:
            if date_filter == '24h':
                applications = applications.filter(applied_at__gte=timezone.now() - timedelta(hours=24))
            elif date_filter == '7d':
                applications = applications.filter(applied_at__gte=timezone.now() - timedelta(days=7))
            elif date_filter == '30d':
                applications = applications.filter(applied_at__gte=timezone.now() - timedelta(days=30))
        
        search_query = request.GET.get('search')
        if search_query:
            applications = applications.filter(
                Q(applicant__user_profile__user__first_name__icontains=search_query) |
                Q(applicant__user_profile__user__last_name__icontains=search_query) |
                Q(applicant__user_profile__user__email__icontains=search_query) |
                Q(job__title__icontains=search_query) |
                Q(cover_letter__icontains=search_query)
            )
        
        # Sorting
        sort_by = request.GET.get('sort', '-applied_at')
        valid_sorts = [
            'applied_at', '-applied_at',
            'status', '-status',
            'job__title', '-job__title',
            'applicant__user_profile__user__first_name', '-applicant__user_profile__user__first_name'
        ]
        
        if sort_by in valid_sorts:
            applications = applications.order_by(sort_by)
        else:
            applications = applications.order_by('-applied_at')
        
        # Pagination
        paginator = Paginator(applications, 20)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        # Get employer's jobs for filter dropdown
        employer_jobs = JobPost.objects.filter(employer=employer_profile).values('id', 'title')
        
        # Get status counts for quick filters
        status_counts = Application.objects.filter(employer=employer_profile).values('status').annotate(
            count=Count('id')
        )
        
        context = {
            'applications': page_obj,
            'employer_jobs': employer_jobs,
            'status_counts': {item['status']: item['count'] for item in status_counts},
            'current_filters': {
                'status': status_filter,
                'job': job_filter,
                'date_range': date_filter,
                'search': search_query,
                'sort': sort_by
            },
            'total_applications': applications.count()
        }
        
        return render(request, 'employers/applications_list.html', context)
        
    except Exception as e:
        logger.error(f'Error in applications_list: {e}')
        messages.error(request, 'An error occurred while loading applications.')
        return redirect('employer:dashboard')

@employer_required
def application_detail(request, application_id):
    """
    Detailed view of a single application with full candidate information
    """
    try:
        employer_profile = request.user.userprofile.employerprofile
        application = get_object_or_404(
            Application.objects.select_related(
                'job', 'applicant__user_profile__user', 'applicant__user_profile'
            ).prefetch_related('status_history', 'interviews', 'messages'),
            id=application_id,
            employer=employer_profile
        )
        
        # Mark application as viewed
        ApplicationAnalytics.objects.filter(application=application).update(
            employer_views=F('employer_views') + 1,
            last_viewed=timezone.now()
        )
        
        # Get candidate's other applications to this company
        candidate_applications = Application.objects.filter(
            applicant=application.applicant,
            employer=employer_profile
        ).exclude(id=application.id).select_related('job')
        
        # Get status history
        status_history = application.status_history.all().order_by('-changed_at')
        
        # Get interviews
        interviews = application.interviews.all().order_by('-scheduled_date')
        
        # Get messages
        messages_list = application.messages.all().order_by('-sent_at')
        
        # Calculate application metrics
        time_since_application = timezone.now() - application.applied_at
        
        context = {
            'application': application,
            'candidate_applications': candidate_applications,
            'status_history': status_history,
            'interviews': interviews,
            'messages': messages_list,
            'time_since_application': time_since_application,
            'available_statuses': Application.STATUS_CHOICES
        }
        
        return render(request, 'employers/application_detail.html', context)
        
    except Exception as e:
        logger.error(f'Error in application_detail: {e}')
        messages.error(request, 'Application not found or access denied.')
        return redirect('employer:applications_list')

@employer_required
@require_POST
def update_application_status_view(request, application_id):
    """
    Update application status with proper tracking and notifications
    """
    try:
        employer_profile = request.user.userprofile.employerprofile
        application = get_object_or_404(
            Application,
            id=application_id,
            employer=employer_profile
        )
        
        data = json.loads(request.body)
        new_status = data.get('status')
        notes = data.get('notes', '')
        
        # Validate status
        valid_statuses = [choice[0] for choice in Application.STATUS_CHOICES]
        if new_status not in valid_statuses:
            return JsonResponse({'error': 'Invalid status'}, status=400)
        
        # Update status using utility function
        success = update_application_status(
            application=application,
            new_status=new_status,
            notes=notes,
            changed_by=request.user
        )
        
        if success:
            return JsonResponse({
                'success': True,
                'message': f'Application status updated to {new_status}',
                'new_status': new_status,
                'status_display': dict(Application.STATUS_CHOICES)[new_status]
            })
        else:
            return JsonResponse({'error': 'Failed to update status'}, status=500)
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f'Error updating application status: {e}')
        return JsonResponse({'error': 'An error occurred'}, status=500)

@employer_required
@require_POST
def bulk_update_applications(request):
    """
    Bulk update multiple applications
    """
    try:
        employer_profile = request.user.userprofile.employerprofile
        data = json.loads(request.body)
        
        application_ids = data.get('application_ids', [])
        action = data.get('action')
        new_status = data.get('status')
        notes = data.get('notes', '')
        
        if not application_ids or not action:
            return JsonResponse({'error': 'Missing required data'}, status=400)
        
        # Get applications
        applications = Application.objects.filter(
            id__in=application_ids,
            employer=employer_profile
        )
        
        if not applications.exists():
            return JsonResponse({'error': 'No valid applications found'}, status=400)
        
        updated_count = 0
        
        if action == 'update_status' and new_status:
            for application in applications:
                success = update_application_status(
                    application=application,
                    new_status=new_status,
                    notes=f'Bulk update: {notes}' if notes else f'Bulk status update to {new_status}',
                    changed_by=request.user
                )
                if success:
                    updated_count += 1
        
        elif action == 'mark_reviewed':
            applications.update(reviewed_at=timezone.now())
            updated_count = applications.count()
        
        elif action == 'archive':
            # Custom archive logic if needed
            updated_count = applications.count()
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully updated {updated_count} applications',
            'updated_count': updated_count
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f'Error in bulk update: {e}')
        return JsonResponse({'error': 'An error occurred'}, status=500)

@employer_required
def application_analytics(request):
    """
    Analytics dashboard for applications
    """
    try:
        employer_profile = request.user.userprofile.employerprofile
        
        # Get date range
        days = int(request.GET.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)
        
        # Basic metrics
        total_applications = Application.objects.filter(employer=employer_profile).count()
        recent_applications = Application.objects.filter(
            employer=employer_profile,
            applied_at__gte=start_date
        ).count()
        
        # Status breakdown
        status_breakdown = Application.objects.filter(
            employer=employer_profile
        ).values('status').annotate(count=Count('id'))
        
        # Applications by job
        applications_by_job = Application.objects.filter(
            employer=employer_profile
        ).values('job__title').annotate(count=Count('id')).order_by('-count')[:10]
        
        # Time-based analytics
        applications_by_date = Application.objects.filter(
            employer=employer_profile,
            applied_at__gte=start_date
        ).extra(
            select={'date': 'DATE(applied_at)'}
        ).values('date').annotate(count=Count('id')).order_by('date')
        
        # Response time analytics
        avg_response_times = ApplicationAnalytics.objects.filter(
            application__employer=employer_profile,
            time_to_first_response__isnull=False
        ).aggregate(
            avg_response=Avg('time_to_first_response')
        )
        
        # Conversion rates
        conversion_data = {}
        for status in ['applied', 'reviewing', 'shortlisted', 'interviewing', 'offered', 'hired']:
            count = Application.objects.filter(employer=employer_profile, status=status).count()
            conversion_data[status] = {
                'count': count,
                'percentage': (count / total_applications * 100) if total_applications > 0 else 0
            }
        
        context = {
            'total_applications': total_applications,
            'recent_applications': recent_applications,
            'status_breakdown': status_breakdown,
            'applications_by_job': applications_by_job,
            'applications_by_date': list(applications_by_date),
            'avg_response_times': avg_response_times,
            'conversion_data': conversion_data,
            'days': days
        }
        
        return render(request, 'employers/application_analytics.html', context)
        
    except Exception as e:
        logger.error(f'Error in application analytics: {e}')
        messages.error(request, 'An error occurred while loading analytics.')
        return redirect('employer:dashboard')

@employer_required
def candidate_search(request):
    """
    Advanced candidate search and filtering
    """
    try:
        employer_profile = request.user.userprofile.employerprofile
        
        # Get search parameters
        query = request.GET.get('q', '')
        skills = request.GET.get('skills', '')
        experience_min = request.GET.get('experience_min')
        experience_max = request.GET.get('experience_max')
        location = request.GET.get('location', '')
        education = request.GET.get('education', '')
        
        # Base queryset - candidates who have applied to this employer
        candidates = Application.objects.filter(
            employer=employer_profile
        ).select_related(
            'applicant__user_profile__user', 'applicant__user_profile'
        ).distinct()
        
        # Apply filters
        if query:
            candidates = candidates.filter(
                Q(applicant__user_profile__user__first_name__icontains=query) |
                Q(applicant__user_profile__user__last_name__icontains=query) |
                Q(applicant__user_profile__user__email__icontains=query) |
                Q(applicant__skills__icontains=query) |
                Q(applicant__bio__icontains=query)
            )
        
        if skills:
            skill_list = [s.strip() for s in skills.split(',')]
            for skill in skill_list:
                candidates = candidates.filter(applicant__skills__icontains=skill)
        
        if experience_min:
            candidates = candidates.filter(applicant__experience_years__gte=int(experience_min))
        
        if experience_max:
            candidates = candidates.filter(applicant__experience_years__lte=int(experience_max))
        
        if location:
            candidates = candidates.filter(
                Q(applicant__location__icontains=location) |
                Q(applicant__preferred_location__icontains=location)
            )
        
        if education:
            candidates = candidates.filter(applicant__education__icontains=education)
        
        # Pagination
        paginator = Paginator(candidates, 20)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'candidates': page_obj,
            'search_params': {
                'q': query,
                'skills': skills,
                'experience_min': experience_min,
                'experience_max': experience_max,
                'location': location,
                'education': education
            },
            'total_candidates': candidates.count()
        }
        
        return render(request, 'employers/candidate_search.html', context)
        
    except Exception as e:
        logger.error(f'Error in candidate search: {e}')
        messages.error(request, 'An error occurred while searching candidates.')
        return redirect('employer:dashboard')
