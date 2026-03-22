from django import forms
from django.contrib.auth.forms import AdminPasswordChangeForm, PasswordChangeForm, UserCreationForm
from django.forms import CheckboxInput, CheckboxSelectMultiple, RadioSelect, Select, SelectMultiple, Textarea

from .models import Usuari


class StyledFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            css = widget.attrs.get('class', '').strip()

            if isinstance(widget, (CheckboxInput,)):
                classes = 'form-check-input'
            elif isinstance(widget, (Select, SelectMultiple)) and not isinstance(widget, (CheckboxSelectMultiple, RadioSelect)):
                classes = 'form-select'
            elif isinstance(widget, (CheckboxSelectMultiple, RadioSelect)):
                classes = css
            else:
                classes = 'form-control'

            if classes:
                widget.attrs['class'] = f'{css} {classes}'.strip()

            if not isinstance(widget, (CheckboxInput, CheckboxSelectMultiple, RadioSelect, SelectMultiple, Textarea)):
                widget.attrs.setdefault('placeholder', field.label)


class PerfilForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Usuari
        fields = ['nom_complet', 'email', 'telefon', 'username']


class CampanyaPasswordChangeForm(StyledFormMixin, PasswordChangeForm):
    pass


class RegistreUsuariForm(StyledFormMixin, UserCreationForm):
    class Meta:
        model = Usuari
        fields = ['nom_complet', 'username', 'email', 'telefon', 'tipus']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.rol = Usuari.Rol.PARTICIPANT
        user.is_active = False
        if commit:
            user.save()
        return user


class UsuariAdminCreateForm(StyledFormMixin, UserCreationForm):
    class Meta:
        model = Usuari
        fields = ['nom_complet', 'username', 'email', 'telefon', 'rol', 'tipus', 'is_active']


class UsuariAdminUpdateForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Usuari
        fields = ['nom_complet', 'username', 'email', 'telefon', 'rol', 'tipus', 'is_active']


class UsuariAdminPasswordForm(StyledFormMixin, AdminPasswordChangeForm):
    pass
