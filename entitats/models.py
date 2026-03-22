from django.db import models
from django.db.models import Q

from core.models import TimeStampedModel


class Entitat(TimeStampedModel):
    nom = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    telefon = models.CharField(max_length=50, blank=True)
    web = models.URLField(blank=True)
    tipologia = models.CharField(max_length=255, blank=True)
    ambit = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    persones = models.ManyToManyField('persones.Persona', blank=True, related_name='entitats')
    external_source = models.CharField(max_length=50, blank=True)
    external_id = models.CharField(max_length=255, blank=True)
    source_url = models.URLField(blank=True)
    source_checksum = models.CharField(max_length=64, blank=True)
    source_payload = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['nom']
        verbose_name = 'entitat'
        verbose_name_plural = 'entitats'
        constraints = [
            models.UniqueConstraint(
                fields=['external_source', 'external_id'],
                condition=Q(external_source__gt='') & Q(external_id__gt=''),
                name='entitats_unique_external_source_id',
            ),
        ]

    def __str__(self):
        return self.nom
