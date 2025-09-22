from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Count, Q, Sum, Avg
from django.utils import timezone
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import send_mail
from django.conf import settings as django_settings
from datetime import datetime, timedelta
import json
import csv
import zipfile
import os
from io import BytesIO

from .models import AdminActivity, SystemSettings, PlatformStatistics, UserReport, MaintenanceMode, EmailTemplate, SystemAlert
from accounts.models import UserProfile, JobSeekerProfile
from employers.models import EmployerProfile, Company
from jobs.models import JobPost, JobCategory, JobLocation
from applications.models import Application


def is_admin(user):
    """Check if user is superuser only"""
    return user.is_authenticated and user.is_superuser


def log_admin_activity(admin_user, activity_type, description, target_model=None, target_id=None, request=None):
    """Log admin activity for audit trail"""
    ip_address = None
    if request:
        ip_address = request.META.get('REMOTE_ADDR')
    
    # Provide default empty string if target_model is None
    if target_model is None:
        target_model = ''
    
    AdminActivity.objects.create(
        admin_user=admin_user,
        activity_type=activity_type,
        description=description,
        target_model=target_model,
        target_id=target_id,
        ip_address=ip_address
    )


@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    """Main admin dashboard with overview statistics"""
    # Get current statistics
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)
    last_week = today - timedelta(days=7)
    last_month = today - timedelta(days=30)
    
    # User statistics
    total_users = User.objects.count()
    new_users_today = User.objects.filter(date_joined__date=today).count()
    new_users_week = User.objects.filter(date_joined__gte=last_week).count()
    active_users_week = User.objects.filter(last_login__gte=last_week).count()
    
    # Job statistics
    total_jobs = JobPost.objects.count()
    active_jobs = JobPost.objects.filter(status='active').count()
    new_jobs_today = JobPost.objects.filter(published_at__date=today).count()
    new_jobs_week = JobPost.objects.filter(published_at__gte=last_week).count()
    
    # Application statistics
    total_applications = Application.objects.count()
    new_applications_today = Application.objects.filter(applied_at__date=today).count()
    new_applications_week = Application.objects.filter(applied_at__gte=last_week).count()
    successful_applications = Application.objects.filter(status='hired').count()
    
    # Company statistics
    total_companies = Company.objects.count()
    active_companies = Company.objects.filter(is_active=True).count()
    
    # Recent activities
    recent_activities = AdminActivity.objects.select_related('admin_user')[:10]
    
    # System alerts
    unread_alerts = SystemAlert.objects.filter(is_read=False).order_by('-priority', '-created_at')[:5]
    
    # Pending reports
    pending_reports = UserReport.objects.filter(status='pending').count()
    
    # Chart data for the last 30 days
    chart_data = []
    for i in range(30):
        date = today - timedelta(days=i)
        stats = PlatformStatistics.objects.filter(date=date).first()
        if stats:
            chart_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'users': stats.new_users,
                'jobs': stats.new_jobs,
                'applications': stats.new_applications
            })
        else:
            chart_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'users': 0,
                'jobs': 0,
                'applications': 0
            })
    
    chart_data.reverse()  # Show oldest to newest
    
    context = {
        'total_users': total_users,
        'new_users_today': new_users_today,
        'new_users_week': new_users_week,
        'active_users_week': active_users_week,
        'total_jobs': total_jobs,
        'active_jobs': active_jobs,
        'new_jobs_today': new_jobs_today,
        'new_jobs_week': new_jobs_week,
        'total_applications': total_applications,
        'new_applications_today': new_applications_today,
        'new_applications_week': new_applications_week,
        'successful_applications': successful_applications,
        'total_companies': total_companies,
        'active_companies': active_companies,
        'recent_activities': recent_activities,
        'unread_alerts': unread_alerts,
        'pending_reports': pending_reports,
        'chart_data': json.dumps(chart_data),
    }
    
    # Check if user is impersonating
    context['impersonating'] = request.session.get('impersonating', False)
    context['original_user_id'] = request.session.get('original_user_id')
    
    return render(request, 'admin_panel/dashboard.html', context)


