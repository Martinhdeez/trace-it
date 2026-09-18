# trace-it: plano de la aplicación

**Estado:** borrador vivo. Se itera hasta tener el plano completo.
**Marcadores:** [DECIDIDO] acordado por el equipo · [PROPUESTA] sugerencia pendiente de validar · [ABIERTO] sin decidir · [DESCARTADO] valorado y rechazado · [PENDIENTE] sección por escribir.

## 1. Visión

trace-it automatiza procesos de decisión de cualquier tipo. Un proceso de decisión tiene siempre la misma forma:

1. **Entradas y fuentes de verdad:** los casos a decidir (documentos, registros) y los datos de referencia contra los que se validan (hojas de cálculo, sistemas externos).
2. **Reglas deterministas** que hay que cumplir, escritas en texto.
3. **Una decisión final** entre los tipos de decisión que define el proceso, algunos de los cuales pueden requerir a una persona.

Los agentes generan, a partir del texto de cada regla, funciones deterministas que la aplican. Deciden esas funciones, nunca un LLM, y solo entre los tipos de decisión configurados en ese proceso. Todo lo propio de un proceso (fuentes, símbolos, reglas, tipos de decisión) son datos, no código. [DECIDIDO]

**Primer proceso: pago de facturas (el reto "500 Sombras de Alberto").** Se decide si pagar cada factura de Alberto:
1. Entradas: PDFs de facturas; fuentes: el Excel de proveedores y pedidos, y el ERP.
2. Reglas: la norma de pagos.
3. Tipos de decisión: PAGAR, NO_PAGAR o ESCALAR (esta última requiere a una persona).

Es el proceso que enseñamos en la demo y con el que se genera la entrega del reto, pero es una instancia del producto, no su definición. [DECIDIDO]

La aplicación mejora con el uso. Cada decisión humana sobre un caso no cubierto por las reglas se convierte en una regla nueva. Así el sistema es cada vez más autónomo y necesita menos a las personas. [DECIDIDO]

## 2. Conceptos

| Concepto | Qué es | Ejemplo en el proceso de facturas |
|---|---|---|
| Proceso | Definición completa: fuentes, símbolos, reglas y tipos de decisión | "Pago de facturas" |
| Fuente de verdad | Datos de referencia contra los que se valida. Cada carga se guarda aparte; la vigente es la última por nombre | Excel de proveedores y pedidos, ERP |
| Instancia | Cada caso que el proceso decide. Tiene un nombre y un fichero de origen | Una factura PDF |
| Estado de la instancia | `PENDIENTE` (sin decidir), `REVISION` (estado interno: extracción o reglas discrepan; no es una decisión) o `DECIDIDA` | |
| Símbolo | Dato con nombre que usan las reglas | `nif`, `iban`, `pedido`, `importe`, `estado_erp` |
| Regla | Condición determinista sobre los símbolos y las fuentes. Es un requisito o una prohibición (P19); si salta, produce el tipo de decisión que tiene asignado y un motivo | "IBAN de la factura ≠ IBAN del maestro" |
| Tipo de decisión | Salidas posibles del proceso. Las define cada proceso, con su prioridad, cuál es la de por defecto y cuáles requieren a una persona (`requiere_persona`) | PAGAR, NO_PAGAR, ESCALAR (esta última con `requiere_persona`) |
| Decisión | Resultado registrado para una instancia, con el resultado de cada regla. Solo se añaden filas; la vigente es la última | |
| Hallazgo | Decisión pasada que una regla nueva dice que fue errónea. Solo avisa, no cambia el pasado (P14) | Factura pagada indebidamente |
| Responsable | Usuario con rol `responsable`: resuelve los casos que requieren persona y activa reglas. El resto de usuarios son `operador` | Alberto |

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
- **Agente compilador.** Lee una regla y escribe el código determinista que la aplica. Se dispara automáticamente cada vez que se añade o cambia una regla: la interfaz encadena "crear regla" y "compilar" (`POST /reglas/{id}/compilar`) y muestra el progreso, porque compilar tarda 30-60 s por las llamadas a los LLM. [DECIDIDO]
- **Decisor (motor).** Para cada instancia, ejecuta el código de todas las reglas activas y resuelve uno de los tipos de decisión del proceso (P19). Se ciñe al resultado del código y no usa LLM (ver P7).

