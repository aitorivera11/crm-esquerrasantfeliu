import hashlib
import html
import json
import os
import re
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from agenda.models import Acte, ActeTipus

RESOURCE_ID = "6353e8e8-53ea-47d9-b121-c4bdeac915a5"
BASE_URL = "https://dadesobertes.seu-e.cat/api/3/action/datastore_search_sql"
TIMEZONE = ZoneInfo("Europe/Madrid")
DAYS_AHEAD = 60
PAGE_SIZE = 1000
REQUEST_TIMEOUT = 30
SOURCE_NAME = "AGENDA_CIUTAT"
EXPECTED_API_HOST = "dadesobertes.seu-e.cat"


class Command(BaseCommand):
    help = "Importa actes confirmats de l'agenda pública de Sant Feliu a la base de dades."

    def add_arguments(self, parser):
        parser.add_argument("--days-ahead", type=int, default=DAYS_AHEAD)
        parser.add_argument("--cleanup", action="store_true", help="Elimina els actes importats que ja no venen de l'API.")

    def handle(self, *args, **options):
        importer = CityEventsImporter(days_ahead=options["days_ahead"], stdout=self.stdout)
        stats = importer.run(cleanup=options["cleanup"])
        self.stdout.write(self.style.SUCCESS(json.dumps(stats, ensure_ascii=False)))


