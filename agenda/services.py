import json
import os
import re
from datetime import datetime, timedelta
from html import unescape
from urllib.request import Request, urlopen

try:
    import pytesseract
except ImportError:  # pragma: no cover - optional dependency
    pytesseract = None

try:
    from PIL import Image
except ImportError:  # pragma: no cover - pillow is optional at runtime
    Image = None

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - optional dependency
    OpenAI = None

CATALAN_SPANISH_MONTHS = {
    'gener': 1,
    'ene': 1,
    'enero': 1,
    'febrer': 2,
    'febrero': 2,
    'marc': 3,
    'març': 3,
    'marzo': 3,
    'abril': 4,
    'abr': 4,
    'maig': 5,
    'mayo': 5,
    'juny': 6,
    'junio': 6,
    'juliol': 7,
    'julio': 7,
    'agost': 8,
    'agosto': 8,
    'setembre': 9,
    'septiembre': 9,
    'octubre': 10,
    'novembre': 11,
    'noviembre': 11,
    'desembre': 12,
    'dic': 12,
    'diciembre': 12,
}

LOCATION_KEYWORDS = (
    'plaça',
    'plaza',
    'carrer',
    'calle',
    'avinguda',
    'avenida',
    'ateneu',
    'casal',
    'centre cívic',
    'centro cívico',
    'parc',
    'parque',
)


def extract_text_from_image(uploaded_file):
    if not uploaded_file:
        return {'text': '', 'warnings': []}
    if pytesseract is None or Image is None:
        return {'text': '', 'warnings': ['OCR no disponible (instal·la pytesseract + tesseract).']}

    try:
        uploaded_file.seek(0)
        image = Image.open(uploaded_file)
        text = pytesseract.image_to_string(image, lang='cat+spa+eng')
        return {'text': text.strip(), 'warnings': []}
    except Exception as exc:  # pragma: no cover - depends on tesseract runtime
        return {'text': '', 'warnings': [f"No s'ha pogut executar l'OCR: {exc}"]}


def _normalize_space(value):
    return re.sub(r'\s+', ' ', (value or '').strip())


def _extract_hours(text):
    ranges = re.findall(r'(\d{1,2})[:h\.](\d{2})\s*(?:h)?\s*(?:-|a|–)\s*(\d{1,2})[:h\.](\d{2})', text, flags=re.I)
    if ranges:
        start = f'{int(ranges[0][0]):02d}:{int(ranges[0][1]):02d}'
        end = f'{int(ranges[0][2]):02d}:{int(ranges[0][3]):02d}'
        return start, end

    single = re.search(r'\b(?:a\s+les\s+|a\s+la\s+|a\s+las\s+|a\s+)?(\d{1,2})[:h\.](\d{2})\s*(?:h)?\b', text, flags=re.I)
    if single:
        start = f'{int(single.group(1)):02d}:{int(single.group(2)):02d}'
        return start, ''

    compact = re.search(r'\b(\d{1,2})\s*h\b', text, flags=re.I)
    if compact:
        start = f'{int(compact.group(1)):02d}:00'
        return start, ''

    return '', ''


def _extract_numeric_date(text):
    match = re.search(r'\b(\d{1,2})[\/\-.](\d{1,2})(?:[\/\-.](\d{2,4}))?\b', text)
    if not match:
        return None
    day = int(match.group(1))
    month = int(match.group(2))
    year_raw = match.group(3)
    now = datetime.now()
    if not year_raw:
        year = now.year
    else:
        year = int(year_raw)
        if year < 100:
            year += 2000

    try:
        parsed = datetime(year, month, day)
    except ValueError:
        return None

    if not year_raw and parsed.date() < now.date() - timedelta(days=2):
        parsed = parsed.replace(year=year + 1)
    return parsed.date()


