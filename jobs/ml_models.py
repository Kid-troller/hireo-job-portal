"""
Advanced ML Models for Job Recommendation System
Implements collaborative filtering, content-based filtering, and hybrid models
"""

# Optional ML dependencies with graceful fallbacks
try:
    import numpy as np
    import pandas as pd
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.decomposition import TruncatedSVD
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler, LabelEncoder
    import joblib
    import pickle
    ML_AVAILABLE = True
except ImportError as e:
    ML_AVAILABLE = False
    print(f"ML libraries not available: {e}")
    # Create dummy classes for graceful fallback
    class DummyModel:
        def __init__(self, *args, **kwargs):
            pass
        def fit(self, *args, **kwargs):
            return False
        def predict(self, *args, **kwargs):
            return [0.5]
        def predict_proba(self, *args, **kwargs):
            return [[0.5, 0.5]]
    
    TfidfVectorizer = DummyModel
    TruncatedSVD = DummyModel
    RandomForestRegressor = DummyModel
    GradientBoostingRegressor = DummyModel
    StandardScaler = DummyModel
    LabelEncoder = DummyModel
from datetime import datetime, timedelta
from django.db.models import Q, Count, Avg, F
from django.utils import timezone
from django.core.cache import cache
import logging

from .models import JobPost, JobCategory, JobLocation
from accounts.models import JobSeekerProfile, UserProfile
from applications.models import Application

logger = logging.getLogger(__name__)

class CollaborativeFilteringModel:
    """Collaborative Filtering using Matrix Factorization"""
    
    def __init__(self, n_components=50, random_state=42):
        self.n_components = n_components
        self.random_state = random_state
        self.svd = TruncatedSVD(n_components=n_components, random_state=random_state)
        self.user_encoder = LabelEncoder()
        self.job_encoder = LabelEncoder()
        self.scaler = StandardScaler()
        self.is_fitted = False
        
    def prepare_interaction_matrix(self):
        """Prepare user-job interaction matrix from application data"""
        try:
            # Get interactions (applications, saves, views)
            applications = Application.objects.select_related('applicant', 'job').all()
            
            interactions = []
            for app in applications:
                user_id = app.applicant.user_profile.user.id
                job_id = app.job.id
                
                # Score based on interaction type
                if app.status in ['hired', 'offered']:
                    score = 5.0
                elif app.status == 'interviewing':
                    score = 4.0
                elif app.status == 'shortlisted':
                    score = 3.0
                elif app.status == 'reviewing':
                    score = 2.0
                else:
                    score = 1.0
                    
                interactions.append({
                    'user_id': user_id,
                    'job_id': job_id,
                    'score': score,
                    'timestamp': app.applied_at
                })
            
            if not interactions:
                return None
                
            df = pd.DataFrame(interactions)
            
            # Create pivot table
            interaction_matrix = df.pivot_table(
                index='user_id', 
                columns='job_id', 
                values='score', 
                fill_value=0
            )
            
            return interaction_matrix
            
        except Exception as e:
            logger.error(f"Error preparing interaction matrix: {e}")
            return None
    
    def fit(self, interaction_matrix=None):
        """Train the collaborative filtering model"""
        try:
            if interaction_matrix is None:
                interaction_matrix = self.prepare_interaction_matrix()
                
            if interaction_matrix is None or interaction_matrix.empty:
                logger.warning("No interaction data available for collaborative filtering")
                return False
            
            # Encode users and jobs
            users = interaction_matrix.index.tolist()
            jobs = interaction_matrix.columns.tolist()
            
            self.user_encoder.fit(users)
            self.job_encoder.fit(jobs)
            
            # Apply SVD
            matrix_scaled = self.scaler.fit_transform(interaction_matrix.values)
            self.user_factors = self.svd.fit_transform(matrix_scaled)
            self.job_factors = self.svd.components_.T
            
            self.is_fitted = True
            logger.info(f"Collaborative filtering model trained with {len(users)} users and {len(jobs)} jobs")
            return True
            
        except Exception as e:
            logger.error(f"Error training collaborative filtering model: {e}")
            return False
    
    def predict_user_job_score(self, user_id, job_id):
        """Predict score for user-job pair"""
        if not self.is_fitted:
            return 0.5  # Default score
            
        try:
            user_idx = self.user_encoder.transform([user_id])[0]
            job_idx = self.job_encoder.transform([job_id])[0]
            
            score = np.dot(self.user_factors[user_idx], self.job_factors[job_idx])
            return max(0, min(1, score))  # Normalize to 0-1
            
        except (ValueError, IndexError):
            return 0.5  # Default for unseen users/jobs
    
    def get_user_recommendations(self, user_id, n_recommendations=10):
        """Get job recommendations for a user"""
        if not self.is_fitted:
            return []
            
        try:
            user_idx = self.user_encoder.transform([user_id])[0]
            user_vector = self.user_factors[user_idx]
            
            # Calculate scores for all jobs
            scores = np.dot(user_vector, self.job_factors.T)
            
            # Get top recommendations
            top_indices = np.argsort(scores)[::-1][:n_recommendations]
            job_ids = self.job_encoder.inverse_transform(top_indices)
            
            recommendations = []
            for i, job_id in enumerate(job_ids):
                recommendations.append({
                    'job_id': job_id,
                    'score': scores[top_indices[i]],
                    'rank': i + 1
                })
            
            return recommendations
            
        except (ValueError, IndexError):
            return []

