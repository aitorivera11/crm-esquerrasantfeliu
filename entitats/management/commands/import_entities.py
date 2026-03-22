import hashlib
import json
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from entitats.models import Entitat

RESOURCE_ID = 'e3bc59ef-5b2d-454f-8b00-63bd13f024a4'
BASE_URL = 'https://dadesobertes.seu-e.cat/api/3/action/datastore_search'
REQUEST_TIMEOUT = 30
PAGE_SIZE = 1000
SOURCE_NAME = 'DIRECTORI_ENTITATS'


class Command(BaseCommand):
    help = 'Importa entitats des del directori públic de dades obertes.'

    def add_arguments(self, parser):
        parser.add_argument('--cleanup', action='store_true', help='Elimina les entitats importades que ja no existeixen a la font.')

    def handle(self, *args, **options):
        importer = EntitiesImporter(stdout=self.stdout)
        stats = importer.run(cleanup=options['cleanup'])
        self.stdout.write(self.style.SUCCESS(json.dumps(stats, ensure_ascii=False)))


class EntitiesImporter:
    def __init__(self, *, stdout):
        self.stdout = stdout

    def run(self, *, cleanup: bool = False) -> dict[str, int]:
        records = self.fetch_all_records()
        normalized = self.normalize_records(records)
        created = 0
        updated = 0
        seen_ids: set[str] = set()

        with transaction.atomic():
            for record in normalized:
                seen_ids.add(record['external_id'])
                entitat, is_created = Entitat.objects.update_or_create(
                    external_source=SOURCE_NAME,
                    external_id=record['external_id'],
                    defaults={
                        'nom': record['nom'],
                        'email': record['email'],
                        'telefon': record['telefon'],
                        'web': record['web'],
                        'tipologia': record['tipologia'],
                        'ambit': record['ambit'],
                        'source_url': record['source_url'],
                        'source_checksum': record['checksum'],
                        'source_payload': record['payload'],
                    },
                )
                created += int(is_created)
                updated += int(not is_created)
                self.stdout.write(f"- {'Creada' if is_created else 'Actualitzada'}: {entitat.nom}")

            removed = 0
            if cleanup:
                removed, _ = Entitat.objects.filter(external_source=SOURCE_NAME).exclude(external_id__in=seen_ids).delete()
            else:
                removed = 0

        return {'created': created, 'updated': updated, 'removed': removed, 'fetched': len(normalized)}

    def fetch_page(self, offset: int) -> list[dict[str, Any]]:
        query = urlencode({'resource_id': RESOURCE_ID, 'limit': PAGE_SIZE, 'offset': offset})
        try:
            with urlopen(f'{BASE_URL}?{query}', timeout=REQUEST_TIMEOUT) as response:
                payload = json.loads(response.read().decode('utf-8'))
        except (HTTPError, URLError) as exc:
            raise CommandError(f"Error consultant l'API pública d'entitats: {exc}") from exc
        if not payload.get('success'):
            raise CommandError(f"Resposta incorrecta de l'API d'entitats: {payload}")
        return payload.get('result', {}).get('records', [])

    def fetch_all_records(self) -> list[dict[str, Any]]:
        offset = 0
        records: list[dict[str, Any]] = []
        while True:
            batch = self.fetch_page(offset)
            if not batch:
                break
            records.extend(batch)
            if len(batch) < PAGE_SIZE:
                break
            offset += PAGE_SIZE
        return records

    def clean_text(self, value: Any) -> str:
        if value is None:
            return ''
        return re.sub(r'\s+', ' ', str(value)).strip()

    def clean_url(self, value: Any) -> str:
        url = self.clean_text(value)
        if not url:
            return ''
        if not re.match(r'^https?://', url, re.I):
            url = f'https://{url}'
        return url

    def get_first(self, record: dict[str, Any], *keys: str) -> str:
        record_lower = {str(key).lower(): value for key, value in record.items()}
        for key in keys:
            value = self.clean_text(record_lower.get(key.lower()))
            if value:
                return value
        return ''

    def make_external_id(self, record: dict[str, Any], nom: str) -> str:
        for key in ('_id', 'id', 'ID'):
            value = self.clean_text(record.get(key))
            if value:
                return value
        return re.sub(r'[^a-z0-9]+', '-', nom.lower()).strip('-') or hashlib.sha1(json.dumps(record, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()

    def normalize_records(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized = []
        seen_ids = set()
        for record in records:
            nom = self.get_first(record, 'title', 'titol', 'nom', 'entitat', 'name')
            if not nom:
                continue
            payload = {
                'email': self.get_first(record, 'mail', 'email', 'correu'),
                'telefon': self.get_first(record, 'telefon', 'tel', 'phone'),
                'web': self.clean_url(self.get_first(record, 'web', 'url', 'website')),
                'tipologia': self.get_first(record, 'tipologia', 'tipus', 'categoria'),
                'ambit': self.get_first(record, 'ambit', 'àmbit', 'ambito'),
                'raw': record,
            }
            external_id = self.make_external_id(record, nom)
            if external_id in seen_ids:
                continue
            seen_ids.add(external_id)
            normalized.append({
                'external_id': external_id,
                'nom': nom,
                'email': payload['email'],
                'telefon': payload['telefon'],
                'web': payload['web'],
                'tipologia': payload['tipologia'],
                'ambit': payload['ambit'],
                'payload': payload,
                'source_url': f'{BASE_URL}?resource_id={RESOURCE_ID}',
                'checksum': hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest(),
            })
        normalized.sort(key=lambda item: item['nom'].lower())
        return normalized
