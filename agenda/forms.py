from datetime import timedelta

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from usuaris.forms import StyledFormMixin

from .models import Acte, ParticipacioActe


class ActeForm(StyledFormMixin, forms.ModelForm):
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
            'visible_per',
            'assistencia_permesa_per',
            'estat',
        ]
        widgets = {
            'inici': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'fi': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'descripcio': forms.Textarea(attrs={'rows': 4}),
            'visible_per': forms.SelectMultiple(attrs={'class': 'form-select', 'size': 6}),
            'assistencia_permesa_per': forms.SelectMultiple(attrs={'class': 'form-select', 'size': 6}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tipus'].queryset = self.fields['tipus'].queryset.filter(actiu=True)
        self.fields['visible_per'].queryset = self.fields['visible_per'].queryset.filter(actiu=True)
        self.fields['assistencia_permesa_per'].queryset = self.fields['assistencia_permesa_per'].queryset.filter(actiu=True)
        self.fields['visible_per'].help_text = 'Deixa-ho buit perquè l’acte sigui visible per a tothom amb accés a l’agenda.'
        self.fields['assistencia_permesa_per'].help_text = 'Deixa-ho buit perquè qualsevol usuari que el vegi pugui confirmar assistència.'

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
        return cleaned_data


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
