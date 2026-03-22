from django import forms

from persones.models import Persona
from usuaris.forms import StyledFormMixin

from .models import Entitat


class EntitatForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Entitat
        fields = ['nom', 'email', 'telefon', 'web', 'tipologia', 'ambit', 'persones', 'notes']
        widgets = {
            'persones': forms.CheckboxSelectMultiple(),
            'notes': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['persones'].queryset = Persona.objects.order_by('nom')
        self.fields['persones'].help_text = 'Relaciona les persones registrades que formen part d’aquesta entitat.'
