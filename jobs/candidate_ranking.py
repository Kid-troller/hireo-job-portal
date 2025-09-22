"""
Candidate Ranking and Recommendation System for Employers
Implements ML models to rank and recommend candidates for job positions
"""

# Optional ML dependencies with graceful fallbacks
try:
    import numpy as np
    import pandas as pd
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
    from sklearn.preprocessing import StandardScaler, LabelEncoder
    from sklearn.model_selection import train_test_split
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.feature_extraction.text import TfidfVectorizer
    import joblib
    ML_AVAILABLE = True
except ImportError as e:
    ML_AVAILABLE = False
    print(f"ML libraries not available for candidate ranking: {e}")
    # Create dummy classes
    class DummyModel:
        def __init__(self, *args, **kwargs):
            pass
        def fit(self, *args, **kwargs):
            return False
        def predict(self, *args, **kwargs):
            return [0.5]
        def predict_proba(self, *args, **kwargs):
            return [[0.5, 0.5]]
        def transform(self, *args, **kwargs):
            return [[0.5]]
    
    RandomForestClassifier = DummyModel
    GradientBoostingRegressor = DummyModel
    StandardScaler = DummyModel
    TfidfVectorizer = DummyModel
from datetime import datetime, timedelta
from django.db.models import Q, Count, Avg, F
from django.utils import timezone
from django.core.cache import cache
import logging

from .models import JobPost
from accounts.models import JobSeekerProfile, UserProfile
from applications.models import Application

logger = logging.getLogger(__name__)

