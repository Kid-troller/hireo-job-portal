from django.contrib import admin
from .models import (
    JobPost, JobCategory, JobLocation, JobAlert, SavedJob, 
    JobView, JobSearch
)

@admin.register(JobCategory)
class JobCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'icon', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at',)

@admin.register(JobLocation)
class JobLocationAdmin(admin.ModelAdmin):
    list_display = ('city', 'state', 'country', 'is_active', 'created_at')
    list_filter = ('is_active', 'country', 'state', 'created_at')
    search_fields = ('city', 'state', 'country')
    readonly_fields = ('created_at',)

@admin.register(JobPost)
class JobPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'category', 'location', 'employment_type', 'experience_level', 'status', 'is_featured', 'created_at')
    list_filter = ('status', 'employment_type', 'experience_level', 'is_featured', 'is_urgent', 'is_remote', 'category', 'created_at')
    search_fields = ('title', 'company__name', 'description', 'requirements')
    readonly_fields = ('views_count', 'applications_count', 'created_at', 'updated_at', 'published_at')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'company', 'employer', 'category', 'location')
        }),
        ('Job Details', {
            'fields': ('description', 'requirements', 'responsibilities', 'benefits')
        }),
        ('Employment Details', {
            'fields': ('employment_type', 'experience_level', 'min_experience', 'max_experience')
        }),
        ('Salary Information', {
            'fields': ('min_salary', 'max_salary', 'salary_currency', 'is_salary_negotiable', 'is_salary_visible')
        }),
        ('Skills and Requirements', {
            'fields': ('required_skills', 'preferred_skills', 'education_required')
        }),
        ('Application Details', {
            'fields': ('application_deadline', 'is_remote', 'remote_percentage')
        }),
        ('Status and Visibility', {
            'fields': ('status', 'is_featured', 'is_urgent')
        }),
        ('Analytics', {
            'fields': ('views_count', 'applications_count'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'published_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change and obj.status == 'active':
            obj.published_at = obj.created_at
        super().save_model(request, obj, form, change)

@admin.register(JobAlert)
class JobAlertAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'keywords', 'location', 'category', 'frequency', 'is_active', 'created_at')
    list_filter = ('frequency', 'is_active', 'created_at', 'last_sent')
    search_fields = ('user__user_profile__user__username', 'title', 'keywords')
    readonly_fields = ('created_at', 'last_sent')
    
    fieldsets = (
        ('Alert Information', {
            'fields': ('user', 'title', 'keywords')
        }),
        ('Filters', {
            'fields': ('location', 'category', 'employment_type', 'experience_level', 'min_salary', 'max_salary', 'is_remote')
        }),
        ('Settings', {
            'fields': ('frequency', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'last_sent'),
            'classes': ('collapse',)
        }),
    )

@admin.register(SavedJob)
class SavedJobAdmin(admin.ModelAdmin):
    list_display = ('user', 'job', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__user_profile__user__username', 'job__title', 'job__company__name')
    readonly_fields = ('created_at',)

@admin.register(JobView)
class JobViewAdmin(admin.ModelAdmin):
    list_display = ('job', 'user', 'viewed_at')
    list_filter = ('viewed_at',)
    search_fields = ('job__title', 'user__username')
    readonly_fields = ('viewed_at',)

@admin.register(JobSearch)
class JobSearchAdmin(admin.ModelAdmin):
    list_display = ('user', 'query', 'results_count', 'searched_at')
    list_filter = ('searched_at',)
    search_fields = ('query', 'user__username')
    readonly_fields = ('searched_at',)
