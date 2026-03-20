from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Usuari


@admin.register(Usuari)
class UsuariAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Campanya', {'fields': ('nom_complet', 'telefon', 'rol', 'tipus')}),
    )
    list_display = ('username', 'nom_complet', 'email', 'rol', 'tipus', 'is_staff')
