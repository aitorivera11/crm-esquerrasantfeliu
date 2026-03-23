from django.contrib import admin

from .models import Persona


@admin.register(Persona)
class PersonaAdmin(admin.ModelAdmin):
    list_display = ('nom', 'email', 'telefon')
    search_fields = ('nom', 'email', 'telefon', 'notes')
