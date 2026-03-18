from django.conf import settings
from django.db import models


class TimeStampedModel(models.Model):
    creat_el = models.DateTimeField(auto_now_add=True)
    actualitzat_el = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Auditoria(TimeStampedModel):
    class Accio(models.TextChoices):
        CREATE = 'CREATE', 'Creació'
        UPDATE = 'UPDATE', 'Actualització'
        DELETE = 'DELETE', 'Eliminació'
        STATUS = 'STATUS', 'Canvi d\'estat'

    usuari = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='auditories',
    )
    accio = models.CharField(max_length=20, choices=Accio.choices)
    model_afectat = models.CharField(max_length=100)
    object_id = models.CharField(max_length=50)
    dades = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-creat_el']
        verbose_name = 'auditoria'
        verbose_name_plural = 'auditories'

    def __str__(self):
        return f'{self.model_afectat} #{self.object_id} - {self.accio}'
