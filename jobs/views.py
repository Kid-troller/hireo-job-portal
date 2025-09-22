from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.utils import timezone
from django.db import transaction
from django.template.loader import render_to_string
from django.urls import reverse
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.views.decorators.http import require_http_methods, require_POST
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from datetime import datetime, timedelta
import json
import os
from hireo import db_utils as db
from .models import JobPost, JobCategory, JobLocation, SavedJob, JobAlert, JobView
from .forms import JobSearchForm, JobApplicationForm
from accounts.models import JobSeekerProfile, UserProfile
from accounts.decorators import jobseeker_required
from employers.models import Company, EmployerProfile
from applications.models import Application
from applications.notification_utils import NotificationManager
from .recommendation_engine import recommendation_engine
from .ai_engine import job_ai_engine
# Optional AI/ML integration with graceful fallbacks
try:
    from .ai_ml_integration import (
        intelligent_search_engine, perform_intelligent_search,
        get_intelligent_recommendations, get_candidate_recommendations,
        analyze_job_fit, initialize_ai_ml_system
    )
    AI_ML_AVAILABLE = True
except ImportError as e:
    AI_ML_AVAILABLE = False
    print(f"AI/ML integration not available: {e}")
    
    # Create fallback functions
    def perform_intelligent_search(*args, **kwargs):
        return {'jobs': [], 'smart_suggestions': {}, 'market_insights': {}, 'personalized_data': {}}
    
    def get_intelligent_recommendations(*args, **kwargs):
        return []
    
    def get_candidate_recommendations(*args, **kwargs):
        return []
    
    def analyze_job_fit(*args, **kwargs):
        return {'error': 'AI/ML features not available'}
    
    def initialize_ai_ml_system():
        return False
    
    class DummySearchEngine:
        def __init__(self):
            self.is_initialized = False
    
    intelligent_search_engine = DummySearchEngine()
from hireo.db_utils import db

def advanced_job_search(request):
    """Advanced job search with sophisticated filtering"""
    form = JobSearchForm(request.GET or None)
    jobs = JobPost.objects.filter(status='active').select_related('company', 'category', 'location')
    
    # Apply filters
    if form.is_valid():
        query = form.cleaned_data.get('query')
        if query:
            jobs = jobs.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query) |
                Q(requirements__icontains=query) |
                Q(company__name__icontains=query)
            )
        
        # Location filter
        location = form.cleaned_data.get('location')
        if location:
            jobs = jobs.filter(
                Q(location__name__icontains=location) |
                Q(location__city__icontains=location) |
                Q(location__state__icontains=location)
            )
        
        # Category filter
        category = form.cleaned_data.get('category')
        if category:
            jobs = jobs.filter(category=category)
        
        # Employment type filter
        employment_type = form.cleaned_data.get('employment_type')
        if employment_type:
            jobs = jobs.filter(employment_type=employment_type)
        
        # Experience level filter
        experience_level = form.cleaned_data.get('experience_level')
        if experience_level:
            jobs = jobs.filter(experience_level=experience_level)
        
        # Salary range filter
        min_salary = form.cleaned_data.get('min_salary')
        max_salary = form.cleaned_data.get('max_salary')
        if min_salary:
            jobs = jobs.filter(min_salary__gte=min_salary)
        if max_salary:
            jobs = jobs.filter(max_salary__lte=max_salary)
        
        # Remote work filter
        remote_work = form.cleaned_data.get('remote_work')
        if remote_work:
            jobs = jobs.filter(remote_work=True)
        
        # Company size filter
        company_size = form.cleaned_data.get('company_size')
        if company_size:
            jobs = jobs.filter(company__company_size=company_size)
        
        # Date posted filter
        date_posted = form.cleaned_data.get('date_posted')
        if date_posted:
            if date_posted == '1':
                jobs = jobs.filter(published_at__gte=timezone.now() - timedelta(days=1))
            elif date_posted == '7':
                jobs = jobs.filter(published_at__gte=timezone.now() - timedelta(days=7))
            elif date_posted == '30':
                jobs = jobs.filter(published_at__gte=timezone.now() - timedelta(days=30))
    
    # Sorting
    sort_by = request.GET.get('sort', 'relevance')
    if sort_by == 'date':
        jobs = jobs.order_by('-published_at')
    elif sort_by == 'salary':
        jobs = jobs.order_by('-salary_max')
    elif sort_by == 'company':
        jobs = jobs.order_by('company__name')
    else:  # relevance (default)
        jobs = jobs.order_by('-published_at', '-views_count')
    
    # Pagination
    paginator = Paginator(jobs, 20)
    page_number = request.GET.get('page')
    jobs_page = paginator.get_page(page_number)
    
    # Get filter counts for sidebar
    filter_counts = {
        'categories': JobCategory.objects.annotate(job_count=Count('jobs')).filter(job_count__gt=0),
        'locations': JobLocation.objects.annotate(job_count=Count('jobs')).filter(job_count__gt=0),
        'employment_types': jobs.values('employment_type').annotate(count=Count('id')),
        'experience_levels': jobs.values('experience_level').annotate(count=Count('id')),
    }
    
    context = {
        'form': form,
        'jobs': jobs_page,
        'filter_counts': filter_counts,
        'total_jobs': jobs.count(),
        'current_sort': sort_by,
        'search_performed': bool(request.GET)
    }
    
    return render(request, 'jobs/advanced_search.html', context)


def get_recommended_jobs(user, limit=4):
    """Get job recommendations using the advanced recommendation engine"""
    try:
        return recommendation_engine.get_user_recommendations(user, limit)
    except Exception as e:
        print(f"Recommendation error: {e}")
        # Fallback to trending jobs
        return JobPost.objects.filter(status='active').order_by('-published_at')[:limit]


