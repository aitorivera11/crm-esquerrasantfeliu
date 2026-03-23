from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from core.models import TimeStampedModel


class EtiquetaReunioTasques(TimeStampedModel):
    nom = models.CharField(max_length=80, unique=True)
    color = models.CharField(max_length=7, blank=True, help_text='Color HEX opcional per destacar l’etiqueta.')
    ordre = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['ordre', 'nom']
        verbose_name = 'etiqueta de reunions i tasques'
        verbose_name_plural = 'etiquetes de reunions i tasques'

    def __str__(self):
        return self.nom


class AreaCampanya(TimeStampedModel):
    nom = models.CharField(max_length=120, unique=True)
    descripcio = models.TextField(blank=True)
    ordre = models.PositiveIntegerField(default=0)
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ['ordre', 'nom']
        verbose_name = 'àrea de campanya'
        verbose_name_plural = 'àrees de campanya'

    def __str__(self):
        return self.nom


class Reunio(TimeStampedModel):
    class Tipus(models.TextChoices):
        INTERNA = 'INTERNA', 'Reunió interna'
        ASSEMBLEA = 'ASSEMBLEA', 'Assemblea'

    class Estat(models.TextChoices):
        PREPARACIO = 'PREPARACIO', 'En preparació'
        CONVOCADA = 'CONVOCADA', 'Convocada'
        CELEBRADA = 'CELEBRADA', 'Celebrada'
        TANCADA = 'TANCADA', 'Tancada'
        CANCEL_LADA = 'CANCEL_LADA', 'Cancel·lada'

    titol = models.CharField(max_length=255)
    tipus = models.CharField(max_length=20, choices=Tipus.choices)
    estat = models.CharField(max_length=20, choices=Estat.choices, default=Estat.PREPARACIO)
    inici = models.DateTimeField()
    fi = models.DateTimeField(null=True, blank=True)
    ubicacio = models.CharField(max_length=255, blank=True)
    descripcio = models.TextField(blank=True)
    objectiu = models.TextField(blank=True)
    convocada_per = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='reunions_convocades',
    )
    moderada_per = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reunions_moderades',
    )
    area = models.ForeignKey(
        AreaCampanya,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reunions',
    )
    es_estrategica = models.BooleanField(default=False)
    es_interna = models.BooleanField(default=True, help_text='Control simple de visibilitat interna.')
    assistents = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='reunions_assistides',
    )
    persones_relacionades = models.ManyToManyField(
        'persones.Persona',
        blank=True,
        related_name='reunions_relacionades',
    )
    entitats_relacionades = models.ManyToManyField(
        'entitats.Entitat',
        blank=True,
        related_name='reunions_relacionades',
    )
    etiquetes = models.ManyToManyField(
        EtiquetaReunioTasques,
        blank=True,
        related_name='reunions',
    )

    class Meta:
        ordering = ['-inici', '-creat_el']
        verbose_name = 'reunió'
        verbose_name_plural = 'reunions'

    def __str__(self):
        return f'{self.titol} · {timezone.localtime(self.inici).strftime("%d/%m/%Y %H:%M")}'

    def clean(self):
        errors = {}
        if self.fi and self.inici and self.fi <= self.inici:
            errors['fi'] = 'La data de finalització ha de ser posterior a l’inici.'
        if self.estat == self.Estat.TANCADA and not hasattr(self, 'acta'):
            errors['estat'] = 'No pots tancar una reunió sense acta.'
        if errors:
            raise ValidationError(errors)

    def get_absolute_url(self):
        return reverse('reunions:reunio_detail', kwargs={'pk': self.pk})


class PuntOrdreDia(TimeStampedModel):
    class Estat(models.TextChoices):
        PENDENT = 'PENDENT', 'Pendent'
        TRACTAT = 'TRACTAT', 'Tractat'
        APLACAT = 'APLACAT', 'Aplaçat'
        NO_TRACTAT = 'NO_TRACTAT', 'No tractat'

    reunio = models.ForeignKey(Reunio, on_delete=models.CASCADE, related_name='punts_ordre_dia')
    ordre = models.PositiveIntegerField(default=1)
    titol = models.CharField(max_length=255)
    descripcio = models.TextField(blank=True)
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='punts_ordre_responsable',
    )
    durada_estimada = models.PositiveIntegerField(null=True, blank=True, help_text='Durada estimada en minuts.')
    requereix_acord = models.BooleanField(default=False)
    estat = models.CharField(max_length=20, choices=Estat.choices, default=Estat.PENDENT)

    class Meta:
        ordering = ['ordre', 'pk']
        verbose_name = "punt de l'ordre del dia"
        verbose_name_plural = "punts de l'ordre del dia"
        constraints = [
            models.UniqueConstraint(fields=['reunio', 'ordre'], name='reunions_unique_punt_ordre_per_reunio'),
        ]

    def __str__(self):
        return f'{self.reunio.titol} · Punt {self.ordre}: {self.titol}'


