from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import redirect


class RestrictedSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Permet autenticació social només per usuaris ja registrats."""

    def is_open_for_signup(self, request, sociallogin):
        return False

    def pre_social_login(self, request, sociallogin):
        if sociallogin.is_existing:
            return

        email = (sociallogin.user.email or '').strip()
        if not email:
            messages.error(
                request,
                "No s'ha pogut validar el compte de Google. Contacta amb administració.",
            )
            raise ImmediateHttpResponse(redirect('account_login'))

        UserModel = get_user_model()
        if not UserModel.objects.filter(email__iexact=email).exists():
            messages.error(
                request,
                "Aquest correu no està autoritzat. Demana accés a administració.",
            )
            raise ImmediateHttpResponse(redirect('account_login'))