def job_list(request):
    """Enhanced job listing page with AI features when available"""
    
    # Get search form
    search_form = JobSearchForm(request.GET)
    
    # Initialize AI features
    ai_suggestions = []
    market_trends = {}
    personalized_filters = {}
    job_match_scores = {}
    
    # Try to use AI/ML features if available
    if AI_ML_AVAILABLE:
        try:
            # Initialize AI/ML system if not already done
            if not intelligent_search_engine.is_initialized:
                initialize_ai_ml_system()
            
            # Get search parameters
            query = request.GET.get('q', '')
            filters = {
                'category': request.GET.get('category'),
                'location': request.GET.get('location'),
                'employment_type': request.GET.get('employment_type'),
                'experience_level': request.GET.get('experience_level'),
                'salary_min': request.GET.get('salary_min'),
                'salary_max': request.GET.get('salary_max'),
                'is_remote': request.GET.get('is_remote'),
                'date_posted': request.GET.get('date_posted'),
            }
            
            # Remove empty filters
            filters = {k: v for k, v in filters.items() if v}
            
            # Perform intelligent search
            user_id = request.user.id if request.user.is_authenticated else None
            search_results = perform_intelligent_search(
                query=query,
                user_id=user_id,
                filters=filters,
                page_size=20,
                use_semantic=True,
                use_ml_ranking=True
            )
            
            # Extract AI results
            ai_jobs = search_results.get('jobs', [])
            if ai_jobs:
                jobs = ai_jobs
            ai_suggestions = search_results.get('smart_suggestions', {})
            market_trends = search_results.get('market_insights', {})
            personalized_filters = search_results.get('personalized_data', {})
            
            # Extract match scores from jobs
            for job in jobs if 'jobs' in locals() else []:
                if hasattr(job, 'ai_match_score'):
                    job_match_scores[job.id] = job.ai_match_score
        except Exception as e:
            print(f"AI/ML features failed, falling back to standard search: {e}")
    
    # Standard job search (fallback or primary)
    if 'jobs' not in locals():
        jobs = JobPost.objects.filter(status='active').order_by('-published_at')
        
        # Apply basic filters
        if search_form.is_valid():
            query = search_form.cleaned_data.get('query')
            location = search_form.cleaned_data.get('location')
            category = search_form.cleaned_data.get('category')
            employment_type = search_form.cleaned_data.get('employment_type')
            experience_level = search_form.cleaned_data.get('experience_level')
            min_salary = search_form.cleaned_data.get('min_salary')
            max_salary = search_form.cleaned_data.get('max_salary')
            is_remote = search_form.cleaned_data.get('is_remote')
            sort_by = search_form.cleaned_data.get('sort_by')
        
            # Advanced filters
            required_skills = search_form.cleaned_data.get('required_skills')
            education_required = search_form.cleaned_data.get('education_required')
            date_posted = search_form.cleaned_data.get('date_posted')
            company_size = search_form.cleaned_data.get('company_size')
            remote_percentage = search_form.cleaned_data.get('remote_percentage')
            is_featured = search_form.cleaned_data.get('is_featured')
        
            if query:
                jobs = jobs.filter(
                    Q(title__icontains=query) |
                    Q(description__icontains=query) |
                    Q(company__name__icontains=query) |
                    Q(required_skills__icontains=query)
                )
            
            if location:
                jobs = jobs.filter(
                    Q(location__city__icontains=location) |
                    Q(location__state__icontains=location) |
                    Q(location__country__icontains=location)
                )
            
            if category:
                jobs = jobs.filter(category=category)
            
            if employment_type:
                jobs = jobs.filter(employment_type=employment_type)
            
            if experience_level:
                jobs = jobs.filter(experience_level=experience_level)
            
            if min_salary:
                jobs = jobs.filter(max_salary__gte=min_salary)
            
            if max_salary:
                jobs = jobs.filter(min_salary__lte=max_salary)
            
            if is_remote:
                jobs = jobs.filter(is_remote=True)
                
            # Apply advanced filters
            if required_skills:
                # Split the comma-separated skills and search for each one
                skills_list = [skill.strip() for skill in required_skills.split(',')]
                for skill in skills_list:
                    jobs = jobs.filter(required_skills__icontains=skill)
            
            if education_required:
                jobs = jobs.filter(education_required__icontains=education_required)
            
            if date_posted:
                days = int(date_posted)
                date_threshold = timezone.now() - timedelta(days=days)
                jobs = jobs.filter(created_at__gte=date_threshold)
        
            if company_size:
                if company_size == 'small':
                    jobs = jobs.filter(company__employee_count__lte=50)
                elif company_size == 'medium':
                    jobs = jobs.filter(company__employee_count__gt=50, company__employee_count__lte=200)
                elif company_size == 'large':
                    jobs = jobs.filter(company__employee_count__gt=200, company__employee_count__lte=1000)
                elif company_size == 'enterprise':
                    jobs = jobs.filter(company__employee_count__gt=1000)
        
            if remote_percentage:
                if remote_percentage == '0':
                    jobs = jobs.filter(remote_percentage=0)
                elif remote_percentage == '1-25':
                    jobs = jobs.filter(remote_percentage__gt=0, remote_percentage__lte=25)
                elif remote_percentage == '26-50':
                    jobs = jobs.filter(remote_percentage__gt=25, remote_percentage__lte=50)
                elif remote_percentage == '51-75':
                    jobs = jobs.filter(remote_percentage__gt=50, remote_percentage__lte=75)
                elif remote_percentage == '76-99':
                    jobs = jobs.filter(remote_percentage__gt=75, remote_percentage__lt=100)
                elif remote_percentage == '100':
                    jobs = jobs.filter(remote_percentage=100)
            
            if is_featured:
                jobs = jobs.filter(is_featured=True)
            
            # Apply sorting
            if sort_by == 'date_posted':
                jobs = jobs.order_by('-created_at')
            elif sort_by == 'salary_high':
                jobs = jobs.order_by('-max_salary')
            elif sort_by == 'salary_low':
                jobs = jobs.order_by('min_salary')
            elif sort_by == 'experience_level':
                jobs = jobs.order_by('min_experience')
            elif sort_by == 'company_rating':
                jobs = jobs.order_by('-company__rating')
    
    # Pagination
    paginator = Paginator(jobs, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get categories for sidebar
    categories = JobCategory.objects.filter(is_active=True)
    
    # Get locations for sidebar
    locations = JobLocation.objects.filter(is_active=True)
    
    # Get recommended jobs if user is authenticated
    recommended_jobs = []
    if request.user.is_authenticated:
        recommended_jobs = get_recommended_jobs(request.user, limit=4)
        
        # Calculate AI match scores for displayed jobs
        try:
            user_profile = request.user.userprofile
            for job in page_obj:
                match_score = job_ai_engine.get_job_match_score(job, user_profile)
                job_match_scores[job.id] = match_score
        except Exception as e:
            print(f"Error calculating match scores: {e}")
    
    # Get salary insights for current filters
    salary_insights = None
    try:
        category_filter = search_form.cleaned_data.get('category') if search_form.is_valid() else None
        location_filter = search_form.cleaned_data.get('location') if search_form.is_valid() else None
        salary_insights = job_ai_engine.get_salary_insights(category_filter, location_filter)
    except Exception as e:
        print(f"Error getting salary insights: {e}")
    
    # Handle total_jobs count for both QuerySet and list
    try:
        total_jobs = jobs.count() if hasattr(jobs, 'count') else len(jobs)
    except:
        total_jobs = len(jobs) if jobs else 0
    
    context = {
        'jobs': page_obj,
        'page_obj': page_obj,
        'search_form': search_form,
        'categories': categories,
        'locations': locations,
        'total_jobs': total_jobs,
        'recommended_jobs': recommended_jobs,
        'ai_suggestions': ai_suggestions,
        'market_trends': market_trends,
        'personalized_filters': personalized_filters,
        'job_match_scores': job_match_scores,
        'salary_insights': salary_insights,
    }
    
    return render(request, 'jobs/job_list.html', context)

@require_http_methods(["GET"])
def ai_search_suggestions(request):
    """API endpoint for AI-powered search suggestions"""
    query = request.GET.get('q', '')
    limit = int(request.GET.get('limit', 5))
    
    try:
        suggestions = job_ai_engine.get_smart_search_suggestions(query, limit)
        return JsonResponse({
            'success': True,
            'suggestions': suggestions
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@require_http_methods(["GET"])
def market_trends_api(request):
    """API endpoint for job market trends"""
    try:
        trends = job_ai_engine.analyze_job_market_trends()
        return JsonResponse({
            'success': True,
            'trends': trends
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@require_http_methods(["GET"])
@login_required
def personalized_suggestions(request):
    """API endpoint for personalized job suggestions"""
    try:
        suggestions = job_ai_engine.get_personalized_filters(request.user)
        return JsonResponse({
            'success': True,
            'suggestions': suggestions
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@require_http_methods(["GET"])
def salary_insights_api(request):
    """API endpoint for salary insights"""
    category = request.GET.get('category')
    location = request.GET.get('location')
    
    try:
        insights = job_ai_engine.get_salary_insights(category, location)
        if insights:
            return JsonResponse({
                'success': True,
                'insights': insights
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'No salary data available for the specified criteria'
            })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@require_http_methods(["GET"])
@login_required
def intelligent_job_recommendations(request):
    """Get AI/ML powered job recommendations"""
    try:
        user_id = request.user.id
        limit = int(request.GET.get('limit', 10))
        
        recommendations = get_intelligent_recommendations(user_id, limit)
        
        # Format recommendations for JSON response
        formatted_recs = []
        for rec in recommendations:
            job = rec['job']
            formatted_recs.append({
                'id': job.id,
                'title': job.title,
                'company': job.company.name if job.company else 'Unknown',
                'location': f"{job.location.city}, {job.location.state}" if job.location else 'Remote',
                'salary': job.get_formatted_salary(),
                'ml_score': round(rec['ml_score'] * 100, 1),
                'match_score': round(rec['match_score'] * 100, 1),
                'combined_score': round(rec['combined_score'] * 100, 1),
                'url': f'/jobs/{job.id}/',
                'is_remote': job.is_remote,
                'employment_type': job.get_employment_type_display(),
                'created_at': job.created_at.strftime('%Y-%m-%d')
            })
        
        return JsonResponse({
            'success': True,
            'recommendations': formatted_recs,
            'total': len(formatted_recs)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@require_http_methods(["GET"])
@login_required
def job_fit_analysis(request, job_id):
    """Analyze job fit for current user"""
    try:
        user_id = request.user.id
        analysis = analyze_job_fit(user_id, job_id)
        
        if 'error' in analysis:
            return JsonResponse({
                'success': False,
                'error': analysis['error']
            })
        
        return JsonResponse({
            'success': True,
            'analysis': {
                'overall_score': round(analysis['overall_score'] * 100, 1),
                'skill_match': round(analysis['skill_match'] * 100, 1),
                'experience_match': round(analysis['experience_match'] * 100, 1),
                'salary_match': round(analysis['salary_match'] * 100, 1),
                'location_match': round(analysis['location_match'] * 100, 1),
                'recommendations': analysis['recommendations'],
                'missing_skills': analysis['missing_skills'],
                'strengths': analysis['strengths']
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@require_http_methods(["GET"])
def semantic_job_search(request):
    """Perform semantic search on jobs"""
    try:
        query = request.GET.get('q', '')
        limit = int(request.GET.get('limit', 20))
        
        if not query:
            return JsonResponse({
                'success': False,
                'error': 'Query parameter is required'
            })
        
        # Perform semantic search
        from .semantic_search import perform_semantic_search
        job_ids = perform_semantic_search(query, limit)
        
        # Get job details
        jobs = JobPost.objects.filter(id__in=job_ids).select_related(
            'company', 'category', 'location'
        )
        
        # Format results
        results = []
        for job in jobs:
            results.append({
                'id': job.id,
                'title': job.title,
                'company': job.company.name if job.company else 'Unknown',
                'location': f"{job.location.city}, {job.location.state}" if job.location else 'Remote',
                'salary': job.get_formatted_salary(),
                'url': f'/jobs/{job.id}/',
                'is_remote': job.is_remote,
                'employment_type': job.get_employment_type_display(),
                'created_at': job.created_at.strftime('%Y-%m-%d'),
                'snippet': job.description[:200] + '...' if job.description else ''
            })
        
        return JsonResponse({
            'success': True,
            'results': results,
            'total': len(results),
            'query': query
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@require_http_methods(["GET"])
def candidate_recommendations_api(request, job_id):
    """Get AI-powered candidate recommendations for employers"""
    try:
        # Check if user is employer for this job
        job = get_object_or_404(JobPost, id=job_id)
        
        # Basic permission check
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': 'Authentication required'
            })
        
        limit = int(request.GET.get('limit', 20))
        candidates = get_candidate_recommendations(job_id, limit)
        
        # Format candidates for response
        formatted_candidates = []
        for candidate_data in candidates:
            candidate = candidate_data['candidate']
            formatted_candidates.append({
                'id': candidate.id,
                'name': candidate.user_profile.user.get_full_name(),
                'email': candidate.user_profile.user.email,
                'experience_years': candidate.experience_years,
                'skills': candidate.skills,
                'education_level': candidate.get_education_level_display(),
                'expected_salary': candidate.expected_salary,
                'final_score': round(candidate_data['final_score'] * 100, 1),
                'ml_score': round(candidate_data['ml_score'] * 100, 1),
                'similarity_score': round(candidate_data['similarity_score'] * 100, 1),
                'source': candidate_data['source'],
                'profile_url': f'/candidates/{candidate.id}/',
                'is_available': candidate.is_available_for_work
            })
        
        return JsonResponse({
            'success': True,
            'candidates': formatted_candidates,
            'total': len(formatted_candidates),
            'job_title': job.title
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

def job_detail(request, job_id):
    """Job detail page"""
    job = get_object_or_404(JobPost, id=job_id)
    
    # Increment view count
    job.increment_views()
    
    # Track job view - temporarily disabled due to database schema mismatch
    # if request.user.is_authenticated:
    #     JobView.objects.create(
    #         job=job,
    #         user=request.user
    #     )
    
    # Check if user has already applied
    has_applied = False
    is_saved = False
    
    if request.user.is_authenticated:
        try:
            user_profile = request.user.userprofile
            if user_profile.user_type == 'jobseeker':
                job_seeker_profile = JobSeekerProfile.objects.get(user_profile=user_profile)
                has_applied = Application.objects.filter(
                    job=job,
                    applicant=job_seeker_profile
                ).exists()
                
                is_saved = SavedJob.objects.filter(
                    job=job,
                    user=job_seeker_profile
                ).exists()
        except (UserProfile.DoesNotExist, JobSeekerProfile.DoesNotExist):
            pass
    
    # Get related jobs
    related_jobs = JobPost.objects.filter(
        Q(category=job.category) |
        Q(location=job.location) |
        Q(employment_type=job.employment_type)
    ).exclude(id=job.id).filter(status='active')[:4]
    
    # Get company reviews
    company_reviews = job.company.reviews.all()[:3]
    
    context = {
        'job': job,
        'has_applied': has_applied,
        'is_saved': is_saved,
        'related_jobs': related_jobs,
        'company_reviews': company_reviews,
    }
    
    return render(request, 'jobs/job_detail.html', context)

@login_required
def apply_job(request, job_id):
    """Enhanced job application with comprehensive validation and notifications - SQLite3 version"""
    # Get job using raw SQL
    job_query = """
    SELECT j.*, c.name as company_name, e.id as employer_id
    FROM jobs_jobpost j
    JOIN employers_company c ON j.company_id = c.id
    JOIN employers_employerprofile e ON j.employer_id = e.id
    WHERE j.id = ? AND j.status = 'active'
    """
    job = db.execute_single(job_query, [job_id])
    if not job:
        messages.error(request, 'Job not found or no longer available.')
        return redirect('jobs:job_list')
    
    # Check if user is logged in and is a job seeker
    if not request.user.is_authenticated:
        messages.error(request, 'Please log in to apply for jobs.')
        return redirect('accounts:login')
    
    # Get user profile using raw SQL
    user_data = db.get_user_by_id(request.user.id)
    if not user_data or user_data['user_type'] != 'jobseeker':
        messages.error(request, 'Only job seekers can apply for jobs.')
        return redirect('jobs:job_detail', job_id=job_id)
    
    # Get job seeker profile using raw SQL
    job_seeker = db.get_jobseeker_profile(request.user.id)
    if not job_seeker:
        messages.error(request, 'Please complete your job seeker profile first.')
        return redirect('accounts:complete_profile')
    
    # Check if already applied using raw SQL
    existing_app_query = """
    SELECT id, applied_at FROM applications_application 
    WHERE job_id = ? AND applicant_id = ?
    """
    existing_application = db.execute_single(existing_app_query, [job_id, job_seeker['id']])
    if existing_application:
        applied_date = datetime.fromisoformat(existing_application['applied_at'].replace('Z', '+00:00'))
        messages.warning(request, f'You have already applied for this job on {applied_date.strftime("%B %d, %Y")}.')
        return redirect('jobs:job_detail', job_id=job_id)
    
    # Check if application deadline has passed
    if job['application_deadline'] and job['application_deadline'] < timezone.now().date().isoformat():
        messages.error(request, 'The application deadline for this job has passed.')
        return redirect('jobs:job_detail', job_id=job_id)
    
    # Allow job application regardless of profile completion status
    # Job seekers can apply with basic information and complete profile later
    
    if request.method == 'POST':
        form = JobApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # Create application using atomic transaction to prevent database locking
                current_time = timezone.now().isoformat()
                
                # Prepare all operations for a single transaction
                operations = []
                
                # 1. Insert application
                application_insert = ("""
                INSERT INTO applications_application 
                (job_id, applicant_id, employer_id, cover_letter, resume, additional_files, status, 
                 is_shortlisted, is_rejected, applied_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    job_id,
                    job_seeker['id'], 
                    job['employer_id'],
                    form.cleaned_data['cover_letter'],
                    form.cleaned_data['resume'].name if form.cleaned_data.get('resume') else None,
                    form.cleaned_data.get('additional_files').name if form.cleaned_data.get('additional_files') else None,
                    'applied',
                    False,  # is_shortlisted
                    False,  # is_rejected
                    current_time,
                    current_time
                ))
                operations.append(application_insert)
                
                # 2. Update job applications count
                count_update = ("""
                UPDATE jobs_jobpost 
                SET applications_count = applications_count + 1 
                WHERE id = ?
                """, (job_id,))
                operations.append(count_update)
                
                # Execute all operations in a single transaction
                success = db.execute_transaction(operations)
                
                if not success:
                    raise Exception("Failed to create application in database transaction")
                
                # Get the application ID from the last insert
                application_id_query = """
                SELECT id FROM applications_application 
                WHERE job_id = ? AND applicant_id = ? AND applied_at = ?
                ORDER BY id DESC LIMIT 1
                """
                application_result = db.execute_single(application_id_query, [job_id, job_seeker['id'], current_time])
                
                if not application_result:
                    raise Exception("Failed to retrieve created application ID")
                
                application_id = application_result['id']
                
                # Create related records in separate transactions to avoid long locks
                try:
                    # Create initial status record
                    status_data = {
                        'application_id': application_id,
                        'status': 'applied',
                        'notes': 'Application submitted by job seeker',
                        'changed_by_id': request.user.id,
                        'changed_at': current_time
                    }
                    db.create_application_status(status_data)
                except Exception as e:
                    # Log but don't fail the application
                    print(f"Warning: Failed to create application status: {e}")
                
                try:
                    # Create analytics record
                    analytics_data = {
                        'application_id': application_id,
                        'created_at': current_time
                    }
                    db.create_application_analytics(analytics_data)
                except Exception as e:
                    # Log but don't fail the application
                    print(f"Warning: Failed to create application analytics: {e}")
                
                # Get employer user ID for notification
                employer_user_query = """
                SELECT up.user_id 
                FROM employers_employerprofile ep
                JOIN accounts_userprofile up ON ep.user_profile_id = up.id
                WHERE ep.id = ?
                """
                employer_user = db.execute_single(employer_user_query, [job['employer_id']])
                
                if employer_user:
                    # Create notification for employer using NotificationManager
                    try:
                        from django.contrib.auth.models import User
                        employer_user_obj = User.objects.get(id=employer_user['user_id'])
                        application_obj = Application.objects.get(id=application_id)
                        NotificationManager.create_new_application_notification(application_obj)
                    except Exception as e:
                        # Fallback to raw SQL notification
                        notification_data = {
                            'user_id': employer_user['user_id'],
                            'notification_type': 'application_status',
                            'title': f'New Application for {job["title"]}',
                            'message': f'{user_data["first_name"]} {user_data["last_name"] or user_data["username"]} has applied for {job["title"]}',
                            'application_id': application_id,
                            'job_id': job_id,
                            'created_at': timezone.now().isoformat(),
                            'is_read': False
                        }
                        db.create_notification(notification_data)
                    
                    # Send real-time notification via WebSocket
                    try:
                        channel_layer = get_channel_layer()
                        async_to_sync(channel_layer.group_send)(
                            f'notifications_{employer_user["user_id"]}',
                            {
                                'type': 'notification_message',
                                'message': {
                                    'type': 'new_notification',
                                    'notification': {
                                        'id': application_id,
                                        'type': 'application_received',
                                        'title': 'New Job Application Received',
                                        'content': f'New application for "{job["title"]}"',
                                        'is_read': False,
                                        'created_at': timezone.now().isoformat(),
                                        'related_id': application_id,
                                        'applicant_name': f'{user_data["first_name"]} {user_data["last_name"] or user_data["username"]}'
                                    }
                                }
                            }
                        )
                    except Exception as e:
                        # Log WebSocket error but don't fail the application
                        print(f"WebSocket notification failed: {e}")
                
                # Success message with detailed confirmation
                messages.success(
                    request, 
                    f'🎉 Your application for "{job["title"]}" at {job["company_name"]} has been successfully submitted! '
                    f'You will receive updates on your application status via email and notifications. '
                    f'Application ID: #{application_id}'
                )
                
                return redirect('accounts:applications')
                    
            except Exception as e:
                # Handle database or other errors gracefully
                messages.error(
                    request, 
                    f'❌ There was an error submitting your application. Please try again. '
                    f'If the problem persists, please contact support. Error: {str(e)}'
                )
                
        else:
            # Form validation errors
            messages.error(
                request, 
                '❌ Please correct the errors in your application form below and try again.'
            )
    else:
        form = JobApplicationForm()
    
    # Get job seeker's existing resume if available
    try:
        if hasattr(job_seeker, 'resume') and job_seeker.resume:
            form.initial['resume'] = job_seeker.resume
    except:
        pass
    
    # Create a proper context object that matches template expectations
    class JobContext:
        def __init__(self, job_data):
            self.data = job_data
            
        def __getattr__(self, name):
            return self.data.get(name)
            
        @property
        def company(self):
            class Company:
                def __init__(self, name):
                    self.name = name
            return Company(self.data.get('company_name'))
            
        def get_formatted_salary(self):
            min_sal = self.data.get('min_salary')
            max_sal = self.data.get('max_salary')
            currency = self.data.get('salary_currency', 'NPR')
            
            if min_sal and max_sal:
                return f"{currency} {min_sal:,} - {max_sal:,}"
            elif min_sal:
                return f"{currency} {min_sal:,}+"
            elif max_sal:
                return f"Up to {currency} {max_sal:,}"
            return "Salary not specified"
            
        @property
        def required_skills_list(self):
            """Return required skills as a list for template iteration"""
            skills = self.data.get('required_skills', '')
            if skills:
                return [skill.strip() for skill in skills.split(',') if skill.strip()]
            return []  
    job_context = JobContext(job)
    
    context = {
        'job': job_context,
        'form': form,
    }
    
    return render(request, 'jobs/job_apply.html', context)

@login_required
def post_job(request):
    """Post a new job (employers only)"""
    try:
        user_profile = request.user.userprofile
        if user_profile.user_type != 'employer':
            messages.error(request, 'Only employers can post jobs.')
            return redirect('home')
        
        try:
            employer_profile = EmployerProfile.objects.get(user_profile=user_profile)
        except EmployerProfile.DoesNotExist:
            messages.error(request, 'Please complete your employer profile first.')
            return redirect('employer:setup_company')
        
        if not employer_profile.can_post_jobs:
            messages.error(request, 'You do not have permission to post jobs.')
            return redirect('employer:dashboard')
        
    except (UserProfile.DoesNotExist, EmployerProfile.DoesNotExist):
        messages.error(request, 'Please complete your employer profile first.')
        return redirect('employer:setup_company')
    
    if request.method == 'POST':
        form = JobPostForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            job.employer = employer_profile
            job.company = employer_profile.company
            
            # Handle status based on user selection
            selected_status = form.cleaned_data.get('status', 'active')
            job.status = selected_status
            
            if selected_status == 'active':
                job.published_at = timezone.now()  # Set published timestamp for active jobs
                success_msg = f'✅ Your job "{job.title}" has been posted successfully and is now live! Job seekers can now view and apply for this position.'
                
                # Create notifications for job seekers with matching skills
                
                # Get job seekers with matching skills
                job_skills = job.required_skills.lower().split(',') if job.required_skills else []
                if job_skills:
                    matching_job_seekers = JobSeekerProfile.objects.filter(
                        skills__icontains=job_skills[0]
                    )
                    
                    # Create notifications for matching job seekers
                    for job_seeker in matching_job_seekers:
                        notification = Notification.objects.create(
                            user=job_seeker.user_profile.user,
                            notification_type='new_job_posting',
                            content=f'New job posting that matches your skills: {job.title}',
                            related_id=job.id,
                            is_email_sent=False
                        )
                        
                        # Send real-time notification via WebSocket
                        channel_layer = get_channel_layer()
                        async_to_sync(channel_layer.group_send)(
                            f'notifications_{job_seeker.user_profile.user.id}',
                            {
                                'type': 'notification_message',
                                'message_type': 'new_notification',
                                'notification': {
                                    'id': notification.id,
                                    'type': notification.notification_type,
                                    'content': notification.content,
                                    'is_read': notification.is_read,
                                    'created_at': notification.created_at.isoformat(),
                                    'related_id': notification.related_id
                                }
                            }
                        )
                
                # Broadcast job feed update
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    'job_feed',
                    {
                        'type': 'job_feed_message',
                        'message_type': 'new_job_posted',
                        'job': {
                            'id': job.id,
                            'title': job.title,
                            'company': job.company.name,
                            'location': f"{job.location.city}, {job.location.state}",
                            'category': job.category.name,
                            'employment_type': job.get_employment_type_display(),
                            'salary': job.get_formatted_salary(),
                            'created_at': job.created_at.isoformat(),
                            'is_remote': job.is_remote,
                            'is_featured': job.is_featured,
                            'url': f'/jobs/{job.id}/'
                        }
                    }
                )
            
            else:
                success_msg = f'📝 Your job "{job.title}" has been saved as a draft. You can publish it later from your job management dashboard.'
            
            job.save()
            
            messages.success(request, success_msg)
            return redirect('employer:job_list')
    else:
        form = JobPostForm()
    
    context = {
        'form': form,
        'employer_profile': employer_profile,
    }
    
    return render(request, 'jobs/post_job.html', context)

@login_required
def edit_job(request, job_id):
    """Edit a job (employers only)"""
    job = get_object_or_404(JobPost, id=job_id)
    
    try:
        user_profile = request.user.userprofile
        if user_profile.user_type != 'employer':
            messages.error(request, 'Only employers can edit jobs.')
            return redirect('home')
        
        try:
            employer_profile = EmployerProfile.objects.get(user_profile=user_profile)
        except EmployerProfile.DoesNotExist:
            messages.error(request, 'Please complete your employer profile first.')
            return redirect('employer:setup_company')
        
        if job.employer != employer_profile:
            messages.error(request, 'You can only edit your own jobs.')
            return redirect('employer:job_list')
        
    except (UserProfile.DoesNotExist, EmployerProfile.DoesNotExist):
        messages.error(request, 'Please complete your employer profile first.')
        return redirect('employer:setup_company')
    
    if request.method == 'POST':
        form = JobPostForm(request.POST, instance=job)
        if form.is_valid():
            job = form.save()
            job.status = 'active'  # Keep jobs active after editing
            job.save()
            
            messages.success(request, 'Your job has been updated successfully!')
            return redirect('employer:job_list')
    else:
        form = JobPostForm(instance=job)
    
    context = {
        'form': form,
        'job': job,
    }
    
    return render(request, 'jobs/edit_job.html', context)

@login_required
def delete_job(request, job_id):
    """Delete a job (employers only) with enhanced safety checks"""
    job = get_object_or_404(JobPost, id=job_id)
    
    try:
        user_profile = request.user.userprofile
        if user_profile.user_type != 'employer':
            messages.error(request, 'Only employers can delete jobs.')
            return redirect('home')
        
        try:
            employer_profile = EmployerProfile.objects.get(user_profile=user_profile)
        except EmployerProfile.DoesNotExist:
            messages.error(request, 'Please complete your employer profile first.')
            return redirect('employer:setup_company')
        
        if job.employer != employer_profile:
            messages.error(request, 'You can only delete your own jobs.')
            return redirect('employer:dashboard')
        
    except (UserProfile.DoesNotExist, EmployerProfile.DoesNotExist):
        messages.error(request, 'Please complete your employer profile first.')
        return redirect('employer:setup_company')
    
    # Check if job has applications
    from applications.models import Application
    application_count = Application.objects.filter(job=job).count()
    
    if request.method == 'POST':
        # Get confirmation from form
        confirmation = request.POST.get('confirm_delete')
        if confirmation == 'DELETE':
            job_title = job.title
            company_name = job.company.name
            
            # Soft delete option - mark as deleted instead of hard delete
            if application_count > 0:
                job.status = 'deleted'
                job.save()
                messages.success(request, f'✅ Job "{job_title}" has been archived due to existing applications. It\'s no longer visible to job seekers.')
            else:
                # Hard delete if no applications
                job.delete()
                messages.success(request, f'✅ Job "{job_title}" has been permanently deleted.')
            
            return redirect('employer:dashboard')
        else:
            messages.error(request, '❌ Job deletion cancelled. Please type "DELETE" to confirm.')
    
    context = {
        'job': job,
        'application_count': application_count,
        'has_applications': application_count > 0,
    }
    
    return render(request, 'jobs/delete_job.html', context)

@login_required
def create_job_alert(request):
    """Create a job alert"""
    try:
        user_profile = request.user.userprofile
        if user_profile.user_type != 'jobseeker':
            messages.error(request, 'Only job seekers can create job alerts.')
            return redirect('home')
        
        try:
            job_seeker_profile = JobSeekerProfile.objects.get(user_profile=user_profile)
        except JobSeekerProfile.DoesNotExist:
            messages.error(request, 'Please complete your job seeker profile first.')
            return redirect('accounts:complete_profile')
        
    except (UserProfile.DoesNotExist, JobSeekerProfile.DoesNotExist):
        messages.error(request, 'Please complete your job seeker profile first.')
        return redirect('accounts:complete_profile')
    
    if request.method == 'POST':
        form = JobAlertForm(request.POST)
        if form.is_valid():
            alert = form.save(commit=False)
            alert.user = job_seeker_profile
            alert.save()
            
            messages.success(request, 'Job alert created successfully!')
            return redirect('accounts:job_alerts_list')
    else:
        form = JobAlertForm()
    
    context = {
        'form': form,
    }
    
    return render(request, 'jobs/create_job_alert.html', context)

@login_required
@require_http_methods(["POST"])
def create_job_alert_ajax(request):
    """Create a job alert via AJAX"""
    try:
        user_profile = request.user.userprofile
        if user_profile.user_type != 'jobseeker':
            return JsonResponse({
                'success': False,
                'error': 'Only job seekers can create job alerts.'
            })
        
        try:
            job_seeker_profile = JobSeekerProfile.objects.get(user_profile=user_profile)
        except JobSeekerProfile.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Please complete your job seeker profile first.'
            })
        
    except UserProfile.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Please complete your job seeker profile first.'
        })
    
    # Get form data from request
    form_data = {
        'title': request.POST.get('alert_name', ''),
        'keywords': request.POST.get('keywords', ''),
        'location': request.POST.get('location', ''),
        'category': request.POST.get('category', ''),
        'employment_type': request.POST.get('employment_type', ''),
        'experience_level': request.POST.get('experience_level', ''),
        'min_salary': request.POST.get('min_salary', ''),
        'max_salary': request.POST.get('max_salary', ''),
        'is_remote': request.POST.get('is_remote') == 'on',
        'frequency': request.POST.get('frequency', 'weekly'),
    }
    
    # Create alert manually since we're using AJAX
    try:
        # Get location and category objects if provided
        location_obj = None
        category_obj = None
        
        if form_data['location']:
            try:
                location_obj = JobLocation.objects.get(id=form_data['location'])
            except JobLocation.DoesNotExist:
                pass
        
        if form_data['category']:
            try:
                category_obj = JobCategory.objects.get(id=form_data['category'])
            except JobCategory.DoesNotExist:
                pass
        
        # Create the job alert
        alert = JobAlert.objects.create(
            user=job_seeker_profile,
            title=form_data['title'] or 'Job Alert',
            keywords=form_data['keywords'],
            location=location_obj,
            category=category_obj,
            employment_type=form_data['employment_type'] if form_data['employment_type'] else None,
            experience_level=form_data['experience_level'] if form_data['experience_level'] else None,
            min_salary=float(form_data['min_salary']) if form_data['min_salary'] else None,
            max_salary=float(form_data['max_salary']) if form_data['max_salary'] else None,
            is_remote=form_data['is_remote'],
            frequency=form_data['frequency'],
            is_active=True
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Job alert created successfully!',
            'alert_id': alert.id,
            'alert_title': alert.title
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error creating job alert: {str(e)}'
        })



def category_jobs(request, category_id):
    """Jobs by category"""
    category = get_object_or_404(JobCategory, id=category_id, is_active=True)
    jobs = JobPost.objects.filter(category=category, status='active').order_by('-created_at')
    
    # Pagination
    paginator = Paginator(jobs, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'category': category,
        'jobs': page_obj,
        'page_obj': page_obj,
        'total_jobs': jobs.count(),
    }
    
    return render(request, 'jobs/category_jobs.html', context)

def location_jobs(request, location_id):
    """Jobs by location"""
    location = get_object_or_404(JobLocation, id=location_id, is_active=True)
    jobs = JobPost.objects.filter(location=location, status='active').order_by('-created_at')
    
    # Pagination
    paginator = Paginator(jobs, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'location': location,
        'jobs': page_obj,
        'page_obj': page_obj,
        'total_jobs': jobs.count(),
    }
    
    return render(request, 'jobs/location_jobs.html', context)

@login_required
@require_http_methods(["POST"])
def save_job(request, job_id):
    """Save/unsave a job (AJAX)"""
    if request.user.userprofile.user_type != 'jobseeker':
        return JsonResponse({'success': False, 'message': 'Unauthorized'})
    
    job = get_object_or_404(JobPost, id=job_id)
    try:
        job_seeker_profile = JobSeekerProfile.objects.get(user_profile=request.user.userprofile)
    except JobSeekerProfile.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Profile not found'})
    
    saved_job, created = SavedJob.objects.get_or_create(
        job=job,
        user=job_seeker_profile
    )
    
    if created:
        return JsonResponse({'success': True, 'message': 'Job saved successfully!', 'action': 'saved'})
    else:
        saved_job.delete()
        return JsonResponse({'success': True, 'message': 'Job removed from saved jobs!', 'action': 'removed'})

def job_statistics(request):
    """Enhanced job statistics page with comprehensive data"""
    from django.db.models import Count, Q, Avg
    from datetime import datetime, timedelta
    from accounts.models import JobSeekerProfile
    
    # Basic statistics
    total_jobs = JobPost.objects.filter(status='active').count()
    total_companies = Company.objects.filter(is_active=True).count()
    total_applications = Application.objects.count()
    total_seekers = JobSeekerProfile.objects.count()
    
    # Jobs by category (top 10)
    jobs_by_category = JobCategory.objects.annotate(
        job_count=Count('jobs', filter=Q(jobs__status='active'))
    ).filter(job_count__gt=0).order_by('-job_count')[:10]
    
    # Jobs by location (top 10)
    jobs_by_location = JobLocation.objects.annotate(
        job_count=Count('jobs', filter=Q(jobs__status='active'))
    ).filter(job_count__gt=0).order_by('-job_count')[:10]
    
    # Employment type distribution
    employment_types = JobPost.objects.filter(status='active').values('employment_type').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Salary range distribution
    salary_ranges = []
    active_jobs = JobPost.objects.filter(status='active', min_salary__isnull=False)
    
    salary_brackets = [
        (0, 30000, '$0-30K'),
        (30000, 50000, '$30K-50K'),
        (50000, 75000, '$50K-75K'),
        (75000, 100000, '$75K-100K'),
        (100000, 125000, '$100K-125K'),
        (125000, 999999, '$125K+')
    ]
    
    for min_sal, max_sal, label in salary_brackets:
        count = active_jobs.filter(min_salary__gte=min_sal, min_salary__lt=max_sal).count()
        if count > 0:
            salary_ranges.append({'range': label, 'count': count})
    
    # Experience level distribution
    experience_levels = JobPost.objects.filter(status='active').values('experience_level').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Remote vs On-site distribution
    remote_distribution = {
        'remote': JobPost.objects.filter(status='active', is_remote=True).count(),
        'hybrid': JobPost.objects.filter(status='active', is_remote=False).count() // 3,  # Simulate hybrid data
        'onsite': JobPost.objects.filter(status='active', is_remote=False).count()
    }
    
    # Recent hiring trends (last 30 days)
    today = timezone.now().date()
    trend_data = []
    application_trend_data = []
    
    for i in range(29, -1, -1):
        date = today - timedelta(days=i)
        
        # Jobs posted on this date
        jobs_count = JobPost.objects.filter(
            created_at__date=date,
            status='active'
        ).count()
        
        # Applications submitted on this date
        apps_count = Application.objects.filter(
            applied_at__date=date
        ).count()
        
        trend_data.append({
            'date': date.strftime('%Y-%m-%d'),
            'jobs': jobs_count
        })
        
        application_trend_data.append({
            'date': date.strftime('%Y-%m-%d'),
            'applications': apps_count
        })
    
    # Top companies by job count
    top_companies = Company.objects.filter(is_active=True).annotate(
        job_count=Count('job_posts', filter=Q(job_posts__status='active'))
    ).filter(job_count__gt=0).order_by('-job_count')[:5]
    
    # Application success rate by category
    category_success_rates = []
    for category in jobs_by_category[:5]:
        total_apps = Application.objects.filter(job__category=category).count()
        successful_apps = Application.objects.filter(
            job__category=category,
            status__in=['hired', 'accepted']
        ).count()
        
        success_rate = (successful_apps / total_apps * 100) if total_apps > 0 else 0
        category_success_rates.append({
            'category': category.name,
            'success_rate': round(success_rate, 1),
            'total_applications': total_apps
        })
    
    # Average salary by category
    avg_salaries_by_category = []
    for category in jobs_by_category[:5]:
        avg_salary = JobPost.objects.filter(
            category=category,
            status='active',
            min_salary__isnull=False
        ).aggregate(avg_salary=Avg('min_salary'))['avg_salary']
        
        if avg_salary:
            avg_salaries_by_category.append({
                'category': category.name,
                'avg_salary': round(avg_salary, 0)
            })
    
    # Recent job posts (enhanced with more details)
    recent_jobs = JobPost.objects.filter(status='active').select_related(
        'company', 'category', 'location'
    ).order_by('-created_at')[:8]
    
    # Job posting activity by day of week
    from django.db.models import Case, When, IntegerField
    weekday_activity = JobPost.objects.filter(
        status='active',
        created_at__gte=today - timedelta(days=90)
    ).extra({
        'weekday': "strftime('%%w', created_at)"
    }).values('weekday').annotate(
        count=Count('id')
    ).order_by('weekday')
    
    # Convert weekday numbers to names
    weekday_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    weekday_data = []
    for item in weekday_activity:
        weekday_data.append({
            'day': weekday_names[int(item['weekday'])],
            'count': item['count']
        })
    
    # Prepare stats data for JSON script tag
    stats_data = {
        'total_jobs': total_jobs,
        'total_companies': total_companies,
        'total_applications': total_applications,
        'total_seekers': total_seekers,
    }
    
    context = {
        'total_jobs': total_jobs,
        'total_companies': total_companies,
        'total_applications': total_applications,
        'total_seekers': total_seekers,
        'stats_data': stats_data,
        
        # Category and location data
        'jobs_by_category': jobs_by_category,
        'jobs_by_location': jobs_by_location,
        
        # Employment and salary data
        'employment_types': employment_types,
        'salary_ranges': salary_ranges,
        'experience_levels': experience_levels,
        'remote_distribution': remote_distribution,
        
        # Trends and analytics
        'trend_data': trend_data,
        'application_trend_data': application_trend_data,
        'top_companies': top_companies,
        'category_success_rates': category_success_rates,
        'avg_salaries_by_category': avg_salaries_by_category,
        'weekday_data': weekday_data,
        
        # Recent jobs
        'recent_jobs': recent_jobs,
    }
    
    return render(request, 'jobs/statistics.html', context)