@login_required
@user_passes_test(is_admin)
def user_management(request):
    """User management interface"""
    # Get filter parameters
    user_type = request.GET.get('type', '')
    status = request.GET.get('status', '')
    search = request.GET.get('search', '')
    
    # Base queryset - fix prefetch_related relationships
    users = User.objects.select_related('userprofile')
    
    # Apply filters
    if user_type == 'jobseeker':
        users = users.filter(userprofile__user_type='jobseeker')
    elif user_type == 'employer':
        users = users.filter(userprofile__user_type='employer')
    
    if status == 'active':
        users = users.filter(is_active=True)
    elif status == 'inactive':
        users = users.filter(is_active=False)
    
    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(users.order_by('-date_joined'), 25)
    page_number = request.GET.get('page')
    users_page = paginator.get_page(page_number)
    
    # Statistics
    user_stats = {
        'total': User.objects.count(),
        'jobseekers': User.objects.filter(userprofile__user_type='jobseeker').count(),
        'employers': User.objects.filter(userprofile__user_type='employer').count(),
        'active': User.objects.filter(is_active=True).count(),
        'inactive': User.objects.filter(is_active=False).count(),
    }
    
    context = {
        'users': users_page,
        'user_stats': user_stats,
        'current_filters': {
            'type': user_type,
            'status': status,
            'search': search,
        }
    }
    
    return render(request, 'admin_panel/user_management.html', context)


