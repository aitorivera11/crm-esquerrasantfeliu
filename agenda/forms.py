from datetime import timedelta

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.formats import localize_input

from core.forms import SearchableSelectMultiple
from entitats.models import Entitat
from persones.models import Persona
from usuaris.forms import StyledFormMixin

from .models import Acte, ParticipacioActe, SegmentVisibilitat
from usuaris.models import Usuari


class ActeForm(StyledFormMixin, forms.ModelForm):
    datetime_input_formats = [
        '%Y-%m-%dT%H:%M',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%d %H:%M',
        '%d/%m/%Y %H:%M',
    ]

    class Meta:
        model = Acte
        fields = [
            'titol',
            'tipus',
            'descripcio',
            'inici',
            'fi',
            'ubicacio',
            'punt_trobada',
            'aforament',
            'entitats_relacionades',
            'persones_relacionades',
            'visible_per',
            'estat',
            'es_important',
        ]
        widgets = {
            'inici': forms.DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={'type': 'datetime-local'}),
            'fi': forms.DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={'type': 'datetime-local'}),
            'descripcio': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Context, objectiu, material necessari…'}),
            'visible_per': SearchableSelectMultiple(search_placeholder='Cerca públics…', empty_text='No hi ha segments disponibles.'),
            'entitats_relacionades': SearchableSelectMultiple(search_placeholder='Cerca entitats…', empty_text='No hi ha entitats disponibles.'),
            'persones_relacionades': SearchableSelectMultiple(search_placeholder='Cerca persones…', empty_text='No hi ha persones disponibles.'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tipus'].queryset = self.fields['tipus'].queryset.filter(actiu=True)
        segment_queryset = SegmentVisibilitat.objects.filter(actiu=True).exclude(
            ambit=SegmentVisibilitat.Ambit.ROL,
            codi=Usuari.Rol.ADMINISTRACIO,
        ).order_by('ambit', 'ordre', 'etiqueta')
        self.fields['visible_per'].queryset = segment_queryset
        self.fields['entitats_relacionades'].queryset = Entitat.objects.order_by('nom')
        self.fields['persones_relacionades'].queryset = Persona.objects.order_by('nom')
        self.fields['visible_per'].help_text = (
            'Deixa-ho buit perquè l’acte sigui visible i assistible per a tothom. '
            'Si selecciones Coordinació, només serà per a coordinació. '
            'Si selecciones Participant o algun tipus, coordinació també hi tindrà accés automàticament.'
        )
        self.fields['entitats_relacionades'].help_text = 'Entitats o associacions implicades en aquest acte.'
        self.fields['persones_relacionades'].help_text = 'Persones registrades que participen o fan seguiment de l’acte.'
        self.fields['visible_per'].label = 'Qui el pot veure i assistir'
        self.fields['entitats_relacionades'].label = 'Entitats relacionades'
        self.fields['persones_relacionades'].label = 'Persones relacionades'
        self.fields['es_important'].label = 'Acte important'
        self.fields['es_important'].help_text = 'Es mostrarà més destacat als llistats i resums per facilitar-ne el seguiment.'
        self.fields['inici'].input_formats = self.datetime_input_formats
        self.fields['fi'].input_formats = self.datetime_input_formats

        for field_name in ('inici', 'fi'):
            field = self.fields[field_name]
            value = self.initial.get(field_name)
            if value:
                field.initial = localize_input(value, field.widget.format or '%Y-%m-%dT%H:%M')

    def clean_inici(self):
        inici = self.cleaned_data['inici']
        if inici < timezone.now() - timedelta(days=365):
            raise ValidationError("La data de l'acte és massa antiga per a una agenda activa.")
        return inici

    def clean(self):
        cleaned_data = super().clean()
        inici = cleaned_data.get('inici')
        fi = cleaned_data.get('fi')
        if inici and fi and fi <= inici:
            self.add_error('fi', "La data/hora de final ha de ser posterior a l'inici.")

        selected_segments = list(cleaned_data.get('visible_per') or [])
        if not selected_segments:
            return cleaned_data

        role_segments = [segment for segment in selected_segments if segment.ambit == SegmentVisibilitat.Ambit.ROL]
        type_segments = [segment for segment in selected_segments if segment.ambit == SegmentVisibilitat.Ambit.TIPUS]

        if any(segment.codi == Usuari.Rol.ADMINISTRACIO for segment in role_segments):
            self.add_error('visible_per', 'Administració no es pot seleccionar com a públic específic d’un acte.')
            return cleaned_data

        coordinator_segment = next((segment for segment in role_segments if segment.codi == Usuari.Rol.COORDINACIO), None)
        participant_segment = next((segment for segment in role_segments if segment.codi == Usuari.Rol.PARTICIPANT), None)

        if coordinator_segment and not participant_segment and not type_segments:
            cleaned_data['visible_per'] = [coordinator_segment]
            return cleaned_data

        normalized_segments = []
        if participant_segment or type_segments:
            if coordinator_segment is None:
                coordinator_segment = SegmentVisibilitat.objects.filter(
                    ambit=SegmentVisibilitat.Ambit.ROL,
                    codi=Usuari.Rol.COORDINACIO,
                    actiu=True,
                ).first()
            if participant_segment is None:
                participant_segment = SegmentVisibilitat.objects.filter(
                    ambit=SegmentVisibilitat.Ambit.ROL,
                    codi=Usuari.Rol.PARTICIPANT,
                    actiu=True,
                ).first()
            if coordinator_segment:
                normalized_segments.append(coordinator_segment)
            if participant_segment:
                normalized_segments.append(participant_segment)
            normalized_segments.extend(type_segments)
            cleaned_data['visible_per'] = normalized_segments
            return cleaned_data

        cleaned_data['visible_per'] = []
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=commit)
        if commit:
            instance.assistencia_permesa_per.set(instance.visible_per.all())
        return instance

    def save_m2m(self):
        super().save_m2m()
        self.instance.assistencia_permesa_per.set(self.instance.visible_per.all())


class ParticipacioForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = ParticipacioActe
        fields = ['intencio', 'observacions']
        widgets = {
            'observacions': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Comentari opcional…'}),
        }

    def __init__(self, *args, usuari=None, acte=None, **kwargs):
        self.usuari = usuari
        self.acte = acte
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        if self.usuari and self.acte:
            qs = ParticipacioActe.objects.filter(usuari=self.usuari, acte=self.acte)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError('Aquest usuari ja té una participació registrada per a aquest acte.')
        return cleaned_data
