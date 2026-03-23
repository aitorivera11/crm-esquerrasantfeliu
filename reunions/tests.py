from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
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

    def _build_form(self, **overrides):
        inici = timezone.now().replace(second=0, microsecond=0) + timedelta(days=3)
        data = {
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
        }
        data.update(overrides)
        return ReunioForm(data=data)

    def test_saving_meeting_creates_linked_agenda_event_and_coordinacio_visibility(self):
        form = self._build_form()

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

    def test_updating_meeting_to_non_internal_clears_restricted_visibility(self):
        create_form = self._build_form()
        self.assertTrue(create_form.is_valid(), create_form.errors)
        reunio = create_form.save()
        self.assertTrue(reunio.acte_agenda.visible_per.exists())

        update_data = {
            'titol': reunio.titol,
            'tipus': reunio.tipus,
            'estat': reunio.estat,
            'inici': timezone.localtime(reunio.inici).strftime('%Y-%m-%dT%H:%M'),
            'fi': timezone.localtime(reunio.fi).strftime('%Y-%m-%dT%H:%M'),
            'ubicacio': reunio.ubicacio,
            'descripcio': reunio.descripcio,
            'objectiu': reunio.objectiu,
            'area': reunio.area_id or '',
            'convocada_per': reunio.convocada_per_id,
            'moderada_per': reunio.moderada_per_id or '',
            'assistents': [],
            'persones_relacionades': [],
            'entitats_relacionades': [],
            'etiquetes': [],
            'es_estrategica': 'on',
            'acte_agenda': reunio.acte_agenda_id,
        }
        update_form = ReunioForm(data=update_data, instance=reunio)

        self.assertTrue(update_form.is_valid(), update_form.errors)
        reunio = update_form.save()
        reunio.acte_agenda.refresh_from_db()

        self.assertFalse(reunio.es_interna)
        self.assertFalse(reunio.acte_agenda.visible_per.exists())
        self.assertFalse(reunio.acte_agenda.assistencia_permesa_per.exists())


class ReunionsPermissionsTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.coord = User.objects.create_user(username='coord-reunions', password='pass', nom_complet='Coord', rol=User.Rol.COORDINACIO)
        self.participant = User.objects.create_user(username='participant-reunions', password='pass', nom_complet='Participant', rol=User.Rol.PARTICIPANT)

    def test_participant_cannot_access_reunions_list(self):
        self.client.force_login(self.participant)
        response = self.client.get(reverse('reunions:reunio_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Accés denegat')

    def test_coord_can_access_reunions_list(self):
        self.client.force_login(self.coord)
        response = self.client.get(reverse('reunions:reunio_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Reunions i assemblees')
