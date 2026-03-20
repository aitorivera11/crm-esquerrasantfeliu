from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from .models import Acte


class ActeExternalIdentifierConstraintTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='coordinador',
            password='test-pass-123',
            nom_complet='Usuari Coordinador',
        )
        self.base_data = {
            'inici': timezone.now() + timedelta(days=1),
            'ubicacio': 'Seu local',
            'creador': self.user,
        }

    def test_allows_multiple_local_events_without_external_identifiers(self):
        Acte.objects.create(titol='Acte local 1', **self.base_data)
        Acte.objects.create(titol='Acte local 2', **self.base_data)

        self.assertEqual(Acte.objects.count(), 2)

    def test_still_rejects_duplicate_non_empty_external_identifiers(self):
        Acte.objects.create(
            titol='Acte importat 1',
            external_source='AGENDA_CIUTAT',
            external_id='abc-123',
            **self.base_data,
        )

        with self.assertRaises(IntegrityError):
            Acte.objects.create(
                titol='Acte importat 2',
                external_source='AGENDA_CIUTAT',
                external_id='abc-123',
                **self.base_data,
            )
