from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from jobs.models import JobPost
from employers.models import Company
from accounts.models import JobSeekerProfile


class JobView(models.Model):
    """Track job post views for analytics"""
    job = models.ForeignKey(JobPost, on_delete=models.CASCADE, related_name='analytics_views')
    viewer = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='job_views')
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    viewed_at = models.DateTimeField(default=timezone.now)
    session_id = models.CharField(max_length=100, blank=True)
    
    class Meta:
        db_table = 'analytics_job_view'
        indexes = [
            models.Index(fields=['job', 'viewed_at']),
            models.Index(fields=['viewer', 'viewed_at']),
        ]


class JobClick(models.Model):
    """Track job post clicks (apply button, save, etc.)"""
    CLICK_TYPES = [
        ('apply', 'Apply Button'),
        ('save', 'Save Job'),
        ('share', 'Share Job'),
        ('company_profile', 'Company Profile'),
        ('external_link', 'External Link'),
    ]
    
    job = models.ForeignKey(JobPost, on_delete=models.CASCADE, related_name='analytics_clicks')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='job_clicks')
    click_type = models.CharField(max_length=20, choices=CLICK_TYPES)
    ip_address = models.GenericIPAddressField()
    clicked_at = models.DateTimeField(default=timezone.now)
    session_id = models.CharField(max_length=100, blank=True)
    
    class Meta:
        db_table = 'analytics_job_click'
        indexes = [
            models.Index(fields=['job', 'click_type', 'clicked_at']),
        ]


class JobSeekerActivity(models.Model):
    """Track job seeker engagement and activity patterns"""
    ACTIVITY_TYPES = [
        ('login', 'Login'),
        ('search', 'Job Search'),
        ('filter', 'Apply Filter'),
        ('profile_update', 'Profile Update'),
        ('application_submit', 'Application Submitted'),
        ('job_save', 'Job Saved'),
        ('job_unsave', 'Job Unsaved'),
    ]
    
    job_seeker = models.ForeignKey(JobSeekerProfile, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    job = models.ForeignKey(JobPost, on_delete=models.CASCADE, null=True, blank=True)
    search_query = models.CharField(max_length=255, blank=True)
    filters_used = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(default=timezone.now)
    session_id = models.CharField(max_length=100, blank=True)
    
    class Meta:
        db_table = 'analytics_jobseeker_activity'
        indexes = [
            models.Index(fields=['job_seeker', 'timestamp']),
            models.Index(fields=['activity_type', 'timestamp']),
        ]


class EmployerEngagement(models.Model):
    """Track employer engagement metrics"""
    ENGAGEMENT_TYPES = [
        ('job_post', 'Job Posted'),
        ('job_edit', 'Job Edited'),
        ('application_view', 'Application Viewed'),
        ('candidate_contact', 'Candidate Contacted'),
        ('job_promote', 'Job Promoted'),
        ('analytics_view', 'Analytics Viewed'),
    ]
    
    employer = models.ForeignKey('employers.EmployerProfile', on_delete=models.CASCADE, related_name='engagements')
    engagement_type = models.CharField(max_length=20, choices=ENGAGEMENT_TYPES)
    job = models.ForeignKey(JobPost, on_delete=models.CASCADE, null=True, blank=True)
    timestamp = models.DateTimeField(default=timezone.now)
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = 'analytics_employer_engagement'
        indexes = [
            models.Index(fields=['employer', 'timestamp']),
            models.Index(fields=['engagement_type', 'timestamp']),
        ]


class SkillDemand(models.Model):
    """Track skill demand across job postings"""
    skill_name = models.CharField(max_length=100, db_index=True)
    job = models.ForeignKey(JobPost, on_delete=models.CASCADE, related_name='skill_demands')
    is_required = models.BooleanField(default=True)  # True for required, False for preferred
    category = models.ForeignKey('jobs.JobCategory', on_delete=models.CASCADE, null=True, blank=True)
    location = models.ForeignKey('jobs.JobLocation', on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'analytics_skill_demand'
        unique_together = ['skill_name', 'job', 'is_required']
        indexes = [
            models.Index(fields=['skill_name', 'created_at']),
            models.Index(fields=['category', 'skill_name']),
        ]


class SalaryInsight(models.Model):
    """Store salary insights for analytics"""
    job = models.OneToOneField(JobPost, on_delete=models.CASCADE, related_name='salary_insight')
    min_salary = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    max_salary = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default='USD')
    is_negotiable = models.BooleanField(default=False)
    category = models.ForeignKey('jobs.JobCategory', on_delete=models.CASCADE)
    location = models.ForeignKey('jobs.JobLocation', on_delete=models.CASCADE)
    experience_level = models.CharField(max_length=20)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'analytics_salary_insight'
        indexes = [
            models.Index(fields=['category', 'location']),
            models.Index(fields=['experience_level', 'created_at']),
        ]


class ApplicationConversion(models.Model):
    """Track application conversion rates"""
    job = models.ForeignKey(JobPost, on_delete=models.CASCADE, related_name='conversion_metrics')
    total_views = models.PositiveIntegerField(default=0)
    total_clicks = models.PositiveIntegerField(default=0)
    total_applications = models.PositiveIntegerField(default=0)
    conversion_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)  # applications/views * 100
    click_through_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)  # clicks/views * 100
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'analytics_application_conversion'


