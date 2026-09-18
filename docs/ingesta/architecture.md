# Integración de la ingesta

## Alcance

La referencia es [la guía del equipo](../guia-equipo.md). `backend/app/features/ingesta/` contiene recepción, PDF, OCR, cola y evidencia. `features/fuentes/` contiene Excel y su servicio público. Cada funcionalidad conserva sus tests. Evidencia, normalización y errores comunes viven en `app/common/`.

El router valida y llama al servicio. `ingesta.service` consume `fuentes.service`, sin importar routers ajenos. `app/main.py` expone la aplicación local; `ingesta.application.create_app` concentra composición y ciclo de vida para la integración posterior.

`ingesta/pdf/invoice.py` es un adaptador determinista de campos de factura de los formatos observados. No implementa los símbolos genéricos por proceso de `features/extraccion/`. Conserva texto completo y evidencia para esa integración.

## Flujo y estado

Archivo → límite y tipo → objeto inmutable SHA-256 → caché versionada → lector PDF o Excel → campos y evidencia → resultado persistido.

PDF usa texto nativo primero. Las páginas sin texto fiable activan OCR local. Los escaneos que parecen completos reciben una lectura local de contraste. La visión opcional propone valores pendientes sin verificarlos. OCR nunca decide PAGAR, NO_PAGAR o ESCALAR.

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
4. **Contratos compartidos:** `app/main.py`, `app/common/` y las rutas HTTP se presentan para revisión. No hay Docker, ERP, autenticación ni migraciones en esta entrega.
5. **Calidad OCR:** quedan errores observados en documentos pendientes. Las referencias visuales requieren validación humana independiente.

Corresponde publicar `data-ingestion` y revisar un PR contra `dev`, sin push directo ni integración automática. El nombre de esta rama se conserva por instrucción del usuario; para nuevas ramas la guía recomienda `feat/<funcionalidad>`. El equipo decide el squash al integrar.

## Prácticas consultadas

- [FastAPI: varios archivos](https://fastapi.tiangolo.com/tutorial/bigger-applications/): router montable y composición separada.
- [Ruff: formato](https://docs.astral.sh/ruff/formatter/) y [configuración](https://docs.astral.sh/ruff/configuration/): configuración versionada, imports ordenados y comprobación automática.
- [PyPA: src y flat layout](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/): se evaluó `src`; prevalece `backend/app` según el equipo, con instalación editable y lockfile.

Formato: cuatro espacios, comillas dobles, 110 columnas y LF. `.editorconfig`, `.gitattributes` y Ruff mantienen el criterio entre Windows y CI.
