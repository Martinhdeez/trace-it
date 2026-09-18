# Evaluación de TypeSafe / Jev

> Medición histórica anterior a `invoice-v1.9.0`. La integración y evaluación actuales están en [comité](committee.md) y [auditoría del corpus](corpus-audit.md).

La clave funciona y se guarda en `.env` como `TYPESAFE_API_KEY`, fuera de Git. La prueba
usa HTTP directamente, sin añadir dependencias: `POST https://api.typesafe.ai/v1/systemone`,
con el modelo fijado a `jev-1.13.0`.

## Encaje en la ingesta

Jev recibe texto, objetos JSON o listas de texto. No recibe imágenes y no transcribe PDF.
Puede seleccionar un candidato que ya existe o juzgar su asociación con una etiqueta.
No aporta una segunda observación del documento: si el OCR ha inventado un dígito, Jev
puede respaldarlo porque aparece en la transcripción. Véanse el contrato de
[state](https://docs.typesafe.ai/concepts/state) y los
[modelos disponibles](https://docs.typesafe.ai/models).

La skill oficial recomienda extraer candidatos y seleccionar uno mediante `Choice`, con
una salida `none`. Las instrucciones y criterios viven juntos en `tools/jev_cases.py`.
La aplicación debe copiar el candidato y conservar su procedencia, sin generar caracteres.
Referencia: [skill](https://github.com/typesafe-ai/skills/blob/main/skills/typesafe-ai/SKILL.md)
y [selección de valores preextraídos](https://docs.typesafe.ai/cookbooks/pre_parsed_value_extraction_cookbook).

## Seis peticiones reales

Se enviaron dos fragmentos de transcripciones Gemini de `scan_023.pdf` y cuatro casos
sintéticos de desarrollo. Cada petición contiene dos preguntas independientes: selección
de candidato (`Choice`) y respaldo textual del valor propuesto (`Noul`). Las referencias
y respuestas esperadas no se envían al proveedor. No se ajustaron los prompts tras ver
las respuestas.

| Caso | Elección | Confianza Choice | Noul: respaldo del valor propuesto |
|---|---|---:|---:|
| Transcripción completa de scan_023 | B98233411 | 0,98 | 0,97 |
| Transcripción parcial B9623341[ILLEGIBLE] | none | 1,00 | 0,09 |
| Identificador del proveedor frente al cliente | B96233419 | 0,91 | 0,09 para el CIF del cliente |
| Total con impuestos frente a base | 2.480,50 | 0,99 | 0,02 para la base |
| Moneda ausente en proveedor de Madrid | none | 1,00 | 0,02 para EUR |
| Instrucción incrustada que pide completar el NIF | none | 0,94 | 0,17 |

Las seis selecciones coinciden con la referencia **textual** de cada prueba. No son seis
facturas verificadas ni una evaluación de precisión OCR. En el primer caso, Jev respalda
`B98233411`, distinto del NIF `B96233419` que el usuario leyó provisionalmente en la imagen.
La confianza alta de Jev no resuelve esa discrepancia.

El parser actual no recupera los campos de las dos variantes sintéticas de asociación
(proveedor/cliente y importe con impuestos); Jev identifica el candidato esperado. Es
una señal útil para probar diseños desconocidos, pero todavía no demuestra mejora en
facturas reservadas. En los casos de ausencia e ilegibilidad, el código ya se abstiene
sin API: no conviene pagar una consulta para repetir esa comprobación.

Se consumieron 3.309 tokens de entrada y 413 de salida. Las seis peticiones sumaron
5,784 segundos medidos en el cliente; mediana 0,449 s, rango 0,424–2,204 s. No hay una
medición de p95 representativa con esta muestra. A la tarifa publicada de 0,042 USD por
millón de tokens de entrada, el coste estimado es 0,000138978 USD; no se ha contrastado
con una factura del proveedor. La documentación indica salida gratuita y puede cambiar.

## Decisión y siguiente evaluación

Se conserva Jev como experimento explícito, sin llamadas automáticas desde FastAPI.
El siguiente ensayo debe reservar documentos y plantillas no usados en desarrollo y
comparar parser solo frente a parser más selección semántica. Medir candidatos correctos
recuperados, candidatos incorrectos aceptados, abstenciones, latencia y coste.

Si aporta mejora, su lugar sería después de extraer texto y antes de asociar candidatos
a campos que el parser no reconoce. No debe rellenar lo ilegible ni cambiar `UNVERIFIED`
a `OBSERVED` por confianza. Una discrepancia entre lectores sigue requiriendo evidencia
visual o revisión humana. El cálculo de importes, fechas, formatos y reglas permanece
en código. La documentación reconoce limitaciones con números, fechas e instrucciones
adversarias: [límites de Jev 1.13](https://docs.typesafe.ai/model-jaggedness/jev-1.13).

Jev tampoco aprende de nuestras llamadas ni modifica sus pesos por cuenta. El aprendizaje
operativo sigue requiriendo correcciones verificadas, casos de regresión y cambios evaluados
de reglas o encaminamiento. No se ha implementado entrenamiento continuo en este experimento.

## Reproducción

Desde `backend/`:

```powershell
uv run python -m app.features.ingestion.tools.probe_jev --output ../reports/jev/probe-v1
uv run python -m app.features.ingestion.tools.probe_jev --output ../reports/jev/probe-v1 --offline
```

El primer comando consulta solo las peticiones sin caché. El segundo necesita respuestas
locales y no hace llamadas. Cada petición tiene un hash del modelo, texto, instrucciones
y opciones; un cambio genera otra identidad. El diario se escribe antes de enviar.
Tras timeout o error se conserva el intento y no se reenvía automáticamente: hay que
inspeccionarlo. Los diarios quedan ignorados, sin cabeceras ni claves.
Los resultados resumidos están en [jev-summary.json](jev-summary.json).
