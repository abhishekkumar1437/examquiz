from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User
from quiz.models import UserProfile


class Command(BaseCommand):
    help = 'Grant daily tokens (10 tokens) to all users who haven\'t received tokens today'

    def handle(self, *args, **options):
        today = timezone.now().date()
        granted_count = 0
        
        for user in User.objects.all():
            profile, created = UserProfile.objects.get_or_create(user=user)
            
            # Grant tokens if not already granted today
            if profile.grant_daily_tokens():
                granted_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Granted 10 tokens to {user.username} (Total: {profile.tokens} tokens)')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'\nSuccessfully granted daily tokens to {granted_count} user(s).')
        )

