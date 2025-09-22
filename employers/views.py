import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, Http404
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from django.template.loader import render_to_string
from django.urls import reverse
from django.core.exceptions import PermissionDenied
from django.db.models import Q, Count, Avg
from datetime import datetime, timedelta
import json
import os
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from io import BytesIO
from hireo import db_utils as db
from .forms import CompanyForm
from .models import EmployerProfile
from accounts.models import UserProfile
from accounts.decorators import employer_required
from jobs.models import JobPost, JobCategory, JobLocation
from applications.models import Application, Interview, Notification
from applications.notification_utils import NotificationManager
from django.db.models import Count, Q, Sum, Avg

# Configure logger
logger = logging.getLogger('hireo')
from hireo.db_utils import db
from .forms import EmployerProfileForm, CompanyForm
from .pdf_utils import (
    generate_candidate_profile_pdf, 
    generate_applications_report_pdf,
    create_pdf_response
)

@employer_required
def employer_dashboard(request):
    """Employer dashboard view - SQLite3 version"""
    # Get user profile using raw SQL
    user_data = db.get_user_by_id(request.user.id)
    if not user_data or user_data['user_type'] != 'employer':
        messages.error(request, 'Please complete your user profile first.')
        return redirect('accounts:complete_profile')
    
    # Get employer profile using raw SQL
    employer_profile = db.get_employer_profile(request.user.id)
    if not employer_profile:
        messages.info(request, 'Please complete your company profile first.')
        return redirect('employer:setup_company')
    
    # Initialize default values
    total_jobs = 0
    active_jobs = 0
    draft_jobs = 0
    inactive_jobs = 0
    total_applications = 0
    recent_applications = []
    company = None
    
    # Get company information
    if employer_profile['company_name']:
        company_id = employer_profile.get('company_id')
        if company_id:
            company = db.get_company_by_id(company_id)
            
            # Job statistics using raw SQL
            try:
                job_stats_query = """
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN status = 'active' THEN 1 END) as active,
                    COUNT(CASE WHEN status = 'draft' THEN 1 END) as draft,
                    COUNT(CASE WHEN status = 'inactive' THEN 1 END) as inactive
                FROM jobs_jobpost 
                WHERE company_id = ?
                """
                job_stats = db.execute_single(job_stats_query, (company_id,))
                if job_stats:
                    total_jobs = job_stats['total']
                    active_jobs = job_stats['active']
                    draft_jobs = job_stats['draft']
                    inactive_jobs = job_stats['inactive']
            except Exception as e:
                logger.warning(f"Could not fetch job statistics: {e}")
            
            # Application statistics using raw SQL
            try:
                # Use the EmployerProfile ID for employer_id, not the User ID
                employer_profile_id = employer_profile['id']
                app_stats = db.get_application_stats_by_employer(employer_profile_id)
                if app_stats:
                    total_applications = app_stats['total_applications']
                
                # Recent applications
                recent_applications = db.get_applications_by_employer(employer_profile_id, limit=5)
                
                # Convert datetime strings to datetime objects for template filters
                for application in recent_applications:
                    datetime_fields = [
                        'applied_at', 'updated_at', 'reviewed_at', 'shortlisted_at', 
                        'hired_at', 'rejected_at', 'interview_scheduled_at', 'interviewed_at',
                        'created_at', 'modified_at'
                    ]
                    
                    for field in datetime_fields:
                        if application.get(field) and isinstance(application[field], str):
                            try:
                                application[field] = datetime.fromisoformat(application[field].replace('Z', '+00:00'))
                            except (ValueError, AttributeError):
                                pass
            except Exception as e:
                logger.warning(f"Could not fetch application statistics: {e}")
    
    # Enhanced statistics for the dashboard
    pending_applications = 0
    reviewed_applications = 0
    shortlisted_applications = 0
    interviewed_applications = 0
    hired_applications = 0
    rejected_applications = 0
    recent_jobs = []
    
    if company:
        try:
            # Application status breakdown using raw SQL
            # Use the EmployerProfile ID for employer_id, not the User ID
            employer_profile_id = employer_profile['id']
            stats = db.get_application_stats_by_employer(employer_profile_id)
            if stats:
                pending_applications = stats['pending']
                reviewed_applications = stats['reviewing']
                shortlisted_applications = stats['shortlisted']
                interviewed_applications = stats['interviewing']
                hired_applications = stats['hired']
                rejected_applications = stats['rejected']
            
            # Recent jobs using raw SQL
            recent_jobs_query = """
            SELECT j.*, COUNT(a.id) as application_count
            FROM jobs_jobpost j
            LEFT JOIN applications_application a ON j.id = a.job_id
            WHERE j.company_id = ?
            GROUP BY j.id
            ORDER BY j.created_at DESC
            LIMIT 5
            """
            recent_jobs = db.execute_query(recent_jobs_query, (company['id'],))
            
        except Exception as e:
            logger.warning(f"Could not fetch enhanced application statistics: {e}")
    
    # Get jobs with applications for enhanced dashboard using raw SQL
    jobs_with_applications = []
    if company:
        try:
            jobs_query = """
            SELECT j.*, 
                   COUNT(a.id) as application_count,
                   COUNT(CASE WHEN a.status = 'applied' THEN 1 END) as new_applications,
                   COUNT(CASE WHEN a.status = 'shortlisted' THEN 1 END) as shortlisted
            FROM jobs_jobpost j
            LEFT JOIN applications_application a ON j.id = a.job_id
            WHERE j.company_id = ?
            GROUP BY j.id
            ORDER BY j.created_at DESC
            """
            jobs_data = db.execute_query(jobs_query, (company['id'],))
            
            for job_data in jobs_data:
                # Get applications for this job
                applications_query = """
                SELECT a.*, u.first_name, u.last_name, u.email, u.username
                FROM applications_application a
                JOIN accounts_jobseekerprofile js ON a.applicant_id = js.id
                JOIN accounts_userprofile up ON js.user_profile_id = up.id
                JOIN auth_user u ON up.user_id = u.id
                WHERE a.job_id = ?
                ORDER BY a.applied_at DESC
                """
                applications = db.execute_query(applications_query, (job_data['id'],))
                
                # Convert datetime strings to datetime objects for template filters
                for application in applications:
                    datetime_fields = [
                        'applied_at', 'updated_at', 'reviewed_at', 'shortlisted_at', 
                        'hired_at', 'rejected_at', 'interview_scheduled_at', 'interviewed_at',
                        'created_at', 'modified_at'
                    ]
                    
                    for field in datetime_fields:
                        if application.get(field) and isinstance(application[field], str):
                            try:
                                application[field] = datetime.fromisoformat(application[field].replace('Z', '+00:00'))
                            except (ValueError, AttributeError):
                                pass
                
                jobs_with_applications.append({
                    'job': job_data,
                    'applications': applications,
                    'application_count': job_data['application_count'] or 0,
                    'new_applications': job_data['new_applications'] or 0,
                    'shortlisted': job_data['shortlisted'] or 0,
                })
        except Exception as e:
            logger.warning(f"Could not fetch jobs with applications: {e}")
    
    # Get notifications for employer
    notifications = NotificationManager.get_user_notifications(request.user, limit=10)
    unread_notifications = NotificationManager.get_user_notifications(request.user, limit=5, unread_only=True)
    notification_counts = NotificationManager.get_notification_counts(request.user)
    
    context = {
        'employer_profile': employer_profile,
        'company': company,
        'jobs_with_applications': jobs_with_applications,
        'total_jobs': total_jobs,
        'active_jobs': active_jobs,
        'draft_jobs': draft_jobs,
        'inactive_jobs': inactive_jobs,
        'total_applications': total_applications,
        'pending_applications': pending_applications,
        'reviewed_applications': reviewed_applications,
        'shortlisted_applications': shortlisted_applications,
        'interviewed_applications': interviewed_applications,
        'hired_applications': hired_applications,
        'rejected_applications': rejected_applications,
        'total_views': 0,  # Will implement job views tracking later
        'recent_applications': recent_applications,
        'recent_jobs': recent_jobs,
        'upcoming_interviews': [],  # Will implement interview tracking later
        'recent_messages': [],  # Will implement messaging later
        'job_analytics': {},  # Will implement analytics later
        'notifications': notifications,
        'unread_notifications': unread_notifications,
        'notification_counts': notification_counts,
    }
    
    return render(request, 'employers/dashboard.html', context)

@login_required
def setup_company(request):
    """Setup company profile for new employers"""
    try:
        user_profile = request.user.userprofile
        if user_profile.user_type != 'employer':
            messages.error(request, 'Access denied. Employer account required.')
            return redirect('home')
        
        # Check if company already exists
        try:
            employer_profile = EmployerProfile.objects.get(user_profile=user_profile)
            if employer_profile.company:
                messages.info(request, 'Company profile already exists.')
                return redirect('employer:dashboard')
        except EmployerProfile.DoesNotExist:
            # Create employer profile if it doesn't exist
            employer_profile = EmployerProfile.objects.create(user_profile=user_profile)
        
    except UserProfile.DoesNotExist:
        messages.error(request, 'Please complete your user profile first.')
        return redirect('accounts:complete_profile')
    
    if request.method == 'POST':
        company_form = CompanyForm(request.POST, request.FILES)
        employer_form = EmployerProfileForm(request.POST)
        
        if not company_form.is_valid():
            for field, errors in company_form.errors.items():
                for error in errors:
                    messages.error(request, f'Company {field}: {error}')
        
        if not employer_form.is_valid():
            for field, errors in employer_form.errors.items():
                for error in errors:
                    messages.error(request, f'Employer {field}: {error}')
        
        if company_form.is_valid() and employer_form.is_valid():
            try:
                company = company_form.save()
                
                # Create or update employer profile
                employer_profile, created = EmployerProfile.objects.get_or_create(
                    user_profile=user_profile,
                    defaults={
                        'company': company,
                        'position': employer_form.cleaned_data['position'],
                        'department': employer_form.cleaned_data['department'],
                        'is_primary_contact': employer_form.cleaned_data['is_primary_contact'],
                    }
                )
                
                if not created:
                    employer_profile.company = company
                    employer_profile.position = employer_form.cleaned_data['position']
                    employer_profile.department = employer_form.cleaned_data['department']
                    employer_profile.is_primary_contact = employer_form.cleaned_data['is_primary_contact']
                    employer_profile.save()
                
                messages.success(request, 'Company profile created successfully! You can now start posting jobs.')
                return redirect('employer:dashboard')
            except Exception as e:
                print(f"Error saving company profile: {e}")
                messages.error(request, f'Error creating company profile: {str(e)}')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        company_form = CompanyForm()
        employer_form = EmployerProfileForm()
    
    context = {
        'company_form': company_form,
        'employer_form': employer_form,
    }
    
    return render(request, 'employers/setup_company.html', context)

