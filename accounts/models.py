from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.validators import FileExtensionValidator
from django.utils import timezone
import uuid
import secrets

class UserProfile(models.Model):
    USER_TYPES = (
        ('jobseeker', 'Job Seeker'),
        ('employer', 'Employer'),
        ('admin', 'Admin'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    user_type = models.CharField(max_length=20, choices=USER_TYPES, default='jobseeker')
    phone = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    zip_code = models.CharField(max_length=10, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.get_user_type_display()}"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.userprofile.save()

class JobSeekerProfile(models.Model):
    user_profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE)
    resume = models.FileField(
        upload_to='resumes/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx'])],
        blank=True,
        null=True
    )
    cover_letter = models.TextField(blank=True, null=True)
    expected_salary = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    preferred_location = models.CharField(max_length=200, blank=True, null=True)
    availability = models.CharField(max_length=50, blank=True, null=True)
    linkedin_url = models.URLField(blank=True, null=True)
    github_url = models.URLField(blank=True, null=True)
    portfolio_url = models.URLField(blank=True, null=True)
    skills = models.TextField(blank=True, null=True)
    experience_years = models.IntegerField(default=0)
    education_level = models.CharField(max_length=100, blank=True, null=True)
    certifications_text = models.TextField(blank=True, null=True)
    languages = models.TextField(blank=True, null=True)
    is_available_for_work = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user_profile.user.username} - Job Seeker Profile"

class Education(models.Model):
    DEGREE_TYPES = (
        ('high_school', 'High School'),
        ('associate', 'Associate Degree'),
        ('bachelor', 'Bachelor Degree'),
        ('master', 'Master Degree'),
        ('phd', 'PhD'),
        ('certification', 'Certification'),
        ('other', 'Other'),
    )
    
    job_seeker = models.ForeignKey(JobSeekerProfile, on_delete=models.CASCADE, related_name='educations')
    degree_type = models.CharField(max_length=20, choices=DEGREE_TYPES)
    institution = models.CharField(max_length=200)
    field_of_study = models.CharField(max_length=200)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    is_current = models.BooleanField(default=False)
    gpa = models.DecimalField(max_digits=3, decimal_places=2, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.institution} - {self.field_of_study}"

class Experience(models.Model):
    job_seeker = models.ForeignKey(JobSeekerProfile, on_delete=models.CASCADE, related_name='experiences')
    company_name = models.CharField(max_length=200)
    job_title = models.CharField(max_length=200)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    is_current = models.BooleanField(default=False)
    
    description = models.TextField()
    responsibilities = models.TextField(blank=True, null=True)
    achievements = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.job_title} at {self.company_name}"

class Skill(models.Model):
    SKILL_LEVELS = (
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('expert', 'Expert'),
    )
    
    job_seeker = models.ForeignKey(JobSeekerProfile, on_delete=models.CASCADE, related_name='skill_set')
    name = models.CharField(max_length=100)
    level = models.CharField(max_length=20, choices=SKILL_LEVELS, default='intermediate')
    years_of_experience = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} - {self.level}"

class Certification(models.Model):
    job_seeker = models.ForeignKey(JobSeekerProfile, on_delete=models.CASCADE, related_name='certifications')
    name = models.CharField(max_length=200)
    issuing_organization = models.CharField(max_length=200)
    issue_date = models.DateField()
    expiry_date = models.DateField(blank=True, null=True)
    credential_id = models.CharField(max_length=100, blank=True, null=True)
    credential_url = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} - {self.issuing_organization}"

class CareerPath(models.Model):
    CAREER_CATEGORIES = (
        ('technology', 'Technology'),
        ('healthcare', 'Healthcare'),
        ('finance', 'Finance'),
        ('marketing', 'Marketing'),
        ('education', 'Education'),
        ('engineering', 'Engineering'),
        ('design', 'Design'),
        ('sales', 'Sales'),
        ('operations', 'Operations'),
        ('consulting', 'Consulting'),
    )
    
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=50, choices=CAREER_CATEGORIES)
    description = models.TextField()
    required_skills = models.TextField(help_text="Comma-separated list of required skills")
    average_salary_range = models.CharField(max_length=100, blank=True, null=True)
    growth_outlook = models.CharField(max_length=200, blank=True, null=True)
    education_requirements = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

class CareerMilestone(models.Model):
    MILESTONE_TYPES = (
        ('skill', 'Skill Development'),
        ('certification', 'Certification'),
        ('project', 'Project Completion'),
        ('experience', 'Work Experience'),
        ('education', 'Educational Achievement'),
    )
    
    career_path = models.ForeignKey(CareerPath, on_delete=models.CASCADE, related_name='milestones')
    title = models.CharField(max_length=200)
    description = models.TextField()
    milestone_type = models.CharField(max_length=20, choices=MILESTONE_TYPES)
    order = models.IntegerField(default=0)
    estimated_duration = models.CharField(max_length=100, blank=True, null=True)
    resources = models.TextField(blank=True, null=True, help_text="Learning resources and links")
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.career_path.name} - {self.title}"

