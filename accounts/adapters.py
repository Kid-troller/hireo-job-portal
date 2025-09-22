from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from .models import UserProfile


class CustomAccountAdapter(DefaultAccountAdapter):
    """Custom account adapter for handling regular account creation"""
    
    def get_login_redirect_url(self, request):
        """Redirect users based on their type after login"""
        user = request.user
        if hasattr(user, 'userprofile'):
            if user.userprofile.user_type == 'employer':
                return reverse('employer:dashboard')
            else:
                return reverse('accounts:dashboard')
        return reverse('accounts:dashboard')


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Custom social account adapter for handling Google OAuth"""
    
    def is_open_for_signup(self, request, sociallogin):
        """Allow social account signup"""
        return True
    
    def save_user(self, request, sociallogin, form=None):
        """Save user and create profile after social login"""
        user = super().save_user(request, sociallogin, form)
        
        # Get additional data from social account
        extra_data = sociallogin.account.extra_data
        
        # Create or update user profile
        profile, created = UserProfile.objects.get_or_create(
            user=user,
            defaults={
                'user_type': 'jobseeker',  # Default to jobseeker, user can change later
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
            }
        )
        
        if created:
            # Set profile picture from Google if available
            if 'picture' in extra_data:
                profile.profile_picture_url = extra_data['picture']
                profile.save()
        
        return user
    
    def get_connect_redirect_url(self, request, socialaccount):
        """Redirect after connecting social account"""
        return reverse('accounts:profile')
    
    def populate_user(self, request, sociallogin, data):
        """Populate user data from social login"""
        user = super().populate_user(request, sociallogin, data)
        
        # Get extra data from social provider
        extra_data = sociallogin.account.extra_data
        
        # Set user fields from Google data
        if 'given_name' in extra_data:
            user.first_name = extra_data['given_name']
        if 'family_name' in extra_data:
            user.last_name = extra_data['family_name']
        if 'email' in extra_data:
            user.email = extra_data['email']
            
        return user
    
    def pre_social_login(self, request, sociallogin):
        """Handle pre-social login logic"""
        # Check if user already exists with this email
        if sociallogin.is_existing:
            return
            
        # Try to connect to existing user with same email
        try:
            user = sociallogin.user
            if user.email:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                existing_user = User.objects.get(email=user.email)
                sociallogin.connect(request, existing_user)
        except User.DoesNotExist:
            pass
    
    def get_signup_redirect_url(self, request):
        """Redirect after social signup"""
        # Check if user needs to complete profile setup
        user = request.user
        if hasattr(user, 'userprofile'):
            profile = user.userprofile
            if not profile.user_type or profile.user_type == 'jobseeker':
                # Redirect to user type selection for new social users
                messages.info(request, 
                    "Welcome! Please select your account type to complete your profile setup.")
                return reverse('accounts:select_user_type')
        
        return reverse('accounts:dashboard')


def handle_social_user_type_selection(request, user, user_type):
    """Helper function to handle user type selection for social users"""
    try:
        profile = user.userprofile
        profile.user_type = user_type
        profile.save()
        
        if user_type == 'employer':
            messages.success(request, 
                "Account type updated! Please complete your company profile.")
            return redirect('employer:profile')
        else:
            messages.success(request, 
                "Account type updated! Welcome to Hireo!")
            return redirect('accounts:dashboard')
            
    except UserProfile.DoesNotExist:
        # Create profile if it doesn't exist
        UserProfile.objects.create(
            user=user,
            user_type=user_type,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email
        )
        
        if user_type == 'employer':
            return redirect('employer:profile')
        else:
            return redirect('accounts:dashboard')
