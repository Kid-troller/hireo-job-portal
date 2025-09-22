"""
AI Context Processor for Global AI Features
Makes AI functionality available in all templates
"""

from django.utils import timezone
from .ai_service import ai_service
from .models import AIRecommendation, AIPersonalization

def ai_context(request):
    """Add AI context to all templates"""
    context = {
        'ai_enabled': True,
        'ai_session_id': ai_service.get_session_id(request),
    }
    
    # Add user-specific AI data for authenticated users
    if request.user.is_authenticated:
        try:
            # Get user's AI preferences
            ai_profile, created = AIPersonalization.objects.get_or_create(
                user=request.user,
                defaults={
                    'ai_assistance_level': 'medium',
                    'preferences': {},
                    'interaction_patterns': {},
                    'skill_interests': [],
                }
            )
            
            context.update({
                'ai_assistance_level': ai_profile.ai_assistance_level,
                'ai_preferences': ai_profile.preferences,
                'user_has_ai_profile': True,
            })
            
            # Get recent recommendations count
            recent_recommendations = AIRecommendation.objects.filter(
                user=request.user,
                is_dismissed=False,
                created_at__gte=timezone.now() - timezone.timedelta(days=7)
            ).count()
            
            context['ai_recommendations_count'] = recent_recommendations
            
        except Exception as e:
            # Graceful fallback if AI features fail
            context.update({
                'ai_assistance_level': 'medium',
                'ai_preferences': {},
                'user_has_ai_profile': False,
                'ai_recommendations_count': 0,
            })
    else:
        # Anonymous user defaults
        context.update({
            'ai_assistance_level': 'medium',
            'ai_preferences': {},
            'user_has_ai_profile': False,
            'ai_recommendations_count': 0,
        })
    
    # Determine current page context for AI
    path = request.path
    if '/jobs/' in path:
        context['ai_page_context'] = 'jobs'
    elif '/accounts/' in path:
        context['ai_page_context'] = 'profile'
    elif '/employer/' in path:
        context['ai_page_context'] = 'employer'
    elif '/dashboard/' in path:
        context['ai_page_context'] = 'dashboard'
    elif '/companies/' in path:
        context['ai_page_context'] = 'companies'
    else:
        context['ai_page_context'] = 'general'
    
    return context
