# Trace Pay · API de extracción

Backend FastAPI para convertir facturas PDF y libros XLSX en datos con evidencia. Implementa extracción, normalización, caché y procesamiento persistente de lotes. `COMPLETE` significa que se han observado los campos requeridos; **no significa PAGAR ni garantiza que un OCR haya leído todos los caracteres correctamente**. El clasificador de pagos, el adaptador ERP y la memoria de correcciones quedan fuera de esta implementación.

## Arranque en Windows

Desde `backend/`, con Python 3.12 y `uv`:

```powershell
uv sync --locked --group dev
uv run python -m app.features.ingesta.tools.download_models
uv run uvicorn app.features.ingesta.application:create_app --factory --host 127.0.0.1 --port 8000 --workers 1
```

Abrir http://127.0.0.1:8000/docs. La descarga de modelos se hace una vez; el servicio OCR funciona después sin conexión. Las revisiones de Hugging Face están fijadas en `scripts/download_models.py`, y los hashes quedan en `.models/manifest.json` y `.models/verify/manifest.json`. El lector latino móvil y el verificador local ocupan juntos unos 102 MB de pesos ONNX.

Para recuperar el material del reto si falta:

```powershell
git submodule update --init --recursive
```

## Usar la API

```powershell
curl.exe -X POST http://127.0.0.1:8000/v1/extractions -F "file=@../.context/500-sombras-de-alberto/facturas/scan_001.pdf"
curl.exe -X POST http://127.0.0.1:8000/v1/extractions -F "file=@../.context/500-sombras-de-alberto/FINAL_v7_DEFINITIVO_ahorasi.xlsx"
curl.exe -X POST http://127.0.0.1:8000/v1/batches -F "files=@primera.pdf" -F "files=@segunda.pdf"
```

| Ruta | Resultado |
|---|---|
| `GET /health` | Configuración de workers, manifiesto OCR y disponibilidad de configuración VLM. No ejecuta inferencia. |
| `POST /v1/extractions` | Extracción síncrona de un archivo. |
| `GET /v1/extractions/{id}` | Resultado persistido con evidencia. |
| `POST /v1/batches` | Acepta hasta 100 archivos; devuelve `202`, identificador y URL de seguimiento. |
| `GET /v1/batches/{id}` | Trabajos `QUEUED`, `RUNNING`, `COMPLETED` o `FAILED`, errores y referencias a resultados. |

El único dato de entrada obligatorio es el archivo. Los POST aceptan los controles de procesamiento `ocr=true` y `vlm=false`. La moneda se extrae del contenido: códigos como EUR, USD, CAD o MXN, la palabra euro y símbolos. Por convención del proyecto, `$` se interpreta como USD; un código explícito en el documento tiene prioridad (por ejemplo, MXN junto a `$`). Si no hay evidencia de moneda, queda `MISSING`; dos códigos contradictorios quedan `AMBIGUOUS`. Los nombres repetidos dentro de un lote se rechazan; archivos distintos con contenido idéntico conservan identidades independientes.

Cada campo contiene `value`, `status`, `origin` y `candidates`. Cada candidato conserva el fragmento original, el método, la página y coordenadas PDF en puntos, o la referencia `Hoja!Celda`. Los importes son cadenas decimales para evitar errores de coma flotante. El resultado incluye SHA-256, versión del pipeline, advertencias, tiempos y número de llamadas a proveedores. `ocr_calls` describe la extracción original; `ocr_calls_this_request` es cero al reutilizar caché.

| Estado de campo | Significado |
|---|---|
| `OBSERVED` | Valor extraído; puede seguir siendo incorrecto en términos de negocio o contener un error de OCR. |
| `MISSING` | No se ha podido extraer. |
| `INVALID` | El formato no se puede normalizar de forma segura, por ejemplo una fecha imposible. |
| `AMBIGUOUS` | Varias observaciones contradictorias. |
| `LOW_CONFIDENCE` | OCR por debajo del umbral, actualmente 0,90 por línea. |
| `UNVERIFIED` | Propuesta generativa, separador corregido, lectura OCR no corroborada, inconsistencia aritmética OCR o fórmula pendiente de comprobación. |

