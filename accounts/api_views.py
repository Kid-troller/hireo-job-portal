"""
API views for authentication and user management
"""
from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core.cache import cache
# from django_ratelimit.decorators import ratelimit  # Disabled until installed
from django.utils.decorators import method_decorator
import logging

logger = logging.getLogger('hireo')

@api_view(['POST'])
@permission_classes([AllowAny])
# @ratelimit(key='ip', rate='3/m', method='POST')  # Disabled until installed
def api_logout(request):
    """API logout endpoint"""
    try:
        request.user.auth_token.delete()
        cache.delete(f'user_{request.user.id}')
        logger.info(f"API logout successful for user: {request.user.username}")
        return Response({'message': 'Successfully logged out'})
    except:
        return Response({'error': 'Error logging out'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_login(request):
    """API login endpoint with rate limiting"""
    username = request.data.get('username')
    password = request.data.get('password')
    
    if not username or not password:
        return Response({
            'error': 'Username and password required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    user = authenticate(username=username, password=password)
    
    if user:
        if user.is_active:
            token, created = Token.objects.get_or_create(user=user)
            
            # Cache user data for faster access
            cache.set(f'user_{user.id}', {
                'username': user.username,
                'email': user.email,
                'user_type': getattr(user.userprofile, 'user_type', None) if hasattr(user, 'userprofile') else None
            }, 300)  # 5 minutes
            
            logger.info(f"API login successful for user: {user.username}")
            
            return Response({
                'token': token.key,
                'user_id': user.id,
                'username': user.username,
                'email': user.email,
                'user_type': getattr(user.userprofile, 'user_type', None) if hasattr(user, 'userprofile') else None
            })
        else:
            return Response({
                'error': 'Account is disabled'
            }, status=status.HTTP_401_UNAUTHORIZED)
    else:
        logger.warning(f"Failed API login attempt for username: {username}")
        return Response({
            'error': 'Invalid credentials'
        }, status=status.HTTP_401_UNAUTHORIZED)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_logout(request):
    """API logout endpoint"""
    try:
        request.user.auth_token.delete()
        cache.delete(f'user_{request.user.id}')
        logger.info(f"API logout successful for user: {request.user.username}")
        return Response({'message': 'Successfully logged out'})
    except:
        return Response({'error': 'Error logging out'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_user_profile(request):
    """Get current user profile"""
    user = request.user
    
    # Try to get from cache first
    cached_data = cache.get(f'user_{user.id}')
    if cached_data:
        return Response(cached_data)
    
    try:
        profile_data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'date_joined': user.date_joined,
            'is_active': user.is_active,
        }
        
        if hasattr(user, 'userprofile'):
            profile_data.update({
                'user_type': user.userprofile.user_type,
                'phone_number': user.userprofile.phone_number,
                'date_of_birth': user.userprofile.date_of_birth,
                'address': user.userprofile.address,
                'city': user.userprofile.city,
                'state': user.userprofile.state,
                'country': user.userprofile.country,
                'zip_code': user.userprofile.zip_code,
            })
        
        # Cache the data
        cache.set(f'user_{user.id}', profile_data, 300)
        
        return Response(profile_data)
        
    except Exception as e:
        logger.error(f"Error fetching user profile for {user.username}: {e}")
        return Response({
            'error': 'Error fetching profile'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# @method_decorator(ratelimit(key='ip', rate='3/m', method='POST'), name='post')  # Disabled until installed
class APIRegisterView(generics.CreateAPIView):
    """API user registration with rate limiting"""
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')
        user_type = request.data.get('user_type', 'jobseeker')
        
        if not all([username, email, password]):
            return Response({
                'error': 'Username, email, and password are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if User.objects.filter(username=username).exists():
            return Response({
                'error': 'Username already exists'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if User.objects.filter(email=email).exists():
            return Response({
                'error': 'Email already exists'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )
            
            # Create user profile
            from .models import UserProfile
            UserProfile.objects.create(
                user=user,
                user_type=user_type
            )
            
            # Create auth token
            token = Token.objects.create(user=user)
            
            logger.info(f"New user registered via API: {username}")
            
            return Response({
                'message': 'User created successfully',
                'token': token.key,
                'user_id': user.id,
                'username': user.username,
                'user_type': user_type
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error creating user {username}: {e}")
            return Response({
                'error': 'Error creating user'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
