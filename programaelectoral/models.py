from django.db import models

from core.models import TimeStampedModel
from entitats.models import Entitat
from persones.models import Persona
from reunions.models import Reunio
from usuaris.models import Usuari


class BlocPrograma(TimeStampedModel):
    class Estat(models.TextChoices):
        PENDENT = 'PENDENT', 'Pendent'
        EN_REVISIO = 'EN_REVISIO', 'En revisió'
        DEFINITIU = 'DEFINITIU', 'Definitiu'
        A_FER = 'A_FER', 'Cal fer alguna cosa'

    titol = models.CharField(max_length=200)
    descripcio = models.TextField(blank=True, default='')
    ordre = models.PositiveSmallIntegerField(default=0)
    pare = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subblocs',
    )
    estat = models.CharField(max_length=20, choices=Estat.choices, default=Estat.PENDENT)
    creat_per = models.ForeignKey(
        Usuari,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='blocs_programa_creats',
    )

    class Meta:
        verbose_name = 'bloc del programa'
        verbose_name_plural = 'blocs del programa'
        ordering = ('ordre', 'titol')
        permissions = [('manage_programa_electoral', 'Pot gestionar el programa electoral')]

    def __str__(self):
        return self.titol

    @property
    def es_subbloc(self):
        return self.pare_id is not None


class Proposta(TimeStampedModel):
    class Estat(models.TextChoices):
        ESBORRANY = 'ESBORRANY', 'Esborrany'
        A_REVISAR = 'A_REVISAR', 'Cal revisar'
        CONFIRMADA = 'CONFIRMADA', 'Confirmada'
        DEFINITIVA = 'DEFINITIVA', 'Definitiva'
        DESCARTADA = 'DESCARTADA', 'Descartada'

    titol = models.CharField(max_length=300)
    contingut = models.TextField(blank=True, default='')
    bloc = models.ForeignKey(
        BlocPrograma,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='propostes',
    )
    estat = models.CharField(max_length=20, choices=Estat.choices, default=Estat.ESBORRANY)
    creat_per = models.ForeignKey(
        Usuari,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='propostes_creades',
    )

    class Meta:
        verbose_name = 'proposta'
        verbose_name_plural = 'propostes'
        ordering = ('bloc__ordre', 'bloc__titol', 'titol')

    def __str__(self):
        return self.titol


class ComentariProposta(TimeStampedModel):
    proposta = models.ForeignKey(Proposta, on_delete=models.CASCADE, related_name='comentaris')
    autor = models.ForeignKey(
        Usuari,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='comentaris_proposta',
    )
    text = models.TextField()

    class Meta:
        verbose_name = 'comentari de proposta'
        verbose_name_plural = 'comentaris de proposta'
        ordering = ('creat_el',)

    def __str__(self):
        return f'Comentari de {self.autor} a "{self.proposta}"'


class IdeaPluja(TimeStampedModel):
    class Font(models.TextChoices):
        ENTITAT = 'ENTITAT', 'Reunió amb entitat'
        PERSONA_EXTERNA = 'PERSONA_EXTERNA', 'Contacte amb persona'
        REUNIO_INTERNA = 'REUNIO_INTERNA', 'Reunió interna del partit'
        FORMULARI_PUBLIC = 'FORMULARI_PUBLIC', 'Formulari públic'
        XARXES = 'XARXES', 'Xarxes socials'
        ALTRA = 'ALTRA', 'Altra font'

    titol = models.CharField(max_length=300)
    descripcio = models.TextField(blank=True, default='')
    font = models.CharField(max_length=20, choices=Font.choices, default=Font.ALTRA)
    font_reunio = models.ForeignKey(
        Reunio,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='idees_pluja',
    )
    font_entitat = models.ForeignKey(
        Entitat,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='idees_pluja',
    )
    font_persona = models.ForeignKey(
        Persona,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='idees_pluja',
    )
    proposta_associada = models.ForeignKey(
        Proposta,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='idees_origen',
    )
    creat_per = models.ForeignKey(
        Usuari,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='idees_pluja_creades',
    )

    class Meta:
        verbose_name = "idea de la pluja d'idees"
        verbose_name_plural = "idees de la pluja d'idees"
        ordering = ('-creat_el',)

    def __str__(self):
        return self.titol


class IdeaPublica(TimeStampedModel):
    idea = models.TextField()
    nom = models.CharField(max_length=200, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    telefon = models.CharField(max_length=30, blank=True, default='')
    persona_identificada = models.ForeignKey(
        Persona,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='idees_publiques',
    )
    processada = models.BooleanField(default=False)
    idea_pluja_resultant = models.ForeignKey(
        IdeaPluja,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='origen_public',
    )

    class Meta:
        verbose_name = 'idea pública'
        verbose_name_plural = 'idees públiques'
        ordering = ('-creat_el',)

    def __str__(self):
        nom = self.nom or '(anònim)'
        return f'Idea de {nom}: {self.idea[:60]}'
