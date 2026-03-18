from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Usuari


@admin.register(Usuari)
class UsuariAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Campanya', {'fields': ('nom_complet', 'telefon', 'rol')}),
    )
    list_display = ('username', 'nom_complet', 'email', 'rol', 'is_staff')
