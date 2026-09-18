# Validación de la ingesta

La medición histórica de esta página corresponde a `invoice-v1.7.1+xlsx-v1.3`.
La versión actual `invoice-v1.8.0+xlsx-v1.3` retiene menos valores canónicos para preservar
la incertidumbre: ver [medición de abstención](abstention.md). Material fijado al commit
`18d43b3`. Los resultados miden extracción, no decisiones de pago ni elegibilidad ante el
verificador privado.

## Corpus completo

| Comprobación | Resultado |
|---|---|
| Archivos | 500 PDF y 1 XLSX |
| PDF nativos | 471; sin llamadas OCR |
| Escaneados | 29; 29 lecturas y 15 verificaciones locales |
| Ejecución sin caché | 142,028 s; 3,53 archivos/s |
| Ejecución con caché | 7,341 s; 68,25 archivos/s; 501 aciertos |
| Estado de extracción | 299 COMPLETE, 202 NEEDS_REVIEW; 0 trabajos fallidos |
| Auditoría nativa independiente | Poppler frente a extracción: 0 discrepancias detectadas en campos revisados |
| Excel | 14 hojas; 3.193 celdas XML y 3.124 campos canónicos comprobados, 0 discrepancias |
| Referencias visuales de escaneos | 254 de 283 valores coinciden; 4 valores incorrectos con estado OBSERVED |

Los cuatro errores observados están en `scan_013.pdf` (NIF, pedido, cuota IVA) y `scan_017.pdf` (fecha). Ambos documentos quedan NEEDS_REVIEW. No hubo un escaneo COMPLETE incorrecto frente a estas etiquetas, pero eso **no garantiza** lecturas correctas fuera del conjunto revisado. Las etiquetas son transcripciones visuales del asistente, pendientes de revisión humana independiente.

175 PDF nativos no imprimen moneda; el extractor conserva MISSING. EUR puede resolverse mediante contexto del lote, separado de la observación documental. Véase [auditoría de moneda](currency-audit.md).

Mediciones locales únicas sobre Windows 11, Python 3.12.13, 32 hilos disponibles, ONNX con 4 hilos por sesión y OpenCV con 1. El OCR ejecutado es CPU. No se ha medido pico de RAM/VRAM ni carga sostenida; no son promesas de capacidad. Datos resumidos en [benchmark-summary.json](benchmark-summary.json).

## Reproducción

Desde `backend/`, con modelos descargados y `pdftotext` en PATH:

```powershell
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
$env:TRACEPAY_DATA_DIR = 'reports/cold-data'
uv run python -m app.features.ingestion.tools.benchmark ../.context/500-sombras-de-alberto --output reports/cold
uv run python -m app.features.ingestion.tools.review_corpus ../.context/500-sombras-de-alberto reports/cold/files.jsonl --output reports/review
uv run python -m app.features.ingestion.tools.evaluate_scans --extractions reports/cold/files.jsonl --output reports/scans
```

Usar un directorio de datos nuevo para medir sin caché. El benchmark genera un registro por archivo con hash y evidencia; los informes detallados quedan fuera de Git. La auditoría no sustituye una lectura humana independiente.

## Cobertura y límites

Las pruebas cubren PDF mixtos, documentos corruptos, límites, caché concurrente, recuperación de trabajos, fallos de proveedor, importes ambiguos, dígitos sin reparación, moneda ausente, fórmulas sin caché, cabeceras contradictorias y dimensiones Excel falsas. Las pruebas OCR requieren pesos; las del material requieren el submódulo. Se omiten explícitamente si faltan.

La reorganización por funcionalidades pasó las 67 pruebas, incluidas las regresiones reales de sombras y bandas verticales. Persisten dos avisos de deprecación del cliente de pruebas de Starlette. No se ha ejecutado una nueva medición completa de rendimiento después de mover los módulos; se conserva la identificación del pipeline y de la medición anterior.

El sistema no funciona perfectamente ante cualquier entrada: quedan OCR ambiguos, casuísticas no soportadas y revisión manual. Las siguientes evaluaciones deben separar lectura de caracteres, asociación a campos y normalización, añadiendo regiones etiquetadas y documentos reservados.
