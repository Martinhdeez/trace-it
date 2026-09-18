# Tareas de Mateo: motor de decisiones y ciclo de vida de las reglas

## Antes de empezar
- Parte de `dev` una vez unido el PR del esqueleto (`feat/esqueleto-backend`): `git switch dev && git pull`.
- Lee `docs/guia-equipo.md` (git y estructura) y de `docs/plano-aplicacion.md`: 3.6, 3.7, 3.8, P3, P7, P14, P15, P18, P19, P21.

## Tu zona
`backend/app/features/reglas/`, `features/decisiones/`, `features/procesos/`, `features/usuarios/`.
No tocas `features/agentes/` (Martín) ni `features/ingesta/`, `extraccion/`, `fuentes/` (Álvaro).

## Contrato que usas de Martín
```python
agentes.sandbox.ejecutar(codigo, instancia, fuentes, otras) -> {"salta": bool, "motivo": str}
```
Lanza excepción ante cualquier error. Hasta que esté hecho, en tus tests usa un ejecutor falso (una función que recibe el código y devuelve el resultado).

## Tareas (en orden, cada una en su rama y su PR a `dev`)

### 1. `feat/motor` — `features/decisiones/motor.py`
Función pura, sin base de datos ni LLM:
```python
decidir(reglas, prioridades: dict[str, int], por_defecto: str,
        instancia: dict, fuentes: dict, otras: list[dict], ejecutar) -> Veredicto
```
- Ejecuta **todas** las reglas activas, cada una con `codigo_a` y `codigo_b`.
- Si las dos versiones discrepan o alguna falla: `REVISION` con motivo. Nunca decide sin esa regla.
- Si no salta ninguna: `por_defecto`. Si saltan varias: gana la de mayor prioridad.
- El veredicto incluye el resultado de cada regla (id, hash, salta, motivo) y el hash del conjunto de reglas.
- Tests: ninguna salta; varias saltan y gana la prioridad; discrepancia A/B a `REVISION`; excepción a `REVISION`.

### 2. `feat/decisiones-api` — servicio y endpoints
- `POST /procesos/{id}/ejecutar`: para cada instancia `PENDIENTE` con símbolos, llama al motor con las fuentes vigentes (última carga por nombre). Guarda una fila en `decisiones` (autor `motor`) o pasa la instancia a `REVISION`. Devuelve el recuento por decisión.
- `GET /procesos/{id}/instancias?estado=` y `GET /instancias/{id}`. El detalle incluye símbolos, el histórico de decisiones con el resultado de cada regla y los eventos.
- `GET /procesos/{id}/cola`: instancias en `REVISION` más las que tienen una decisión cuyo tipo tiene `requiere_persona`. Filtro opcional `?tipo=`. Ningún nombre de decisión fijo en el código: los tipos son del proceso (`TipoDecision.requiere_persona`, añadido en el PR #5).
- `POST /instancias/{id}/resolver` con `{decision, motivo}`: decisión nueva con autor = usuario actual. El histórico solo añade filas, nunca edita.
- `GET /procesos/{id}/exportar`: una línea por instancia con su nombre y su decisión. El formato del reto (`outcomes.jsonl`) es `{"file_id": nombre, "result": decisión}`; el código no sabe nada de facturas, solo usa esos dos nombres de campo. Devuelve 409 si queda alguna instancia `PENDIENTE` o en `REVISION`.
  - **Qué decisión se exporta [DECIDIDO]:** la última decisión del **motor**. Las decisiones de una persona llevan un tipo: `resolucion` (resuelve un caso cuyo tipo tiene `requiere_persona`; nunca cambia lo exportado, P4) o `correccion_revision` (corrige una instancia que estaba en `REVISION`; se exporta si no hay decisión del motor).
  - **Nombres repetidos [DECIDIDO]:** se exporta solo la instancia más reciente de cada `nombre` y se avisa si había repetidos.
  - Hecho en `fix/exportar-decision-motor` (`Decision.tipo_humana`, cabecera `X-Nombres-Repetidos`).

### 3. `feat/auditoria` — `features/decisiones/auditoria.py` + comprobación al activar
- `comprobar(session, proceso_id, regla_nueva)` vuelve a ejecutar las reglas activas + la nueva sobre los símbolos guardados de todas las instancias decididas. No relee PDFs ni llama al ERP.
- Clasifica cada instancia en tres grupos:
  - sin cambio;
  - cambio (una decisión del motor que cambiaría);
  - conflicto (contradice una decisión validada por una persona).
- Para cada decisión pasada que cambiaría, genera un hallazgo con la decisión registrada y la que saldría ahora (en facturas: pagada indebidamente, no pagada debiendo). Ningún nombre de decisión fijo en el código. Nunca modifica el pasado.
- `reglas.service.activar` lo usa: si hay conflictos, 409 y la regla no entra.
- `GET /procesos/{id}/hallazgos`.

### 4. ~~`feat/seed-facturas`~~ — hecho
Lo cubre el setup rápido (PR #11): `procesos/pago-facturas.json` + `make setup`.

## Criterio de hecho en cada PR
- `uv run ruff check .` y `uv run pytest` en verde.
- Endpoints visibles en `/docs`.
- Otra persona lo revisa antes del squash merge.

Si cambias un modelo compartido (`reglas`, `decisiones`, `instancias`), genera la migración con `alembic revision --autogenerate` y avisa en el grupo.
