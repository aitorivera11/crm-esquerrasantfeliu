from django import forms

from entitats.models import Entitat
from usuaris.forms import StyledFormMixin

from .models import Persona


class PersonaForm(StyledFormMixin, forms.ModelForm):
    entitats = forms.ModelMultipleChoiceField(
        queryset=Entitat.objects.order_by('nom'),
        required=False,
        widget=forms.CheckboxSelectMultiple(),
        help_text='Selecciona les entitats amb què es relaciona aquesta persona.',
    )

    class Meta:
        model = Persona
        fields = ['nom', 'email', 'telefon', 'entitats', 'notes']
        widgets = {'notes': forms.Textarea(attrs={'rows': 4})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['entitats'].initial = self.instance.entitats.all()

    def save(self, commit=True):
        persona = super().save(commit=commit)
        def save_m2m():
            persona.entitats.set(self.cleaned_data['entitats'])
        if commit:
            save_m2m()
        else:
            self.save_m2m = save_m2m
        return persona
