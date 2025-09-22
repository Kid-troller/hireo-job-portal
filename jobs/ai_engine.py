"""
AI Engine for Enhanced Job Search and Recommendations
Provides intelligent features for the jobs page
"""

import re
import json
import math
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from django.db.models import Q, Count, Avg, F
from django.utils import timezone
from django.contrib.auth.models import User
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from .models import JobPost, JobCategory, JobLocation
from accounts.models import JobSeekerProfile, UserProfile
from applications.models import Application

class JobAIEngine:
    """Advanced AI engine for job search enhancement"""
    
    def __init__(self):
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2),
            lowercase=True
        )
    
    def get_smart_search_suggestions(self, query, limit=5):
        """Generate intelligent search suggestions based on query"""
        suggestions = []
        
        if not query or len(query) < 2:
            # Popular searches
            popular_titles = JobPost.objects.filter(
                status='active'
            ).values('title').annotate(
                count=Count('id')
            ).order_by('-count')[:limit]
            
            return [item['title'] for item in popular_titles]
        
        # Find similar job titles
        similar_jobs = JobPost.objects.filter(
            Q(title__icontains=query) | 
            Q(required_skills__icontains=query),
            status='active'
        ).values('title').distinct()[:limit]
        
        suggestions.extend([job['title'] for job in similar_jobs])
        
        # Add skill-based suggestions
        if len(suggestions) < limit:
            skill_matches = JobPost.objects.filter(
                required_skills__icontains=query,
                status='active'
            ).values('required_skills')[:10]
            
            all_skills = []
            for match in skill_matches:
                if match['required_skills']:
                    skills = [s.strip() for s in match['required_skills'].split(',')]
                    all_skills.extend(skills)
            
            # Find skills similar to query
            similar_skills = [skill for skill in set(all_skills) 
                            if query.lower() in skill.lower() and skill.lower() != query.lower()]
            suggestions.extend(similar_skills[:limit - len(suggestions)])
        
        return suggestions[:limit]
    
    def get_job_match_score(self, job, user_profile=None):
        """Calculate AI-powered job match score"""
        if not user_profile or user_profile.user_type != 'jobseeker':
            return 50  # Default score
        
        try:
            job_seeker = JobSeekerProfile.objects.get(user_profile=user_profile)
        except JobSeekerProfile.DoesNotExist:
            return 50
        
        score = 0
        max_score = 100
        
        # Skills matching (40% weight)
        if job_seeker.skills and job.required_skills:
            user_skills = set(skill.strip().lower() for skill in job_seeker.skills.split(','))
            job_skills = set(skill.strip().lower() for skill in job.required_skills.split(','))
            
            if user_skills and job_skills:
                skill_overlap = len(user_skills.intersection(job_skills))
                skill_score = (skill_overlap / len(job_skills)) * 40
                score += min(skill_score, 40)
        
        # Experience level matching (25% weight)
        if job_seeker.experience_years and job.min_experience:
            exp_diff = abs(job_seeker.experience_years - job.min_experience)
            if exp_diff <= 1:
                score += 25
            elif exp_diff <= 3:
                score += 15
            elif exp_diff <= 5:
                score += 10
        
        # Salary expectations (20% weight)
        if job_seeker.expected_salary and job.max_salary:
            if job_seeker.expected_salary <= job.max_salary:
                score += 20
            elif job_seeker.expected_salary <= job.max_salary * 1.2:
                score += 10
        
        # Location preference (15% weight)
        if job_seeker.preferred_location and job.location:
            if job_seeker.preferred_location.lower() in job.location.city.lower():
                score += 15
            elif job.is_remote:
                score += 10
        
        return min(score, max_score)
    
    def get_trending_keywords(self, days=7):
        """Get trending job keywords from recent postings"""
        recent_jobs = JobPost.objects.filter(
            status='active',
            created_at__gte=timezone.now() - timedelta(days=days)
        )
        
        all_skills = []
        for job in recent_jobs:
            if job.required_skills:
                skills = [s.strip().lower() for s in job.required_skills.split(',')]
                all_skills.extend(skills)
        
        # Count frequency
        skill_counter = Counter(all_skills)
        return skill_counter.most_common(10)
    
    def get_salary_insights(self, category=None, location=None):
        """Get AI-powered salary insights"""
        jobs = JobPost.objects.filter(status='active')
        
        if category:
            jobs = jobs.filter(category=category)
        if location:
            jobs = jobs.filter(location=location)
        
        jobs_with_salary = jobs.exclude(
            Q(min_salary__isnull=True) & Q(max_salary__isnull=True)
        )
        
        if not jobs_with_salary.exists():
            return None
        
        # Calculate statistics
        salaries = []
        for job in jobs_with_salary:
            if job.min_salary and job.max_salary:
                avg_salary = (job.min_salary + job.max_salary) / 2
            elif job.min_salary:
                avg_salary = job.min_salary
            elif job.max_salary:
                avg_salary = job.max_salary
            else:
                continue
            salaries.append(float(avg_salary))
        
        if not salaries:
            return None
        
        return {
            'average': sum(salaries) / len(salaries),
            'median': sorted(salaries)[len(salaries) // 2],
            'min': min(salaries),
            'max': max(salaries),
            'count': len(salaries)
        }
    
    def analyze_job_market_trends(self):
        """Analyze current job market trends"""
        now = timezone.now()
        last_month = now - timedelta(days=30)
        
        # Job posting trends
        recent_jobs = JobPost.objects.filter(
            status='active',
            created_at__gte=last_month
        )
        
        # Category trends
        category_trends = recent_jobs.values('category__name').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        
        # Location trends
        location_trends = recent_jobs.values('location__city').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        
        # Remote work trends
        remote_percentage = recent_jobs.filter(is_remote=True).count() / max(recent_jobs.count(), 1) * 100
        
        return {
            'total_jobs': recent_jobs.count(),
            'category_trends': list(category_trends),
            'location_trends': list(location_trends),
            'remote_percentage': round(remote_percentage, 1),
            'trending_keywords': self.get_trending_keywords()
        }
    
    def get_personalized_filters(self, user):
        """Get AI-suggested filters based on user profile"""
        if not user.is_authenticated:
            return {}
        
        try:
            user_profile = user.userprofile
            if user_profile.user_type != 'jobseeker':
                return {}
            
            job_seeker = JobSeekerProfile.objects.get(user_profile=user_profile)
        except (UserProfile.DoesNotExist, JobSeekerProfile.DoesNotExist):
            return {}
        
        suggestions = {}
        
        # Suggest categories based on skills
        if job_seeker.skills:
            user_skills = [s.strip().lower() for s in job_seeker.skills.split(',')]
            
            # Find categories with matching skills
            matching_categories = JobPost.objects.filter(
                status='active'
            ).values('category__name', 'category__id').annotate(
                skill_matches=Count('id', filter=Q(required_skills__icontains=user_skills[0]))
            ).order_by('-skill_matches')[:3]
            
            if matching_categories:
                suggestions['categories'] = list(matching_categories)
        
        # Suggest experience level
        if job_seeker.experience_years:
            if job_seeker.experience_years <= 1:
                suggestions['experience_level'] = 'entry'
            elif job_seeker.experience_years <= 3:
                suggestions['experience_level'] = 'junior'
            elif job_seeker.experience_years <= 7:
                suggestions['experience_level'] = 'mid'
            else:
                suggestions['experience_level'] = 'senior'
        
        # Suggest location
        if job_seeker.preferred_location:
            suggestions['location'] = job_seeker.preferred_location
        
        # Suggest salary range
        if job_seeker.expected_salary:
            suggestions['salary_min'] = max(0, float(job_seeker.expected_salary) * 0.8)
            suggestions['salary_max'] = float(job_seeker.expected_salary) * 1.2
        
        return suggestions

# Global instance
job_ai_engine = JobAIEngine()
