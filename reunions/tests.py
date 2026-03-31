from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from agenda.models import Acte, SegmentVisibilitat

from .forms import ReunioForm, sincronitzar_punts_acta_amb_ordre_dia
from .models import Acta, PuntActa, PuntOrdreDia, Reunio, Tasca
from .views import generar_text_ordre_dia, parse_task_commands


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


class PuntOrdreDiaMoveTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.coord = User.objects.create_user(
            username='coord-move-ordre',
            password='pass',
            nom_complet='Coord Move',
            rol=User.Rol.COORDINACIO,
        )
        self.reunio = Reunio.objects.create(
            titol='Reunió ordre del dia',
            tipus=Reunio.Tipus.INTERNA,
            estat=Reunio.Estat.PREPARACIO,
            inici=timezone.now() + timedelta(days=1),
            convocada_per=self.coord,
            moderada_per=self.coord,
        )
        self.punt_1 = PuntOrdreDia.objects.create(reunio=self.reunio, ordre=1, titol='Punt 1')
        self.punt_2 = PuntOrdreDia.objects.create(reunio=self.reunio, ordre=2, titol='Punt 2')
        self.punt_3 = PuntOrdreDia.objects.create(reunio=self.reunio, ordre=3, titol='Punt 3')

    def test_move_down_swaps_order_without_unique_constraint_error(self):
        self.client.force_login(self.coord)
        response = self.client.post(
            reverse('reunions:punt_ordre_move', kwargs={'pk': self.reunio.pk, 'punt_pk': self.punt_2.pk}),
            {'direction': 'down'},
        )

        self.assertEqual(response.status_code, 302)
        self.punt_2.refresh_from_db()
        self.punt_3.refresh_from_db()
        self.assertEqual(self.punt_2.ordre, 3)
        self.assertEqual(self.punt_3.ordre, 2)


class ActaTaskCommandTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.coord = User.objects.create_user(
            username='coord-acta',
            password='pass',
            nom_complet='Coord Acta',
            rol=User.Rol.COORDINACIO,
        )
        self.altre = User.objects.create_user(
            username='jenny',
            password='pass',
            nom_complet='Jenny',
            rol=User.Rol.COORDINACIO,
        )
        self.reunio = Reunio.objects.create(
            titol='Reunió comissions',
            tipus=Reunio.Tipus.INTERNA,
            estat=Reunio.Estat.CELEBRADA,
            inici=timezone.now() - timedelta(days=1),
            convocada_per=self.coord,
            moderada_per=self.coord,
        )
        self.acta = Acta.objects.create(reunio=self.reunio, redactada_per=self.coord)
        self.punt = PuntActa.objects.create(acta=self.acta, ordre=1, titol='Comissions')

    def test_parse_task_commands_supports_username_date_and_priority(self):
        commands = parse_task_commands('@tasca Demanar estand Sant Jordi | @jenny | 2030-04-05 | URGENT')
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0]['title'], 'Demanar estand Sant Jordi')
        self.assertEqual(commands[0]['username'], 'jenny')
        self.assertEqual(str(commands[0]['due_date']), '2030-04-05')
        self.assertEqual(commands[0]['priority'], Tasca.Prioritat.URGENT)

    def test_command_endpoint_creates_tasks_linked_to_point(self):
        self.client.force_login(self.coord)
        response = self.client.post(
            reverse('reunions:punt_acta_task_command_create', kwargs={'pk': self.punt.pk}),
            {'content': '@tasca Trucar al Gerard | @jenny | 2030-05-01 | ALTA'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Tasca.objects.count(), 1)
        task = Tasca.objects.first()
        self.assertEqual(task.reunio_origen_id, self.reunio.pk)
        self.assertEqual(task.punt_acta_origen_id, self.punt.pk)
        self.assertEqual(task.responsable_id, self.altre.pk)
        self.assertEqual(task.prioritat, Tasca.Prioritat.ALTA)


class OrdreDiaShareTextTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.coord = User.objects.create_user(
            username='coord-share-ordre',
            password='pass',
            nom_complet='Coord Share',
            rol=User.Rol.COORDINACIO,
        )
        self.reunio = Reunio.objects.create(
            titol='Trobada Pla de Campanya',
            tipus=Reunio.Tipus.INTERNA,
            estat=Reunio.Estat.CONVOCADA,
            inici=timezone.now().replace(second=0, microsecond=0) + timedelta(days=1),
            fi=timezone.now().replace(second=0, microsecond=0) + timedelta(days=1, hours=2, minutes=30),
            ubicacio='Local',
            convocada_per=self.coord,
            moderada_per=self.coord,
        )
        PuntOrdreDia.objects.create(reunio=self.reunio, ordre=1, titol='Formació ENGEGA')

    def test_generar_text_ordre_dia_includes_schedule_location_and_link(self):
        text = generar_text_ordre_dia(self.reunio, share_url='https://crm-esquerrasantfeliu.vercel.app/agenda/175/')

        self.assertIn('Trobada Pla de Campanya', text)
        self.assertIn('📅 ', text)
        self.assertIn('⏱️ Fins a les ', text)
        self.assertIn('📍 Local', text)
        self.assertIn('Ordre del dia', text)
        self.assertIn('1. Formació ENGEGA', text)
        self.assertTrue(text.endswith('https://crm-esquerrasantfeliu.vercel.app/agenda/175/'))


class ActaOrdreDiaSyncTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.coord = User.objects.create_user(
            username='coord-sync-acta',
            password='pass',
            nom_complet='Coord Sync',
            rol=User.Rol.COORDINACIO,
        )
        self.reunio = Reunio.objects.create(
            titol='Reunió amb ordre canviant',
            tipus=Reunio.Tipus.INTERNA,
            estat=Reunio.Estat.CELEBRADA,
            inici=timezone.now() + timedelta(days=1),
            convocada_per=self.coord,
            moderada_per=self.coord,
        )
        self.acta = Acta.objects.create(reunio=self.reunio, redactada_per=self.coord)
        self.client.force_login(self.coord)

    def test_sincronitzar_no_duplica_i_afegeix_només_punts_faltants(self):
        punt1 = PuntOrdreDia.objects.create(reunio=self.reunio, ordre=1, titol='Seguiment')
        creats_inicials = sincronitzar_punts_acta_amb_ordre_dia(self.acta)
        self.assertEqual(creats_inicials, 1)
        self.assertEqual(self.acta.punts.count(), 1)

        PuntOrdreDia.objects.create(reunio=self.reunio, ordre=2, titol='Torn obert')
        creats_posteriors = sincronitzar_punts_acta_amb_ordre_dia(self.acta)

        self.assertEqual(creats_posteriors, 1)
        self.assertEqual(self.acta.punts.count(), 2)
        self.assertTrue(self.acta.punts.filter(punt_ordre_origen=punt1).exists())

    def test_crear_punt_des_de_tasca_actualitza_acta_si_ja_existeix(self):
        tasca = Tasca.objects.create(
            titol='Punt per tractar',
            creada_per=self.coord,
            responsable=self.coord,
            origen=Tasca.Origen.INDEPENDENT,
            proposar_seguent_ordre_dia=True,
        )

        response = self.client.post(
            reverse('reunions:punt_ordre_from_tasca', kwargs={'pk': self.reunio.pk, 'tasca_pk': tasca.pk}),
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.reunio.punts_ordre_dia.count(), 1)
        self.assertEqual(self.acta.punts.count(), 1)
        punt_acta = self.acta.punts.first()
        self.assertTrue(punt_acta.ve_de_ordre_dia)
        self.assertIsNotNone(punt_acta.punt_ordre_origen_id)