Así la misma instancia con las mismas reglas da siempre el mismo resultado.

Contrato del código de una regla [DECIDIDO, detalle en P18]:
- Es una función pura: recibe los símbolos de la instancia, las fuentes y las demás instancias, y devuelve si la regla salta y un código de motivo. La decisión no la devuelve el código: la fija la regla.
- No tiene red, disco, reloj ni aleatoriedad. La fecha de corte entra como símbolo.
- Se guarda junto al texto de la regla del que sale, con un hash de texto y código.

Validación antes de activar código nuevo [DECIDIDO, detalle en P9 y P21]:
1. Dos agentes generan, cada uno, código y casos de prueba a partir del texto de la regla.
2. Los dos códigos deben pasar todos los casos y coincidir en todo el histórico.
3. Se ejecuta contra el histórico y se muestra qué decisiones cambian (ver P2).
4. El responsable aprueba. Solo entonces la regla pasa a activa.

Si la validación falla, la regla anterior sigue activa y el proceso no se para.

### 3.3 Ejecutar
Para cada instancia, el sistema extrae los símbolos, ejecuta el código de las reglas activas y decide. Si no salta ninguna regla, se aplica el tipo por defecto del proceso. La instancia va a la cola del responsable si la decisión es de un tipo con `requiere_persona` o si queda en `REVISION` (P21). [PENDIENTE: detalle; ver `.artifacts/specs/2026-09-18-reglas-sistema.md` para extracción, ERP y resiliencia]

### 3.4 Escalado asistido [DECIDIDO]
Una instancia está escalada cuando su decisión es de un tipo con `requiere_persona` o cuando está en `REVISION`. El responsable ve:
- el caso y por qué se escaló,
- **la decisión que tomaría el agente y su razonamiento**,
- **la regla nueva que propone el agente** para resolver solo los casos similares futuros.

El responsable tiene dos opciones:
- **Aceptar:** toma la misma decisión que el agente y añade la regla propuesta.
- **Rechazar:** toma su propia decisión y escribe su propia regla.

En los dos casos entra una regla nueva en el proceso. Por eso el proceso aprende de forma continua.

### 3.5 Autocorrección por revisión [DECIDIDO]
El responsable puede revisar cualquier instancia ya decidida, no solo las escaladas. Si encuentra un error, explica por qué ocurrió. El proceso se corrige a sí mismo a partir de esa explicación.
[PROPUESTA] Usar el mismo mecanismo que el escalado: el agente convierte la explicación en un cambio de regla y el responsable lo aprueba.

### 3.6 Registro de decisiones y comprobación de reglas nuevas [DECIDIDO]
Se aplican todas las reglas a cada instancia, con funciones deterministas. Todas las decisiones quedan registradas. Cuando entra una regla nueva, se vuelve a ejecutar sobre las decisiones pasadas para comprobar si con ella todo sigue bien.

[PROPUESTA] Qué guarda cada decisión:
- Instancia: identificador y hash del fichero.
- **Símbolos usados**, con el valor exacto y su origen (texto del fichero o fuente de la que sale; si es un sistema externo, con la fecha de la consulta).
- Versión del conjunto de reglas y resultado de cada regla (se cumple o no, código de motivo).
- Decisión final y quién la tomó: motor o responsable.
- Si un humano la validó o la corrigió: decisión correcta y motivo.

Guardar los símbolos permite repetir la decisión sin volver a leer el fichero ni consultar sistemas externos. Así la comprobación es rápida, gratis y siempre da lo mismo.

