from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from agenda.models import Acte
from entitats.models import Entitat
from reunions.models import Reunio, Tasca, TipusReunio

from .models import Persona


class PersonesPermissionsTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.coord = User.objects.create_user(username='coord-per', password='pass', nom_complet='Coord', rol=User.Rol.COORDINACIO)
        self.participant = User.objects.create_user(
            username='participant-per',
            password='pass',
            nom_complet='Participant',
            rol=User.Rol.PARTICIPANT,
        )

    def test_participant_cannot_access_persones_list(self):
        self.client.force_login(self.participant)
        response = self.client.get(reverse('persones:persona_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Accés denegat')

    def test_persona_detail_shows_related_tracking_data(self):
        persona = Persona.objects.create(nom='Núria Seguiment', email='nuria@example.com')
        entitat = Entitat.objects.create(nom='Ateneu Seguiment')
        entitat.persones.add(persona)

        tipus = TipusReunio.objects.create(codi='seguiment', nom='Seguiment')
        reunio = Reunio.objects.create(
            titol='Trobada d’entorn',
            tipus=tipus,
            inici=timezone.now(),
            convocada_per=self.coord,
        )
        reunio.persones_relacionades.add(persona)

        tasca = Tasca.objects.create(
            titol='Preparar retorn a la persona',
            creada_per=self.coord,
            responsable=self.coord,
        )
        tasca.persones_relacionades.add(persona)

        acte = Acte.objects.create(
            titol='Assemblea barri',
            inici=timezone.now(),
            ubicacio='Centre Cívic',
            creador=self.coord,
        )
        acte.persones_relacionades.add(persona)

        self.client.force_login(self.coord)
        response = self.client.get(reverse('persones:persona_detail', args=[persona.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Trobada d’entorn')
        self.assertContains(response, 'Preparar retorn a la persona')
        self.assertContains(response, 'Assemblea barri')
        self.assertContains(response, 'Ateneu Seguiment')
