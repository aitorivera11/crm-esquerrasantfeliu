# Auditoría técnica del proyecto

Fecha de auditoría: 2026-03-23

## Resumen ejecutivo

La base del proyecto es sólida y la separación por dominios (`agenda`, `reunions`, `persones`, `entitats`, `usuaris`) está bien planteada. El módulo de `agenda` es el más maduro en permisos, cobertura de tests y consistencia de UX. Aun así, se han detectado varias incoherencias relevantes, especialmente en permisos, consistencia visual/editorial y algunas oportunidades claras de optimización.

## Hallazgos prioritarios

### 1. Incoherencia de permisos entre módulos

- `agenda` protege creación/edición mediante permisos explícitos.
- `reunions` permite la mayoría de operaciones con solo `LoginRequiredMixin`.
- Los grupos automáticos definidos en `usuaris/signals.py` no contemplan permisos específicos para reuniones o tareas.

**Riesgo:** usuarios autenticados con perfil básico pueden acceder a acciones de edición que no encajan con la política aplicada al resto de módulos.

**Recomendación:** definir permisos funcionales para reuniones/tareas y aplicarlos a vistas de escritura, igual que ya se hace en agenda.

### 2. Navegación y acciones visibles para usuarios sin permiso real

- El menú lateral muestra `Persones` a cualquier usuario autenticado.
- La vista de `persones` solo está permitida a administración y coordinación.
- El dashboard muestra `Afegir persona` aunque el usuario no tenga acceso al módulo.

**Riesgo:** experiencia incoherente y sensación de producto “roto” al llevar al usuario a un acceso denegado.

**Recomendación:** renderizar navegación y CTAs según permisos o roles efectivos.

### 3. Bug lógico en la sincronización reunión ↔ acto de agenda

En `ReunioForm.sync_acte_agenda()`:

- si la reunión es interna, se restringe la visibilidad a coordinación;
- si deja de ser interna y el acto ya existía, la limpieza solo se ejecuta si el acto se estaba creando en ese momento.

**Riesgo:** reuniones que han dejado de ser internas pueden seguir restringidas por arrastre.

**Recomendación:** recalcular siempre `visible_per` y `assistencia_permesa_per` cuando cambie `es_interna`.

## Hallazgos de nivel medio

### 4. Filtrado y cómputo en Python en lugar de base de datos

Se han detectado patrones como:

- cálculo de tareas vencidas iterando en Python;
- conversión de `QuerySet` a lista en `TascaListView` cuando se filtra por vencidas;
- panel de seguimiento que vuelve a calcular en memoria información derivada.

**Riesgo:** peor escalabilidad y pérdida de optimizaciones futuras (paginación, ordenación, chaining de queryset).

**Recomendación:** llevar estos filtros a SQL siempre que sea viable.

### 5. Campo potencialmente infrautilizado: `assistencia_permesa_per`

El modelo `Acte` distingue entre:

- `visible_per`
- `assistencia_permesa_per`

Pero la lógica visible en vistas usa principalmente `visible_per`.

**Riesgo:** deuda funcional o campo “muerto” que añade complejidad sin valor real.

**Recomendación:** decidir si ese campo debe participar en reglas de negocio reales o si conviene simplificar el modelo.

### 6. Configuración de base de datos poco portable para test/local

Con la configuración por defecto, `manage.py test` falla sobre SQLite si no se fuerza `DB_SSL_REQUIRE=False`, porque se inyecta `sslmode`.

**Riesgo:** fricción en entornos locales y CI sencillos.

**Recomendación:** condicionar `ssl_require` al backend real de base de datos.

## Incoherencias de interfaz

### 7. Terminología mezclada

Se mezclan expresiones como:

- `Panel de seguiment`
- `Panell de reunions`
- `Filtra`
- `Aplicar filtres`

**Riesgo:** falta de coherencia editorial y visual.

**Recomendación:** fijar una guía mínima de copy UI.

### 8. URLs hardcodeadas en estados vacíos

El componente `empty_state` recibe rutas directas como `'/agenda/nou/'` o `'/reunions/nova/'` en varias plantillas.

**Riesgo:** menor mantenibilidad ante refactors de rutas.

**Recomendación:** usar siempre `{% url %}` cuando sea posible.

## Fortalezas detectadas

- `agenda` tiene una cobertura de tests mucho más profunda que el resto.
- La estructura del proyecto es clara y extensible.
- La integración reunión ↔ agenda es una buena base de producto.
- La UI base tiene una dirección visual consistente, aunque necesita pulido editorial.

## Priorización sugerida

### Prioridad 1

1. Aplicar permisos reales a `reunions` y `tasques`.
2. Ocultar enlaces/acciones no permitidas por rol.
3. Corregir la resincronización de visibilidad al cambiar `es_interna`.

### Prioridad 2

4. Optimizar filtros/cómputos en Python.
5. Mejorar la portabilidad de la configuración de DB para test/local.

### Prioridad 3

6. Unificar terminología de interfaz.
7. Sustituir URLs hardcodeadas por rutas nombradas.
8. Ampliar tests de `reunions`, especialmente permisos y flujos de edición.

## Comprobaciones realizadas durante la auditoría

- `DB_SSL_REQUIRE=False python manage.py check`
- `DB_SSL_REQUIRE=False python manage.py test`
- `python manage.py test` → falla con SQLite por la configuración SSL por defecto