def _extract_named_date(text):
    match = re.search(
        r'\b(\d{1,2})\s*(?:de\s+)?([A-Za-zÀ-ÿçÇ]+)\s*(?:de\s+)?(\d{4})?\b',
        text,
        flags=re.I,
    )
    if not match:
        return None

    day = int(match.group(1))
    month_name = match.group(2).strip().lower()
    month_name = month_name.replace('ç', 'c')
    month = CATALAN_SPANISH_MONTHS.get(month_name)
    if not month:
        return None
    year = int(match.group(3)) if match.group(3) else datetime.now().year

    try:
        parsed = datetime(year, month, day)
    except ValueError:
        return None

    if not match.group(3) and parsed.date() < datetime.now().date() - timedelta(days=2):
        parsed = parsed.replace(year=year + 1)
    return parsed.date()


def _extract_location(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    lowered_lines = [line.lower() for line in lines]
    for idx, line in enumerate(lowered_lines):
        if any(keyword in line for keyword in LOCATION_KEYWORDS):
            return _normalize_space(lines[idx])

    inline = re.search(
        r'\b(?:lloc|ubicacio|ubicación|lugar)\s*[:\-]\s*([^\n\.]{4,120})',
        text,
        flags=re.I,
    )
    if inline:
        return _normalize_space(inline.group(1))
    return ''


def _extract_title(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines:
        normalized = _normalize_space(line)
        if len(normalized) < 6:
            continue
        if re.search(r'\b(\d{1,2}[\/\-.]\d{1,2}|\d{1,2}:\d{2}|@)\b', normalized):
            continue
        return normalized[:255]
    return (lines[0][:255] if lines else 'Acte des d’Instagram')


def _extract_municipality(text):
    match = re.search(r'\b(?:a|en)\s+([A-ZÀ-Ý][\wÀ-ÿ\-\s]{2,40})\b', text)
    if match:
        return _normalize_space(match.group(1))
    return ''


def _extract_entity(text):
    patterns = [
        r'\borganitza\s*[:\-]?\s*([^\n\.]{3,100})',
        r'\borganizado por\s*[:\-]?\s*([^\n\.]{3,100})',
        r'@([A-Za-z0-9_\.]{3,40})',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.I)
        if match:
            return _normalize_space(match.group(1))
    return ''


def extract_event_fields_from_text(text):
    clean_text = (text or '').strip()
    if not clean_text:
        return {}

    date_value = _extract_numeric_date(clean_text) or _extract_named_date(clean_text)
    start_time, end_time = _extract_hours(clean_text)
    location = _extract_location(clean_text)

    return {
        'title': _extract_title(clean_text),
        'description': clean_text[:4000],
        'date': date_value.isoformat() if date_value else '',
        'start_time': start_time,
        'end_time': end_time,
        'location': location,
        'municipality': _extract_municipality(clean_text),
        'organizer': _extract_entity(clean_text),
    }


def _extract_with_ai(combined_text):
    api_key = os.getenv('OPENAI_API_KEY', '').strip()
    if not api_key or OpenAI is None:
        return {'fields': {}, 'warnings': []}

    model = os.getenv('INSTAGRAM_EVENT_AI_MODEL', 'gpt-4.1-mini')
    client = OpenAI(api_key=api_key)
    prompt = (
        'Extreu camps d\'un possible esdeveniment des d\'un text. '
        'Retorna NOMÉS JSON amb claus: title, description, date(YYYY-MM-DD), '
        'start_time(HH:MM), end_time(HH:MM), location, municipality, organizer. '
        'Si no tens un valor fiable, deixa cadena buida.'
    )
    try:  # pragma: no cover - external API
        response = client.responses.create(
            model=model,
            input=[
                {'role': 'system', 'content': prompt},
                {'role': 'user', 'content': combined_text[:12000]},
            ],
            temperature=0,
        )
        content = response.output_text or '{}'
        parsed = json.loads(content)
        return {'fields': parsed if isinstance(parsed, dict) else {}, 'warnings': []}
    except Exception as exc:  # pragma: no cover - external API
        return {'fields': {}, 'warnings': [f'Extracció IA no disponible: {exc}']}


def fetch_instagram_post_preview(instagram_url):
    url = (instagram_url or '').strip()
    if not url:
        return {'caption': '', 'image_url': '', 'warnings': []}

    try:
        request = Request(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (compatible; CRMEsquerraSantFeliuBot/1.0)',
                'Accept-Language': 'ca,es;q=0.9,en;q=0.8',
            },
        )
        with urlopen(request, timeout=10) as response:  # nosec B310 - trusted public URL provided by user
            html = response.read().decode('utf-8', errors='ignore')
    except Exception as exc:  # pragma: no cover - network dependent
        return {'caption': '', 'image_url': '', 'warnings': [f"No s'ha pogut llegir la publicació d'Instagram: {exc}"]}

    def _meta_content(name):
        pattern = rf'<meta[^>]+(?:property|name)=["\']{name}["\'][^>]+content=["\']([^"\']+)["\']'
        match = re.search(pattern, html, flags=re.I)
        return unescape(match.group(1)).strip() if match else ''

    caption = _meta_content('og:description') or _meta_content('description')
    image_url = _meta_content('og:image')
    return {'caption': caption, 'image_url': image_url, 'warnings': []}


def build_event_from_instagram_source(instagram_url, manual_text='', ocr_text='', observations='', instagram_caption=''):
    chunks = [
        f'URL font: {instagram_url}'.strip(),
        (instagram_caption or '').strip(),
        (manual_text or '').strip(),
        (ocr_text or '').strip(),
    ]
    combined_text = '\n\n'.join(chunk for chunk in chunks if chunk)
    heuristic_fields = extract_event_fields_from_text(combined_text)
    ai_result = _extract_with_ai(combined_text)
    ai_fields = ai_result.get('fields') or {}

    merged = {**heuristic_fields}
    for key, value in ai_fields.items():
        if value and not merged.get(key):
            merged[key] = str(value).strip()

    residual_notes = []
    if merged.get('municipality'):
        residual_notes.append(f"Municipi detectat: {merged['municipality']}")
    if merged.get('organizer'):
        residual_notes.append(f"Entitat/organitzador detectat: {merged['organizer']}")
    if observations:
        residual_notes.append(f'Observacions importació: {observations.strip()}')

    description_lines = [merged.get('description', '').strip()]
    if residual_notes:
        description_lines.append('')
        description_lines.append('---')
        description_lines.extend(residual_notes)

    merged['description'] = '\n'.join(line for line in description_lines if line).strip()
    merged['source_url'] = (instagram_url or '').strip()
    merged['observations'] = (observations or '').strip()

    return {
        'fields': merged,
        'combined_text': combined_text,
        'warnings': ai_result.get('warnings', []),
        'heuristic_fields': heuristic_fields,
        'ai_fields': ai_fields,
    }


def parse_instagram_event_data(instagram_url='', manual_text='', image_file=None, observations=''):
    instagram_preview = fetch_instagram_post_preview(instagram_url)
    ocr_result = extract_text_from_image(image_file)
    proposal = build_event_from_instagram_source(
        instagram_url=instagram_url,
        manual_text=manual_text,
        ocr_text=ocr_result.get('text', ''),
        observations=observations,
        instagram_caption=instagram_preview.get('caption', ''),
    )
    warnings = []
    warnings.extend(instagram_preview.get('warnings', []))
    warnings.extend(ocr_result.get('warnings', []))
    warnings.extend(proposal.get('warnings', []))
    return {
        'fields': proposal['fields'],
        'raw_text': proposal['combined_text'],
        'ocr_text': ocr_result.get('text', ''),
        'warnings': warnings,
        'heuristic_fields': proposal.get('heuristic_fields', {}),
        'ai_fields': proposal.get('ai_fields', {}),
    }
