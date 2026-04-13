from django.contrib import admin

from .models import (
    AssignacioMaterial,
    CategoriaMaterial,
    CompraMaterial,
    ItemMaterial,
    LiniaCompraMaterial,
    MovimentMaterial,
    StockMaterial,
    UbicacioMaterial,
)


@admin.register(CategoriaMaterial)
class CategoriaMaterialAdmin(admin.ModelAdmin):
    list_display = ('nom', 'pare', 'activa')
    list_filter = ('activa',)
    search_fields = ('nom',)


@admin.register(UbicacioMaterial)
class UbicacioMaterialAdmin(admin.ModelAdmin):
    list_display = ('nom', 'responsable_per_defecte', 'activa')
    list_filter = ('activa',)
    search_fields = ('nom', 'adreca')


class LiniaCompraInline(admin.TabularInline):
    model = LiniaCompraMaterial
    extra = 0


@admin.register(CompraMaterial)
class CompraMaterialAdmin(admin.ModelAdmin):
    list_display = ('id', 'data_compra', 'proveidor', 'cost_total', 'metode_pagament')
    list_filter = ('metode_pagament', 'data_compra')
    search_fields = ('proveidor', 'num_factura_ticket')
    inlines = [LiniaCompraInline]


@admin.register(ItemMaterial)
class ItemMaterialAdmin(admin.ModelAdmin):
    list_display = ('codi_intern', 'descripcio', 'estat', 'ubicacio_actual', 'data_alta')
    list_filter = ('estat', 'categoria', 'ubicacio_actual')
    search_fields = ('codi_intern', 'descripcio', 'codi_barres')


@admin.register(StockMaterial)
class StockMaterialAdmin(admin.ModelAdmin):
    list_display = ('producte', 'ubicacio', 'quantitat_actual', 'unitat', 'llindar_minim')
    list_filter = ('categoria', 'ubicacio')
    search_fields = ('producte', 'codi_barres')


@admin.register(MovimentMaterial)
class MovimentMaterialAdmin(admin.ModelAdmin):
    list_display = ('tipus_moviment', 'data_moviment', 'origen', 'desti', 'quantitat', 'actor')
    list_filter = ('tipus_moviment',)


@admin.register(AssignacioMaterial)
class AssignacioMaterialAdmin(admin.ModelAdmin):
    list_display = ('id', 'acte', 'tasca', 'item', 'stock', 'quantitat_reservada', 'estat_reserva')
    list_filter = ('estat_reserva',)
