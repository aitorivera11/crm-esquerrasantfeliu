from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from usuaris.models import Usuari

from .forms import AssignacioMaterialForm, InventariRapidForm, TrasllatRapidForm
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
from .services import lookup_product_by_barcode, parse_purchase_document


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


class PurchaseDocumentParserTests(TestCase):
    @patch('material.services.PdfReader')
    def test_parse_purchase_document_detects_fields_and_lines_from_pdf(self, mock_pdf_reader):
        pdf_file = SimpleNamespace(name='ticket.pdf')
        mock_pdf_reader.return_value.pages = [
            MagicMock(extract_text=MagicMock(return_value=(
                "Forn Sant Josep\n"
                "Ticket: ABC-4433\n"
                "14/04/2026\n"
                "Barra de pa 2 1,20 2,40\n"
                "Aigua 1 0,80 0,80\n"
                "TOTAL 3,20 €"
            )))
        ]

        parsed = parse_purchase_document(pdf_file)

        self.assertEqual(parsed['fields']['proveidor'], 'Forn Sant Josep')
        self.assertEqual(parsed['fields']['num_factura_ticket'], 'ABC-4433')
        self.assertEqual(parsed['fields']['cost_total'], Decimal('3.20'))
        self.assertEqual(len(parsed['lines']), 2)

    def test_parse_purchase_document_without_file_returns_warning(self):
        parsed = parse_purchase_document(None)
        self.assertTrue(parsed['warnings'])


class PurchaseCreateStockSyncTests(TestCase):
    def setUp(self):
        self.user = Usuari.objects.create_user(
            username='adminstock',
            password='secret12345',
            nom_complet='Admin Stock',
            rol=Usuari.Rol.ADMINISTRACIO,
        )
        self.client.force_login(self.user)
        self.ubicacio = UbicacioMaterial.objects.create(nom='Magatzem Central', activa=True)
        self.categoria = CategoriaMaterial.objects.create(nom='Mobiliari')

    def test_creating_purchase_routes_inventariable_to_items_and_consumible_to_stock(self):
        response = self.client.post(
            reverse('material:compra_create'),
            data={
                'data_compra': '2026-04-15',
                'proveidor': 'Fusteria Soler',
                'cost_total': '200.00',
                'metode_pagament': 'TARGETA',
                'num_factura_ticket': 'FAC-2026-15',
                'linies-TOTAL_FORMS': '2',
                'linies-INITIAL_FORMS': '0',
                'linies-MIN_NUM_FORMS': '0',
                'linies-MAX_NUM_FORMS': '1000',
                'linies-0-compra': '',
                'linies-0-categoria': str(self.categoria.pk),
                'linies-0-tipus_linia': LiniaCompraMaterial.TipusLinia.INVENTARIABLE,
                'linies-0-descripcio': 'Taula plegable',
                'linies-0-quantitat': '2',
                'linies-0-preu_unitari': '75.00',
                'linies-0-iva_percent': '21.00',
                'linies-0-total_linia': '150.00',
                'linies-0-codi_barres': '',
                'linies-1-compra': '',
                'linies-1-categoria': str(self.categoria.pk),
                'linies-1-tipus_linia': LiniaCompraMaterial.TipusLinia.CONSUMIBLE,
                'linies-1-descripcio': 'Díptic campanya',
                'linies-1-quantitat': '50',
                'linies-1-preu_unitari': '1.00',
                'linies-1-iva_percent': '21.00',
                'linies-1-total_linia': '50.00',
                'linies-1-codi_barres': '',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(CompraMaterial.objects.count(), 1)
        self.assertEqual(ItemMaterial.objects.filter(descripcio='Taula plegable').count(), 2)

        stock = StockMaterial.objects.get(producte='Díptic campanya')
        self.assertEqual(stock.quantitat_actual, Decimal('50'))

        self.assertEqual(
            MovimentMaterial.objects.filter(item__descripcio='Taula plegable', tipus_moviment=MovimentMaterial.Tipus.ENTRADA).count(),
            2,
        )
        self.assertTrue(MovimentMaterial.objects.filter(stock=stock, tipus_moviment=MovimentMaterial.Tipus.ENTRADA).exists())
