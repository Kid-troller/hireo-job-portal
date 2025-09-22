from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.db.models import Count, Sum, Avg, Q, F
from django.db.models.functions import TruncMonth, TruncWeek, TruncDay
from django.utils import timezone
from datetime import datetime, timedelta
from django.core.paginator import Paginator
import json
import csv
from io import StringIO

from .models import (
    JobView, JobClick, JobSeekerActivity, EmployerEngagement,
    SkillDemand, SalaryInsight, ApplicationConversion, TrendingJob,
    CompanyMetrics, MarketInsight, UserAlert
)
from jobs.models import JobPost, JobCategory, JobLocation
from employers.models import Company
from accounts.models import JobSeekerProfile, UserProfile
from applications.models import Application


@login_required
def analytics_dashboard(request):
    """Main analytics dashboard view"""
    user_type = request.user.userprofile.user_type
    
    if user_type == 'employer':
        return employer_analytics_dashboard(request)
    elif user_type == 'jobseeker':
        return jobseeker_analytics_dashboard(request)
    else:
        return admin_analytics_dashboard(request)


def employer_analytics_dashboard(request):
    """Analytics dashboard for employers"""
    try:
        employer_profile = request.user.userprofile.employerprofile
        company = employer_profile.company
    except:
        company = None
    
    # Get date range filter
    days = int(request.GET.get('days', 30))
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    # Basic metrics
    if company:
        total_jobs = JobPost.objects.filter(company=company).count()
        active_jobs = JobPost.objects.filter(company=company, status='active').count()
        total_applications = Application.objects.filter(job__company=company).count()
        
        # Job performance metrics
        job_views = JobView.objects.filter(
            job__company=company,
            viewed_at__range=[start_date, end_date]
        ).count()
        
        job_clicks = JobClick.objects.filter(
            job__company=company,
            clicked_at__range=[start_date, end_date]
        ).count()
        
        # Top performing jobs
        top_jobs = JobPost.objects.filter(
            company=company,
            status='active'
        ).annotate(
            view_count=Count('analytics_views'),
            application_count=Count('applications')
        ).order_by('-view_count')[:5]
        
        # Application trends
        application_trends = Application.objects.filter(
            job__company=company,
            applied_at__range=[start_date, end_date]
        ).extra(
            select={'day': 'date(applied_at)'}
        ).values('day').annotate(
            count=Count('id')
        ).order_by('day')
        
    else:
        total_jobs = active_jobs = total_applications = job_views = job_clicks = 0
        top_jobs = []
        application_trends = []
    
    context = {
        'user_type': 'employer',
        'total_jobs': total_jobs,
        'active_jobs': active_jobs,
        'total_applications': total_applications,
        'job_views': job_views,
        'job_clicks': job_clicks,
        'top_jobs': top_jobs,
        'application_trends': list(application_trends),
        'days': days,
    }
    
    return render(request, 'analytics/employer_dashboard.html', context)


def jobseeker_analytics_dashboard(request):
    """Analytics dashboard for job seekers"""
    try:
        jobseeker_profile = request.user.userprofile.jobseekerprofile
    except:
        jobseeker_profile = None
    
    # Get date range filter
    days = int(request.GET.get('days', 30))
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    # Basic metrics
    total_applications = Application.objects.filter(
        applicant=jobseeker_profile,
        applied_at__range=[start_date, end_date]
    ).count() if jobseeker_profile else 0
    
    # Application status breakdown
    application_status = Application.objects.filter(
        applicant=jobseeker_profile
    ).values('status').annotate(
        count=Count('id')
    ) if jobseeker_profile else []
    
    # Job search activity
    search_activity = JobSeekerActivity.objects.filter(
        job_seeker=jobseeker_profile,
        timestamp__range=[start_date, end_date]
    ).values('activity_type').annotate(
        count=Count('id')
    ) if jobseeker_profile else []
    
    # Recommended skills based on market demand
    trending_skills = SkillDemand.objects.values('skill_name').annotate(
        demand_count=Count('id')
    ).order_by('-demand_count')[:10]
    
    # Job market insights
    market_insights = get_job_market_insights()
    
    context = {
        'user_type': 'jobseeker',
        'total_applications': total_applications,
        'application_status': list(application_status),
        'search_activity': list(search_activity),
        'trending_skills': trending_skills,
        'market_insights': market_insights,
        'days': days,
    }
    
    return render(request, 'analytics/jobseeker_dashboard.html', context)