class ContentBasedModel:
    """Content-based filtering using job and user features"""
    
    def __init__(self):
        self.job_vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2),
            lowercase=True
        )
        self.user_vectorizer = TfidfVectorizer(
            max_features=500,
            stop_words='english',
            ngram_range=(1, 2),
            lowercase=True
        )
        self.job_vectors = None
        self.user_vectors = None
        self.job_ids = []
        self.user_ids = []
        self.is_fitted = False
    
    def extract_job_features(self, job):
        """Extract textual features from job posting"""
        features = []
        
        if job.title:
            features.append(job.title)
        if job.description:
            features.append(job.description)
        if job.requirements:
            features.append(job.requirements)
        if job.required_skills:
            features.append(job.required_skills)
        if job.category:
            features.append(job.category.name)
        if job.location:
            features.append(f"{job.location.city} {job.location.state}")
        
        return ' '.join(features)
    
    def extract_user_features(self, user_profile):
        """Extract textual features from user profile"""
        features = []
        
        try:
            job_seeker = JobSeekerProfile.objects.get(user_profile=user_profile)
            
            if job_seeker.skills:
                features.append(job_seeker.skills)
            if job_seeker.preferred_job_title:
                features.append(job_seeker.preferred_job_title)
            if job_seeker.bio:
                features.append(job_seeker.bio)
            if job_seeker.education_level:
                features.append(job_seeker.education_level)
            
            # Add education and experience
            for education in job_seeker.resumeeducation_set.all():
                features.extend([education.degree, education.field_of_study])
            
            for experience in job_seeker.resumeexperience_set.all():
                features.extend([experience.job_title, experience.description])
                
        except JobSeekerProfile.DoesNotExist:
            pass
        
        return ' '.join(features) if features else 'general'
    
    def fit(self):
        """Train the content-based model"""
        try:
            # Get active jobs
            jobs = JobPost.objects.filter(status='active').select_related('category', 'location', 'company')
            job_texts = []
            job_ids = []
            
            for job in jobs:
                job_text = self.extract_job_features(job)
                job_texts.append(job_text)
                job_ids.append(job.id)
            
            if not job_texts:
                logger.warning("No jobs available for content-based model")
                return False
            
            # Vectorize job descriptions
            self.job_vectors = self.job_vectorizer.fit_transform(job_texts)
            self.job_ids = job_ids
            
            # Get user profiles
            user_profiles = UserProfile.objects.filter(user_type='jobseeker')
            user_texts = []
            user_ids = []
            
            for profile in user_profiles:
                user_text = self.extract_user_features(profile)
                user_texts.append(user_text)
                user_ids.append(profile.user.id)
            
            if user_texts:
                self.user_vectors = self.user_vectorizer.fit_transform(user_texts)
                self.user_ids = user_ids
            
            self.is_fitted = True
            logger.info(f"Content-based model trained with {len(job_ids)} jobs and {len(user_ids)} users")
            return True
            
        except Exception as e:
            logger.error(f"Error training content-based model: {e}")
            return False
    
    def get_user_job_similarity(self, user_id, job_id):
        """Calculate similarity between user and job"""
        if not self.is_fitted:
            return 0.5
            
        try:
            user_idx = self.user_ids.index(user_id)
            job_idx = self.job_ids.index(job_id)
            
            user_vector = self.user_vectors[user_idx]
            job_vector = self.job_vectors[job_idx]
            
            # Transform user vector to job vector space
            user_features = self.user_vectorizer.inverse_transform(user_vector)[0]
            user_text = ' '.join(user_features)
            user_in_job_space = self.job_vectorizer.transform([user_text])
            
            similarity = cosine_similarity(user_in_job_space, job_vector)[0][0]
            return max(0, similarity)
            
        except (ValueError, IndexError):
            return 0.5
    
    def get_user_recommendations(self, user_id, n_recommendations=10):
        """Get content-based recommendations for user"""
        if not self.is_fitted:
            return []
            
        try:
            user_idx = self.user_ids.index(user_id)
            user_vector = self.user_vectors[user_idx]
            
            # Transform to job space and calculate similarities
            user_features = self.user_vectorizer.inverse_transform(user_vector)[0]
            user_text = ' '.join(user_features)
            user_in_job_space = self.job_vectorizer.transform([user_text])
            
            similarities = cosine_similarity(user_in_job_space, self.job_vectors)[0]
            
            # Get top recommendations
            top_indices = np.argsort(similarities)[::-1][:n_recommendations]
            
            recommendations = []
            for i, idx in enumerate(top_indices):
                recommendations.append({
                    'job_id': self.job_ids[idx],
                    'score': similarities[idx],
                    'rank': i + 1
                })
            
            return recommendations
            
        except (ValueError, IndexError):
            return []

