from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import json

class AIInteraction(models.Model):
    """Store all AI interactions across the platform"""
    INTERACTION_TYPES = [
        ('chatbot', 'Chatbot Conversation'),
        ('search', 'AI Search Query'),
        ('recommendation', 'Content Recommendation'),
        ('suggestion', 'Auto Suggestion'),
        ('analysis', 'Content Analysis'),
        ('personalization', 'Personalization'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_id = models.CharField(max_length=100, db_index=True)
    interaction_type = models.CharField(max_length=20, choices=INTERACTION_TYPES, db_index=True)
    page_url = models.URLField(max_length=500)
    page_title = models.CharField(max_length=200, blank=True)
    user_input = models.TextField()
    ai_response = models.TextField()
    context_data = models.JSONField(default=dict, blank=True)
    response_time_ms = models.IntegerField(default=0)
    satisfaction_score = models.IntegerField(null=True, blank=True)  # 1-5 rating
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'interaction_type']),
            models.Index(fields=['session_id', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.interaction_type} - {self.user or 'Anonymous'} - {self.created_at}"

class AIRecommendation(models.Model):
    """Store AI-generated recommendations for users"""
    RECOMMENDATION_TYPES = [
        ('job', 'Job Recommendation'),
        ('content', 'Content Recommendation'),
        ('action', 'Action Suggestion'),
        ('learning', 'Learning Resource'),
        ('connection', 'Network Connection'),
        ('skill', 'Skill Development'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_id = models.CharField(max_length=100, db_index=True)
    recommendation_type = models.CharField(max_length=20, choices=RECOMMENDATION_TYPES, db_index=True)
    title = models.CharField(max_length=200)
    description = models.TextField()
    target_url = models.URLField(max_length=500, blank=True)
    confidence_score = models.FloatField(default=0.0)  # 0.0 to 1.0
    metadata = models.JSONField(default=dict, blank=True)
    is_clicked = models.BooleanField(default=False)
    is_dismissed = models.BooleanField(default=False)
    clicked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-confidence_score', '-created_at']
        indexes = [
            models.Index(fields=['user', 'recommendation_type']),
            models.Index(fields=['created_at', 'expires_at']),
        ]
    
    def __str__(self):
        return f"{self.recommendation_type}: {self.title}"
    
    def is_expired(self):
        return self.expires_at and timezone.now() > self.expires_at

class AIChatSession(models.Model):
    """Store chatbot conversation sessions"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_id = models.CharField(max_length=100, unique=True, db_index=True)
    page_context = models.CharField(max_length=100)  # e.g., 'jobs', 'profile', 'dashboard'
    conversation_data = models.JSONField(default=list)  # Store full conversation
    is_active = models.BooleanField(default=True)
    satisfaction_rating = models.IntegerField(null=True, blank=True)  # 1-5
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"Chat Session - {self.user or 'Anonymous'} - {self.page_context}"
    
    def add_message(self, message_type, content, metadata=None):
        """Add a message to the conversation"""
        message = {
            'type': message_type,  # 'user' or 'ai'
            'content': content,
            'timestamp': timezone.now().isoformat(),
            'metadata': metadata or {}
        }
        self.conversation_data.append(message)
        self.save()

class AISearchQuery(models.Model):
    """Store AI-enhanced search queries and results"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_id = models.CharField(max_length=100, db_index=True)
    original_query = models.CharField(max_length=500)
    enhanced_query = models.CharField(max_length=500, blank=True)
    search_context = models.CharField(max_length=50)  # 'jobs', 'companies', 'profiles'
    results_count = models.IntegerField(default=0)
    suggestions_provided = models.JSONField(default=list)
    filters_applied = models.JSONField(default=dict)
    click_through_rate = models.FloatField(default=0.0)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Search: {self.original_query} ({self.results_count} results)"

class AIPersonalization(models.Model):
    """Store user personalization preferences and AI learning data"""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    preferences = models.JSONField(default=dict)  # UI preferences, content types, etc.
    interaction_patterns = models.JSONField(default=dict)  # Usage patterns
    skill_interests = models.JSONField(default=list)  # Inferred interests
    career_stage = models.CharField(max_length=50, blank=True)
    ai_assistance_level = models.CharField(max_length=20, default='medium', choices=[
        ('minimal', 'Minimal AI Assistance'),
        ('medium', 'Moderate AI Assistance'),
        ('maximum', 'Maximum AI Assistance'),
    ])
    notification_preferences = models.JSONField(default=dict)
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"AI Profile - {self.user.username}"
    
    def update_interaction_pattern(self, pattern_type, data):
        """Update user interaction patterns for AI learning"""
        if pattern_type not in self.interaction_patterns:
            self.interaction_patterns[pattern_type] = []
        
        self.interaction_patterns[pattern_type].append({
            'data': data,
            'timestamp': timezone.now().isoformat()
        })
        
        # Keep only last 100 interactions per pattern
        self.interaction_patterns[pattern_type] = self.interaction_patterns[pattern_type][-100:]
        self.save()

class AIAnalytics(models.Model):
    """Store AI system analytics and performance metrics"""
    date = models.DateField(db_index=True)
    metric_type = models.CharField(max_length=50, db_index=True)
    metric_name = models.CharField(max_length=100)
    metric_value = models.FloatField()
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        unique_together = ['date', 'metric_type', 'metric_name']
        ordering = ['-date', 'metric_type']
    
    def __str__(self):
        return f"{self.metric_name}: {self.metric_value} ({self.date})"
