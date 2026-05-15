from django.shortcuts import redirect
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.core.exceptions import ValidationError
from django.contrib import messages
from .constants import YGG_EMAIL

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        """
        Restricts social logins to users with specific email domains.
        """
        allowed_domain = YGG_EMAIL
        user_email = sociallogin.user.email
        if not user_email or user_email.split("@")[-1].lower() != allowed_domain.lower():
            messages.error(request,
                           f"Only users with an '@{allowed_domain}' email address can log in.")
            raise ValidationError(f"Only users with an '@{allowed_domain}' email address can log in.")

