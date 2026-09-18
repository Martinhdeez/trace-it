# trace-it: plano de la aplicación

**Estado:** borrador vivo. Se itera hasta tener el plano completo.
**Marcadores:** [DECIDIDO] acordado por el equipo · [PROPUESTA] sugerencia pendiente de validar · [ABIERTO] sin decidir · [DESCARTADO] valorado y rechazado · [PENDIENTE] sección por escribir.

## 1. Visión

Resolvemos el reto de forma general. El reto describe un proceso concreto (pagar o no las facturas de Alberto). Ese proceso tiene tres partes:

1. **Entradas y fuentes de verdad:** PDFs de facturas, el Excel de proveedores y pedidos, y el ERP.
2. **Reglas deterministas** que hay que cumplir: la norma de pagos.
3. **Una decisión final**, en parte subjetiva: PAGAR, NO_PAGAR o ESCALAR.

La aplicación sirve para este proceso y para cualquier otro con la misma forma. El proceso de facturas es la primera instancia, no el producto. [DECIDIDO]

La aplicación mejora con el uso. Cada decisión humana sobre un caso no cubierto por las reglas se convierte en una regla nueva. Así el sistema es cada vez más autónomo y escala menos. [DECIDIDO]

## 2. Conceptos

| Concepto | Qué es | Ejemplo en el reto |
|---|---|---|
| Proceso | Definición completa: fuentes, símbolos, reglas y tipos de decisión | "Pago de facturas" |
| Fuente de verdad | Datos de referencia contra los que se valida | Excel de proveedores y pedidos, ERP |
| Instancia | Cada caso que el proceso decide | Una factura PDF |
| Símbolo | Dato con nombre que usan las reglas | `nif`, `iban`, `pedido`, `importe`, `estado_erp` |
| Regla | Condición determinista sobre símbolos que produce una decisión o un motivo | "IBAN de la factura ≠ IBAN del maestro" |
| Tipo de decisión | Salidas posibles del proceso. Las define cada proceso, con su prioridad, cuál es la de por defecto y cuáles requieren a una persona (`requiere_persona`) | PAGAR, NO_PAGAR, ESCALAR (esta última con `requiere_persona`) |
| Responsable | Persona que decide lo que las reglas no cubren | Manager / Alberto |

## 3. Ciclo de vida de un proceso

### 3.1 Crear el proceso [DECIDIDO]
1. El usuario sube todos los datos relevantes: documentos, hojas de cálculo, acceso a sistemas.
2. Opcionalmente añade texto en lenguaje natural para lo que no esté en los datos.
3. El sistema deriva de todo ello:
   - los **símbolos** necesarios,
   - las **reglas**,
   - los **tipos de decisión**.

### 3.2 Compilar las reglas a código [DECIDIDO]
Decidir tiene que ser totalmente determinista, y las reglas tienen que poder cambiar sin romper el sistema. Por eso las reglas no se interpretan en ejecución: se convierten en código.

Hay dos agentes distintos:
- **Agente compilador.** Lee una regla y escribe el código determinista que la aplica. Se dispara automáticamente cada vez que se añade o cambia una regla.
- **Decisor (motor).** Para cada instancia, ejecuta el código de todas las reglas activas y resuelve PAGAR, NO_PAGAR o ESCALAR. Se ciñe al resultado del código y no usa LLM (ver P7).

Así la misma instancia con las mismas reglas da siempre el mismo resultado.

[PROPUESTA] Contrato del código de una regla:
- Es una función pura: recibe los símbolos de la instancia y devuelve si se cumple, un código de motivo y la decisión que implica.
- No tiene red, disco, reloj ni aleatoriedad. La fecha de corte entra como símbolo.
- Se guarda versionada junto al texto de la regla del que sale y el hash de ambos.

[PROPUESTA] Validación antes de activar código nuevo:
1. El compilador genera también casos de prueba a partir de la regla (los que cumplen y los que no).
2. El código debe pasar esos casos y los casos reales ya etiquetados.
3. Se ejecuta contra el histórico y se muestra qué decisiones cambian (ver P2).
4. El responsable aprueba. Solo entonces la versión pasa a activa.

