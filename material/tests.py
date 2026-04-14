from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from usuaris.models import Usuari

from .forms import AssignacioMaterialForm, InventariRapidForm, TrasllatRapidForm
from .models import AssignacioMaterial, CategoriaMaterial, ItemMaterial, StockMaterial, UbicacioMaterial
from .services import lookup_product_by_barcode


class MaterialModelTests(TestCase):
    def setUp(self):
        self.ubicacio = UbicacioMaterial.objects.create(nom='Local')
        self.ubicacio2 = UbicacioMaterial.objects.create(nom='Magatzem')
        self.categoria = CategoriaMaterial.objects.create(nom='Consumibles')

    def test_stock_no_negatiu(self):
        stock = StockMaterial(
            producte='Cartells',
            categoria=self.categoria,
            ubicacio=self.ubicacio,
            quantitat_actual=-1,
            unitat='u',
        )
        with self.assertRaises(ValidationError):
            stock.full_clean()

    def test_assignacio_requires_target(self):
        with self.assertRaises(ValidationError):
            AssignacioMaterial().full_clean()

    def test_assignacio_form_bloca_sobre_reserva(self):
        stock = StockMaterial.objects.create(
            producte='Flyers',
            categoria=self.categoria,
            ubicacio=self.ubicacio,
            quantitat_actual=Decimal('10'),
            unitat='u',
        )
        AssignacioMaterial.objects.create(stock=stock, quantitat_reservada=Decimal('8'), estat_reserva=AssignacioMaterial.EstatReserva.RESERVAT)
        form = AssignacioMaterialForm(
            data={
                'stock': stock.pk,
                'quantitat_reservada': '5',
                'quantitat_retornada': '0',
                'estat_reserva': AssignacioMaterial.EstatReserva.RESERVAT,
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn('No hi ha disponibilitat suficient', str(form.errors))

    def test_trasllat_rapid_form_rebutja_mateixa_ubicacio(self):
        item = ItemMaterial.objects.create(
            codi_intern='INV-0001',
            descripcio='Carpa',
            ubicacio_actual=self.ubicacio,
            data_alta=date.today(),
            valor_estimad=0,
        )
        form = TrasllatRapidForm(data={'item': item.pk, 'desti': self.ubicacio.pk, 'observacions': ''})
        self.assertFalse(form.is_valid())

    def test_inventari_rapid_form_valid(self):
        form = InventariRapidForm(
            data={
                'prefix_codi': 'INV',
                'descripcio': 'Cadira',
                'categoria': self.categoria.pk,
                'ubicacio_actual': self.ubicacio2.pk,
                'quantitat': 3,
                'data_alta': date.today(),
                'valor_estimad': '20.00',
            }
        )
        self.assertTrue(form.is_valid())


class BarcodeLookupTests(TestCase):
    def setUp(self):
        self.user = Usuari.objects.create_user(
            username='coordi',
            password='secret12345',
            nom_complet='Usuari Coordinació',
            rol=Usuari.Rol.COORDINACIO,
        )
        self.client.force_login(self.user)

    @patch('material.services.requests.post')
    def test_lookup_product_by_barcode_parses_response(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'items': [
                {
                    'title': 'Retolador permanent',
                    'brand': 'Staedtler',
                    'category': 'Office',
                    'description': 'Retolador negre punta fina',
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = lookup_product_by_barcode('1234567890123')

        self.assertEqual(result['title'], 'Retolador permanent')
        self.assertEqual(result['brand'], 'Staedtler')

    @patch('material.views.lookup_product_by_barcode')
    def test_barcode_lookup_endpoint_returns_json(self, mock_lookup):
        mock_lookup.return_value = {
            'title': 'Adhesiu',
            'brand': 'MarcaX',
            'category': 'Merch',
            'description': 'Adhesiu campanya',
        }

        response = self.client.get(reverse('material:barcode_lookup'), {'upc': '8412345678901'})

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            response.content,
            {
                'ok': True,
                'item': {
                    'title': 'Adhesiu',
                    'brand': 'MarcaX',
                    'category': 'Merch',
                    'description': 'Adhesiu campanya',
                },
            },
        )
