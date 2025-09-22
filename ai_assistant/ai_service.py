"""
Core AI Service Engine for Hireo Job Portal
Provides reusable AI functionality across all pages
"""

import json
import random
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Q
from django.core.cache import cache

from .models import (
    AIInteraction, AIRecommendation, AIChatSession, 
    AISearchQuery, AIPersonalization, AIAnalytics
)

class AIService:
    """Main AI service class providing all AI functionality"""
    
    def __init__(self):
        self.cache_timeout = 300  # 5 minutes
        
    def get_session_id(self, request):
        """Get or create session ID for tracking"""
        if not request.session.session_key:
            request.session.create()
        return request.session.session_key
    
    def log_interaction(self, user, session_id, interaction_type, page_url, 
                       user_input, ai_response, context_data=None, response_time=0):
        """Log AI interaction for analytics and learning"""
        try:
            AIInteraction.objects.create(
                user=user,
                session_id=session_id,
                interaction_type=interaction_type,
                page_url=page_url,
                user_input=user_input,
                ai_response=ai_response,
                context_data=context_data or {},
                response_time_ms=response_time
            )
        except Exception as e:
            print(f"Error logging AI interaction: {e}")
    
    def get_chatbot_response(self, user_message, context, user=None, session_id=None):
        """Generate intelligent chatbot responses based on context"""
        start_time = datetime.now()
        
        # Context-aware responses
        responses = self._get_contextual_responses(user_message.lower(), context, user)
        
        # Select best response
        response = self._select_best_response(responses, user_message, context)
        
        # Log interaction
        response_time = int((datetime.now() - start_time).total_seconds() * 1000)
        if session_id:
            self.log_interaction(
                user, session_id, 'chatbot', f'/{context}/',
                user_message, response, {'context': context}, response_time
            )
        
        return response
    
    def _get_contextual_responses(self, message, context, user=None):
        """Generate context-aware responses"""
        responses = []
        
        # Job-related context
        if context == 'jobs':
            if any(word in message for word in ['search', 'find', 'looking']):
                responses.extend([
                    "I can help you find the perfect job! Try using our AI-powered search with specific skills or job titles.",
                    "Let me suggest some search filters that might help you find better matches based on your profile.",
                    "I notice you're looking for jobs. Would you like me to show you personalized recommendations?"
                ])
            elif any(word in message for word in ['apply', 'application']):
                responses.extend([
                    "I can guide you through the application process. Make sure your profile is complete for better chances!",
                    "Before applying, let me check if this job matches your skills and experience level.",
                    "Would you like tips on how to make your application stand out for this position?"
                ])
        
        # Profile context
        elif context == 'profile':
            if any(word in message for word in ['improve', 'better', 'enhance']):
                responses.extend([
                    "I can suggest improvements to make your profile more attractive to employers.",
                    "Based on job market trends, here are some skills you might want to highlight.",
                    "Let me analyze your profile completeness and suggest missing sections."
                ])
            elif any(word in message for word in ['skills', 'experience']):
                responses.extend([
                    "I can recommend skills that are in high demand for your field.",
                    "Would you like me to suggest ways to better showcase your experience?",
                    "I can help you identify skill gaps based on your target positions."
                ])
        
        # Dashboard context
        elif context == 'dashboard':
            if any(word in message for word in ['stats', 'analytics', 'progress']):
                responses.extend([
                    "I can provide insights about your job search progress and application success rate.",
                    "Let me show you trends in your job search activity and suggest improvements.",
                    "Would you like personalized recommendations based on your recent activity?"
                ])
        
        # Company context
        elif context == 'companies':
            if any(word in message for word in ['research', 'information', 'about']):
                responses.extend([
                    "I can help you research companies and find the best cultural fits for you.",
                    "Let me provide insights about company culture, salary ranges, and growth opportunities.",
                    "Would you like me to suggest similar companies based on your preferences?"
                ])
        
        # General helpful responses
        general_responses = [
            "I'm here to help! What specific assistance do you need with your job search?",
            "I can provide personalized recommendations based on your profile and preferences.",
            "Let me know what you're looking for, and I'll do my best to assist you!",
            "I have access to job market insights and can provide tailored advice for your career."
        ]
        
        if not responses:
            responses = general_responses
        
        return responses
    
    def _select_best_response(self, responses, user_message, context):
        """Select the most appropriate response"""
        if not responses:
            return "I'm here to help! How can I assist you today?"
        
        # For now, return a random response
        # In a real implementation, you'd use NLP to select the best match
        return random.choice(responses)
    
    def get_smart_suggestions(self, query, context, user=None, limit=5):
        """Generate smart search suggestions"""
        suggestions = []
        
        # Context-based suggestions
        if context == 'jobs':
            job_suggestions = [
                "Software Engineer Python", "Data Scientist Remote", "Product Manager",
                "UX Designer", "DevOps Engineer", "Marketing Manager", "Sales Representative",
                "Business Analyst", "Project Manager", "Full Stack Developer"
            ]
            
            # Filter suggestions based on query
            if query:
                suggestions = [s for s in job_suggestions if query.lower() in s.lower()]
            else:
                suggestions = job_suggestions
        
        elif context == 'companies':
            company_suggestions = [
                "Tech Startups", "Fortune 500", "Remote Companies", "Local Businesses",
                "Healthcare Companies", "Financial Services", "E-commerce", "Consulting Firms"
            ]
            suggestions = company_suggestions
        
        elif context == 'skills':
            skill_suggestions = [
                "Python Programming", "Machine Learning", "Data Analysis", "Project Management",
                "Digital Marketing", "UI/UX Design", "Cloud Computing", "Agile Methodology"
            ]
            suggestions = skill_suggestions
        
        return suggestions[:limit]
    
    def get_personalized_recommendations(self, user, context, limit=5):
        """Generate personalized recommendations for user"""
        if not user or not user.is_authenticated:
            return self._get_default_recommendations(context, limit)
        
        # Get or create user personalization profile
        profile, created = AIPersonalization.objects.get_or_create(user=user)
        
        recommendations = []
        
        if context == 'jobs':
            recommendations = self._get_job_recommendations(user, profile, limit)
        elif context == 'learning':
            recommendations = self._get_learning_recommendations(user, profile, limit)
        elif context == 'networking':
            recommendations = self._get_networking_recommendations(user, profile, limit)
        elif context == 'skills':
            recommendations = self._get_skill_recommendations(user, profile, limit)
        
        # Store recommendations in database
        self._store_recommendations(user, recommendations, context)
        
        return recommendations
    
    def _get_job_recommendations(self, user, profile, limit):
        """Generate job recommendations"""
        recommendations = [
            {
                'title': 'Senior Python Developer',
                'description': 'Perfect match for your Python skills and experience level',
                'url': '/jobs/1/',
                'confidence': 0.95,
                'type': 'job'
            },
            {
                'title': 'Data Science Manager',
                'description': 'Leadership role combining your technical and management interests',
                'url': '/jobs/2/',
                'confidence': 0.87,
                'type': 'job'
            },
            {
                'title': 'Remote Full Stack Position',
                'description': 'Matches your remote work preference and full-stack skills',
                'url': '/jobs/3/',
                'confidence': 0.82,
                'type': 'job'
            }
        ]
        return recommendations[:limit]
    
    def _get_learning_recommendations(self, user, profile, limit):
        """Generate learning recommendations"""
        recommendations = [
            {
                'title': 'Advanced Machine Learning Course',
                'description': 'Enhance your AI skills with this comprehensive course',
                'url': '/learning/ml-course/',
                'confidence': 0.90,
                'type': 'learning'
            },
            {
                'title': 'Leadership Skills Workshop',
                'description': 'Develop management skills for career advancement',
                'url': '/learning/leadership/',
                'confidence': 0.85,
                'type': 'learning'
            }
        ]
        return recommendations[:limit]
    
    def _get_networking_recommendations(self, user, profile, limit):
        """Generate networking recommendations"""
        recommendations = [
            {
                'title': 'Connect with Tech Leaders',
                'description': 'Expand your network in the technology industry',
                'url': '/networking/tech-leaders/',
                'confidence': 0.88,
                'type': 'connection'
            },
            {
                'title': 'Join Python Developers Group',
                'description': 'Connect with other Python developers in your area',
                'url': '/networking/python-group/',
                'confidence': 0.92,
                'type': 'connection'
            }
        ]
        return recommendations[:limit]
    
    def _get_skill_recommendations(self, user, profile, limit):
        """Generate skill development recommendations"""
        recommendations = [
            {
                'title': 'Learn Docker & Kubernetes',
                'description': 'High-demand containerization skills for DevOps roles',
                'url': '/skills/docker-kubernetes/',
                'confidence': 0.89,
                'type': 'skill'
            },
            {
                'title': 'Advanced SQL Techniques',
                'description': 'Enhance your database skills for better job prospects',
                'url': '/skills/advanced-sql/',
                'confidence': 0.86,
                'type': 'skill'
            }
        ]
        return recommendations[:limit]
    
    def _get_default_recommendations(self, context, limit):
        """Get default recommendations for anonymous users"""
        default_recs = [
            {
                'title': 'Complete Your Profile',
                'description': 'Get better job matches by completing your profile',
                'url': '/accounts/profile/',
                'confidence': 0.95,
                'type': 'action'
            },
            {
                'title': 'Explore Popular Jobs',
                'description': 'Check out the most popular job postings this week',
                'url': '/jobs/?sort=popular',
                'confidence': 0.80,
                'type': 'content'
            },
            {
                'title': 'Join Our Community',
                'description': 'Connect with other professionals in your field',
                'url': '/community/',
                'confidence': 0.75,
                'type': 'action'
            }
        ]
        return default_recs[:limit]
    
    def _store_recommendations(self, user, recommendations, context):
        """Store recommendations in database"""
        session_id = f"rec_{user.id}_{timezone.now().timestamp()}"
        
        for rec in recommendations:
            try:
                AIRecommendation.objects.create(
                    user=user,
                    session_id=session_id,
                    recommendation_type=rec.get('type', 'content'),
                    title=rec['title'],
                    description=rec['description'],
                    target_url=rec.get('url', ''),
                    confidence_score=rec.get('confidence', 0.5),
                    metadata={'context': context},
                    expires_at=timezone.now() + timedelta(days=7)
                )
            except Exception as e:
                print(f"Error storing recommendation: {e}")
    
    def enhance_search_query(self, query, context, user=None):
        """Enhance search query with AI"""
        if not query:
            return query
        
        # Simple query enhancement (in production, use NLP)
        enhanced_query = query
        
        # Add synonyms and related terms
        synonyms = {
            'developer': ['programmer', 'engineer', 'coder'],
            'manager': ['supervisor', 'lead', 'director'],
            'remote': ['work from home', 'telecommute', 'distributed'],
            'junior': ['entry level', 'associate', 'trainee'],
            'senior': ['experienced', 'lead', 'principal']
        }
        
        for word, alternatives in synonyms.items():
            if word in query.lower():
                enhanced_query += f" OR {' OR '.join(alternatives)}"
        
        # Log search query
        if user:
            session_id = f"search_{user.id}_{timezone.now().timestamp()}"
            AISearchQuery.objects.create(
                user=user,
                session_id=session_id,
                original_query=query,
                enhanced_query=enhanced_query,
                search_context=context
            )
        
        return enhanced_query
    
    def get_page_insights(self, page_context, user=None):
        """Get AI insights for specific page"""
        insights = []
        
        if page_context == 'dashboard':
            insights = [
                {
                    'type': 'tip',
                    'title': 'Optimize Your Profile',
                    'message': 'Complete profiles get 3x more views from employers',
                    'action': 'Complete Profile',
                    'url': '/accounts/profile/edit/'
                },
                {
                    'type': 'insight',
                    'title': 'Market Trend',
                    'message': 'Python skills are in high demand this month',
                    'action': 'View Jobs',
                    'url': '/jobs/?skills=python'
                }
            ]
        
        elif page_context == 'jobs':
            insights = [
                {
                    'type': 'suggestion',
                    'title': 'Smart Search',
                    'message': 'Try using specific skills in your search for better matches',
                    'action': 'Try AI Search',
                    'url': '#'
                }
            ]
        
        elif page_context == 'profile':
            insights = [
                {
                    'type': 'recommendation',
                    'title': 'Skill Gap Analysis',
                    'message': 'Add these trending skills to increase your job matches',
                    'action': 'View Skills',
                    'url': '/skills/trending/'
                }
            ]
        
        return insights
    
    def update_user_preferences(self, user, preferences):
        """Update user AI preferences"""
        if not user or not user.is_authenticated:
            return False
        
        try:
            profile, created = AIPersonalization.objects.get_or_create(user=user)
            profile.preferences.update(preferences)
            profile.save()
            return True
        except Exception as e:
            print(f"Error updating user preferences: {e}")
            return False

# Global AI service instance
ai_service = AIService()
