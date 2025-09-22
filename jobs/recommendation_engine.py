"""
Advanced Job Recommendation Engine for Hireo Job Portal
Uses machine learning algorithms and user behavior analysis for intelligent job matching
"""

import re
import math
from collections import Counter
from datetime import datetime, timedelta
from django.db.models import Q, Count, Avg, F
from django.utils import timezone
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from .models import JobPost, JobCategory, JobLocation, JobView, JobSearch, SavedJob
from accounts.models import JobSeekerProfile, UserProfile
from applications.models import Application


class JobRecommendationEngine:
    """Advanced job recommendation engine with multiple algorithms"""
    
    def __init__(self):
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2),
            lowercase=True
        )
    
    def get_user_recommendations(self, user, limit=10):
        """Get personalized job recommendations for a user"""
        try:
            user_profile = user.userprofile
            if user_profile.user_type != 'jobseeker':
                return self._get_trending_jobs(limit)
            
            try:
                job_seeker = JobSeekerProfile.objects.get(user_profile=user_profile)
            except JobSeekerProfile.DoesNotExist:
                return self._get_trending_jobs(limit)
            
            # Get different types of recommendations
            content_based = self._content_based_recommendations(job_seeker, limit)
            collaborative = self._collaborative_filtering(job_seeker, limit)
            behavior_based = self._behavior_based_recommendations(job_seeker, limit)
            trending = self._get_trending_jobs(limit)
            
            # Combine and score recommendations
            combined_recommendations = self._combine_recommendations({
                'content_based': content_based,
                'collaborative': collaborative,
                'behavior_based': behavior_based,
                'trending': trending
            }, limit)
            
            return combined_recommendations
            
        except Exception as e:
            print(f"Error in recommendations: {e}")
            return self._get_trending_jobs(limit)
    
    def _content_based_recommendations(self, job_seeker, limit):
        """Content-based filtering using user profile and job descriptions"""
        try:
            # Build user profile text
            user_text = self._build_user_profile_text(job_seeker)
            
            # Get active jobs
            jobs = JobPost.objects.filter(status='active').select_related('company', 'category')
            
            if not jobs.exists():
                return []
            
            # Build job texts
            job_texts = []
            job_ids = []
            
            for job in jobs:
                job_text = self._build_job_text(job)
                job_texts.append(job_text)
                job_ids.append(job.id)
            
            # Add user profile to texts for comparison
            all_texts = [user_text] + job_texts
            
            # Calculate TF-IDF similarity
            tfidf_matrix = self.tfidf_vectorizer.fit_transform(all_texts)
            user_vector = tfidf_matrix[0]
            job_vectors = tfidf_matrix[1:]
            
            # Calculate cosine similarity
            similarities = cosine_similarity(user_vector, job_vectors).flatten()
            
            # Get top recommendations
            job_similarity_pairs = list(zip(job_ids, similarities))
            job_similarity_pairs.sort(key=lambda x: x[1], reverse=True)
            
            recommended_job_ids = [job_id for job_id, _ in job_similarity_pairs[:limit]]
            
            # Return jobs in order of similarity
            jobs_dict = {job.id: job for job in jobs}
            return [jobs_dict[job_id] for job_id in recommended_job_ids if job_id in jobs_dict]
            
        except Exception as e:
            print(f"Content-based recommendation error: {e}")
            return []
    
    def _collaborative_filtering(self, job_seeker, limit):
        """Collaborative filtering based on similar users' preferences"""
        try:
            # Find users with similar profiles
            similar_users = self._find_similar_users(job_seeker)
            
            if not similar_users:
                return []
            
            # Get jobs that similar users have saved or applied to
            similar_user_profiles = [user.user_profile for user in similar_users]
            
            # Jobs saved by similar users
            saved_jobs = SavedJob.objects.filter(
                user__user_profile__in=similar_user_profiles
            ).values_list('job_id', flat=True)
            
            # Jobs applied to by similar users
            applied_jobs = Application.objects.filter(
                applicant__user_profile__in=similar_user_profiles,
                status__in=['applied', 'reviewing', 'shortlisted']
            ).values_list('job_id', flat=True)
            
            # Combine and get unique job IDs
            recommended_job_ids = list(set(list(saved_jobs) + list(applied_jobs)))
            
            # Exclude jobs user has already interacted with
            user_applied_jobs = Application.objects.filter(
                applicant=job_seeker
            ).values_list('job_id', flat=True)
            
            user_saved_jobs = SavedJob.objects.filter(
                user=job_seeker
            ).values_list('job_id', flat=True)
            
            excluded_jobs = set(list(user_applied_jobs) + list(user_saved_jobs))
            recommended_job_ids = [job_id for job_id in recommended_job_ids if job_id not in excluded_jobs]
            
            # Get job objects
            jobs = JobPost.objects.filter(
                id__in=recommended_job_ids[:limit],
                status='active'
            ).select_related('company', 'category')
            
            return list(jobs)
            
        except Exception as e:
            print(f"Collaborative filtering error: {e}")
            return []
    
    def _behavior_based_recommendations(self, job_seeker, limit):
        """Recommendations based on user behavior patterns"""
        try:
            user = job_seeker.user_profile.user
            
            # Get user's search history
            recent_searches = JobSearch.objects.filter(
                job_seeker=job_seeker,
                searched_at__gte=timezone.now() - timedelta(days=30)
            ).order_by('-searched_at')
            
            # Get user's viewed jobs
            viewed_jobs = JobView.objects.filter(
                user=user,
                viewed_at__gte=timezone.now() - timedelta(days=30)
            ).select_related('job')
            
            # Extract keywords from searches and viewed jobs
            keywords = []
            categories = []
            locations = []
            
            for search in recent_searches:
                if search.query:
                    keywords.extend(search.query.lower().split())
                if search.category:
                    categories.append(search.category.id)
                if search.location:
                    locations.append(search.location.id)
            
            for view in viewed_jobs:
                job = view.job
                keywords.extend(job.title.lower().split())
                if job.category:
                    categories.append(job.category.id)
                if job.location:
                    locations.append(job.location.id)
            
            # Find jobs matching user behavior patterns
            jobs_query = JobPost.objects.filter(status='active')
            
            if keywords:
                keyword_q = Q()
                for keyword in set(keywords):
                    keyword_q |= (
                        Q(title__icontains=keyword) |
                        Q(description__icontains=keyword) |
                        Q(requirements__icontains=keyword)
                    )
                jobs_query = jobs_query.filter(keyword_q)
            
            if categories:
                jobs_query = jobs_query.filter(category_id__in=set(categories))
            
            if locations:
                jobs_query = jobs_query.filter(location_id__in=set(locations))
            
            # Exclude already applied jobs
            applied_jobs = Application.objects.filter(
                applicant=job_seeker
            ).values_list('job_id', flat=True)
            
            jobs_query = jobs_query.exclude(id__in=applied_jobs)
            
            return list(jobs_query.select_related('company', 'category')[:limit])
            
        except Exception as e:
            print(f"Behavior-based recommendation error: {e}")
            return []
    
    def _get_trending_jobs(self, limit):
        """Get trending jobs based on views and applications"""
        try:
            # Calculate trending score based on recent activity
            trending_jobs = JobPost.objects.filter(
                status='active',
                published_at__gte=timezone.now() - timedelta(days=7)
            ).annotate(
                recent_views=Count('jobview', filter=Q(jobview__viewed_at__gte=timezone.now() - timedelta(days=3))),
                recent_applications=Count('application', filter=Q(application__applied_at__gte=timezone.now() - timedelta(days=3))),
                trending_score=F('recent_views') + F('recent_applications') * 2
            ).order_by('-trending_score', '-published_at').select_related('company', 'category')
            
            return list(trending_jobs[:limit])
            
        except Exception as e:
            print(f"Trending jobs error: {e}")
            return JobPost.objects.filter(status='active').order_by('-published_at')[:limit]
    
    def _combine_recommendations(self, recommendation_sets, limit):
        """Combine different recommendation algorithms with weighted scoring"""
        job_scores = {}
        weights = {
            'content_based': 0.4,
            'collaborative': 0.3,
            'behavior_based': 0.2,
            'trending': 0.1
        }
        
        for algorithm, jobs in recommendation_sets.items():
            weight = weights.get(algorithm, 0.1)
            for i, job in enumerate(jobs):
                if job.id not in job_scores:
                    job_scores[job.id] = {'job': job, 'score': 0}
                
                # Higher score for higher ranking
                position_score = (len(jobs) - i) / len(jobs)
                job_scores[job.id]['score'] += weight * position_score
        
        # Sort by combined score
        sorted_jobs = sorted(job_scores.values(), key=lambda x: x['score'], reverse=True)
        
        return [item['job'] for item in sorted_jobs[:limit]]
    
    def _build_user_profile_text(self, job_seeker):
        """Build text representation of user profile"""
        text_parts = []
        
        if job_seeker.skills:
            text_parts.append(job_seeker.skills)
        
        if job_seeker.experience_level:
            text_parts.append(job_seeker.experience_level)
        
        if job_seeker.preferred_job_title:
            text_parts.append(job_seeker.preferred_job_title)
        
        if job_seeker.bio:
            text_parts.append(job_seeker.bio)
        
        # Add education and experience
        for education in job_seeker.resumeeducation_set.all():
            text_parts.extend([education.degree, education.field_of_study, education.institution])
        
        for experience in job_seeker.resumeexperience_set.all():
            text_parts.extend([experience.job_title, experience.company, experience.description])
        
        return ' '.join(filter(None, text_parts))
    
    def _build_job_text(self, job):
        """Build text representation of job posting"""
        text_parts = [
            job.title,
            job.description,
            job.requirements,
            job.employment_type,
            job.experience_level,
            job.company.name if job.company else '',
            job.category.name if job.category else '',
            job.location.name if job.location else ''
        ]
        
        return ' '.join(filter(None, text_parts))
    
    def _find_similar_users(self, job_seeker, limit=10):
        """Find users with similar profiles"""
        try:
            # Find users with similar skills, experience level, and preferences
            similar_users = JobSeekerProfile.objects.exclude(id=job_seeker.id)
            
            if job_seeker.skills:
                user_skills = set(skill.strip().lower() for skill in job_seeker.skills.split(','))
                similar_users = similar_users.filter(skills__isnull=False)
                
                # Calculate skill similarity (simplified)
                similar_users_list = []
                for user in similar_users:
                    if user.skills:
                        other_skills = set(skill.strip().lower() for skill in user.skills.split(','))
                        similarity = len(user_skills.intersection(other_skills)) / len(user_skills.union(other_skills))
                        if similarity > 0.2:  # At least 20% skill overlap
                            similar_users_list.append(user)
                
                return similar_users_list[:limit]
            
            # Fallback to experience level similarity
            if job_seeker.experience_level:
                similar_users = similar_users.filter(experience_level=job_seeker.experience_level)
            
            return list(similar_users[:limit])
            
        except Exception as e:
            print(f"Similar users error: {e}")
            return []
    
    def get_job_match_score(self, job, job_seeker):
        """Calculate match score between a job and job seeker"""
        try:
            score = 0
            max_score = 100
            
            # Skills matching (40% weight)
            if job_seeker.skills and job.requirements:
                user_skills = set(skill.strip().lower() for skill in job_seeker.skills.split(','))
                job_requirements = job.requirements.lower()
                
                skill_matches = sum(1 for skill in user_skills if skill in job_requirements)
                skill_score = (skill_matches / len(user_skills)) * 40 if user_skills else 0
                score += skill_score
            
            # Experience level matching (20% weight)
            if job_seeker.experience_level and job.experience_level:
                if job_seeker.experience_level == job.experience_level:
                    score += 20
                elif self._experience_level_compatible(job_seeker.experience_level, job.experience_level):
                    score += 10
            
            # Location preference (15% weight)
            if job_seeker.preferred_location and job.location:
                if job_seeker.preferred_location.lower() in job.location.name.lower():
                    score += 15
                elif job.remote_work:
                    score += 10
            
            # Job title preference (15% weight)
            if job_seeker.preferred_job_title and job.title:
                if job_seeker.preferred_job_title.lower() in job.title.lower():
                    score += 15
            
            # Salary expectations (10% weight)
            if job_seeker.expected_salary and job.salary_max:
                if job_seeker.expected_salary <= job.salary_max:
                    score += 10
                elif job_seeker.expected_salary <= job.salary_max * 1.2:  # Within 20%
                    score += 5
            
            return min(score, max_score)
            
        except Exception as e:
            print(f"Match score error: {e}")
            return 0
    
    def _experience_level_compatible(self, user_level, job_level):
        """Check if experience levels are compatible"""
        level_hierarchy = {
            'entry': 1,
            'junior': 2,
            'mid': 3,
            'senior': 4,
            'lead': 5,
            'executive': 6
        }
        
        user_rank = level_hierarchy.get(user_level.lower(), 3)
        job_rank = level_hierarchy.get(job_level.lower(), 3)
        
        # Allow one level difference
        return abs(user_rank - job_rank) <= 1


# Global instance
recommendation_engine = JobRecommendationEngine()