@login_required
def company_profile(request):
    """Company profile view"""
    try:
        user_profile = request.user.userprofile
        if user_profile.user_type != 'employer':
            messages.error(request, 'Access denied. Employer account required.')
            return redirect('home')
        
        employer_profile = EmployerProfile.objects.get(user_profile=user_profile)
        company = employer_profile.company
        
    except (UserProfile.DoesNotExist, EmployerProfile.DoesNotExist):
        messages.error(request, 'Please complete your employer profile first.')
        return redirect('employer:setup_company')
    
    # Get company statistics
    total_jobs = JobPost.objects.filter(company=company).count()
    active_jobs = JobPost.objects.filter(company=company, status='active').count()
    total_applications = Application.objects.filter(employer=employer_profile).count()
    
    context = {
        'employer_profile': employer_profile,
        'company': company,
        'total_jobs': total_jobs,
        'active_jobs': active_jobs,
        'total_applications': total_applications,
    }
    
    return render(request, 'employers/company_profile.html', context)

@login_required
def edit_company(request):
    """Edit company profile"""
    try:
        user_profile = request.user.userprofile
        if user_profile.user_type != 'employer':
            messages.error(request, 'Access denied. Employer account required.')
            return redirect('home')
        
        employer_profile = EmployerProfile.objects.get(user_profile=user_profile)
        company = employer_profile.company
        
    except (UserProfile.DoesNotExist, EmployerProfile.DoesNotExist):
        messages.error(request, 'Please complete your employer profile first.')
        return redirect('employer:setup_company')
    
    if request.method == 'POST':
        company_form = CompanyForm(request.POST, request.FILES, instance=company)
        employer_form = EmployerProfileForm(request.POST, instance=employer_profile)
        
        if company_form.is_valid() and employer_form.is_valid():
            company_form.save()
            employer_form.save()
            messages.success(request, 'Company profile updated successfully!')
            return redirect('employer:company_profile')
    else:
        company_form = CompanyForm(instance=company)
        employer_form = EmployerProfileForm(instance=employer_profile)
    
    context = {
        'company_form': company_form,
        'employer_form': employer_form,
        'company': company,
    }
    
    return render(request, 'employers/edit_company.html', context)

@login_required
def job_list(request):
    """Employer's job list"""
    try:
        user_profile = request.user.userprofile
        if user_profile.user_type != 'employer':
            messages.error(request, 'Access denied. Employer account required.')
            return redirect('home')
        
        employer_profile = EmployerProfile.objects.get(user_profile=user_profile)
        
    except (UserProfile.DoesNotExist, EmployerProfile.DoesNotExist):
        messages.error(request, 'Please complete your employer profile first.')
        return redirect('employer:setup_company')
    
    jobs = JobPost.objects.filter(employer=employer_profile).order_by('-created_at')
    
    # Pagination
    paginator = Paginator(jobs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'employer_profile': employer_profile,
        'jobs': page_obj,
        'page_obj': page_obj,
        'total_jobs': jobs.count(),
    }
    
    return render(request, 'employers/job_management.html', context)