[PROPUESTA] Resultado de la comprobación de una regla nueva, por instancia:
- **Sin cambio:** la decisión es la misma.
- **Conflicto:** cambia una decisión que un humano ya validó. Bloquea la activación hasta que el responsable la resuelva (P15).
- **Cambio por revisar:** cambia una decisión que nadie validó. Se muestra al responsable antes de activar.

### 3.7 Auditoría retroactiva [DECIDIDO]
Hay un histórico de todas las decisiones, tomadas por el motor o por personas. Cada vez que se añade una regla, se revisa el histórico para ver si alguna decisión pasada fue incorrecta según la regla nueva. En el proceso de facturas, por ejemplo:
- una factura pagada que no tocaba pagar,
- una factura no pagada que sí había que pagar.

### 3.8 Procesos y versionado de reglas [DECIDIDO]
- **Proceso:** es como una carpeta que contiene unas reglas. Dentro se pueden añadir y quitar reglas.
- Cada proceso tiene **su propio histórico de decisiones** y **su propio versionado de reglas**. Se puede volver a una versión anterior o avanzar a una posterior, como un git simplificado.
- Si se quieren aplicar reglas totalmente distintas, se crea un **proceso independiente**.
- Al ejecutar, se elige qué proceso aplicar. Los procesos no comparten reglas ni histórico.

Detalle en P11 a P16.

## 4. Preguntas abiertas (con recomendación)

**P1. ¿Qué forma tiene una regla nueva?** [DECIDIDO]
La regla se escribe en texto. La aplicación genera por debajo el código que la aplica, de forma automática. Ver P8.

**P2. ¿Una regla nueva se aplica también al pasado?** [DECIDIDO]
Sí, como comprobación: antes de activarla se ejecuta contra todas las decisiones registradas (ver 3.6). El responsable confirma viendo el impacto.

**P3. ¿Qué pasa si dos reglas chocan?** [DECIDIDO]
- **En ejecución:** si saltan varias reglas con decisiones distintas, gana el tipo de decisión de mayor prioridad del proceso (P19). No se escala.
- **Al añadir una regla:** si choca con otra regla activa, se avisa y la regla no entra hasta que el responsable lo resuelva (P21), por ejemplo reescribiendo una de las dos.

**P4. Decisiones que requieren persona y el filtro del reto.** [DECIDIDO]
- Un tipo con `requiere_persona` (ESCALAR en facturas) es una salida válida del proceso: una regla puede darla como solución correcta. La resolución posterior del responsable se guarda aparte y no cambia esa salida.
- Se sabe con qué reglas se tomó cada decisión, así que el aprendizaje posterior no altera lo ya decidido.
- El versionado completo es de la iteración 2.
- La aplicación exporta, por instancia, su nombre y su decisión. `outcomes.jsonl` (`{"file_id", "result"}`) es solo el formato de esa exportación que pide el reto, no un concepto de la aplicación. [DECIDIDO]
- [PROPUESTA] En la iteración 1, cada decisión guarda el hash del código de cada regla aplicada. Es barato y, en la iteración 2, permite asociar las decisiones antiguas a su versión.

**P5. ¿Quién valida el proceso generado al crearlo?** [ABIERTO]
Recomendación: el usuario revisa los símbolos, las reglas y los tipos de decisión extraídos antes de la primera ejecución. Cada regla muestra de dónde sale (hoja de un Excel, frase del texto). Si un error de lectura pasa aquí, se repite en todas las instancias.

**P6. ¿Cómo se representan los símbolos que requieren sistemas externos?** [ABIERTO]
Recomendación: cada fuente de verdad es un conector con un contrato fijo (qué datos da y cómo falla). El ERP del reto es el primer conector. Esto es lo que permite reutilizar el sistema en otros procesos.

