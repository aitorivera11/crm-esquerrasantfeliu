from django.conf import settings
from django.db import models
from django.urls import reverse

from core.models import TimeStampedModel


class Acte(TimeStampedModel):
    class Estat(models.TextChoices):
        ESBORRANY = 'ESBORRANY', 'Esborrany'
        PUBLICAT = 'PUBLICAT', 'Publicat'

    titol = models.CharField(max_length=255)
    descripcio = models.TextField(blank=True)
    inici = models.DateTimeField()
    ubicacio = models.CharField(max_length=255)
    estat = models.CharField(max_length=20, choices=Estat.choices, default=Estat.ESBORRANY)
    creador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='actes_creats',
    )

    class Meta:
        ordering = ['inici']
        permissions = [
            ('can_view_participants', 'Pot veure participants'),
            ('can_mark_attendance', 'Pot marcar assistència real'),
        ]

    def __str__(self):
        return self.titol

    def get_absolute_url(self):
        return reverse('agenda:acte_detail', kwargs={'pk': self.pk})


class ParticipacioActe(TimeStampedModel):
    class Intencio(models.TextChoices):
        HI_ANIRE = 'HI_ANIRE', 'Hi aniré'
        POTSER = 'POTSER', 'Potser'
        NO_HI_ANIRE = 'NO_HI_ANIRE', 'No hi aniré'

    class AssistenciaReal(models.TextChoices):
        PENDENT = 'PENDENT', 'Pendent'
        ASSISTEIX = 'ASSISTEIX', 'Ha assistit'
        NO_ASSISTEIX = 'NO_ASSISTEIX', 'No ha assistit'

    usuari = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='participacions_actes',
    )
    acte = models.ForeignKey(
        Acte,
        on_delete=models.CASCADE,
        related_name='participants',
    )
    intencio = models.CharField(max_length=20, choices=Intencio.choices)
    assistencia_real = models.CharField(
        max_length=20,
        choices=AssistenciaReal.choices,
        default=AssistenciaReal.PENDENT,
    )
    observacions = models.TextField(blank=True)

    class Meta:
        ordering = ['usuari__nom_complet', 'usuari__username']
        unique_together = ('usuari', 'acte')
        verbose_name = 'participació a acte'
        verbose_name_plural = 'participacions a actes'

    def __str__(self):
        return f'{self.usuari} · {self.acte} · {self.intencio}'
