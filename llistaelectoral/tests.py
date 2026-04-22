import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Candidatura, IntegrantLlista, PosicioLlista


class LlistaElectoralTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(username='admin-llista', password='pass', nom_complet='Admin', rol=User.Rol.ADMINISTRACIO)
        self.participant = User.objects.create_user(username='user-llista', password='pass', nom_complet='User', rol=User.Rol.PARTICIPANT)
        self.candidatura = Candidatura.objects.create(nom='Municipals', activa=True)
        for n in range(1, 32):
            PosicioLlista.objects.create(candidatura=self.candidatura, numero=n)

    def test_dashboard_requires_admin_or_permission(self):
        self.client.force_login(self.participant)
        response = self.client.get(reverse('llistaelectoral:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/access_denied.html')

    def test_assign_position_swaps_members(self):
        self.client.force_login(self.admin)
        a = IntegrantLlista.objects.create(candidatura=self.candidatura, usuari=self.admin)
        b = IntegrantLlista.objects.create(candidatura=self.candidatura, usuari=self.participant)
        p1 = PosicioLlista.objects.get(candidatura=self.candidatura, numero=1)
        p2 = PosicioLlista.objects.get(candidatura=self.candidatura, numero=2)
        p1.integrant = a
        p2.integrant = b
        p1.save()
        p2.save()

        response = self.client.post(
            reverse('llistaelectoral:assignar_posicio'),
            data=json.dumps({'integrant_id': b.pk, 'target_position': 1, 'source_position': 2}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        p1.refresh_from_db()
        p2.refresh_from_db()
        self.assertEqual(p1.integrant_id, b.pk)
        self.assertEqual(p2.integrant_id, a.pk)