class TrendingJob(models.Model):
    """Store trending jobs based on various metrics"""
    TREND_TYPES = [
        ('views', 'Most Viewed'),
        ('applications', 'Most Applied'),
        ('saves', 'Most Saved'),
        ('recent', 'Recently Posted'),
        ('urgent', 'Urgent Hiring'),
    ]
    
    job = models.ForeignKey(JobPost, on_delete=models.CASCADE, related_name='trending_metrics')
    trend_type = models.CharField(max_length=20, choices=TREND_TYPES)
    score = models.DecimalField(max_digits=10, decimal_places=2)
    rank = models.PositiveIntegerField()
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'analytics_trending_job'
        unique_together = ['job', 'trend_type', 'period_start']
        indexes = [
            models.Index(fields=['trend_type', 'rank']),
            models.Index(fields=['created_at']),
        ]


class CompanyMetrics(models.Model):
    """Aggregate company performance metrics"""
    company = models.OneToOneField(Company, on_delete=models.CASCADE, related_name='metrics')
    total_jobs_posted = models.PositiveIntegerField(default=0)
    active_jobs = models.PositiveIntegerField(default=0)
    total_applications_received = models.PositiveIntegerField(default=0)
    total_hires = models.PositiveIntegerField(default=0)
    avg_time_to_hire = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)  # days
    company_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    total_reviews = models.PositiveIntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'analytics_company_metrics'


class MarketInsight(models.Model):
    """Store market-wide insights and trends"""
    INSIGHT_TYPES = [
        ('job_growth', 'Job Growth Rate'),
        ('salary_trend', 'Salary Trends'),
        ('skill_demand', 'Skill Demand'),
        ('location_hotspot', 'Location Hotspots'),
        ('industry_growth', 'Industry Growth'),
    ]
    
    insight_type = models.CharField(max_length=20, choices=INSIGHT_TYPES)
    category = models.ForeignKey('jobs.JobCategory', on_delete=models.CASCADE, null=True, blank=True)
    location = models.ForeignKey('jobs.JobLocation', on_delete=models.CASCADE, null=True, blank=True)
    metric_value = models.DecimalField(max_digits=12, decimal_places=2)
    metric_label = models.CharField(max_length=100)
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    created_at = models.DateTimeField(default=timezone.now)
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = 'analytics_market_insight'
        indexes = [
            models.Index(fields=['insight_type', 'created_at']),
            models.Index(fields=['category', 'location']),
        ]


class UserAlert(models.Model):
    """Store user alerts and notifications"""
    ALERT_TYPES = [
        ('job_performance', 'Job Performance Alert'),
        ('skill_recommendation', 'Skill Recommendation'),
        ('market_trend', 'Market Trend Alert'),
        ('application_milestone', 'Application Milestone'),
        ('hiring_suggestion', 'Hiring Suggestion'),
    ]
    
    ALERT_PRIORITIES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='analytics_alerts')
    alert_type = models.CharField(max_length=25, choices=ALERT_TYPES)
    priority = models.CharField(max_length=10, choices=ALERT_PRIORITIES, default='medium')
    title = models.CharField(max_length=200)
    message = models.TextField()
    action_url = models.URLField(blank=True)
    is_read = models.BooleanField(default=False)
    is_dismissed = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = 'analytics_user_alert'
        indexes = [
            models.Index(fields=['user', 'is_read', 'created_at']),
            models.Index(fields=['alert_type', 'priority']),
        ]