class CandidateRankingModel:
    """ML model to rank candidates for job positions"""
    
    def __init__(self):
        self.ranking_model = GradientBoostingRegressor(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=6,
            random_state=42
        )
        self.acceptance_model = RandomForestClassifier(
            n_estimators=100,
            random_state=42
        )
        self.feature_scaler = StandardScaler()
        self.is_fitted = False
    
    def extract_candidate_features(self, job_seeker: JobSeekerProfile, job: JobPost) -> np.array:
        """Extract features for candidate-job pair"""
        features = []
        
        try:
            # Basic candidate features
            features.extend([
                job_seeker.experience_years or 0,
                1 if job_seeker.is_available_for_work else 0,
                len(job_seeker.skills.split(',')) if job_seeker.skills else 0,
                job_seeker.expected_salary or 0,
            ])
            
            # Education level encoding
            education_levels = {
                'high_school': 1,
                'associate': 2,
                'bachelor': 3,
                'master': 4,
                'phd': 5
            }
            education_score = education_levels.get(job_seeker.education_level, 0)
            features.append(education_score)
            
            # Job compatibility features
            skill_match_score = self.calculate_skill_match(job_seeker, job)
            experience_match_score = self.calculate_experience_match(job_seeker, job)
            salary_match_score = self.calculate_salary_match(job_seeker, job)
            location_match_score = self.calculate_location_match(job_seeker, job)
            
            features.extend([
                skill_match_score,
                experience_match_score,
                salary_match_score,
                location_match_score
            ])
            
            # Job features
            features.extend([
                job.views_count,
                job.applications_count,
                (timezone.now() - job.created_at).days,
                1 if job.is_featured else 0,
                1 if job.is_remote else 0,
                job.remote_percentage,
                job.min_salary or 0,
                job.max_salary or 0,
            ])
            
            # Candidate activity features
            total_applications = Application.objects.filter(applicant=job_seeker).count()
            recent_applications = Application.objects.filter(
                applicant=job_seeker,
                applied_at__gte=timezone.now() - timedelta(days=30)
            ).count()
            
            success_rate = 0
            if total_applications > 0:
                successful_apps = Application.objects.filter(
                    applicant=job_seeker,
                    status__in=['hired', 'offered', 'interviewing']
                ).count()
                success_rate = successful_apps / total_applications
            
            features.extend([
                total_applications,
                recent_applications,
                success_rate
            ])
            
        except Exception as e:
            logger.error(f"Error extracting candidate features: {e}")
            features = [0] * 20
        
        return np.array(features)
    
    def calculate_skill_match(self, job_seeker: JobSeekerProfile, job: JobPost) -> float:
        """Calculate skill match score between candidate and job"""
        if not job_seeker.skills or not job.required_skills:
            return 0.0
        
        try:
            candidate_skills = set(skill.strip().lower() for skill in job_seeker.skills.split(','))
            job_skills = set(skill.strip().lower() for skill in job.required_skills.split(','))
            
            if not job_skills:
                return 0.0
            
            intersection = candidate_skills.intersection(job_skills)
            return len(intersection) / len(job_skills)
            
        except Exception:
            return 0.0
    
    def calculate_experience_match(self, job_seeker: JobSeekerProfile, job: JobPost) -> float:
        """Calculate experience match score"""
        if not job_seeker.experience_years or not job.min_experience:
            return 0.5
        
        try:
            exp_diff = abs(job_seeker.experience_years - job.min_experience)
            return max(0, 1 - exp_diff / 10)
        except Exception:
            return 0.5
    
    def calculate_salary_match(self, job_seeker: JobSeekerProfile, job: JobPost) -> float:
        """Calculate salary expectation match"""
        if not job_seeker.expected_salary or not job.max_salary:
            return 0.5
        
        try:
            if job_seeker.expected_salary <= job.max_salary:
                return 1.0
            elif job_seeker.expected_salary <= job.max_salary * 1.2:
                return 0.7
            else:
                return 0.3
        except Exception:
            return 0.5
    
    def calculate_location_match(self, job_seeker: JobSeekerProfile, job: JobPost) -> float:
        """Calculate location preference match"""
        if job.is_remote:
            return 1.0
        
        if not job_seeker.preferred_location or not job.location:
            return 0.5
        
        try:
            if job_seeker.preferred_location.lower() in job.location.city.lower():
                return 1.0
            elif job_seeker.preferred_location.lower() in job.location.state.lower():
                return 0.7
            else:
                return 0.3
        except Exception:
            return 0.5
    
    def prepare_training_data(self):
        """Prepare training data from historical applications"""
        try:
            applications = Application.objects.select_related(
                'applicant', 'job'
            ).all()
            
            X, y_ranking, y_acceptance = [], [], []
            
            for app in applications:
                job_seeker = app.applicant
                job = app.job
                
                features = self.extract_candidate_features(job_seeker, job)
                
                # Ranking score based on application outcome
                if app.status == 'hired':
                    ranking_score = 1.0
                    accepted = 1
                elif app.status == 'offered':
                    ranking_score = 0.9
                    accepted = 1
                elif app.status == 'interviewing':
                    ranking_score = 0.7
                    accepted = 0
                elif app.status == 'shortlisted':
                    ranking_score = 0.5
                    accepted = 0
                elif app.status == 'reviewing':
                    ranking_score = 0.3
                    accepted = 0
                else:
                    ranking_score = 0.1
                    accepted = 0
                
                X.append(features)
                y_ranking.append(ranking_score)
                y_acceptance.append(accepted)
            
            return np.array(X), np.array(y_ranking), np.array(y_acceptance)
            
        except Exception as e:
            logger.error(f"Error preparing training data: {e}")
            return None, None, None
    
    def fit(self):
        """Train the candidate ranking models"""
        try:
            X, y_ranking, y_acceptance = self.prepare_training_data()
            
            if X is None or len(X) == 0:
                logger.warning("No training data available for candidate ranking")
                return False
            
            # Scale features
            X_scaled = self.feature_scaler.fit_transform(X)
            
            # Train ranking model
            self.ranking_model.fit(X_scaled, y_ranking)
            
            # Train acceptance prediction model
            self.acceptance_model.fit(X_scaled, y_acceptance)
            
            self.is_fitted = True
            logger.info(f"Candidate ranking models trained with {len(X)} samples")
            return True
            
        except Exception as e:
            logger.error(f"Error training candidate ranking models: {e}")
            return False
    
    def predict_candidate_score(self, job_seeker: JobSeekerProfile, job: JobPost) -> dict:
        """Predict candidate score and acceptance probability"""
        if not self.is_fitted:
            return {'ranking_score': 0.5, 'acceptance_probability': 0.5}
        
        try:
            features = self.extract_candidate_features(job_seeker, job)
            features_scaled = self.feature_scaler.transform([features])
            
            ranking_score = self.ranking_model.predict(features_scaled)[0]
            acceptance_prob = self.acceptance_model.predict_proba(features_scaled)[0][1]
            
            return {
                'ranking_score': max(0, min(1, ranking_score)),
                'acceptance_probability': acceptance_prob
            }
            
        except Exception as e:
            logger.error(f"Error predicting candidate score: {e}")
            return {'ranking_score': 0.5, 'acceptance_probability': 0.5}
    
    def rank_candidates_for_job(self, job: JobPost, candidate_limit: int = 50) -> list:
        """Rank candidates for a specific job"""
        if not self.is_fitted:
            return []
        
        try:
            # Get potential candidates (job seekers who haven't applied yet)
            applied_candidate_ids = Application.objects.filter(job=job).values_list(
                'applicant__user_profile__user_id', flat=True
            )
            
            potential_candidates = JobSeekerProfile.objects.filter(
                is_available_for_work=True
            ).exclude(
                user_profile__user_id__in=applied_candidate_ids
            ).select_related('user_profile__user')[:candidate_limit]
            
            candidate_scores = []
            
            for candidate in potential_candidates:
                scores = self.predict_candidate_score(candidate, job)
                candidate_scores.append({
                    'candidate': candidate,
                    'ranking_score': scores['ranking_score'],
                    'acceptance_probability': scores['acceptance_probability'],
                    'combined_score': scores['ranking_score'] * 0.7 + scores['acceptance_probability'] * 0.3
                })
            
            # Sort by combined score
            candidate_scores.sort(key=lambda x: x['combined_score'], reverse=True)
            
            return candidate_scores
            
        except Exception as e:
            logger.error(f"Error ranking candidates: {e}")
            return []

