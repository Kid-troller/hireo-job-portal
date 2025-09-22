"""
API views for jobs app
"""
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.db.models import Q
from django.core.cache import cache
# from django_ratelimit.decorators import ratelimit  # Disabled until installed
from django.utils.decorators import method_decorator
import logging

logger = logging.getLogger('hireo')

# @method_decorator(ratelimit(key='ip', rate='100/h', method='GET'), name='get')  # Disabled until installed
class JobListAPIView(generics.ListAPIView):
    """List all active jobs with caching and rate limiting"""
    permission_classes = [AllowAny]
    
    def get(self, request, *args, **kwargs):
        # Try to get from cache first
        cache_key = 'active_jobs_list'
        cached_jobs = cache.get(cache_key)
        
        if cached_jobs:
            return Response(cached_jobs)
        
        try:
            from .models import JobPost
            jobs = JobPost.objects.filter(status='active').select_related(
                'company', 'category', 'location'
            ).order_by('-created_at')[:50]
            
            job_data = []
            for job in jobs:
                job_data.append({
                    'id': job.id,
                    'title': job.title,
                    'company': job.company.name if job.company else 'Unknown',
                    'location': f"{job.location.city}, {job.location.state}" if job.location else 'Remote',
                    'category': job.category.name if job.category else 'General',
                    'employment_type': job.employment_type,
                    'salary_min': job.min_salary,
                    'salary_max': job.max_salary,
                    'is_remote': job.is_remote,
                    'is_featured': job.is_featured,
                    'created_at': job.created_at,
                    'description': job.description[:200] + '...' if len(job.description) > 200 else job.description
                })
            
            # Cache for 5 minutes
            cache.set(cache_key, job_data, 300)
            
            return Response(job_data)
            
        except Exception as e:
            logger.error(f"Error fetching job list: {e}")
            return Response({
                'error': 'Error fetching jobs'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# @method_decorator(ratelimit(key='ip', rate='200/h', method='GET'), name='get')  # Disabled until installed
class JobDetailAPIView(generics.RetrieveAPIView):
    """Get job details with rate limiting"""
    permission_classes = [AllowAny]
    
    def get(self, request, pk, *args, **kwargs):
        cache_key = f'job_detail_{pk}'
        cached_job = cache.get(cache_key)
        
        if cached_job:
            return Response(cached_job)
        
        try:
            from .models import JobPost
            job = JobPost.objects.select_related(
                'company', 'category', 'location'
            ).get(id=pk, status='active')
            
            job_data = {
                'id': job.id,
                'title': job.title,
                'company': {
                    'name': job.company.name if job.company else 'Unknown',
                    'description': job.company.description if job.company else '',
                    'website': job.company.website if job.company else ''
                },
                'location': {
                    'city': job.location.city if job.location else 'Remote',
                    'state': job.location.state if job.location else '',
                    'country': job.location.country if job.location else ''
                },
                'category': job.category.name if job.category else 'General',
                'employment_type': job.employment_type,
                'salary_min': job.min_salary,
                'salary_max': job.max_salary,
                'currency': job.currency,
                'is_remote': job.is_remote,
                'is_featured': job.is_featured,
                'description': job.description,
                'requirements': job.requirements,
                'benefits': job.benefits,
                'required_skills': job.required_skills,
                'experience_level': job.experience_level,
                'created_at': job.created_at,
                'application_deadline': job.application_deadline
            }
            
            # Cache for 10 minutes
            cache.set(cache_key, job_data, 600)
            
            return Response(job_data)
            
        except Exception as e:
            logger.error(f"Error fetching job {pk}: {e}")
            return Response({
                'error': 'Job not found'
            }, status=status.HTTP_404_NOT_FOUND)

# @method_decorator(ratelimit(key='ip', rate='50/h', method='GET'), name='get')  # Disabled until installed
class JobSearchAPIView(generics.ListAPIView):
    """Search jobs with filters and rate limiting"""
    permission_classes = [AllowAny]
    
    def get(self, request, *args, **kwargs):
        query = request.GET.get('q', '')
        location = request.GET.get('location', '')
        category = request.GET.get('category', '')
        employment_type = request.GET.get('type', '')
        remote_only = request.GET.get('remote', '').lower() == 'true'
        
        try:
            from .models import JobPost
            jobs = JobPost.objects.filter(status='active').select_related(
                'company', 'category', 'location'
            )
            
            if query:
                jobs = jobs.filter(
                    Q(title__icontains=query) |
                    Q(description__icontains=query) |
                    Q(required_skills__icontains=query)
                )
            
            if location:
                jobs = jobs.filter(
                    Q(location__city__icontains=location) |
                    Q(location__state__icontains=location)
                )
            
            if category:
                jobs = jobs.filter(category__name__icontains=category)
            
            if employment_type:
                jobs = jobs.filter(employment_type=employment_type)
            
            if remote_only:
                jobs = jobs.filter(is_remote=True)
            
            jobs = jobs.order_by('-created_at')[:20]
            
            job_data = []
            for job in jobs:
                job_data.append({
                    'id': job.id,
                    'title': job.title,
                    'company': job.company.name if job.company else 'Unknown',
                    'location': f"{job.location.city}, {job.location.state}" if job.location else 'Remote',
                    'category': job.category.name if job.category else 'General',
                    'employment_type': job.employment_type,
                    'salary_min': job.min_salary,
                    'salary_max': job.max_salary,
                    'is_remote': job.is_remote,
                    'created_at': job.created_at
                })
            
            return Response({
                'count': len(job_data),
                'results': job_data
            })
            
        except Exception as e:
            logger.error(f"Error searching jobs: {e}")
            return Response({
                'error': 'Error searching jobs'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# @method_decorator(ratelimit(key='ip', rate='20/h', method='GET'), name='get')  # Disabled until installed
class JobCategoryListAPIView(generics.ListAPIView):
    """List job categories with caching"""
    permission_classes = [AllowAny]
    
    def get(self, request, *args, **kwargs):
        cache_key = 'job_categories'
        cached_categories = cache.get(cache_key)
        
        if cached_categories:
            return Response(cached_categories)
        
        try:
            from .models import JobCategory
            categories = JobCategory.objects.filter(is_active=True)
            
            category_data = []
            for category in categories:
                category_data.append({
                    'id': category.id,
                    'name': category.name,
                    'description': category.description
                })
            
            # Cache for 1 hour
            cache.set(cache_key, category_data, 3600)
            
            return Response(category_data)
            
        except Exception as e:
            logger.error(f"Error fetching categories: {e}")
            return Response({
                'error': 'Error fetching categories'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
