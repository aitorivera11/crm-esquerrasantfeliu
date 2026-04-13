# CRM Esquerra Sant Feliu

Base inicial d'un gestor de campanya municipal amb Django, templates i HTMX, preparada per desplegar-se en qualsevol entorn compatible amb Python i PostgreSQL/Neon.

## Arquitectura

- `config/`: configuració global Django, WSGI/ASGI i rutes principals.
- `core/`: models comuns, auditoria i peces compartides.
- `usuaris/`: model d'usuari personalitzat i rols de campanya.
- `agenda/`: actes, participació i flux principal de l'MVP.
- `persones/`: punt d'entrada mínim per al futur mòdul de contactes.
- `templates/`: interfície amb Django templates i HTMX.

Aquesta separació evita barrejar autenticació, domini de negoci i utilitats compartides, i permet créixer en nous mòduls sense reescriure el projecte.

## Instal·lació local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Variables d'entorn

- `SECRET_KEY`
- `DEBUG`
- `ALLOWED_HOSTS`
- `DATABASE_URL`
- `SITE_ID` (opcional, per defecte `1`)

## Accés amb Google (OAuth)

Aquest projecte està preparat amb `django-allauth` per oferir inici de sessió amb Google a la pantalla d'accés.

### 1) Crear credencials OAuth a Google

- **Google**: crea un OAuth Client (tipus *Web application*) a Google Cloud.

En tots els casos, afegeix l'URL de callback que et mostrarà allauth. Exemple local típic:

- `http://localhost:8000/accounts/google/login/callback/`

### 2) Migracions

Allauth necessita les taules de `sites` i `socialaccount`:

```bash
python manage.py migrate
```

### 3) Configurar el Site

Al panell d'admin (`/admin/`), revisa **Sites** i assegura que el domini coincideix amb el teu entorn (`localhost:8000`, staging o producció). Si fas servir un altre `SITE_ID`, defineix-lo per variable d'entorn.

### 4) Donar d'alta el proveïdor a Django Admin

A `Social applications` (admin):

1. Tria proveïdor (`Google`).
2. Introdueix `Client id` i `Secret key`.
3. Associa l'aplicació al `Site` correcte.

### 5) Provar login

A `/accounts/login/` veuràs el botó de “Continuar amb Google”.

## Desplegament (Docker + Gunicorn)

- `Dockerfile` genera una imatge Python 3.12 i instal·la dependències de sistema per PostgreSQL.
- `start.sh` espera la base de dades, executa `python manage.py migrate --noinput` i `python manage.py collectstatic --noinput`, i aixeca Gunicorn.
- `settings.py` llegeix `DATABASE_URL` via `dj-database-url` i manté WhiteNoise per servir estàtics.
- Compatible amb PostgreSQL de Neon o qualsevol PostgreSQL estàndard.

## Migracions en entorns de producció

- Executa sempre `python manage.py migrate --noinput` abans d'arrencar l'aplicació.
- Si el desplegament és amb contenidors, aquest pas ja queda cobert a `start.sh`.
- Per forçar la recollida d'estàtics manualment: `python manage.py collectstatic --noinput --clear`.

## Importació automàtica d'actes de ciutat

- El comandament `python manage.py import_city_events --cleanup` importa cada nit els actes confirmats de l'API pública de Sant Feliu i els desa a la taula `agenda_acte`.
- Els actes importats queden marcats amb `external_source='AGENDA_CIUTAT'`, es publiquen automàticament i mantenen el payload original a `source_payload` per a futurs camps o integracions.
- Configura un cron extern a les `02:00` (UTC) contra `/agenda/cron/import-city-events/`.
- Protegeix aquest endpoint amb `CRON_SECRET` i, si vols controlar el propietari dels actes creats, defineix `CITY_EVENTS_IMPORT_USER_ID`.
- Per provar-ho localment: `DB_SSL_REQUIRE=False python manage.py import_city_events --cleanup`.

## Rols i permisos recomanats

- **Administració**: tots els permisos del sistema i gestió completa d’usuaris.
- **Coordinació**: crear/editar actes, veure participants i marcar assistència real.
- **Participant**: veure l’agenda publicada i indicar participació.

A més del rol, cada usuari pot tenir un **tipus intern** (`Militant`, `Voluntari` o `Amic`) per segmentar la base de participants sense canviar permisos.

Implementació suggerida amb `Django Groups` i permisos de model:

- Crear actes: `agenda.add_acte`
- Editar actes: `agenda.change_acte`
- Veure participants: `agenda.can_view_participants`
- Marcar assistència real: `agenda.can_mark_attendance`

## Flux d'usuari MVP

1. Una persona de coordinació crea l'acte des de `/agenda/nou/`.
2. L'equip consulta la llista a `/agenda/`.
3. Cada usuari entra al detall i fa clic a `Hi aniré`, `Potser` o `No hi aniré`.
4. Coordinació revisa `/agenda/<id>/participants/`.
5. Després de l'acte, coordinació marca l'assistència real.

## Full de ruta

### MVP
- models i autenticació
- agenda i participació
- auditoria bàsica
- desplegament funcional en infraestructura pròpia o cloud

### Iteracions següents
- millores UX i filtres
- notificacions
- dashboard de campanya
- mòduls de persones, tasques, materials i incidències