class TalentPoolRecommender:
    """Recommend candidates from talent pool even if they haven't applied"""
    
    def __init__(self):
        self.skill_vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2)
        )
        self.candidate_vectors = None
        self.candidate_profiles = []
        self.is_fitted = False
    
    def build_candidate_index(self):
        """Build searchable index of all candidates"""
        try:
            candidates = JobSeekerProfile.objects.filter(
                is_available_for_work=True
            ).select_related('user_profile__user')
            
            candidate_texts = []
            self.candidate_profiles = []
            
            for candidate in candidates:
                # Create searchable text from candidate profile
                text_parts = []
                
                if candidate.skills:
                    text_parts.append(candidate.skills)
                
                if candidate.bio:
                    text_parts.append(candidate.bio)
                
                if candidate.education_level:
                    text_parts.append(candidate.education_level)
                
                # Add education and experience details
                try:
                    for education in candidate.resumeeducation_set.all():
                        text_parts.extend([education.degree, education.field_of_study])
                    
                    for experience in candidate.resumeexperience_set.all():
                        text_parts.extend([experience.job_title, experience.description])
                except:
                    pass
                
                candidate_text = ' '.join(text_parts) if text_parts else 'general'
                candidate_texts.append(candidate_text)
                self.candidate_profiles.append(candidate)
            
            if candidate_texts:
                self.candidate_vectors = self.skill_vectorizer.fit_transform(candidate_texts)
                self.is_fitted = True
                logger.info(f"Built candidate index for {len(candidate_texts)} candidates")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error building candidate index: {e}")
            return False
    
    def find_candidates_for_job(self, job: JobPost, top_k: int = 20) -> list:
        """Find best candidates for a job from talent pool"""
        if not self.is_fitted:
            return []
        
        try:
            # Create job description text
            job_text_parts = []
            
            if job.title:
                job_text_parts.append(job.title)
            if job.required_skills:
                job_text_parts.append(job.required_skills)
            if job.description:
                job_text_parts.append(job.description)
            if job.requirements:
                job_text_parts.append(job.requirements)
            
            job_text = ' '.join(job_text_parts)
            
            # Vectorize job description
            job_vector = self.skill_vectorizer.transform([job_text])
            
            # Calculate similarities
            similarities = cosine_similarity(job_vector, self.candidate_vectors)[0]
            
            # Get top candidates
            top_indices = np.argsort(similarities)[::-1][:top_k]
            
            recommendations = []
            for i, idx in enumerate(top_indices):
                if similarities[idx] > 0.1:  # Minimum similarity threshold
                    recommendations.append({
                        'candidate': self.candidate_profiles[idx],
                        'similarity_score': float(similarities[idx]),
                        'rank': i + 1
                    })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error finding candidates for job: {e}")
            return []

