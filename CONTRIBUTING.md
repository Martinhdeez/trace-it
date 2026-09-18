# Contribuir

La [guía del equipo](docs/guia-equipo.md) define ramas, responsables y estructura. Partir de `dev`, trabajar por funcionalidad y abrir un PR contra `dev`. Nunca hacer push directo a `dev` o `main`. Otra persona revisa y aprueba; se integra con squash.

## Cambios pequeños y verificables

- Un commit representa un comportamiento o cambio coherente, con sus pruebas cuando correspondan. Usar Conventional Commits, por ejemplo `fix(ingestion): preserve ambiguous OCR candidates`.
- Use English for new package and file names, identifiers, comments, docstrings and developer messages. Preserve source-language document text, parser labels and test fixtures when they are input data or evidence.
- Conservar los tests dentro de `backend/app/features/<funcionalidad>/tests/` y el router separado del servicio.
- Mantener evidencia original al normalizar. Un valor ilegible no se completa con el resultado esperado de otra fuente.
- Documentar en `docs/` cambios de contrato, configuración, límites y resultados de evaluación.
- Coordinar contratos compartidos y carpetas de otra persona según la guía antes de integrar.
- Dependencias y modelos deben tener versiones reproducibles. El lockfile y las referencias de evaluación se revisan en commits separados del código cuando su tamaño lo aconseje.

## Comprobaciones

Desde `backend/`:

```powershell
uv sync --locked --group dev
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
```

La suite general incluye pruebas de procesos que necesitan Postgres y el entorno indicado en la guía. Para comprobar esta entrega aisladamente: `uv run pytest -q app/features/ingestion/tests app/features/sources/tests`. La prueba asíncrona de procesos de dev falla actualmente con ProactorEventLoop en Windows; no está oculta ni modificada por la ingesta.

Para aplicar formato: `uv run ruff format .`. Ruff y `.editorconfig` fijan espaciado, imports y finales de línea. No reformatear archivos ajenos como efecto secundario de una feature.

CI ejecuta lint, formato y tests sin pesos ni credenciales en Windows y Linux. La regresión real OCR se ejecuta localmente con los pesos y el submódulo; no equivale a una validación humana del corpus. Los experimentos remotos se lanzan explícitamente y pueden consumir saldo.

Antes de subir:

```powershell
git fetch origin dev
git rebase origin/dev
git diff --check
git status --short
git push -u origin BRANCH-NAME
```

Repetir las comprobaciones si el rebase cambia código. Las claves van en `.env`; los informes, objetos y modelos permanecen ignorados. Un PR debe explicar comportamiento, validación y diferencias de integración pendientes.