`NEEDS_REVIEW` identifica extracción incompleta o incierta. No equivale a la decisión de negocio `ESCALAR` del reto.

## Flujo y límites

1. Guardar el archivo por SHA-256 y conservar su nombre original. Comprobar tipo y tamaño: PDF/XLSX, hasta 25 MiB por archivo.
2. Consultar caché por contenido, opciones, versión del pipeline, manifiesto de modelos y configuración relevante. Ocho solicitudes simultáneas del mismo contenido comparten una extracción en las pruebas.
3. PDF: obtener texto y posiciones de todas las páginas con PyMuPDF. Aplicar reglas de campos y normalizadores deterministas. No rasterizar ni invocar modelos cuando el texto es suficiente.
4. Para páginas sin texto útil, corrupto o con una imagen dominante y campos pendientes: renderizar a 240 DPI, limitar a 18 millones de píxeles, detectar sombras/rayas fuertes, corregir la iluminación o el fondo cuando corresponda, recortar márgenes y ejecutar PP-OCRv5 local. Se mantienen coordenadas respecto al PDF original y las operaciones figuran en la evidencia. Una segunda página escaneada se procesa aunque la primera tenga texto. Si la lectura parece completa, un segundo reconocedor local contrasta los campos: las discrepancias quedan pendientes. No se selecciona un tratamiento por nombre de archivo.
5. Reconocer etiquetas y formatos del lote. Conservar candidatos incompatibles. Corregir separadores e invisibles de Unicode cuando la transformación es inequívoca; tolerar errores conocidos en etiquetas OCR sin sustituir dígitos de NIF, IBAN, pedido o importes.
6. XLSX: leer todas las hojas, incluso ocultas, con `openpyxl` en modo de lectura. Detectar cabeceras entre las primeras 25 filas, conservar celdas originales, `xml_numeric_value` y `number_format`, y extraer proveedores, pedidos y asientos cuando el esquema es reconocible. Leer también libros con dimensiones ausentes o incorrectas, comprobando límites sobre las coordenadas reales. Conservar las hojas de normas como texto; no convertirlas automáticamente en reglas ejecutables.
7. Solo si quedan campos sin resolver y `vlm=true`, consultar el servidor visual configurado. Las propuestas quedan registradas en `data.vision_proposals`. Los campos faltantes propuestos por el modelo quedan `UNVERIFIED`; no se sobrescriben valores observados. Una fecha inválida claramente impresa no se "arregla" mediante un LLM.
8. Persistir resultado y estado en SQLite WAL. Los trabajos `RUNNING` vuelven a `QUEUED` al reiniciar. Los fallos OCR/VLM preservan la evidencia y no se almacenan como aciertos de caché: reenviar el archivo permite reintentar.

PDF: máximo 40 páginas; documentos cifrados o corruptos se rechazan. XLSX: máximo 200 MiB descomprimidos, 2.000 miembros ZIP, 500.000 celdas, 25.000 filas y 100 columnas por hoja. Se conservan fórmulas, pero no se ejecutan: un caché de fórmula puede estar desactualizado. Las hojas no reconocidas se devuelven con `UNRECOGNIZED_SCHEMA`.

Los adaptadores actuales cubren las plantillas españolas observadas, NIF societario, pedidos `PO-AAAA-NNNN`, importes con coma o punto decimal y un único tipo de IVA por factura. Tipos múltiples de IVA, otros identificadores, idiomas o diseños necesitan otro adaptador o revisión. No se completan documentos a partir de valores esperados del Excel, ni se confunde el CIF del cliente con el NIF del emisor. No se usa el checksum de los IBAN sintéticos como filtro de extracción. XLS, CSV e imágenes sueltas no son entradas admitidas todavía.

El servicio está pensado para uso local. El límite por archivo se aplica al guardar; el framework recibe primero el multipart. Una publicación externa necesita autenticación y límites de cuerpo/conexiones en el proxy. Los objetos, resultados y la cola tienen persistencia local sin política automática de retención.

## Hardware y configuración

Para 32 GB RAM, 12 GB VRAM y 32 hilos se inicia con **2 trabajos concurrentes, sesiones OCR acotadas, 4 hilos ONNX por sesión y 1 hilo OpenCV**. El OCR corre en CPU; la GPU queda disponible para el servidor visual opcional. El acceso a MuPDF está serializado porque su API no es segura para uso concurrente entre hilos. No lanzar varios procesos Uvicorn sobre el mismo directorio: un bloqueo lo impide.

