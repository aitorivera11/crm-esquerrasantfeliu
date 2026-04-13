from django.core.exceptions import ValidationError
from django.test import TestCase

from .models import AssignacioMaterial, CategoriaMaterial, StockMaterial, UbicacioMaterial


class MaterialModelTests(TestCase):
    def test_stock_no_negatiu(self):
        ubicacio = UbicacioMaterial.objects.create(nom='Local')
        categoria = CategoriaMaterial.objects.create(nom='Consumibles')
        stock = StockMaterial(
            producte='Cartells',
            categoria=categoria,
            ubicacio=ubicacio,
            quantitat_actual=-1,
            unitat='u',
        )
        with self.assertRaises(ValidationError):
            stock.full_clean()

    def test_assignacio_requires_target(self):
        with self.assertRaises(ValidationError):
            AssignacioMaterial().full_clean()