Si la validación falla, la regla anterior sigue activa y el proceso no se para.

### 3.3 Ejecutar
Para cada instancia, el sistema extrae los símbolos, ejecuta el código de las reglas activas y decide. Si ninguna regla resuelve el caso, o una regla dice escalar, la instancia va al responsable. [PENDIENTE: detalle; ver `.artifacts/specs/2026-09-18-reglas-sistema.md` para extracción, ERP y resiliencia]

### 3.4 Escalado asistido [DECIDIDO]
Cuando una instancia se escala, el responsable ve:
- el caso y por qué se escaló,
- **la decisión que tomaría el agente y su razonamiento**,
- **la regla nueva que propone el agente** para resolver solo los casos similares futuros.

El responsable tiene dos opciones:
- **Aceptar:** toma la misma decisión que el agente y añade la regla propuesta.
- **Rechazar:** toma su propia decisión y escribe su propia regla.

En los dos casos entra una regla nueva en el proceso. Por eso el proceso aprende de forma continua.

### 3.5 Autocorrección por revisión [DECIDIDO]
El manager puede revisar cualquier instancia ya decidida, no solo las escaladas. Si encuentra un error, explica por qué ocurrió. El proceso se corrige a sí mismo a partir de esa explicación.
[PROPUESTA] Usar el mismo mecanismo que el escalado: el agente convierte la explicación en un cambio de regla y el manager lo aprueba.

### 3.6 Registro de decisiones y comprobación de reglas nuevas [DECIDIDO]
Se aplican todas las reglas a cada instancia, con funciones deterministas. Todas las decisiones quedan registradas. Cuando entra una regla nueva, se vuelve a ejecutar sobre las decisiones pasadas para comprobar si con ella todo sigue bien.

[PROPUESTA] Qué guarda cada decisión:
- Instancia: identificador y hash del fichero.
- **Símbolos usados**, con el valor exacto y su origen (texto de la factura, Excel, ERP con fecha de la consulta).
- Versión del conjunto de reglas y resultado de cada regla (se cumple o no, código de motivo).
- Decisión final y quién la tomó: motor o responsable.
- Si un humano la validó o la corrigió: decisión correcta y motivo.

Guardar los símbolos permite repetir la decisión sin volver a leer el PDF ni llamar al ERP. Así la comprobación es rápida, gratis y siempre da lo mismo.

[PROPUESTA] Resultado de la comprobación de una regla nueva, por instancia:
- **Sin cambio:** la decisión es la misma.
- **Regresión:** cambia una decisión que un humano ya validó. Bloquea la activación hasta que el responsable la resuelva.
- **Cambio por revisar:** cambia una decisión que nadie validó. Se muestra al responsable antes de activar.

### 3.7 Auditoría retroactiva [DECIDIDO]
Hay un histórico de todas las decisiones, tomadas por el motor o por personas. Cada vez que se añade una regla, se revisa el histórico para ver si alguna decisión pasada fue incorrecta según la regla nueva. Por ejemplo:
- una factura pagada que no tocaba pagar,
- una factura no pagada que sí había que pagar.

### 3.8 Procesos y versionado de reglas [DECIDIDO]
- **Proceso:** es como una carpeta que contiene unas reglas. Dentro se pueden añadir y quitar reglas.
- Cada proceso tiene **su propio histórico de decisiones** y **su propio versionado de reglas**. Se puede volver a una versión anterior o avanzar a una posterior, como un git simplificado.
- Si se quieren aplicar reglas totalmente distintas, se crea un **proceso independiente**.
- Al ejecutar, se elige qué proceso aplicar. Los procesos no comparten reglas ni histórico.

Detalle en P13 a P16.

## 4. Preguntas abiertas (con recomendación)

**P1. ¿Qué forma tiene una regla nueva?** [DECIDIDO]
La regla se escribe en texto. La aplicación genera por debajo el código que la aplica, de forma automática. Ver P8.

