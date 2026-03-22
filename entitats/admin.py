from django.contrib import admin

from .models import Entitat


@admin.register(Entitat)
class EntitatAdmin(admin.ModelAdmin):
    list_display = ('nom', 'email', 'telefon', 'tipologia', 'ambit', 'external_source')
    search_fields = ('nom', 'email', 'telefon', 'tipologia', 'ambit')
    filter_horizontal = ('persones',)