@login_required
def applications_list(request):
    """Employer's applications list - SQLite3 version"""
    # Get user data using raw SQL
    user_data = db.get_user_by_id(request.user.id)
    if not user_data or user_data['user_type'] != 'employer':
        messages.error(request, 'Access denied. Employer account required.')
        return redirect('home')
    
    # Get employer profile using raw SQL
    employer_profile = db.get_employer_profile(request.user.id)
    if not employer_profile:
        messages.error(request, 'Please complete your employer profile first.')
        return redirect('employer:setup_company')
    
    employer_id = employer_profile['id']
    # Also capture company_id to include applications tied to this employer's company
    company_id = employer_profile.get('company_id')
    
    # Build base query for applications with joins
    base_query = """
    SELECT a.*, 
           j.title as job_title, j.id as job_id,
           u.first_name, u.last_name, js.skills, js.experience_years, js.resume,
           u.email, u.username,
           c.name as company_name
    FROM applications_application a
    JOIN jobs_jobpost j ON a.job_id = j.id
    JOIN accounts_jobseekerprofile js ON a.applicant_id = js.id
    JOIN accounts_userprofile up ON js.user_profile_id = up.id
    JOIN auth_user u ON up.user_id = u.id
    LEFT JOIN employers_company c ON j.company_id = c.id
    WHERE a.employer_id = ?
    """
    # If employer has a company, also include applications for jobs under that company
    if company_id:
        base_query = base_query.replace(
            "WHERE a.employer_id = ?",
            "WHERE (a.employer_id = ? OR j.company_id = ?)"
        )
    
    # Get filter parameters
    query = request.GET.get('q', '')
    job_filter = request.GET.get('job', '')
    experience_filter = request.GET.get('experience', '')
    status_filter = request.GET.get('status', '')
    
    # Build WHERE conditions and parameters
    where_conditions = []
    params = [employer_id]
    if company_id:
        params.append(company_id)
    
    if query:
        where_conditions.append("""
        (u.first_name LIKE ? OR u.last_name LIKE ? OR 
         js.skills LIKE ? OR j.title LIKE ?)
        """)
        query_param = f'%{query}%'
        params.extend([query_param, query_param, query_param, query_param])
    
    if job_filter:
        where_conditions.append("j.id = ?")
        params.append(job_filter)
    
    if experience_filter:
        if experience_filter == 'entry':
            where_conditions.append("js.experience_years <= 2")
        elif experience_filter == 'mid':
            where_conditions.append("js.experience_years >= 3 AND js.experience_years <= 7")
        elif experience_filter == 'senior':
            where_conditions.append("js.experience_years >= 8")
    
    if status_filter:
        where_conditions.append("a.status = ?")
        params.append(status_filter)
    
    # Add WHERE conditions to query
    if where_conditions:
        base_query += " AND " + " AND ".join(where_conditions)
    
    # Get total count - use simpler count query to avoid JOIN issues
    count_query = """
    SELECT COUNT(*) as total_count
    FROM applications_application a
    WHERE a.employer_id = ?
    """
    if company_id:
        count_query = count_query.replace(
            "WHERE a.employer_id = ?",
            "JOIN jobs_jobpost j ON a.job_id = j.id\n    WHERE (a.employer_id = ? OR j.company_id = ?)"
        )
    count_params = [employer_id]
    if company_id:
        count_params.append(company_id)
    
    # Add the same WHERE conditions for count
    if where_conditions:
        # For count query, we need to add the JOINs if we're filtering by job seeker data
        if any('u.first_name' in condition or 'u.last_name' in condition or 'js.' in condition for condition in where_conditions):
            count_query = """
            SELECT COUNT(*) as total_count
            FROM applications_application a
            JOIN jobs_jobpost j ON a.job_id = j.id
            JOIN accounts_jobseekerprofile js ON a.applicant_id = js.id
            JOIN accounts_userprofile up ON js.user_profile_id = up.id
            JOIN auth_user u ON up.user_id = u.id
            WHERE a.employer_id = ?
            """
            if company_id:
                count_query = count_query.replace(
                    "WHERE a.employer_id = ?",
                    "WHERE (a.employer_id = ? OR j.company_id = ?)"
                )
        count_query += " AND " + " AND ".join(where_conditions)
        count_params = params
    
    count_result = db.execute_single(count_query, count_params)
    total_applications_count = count_result['total_count'] if count_result else 0
    
    # Add ordering and pagination
    page_number = int(request.GET.get('page', 1))
    per_page = 15
    offset = (page_number - 1) * per_page
    
    applications_query = base_query + " ORDER BY a.applied_at DESC LIMIT ? OFFSET ?"
    applications = db.execute_query(applications_query, params + [per_page, offset])
    
    # Convert datetime strings to datetime objects for template filters
    for application in applications:
        datetime_fields = [
            'applied_at', 'updated_at', 'reviewed_at', 'shortlisted_at', 
            'hired_at', 'rejected_at', 'interview_scheduled_at', 'interviewed_at',
            'created_at', 'modified_at'
        ]
        
        for field in datetime_fields:
            if application.get(field) and isinstance(application[field], str):
                try:
                    application[field] = datetime.fromisoformat(application[field].replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    pass
    
    # Get statistics by status
    stats_query = """
    SELECT 
        COUNT(CASE WHEN a.status = 'applied' THEN 1 END) as pending,
        COUNT(CASE WHEN a.status = 'reviewing' THEN 1 END) as reviewed,
        COUNT(CASE WHEN a.status = 'shortlisted' THEN 1 END) as shortlisted,
        COUNT(CASE WHEN a.status = 'interviewing' THEN 1 END) as interviewed,
        COUNT(CASE WHEN a.status = 'hired' THEN 1 END) as hired,
        COUNT(CASE WHEN a.status = 'rejected' THEN 1 END) as rejected
    FROM applications_application a
    JOIN jobs_jobpost j ON a.job_id = j.id
    WHERE a.employer_id = ?
    """
    if company_id:
        stats_query = stats_query.replace(
            "WHERE a.employer_id = ?",
            "WHERE (a.employer_id = ? OR j.company_id = ?)"
        )
    stats_params = [employer_id]
    if company_id:
        stats_params.append(company_id)
    stats = db.execute_single(stats_query, stats_params)
    
    # Get applications by status for tabs
    status_queries = {
        'pending': "SELECT a.*, j.title as job_title, u.first_name, u.last_name, js.resume FROM applications_application a JOIN jobs_jobpost j ON a.job_id = j.id JOIN accounts_jobseekerprofile js ON a.applicant_id = js.id JOIN accounts_userprofile up ON js.user_profile_id = up.id JOIN auth_user u ON up.user_id = u.id WHERE a.employer_id = ? AND a.status = 'applied' ORDER BY a.applied_at DESC",
        'shortlisted': "SELECT a.*, j.title as job_title, u.first_name, u.last_name, js.resume FROM applications_application a JOIN jobs_jobpost j ON a.job_id = j.id JOIN accounts_jobseekerprofile js ON a.applicant_id = js.id JOIN accounts_userprofile up ON js.user_profile_id = up.id JOIN auth_user u ON up.user_id = u.id WHERE a.employer_id = ? AND a.status = 'shortlisted' ORDER BY a.applied_at DESC",
        'interviewed': "SELECT a.*, j.title as job_title, u.first_name, u.last_name, js.resume FROM applications_application a JOIN jobs_jobpost j ON a.job_id = j.id JOIN accounts_jobseekerprofile js ON a.applicant_id = js.id JOIN accounts_userprofile up ON js.user_profile_id = up.id JOIN auth_user u ON up.user_id = u.id WHERE a.employer_id = ? AND a.status = 'interviewing' ORDER BY a.applied_at DESC",
        'hired': "SELECT a.*, j.title as job_title, u.first_name, u.last_name, js.resume FROM applications_application a JOIN jobs_jobpost j ON a.job_id = j.id JOIN accounts_jobseekerprofile js ON a.applicant_id = js.id JOIN accounts_userprofile up ON js.user_profile_id = up.id JOIN auth_user u ON up.user_id = u.id WHERE a.employer_id = ? AND a.status = 'hired' ORDER BY a.applied_at DESC",
        'rejected': "SELECT a.*, j.title as job_title, u.first_name, u.last_name, js.resume FROM applications_application a JOIN jobs_jobpost j ON a.job_id = j.id JOIN accounts_jobseekerprofile js ON a.applicant_id = js.id JOIN accounts_userprofile up ON js.user_profile_id = up.id JOIN auth_user u ON up.user_id = u.id WHERE a.employer_id = ? AND a.status = 'rejected' ORDER BY a.applied_at DESC"
    }
    if company_id:
        for key in list(status_queries.keys()):
            status_queries[key] = status_queries[key].replace(
                "WHERE a.employer_id = ?",
                "WHERE (a.employer_id = ? OR j.company_id = ?)"
            )
    
    status_applications = {}
    for status, query in status_queries.items():
        status_params = [employer_id]
        if company_id:
            status_params.append(company_id)
        status_apps = db.execute_query(query, status_params)
        
        # Convert datetime strings to datetime objects for template filters
        for application in status_apps:
            datetime_fields = [
                'applied_at', 'updated_at', 'reviewed_at', 'shortlisted_at', 
                'hired_at', 'rejected_at', 'interview_scheduled_at', 'interviewed_at',
                'created_at', 'modified_at'
            ]
            
            for field in datetime_fields:
                if application.get(field) and isinstance(application[field], str):
                    try:
                        application[field] = datetime.fromisoformat(application[field].replace('Z', '+00:00'))
                    except (ValueError, AttributeError):
                        pass
        
        status_applications[f'{status}_applications_list'] = status_apps
    
    # Get jobs for filter dropdown
    jobs_query = """
    SELECT id, title 
    FROM jobs_jobpost 
    WHERE company_id = (SELECT company_id FROM employers_employerprofile WHERE id = ?)
    ORDER BY title
    """
    jobs = db.execute_query(jobs_query, [employer_id])
    
    # Create pagination info
    class PaginationInfo:
        def __init__(self, items, page_num, total_items, per_page):
            self.object_list = items
            self.number = page_num
            self.paginator = type('obj', (object,), {
                'num_pages': (total_items + per_page - 1) // per_page,
                'count': total_items
            })()
            self.has_previous = lambda: page_num > 1
            self.has_next = lambda: page_num < self.paginator.num_pages
            self.previous_page_number = lambda: page_num - 1 if self.has_previous() else None
            self.next_page_number = lambda: page_num + 1 if self.has_next() else None
    
    applications_page = PaginationInfo(applications, page_number, total_applications_count, per_page)
    
    context = {
        'employer_profile': employer_profile,
        'applications': applications,
        'applications_page': applications_page,
        'total_applications': total_applications_count,
        'pending_applications': stats['pending'],
        'reviewed_applications': stats['reviewed'],
        'shortlisted_applications': stats['shortlisted'],
        'interviewed_applications': stats['interviewed'],
        'hired_applications': stats['hired'],
        'rejected_applications': stats['rejected'],
        **status_applications,
        'jobs': jobs,
    }
    
    return render(request, 'employers/applications.html', context)

@login_required
def application_detail(request, application_id):
    """Application detail view"""
    application = get_object_or_404(Application, id=application_id)
    
    try:
        user_profile = request.user.userprofile
        if user_profile.user_type != 'employer':
            messages.error(request, 'Access denied. Employer account required.')
            return redirect('home')
        
        employer_profile = EmployerProfile.objects.get(user_profile=user_profile)
        
        if application.employer != employer_profile:
            messages.error(request, 'Access denied. You can only view your own applications.')
            return redirect('employer:applications_list')
        
    except (UserProfile.DoesNotExist, EmployerProfile.DoesNotExist):
        messages.error(request, 'Please complete your employer profile first.')
        return redirect('employer:setup_company')
    
    # Get application messages
    messages_list = Message.objects.filter(application=application).order_by('sent_at')
    
    # Get interviews
    interviews = Interview.objects.filter(application=application).order_by('scheduled_date')
    
    context = {
        'application': application,
        'employer_profile': employer_profile,
        'messages_list': messages_list,
        'interviews': interviews,
    }
    
    return render(request, 'employers/application_detail.html', context)

@login_required
def update_application_status(request, application_id):
    """Update application status"""
    application = get_object_or_404(Application, id=application_id)
    
    try:
        user_profile = request.user.userprofile
        if user_profile.user_type != 'employer':
            return JsonResponse({'success': False, 'message': 'Access denied'})
        
        employer_profile = EmployerProfile.objects.get(user_profile=user_profile)
        
        if application.employer != employer_profile:
            return JsonResponse({'success': False, 'message': 'Access denied'})
        
    except (UserProfile.DoesNotExist, EmployerProfile.DoesNotExist):
        return JsonResponse({'success': False, 'message': 'Profile not found'})
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        notes = request.POST.get('notes', '')
        instructions = request.POST.get('instructions', '')
        
        if new_status in dict(Application.STATUS_CHOICES):
            # Update application status
            old_status = application.status
            application.status = new_status
            application.employer_notes = notes
            application.reviewed_at = timezone.now()
            
            # Update shortlisted flag and instructions
            if new_status == 'shortlisted':
                application.is_shortlisted = True
                application.shortlist_instructions = instructions
            elif old_status == 'shortlisted' and new_status != 'shortlisted':
                application.is_shortlisted = False
                application.shortlist_instructions = None
                
            application.save()
            
            # Create status history record
            from applications.models import ApplicationStatus, Notification
            ApplicationStatus.objects.create(
                application=application,
                status=new_status,
                notes=notes,
                changed_by=request.user
            )
            
            # Create notification for job seeker when shortlisted
            if new_status == 'shortlisted':
                notification_title = f'Congratulations! You have been shortlisted - {application.job.title}'
                notification_message = f'Your application has been shortlisted for the position of {application.job.title} at {application.job.company.company_name}.'
                
                if instructions:
                    notification_message += f'\n\nNext Steps: {instructions}'
                else:
                    notification_message += ' Please wait for further instructions from the employer.'
                
                Notification.objects.create(
                    user=application.applicant.user_profile.user,
                    notification_type='application_status',
                    title=notification_title,
                    message=notification_message,
                    application=application,
                    job=application.job
                )
                
                # Send email notification if configured
                try:
                    from django.core.mail import send_mail
                    from django.conf import settings
                    
                    send_mail(
                        subject=notification_title,
                        message=notification_message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[application.applicant.user_profile.user.email],
                        fail_silently=True,
                    )
                except Exception as e:
                    print(f"Email notification failed: {e}")
            
            return JsonResponse({
                'success': True, 
                'message': f'Status updated to {application.get_status_display()}',
                'new_status': new_status,
                'status_display': application.get_status_display()
            })
        else:
            return JsonResponse({'success': False, 'message': 'Invalid status'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@login_required
def schedule_interview(request, application_id):
    """Schedule interview for an application"""
    application = get_object_or_404(Application, id=application_id)
    
    try:
        user_profile = request.user.userprofile
        if user_profile.user_type != 'employer':
            messages.error(request, 'Access denied. Employer account required.')
            return redirect('home')
        
        employer_profile = EmployerProfile.objects.get(user_profile=user_profile)
        
        if application.employer != employer_profile:
            messages.error(request, 'Access denied. You can only schedule interviews for your own applications.')
            return redirect('employer:applications_list')
        
    except (UserProfile.DoesNotExist, EmployerProfile.DoesNotExist):
        messages.error(request, 'Please complete your employer profile first.')
        return redirect('employer:setup_company')
    
    if request.method == 'POST':
        # Handle interview scheduling form
        interview_type = request.POST.get('interview_type')
        scheduled_date = request.POST.get('scheduled_date')
        duration = request.POST.get('duration', 60)
        location = request.POST.get('location', '')
        instructions = request.POST.get('instructions', '')
        
        if interview_type and scheduled_date:
            try:
                scheduled_datetime = datetime.strptime(scheduled_date, '%Y-%m-%dT%H:%M')
                interview = Interview.objects.create(
                    application=application,
                    interview_type=interview_type,
                    scheduled_date=scheduled_datetime,
                    duration=duration,
                    location=location,
                    instructions=instructions,
                    interviewer_name=f"{employer_profile.user_profile.user.first_name} {employer_profile.user_profile.user.last_name}",
                    interviewer_email=employer_profile.user_profile.user.email,
                )
                
                messages.success(request, 'Interview scheduled successfully!')
                return redirect('employer:application_detail', application_id=application_id)
                
            except ValueError:
                messages.error(request, 'Invalid date format.')
        else:
            messages.error(request, 'Please fill in all required fields.')
    
    context = {
        'application': application,
        'employer_profile': employer_profile,
    }
    
    return render(request, 'employers/schedule_interview.html', context)

@login_required
def send_message(request, application_id):
    """Send message to applicant"""
    application = get_object_or_404(Application, id=application_id)
    
    try:
        user_profile = request.user.userprofile
        if user_profile.user_type != 'employer':
            return JsonResponse({'success': False, 'message': 'Access denied'})
        
        employer_profile = EmployerProfile.objects.get(user_profile=user_profile)
        
        if application.employer != employer_profile:
            return JsonResponse({'success': False, 'message': 'Access denied'})
        
    except (UserProfile.DoesNotExist, EmployerProfile.DoesNotExist):
        return JsonResponse({'success': False, 'message': 'Profile not found'})
    
    if request.method == 'POST':
        subject = request.POST.get('subject')
        content = request.POST.get('content')
        
        if subject and content:
            message = Message.objects.create(
                application=application,
                sender=request.user,
                recipient=application.applicant.user_profile.user,
                subject=subject,
                content=content,
                message_type='application'
            )
            
            return JsonResponse({'success': True, 'message': 'Message sent successfully'})
        else:
            return JsonResponse({'success': False, 'message': 'Subject and content are required'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

def company_public_profile(request, company_id):
    """Public company profile view"""
    company = get_object_or_404(Company, id=company_id, is_active=True)
    
    # Get company jobs
    jobs = JobPost.objects.filter(company=company, status='active').order_by('-created_at')[:5]
    
    # Get company reviews
    reviews = CompanyReview.objects.filter(company=company).order_by('-created_at')
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
    
    # Get company photos
    photos = CompanyPhoto.objects.filter(company=company).order_by('-is_featured', '-created_at')
    
    # Get company benefits
    benefits = CompanyBenefit.objects.filter(company=company)
    
    context = {
        'company': company,
        'jobs': jobs,
        'reviews': reviews,
        'avg_rating': avg_rating,
        'photos': photos,
        'benefits': benefits,
    }
    
    return render(request, 'employers/company_public_profile.html', context)

@login_required
def company_analytics(request):
    """Company analytics view"""
    try:
        user_profile = request.user.userprofile
        if user_profile.user_type != 'employer':
            messages.error(request, 'Access denied. Employer account required.')
            return redirect('home')
        
        employer_profile = EmployerProfile.objects.get(user_profile=user_profile)
        company = employer_profile.company
        
    except (UserProfile.DoesNotExist, EmployerProfile.DoesNotExist):
        messages.error(request, 'Please complete your employer profile first.')
        return redirect('employer:setup_company')
    
    # Get job analytics
    jobs = JobPost.objects.filter(company=company)
    job_stats = jobs.aggregate(
        total_jobs=Count('id'),
        active_jobs=Count('id', filter=Q(status='active')),
        total_views=Sum('views_count'),
        total_applications=Sum('applications_count')
    )
    
    # Get monthly job postings - SQLite compatible
    from django.db.models import DateTimeField
    from django.db.models.functions import TruncMonth
    
    monthly_jobs = jobs.annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(count=Count('id')).order_by('month')
    
    # Get top performing jobs
    top_jobs = jobs.filter(status='active').order_by('-views_count')[:5]
    
    # Get application analytics
    applications = Application.objects.filter(employer=employer_profile)
    application_stats = applications.aggregate(
        total_applications=Count('id'),
        shortlisted=Count('id', filter=Q(status='shortlisted')),
        hired=Count('id', filter=Q(status='hired'))
    )
    
    context = {
        'employer_profile': employer_profile,
        'company': company,
        'job_stats': job_stats,
        'monthly_jobs': monthly_jobs,
        'top_jobs': top_jobs,
        'application_stats': application_stats,
    }
    
    return render(request, 'employers/company_analytics.html', context)

@login_required
def post_job(request):
    """Post a new job view with comprehensive error handling"""
    from django.db import transaction
    from jobs.forms import JobPostForm
    from jobs.models import JobCategory, JobLocation
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        user_profile = request.user.userprofile
        if user_profile.user_type != 'employer':
            messages.error(request, 'Access denied. Employer account required.')
            return redirect('home')
        
        employer_profile = EmployerProfile.objects.get(user_profile=user_profile)
        
    except UserProfile.DoesNotExist:
        logger.error(f"UserProfile not found for user {request.user.id}")
        messages.error(request, 'User profile not found. Please contact support.')
        return redirect('home')
    except EmployerProfile.DoesNotExist:
        logger.error(f"EmployerProfile not found for user {request.user.id}")
        messages.error(request, 'Employer profile not found. Please complete your employer profile first.')
        return redirect('employer:setup_company')
    
    if not employer_profile.company:
        messages.error(request, 'Company profile required. Please set up your company profile first.')
        return redirect('employer:setup_company')
    
    if request.method == 'POST':
        form = JobPostForm(request.POST)
        
        try:
            if form.is_valid():
                # Use database transaction for data consistency
                with transaction.atomic():
                    job = form.save(commit=False)
                    job.company = employer_profile.company
                    job.employer = employer_profile
                    
                    # Handle job status based on form selection
                    status = form.cleaned_data.get('status', 'draft')
                    if status == 'active':
                        job.status = 'active'
                        job.published_at = timezone.now()
                        success_msg = '✅ Your job has been posted successfully and is now live! Job seekers can now view and apply for this position.'
                    else:
                        job.status = 'draft'
                        success_msg = '📝 Your job has been saved as a draft. You can publish it later from your job management dashboard.'
                    
                    # Save the job
                    job.save()
                    logger.info(f"Job '{job.title}' created successfully by employer {employer_profile.id}")
                    
                    messages.success(request, success_msg)
                    
                    # Redirect based on status
                    if status == 'active':
                        return redirect('employer:dashboard')
                    else:
                        return redirect('employer:job_list')
            else:
                # Form validation failed
                logger.warning(f"Job posting form validation failed for employer {employer_profile.id}: {form.errors}")
                
                # Add specific error messages for better user feedback
                error_count = sum(len(errors) for errors in form.errors.values())
                if form.non_field_errors():
                    error_count += len(form.non_field_errors())
                
                messages.error(request, f'❌ Please fix {error_count} error{"s" if error_count != 1 else ""} in the form below.')
                
        except Exception as e:
            # Database or other unexpected errors
            logger.error(f"Unexpected error during job posting for employer {employer_profile.id}: {str(e)}")
            messages.error(request, '❌ Database error: Unable to save the job. Please try again or contact support if the problem persists.')
            
            # Return form with preserved data
            form = JobPostForm(request.POST)
    else:
        form = JobPostForm()
    
    try:
        # Get categories and locations for the form
        categories = JobCategory.objects.filter(is_active=True).order_by('name')
        locations = JobLocation.objects.filter(is_active=True).order_by('name')
        
        if not categories.exists():
            messages.warning(request, 'No job categories available. Please contact administrator.')
        if not locations.exists():
            messages.warning(request, 'No job locations available. Please contact administrator.')
            
    except Exception as e:
        logger.error(f"Error fetching categories/locations: {str(e)}")
        messages.error(request, 'Error loading form data. Please refresh the page.')
        categories = JobCategory.objects.none()
        locations = JobLocation.objects.none()
    
    context = {
        'form': form,
        'employer_profile': employer_profile,
        'categories': categories,
        'locations': locations,
    }
    return render(request, 'employers/post_job.html', context)

@login_required
def find_candidates(request):
    """Find candidates view"""
    try:
        user_profile = request.user.userprofile
        if user_profile.user_type != 'employer':
            messages.error(request, 'Access denied. Employer account required.')
            return redirect('home')
        
        employer_profile = EmployerProfile.objects.get(user_profile=user_profile)
        
    except (UserProfile.DoesNotExist, EmployerProfile.DoesNotExist):
        messages.error(request, 'Please complete your employer profile first.')
        return redirect('employer:setup_company')
    
    # Get search parameters
    query = request.GET.get('q', '')
    location = request.GET.get('location', '')
    experience = request.GET.get('experience', '')
    
    # Filter candidates based on search parameters
    candidates_queryset = UserProfile.objects.filter(user_type='job_seeker')
    
    if query:
        candidates_queryset = candidates_queryset.filter(
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(current_position__icontains=query) |
            Q(skills__name__icontains=query)
        ).distinct()
    
    if location:
        candidates_queryset = candidates_queryset.filter(location__icontains=location)
    
    if experience:
        candidates_queryset = candidates_queryset.filter(experience_level=experience)
    
    # Get count before pagination
    matching_candidates_count = candidates_queryset.count()
    
    # Pagination
    paginator = Paginator(candidates_queryset, 12)
    page_number = request.GET.get('page')
    candidates = paginator.get_page(page_number)
    
    context = {
        'candidates': candidates,
        'employer_profile': employer_profile,
        'total_candidates': UserProfile.objects.filter(user_type='job_seeker').count(),
        'matching_candidates': matching_candidates_count,
        'active_jobs': JobPost.objects.filter(company=employer_profile.company, status='active').count() if employer_profile.company else 0,
        'total_applications': Application.objects.filter(employer=employer_profile).count(),
    }
    return render(request, 'employers/find_candidates.html', context)

@login_required
def view_candidate(request, candidate_id):
    """View candidate profile"""
    try:
        user_profile = request.user.userprofile
        if user_profile.user_type != 'employer':
            messages.error(request, 'Access denied. Employer account required.')
            return redirect('home')
        
        candidate = get_object_or_404(UserProfile, id=candidate_id, user_type='job_seeker')
        
    except UserProfile.DoesNotExist:
        messages.error(request, 'Candidate not found.')
        return redirect('employer:find_candidates')
    
    context = {
        'candidate': candidate,
    }
    return render(request, 'employers/candidate_detail.html', context)

@login_required
def save_candidate(request, candidate_id):
    """Save candidate to favorites"""
    if request.method == 'POST':
        try:
            candidate = get_object_or_404(UserProfile, id=candidate_id, user_type='job_seeker')
            # Add logic to save candidate to favorites
            return JsonResponse({'success': True, 'message': 'Candidate saved successfully!'})
        except:
            return JsonResponse({'success': False, 'message': 'Error saving candidate'})
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@login_required
def message_candidate(request, candidate_id):
    """Send message to candidate"""
    if request.method == 'POST':
        try:
            candidate = get_object_or_404(UserProfile, id=candidate_id, user_type='job_seeker')
            # Add logic to send message
            return JsonResponse({'success': True, 'message': 'Message sent successfully!'})
        except:
            return JsonResponse({'success': False, 'message': 'Error sending message'})
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@login_required
def employer_settings(request):
    """Employer settings view"""
    try:
        user_profile = request.user.userprofile
        if user_profile.user_type != 'employer':
            messages.error(request, 'Access denied. Employer account required.')
            return redirect('home')
        
        employer_profile = EmployerProfile.objects.get(user_profile=user_profile)
        
    except (UserProfile.DoesNotExist, EmployerProfile.DoesNotExist):
        messages.error(request, 'Please complete your employer profile first.')
        return redirect('employer:setup_company')
    
    context = {
        'employer_profile': employer_profile,
    }
    return render(request, 'employers/settings.html', context)

@login_required
def update_settings(request):
    """Update employer settings"""
    if request.method == 'POST':
        try:
            user_profile = request.user.userprofile
            employer_profile = EmployerProfile.objects.get(user_profile=user_profile)
            
            # Handle settings update logic here
            return JsonResponse({'success': True, 'message': 'Settings updated successfully!'})
        except:
            return JsonResponse({'success': False, 'message': 'Error updating settings'})
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@login_required
def delete_account(request):
    """Delete employer account"""
    if request.method == 'POST':
        try:
            user = request.user
            user.delete()
            return JsonResponse({'success': True, 'message': 'Account deleted successfully!'})
        except:
            return JsonResponse({'success': False, 'message': 'Error deleting account'})
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@login_required
def analytics_data(request):
    """Get analytics data for charts"""
    try:
        user_profile = request.user.userprofile
        if user_profile.user_type != 'employer':
            return JsonResponse({'success': False, 'message': 'Access denied'})
        
        employer_profile = EmployerProfile.objects.get(user_profile=user_profile)
        company = employer_profile.company
        
        if not company:
            return JsonResponse({'success': False, 'message': 'Company not found'})
        
        period = request.GET.get('period', '30')
        
        # Calculate analytics data based on period
        # This is a simplified version - you can enhance it based on your needs
        analytics_data = {
            'total_views': JobPost.objects.filter(company=company).count(),
            'total_applications': Application.objects.filter(job__company=company).count(),
            'shortlisted_applications': Application.objects.filter(job__company=company, status='shortlisted').count(),
            'hired_applications': Application.objects.filter(job__company=company, status='hired').count(),
            'application_rate': 0,
            'avg_response_time': 0,
            'conversion_rate': 0,
            'expiring_soon': 0,
        }
        
        return JsonResponse({'success': True, 'data': analytics_data})
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
def export_analytics(request, format):
    """Export analytics data"""
    try:
        user_profile = request.user.userprofile
        if user_profile.user_type != 'employer':
            return JsonResponse({'success': False, 'message': 'Access denied'})
        
        # Handle export logic here
        return JsonResponse({'success': True, 'message': f'Analytics exported in {format} format'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
def bulk_application_action(request):
    """Handle bulk actions on applications"""
    if request.method == 'POST':
        try:
            data = request.POST
            action = data.get('action')
            application_ids = data.getlist('application_ids')
            
            # Handle bulk action logic here
            return JsonResponse({'success': True, 'message': f'Bulk action {action} completed successfully!'})
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@login_required
def edit_job(request, job_id):
    """Edit existing job"""
    try:
        user_profile = request.user.userprofile
        if user_profile.user_type != 'employer':
            messages.error(request, 'Access denied. Employer account required.')
            return redirect('home')
        
        employer_profile = EmployerProfile.objects.get(user_profile=user_profile)
        job = get_object_or_404(JobPost, id=job_id, company=employer_profile.company)
        
        if request.method == 'POST':
            from jobs.forms import JobPostForm
            form = JobPostForm(request.POST, instance=job)
            
            if form.is_valid():
                job = form.save(commit=False)
                
                # Handle job status based on form action
                action = request.POST.get('action', 'save_draft')
                if action == 'publish':
                    job.status = 'active'
                    if not job.published_at:
                        job.published_at = timezone.now()
                    messages.success(request, 'Job updated and published successfully!')
                elif action == 'unpublish':
                    job.status = 'draft'
                    messages.success(request, 'Job unpublished and saved as draft!')
                else:
                    messages.success(request, 'Job updated successfully!')
                
                job.save()
                return redirect('employer:job_list')
            else:
                messages.error(request, 'Please correct the errors below.')
        else:
            from jobs.forms import JobPostForm
            form = JobPostForm(instance=job)
        
        # Get categories and locations for the form
        from jobs.models import JobCategory, JobLocation
        categories = JobCategory.objects.filter(is_active=True)
        locations = JobLocation.objects.filter(is_active=True)
        
        context = {
            'form': form,
            'job': job,
            'categories': categories,
            'locations': locations,
            'is_editing': True,
        }
        return render(request, 'employers/post_job.html', context)
        
    except JobPost.DoesNotExist:
        messages.error(request, 'Job not found.')
        return redirect('employer:job_list')

@login_required
def delete_job(request, job_id):
    """Delete job"""
    if request.method == 'POST':
        try:
            user_profile = request.user.userprofile
            employer_profile = EmployerProfile.objects.get(user_profile=user_profile)
            job = get_object_or_404(JobPost, id=job_id, company=employer_profile.company)
            job.delete()
            return JsonResponse({'success': True, 'message': 'Job deleted successfully!'})
        except:
            return JsonResponse({'success': False, 'message': 'Error deleting job'})
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@login_required
def duplicate_job(request, job_id):
    """Duplicate existing job"""
    if request.method == 'POST':
        try:
            user_profile = request.user.userprofile
            employer_profile = EmployerProfile.objects.get(user_profile=user_profile)
            job = get_object_or_404(JobPost, id=job_id, company=employer_profile.company)
            
            # Create a copy of the job
            new_job = JobPost.objects.create(
                title=f"{job.title} (Copy)",
                company=job.company,
                description=job.description,
                requirements=job.requirements,
                salary_min=job.min_salary,
                salary_max=job.max_salary,
                location=job.location,
                employment_type=job.employment_type,
                experience_level=job.experience_level,
                status='draft'
            )
            
            return JsonResponse({'success': True, 'message': 'Job duplicated successfully!', 'job_id': new_job.id})
        except:
            return JsonResponse({'success': False, 'message': 'Error duplicating job'})
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@login_required
def skill_assessment(request):
    """Skill assessment tool for evaluating candidates"""
    user_profile = request.user.userprofile
    if user_profile.user_type != 'employer':
        return redirect('accounts:dashboard')
    
    try:
        employer_profile = EmployerProfile.objects.get(user_profile=user_profile)
    except EmployerProfile.DoesNotExist:
        return redirect('employer:setup_company')
    
    context = {
        'employer_profile': employer_profile,
    }
    return render(request, 'employers/skill_assessment.html', context)

@login_required
def career_guidance(request):
    """Career guidance tool for helping candidates"""
    user_profile = request.user.userprofile
    if user_profile.user_type != 'employer':
        return redirect('accounts:dashboard')
    
    try:
        employer_profile = EmployerProfile.objects.get(user_profile=user_profile)
    except EmployerProfile.DoesNotExist:
        return redirect('employer:setup_company')
    
    context = {
        'employer_profile': employer_profile,
    }
    return render(request, 'employers/career_guidance.html', context)

from .smart_matching_views import (
    download_matching_results_pdf,
    smart_matching,
    smart_matching_results,
    smart_matching_candidate_detail,
    smart_matching_preferences,
    smart_matching_analytics,
    run_smart_matching
)

@login_required
def networking(request):
    """Professional networking tools for employers"""
    user_profile = request.user.userprofile
    if user_profile.user_type != 'employer':
        return redirect('accounts:dashboard')
    
    try:
        employer_profile = EmployerProfile.objects.get(user_profile=user_profile)
    except EmployerProfile.DoesNotExist:
        return redirect('employer:setup_company')
    
    context = {
        'employer_profile': employer_profile,
    }
    return render(request, 'employers/networking.html', context)

@login_required
def candidate_detail(request, candidate_id):
    """Detailed view of a specific candidate"""
    user_profile = request.user.userprofile
    if user_profile.user_type != 'employer':
        return redirect('accounts:dashboard')
    
    try:
        employer_profile = EmployerProfile.objects.get(user_profile=user_profile)
    except EmployerProfile.DoesNotExist:
        return redirect('employer:setup_company')
    
    try:
        from accounts.models import JobSeekerProfile
        try:
            candidate = JobSeekerProfile.objects.get(id=candidate_id)
        except JobSeekerProfile.DoesNotExist:
            messages.error(request, f'Candidate with ID {candidate_id} not found.')
            return redirect('employer:applications')
    except ImportError:
        messages.error(request, 'Candidate profile system not available.')
        return redirect('employer:applications')
    
    # Check if candidate has applied to any of this employer's jobs
    application = None
    try:
        from applications.models import Application
        from jobs.models import JobPost
        employer_jobs = JobPost.objects.filter(company=employer_profile.company)
        application = Application.objects.filter(
            job__in=employer_jobs,
            applicant=candidate
        ).first()
    except ImportError:
        pass
    
    # Get candidate notes (if notes system exists)
    candidate_notes = []
    try:
        from .models import CandidateNote
        candidate_notes = CandidateNote.objects.filter(
            candidate=candidate,
            employer=employer_profile
        ).order_by('-created_at')
    except:
        pass
    
    context = {
        'candidate': candidate,
        'application': application,
        'candidate_notes': candidate_notes,
        'employer_profile': employer_profile,
    }
    return render(request, 'employers/candidate_detail.html', context)

@login_required
def update_candidate_status(request, candidate_id):
    """Update application status for a candidate"""
    if request.method != 'POST':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'POST method required'}, status=405)
        return redirect('employer:candidate_detail', candidate_id=candidate_id)
    
    user_profile = request.user.userprofile
    if user_profile.user_type != 'employer':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
        return redirect('accounts:dashboard')
    
    try:
        employer_profile = EmployerProfile.objects.get(user_profile=user_profile)
    except EmployerProfile.DoesNotExist:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Employer profile required'}, status=400)
        return redirect('employer:setup_company')
    
    try:
        from applications.models import Application, ApplicationStatus, Notification
        application_id = request.POST.get('application_id')
        new_status = request.POST.get('status')
        notes = request.POST.get('notes', '')
        
        if not application_id or not new_status:
            error_msg = 'Missing application ID or status'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': error_msg}, status=400)
            messages.error(request, error_msg)
            return redirect('employer:candidate_detail', candidate_id=candidate_id)
        
        # Validate status
        valid_statuses = ['applied', 'under_review', 'shortlisted', 'interview_scheduled', 'hired', 'rejected']
        if new_status not in valid_statuses:
            error_msg = f'Invalid status: {new_status}'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': error_msg}, status=400)
            messages.error(request, error_msg)
            return redirect('employer:candidate_detail', candidate_id=candidate_id)
        
        application = get_object_or_404(Application, id=application_id, employer=employer_profile)
        old_status = application.status
        
        # Update application status
        with transaction.atomic():
            application.status = new_status
            application.save()
            
            # Create status history
            try:
                ApplicationStatus.objects.create(
                    application=application,
                    status=new_status,
                    notes=notes,
                    changed_by=request.user
                )
            except Exception as e:
                logger.warning(f"Could not create status history: {e}")
            
            # Create notification for candidate
            try:
                status_display_names = {
                    'applied': 'Applied',
                    'under_review': 'Under Review',
                    'shortlisted': 'Shortlisted',
                    'interview_scheduled': 'Interview Scheduled',
                    'hired': 'Hired',
                    'rejected': 'Rejected'
                }
                
                Notification.objects.create(
                    user=application.applicant.user_profile.user,
                    notification_type='application_status',
                    title=f'Application Status Updated - {application.job.title}',
                    message=f'Your application status has been updated to: {status_display_names.get(new_status, new_status)}',
                    application=application,
                    job=application.job
                )
            except Exception as e:
                logger.warning(f"Could not create notification: {e}")
        
        status_messages = {
            'applied': 'Application status reset to applied',
            'under_review': 'Application marked as under review',
            'shortlisted': 'Candidate has been shortlisted',
            'interview_scheduled': 'Interview has been scheduled',
            'hired': 'Candidate has been hired',
            'rejected': 'Application has been rejected'
        }
        
        success_msg = status_messages.get(new_status, 'Status updated successfully')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': success_msg,
                'new_status': new_status,
                'status_display': status_display_names.get(new_status, new_status),
                'old_status': old_status
            })
        
        messages.success(request, success_msg)
            
    except ImportError:
        error_msg = 'Application system not available'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': error_msg}, status=500)
        messages.error(request, error_msg)
    except Exception as e:
        error_msg = f'Error updating status: {str(e)}'
        logger.error(f"Status update error: {e}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': error_msg}, status=500)
        messages.error(request, error_msg)
    
    return redirect('employer:candidate_detail', candidate_id=candidate_id)

@login_required
def send_candidate_message(request, candidate_id):
    """Send message to a candidate"""
    if request.method != 'POST':
        return redirect('employer:candidate_detail', candidate_id=candidate_id)
    
    user_profile = request.user.userprofile
    if user_profile.user_type != 'employer':
        return redirect('accounts:dashboard')
    
    try:
        employer_profile = EmployerProfile.objects.get(user_profile=user_profile)
    except EmployerProfile.DoesNotExist:
        return redirect('employer:setup_company')
    
    subject = request.POST.get('subject')
    content = request.POST.get('content')
    
    if subject and content:
        try:
            # Here you would implement actual message sending
            # For now, we'll just show a success message
            messages.success(request, f'Message "{subject}" sent successfully to candidate')
        except Exception as e:
            messages.error(request, f'Error sending message: {str(e)}')
    else:
        messages.error(request, 'Subject and message content are required')
    
    return redirect('employer:candidate_detail', candidate_id=candidate_id)

@login_required
def schedule_candidate_interview(request, candidate_id):
    """Schedule interview with a candidate"""
    if request.method != 'POST':
        return redirect('employer:candidate_detail', candidate_id=candidate_id)
    
    user_profile = request.user.userprofile
    if user_profile.user_type != 'employer':
        return redirect('accounts:dashboard')
    
    try:
        employer_profile = EmployerProfile.objects.get(user_profile=user_profile)
    except EmployerProfile.DoesNotExist:
        return redirect('employer:setup_company')
    
    interview_date = request.POST.get('interview_date')
    interview_type = request.POST.get('interview_type')
    notes = request.POST.get('notes', '')
    
    if interview_date and interview_type:
        try:
            # Here you would create an Interview object
            # For now, we'll just show a success message
            messages.success(request, f'Interview scheduled for {interview_date} ({interview_type})')
        except Exception as e:
            messages.error(request, f'Error scheduling interview: {str(e)}')
    else:
        messages.error(request, 'Interview date and type are required')
    
    return redirect('employer:candidate_detail', candidate_id=candidate_id)

@login_required
def add_candidate_note(request, candidate_id):
    """Add internal note about a candidate"""
    if request.method != 'POST':
        return redirect('employer:candidate_detail', candidate_id=candidate_id)
    
    user_profile = request.user.userprofile
    if user_profile.user_type != 'employer':
        return redirect('accounts:dashboard')
    
    try:
        employer_profile = EmployerProfile.objects.get(user_profile=user_profile)
    except EmployerProfile.DoesNotExist:
        return redirect('employer:setup_company')
    
    note_content = request.POST.get('note')
    
    if note_content:
        try:
            # Here you would create a CandidateNote object
            # For now, we'll just show a success message
            messages.success(request, 'Note added successfully')
        except Exception as e:
            messages.error(request, f'Error adding note: {str(e)}')
    else:
        messages.error(request, 'Note content is required')
    
    return redirect('employer:candidate_detail', candidate_id=candidate_id)

@login_required
@employer_required
def download_resume(request, application_id):
    """Download resume for a specific application"""
    try:
        application = Application.objects.select_related('applicant').get(
            id=application_id,
            job__employer=request.user.userprofile.employerprofile
        )
        
        if application.resume:
            try:
                # Check if file exists before trying to read it
                if application.resume.storage.exists(application.resume.name):
                    # Determine content type based on file extension
                    file_extension = application.resume.name.lower().split('.')[-1]
                    content_type_map = {
                        'pdf': 'application/pdf',
                        'doc': 'application/msword',
                        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                    }
                    content_type = content_type_map.get(file_extension, 'application/octet-stream')
                    
                    response = HttpResponse(application.resume.read(), content_type=content_type)
                    response['Content-Disposition'] = f'attachment; filename="{application.applicant.user_profile.user.get_full_name()}_resume.{file_extension}"'
                    return response
                else:
                    messages.error(request, f'Resume file not found on server. The file "{application.resume.name}" may have been moved or deleted.')
                    return redirect('employer:applications')
            except Exception as e:
                messages.error(request, f'Error accessing resume file: {str(e)}')
                return redirect('employer:applications')
        else:
            messages.error(request, 'No resume attached to this application.')
            return redirect('employer:applications')
            
    except Application.DoesNotExist:
        messages.error(request, 'Application not found.')
        return redirect('employer:applications')


@login_required
@employer_required
def download_candidate_resume(request, candidate_id):
    """Download resume for a specific candidate"""
    try:
        # Get the candidate's user profile
        from accounts.models import UserProfile
        candidate_profile = UserProfile.objects.select_related('user').get(
            id=candidate_id,
            user_type='job_seeker'
        )
        
        # Find the most recent application from this candidate to any of employer's jobs
        from applications.models import Application
        application = Application.objects.select_related('applicant').filter(
            applicant=candidate_profile.user,
            job__employer=request.user.userprofile.employerprofile
        ).first()
        
        if application and application.resume:
            try:
                # Check if file exists before trying to read it
                if application.resume.storage.exists(application.resume.name):
                    # Determine content type based on file extension
                    file_extension = application.resume.name.lower().split('.')[-1]
                    content_type_map = {
                        'pdf': 'application/pdf',
                        'doc': 'application/msword',
                        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                    }
                    content_type = content_type_map.get(file_extension, 'application/octet-stream')
                    
                    response = HttpResponse(application.resume.read(), content_type=content_type)
                    response['Content-Disposition'] = f'attachment; filename="{candidate_profile.user.get_full_name()}_resume.{file_extension}"'
                    return response
                else:
                    messages.error(request, f'Resume file not found on server. The file "{application.resume.name}" may have been moved or deleted.')
                    return redirect('employer:applications')
            except Exception as e:
                messages.error(request, f'Error accessing resume file: {str(e)}')
                return redirect('employer:applications')
        else:
            messages.error(request, 'No resume found for this candidate.')
            return redirect('employer:applications')
            
    except UserProfile.DoesNotExist:
        messages.error(request, 'Candidate not found.')
        return redirect('employer:applications')


@login_required
@employer_required
def send_application_message(request, application_id):
    """Send a message to job seeker for a specific application"""
    if request.method == 'POST':
        try:
            # Get the application
            application = Application.objects.select_related('applicant', 'job').get(
                id=application_id,
                job__employer=request.user.userprofile.employerprofile
            )
            
            content = request.POST.get('content', '').strip()
            if not content:
                return JsonResponse({
                    'success': False,
                    'error': 'Message content is required'
                })
            
            # Create the message
            from applications.models import Message
            message = Message.objects.create(
                application=application,
                sender=request.user,
                recipient=application.applicant.user_profile.user,
                subject=f'Message regarding {application.job.title}',
                content=content,
                message_type='application'
            )
            
            # Create notification for job seeker
            from applications.models import Notification
            Notification.objects.create(
                user=application.applicant.user_profile.user,
                notification_type='message',
                title=f'New message from {request.user.get_full_name()}',
                message=f'You have received a new message regarding your application for {application.job.title}',
                application=application
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Message sent successfully',
                'sender_name': request.user.get_full_name()
            })
            
        except Application.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Application not found'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Failed to send message: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'error': 'Invalid request method'
    })

@login_required
def download_candidate_pdf(request, candidate_id):
    """Download candidate profile as PDF"""
    user_profile = request.user.userprofile
    if user_profile.user_type != 'employer':
        return redirect('accounts:dashboard')
    
    try:
        from accounts.models import JobSeekerProfile
        candidate = get_object_or_404(JobSeekerProfile, id=candidate_id)
        
        # Get job context if provided
        job_id = request.GET.get('job_id')
        job = None
        if job_id:
            job = get_object_or_404(JobPost, id=job_id, employer__user_profile=user_profile)
        
        # Generate PDF
        pdf_content = generate_candidate_profile_pdf(candidate, job)
        
        # Create response
        filename = f"{candidate.user_profile.user.get_full_name().replace(' ', '_')}_Profile.pdf"
        return create_pdf_response(pdf_content, filename)
        
    except Exception as e:
        messages.error(request, f'Error generating PDF: {str(e)}')
        return redirect('employer:candidate_detail', candidate_id=candidate_id)

@login_required
def download_applications_pdf(request):
    """Download applications report as PDF"""
    user_profile = request.user.userprofile
    if user_profile.user_type != 'employer':
        return redirect('accounts:dashboard')
    
    try:
        employer_profile = get_object_or_404(EmployerProfile, user_profile=user_profile)
        
        # Get applications for this employer
        applications = Application.objects.filter(
            job__employer=employer_profile
        ).select_related('job', 'applicant__user_profile__user')
        
        # Filter by job if specified
        job_id = request.GET.get('job_id')
        if job_id:
            applications = applications.filter(job_id=job_id)
        
        # Generate PDF
        pdf_content = generate_applications_report_pdf(applications, employer_profile.company)
        
        # Create response
        filename = f"Applications_Report_{timezone.now().strftime('%Y%m%d')}.pdf"
        return create_pdf_response(pdf_content, filename)
        
    except Exception as e:
        messages.error(request, f'Error generating PDF: {str(e)}')
        return redirect('employer:applications')

def company_list(request):
    """List all companies with search and filtering"""
    companies = Company.objects.annotate(
        job_count=Count('job_posts'),
        avg_rating=Avg('reviews__rating')
    ).order_by('-created_at')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        companies = companies.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(industry__icontains=search_query)
        )
    
    # Industry filter
    industry_filter = request.GET.get('industry', '')
    if industry_filter:
        companies = companies.filter(industry=industry_filter)
    
    # Pagination
    paginator = Paginator(companies, 12)
    page_number = request.GET.get('page')
    companies_page = paginator.get_page(page_number)
    
    # Get unique industries for filter
    industries = Company.objects.filter(is_active=True).values_list('industry', flat=True).distinct()
    
    context = {
        'companies': companies_page,
        'industries': industries,
        'search_query': search_query,
        'industry_filter': industry_filter,
    }
    return render(request, 'employers/company_list.html', context)