@login_required
@user_passes_test(is_admin)
def job_management(request):
    """Job management interface"""
    # Get filter parameters
    status = request.GET.get('status', '')
    category = request.GET.get('category', '')
    search = request.GET.get('search', '')
    
    # Base queryset
    jobs = JobPost.objects.select_related('company', 'category', 'location')
    
    # Apply filters
    if status:
        jobs = jobs.filter(status=status)
    
    if category:
        jobs = jobs.filter(category_id=category)
    
    if search:
        jobs = jobs.filter(
            Q(title__icontains=search) |
            Q(company__name__icontains=search) |
            Q(description__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(jobs.order_by('-published_at'), 25)
    page_number = request.GET.get('page')
    jobs_page = paginator.get_page(page_number)
    
    # Statistics
    job_stats = {
        'total': JobPost.objects.count(),
        'active': JobPost.objects.filter(status='active').count(),
        'draft': JobPost.objects.filter(status='draft').count(),
        'inactive': JobPost.objects.filter(status='inactive').count(),
        'expired': JobPost.objects.filter(status='expired').count(),
    }
    
    # Categories for filter
    categories = JobCategory.objects.all()
    
    context = {
        'jobs': jobs_page,
        'job_stats': job_stats,
        'categories': categories,
        'current_filters': {
            'status': status,
            'category': category,
            'search': search,
        }
    }
    
    return render(request, 'admin_panel/job_management.html', context)


@login_required
@user_passes_test(is_admin)
def application_management(request):
    """Application management interface"""
    # Get filter parameters
    status = request.GET.get('status', '')
    search = request.GET.get('search', '')
    
    # Base queryset
    applications = Application.objects.select_related('job', 'applicant__user_profile__user', 'job__company')
    
    # Apply filters
    if status:
        applications = applications.filter(status=status)
    
    if search:
        applications = applications.filter(
            Q(job__title__icontains=search) |
            Q(applicant__user_profile__user__username__icontains=search) |
            Q(job__company__name__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(applications.order_by('-applied_at'), 25)
    page_number = request.GET.get('page')
    applications_page = paginator.get_page(page_number)
    
    # Statistics
    application_stats = {
        'total': Application.objects.count(),
        'applied': Application.objects.filter(status='applied').count(),
        'reviewing': Application.objects.filter(status='reviewing').count(),
        'shortlisted': Application.objects.filter(status='shortlisted').count(),
        'interviewing': Application.objects.filter(status='interviewing').count(),
        'hired': Application.objects.filter(status='hired').count(),
        'rejected': Application.objects.filter(status='rejected').count(),
    }
    
    context = {
        'applications': applications_page,
        'application_stats': application_stats,
        'current_filters': {
            'status': status,
            'search': search,
        }
    }
    
    return render(request, 'admin_panel/application_management.html', context)


@login_required
@user_passes_test(is_admin)
def reports_management(request):
    """User reports management"""
    # Get filter parameters
    status = request.GET.get('status', '')
    report_type = request.GET.get('type', '')
    
    # Base queryset
    reports = UserReport.objects.select_related('reporter', 'assigned_admin')
    
    # Apply filters
    if status:
        reports = reports.filter(status=status)
    
    if report_type:
        reports = reports.filter(report_type=report_type)
    
    # Pagination
    paginator = Paginator(reports.order_by('-created_at'), 25)
    page_number = request.GET.get('page')
    reports_page = paginator.get_page(page_number)
    
    # Statistics
    report_stats = {
        'total': UserReport.objects.count(),
        'pending': UserReport.objects.filter(status='pending').count(),
        'investigating': UserReport.objects.filter(status='investigating').count(),
        'resolved': UserReport.objects.filter(status='resolved').count(),
        'dismissed': UserReport.objects.filter(status='dismissed').count(),
    }
    
    context = {
        'reports': reports_page,
        'report_stats': report_stats,
        'current_filters': {
            'status': status,
            'type': report_type,
        }
    }
    
    return render(request, 'admin_panel/reports_management.html', context)


@login_required
@user_passes_test(is_admin)
def system_settings(request):
    """System settings management"""
    # Get all settings as a dictionary for easy template access
    settings_queryset = SystemSettings.objects.filter(is_active=True)
    settings_dict = {setting.key: setting.value for setting in settings_queryset}
    
    context = {
        'settings': settings_dict,
    }
    
    return render(request, 'admin_panel/system_settings.html', context)


@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def save_system_settings(request):
    """Save system settings via AJAX"""
    try:
        # Update settings
        for key, value in request.POST.items():
            if key != 'csrfmiddlewaretoken':
                # Handle checkbox values
                if value == 'on':
                    value = 'true'
                elif value == 'off':
                    value = 'false'
                
                setting, created = SystemSettings.objects.get_or_create(
                    key=key,
                    defaults={'value': value, 'updated_by': request.user}
                )
                if not created:
                    setting.value = value
                    setting.updated_by = request.user
                    setting.save()
        
        log_admin_activity(
            request.user,
            'settings_changed',
            'System settings updated',
            request=request
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Settings saved successfully!'
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def reset_system_settings(request):
    """Reset system settings to defaults"""
    try:
        # Delete all current settings to reset to defaults
        SystemSettings.objects.all().delete()
        
        log_admin_activity(
            request.user,
            'settings_reset',
            'System settings reset to defaults',
            request=request
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Settings reset to defaults successfully!'
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def test_email_settings(request):
    """Test email configuration"""
    try:
        test_email = request.user.email or 'admin@hireo.com'
        
        send_mail(
            'Hireo - Email Configuration Test',
            'This is a test email to verify your email configuration is working correctly.',
            django_settings.DEFAULT_FROM_EMAIL,
            [test_email],
            fail_silently=False,
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Test email sent successfully to {test_email}!'
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Email test failed: {str(e)}'
        })


@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def run_maintenance_tasks(request):
    """Run system maintenance tasks"""
    try:
        tasks_completed = []
        
        # Clean up old log entries
        old_logs = AdminActivity.objects.filter(
            timestamp__lt=timezone.now() - timedelta(days=90)
        )
        deleted_logs = old_logs.count()
        old_logs.delete()
        tasks_completed.append(f'Cleaned up {deleted_logs} old log entries')
        
        # Clean up old system alerts
        old_alerts = SystemAlert.objects.filter(
            created_at__lt=timezone.now() - timedelta(days=30),
            is_read=True
        )
        deleted_alerts = old_alerts.count()
        old_alerts.delete()
        tasks_completed.append(f'Cleaned up {deleted_alerts} old alerts')
        
        # Update platform statistics
        today = timezone.now().date()
        stats, created = PlatformStatistics.objects.get_or_create(
            date=today,
            defaults={
                'new_users': User.objects.filter(date_joined__date=today).count(),
                'new_jobs': JobPost.objects.filter(published_at__date=today).count(),
                'new_applications': Application.objects.filter(applied_at__date=today).count(),
                'revenue': 0.00
            }
        )
        if created:
            tasks_completed.append('Updated platform statistics for today')
        
        log_admin_activity(
            request.user,
            'maintenance_run',
            f'Maintenance tasks completed: {", ".join(tasks_completed)}',
            request=request
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Maintenance completed: {", ".join(tasks_completed)}'
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Maintenance failed: {str(e)}'
        })


@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def create_system_backup(request):
    """Create and download system backup"""
    try:
        # Create a zip file in memory
        zip_buffer = BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Export users data
            users_data = []
            for user in User.objects.all():
                users_data.append({
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'date_joined': user.date_joined.isoformat(),
                    'is_active': user.is_active
                })
            zip_file.writestr('users.json', json.dumps(users_data, indent=2))
            
            # Export jobs data
            jobs_data = []
            for job in JobPost.objects.select_related('company', 'category'):
                jobs_data.append({
                    'id': job.id,
                    'title': job.title,
                    'company': job.company.name if job.company else '',
                    'category': job.category.name if job.category else '',
                    'status': job.status,
                    'published_at': job.published_at.isoformat() if job.published_at else None
                })
            zip_file.writestr('jobs.json', json.dumps(jobs_data, indent=2))
            
            # Export applications data
            applications_data = []
            for app in Application.objects.select_related('job', 'applicant'):
                applications_data.append({
                    'id': app.id,
                    'job_title': app.job.title,
                    'status': app.status,
                    'applied_at': app.applied_at.isoformat()
                })
            zip_file.writestr('applications.json', json.dumps(applications_data, indent=2))
            
            # Export system settings
            settings_data = []
            for setting in SystemSettings.objects.all():
                settings_data.append({
                    'key': setting.key,
                    'value': setting.value,
                    'updated_at': setting.updated_at.isoformat()
                })
            zip_file.writestr('settings.json', json.dumps(settings_data, indent=2))
        
        zip_buffer.seek(0)
        
        log_admin_activity(
            request.user,
            'backup_created',
            'System backup created and downloaded',
            request=request
        )
        
        response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="hireo_backup_{timezone.now().strftime("%Y%m%d_%H%M%S")}.zip"'
        
        return response
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Backup creation failed: {str(e)}'
        })


@login_required
@user_passes_test(is_admin)
def analytics_dashboard(request):
    """Advanced analytics dashboard"""
    # Date range
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)
    
    # Get period from request
    period = int(request.GET.get('period', 30))
    start_date = end_date - timedelta(days=period)
    
    # Current statistics
    total_users = User.objects.count()
    active_jobs = JobPost.objects.filter(status='active').count()
    total_applications = Application.objects.count()
    
    # Calculate growth percentages
    last_month_start = start_date - timedelta(days=period)
    last_month_users = User.objects.filter(date_joined__date__range=[last_month_start, start_date]).count()
    last_month_jobs = JobPost.objects.filter(published_at__date__range=[last_month_start, start_date]).count()
    last_month_applications = Application.objects.filter(applied_at__date__range=[last_month_start, start_date]).count()
    
    current_users = User.objects.filter(date_joined__date__range=[start_date, end_date]).count()
    current_jobs = JobPost.objects.filter(published_at__date__range=[start_date, end_date]).count()
    current_applications = Application.objects.filter(applied_at__date__range=[start_date, end_date]).count()
    
    user_growth = ((current_users - last_month_users) / max(last_month_users, 1)) * 100 if last_month_users > 0 else 0
    job_growth = ((current_jobs - last_month_jobs) / max(last_month_jobs, 1)) * 100 if last_month_jobs > 0 else 0
    application_growth = ((current_applications - last_month_applications) / max(last_month_applications, 1)) * 100 if last_month_applications > 0 else 0
    
    # Get statistics for the period
    stats = PlatformStatistics.objects.filter(
        date__range=[start_date, end_date]
    ).order_by('date')
    
    # If no stats exist, create dummy data for demonstration
    if not stats.exists():
        chart_data = {
            'dates': [(start_date + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(period)],
            'users': [User.objects.filter(date_joined__date=start_date + timedelta(days=i)).count() for i in range(period)],
            'jobs': [JobPost.objects.filter(published_at__date=start_date + timedelta(days=i)).count() for i in range(period)],
            'applications': [Application.objects.filter(applied_at__date=start_date + timedelta(days=i)).count() for i in range(period)],
            'revenue': [0.0 for i in range(period)],
        }
    else:
        # Prepare chart data from existing stats
        chart_data = {
            'dates': [stat.date.strftime('%Y-%m-%d') for stat in stats],
            'users': [stat.new_users for stat in stats],
            'jobs': [stat.new_jobs for stat in stats],
            'applications': [stat.new_applications for stat in stats],
            'revenue': [float(stat.revenue) for stat in stats],
        }
    
    # Top performing categories
    top_categories = JobCategory.objects.annotate(
        job_count=Count('jobs'),
        application_count=Count('jobs__job_applications')
    ).order_by('-job_count')[:10]
    
    # User engagement metrics
    engagement_metrics = {
        'avg_session_duration': '12:34',
        'bounce_rate': '23.4%',
        'page_views_per_session': '4.2',
        'conversion_rate': '8.7%',
    }
    
    # Recent activities
    recent_activities = AdminActivity.objects.select_related('admin_user').order_by('-timestamp')[:10]
    
    context = {
        'chart_data': json.dumps(chart_data),
        'top_categories': top_categories,
        'engagement_metrics': engagement_metrics,
        'start_date': start_date,
        'end_date': end_date,
        'total_users': total_users,
        'active_jobs': active_jobs,
        'total_applications': total_applications,
        'total_revenue': sum(chart_data['revenue']),
        'user_growth': round(user_growth, 1),
        'job_growth': round(job_growth, 1),
        'application_growth': round(application_growth, 1),
        'revenue_growth': 15.2,  # Placeholder
        'recent_activities': recent_activities,
        'period': period,
    }
    
    return render(request, 'admin_panel/analytics_dashboard.html', context)


@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def toggle_user_status(request, user_id):
    """Toggle user active/inactive status"""
    user = get_object_or_404(User, id=user_id)
    user.is_active = not user.is_active
    user.save()
    
    action = "activated" if user.is_active else "deactivated"
    log_admin_activity(
        request.user,
        'user_action',
        f'User {user.username} {action}',
        'User',
        user.id,
        request
    )
    
    return JsonResponse({
        'success': True,
        'status': 'active' if user.is_active else 'inactive',
        'message': f'User {action} successfully'
    })


@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def update_job_status(request, job_id):
    """Update job status"""
    job = get_object_or_404(JobPost, id=job_id)
    new_status = request.POST.get('status')
    
    if new_status in ['active', 'inactive', 'expired']:
        old_status = job.status
        job.status = new_status
        job.save()
        
        log_admin_activity(
            request.user,
            'job_action',
            f'Job "{job.title}" status changed from {old_status} to {new_status}',
            'JobPost',
            job.id,
            request
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Job status updated to {new_status}'
        })
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid status'
    })


