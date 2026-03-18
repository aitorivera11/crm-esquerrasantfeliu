from django.contrib import admin

from .models import Acte, ParticipacioActe


class ParticipacioInline(admin.TabularInline):
    model = ParticipacioActe
    extra = 0


@admin.register(Acte)
class ActeAdmin(admin.ModelAdmin):
    list_display = ('titol', 'inici', 'ubicacio', 'estat', 'creador')
    list_filter = ('estat',)
    search_fields = ('titol', 'ubicacio')
    inlines = [ParticipacioInline]


@admin.register(ParticipacioActe)
class ParticipacioActeAdmin(admin.ModelAdmin):
    list_display = ('acte', 'usuari', 'intencio', 'assistencia_real', 'actualitzat_el')
    list_filter = ('intencio', 'assistencia_real')
    search_fields = ('acte__titol', 'usuari__username', 'usuari__nom_complet')
