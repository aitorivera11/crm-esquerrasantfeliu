from django.contrib import admin

from .models import (
    Acta,
    AreaCampanya,
    DocumentAdjunt,
    EtiquetaReunioTasques,
    HistoricEstatTasca,
    PuntActa,
    PuntOrdreDia,
    Reunio,
    SeguimentTasca,
    Tasca,
    TascaRelacioReunio,
    TipusReunio,
)


class PuntOrdreDiaInline(admin.TabularInline):
    model = PuntOrdreDia
    extra = 0
    ordering = ('ordre',)
    autocomplete_fields = ('responsable',)


class PuntActaInline(admin.TabularInline):
    model = PuntActa
    extra = 0
    ordering = ('ordre',)
    autocomplete_fields = ('punt_ordre_origen',)


class TascaRelacioReunioInline(admin.TabularInline):
    model = TascaRelacioReunio
    extra = 0
    autocomplete_fields = ('tasca', 'punt_ordre_dia', 'punt_acta')


class SeguimentTascaInline(admin.TabularInline):
    model = SeguimentTasca
    extra = 0
    autocomplete_fields = ('autor', 'reunio')


class DocumentAdjuntInline(admin.TabularInline):
    model = DocumentAdjunt
    extra = 0
    autocomplete_fields = ('pujat_per',)


@admin.register(AreaCampanya)
class AreaCampanyaAdmin(admin.ModelAdmin):
    list_display = ('nom', 'ordre', 'activa')
    list_filter = ('activa',)
    search_fields = ('nom', 'descripcio')


@admin.register(EtiquetaReunioTasques)
class EtiquetaReunioTasquesAdmin(admin.ModelAdmin):
    list_display = ('nom', 'ordre', 'color')
    search_fields = ('nom',)


@admin.register(TipusReunio)
class TipusReunioAdmin(admin.ModelAdmin):
    list_display = ('nom', 'codi', 'ordre', 'activa', 'permet_ordre_dia_i_acta')
    list_filter = ('activa', 'permet_ordre_dia_i_acta')
    search_fields = ('nom', 'codi', 'descripcio')


@admin.register(Reunio)
class ReunioAdmin(admin.ModelAdmin):
    list_display = ('titol', 'tipus', 'estat', 'inici', 'area', 'convocada_per', 'es_estrategica')
    list_filter = ('tipus', 'estat', 'es_estrategica', 'area')
    search_fields = ('titol', 'descripcio', 'objectiu', 'ubicacio')
    autocomplete_fields = ('convocada_per', 'moderada_per', 'area', 'assistents', 'persones_relacionades', 'entitats_relacionades', 'etiquetes')
    inlines = [PuntOrdreDiaInline, TascaRelacioReunioInline, DocumentAdjuntInline]



@admin.register(PuntOrdreDia)
class PuntOrdreDiaAdmin(admin.ModelAdmin):
    list_display = ('reunio', 'ordre', 'titol', 'responsable', 'estat', 'requereix_acord')
    list_filter = ('estat', 'requereix_acord')
    search_fields = ('titol', 'descripcio', 'reunio__titol')
    autocomplete_fields = ('reunio', 'responsable')


@admin.register(PuntActa)
class PuntActaAdmin(admin.ModelAdmin):
    list_display = ('acta', 'ordre', 'titol', 've_de_ordre_dia')
    list_filter = ('ve_de_ordre_dia',)
    search_fields = ('titol', 'contingut', 'acords', 'acta__reunio__titol')
    autocomplete_fields = ('acta', 'punt_ordre_origen')


@admin.register(Acta)
class ActaAdmin(admin.ModelAdmin):
    list_display = ('reunio', 'estat', 'data_tancament', 'redactada_per')
    list_filter = ('estat', 'data_tancament')
    search_fields = ('reunio__titol', 'resum_general', 'acords_presos')
    autocomplete_fields = ('reunio', 'redactada_per')
    inlines = [PuntActaInline]


@admin.register(Tasca)
class TascaAdmin(admin.ModelAdmin):
    list_display = ('titol', 'estat', 'prioritat', 'responsable', 'data_limit', 'origen', 'es_estrategica')
    list_filter = ('estat', 'prioritat', 'origen', 'es_estrategica', 'visibilitat', 'area')
    search_fields = ('titol', 'descripcio', 'observacions_seguiment', 'resultat_tancament')
    autocomplete_fields = ('creada_per', 'responsable', 'collaboradors', 'area', 'reunio_origen', 'punt_acta_origen', 'persones_relacionades', 'entitats_relacionades', 'etiquetes')
    inlines = [TascaRelacioReunioInline, SeguimentTascaInline, DocumentAdjuntInline]


@admin.register(DocumentAdjunt)
class DocumentAdjuntAdmin(admin.ModelAdmin):
    list_display = ('titol', 'reunio', 'tasca', 'pujat_per', 'creat_el')
    list_filter = ('creat_el',)
    search_fields = ('titol', 'descripcio', 'reunio__titol', 'tasca__titol')
    autocomplete_fields = ('reunio', 'tasca', 'pujat_per')


@admin.register(SeguimentTasca)
class SeguimentTascaAdmin(admin.ModelAdmin):
    list_display = ('tasca', 'tipus', 'autor', 'nou_estat', 'reunio', 'creat_el')
    list_filter = ('tipus', 'nou_estat')
    search_fields = ('tasca__titol', 'comentari', 'autor__nom_complet', 'autor__username')
    autocomplete_fields = ('tasca', 'autor', 'reunio')


@admin.register(TascaRelacioReunio)
class TascaRelacioReunioAdmin(admin.ModelAdmin):
    list_display = ('tasca', 'reunio', 'tipus_relacio', 'tractada_el')
    list_filter = ('tipus_relacio',)
    search_fields = ('tasca__titol', 'reunio__titol', 'resum')
    autocomplete_fields = ('tasca', 'reunio', 'punt_ordre_dia', 'punt_acta')


@admin.register(HistoricEstatTasca)
class HistoricEstatTascaAdmin(admin.ModelAdmin):
    list_display = ('tasca', 'estat_anterior', 'estat_nou', 'canviat_per', 'creat_el')
    list_filter = ('estat_nou',)
    search_fields = ('tasca__titol', 'motiu')
    autocomplete_fields = ('tasca', 'canviat_per')
