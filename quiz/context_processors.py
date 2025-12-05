"""
Context processors to make data available to all templates
"""
from .models import UserProfile


def user_profile(request):
    """Add user profile to template context"""
    if request.user.is_authenticated:
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        return {'user_profile': profile}
    return {'user_profile': None}

