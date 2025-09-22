from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

def employer_required(view_func):
    """
    Decorator that requires user to be logged in and be an employer.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please log in to access this page.')
            return redirect('accounts:login')
        
        try:
            user_profile = request.user.userprofile
            if user_profile.user_type != 'employer':
                messages.error(request, 'Access denied. Employer account required.')
                return redirect('accounts:dashboard')
        except AttributeError:
            messages.error(request, 'Please complete your profile first.')
            return redirect('accounts:complete_profile')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def jobseeker_required(view_func):
    """
    Decorator that requires user to be logged in and be a job seeker.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please log in to access this page.')
            return redirect('accounts:login')
        
        try:
            user_profile = request.user.userprofile
            if user_profile.user_type != 'jobseeker':
                messages.error(request, 'Access denied. Job seeker account required.')
                return redirect('employer:dashboard')
        except AttributeError:
            messages.error(request, 'Please complete your profile first.')
            return redirect('accounts:complete_profile')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def user_type_required(user_type):
    """
    Decorator factory that creates a decorator requiring specific user type.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.error(request, 'Please log in to access this page.')
                return redirect('accounts:login')
            
            try:
                user_profile = request.user.userprofile
                if user_profile.user_type != user_type:
                    if user_type == 'employer':
                        messages.error(request, 'Access denied. Employer account required.')
                        return redirect('accounts:dashboard')
                    else:
                        messages.error(request, 'Access denied. Job seeker account required.')
                        return redirect('employer:dashboard')
            except AttributeError:
                messages.error(request, 'Please complete your profile first.')
                return redirect('accounts:complete_profile')
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
