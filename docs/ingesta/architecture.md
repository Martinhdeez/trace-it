# Integración de la ingesta

## Alcance

La referencia es [la guía del equipo](../guia-equipo.md). `backend/app/features/ingestion/` contiene recepción, PDF, OCR, cola y evidencia. `features/sources/` contiene Excel y su servicio público. Cada funcionalidad conserva sus tests. Evidencia, normalización y errores comunes viven en `app/common/`.

Los paquetes añadidos en `data-ingestion` usan nombres en inglés. Los modelos PostgreSQL previos siguen en `features/ingesta/model.py` y `features/fuentes/model.py`, con sus imports y contratos originales. Este cambio de nombres no migra tablas ni modifica la API previa de la aplicación.

El router valida y llama al servicio. `ingestion.service` consume `sources.service`, sin importar routers ajenos. `app/main.py` conserva el arranque general de dev. `ingestion.application.create_app` ofrece la API independiente con composición y ciclo de vida propios; sus rutas aún no están montadas en la aplicación general.

`ingestion/pdf/invoice.py` es un adaptador determinista de campos de factura de los formatos observados. No implementa los símbolos genéricos por proceso de `features/extraccion/`. Conserva texto completo y evidencia para esa integración.

## Flujo y estado

Archivo → límite y tipo → objeto inmutable SHA-256 → caché versionada → lector PDF o Excel → campos y evidencia → resultado persistido.

PDF usa texto nativo primero. Las páginas sin texto fiable activan OCR local. Toda página que necesita OCR recibe dos lecturas locales, aunque la primera esté incompleta. Los campos pendientes activan el lector visual configurado y después el juez textual Jev. El comité conserva candidatos y solo acepta corroboración sin conflictos; Jev recomienda, pero no añade un voto visual. Ver [política del comité](committee.md). OCR nunca decide PAGAR, NO_PAGAR o ESCALAR.

SQLite WAL guarda resultados y cola; los originales permanecen en disco. Un proceso Uvicorn mantiene trabajadores acotados y recupera trabajos interrumpidos. Identidad documental y hash se separan: reutilizar procesamiento no elimina documentos.

## Decisiones

| Decisión | Alternativa | Consecuencia y evidencia |
|---|---|---|
| Estructura por funcionalidades del equipo | Paquete independiente `src/tracepay` | Facilita integrar ingesta y fuentes; tests junto a cada feature. |
| Texto nativo y celdas antes de OCR | Pasar todo por modelos | 471 PDF nativos sin OCR; otros formatos pueden necesitar un adaptador. |
| Conservar candidatos y originales | Completar valores ilegibles con el maestro | Más revisiones, sin fabricar IBAN ni dígitos; pruebas de discrepancia. |
| Cola persistente local durante desarrollo | Añadir ya Postgres y cola distribuida | Recuperación probada; no permite múltiples nodos ni implementa la persistencia del producto. |

## Antes de integrar en dev

1. **Persistencia:** el plano prevé SQLAlchemy, sesiones y Alembic sobre Postgres. Hay que acordar la integración de esta cola SQLite aislada.
2. **Extracción:** P20 pide dos extracciones LLM independientes por proceso. Esta entrega implementa la cascada determinista solicitada y un adaptador visual opcional; no cumple todavía P20.
3. **Estados y nombres:** falta acordar la traducción de `COMPLETE`/`NEEDS_REVIEW` a instancias y `REVISION`. Los campos técnicos actuales están en inglés y no sustituyen los símbolos configurables por proceso.
4. **Contratos compartidos:** Se conservan `app/main.py`, los errores comunes y las migraciones de dev. La API de ingesta queda separada, pendiente de vinculación a procesos/instancias y autenticación; ERP no está implementado en esta feature.
5. **Calidad OCR:** quedan errores observados en documentos pendientes. Las referencias visuales requieren validación humana independiente.

Corresponde publicar `data-ingestion` y revisar un PR contra `dev`, sin push directo ni integración automática. El nombre de esta rama se conserva por instrucción del usuario; para nuevas ramas la guía recomienda `feat/<funcionalidad>`. El equipo decide el squash al integrar.

## Prácticas consultadas

- [FastAPI: varios archivos](https://fastapi.tiangolo.com/tutorial/bigger-applications/): router montable y composición separada.
- [Ruff: formato](https://docs.astral.sh/ruff/formatter/) y [configuración](https://docs.astral.sh/ruff/configuration/): configuración versionada, imports ordenados y comprobación automática.
- [PyPA: src y flat layout](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/): se evaluó `src`; prevalece `backend/app` según el equipo, con instalación editable y lockfile.

Formato: cuatro espacios, comillas dobles, 100 columnas y LF. `.editorconfig`, `.gitattributes` y Ruff mantienen el criterio entre Windows y CI.
