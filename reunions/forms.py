from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max
from django.utils.formats import localize_input

from agenda.models import Acte, ActeTipus, SegmentVisibilitat
from core.forms import SearchableSelectMultiple
from entitats.models import Entitat
from persones.models import Persona
from usuaris.forms import StyledFormMixin
from usuaris.models import Usuari

from .models import Acta, AreaCampanya, PuntActa, PuntOrdreDia, Reunio, SeguimentTasca, Tasca, TascaRelacioReunio


class ReunioForm(StyledFormMixin, forms.ModelForm):
    datetime_input_formats = [
        '%Y-%m-%dT%H:%M',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%d %H:%M',
        '%d/%m/%Y %H:%M',
    ]

    class Meta:
        model = Reunio
        fields = [
            'titol', 'tipus', 'estat', 'inici', 'fi', 'ubicacio', 'descripcio', 'objectiu',
            'area', 'convocada_per', 'moderada_per', 'assistents', 'persones_relacionades',
            'entitats_relacionades', 'etiquetes', 'es_estrategica', 'es_interna', 'acte_agenda',
        ]
        widgets = {
            'inici': forms.DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={'type': 'datetime-local'}),
            'fi': forms.DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={'type': 'datetime-local'}),
            'descripcio': forms.Textarea(attrs={'rows': 4}),
            'objectiu': forms.Textarea(attrs={'rows': 3}),
            'assistents': SearchableSelectMultiple(search_placeholder='Cerca assistents…'),
            'persones_relacionades': SearchableSelectMultiple(search_placeholder='Cerca persones…'),
            'entitats_relacionades': SearchableSelectMultiple(search_placeholder='Cerca entitats…'),
            'etiquetes': SearchableSelectMultiple(search_placeholder='Cerca etiquetes…'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['convocada_per'].queryset = Usuari.objects.order_by('nom_complet', 'username')
        self.fields['moderada_per'].queryset = Usuari.objects.order_by('nom_complet', 'username')
        self.fields['assistents'].queryset = Usuari.objects.order_by('nom_complet', 'username')
        self.fields['persones_relacionades'].queryset = Persona.objects.order_by('nom')
        self.fields['entitats_relacionades'].queryset = Entitat.objects.order_by('nom')
        self.fields['area'].queryset = AreaCampanya.objects.filter(activa=True).order_by('ordre', 'nom')
        self.fields['acte_agenda'].queryset = Acte.objects.filter(external_source='').order_by('-inici', 'titol')
        self.fields['acte_agenda'].required = False
        self.fields['acte_agenda'].label = 'Acte vinculat a l’agenda'
        self.fields['acte_agenda'].help_text = 'Si el deixes buit, es crearà o s’actualitzarà automàticament un acte de l’agenda per aquesta reunió.'
        self.fields['inici'].input_formats = self.datetime_input_formats
        self.fields['fi'].input_formats = self.datetime_input_formats

        for field_name in ('inici', 'fi'):
            field = self.fields[field_name]
            value = self.initial.get(field_name)
            if value:
                field.initial = localize_input(value, field.widget.format or '%Y-%m-%dT%H:%M')

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
            self.save_m2m()
            self.sync_acte_agenda(instance)
        return instance

    def save_m2m(self):
        super().save_m2m()
        if self.instance.pk:
            self.sync_acte_agenda(self.instance)

    def sync_acte_agenda(self, reunio):
        acte = reunio.acte_agenda
        creating = acte is None
        if creating:
            acte = Acte(creador=reunio.convocada_per)

        tipus_nom = reunio.get_tipus_display()
        acte_tipus, _ = ActeTipus.objects.get_or_create(nom=tipus_nom, defaults={'ordre': 0, 'actiu': True})
        acte.titol = reunio.titol
        acte.tipus = acte_tipus
        acte.descripcio = reunio.descripcio or reunio.objectiu
        acte.inici = reunio.inici
        acte.fi = reunio.fi
        acte.ubicacio = reunio.ubicacio
        acte.estat = Acte.Estat.PUBLICAT if reunio.estat in {Reunio.Estat.CONVOCADA, Reunio.Estat.CELEBRADA, Reunio.Estat.TANCADA} else Acte.Estat.ESBORRANY
        acte.es_important = reunio.es_estrategica
        if not acte.creador_id:
            acte.creador = reunio.convocada_per
        acte.save()

        if creating or reunio.acte_agenda_id != acte.pk:
            reunio.acte_agenda = acte
            reunio.save(update_fields=['acte_agenda', 'actualitzat_el'])

        acte.persones_relacionades.set(reunio.persones_relacionades.all())
        acte.entitats_relacionades.set(reunio.entitats_relacionades.all())

        visibility_segments = []
        if reunio.es_interna:
            coordinacio_segment, _ = SegmentVisibilitat.objects.get_or_create(
                ambit=SegmentVisibilitat.Ambit.ROL,
                codi=Usuari.Rol.COORDINACIO,
                defaults={'etiqueta': 'Coordinació'},
            )
            visibility_segments = [coordinacio_segment]
        acte.visible_per.set(visibility_segments)
        acte.assistencia_permesa_per.set(visibility_segments)

        confirmats_ids = reunio.acte_agenda.participants.filter(intencio='HI_ANIRE').values_list('usuari_id', flat=True) if reunio.acte_agenda_id else []
        reunio.assistents.add(*list(confirmats_ids))


class PuntOrdreDiaForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = PuntOrdreDia
        fields = ['ordre', 'titol', 'descripcio', 'responsable', 'durada_estimada', 'requereix_acord', 'estat']
        widgets = {'descripcio': forms.Textarea(attrs={'rows': 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['ordre'].required = False
        self.fields['responsable'].queryset = Usuari.objects.order_by('nom_complet', 'username')


class ActaForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Acta
        fields = [
            'resum_general',
            'acords_presos',
            'observacions',
            'resultat_post_acte',
            'incidencies_post_acte',
            'tasques_derivades_post_acte',
            'data_tancament',
            'redactada_per',
            'estat',
        ]
        widgets = {
            'resum_general': forms.Textarea(attrs={'rows': 5}),
            'acords_presos': forms.Textarea(attrs={'rows': 4}),
            'observacions': forms.Textarea(attrs={'rows': 4}),
            'resultat_post_acte': forms.Textarea(attrs={'rows': 3}),
            'incidencies_post_acte': forms.Textarea(attrs={'rows': 3}),
            'tasques_derivades_post_acte': forms.Textarea(attrs={'rows': 3}),
            'data_tancament': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
        }

    def __init__(self, *args, reunio=None, **kwargs):
        self.reunio = reunio
        super().__init__(*args, **kwargs)
        self.fields['redactada_per'].queryset = Usuari.objects.order_by('nom_complet', 'username')
        self.fields['data_tancament'].input_formats = ['%Y-%m-%d', '%d/%m/%Y']
        value = self.initial.get('data_tancament')
        if value:
            self.fields['data_tancament'].initial = localize_input(
                value,
                self.fields['data_tancament'].widget.format or '%Y-%m-%d',
            )


class PuntActaForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = PuntActa
        fields = ['ordre', 'titol', 'contingut', 'acords', 've_de_ordre_dia', 'punt_ordre_origen']
        widgets = {
            'contingut': forms.Textarea(attrs={'rows': 4}),
            'acords': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, reunio=None, **kwargs):
        self.reunio = reunio
        super().__init__(*args, **kwargs)
        if self.reunio:
            self.fields['punt_ordre_origen'].queryset = self.reunio.punts_ordre_dia.order_by('ordre')


class TascaForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Tasca
        fields = [
            'titol', 'descripcio', 'estat', 'prioritat', 'data_limit', 'creada_per', 'responsable',
            'collaboradors', 'area', 'observacions_seguiment', 'resultat_tancament',
            'proposar_seguent_ordre_dia', 'motiu_proposta_ordre_dia', 'origen', 'reunio_origen',
            'punt_acta_origen', 'es_estrategica', 'visibilitat', 'persones_relacionades',
            'entitats_relacionades', 'etiquetes',
        ]
        widgets = {
            'descripcio': forms.Textarea(attrs={'rows': 4}),
            'observacions_seguiment': forms.Textarea(attrs={'rows': 3}),
            'resultat_tancament': forms.Textarea(attrs={'rows': 3}),
            'motiu_proposta_ordre_dia': forms.Textarea(attrs={'rows': 3}),
            'data_limit': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
            'collaboradors': SearchableSelectMultiple(search_placeholder='Cerca persones col·laboradores…'),
            'persones_relacionades': SearchableSelectMultiple(search_placeholder='Cerca persones…'),
            'entitats_relacionades': SearchableSelectMultiple(search_placeholder='Cerca entitats…'),
            'etiquetes': SearchableSelectMultiple(search_placeholder='Cerca etiquetes…'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        ordered_users = Usuari.objects.order_by('nom_complet', 'username')
        self.fields['creada_per'].queryset = ordered_users
        self.fields['responsable'].queryset = ordered_users
        self.fields['collaboradors'].queryset = ordered_users
        self.fields['area'].queryset = AreaCampanya.objects.filter(activa=True).order_by('ordre', 'nom')
        self.fields['reunio_origen'].queryset = Reunio.objects.order_by('-inici')
        self.fields['punt_acta_origen'].queryset = PuntActa.objects.select_related('acta__reunio').order_by('-acta__reunio__inici', 'ordre')
        self.fields['persones_relacionades'].queryset = Persona.objects.order_by('nom')
        self.fields['entitats_relacionades'].queryset = Entitat.objects.order_by('nom')
        self.fields['data_limit'].input_formats = ['%Y-%m-%d', '%d/%m/%Y']
        value = self.initial.get('data_limit')
        if value:
            self.fields['data_limit'].initial = localize_input(
                value,
                self.fields['data_limit'].widget.format or '%Y-%m-%d',
            )

    def clean(self):
        cleaned_data = super().clean()
        origen = cleaned_data.get('origen')
        reunio_origen = cleaned_data.get('reunio_origen')
        punt_acta_origen = cleaned_data.get('punt_acta_origen')
        if origen == Tasca.Origen.PUNT_ACTA and punt_acta_origen and not reunio_origen:
            cleaned_data['reunio_origen'] = punt_acta_origen.acta.reunio
        if origen == Tasca.Origen.INDEPENDENT:
            cleaned_data['reunio_origen'] = None
            cleaned_data['punt_acta_origen'] = None
        return cleaned_data


class SeguimentTascaForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = SeguimentTasca
        fields = ['tipus', 'comentari', 'nou_estat', 'reunio']
        widgets = {'comentari': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Seguiment, acord o bloqueig…'})}

    def __init__(self, *args, tasca=None, autor=None, **kwargs):
        self.tasca = tasca
        self.autor = autor
        super().__init__(*args, **kwargs)
        self.fields['reunio'].queryset = Reunio.objects.order_by('-inici')
        self.fields['nou_estat'].required = False

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.tasca:
            instance.tasca = self.tasca
        if self.autor:
            instance.autor = self.autor
        if commit:
            instance.save()
        return instance


class TascaRelacioReunioForm(StyledFormMixin, forms.ModelForm):
    datetime_input_formats = [
        '%Y-%m-%dT%H:%M',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%d %H:%M',
        '%d/%m/%Y %H:%M',
    ]

    class Meta:
        model = TascaRelacioReunio
        fields = ['reunio', 'punt_ordre_dia', 'punt_acta', 'tipus_relacio', 'resum', 'tractada_el']
        widgets = {
            'resum': forms.Textarea(attrs={'rows': 3}),
            'tractada_el': forms.DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={'type': 'datetime-local'}),
        }

    def __init__(self, *args, tasca=None, **kwargs):
        self.tasca = tasca
        super().__init__(*args, **kwargs)
        self.fields['reunio'].queryset = Reunio.objects.order_by('-inici')
        self.fields['tractada_el'].input_formats = self.datetime_input_formats
        value = self.initial.get('tractada_el')
        if value:
            self.fields['tractada_el'].initial = localize_input(
                value,
                self.fields['tractada_el'].widget.format or '%Y-%m-%dT%H:%M',
            )

    def clean(self):
        cleaned_data = super().clean()
        reunio = cleaned_data.get('reunio')
        punt_ordre = cleaned_data.get('punt_ordre_dia')
        punt_acta = cleaned_data.get('punt_acta')
        errors = {}
        if punt_ordre and reunio and punt_ordre.reunio_id != reunio.pk:
            errors['punt_ordre_dia'] = 'Aquest punt no pertany a la reunió seleccionada.'
        if punt_acta and reunio and punt_acta.acta.reunio_id != reunio.pk:
            errors['punt_acta'] = 'Aquest punt d’acta no pertany a la reunió seleccionada.'
        if errors:
            raise ValidationError(errors)
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.tasca:
            instance.tasca = self.tasca
        if commit:
            instance.save()
        return instance


class TascaRapidaReunioForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Tasca
        fields = ['titol', 'responsable', 'data_limit', 'prioritat']
        widgets = {
            'data_limit': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
        }

    def __init__(self, *args, usuari=None, **kwargs):
        self.usuari = usuari
        super().__init__(*args, **kwargs)
        ordered_users = Usuari.objects.order_by('nom_complet', 'username')
        self.fields['responsable'].queryset = ordered_users
        self.fields['responsable'].required = False
        self.fields['data_limit'].input_formats = ['%Y-%m-%d', '%d/%m/%Y']
        value = self.initial.get('data_limit')
        if value:
            self.fields['data_limit'].initial = localize_input(
                value,
                self.fields['data_limit'].widget.format or '%Y-%m-%d',
            )


class ReunioRapidaForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Reunio
        fields = ['titol', 'tipus', 'inici', 'fi', 'ubicacio', 'convocada_per', 'moderada_per']
        widgets = {
            'inici': forms.DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={'type': 'datetime-local'}),
            'fi': forms.DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        ordered_users = Usuari.objects.order_by('nom_complet', 'username')
        self.fields['convocada_per'].queryset = ordered_users
        self.fields['moderada_per'].queryset = ordered_users
        self.fields['fi'].required = False
        self.fields['inici'].input_formats = ReunioForm.datetime_input_formats
        self.fields['fi'].input_formats = ReunioForm.datetime_input_formats


class TascaRapidaForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Tasca
        fields = ['titol', 'estat', 'prioritat', 'data_limit', 'responsable', 'creada_per']
        widgets = {'data_limit': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        ordered_users = Usuari.objects.order_by('nom_complet', 'username')
        self.fields['responsable'].queryset = ordered_users
        self.fields['creada_per'].queryset = ordered_users
        self.fields['data_limit'].input_formats = ['%Y-%m-%d', '%d/%m/%Y']


def inicialitzar_punts_acta_des_de_ordre_dia(acta):
    return sincronitzar_punts_acta_amb_ordre_dia(acta, nomes_si_buit=True)


def sincronitzar_punts_acta_amb_ordre_dia(acta, *, nomes_si_buit=False):
    if nomes_si_buit and acta.punts.exists():
        return 0

    creats = 0
    ordre_maxim = acta.punts.aggregate(max_ordre=Max('ordre'))['max_ordre'] or 0
    punts_existents = set(
        acta.punts.filter(ve_de_ordre_dia=True, punt_ordre_origen__isnull=False).values_list('punt_ordre_origen_id', flat=True)
    )

    for punt in acta.reunio.punts_ordre_dia.order_by('ordre', 'pk'):
        if punt.pk in punts_existents:
            continue
        ordre_maxim += 1
        PuntActa.objects.create(
            acta=acta,
            ordre=ordre_maxim,
            titol=punt.titol,
            ve_de_ordre_dia=True,
            punt_ordre_origen=punt,
            acords='',
            contingut=punt.descripcio,
        )
        creats += 1

    return creats


@transaction.atomic
def reordenar_punts_ordre_dia(reunio, punt_ids):
    punts = {punt.pk: punt for punt in reunio.punts_ordre_dia.all()}
    for index, punt_id in enumerate(punt_ids, start=1):
        punt = punts.get(punt_id)
        if punt and punt.ordre != index:
            punt.ordre = index
            punt.save(update_fields=['ordre'])


@transaction.atomic
def reordenar_punts_acta(acta, punt_ids):
    punts = {punt.pk: punt for punt in acta.punts.all()}
    for index, punt_id in enumerate(punt_ids, start=1):
        punt = punts.get(punt_id)
        if punt and punt.ordre != index:
            punt.ordre = index
            punt.save(update_fields=['ordre'])