@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def toggle_job_featured(request, job_id):
    """Toggle job featured status"""
    job = get_object_or_404(JobPost, id=job_id)
    job.is_featured = not job.is_featured
    job.save()
    
    action = "featured" if job.is_featured else "unfeatured"
    log_admin_activity(
        request.user,
        'job_action',
        f'Job "{job.title}" {action}',
        'JobPost',
        job.id,
        request
    )
    
    return JsonResponse({
        'success': True,
        'is_featured': job.is_featured,
        'message': f'Job {action} successfully'
    })


@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def update_report_status(request, report_id):
    """Update report status"""
    report = get_object_or_404(UserReport, id=report_id)
    new_status = request.POST.get('status')
    
    valid_statuses = ['pending', 'investigating', 'resolved', 'dismissed']
    
    if new_status in valid_statuses:
        old_status = report.status
        report.status = new_status
        report.save()
        
        log_admin_activity(
            request.user,
            'report_action',
            f'Report #{report.id} status changed from {old_status} to {new_status}',
            'UserReport',
            report.id,
            request
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Report status updated to {new_status}'
        })
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid status'
    })


@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def assign_report(request, report_id):
    """Assign report to admin"""
    report = get_object_or_404(UserReport, id=report_id)
    report.assigned_admin = request.user
    report.save()
    
    log_admin_activity(
        request.user,
        'report_action',
        f'Report #{report.id} assigned to {request.user.username}',
        'UserReport',
        report.id,
        request
    )
    
    return JsonResponse({
        'success': True,
        'message': f'Report assigned to {request.user.username}'
    })