@employer_required
def manage_applications(request):
    """Enhanced application management for employers"""
    try:
        user_profile = request.user.userprofile
        employer_profile = EmployerProfile.objects.get(user_profile=user_profile)
        
        if not employer_profile.company:
            messages.error(request, 'Please complete your company profile first.')
            return redirect('employer:setup_company')
        
        # Get all applications for this employer's jobs
        applications = Application.objects.filter(
            job__company=employer_profile.company
        ).select_related(
            'applicant__user_profile__user', 'job', 'job__category'
        ).order_by('-applied_at')
        
        # Filter by status if provided
        status_filter = request.GET.get('status')
        if status_filter:
            applications = applications.filter(status=status_filter)
        
        # Filter by job if provided
        job_filter = request.GET.get('job')
        if job_filter:
            applications = applications.filter(job_id=job_filter)
        
        # Search by applicant name
        search = request.GET.get('search')
        if search:
            applications = applications.filter(
                Q(applicant__user_profile__user__first_name__icontains=search) |
                Q(applicant__user_profile__user__last_name__icontains=search) |
                Q(applicant__user_profile__user__username__icontains=search)
            )
        
        # Pagination
        paginator = Paginator(applications, 20)
        page_number = request.GET.get('page')
        applications_page = paginator.get_page(page_number)
        
        # Get jobs for filter dropdown
        jobs = JobPost.objects.filter(company=employer_profile.company).order_by('-created_at')
        
        # Application status choices for filter
        status_choices = Application.STATUS_CHOICES
        
        context = {
            'applications': applications_page,
            'jobs': jobs,
            'status_choices': status_choices,
            'current_status': status_filter,
            'current_job': job_filter,
            'search_query': search,
            'employer_profile': employer_profile,
        }
        
        return render(request, 'employers/manage_applications.html', context)
        
    except EmployerProfile.DoesNotExist:
        messages.error(request, 'Employer profile not found.')
        return redirect('employer:profile')

