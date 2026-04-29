import os
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
import json

import requests
try:
    from google import genai
except ImportError:  # pragma: no cover - optional dependency
    genai = None

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
    cleaned = (raw_value or '').replace('€', '').replace(' ', '')
    if ',' in cleaned and '.' in cleaned:
        cleaned = cleaned.replace('.', '').replace(',', '.')
    elif ',' in cleaned:
        cleaned = cleaned.replace(',', '.')
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


def _strip_markdown_json(raw_text):
    text = (raw_text or '').strip()
    if text.startswith('```'):
        text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.I)
        text = re.sub(r'\s*```$', '', text)
    return text.strip()


def _parse_date(raw_value):
    value = (raw_value or '').strip()
    if not value:
        return None
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y', '%d/%m/%y', '%d-%m-%y'):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _normalize_gemini_payload(payload):
    fields = payload.get('fields') or {}
    lines = payload.get('lines') or []
    return {
        'fields': {
            'proveidor': (fields.get('proveidor') or '')[:150],
            'num_factura_ticket': (fields.get('num_factura_ticket') or '')[:80],
            'cost_total': _to_decimal(str(fields.get('cost_total') or '')),
            'data_compra': _parse_date(str(fields.get('data_compra') or '')),
        },
        'lines': [
            {
                'tipus_linia': line.get('tipus_linia') or None,
                'descripcio': (line.get('descripcio') or 'Línia detectada automàticament')[:255],
                'quantitat': max(int(_to_decimal(str(line.get('quantitat') or '1')) or 1), 1),
                'preu_unitari': _to_decimal(str(line.get('preu_unitari') or '0')) or Decimal('0'),
                'iva_percent': _to_decimal(str(line.get('iva_percent') or '21')) or Decimal('21'),
                'total_linia': _to_decimal(str(line.get('total_linia') or '0')) or Decimal('0'),
            }
            for line in lines
            if isinstance(line, dict)
        ],
    }


def _extract_text_from_gemini_response(payload):
    candidates = payload.get('candidates') or []
    if not candidates:
        return ''
    parts = (candidates[0].get('content') or {}).get('parts') or []
    return ''.join(part.get('text', '') for part in parts if isinstance(part, dict))


def _call_gemini_purchase_parser(text):
    api_key = os.getenv('GEMINI_API_KEY', '').strip()
    if not api_key or genai is None:
        return None

    model = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash').strip() or 'gemini-2.0-flash'
    prompt = (
        "Extreu informació d'un ticket o factura i respon NOMÉS JSON vàlid amb aquest esquema:"
        '{"fields":{"proveidor":"","num_factura_ticket":"","cost_total":"","data_compra":""},'
        '"lines":[{"tipus_linia":"CONSUMIBLE","descripcio":"","quantitat":1,"preu_unitari":"","iva_percent":"","total_linia":""}]}. '
        "Data preferentment en format YYYY-MM-DD. Mantén decimals amb punt."
        "\n\nDocument OCR:\n"
        f"{text[:12000]}"
    )
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=[prompt, text[:12000]],
        config={'temperature': 0},
    )
    raw_text = getattr(response, 'text', '') or ''
    if not raw_text:
        raw_text = _extract_text_from_gemini_response(response.to_json_dict())
    cleaned = _strip_markdown_json(raw_text)
    parsed = json.loads(cleaned)
    return _normalize_gemini_payload(parsed)


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

    parsed_by_gemini = None
    try:
        parsed_by_gemini = _call_gemini_purchase_parser(text)
    except Exception:
        result['warnings'].append('Gemini no ha pogut analitzar el document; s’aplica detecció local.')

    if parsed_by_gemini:
        result['fields'] = parsed_by_gemini.get('fields', {})
        result['lines'] = parsed_by_gemini.get('lines', [])
    else:
        result['fields'] = _extract_header_fields(text)
        result['lines'] = _extract_lines(text)
    if not result['lines']:
        result['warnings'].append('No s’han detectat línies de compra automàticament.')
    return result
