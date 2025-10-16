from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from .models import AppUser

User = get_user_model()

class AppUserBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            app_user = AppUser.objects.get(username=username)
            if app_user.passwrd == password:
                user, created = User.objects.get_or_create(
                    username=username,
                    defaults={'email': f'{username}@sentiment.local'}
                )
                return user
        except AppUser.DoesNotExist:
            pass
        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None