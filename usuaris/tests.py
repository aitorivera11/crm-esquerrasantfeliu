from types import SimpleNamespace

from allauth.core.exceptions import ImmediateHttpResponse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.messages import get_messages
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory, TestCase

from .adapters import RestrictedSocialAccountAdapter
from .signals import GROUP_ADMINISTRACIO, GROUP_COORDINACIO, GROUP_PARTICIPANT


class UsuariRoleManagementTests(TestCase):
    def setUp(self):
        self.User = get_user_model()

    def test_normalizes_legacy_role_values_when_saving(self):
        user = self.User.objects.create_user(
            username='legacy-admin',
            password='test-pass-123',
            nom_complet='Legacy Admin',
            rol='ADMINISTRADOR',
        )

        user.refresh_from_db()

        self.assertEqual(user.rol, self.User.Rol.ADMINISTRACIO)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.groups.filter(name=GROUP_ADMINISTRACIO).exists())

    def test_assigns_expected_group_for_each_supported_role(self):
        coord = self.User.objects.create_user(
            username='coord-role',
            password='test-pass-123',
            nom_complet='Coord Role',
            rol=self.User.Rol.COORDINACIO,
        )
        participant = self.User.objects.create_user(
            username='participant-role',
            password='test-pass-123',
            nom_complet='Participant Role',
            rol=self.User.Rol.PARTICIPANT,
        )

        self.assertTrue(coord.groups.filter(name=GROUP_COORDINACIO).exists())
        self.assertTrue(participant.groups.filter(name=GROUP_PARTICIPANT).exists())
        self.assertFalse(participant.is_staff)

    def test_role_change_replaces_previous_managed_group(self):
        user = self.User.objects.create_user(
            username='switch-role',
            password='test-pass-123',
            nom_complet='Switch Role',
            rol=self.User.Rol.PARTICIPANT,
        )

        user.rol = self.User.Rol.COORDINACIO
        user.save()

        managed_groups = Group.objects.filter(name__in=[GROUP_ADMINISTRACIO, GROUP_COORDINACIO, GROUP_PARTICIPANT])
        self.assertEqual(user.groups.filter(pk__in=managed_groups).count(), 1)
        self.assertTrue(user.groups.filter(name=GROUP_COORDINACIO).exists())


class RestrictedSocialAccountAdapterTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.adapter = RestrictedSocialAccountAdapter()
        self.User = get_user_model()

    def test_blocks_google_login_when_email_is_not_registered(self):
        request = self.factory.get('/accounts/google/login/callback/')
        request.session = self.client.session
        request._messages = FallbackStorage(request)
        sociallogin = SimpleNamespace(
            is_existing=False,
            user=SimpleNamespace(email='nou@example.com'),
        )

        with self.assertRaises(ImmediateHttpResponse):
            self.adapter.pre_social_login(request, sociallogin)

        messages = [message.message for message in get_messages(request)]
        self.assertIn('Aquest correu no està autoritzat. Demana accés a administració.', messages)

    def test_allows_google_login_when_email_is_registered(self):
        self.User.objects.create_user(
            username='registre',
            password='test-pass-123',
            email='registre@example.com',
            nom_complet='Usuari Registrat',
        )
        request = self.factory.get('/accounts/google/login/callback/')
        request.session = self.client.session
        request._messages = FallbackStorage(request)
        sociallogin = SimpleNamespace(
            is_existing=False,
            user=SimpleNamespace(email='registre@example.com'),
        )

        self.adapter.pre_social_login(request, sociallogin)
