from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from agenda.models import Acte
from entitats.management.commands.import_entities import EntitiesImporter
from persones.models import Persona

from .models import Entitat


class EntitatsPermissionsTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(username='admin', password='pass', nom_complet='Admin', rol=User.Rol.ADMINISTRACIO)
        self.coord = User.objects.create_user(username='coord-ent', password='pass', nom_complet='Coord', rol=User.Rol.COORDINACIO)
        self.participant = User.objects.create_user(username='participant-ent', password='pass', nom_complet='Participant', rol=User.Rol.PARTICIPANT)

    def test_participant_cannot_access_entitats_list(self):
        self.client.force_login(self.participant)
        response = self.client.get(reverse('entitats:entitat_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Accés denegat')

    def test_coord_can_create_entitat_and_link_persona(self):
        persona = Persona.objects.create(nom='Maria Exemple', email='maria@example.com')
        self.client.force_login(self.coord)
        response = self.client.post(reverse('entitats:entitat_create'), {
            'nom': 'Ateneu Popular',
            'email': 'info@ateneu.cat',
            'telefon': '600123123',
            'web': 'https://ateneu.cat',
            'tipologia': 'Associació',
            'ambit': 'Cultural',
            'persones': [persona.pk],
            'notes': 'Contacte estable',
        })
        self.assertRedirects(response, reverse('entitats:entitat_list'))
        entitat = Entitat.objects.get(nom='Ateneu Popular')
        self.assertEqual(list(entitat.persones.all()), [persona])


class EntitatsImporterTests(TestCase):
    def test_normalize_records_maps_expected_fields(self):
        importer = EntitiesImporter(stdout=None)
        records = [{
            '_id': 7,
            'NOM': 'Associació Veïnal',
            'MAIL': 'contacte@example.org',
            'TELEFON': '931234567',
            'WEB': 'example.org',
            'TIPOLOGIA': 'Associació',
            'AMBIT': 'Barri',
        }]

        normalized = importer.normalize_records(records)

        self.assertEqual(len(normalized), 1)
        self.assertEqual(normalized[0]['nom'], 'Associació Veïnal')
        self.assertEqual(normalized[0]['email'], 'contacte@example.org')
        self.assertEqual(normalized[0]['telefon'], '931234567')
        self.assertEqual(normalized[0]['web'], 'https://example.org')
        self.assertEqual(normalized[0]['tipologia'], 'Associació')
        self.assertEqual(normalized[0]['ambit'], 'Barri')


class AgendaRelationsTests(TestCase):
    def test_acte_can_link_entitats_and_persones(self):
        User = get_user_model()
        user = User.objects.create_user(username='agenda-rel', password='pass', nom_complet='Agenda Rel', rol=User.Rol.COORDINACIO)
        persona = Persona.objects.create(nom='Laura Rel')
        entitat = Entitat.objects.create(nom='Colla Rel')
        entitat.persones.add(persona)
        acte = Acte.objects.create(titol='Reunió de seguiment', inici='2030-01-01T10:00:00Z', ubicacio='Seu', creador=user)
        acte.persones_relacionades.add(persona)
        acte.entitats_relacionades.add(entitat)

        self.assertEqual(list(acte.persones_relacionades.all()), [persona])
        self.assertEqual(list(acte.entitats_relacionades.all()), [entitat])
