from django import forms

from usuaris.forms import StyledFormMixin

from .models import (
    AssignacioMaterial,
    CategoriaMaterial,
    CompraMaterial,
    ItemMaterial,
    LiniaCompraMaterial,
    StockMaterial,
    UbicacioMaterial,
)


class CategoriaMaterialForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = CategoriaMaterial
        fields = ['nom', 'pare', 'activa']


class UbicacioMaterialForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = UbicacioMaterial
        fields = ['nom', 'adreca', 'responsable_per_defecte', 'notes', 'activa']
        widgets = {'notes': forms.Textarea(attrs={'rows': 3})}


class CompraMaterialForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = CompraMaterial
        fields = [
            'data_compra',
            'proveidor',
            'pagador_usuari',
            'pagador_entitat',
            'cost_total',
            'metode_pagament',
            'num_factura_ticket',
            'document',
            'observacions',
        ]
        widgets = {
            'data_compra': forms.DateInput(attrs={'type': 'date'}),
            'observacions': forms.Textarea(attrs={'rows': 3}),
        }


class LiniaCompraMaterialForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = LiniaCompraMaterial
        fields = [
            'compra',
            'categoria',
            'descripcio',
            'quantitat',
            'preu_unitari',
            'iva_percent',
            'total_linia',
            'codi_barres',
            'foto',
        ]


class ItemMaterialForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = ItemMaterial
        fields = [
            'codi_intern',
            'descripcio',
            'categoria',
            'estat',
            'ubicacio_actual',
            'data_alta',
            'valor_estimad',
            'codi_barres',
            'foto_principal',
        ]
        widgets = {'data_alta': forms.DateInput(attrs={'type': 'date'})}


class StockMaterialForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = StockMaterial
        fields = ['producte', 'categoria', 'ubicacio', 'quantitat_actual', 'unitat', 'llindar_minim', 'codi_barres']


class AssignacioMaterialForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = AssignacioMaterial
        fields = [
            'acte',
            'tasca',
            'item',
            'stock',
            'quantitat_reservada',
            'quantitat_retornada',
            'estat_reserva',
        ]
