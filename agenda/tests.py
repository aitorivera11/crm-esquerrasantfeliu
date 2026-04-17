from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.timezone import localtime

from agenda.management.commands.import_city_events import CityEventsImporter, SOURCE_NAME
from reunions.models import Reunio, TipusReunio
from .forms import ActeForm
from .models import Acte, ParticipacioActe, SegmentVisibilitat


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


class ActeFormBehaviorTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='coord-form',
            password='test-pass-123',
            nom_complet='Coord Form',
        )

    def test_datetime_fields_are_rendered_with_datetime_local_format(self):
        acte = Acte.objects.create(
            titol='Acte amb dates',
            inici=timezone.now().replace(second=0, microsecond=0) + timedelta(days=2),
            fi=timezone.now().replace(second=0, microsecond=0) + timedelta(days=2, hours=1),
            ubicacio='Local',
            creador=self.user,
        )

        form = ActeForm(instance=acte)

        self.assertIn(f"value=\"{localtime(acte.inici).strftime('%Y-%m-%dT%H:%M')}\"", str(form['inici']))
        self.assertIn(f"value=\"{localtime(acte.fi).strftime('%Y-%m-%dT%H:%M')}\"", str(form['fi']))

    def test_accepts_datetime_local_input_format(self):
        inici = timezone.now().replace(second=0, microsecond=0) + timedelta(days=3)
        fi = inici + timedelta(hours=2)
        form = ActeForm(
            data={
                'titol': 'Acte nou',
                'tipus': '',
                'descripcio': 'Desc',
                'inici': inici.strftime('%Y-%m-%dT%H:%M'),
                'fi': fi.strftime('%Y-%m-%dT%H:%M'),
                'ubicacio': 'Local',
                'punt_trobada': '',
                'aforament': '',
                'visible_per': [],
                'estat': Acte.Estat.PUBLICAT,
            }
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_participant_selection_auto_adds_coordinacio_and_syncs_attendance(self):
        segment_coord, _ = SegmentVisibilitat.objects.get_or_create(
            ambit=SegmentVisibilitat.Ambit.ROL,
            codi=get_user_model().Rol.COORDINACIO,
            defaults={'etiqueta': 'Rol - Coordinació'},
        )
        segment_participant, _ = SegmentVisibilitat.objects.get_or_create(
            ambit=SegmentVisibilitat.Ambit.ROL,
            codi=get_user_model().Rol.PARTICIPANT,
            defaults={'etiqueta': 'Rol - Participant'},
        )
        segment_tipus, _ = SegmentVisibilitat.objects.get_or_create(
            ambit=SegmentVisibilitat.Ambit.TIPUS,
            codi=get_user_model().Tipus.MILITANT,
            defaults={'etiqueta': 'Tipus - Militant'},
        )
        inici = timezone.now().replace(second=0, microsecond=0) + timedelta(days=3)
        fi = inici + timedelta(hours=2)
        form = ActeForm(
            data={
                'titol': 'Acte segmentat',
                'tipus': '',
                'descripcio': 'Desc',
                'inici': inici.strftime('%Y-%m-%dT%H:%M'),
                'fi': fi.strftime('%Y-%m-%dT%H:%M'),
                'ubicacio': 'Local',
                'punt_trobada': '',
                'aforament': '',
                'visible_per': [str(segment_tipus.pk)],
                'estat': Acte.Estat.PUBLICAT,
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        form.instance.creador = self.user
        acte = form.save()

        self.assertQuerySetEqual(
            acte.visible_per.order_by('ambit', 'codi'),
            [segment_coord, segment_participant, segment_tipus],
            transform=lambda segment: segment,
        )
        self.assertQuerySetEqual(
            acte.assistencia_permesa_per.order_by('ambit', 'codi'),
            [segment_coord, segment_participant, segment_tipus],
            transform=lambda segment: segment,
        )

    def test_admin_segment_is_not_available_in_form_queryset(self):
        SegmentVisibilitat.objects.get_or_create(
            ambit=SegmentVisibilitat.Ambit.ROL,
            codi=get_user_model().Rol.ADMINISTRACIO,
            defaults={'etiqueta': 'Rol - Administració'},
        )

        form = ActeForm()

        self.assertFalse(form.fields['visible_per'].queryset.filter(codi=get_user_model().Rol.ADMINISTRACIO).exists())


class AgendaPermissionsAndFiltersTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.coord = User.objects.create_user(
            username='coord',
            password='test-pass-123',
            nom_complet='Coord',
            rol=User.Rol.COORDINACIO,
        )
        self.vol = User.objects.create_user(
            username='basic',
            password='test-pass-123',
            nom_complet='Basic',
            rol=User.Rol.PARTICIPANT,
            tipus=User.Tipus.MILITANT,
        )
        self.view_perm = Permission.objects.get(codename='can_view_participants')
        self.change_perm = Permission.objects.get(codename='change_acte')
        self.coord.user_permissions.add(self.view_perm, self.change_perm)

        self.segment_rol, _ = SegmentVisibilitat.objects.get_or_create(
            ambit=SegmentVisibilitat.Ambit.ROL,
            codi=User.Rol.COORDINACIO,
            defaults={'etiqueta': 'Rol - Coordinació'},
        )
        self.segment_tipus, _ = SegmentVisibilitat.objects.get_or_create(
            ambit=SegmentVisibilitat.Ambit.TIPUS,
            codi=User.Tipus.MILITANT,
            defaults={'etiqueta': 'Tipus - Militant'},
        )
        now = timezone.now().replace(second=0, microsecond=0)
        self.future_event = Acte.objects.create(
            titol='Acte futur',
            inici=now + timedelta(days=1),
            fi=now + timedelta(days=1, hours=2),
            ubicacio='Local',
            creador=self.coord,
            estat=Acte.Estat.PUBLICAT,
        )
        self.past_event = Acte.objects.create(
            titol='Acte passat',
            inici=now - timedelta(days=2),
            fi=now - timedelta(days=2, hours=-1),
            ubicacio='Ateneu',
            creador=self.coord,
            estat=Acte.Estat.PUBLICAT,
        )
        self.future_event.visible_per.add(self.segment_rol, self.segment_tipus)
        ParticipacioActe.objects.create(acte=self.future_event, usuari=self.coord, intencio=ParticipacioActe.Intencio.HI_ANIRE)

    def test_day_filter_can_show_past_day_without_show_past_toggle(self):
        self.client.force_login(self.coord)

        response = self.client.get(reverse('agenda:acte_list'), {'day': self.past_event.inici.date().isoformat()})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Acte passat')

    def test_show_past_toggle_remains_checked_in_context(self):
        self.client.force_login(self.coord)

        response = self.client.get(reverse('agenda:acte_list'), {'show_past': '1'})

        self.assertTrue(response.context['current_filters']['show_past'])

    def test_basic_user_does_not_see_admin_configuration_details(self):
        self.client.force_login(self.vol)

        response = self.client.get(reverse('agenda:acte_detail', args=[self.future_event.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Qui el pot veure i assistir:')
        self.assertNotContains(response, 'Participants')
        self.assertNotContains(response, 'Hi van')
        self.assertContains(response, 'La meva resposta')

    def test_detail_context_exposes_social_share_links(self):
        self.client.force_login(self.coord)

        response = self.client.get(reverse('agenda:acte_detail', args=[self.future_event.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertIn('wa.me/?text=', response.context['whatsapp_url'])
        self.assertIn('calendar.google.com/calendar/render', response.context['google_calendar_url'])
        self.assertTrue(response.context['ics_url'].endswith(f"/agenda/{self.future_event.pk}/calendar.ics"))
        self.assertContains(response, 'Comparteix i exporta')
        self.assertContains(response, 'Google Calendar')

    def test_ics_export_returns_calendar_file(self):
        self.client.force_login(self.coord)

        response = self.client.get(reverse('agenda:acte_ics', args=[self.future_event.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/calendar; charset=utf-8')
        self.assertIn('attachment;', response['Content-Disposition'])
        self.assertContains(response, 'BEGIN:VCALENDAR')
        self.assertContains(response, 'SUMMARY:Acte futur')


class AgendaImportedAndImportantUxTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username='ux-user',
            password='test-pass-123',
            nom_complet='UX User',
            rol=User.Rol.COORDINACIO,
        )
        now = timezone.now().replace(second=0, microsecond=0)
        self.local_event = Acte.objects.create(
            titol='Acte local visible',
            inici=now + timedelta(days=1),
            ubicacio='Casal',
            creador=self.user,
            estat=Acte.Estat.PUBLICAT,
            es_important=True,
        )
        self.imported_event = Acte.objects.create(
            titol='Acte importat ocult',
            inici=now + timedelta(days=2),
            ubicacio='Plaça',
            creador=self.user,
            estat=Acte.Estat.PUBLICAT,
            external_source='AGENDA_CIUTAT',
            external_id='city-1',
        )

    def test_imported_events_are_hidden_by_default_in_list(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('agenda:acte_list'))

        self.assertContains(response, 'Acte local visible')
        self.assertNotContains(response, 'Acte importat ocult')

    def test_imported_events_can_be_shown_with_toggle(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('agenda:acte_list'), {'show_imported': '1'})

        self.assertContains(response, 'Acte importat ocult')
        self.assertTrue(response.context['current_filters']['show_imported'])

    def test_important_badge_is_rendered_in_list(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('agenda:acte_list'))

        self.assertContains(response, 'Important')

    def test_default_list_filters_next_seven_days(self):
        self.client.force_login(self.user)
        later_event = Acte.objects.create(
            titol='Acte massa llunyà',
            inici=timezone.now().replace(second=0, microsecond=0) + timedelta(days=12),
            ubicacio='Lluny',
            creador=self.user,
            estat=Acte.Estat.PUBLICAT,
        )

        response = self.client.get(reverse('agenda:acte_list'))

        self.assertContains(response, 'Acte local visible')
        self.assertNotContains(response, later_event.titol)
        self.assertEqual(response.context['current_filters']['date_to'], (timezone.localdate() + timedelta(days=6)).isoformat())

    def test_text_search_filters_the_list(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('agenda:acte_list'), {'q': 'Casal'})

        self.assertContains(response, 'Acte local visible')
        self.assertNotContains(response, 'Acte importat ocult')

    def test_admin_cards_show_compact_social_actions(self):
        self.client.force_login(self.user)
        self.user.user_permissions.add(Permission.objects.get(codename='change_acte'))

        response = self.client.get(reverse('agenda:acte_list'))

        self.assertContains(response, 'aria-label="Compartir enllaç"')
        self.assertContains(response, 'aria-label="Compartir per WhatsApp"')
        self.assertContains(response, 'aria-label="Afegir al calendari"')

    def test_compact_card_uses_short_cta_labels(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('agenda:acte_list'))

        self.assertContains(response, '>Sí<', html=False)
        self.assertContains(response, '>Potser<', html=False)
        self.assertContains(response, '>No<', html=False)

    def test_list_shows_admin_sync_button_for_users_with_change_permission(self):
        self.client.force_login(self.user)
        self.user.user_permissions.add(Permission.objects.get(codename='change_acte'))

        response = self.client.get(reverse('agenda:acte_list'))

        self.assertContains(response, 'Sincronitzar importats')

    def test_sync_imported_events_endpoint_requires_permissions(self):
        User = get_user_model()
        basic_user = User.objects.create_user(
            username='basic-sync-user',
            password='test-pass-123',
            nom_complet='Basic Sync User',
            rol=User.Rol.PARTICIPANT,
        )
        self.client.force_login(basic_user)

        response = self.client.post(reverse('agenda:sync_imported_events'))

        self.assertIn(response.status_code, {403, 405})

    @patch('agenda.views.call_command')
    def test_sync_imported_events_runs_import_command(self, mocked_call_command):
        self.client.force_login(self.user)
        self.user.user_permissions.add(Permission.objects.get(codename='change_acte'))

        response = self.client.post(reverse('agenda:sync_imported_events'))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('agenda:acte_list'))
        mocked_call_command.assert_called_once()
        self.assertEqual(mocked_call_command.call_args.args, ('import_city_events', '--cleanup'))


class AgendaMeetingSyncTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.coord = User.objects.create_user(
            username='coord-sync',
            password='test-pass-123',
            nom_complet='Coord Sync',
            rol=User.Rol.COORDINACIO,
        )
        self.participant = User.objects.create_user(
            username='participant-sync',
            password='test-pass-123',
            nom_complet='Participant Sync',
            rol=User.Rol.COORDINACIO,
        )
        self.client.force_login(self.participant)
        now = timezone.now().replace(second=0, microsecond=0) + timedelta(days=2)
        self.acte = Acte.objects.create(
            titol='Executiva local',
            inici=now,
            fi=now + timedelta(hours=2),
            ubicacio='Online',
            creador=self.coord,
            estat=Acte.Estat.PUBLICAT,
        )
        self.reunio = Reunio.objects.create(
            titol='Executiva local',
            tipus=TipusReunio.objects.get_or_create(codi='interna', defaults={'nom': 'Reunió interna', 'ordre': 0})[0],
            estat=Reunio.Estat.CONVOCADA,
            inici=self.acte.inici,
            fi=self.acte.fi,
            ubicacio=self.acte.ubicacio,
            descripcio='Seguiment setmanal',
            convocada_per=self.coord,
            moderada_per=self.coord,
            acte_agenda=self.acte,
        )

    def test_confirming_participation_adds_user_to_linked_meeting_attendees(self):
        response = self.client.post(
            reverse('agenda:participar_acte', args=[self.acte.pk]),
            {'intencio': ParticipacioActe.Intencio.HI_ANIRE, 'observacions': '', 'render_mode': 'detail'},
        )

        self.assertEqual(response.status_code, 200)
        self.reunio.refresh_from_db()
        self.assertTrue(self.reunio.assistents.filter(pk=self.participant.pk).exists())

    def test_declining_participation_removes_user_from_linked_meeting_attendees(self):
        self.reunio.assistents.add(self.participant)

        response = self.client.post(
            reverse('agenda:participar_acte', args=[self.acte.pk]),
            {'intencio': ParticipacioActe.Intencio.NO_HI_ANIRE, 'observacions': '', 'render_mode': 'detail'},
        )

        self.assertEqual(response.status_code, 200)
        self.reunio.refresh_from_db()
        self.assertFalse(self.reunio.assistents.filter(pk=self.participant.pk).exists())

    def test_acte_detail_shows_link_to_meeting_management(self):
        response = self.client.get(reverse('agenda:acte_detail', args=[self.acte.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Gestionar reunió')


class ImportCityEventsCleanupPolicyTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username='import-cleanup-user',
            password='test-pass-123',
            nom_complet='Import Cleanup User',
            rol=User.Rol.COORDINACIO,
        )
        now = timezone.now().replace(second=0, microsecond=0)
        self.past_imported = Acte.objects.create(
            titol='Importat passat',
            inici=now - timedelta(days=10),
            ubicacio='Plaça',
            creador=self.user,
            estat=Acte.Estat.PUBLICAT,
            external_source=SOURCE_NAME,
            external_id='past-1',
        )
        self.future_imported_stale = Acte.objects.create(
            titol='Importat futur desaparegut',
            inici=now + timedelta(days=10),
            ubicacio='Casal',
            creador=self.user,
            estat=Acte.Estat.PUBLICAT,
            external_source=SOURCE_NAME,
            external_id='future-stale-1',
        )

    @patch.object(CityEventsImporter, 'fetch_all_events', return_value=[])
    @patch.object(CityEventsImporter, 'normalize_records', return_value=[])
    @patch.object(CityEventsImporter, 'get_owner_user')
    @patch.object(CityEventsImporter, 'get_external_type', return_value=None)
    def test_cleanup_deletes_only_future_missing_imported_events(
        self,
        mocked_external_type,
        mocked_owner_user,
        mocked_normalize,
        mocked_fetch,
    ):
        mocked_owner_user.return_value = self.user
        importer = CityEventsImporter(days_ahead=60, stdout=None)

        stats = importer.run(cleanup=True)

        self.assertEqual(stats['cleanup'], 1)
        self.assertTrue(Acte.objects.filter(pk=self.past_imported.pk).exists())
        self.assertFalse(Acte.objects.filter(pk=self.future_imported_stale.pk).exists())


class ImportCityEventsTypeFilterTests(TestCase):
    def test_normalize_records_skips_sports_competitions(self):
        importer = CityEventsImporter(days_ahead=60, stdout=None)
        records = [
            {
                "_id": 1,
                "ID": "sport-1",
                "TITOL": "Torneig local",
                "TIPUS_ACTE": "Competició esportiva",
                "DATA_HORA_INICI_ACTE": "20260420090000",
                "NOM_LLOC": "Pavelló",
                "ADREÇA_COMPLETA": "Carrer Major, 1",
            },
            {
                "_id": 2,
                "ID": "culture-1",
                "TITOL": "Concert de primavera",
                "TIPUS_ACTE": "Concert",
                "DATA_HORA_INICI_ACTE": "20260420110000",
                "NOM_LLOC": "Ateneu",
                "ADREÇA_COMPLETA": "Plaça de la Vila, 2",
            },
        ]

        normalized = importer.normalize_records(records)

        self.assertEqual(len(normalized), 1)
        self.assertEqual(normalized[0]["external_id"], "culture-1")