def admin_analytics_dashboard(request):
    """Analytics dashboard for admins"""
    # Get date range filter
    days = int(request.GET.get('days', 30))
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    # Overall platform metrics
    total_jobs = JobPost.objects.count()
    active_jobs = JobPost.objects.filter(status='active').count()
    total_users = UserProfile.objects.count()
    total_companies = Company.objects.count()
    
    # Growth metrics
    new_jobs = JobPost.objects.filter(
        created_at__range=[start_date, end_date]
    ).count()
    
    new_users = UserProfile.objects.filter(
        created_at__range=[start_date, end_date]
    ).count()
    
    # Top categories
    top_categories = JobPost.objects.values(
        'category__name'
    ).annotate(
        job_count=Count('id')
    ).order_by('-job_count')[:10]
    
    # Top locations
    top_locations = JobPost.objects.values(
        'location__city'
    ).annotate(
        job_count=Count('id')
    ).order_by('-job_count')[:10]
    
    # Salary insights
    salary_insights = get_salary_insights()
    
    context = {
        'user_type': 'admin',
        'total_jobs': total_jobs,
        'active_jobs': active_jobs,
        'total_users': total_users,
        'total_companies': total_companies,
        'new_jobs': new_jobs,
        'new_users': new_users,
        'top_categories': top_categories,
        'top_locations': top_locations,
        'salary_insights': salary_insights,
        'days': days,
    }
    
    return render(request, 'analytics/admin_dashboard.html', context)


def get_job_market_insights():
    """Get general job market insights"""
    insights = {}
    
    # Most in-demand skills
    insights['top_skills'] = SkillDemand.objects.values('skill_name').annotate(
        demand_count=Count('id')
    ).order_by('-demand_count')[:10]
    
    # Fastest growing categories
    thirty_days_ago = timezone.now() - timedelta(days=30)
    insights['growing_categories'] = JobPost.objects.filter(
        created_at__gte=thirty_days_ago
    ).values('category__name').annotate(
        job_count=Count('id')
    ).order_by('-job_count')[:5]
    
    # Top hiring companies
    insights['top_companies'] = JobPost.objects.filter(
        status='active'
    ).values('company__name').annotate(
        job_count=Count('id')
    ).order_by('-job_count')[:10]
    
    return insights


def get_salary_insights():
    """Get salary insights across different categories and locations"""
    salary_data = SalaryInsight.objects.values(
        'category__name',
        'location__city'
    ).annotate(
        avg_min_salary=Avg('min_salary'),
        avg_max_salary=Avg('max_salary'),
        job_count=Count('id')
    ).order_by('-avg_max_salary')[:20]
    
    return salary_data


@login_required
def trending_jobs_api(request):
    """API endpoint for trending jobs"""
    trend_type = request.GET.get('type', 'views')
    limit = int(request.GET.get('limit', 10))
    
    trending = TrendingJob.objects.filter(
        trend_type=trend_type
    ).select_related('job', 'job__company', 'job__category').order_by('rank')[:limit]
    
    data = []
    for trend in trending:
        data.append({
            'job_id': trend.job.id,
            'title': trend.job.title,
            'company': trend.job.company.name,
            'category': trend.job.category.name,
            'score': float(trend.score),
            'rank': trend.rank
        })
    
    return JsonResponse({'trending_jobs': data})


@login_required
def skill_demand_api(request):
    """API endpoint for skill demand analysis"""
    category_id = request.GET.get('category')
    location_id = request.GET.get('location')
    limit = int(request.GET.get('limit', 20))
    
    queryset = SkillDemand.objects.all()
    
    if category_id:
        queryset = queryset.filter(category_id=category_id)
    if location_id:
        queryset = queryset.filter(location_id=location_id)
    
    skill_data = queryset.values('skill_name').annotate(
        total_demand=Count('id'),
        required_count=Count('id', filter=Q(is_required=True)),
        preferred_count=Count('id', filter=Q(is_required=False))
    ).order_by('-total_demand')[:limit]
    
    return JsonResponse({'skill_demand': list(skill_data)})