**P7. ¿El agente decisor es un LLM?** [DECIDIDO: no]
Si un LLM eligiera qué regla aplicar, la elección no sería determinista y podría saltarse una regla que sí aplicaba.
Decisión:
- Se ejecuta **siempre el código de todas las reglas activas** sobre cada instancia; nadie elige cuáles.
- Los resultados se combinan con la prioridad de los tipos de decisión del proceso (P19). En facturas: ESCALAR > NO_PAGAR > PAGAR.
- El "agente decisor" es ese motor, sin LLM.
- El LLM solo interviene después: explica la decisión y, si la instancia se escala, propone decisión y regla (3.4).

**P8. ¿Código libre o lenguaje de reglas?** [DECIDIDO: código libre]
- El agente compilador genera **código Python** para cada regla, de forma totalmente automática.
- Motivo: las reglas cambian todo el tiempo (se añaden, se quitan, se modifican) y la aplicación debe seguir funcionando sin que nadie toque su código. Además debe servir para cualquier proceso, no solo para el de facturas. Un catálogo cerrado de primitivas obligaría a programar cada tipo de regla nuevo.
- Se descarta el catálogo de primitivas (reglas como datos) por ese motivo.

[DECIDIDO] Ejecución segura del código generado (lo ha escrito un LLM; implementada en `features/agentes/sandbox.py`):
- Comprobación estática antes de aceptarlo: solo imports permitidos (`decimal`, `datetime`, `re`, `math`, `unicodedata`) y nada de `open`, `exec`, `eval`, `__import__` ni acceso a red.
- Ejecución en un proceso aparte, con tiempo máximo, sin red y sin disco.
- La función devuelve un resultado con forma fija: `{salta, motivo}` (P18). Si devuelve otra cosa, falla o se pasa de tiempo, la instancia pasa a `REVISION` con el motivo (P21). Nunca se decide sin esa regla.

**P9. ¿Cómo se sabe que el código generado es correcto?** [DECIDIDO]
1. Dos agentes independientes (a ser posible, modelos distintos). Cada uno escribe, solo a partir del texto de la regla, su código y sus tests: código A + tests A, código B + tests B. Ninguno ve lo del otro.
2. **Todos los tests se pasan por los dos códigos**: el cruce (A con tests B, B con tests A) detecta diferencias de interpretación; los tests propios detectan errores de programación.
3. Los dos códigos deben coincidir en todas las instancias del histórico.
4. El responsable revisa el impacto y activa.
5. En producción se ejecutan los dos códigos. Si no coinciden en una instancia, la instancia pasa a `REVISION` con el motivo (P21).

Si un test falla, no se sabe quién tiene razón (código o test). Lo resuelve el responsable, normalmente aclarando el texto de la regla y recompilando. Coste: dos compilaciones por cambio de regla, no por instancia.
Límite: si los dos agentes malinterpretan igual un texto ambiguo, pasa. Lo cubre la revisión del impacto (paso 4).

**P10. ¿Y si la regla nueva usa un símbolo que no se guardó?** [ABIERTO]
Por ejemplo, en facturas, una regla nueva sobre el "recargo financiero" necesita un campo que antes no se extraía.
Ya se guarda siempre el texto completo de cada fichero (F2, `ficheros.texto`). Recomendación: si falta un símbolo, se extrae del texto guardado (sin volver a leer escaneos) y se registra como símbolo nuevo antes de comprobar la regla. Si el dato viene de un sistema externo, se usa la carga guardada de esa fuente, no el sistema en vivo.

**P11. ¿Cómo se llama la unidad?** [DECIDIDO]
**Proceso.** No existe "proyecto". Ver 3.8.

**P12. ¿Cuándo se crea un proceso nuevo y cuándo una versión nueva?** [DECIDIDO]
- **Versión nueva:** se añaden, quitan o cambian reglas dentro del mismo proceso. Ejemplo en facturas: norma v3 → norma v4.
- **Proceso nuevo:** reglas totalmente distintas. Proceso independiente, con su propio histórico.
- [PROPUESTA] Un proceso nuevo puede crearse copiando las reglas de otro, pero su histórico empieza vacío.

