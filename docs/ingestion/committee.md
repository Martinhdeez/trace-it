# Comité de extracción

Desde `invoice-v1.9.0`, la API usa lectores complementarios según la evidencia disponible.
El objetivo es transcribir el documento; esta funcionalidad no decide pagos ni modifica
las reglas publicadas de un proceso.

1. El texto nativo suficiente evita llamadas OCR y visuales.
2. Las páginas que necesitan OCR pasan por el reconocedor primario y el secundario local.
   El segundo ya no exige una primera extracción casi completa. Puede corroborar campos
   sueltos o aportar candidatos que faltaban.
3. Si quedan campos pendientes, se consulta el lector visual configurado. Se usa el servidor
   `TRACEPAY_VLM_URL` cuando existe; en su ausencia, Gemini con `GEMINI_API_KEY`.
4. Si siguen existiendo campos pendientes y hay `TYPESAFE_API_KEY`, Jev recibe las
   transcripciones etiquetadas por lector y selecciona entre candidatos existentes o `none`.
   Su recomendación queda en `data.committee.text_judge`; no modifica el valor canónico.

Los POST aceptan `vlm` y `jev` por separado. Omitirlos permite la participación automática
del proveedor configurado; `false` impide su uso y `true` solicita su uso cuando corresponde.
No se exige ninguna clave para procesar documentos localmente. La biblioteca toma variables
del entorno; Uvicorn puede cargar `.env` mediante `--env-file ../.env` desde `backend/`.

## Política por campo

Una observación nativa clara puede aceptarse por sí sola. Para OCR se requieren dos lectores
concordantes y sin evidencia incompatible. Una lectura local solo aporta soporte si supera
el umbral configurado y sus comprobaciones; una lectura visual sola queda pendiente.
Las propuestas de separadores, los fragmentos ilegibles y los conflictos no se resuelven
por mayoría. Todos los candidatos y sus regiones se conservan.

Los dos reconocedores locales pertenecen a la misma familia y pueden equivocarse igual.
Por eso también se comprueba la aritmética con los campos disponibles: base, porcentaje y
cuota bastan para detectar una discrepancia aunque falte el total. Un desacuerdo aritmético
en OCR mantiene los importes pendientes; nunca se cambia el importe para cuadrar la factura.
El texto nativo claramente impreso se conserva aunque los números del documento no cuadren.

Jev no recibe imágenes. Que seleccione un IBAN significa que lo encuentra respaldado por
las transcripciones, no que haya leído esos caracteres en el original. Contar esa selección
como otro voto visual duplicaría la misma evidencia. El consumidor puede mostrarla como
la mejor propuesta textual, junto a los candidatos y los motivos de revisión.

`OBSERVED` significa que se cumple esta política, no una garantía matemática de exactitud.
Los modelos pueden compartir errores. Los campos inciertos devuelven `value=null` y el
documento requiere `HUMAN_REVIEW`. El comité no contiene excepciones por nombre de archivo,
valores esperados del Excel ni respuestas de la auditoría.

## Trazabilidad y recuperación

`data.committee` identifica la política, los lectores y el soporte por campo.
Los localizadores OCR incluyen el lector, de modo que dos regiones con el mismo índice
siguen siendo distinguibles. `vision_proposals` y `ocr_verification` se conservan por
compatibilidad. Los resultados y métricas se persisten con una nueva versión del pipeline.

La caché de extracción depende de las opciones, modelos, configuración y activación de
proveedores. Los diarios de `.data/provider-journal/` conservan identidad de petición,
respuesta, tiempos y estado, sin credenciales. Una petición completa puede reutilizarse.
Una petición interrumpida o fallida queda bloqueada para evitar duplicarla automáticamente;
requiere inspección del diario antes de un reenvío deliberado. No borrar ese registro como
parte de un reintento automático. Los errores mantienen la evidencia y requieren revisión.

Las métricas de llamadas cuentan invocaciones del adaptador; el diario indica si hubo una
petición remota. En una respuesta servida desde la caché de extracción, los contadores
`*_calls_this_request` son cero. Los diarios contienen texto documental y se quedan fuera
de Git, igual que los originales y los resultados locales.

## Límites pendientes

La selección conservadora deja campos legibles pendientes cuando un lector los contradice.
No se ha entrenado un árbitro visual calibrado capaz de descartar de forma fiable una lectura
errónea. Tampoco hay una bandeja humana ni memoria de correcciones conectada a PostgreSQL.
Las referencias visuales de esta auditoría son provisionales salvo los campos confirmados
expresamente por el usuario. Ver [resultados y documentos concretos](corpus-audit.md).
