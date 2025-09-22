"""
Security utilities for application management
"""
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.core.files.uploadedfile import UploadedFile
from django.conf import settings
import os
import magic
from PIL import Image

from .models import Application
from accounts.models import JobSeekerProfile
from employers.models import EmployerProfile

def validate_file_upload(uploaded_file):
    """
    Validate uploaded files for security
    """
    if not uploaded_file:
        return True
    
    # Check file size (5MB limit)
    max_size = 5 * 1024 * 1024  # 5MB
    if uploaded_file.size > max_size:
        raise ValueError("File size exceeds 5MB limit")
    
    # Check file extension
    allowed_extensions = ['.pdf', '.doc', '.docx', '.txt', '.rtf']
    file_extension = os.path.splitext(uploaded_file.name)[1].lower()
    if file_extension not in allowed_extensions:
        raise ValueError(f"File type {file_extension} not allowed. Allowed types: {', '.join(allowed_extensions)}")
    
    # Check MIME type using python-magic
    try:
        file_mime = magic.from_buffer(uploaded_file.read(1024), mime=True)
        uploaded_file.seek(0)  # Reset file pointer
        
        allowed_mimes = [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'text/plain',
            'text/rtf',
            'application/rtf'
        ]
        
        if file_mime not in allowed_mimes:
            raise ValueError(f"File MIME type {file_mime} not allowed")
            
    except Exception as e:
        # If magic fails, fall back to extension check
        pass
    
    return True

def validate_application_access(user, application_id, user_type=None):
    """
    Validate that user has access to the application
    """
    application = get_object_or_404(Application, id=application_id)
    
    if not user.is_authenticated:
        raise PermissionDenied("Authentication required")
    
    try:
        user_profile = user.userprofile
    except:
        raise PermissionDenied("User profile not found")
    
    # Check user type if specified
    if user_type and user_profile.user_type != user_type:
        raise PermissionDenied(f"Access denied. {user_type.title()} account required.")
    
    # Validate access based on user type
    if user_profile.user_type == 'jobseeker':
        try:
            job_seeker_profile = JobSeekerProfile.objects.get(user_profile=user_profile)
        except JobSeekerProfile.DoesNotExist:
            raise PermissionDenied("Job seeker profile not found. Please complete your profile first.")
        if application.applicant != job_seeker_profile:
            raise PermissionDenied("Access denied. You can only view your own applications.")
    
    elif user_profile.user_type == 'employer':
        try:
            employer_profile = EmployerProfile.objects.get(user_profile=user_profile)
        except EmployerProfile.DoesNotExist:
            raise PermissionDenied("Employer profile not found. Please complete your company profile first.")
        if application.employer != employer_profile:
            raise PermissionDenied("Access denied. You can only view applications for your jobs.")
    
    else:
        raise PermissionDenied("Invalid user type")
    
    return application

def validate_duplicate_application(job, job_seeker_profile):
    """
    Check for duplicate applications
    """
    existing_application = Application.objects.filter(
        job=job,
        applicant=job_seeker_profile
    ).first()
    
    if existing_application:
        raise ValueError(f"You have already applied for this job on {existing_application.applied_at.strftime('%B %d, %Y')}")
    
    return True

def sanitize_input(text, max_length=None):
    """
    Sanitize text input to prevent XSS and other attacks
    """
    if not text:
        return text
    
    # Remove potentially dangerous characters
    import html
    text = html.escape(text)
    
    # Limit length if specified
    if max_length and len(text) > max_length:
        text = text[:max_length]
    
    return text.strip()

def validate_status_transition(current_status, new_status, user_type):
    """
    Validate that status transition is allowed
    """
    # Define allowed transitions
    allowed_transitions = {
        'applied': ['reviewing', 'shortlisted', 'rejected'],
        'reviewing': ['shortlisted', 'interviewing', 'rejected'],
        'shortlisted': ['interviewing', 'offered', 'rejected'],
        'interviewing': ['offered', 'hired', 'rejected'],
        'offered': ['hired', 'rejected'],
        'hired': [],  # Final state
        'rejected': [],  # Final state
        'withdrawn': []  # Final state
    }
    
    # Only employers can change status (except withdrawal)
    if user_type != 'employer' and new_status != 'withdrawn':
        raise PermissionDenied("Only employers can update application status")
    
    # Job seekers can only withdraw
    if user_type == 'jobseeker' and new_status != 'withdrawn':
        raise PermissionDenied("Job seekers can only withdraw applications")
    
    # Check if transition is allowed
    if new_status not in allowed_transitions.get(current_status, []):
        raise ValueError(f"Cannot change status from {current_status} to {new_status}")
    
    return True

def rate_limit_check(user, action, time_window=3600, max_attempts=10):
    """
    Simple rate limiting for actions
    """
    from django.core.cache import cache
    from django.utils import timezone
    
    cache_key = f"rate_limit_{user.id}_{action}"
    current_time = timezone.now().timestamp()
    
    # Get existing attempts
    attempts = cache.get(cache_key, [])
    
    # Remove old attempts outside time window
    attempts = [attempt for attempt in attempts if current_time - attempt < time_window]
    
    # Check if limit exceeded
    if len(attempts) >= max_attempts:
        raise PermissionDenied(f"Rate limit exceeded for {action}. Try again later.")
    
    # Add current attempt
    attempts.append(current_time)
    cache.set(cache_key, attempts, time_window)
    
    return True

def log_security_event(user, action, details=None, ip_address=None):
    """
    Log security-related events
    """
    import logging
    
    logger = logging.getLogger('security')
    
    log_data = {
        'user_id': user.id if user else None,
        'username': user.username if user else 'Anonymous',
        'action': action,
        'details': details,
        'ip_address': ip_address,
        'timestamp': timezone.now().isoformat()
    }
    
    logger.info(f"Security Event: {log_data}")
    
    return True