@employer_required
def update_application_status(request, application_id):
    """Update application status with notes"""
    if request.method == 'POST':
        try:
            user_profile = request.user.userprofile
            employer_profile = EmployerProfile.objects.get(user_profile=user_profile)
            
            application = get_object_or_404(
                Application, 
                id=application_id, 
                job__company=employer_profile.company
            )
            
            new_status = request.POST.get('status')
            notes = request.POST.get('notes', '')
            
            # Valid status choices for applications
            valid_statuses = ['applied', 'under_review', 'shortlisted', 'interview_scheduled', 'hired', 'rejected']
            
            if new_status in valid_statuses:
                old_status = application.status
                
                with transaction.atomic():
                    application.status = new_status
                    if notes:
                        application.employer_notes = notes
                    application.save()
                    
                    # Create status history if ApplicationStatus model exists
                    try:
                        from applications.models import ApplicationStatus
                        ApplicationStatus.objects.create(
                            application=application,
                            status=new_status,
                            notes=notes,
                            changed_by=request.user
                        )
                    except ImportError:
                        pass  # ApplicationStatus model doesn't exist
                    
                    # Create notification for job seeker
                    try:
                        from applications.models import Notification
                        status_messages = {
                            'applied': 'Your application is being processed',
                            'under_review': 'Your application is now being reviewed',
                            'shortlisted': 'Congratulations! You have been shortlisted',
                            'interview_scheduled': 'You have been selected for an interview',
                            'hired': 'Congratulations! You have been hired',
                            'rejected': 'Thank you for your interest. We have decided to move forward with other candidates'
                        }
                        
                        Notification.objects.create(
                            user=application.applicant.user_profile.user,
                            notification_type='application_status',
                            title=f'Application Status Update - {application.job.title}',
                            message=status_messages.get(new_status, f'Your application status has been updated to {new_status}'),
                            application=application,
                            job=application.job,
                            is_read=False
                        )
                    except ImportError:
                        pass  # Notification model doesn't exist
                
                success_msg = f'Application status updated from "{old_status}" to "{new_status}" successfully!'
                
                # Return JSON response for AJAX requests
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': success_msg,
                        'new_status': new_status,
                        'old_status': old_status
                    })
                
                messages.success(request, success_msg)
            else:
                error_msg = f'Invalid status: {new_status}. Valid statuses are: {", ".join(valid_statuses)}'
                
                # Return JSON response for AJAX requests
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'error': error_msg
                    }, status=400)
                
                messages.error(request, error_msg)
                
        except EmployerProfile.DoesNotExist:
            error_msg = 'Employer profile not found.'
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': error_msg
                }, status=403)
            
            messages.error(request, error_msg)
        except Exception as e:
            error_msg = f'Error updating application status: {str(e)}'
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': error_msg
                }, status=500)
            
            messages.error(request, error_msg)
    
    # For non-AJAX requests, redirect back
    return redirect('employer:applications')

