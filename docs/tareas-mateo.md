# Tareas de Mateo: motor de decisiones y ciclo de vida de las reglas

## Antes de empezar
- Parte de `dev` una vez unido el PR del esqueleto (`feat/esqueleto-backend`): `git switch dev && git pull`.
- Lee `docs/guia-equipo.md` (git y estructura) y de `docs/plano-aplicacion.md`: 3.6, 3.7, 3.8, P3, P7, P14, P15, P18, P19, P21.

## Tu zona
`backend/app/features/rules/`, `features/decisions/`, `features/processes/`, `features/users/`.
No tocas `features/agents/` (Martín) ni `features/ingestion/`, `extraction/`, `sources/` (Álvaro).

## Contrato que usas de Martín
```python
agents.sandbox.run(code, instance, sources, others) -> {"fires": bool, "reason": str}
```
Lanza excepción ante cualquier error. Hasta que esté hecho, en tus tests usa un ejecutor falso (una función que recibe el código y devuelve el resultado).

## Tareas (en orden, cada una en su rama y su PR a `dev`)

### 1. `feat/motor` — `features/decisions/engine.py`
Función pura, sin base de datos ni LLM:
```python
decide(rules, priorities: dict[str, int], default: str, escalate: str,
       instance: dict, sources: dict, others: list[dict], run) -> Verdict
```
- Ejecuta **todas** las reglas activas, cada una con `code_a` y `code_b`.
- Si las dos versiones discrepan o alguna falla: `REVIEW` con motivo. Nunca decide sin esa regla.
- Si no salta ninguna: `default`. Si saltan varias: gana la de mayor prioridad.
- El veredicto incluye el resultado de cada regla (`rule_id`, `hash`, `fires`, `reason`) y el hash del conjunto de reglas.
- Tests: ninguna salta; varias saltan y gana la prioridad; discrepancia A/B a `REVIEW`; excepción a `REVIEW`.

### 2. `feat/decisiones-api` — servicio y endpoints
- `POST /processes/{id}/run`: para cada instancia `PENDING` con símbolos, llama al motor con las fuentes vigentes (última carga por nombre). Guarda una fila en `decisions` (`author` = `engine`) o pasa la instancia a `REVIEW`. Devuelve el recuento por decisión.
- `GET /processes/{id}/instances?status=` y `GET /instances/{id}`. El detalle incluye símbolos, el histórico de decisiones con el resultado de cada regla y los eventos.
- `GET /processes/{id}/queue`: instancias en `REVIEW` más las que tienen una decisión cuyo tipo tiene `requires_human`. Filtro opcional `?type=`. Ningún nombre de decisión fijo en el código: los tipos son del proceso (`DecisionType.requires_human`, añadido en el PR #5).
- `POST /instances/{id}/resolve` con `{decision, reason}`: decisión nueva con autor = usuario actual. El histórico solo añade filas, nunca edita.
- `GET /processes/{id}/export`: una línea por instancia con su nombre y su decisión. El formato del reto (`outcomes.jsonl`) es `{"file_id": nombre, "result": decisión}`; el código no sabe nada de facturas, solo usa esos dos nombres de campo. Devuelve 409 si queda alguna instancia `PENDING` o en `REVIEW`.
  - **Qué decisión se exporta [DECIDIDO]:** la última decisión del **motor**. Las decisiones de una persona llevan un tipo: `resolution` (resuelve un caso cuyo tipo tiene `requires_human`; nunca cambia lo exportado, P4) o `review_correction` (corrige una instancia que estaba en `REVIEW`; se exporta si no hay decisión del motor).
  - **Nombres repetidos [DECIDIDO]:** se exporta solo la instancia más reciente de cada `name` y se avisa si había repetidos.
  - Hecho en `fix/exportar-decision-motor` (`Decision.human_kind`, cabecera `X-Duplicate-Names`).

### 3. `feat/auditoria` — `features/decisions/audit.py` + comprobación al activar
- `audit.check(session, process_id, proposed)` vuelve a ejecutar las reglas activas + la nueva sobre los símbolos guardados de todas las instancias decididas. No relee PDFs ni llama al ERP.
- Clasifica cada instancia en tres grupos:
  - sin cambio;
  - cambio (una decisión del motor que cambiaría);
  - conflicto (contradice una decisión validada por una persona).
- Para cada decisión pasada que cambiaría, genera un hallazgo (`Finding`) con la decisión registrada y la que saldría ahora (en facturas: pagada indebidamente, no pagada debiendo). Ningún nombre de decisión fijo en el código. Nunca modifica el pasado.
- `rules.service.activate` (y `retire`) lo usa: si hay conflictos, 409 y la regla no entra.
- `GET /processes/{id}/findings` y `GET /rules/{id}/impact`.

### 4. ~~`feat/seed-facturas`~~ — hecho
Lo cubre el setup rápido (PR #11): `processes/invoice-payment.json` + `make setup`.

## Criterio de hecho en cada PR
- `uv run ruff check .` y `uv run pytest` en verde.
- Endpoints visibles en `/docs`.
- Otra persona lo revisa antes del squash merge.

Si cambias un modelo compartido (`rules`, `decisions`, `instances`), genera la migración con `alembic revision --autogenerate` y avisa en el grupo.