class Acta(TimeStampedModel):
    class Estat(models.TextChoices):
        ESBORRANY = 'ESBORRANY', 'Esborrany'
        VALIDADA = 'VALIDADA', 'Validada'

    reunio = models.OneToOneField(Reunio, on_delete=models.CASCADE, related_name='acta')
    resum_general = models.TextField(blank=True)
    acords_presos = models.TextField(blank=True)
    observacions = models.TextField(blank=True)
    data_tancament = models.DateField(null=True, blank=True)
    redactada_per = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='actes_redactades',
    )
    estat = models.CharField(max_length=20, choices=Estat.choices, default=Estat.ESBORRANY)

    class Meta:
        ordering = ['-reunio__inici']
        verbose_name = 'acta'
        verbose_name_plural = 'actes'

    def __str__(self):
        return f'Acta · {self.reunio.titol}'

    def clean(self):
        errors = {}
        if self.estat == self.Estat.VALIDADA and not self.data_tancament:
            errors['data_tancament'] = 'Una acta validada ha de tenir data de tancament.'
        if self.data_tancament and self.reunio_id and self.data_tancament < timezone.localdate(self.reunio.inici):
            errors['data_tancament'] = 'La data de tancament no pot ser anterior a la reunió.'
        if errors:
            raise ValidationError(errors)


class PuntActa(TimeStampedModel):
    acta = models.ForeignKey(Acta, on_delete=models.CASCADE, related_name='punts')
    ordre = models.PositiveIntegerField(default=1)
    titol = models.CharField(max_length=255)
    contingut = models.TextField(blank=True)
    acords = models.TextField(blank=True)
    ve_de_ordre_dia = models.BooleanField(default=False)
    punt_ordre_origen = models.ForeignKey(
        PuntOrdreDia,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='punts_acta_generats',
    )

    class Meta:
        ordering = ['ordre', 'pk']
        verbose_name = "punt d'acta"
        verbose_name_plural = "punts d'acta"
        constraints = [
            models.UniqueConstraint(fields=['acta', 'ordre'], name='reunions_unique_punt_acta_per_acta'),
        ]

    def __str__(self):
        return f'{self.acta.reunio.titol} · Acta punt {self.ordre}: {self.titol}'

    def clean(self):
        if self.ve_de_ordre_dia and not self.punt_ordre_origen:
            raise ValidationError({'punt_ordre_origen': 'Cal indicar el punt d’ordre del dia original.'})
        if self.punt_ordre_origen and self.acta_id and self.punt_ordre_origen.reunio_id != self.acta.reunio_id:
            raise ValidationError({'punt_ordre_origen': 'El punt original ha de pertànyer a la mateixa reunió.'})