@login_required
@user_passes_test(is_admin)
def analytics_data_api(request):
    """API endpoint for analytics data"""
    # Get date range from request
    days = int(request.GET.get('days', 30))
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)
    
    # Get statistics for the period
    stats = PlatformStatistics.objects.filter(
        date__range=[start_date, end_date]
    ).order_by('date')
    
    # Prepare response data
    data = {
        'chart_data': {
            'dates': [stat.date.strftime('%Y-%m-%d') for stat in stats],
            'users': [stat.new_users for stat in stats],
            'jobs': [stat.new_jobs for stat in stats],
            'applications': [stat.new_applications for stat in stats],
            'revenue': [float(stat.revenue) for stat in stats],
        },
        'summary': {
            'total_users': sum(stat.new_users for stat in stats),
            'total_jobs': sum(stat.new_jobs for stat in stats),
            'total_applications': sum(stat.new_applications for stat in stats),
            'total_revenue': sum(stat.revenue for stat in stats),
        }
    }
    
    return JsonResponse(data)


@login_required
@user_passes_test(is_admin)
def export_analytics_data(request):
    """Export analytics data to CSV"""
    days = int(request.GET.get('days', 30))
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="analytics_{start_date}_to_{end_date}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Date', 'New Users', 'New Jobs', 'New Applications', 'Revenue'])
    
    stats = PlatformStatistics.objects.filter(
        date__range=[start_date, end_date]
    ).order_by('date')
    
    for stat in stats:
        writer.writerow([
            stat.date.strftime('%Y-%m-%d'),
            stat.new_users,
            stat.new_jobs,
            stat.new_applications,
            float(stat.revenue)
        ])
    
    log_admin_activity(
        request.user,
        'report_generated',
        f'Analytics data exported for {days} days',
        request=request
    )
    
    return response


