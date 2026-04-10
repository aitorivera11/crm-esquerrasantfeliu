# Revisión funcional y de usabilidad (producto) — CRM de campaña

Fecha: 2026-04-10

## 1) Resumen ejecutivo

**Veredicto:** el producto tiene una base útil y una dirección correcta para un equipo de campaña, pero **todavía no está listo** para adopción sólida en un equipo municipal/territorial mediano sin fricción operativa.

### Fortalezas principales
- Existe un hilo funcional potente entre **agenda → reunión → acta → tareas**, incluyendo sincronización de asistencia y relación de tareas con puntos de acta/reunión.
- Hay una intención clara de “producto interno” (atajos, paneles, autosave de acta, creación rápida de tareas desde reunión y desde comandos de texto).
- Se han definido roles y permisos mínimos con una separación operativa razonable (administración, coordinación, participante).

### Debilidades críticas
- Gran parte del valor de coordinación depende de formularios largos y de decisiones manuales no guiadas (especialmente en tareas y reunión).
- Hay mezcla entre lógica de negocio y UX que genera ambigüedad: estados, visibilidad y trazabilidad están, pero no siempre se presentan de forma accionable.
- Faltan piezas clave para operación política real: gestión explícita de acuerdos, decisiones, bloqueos políticos, dependencias, alertas y continuidad estructurada entre reuniones.

### Impresión global de usabilidad
- **Nivel actual:** “MVP avanzado / beta interna”.
- **Riesgo de adopción:** medio-alto si el equipo no tiene una persona “superusuaria” que haga de soporte funcional.

---

## 2) Diagnóstico por módulo

## A. Agenda

### Qué está bien
- Buen conjunto de filtros de agenda (texto, rango, tipo, estado, visibilidad, respuesta personal), con visión de volumen (próximos/importados/pasados/importantes).
- Flujo personal de participación bien definido (Sí / Quizá / No) y módulo de “mis actos”.
- Soporte de compartición (WhatsApp/correo/copiar), exportación a calendario (Google + .ics), y diferenciación de eventos importados.
- Vinculación con reunión para sincronizar asistentes.

### Qué está mal / fricciones
- El modelo de acto no diferencia de forma nativa categorías operativas clave de campaña (institucional, puerta a puerta, acto barrio, prensa, interno de coordinación) más allá de “tipo” genérico; eso obliga a convenciones manuales.
- El formulario de acto pide muchos campos sin progresión por contexto (acto simple vs acto complejo).
- Detección de conflictos de agenda inexistente: no hay aviso de solapamientos de personas clave, espacios o reuniones relacionadas.
- El seguimiento post-acto es pobre: hay asistencia real, pero no hay bloque estándar de “resultado político / incidencias / próximos pasos”.

### Qué falta
- Checklist operativo pre-acto (materiales, responsables, logística, mensajes).
- Resultado post-acto estructurado y conectado a tareas/acuerdos.
- Vista calendario real (semanal/mensual por persona/equipo) con conflictos.

### Gravedad
- **Alta** para conflictos/no seguimiento post-acto.
- **Media** para complejidad de formulario.

## B. Reuniones y asambleas

### Qué está bien
- Flujo de reunión completo (orden del día, acta, puntos, exportación, workspace de ejecución).
- Muy buen concepto de workspace con autosave y creación de tareas desde el propio punto de acta (incluida creación por comandos `@tasca ...`).
- Capacidad de convertir tareas marcadas en “llevar al siguiente orden del día”.

### Qué está mal / fricciones
- El formulario de reunión es excesivamente amplio para el primer paso; no diferencia “convocar” de “documentar en profundidad”.
- Falta “continuidad guiada” entre reunión N y N+1: hay piezas sueltas, pero no un bloque único de “pendiente heredado / decisión pendiente / replanificación”.
- Los acuerdos están parcialmente modelados en texto libre (acta/puntos), pero no como entidad operativa con responsable/plazo/estado.
- La trazabilidad es técnica pero no siempre operativa: para saber qué está “pendiente de decisión política” hay que navegar varias vistas.

### Qué falta
- Entidad “Acuerdo/Decisión” con ciclo de vida propio y vínculo a tareas.
- Vista de cierre de reunión (qué se decide, qué se delega, qué se bloquea, qué sube al próximo orden del día).
- Plantillas de orden del día por tipo de reunión (interna, asamblea, coordinación territorial).

### Gravedad
- **Alta** para acuerdos/continuidad entre reuniones.
- **Media** para sobrecarga en formulario de reunión.

## C. Tareas y seguimiento

### Qué está bien
- Modelo de tarea relativamente rico (estado, prioridad, origen, visibilidad, área, estratégica, relaciones con personas/entidades).
- Historial de estados y seguimiento comentado, con vinculación a reuniones.
- Panel de seguimiento con vencidas/bloqueadas/abiertas.