class HybridRecommendationModel:
    """Hybrid model combining collaborative and content-based filtering"""
    
    def __init__(self, collaborative_weight=0.6, content_weight=0.4):
        self.collaborative_model = CollaborativeFilteringModel()
        self.content_model = ContentBasedModel()
        self.collaborative_weight = collaborative_weight
        self.content_weight = content_weight
        self.is_fitted = False
    
    def fit(self):
        """Train both models"""
        try:
            collab_success = self.collaborative_model.fit()
            content_success = self.content_model.fit()
            
            if collab_success or content_success:
                self.is_fitted = True
                logger.info("Hybrid recommendation model trained successfully")
                return True
            else:
                logger.error("Failed to train hybrid model - both sub-models failed")
                return False
                
        except Exception as e:
            logger.error(f"Error training hybrid model: {e}")
            return False
    
    def get_user_recommendations(self, user_id, n_recommendations=10):
        """Get hybrid recommendations combining both models"""
        if not self.is_fitted:
            return []
        
        try:
            # Get recommendations from both models
            collab_recs = self.collaborative_model.get_user_recommendations(user_id, n_recommendations * 2)
            content_recs = self.content_model.get_user_recommendations(user_id, n_recommendations * 2)
            
            # Combine scores
            combined_scores = {}
            
            # Add collaborative filtering scores
            for rec in collab_recs:
                job_id = rec['job_id']
                combined_scores[job_id] = rec['score'] * self.collaborative_weight
            
            # Add content-based scores
            for rec in content_recs:
                job_id = rec['job_id']
                if job_id in combined_scores:
                    combined_scores[job_id] += rec['score'] * self.content_weight
                else:
                    combined_scores[job_id] = rec['score'] * self.content_weight
            
            # Sort by combined score
            sorted_jobs = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)
            
            # Format recommendations
            recommendations = []
            for i, (job_id, score) in enumerate(sorted_jobs[:n_recommendations]):
                recommendations.append({
                    'job_id': job_id,
                    'score': score,
                    'rank': i + 1
                })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting hybrid recommendations: {e}")
            return []
    
    def predict_user_job_score(self, user_id, job_id):
        """Predict hybrid score for user-job pair"""
        if not self.is_fitted:
            return 0.5
        
        try:
            collab_score = self.collaborative_model.predict_user_job_score(user_id, job_id)
            content_score = self.content_model.get_user_job_similarity(user_id, job_id)
            
            hybrid_score = (collab_score * self.collaborative_weight + 
                          content_score * self.content_weight)
            
            return hybrid_score
            
        except Exception as e:
            logger.error(f"Error predicting hybrid score: {e}")
            return 0.5

