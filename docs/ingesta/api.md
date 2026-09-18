# API de ingesta

Desde `backend/`: `uv run uvicorn app.features.ingesta.application:create_app --factory --host 127.0.0.1 --port 8000 --workers 1`.

Swagger en `/docs`, referencia en `/redoc` y contrato en `/openapi.json`. Rutas agrupadas bajo `Ingestion`.

## Extraer un documento

```powershell
curl.exe http://127.0.0.1:8000/v1/extractions -F "file=@../.context/500-sombras-de-alberto/facturas/scan_001.pdf"
curl.exe http://127.0.0.1:8000/v1/extractions -F "file=@../.context/500-sombras-de-alberto/FINAL_v7_DEFINITIVO_ahorasi.xlsx"
```

Multipart: `file` obligatorio, `ocr=true` y `vlm=false` opcionales. No se pide moneda, NIF ni otro campo que deba leerse del documento. Hasta 25 MiB por archivo. Un `200` devuelve:

- `id`, `file_id`, `sha256`: identidad de esta ingesta y contenido original.
- `kind`: `invoice` o `workbook`.
- `status`: `COMPLETE` o `NEEDS_REVIEW`; ninguno es una decisión de pago.
- `fields`: valores normalizados, estados y candidatos con texto, página y coordenadas.
- `data`: hojas/celdas de Excel, propuestas visuales y procedencia del procesamiento.
- `warnings`, `pages`, `metrics`, `pipeline_version`, `cache_hit`.

Los importes son cadenas decimales. `OBSERVED` es una observación que puede contener errores OCR. Un candidato generativo queda `UNVERIFIED`. Excel conserva hoja, celda, fórmula, caché de fórmula y formato numérico.

`GET /v1/extractions/{id}` recupera el resultado persistido. Subir contenido idéntico con otro nombre reutiliza la extracción y conserva otra identidad documental; no deduplica facturas a efectos de pago.

## Procesar un lote

```powershell
curl.exe http://127.0.0.1:8000/v1/batches -F "files=@primera.pdf" -F "files=@segunda.pdf"
curl.exe http://127.0.0.1:8000/v1/batches/IDENTIFICADOR
```

El POST admite hasta 100 archivos, rechaza nombres repetidos y responde `202` con `id`, `files` y `status_url`. La consulta devuelve trabajos y recuentos `QUEUED`, `RUNNING`, `COMPLETED`, `FAILED`, además de `finished`. `COMPLETED` significa trabajo ejecutado; hay que consultar también el `status` del resultado.

Tras reiniciar se recuperan los trabajos en curso. Un fallo transitorio del proveedor conserva lo leído y evita guardar un éxito en caché. Reenviar el documento permite reintentar. Los lotes fallidos no se reenvían automáticamente.

## Errores

| HTTP | Significado |
|---|---|
| 404 | Identificador inexistente. |
| 422 | Entrada, tamaño, estructura o formato no admitido. |
| 500 | Fallo interno; detalle técnico en el log. |

Los errores de aplicación siguen dev: `{"code":"invalid_document","message":"mensaje"}`; la validación de parámetros de FastAPI puede devolver una lista en `detail`.

`GET /health` informa de configuración y modelos; no prueba inferencia remota. Un proceso Uvicorn por directorio de datos. Una exposición externa requiere autenticación y límites de carga en el proxy.
