# Auditoría de los 500 PDF y del comité

Auditoría del 19 de septiembre de 2026 sobre `500-sombras-de-alberto/facturas`:
**500 PDF, 522 páginas, 471 documentos con texto nativo y 29 escaneados**.
Los originales se conservaron y se identificaron por SHA-256.

## Método y límites de la referencia

Se renderizaron todas las páginas y se revisaron visualmente. Para los documentos nativos,
Poppler proporcionó una extracción de texto separada del lector PyMuPDF de producción;
la revisión visual incluyó todas las filas con contenido. Los escaneados se revisaron en
la imagen original y recortes, con lecturas provisionales de sus diez campos.
Las transcripciones de referencia de los escaneados están normalizadas, no son una
transcripción exacta carácter por carácter; no permiten afirmar una tasa CER/WER.

La referencia visual del asistente **no es ground truth humano independiente**. El usuario
corrigió dos lecturas iniciales del asistente, en las que los modelos habían acertado:

- `scan_023.pdf`: factura `2026/22608`, no `2026/22808`.
- `scan_011.pdf`: IBAN que comienza `ES83`, no `ES93`.

Las cifras siguientes incorporan ambas confirmaciones. Ocho campos de cuatro documentos
siguen sin referencia fiable por degradación de la imagen y se excluyen del denominador
de aciertos/errores. No se completaron utilizando el Excel ni otras facturas del proveedor.

Se conservaron dos ejecuciones distintas:

1. Baseline `invoice-v1.8.0`: API local, OCR primario forzado sobre las 522 páginas para
   comparar también documentos nativos y segundo OCR forzado sobre los 29 escaneados.
2. Comité `invoice-v1.9.0`: subida y recuperación mediante la API de los 500 PDF, con OCR
   locales reales, Gemini `gemini-3.1-flash-lite` y Jev `jev-1.13.0` configurados.
   Las referencias nunca se enviaron a los proveedores ni al comité.

## Resultados

| Ejecución | COMPLETE | NEEDS_REVIEW | Fallos de procesamiento |
|---|---:|---:|---:|
| Baseline local | 295 | 205 | 0 |
| Comité | 305 | 195 | 0 |

El comité ejecutó 58 llamadas OCR (29 primarias y 29 secundarias), 28 lecturas visuales
y 18 consultas textuales a Jev. No llamó a proveedores para los 471 PDF nativos.
No hubo errores de proveedor en esta ejecución. La ejecución completa por API tardó
aproximadamente 250 segundos en el equipo de desarrollo.

Sobre **282 campos con referencia** de los 29 escaneados:

| Salida | Coincide con referencia | Discrepa | Pendiente / abstención |
|---|---:|---:|---:|
| OCR primario aislado, valores OBSERVED | 230 | 7 | 45 |
| OCR secundario aislado, valores OBSERVED | 178 | 9 | 95 |
| Baseline local, valores canónicos | 113 | 0 | 169 |
| Comité, valores canónicos | 224 | 0 | 58 |

La cobertura de valores canónicos pasa del 40,1 % al 79,4 %. Cero discrepancias observadas
con esta referencia provisional no garantiza ausencia de errores en otros documentos.
Los ocho campos sin referencia permanecen sin valor canónico también en el comité.

Gemini intervino en 28 escaneados: de sus **272 campos evaluables**, 269 propuestas
coinciden, una discrepa y dos no se extraen. La discrepancia es el IBAN de `scan_010.pdf`:
propone un grupo `1236` donde la imagen muestra `1235`; el comité conserva el conflicto.
En los otros ocho campos sin referencia no se califica su propuesta como acierto.

Jev intervino en 18 escaneados: 162 selecciones coinciden y 10 son abstenciones sobre
172 campos evaluables; otros ocho carecen de referencia. Este subconjunto es distinto del
de Gemini. Jev no es un OCR ni una lectura independiente: selecciona sobre texto existente.
En el fax respalda una propuesta completa de IBAN que no puede confirmarse visualmente.

En los documentos nativos se conservan 4.532 valores coincidentes, 175 ausencias de moneda
y tres fechas impresas inválidas. Forzar OCR sobre ellos produce 4.490 valores coincidentes
y 42 abstenciones adicionales; no mejora la extracción nativa.
Las fechas inválidas corresponden a `2026-03-19_P008.pdf`, `FA-1123_construcciones.pdf`
y `FA-2967_seguridad.pdf`. No se sustituyeron por fechas plausibles.

