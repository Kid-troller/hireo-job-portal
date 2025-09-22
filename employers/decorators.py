from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from functools import wraps

def employer_required(view_func):
    """
    Decorator to ensure only employers can access the view
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        try:
            user_profile = request.user.userprofile
            if user_profile.user_type != 'employer':
                messages.error(request, 'Access denied. This page is only accessible to employers.')
                return redirect('accounts:dashboard')
            return view_func(request, *args, **kwargs)
        except AttributeError:
            messages.error(request, 'Please complete your profile setup.')
            return redirect('accounts:complete_profile')
    return _wrapped_view
