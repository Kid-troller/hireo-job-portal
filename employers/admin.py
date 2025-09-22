from django.contrib import admin
from .models import (
    Company, EmployerProfile, CompanyReview, CompanyPhoto, 
    CompanyBenefit, EmployerSubscription
)

class CompanyPhotoInline(admin.TabularInline):
    model = CompanyPhoto
    extra = 1

class CompanyBenefitInline(admin.TabularInline):
    model = CompanyBenefit
    extra = 1

class CompanyReviewInline(admin.TabularInline):
    model = CompanyReview
    extra = 0
    readonly_fields = ('created_at',)

class EmployerProfileInline(admin.TabularInline):
    model = EmployerProfile
    extra = 0
    readonly_fields = ('created_at',)

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'industry', 'company_size', 'city', 'state', 'country', 'is_verified', 'is_active', 'created_at')
    list_filter = ('industry', 'company_size', 'is_verified', 'is_active', 'created_at', 'country')
    search_fields = ('name', 'description', 'city', 'state', 'country')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [CompanyPhotoInline, CompanyBenefitInline, EmployerProfileInline]
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'industry', 'company_size', 'founded_year')
        }),
        ('Contact Information', {
            'fields': ('website', 'email', 'phone', 'address', 'city', 'state', 'country', 'zip_code')
        }),
        ('Social Media', {
            'fields': ('linkedin_url', 'facebook_url', 'twitter_url'),
            'classes': ('collapse',)
        }),
        ('Company Details', {
            'fields': ('logo', 'company_culture', 'benefits')
        }),
        ('Status', {
            'fields': ('is_verified', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(EmployerProfile)
class EmployerProfileAdmin(admin.ModelAdmin):
    list_display = ('user_profile', 'company', 'position', 'department', 'is_primary_contact', 'can_post_jobs', 'created_at')
    list_filter = ('is_primary_contact', 'can_post_jobs', 'can_manage_applications', 'can_view_analytics', 'created_at')
    search_fields = ('user_profile__user__username', 'user_profile__user__email', 'company__name', 'position')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Profile Information', {
            'fields': ('user_profile', 'company', 'position', 'department')
        }),
        ('Permissions', {
            'fields': ('is_primary_contact', 'can_post_jobs', 'can_manage_applications', 'can_view_analytics')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(CompanyReview)
class CompanyReviewAdmin(admin.ModelAdmin):
    list_display = ('company', 'reviewer', 'rating', 'title', 'is_anonymous', 'is_verified_employee', 'created_at')
    list_filter = ('rating', 'is_anonymous', 'is_verified_employee', 'created_at')
    search_fields = ('company__name', 'reviewer__user_profile__user__username', 'title', 'review')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Review Information', {
            'fields': ('company', 'reviewer', 'rating', 'title', 'review')
        }),
        ('Additional Details', {
            'fields': ('pros', 'cons')
        }),
        ('Status', {
            'fields': ('is_anonymous', 'is_verified_employee')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(CompanyPhoto)
class CompanyPhotoAdmin(admin.ModelAdmin):
    list_display = ('company', 'caption', 'is_featured', 'created_at')
    list_filter = ('is_featured', 'created_at')
    search_fields = ('company__name', 'caption')
    readonly_fields = ('created_at',)

@admin.register(CompanyBenefit)
class CompanyBenefitAdmin(admin.ModelAdmin):
    list_display = ('company', 'name', 'description', 'icon', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('company__name', 'name', 'description')
    readonly_fields = ('created_at',)

@admin.register(EmployerSubscription)
class EmployerSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('employer', 'subscription_type', 'status', 'start_date', 'end_date', 'price', 'is_active')
    list_filter = ('subscription_type', 'status', 'start_date', 'end_date')
    search_fields = ('employer__user_profile__user__username', 'employer__company__name')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Subscription Details', {
            'fields': ('employer', 'subscription_type', 'status', 'price')
        }),
        ('Dates', {
            'fields': ('start_date', 'end_date')
        }),
        ('Features', {
            'fields': ('features',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def is_active(self, obj):
        return obj.is_active
    is_active.boolean = True
    is_active.short_description = 'Active'