@login_required
def salary_trends_api(request):
    """API endpoint for salary trends"""
    category_id = request.GET.get('category')
    location_id = request.GET.get('location')
    experience_level = request.GET.get('experience')
    
    queryset = SalaryInsight.objects.all()
    
    if category_id:
        queryset = queryset.filter(category_id=category_id)
    if location_id:
        queryset = queryset.filter(location_id=location_id)
    if experience_level:
        queryset = queryset.filter(experience_level=experience_level)
    
    salary_data = queryset.aggregate(
        avg_min=Avg('min_salary'),
        avg_max=Avg('max_salary'),
        min_salary=Min('min_salary'),
        max_salary=Max('max_salary'),
        job_count=Count('id')
    )
    
    return JsonResponse({'salary_trends': salary_data})


@login_required
def export_analytics_data(request):
    """Export analytics data to CSV"""
    data_type = request.GET.get('type', 'jobs')
    format_type = request.GET.get('format', 'csv')
    
    if format_type == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{data_type}_analytics.csv"'
        
        writer = csv.writer(response)
        
        if data_type == 'jobs':
            writer.writerow(['Job Title', 'Company', 'Category', 'Views', 'Applications', 'Created Date'])
            
            jobs = JobPost.objects.select_related('company', 'category').annotate(
                view_count=Count('analytics_views'),
                app_count=Count('applications')
            )
            
            for job in jobs:
                writer.writerow([
                    job.title,
                    job.company.name,
                    job.category.name,
                    job.view_count,
                    job.app_count,
                    job.created_at.strftime('%Y-%m-%d')
                ])
        
        elif data_type == 'skills':
            writer.writerow(['Skill Name', 'Total Demand', 'Required Count', 'Preferred Count'])
            
            skills = SkillDemand.objects.values('skill_name').annotate(
                total_demand=Count('id'),
                required_count=Count('id', filter=Q(is_required=True)),
                preferred_count=Count('id', filter=Q(is_required=False))
            ).order_by('-total_demand')
            
            for skill in skills:
                writer.writerow([
                    skill['skill_name'],
                    skill['total_demand'],
                    skill['required_count'],
                    skill['preferred_count']
                ])
        
        return response
    
    return JsonResponse({'error': 'Unsupported format'}, status=400)


@login_required
def live_job_feed_api(request):
    """API endpoint for live job feed"""
    last_id = request.GET.get('last_id', 0)
    limit = int(request.GET.get('limit', 10))
    
    jobs = JobPost.objects.filter(
        id__gt=last_id,
        status='active'
    ).select_related('company', 'category', 'location').order_by('-created_at')[:limit]
    
    data = []
    for job in jobs:
        data.append({
            'id': job.id,
            'title': job.title,
            'company': job.company.name,
            'category': job.category.name,
            'location': f"{job.location.city}, {job.location.state}",
            'created_at': job.created_at.isoformat(),
            'salary_range': f"${job.min_salary} - ${job.max_salary}" if job.min_salary and job.max_salary else "Not specified"
        })
    
    return JsonResponse({
        'jobs': data,
        'last_id': jobs[0].id if jobs else last_id
    })


def track_job_view(request, job_id):
    """Track job view for analytics"""
    job = get_object_or_404(JobPost, id=job_id)
    
    # Get client IP
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    
    # Create job view record
    JobView.objects.create(
        job=job,
        viewer=request.user if request.user.is_authenticated else None,
        ip_address=ip,
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        session_id=request.session.session_key or ''
    )
    
    return JsonResponse({'status': 'success'})


def track_job_click(request, job_id):
    """Track job click for analytics"""
    job = get_object_or_404(JobPost, id=job_id)
    click_type = request.POST.get('click_type', 'apply')
    
    # Get client IP
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    
    # Create job click record
    JobClick.objects.create(
        job=job,
        user=request.user if request.user.is_authenticated else None,
        click_type=click_type,
        ip_address=ip,
        session_id=request.session.session_key or ''
    )
    
    return JsonResponse({'status': 'success'})
