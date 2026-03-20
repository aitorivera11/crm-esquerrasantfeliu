from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.timezone import localtime

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

        self.assertIn(f'value="{localtime(acte.inici).strftime('%Y-%m-%dT%H:%M')}"', str(form['inici']))
        self.assertIn(f'value="{localtime(acte.fi).strftime('%Y-%m-%dT%H:%M')}"', str(form['fi']))

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
                'assistencia_permesa_per': [],
                'estat': Acte.Estat.PUBLICAT,
            }
        )

        self.assertTrue(form.is_valid(), form.errors)


class AgendaPermissionsAndFiltersTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.coord = User.objects.create_user(
            username='coord',
            password='test-pass-123',
            nom_complet='Coord',
            rol=User.Rol.COORDINADOR,
        )
        self.vol = User.objects.create_user(
            username='basic',
            password='test-pass-123',
            nom_complet='Basic',
            rol=User.Rol.VOLUNTARI,
            tipus=User.Tipus.MILITANT,
        )
        self.view_perm = Permission.objects.get(codename='can_view_participants')
        self.change_perm = Permission.objects.get(codename='change_acte')
        self.coord.user_permissions.add(self.view_perm, self.change_perm)

        self.segment_rol, _ = SegmentVisibilitat.objects.get_or_create(
            ambit=SegmentVisibilitat.Ambit.ROL,
            codi=User.Rol.COORDINADOR,
            defaults={'etiqueta': 'Rol - Coordinador'},
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
        self.future_event.assistencia_permesa_per.add(self.segment_tipus)
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
        self.assertNotContains(response, 'Qui el pot veure:')
        self.assertNotContains(response, 'Participants')
        self.assertNotContains(response, 'Hi van')
        self.assertContains(response, 'La meva resposta')
