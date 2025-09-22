from django.contrib.auth.models import User
from django.db import connection
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta


def admin_dashboard_stats(request):
    """
    Context processor to provide dashboard statistics for admin interface
    """
    if not request.path.startswith('/admin/'):
        return {}
    
    # Check cache first
    cache_key = 'admin_dashboard_stats'
    stats = cache.get(cache_key)
    
    if stats is None:
        try:
            with connection.cursor() as cursor:
                # Get total users
                cursor.execute("SELECT COUNT(*) FROM auth_user")
                total_users = cursor.fetchone()[0]
                
                # Get total active jobs
                cursor.execute("SELECT COUNT(*) FROM jobs_jobpost WHERE status = 'active'")
                total_jobs = cursor.fetchone()[0]
                
                # Get total applications
                cursor.execute("SELECT COUNT(*) FROM applications_application")
                total_applications = cursor.fetchone()[0]
                
                # Get total companies
                cursor.execute("SELECT COUNT(DISTINCT company_id) FROM employers_employerprofile WHERE company_id IS NOT NULL")
                total_companies = cursor.fetchone()[0]
                
                # Get recent activities
                recent_activities = []
                
                # Recent user registrations (last 24 hours)
                cursor.execute("""
                    SELECT username, date_joined 
                    FROM auth_user 
                    WHERE date_joined >= %s 
                    ORDER BY date_joined DESC 
                    LIMIT 5
                """, [timezone.now() - timedelta(hours=24)])
                
                for username, date_joined in cursor.fetchall():
                    time_diff = timezone.now() - date_joined
                    if time_diff.total_seconds() < 3600:  # Less than 1 hour
                        time_ago = f"{int(time_diff.total_seconds() // 60)} minutes ago"
                    elif time_diff.total_seconds() < 86400:  # Less than 24 hours
                        time_ago = f"{int(time_diff.total_seconds() // 3600)} hours ago"
                    else:
                        time_ago = f"{time_diff.days} days ago"
                    
                    recent_activities.append({
                        'type': 'user_registration',
                        'icon': 'fas fa-user-check',
                        'icon_class': 'success',
                        'title': f'New user "{username}" registered',
                        'time': time_ago,
                        'link': f'/admin/auth/user/?q={username}'
                    })
                
                # Recent job postings (last 24 hours)
                cursor.execute("""
                    SELECT title, created_at 
                    FROM jobs_jobpost 
                    WHERE created_at >= %s 
                    ORDER BY created_at DESC 
                    LIMIT 5
                """, [timezone.now() - timedelta(hours=24)])
                
                for title, created_at in cursor.fetchall():
                    time_diff = timezone.now() - created_at
                    if time_diff.total_seconds() < 3600:
                        time_ago = f"{int(time_diff.total_seconds() // 60)} minutes ago"
                    elif time_diff.total_seconds() < 86400:
                        time_ago = f"{int(time_diff.total_seconds() // 3600)} hours ago"
                    else:
                        time_ago = f"{time_diff.days} days ago"
                    
                    recent_activities.append({
                        'type': 'job_posting',
                        'icon': 'fas fa-briefcase',
                        'icon_class': 'info',
                        'title': f'New job "{title[:30]}..." posted',
                        'time': time_ago,
                        'link': '/admin/jobs/jobpost/'
                    })
                
                # Recent applications (last 24 hours)
                cursor.execute("""
                    SELECT jp.title, a.created_at 
                    FROM applications_application a
                    JOIN jobs_jobpost jp ON a.job_id = jp.id
                    WHERE a.created_at >= %s 
                    ORDER BY a.created_at DESC 
                    LIMIT 5
                """, [timezone.now() - timedelta(hours=24)])
                
                for job_title, created_at in cursor.fetchall():
                    time_diff = timezone.now() - created_at
                    if time_diff.total_seconds() < 3600:
                        time_ago = f"{int(time_diff.total_seconds() // 60)} minutes ago"
                    elif time_diff.total_seconds() < 86400:
                        time_ago = f"{int(time_diff.total_seconds() // 3600)} hours ago"
                    else:
                        time_ago = f"{time_diff.days} days ago"
                    
                    recent_activities.append({
                        'type': 'application_submission',
                        'icon': 'fas fa-file-alt',
                        'icon_class': 'warning',
                        'title': f'Application for "{job_title[:25]}..." submitted',
                        'time': time_ago,
                        'link': '/admin/applications/application/'
                    })
                
                # Sort all activities by most recent
                recent_activities.sort(key=lambda x: x['time'])
                recent_activities = recent_activities[:10]  # Limit to 10 most recent
                
                stats = {
                    'total_users': total_users,
                    'total_jobs': total_jobs,
                    'total_applications': total_applications,
                    'total_companies': total_companies,
                    'recent_activities': recent_activities,
                }
                
                # Cache for 2 minutes (shorter cache for activities)
                cache.set(cache_key, stats, 120)
                
        except Exception as e:
            # Fallback values if database queries fail
            stats = {
                'total_users': 0,
                'total_jobs': 0,
                'total_applications': 0,
                'total_companies': 0,
                'recent_activities': [],
            }
    
    return stats
