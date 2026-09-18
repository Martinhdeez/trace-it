# Abstención y revisión de OCR

Pipeline: `invoice-v1.8.0+xlsx-v1.3`. Un fragmento ilegible no se completa por plausibilidad,
checksum o coincidencia con el maestro de proveedores. El texto original y las propuestas
se conservan como evidencia; un campo incierto no expone un valor canónico utilizable.

La API devuelve `NEEDS_REVIEW` y `review.action=HUMAN_REVIEW` cuando faltan campos, hay
contradicciones o regiones ilegibles. También exige número de factura. Este contrato sirve
para que la aplicación derive el trabajo: todavía no implementa una bandeja de revisores.

Los marcadores `[ILLEGIBLE]`, `?` y caracteres de sustitución asociados a un campo lo dejan
`UNVERIFIED`. Un marcador explícito sin campo identificable bloquea la completitud del
documento. El OCR sin corroboración mantiene candidatos, pero no un valor aceptado. La
segunda lectura debe superar el umbral de confianza; coincidir con baja confianza no basta.
Si dos modelos discrepan, no se elige el candidato que parezca más plausible.

Esto no garantiza detectar todos los errores: dos reconocedores pueden coincidir en una
lectura incorrecta y una capa textual nativa también puede contener errores.

## Medición en los archivos disponibles

Ejecución local sin caché, 501 archivos, Windows 11 y Python 3.12.13:

| Medida | Resultado |
|---|---|
| Archivos procesados | 500 PDF y 1 XLSX; cero fallos de procesamiento |
| Estado | 295 COMPLETE; 206 NEEDS_REVIEW |
| Invocaciones | 44 OCR; 0 VLM |
| Tiempo | 75,568 s; 6,63 archivos/s |
| Campos etiquetados en 29 escaneados | 283 |
| Valores canónicos coincidentes | 113 |
| Valores canónicos retenidos por incertidumbre | 170, expuestos como `null` |
| Valores OBSERVED discrepantes con la referencia | 0 |

La referencia es una transcripción visual provisional, no ground truth humano confirmado.
Los cuatro errores antes publicados como `OBSERVED` ahora quedan retenidos; no se han
corregido sus caracteres. La mejora en contención reduce la cobertura automática y aumenta
la revisión. El tiempo es una ejecución individual con actividad concurrente de pruebas;
no constituye una comparación controlada de rendimiento ni una garantía de capacidad.

En `scan_025.pdf`, el número de factura no tiene corroboración y queda `UNVERIFIED`.
En `scan_026.pdf`, los lectores discrepan entre `F26-7712` y `NF26-7712`: queda `AMBIGUOUS`.
Los otros nueve campos de ambas facturas mantienen las coincidencias de la regresión.

Para reproducir, ejecutar el benchmark con un directorio de datos nuevo y contrastar
`files.jsonl` mediante `tools.evaluate_scans`, como explica [validación](extraction-validation.md).
Las salidas locales de esta ejecución están en `backend/reports/abstention-cold/`, ignoradas
por Git. Un cambio de pipeline invalida la reutilización de resultados anteriores en caché.