@employer_required
def application_detail(request, application_id):
    """Detailed view of a single application"""
    try:
        user_profile = request.user.userprofile
        employer_profile = EmployerProfile.objects.get(user_profile=user_profile)
        
        application = get_object_or_404(
            Application, 
            id=application_id, 
            job__company=employer_profile.company
        )
        
        # Get application status history
        from applications.models import ApplicationStatus
        status_history = ApplicationStatus.objects.filter(
            application=application
        ).order_by('-changed_at')
        
        # Get related interviews
        from applications.models import Interview
        interviews = Interview.objects.filter(
            application=application
        ).order_by('-scheduled_date')
        
        # Get messages
        from applications.models import Message
        messages_list = Message.objects.filter(
            application=application
        ).order_by('sent_at')
        
        # Process skills for template display
        skills_list = []
        if application.applicant.skills:
            skills_list = [skill.strip() for skill in application.applicant.skills.split(',') if skill.strip()]
        
        context = {
            'application': application,
            'status_history': status_history,
            'interviews': interviews,
            'messages': messages_list,
            'employer_profile': employer_profile,
            'status_choices': Application.STATUS_CHOICES,
            'skills_list': skills_list,
        }
        
        return render(request, 'employers/application_detail.html', context)
        
    except EmployerProfile.DoesNotExist:
        messages.error(request, 'Employer profile not found.')
        return redirect('employer:profile')

