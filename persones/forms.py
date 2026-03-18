from django import forms

from usuaris.forms import StyledFormMixin

from .models import Persona


class PersonaForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Persona
        fields = ['nom', 'email', 'telefon', 'notes']
        widgets = {'notes': forms.Textarea(attrs={'rows': 4})}
