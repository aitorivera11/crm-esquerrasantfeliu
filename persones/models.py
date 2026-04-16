from django.db import models
from django.urls import reverse

from core.models import TimeStampedModel


class Persona(TimeStampedModel):
    nom = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    telefon = models.CharField(max_length=20, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = 'persona'
        verbose_name_plural = 'persones'
        ordering = ['nom']

    def __str__(self):
        return self.nom

    def get_absolute_url(self):
        return reverse('persones:persona_detail', kwargs={'pk': self.pk})
