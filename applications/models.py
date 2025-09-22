from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator

class Application(models.Model):
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
    
    job = models.ForeignKey('jobs.JobPost', on_delete=models.CASCADE, related_name='job_applications')
    applicant = models.ForeignKey('accounts.JobSeekerProfile', on_delete=models.CASCADE, related_name='job_applications')
    employer = models.ForeignKey('employers.EmployerProfile', on_delete=models.CASCADE, related_name='received_applications')
    
    # Application Details
    cover_letter = models.TextField()
    resume = models.FileField(
        upload_to='applications/resumes/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx'])]
    )
    additional_files = models.FileField(
        upload_to='applications/additional/',
        blank=True,
        null=True
    )
    
    # Status and Tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='applied')
    is_shortlisted = models.BooleanField(default=False)
    is_rejected = models.BooleanField(default=False)
    
    # Timestamps
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reviewed_at = models.DateTimeField(blank=True, null=True)
    
    # Notes and Feedback
    employer_notes = models.TextField(blank=True, null=True)
    applicant_notes = models.TextField(blank=True, null=True)
    shortlist_instructions = models.TextField(blank=True, null=True, help_text="Instructions for shortlisted candidates")
    
    def __str__(self):
        return f"{self.applicant.user_profile.user.username} - {self.job.title}"
    
    class Meta:
        unique_together = ['job', 'applicant']
        ordering = ['-applied_at']

class ApplicationStatus(models.Model):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='status_history')
    status = models.CharField(max_length=20, choices=Application.STATUS_CHOICES)
    notes = models.TextField(blank=True, null=True)
    changed_by = models.ForeignKey(User, on_delete=models.CASCADE)
    changed_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.application} - {self.status}"

class Interview(models.Model):
    INTERVIEW_TYPE_CHOICES = (
        ('phone', 'Phone Interview'),
        ('video', 'Video Interview'),
        ('in_person', 'In-Person Interview'),
        ('technical', 'Technical Interview'),
        ('behavioral', 'Behavioral Interview'),
        ('panel', 'Panel Interview'),
    )
    
    STATUS_CHOICES = (
        ('scheduled', 'Scheduled'),
        ('confirmed', 'Confirmed'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('rescheduled', 'Rescheduled'),
    )
    
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='interviews')
    interview_type = models.CharField(max_length=20, choices=INTERVIEW_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    
    # Scheduling
    scheduled_date = models.DateTimeField()
    duration = models.IntegerField(help_text="Duration in minutes", default=60)
    timezone = models.CharField(max_length=50, default='UTC')
    
    # Location/Platform
    location = models.CharField(max_length=200, blank=True, null=True)
    video_platform = models.CharField(max_length=100, blank=True, null=True)
    meeting_link = models.URLField(blank=True, null=True)
    
    # Participants
    interviewer_name = models.CharField(max_length=100)
    interviewer_email = models.EmailField()
    interviewer_phone = models.CharField(max_length=15, blank=True, null=True)
    
    # Notes
    instructions = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.application} - {self.interview_type} on {self.scheduled_date}"

class Message(models.Model):
    MESSAGE_TYPE_CHOICES = (
        ('application', 'Application Related'),
        ('interview', 'Interview Related'),
        ('general', 'General'),
    )
    
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPE_CHOICES, default='general')
    
    subject = models.CharField(max_length=200)
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    
    # Attachments
    attachment = models.FileField(upload_to='messages/attachments/', blank=True, null=True)
    
    # Timestamps
    sent_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.sender.username} to {self.recipient.username} - {self.subject}"
    
    class Meta:
        ordering = ['-sent_at']

class Notification(models.Model):
    NOTIFICATION_TYPE_CHOICES = (
        ('application_status', 'Application Status Update'),
        ('interview_scheduled', 'Interview Scheduled'),
        ('message_received', 'New Message'),
        ('job_recommendation', 'Job Recommendation'),
        ('application_viewed', 'Application Viewed'),
        ('interview_reminder', 'Interview Reminder'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='app_notifications')
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPE_CHOICES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Related objects
    application = models.ForeignKey(Application, on_delete=models.CASCADE, blank=True, null=True)
    interview = models.ForeignKey(Interview, on_delete=models.CASCADE, blank=True, null=True)
    job = models.ForeignKey('jobs.JobPost', on_delete=models.CASCADE, blank=True, null=True)
    
    # Status
    is_read = models.BooleanField(default=False)
    is_email_sent = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.notification_type}"
    
    class Meta:
        ordering = ['-created_at']

class ApplicationAnalytics(models.Model):
    application = models.OneToOneField(Application, on_delete=models.CASCADE, related_name='analytics')
    
    # View tracking
    employer_views = models.IntegerField(default=0)
    last_viewed = models.DateTimeField(blank=True, null=True)
    
    # Response tracking
    time_to_first_response = models.DurationField(blank=True, null=True)
    time_to_decision = models.DurationField(blank=True, null=True)
    
    # Interview tracking
    interviews_count = models.IntegerField(default=0)
    interview_success_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Communication tracking
    messages_count = models.IntegerField(default=0)
    last_communication = models.DateTimeField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Analytics for {self.application}"

class ApplicationView(models.Model):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='views')
    viewer = models.ForeignKey(User, on_delete=models.CASCADE)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True, null=True)
    viewed_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.application} viewed by {self.viewer.username}"

class ApplicationRating(models.Model):
    RATING_CHOICES = (
        (1, 'Poor'),
        (2, 'Fair'),
        (3, 'Good'),
        (4, 'Very Good'),
        (5, 'Excellent'),
    )
    
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='ratings')
    rater = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=RATING_CHOICES)
    comments = models.TextField(blank=True, null=True)
    rated_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.application} - {self.rating} stars by {self.rater.username}"
    
    class Meta:
        unique_together = ['application', 'rater']
