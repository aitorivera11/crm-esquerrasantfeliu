from datetime import timedelta

from django import forms

from usuaris.forms import StyledFormMixin
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Acte, ParticipacioActe


class ActeForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Acte
        fields = ['titol', 'descripcio', 'inici', 'ubicacio', 'estat']
        widgets = {
            'inici': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'descripcio': forms.Textarea(attrs={'rows': 4}),
        }

    def clean_inici(self):
        inici = self.cleaned_data['inici']
        if inici < timezone.now() - timedelta(days=365):
            raise ValidationError('La data de l\'acte és massa antiga per a una agenda activa.')
        return inici


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
