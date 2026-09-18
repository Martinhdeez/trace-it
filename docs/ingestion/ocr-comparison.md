# Comparación OCR sobre facturas difíciles

Se compararon `scan_021`, `022`, `023`, `025` y `026`; no existe `scan_024.pdf` en el lote. La referencia provisional contiene 47 campos visualmente transcribibles. Los restantes no se completan con el maestro.

| Sistema y entrada | Valores coincidentes |
|---|---|
| Ruta local anterior al preprocesamiento dirigido | 35/47 |
| Ruta local v1.7.1 con corrección de iluminación/bandas y contraste local | 42/47 |
| GOT-OCR v2, páginas originales, parser actual | 12/47 |
| GOT-OCR v2, correcciones y recortes, parser actual | 29/47 |
| Gemini 3.1 Flash-Lite, páginas originales | 46/47 |

El local actual obtiene 7/8, 7/10, 8/9, 10/10 y 10/10 respectivamente. Estas cifras evalúan OCR **más extracción de campos**, sobre casos de desarrollo. No son un ranking universal de modelos ni una evaluación independiente.

## Experimentos remotos

Se completaron 11 peticiones autenticadas: cinco páginas, cinco recortes y una variante `do_format=true`. El último intento, sobre scan_025, recuperó 2/10 campos y degeneró en repeticiones. Otros resultados también contienen texto repetido o confusión entre etiquetas e importes.

El recorte de scan_023 excluyó parte de la cabecera porque se calculó con la evidencia que el local había encontrado. Esto limita la comparación: no sirve para evaluar recuperación de campos que quedaron fuera del recorte.

La tarifa publicada de GOT-OCR en el momento de la consulta fue 0,05 USD por imagen: coste teórico de los 11 intentos, 0,55 USD. No se contrastó con una factura del proveedor. Fuente: [GOT-OCR v2 en fal](https://fal.ai/models/fal-ai/got-ocr/v2).

El experimento es explícito, fuera de la ruta automática de la API. Desde `backend/`:

```powershell
uv run python -m app.features.ingestion.tools.compare_fal_ocr --output ../reports/fal-got --offline
```

`--offline` reinterpreta respuestas locales sin llamadas ni cargos. Sin esa opción, el script puede enviar imágenes al proveedor y consumir saldo. Lee `FAL_KEY` del `.env` de la raíz. Guarda el identificador de petición antes de esperar y recupera la petición existente tras un timeout. Los recortes requieren `--local-extractions ruta/al/files.jsonl`.

## Selección y trabajo pendiente

Se conserva PP-OCRv5 local como ruta inicial; GOT no lo sustituye con estos resultados. Las propuestas generativas siguen sin verificar.

La prueba posterior con la API directa de Gemini mejora la recuperación a 46/47, con un NIF discrepante y un IBAN no verificable. El recorte del NIF logra abstención en el carácter ilegible. Ver [resultados y límites de Gemini](gemini-ocr.md).

Todavía no se han ejecutado comparaciones de PaddleOCR-VL-1.6, LightOnOCR-2 ni del router visual de fal. Tampoco están implementados el trabajador GPU separado, la cascada por campo/región ni el aprendizaje de correcciones. Su evaluación debe partir de referencias humanas, medir errores aceptados y abstenciones, y reservar documentos completos fuera del desarrollo.
