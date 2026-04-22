from django.core.exceptions import ValidationError
from django.db import models

from core.models import TimeStampedModel
from persones.models import Persona
from usuaris.models import Usuari


class Candidatura(TimeStampedModel):
    nom = models.CharField(max_length=120, default='Municipals 2027')
    activa = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'candidatura'
        verbose_name_plural = 'candidatures'
        permissions = [('manage_electoral_list', 'Pot gestionar la llista electoral')]

    def __str__(self):
        return self.nom


class IntegrantLlista(TimeStampedModel):
    class Afiliacio(models.TextChoices):
        INDEPENDENT = 'INDEPENDENT', 'Independent'
        JOVENT = 'JOVENT', 'Jovent'
        ESQUERRA = 'ESQUERRA', 'Esquerra'

    class Estat(models.TextChoices):
        CONFIRMADA = 'CONFIRMADA', 'Confirmada'
        PENDENT = 'PENDENT', 'Pendent de confirmació'
        IDEA = 'IDEA', 'Idea'

    candidatura = models.ForeignKey(Candidatura, on_delete=models.CASCADE, related_name='integrants')
    persona = models.ForeignKey(Persona, on_delete=models.SET_NULL, null=True, blank=True, related_name='candidatures')
    usuari = models.ForeignKey(Usuari, on_delete=models.SET_NULL, null=True, blank=True, related_name='candidatures')
    afiliacio = models.CharField(max_length=20, choices=Afiliacio.choices, default=Afiliacio.ESQUERRA)
    estat = models.CharField(max_length=20, choices=Estat.choices, default=Estat.IDEA)

    class Meta:
        verbose_name = 'integrant de llista'
        verbose_name_plural = 'integrants de llista'
        unique_together = ('candidatura', 'persona', 'usuari')

    def clean(self):
        super().clean()
        if not self.persona and not self.usuari:
            raise ValidationError('Cal seleccionar una persona o un usuari.')

    @property
    def nom_mostrat(self):
        if self.persona_id:
            return self.persona.nom
        if self.usuari_id:
            return self.usuari.nom_complet or self.usuari.username
        return '(sense nom)'

    def __str__(self):
        return self.nom_mostrat


class PermisLlistaElectoral(TimeStampedModel):
    user = models.ForeignKey(Usuari, on_delete=models.CASCADE, related_name='permisos_llista_electoral')

    class Meta:
        verbose_name = 'permís llista electoral'
        verbose_name_plural = 'permisos llista electoral'
        constraints = [models.UniqueConstraint(fields=['user'], name='uniq_permis_llista_user')]

    def __str__(self):
        return self.user.nom_complet or self.user.username


class PosicioLlista(TimeStampedModel):
    MIN_POSICIO = 1
    MAX_POSICIO = 31
    LIMIT_TITULARS = 21

    candidatura = models.ForeignKey(Candidatura, on_delete=models.CASCADE, related_name='posicions')
    numero = models.PositiveSmallIntegerField()
    integrant = models.OneToOneField(
        IntegrantLlista,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='posicio',
    )

    class Meta:
        verbose_name = 'posició de llista'
        verbose_name_plural = 'posicions de llista'
        unique_together = ('candidatura', 'numero')
        ordering = ('numero',)

    def clean(self):
        super().clean()
        if self.numero < self.MIN_POSICIO or self.numero > self.MAX_POSICIO:
            raise ValidationError(f'La posició ha d’estar entre {self.MIN_POSICIO} i {self.MAX_POSICIO}.')

    @property
    def es_titular(self):
        return self.numero <= self.LIMIT_TITULARS