### Qué está mal / fricciones
- El formulario de tarea es demasiado largo para uso cotidiano; puede aumentar abandono o tareas incompletas.
- No hay dependencias entre tareas ni gestión de capacidad de responsables.
- Falta señalización fuerte de cuellos de botella (por persona, por área, por antigüedad en bloqueo).
- Cerrar una tarea exige “resultado de cierre” (positivo para trazabilidad), pero no existe un flujo de cierre asistido por contexto.

### Qué falta
- Dependencias (`bloqueada_por`, `desbloquea_a`) y alertas por dependencia crítica.
- Semáforos operativos: “sin movimiento X días”, “bloqueada > N días”, “sin responsable claro”.
- Vista tipo Kanban por estado/responsable/área.

### Gravedad
- **Alta** para ausencia de dependencias y visión de capacidad.
- **Media** para fricción de formulario.

## D. Personas, roles y coordinación

### Qué está bien
- Roles básicos bien definidos (admin/coordinación/participante) y sincronizados con grupos.
- Módulos de personas y entidades existen y se relacionan con agenda/reuniones/tareas.

### Qué está mal / fricciones
- El sistema de permisos se apoya mucho en rol global; falta granularidad por territorio/área/equipo.
- Comunicación interna no está resuelta en producto (solo seguimiento textual en tareas).
- Las personas externas (aliados, portavoces de entidad, perfiles institucionales) no tienen tipologías operativas potentes para coordinación política.

### Qué falta
- Permisos por ámbito (barrios, áreas, campaña específica).
- Modelo de “responsable político” vs “responsable operativo”.
- Registro de stakeholders externos y nivel de relación/compromiso.

### Gravedad
- **Media-Alta** para escalado a equipos medianos.

## E. Navegación general

### Qué está bien
- Navegación lateral clara por dominios (agenda, trabajo interno, entorno, usuario, admin).
- Dashboard con entradas rápidas y métricas de alto nivel.

### Qué está mal / fricciones
- El dashboard prioriza conteos, pero falta una capa “qué tengo que decidir hoy”.
- Algunos caminos clave requieren demasiada navegación cruzada (reunión ↔ tarea ↔ acta) para preguntas simples de coordinación.
- Participante tiene experiencia bastante limitada (agenda y respuesta), poca sensación de progreso o utilidad continua.

### Qué falta
- Bandeja de trabajo por rol: “hoy / esta semana / bloqueos / decisiones pendientes”.
- Alertas proactivas (no solo consulta manual).

### Gravedad
- **Media**.

## F. Formularios

### Qué está bien
- Uso consistente de componentes y estilo visual homogéneo.
- Widgets de selección múltiple con búsqueda y acciones masivas.

### Qué está mal / fricciones
- Formularios críticos (reunión/tarea) no están orientados al principio de “mínimo dato viable + completar después”.
- Sobrecarga cognitiva por mezclar campos estratégicos, logísticos y de trazabilidad en una sola pantalla.

### Qué falta
- Formularios escalonados (pasos o bloques progresivos).
- Valores por defecto inteligentes basados en contexto (tipo de reunión, responsable habitual, plantillas).

### Gravedad
- **Alta** en tareas/reuniones.

## G. Dashboards / seguimiento

### Qué está bien
- Existen paneles de seguimiento funcionales y conteos útiles.

### Qué está mal / fricciones
- Paneles centrados en listados, no en decisiones o desviaciones.
- No hay vista territorial (barrios/distritos), ni vista de compromisos políticos.

### Qué falta
- Dashboard de compromisos y decisiones.
- Dashboard territorial y de capacidad de equipo.

### Gravedad
- **Media-Alta**.

---

## 3) Problemas de usabilidad concretos (lista directa)

1. Formularios de reunión y tarea demasiado largos para uso diario. **(Alta)**
2. Ausencia de detección de solapamientos en agenda (persona/recurso/evento). **(Alta)**
3. Acuerdos y decisiones no modelados como objeto operativo. **(Alta)**
4. Continuidad entre reuniones no guiada por flujo único. **(Alta)**
5. Sin dependencias entre tareas ni alerta de cadena bloqueada. **(Alta)**
6. Poca visibilidad de “qué requiere decisión política” frente a “qué requiere ejecución”. **(Alta)**
7. Participación y asistencia bien capturadas, pero sin cierre cualitativo del acto. **(Media-Alta)**
8. Navegación con demasiado salto entre módulos para preguntas simples. **(Media)**
9. Participante con experiencia limitada y baja retención funcional. **(Media)**
10. Falta de recordatorios/alertas automáticas. **(Media-Alta)**
11. Falta de priorización visual fuerte por antigüedad de bloqueo. **(Media)**
12. Riesgo de sobrecarga administrativa para coordinación (demasiado dato manual). **(Alta)**

