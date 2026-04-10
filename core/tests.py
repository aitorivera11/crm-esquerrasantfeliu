from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class CoreViewsAccessTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(
            username='core-admin',
            password='test-pass-123',
            nom_complet='Core Admin',
            rol=User.Rol.ADMINISTRACIO,
        )

    def test_dashboard_requires_authentication(self):
        response = self.client.get(reverse('core:home'))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

    def test_dashboard_renders_for_authenticated_user(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse('core:home'))

        self.assertEqual(response.status_code, 200)

    def test_access_denied_page_renders_for_authenticated_user(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse('core:access_denied'))

        self.assertEqual(response.status_code, 200)