**P2. ¿Una regla nueva se aplica también al pasado?** [DECIDIDO]
Sí, como comprobación: antes de activarla se ejecuta contra todas las decisiones registradas (ver 3.6). El responsable confirma viendo el impacto.

**P3. ¿Qué pasa si dos reglas chocan?** [DECIDIDO]
Si dos reglas dan decisiones distintas para el mismo caso, el choque se escala a una persona. Esa persona decide qué regla queda por encima de la otra. La prioridad elegida entra como cambio de reglas (versión nueva).

**P4. ESCALAR y el filtro del reto.** [DECIDIDO]
- ESCALAR es una salida válida del proceso: una regla puede dar ESCALAR como solución correcta. La resolución posterior del responsable se guarda aparte y no cambia esa salida.
- Se sabe con qué reglas se tomó cada decisión, así que el aprendizaje posterior no altera lo ya decidido.
- El versionado completo es de la iteración 2.
- `outcomes.jsonl` es solo una exportación para enviar al reto, no un concepto de la aplicación. Basta con poder exportarlo. [DECIDIDO]
- [PROPUESTA] En la iteración 1, cada decisión guarda el hash del código de cada regla aplicada. Es barato y, en la iteración 2, permite asociar las decisiones antiguas a su versión.

**P5. ¿Quién valida el proceso generado al crearlo?** [ABIERTO]
Recomendación: el usuario revisa los símbolos, las reglas y los tipos de decisión extraídos antes de la primera ejecución. Cada regla muestra de dónde sale (hoja del Excel, frase del texto). Si un error de lectura pasa aquí, se repite en todas las instancias.

**P6. ¿Cómo se representan los símbolos que requieren sistemas externos (ERP)?** [ABIERTO]
Recomendación: cada fuente de verdad es un conector con un contrato fijo (qué símbolos da y cómo falla). El ERP del reto es el primer conector. Esto es lo que permite reutilizar el sistema en otros procesos.

**P7. ¿El agente decisor es un LLM?** [DECIDIDO: no]
Si un LLM eligiera qué regla aplicar, la elección no sería determinista y podría saltarse una regla que sí aplicaba.
Decisión:
- Se ejecuta **siempre el código de todas las reglas activas** sobre cada instancia; nadie elige cuáles.
- Una tabla de precedencia fija combina los resultados: ESCALAR > NO_PAGAR > PAGAR.
- El "agente decisor" es ese motor, sin LLM.
- El LLM solo interviene después: explica la decisión y, si la instancia se escala, propone decisión y regla (3.4).

**P8. ¿Código libre o lenguaje de reglas?** [DECIDIDO: código libre]
- El agente compilador genera **código Python** para cada regla, de forma totalmente automática.
- Motivo: las reglas cambian todo el tiempo (se añaden, se quitan, se modifican) y la aplicación debe seguir funcionando sin que nadie toque su código. Además debe servir para otros problemas distintos de las facturas. Un catálogo cerrado de primitivas obligaría a programar cada tipo de regla nuevo.
- Se descarta el catálogo de primitivas (reglas como datos) por ese motivo.

[PROPUESTA] Ejecución segura del código generado (lo ha escrito un LLM):
- Comprobación estática antes de aceptarlo: solo imports permitidos (`decimal`, `datetime`, `re`, `math`, `unicodedata`) y nada de `open`, `exec`, `eval`, `__import__` ni acceso a red.
- Ejecución en un proceso aparte, con tiempo máximo, sin red y sin disco.
- La función recibe los símbolos y devuelve un resultado con forma fija: `{cumple, motivo, decision}`. Si devuelve otra cosa, falla o se pasa de tiempo, la instancia se escala con motivo `ERROR_REGLA` y se avisa. Nunca se decide sin esa regla.

**P9. ¿Cómo se sabe que el código generado es correcto?** [DECIDIDO]
1. Dos agentes independientes (a ser posible, modelos distintos). Cada uno escribe, solo a partir del texto de la regla, su código y sus tests: código A + tests A, código B + tests B. Ninguno ve lo del otro.
2. **Todos los tests se pasan por los dos códigos**: el cruce (A con tests B, B con tests A) detecta diferencias de interpretación; los tests propios detectan errores de programación.
3. Los dos códigos deben coincidir en todas las instancias del histórico.
4. El responsable revisa el impacto y activa.
5. En producción se ejecutan los dos códigos. Si no coinciden en una instancia, se escala con `DISCREPANCIA_REGLA`.