class LearningToRankModel:
    """Learning-to-rank model for job search results"""
    
    def __init__(self):
        self.model = GradientBoostingRegressor(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=6,
            random_state=42
        )
        self.feature_scaler = StandardScaler()
        self.is_fitted = False
    
    def extract_ranking_features(self, user_id, job):
        """Extract features for ranking"""
        features = []
        
        try:
            user_profile = UserProfile.objects.get(user_id=user_id)
            job_seeker = JobSeekerProfile.objects.get(user_profile=user_profile)
            
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
            
            # User-job compatibility features
            skill_match = 0
            if job_seeker.skills and job.required_skills:
                user_skills = set(s.strip().lower() for s in job_seeker.skills.split(','))
                job_skills = set(s.strip().lower() for s in job.required_skills.split(','))
                skill_match = len(user_skills.intersection(job_skills)) / len(job_skills) if job_skills else 0
            
            exp_match = 0
            if job_seeker.experience_years and job.min_experience:
                exp_diff = abs(job_seeker.experience_years - job.min_experience)
                exp_match = max(0, 1 - exp_diff / 10)  # Normalize
            
            salary_match = 0
            if job_seeker.expected_salary and job.max_salary:
                salary_match = 1 if job_seeker.expected_salary <= job.max_salary else 0
            
            features.extend([skill_match, exp_match, salary_match])
            
            # Category and location features
            features.extend([
                job.category.id if job.category else 0,
                job.location.id if job.location else 0,
            ])
            
        except (UserProfile.DoesNotExist, JobSeekerProfile.DoesNotExist):
            # Default features for non-job seekers
            features = [0] * 13
        
        return np.array(features)
    
    def prepare_training_data(self):
        """Prepare training data from user interactions"""
        try:
            applications = Application.objects.select_related(
                'applicant__user_profile__user', 'job'
            ).all()
            
            X, y = [], []
            
            for app in applications:
                user_id = app.applicant.user_profile.user.id
                job = app.job
                
                features = self.extract_ranking_features(user_id, job)
                
                # Target score based on application outcome
                if app.status in ['hired', 'offered']:
                    score = 1.0
                elif app.status == 'interviewing':
                    score = 0.8
                elif app.status == 'shortlisted':
                    score = 0.6
                elif app.status == 'reviewing':
                    score = 0.4
                else:
                    score = 0.2
                
                X.append(features)
                y.append(score)
            
            return np.array(X), np.array(y)
            
        except Exception as e:
            logger.error(f"Error preparing ranking training data: {e}")
            return None, None
    
    def fit(self):
        """Train the learning-to-rank model"""
        try:
            X, y = self.prepare_training_data()
            
            if X is None or len(X) == 0:
                logger.warning("No training data available for ranking model")
                return False
            
            # Scale features
            X_scaled = self.feature_scaler.fit_transform(X)
            
            # Train model
            self.model.fit(X_scaled, y)
            self.is_fitted = True
            
            logger.info(f"Learning-to-rank model trained with {len(X)} samples")
            return True
            
        except Exception as e:
            logger.error(f"Error training ranking model: {e}")
            return False
    
    def predict_relevance_score(self, user_id, job):
        """Predict relevance score for user-job pair"""
        if not self.is_fitted:
            return 0.5
        
        try:
            features = self.extract_ranking_features(user_id, job)
            features_scaled = self.feature_scaler.transform([features])
            score = self.model.predict(features_scaled)[0]
            
            return max(0, min(1, score))  # Normalize to 0-1
            
        except Exception as e:
            logger.error(f"Error predicting relevance score: {e}")
            return 0.5
    
    def rank_jobs(self, user_id, jobs):
        """Rank jobs for a user"""
        if not self.is_fitted:
            return jobs
        
        try:
            job_scores = []
            for job in jobs:
                score = self.predict_relevance_score(user_id, job)
                job_scores.append((job, score))
            
            # Sort by score descending
            job_scores.sort(key=lambda x: x[1], reverse=True)
            
            return [job for job, score in job_scores]
            
        except Exception as e:
            logger.error(f"Error ranking jobs: {e}")
            return jobs

# Global model instances
hybrid_model = HybridRecommendationModel()
ranking_model = LearningToRankModel()

def train_models():
    """Train all ML models"""
    if not ML_AVAILABLE:
        logger.warning("ML libraries not available, skipping model training")
        return False
        
    try:
        logger.info("Starting ML model training...")
        
        # Train hybrid recommendation model
        hybrid_success = hybrid_model.fit()
        
        # Train ranking model
        ranking_success = ranking_model.fit()
        
        if hybrid_success or ranking_success:
            logger.info("ML model training completed successfully")
            return True
        else:
            logger.error("All ML model training failed")
            return False
            
    except Exception as e:
        logger.error(f"Error in model training: {e}")
        return False

def get_ml_recommendations(user_id, n_recommendations=10):
    """Get ML-powered job recommendations"""
    try:
        if hybrid_model.is_fitted:
            return hybrid_model.get_user_recommendations(user_id, n_recommendations)
        else:
            logger.warning("Hybrid model not fitted, returning empty recommendations")
            return []
    except Exception as e:
        logger.error(f"Error getting ML recommendations: {e}")
        return []

def rank_search_results(user_id, jobs):
    """Rank search results using ML"""
    try:
        if ranking_model.is_fitted:
            return ranking_model.rank_jobs(user_id, jobs)
        else:
            return jobs
    except Exception as e:
        logger.error(f"Error ranking search results: {e}")
        return jobs
