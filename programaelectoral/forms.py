from django import forms

from .models import BlocPrograma, ComentariProposta, IdeaPluja, IdeaPublica, Proposta


class BlocProgramaForm(forms.ModelForm):
    class Meta:
        model = BlocPrograma
        fields = ('titol', 'descripcio', 'ordre', 'pare', 'estat')
        widgets = {
            'titol': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Títol del bloc'}),
            'descripcio': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'ordre': forms.NumberInput(attrs={'class': 'form-control'}),
            'pare': forms.Select(attrs={'class': 'form-select'}),
            'estat': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['pare'].queryset = BlocPrograma.objects.filter(pare__isnull=True)
        self.fields['pare'].empty_label = '— Bloc arrel (sense pare) —'
        self.fields['pare'].required = False


class PropostaForm(forms.ModelForm):
    class Meta:
        model = Proposta
        fields = ('titol', 'contingut', 'bloc', 'estat')
        widgets = {
            'titol': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Títol de la proposta'}),
            'contingut': forms.Textarea(attrs={'class': 'form-control', 'rows': 6}),
            'bloc': forms.Select(attrs={'class': 'form-select'}),
            'estat': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['bloc'].required = False
        self.fields['bloc'].empty_label = '— Sense bloc assignat —'
        self.fields['contingut'].required = False


class ComentariPropostaForm(forms.ModelForm):
    class Meta:
        model = ComentariProposta
        fields = ('text',)
        widgets = {
            'text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Escriu el teu comentari...',
            }),
        }


class IdeaPlujaForm(forms.ModelForm):
    class Meta:
        model = IdeaPluja
        fields = ('titol', 'descripcio', 'font', 'font_reunio', 'font_entitat', 'font_persona')
        widgets = {
            'titol': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Resum breu de la idea'}),
            'descripcio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'font': forms.Select(attrs={'class': 'form-select', 'x-model': 'fontSelected', '@change': 'fontSelected = $event.target.value'}),
            'font_reunio': forms.Select(attrs={'class': 'form-select'}),
            'font_entitat': forms.Select(attrs={'class': 'form-select'}),
            'font_persona': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in ('font_reunio', 'font_entitat', 'font_persona'):
            self.fields[f].required = False
        self.fields['font_reunio'].empty_label = '— Selecciona una reunió —'
        self.fields['font_entitat'].empty_label = '— Selecciona una entitat —'
        self.fields['font_persona'].empty_label = '— Selecciona una persona —'
        self.fields['descripcio'].required = False


class IdeaPublicaForm(forms.ModelForm):
    deixar_contacte = forms.BooleanField(required=False, label='Vull deixar el meu contacte')
    persona_existent_id = forms.IntegerField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = IdeaPublica
        fields = ('idea', 'nom', 'email', 'telefon')
        widgets = {
            'idea': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Descriu la teva idea o proposta per al programa electoral...',
            }),
            'nom': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom i cognoms'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'correu@exemple.cat'}),
            'telefon': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '600 000 000'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in ('nom', 'email', 'telefon'):
            self.fields[f].required = False


class ConvertirIdeaForm(forms.Form):
    titol = forms.CharField(
        max_length=300,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Títol de la proposta',
    )
    contingut = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        label='Contingut',
    )
    bloc = forms.ModelChoiceField(
        queryset=BlocPrograma.objects.all(),
        required=False,
        empty_label='— Sense bloc assignat —',
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Bloc',
    )
    estat = forms.ChoiceField(
        choices=Proposta.Estat.choices,
        initial=Proposta.Estat.ESBORRANY,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Estat',
    )
