from django.conf import settings
from django.db import models
from django.db.models import Q
from django.urls import reverse

from core.models import TimeStampedModel
from entitats.models import Entitat


class ActeTipus(TimeStampedModel):
    nom = models.CharField(max_length=100, unique=True)
    descripcio = models.TextField(blank=True)
    color = models.CharField(max_length=7, blank=True, help_text='Color HEX opcional per destacar el tipus.')
    ordre = models.PositiveIntegerField(default=0)
    actiu = models.BooleanField(default=True)

    class Meta:
        ordering = ['ordre', 'nom']
        verbose_name = "tipus d'acte"
        verbose_name_plural = "tipus d'actes"

    def __str__(self):
        return self.nom


class SegmentVisibilitat(TimeStampedModel):
    class Ambit(models.TextChoices):
        ROL = 'ROL', 'Rol'
        TIPUS = 'TIPUS', "Tipus d'usuari"

    ambit = models.CharField(max_length=10, choices=Ambit.choices)
    codi = models.CharField(max_length=50)
    etiqueta = models.CharField(max_length=100)
    ordre = models.PositiveIntegerField(default=0)
    actiu = models.BooleanField(default=True)

    class Meta:
        ordering = ['ambit', 'ordre', 'etiqueta']
        constraints = [
            models.UniqueConstraint(fields=['ambit', 'codi'], name='agenda_unique_segment_scope_code'),
        ]
        verbose_name = 'segment de visibilitat'
        verbose_name_plural = 'segments de visibilitat'

    def __str__(self):
        return f'{self.get_ambit_display()} · {self.etiqueta}'


class Acte(TimeStampedModel):
    class Estat(models.TextChoices):
        ESBORRANY = 'ESBORRANY', 'Esborrany'
        PUBLICAT = 'PUBLICAT', 'Publicat'

    titol = models.CharField(max_length=255)
    imatge = models.ImageField(upload_to='material/agenda/', blank=True)
    descripcio = models.TextField(blank=True)
    tipus = models.ForeignKey(
        ActeTipus,
        on_delete=models.SET_NULL,
        related_name='actes',
        null=True,
        blank=True,
    )
    inici = models.DateTimeField()
    fi = models.DateTimeField(null=True, blank=True)
    ubicacio = models.CharField(max_length=255)
    aforament = models.PositiveIntegerField(null=True, blank=True)
    punt_trobada = models.CharField(max_length=255, blank=True)
    estat = models.CharField(max_length=20, choices=Estat.choices, default=Estat.ESBORRANY)
    es_important = models.BooleanField(default=False, help_text='Destaca l’acte a la llista i als resums clau.')
    creador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='actes_creats',
    )
    visible_per = models.ManyToManyField(
        SegmentVisibilitat,
        blank=True,
        related_name='actes_visibles',
    )
    assistencia_permesa_per = models.ManyToManyField(
        SegmentVisibilitat,
        blank=True,
        related_name='actes_assistencia',
    )

    persones_relacionades = models.ManyToManyField(
        'persones.Persona',
        blank=True,
        related_name='actes_relacionats',
    )
    entitats_relacionades = models.ManyToManyField(
        Entitat,
        blank=True,
        related_name='actes_relacionats',
    )

    external_source = models.CharField(max_length=50, blank=True)
    external_id = models.CharField(max_length=255, blank=True)
    source_url = models.URLField(blank=True)
    source_checksum = models.CharField(max_length=64, blank=True)
    source_payload = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['inici']
        constraints = [
            models.UniqueConstraint(
                fields=['external_source', 'external_id'],
                condition=Q(external_source__gt='') & Q(external_id__gt=''),
                name='agenda_unique_external_source_id',
            ),
        ]
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