class UserCareerProgress(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='career_progress')
    career_path = models.ForeignKey(CareerPath, on_delete=models.CASCADE)
    selected_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    target_completion_date = models.DateField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        unique_together = ['user_profile', 'career_path']
    
    def __str__(self):
        return f"{self.user_profile.user.username} - {self.career_path.name}"
    
    def get_completion_percentage(self):
        total_milestones = self.career_path.milestones.count()
        if total_milestones == 0:
            return 0
        completed_milestones = self.milestone_progress.filter(is_completed=True).count()
        return round((completed_milestones / total_milestones) * 100, 1)
    
    def get_next_milestone(self):
        return self.milestone_progress.filter(is_completed=False).order_by('milestone__order').first()

class MilestoneProgress(models.Model):
    user_career_progress = models.ForeignKey(UserCareerProgress, on_delete=models.CASCADE, related_name='milestone_progress')
    milestone = models.ForeignKey(CareerMilestone, on_delete=models.CASCADE)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(blank=True, null=True)


class CustomCareerRoadmap(models.Model):
    """User-created custom career roadmaps"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('completed', 'Completed'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='custom_roadmaps')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    target_position = models.CharField(max_length=200)
    target_company = models.CharField(max_length=200, blank=True)
    target_salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    timeline_months = models.PositiveIntegerField(default=12)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"
    
    @property
    def progress_percentage(self):
        """Calculate overall progress percentage based on completed steps"""
        steps = self.steps.all()
        if not steps.exists():
            return 0
        
        total_progress = sum(step.progress_percentage for step in steps)
        return round(total_progress / steps.count(), 1)
    
    @property
    def completed_steps_count(self):
        """Count of completed steps"""
        return self.steps.filter(is_completed=True).count()
    
    @property
    def total_steps_count(self):
        """Total count of steps"""
        return self.steps.count()
    
    @property
    def is_completed(self):
        """Check if roadmap is completed"""
        return self.status == 'completed' or (
            self.steps.exists() and 
            self.steps.filter(is_completed=False).count() == 0
        )
    
    def get_current_step(self):
        return self.steps.filter(is_completed=False).order_by('order').first()
    
    def get_next_milestone(self):
        return self.steps.filter(is_completed=False, step_type='milestone').order_by('order').first()


class CustomRoadmapStep(models.Model):
    """Individual steps in a custom career roadmap"""
    STEP_TYPES = (
        ('skill', 'Skill Development'),
        ('certification', 'Certification'),
        ('project', 'Project'),
        ('experience', 'Work Experience'),
        ('education', 'Education/Course'),
        ('networking', 'Networking'),
        ('milestone', 'Major Milestone'),
        ('other', 'Other'),
    )
    
    PRIORITY_LEVELS = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    )
    
    roadmap = models.ForeignKey(CustomCareerRoadmap, on_delete=models.CASCADE, related_name='steps')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    step_type = models.CharField(max_length=20, choices=STEP_TYPES)
    priority = models.CharField(max_length=10, choices=PRIORITY_LEVELS, default='medium')
    order = models.IntegerField(default=0)
    estimated_duration = models.CharField(max_length=100, blank=True, null=True)
    resources = models.TextField(blank=True, null=True, help_text="Links, courses, books, etc.")
    cost_estimate = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.roadmap.title} - {self.title}"
    
    @property
    def progress_percentage(self):
        """Get the latest progress percentage from progress logs"""
        latest_log = self.progress_logs.order_by('-created_at').first()
        if latest_log:
            return latest_log.progress_percentage
        return 0 if not self.is_completed else 100
    
    @property
    def recent_progress(self):
        """Get recent progress updates (last 5)"""
        return self.progress_logs.order_by('-created_at')[:5]
    
    @property
    def resources_list(self):
        """Convert resources text to list of URLs"""
        if not self.resources:
            return []
        return [url.strip() for url in self.resources.split('\n') if url.strip()]
    
    def get_step_type_color(self):
        """Return Bootstrap color class for step type"""
        colors = {
            'skill': 'primary',
            'certification': 'success',
            'project': 'info',
            'experience': 'warning',
            'education': 'secondary',
            'networking': 'dark',
            'milestone': 'danger',
            'other': 'light'
        }
        return colors.get(self.step_type, 'secondary')
    
    def get_priority_color(self):
        """Return Bootstrap color class for priority"""
        colors = {
            'low': 'success',
            'medium': 'warning',
            'high': 'danger',
            'critical': 'dark'
        }
        return colors.get(self.priority, 'secondary')


class RoadmapProgressLog(models.Model):
    """Track progress updates and notes for roadmap steps"""
    step = models.ForeignKey(CustomRoadmapStep, on_delete=models.CASCADE, related_name='progress_logs')
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    progress_percentage = models.IntegerField(default=0, help_text="Progress percentage (0-100)")
    notes = models.TextField()
    evidence_url = models.URLField(blank=True, null=True, help_text="Link to portfolio, certificate, etc.")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.step.title} - {self.progress_percentage}% - {self.created_at.date()}"
    
    def mark_completed(self):
        self.is_completed = True
        self.completed_at = timezone.now()
        self.progress_percentage = 100
        self.save()

class CareerAssessment(models.Model):
    ASSESSMENT_TYPES = (
        ('skill_test', 'Skill Test'),
        ('knowledge_quiz', 'Knowledge Quiz'),
        ('project_review', 'Project Review'),
        ('self_evaluation', 'Self Evaluation'),
    )
    
    user_career_progress = models.ForeignKey(UserCareerProgress, on_delete=models.CASCADE, related_name='assessments')
    milestone = models.ForeignKey(CareerMilestone, on_delete=models.CASCADE, blank=True, null=True)
    assessment_type = models.CharField(max_length=20, choices=ASSESSMENT_TYPES)
    title = models.CharField(max_length=200)
    description = models.TextField()
    score = models.IntegerField(blank=True, null=True, help_text="Score out of 100")
    feedback = models.TextField(blank=True, null=True)
    taken_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user_career_progress.user_profile.user.username} - Assessment: {self.title}"

class Resume(models.Model):
    TEMPLATE_CHOICES = [
        ('modern-clean', 'Modern Clean'),
        ('modern-sidebar', 'Modern Sidebar'),
        ('professional-classic', 'Professional Classic'),
        ('professional-timeline', 'Professional Timeline'),
        ('creative-portfolio', 'Creative Portfolio'),
        ('creative-colorful', 'Creative Colorful'),
        ('executive-premium', 'Executive Premium'),
        ('executive-minimal', 'Executive Minimal'),
    ]
    
    COLOR_SCHEMES = [
        ('blue', 'Blue'),
        ('green', 'Green'),
        ('red', 'Red'),
        ('purple', 'Purple'),
        ('orange', 'Orange'),
        ('teal', 'Teal'),
        ('gray', 'Gray'),
        ('black', 'Black'),
    ]
    
    FONT_CHOICES = [
        ('arial', 'Arial'),
        ('helvetica', 'Helvetica'),
        ('times', 'Times New Roman'),
        ('georgia', 'Georgia'),
        ('calibri', 'Calibri'),
        ('open-sans', 'Open Sans'),
        ('roboto', 'Roboto'),
        ('lato', 'Lato'),
    ]
    
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='resumes')
    title = models.CharField(max_length=200, default='My Resume')
    template = models.CharField(max_length=50, choices=TEMPLATE_CHOICES, default='modern-clean')
    color_scheme = models.CharField(max_length=20, choices=COLOR_SCHEMES, default='blue')
    font_family = models.CharField(max_length=30, choices=FONT_CHOICES, default='arial')
    
    # Personal Information
    full_name = models.CharField(max_length=200, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    website = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)
    github_url = models.URLField(blank=True)
    profile_picture = models.ImageField(upload_to='resume_photos/', blank=True, null=True)
    
    # Professional Summary
    professional_summary = models.TextField(blank=True, help_text='Brief professional summary or objective')
    
    # Settings
    is_public = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    section_order = models.JSONField(default=list, help_text='Order of resume sections')
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_exported = models.DateTimeField(blank=True, null=True)
    export_count = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.user_profile.user.username} - {self.title}"
    
    def get_completion_percentage(self):
        """Calculate resume completion percentage"""
        total_fields = 15  # Adjust based on required fields
        completed_fields = 0
        
        if self.full_name: completed_fields += 1
        if self.email: completed_fields += 1
        if self.phone: completed_fields += 1
        if self.professional_summary: completed_fields += 1
        if self.work_experiences.exists(): completed_fields += 3
        if self.educations.exists(): completed_fields += 2
        if self.skills.exists(): completed_fields += 2
        if self.projects.exists(): completed_fields += 1
        if self.certifications.exists(): completed_fields += 1
        if self.achievements.exists(): completed_fields += 1
        if self.references.exists(): completed_fields += 1
        
        return min(round((completed_fields / total_fields) * 100), 100)


class ResumeWorkExperience(models.Model):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='work_experiences')
    company_name = models.CharField(max_length=200)
    position = models.CharField(max_length=200)
    location = models.CharField(max_length=200, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    is_current = models.BooleanField(default=False)
    description = models.TextField(help_text='Job responsibilities and achievements')
    order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-start_date', 'order']
    
    def __str__(self):
        return f"{self.position} at {self.company_name}"


class ResumeEducation(models.Model):
    DEGREE_TYPES = [
        ('high_school', 'High School'),
        ('associate', 'Associate Degree'),
        ('bachelor', 'Bachelor\'s Degree'),
        ('master', 'Master\'s Degree'),
        ('doctorate', 'Doctorate'),
        ('certificate', 'Certificate'),
        ('diploma', 'Diploma'),
    ]
    
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='educations')
    institution = models.CharField(max_length=200)
    degree_type = models.CharField(max_length=20, choices=DEGREE_TYPES)
    field_of_study = models.CharField(max_length=200)
    location = models.CharField(max_length=200, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    gpa = models.DecimalField(max_digits=3, decimal_places=2, blank=True, null=True)
    description = models.TextField(blank=True, help_text='Relevant coursework, honors, etc.')
    order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-start_date', 'order']
    
    def __str__(self):
        return f"{self.degree_type} in {self.field_of_study} from {self.institution}"


class ResumeSkill(models.Model):
    SKILL_LEVELS = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('expert', 'Expert'),
    ]
    
    SKILL_CATEGORIES = [
        ('technical', 'Technical'),
        ('soft', 'Soft Skills'),
        ('language', 'Languages'),
        ('tools', 'Tools & Software'),
        ('other', 'Other'),
    ]
    
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='skills')
    name = models.CharField(max_length=100)
    level = models.CharField(max_length=20, choices=SKILL_LEVELS, default='intermediate')
    category = models.CharField(max_length=20, choices=SKILL_CATEGORIES, default='technical')
    years_experience = models.IntegerField(blank=True, null=True)
    order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['category', 'order', 'name']
        unique_together = ['resume', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.level})"


class ResumeProject(models.Model):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='projects')
    title = models.CharField(max_length=200)
    description = models.TextField()
    technologies = models.CharField(max_length=500, help_text='Comma-separated list of technologies used')
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    project_url = models.URLField(blank=True)
    github_url = models.URLField(blank=True)
    order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-start_date', 'order']
    
    def __str__(self):
        return self.title


class ResumeCertification(models.Model):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='certifications')
    name = models.CharField(max_length=200)
    issuing_organization = models.CharField(max_length=200)
    issue_date = models.DateField()
    expiry_date = models.DateField(blank=True, null=True)
    credential_id = models.CharField(max_length=100, blank=True)
    credential_url = models.URLField(blank=True)
    order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-issue_date', 'order']
    
    def __str__(self):
        return f"{self.name} - {self.issuing_organization}"


class ResumeAchievement(models.Model):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='achievements')
    title = models.CharField(max_length=200)
    description = models.TextField()
    date_achieved = models.DateField(blank=True, null=True)
    organization = models.CharField(max_length=200, blank=True)
    order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-date_achieved', 'order']
    
    def __str__(self):
        return self.title


class ResumeVolunteerExperience(models.Model):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='volunteer_experiences')
    organization = models.CharField(max_length=200)
    role = models.CharField(max_length=200)
    location = models.CharField(max_length=200, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    is_current = models.BooleanField(default=False)
    description = models.TextField(help_text='Volunteer responsibilities and impact')
    order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-start_date', 'order']
    
    def __str__(self):
        return f"{self.role} at {self.organization}"


class ResumeLanguage(models.Model):
    PROFICIENCY_LEVELS = [
        ('native', 'Native'),
        ('fluent', 'Fluent'),
        ('advanced', 'Advanced'),
        ('intermediate', 'Intermediate'),
        ('basic', 'Basic'),
    ]
    
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='languages')
    language = models.CharField(max_length=100)
    proficiency = models.CharField(max_length=20, choices=PROFICIENCY_LEVELS)
    certification = models.CharField(max_length=200, blank=True, help_text='e.g., IELTS, TOEFL score')
    order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['order', 'language']
        unique_together = ['resume', 'language']
    
    def __str__(self):
        return f"{self.language} ({self.proficiency})"


class ResumeReference(models.Model):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='references')
    name = models.CharField(max_length=200)
    position = models.CharField(max_length=200)
    company = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    relationship = models.CharField(max_length=100, help_text='e.g., Former Manager, Colleague')
    order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['order', 'name']
    
    def __str__(self):
        return f"{self.name} - {self.position}"


class ResumeExport(models.Model):
    EXPORT_FORMATS = [
        ('pdf', 'PDF'),
        ('docx', 'Word Document'),
        ('html', 'HTML'),
    ]
    
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='exports')
    format = models.CharField(max_length=10, choices=EXPORT_FORMATS)
    file_path = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    download_count = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.resume.title} - {self.format.upper()}"


class ResumeAnalytics(models.Model):
    resume = models.OneToOneField(Resume, on_delete=models.CASCADE, related_name='analytics')
    
    # Content Analysis
    word_count = models.IntegerField(default=0)
    readability_score = models.FloatField(default=0.0)
    keyword_density = models.JSONField(default=dict)
    
    # AI Suggestions
    grammar_suggestions = models.JSONField(default=list)
    content_suggestions = models.JSONField(default=list)
    keyword_suggestions = models.JSONField(default=list)
    
    # Performance Metrics
    ats_score = models.IntegerField(default=0, help_text='ATS compatibility score (0-100)')
    completeness_score = models.IntegerField(default=0, help_text='Resume completeness score (0-100)')
    
    # Timestamps
    last_analyzed = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Analytics for {self.resume.title}"

class EmailVerificationToken(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Verification token for {self.user.username}"
    
    def is_valid(self):
        return not self.is_used and self.expires_at > timezone.now()
    
    @classmethod
    def generate_token(cls, user):
        # Delete any existing tokens for this user
        cls.objects.filter(user=user).delete()
        
        # Generate a new token
        token = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timezone.timedelta(days=2)
        
        # Create and return the token object
        return cls.objects.create(
            user=user,
            token=token,
            expires_at=expires_at
        )

class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('application_received', 'Application Received'),
        ('application_status', 'Application Status Update'),
        ('new_job_posting', 'New Job Posting'),
        ('new_message', 'New Message'),
        ('system', 'System Notification'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES)
    content = models.TextField()
    related_id = models.IntegerField(blank=True, null=True, help_text="ID of related object (job, application, etc.)")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.get_notification_type_display()}"
    
    def mark_as_read(self):
        self.is_read = True
        self.save()
    
    @classmethod
    def create_notification(cls, user, notification_type, content, related_id=None):
        return cls.objects.create(
            user=user,
            notification_type=notification_type,
            content=content,
            related_id=related_id
        )


# AI-Powered Interview Preparation Models
class InterviewQuestion(models.Model):
    DIFFICULTY_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('expert', 'Expert'),
    ]
    
    CATEGORY_CHOICES = [
        ('behavioral', 'Behavioral'),
        ('technical', 'Technical'),
        ('situational', 'Situational'),
        ('competency', 'Competency'),
        ('industry_specific', 'Industry Specific'),
        ('leadership', 'Leadership'),
        ('problem_solving', 'Problem Solving'),
        ('communication', 'Communication'),
    ]
    
    INDUSTRY_CHOICES = [
        ('technology', 'Technology'),
        ('finance', 'Finance'),
        ('healthcare', 'Healthcare'),
        ('marketing', 'Marketing'),
        ('sales', 'Sales'),
        ('education', 'Education'),
        ('consulting', 'Consulting'),
        ('engineering', 'Engineering'),
        ('design', 'Design'),
        ('operations', 'Operations'),
        ('general', 'General'),
    ]
    
    question_text = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    industry = models.CharField(max_length=20, choices=INDUSTRY_CHOICES, default='general')
    difficulty = models.CharField(max_length=15, choices=DIFFICULTY_CHOICES, default='intermediate')
    model_answer = models.TextField()
    guidance_tips = models.TextField()
    keywords = models.JSONField(default=list, help_text="Important keywords for this question")
    time_limit = models.IntegerField(default=120, help_text="Recommended time limit in seconds")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['category', 'difficulty', 'question_text']
    
    def __str__(self):
        return f"{self.category.title()} - {self.question_text[:50]}..."


class InterviewSession(models.Model):
    SESSION_TYPES = [
        ('practice', 'Practice Session'),
        ('mock_interview', 'Mock Interview'),
        ('quick_practice', 'Quick Practice'),
        ('timed_challenge', 'Timed Challenge'),
    ]
    
    STATUS_CHOICES = [
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('paused', 'Paused'),
        ('abandoned', 'Abandoned'),
    ]
    
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='interview_sessions')
    session_type = models.CharField(max_length=20, choices=SESSION_TYPES, default='practice')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='in_progress')
    industry_focus = models.CharField(max_length=20, choices=InterviewQuestion.INDUSTRY_CHOICES, default='general')
    difficulty_level = models.CharField(max_length=15, choices=InterviewQuestion.DIFFICULTY_CHOICES, default='intermediate')
    total_questions = models.IntegerField(default=5)
    questions_answered = models.IntegerField(default=0)
    overall_score = models.FloatField(null=True, blank=True)
    session_duration = models.IntegerField(null=True, blank=True, help_text="Duration in seconds")
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-started_at']
    
    def __str__(self):
        return f"{self.user_profile.user.username} - {self.session_type} ({self.status})"
    
    @property
    def completion_percentage(self):
        if self.total_questions == 0:
            return 0
        return (self.questions_answered / self.total_questions) * 100


class InterviewAnswer(models.Model):
    INPUT_TYPES = [
        ('text', 'Text Input'),
        ('voice', 'Voice Input'),
        ('mixed', 'Mixed Input'),
    ]
    
    session = models.ForeignKey(InterviewSession, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(InterviewQuestion, on_delete=models.CASCADE)
    answer_text = models.TextField()
    voice_file_path = models.CharField(max_length=500, blank=True, null=True)
    input_type = models.CharField(max_length=10, choices=INPUT_TYPES, default='text')
    response_time = models.IntegerField(help_text="Time taken to answer in seconds")
    
    # AI Evaluation Scores
    content_score = models.FloatField(default=0.0, help_text="Content relevance and completeness (0-100)")
    clarity_score = models.FloatField(default=0.0, help_text="Clarity and structure (0-100)")
    confidence_score = models.FloatField(default=0.0, help_text="Confidence and tone (0-100)")
    keyword_score = models.FloatField(default=0.0, help_text="Keyword usage (0-100)")
    overall_score = models.FloatField(default=0.0, help_text="Overall score (0-100)")
    
    # AI Feedback
    strengths = models.JSONField(default=list, help_text="List of identified strengths")
    weaknesses = models.JSONField(default=list, help_text="List of areas for improvement")
    suggestions = models.JSONField(default=list, help_text="Specific improvement suggestions")
    alternative_phrases = models.JSONField(default=list, help_text="Suggested alternative phrasings")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Answer to: {self.question.question_text[:30]}... (Score: {self.overall_score})"


class InterviewAnalytics(models.Model):
    user_profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name='interview_analytics')
    
    # Overall Statistics
    total_sessions = models.IntegerField(default=0)
    total_questions_answered = models.IntegerField(default=0)
    total_practice_time = models.IntegerField(default=0, help_text="Total practice time in minutes")
    
    # Performance Metrics
    average_score = models.FloatField(default=0.0)
    best_score = models.FloatField(default=0.0)
    improvement_rate = models.FloatField(default=0.0, help_text="Improvement percentage over time")
    
    # Category Performance
    behavioral_avg_score = models.FloatField(default=0.0)
    technical_avg_score = models.FloatField(default=0.0)
    situational_avg_score = models.FloatField(default=0.0)
    communication_avg_score = models.FloatField(default=0.0)
    
    # Skill Tracking
    confidence_trend = models.JSONField(default=list, help_text="Confidence scores over time")
    clarity_trend = models.JSONField(default=list, help_text="Clarity scores over time")
    content_trend = models.JSONField(default=list, help_text="Content scores over time")
    
    # Streaks and Achievements
    current_streak = models.IntegerField(default=0, help_text="Current daily practice streak")
    longest_streak = models.IntegerField(default=0, help_text="Longest daily practice streak")
    achievements = models.JSONField(default=list, help_text="Unlocked achievements")
    
    last_updated = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Analytics for {self.user_profile.user.username}"
    
    def update_analytics(self):
        """Update analytics based on recent sessions and answers"""
        sessions = self.user_profile.interview_sessions.filter(status='completed')
        answers = InterviewAnswer.objects.filter(session__user_profile=self.user_profile)
        
        if sessions.exists():
            self.total_sessions = sessions.count()
            self.average_score = answers.aggregate(avg_score=models.Avg('overall_score'))['avg_score'] or 0.0
            self.best_score = answers.aggregate(max_score=models.Max('overall_score'))['max_score'] or 0.0
            
            # Calculate category averages
            behavioral_answers = answers.filter(question__category='behavioral')
            if behavioral_answers.exists():
                self.behavioral_avg_score = behavioral_answers.aggregate(avg=models.Avg('overall_score'))['avg'] or 0.0
            
            technical_answers = answers.filter(question__category='technical')
            if technical_answers.exists():
                self.technical_avg_score = technical_answers.aggregate(avg=models.Avg('overall_score'))['avg'] or 0.0
            
            situational_answers = answers.filter(question__category='situational')
            if situational_answers.exists():
                self.situational_avg_score = situational_answers.aggregate(avg=models.Avg('overall_score'))['avg'] or 0.0
            
            communication_answers = answers.filter(question__category='communication')
            if communication_answers.exists():
                self.communication_avg_score = communication_answers.aggregate(avg=models.Avg('overall_score'))['avg'] or 0.0
        
        self.save()


class InterviewFeedback(models.Model):
    FEEDBACK_TYPES = [
        ('strength', 'Strength'),
        ('improvement', 'Area for Improvement'),
        ('suggestion', 'Suggestion'),
        ('tip', 'Pro Tip'),
    ]
    
    answer = models.ForeignKey(InterviewAnswer, on_delete=models.CASCADE, related_name='detailed_feedback')
    feedback_type = models.CharField(max_length=15, choices=FEEDBACK_TYPES)
    title = models.CharField(max_length=200)
    description = models.TextField()
    priority = models.IntegerField(default=1, help_text="Priority level (1-5)")
    is_actionable = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-priority', 'created_at']
    
    def __str__(self):
        return f"{self.feedback_type.title()}: {self.title}"


# Next-Generation ATS-Friendly Resume Builder Models
class JobDescription(models.Model):
    """Store job descriptions for ATS analysis"""
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='job_descriptions')
    title = models.CharField(max_length=200)
    company = models.CharField(max_length=200, blank=True)
    description = models.TextField()
    requirements = models.TextField(blank=True)
    
    # Extracted data
    extracted_keywords = models.JSONField(default=list, help_text="AI-extracted keywords")
    required_skills = models.JSONField(default=list, help_text="AI-extracted required skills")
    preferred_skills = models.JSONField(default=list, help_text="AI-extracted preferred skills")
    experience_level = models.CharField(max_length=50, blank=True)
    education_requirements = models.JSONField(default=list)
    
    # Analysis metadata
    keyword_count = models.IntegerField(default=0)
    analysis_score = models.FloatField(default=0.0, help_text="Quality of job description analysis")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} at {self.company or 'Unknown Company'}"


class ATSOptimization(models.Model):
    """ATS optimization analysis for resumes"""
    resume = models.OneToOneField(Resume, on_delete=models.CASCADE, related_name='ats_optimization')
    job_description = models.ForeignKey(JobDescription, on_delete=models.CASCADE, null=True, blank=True)
    
    # ATS Scores
    overall_ats_score = models.IntegerField(default=0, help_text="Overall ATS score (0-100)")
    keyword_match_score = models.IntegerField(default=0, help_text="Keyword match score (0-100)")
    formatting_score = models.IntegerField(default=0, help_text="Formatting compliance score (0-100)")
    content_relevance_score = models.IntegerField(default=0, help_text="Content relevance score (0-100)")
    
    # Keyword Analysis
    matched_keywords = models.JSONField(default=list, help_text="Keywords found in resume")
    missing_keywords = models.JSONField(default=list, help_text="Important keywords missing from resume")
    keyword_density = models.JSONField(default=dict, help_text="Keyword frequency analysis")
    
    # Content Analysis
    weak_bullet_points = models.JSONField(default=list, help_text="Bullet points needing improvement")
    suggested_improvements = models.JSONField(default=list, help_text="AI-generated improvement suggestions")
    action_words_used = models.JSONField(default=list, help_text="Strong action words found")
    missing_action_words = models.JSONField(default=list, help_text="Suggested action words to add")
    
    # Compliance Issues
    formatting_issues = models.JSONField(default=list, help_text="ATS formatting problems")
    compliance_warnings = models.JSONField(default=list, help_text="ATS compliance warnings")
    
    # Recommendations
    priority_fixes = models.JSONField(default=list, help_text="High-priority improvements")
    quick_wins = models.JSONField(default=list, help_text="Easy improvements for quick score boost")
    
    last_analyzed = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"ATS Analysis for {self.resume.title} (Score: {self.overall_ats_score})"


class ResumeVersion(models.Model):
    """Multiple versions of resumes for different jobs"""
    base_resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='versions')
    job_description = models.ForeignKey(JobDescription, on_delete=models.CASCADE, null=True, blank=True)
    
    version_name = models.CharField(max_length=200)
    description = models.TextField(blank=True, help_text="What makes this version unique")
    
    # Tailored content
    tailored_summary = models.TextField(blank=True)
    emphasized_skills = models.JSONField(default=list, help_text="Skills to emphasize for this version")
    reordered_sections = models.JSONField(default=list, help_text="Custom section order")
    
    # Performance tracking
    applications_sent = models.IntegerField(default=0)
    responses_received = models.IntegerField(default=0)
    interviews_scheduled = models.IntegerField(default=0)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.base_resume.title} - {self.version_name}"
    
    @property
    def response_rate(self):
        if self.applications_sent == 0:
            return 0
        return round((self.responses_received / self.applications_sent) * 100, 1)


class AIBulletPoint(models.Model):
    """AI-generated and enhanced bullet points"""
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='ai_bullet_points')
    section_type = models.CharField(max_length=50, default='experience', help_text="experience, education, projects, etc.")
    
    original_text = models.TextField(help_text="Original bullet point")
    enhanced_text = models.TextField(help_text="AI-enhanced version")
    
    # Enhancement details
    improvements_made = models.JSONField(default=list, help_text="List of improvements applied")
    action_words_added = models.JSONField(default=list, help_text="Strong action words added")
    quantification_added = models.BooleanField(default=False)
    
    # Scoring
    original_score = models.IntegerField(default=0, help_text="Original bullet point score (0-100)")
    enhanced_score = models.IntegerField(default=0, help_text="Enhanced bullet point score (0-100)")
    improvement_percentage = models.FloatField(default=0.0)
    
    is_applied = models.BooleanField(default=False, help_text="Whether user applied this enhancement")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-enhanced_score', '-created_at']
    
    def __str__(self):
        return f"Enhanced: {self.original_text[:50]}..."


class ResumeTemplate(models.Model):
    """ATS-compliant resume templates"""
    name = models.CharField(max_length=100)
    description = models.TextField()
    category = models.CharField(max_length=50, choices=[
        ('ats-optimized', 'ATS Optimized'),
        ('creative', 'Creative'),
        ('executive', 'Executive'),
        ('technical', 'Technical'),
        ('academic', 'Academic'),
    ], default='ats-optimized')
    
    # Template configuration
    html_template = models.TextField(help_text="HTML template code")
    css_styles = models.TextField(help_text="CSS styles")
    
    # ATS compatibility
    ats_score = models.IntegerField(default=100, help_text="ATS compatibility score (0-100)")
    supports_ats_parsing = models.BooleanField(default=True)
    
    # Features
    supports_sections = models.JSONField(default=list, help_text="Supported resume sections")
    color_customizable = models.BooleanField(default=True)
    font_customizable = models.BooleanField(default=True)
    
    is_premium = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    usage_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-ats_score', 'name']
    
    def __str__(self):
        return f"{self.name} (ATS: {self.ats_score}%)"


class ResumeComparison(models.Model):
    """Compare different resume versions"""
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='resume_comparisons')
    resume_a = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='comparisons_as_a')
    resume_b = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='comparisons_as_b')
    
    # Comparison results
    ats_score_diff = models.IntegerField(default=0, help_text="ATS score difference (B - A)")
    keyword_match_diff = models.IntegerField(default=0)
    content_quality_diff = models.IntegerField(default=0)
    
    # Detailed analysis
    improvements_found = models.JSONField(default=list, help_text="Improvements in resume B")
    regressions_found = models.JSONField(default=list, help_text="Areas where resume B is worse")
    recommendations = models.JSONField(default=list, help_text="Recommendations based on comparison")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Comparison: {self.resume_a.title} vs {self.resume_b.title}"


class CoverLetter(models.Model):
    """AI-assisted cover letter builder"""
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='cover_letters')
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='cover_letters', null=True, blank=True)
    job_description = models.ForeignKey(JobDescription, on_delete=models.CASCADE, null=True, blank=True)
    
    title = models.CharField(max_length=200, default='Cover Letter')
    content = models.TextField()
    
    # AI enhancements
    ai_suggestions = models.JSONField(default=list, help_text="AI improvement suggestions")
    tone_analysis = models.JSONField(default=dict, help_text="Tone and style analysis")
    
    # Performance
    ats_score = models.IntegerField(default=0, help_text="ATS compatibility score")
    readability_score = models.FloatField(default=0.0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.title} for {self.job_description.title if self.job_description else 'General'}"


class JobApplicationTracker(models.Model):
    """Track job applications with resume versions"""
    STATUS_CHOICES = [
        ('applied', 'Applied'),
        ('under_review', 'Under Review'),
        ('interview_scheduled', 'Interview Scheduled'),
        ('interviewed', 'Interviewed'),
        ('offer_received', 'Offer Received'),
        ('rejected', 'Rejected'),
        ('withdrawn', 'Withdrawn'),
    ]
    
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='job_applications')
    job_description = models.ForeignKey(JobDescription, on_delete=models.CASCADE)
    resume_version = models.ForeignKey(ResumeVersion, on_delete=models.CASCADE, null=True, blank=True)
    cover_letter = models.ForeignKey(CoverLetter, on_delete=models.CASCADE, null=True, blank=True)
    
    company_name = models.CharField(max_length=200)
    position_title = models.CharField(max_length=200)
    application_url = models.URLField(blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='applied')
    applied_date = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    
    # Follow-up tracking
    follow_up_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    
    # Analytics
    resume_ats_score = models.IntegerField(default=0, help_text="ATS score when applied")
    
    class Meta:
        ordering = ['-applied_date']
    
    def __str__(self):
        return f"{self.position_title} at {self.company_name} ({self.status})"


class ResumeAnalyticsReport(models.Model):
    """Detailed analytics and insights"""
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='analytics_reports')
    
    # Performance metrics
    total_applications = models.IntegerField(default=0)
    total_responses = models.IntegerField(default=0)
    total_interviews = models.IntegerField(default=0)
    
    # Resume insights
    best_performing_keywords = models.JSONField(default=list)
    underperforming_sections = models.JSONField(default=list)
    improvement_suggestions = models.JSONField(default=list)
    
    # Trends
    ats_score_trend = models.JSONField(default=list, help_text="ATS scores over time")
    response_rate_trend = models.JSONField(default=list, help_text="Response rates over time")
    
    # Industry insights
    industry_benchmarks = models.JSONField(default=dict)
    competitive_analysis = models.JSONField(default=dict)
    
    generated_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-generated_at']
    
    def __str__(self):
        return f"Analytics Report for {self.user_profile.user.username} - {self.generated_at.date()}"


class ResumeExport(models.Model):
    """Model to track resume exports and cloud storage"""
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='exports')
    format = models.CharField(max_length=10, choices=[
        ('PDF', 'PDF'),
        ('DOCX', 'DOCX'),
        ('TXT', 'Plain Text'),
        ('HTML', 'HTML')
    ])
    filename = models.CharField(max_length=255)
    cloud_url = models.URLField(blank=True, null=True)
    file_size = models.PositiveIntegerField(null=True, blank=True)  # Size in bytes
    download_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.resume.title} - {self.format} Export"
    
    @property
    def file_size_mb(self):
        """Return file size in MB"""
        if self.file_size:
            return round(self.file_size / (1024 * 1024), 2)
        return 0


# Security Questions for Password Recovery
class SecurityQuestion(models.Model):
    """Predefined security questions for password recovery"""
    question_text = models.CharField(max_length=200, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['question_text']
    
    def __str__(self):
        return self.question_text


class UserSecurityAnswer(models.Model):
    """User answers to security questions for password recovery"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='security_answers')
    security_question = models.ForeignKey(SecurityQuestion, on_delete=models.CASCADE)
    answer = models.CharField(max_length=200, help_text="Answer will be stored in lowercase for case-insensitive matching")
    answer_hash = models.TextField(help_text="Hashed version of the answer for additional security")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'security_question']
        ordering = ['security_question__question_text']
    
    def save(self, *args, **kwargs):
        # Store answer in lowercase for case-insensitive matching
        self.answer = self.answer.lower().strip()
        # Ensure answer_hash is always populated to satisfy NOT NULL constraint
        if not hasattr(self, 'answer_hash') or not self.answer_hash:
            self.answer_hash = self.answer
        super().save(*args, **kwargs)
    
    def check_answer(self, provided_answer):
        """Check if provided answer matches stored answer (case-insensitive)"""
        return self.answer == provided_answer.lower().strip()
    
    def __str__(self):
        return f"{self.user.username} - {self.security_question.question_text}"


class PasswordResetSession(models.Model):
    """Track password reset sessions using security questions"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_reset_sessions')
    session_token = models.CharField(max_length=100, unique=True)
    questions_answered_correctly = models.IntegerField(default=0)
    is_verified = models.BooleanField(default=False)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Password reset session for {self.user.username}"
    
    def is_valid(self):
        """Check if session is still valid"""
        return not self.is_used and self.expires_at > timezone.now()
    
    def mark_as_used(self):
        """Mark session as used"""
        self.is_used = True
        self.save()
    
    @classmethod
    def create_session(cls, user):
        """Create a new password reset session"""
        # Delete any existing sessions for this user
        cls.objects.filter(user=user).delete()
        
        # Generate session token
        token = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timezone.timedelta(hours=1)  # 1 hour expiry
        
        return cls.objects.create(
            user=user,
            session_token=token,
            expires_at=expires_at
        )
