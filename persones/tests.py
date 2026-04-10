from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Persona


class PersonesPermissionTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(
            username='persones-admin',
            password='test-pass-123',
            nom_complet='Persones Admin',
            rol=User.Rol.ADMINISTRACIO,
        )
        self.coord = User.objects.create_user(
            username='persones-coord',
            password='test-pass-123',
            nom_complet='Persones Coord',
            rol=User.Rol.COORDINACIO,
        )
        self.participant = User.objects.create_user(
            username='persones-participant',
            password='test-pass-123',
            nom_complet='Persones Participant',
            rol=User.Rol.PARTICIPANT,
        )
        Persona.objects.create(nom='Ada Lovelace', email='ada@example.org')

    def test_list_requires_authentication(self):
        response = self.client.get(reverse('persones:persona_list'))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

    def test_participant_cannot_access_persones_section(self):
        self.client.force_login(self.participant)

        response = self.client.get(reverse('persones:persona_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Accés denegat')

    def test_coord_can_access_persones_list(self):
        self.client.force_login(self.coord)

        response = self.client.get(reverse('persones:persona_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ada Lovelace')

    def test_admin_can_filter_persones_by_query(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse('persones:persona_list'), {'q': 'Ada'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ada Lovelace')
