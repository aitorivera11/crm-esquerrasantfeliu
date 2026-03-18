from django import forms
from django.contrib.auth.forms import AdminPasswordChangeForm, PasswordChangeForm, UserCreationForm

from .models import Usuari


class StyledFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = f'{css} form-control'.strip()
            field.widget.attrs.setdefault('placeholder', field.label)


class PerfilForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Usuari
        fields = ['nom_complet', 'email', 'telefon', 'username']


class CampanyaPasswordChangeForm(StyledFormMixin, PasswordChangeForm):
    pass


class UsuariAdminCreateForm(StyledFormMixin, UserCreationForm):
    class Meta:
        model = Usuari
        fields = ['nom_complet', 'username', 'email', 'telefon', 'rol', 'is_active']


class UsuariAdminUpdateForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Usuari
        fields = ['nom_complet', 'username', 'email', 'telefon', 'rol', 'is_active']


class UsuariAdminPasswordForm(StyledFormMixin, AdminPasswordChangeForm):
    pass
