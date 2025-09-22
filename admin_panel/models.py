from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta


class AdminActivity(models.Model):
    """Track admin activities for audit purposes"""
    ACTIVITY_TYPES = [
        ('user_action', 'User Action'),
        ('job_action', 'Job Action'),
        ('application_action', 'Application Action'),
        ('system_action', 'System Action'),
        ('report_generated', 'Report Generated'),
        ('settings_changed', 'Settings Changed'),
    ]
    
    admin_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='admin_activities')
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    description = models.TextField()
    target_model = models.CharField(max_length=50, blank=True, null=True)
    target_id = models.PositiveIntegerField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Admin Activity'
        verbose_name_plural = 'Admin Activities'
    
    def __str__(self):
        return f"{self.admin_user.username} - {self.activity_type} - {self.timestamp}"


class SystemSettings(models.Model):
    """System-wide settings for the platform"""
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        verbose_name = 'System Setting'
        verbose_name_plural = 'System Settings'
    
    def __str__(self):
        return f"{self.key}: {self.value[:50]}"


class PlatformStatistics(models.Model):
    """Daily platform statistics for analytics"""
    date = models.DateField(unique=True)
    total_users = models.PositiveIntegerField(default=0)
    new_users = models.PositiveIntegerField(default=0)
    active_users = models.PositiveIntegerField(default=0)
    total_jobs = models.PositiveIntegerField(default=0)
    new_jobs = models.PositiveIntegerField(default=0)
    active_jobs = models.PositiveIntegerField(default=0)
    total_applications = models.PositiveIntegerField(default=0)
    new_applications = models.PositiveIntegerField(default=0)
    successful_applications = models.PositiveIntegerField(default=0)
    total_companies = models.PositiveIntegerField(default=0)
    active_companies = models.PositiveIntegerField(default=0)
    revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date']
        verbose_name = 'Platform Statistics'
        verbose_name_plural = 'Platform Statistics'
    
    def __str__(self):
        return f"Stats for {self.date}"


class UserReport(models.Model):
    """User-generated reports for content moderation"""
    REPORT_TYPES = [
        ('inappropriate_job', 'Inappropriate Job Posting'),
        ('fake_company', 'Fake Company'),
        ('spam_user', 'Spam User'),
        ('harassment', 'Harassment'),
        ('fraud', 'Fraudulent Activity'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('investigating', 'Under Investigation'),
        ('resolved', 'Resolved'),
        ('dismissed', 'Dismissed'),
    ]
    
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports_made')
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    description = models.TextField()
    target_model = models.CharField(max_length=50)  # 'user', 'job', 'company', etc.
    target_id = models.PositiveIntegerField()
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    assigned_admin = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_reports')
    admin_notes = models.TextField(blank=True)
    resolution = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'User Report'
        verbose_name_plural = 'User Reports'
    
    def __str__(self):
        return f"{self.report_type} - {self.status}"


class MaintenanceMode(models.Model):
    """System maintenance mode settings"""
    is_active = models.BooleanField(default=False)
    message = models.TextField(default="System is under maintenance. Please try again later.")
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    allowed_ips = models.TextField(blank=True, help_text="Comma-separated list of IP addresses allowed during maintenance")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Maintenance Mode'
        verbose_name_plural = 'Maintenance Mode'
    
    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"Maintenance Mode - {status}"


class EmailTemplate(models.Model):
    """Email templates for system notifications"""
    TEMPLATE_TYPES = [
        ('welcome', 'Welcome Email'),
        ('job_alert', 'Job Alert'),
        ('application_received', 'Application Received'),
        ('application_status', 'Application Status Update'),
        ('interview_scheduled', 'Interview Scheduled'),
        ('password_reset', 'Password Reset'),
        ('account_verification', 'Account Verification'),
        ('newsletter', 'Newsletter'),
        ('system_notification', 'System Notification'),
    ]
    
    name = models.CharField(max_length=100)
    template_type = models.CharField(max_length=25, choices=TEMPLATE_TYPES)
    subject = models.CharField(max_length=200)
    html_content = models.TextField()
    text_content = models.TextField(blank=True)
    variables = models.TextField(blank=True, help_text="JSON format of available variables")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        verbose_name = 'Email Template'
        verbose_name_plural = 'Email Templates'
    
    def __str__(self):
        return f"{self.name} ({self.template_type})"


class SystemAlert(models.Model):
    """System alerts for administrators"""
    ALERT_TYPES = [
        ('error', 'Error'),
        ('warning', 'Warning'),
        ('info', 'Information'),
        ('security', 'Security Alert'),
    ]
    
    PRIORITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    title = models.CharField(max_length=200)
    message = models.TextField()
    alert_type = models.CharField(max_length=10, choices=ALERT_TYPES)
    priority = models.CharField(max_length=10, choices=PRIORITY_LEVELS)
    is_read = models.BooleanField(default=False)
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'System Alert'
        verbose_name_plural = 'System Alerts'
    
    def __str__(self):
        return f"{self.title} ({self.priority})"