**P13. ¿Qué es una versión y cómo se "vuelve atrás"?** [DECIDIDO]
- El versionado es lineal: un registro de los cambios de reglas del proceso.
- Cada cambio crea una versión nueva e inmutable con la foto completa de las reglas, quién la hizo, el motivo y la instancia que la provocó, si la hay.
- "Volver atrás" activa una versión anterior. No borra nada y queda registrado como un paso más.
- Solo hay una versión activa por proceso. Las instancias nuevas se deciden con ella.

**P14. ¿Qué hace la auditoría retroactiva con una decisión pasada que ahora sale distinta?** [DECIDIDO]
**Nunca cambia el pasado.** Solo avisa: genera información sobre decisiones pasadas erróneas (hallazgos); en facturas, por ejemplo, "pagada indebidamente" o "no pagada debiendo pagarse". Con eso la empresa decide qué hacer (en facturas, reclamar el dinero o pagar lo pendiente). La gestión de ese aviso queda fuera del sistema.

**P15. Si la regla nueva contradice una decisión que validó una persona, ¿quién gana?** [DECIDIDO]
Ninguno de los dos automáticamente. Se marca como conflicto y lo resuelve el responsable.

**P16. ¿Se versionan también los datos (ficheros, fuentes)?** [DECIDIDO: no]
- Los ficheros ingeridos no tienen versiones: se guardan tal cual y no cambian. Lo que cambia son las decisiones sobre ellos.
- Cada decisión del histórico queda asociada a los ficheros con los que se tomó.
- Si un fichero se modifica, se trata como un fichero nuevo. Se identifica por su hash de contenido.
- [PROPUESTA] Un sistema externo (el ERP en facturas) no es un fichero, sino un sistema vivo. Cada descarga se guarda como una carga más de la fuente, con su fecha, igual que un fichero nuevo. Así la regla anterior también le aplica.

**P17. ¿Comparar dos versiones cualesquiera?** [DESCARTADO]
No hace falta como funcionalidad propia: basta con ejecutar una versión y luego otra.

**P18. Datos que recibe la función de una regla.** [DECIDIDO]
Firma única para todas las reglas y todos los procesos:
```python
def evaluar(instancia: dict, fuentes: dict[str, list[dict]], otras: list[dict]) -> dict:
    # devuelve {"salta": bool, "motivo": str}
```
- `instancia`: símbolos de la instancia.
- `fuentes`: última carga de cada fuente, por nombre (en facturas: proveedores, pedidos, foto local del ERP).
- `otras`: símbolos del resto de instancias del proceso, para reglas sobre varias instancias (en facturas: "pedido duplicado").
Función pura: sin red, sin disco, sin reloj.
La decisión no la devuelve el código: la fija la regla en su definición (campo `decision`), que la aprueba una persona. El código solo dice si salta y por qué.

**P19. Tipos de regla y combinación.** [DECIDIDO]
Se ejecutan todas las reglas sobre cada instancia. Hay dos tipos:
- **Requisito:** algo que tiene que cumplirse. Si no se cumple, la regla salta. Ejemplo en facturas: "el IBAN coincide con el del maestro".
- **Prohibición:** algo que no debe darse. Si se da, la regla salta. Ejemplo en facturas: "el ERP dice PAGADA".
Cada regla declara qué decisión produce cuando salta. Si no salta ninguna: la decisión por defecto del proceso. Si saltan varias: gana la de mayor prioridad.

**Tipos de decisión configurables por proceso [DECIDIDO].** Ningún nombre de decisión está fijo en el código. Cada proceso define sus tipos con:
- `prioridad`: gana la mayor si saltan varias reglas;
- `por_defecto`: exactamente uno, se aplica si no salta ninguna;
- `requiere_persona`: las instancias con esa decisión van a la cola del responsable y el asistente propone cómo resolverlas.
En el proceso de facturas: ESCALAR (3, requiere persona) > NO_PAGAR (2) > PAGAR (1, por defecto).

