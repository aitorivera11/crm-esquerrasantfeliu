# CRM Esquerra Sant Feliu

Base inicial d'un gestor de campanya municipal amb Django, templates i HTMX, preparada per desplegar a Vercel amb PostgreSQL/Neon.

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

## Desplegament a Vercel

- El runtime de Vercel entra per `wsgi.py`, que reexporta l'app Django de `config/wsgi.py`.
- `vercel.json` segueix l'esquema de `version: 2` amb dos builds: `@vercel/python` per a `wsgi.py` i `@vercel/static-build` per a `build.sh`, que publica els estàtics generats dins `staticfiles_build/`.
- `settings.py` llegeix `DATABASE_URL` via `dj-database-url`.
- `build.sh` executa `python manage.py migrate --noinput` i després `python manage.py collectstatic --noinput --clear`, de manera que les migracions i la recopilació d'estàtics passen durant el build.
- Els estàtics es publiquen a `staticfiles_build/static/` i Vercel els resol amb la ruta `/static/(.*)`; Django també manté WhiteNoise amb `CompressedManifestStaticFilesStorage` per servir-los correctament si la petició entra per l'app Python.
- Compatible amb PostgreSQL de Neon.


## Migracions a Vercel amb Neon

1. Defineix `DATABASE_URL` a Vercel amb la cadena de connexió de Neon.
2. Cada desplegament executa `./build.sh`.
3. Aquest script corre `python manage.py migrate --noinput` contra la base de dades remota i després `python manage.py collectstatic --noinput --clear`.
4. Si hi ha una migració nova pendent, queda aplicada durant el build abans que el deploy entri en producció.

Això evita haver d'entrar manualment a un contenidor: el mateix deploy de Vercel actualitza l'esquema de Neon.


## Importació automàtica d'actes de ciutat

- El comandament `python manage.py import_city_events --cleanup` importa cada nit els actes confirmats de l'API pública de Sant Feliu i els desa a la taula `agenda_acte`.
- Els actes importats queden marcats amb `external_source='AGENDA_CIUTAT'`, es publiquen automàticament i mantenen el payload original a `source_payload` per a futurs camps o integracions.
- Vercel executa un cron a les `02:00` (UTC) contra `/agenda/cron/import-city-events/`.
- Protegeix aquest endpoint amb `CRON_SECRET` i, si vols controlar el propietari dels actes creats, defineix `CITY_EVENTS_IMPORT_USER_ID`.
- Per provar-ho localment: `DB_SSL_REQUIRE=False python manage.py import_city_events --cleanup`.

## Rols i permisos recomanats

- **Administrador**: tots els permisos del sistema.
- **Coordinador**: crear/editar actes, veure participants, marcar assistència real.
- **Voluntari / militant**: veure agenda publicada i indicar participació.
- **Consulta**: lectura de l'agenda publicada.

A més del rol, cada usuari pot tenir un **tipus intern** (`Militant`, `Voluntari` o `Amic`) per segmentar la base de participants sense canviar permisos.

Implementació suggerida amb `Django Groups` i permisos de model:

- Crear actes: `agenda.add_acte`
- Editar actes: `agenda.change_acte`
- Veure participants: `agenda.can_view_participants`
- Marcar assistència real: `agenda.can_mark_attendance`

## Flux d'usuari MVP

1. Una persona coordinadora crea l'acte des de `/agenda/nou/`.
2. L'equip consulta la llista a `/agenda/`.
3. Cada usuari entra al detall i fa clic a `Hi aniré`, `Potser` o `No hi aniré`.
4. Coordinació revisa `/agenda/<id>/participants/`.
5. Després de l'acte, coordinació marca l'assistència real.

## Full de ruta

### MVP
- models i autenticació
- agenda i participació
- auditoria bàsica
- desplegament funcional a Vercel

### Iteracions següents
- millores UX i filtres
- notificacions
- dashboard de campanya
- mòduls de persones, tasques, materials i incidències