@login_required
@user_passes_test(is_admin)
def export_data(request):
    """Export platform data to CSV"""
    data_type = request.GET.get('type', 'users')
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{data_type}_{timezone.now().strftime("%Y%m%d")}.csv"'
    
    writer = csv.writer(response)
    
    if data_type == 'users':
        writer.writerow(['ID', 'Username', 'Email', 'First Name', 'Last Name', 'User Type', 'Date Joined', 'Is Active'])
        users = User.objects.select_related('userprofile').all()
        for user in users:
            writer.writerow([
                user.id,
                user.username,
                user.email,
                user.first_name,
                user.last_name,
                getattr(user.userprofile, 'user_type', ''),
                user.date_joined.strftime('%Y-%m-%d'),
                user.is_active
            ])
    
    elif data_type == 'jobs':
        writer.writerow(['ID', 'Title', 'Company', 'Category', 'Location', 'Status', 'Posted Date', 'Salary Min', 'Salary Max'])
        jobs = JobPost.objects.select_related('company', 'category', 'location').all()
        for job in jobs:
            writer.writerow([
                job.id,
                job.title,
                job.company.name if job.company else '',
                job.category.name if job.category else '',
                job.location.name if job.location else '',
                job.status,
                job.published_at.strftime('%Y-%m-%d'),
                job.salary_min or '',
                job.salary_max or ''
            ])
    
    elif data_type == 'applications':
        writer.writerow(['ID', 'Job Title', 'Applicant', 'Company', 'Status', 'Applied Date'])
        applications = Application.objects.select_related('job', 'applicant__user_profile__user', 'job__company').all()
        for app in applications:
            writer.writerow([
                app.id,
                app.job.title,
                app.applicant.user_profile.user.username,
                app.job.company.name if app.job.company else '',
                app.status,
                app.applied_at.strftime('%Y-%m-%d')
            ])
    
    log_admin_activity(
        request.user,
        'report_generated',
        f'Exported {data_type} data to CSV',
        request=request
    )
    
    return response


@login_required
@user_passes_test(is_admin)
def jobseeker_detail(request, user_id):
    """Detailed view of job seeker profile with admin controls"""
    user = get_object_or_404(User, id=user_id)
    
    try:
        user_profile = user.userprofile
        jobseeker_profile = user_profile.jobseekerprofile
    except (UserProfile.DoesNotExist, JobSeekerProfile.DoesNotExist):
        messages.error(request, 'Job seeker profile not found.')
        return redirect('admin_panel:user_management')
    
    # Get job seeker's applications
    applications = Application.objects.filter(
        applicant=jobseeker_profile
    ).select_related('job', 'job__company').order_by('-applied_at')[:10]
    
    # Get job seeker's activity statistics
    stats = {
        'total_applications': Application.objects.filter(applicant=jobseeker_profile).count(),
        'active_applications': Application.objects.filter(
            applicant=jobseeker_profile, 
            status__in=['applied', 'reviewing', 'shortlisted', 'interviewing']
        ).count(),
        'successful_applications': Application.objects.filter(
            applicant=jobseeker_profile, 
            status='hired'
        ).count(),
        'profile_completion': calculate_profile_completion(jobseeker_profile),
    }
    
    context = {
        'user': user,
        'jobseeker_profile': jobseeker_profile,
        'applications': applications,
        'stats': stats,
    }
    
    return render(request, 'admin_panel/jobseeker_detail.html', context)