@login_required
@employer_required
def redirect_application_detail(request, application_id):
    """Redirect old application detail URLs to new format"""
    return redirect('employer:application_detail', application_id=application_id)

@login_required
def redirect_schedule_interview(request, application_id):
    """Redirect old schedule interview URLs to new format"""
    return redirect('employer:schedule_interview', application_id=application_id)

@login_required
@employer_required
def messages_view(request):
    """Messages view for employers to communicate with candidates"""
    try:
        user_profile = request.user.userprofile
        employer_profile = EmployerProfile.objects.get(user_profile=user_profile)
        
        # Get all messages for this employer's applications
        from applications.models import Message
        messages_list = Message.objects.filter(
            application__job__company=employer_profile.company
        ).select_related(
            'application__applicant',
            'application__job',
            'sender'
        ).order_by('-sent_at')
        
        # Paginate messages
        paginator = Paginator(messages_list, 20)
        page_number = request.GET.get('page')
        messages_page = paginator.get_page(page_number)
        
        # Get conversation threads (group by application)
        conversations = {}
        for message in messages_list:
            app_id = message.application.id
            if app_id not in conversations:
                conversations[app_id] = {
                    'application': message.application,
                    'messages': [],
                    'last_message': message
                }
            conversations[app_id]['messages'].append(message)
        
        context = {
            'messages': messages_page,
            'conversations': conversations,
            'employer_profile': employer_profile,
        }
        
        return render(request, 'employers/messages.html', context)
        
    except EmployerProfile.DoesNotExist:
        messages.error(request, 'Employer profile not found.')
        return redirect('employer:profile')


# Delete functionality for employers
@login_required
@employer_required
def delete_account(request):
    """Delete employer account and all related data"""
    if request.method == 'POST':
        password = request.POST.get('password')
        if request.user.check_password(password):
            with transaction.atomic():
                user = request.user
                
                # Get employer profile
                try:
                    employer_profile = EmployerProfile.objects.get(user_profile=user.userprofile)
                    company = employer_profile.company
                    
                    # Delete all job posts and related data
                    job_posts = JobPost.objects.filter(company=company)
                    for job in job_posts:
                        # Delete applications for this job
                        Application.objects.filter(job=job).delete()
                    job_posts.delete()
                    
                    # Delete company data
                    if company:
                        CompanyReview.objects.filter(company=company).delete()
                        CompanyPhoto.objects.filter(company=company).delete()
                        CompanyBenefit.objects.filter(company=company).delete()
                        company.delete()
                    
                    # Delete employer profile
                    employer_profile.delete()
                    
                except EmployerProfile.DoesNotExist:
                    pass
                
                # Delete user profile and user
                if hasattr(user, 'userprofile'):
                    user.userprofile.delete()
                
                user.delete()
                
                messages.success(request, 'Your employer account has been permanently deleted.')
                return redirect('home')
        else:
            messages.error(request, 'Incorrect password. Account deletion cancelled.')
    
    return render(request, 'employers/delete_account.html')