Si un test falla, no se sabe quién tiene razón (código o test). Lo resuelve el responsable, normalmente aclarando el texto de la regla y recompilando. Coste: dos compilaciones por cambio de regla, no por instancia.
Límite: si los dos agentes malinterpretan igual un texto ambiguo, pasa. Lo cubre la revisión del impacto (paso 4).

**P10. ¿Y si la regla nueva usa un símbolo que no se guardó?** [ABIERTO]
Por ejemplo, una regla nueva sobre el "recargo financiero" necesita un campo que antes no se extraía.
Recomendación: guardar siempre el texto completo extraído de cada factura, además de los símbolos. Si falta un símbolo, se extrae del texto guardado (sin volver a leer PDFs escaneados) y se registra como símbolo nuevo antes de comprobar la regla. Si el símbolo viene del ERP, se consulta la foto local guardada del ERP, no el ERP en vivo.

**P11. ¿Cómo se llama la unidad?** [DECIDIDO]
**Proceso.** No existe "proyecto". Ver 3.8.

**P12. ¿Cuándo se crea un proceso nuevo y cuándo una versión nueva?** [DECIDIDO]
- **Versión nueva:** se añaden, quitan o cambian reglas dentro del mismo proceso. Ejemplo: norma v3 → norma v4.
- **Proceso nuevo:** reglas totalmente distintas. Proceso independiente, con su propio histórico.
- [PROPUESTA] Un proceso nuevo puede crearse copiando las reglas de otro, pero su histórico empieza vacío.

**P13. ¿Qué es una versión y cómo se "vuelve atrás"?** [DECIDIDO]
- El versionado es lineal: un registro de los cambios de reglas del proceso.
- Cada cambio crea una versión nueva e inmutable con la foto completa de las reglas, quién la hizo, el motivo y la instancia que la provocó, si la hay.
- "Volver atrás" activa una versión anterior. No borra nada y queda registrado como un paso más.
- Solo hay una versión activa por proceso. Las instancias nuevas se deciden con ella.

**P14. ¿Qué hace la auditoría retroactiva con una decisión pasada que ahora sale distinta?** [DECIDIDO]
**Nunca cambia el pasado.** Solo avisa: genera información sobre decisiones pasadas erróneas, por ejemplo "pagada indebidamente" o "no pagada debiendo pagarse". Con eso la empresa decide si reclama el dinero o paga lo pendiente. La gestión de ese aviso queda fuera del sistema.

**P15. Si la regla nueva contradice una decisión que validó una persona, ¿quién gana?** [DECIDIDO]
Ninguno de los dos automáticamente. Se marca como conflicto y lo resuelve el responsable.

**P16. ¿Se versionan también los datos (Excel, ERP)?** [DECIDIDO: no]
- Los ficheros ingeridos no tienen versiones: se guardan tal cual y no cambian. Lo que cambia son las decisiones sobre ellos.
- Cada decisión del histórico queda asociada a los ficheros con los que se tomó.
- Si un fichero se modifica, se trata como un fichero nuevo. Se identifica por su hash de contenido.
- [PROPUESTA] El ERP no es un fichero, sino un sistema vivo. Cada descarga del ERP se guarda como un ingreso más, con su fecha, igual que un fichero nuevo. Así la regla anterior también le aplica.

**P17. ¿Comparar dos versiones cualesquiera?** [DESCARTADO]
No hace falta como funcionalidad propia: basta con ejecutar una versión y luego otra.

