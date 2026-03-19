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
- `vercel.json` fa servir `buildCommand` per executar `python manage.py migrate --noinput` a cada deploy, i les `routes` amb `handle: filesystem` deixen que Vercel serveixi primer els fitxers reals (com `/static/...`) abans de reenviar la resta a Django.
- `settings.py` llegeix `DATABASE_URL` via `dj-database-url`.
- El `buildCommand` de `vercel.json` executa `python manage.py migrate --noinput`; després `build.sh` també corre `collectstatic`, així que les migracions s'apliquen directament sobre Neon abans de servir el deploy.
- Els estàtics es serveixen amb WhiteNoise i `CompressedStaticFilesStorage`, també a Vercel; `collectstatic` els deixa a `staticfiles/` i `WHITENOISE_USE_FINDERS` permet servir `static/` com a fallback si el directori empaquetat no existeix encara, evitant dependència de noms hashats antics en canvis de deploy o caché.
- Compatible amb PostgreSQL de Neon.


## Migracions a Vercel amb Neon

1. Defineix `DATABASE_URL` a Vercel amb la cadena de connexió de Neon.
2. Cada desplegament executa `./build.sh`.
3. Aquest script corre `python manage.py migrate --noinput` contra la base de dades remota i després `python manage.py collectstatic --noinput`.
4. Si hi ha una migració nova pendent, queda aplicada durant el build abans que el deploy entri en producció.

Això evita haver d'entrar manualment a un contenidor: el mateix deploy de Vercel actualitza l'esquema de Neon.

## Rols i permisos recomanats

- **Administrador**: tots els permisos del sistema.
- **Coordinador**: crear/editar actes, veure participants, marcar assistència real.
- **Voluntari / militant**: veure agenda publicada i indicar participació.
- **Consulta**: lectura de l'agenda publicada.

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
