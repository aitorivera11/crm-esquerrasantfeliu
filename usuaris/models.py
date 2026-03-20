from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuari(AbstractUser):
    class Rol(models.TextChoices):
        ADMINISTRACIO = 'ADMINISTRACIO', 'Administració'
        COORDINACIO = 'COORDINACIO', 'Coordinació'
        PARTICIPANT = 'PARTICIPANT', 'Participant'

        @classmethod
        def normalize(cls, value):
            legacy_map = {
                'ADMINISTRADOR': cls.ADMINISTRACIO,
                'COORDINADOR': cls.COORDINACIO,
                'VOLUNTARI': cls.PARTICIPANT,
                'CONSULTA': cls.PARTICIPANT,
                cls.ADMINISTRACIO: cls.ADMINISTRACIO,
                cls.COORDINACIO: cls.COORDINACIO,
                cls.PARTICIPANT: cls.PARTICIPANT,
            }
            return legacy_map.get(value, cls.PARTICIPANT)

    class Tipus(models.TextChoices):
        MILITANT = 'MILITANT', 'Militant'
        VOLUNTARI = 'VOLUNTARI', 'Voluntari/a'
        AMIC = 'AMIC', 'Amic o amiga'

    nom_complet = models.CharField(max_length=255)
    telefon = models.CharField(max_length=20, blank=True)
    rol = models.CharField(max_length=20, choices=Rol.choices, default=Rol.PARTICIPANT)
    tipus = models.CharField(
        max_length=20,
        choices=Tipus.choices,
        blank=True,
        default='',
        help_text='Classificació interna per distingir militants, voluntaris i amics.',
    )

    class Meta:
        verbose_name = 'usuari'
        verbose_name_plural = 'usuaris'

    def save(self, *args, **kwargs):
        self.rol = self.Rol.normalize(self.rol)
        super().save(*args, **kwargs)

    @property
    def esta_pendent_activacio(self):
        return not self.is_active

    @property
    def es_administracio(self):
        return self.rol == self.Rol.ADMINISTRACIO

    def __str__(self):
        return self.nom_complet or self.username