**P18. Datos que recibe la función de una regla.** [DECIDIDO]
Firma única para todas las reglas y todos los procesos:
```python
def evaluar(instancia: dict, fuentes: dict[str, list[dict]], otras: list[dict]) -> dict:
    # devuelve {"salta": bool, "motivo": str}
```
- `instancia`: símbolos de la instancia.
- `fuentes`: tablas ya cargadas (proveedores, pedidos, foto local del ERP).
- `otras`: símbolos del resto de instancias del proceso (para reglas como "pedido duplicado").
Función pura: sin red, sin disco, sin reloj.
La decisión no la devuelve el código: la fija la regla en su definición (campo `decision`), que la aprueba una persona. El código solo dice si salta y por qué.

**P19. Tipos de regla y combinación.** [DECIDIDO]
Se ejecutan todas las reglas sobre cada instancia. Hay dos tipos:
- **Requisito:** algo que tiene que cumplirse. Si no se cumple, la regla salta. Ejemplo: "el IBAN coincide con el del maestro".
- **Prohibición:** algo que, si se cumple, impide pagar. Si se cumple, la regla salta. Ejemplo: "el ERP dice PAGADA".
Cada regla declara qué decisión produce cuando salta. Si no salta ninguna: la decisión por defecto del proceso. Si saltan varias: gana la de mayor prioridad.

**Tipos de decisión configurables por proceso [DECIDIDO].** Ningún nombre de decisión está fijo en el código. Cada proceso define sus tipos con:
- `prioridad`: gana la mayor si saltan varias reglas;
- `por_defecto`: exactamente uno, se aplica si no salta ninguna;
- `requiere_persona`: las instancias con esa decisión van a la cola del responsable y el asistente propone cómo resolverlas.
En el proceso de facturas: ESCALAR (3, requiere persona) > NO_PAGAR (2) > PAGAR (1, por defecto).

**P20. Extracción de símbolos.** [DECIDIDO]
- Cada proceso define su lista de símbolos (nombre, tipo, descripción).
- Un LLM la rellena con salida estructurada: sobre el texto del PDF, o sobre la imagen si es un escaneo. Sin parsers por plantilla.
- Dos extracciones independientes (proveedores distintos) deben coincidir. Además, validadores fijos donde apliquen: IBAN mod-97, letra del NIF, base + IVA = total.
- Si no coinciden o un validador falla: estado `REVISION` (P21).

**P21. Discrepancias.** [DECIDIDO]
- **Al añadir una regla:** si los dos códigos discrepan, o chocan con otra regla o con una decisión validada, el sistema lo detecta, avisa al usuario y la regla **no entra** hasta que se resuelva.
- [PROPUESTA] **En ejecución:** si las dos extracciones no coinciden, o los dos códigos de una regla ya aceptada discrepan en una instancia nueva, la instancia pasa a `REVISION`. `REVISION` es un estado interno, no una decisión: no es ESCALAR. No se puede exportar `outcomes.jsonl` mientras quede alguna instancia en `REVISION`.

**P22. Proveedores de LLM.** [DECIDIDO]
- El sistema no depende de ningún proveedor. Cualquier API (Anthropic, OpenAI, Gemini, local...) se puede usar.
- Cada papel tiene su propia configuración, cambiable en ejecución: `compilador_a`, `compilador_b`, `extractor_1`, `extractor_2`, `asistente`. Cada uno elige proveedor y modelo.
- [PROPUESTA] Implementación: LiteLLM, que ya ofrece una única interfaz para todos los proveedores (texto, imagen y salida estructurada). Evita escribir un adaptador por proveedor.
- Por defecto, los papeles emparejados (`_a`/`_b`, `_1`/`_2`) usan proveedores distintos, para que no se equivoquen igual.

## 5. Funcionalidades de la primera iteración [PROPUESTA; corte de F11 DECIDIDO]
Objetivo de la iteración 1 (sábado ~14:00): `outcomes.jsonl` del lote 1 correcto y todo el ciclo de reglas funcionando de punta a punta en un proceso.