@login_required
@employer_required
def delete_job(request, job_id):
    """Delete a job posting"""
    try:
        employer_profile = EmployerProfile.objects.get(user_profile=request.user.userprofile)
        job = get_object_or_404(JobPost, id=job_id, company=employer_profile.company)
        
        if request.method == 'POST':
            with transaction.atomic():
                # Delete related applications
                applications = Application.objects.filter(job=job)
                for app in applications:
                    # Delete related messages and interviews
                    from applications.models import Message
                    Message.objects.filter(application=app).delete()
                    Interview.objects.filter(application=app).delete()
                
                applications.delete()
                
                # Delete the job
                job_title = job.title
                job.delete()
                
                messages.success(request, f'Job posting "{job_title}" has been deleted successfully.')
            
            return redirect('employer:dashboard')
        
        # Get application count for confirmation
        application_count = Application.objects.filter(job=job).count()
        
        return render(request, 'employers/delete_job.html', {
            'job': job,
            'application_count': application_count
        })
        
    except EmployerProfile.DoesNotExist:
        messages.error(request, 'Employer profile not found.')
        return redirect('employer:profile')


@login_required
@employer_required
def delete_company(request):
    """Delete company profile"""
    try:
        employer_profile = EmployerProfile.objects.get(user_profile=request.user.userprofile)
        company = employer_profile.company
        
        if not company:
            messages.error(request, 'No company profile found.')
            return redirect('employer:profile')
        
        if request.method == 'POST':
            with transaction.atomic():
                # Check if there are active jobs
                active_jobs = JobPost.objects.filter(company=company, status='active').count()
                if active_jobs > 0:
                    messages.error(request, f'Cannot delete company profile. You have {active_jobs} active job postings. Please delete or deactivate them first.')
                    return redirect('employer:profile')
                
                # Delete all job posts and related data
                job_posts = JobPost.objects.filter(company=company)
                for job in job_posts:
                    Application.objects.filter(job=job).delete()
                job_posts.delete()
                
                # Delete company data
                CompanyReview.objects.filter(company=company).delete()
                CompanyPhoto.objects.filter(company=company).delete()
                CompanyBenefit.objects.filter(company=company).delete()
                
                company_name = company.name
                company.delete()
                
                # Update employer profile
                employer_profile.company = None
                employer_profile.save()
                
                messages.success(request, f'Company profile "{company_name}" has been deleted successfully.')
            
            return redirect('employer:setup_company')
        
        # Get statistics for confirmation
        job_count = JobPost.objects.filter(company=company).count()
        application_count = Application.objects.filter(job__company=company).count()
        
        return render(request, 'employers/delete_company.html', {
            'company': company,
            'job_count': job_count,
            'application_count': application_count
        })
        
    except EmployerProfile.DoesNotExist:
        messages.error(request, 'Employer profile not found.')
        return redirect('employer:profile')

@employer_required
def posted_jobs(request):
    """View all jobs posted by the current employer"""
    # Get user profile using raw SQL
    user_data = db.get_user_by_id(request.user.id)
    if not user_data or user_data['user_type'] != 'employer':
        messages.error(request, 'Access denied.')
        return redirect('accounts:login')
    
    # Get employer profile
    employer_profile = db.get_employer_profile(request.user.id)
    if not employer_profile:
        messages.error(request, 'Please complete your employer profile first.')
        return redirect('employer:setup_company')
    
    employer_id = employer_profile['id']
    company_id = employer_profile.get('company_id')
    
    # Get filters from request
    status_filter = request.GET.get('status', '')
    category_filter = request.GET.get('category', '')
    search_query = request.GET.get('q', '')
    
    # Build base query for jobs posted by this employer
    base_query = """
    SELECT j.*, 
           c.name as company_name,
           cat.name as category_name,
           COALESCE(loc.city || ', ' || loc.state || ', ' || loc.country, 'Location not specified') as location_name,
           COUNT(a.id) as application_count
    FROM jobs_jobpost j
    LEFT JOIN employers_company c ON j.company_id = c.id
    LEFT JOIN jobs_jobcategory cat ON j.category_id = cat.id
    LEFT JOIN jobs_joblocation loc ON j.location_id = loc.id
    LEFT JOIN applications_application a ON j.id = a.job_id
    WHERE (j.employer_id = ? OR j.company_id = ?)
    """
    
    params = [employer_id]
    if company_id:
        params.append(company_id)
    else:
        params.append(employer_id)  # Use employer_id as fallback
    
    # Add filters
    where_conditions = []
    
    if status_filter:
        where_conditions.append("j.status = ?")
        params.append(status_filter)
    
    if category_filter:
        where_conditions.append("j.category_id = ?")
        params.append(category_filter)
    
    if search_query:
        where_conditions.append("(j.title LIKE ? OR j.description LIKE ?)")
        params.extend([f'%{search_query}%', f'%{search_query}%'])
    
    if where_conditions:
        base_query += " AND " + " AND ".join(where_conditions)
    
    # Add GROUP BY and ORDER BY
    jobs_query = base_query + " GROUP BY j.id ORDER BY j.created_at DESC"
    
    # Get total count for pagination
    count_query = """
    SELECT COUNT(DISTINCT j.id) as total_count
    FROM jobs_jobpost j
    LEFT JOIN employers_company c ON j.company_id = c.id
    WHERE (j.employer_id = ? OR j.company_id = ?)
    """
    
    count_params = [employer_id]
    if company_id:
        count_params.append(company_id)
    else:
        count_params.append(employer_id)
    
    if where_conditions:
        # Remove GROUP BY related conditions for count query
        count_where = []
        count_params_filtered = [employer_id]
        if company_id:
            count_params_filtered.append(company_id)
        else:
            count_params_filtered.append(employer_id)
        
        param_index = 2  # Skip first two params
        for condition in where_conditions:
            if 'j.status' in condition or 'j.category_id' in condition or 'j.title' in condition or 'j.description' in condition:
                count_where.append(condition)
                if 'j.title' in condition or 'j.description' in condition:
                    count_params_filtered.extend([f'%{search_query}%', f'%{search_query}%'])
                    param_index += 2
                else:
                    count_params_filtered.append(params[param_index])
                    param_index += 1
        
        if count_where:
            count_query += " AND " + " AND ".join(count_where)
        count_params = count_params_filtered
    
    # Execute count query
    count_result = db.execute_single(count_query, count_params)
    total_jobs_count = count_result['total_count'] if count_result else 0
    
    # Pagination
    page_number = int(request.GET.get('page', 1))
    per_page = 10
    offset = (page_number - 1) * per_page
    
    # Execute main query with pagination
    paginated_query = jobs_query + " LIMIT ? OFFSET ?"
    jobs = db.execute_query(paginated_query, params + [per_page, offset])
    
    # Get job statistics
    stats_query = """
    SELECT 
        COUNT(CASE WHEN j.status = 'active' THEN 1 END) as active_jobs,
        COUNT(CASE WHEN j.status = 'draft' THEN 1 END) as draft_jobs,
        COUNT(CASE WHEN j.status = 'inactive' THEN 1 END) as inactive_jobs,
        COUNT(CASE WHEN j.status = 'closed' THEN 1 END) as closed_jobs,
        COUNT(*) as total_jobs
    FROM jobs_jobpost j
    WHERE (j.employer_id = ? OR j.company_id = ?)
    """
    
    stats_params = [employer_id]
    if company_id:
        stats_params.append(company_id)
    else:
        stats_params.append(employer_id)
    
    stats = db.execute_single(stats_query, stats_params)
    
    # Get categories for filter dropdown
    categories_query = "SELECT * FROM jobs_jobcategory ORDER BY name"
    categories = db.execute_query(categories_query, [])
    
    # Calculate pagination info
    total_pages = (total_jobs_count + per_page - 1) // per_page
    has_previous = page_number > 1
    has_next = page_number < total_pages
    
    context = {
        'jobs': jobs,
        'stats': stats or {},
        'categories': categories,
        'current_filters': {
            'status': status_filter,
            'category': category_filter,
            'search': search_query,
        },
        'pagination': {
            'current_page': page_number,
            'total_pages': total_pages,
            'has_previous': has_previous,
            'has_next': has_next,
            'previous_page': page_number - 1 if has_previous else None,
            'next_page': page_number + 1 if has_next else None,
            'total_count': total_jobs_count,
        },
        'employer_profile': employer_profile,
    }
    
    return render(request, 'employers/posted_jobs.html', context)


@login_required
@employer_required
def get_cover_letter(request, application_id):
    """
    API endpoint to fetch full cover letter content for an application
    """
    try:
        # Get employer profile
        employer_profile = request.user.userprofile.employerprofile
        
        # Get application and verify it belongs to employer's company
        application_data = db.get_application_by_id(application_id)
        
        if not application_data:
            return JsonResponse({
                'success': False,
                'message': 'Application not found'
            })
        
        # Verify the application belongs to this employer's company
        job_data = db.get_job_by_id(application_data['job_id'])
        if not job_data or job_data['company_id'] != employer_profile.company.id:
            return JsonResponse({
                'success': False,
                'message': 'Unauthorized access to this application'
            })
        
        # Get applicant details
        applicant_data = db.get_user_by_id(application_data['applicant_id'])
        
        return JsonResponse({
            'success': True,
            'cover_letter': application_data.get('cover_letter', 'No cover letter provided'),
            'applicant_name': f"{applicant_data.get('first_name', '')} {applicant_data.get('last_name', '')}".strip() or applicant_data.get('username', 'Unknown'),
            'job_title': job_data.get('title', 'Unknown Position'),
            'application_id': application_id
        })
        
    except Exception as e:
        logger.error(f"Error fetching cover letter for application {application_id}: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Error loading cover letter'
        })