@login_required
@user_passes_test(is_admin)
def employer_detail(request, user_id):
    """Detailed view of employer profile with admin controls"""
    user = get_object_or_404(User, id=user_id)
    
    try:
        # Get UserProfile first, then EmployerProfile
        user_profile = UserProfile.objects.get(user=user)
        employer_profile = EmployerProfile.objects.get(user_profile=user_profile)
    except (UserProfile.DoesNotExist, EmployerProfile.DoesNotExist):
        messages.error(request, 'Employer profile not found.')
        return redirect('admin_panel:user_management')
    
    # Get employer's company
    company = getattr(employer_profile, 'company', None)
    
    # Get employer's job postings
    jobs = JobPost.objects.filter(
        company=company
    ).order_by('-published_at')[:10] if company else []
    
    # Get applications for employer's jobs
    applications = Application.objects.filter(
        job__company=company
    ).select_related('job', 'applicant__user_profile__user').order_by('-applied_at')[:10] if company else []
    
    # Get employer's activity statistics
    stats = {
        'total_jobs': JobPost.objects.filter(company=company).count() if company else 0,
        'active_jobs': JobPost.objects.filter(company=company, status='active').count() if company else 0,
        'total_applications': Application.objects.filter(job__company=company).count() if company else 0,
        'pending_applications': Application.objects.filter(
            job__company=company, 
            status__in=['applied', 'reviewing']
        ).count() if company else 0,
    }
    
    context = {
        'user': user,
        'employer_profile': employer_profile,
        'company': company,
        'jobs': jobs,
        'applications': applications,
        'stats': stats,
    }
    
    return render(request, 'admin_panel/employer_detail.html', context)


@login_required
@user_passes_test(is_admin)
def impersonate_user(request, user_id):
    """Allow admin to impersonate a user (job seeker or employer)"""
    if not request.user.is_superuser:
        messages.error(request, 'Only superusers can impersonate other users.')
        return redirect('admin_panel:user_management')
    
    target_user = get_object_or_404(User, id=user_id)
    
    # Store original user in session
    request.session['original_user_id'] = request.user.id
    request.session['impersonating'] = True
    
    # Log the impersonation
    log_admin_activity(
        request.user,
        'user_action',
        f'Started impersonating user {target_user.username}',
        'User',
        target_user.id,
        request
    )
    
    # Switch to target user
    from django.contrib.auth import login
    login(request, target_user, backend='django.contrib.auth.backends.ModelBackend')
    
    # Redirect based on user type
    try:
        user_profile = target_user.userprofile
        if user_profile.user_type == 'employer':
            messages.success(request, f'Now impersonating employer: {target_user.username}')
            return redirect('employer:dashboard')
        else:
            messages.success(request, f'Now impersonating job seeker: {target_user.username}')
            return redirect('accounts:dashboard')
    except UserProfile.DoesNotExist:
        messages.warning(request, f'Impersonating user without profile: {target_user.username}')
        return redirect('accounts:dashboard')


@login_required
def stop_impersonation(request):
    """Stop impersonating and return to admin user"""
    if not request.session.get('impersonating'):
        return redirect('admin_panel:dashboard')
    
    original_user_id = request.session.get('original_user_id')
    if original_user_id:
        original_user = get_object_or_404(User, id=original_user_id)
        
        # Log the end of impersonation
        log_admin_activity(
            original_user,
            'user_action',
            f'Stopped impersonating user {request.user.username}',
            'User',
            request.user.id,
            request
        )
        
        # Clear impersonation session data
        del request.session['original_user_id']
        del request.session['impersonating']
        
        # Switch back to original user
        from django.contrib.auth import login
        login(request, original_user, backend='django.contrib.auth.backends.ModelBackend')
        
        messages.success(request, 'Stopped impersonation and returned to admin panel.')
    
    return redirect('admin_panel:dashboard')