| # | Funcionalidad | Qué hace | Entra en v1 |
|---|---|---|---|
| F1 | Procesos | Crear, listar y seleccionar procesos. Cada uno con sus reglas, versiones e histórico | Sí |
| F2 | Ingesta | Subir ficheros. Se identifican por hash; se guardan tal cual con el texto completo extraído (texto del PDF u OCR/visión para escaneos) | Sí |
| F3 | Conectores | Excel (maestros) y ERP (API tolerante a fallos). Cada descarga del ERP se guarda como un ingreso | Sí |
| F4 | Extracción de símbolos | Saca de cada instancia los símbolos que usan las reglas, con su origen | Sí |
| F5 | Reglas y compilador | Alta de una regla en texto; dos agentes generan código y tests; tests cruzados, coincidencia sobre el histórico; se activa si no hay discrepancias (P9, P21) | Sí |
| F6 | Motor | Ejecuta todas las reglas activas sobre cada instancia, aplica la precedencia y registra la decisión. Sin LLM | Sí |
| F7 | Histórico y auditoría | Registro de todas las decisiones. Al activar una versión, se reejecuta sobre el histórico: cambios, conflictos y hallazgos | Sí |
| F8 | Escalado asistido | Cola de escalados. El agente sugiere decisión, razonamiento y regla; el responsable acepta o escribe la suya | Sí |
| F9 | Versionado | Lista lineal de versiones; activar una anterior | Iteración 2 [DECIDIDO] |
| F10 | Exportar | Botón para descargar `outcomes.jsonl` con las decisiones actuales | Sí |
| F11 | Crear proceso desde datos | A partir de todos los datos subidos y texto libre, deriva símbolos, reglas y tipos de decisión | Iteración 2 |
| F12 | Autocorrección por revisión | El manager marca un error en una decisión y explica por qué; el agente propone el cambio de regla | Iteración 2 |

Motivo del corte: F11 es lo más difícil de dejar fiable y no hace falta para pasar el filtro. En v1, las reglas de la norma v3 se dan de alta una a una por F5. Así el mismo flujo del producto genera la entrega.

## 6. Arquitectura [PROPUESTA]

**Stack [DECIDIDO]:** backend en Python con FastAPI; base de datos PostgreSQL. Frontend a elegir por Carlos.

### 6.1 Componentes
| Componente | Responsabilidad | ¿Usa LLM? |
|---|---|---|
| Almacén | PostgreSQL: procesos, versiones, reglas, ficheros, instancias, símbolos, decisiones, hallazgos, eventos | No |
| Ingesta | Hash, guardado del fichero, extracción de texto | Solo para escaneos (visión) |
| Conectores | Excel y ERP. El cliente del ERP gestiona token, reintentos, límite de peticiones y cortes | No |
| Extractor de símbolos | Texto de la instancia + fuentes a símbolos con origen | Solo si el texto no se puede leer con reglas fijas |
| Compilador | Regla en texto a código + pruebas | Sí |
| Motor | Ejecuta el código de todas las reglas y decide | **No** |
| Auditor | Reejecuta una versión sobre el histórico y clasifica las diferencias | No |
| Asistente de escalado | Sugiere decisión, razonamiento y regla para un escalado | Sí |
| API + web | Interfaz del responsable | No |

Principio: el LLM nunca está en el camino de la decisión. Solo escribe código de reglas, lee escaneos y sugiere al responsable.

### 6.2 Flujo de una instancia
1. Ingesta: fichero → hash → texto completo guardado.
2. Extracción: texto + fuentes → símbolos con origen.
3. Motor: símbolos + código de la versión activa → resultado de cada regla → decisión.
4. Registro: decisión con símbolos, versión y resultados de cada regla.
5. Si la decisión es ESCALAR → cola del responsable con la sugerencia del asistente.

### 6.3 Flujo de un cambio de regla
1. Texto de la regla (escrita por el responsable o propuesta por el asistente).
2. El compilador genera código y pruebas.
3. El código pasa sus pruebas y todas las decisiones validadas por humanos.
4. El auditor reejecuta sobre el histórico: sin cambio, cambio por revisar, conflicto y hallazgos.
5. El responsable aprueba → versión nueva activa.

## 7. Pendiente [PENDIENTE]
- Interfaz del responsable (pantallas).
- Trazabilidad: formato de eventos y cómo se consulta "por qué se decidió X".
- Encaje con la rúbrica y lista de ADRs.
- Frontend.
- Reparto del trabajo en el equipo.