# Global instances
candidate_ranker = CandidateRankingModel()
talent_recommender = TalentPoolRecommender()

def train_candidate_models():
    """Train all candidate-related models"""
    if not ML_AVAILABLE:
        logger.warning("ML libraries not available, skipping candidate model training")
        return False
        
    try:
        logger.info("Training candidate ranking models...")
        
        # Train candidate ranking model
        ranking_success = candidate_ranker.fit()
        
        # Build talent pool index
        talent_success = talent_recommender.build_candidate_index()
        
        if ranking_success or talent_success:
            logger.info("Candidate model training completed")
            return True
        else:
            logger.error("Candidate model training failed")
            return False
            
    except Exception as e:
        logger.error(f"Error training candidate models: {e}")
        return False

def get_ranked_candidates_for_job(job_id: int, limit: int = 20) -> list:
    """Get ranked candidates for a specific job"""
    try:
        job = JobPost.objects.get(id=job_id)
        
        # Get ML rankings if available
        if candidate_ranker.is_fitted:
            ml_candidates = candidate_ranker.rank_candidates_for_job(job, limit)
        else:
            ml_candidates = []
        
        # Get talent pool recommendations
        if talent_recommender.is_fitted:
            talent_candidates = talent_recommender.find_candidates_for_job(job, limit)
        else:
            talent_candidates = []
        
        # Combine and deduplicate
        all_candidates = {}
        
        # Add ML ranked candidates
        for candidate_data in ml_candidates:
            candidate_id = candidate_data['candidate'].id
            all_candidates[candidate_id] = {
                'candidate': candidate_data['candidate'],
                'ml_score': candidate_data['combined_score'],
                'similarity_score': 0,
                'source': 'ml_ranking'
            }
        
        # Add talent pool candidates
        for candidate_data in talent_candidates:
            candidate_id = candidate_data['candidate'].id
            if candidate_id in all_candidates:
                all_candidates[candidate_id]['similarity_score'] = candidate_data['similarity_score']
            else:
                all_candidates[candidate_id] = {
                    'candidate': candidate_data['candidate'],
                    'ml_score': 0,
                    'similarity_score': candidate_data['similarity_score'],
                    'source': 'talent_pool'
                }
        
        # Calculate final scores and sort
        final_candidates = []
        for candidate_data in all_candidates.values():
            # Combine ML score and similarity score
            final_score = (candidate_data['ml_score'] * 0.6 + 
                          candidate_data['similarity_score'] * 0.4)
            
            final_candidates.append({
                'candidate': candidate_data['candidate'],
                'final_score': final_score,
                'ml_score': candidate_data['ml_score'],
                'similarity_score': candidate_data['similarity_score'],
                'source': candidate_data['source']
            })
        
        # Sort by final score
        final_candidates.sort(key=lambda x: x['final_score'], reverse=True)
        
        return final_candidates[:limit]
        
    except Exception as e:
        logger.error(f"Error getting ranked candidates: {e}")
        return []
