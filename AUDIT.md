# Auditoría técnica del proyecto

Fecha de auditoría: 2026-04-01

## Resumen ejecutivo

Se ha realizado una nueva revisión funcional y de seguridad del código Django del repositorio. La base general es consistente, y se observa una mejora clara respecto a auditorías anteriores en dos áreas clave: permisos de escritura en `reunions` y portabilidad de la configuración de base de datos para entornos SQLite.

Aun así, persisten riesgos relevantes, especialmente en un endpoint de importación expuesto por HTTP GET con efectos de escritura y autenticación opcional según configuración. También se detectan riesgos de endurecimiento de seguridad en `settings.py` y deuda de testing en módulos sin cobertura.

## Hallazgos prioritarios

### 1) Endpoint de cron con efecto de escritura vía GET y secreto opcional (ALTO)

**Dónde:** `agenda/views.py` (`ImportCityEventsCronView`) + `agenda/urls.py`.

**Qué ocurre:**

- La vista acepta `GET` y ejecuta `call_command('import_city_events', '--cleanup', ...)`, es decir, muta datos.
- El control de acceso depende de `CRON_SECRET`, pero si `CRON_SECRET` está vacío, la condición de rechazo no se activa y el endpoint queda operativo sin autenticación efectiva.
- El secreto puede recibirse también por querystring (`?key=`), aumentando exposición accidental en logs/intermediarios.

**Riesgo:** ejecución no autorizada de importaciones, consumo de recursos y alteración del estado de agenda.

**Recomendación:**

1. Exigir siempre autenticación fuerte (secret obligatorio o firma HMAC con expiración).
2. Cambiar a `POST` (o al menos rechazar GET para operaciones mutables).
3. Eliminar el paso de credenciales por querystring y aceptar solo cabecera.
4. Añadir test específico que falle si `CRON_SECRET` está ausente.

### 2) Configuración de seguridad de producción insuficientemente endurecida (ALTO)

**Dónde:** `config/settings.py`.

**Qué ocurre:** no se observa activación condicional de controles estándar de hardening en producción (`SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, HSTS, etc.).

**Riesgo:** degradación de seguridad en despliegues reales si no se compensa externamente.

**Recomendación:** añadir bloque de seguridad cuando `DEBUG=False`, con valores por entorno y documentación mínima en README.

## Hallazgos de nivel medio

### 3) Cobertura de tests incompleta por dominios

**Dónde:** existen tests en `agenda`, `reunions`, `entitats`, `usuaris`, pero no en `persones` ni `core`.

**Riesgo:** regresiones silenciosas en permisos, navegación o flujos de vistas base.

**Recomendación:** incorporar una suite mínima en `persones/tests.py` y `core/tests.py` (acceso por rol, respuesta 200/403, navegación esperada).

### 4) Warning de estáticos durante test suite

**Dónde:** ejecución de `python manage.py test`.

**Qué ocurre:** aparece warning por ausencia de `staticfiles_build/static/`.

**Riesgo:** ruido en CI y potencial confusión de errores reales frente a advertencias de entorno.

**Recomendación:** crear directorio en setup de CI o condicionar configuración de estáticos para test.

## Aspectos verificados como mejora respecto a la auditoría previa

1. **Permisos en `reunions` mejor definidos:** uso de `PermissionRequiredMixin` para operaciones de escritura de reuniones, actas, puntos y tareas.
2. **Configuración de DB más portable:** el cálculo de `ssl_require` ya contempla SQLite por defecto, evitando el fallo anterior en tests locales.
3. **Navegación más coherente por permisos:** el sidebar ya condiciona enlaces sensibles por rol/permisos.

## Priorización sugerida

### Prioridad 1 (inmediata)

1. Cerrar el riesgo del endpoint `import-city-events` (auth obligatoria + método POST + tests).
2. Endurecer `settings.py` para producción (`SECURE_*`, HSTS, cookies seguras).

### Prioridad 2

3. Añadir cobertura de tests para `core` y `persones`.
4. Limpiar warning de estáticos en pipeline de tests.

## Comprobaciones ejecutadas en esta auditoría

- `python manage.py check` → OK
- `python manage.py test` → OK (44 tests), con warning de estáticos

