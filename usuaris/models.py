from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuari(AbstractUser):
    class Rol(models.TextChoices):
        ADMINISTRADOR = 'ADMINISTRADOR', 'Administrador'
        COORDINADOR = 'COORDINADOR', 'Coordinador'
        VOLUNTARI = 'VOLUNTARI', 'Voluntari / militant'
        CONSULTA = 'CONSULTA', 'Consulta'

    class Tipus(models.TextChoices):
        MILITANT = 'MILITANT', 'Militant'
        VOLUNTARI = 'VOLUNTARI', 'Voluntari'
        AMIC = 'AMIC', 'Amic'

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

    def __str__(self):
        return self.nom_complet or self.username