**P20. Extracción de símbolos.** [DECIDIDO]
- Cada proceso define su lista de símbolos (nombre, tipo, descripción).
- Un LLM la rellena con salida estructurada: sobre el texto del fichero, o sobre la imagen si es un escaneo. Sin parsers por plantilla.
- Dos extracciones independientes (proveedores de LLM distintos) deben coincidir. Además, validadores fijos donde apliquen (en facturas: IBAN mod-97, letra del NIF, base + IVA = total).
- Si no coinciden o un validador falla: estado `REVISION` (P21). El fallo de un validador nunca se devuelve al modelo para que lo corrija: aprendería a dar un valor que cuadre en vez del que pone el documento.
- Cada fichero se extrae una sola vez (por su hash) y los símbolos se guardan; repetir decisiones o auditorías no vuelve a llamar al LLM.

**P21. Discrepancias.** [DECIDIDO]
- **Al añadir una regla:** si los dos códigos discrepan, o chocan con otra regla o con una decisión validada, el sistema lo detecta, avisa al usuario y la regla **no entra** hasta que se resuelva.
- **En ejecución:** si las dos extracciones no coinciden, o los dos códigos de una regla ya aceptada discrepan o fallan en una instancia, la instancia pasa a `REVISION`. `REVISION` es un estado interno de la instancia, no una decisión: no es un tipo de decisión del proceso (en facturas, no es ESCALAR). No se puede exportar mientras quede alguna instancia `PENDIENTE` o en `REVISION`.

**P22. Proveedores de LLM.** [DECIDIDO]
- El sistema no depende de ningún proveedor. Cualquier API (Anthropic, OpenAI, Gemini, local...) se puede usar.
- Cada papel tiene su propia configuración, cambiable en ejecución: `compilador_a`, `compilador_b`, `extractor_1`, `extractor_2`, `asistente` (y `corrector` en la iteración 2). Cada uno elige una cadena de modelos (el primero y sus sustitutos si falla un proveedor), sus ajustes, reintentos, límite de peticiones y prompt.
- [DECIDIDO] Implementación: PydanticAI (P23). La configuración sale de presets en el repo y se guarda en la base de datos como versiones que solo se añaden (`config_agente`); cada llamada usa la versión activa de su papel y la anota en la traza. Detalle en `docs/plan-agentes.md`.
- Por defecto, los papeles emparejados (`_a`/`_b`, `_1`/`_2`) usan proveedores distintos, también en sus modelos de sustitución, para que no se equivoquen igual.

**P23. Framework de agentes: PydanticAI.** [DECIDIDO]

*Contexto.* Los agentes (compilador A y B, asistente, extractores y, en la iteración 2, el corrector) llamaban a los LLM con un cliente propio sobre LiteLLM: salida estructurada validada a mano, un bucle de reparación escrito para cada agente, sin cambio de proveedor si uno cae y tests que parchean el cliente. Queríamos lo mismo en todos los agentes: salida tipada, reintentos acotados con el error devuelto al modelo, cadena de modelos de reserva, límites de uso, coste por llamada y tests sin red. Todo sin atarnos a un proveedor (P22) y sin mover el control del flujo fuera de nuestro código: la máquina de estados de instancias y reglas, la cola del responsable y la idempotencia ya viven en Postgres.

*Alternativas.*

| Opción | Por qué no |
|---|---|
| LiteLLM a pelo (lo que había) | Da una interfaz común, pero todo lo demás (validar la salida, reintentar con el error, cadena de reserva, límites, tests) hay que escribirlo en cada agente. Ya teníamos dos bucles de reparación distintos |
| LangGraph | Su valor es el grafo con estado y persistencia propios. Duplicaría lo que ya está en Postgres y sacaría el control del flujo de nuestro código |
| Claude Agent SDK / OpenAI Agents SDK | Cada uno pensado para su proveedor; choca con P22 y con que los papeles emparejados usen proveedores distintos |
| CrewAI | Modela equipos de agentes con roles y tareas que se coordinan solos. Nuestros agentes no conversan entre sí: el flujo lo fija el código y el LLM nunca decide (P7) |
| **PydanticAI** | Elegido |

