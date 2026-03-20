from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuari(AbstractUser):
    class Rol(models.TextChoices):
        ADMINISTRADOR = 'ADMINISTRADOR', 'Administrador'
        COORDINADOR = 'COORDINADOR', 'Coordinador'
        VOLUNTARI = 'VOLUNTARI', 'Bàsic'
        CONSULTA = 'CONSULTA', 'Consulta'

    class Tipus(models.TextChoices):
        MILITANT = 'MILITANT', 'Militant'
        VOLUNTARI = 'VOLUNTARI', 'Voluntari/a'
        AMIC = 'AMIC', 'Amic o amiga'

    nom_complet = models.CharField(max_length=255)
    telefon = models.CharField(max_length=20, blank=True)
    rol = models.CharField(max_length=20, choices=Rol.choices, default=Rol.VOLUNTARI)
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

    @property
    def esta_pendent_activacio(self):
        return not self.is_active

    def __str__(self):
        return self.nom_complet or self.username
