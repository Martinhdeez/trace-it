# Trace Pay

Aplicación para convertir documentos y fuentes de referencia en decisiones auditables. Diseño: [plano](docs/plano-aplicacion.md), [MVP](docs/plan-mvp.md) y [guía del equipo](docs/guia-equipo.md).

Esta rama implementa la **ingesta de PDF y Excel**: extracción con evidencia, OCR local, normalización y API FastAPI. Las decisiones de pago pertenecen al motor de reglas.

## Arranque

Desde la raíz, con Python 3.12 y uv:

```powershell
cd backend
uv sync --locked --group dev
uv run python -m app.features.ingestion.tools.download_models
uv run uvicorn app.features.ingestion.application:create_app --factory --host 127.0.0.1 --port 8000 --workers 1
```

Abrir <http://127.0.0.1:8000/docs>. PDF nativo y Excel funcionan sin descargar modelos. La ingesta independiente no necesita Postgres. El backend general de dev se conserva: `uvicorn app.main:app` arranca sus routers; la ingesta aún no está conectada a sus procesos e instancias.

## Organización por funcionalidades

```text
backend/
  pyproject.toml, uv.lock
  app/
    main.py                  # FastAPI entry point
    common/                  # shared evidence, normalization and errors
    features/
      ingestion/
        router.py, schemas.py # HTTP interface and contracts
        service.py, store.py  # orchestration, cache and jobs
        pdf/, ocr/           # readers and providers
        tests/, tools/       # regression tests and experiments
      sources/
        service.py, excel.py # structured Excel extraction
        config.py, tests/
docs/ingesta/                # usage, integration, measurements and limits
```

- [Guía de ingesta](docs/ingesta/README.md)
- [Contrato HTTP y ejemplos](docs/ingesta/api.md)
- [Integración y diferencias pendientes con dev](docs/ingesta/architecture.md)
- [Validación y límites conocidos](docs/ingesta/extraction-validation.md)
- [Comparación real de Gemini, OCR local y GOT](docs/ingesta/gemini-ocr.md)
- [Contribuir y comprobar cambios](CONTRIBUTING.md)

El material oficial se conserva como submódulo en `.context/500-sombras-de-alberto`. Modelos, credenciales, resultados de ejecución y datos locales están excluidos de Git.