@login_required
@user_passes_test(is_admin)
def admin_job_management(request):
    """Enhanced job management with admin controls"""
    # Get all jobs with detailed information
    jobs = JobPost.objects.select_related(
        'company', 'category', 'location'
    ).prefetch_related('application_set').order_by('-published_at')
    
    # Apply filters
    status_filter = request.GET.get('status')
    if status_filter:
        jobs = jobs.filter(status=status_filter)
    
    search = request.GET.get('search')
    if search:
        jobs = jobs.filter(
            Q(title__icontains=search) |
            Q(company__name__icontains=search) |
            Q(description__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(jobs, 20)
    page_number = request.GET.get('page')
    jobs_page = paginator.get_page(page_number)
    
    # Enhanced statistics
    job_stats = {
        'total': JobPost.objects.count(),
        'active': JobPost.objects.filter(status='active').count(),
        'draft': JobPost.objects.filter(status='draft').count(),
        'inactive': JobPost.objects.filter(status='inactive').count(),
        'expired': JobPost.objects.filter(status='expired').count(),
        'total_applications': Application.objects.count(),
        'avg_applications_per_job': Application.objects.count() / max(JobPost.objects.count(), 1),
    }
    
    context = {
        'jobs': jobs_page,
        'job_stats': job_stats,
        'current_filters': {
            'status': status_filter,
            'search': search,
        }
    }
    
    return render(request, 'admin_panel/admin_job_management.html', context)


@login_required
@user_passes_test(is_admin)
def admin_application_management(request):
    """Enhanced application management with admin controls"""
    # Get all applications with detailed information
    applications = Application.objects.select_related(
        'job', 'job__company', 'applicant__user_profile__user'
    ).order_by('-applied_at')
    
    # Apply filters
    status_filter = request.GET.get('status')
    if status_filter:
        applications = applications.filter(status=status_filter)
    
    search = request.GET.get('search')
    if search:
        applications = applications.filter(
            Q(job__title__icontains=search) |
            Q(applicant__user_profile__user__username__icontains=search) |
            Q(job__company__name__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(applications, 20)
    page_number = request.GET.get('page')
    applications_page = paginator.get_page(page_number)
    
    # Enhanced statistics
    application_stats = {
        'total': Application.objects.count(),
        'applied': Application.objects.filter(status='applied').count(),
        'reviewing': Application.objects.filter(status='reviewing').count(),
        'shortlisted': Application.objects.filter(status='shortlisted').count(),
        'interviewing': Application.objects.filter(status='interviewing').count(),
        'hired': Application.objects.filter(status='hired').count(),
        'rejected': Application.objects.filter(status='rejected').count(),
        'success_rate': (Application.objects.filter(status='hired').count() / max(Application.objects.count(), 1)) * 100,
    }
    
    context = {
        'applications': applications_page,
        'application_stats': application_stats,
        'current_filters': {
            'status': status_filter,
            'search': search,
        }
    }
    
    return render(request, 'admin_panel/admin_application_management.html', context)


def calculate_profile_completion(jobseeker_profile):
    """Calculate job seeker profile completion percentage"""
    fields_to_check = [
        'phone', 'location', 'bio', 'skills', 'experience_years',
        'education_level', 'current_salary', 'expected_salary'
    ]
    
    completed_fields = 0
    total_fields = len(fields_to_check)
    
    for field in fields_to_check:
        if hasattr(jobseeker_profile, field):
            value = getattr(jobseeker_profile, field)
            if value:
                completed_fields += 1
    
    return (completed_fields / total_fields) * 100


@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def admin_update_application_status(request, application_id):
    """Admin can update any application status"""
    application = get_object_or_404(Application, id=application_id)
    new_status = request.POST.get('status')
    
    valid_statuses = ['applied', 'reviewing', 'shortlisted', 'interviewing', 'hired', 'rejected']
    
    if new_status in valid_statuses:
        old_status = application.status
        application.status = new_status
        application.save()
        
        log_admin_activity(
            request.user,
            'application_action',
            f'Application #{application.id} status changed from {old_status} to {new_status}',
            'Application',
            application.id,
            request
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Application status updated to {new_status}'
        })
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid status'
    })


@login_required
@user_passes_test(is_admin)
def view_user_password(request, user_id):
    """View user password (for admin purposes only)"""
    user = get_object_or_404(User, id=user_id)
    
    # Log admin activity
    AdminActivity.objects.create(
        admin=request.user,
        action='VIEW_PASSWORD',
        target_model='User',
        target_id=user.id,
        details=f'Viewed password for user: {user.username}'
    )
    
    # Return password hash and user info
    return JsonResponse({
        'success': True,
        'username': user.username,
        'email': user.email,
        'password_hash': user.password,
        'last_login': user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else 'Never',
        'date_joined': user.date_joined.strftime('%Y-%m-%d %H:%M:%S'),
        'is_active': user.is_active,
    })


@login_required
@user_passes_test(is_admin)
def reset_user_password(request, user_id):
    """Reset user password to a temporary password"""
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        
        # Generate temporary password
        import secrets
        import string
        temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
        
        # Set new password
        user.set_password(temp_password)
        user.save()
        
        # Log admin activity
        AdminActivity.objects.create(
            admin=request.user,
            action='RESET_PASSWORD',
            target_model='User',
            target_id=user.id,
            details=f'Reset password for user: {user.username}'
        )
        
        # Send email notification (optional)
        try:
            send_mail(
                'Password Reset - Hireo',
                f'Your password has been reset by an administrator.\n\nNew temporary password: {temp_password}\n\nPlease log in and change your password immediately.',
                django_settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=True,
            )
        except:
            pass
        
        return JsonResponse({
            'success': True,
            'message': f'Password reset successfully for {user.username}',
            'temp_password': temp_password
        })
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method'
    })