class CityEventsImporter:
    def __init__(self, *, days_ahead: int, stdout):
        self.days_ahead = days_ahead
        self.stdout = stdout

    def validate_api_url(self) -> None:
        parsed = urlsplit(BASE_URL)
        if parsed.scheme.lower() != "https":
            raise CommandError("La URL de l'API pública ha de ser HTTPS.")
        if parsed.hostname != EXPECTED_API_HOST:
            raise CommandError(f"Host d'API no permès: {parsed.hostname}")

    def run(self, *, cleanup: bool = False) -> dict[str, int]:
        self.validate_api_url()
        records = self.fetch_all_events()
        events = self.normalize_records(records)
        owner = self.get_owner_user()
        external_type = self.get_external_type()

        created = 0
        updated = 0
        seen_ids: set[str] = set()

        with transaction.atomic():
            for item in events:
                seen_ids.add(item["external_id"])
                defaults = {
                    "titol": item["title"],
                    "descripcio": item["description"],
                    "inici": item["start"],
                    "ubicacio": item["location"] or "Sant Feliu de Llobregat",
                    "estat": Acte.Estat.PUBLICAT,
                    "creador": owner,
                    "external_source": SOURCE_NAME,
                    "source_url": item["url"],
                    "source_payload": item["payload"],
                    "source_checksum": item["checksum"],
                    "tipus": external_type,
                }
                acte, is_created = Acte.objects.update_or_create(
                    external_source=SOURCE_NAME,
                    external_id=item["external_id"],
                    defaults=defaults,
                )
                created += int(is_created)
                updated += int(not is_created)
                self.stdout.write(f"- {'Creat' if is_created else 'Actualitzat'}: {acte.titol}")

            removed = 0
            if cleanup:
                # L'API pública només retorna actes des d'avui endavant.
                # No eliminem històric passat encara que no aparegui a la resposta.
                removed, _ = (
                    Acte.objects.filter(external_source=SOURCE_NAME, inici__gte=timezone.now())
                    .exclude(external_id__in=seen_ids)
                    .delete()
                )

        return {"created": created, "updated": updated, "fetched": len(events), "cleanup": removed}


    def get_external_type(self):
        return ActeTipus.objects.filter(nom__iexact="Acte extern").first()

    def get_owner_user(self):
        User = get_user_model()
        user_id = os.getenv("CITY_EVENTS_IMPORT_USER_ID")
        if user_id:
            user = User.objects.filter(pk=user_id).first()
            if user:
                return user

        user = User.objects.filter(is_superuser=True, is_active=True).order_by("id").first()
        if user:
            return user

        user = User.objects.filter(is_staff=True, is_active=True).order_by("id").first()
        if user:
            return user

        raise CommandError("No hi ha cap usuari actiu per assignar com a creador dels actes importats.")

    def now_local(self) -> datetime:
        return timezone.now().astimezone(TIMEZONE).replace(second=0, microsecond=0)

    def get_date_range(self) -> tuple[datetime, datetime]:
        start = self.now_local()
        return start, start + timedelta(days=self.days_ahead)

    def format_api_dt(self, dt: datetime) -> str:
        return dt.strftime("%Y%m%d%H%M%S")

    def parse_api_dt(self, value: str | None) -> datetime | None:
        if not value:
            return None
        value = str(value).strip()
        if not value:
            return None
        for fmt in ("%Y%m%d%H%M%S", "%Y%m%d"):
            try:
                parsed = datetime.strptime(value, fmt)
                return parsed.replace(tzinfo=TIMEZONE)
            except ValueError:
                continue
        return None

    def collapse_whitespace(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    def strip_html(self, raw: str) -> str:
        text = html.unescape(raw)
        text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"</p\s*>", "\n\n", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
        return text.strip()

    def clean_text(self, value: Any) -> str:
        if value is None:
            return ""
        text = str(value).strip()
        if not text:
            return ""
        if "<" in text and ">" in text:
            text = self.strip_html(text)
        text = html.unescape(text).replace("\r\n", "\n").replace("\r", "\n")
        lines = [self.collapse_whitespace(line) for line in text.split("\n")]
        return "\n".join(line for line in lines if line).strip()

    def build_sql(self, start_dt: datetime, end_dt: datetime, limit: int, offset: int) -> str:
        start_value = self.format_api_dt(start_dt)
        end_value = self.format_api_dt(end_dt)
        if not (start_value.isdigit() and end_value.isdigit()):
            raise CommandError("Format de data invàlid per construir la consulta d'importació.")

        # Aquest SQL no admet placeholders en aquest endpoint CKAN (datastore_search_sql),
        # així que validem i limitem tots els valors dinàmics abans d'interpolar-los.
        clean_limit = max(1, int(limit))
        clean_offset = max(0, int(offset))
        sql_parts = [
            f'SELECT * FROM "{RESOURCE_ID}"',  # nosec B608
            'WHERE "ESTAT" = \'Confirmat\'',
            f'AND "DATA_HORA_INICI_ACTE" >= \'{start_value}\'',
            f'AND "DATA_HORA_INICI_ACTE" < \'{end_value}\'',
            'ORDER BY "DATA_HORA_INICI_ACTE" ASC',
            f"LIMIT {clean_limit} OFFSET {clean_offset}",
        ]
        return " ".join(sql_parts)

    def fetch_page(self, sql: str) -> list[dict[str, Any]]:
        try:
            response = requests.get(BASE_URL, params={"sql": sql}, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            payload = response.json()
        except requests.exceptions.RequestException as exc:
            raise CommandError(f"Error consultant l'API pública: {exc}") from exc
        except ValueError as exc:
            raise CommandError(f"Resposta no JSON de l'API pública: {exc}") from exc
        if not payload.get("success"):
            raise CommandError(f"Resposta incorrecta de l'API: {payload}")
        return payload.get("result", {}).get("records", [])

    def fetch_all_events(self) -> list[dict[str, Any]]:
        start_dt, end_dt = self.get_date_range()
        all_records: list[dict[str, Any]] = []
        offset = 0
        while True:
            records = self.fetch_page(self.build_sql(start_dt, end_dt, PAGE_SIZE, offset))
            if not records:
                break
            all_records.extend(records)
            if len(records) < PAGE_SIZE:
                break
            offset += PAGE_SIZE
        return all_records

    def build_location(self, record: dict[str, Any]) -> str:
        parts = [self.clean_text(record.get("NOM_LLOC")), self.clean_text(record.get("ADREÇA_COMPLETA"))]
        return " · ".join(part for part in parts if part)

    def get_optional_field(self, record: dict[str, Any], *keys: str) -> str:
        for key in keys:
            value = self.clean_text(record.get(key))
            if value:
                return value
        return ""

    def build_description(self, record: dict[str, Any]) -> str:
        pieces: list[str] = []
        for text in (self.clean_text(record.get("DESCRIPCIO")), self.clean_text(record.get("OBSERVACIONS"))):
            if text:
                pieces.append(text)
        meta = []
        for label, value in (
            ("Tipus", self.get_optional_field(record, "TIPUS_ACTE", "TIPUS")),
            ("Lloc", self.clean_text(record.get("NOM_LLOC"))),
            ("Adreça", self.clean_text(record.get("ADREÇA_COMPLETA"))),
            ("Preu", self.get_optional_field(record, "PRICE", "price", "PREU", "IMPORT")),
            ("Enllaç", self.clean_text(record.get("URL"))),
        ):
            if value:
                meta.append(f"{label}: {value}")
        if meta:
            pieces.append("\n".join(meta))
        return "\n\n".join(pieces).strip()

    def get_source_id(self, record: dict[str, Any]) -> str:
        for key in ("ID", "_id"):
            value = self.clean_text(record.get(key))
            if value:
                return value
        return ""

    def make_external_id(self, record: dict[str, Any], start: datetime, title: str) -> str:
        source_id = self.get_source_id(record)
        if source_id:
            return source_id
        safe_title = re.sub(r"[^a-zA-Z0-9]+", "-", title.lower()).strip("-")
        return f"{safe_title}-{self.format_api_dt(start)}"

    def normalize_records(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized = []
        seen = set()
        for record in records:
            title = self.clean_text(record.get("TITOL")) or "Sense títol"
            start = self.parse_api_dt(record.get("DATA_HORA_INICI_ACTE"))
            if start is None:
                continue
            external_id = self.make_external_id(record, start, title)
            if external_id in seen:
                continue
            seen.add(external_id)
            payload = {
                "location_name": self.clean_text(record.get("NOM_LLOC")),
                "address": self.clean_text(record.get("ADREÇA_COMPLETA")),
                "type": self.get_optional_field(record, "TIPUS_ACTE", "TIPUS"),
                "free": self.get_optional_field(record, "FREE", "free", "GRATUIT", "GRATUÏT", "ES_GRATUIT"),
                "price": self.get_optional_field(record, "PRICE", "price", "PREU", "IMPORT"),
                "start": start.isoformat(),
                "end": (self.parse_api_dt(record.get("DATA_HORA_FINAL_ACTE")) or (start + timedelta(hours=1))).isoformat(),
                "url": self.clean_text(record.get("URL")),
                "raw": record,
            }
            normalized.append({
                "external_id": external_id,
                "title": title,
                "start": start,
                "location": self.build_location(record),
                "description": self.build_description(record),
                "url": payload["url"],
                "payload": payload,
                "checksum": hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest(),
            })
        normalized.sort(key=lambda item: (item["start"], item["title"]))
        return normalized