Configurar mediante variables de entorno antes de arrancar:

| Variable | Valor inicial |
|---|---|
| `TRACEPAY_DATA_DIR` | `.data` |
| `TRACEPAY_MODEL_DIR` | `.models` |
| `TRACEPAY_WORKERS` | `2`, entre 1 y 8 |
| `TRACEPAY_OCR_THREADS` | `4`, entre 1 y 16 |
| `TRACEPAY_OCR_CUDA` | `0`. El paquete incluido usa CPU; CUDA requiere un runtime ONNX compatible. |
| `TRACEPAY_VLM_URL` | Sin configurar; URL base de un servidor compatible, por ejemplo `http://127.0.0.1:8001/v1`. |
| `TRACEPAY_VLM_MODEL` | Nombre publicado por ese servidor. |
| `TRACEPAY_VLM_API_KEY` | Opcional. |

El adaptador VLM tiene timeout de 60 segundos, concurrencia 1 y salida limitada. **No se incluye ni se ha validado un servidor VLM real en esta entrega**; su contrato y degradación están probados con dobles de prueba. El OCR local sí está descargado y ejecutado con archivos reales. No se presupone que cualquier modelo visual entienda el protocolo del adaptador.

## Verificación reproducible

```powershell
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run python -m app.features.ingesta.tools.benchmark ../.context/500-sombras-de-alberto --output reports/extraction
uv run python -m app.features.ingesta.tools.review_corpus ../.context/500-sombras-de-alberto reports/extraction/files.jsonl --output reports/review
```

El benchmark genera `files.jsonl` con evidencia por archivo y `summary.json`. Para una medición sin caché, usar un `TRACEPAY_DATA_DIR` nuevo. No se suministran campos de negocio ni una moneda predeterminada. Las pruebas de material requieren el submódulo y la prueba OCR real requiere los pesos; si faltan se omiten indicando el motivo.

Ver [medición y casuísticas](extraction-validation.md). La medición de completitud no sustituye a una evaluación con campos etiquetados ni al verificador privado de decisiones del reto.

Se ha probado GOT-OCR v2 de fal.ai con peticiones reales, comparándolo con las lecturas visuales de los scans difíciles. La clave se lee de `.env` mediante `FAL_KEY` y está excluida de Git. El experimento se ejecuta explícitamente con `python -m app.features.ingesta.tools.compare_fal_ocr`; `--offline` reevalúa las respuestas guardadas sin llamadas ni cargos. El script conserva los identificadores de petición para recuperar trabajos sin volver a enviarlos. Este proveedor no se activa automáticamente en la API. Ver [comparación de OCR](ocr-comparison.md).

## Decisiones de implementación

- Reglas y normalización antes de modelos: coste bajo y evidencia estable. Consecuencia: un diseño desconocido puede quedar pendiente aunque una persona lo lea fácilmente.
- OCR móvil local antes de modelos generativos: pesos pequeños y cero coste de API. Consecuencia: escaneados dañados siguen necesitando revisión o un modelo mayor; la confianza del OCR no es una probabilidad calibrada de corrección.
- SQLite y objetos locales: estado recuperable sin infraestructura adicional. Consecuencia: una sola instancia; para varios nodos habría que sustituir cola, almacenamiento y coordinación.
- Evidencia inmutable y propuestas separadas: no se utiliza el resultado esperado para fabricar datos. Consecuencia: más casos pendientes, pero quedan disponibles los errores reales para un futuro conjunto de evaluación y aprendizaje supervisado.

Referencias de implementación: [FastAPI UploadFile](https://fastapi.tiangolo.com/tutorial/request-files/), [RapidOCR](https://rapidai.github.io/RapidOCRDocs/main/install_usage/rapidocr/usage/), [detector oficial](https://huggingface.co/PaddlePaddle/PP-OCRv5_mobile_det_onnx), [reconocedor latino oficial](https://huggingface.co/PaddlePaddle/latin_PP-OCRv5_mobile_rec_onnx).