class Tasca(TimeStampedModel):
    class Estat(models.TextChoices):
        PENDENT = 'PENDENT', 'Pendent'
        EN_CURS = 'EN_CURS', 'En curs'
        BLOQUEJADA = 'BLOQUEJADA', 'Bloquejada'
        COMPLETADA = 'COMPLETADA', 'Completada'
        CANCEL_LADA = 'CANCEL_LADA', 'Cancel·lada'

    class Prioritat(models.TextChoices):
        BAIXA = 'BAIXA', 'Baixa'
        MITJANA = 'MITJANA', 'Mitjana'
        ALTA = 'ALTA', 'Alta'
        URGENT = 'URGENT', 'Urgent'

    class Origen(models.TextChoices):
        PUNT_ACTA = 'PUNT_ACTA', 'Punt d’acta'
        REUNIO = 'REUNIO', 'Reunió'
        INDEPENDENT = 'INDEPENDENT', 'Independent'

    class Visibilitat(models.TextChoices):
        INTERNA = 'INTERNA', 'Interna'
        COORDINACIO = 'COORDINACIO', 'Només coordinació'

    titol = models.CharField(max_length=255)
    descripcio = models.TextField(blank=True)
    estat = models.CharField(max_length=20, choices=Estat.choices, default=Estat.PENDENT)
    prioritat = models.CharField(max_length=20, choices=Prioritat.choices, default=Prioritat.MITJANA)
    data_limit = models.DateField(null=True, blank=True)
    creada_per = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='tasques_creades',
    )
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='tasques_assignades',
    )
    collaboradors = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='tasques_collaboradors',
    )
    area = models.ForeignKey(AreaCampanya, on_delete=models.SET_NULL, null=True, blank=True, related_name='tasques')
    observacions_seguiment = models.TextField(blank=True)
    resultat_tancament = models.TextField(blank=True)
    proposar_seguent_ordre_dia = models.BooleanField(default=False)
    motiu_proposta_ordre_dia = models.TextField(blank=True)
    origen = models.CharField(max_length=20, choices=Origen.choices, default=Origen.INDEPENDENT)
    reunio_origen = models.ForeignKey(
        Reunio,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tasques_originades',
    )
    punt_acta_origen = models.ForeignKey(
        PuntActa,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tasques_generades',
    )
    es_estrategica = models.BooleanField(default=False)
    visibilitat = models.CharField(max_length=20, choices=Visibilitat.choices, default=Visibilitat.INTERNA)
    persones_relacionades = models.ManyToManyField('persones.Persona', blank=True, related_name='tasques_relacionades')
    entitats_relacionades = models.ManyToManyField('entitats.Entitat', blank=True, related_name='tasques_relacionades')
    etiquetes = models.ManyToManyField(EtiquetaReunioTasques, blank=True, related_name='tasques')

    class Meta:
        ordering = ['data_limit', '-es_estrategica', '-creat_el']
        verbose_name = 'tasca'
        verbose_name_plural = 'tasques'

    def __str__(self):
        return self.titol

    def clean(self):
        errors = {}
        if self.origen == self.Origen.PUNT_ACTA and not self.punt_acta_origen:
            errors['punt_acta_origen'] = 'Cal indicar el punt d’acta d’origen.'
        if self.origen == self.Origen.REUNIO and not self.reunio_origen:
            errors['reunio_origen'] = 'Cal indicar la reunió d’origen.'
        if self.punt_acta_origen and self.reunio_origen and self.punt_acta_origen.acta.reunio_id != self.reunio_origen_id:
            errors['reunio_origen'] = 'La reunió d’origen ha de coincidir amb la del punt d’acta.'
        if self.proposar_seguent_ordre_dia and not self.motiu_proposta_ordre_dia:
            errors['motiu_proposta_ordre_dia'] = 'Explica per què s’ha de portar al següent ordre del dia.'
        if self.estat == self.Estat.COMPLETADA and not self.resultat_tancament:
            errors['resultat_tancament'] = 'Cal informar del resultat o tancament quan la tasca es completa.'
        if errors:
            raise ValidationError(errors)

    @property
    def esta_vencuda(self):
        return bool(self.data_limit and self.estat not in {self.Estat.COMPLETADA, self.Estat.CANCEL_LADA} and self.data_limit < timezone.localdate())

    def get_absolute_url(self):
        return reverse('reunions:tasca_detail', kwargs={'pk': self.pk})


class TascaRelacioReunio(TimeStampedModel):
    class TipusRelacio(models.TextChoices):
        ORIGEN = 'ORIGEN', 'Origen'
        SEGUIMENT = 'SEGUIMENT', 'Seguiment'
        PROPOSTA_ORDRE_DIA = 'PROPOSTA_ORDRE_DIA', 'Proposta per ordre del dia'
        TANCAMENT = 'TANCAMENT', 'Tancament'

    tasca = models.ForeignKey(Tasca, on_delete=models.CASCADE, related_name='relacions_reunio')
    reunio = models.ForeignKey(Reunio, on_delete=models.CASCADE, related_name='relacions_tasca')
    punt_ordre_dia = models.ForeignKey(
        PuntOrdreDia,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='relacions_tasca',
    )
    punt_acta = models.ForeignKey(
        PuntActa,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='relacions_tasca',
    )
    tipus_relacio = models.CharField(max_length=20, choices=TipusRelacio.choices, default=TipusRelacio.SEGUIMENT)
    resum = models.TextField(blank=True)
    tractada_el = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-tractada_el', '-pk']
        verbose_name = 'relació entre tasca i reunió'
        verbose_name_plural = 'relacions entre tasques i reunions'
        constraints = [
            models.UniqueConstraint(
                fields=['tasca', 'reunio', 'punt_ordre_dia', 'punt_acta', 'tipus_relacio'],
                name='reunions_unique_tasca_reunio_link',
            ),
        ]

    def __str__(self):
        return f'{self.tasca} · {self.reunio} · {self.get_tipus_relacio_display()}'

    def clean(self):
        errors = {}
        if self.punt_ordre_dia and self.punt_ordre_dia.reunio_id != self.reunio_id:
            errors['punt_ordre_dia'] = 'El punt de l’ordre del dia ha de ser de la reunió indicada.'
        if self.punt_acta and self.punt_acta.acta.reunio_id != self.reunio_id:
            errors['punt_acta'] = 'El punt d’acta ha de ser de la reunió indicada.'
        if self.punt_acta and self.punt_ordre_dia and self.punt_acta.punt_ordre_origen_id and self.punt_acta.punt_ordre_origen_id != self.punt_ordre_dia_id:
            errors['punt_acta'] = 'El punt d’acta no correspon amb el punt de l’ordre del dia indicat.'
        if errors:
            raise ValidationError(errors)


