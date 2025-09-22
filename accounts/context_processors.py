from accounts.models import Notification

def notifications_processor(request):
    """
    Context processor that adds notifications to the template context.
    """
    context = {
        'notifications': [],
        'notifications_count': 0
    }
    
    if request.user.is_authenticated:
        notifications = Notification.objects.filter(user=request.user, is_read=False)
        context['notifications'] = notifications
        context['notifications_count'] = notifications.count()
    
    return context