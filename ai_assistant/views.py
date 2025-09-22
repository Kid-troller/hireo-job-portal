from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from django.utils import timezone
import json
import uuid

from .ai_service import ai_service
from .models import AIChatSession, AIRecommendation, AIInteraction

@csrf_exempt
@require_http_methods(["POST"])
def chatbot_api(request):
    """Handle chatbot conversations"""
    try:
        data = json.loads(request.body)
        message = data.get('message', '')
        context = data.get('context', 'general')
        session_id = data.get('session_id') or ai_service.get_session_id(request)
        
        if not message:
            return JsonResponse({'error': 'Message is required'}, status=400)
        
        # Get AI response
        response = ai_service.get_chatbot_response(
            message, context, request.user if request.user.is_authenticated else None, session_id
        )
        
        # Store conversation in session
        chat_session, created = AIChatSession.objects.get_or_create(
            session_id=session_id,
            defaults={
                'user': request.user if request.user.is_authenticated else None,
                'page_context': context,
                'conversation_data': []
            }
        )
        
        # Add messages to conversation
        chat_session.add_message('user', message)
        chat_session.add_message('ai', response)
        
        return JsonResponse({
            'response': response,
            'session_id': session_id,
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["GET"])
def smart_suggestions_api(request):
    """Get smart search suggestions"""
    try:
        query = request.GET.get('q', '')
        context = request.GET.get('context', 'general')
        limit = int(request.GET.get('limit', 5))
        
        suggestions = ai_service.get_smart_suggestions(
            query, context, request.user if request.user.is_authenticated else None, limit
        )
        
        return JsonResponse({
            'suggestions': suggestions,
            'query': query,
            'context': context
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["GET"])
def personalized_recommendations_api(request):
    """Get personalized recommendations"""
    try:
        context = request.GET.get('context', 'general')
        limit = int(request.GET.get('limit', 5))
        
        recommendations = ai_service.get_personalized_recommendations(
            request.user if request.user.is_authenticated else None, context, limit
        )
        
        return JsonResponse({
            'recommendations': recommendations,
            'context': context,
            'user_authenticated': request.user.is_authenticated
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["GET"])
def page_insights_api(request):
    """Get AI insights for current page"""
    try:
        context = request.GET.get('context', 'general')
        
        insights = ai_service.get_page_insights(
            context, request.user if request.user.is_authenticated else None
        )
        
        return JsonResponse({
            'insights': insights,
            'context': context
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def enhanced_search_api(request):
    """Enhance search query with AI"""
    try:
        data = json.loads(request.body)
        query = data.get('query', '')
        context = data.get('context', 'general')
        
        enhanced_query = ai_service.enhance_search_query(
            query, context, request.user if request.user.is_authenticated else None
        )
        
        suggestions = ai_service.get_smart_suggestions(query, context, request.user, 3)
        
        return JsonResponse({
            'original_query': query,
            'enhanced_query': enhanced_query,
            'suggestions': suggestions,
            'context': context
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def update_preferences_api(request):
    """Update user AI preferences"""
    try:
        data = json.loads(request.body)
        preferences = data.get('preferences', {})
        
        success = ai_service.update_user_preferences(request.user, preferences)
        
        return JsonResponse({
            'success': success,
            'message': 'Preferences updated successfully' if success else 'Failed to update preferences'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def feedback_api(request):
    """Handle AI feedback and ratings"""
    try:
        data = json.loads(request.body)
        interaction_id = data.get('interaction_id')
        rating = data.get('rating')  # 1-5
        feedback = data.get('feedback', '')
        
        if interaction_id and rating:
            try:
                interaction = AIInteraction.objects.get(id=interaction_id)
                interaction.satisfaction_score = rating
                interaction.save()
                
                # Log feedback as new interaction
                ai_service.log_interaction(
                    request.user if request.user.is_authenticated else None,
                    ai_service.get_session_id(request),
                    'feedback',
                    request.META.get('HTTP_REFERER', '/'),
                    feedback,
                    f"Rating: {rating}/5",
                    {'original_interaction_id': interaction_id}
                )
                
                return JsonResponse({'success': True, 'message': 'Feedback recorded'})
            except AIInteraction.DoesNotExist:
                return JsonResponse({'error': 'Interaction not found'}, status=404)
        
        return JsonResponse({'error': 'Invalid feedback data'}, status=400)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["GET"])
def conversation_history_api(request):
    """Get conversation history for user"""
    try:
        session_id = request.GET.get('session_id')
        limit = int(request.GET.get('limit', 10))
        
        if session_id:
            try:
                chat_session = AIChatSession.objects.get(session_id=session_id)
                conversation = chat_session.conversation_data[-limit:] if chat_session.conversation_data else []
                
                return JsonResponse({
                    'conversation': conversation,
                    'session_id': session_id,
                    'page_context': chat_session.page_context
                })
            except AIChatSession.DoesNotExist:
                return JsonResponse({'conversation': [], 'session_id': session_id})
        
        # Get recent conversations for authenticated user
        if request.user.is_authenticated:
            recent_sessions = AIChatSession.objects.filter(
                user=request.user
            ).order_by('-updated_at')[:5]
            
            sessions_data = []
            for session in recent_sessions:
                sessions_data.append({
                    'session_id': session.session_id,
                    'page_context': session.page_context,
                    'last_message': session.conversation_data[-1] if session.conversation_data else None,
                    'updated_at': session.updated_at.isoformat()
                })
            
            return JsonResponse({'recent_sessions': sessions_data})
        
        return JsonResponse({'conversation': []})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_http_methods(["GET"])
def user_analytics_api(request):
    """Get user AI analytics"""
    try:
        # Get user interaction stats
        interactions = AIInteraction.objects.filter(user=request.user)
        
        stats = {
            'total_interactions': interactions.count(),
            'chatbot_conversations': interactions.filter(interaction_type='chatbot').count(),
            'search_queries': interactions.filter(interaction_type='search').count(),
            'recommendations_received': AIRecommendation.objects.filter(user=request.user).count(),
            'recommendations_clicked': AIRecommendation.objects.filter(
                user=request.user, is_clicked=True
            ).count(),
            'average_satisfaction': interactions.exclude(
                satisfaction_score__isnull=True
            ).aggregate(avg_rating=models.Avg('satisfaction_score'))['avg_rating'] or 0
        }
        
        # Recent activity
        recent_interactions = interactions.order_by('-created_at')[:10]
        recent_activity = []
        
        for interaction in recent_interactions:
            recent_activity.append({
                'type': interaction.interaction_type,
                'page': interaction.page_url,
                'timestamp': interaction.created_at.isoformat(),
                'satisfaction': interaction.satisfaction_score
            })
        
        return JsonResponse({
            'stats': stats,
            'recent_activity': recent_activity
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

class AIAssistantView(View):
    """Main AI assistant interface"""
    
    def get(self, request):
        """Render AI assistant interface"""
        context = {
            'page_title': 'AI Assistant',
            'user_authenticated': request.user.is_authenticated,
        }
        
        if request.user.is_authenticated:
            # Get user's recent recommendations
            recent_recommendations = AIRecommendation.objects.filter(
                user=request.user,
                is_dismissed=False
            ).order_by('-confidence_score', '-created_at')[:5]
            
            context['recent_recommendations'] = recent_recommendations
        
        return render(request, 'ai_assistant/assistant.html', context)
