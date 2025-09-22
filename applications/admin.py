from django.contrib import admin
from .models import (
    Application, ApplicationStatus, Interview, Message, Notification,
    ApplicationAnalytics, ApplicationView, ApplicationRating
)

@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('job', 'applicant', 'employer', 'status', 'is_shortlisted', 'applied_at')
    list_filter = ('status', 'is_shortlisted', 'applied_at', 'updated_at')
    search_fields = ('job__title', 'applicant__user_profile__user__username', 'employer__company__name')
    readonly_fields = ('applied_at', 'updated_at', 'reviewed_at')
    date_hierarchy = 'applied_at'
    
    fieldsets = (
        ('Application Information', {
            'fields': ('job', 'applicant', 'employer', 'cover_letter', 'resume', 'additional_files')
        }),
        ('Status and Tracking', {
            'fields': ('status', 'is_shortlisted', 'is_rejected')
        }),
        ('Notes and Feedback', {
            'fields': ('employer_notes', 'applicant_notes')
        }),
        ('Timestamps', {
            'fields': ('applied_at', 'updated_at', 'reviewed_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(ApplicationStatus)
class ApplicationStatusAdmin(admin.ModelAdmin):
    list_display = ('application', 'status', 'changed_by', 'changed_at')
    list_filter = ('status', 'changed_at')
    search_fields = ('application__job__title', 'application__applicant__user_profile__user__username')
    readonly_fields = ('changed_at',)

@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin):
    list_display = ('application', 'interview_type', 'status', 'scheduled_date', 'duration', 'interviewer_name')
    list_filter = ('interview_type', 'status', 'scheduled_date', 'created_at')
    search_fields = ('application__job__title', 'application__applicant__user_profile__user__username', 'interviewer_name')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'scheduled_date'
    
    fieldsets = (
        ('Interview Information', {
            'fields': ('application', 'interview_type', 'status')
        }),
        ('Scheduling', {
            'fields': ('scheduled_date', 'duration', 'timezone')
        }),
        ('Location/Platform', {
            'fields': ('location', 'video_platform', 'meeting_link')
        }),
        ('Participants', {
            'fields': ('interviewer_name', 'interviewer_email', 'interviewer_phone')
        }),
        ('Notes', {
            'fields': ('instructions', 'notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('application', 'sender', 'recipient', 'subject', 'message_type', 'is_read', 'sent_at')
    list_filter = ('message_type', 'is_read', 'sent_at', 'read_at')
    search_fields = ('application__job__title', 'sender__username', 'recipient__username', 'subject')
    readonly_fields = ('sent_at', 'read_at')
    date_hierarchy = 'sent_at'
    
    fieldsets = (
        ('Message Information', {
            'fields': ('application', 'sender', 'recipient', 'message_type')
        }),
        ('Content', {
            'fields': ('subject', 'content', 'attachment')
        }),
        ('Status', {
            'fields': ('is_read',)
        }),
        ('Timestamps', {
            'fields': ('sent_at', 'read_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_type', 'title', 'is_read', 'is_email_sent', 'created_at')
    list_filter = ('notification_type', 'is_read', 'is_email_sent', 'created_at')
    search_fields = ('user__username', 'title', 'message')
    readonly_fields = ('created_at', 'read_at')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Notification Information', {
            'fields': ('user', 'notification_type', 'title', 'message')
        }),
        ('Related Objects', {
            'fields': ('application', 'interview', 'job'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_read', 'is_email_sent')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'read_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(ApplicationAnalytics)
class ApplicationAnalyticsAdmin(admin.ModelAdmin):
    list_display = ('application', 'employer_views', 'interviews_count', 'messages_count', 'created_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('application__job__title', 'application__applicant__user_profile__user__username')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Analytics Information', {
            'fields': ('application',)
        }),
        ('View Tracking', {
            'fields': ('employer_views', 'last_viewed')
        }),
        ('Response Tracking', {
            'fields': ('time_to_first_response', 'time_to_decision')
        }),
        ('Interview Tracking', {
            'fields': ('interviews_count', 'interview_success_rate')
        }),
        ('Communication Tracking', {
            'fields': ('messages_count', 'last_communication')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(ApplicationView)
class ApplicationViewAdmin(admin.ModelAdmin):
    list_display = ('application', 'viewer', 'ip_address', 'viewed_at')
    list_filter = ('viewed_at',)
    search_fields = ('application__job__title', 'viewer__username', 'ip_address')
    readonly_fields = ('viewed_at',)

@admin.register(ApplicationRating)
class ApplicationRatingAdmin(admin.ModelAdmin):
    list_display = ('application', 'rater', 'rating', 'rated_at')
    list_filter = ('rating', 'rated_at')
    search_fields = ('application__job__title', 'rater__username', 'comments')
    readonly_fields = ('rated_at',)
