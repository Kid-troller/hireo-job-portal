from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator, FileExtensionValidator
from django.utils import timezone
from datetime import date

class JobCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    icon = models.CharField(max_length=50, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Job Categories"

class JobLocation(models.Model):
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.city}, {self.state}, {self.country}"
    
    class Meta:
        unique_together = ['city', 'state', 'country']

class JobPost(models.Model):
    EMPLOYMENT_TYPE_CHOICES = (
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('contract', 'Contract'),
        ('internship', 'Internship'),
        ('freelance', 'Freelance'),
        ('temporary', 'Temporary'),
    )
    
    EXPERIENCE_LEVEL_CHOICES = (
        ('entry', 'Entry Level'),
        ('junior', 'Junior'),
        ('mid', 'Mid Level'),
        ('senior', 'Senior'),
        ('lead', 'Lead'),
        ('executive', 'Executive'),
    )
    
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('expired', 'Expired'),
        ('closed', 'Closed'),
    )
    
    CURRENCY_CHOICES = (
        ('NPR', 'Nepalese Rupee (NPR)'),
        ('USD', 'US Dollar (USD)'),
        ('GBP', 'British Pound (GBP)'),
        ('INR', 'Indian Rupee (INR)'),
    )
    
    # Basic Information
    title = models.CharField(max_length=200)
    company = models.ForeignKey('employers.Company', on_delete=models.CASCADE, related_name='job_posts')
    employer = models.ForeignKey('employers.EmployerProfile', on_delete=models.CASCADE, related_name='posted_jobs')
    category = models.ForeignKey(JobCategory, on_delete=models.CASCADE, related_name='jobs')
    location = models.ForeignKey(JobLocation, on_delete=models.CASCADE, related_name='jobs')
    
    # Job Details
    description = models.TextField()
    requirements = models.TextField()
    responsibilities = models.TextField()
    benefits = models.TextField(blank=True, null=True)
    
    # Employment Details
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_TYPE_CHOICES)
    experience_level = models.CharField(max_length=20, choices=EXPERIENCE_LEVEL_CHOICES)
    min_experience = models.IntegerField(default=0)
    max_experience = models.IntegerField(default=0)
    
    # Salary Information
    min_salary = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    max_salary = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    salary_currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='NPR')
    is_salary_negotiable = models.BooleanField(default=False)
    is_salary_visible = models.BooleanField(default=True)
    
    # Skills and Requirements
    required_skills = models.TextField(blank=True, null=True)
    preferred_skills = models.TextField(blank=True, null=True)
    education_required = models.CharField(max_length=100, blank=True, null=True)
    
    # Application Details
    application_deadline = models.DateField()
    is_remote = models.BooleanField(default=False)
    remote_percentage = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        default=0
    )
    
    # Status and Visibility
    is_featured = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    is_urgent = models.BooleanField(default=False)
    
    # Analytics
    views_count = models.IntegerField(default=0)
    applications_count = models.IntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(blank=True, null=True)
    
    def get_currency_symbol(self):
        """Return currency symbol for display"""
        currency_symbols = {
            'NPR': 'Rs.',
            'USD': '$',
            'GBP': '£',
            'INR': '₹',
        }
        return currency_symbols.get(self.salary_currency, self.salary_currency)
    
    def get_formatted_salary(self):
        """Return formatted salary range with currency symbol"""
        symbol = self.get_currency_symbol()
        if self.min_salary and self.max_salary:
            return f"{symbol}{self.min_salary:,.0f} - {symbol}{self.max_salary:,.0f}"
        elif self.min_salary:
            return f"{symbol}{self.min_salary:,.0f}+"
        elif self.max_salary:
            return f"Up to {symbol}{self.max_salary:,.0f}"
        else:
            return "Salary not specified"
    
    def __str__(self):
        return f"{self.title} at {self.company.name}"
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('jobs:job_detail', kwargs={'pk': self.pk})
    
    @property
    def is_active(self):
        return self.status == 'active' and self.application_deadline >= date.today()
    
    @property
    def salary_range(self):
        if self.min_salary and self.max_salary:
            return f"{self.salary_currency} {self.min_salary:,} - {self.max_salary:,}"
        elif self.min_salary:
            return f"{self.salary_currency} {self.min_salary:,}+"
        elif self.max_salary:
            return f"Up to {self.salary_currency} {self.max_salary:,}"
        return "Not specified"
    
    def increment_views(self):
        self.views_count += 1
        self.save(update_fields=['views_count'])
    
    def increment_applications(self):
        self.applications_count += 1
        self.save(update_fields=['applications_count'])

class SavedJob(models.Model):
    user = models.ForeignKey('accounts.JobSeekerProfile', on_delete=models.CASCADE, related_name='saved_jobs')
    job = models.ForeignKey(JobPost, on_delete=models.CASCADE, related_name='saved_by')
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        unique_together = ('user', 'job')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user} saved {self.job.title}"

class JobView(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    job = models.ForeignKey(JobPost, on_delete=models.CASCADE, related_name='views')
    viewed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-viewed_at']
    
    def __str__(self):
        return f"{self.user.username} viewed {self.job.title}"

class JobApplication(models.Model):
    STATUS_CHOICES = (
        ('applied', 'Applied'),
        ('reviewing', 'Under Review'),
        ('shortlisted', 'Shortlisted'),
        ('interviewing', 'Interviewing'),
        ('offered', 'Job Offered'),
        ('hired', 'Hired'),
        ('rejected', 'Rejected'),
        ('withdrawn', 'Withdrawn'),
    )
    
    job = models.ForeignKey(JobPost, on_delete=models.CASCADE, related_name='applications')
    applicant = models.ForeignKey('accounts.JobSeekerProfile', on_delete=models.CASCADE, related_name='applications')
    cover_letter = models.TextField()
    resume = models.FileField(
        upload_to='applications/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx'])]
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='applied')
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Additional fields for tracking
    is_shortlisted = models.BooleanField(default=False)
    interview_date = models.DateTimeField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.applicant.user_profile.user.username} - {self.job.title}"
    
    class Meta:
        unique_together = ['job', 'applicant']

class JobAlert(models.Model):
    FREQUENCY_CHOICES = (
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    )
    
    user = models.ForeignKey('accounts.JobSeekerProfile', on_delete=models.CASCADE, related_name='job_alerts')
    title = models.CharField(max_length=200)
    keywords = models.CharField(max_length=500, blank=True, null=True)
    location = models.ForeignKey(JobLocation, on_delete=models.CASCADE, blank=True, null=True)
    category = models.ForeignKey(JobCategory, on_delete=models.CASCADE, blank=True, null=True)
    employment_type = models.CharField(max_length=20, choices=JobPost.EMPLOYMENT_TYPE_CHOICES, blank=True, null=True)
    experience_level = models.CharField(max_length=20, choices=JobPost.EXPERIENCE_LEVEL_CHOICES, blank=True, null=True)
    min_salary = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    max_salary = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    is_remote = models.BooleanField(default=False)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default='weekly')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_sent = models.DateTimeField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.user.user_profile.user.username} - {self.title}"


class JobSearch(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    job_seeker = models.ForeignKey('accounts.JobSeekerProfile', on_delete=models.CASCADE, blank=True, null=True, related_name='searches')
    query = models.CharField(max_length=500, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    category = models.ForeignKey(JobCategory, on_delete=models.SET_NULL, null=True, blank=True)
    filters = models.JSONField(default=dict)
    results_count = models.IntegerField(default=0)
    searched_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-searched_at']
    
    def __str__(self):
        return f"{self.query or 'jobs'} - {self.searched_at}"