---

## 4) Mejoras propuestas (priorizadas)

## 4.1 Impacto alto / esfuerzo bajo
1. **Dividir formularios de reunión y tarea** en “rápido” y “completo”.
2. **Añadir bloque de “siguientes pasos” post-acto** (3 campos: resultado, incidencias, tareas derivadas).
3. **Banner de alertas operativas** en dashboard: vencidas, bloqueadas >7 días, reuniones sin acta cerrada.
4. **Atajo “llevar al próximo orden del día”** visible directamente en lista de tareas.
5. **Estados visuales más fuertes** (chips por urgencia + antigüedad de bloqueo).

## 4.2 Impacto alto / esfuerzo medio
1. **Modelo de Acuerdo/Decisión** con responsable, fecha objetivo, estado y enlace a tareas.
2. **Detección de conflictos de agenda** (solape temporal de asistentes clave y reuniones).
3. **Vista de continuidad entre reuniones**: pendientes heredados, acuerdos abiertos, tareas críticas.
4. **Alertas programadas** (correo/in-app) por vencimientos y bloqueos.
5. **Dashboard por rol** (admin/coordinación/participante) orientado a acciones.

## 4.3 Mejoras estructurales profundas
1. **Motor de flujo político-operativo**: decisión ↔ acuerdo ↔ tarea ↔ seguimiento ↔ cierre.
2. **Permisos por ámbito territorial/área** (no solo rol global).
3. **Capa territorial** (barrios/distritos) para agenda, tareas y compromisos.
4. **Modelo de stakeholders externos** (entidades, contactos clave, compromisos abiertos).

---

## 5) Quick wins

- Simplificar formulario de tarea inicial a: título, responsable, fecha límite, prioridad, origen.
- Plantillas de orden del día por tipo de reunión.
- Campo “decisión requerida” en punto de orden del día con semáforo en reunión.
- Campo “resultado político” en cierre de acto.
- Filtro “sin movimiento en 7/14 días” en tareas.
- Acceso rápido en dashboard a “mis 5 bloqueos principales”.
- Wizard de cierre de reunión en 3 pasos: acuerdos, tareas, pendientes para siguiente.

---

## 6) Riesgos funcionales si se mantiene el diseño actual

1. **Adopción parcial:** el equipo volverá a WhatsApp/hojas para lo crítico.
2. **Dependencia de una persona experta:** riesgo de “single point of failure” operativo.
3. **Pérdida de trazabilidad política:** decisiones relevantes quedan en texto libre y conversaciones externas.
4. **Fatiga administrativa:** exceso de campos reduce calidad de datos y puntualidad de registro.
5. **Baja capacidad de anticipación:** sin alertas ni conflictos, se detectan problemas demasiado tarde.
6. **Escalabilidad limitada:** al crecer el equipo/territorio, el rol global no será suficiente.

---

## 7) Oportunidades no cubiertas (producto de campaña)

- Seguimiento formal de compromisos políticos por tema/territorio.
- Gestión de incidencias (acto, logística, comunicación, reputación).
- Banco de materiales (argumentarios, creatividades, guiones, actas modelo).
- Diferenciación entre responsables políticos y orgánicos/operativos.
- Control de asistencia más rico (confirmado, asistió, puntualidad, rol en acto).
- Historial de decisiones con impacto y evaluación posterior.
- Alertas y recordatorios automáticos (antes de reunión/acto y para tareas críticas).
- Preparación logística estructurada por checklist.
- Relación explícita entre tarea y decisión política subyacente.
- Seguimiento por barrios/distritos y entidades colaboradoras.

---

## 8) Roadmap propuesto (3 fases)

## Fase 1 — mejoras inmediatas (4-6 semanas)
- Formularios rápidos de reunión/tarea.
- Cierre post-acto mínimo.
- Alertas visuales básicas en dashboard.
- Plantillas de orden del día.

## Fase 2 — consolidación funcional (6-10 semanas)
- Entidad Acuerdo/Decisión.
- Continuidad entre reuniones (vista consolidada).
- Detección de solapamientos agenda.
- Alertas automáticas por vencimiento/bloqueo.

## Fase 3 — evolución de producto (10-16 semanas)
- Permisos por territorio/área.
- Capa territorial y stakeholders externos.
- Dashboard estratégico político-operativo.
- Métricas de ejecución y trazabilidad de decisiones.

---

## 9) Nota metodológica

Este diagnóstico se basa en análisis de estructura Django (modelos, vistas, formularios, plantillas, navegación y permisos) y reconstrucción de flujos de uso reales desde código y UI server-rendered. Cuando hay inferencias de comportamiento de equipo, se consideran hipótesis razonables para una campaña municipal/territorial y se han marcado implícitamente en el diagnóstico de riesgos/adopción.
