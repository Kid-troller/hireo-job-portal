"""
AI/ML Integration Module for Job Search Platform
Combines all AI/ML components for comprehensive intelligent job matching
"""

import logging
from typing import List, Dict, Optional, Tuple
from django.db.models import Q, QuerySet
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta

from .models import JobPost, JobCategory, JobLocation
from accounts.models import JobSeekerProfile, UserProfile
from applications.models import Application

# Import AI/ML modules
from .ai_engine import job_ai_engine
from .ml_models import (
    hybrid_model, ranking_model, train_models, 
    get_ml_recommendations, rank_search_results
)
from .semantic_search import (
    semantic_engine, query_expander, filter_suggester,
    initialize_semantic_search, perform_semantic_search,
    get_smart_filter_suggestions
)
from .candidate_ranking import (
    candidate_ranker, talent_recommender, train_candidate_models,
    get_ranked_candidates_for_job
)

logger = logging.getLogger(__name__)

class IntelligentJobSearchEngine:
    """Main AI/ML powered job search engine"""
    
    def __init__(self):
        self.is_initialized = False
        self.last_training_time = None
        self.cache_timeout = 3600  # 1 hour
    
    def initialize(self):
        """Initialize all AI/ML components"""
        try:
            logger.info("Initializing AI/ML job search engine...")
            
            # Initialize semantic search
            semantic_success = initialize_semantic_search()
            
            # Train ML models
            ml_success = train_models()
            
            # Train candidate models
            candidate_success = train_candidate_models()
            
            if semantic_success or ml_success or candidate_success:
                self.is_initialized = True
                self.last_training_time = timezone.now()
                logger.info("AI/ML job search engine initialized successfully")
                return True
            else:
                logger.error("Failed to initialize AI/ML components")
                return False
                
        except Exception as e:
            logger.error(f"Error initializing AI/ML engine: {e}")
            return False
    
    def intelligent_job_search(self, 
                             query: str = "",
                             user_id: Optional[int] = None,
                             filters: Dict = None,
                             page_size: int = 20,
                             use_semantic: bool = True,
                             use_ml_ranking: bool = True) -> Dict:
        """
        Perform intelligent job search combining multiple AI/ML techniques
        """
        try:
            results = {
                'jobs': [],
                'total_count': 0,
                'semantic_results': [],
                'ml_recommendations': [],
                'smart_suggestions': {},
                'market_insights': {},
                'personalized_data': {}
            }
            
            # Start with base queryset
            jobs_queryset = JobPost.objects.filter(status='active').select_related(
                'category', 'location', 'company'
            )
            
            # Apply basic filters
            if filters:
                jobs_queryset = self._apply_filters(jobs_queryset, filters)
            
            # Semantic search if query provided
            semantic_job_ids = []
            if query and use_semantic:
                semantic_job_ids = perform_semantic_search(query, top_k=page_size * 2)
                results['semantic_results'] = semantic_job_ids
                
                if semantic_job_ids:
                    # Filter by semantic results
                    jobs_queryset = jobs_queryset.filter(id__in=semantic_job_ids)
            
            # Get jobs list
            jobs_list = list(jobs_queryset[:page_size * 2])  # Get more for ranking
            
            # ML-based ranking if user authenticated
            if user_id and use_ml_ranking and jobs_list:
                ranked_jobs = rank_search_results(user_id, jobs_list)
                jobs_list = ranked_jobs[:page_size]
            else:
                jobs_list = jobs_list[:page_size]
            
            # Get ML recommendations for user
            if user_id:
                ml_recommendations = get_ml_recommendations(user_id, 10)
                results['ml_recommendations'] = ml_recommendations
                
                # Get personalized data
                results['personalized_data'] = self._get_personalized_data(user_id)
            
            # Get smart filter suggestions
            if query:
                smart_suggestions = get_smart_filter_suggestions(query)
                results['smart_suggestions'] = smart_suggestions
            
            # Get market insights
            results['market_insights'] = job_ai_engine.analyze_job_market_trends()
            
            # Calculate match scores for authenticated users
            if user_id:
                for job in jobs_list:
                    try:
                        user_profile = UserProfile.objects.get(user_id=user_id)
                        match_score = job_ai_engine.get_job_match_score(job, user_profile)
                        job.ai_match_score = match_score
                    except:
                        job.ai_match_score = 0
            
            results['jobs'] = jobs_list
            results['total_count'] = len(jobs_list)
            
            return results
            
        except Exception as e:
            logger.error(f"Error in intelligent job search: {e}")
            return {
                'jobs': [],
                'total_count': 0,
                'error': str(e)
            }
    
    def _apply_filters(self, queryset: QuerySet, filters: Dict) -> QuerySet:
        """Apply search filters to queryset"""
        try:
            if filters.get('category'):
                queryset = queryset.filter(category_id=filters['category'])
            
            if filters.get('location'):
                queryset = queryset.filter(
                    Q(location__city__icontains=filters['location']) |
                    Q(location__state__icontains=filters['location'])
                )
            
            if filters.get('employment_type'):
                queryset = queryset.filter(employment_type=filters['employment_type'])
            
            if filters.get('experience_level'):
                queryset = queryset.filter(experience_level=filters['experience_level'])
            
            if filters.get('is_remote'):
                queryset = queryset.filter(is_remote=True)
            
            if filters.get('salary_min'):
                queryset = queryset.filter(min_salary__gte=filters['salary_min'])
            
            if filters.get('salary_max'):
                queryset = queryset.filter(max_salary__lte=filters['salary_max'])
            
            if filters.get('date_posted'):
                days = int(filters['date_posted'])
                cutoff_date = timezone.now() - timedelta(days=days)
                queryset = queryset.filter(created_at__gte=cutoff_date)
            
            return queryset
            
        except Exception as e:
            logger.error(f"Error applying filters: {e}")
            return queryset
    
    def _get_personalized_data(self, user_id: int) -> Dict:
        """Get personalized data for user"""
        try:
            cache_key = f"personalized_data_{user_id}"
            cached_data = cache.get(cache_key)
            
            if cached_data:
                return cached_data
            
            personalized_data = {
                'recommended_categories': [],
                'skill_based_suggestions': [],
                'salary_insights': {},
                'application_history': {}
            }
            
            try:
                user_profile = UserProfile.objects.get(user_id=user_id)
                job_seeker = JobSeekerProfile.objects.get(user_profile=user_profile)
                
                # Get recommended categories based on skills
                if job_seeker.skills:
                    user_skills = [s.strip().lower() for s in job_seeker.skills.split(',')]
                    
                    # Find categories with matching skills
                    matching_categories = JobCategory.objects.filter(
                        jobpost__required_skills__iregex=r'\b(' + '|'.join(user_skills) + r')\b'
                    ).distinct()[:5]
                    
                    personalized_data['recommended_categories'] = [
                        {'id': cat.id, 'name': cat.name} for cat in matching_categories
                    ]
                
                # Get application history insights
                applications = Application.objects.filter(
                    applicant=job_seeker
                ).select_related('job__category')
                
                if applications.exists():
                    # Most applied categories
                    category_counts = {}
                    for app in applications:
                        if app.job.category:
                            cat_name = app.job.category.name
                            category_counts[cat_name] = category_counts.get(cat_name, 0) + 1
                    
                    personalized_data['application_history'] = {
                        'total_applications': applications.count(),
                        'favorite_categories': sorted(
                            category_counts.items(), 
                            key=lambda x: x[1], 
                            reverse=True
                        )[:3]
                    }
                
                # Cache the data
                cache.set(cache_key, personalized_data, self.cache_timeout)
                
            except (UserProfile.DoesNotExist, JobSeekerProfile.DoesNotExist):
                pass
            
            return personalized_data
            
        except Exception as e:
            logger.error(f"Error getting personalized data: {e}")
            return {}
    
    def get_job_recommendations_for_user(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Get comprehensive job recommendations for user"""
        try:
            recommendations = []
            
            # Get ML-based recommendations
            ml_recs = get_ml_recommendations(user_id, limit)
            
            for rec in ml_recs:
                try:
                    job = JobPost.objects.get(id=rec['job_id'])
                    user_profile = UserProfile.objects.get(user_id=user_id)
                    
                    # Calculate additional scores
                    match_score = job_ai_engine.get_job_match_score(job, user_profile)
                    
                    recommendations.append({
                        'job': job,
                        'ml_score': rec['score'],
                        'match_score': match_score,
                        'combined_score': (rec['score'] * 0.6 + match_score * 0.4),
                        'recommendation_type': 'ml_based'
                    })
                except JobPost.DoesNotExist:
                    continue
            
            # Sort by combined score
            recommendations.sort(key=lambda x: x['combined_score'], reverse=True)
            
            return recommendations[:limit]
            
        except Exception as e:
            logger.error(f"Error getting job recommendations: {e}")
            return []
    
    def get_candidate_recommendations_for_job(self, job_id: int, limit: int = 20) -> List[Dict]:
        """Get AI-powered candidate recommendations for employers"""
        try:
            return get_ranked_candidates_for_job(job_id, limit)
        except Exception as e:
            logger.error(f"Error getting candidate recommendations: {e}")
            return []
    
    def analyze_user_job_fit(self, user_id: int, job_id: int) -> Dict:
        """Comprehensive analysis of user-job fit"""
        try:
            analysis = {
                'overall_score': 0,
                'skill_match': 0,
                'experience_match': 0,
                'salary_match': 0,
                'location_match': 0,
                'recommendations': [],
                'missing_skills': [],
                'strengths': []
            }
            
            job = JobPost.objects.get(id=job_id)
            user_profile = UserProfile.objects.get(user_id=user_id)
            
            # Get AI match score
            overall_score = job_ai_engine.get_job_match_score(job, user_profile)
            analysis['overall_score'] = overall_score
            
            try:
                job_seeker = JobSeekerProfile.objects.get(user_profile=user_profile)
                
                # Skill analysis
                if job_seeker.skills and job.required_skills:
                    user_skills = set(s.strip().lower() for s in job_seeker.skills.split(','))
                    job_skills = set(s.strip().lower() for s in job.required_skills.split(','))
                    
                    matching_skills = user_skills.intersection(job_skills)
                    missing_skills = job_skills - user_skills
                    
                    analysis['skill_match'] = len(matching_skills) / len(job_skills) if job_skills else 0
                    analysis['missing_skills'] = list(missing_skills)
                    analysis['strengths'] = list(matching_skills)
                
                # Experience analysis
                if job_seeker.experience_years and job.min_experience:
                    exp_diff = job_seeker.experience_years - job.min_experience
                    if exp_diff >= 0:
                        analysis['experience_match'] = min(1.0, 1 - abs(exp_diff) / 10)
                    else:
                        analysis['experience_match'] = max(0, 0.5 + exp_diff / 10)
                
                # Salary analysis
                if job_seeker.expected_salary and job.max_salary:
                    if job_seeker.expected_salary <= job.max_salary:
                        analysis['salary_match'] = 1.0
                    else:
                        analysis['salary_match'] = job.max_salary / job_seeker.expected_salary
                
                # Generate recommendations
                if analysis['skill_match'] < 0.7:
                    analysis['recommendations'].append(
                        f"Consider learning: {', '.join(list(analysis['missing_skills'])[:3])}"
                    )
                
                if analysis['experience_match'] < 0.5:
                    analysis['recommendations'].append(
                        "Gain more relevant experience in this field"
                    )
                
            except JobSeekerProfile.DoesNotExist:
                pass
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing user-job fit: {e}")
            return {'error': str(e)}
    
    def retrain_models(self):
        """Retrain all ML models with latest data"""
        try:
            logger.info("Starting model retraining...")
            
            # Retrain job recommendation models
            ml_success = train_models()
            
            # Retrain candidate models
            candidate_success = train_candidate_models()
            
            # Rebuild semantic search index
            semantic_success = initialize_semantic_search()
            
            if ml_success or candidate_success or semantic_success:
                self.last_training_time = timezone.now()
                logger.info("Model retraining completed successfully")
                return True
            else:
                logger.error("Model retraining failed")
                return False
                
        except Exception as e:
            logger.error(f"Error retraining models: {e}")
            return False
    
    def should_retrain(self) -> bool:
        """Check if models should be retrained"""
        if not self.last_training_time:
            return True
        
        # Retrain weekly
        time_since_training = timezone.now() - self.last_training_time
        return time_since_training > timedelta(days=7)

# Global intelligent search engine instance
intelligent_search_engine = IntelligentJobSearchEngine()

def initialize_ai_ml_system():
    """Initialize the complete AI/ML system"""
    return intelligent_search_engine.initialize()

def perform_intelligent_search(query: str = "", 
                             user_id: Optional[int] = None,
                             filters: Dict = None,
                             **kwargs) -> Dict:
    """Perform intelligent job search"""
    if not intelligent_search_engine.is_initialized:
        intelligent_search_engine.initialize()
    
    return intelligent_search_engine.intelligent_job_search(
        query=query,
        user_id=user_id,
        filters=filters or {},
        **kwargs
    )

def get_intelligent_recommendations(user_id: int, limit: int = 10) -> List[Dict]:
    """Get intelligent job recommendations"""
    if not intelligent_search_engine.is_initialized:
        intelligent_search_engine.initialize()
    
    return intelligent_search_engine.get_job_recommendations_for_user(user_id, limit)

def get_candidate_recommendations(job_id: int, limit: int = 20) -> List[Dict]:
    """Get intelligent candidate recommendations"""
    if not intelligent_search_engine.is_initialized:
        intelligent_search_engine.initialize()
    
    return intelligent_search_engine.get_candidate_recommendations_for_job(job_id, limit)

def analyze_job_fit(user_id: int, job_id: int) -> Dict:
    """Analyze user-job compatibility"""
    if not intelligent_search_engine.is_initialized:
        intelligent_search_engine.initialize()
    
    return intelligent_search_engine.analyze_user_job_fit(user_id, job_id)

def schedule_model_retraining():
    """Schedule model retraining if needed"""
    if intelligent_search_engine.should_retrain():
        return intelligent_search_engine.retrain_models()
    return False
