import os
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

import requests

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover - handled by warning in parser output
    PdfReader = None

try:
    import pytesseract
except ImportError:  # pragma: no cover - optional dependency
    pytesseract = None

try:
    from PIL import Image
except ImportError:  # pragma: no cover - pillow is in requirements
    Image = None


UPCITEMDB_TRIAL_ENDPOINT = 'https://api.upcitemdb.com/prod/trial/lookup'
UPCITEMDB_PRO_ENDPOINT = 'https://api.upcitemdb.com/prod/v1/lookup'


def lookup_product_by_barcode(upc: str):
    """Return normalized product data from UPCitemdb or None when unavailable."""
    upc = (upc or '').strip()
    if not upc:
        return None

    api_key = os.getenv('UPCITEMDB_USER_KEY', '').strip()
    key_type = os.getenv('UPCITEMDB_KEY_TYPE', '3scale').strip()

    endpoint = UPCITEMDB_PRO_ENDPOINT if api_key else UPCITEMDB_TRIAL_ENDPOINT
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
    if api_key:
        headers.update({'user_key': api_key, 'key_type': key_type})

    response = requests.post(endpoint, json={'upc': upc}, headers=headers, timeout=6)
    response.raise_for_status()

    payload = response.json()
    items = payload.get('items') or []
    if not items:
        return None

    item = items[0]
    return {
        'title': item.get('title') or '',
        'brand': item.get('brand') or '',
        'category': item.get('category') or '',
        'description': item.get('description') or '',
    }


def _to_decimal(raw_value):
    cleaned = (raw_value or '').replace('€', '').replace(' ', '').replace('.', '').replace(',', '.')
    try:
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return None


def _extract_header_fields(text):
    header = {
        'proveidor': '',
        'num_factura_ticket': '',
        'cost_total': None,
        'data_compra': None,
    }
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if lines:
        header['proveidor'] = lines[0][:150]

    invoice_match = re.search(r'(factura|ticket|núm\.?|num\.?|n[ºo])\s*[:#]?\s*([A-Z0-9\-\/]{4,})', text, re.I)
    if invoice_match:
        header['num_factura_ticket'] = invoice_match.group(2)[:80]

    total_match = re.search(r'(total|import)\s*[: ]\s*([0-9][0-9\., ]{1,12})\s*€?', text, re.I)
    if total_match:
        header['cost_total'] = _to_decimal(total_match.group(2))

    date_match = re.search(r'(\d{1,2}[\/\.-]\d{1,2}[\/\.-]\d{2,4})', text)
    if date_match:
        for fmt in ('%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y', '%d/%m/%y', '%d-%m-%y'):
            try:
                header['data_compra'] = datetime.strptime(date_match.group(1), fmt).date()
                break
            except ValueError:
                continue
    return header


def _extract_lines(text):
    """
    Heurística tolerant per detectar línies de compra en tickets/factures OCR.
    Exemples compatibles:
    - Producte X      2  3,50  7,00
    - Producte Y 1x4,20
    """
    detected = []
    for raw_line in text.splitlines():
        line = " ".join(raw_line.strip().split())
        if len(line) < 4:
            continue
        if re.search(r'^(total|subtotal|iva|base|pagat|canvi)\b', line, re.I):
            continue

        qty_price_total = re.match(
            r'^(?P<desc>.*?[A-Za-zÀ-ÿ].*?)\s+(?P<qty>\d+(?:[\.,]\d+)?)\s+(?P<unit>\d+(?:[\.,]\d{1,2})?)\s+(?P<total>\d+(?:[\.,]\d{1,2})?)$',
            line,
        )
        if qty_price_total:
            qty = _to_decimal(qty_price_total.group('qty')) or Decimal('1')
            unit = _to_decimal(qty_price_total.group('unit'))
            total = _to_decimal(qty_price_total.group('total'))
            if unit is not None and total is not None:
                detected.append(
                    {
                        'descripcio': qty_price_total.group('desc')[:255],
                        'quantitat': max(int(qty), 1),
                        'preu_unitari': unit,
                        'total_linia': total,
                        'iva_percent': Decimal('21'),
                    }
                )
                continue

        short_match = re.match(
            r'^(?P<desc>.*?[A-Za-zÀ-ÿ].*?)\s+(?P<qty>\d+)x(?P<unit>\d+(?:[\.,]\d{1,2})?)$',
            line,
            re.I,
        )
        if short_match:
            qty = int(short_match.group('qty'))
            unit = _to_decimal(short_match.group('unit')) or Decimal('0')
            detected.append(
                {
                    'descripcio': short_match.group('desc')[:255],
                    'quantitat': max(qty, 1),
                    'preu_unitari': unit,
                    'total_linia': unit * qty,
                    'iva_percent': Decimal('21'),
                }
            )
    return detected


def parse_purchase_document(uploaded_file):
    """
    Retorna dades suggerides de compra a partir d'un PDF o imatge.
    Sempre retorna dict amb claus: fields, lines, warnings.
    """
    result = {'fields': {}, 'lines': [], 'warnings': []}
    if not uploaded_file:
        result['warnings'].append('No s’ha seleccionat cap fitxer.')
        return result

    file_name = uploaded_file.name.lower()
    text = ''

    if file_name.endswith('.pdf'):
        if PdfReader is None:
            result['warnings'].append('Cal instal·lar pypdf per analitzar PDFs.')
            return result
        reader = PdfReader(uploaded_file)
        text = '\n'.join((page.extract_text() or '') for page in reader.pages)
    else:
        if pytesseract is None or Image is None:
            result['warnings'].append('OCR d’imatges no disponible (instal·la pytesseract + tesseract).')
            return result
        image = Image.open(uploaded_file)
        text = pytesseract.image_to_string(image, lang='cat+spa+eng')

    if not text.strip():
        result['warnings'].append('No s’ha pogut extreure text del document.')
        return result

    result['fields'] = _extract_header_fields(text)
    result['lines'] = _extract_lines(text)
    if not result['lines']:
        result['warnings'].append('No s’han detectat línies de compra automàticament.')
    return result
