from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from agenda.models import Acte, SegmentVisibilitat

from .forms import ReunioForm
from .models import Reunio


class ReunioAgendaSyncTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.coord = User.objects.create_user(
            username='coord-reunio',
            password='test-pass-123',
            nom_complet='Coord Reunio',
            rol=User.Rol.COORDINACIO,
        )

    def test_saving_meeting_creates_linked_agenda_event_and_coordinacio_visibility(self):
        inici = timezone.now().replace(second=0, microsecond=0) + timedelta(days=3)
        form = ReunioForm(data={
            'titol': 'Executiva local',
            'tipus': Reunio.Tipus.INTERNA,
            'estat': Reunio.Estat.CONVOCADA,
            'inici': inici.strftime('%Y-%m-%dT%H:%M'),
            'fi': (inici + timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M'),
            'ubicacio': 'Online',
            'descripcio': 'Seguiment intern',
            'objectiu': 'Alinear equips',
            'area': '',
            'convocada_per': self.coord.pk,
            'moderada_per': self.coord.pk,
            'assistents': [],
            'persones_relacionades': [],
            'entitats_relacionades': [],
            'etiquetes': [],
            'es_estrategica': 'on',
            'es_interna': 'on',
            'acte_agenda': '',
        })

        self.assertTrue(form.is_valid(), form.errors)
        reunio = form.save()

        self.assertIsNotNone(reunio.acte_agenda)
        self.assertEqual(Acte.objects.count(), 1)
        self.assertEqual(reunio.acte_agenda.titol, reunio.titol)
        self.assertEqual(reunio.acte_agenda.estat, Acte.Estat.PUBLICAT)
        self.assertTrue(
            reunio.acte_agenda.visible_per.filter(
                ambit=SegmentVisibilitat.Ambit.ROL,
                codi=get_user_model().Rol.COORDINACIO,
            ).exists()
        )
