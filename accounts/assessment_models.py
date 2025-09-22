from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import json

class SkillCategory(models.Model):
    """Categories for different skill types"""
    CATEGORY_TYPES = [
        ('technical', 'Technical Skills'),
        ('soft_skills', 'Soft Skills'),
        ('domain_specific', 'Domain Specific'),
        ('aptitude', 'Aptitude & Reasoning'),
        ('language', 'Language & Communication'),
        ('typing', 'Typing & Data Entry'),
    ]
    
    name = models.CharField(max_length=100)
    category_type = models.CharField(max_length=20, choices=CATEGORY_TYPES)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, default='fas fa-cog')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Skill Categories"
    
    def __str__(self):
        return self.name

class AssessmentQuestion(models.Model):
    """Individual assessment questions"""
    QUESTION_TYPES = [
        ('mcq', 'Multiple Choice Question'),
        ('practical', 'Practical/Task-Based'),
        ('scenario', 'Situational/Scenario'),
        ('typing', 'Typing Test'),
        ('coding', 'Coding Challenge'),
        ('essay', 'Essay/Written Response'),
    ]
    
    DIFFICULTY_LEVELS = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('expert', 'Expert'),
    ]
    
    category = models.ForeignKey(SkillCategory, on_delete=models.CASCADE, related_name='questions')
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES)
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_LEVELS)
    title = models.CharField(max_length=200)
    question_text = models.TextField()
    
    # For MCQ questions
    options = models.JSONField(default=dict, blank=True)  # {"A": "option1", "B": "option2", ...}
    correct_answer = models.CharField(max_length=10, blank=True)  # "A", "B", etc.
    
    # For practical/coding questions
    starter_code = models.TextField(blank=True)
    expected_output = models.TextField(blank=True)
    test_cases = models.JSONField(default=list, blank=True)
    
    # For scenario questions
    scenario_context = models.TextField(blank=True)
    evaluation_criteria = models.JSONField(default=list, blank=True)
    
    # For typing tests
    typing_text = models.TextField(blank=True)
    time_limit_seconds = models.IntegerField(default=300)  # 5 minutes default
    
    # Scoring
    max_points = models.IntegerField(default=10)
    time_weight = models.FloatField(default=0.2)  # How much time affects score
    
    # Metadata
    tags = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.title} ({self.get_question_type_display()})"

class Assessment(models.Model):
    """Assessment sessions"""
    STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assessments')
    category = models.ForeignKey(SkillCategory, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Configuration
    total_questions = models.IntegerField(default=20)
    time_limit_minutes = models.IntegerField(default=60)
    passing_score = models.IntegerField(default=70, validators=[MinValueValidator(0), MaxValueValidator(100)])
    
    # Status and timing
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_started')
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Results
    score = models.FloatField(null=True, blank=True)
    percentage = models.FloatField(null=True, blank=True)
    passed = models.BooleanField(default=False)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"
    
    def is_expired(self):
        if self.expires_at and timezone.now() > self.expires_at:
            return True
        return False
    
    def time_remaining(self):
        if self.started_at and self.time_limit_minutes:
            end_time = self.started_at + timezone.timedelta(minutes=self.time_limit_minutes)
            remaining = end_time - timezone.now()
            if remaining.total_seconds() > 0:
                return remaining
        return None

class AssessmentResponse(models.Model):
    """User responses to assessment questions"""
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name='responses')
    question = models.ForeignKey(AssessmentQuestion, on_delete=models.CASCADE)
    
    # Response data
    answer = models.TextField(blank=True)  # User's answer
    selected_option = models.CharField(max_length=10, blank=True)  # For MCQ
    code_submission = models.TextField(blank=True)  # For coding questions
    
    # Timing
    time_taken_seconds = models.IntegerField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    
    # Scoring
    is_correct = models.BooleanField(default=False)
    points_earned = models.FloatField(default=0)
    feedback = models.TextField(blank=True)
    
    # For typing tests
    typing_speed_wpm = models.IntegerField(null=True, blank=True)
    typing_accuracy = models.FloatField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.assessment.user.username} - {self.question.title}"

class SkillCertificate(models.Model):
    """Certificates awarded for completed assessments"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='certificates')
    assessment = models.OneToOneField(Assessment, on_delete=models.CASCADE)
    certificate_id = models.CharField(max_length=50, unique=True)
    
    # Certificate details
    skill_name = models.CharField(max_length=200)
    level = models.CharField(max_length=50)  # Beginner, Intermediate, Advanced, Expert
    score = models.FloatField()
    percentage = models.FloatField()
    
    # Validity
    issued_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_valid = models.BooleanField(default=True)
    
    # Verification
    verification_url = models.URLField(blank=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.skill_name} Certificate"

class AssessmentAttempt(models.Model):
    """Track multiple attempts for the same assessment"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.ForeignKey(SkillCategory, on_delete=models.CASCADE)
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE)
    
    attempt_number = models.IntegerField(default=1)
    score = models.FloatField()
    percentage = models.FloatField()
    passed = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'category', 'attempt_number']
    
    def __str__(self):
        return f"{self.user.username} - {self.category.name} (Attempt {self.attempt_number})"