*Decisión.* Todos los agentes se escriben con PydanticAI v2 (`pydantic-ai-slim`, extras `openai`, `anthropic`, `google`):
- un `Agent` por tipo de agente, con `output_type` tipado;
- `output_validator` + `ModelRetry` donde el error ayuda al modelo a corregirse: el compilador (sandbox y sus propios tests) y el asistente (decisión dentro de los tipos del proceso). Nunca en la extracción (P20);
- `FallbackModel` con la cadena de modelos de cada papel, `UsageLimits` y `timeout` por petición;
- la configuración de cada papel vive en presets del repo (`agentes/presets/*.json`) y en versiones que solo se añaden en `config_agente`, editables en ejecución y sin reinicio;
- cada ejecución deja un evento en `eventos` con la versión de configuración, el modelo que respondió, el hash del prompt, tokens, coste, latencia y reintentos;
- tests con `FunctionModel`/`TestModel` y `agent.override`, sin llamadas reales.
No se usan sus grafos, su ejecución durable ni sus tools con aprobación humana: el flujo, el estado y la aprobación ya están en nuestro código y en Postgres.

*Consecuencias.*
- Desaparecen `features/llm/cliente.py`, `config_llm` y los endpoints `/llm/config`, sustituidos por `config_agente` y `/agentes/.../config` (el frontend cambia de endpoint).
- Los nombres de modelo pasan del formato de LiteLLM (`anthropic/claude-opus-5`) al de PydanticAI (`anthropic:claude-opus-5`). La clave de Gemini se llama `GOOGLE_API_KEY`.
- Se puede comparar configuraciones con datos: cada resultado apunta a la versión exacta que lo produjo.
- Nueva dependencia con cambios frecuentes: se fija la versión (`>=2.45,<3` y `uv.lock`) y la documentación local está en `.context/pydantic-ai/` para no programar contra APIs viejas.
- Riesgo: si todos los modelos de una cadena fallan, el agente falla en cerrado (la regla no se activa, la instancia queda en `REVISION`), nunca decide.

*Evidencia.* Las APIs usadas están comprobadas en la documentación local de PydanticAI v2 (referencias por sección en `docs/plan-agentes.md` §12). Las comparativas con LangGraph, CrewAI y los SDK de Claude y OpenAI están en esa misma documentación y las escribe Pydantic, así que se leen con su sesgo; la razón de fondo para descartarlas es nuestra arquitectura (P7, P22 y el estado en Postgres), no esas tablas. Las cifras de coste y latencia por etapa saldrán de `GET /procesos/{id}/metricas` sobre `eventos` (plan, §7.4).

## 5. Funcionalidades de la primera iteración [PROPUESTA; corte de F11 DECIDIDO]
Objetivo de la iteración 1 (sábado ~14:00): `outcomes.jsonl` del lote 1 correcto y todo el ciclo de reglas funcionando de punta a punta en un proceso.

