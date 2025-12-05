from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.utils import timezone
from .models import UserProfile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create UserProfile automatically when a new user is created"""
    if created:
        today = timezone.now().date()
        profile, created_profile = UserProfile.objects.get_or_create(
            user=instance,
            defaults={
                'tokens': 100,
                'subscription_plan': 'basic',
                'last_token_grant_date': today  # Mark today as granted to avoid duplicate on creation day
            }
        )
        # Ensure new users get 100 tokens
        if created_profile and profile.tokens == 0:
            profile.tokens = 100
            profile.save()


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save UserProfile when user is saved"""
    if hasattr(instance, 'profile'):
        instance.profile.save()
