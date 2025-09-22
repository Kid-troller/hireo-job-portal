from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator

class Company(models.Model):
    INDUSTRY_CHOICES = (
        ('technology', 'Technology'),
        ('healthcare', 'Healthcare'),
        ('finance', 'Finance'),
        ('education', 'Education'),
        ('retail', 'Retail'),
        ('manufacturing', 'Manufacturing'),
        ('consulting', 'Consulting'),
        ('media', 'Media & Entertainment'),
        ('real_estate', 'Real Estate'),
        ('transportation', 'Transportation'),
        ('energy', 'Energy'),
        ('non_profit', 'Non-Profit'),
        ('other', 'Other'),
    )
    
    COMPANY_SIZE_CHOICES = (
        ('1-10', '1-10 employees'),
        ('11-50', '11-50 employees'),
        ('51-200', '51-200 employees'),
        ('201-500', '201-500 employees'),
        ('501-1000', '501-1000 employees'),
        ('1000+', '1000+ employees'),
    )
    
    name = models.CharField(max_length=200)
    description = models.TextField()
    industry = models.CharField(max_length=50, choices=INDUSTRY_CHOICES)
    company_size = models.CharField(max_length=20, choices=COMPANY_SIZE_CHOICES)
    founded_year = models.IntegerField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    logo = models.ImageField(upload_to='company_logos/', blank=True, null=True)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=10, blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField()
    linkedin_url = models.URLField(blank=True, null=True)
    facebook_url = models.URLField(blank=True, null=True)
    twitter_url = models.URLField(blank=True, null=True)
    company_culture = models.TextField(blank=True, null=True)
    benefits = models.TextField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('employer:company_detail', kwargs={'pk': self.pk})

class EmployerProfile(models.Model):
    user_profile = models.OneToOneField('accounts.UserProfile', on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='employers', null=True, blank=True)
    position = models.CharField(max_length=100, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)
    is_primary_contact = models.BooleanField(default=False)
    can_post_jobs = models.BooleanField(default=True)
    can_manage_applications = models.BooleanField(default=True)
    can_view_analytics = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        company_name = self.company.name if self.company else "No Company"
        return f"{self.user_profile.user.username} - {company_name}"

class CompanyReview(models.Model):
    RATING_CHOICES = (
        (1, '1 Star'),
        (2, '2 Stars'),
        (3, '3 Stars'),
        (4, '4 Stars'),
        (5, '5 Stars'),
    )
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='reviews')
    reviewer = models.ForeignKey('accounts.JobSeekerProfile', on_delete=models.CASCADE)
    rating = models.IntegerField(choices=RATING_CHOICES)
    title = models.CharField(max_length=200)
    review = models.TextField()
    pros = models.TextField(blank=True, null=True)
    cons = models.TextField(blank=True, null=True)
    is_anonymous = models.BooleanField(default=False)
    is_verified_employee = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.company.name} - {self.rating} stars"
    
    class Meta:
        unique_together = ['company', 'reviewer']

class CompanyPhoto(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(upload_to='company_photos/')
    caption = models.CharField(max_length=200, blank=True, null=True)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.company.name} - {self.caption or 'Photo'}"

class CompanyBenefit(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='benefits_list')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    icon = models.CharField(max_length=50, blank=True, null=True)  # For FontAwesome icons
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.company.name} - {self.name}"

class EmployerSubscription(models.Model):
    SUBSCRIPTION_TYPES = (
        ('basic', 'Basic'),
        ('premium', 'Premium'),
        ('enterprise', 'Enterprise'),
    )
    
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
        ('pending', 'Pending'),
    )
    
    employer = models.ForeignKey(EmployerProfile, on_delete=models.CASCADE)
    subscription_type = models.CharField(max_length=20, choices=SUBSCRIPTION_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    start_date = models.DateField()
    end_date = models.DateField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    features = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.employer.user_profile.user.username} - {self.subscription_type}"
    
    @property
    def is_active(self):
        from django.utils import timezone
        return self.status == 'active' and self.end_date >= timezone.now().date()