| # | Funcionalidad | Qué hace | Entra en v1 |
|---|---|---|---|
| F1 | Procesos | Crear, listar y seleccionar procesos. Cada uno con sus reglas, versiones e histórico | Sí |
| F2 | Ingesta | Subir ficheros. Se identifican por hash; se guardan tal cual con el texto completo extraído (texto del PDF u OCR/visión para escaneos) | Sí |
| F3 | Conectores | Hojas de cálculo y sistemas externos (en facturas: Excel de maestros y ERP, con API tolerante a fallos). Cada carga o descarga se guarda aparte | Sí |
| F4 | Extracción de símbolos | Saca de cada instancia los símbolos que usan las reglas, con su origen | Sí |
| F5 | Reglas y compilador | Alta de una regla en texto; dos agentes generan código y tests; tests cruzados, coincidencia sobre el histórico; se activa si no hay discrepancias (P9, P21) | Sí |
| F6 | Motor | Ejecuta todas las reglas activas sobre cada instancia, aplica la prioridad de los tipos de decisión y registra la decisión. Sin LLM | Sí |
| F7 | Histórico y auditoría | Registro de todas las decisiones. Al activar una versión, se reejecuta sobre el histórico: cambios, conflictos y hallazgos | Sí |
| F8 | Escalado asistido | Cola del responsable (tipos con `requiere_persona` y `REVISION`). El agente sugiere decisión, razonamiento y regla; el responsable acepta o escribe la suya | Sí |
| F9 | Versionado | Lista lineal de versiones; activar una anterior | Iteración 2 [DECIDIDO] |
| F10 | Exportar | Descargar nombre y decisión de cada instancia. En facturas, en el formato del reto (`outcomes.jsonl`) | Sí |
| F11 | Crear proceso desde datos | A partir de todos los datos subidos y texto libre, deriva símbolos, reglas y tipos de decisión | Iteración 2 |
| F12 | Autocorrección por revisión | El responsable marca un error en una decisión y explica por qué; el agente propone el cambio de regla | Iteración 2 |

Motivo del corte: F11 es lo más difícil de dejar fiable y no hace falta para pasar el filtro. En v1, las reglas de la norma v3 se dan de alta una a una por F5. Así el mismo flujo del producto genera la entrega.

## 6. Arquitectura [PROPUESTA]

**Stack [DECIDIDO]:** backend en Python con FastAPI; base de datos PostgreSQL. Frontend a elegir por Carlos.

### 6.1 Componentes
| Componente | Responsabilidad | ¿Usa LLM? |
|---|---|---|
| Almacén | PostgreSQL: usuarios, procesos, tipos de decisión, símbolos, fuentes, ficheros, instancias, extracciones, reglas, decisiones, hallazgos, eventos, configuración de los agentes por versiones (`config_agente`); versiones de reglas: iteración 2 | No |
| Ingesta | Hash, guardado del fichero, extracción de texto | Solo para escaneos (visión) |
| Conectores | Hojas de cálculo y sistemas externos. El cliente de un sistema externo gestiona autenticación, reintentos, límite de peticiones y cortes (en facturas: el ERP) | No |
| Extractor de símbolos | Texto de la instancia + fuentes a símbolos con origen | Sí (doble extracción, P20) |
| Compilador | Regla en texto a código + pruebas | Sí |
| Motor | Ejecuta el código de todas las reglas y decide | **No** |
| Auditor | Reejecuta una versión sobre el histórico y clasifica las diferencias | No |
| Asistente de escalado | Sugiere decisión, razonamiento y regla para un escalado | Sí |
| API + web | Interfaz del responsable | No |

Principio: el LLM nunca está en el camino de la decisión. Solo escribe código de reglas, extrae símbolos y sugiere al responsable.

**Capa de agentes [DECIDIDO, P23].** Los componentes que usan LLM (extractor, compilador, asistente) son agentes de PydanticAI sobre una infraestructura común (`features/llm/`): el modelo de cada llamada se construye desde la versión activa de su papel en `config_agente` (cadena de modelos de reserva, ajustes, reintentos, límites y prompt), y cada ejecución deja un evento en `eventos` con esa versión, el modelo que respondió, tokens, coste y latencia. Cada resultado de un LLM (símbolos por fichero, código por regla) se calcula una vez y se guarda; decidir y auditar no vuelven a llamar al LLM. Plan de ejecución: `docs/plan-agentes.md`.

### 6.2 Flujo de una instancia
1. Ingesta: fichero → hash → texto completo guardado.
2. Extracción: texto + fuentes → símbolos con origen.
3. Motor: símbolos + código de la versión activa → resultado de cada regla → decisión.
4. Registro: decisión con símbolos, versión y resultados de cada regla.
5. Si la decisión es de un tipo con `requiere_persona`, o la instancia queda en `REVISION` → cola del responsable con la sugerencia del asistente.

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

El reparto del trabajo está en `docs/plan-mvp.md` y `docs/guia-equipo.md`.
