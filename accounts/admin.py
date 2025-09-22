from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    UserProfile, JobSeekerProfile, Education, Experience, 
    Skill, Certification, CoverLetter, JobDescription, Resume, JobApplicationTracker,
    ResumeAnalyticsReport
)

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'User Profile'

class JobSeekerProfileInline(admin.StackedInline):
    model = JobSeekerProfile
    can_delete = False
    verbose_name_plural = 'Job Seeker Profile'
    extra = 0

class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'get_full_name', 'user_type_badge', 'is_staff', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'date_joined', 'userprofile__user_type')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    ordering = ('-date_joined',)
    list_per_page = 25
    
    def user_type_badge(self, obj):
        if hasattr(obj, 'userprofile'):
            user_type = obj.userprofile.user_type
            colors = {
                'job_seeker': '#10b981',
                'employer': '#3b82f6',
                'admin': '#f59e0b'
            }
            color = colors.get(user_type, '#64748b')
            return format_html(
                '<span style="background: {}; color: white; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 500;">{}</span>',
                color, user_type.replace('_', ' ').title()
            )
        return format_html('<span style="color: #64748b;">No Profile</span>')
    user_type_badge.short_description = 'User Type'
    user_type_badge.admin_order_field = 'userprofile__user_type'

class EducationAdmin(admin.ModelAdmin):
    list_display = ('institution', 'field_of_study', 'degree_type', 'job_seeker', 'start_date', 'end_date', 'is_current')
    list_filter = ('degree_type', 'is_current', 'start_date')
    search_fields = ('institution', 'field_of_study', 'job_seeker__user_profile__user__username')
    date_hierarchy = 'start_date'

class ExperienceAdmin(admin.ModelAdmin):
    list_display = ('user_link', 'job_title', 'company_name', 'duration_display', 'current_badge')
    list_filter = ('is_current', 'start_date', 'end_date')
    search_fields = ('job_seeker__user_profile__user__username', 'job_title', 'company_name')
    ordering = ('-start_date',)
    list_per_page = 25
    
    def user_link(self, obj):
        user = obj.job_seeker.user_profile.user
        url = reverse('admin:auth_user_change', args=[user.pk])
        return format_html('<a href="{}" style="color: #3b82f6; text-decoration: none;">{}</a>', url, user.get_full_name() or user.username)
    user_link.short_description = 'User'
    user_link.admin_order_field = 'job_seeker__user_profile__user__username'
    
    def duration_display(self, obj):
        from datetime import date
        start = obj.start_date
        end = obj.end_date or date.today()
        years = (end - start).days // 365
        months = ((end - start).days % 365) // 30
        duration = f"{years}y {months}m" if years > 0 else f"{months}m"
        return format_html('<span style="font-weight: 500;">{}</span>', duration)
    duration_display.short_description = 'Duration'
    
    def current_badge(self, obj):
        if obj.is_current:
            return format_html(
                '<span style="background: #10b981; color: white; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 500;">Current</span>'
            )
        return format_html(
            '<span style="background: #64748b; color: white; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 500;">Past</span>'
        )
    current_badge.short_description = 'Status'

class JobSeekerProfileAdmin(admin.ModelAdmin):
    list_display = ('user_link', 'resume', 'expected_salary', 'preferred_location', 'is_available_for_work')
    list_filter = ('is_available_for_work', 'created_at')
    search_fields = ('user_profile__user__username', 'user_profile__user__email', 'preferred_location')
    ordering = ('-created_at',)
    list_per_page = 25
    
    def user_link(self, obj):
        user = obj.user_profile.user
        url = reverse('admin:auth_user_change', args=[user.pk])
        return format_html('<a href="{}" style="color: #3b82f6; text-decoration: none;">{}</a>', url, user.get_full_name() or user.username)
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user_profile__user__username'

class SkillAdmin(admin.ModelAdmin):
    list_display = ('name', 'job_seeker', 'level', 'years_of_experience')
    list_filter = ('level', 'years_of_experience')
    search_fields = ('name', 'job_seeker__user_profile__user__username')

class CertificationAdmin(admin.ModelAdmin):
    list_display = ('name', 'issuing_organization', 'job_seeker', 'issue_date', 'expiry_date')
    list_filter = ('issue_date', 'expiry_date')
    search_fields = ('name', 'issuing_organization', 'job_seeker__user_profile__user__username')
    date_hierarchy = 'issue_date'

