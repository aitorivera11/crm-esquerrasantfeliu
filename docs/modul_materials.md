# Mòdul de Material i Inventari (proposta funcional)

## 1) Objectiu del mòdul

Crear un mòdul únic per gestionar **compres**, **inventari**, **ubicacions** i **ús de material en actes/tasques**.
Ha de permetre treball ràpid des de mòbil (captura de codi de barres i foto), però mantenint traçabilitat (qui compra, cost, on és cada element i en quin estat està).

---

## 2) Principis de disseny

1. **Alta velocitat de registre**
   - Flux “ràpid” per inventariar en 20-30 segons.
   - Flux “complet” per compres amb factura/ticket.

2. **Traçabilitat sense fricció**
   - Històric de moviments (canvis d’ubicació, préstecs, baixes).
   - Vincle amb usuari responsable i data.

3. **Integració amb el “Todo” del CRM**
   - Relació nativa amb `agenda.Acte`.
   - Relació nativa amb `reunions.Tasca`.
   - Possibilitat de crear compra o item des d’una tasca de tipus “Comprar material”.

4. **Inventari útil (no només catàleg)**
   - Diferenciar **consumible** vs **inventariable**.
   - Informar quantitat disponible, mínims i alertes de reposició.

---

## 3) Estructura conceptual

### 3.1 Entitats principals

- **CategoriaMaterial**
  - Exemples: Consumibles, Inventariables, Merchandising, Material de paradeta, Oficina, Audiovisual.
  - Permetre jerarquia (pare/fill) per no quedar-se curt.

- **UbicacioMaterial**
  - Tipus: casa militant, local, despatx ajuntament, magatzem, armari, vehicle, “en préstec”.
  - Camps clau: nom, adreça/notes, responsable per defecte, activa/inactiva.

- **CompraMaterial**
  - Grup de línies d’una compra real.
  - Camps: data compra, proveïdor, pagador (usuari o entitat), cost total, mètode pagament, núm. factura/ticket, fitxer adjunt.

- **LiniaCompraMaterial**
  - Producte concret dins una compra.
  - Camps: descripció, quantitat, preu unitari, IVA, total línia, codi de barres (opcional), foto (opcional), categoria.