class SeguimentTasca(TimeStampedModel):
    class Tipus(models.TextChoices):
        COMENTARI = 'COMENTARI', 'Comentari'
        BLOCATGE = 'BLOCATGE', 'Bloqueig'
        AVENC = 'AVENC', 'Avenç'
        DECISIO = 'DECISIO', 'Decisió'

    tasca = models.ForeignKey(Tasca, on_delete=models.CASCADE, related_name='seguiments')
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='seguiments_tasca')
    tipus = models.CharField(max_length=20, choices=Tipus.choices, default=Tipus.COMENTARI)
    comentari = models.TextField()
    nou_estat = models.CharField(max_length=20, choices=Tasca.Estat.choices, blank=True)
    reunio = models.ForeignKey(Reunio, on_delete=models.SET_NULL, null=True, blank=True, related_name='seguiments_tasca')

    class Meta:
        ordering = ['-creat_el']
        verbose_name = 'seguiment de tasca'
        verbose_name_plural = 'seguiments de tasques'

    def __str__(self):
        return f'{self.tasca} · {self.get_tipus_display()} · {self.creat_el:%d/%m/%Y}'


class HistoricEstatTasca(TimeStampedModel):
    tasca = models.ForeignKey(Tasca, on_delete=models.CASCADE, related_name='historic_estats')
    estat_anterior = models.CharField(max_length=20, choices=Tasca.Estat.choices, blank=True)
    estat_nou = models.CharField(max_length=20, choices=Tasca.Estat.choices)
    canviat_per = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='canvis_estat_tasca')
    motiu = models.TextField(blank=True)

    class Meta:
        ordering = ['-creat_el']
        verbose_name = 'històric d’estat de tasca'
        verbose_name_plural = 'històrics d’estat de tasca'

    def __str__(self):
        return f'{self.tasca} · {self.estat_anterior or "-"} → {self.estat_nou}'


from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver


@receiver(pre_save, sender=Tasca)
def preparar_canvi_estat_tasca(sender, instance, **kwargs):
    if instance.pk:
        instance._estat_anterior = sender.objects.filter(pk=instance.pk).values_list('estat', flat=True).first() or ''
    else:
        instance._estat_anterior = ''


@receiver(post_save, sender=Tasca)
def registrar_canvi_estat_tasca(sender, instance, created, **kwargs):
    if created:
        HistoricEstatTasca.objects.get_or_create(
            tasca=instance,
            estat_anterior='',
            estat_nou=instance.estat,
            canviat_per=instance.creada_per,
        )
        if instance.reunio_origen_id or instance.punt_acta_origen_id:
            TascaRelacioReunio.objects.get_or_create(
                tasca=instance,
                reunio=instance.reunio_origen or instance.punt_acta_origen.acta.reunio,
                punt_acta=instance.punt_acta_origen,
                punt_ordre_dia=instance.punt_acta_origen.punt_ordre_origen if instance.punt_acta_origen_id else None,
                tipus_relacio=TascaRelacioReunio.TipusRelacio.ORIGEN,
                defaults={'resum': 'Origen automàtic de la tasca a partir de la seva creació.'},
            )
        return

    previous = getattr(instance, '_estat_anterior', '')
    if previous and previous != instance.estat:
        HistoricEstatTasca.objects.create(tasca=instance, estat_anterior=previous, estat_nou=instance.estat)


@receiver(pre_save, sender=SeguimentTasca)
def aplicar_estat_des_de_seguiment(sender, instance, **kwargs):
    if instance.nou_estat and instance.tasca.estat != instance.nou_estat:
        HistoricEstatTasca.objects.create(
            tasca=instance.tasca,
            estat_anterior=instance.tasca.estat,
            estat_nou=instance.nou_estat,
            canviat_per=instance.autor,
            motiu=instance.comentari,
        )
        Tasca.objects.filter(pk=instance.tasca_id).update(estat=instance.nou_estat)
        instance.tasca.estat = instance.nou_estat