class CoverLetterAdmin(admin.ModelAdmin):
    list_display = ('title', 'user_link', 'job_description_link', 'ats_score', 'readability_score', 'created_at')
    list_filter = ('ats_score', 'created_at', 'updated_at')
    search_fields = ('title', 'user_profile__user__username', 'content')
    ordering = ('-updated_at',)
    list_per_page = 25
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user_profile', 'resume', 'job_description', 'title', 'content')
        }),
        ('AI Analysis', {
            'fields': ('ai_suggestions', 'tone_analysis', 'ats_score', 'readability_score'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def user_link(self, obj):
        user = obj.user_profile.user
        url = reverse('admin:auth_user_change', args=[user.pk])
        return format_html('<a href="{}" style="color: #3b82f6; text-decoration: none;">{}</a>', url, user.get_full_name() or user.username)
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user_profile__user__username'
    
    def job_description_link(self, obj):
        if obj.job_description:
            return format_html('<span style="color: #10b981; font-weight: 500;">{}</span>', obj.job_description.title[:50])
        return format_html('<span style="color: #64748b;">General</span>')
    job_description_link.short_description = 'Job Description'

class JobDescriptionAdmin(admin.ModelAdmin):
    list_display = ('title', 'user_link', 'analysis_score', 'created_at')
    list_filter = ('analysis_score', 'created_at')
    search_fields = ('title', 'user_profile__user__username', 'description')
    ordering = ('-updated_at',)
    list_per_page = 25
    readonly_fields = ('created_at', 'updated_at')
    
    def user_link(self, obj):
        user = obj.user_profile.user
        url = reverse('admin:auth_user_change', args=[user.pk])
        return format_html('<a href="{}" style="color: #3b82f6; text-decoration: none;">{}</a>', url, user.get_full_name() or user.username)
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user_profile__user__username'

class JobApplicationTrackerAdmin(admin.ModelAdmin):
    list_display = ('position_title', 'company_name', 'user_link', 'status', 'applied_date', 'resume_ats_score')
    list_filter = ('status', 'applied_date', 'resume_ats_score')
    search_fields = ('position_title', 'company_name', 'user_profile__user__username', 'notes')
    ordering = ('-applied_date',)
    list_per_page = 25
    readonly_fields = ('applied_date', 'last_updated')
    
    fieldsets = (
        ('Application Information', {
            'fields': ('user_profile', 'job_description', 'company_name', 'position_title', 'application_url')
        }),
        ('Documents', {
            'fields': ('resume_version', 'cover_letter'),
            'classes': ('collapse',)
        }),
        ('Status & Tracking', {
            'fields': ('status', 'follow_up_date', 'notes')
        }),
        ('Analytics', {
            'fields': ('resume_ats_score',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('applied_date', 'last_updated'),
            'classes': ('collapse',)
        }),
    )
    
    def user_link(self, obj):
        user = obj.user_profile.user
        url = reverse('admin:auth_user_change', args=[user.pk])
        return format_html('<a href="{}" style="color: #3b82f6; text-decoration: none;">{}</a>', url, user.get_full_name() or user.username)
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user_profile__user__username'

# Unregister the default User admin and register our custom one
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

# Register other models
admin.site.register(JobSeekerProfile, JobSeekerProfileAdmin)
admin.site.register(Education, EducationAdmin)
admin.site.register(Experience, ExperienceAdmin)
admin.site.register(Skill, SkillAdmin)
admin.site.register(Certification, CertificationAdmin)
admin.site.register(CoverLetter, CoverLetterAdmin)
admin.site.register(JobDescription, JobDescriptionAdmin)
admin.site.register(JobApplicationTracker, JobApplicationTrackerAdmin)

@admin.register(ResumeAnalyticsReport)
class ResumeAnalyticsReportAdmin(admin.ModelAdmin):
    list_display = ('user_profile', 'total_applications', 'total_responses', 'total_interviews', 'response_rate', 'generated_at')
    list_filter = ('generated_at', 'total_applications', 'total_responses')
    search_fields = ('user_profile__user__username', 'user_profile__user__email', 'user_profile__user__first_name', 'user_profile__user__last_name')
    readonly_fields = ('generated_at', 'response_rate', 'interview_rate')
    ordering = ('-generated_at',)
    
    fieldsets = (
        ('User Information', {
            'fields': ('user_profile',)
        }),
        ('Performance Metrics', {
            'fields': ('total_applications', 'total_responses', 'total_interviews', 'response_rate', 'interview_rate')
        }),
        ('Resume Insights', {
            'fields': ('best_performing_keywords', 'underperforming_sections', 'improvement_suggestions'),
            'classes': ('collapse',)
        }),
        ('Trends', {
            'fields': ('ats_score_trend', 'response_rate_trend'),
            'classes': ('collapse',)
        }),
        ('Industry Analysis', {
            'fields': ('industry_benchmarks', 'competitive_analysis'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('generated_at',),
            'classes': ('collapse',)
        }),
    )
    
    def response_rate(self, obj):
        if obj.total_applications > 0:
            rate = (obj.total_responses / obj.total_applications) * 100
            return f"{rate:.1f}%"
        return "0%"
    response_rate.short_description = 'Response Rate'
    
    def interview_rate(self, obj):
        if obj.total_applications > 0:
            rate = (obj.total_interviews / obj.total_applications) * 100
            return f"{rate:.1f}%"
        return "0%"
    interview_rate.short_description = 'Interview Rate'