- **ItemMaterial (inventariable)**
  - Unitat traçable (carpa #1, rollup #2, megàfon #1...).
  - Camps: codi intern, estat (operatiu, reparació, baixa), ubicació actual, data alta, valor estimat.

- **StockMaterial (consumible)**
  - Stock agregat per producte+ubicació.
  - Camps: quantitat actual, unitat (u, capsa, metre, kg), llindar mínim.

- **MovimentMaterial**
  - Qualsevol canvi: entrada, sortida, trasllat, ajust inventari, préstec, devolució, baixa.
  - Camps: tipus moviment, data, origen, destí, quantitat, observacions, actor.

- **AssignacioMaterial**
  - Vincle de material amb un acte o tasca.
  - Camps: objecte referenciat (`acte` o `tasca`), quantitat reservada, quantitat retornada, estat reserva.

---

## 4) Funcionalitats clau

### 4.1 Alta de compra (mode complet)

Flux:
1. Crear compra (capçalera) amb pagador, import i document.
2. Afegir línies (manual o escanejant codi de barres).
3. Per cada línia, decidir si genera:
   - stock consumible, o
   - items inventariables (N unitats).
4. Registrar entrada automàtica a ubicació inicial.

### 4.2 Alta independent d’inventari (mode ràpid)

Pensat per “inventariar el local”:
- Crear producte/item sense compra associada.
- Entrada ràpida de múltiples unitats.
- Codi intern autogenerat (p.ex. `INV-CARPA-0007`).

### 4.3 Escaneig de codi de barres amb mòbil

- Botó “Escanejar” al formulari de línia de compra o fitxa de material.
- Ús de càmera via navegador (PWA/web responsive).
- Proposta tècnica:
  - primer intent amb `BarcodeDetector` (si el navegador ho suporta),
  - fallback JS amb llibreria (ex. ZXing) per compatibilitat.
- Quan detecta codi:
  - autocompleta camp EAN/UPC,
  - si ja existeix producte, suggereix reutilitzar-lo.

### 4.4 Fotos del material

- Permetre 1+ fotos per producte/item (estat real, identificació ràpida).
- Captura directa des de mòbil i galeria.
- Miniatura a llistats per trobar ràpidament carpes, rollups, cables, etc.

### 4.5 Ubicacions i mapatge real

- Camp d’ubicació actual obligatori per inventariables.
- Historial “on ha estat” (moviments).
- Cerca per ubicació: “què hi ha a l’armari X?”.

### 4.6 Préstecs i retorns

- “Prestar a persona/entitat” amb data prevista de retorn.
- Estat pendent/retornat/retard.
- Alertes de retorn pendent.

### 4.7 Consumibles i reposició

- Descompte de stock quan s’usa en acte/tasca.
- Alertes si baixa de mínim.
- Vista “llista de compra suggerida”.

### 4.8 Relació amb actes i tasques

- Des d’un **acte**:
  - reservar material (carpes, taules, flyers),
  - veure check-list de sortida/retorn.
- Des d’una **tasca**:
  - tasca “Comprar rollup” → al marcar compra, crear `CompraMaterial` i línies.
  - tasca “Preparar paradeta” → reservar material i deixar traça.

---

## 5) Vistes/UI recomanades

1. **Dashboard Material**
   - stock crític, préstecs pendents, compres recents, material més utilitzat.

2. **Llistat Material** (filtres potents)
   - per categoria, tipus (consumible/inventariable), ubicació, estat, etiqueta.

3. **Compres**
   - llistat + detall compra amb línies, import i document.

4. **Inventari físic**
   - mode recompte (quantitat comptada vs sistema, generar ajust).

5. **Calendari de reserves**
   - veure conflictes (mateixa carpa reservada en dos actes alhora).

---

## 6) Dades mínimes i dades avançades

### MVP (curt termini)
- Categories.
- Ubicacions.
- Compra + línies + adjunt.
- Item inventariable i stock consumible.
- Moviments bàsics (entrada/sortida/trasllat).
- Vincle amb acte/tasca.
- Escaneig de codi de barres (1r tall funcional).
- Foto principal.

### Fase 2
- Préstecs amb alertes.
- Recompte inventari assistit.
- Alertes de stock mínim i proposta de compra.
- Múltiples fotos i etiquetes avançades.

### Fase 3
- KPI de costos per tipus d’acte.
- Predicció simple de consum (històric).
- QR intern per inventariables (enganxina pròpia del partit).

---

## 7) Regles de negoci importants

1. Tot moviment ha de deixar històric (immutable a nivell funcional).
2. Inventariable no pot estar a dues ubicacions alhora.
3. Consumible no pot baixar de 0 (excepte ajust explícit amb motiu).
4. Si una reserva d’acte supera stock disponible, avisar abans de confirmar.
5. En tancar acte, proposar devolució automàtica del material reservat.

---

## 8) Permisos i rols

- **Administració**: gestió completa (inclòs ajust inventari i baixa patrimonial).
- **Coordinació**: crear compres, moure material, reservar per actes/tasques.
- **Participant**: consulta limitada (què portar a l’acte, estat de reserva assignada).

Permisos granulars suggerits:
- `material.add_compra`, `material.change_compra`, `material.view_costs`.
- `material.adjust_stock`.
- `material.manage_loans`.
- `material.assign_to_events_tasks`.

---

## 9) Integració tècnica amb el projecte actual

1. **Nova app Django**: `material`.
2. Reutilitzar patrons de `reunions`:
   - formulari ràpid + formulari complet,
   - adjunts,
   - traçabilitat i historial.
3. Relacions:
   - FK/M2M amb `agenda.Acte`.
   - FK/M2M amb `reunions.Tasca`.
4. UI coherent amb templates existents i sidebar amb entrada “Material”.

---

## 10) Fluxos d’usuari prioritaris (els 5 que donen valor ràpid)

1. **Compra amb ticket + codi de barres + foto** (mòbil).
2. **Inventari ràpid del local** (alta independent).
3. **Traslladar material entre ubicacions**.
4. **Reservar material per un acte**.
5. **Crear compra des d’una tasca i deixar-la vinculada**.

---

## 11) Suggeriments per millorar encara més

- **Etiquetes lliures** (ex. `campanya-2027`, `sant-jordi`, `fragil`).
- **Estat de manteniment** per inventariables (OK, revisar, reparar, fora de servei).
- **Pack de material** (kit paradeta: carpa + taula + estovalles + flyers).
- **Camp “criticitat”** per saber què no pot faltar en un acte.
- **Export CSV** per quadrar comptabilitat i auditories.

---

## 12) Proposta de següent pas (execució)

Per començar sense sobrecarregar:

### Sprint 1 (MVP real)
- Models bàsics + admin.
- CRUD de categories, ubicacions, compres i línies.
- Alta d’inventariable/consumible.
- Adjunt de ticket/factura.
- Vinculació amb acte/tasca.

### Sprint 2 (mòbil i operativa)
- Escaneig de codi de barres.
- Captura de fotos des de mòbil.
- Moviments i trasllats.
- Reserva de material per actes.

### Sprint 3 (control i qualitat)
- Alertes stock mínim.
- Préstecs i devolucions.
- Recompte inventari i ajustos.
- Dashboard i KPI bàsics.

Aquesta seqüència dona valor des de la primera iteració i evita construir un ERP massa pesat.
