from django.contrib import admin

from .models import Acte, ActeTipus, ParticipacioActe, SegmentVisibilitat


class ParticipacioInline(admin.TabularInline):
    model = ParticipacioActe
    extra = 0


@admin.register(ActeTipus)
class ActeTipusAdmin(admin.ModelAdmin):
    list_display = ('nom', 'ordre', 'actiu')
    list_filter = ('actiu',)
    search_fields = ('nom', 'descripcio')


@admin.register(SegmentVisibilitat)
class SegmentVisibilitatAdmin(admin.ModelAdmin):
    list_display = ('etiqueta', 'ambit', 'codi', 'ordre', 'actiu')
    list_filter = ('ambit', 'actiu')
    search_fields = ('etiqueta', 'codi')


@admin.register(Acte)
class ActeAdmin(admin.ModelAdmin):
    list_display = ('titol', 'tipus', 'inici', 'fi', 'ubicacio', 'estat', 'creador')
    list_filter = ('estat', 'tipus')
    search_fields = ('titol', 'ubicacio', 'punt_trobada')
    filter_horizontal = ('visible_per',)
    inlines = [ParticipacioInline]


@admin.register(ParticipacioActe)
class ParticipacioActeAdmin(admin.ModelAdmin):
    list_display = ('acte', 'usuari', 'intencio', 'assistencia_real', 'actualitzat_el')
    list_filter = ('intencio', 'assistencia_real')
    search_fields = ('acte__titol', 'usuari__username', 'usuari__nom_complet')
