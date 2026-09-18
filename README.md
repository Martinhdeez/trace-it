# Trace Pay

Aplicación para convertir documentos y fuentes de referencia en decisiones auditables. Diseño: [plano](docs/plano-aplicacion.md), [MVP](docs/plan-mvp.md) y [guía del equipo](docs/guia-equipo.md).

Esta rama implementa la **ingesta de PDF y Excel**: extracción con evidencia, OCR local, normalización y API FastAPI. Las decisiones de pago pertenecen al motor de reglas.

## Arranque

Desde la raíz, con Python 3.12 y uv:

```powershell
cd backend
uv sync --locked --group dev
uv run python -m app.features.ingesta.tools.download_models
uv run uvicorn app.features.ingesta.application:create_app --factory --host 127.0.0.1 --port 8000 --workers 1
```

Abrir <http://127.0.0.1:8000/docs>. PDF nativo y Excel funcionan sin descargar modelos. La ingesta independiente no necesita Postgres. El backend general de dev se conserva: `uvicorn app.main:app` arranca sus routers; la ingesta aún no está conectada a sus procesos e instancias.

## Organización por funcionalidades

```text
backend/
  pyproject.toml, uv.lock
  app/
    main.py                  # entrada de FastAPI
    common/                  # evidencia, normalización y errores compartidos
    features/
      ingesta/
        router.py, schemas.py # interfaz HTTP y contratos
        service.py, store.py  # orquestación, caché y trabajos
        pdf/, ocr/           # lectores y proveedores
        tests/, tools/       # regresión y experimentos
      fuentes/
        service.py, excel.py # lectura estructural de Excel
        config.py, tests/
docs/ingesta/                # uso, integración, mediciones y límites
```

- [Guía de ingesta](docs/ingesta/README.md)
- [Contrato HTTP y ejemplos](docs/ingesta/api.md)
- [Integración y diferencias pendientes con dev](docs/ingesta/architecture.md)
- [Validación y límites conocidos](docs/ingesta/extraction-validation.md)
- [Comparación real de Gemini, OCR local y GOT](docs/ingesta/gemini-ocr.md)
- [Contribuir y comprobar cambios](CONTRIBUTING.md)

El material oficial se conserva como submódulo en `.context/500-sombras-de-alberto`. Modelos, credenciales, resultados de ejecución y datos locales están excluidos de Git.