## Los cinco documentos solicitados

| Archivo | Baseline: campos canónicos | Comité: campos canónicos | Propuestas visuales coincidentes / evaluables | Resultado |
|---|---:|---:|---:|---|
| `scan_016.pdf` | 7/10 | 10/10 | 10/10 | COMPLETE |
| `scan_017.pdf` | 0/10 | 3/10 | 9/10 | NEEDS_REVIEW |
| `scan_023.pdf` | 0/10 | 6/10 | 8/8 | NEEDS_REVIEW |
| `fax_2026_0411.pdf` | 0/10 | 0/10 | 8/8 | NEEDS_REVIEW |
| `copia_2026_0518.pdf` | 0/10 | 5/10 | 8/8 | NEEDS_REVIEW |

El lector visual sí recupera gran parte del texto: 43 de 44 campos evaluables de estos cinco
archivos. Que el fax tenga cero valores canónicos no significa que Gemini no lo lea: sus
campos carecen de corroboración local suficiente o presentan conflictos. Jev recomienda
candidatos, pero no convierte esa misma transcripción en una segunda evidencia visual.

La limitación anterior era una condición de código: el segundo OCR solo se ejecutaba si
todos los campos salvo moneda eran OBSERVED tras la primera lectura. En los cinco archivos,
solo `scan_016.pdf` cumplía esa condición. Ahora el segundo lector se ejecuta en las páginas
que necesitan OCR, aunque la primera lectura sea incompleta. La política sigue siendo
conservadora frente a desacuerdos; no se ha implementado un árbitro visual capaz de resolver
con fiabilidad todas las diferencias entre lectores.

## Ilegibilidad y revisión humana

| Archivo | Campos sin referencia fiable | Motivo |
|---|---|---|
| `scan_023.pdf` | NIF e IBAN | Desenfoque y manchas; el usuario confirma escalado por ilegibilidad. Reducir la imagen ayuda a percibir formas, pero no confirma todos los caracteres. |
| `scan_021.pdf` | Número de factura y NIF | Bandas negras horizontales ocultan caracteres; pedir un original mejor. |
| `fax_2026_0411.pdf` | NIF e IBAN | Trama de fax y ruido sobre los dígitos; revisar el original o pedir una copia mejor. |
| `copia_2026_0518.pdf` | NIF e IBAN | Bandas verticales sobre los identificadores; revisar el original o pedir una copia mejor. |

El resto de los campos de referencia pudo leerse. Los desacuerdos OCR de esos campos
no se etiquetan como documento ilegible: son limitaciones de los lectores o del adaptador.
Las confirmaciones del usuario quedan en la referencia de auditoría; no se han añadido
excepciones por documento ni memoria de correcciones al código de producción.

## Artefactos y comprobaciones

Los artefactos completos permanecen en `backend/reports/corpus-audit-20260919/`, ignorados
por Git: originales rasterizados, manifiesto, textos nativos, transcripciones OCR, referencias,
resultados por documento, diarios remotos y scripts de ejecución/comparación.

- `documents.csv` y `fields.csv`: comparación detallada del baseline.
- `committee-documents.csv`: resultado y campos pendientes de cada uno de los 500 PDF.
- `committee-fields.csv`: comparación campo a campo de comité, Gemini y Jev.
- `scan-summary.csv`, `comparison-summary.json` y `committee-summary.json`: recuentos.
- `reference/`: texto extraído de cada documento; `visual-scan-reference.json`: campos y dudas.
- `run_committee.py` y `summarize_committee.py`: ejecución HTTP y evaluación separada.

La feature pasa 92 pruebas y Ruff. La suite general anterior a sincronizar con los cambios
recientes de `dev` termina con 137 pasadas, cuatro omitidas y seis fallos de procesos/decisiones
por Psycopg y ProactorEventLoop en Windows. Los fallos están fuera de la ingesta.
No se ha validado todavía contra un conjunto humano independiente ni contra decisiones
de pago; COMPLETE y HUMAN_REVIEW siguen siendo estados de extracción.
