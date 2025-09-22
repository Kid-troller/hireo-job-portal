from django.contrib import admin
from .models import (
    JobView, JobClick, JobSeekerActivity, EmployerEngagement,
    SkillDemand, SalaryInsight, ApplicationConversion, TrendingJob,
    CompanyMetrics, MarketInsight, UserAlert
)


@admin.register(JobView)
class JobViewAdmin(admin.ModelAdmin):
    list_display = ['job', 'viewer', 'ip_address', 'viewed_at']
    list_filter = ['viewed_at', 'job__category']
    search_fields = ['job__title', 'viewer__username']
    readonly_fields = ['viewed_at']


@admin.register(JobClick)
class JobClickAdmin(admin.ModelAdmin):
    list_display = ['job', 'user', 'click_type', 'clicked_at']
    list_filter = ['click_type', 'clicked_at']
    search_fields = ['job__title', 'user__username']


@admin.register(JobSeekerActivity)
class JobSeekerActivityAdmin(admin.ModelAdmin):
    list_display = ['job_seeker', 'activity_type', 'job', 'timestamp']
    list_filter = ['activity_type', 'timestamp']
    search_fields = ['job_seeker__user_profile__user__username', 'search_query']


@admin.register(EmployerEngagement)
class EmployerEngagementAdmin(admin.ModelAdmin):
    list_display = ['employer', 'engagement_type', 'job', 'timestamp']
    list_filter = ['engagement_type', 'timestamp']
    search_fields = ['employer__user_profile__user__username']


@admin.register(SkillDemand)
class SkillDemandAdmin(admin.ModelAdmin):
    list_display = ['skill_name', 'job', 'is_required', 'category', 'created_at']
    list_filter = ['is_required', 'category', 'created_at']
    search_fields = ['skill_name', 'job__title']


@admin.register(SalaryInsight)
class SalaryInsightAdmin(admin.ModelAdmin):
    list_display = ['job', 'min_salary', 'max_salary', 'category', 'experience_level']
    list_filter = ['category', 'experience_level', 'currency']
    search_fields = ['job__title']


@admin.register(ApplicationConversion)
class ApplicationConversionAdmin(admin.ModelAdmin):
    list_display = ['job', 'total_views', 'total_applications', 'conversion_rate', 'last_updated']
    list_filter = ['last_updated']
    search_fields = ['job__title']
    readonly_fields = ['conversion_rate', 'click_through_rate']


@admin.register(TrendingJob)
class TrendingJobAdmin(admin.ModelAdmin):
    list_display = ['job', 'trend_type', 'rank', 'score', 'created_at']
    list_filter = ['trend_type', 'created_at']
    search_fields = ['job__title']


@admin.register(CompanyMetrics)
class CompanyMetricsAdmin(admin.ModelAdmin):
    list_display = ['company', 'total_jobs_posted', 'active_jobs', 'total_applications_received', 'company_rating']
    list_filter = ['last_updated']
    search_fields = ['company__name']
    readonly_fields = ['last_updated']


@admin.register(MarketInsight)
class MarketInsightAdmin(admin.ModelAdmin):
    list_display = ['insight_type', 'category', 'location', 'metric_value', 'created_at']
    list_filter = ['insight_type', 'category', 'created_at']
    search_fields = ['metric_label']


@admin.register(UserAlert)
class UserAlertAdmin(admin.ModelAdmin):
    list_display = ['user', 'alert_type', 'priority', 'title', 'is_read', 'created_at']
    list_filter = ['alert_type', 'priority', 'is_read', 'created_at']
    search_fields = ['user__username', 'title', 'message']
    actions = ['mark_as_read', 'mark_as_dismissed']
    
    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)
    mark_as_read.short_description = "Mark selected alerts as read"
    
    def mark_as_dismissed(self, request, queryset):
        queryset.update(is_dismissed=True)
    mark_as_dismissed.short_description = "Mark selected alerts as dismissed"
