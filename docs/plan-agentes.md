# trace-it: plan de los agentes sobre PydanticAI

**Estado:** plan de ejecución. Solo documentación: aún no hay código de este plan.
**Decisión de fondo:** P23 en `docs/plano-aplicacion.md`.
**Fuente de las APIs:** la documentación local de PydanticAI v2 en `.context/pydantic-ai/` (ver "Referencias"). Todo nombre de clase o función de este documento está comprobado ahí. Lo que no aparece en la documentación está en "APIs sin confirmar".

## 0. Decisiones previas (no se reabren)

- PydanticAI sustituye al cliente directo de LiteLLM (`features/llm/cliente.py`) en todos los agentes. LangGraph descartado: la máquina de estados, la cola humana y la idempotencia ya viven en Postgres. Sin dependencia de proveedor (P22).
- Agentes: compilador A y B (ciegos entre sí, P9), asistente de escalado, extractor(es) de símbolos (de Álvaro, sobre la misma infraestructura) y corrector (iteración 2, con tools).
- El LLM nunca decide en el flujo: el motor solo ejecuta código compilado (P7).
- Compilador: su `output_validator` ejecuta `sandbox.comprobar` y los tests **propios** con `sandbox.ejecutar_lote`, y lanza `ModelRetry` con los fallos. Reintentos acotados. Los tests cruzados y el histórico siguen fuera de los agentes, en la función pura `validar`.
- Asistente: su `output_validator` rechaza con `ModelRetry` una decisión que no es un tipo del proceso.
- Extracción: los validadores (IBAN mod-97, letra del NIF, base + IVA = total), ligados a tipos de símbolo y no a nombres de campos de factura, **no** lanzan `ModelRetry`: si fallan, la instancia pasa a `REVISION`. Dos extracciones independientes deben coincidir.
- Configuración por papel: presets en ficheros del repo y versiones en la base de datos, editables en ejecución, sin reinicio y sin perder nunca un experimento (sección 4). Prompts versionados en el repo, con sobrescritura opcional por versión. Claves de API solo en `.env`.
- Trazabilidad: cada ejecución de un agente registra en `eventos` la versión de configuración usada (`config_agente.id`), el papel, el modelo que respondió de verdad, el hash del prompt efectivo, tokens, coste, latencia, reintentos y resultado.

## 1. Qué cambia y qué no

| Pieza | Hoy | Después |
|---|---|---|
| Llamada al LLM | `cliente.completar(session, papel, mensajes, formato)` sobre `litellm.acompletion` | `Agent.run(...)` de PydanticAI, con el modelo construido en cada llamada desde la versión activa del papel |
| Salida estructurada | JSON validado a mano (`model_validate_json`) | `output_type=` del agente |
| Bucle de reparación | Bucle propio con mensajes `assistant`/`user` (`MAX_REPARACIONES`) | `@agente.output_validator` + `ModelRetry` + `retries={'output': N}` |
| Proveedor caído | Error 502 | `FallbackModel` pasa al siguiente modelo de la cadena; si fallan todos, error y traza |
| Coste | `litellm.completion_cost` | `result.usage.cost` (`Decimal` o `None`, calculado con genai-prices) |
| Configuración | `config_llm`: un modelo por papel, se sobrescribe | `config_agente`: versiones por papel, solo se añaden; presets en `agentes/presets/*.json` |
| Tests | `monkeypatch` de `cliente.completar` | `agente.override(model=FunctionModel(...))` y `models.ALLOW_MODEL_REQUESTS = False` |

No cambia: `sandbox.py`, la función pura `validar`, el motor, la cola del responsable y el contrato de `reglas.service.compilar`.

## 2. Arquitectura objetivo

### 2.1 Árbol de ficheros

```
backend/app/
  conftest.py                  # models.ALLOW_MODEL_REQUESTS = False para toda la suite
  features/
    llm/                       # runtime genérico, sin conocer papeles ni tablas
      fabrica.py               # dict de config -> Model (FallbackModel), ModelSettings, UsageLimits
      ejecutar.py              # ejecutar(): run acotado + evento en `eventos` + errores
      tests/test_fabrica.py
      tests/test_ejecutar.py
      (cliente.py, model.py, router.py, schemas.py: se borran en la tarea 8)
    agentes/
      model.py                 # ConfigAgente (tabla config_agente), PAPELES
      config.py                # versión activa, crear versión, activar, presets, exportar, prompt efectivo
      schemas.py               # Config, ConfigVersionIn/Out, SugerenciaOut
      router.py                # /agentes/config..., /agentes/presets/..., sugerencia
      presets/
        calidad.json           # preset por defecto (make setup)
        barato.json
        rapido.json
      prompts/
        compilador.md
        asistente.md
        extractor.md           # lo mantiene Álvaro
        corrector.md           # iteración 2
      compilador.py            # Agent + output_validator (sandbox); validar() sin cambios
      asistente.py             # Agent + output_validator (tipos del proceso)
      corrector.py             # iteración 2: Agent con tools de solo lectura
      sandbox.py               # sin cambios
      tests/
    extraccion/                # Álvaro
      extractor.py             # Agent de extracción sobre features/llm
      validadores.py           # puros, por tipo de símbolo
      service.py               # dos extracciones, comparación, REVISION
      tests/
```

Capas: `llm/` es el runtime y no importa nada de `agentes/`; recibe la configuración ya resuelta. `agentes/` guarda la configuración y define los agentes. `extraccion/` usa `agentes.config` (su `model.py`/servicio, permitido por la guía) y `llm.ejecutar`.

Cada agente es un `Agent` de nivel de módulo, sin modelo fijo (`Agent(None, ...)` está permitido si el modelo se pasa en cada `run`). Las dependencias (`deps_type`) son dataclasses definidas en el módulo de cada agente, solo donde hacen falta (asistente y corrector); no hay un fichero `deps.py` común porque no hay nada que compartir.

### 2.2 Flujo de la configuración

```
  REPO (git)                  POSTGRES                        EJECUCION                    TRAZA
 +----------------------+    +----------------------------+    +------------------------+    +-------------------------+
 | agentes/presets/     | 1  | config_agente              | 3  | en cada llamada:       |    | eventos, paso "agente": |
 |   *.json             |--->|  (solo se anade)           |--->|  version activa        |--->|  config_agente_id       |
 |   modelos, ajustes,  |    |  id, papel, version,       |    |  -> FallbackModel      |    |  papel, version         |
 |   reintentos, limite,|    |  config JSON, prompt?,     |    |  -> ModelSettings      |    |  prompt_hash, modelo    |
 |   prompt .md         |    |  autor, nota, creada,      |    |  -> UsageLimits        |    |  tokens, coste          |
 | agentes/prompts/*.md |    |  activa (1 por papel)      |    |  -> prompt + hash      |    |  latencia, reintentos   |
 +----------------------+    +----------------------------+    +------------------------+    +-------------------------+
            ^                    ^            |
            |                  2 | nueva version / activar (responsable, en caliente)
            +------- 4 exportar -------------+
```

1. `make setup` (o `POST /agentes/presets/{nombre}/aplicar`) carga un preset como versiones nuevas.
2. En ejecución, el responsable crea versiones nuevas y activa cualquiera, también una antigua (vuelta atrás).
3. Cada llamada lee la versión activa y construye el modelo: un cambio vale desde la llamada siguiente, sin reiniciar.
4. Un experimento bueno se exporta como JSON de preset y se sube al repo.

### 2.3 Infraestructura común (`features/llm/`)

**`fabrica.py`** (esbozo; nombres de PydanticAI comprobados):

```python
from functools import cache
from pydantic_ai import ConcurrencyLimitedModel, ConcurrencyLimiter, ModelSettings, UsageLimits
from pydantic_ai.models import Model, infer_model
from pydantic_ai.models.anthropic import AnthropicModel, AnthropicModelSettings
from pydantic_ai.models.fallback import FallbackModel

@cache  # un limitador por proveedor, compartido por todos los papeles
def _limitador(proveedor: str) -> ConcurrencyLimiter:
    return ConcurrencyLimiter(max_running=settings.llm_concurrencia, name=proveedor)

@cache  # un Model (y su cliente HTTP) por nombre, reutilizado
def _modelo(nombre: str, cachear: bool) -> Model:
    proveedor, _, id_modelo = nombre.partition(":")
    if cachear and proveedor == "anthropic":
        base = AnthropicModel(id_modelo, settings=AnthropicModelSettings(
            anthropic_cache_instructions=True, anthropic_cache_tool_definitions=True))
    else:
        base = infer_model(nombre)
    return ConcurrencyLimitedModel(base, limiter=_limitador(proveedor))

def modelo(config: dict) -> Model:
    primero, *resto = [_modelo(n, config.get("cache", False)) for n in config["modelos"]]
    return FallbackModel(primero, *resto) if resto else primero

def ajustes(config: dict) -> ModelSettings:
    return ModelSettings(**config["ajustes"])  # temperature, max_tokens, timeout...

def limites(config: dict) -> UsageLimits:
    return UsageLimits(request_limit=config["limite_peticiones"])
```

- Los nombres de modelo van en el formato de PydanticAI, `proveedor:modelo` (`anthropic:claude-opus-5`, `openai:gpt-5`, `google:gemini-3-flash-preview`). En v2, `openai:` usa la Responses API; `openai-chat:` fuerza Chat Completions.
- La caché es por nombre y no por versión: cambiar la configuración cambia qué nombres se piden, no hay que invalidar nada. Los `Model` viven lo que el proceso (el provider es dueño de su cliente HTTP).
- `ConcurrencyLimitedModel` + un `ConcurrencyLimiter` por proveedor: como mucho `TRACE_LLM_CONCURRENCIA` peticiones a la vez a cada proveedor (por defecto 8), sumando todos los papeles. Es lo que deja lanzar las 540 extracciones con un `gather` sin pasarse de los límites de peticiones.
- `cache: true` en la config activa la caché de prompts de Anthropic en los modelos `anthropic:` de la cadena, como ajuste del propio modelo (la forma documentada de dar ajustes distintos a cada modelo de un `FallbackModel`). Los demás modelos no lo ven.
- `infer_model` comprueba las variables de entorno del proveedor. Se usa también para validar una versión antes de guardarla.

**`ejecutar.py`**: la única forma de llamar a un agente.

```python
@dataclass(frozen=True)
class ConfigActiva:          # lo que `agentes.config` resuelve para un papel
    id: int                  # config_agente.id
    papel: str
    version: int
    config: dict             # modelos, ajustes, reintentos, limite_peticiones, prompt
    prompt: str              # texto efectivo: sobrescritura de la versión o fichero del repo
    prompt_hash: str         # sha256 del texto efectivo, 12 primeros caracteres

async def ejecutar(session, agente, activa: ConfigActiva, entrada, *, deps=None,
                   output_type=None, instancia_id=None, datos=None) -> AgentRunResult:
    # 1. agente.run(entrada, model=modelo(c), instructions=activa.prompt, deps=deps,
    #               output_type=..., model_settings=ajustes(c), usage_limits=limites(c),
    #               retries={"output": c["reintentos"]})
    #    dentro de asyncio.timeout(ajustes.timeout * limite_peticiones)
    # 2. registrar(session, "agente", ...) con el resultado o el error
    # 3. errores de PydanticAI y TimeoutError -> AgenteError (TraceError, 502)
```

- El prompt del papel entra como `instructions=` del `run` (el parámetro existe en `Agent.run`). Así el prompt es dato de la versión y no del código.
- `registrar` solo hace `session.add`, sin E/S: dos `ejecutar` concurrentes sobre la misma sesión (compilador A y B) no chocan si la versión activa se leyó antes del `asyncio.gather`, como hoy `_leer` precarga `ConfigLLM`.
- Se captura: `AgentRunError` (base de `UnexpectedModelBehavior`, `UsageLimitExceeded`, `ModelAPIError`), `FallbackExceptionGroup` (base `ExceptionGroup`) y `TimeoutError`. Todo lo demás es un fallo nuestro y se propaga.

Evento por ejecución (`eventos.paso = "agente"`):

| Campo | De dónde sale |
|---|---|
| `datos.config_agente_id`, `datos.papel`, `datos.version` | `ConfigActiva` |
| `datos.prompt_hash` | hash del prompt efectivo |
| `datos.modelo`, `datos.proveedor` | `result.response.model_name`, `result.response.provider_name` (el que respondió de verdad, tras el fallback) |
| `datos.peticiones`, `datos.tokens_entrada`, `datos.tokens_salida` | `result.usage.requests`, `.input_tokens`, `.output_tokens` |
| `datos.reintentos` | número de `RetryPromptPart` en `result.all_messages()` |
| `datos.resultado`, `datos.error` | `ok` o `error` con el tipo y el mensaje (500 caracteres) |
| `coste` | `result.usage.cost` (`None` si genai-prices no conoce el modelo) |
| `latencia_ms`, `instancia_id` | medido alrededor del `run`; el que pase quien llama |
| resto de `datos` | lo que añade quien llama (`regla_id`...) |

Nota: en v2 `result.usage` es una propiedad, no un método (`result.usage`, no `result.usage()`).

## 3. Agentes

### 3.1 Compilador A y B (Martín)

| | |
|---|---|
| Definición | `compilador = Agent(None, output_type=Propuesta, name="compilador")`. Un solo agente; A y B son dos ejecuciones con papeles distintos (`compilador_a`, `compilador_b`), cada una con su versión activa, sus modelos y su historial. Ninguna ve lo de la otra (P9) |
| `output_type` | `Propuesta` actual: `codigo` + `tests` con `instancia_json`/`fuentes_json`/`otras_json` como texto. Se mantiene: el modo estricto de JSON Schema no admite objetos libres |
| `deps_type` | ninguno |
| Instrucciones | `agentes/prompts/compilador.md` (el `SISTEMA` actual) o la sobrescritura de la versión. El contexto de la regla (`_contexto`) va en el mensaje de usuario |
| Validador | `@compilador.output_validator` async: `_tests(p)` (menos de `MIN_TESTS` o JSON inválido → `ModelRetry`) y `await asyncio.to_thread(_errores_propios, p.codigo, tests)`; si devuelve texto → `ModelRetry(texto)` |
| Reintentos / límites | `reintentos: 2` (equivale al `MAX_REPARACIONES` actual), `limite_peticiones: 4` |
| Invocación | `compilar()` lee las dos versiones activas, luego `asyncio.gather(ejecutar(A), ejecutar(B))`, luego `asyncio.to_thread(validar, ...)` igual que hoy |
| Registra | un evento `agente` por papel (con `regla_id`) y el evento `compilar_regla` actual con `valida` y los `config_agente_id` de A y B. Si A y B acabaron en el mismo proveedor (por fallback), `informe.aviso_mismo_proveedor = true` |
| Fallo | `AgenteError` tras agotar reintentos o modelos → `CompilacionError` (502). `reglas.service.compilar` hace commit de los eventos antes de relanzar |
| Tests | `compilador.override(model=FunctionModel(fn))`: 1) código correcto a la primera → evento con `reintentos=0`; 2) primero código que falla sus tests y luego uno bueno → `reintentos=1` y el mensaje de reintento contiene el test fallido; 3) siempre mal → `CompilacionError`. `validar` conserva sus tests puros. `fn` responde llamando a la tool de salida (`info.output_tools[0].name`) |

Por qué el validador corre en un hilo: `ejecutar_lote` lanza un subproceso y espera hasta 10 s; en el bucle de eventos bloquearía la API. `asyncio.to_thread` ya es el patrón del código actual.

### 3.2 Asistente de escalado (Martín)

| | |
|---|---|
| Definición | `asistente = Agent(None, output_type=_Salida, deps_type=DepsAsistente, name="asistente")` |
| `deps_type` | `@dataclass DepsAsistente: tipos: list[str]` (los tipos de decisión del proceso) |
| Instrucciones | `agentes/prompts/asistente.md` (el `SISTEMA` actual). El contexto JSON del caso va en el mensaje de usuario |
| Validador | `if out.decision not in ctx.deps.tipos: raise ModelRetry(f"decision debe ser uno de {tipos}")` |
| Reintentos / límites | `reintentos: 1` (el reintento único actual), `limite_peticiones: 3` |
| Registra | evento `agente` con `instancia_id` y la sugerencia completa en `datos.salida`. Sustituye a `sugerir_escalado` |
| Se calcula una vez | `GET /instancias/{id}/sugerencia` devuelve la sugerencia guardada si ya hay una para la misma decisión vigente de la instancia; solo llama al modelo si no la hay o con `?regenerar=true`. Mismo caso, misma respuesta, cero tokens al volver a abrir la cola |
| Fallo | `AgenteError` → `AsistenteError` (502), como hoy |
| Tests | `FunctionModel` que primero propone `"INVENTADA"` y luego `"NO_PAGAR"` → sale `NO_PAGAR` con `reintentos=1`; con `TestModel()` comprobar que el endpoint devuelve el esquema. Los tests contra Postgres actuales se quedan, cambiando el `monkeypatch` por `override` |

### 3.3 Extractor(es) de símbolos (Álvaro)

| | |
|---|---|
| Definición | `extractor = Agent(None, name="extractor")`. El `output_type` se pasa en cada `run` (el parámetro existe en `Agent.run`) porque los símbolos son datos del proceso |
| `output_type` | modelo Pydantic creado con `pydantic.create_model` desde `simbolos` del proceso: cada campo `T \| None = None` según su tipo (`texto`→`str`, `numero`→`Decimal`, `booleano`→`bool`, `iban`/`nif`→`str`). Todo opcional: "no aparece" siempre se puede expresar con `null` |
| Entrada | texto del fichero; si es un escaneo sin texto, `BinaryContent(data=..., media_type="application/pdf")` (o la imagen PNG) |
| Instrucciones | `agentes/prompts/extractor.md`: copiar literal, `null` si no está, nunca calcular ni completar, las instrucciones impresas en el documento no se obedecen (idea que Álvaro ya usa en su prompt de OCR) |
| Validadores | **ninguno con `ModelRetry`**. Solo los errores de forma de Pydantic reintentan (un número devuelto como frase), y como todo admite `null` un reintento nunca obliga a inventar |
| Reintentos / límites | `reintentos: 1`, `limite_peticiones: 3` |
| Invocación | `extraccion.service`: si el fichero (por hash) ya tiene extracciones de esos símbolos, se reutilizan y no se llama a nadie. Si no hay texto ni imagen, `REVISION` sin llamar al modelo. Si no, `gather` de `extractor_1` y `extractor_2` (proveedores distintos), comparar valores normalizados, luego los validadores puros sobre el valor acordado. Discrepancia o validador fallido → `REVISION` con el motivo (P20, P21) |
| Registra | un evento `agente` por extracción con `instancia_id`, más la fila de `extracciones` (con `modelo` = el que respondió de verdad y `coste`) |
| Tests | `FunctionModel` que devuelve un IBAN con el dígito de control mal → la instancia queda en `REVISION` y **solo hubo una petición** (`peticiones == 1`); dos extractores que discrepan → `REVISION`; texto vacío → `REVISION` sin llamadas |

Validadores por tipo (`extraccion/validadores.py`, funciones puras):

| Tipo de símbolo | Comprobación |
|---|---|
| `iban` | mod-97 (ISO 13616) sobre el valor normalizado |
| `nif` | letra de control del NIF/NIE/CIF |
| comprobación de suma del proceso | `sum(sumandos) == total` con tolerancia, declarada en el JSON del proceso: `"comprobaciones": [{"tipo": "suma", "sumandos": ["base", "cuota_iva"], "total": "total", "tolerancia": "0.01"}]` |

Los tipos `iban` y `nif` y el campo `comprobaciones` son un cambio del contrato de `procesos` (carpeta de Mateo): se acuerda con él antes (tarea 6).

### 3.4 Corrector (iteración 2, Martín)

| | |
|---|---|
| Definición | `corrector = Agent(None, output_type=ReglaPropuesta, deps_type=DepsCorrector, name="corrector")` |
| `deps_type` | foto en memoria: reglas activas, fuentes, histórico de símbolos y decisiones validadas. Sin `AsyncSession`: las tools no tocan la base de datos |
| Tools | `@corrector.tool` de solo lectura: `probar_codigo(ctx, codigo)` ejecuta un borrador en el sandbox sobre la instancia y las decisiones validadas (con `asyncio.to_thread`), `ver_regla(ctx, id)`. Errores del sandbox → `ModelRetry` en la tool |
| Salida | `ReglaPropuesta(texto, tipo, decision, explicacion)`; validador igual que el asistente (`decision` en los tipos). La propuesta entra como regla en borrador y se compila con A y B como cualquier otra: el corrector nunca escribe código activo |
| Límites | `limite_peticiones: 10`; `UsageLimits(tool_calls_limit=...)` se puede añadir a la config si hace falta |
| Tests | `FunctionModel` que llama a `probar_codigo` y luego devuelve la propuesta |

## 4. Configuración

### 4.1 Tabla `config_agente` (sustituye a `config_llm`)

| Columna | Tipo | Nota |
|---|---|---|
| `id` | `bigint` PK | lo que se guarda en cada evento |
| `papel` | `text` not null | uno de `PAPELES` |
| `version` | `int` not null | 1, 2, 3... por papel; `unique (papel, version)` |
| `config` | `jsonb` not null | forma abajo |
| `prompt` | `text` null | sobrescritura del prompt para experimentar; `null` = fichero del repo |
| `autor` | `text` not null | email del usuario o `preset:<nombre>` |
| `nota` | `text` null | qué se prueba |
| `creada` | `timestamptz` | `created_at` |
| `activa` | `bool` not null default false | índice único parcial `(papel) where activa`: como mucho una activa por papel |

Reglas:
- Nunca se borra una fila ni se cambia su `config`, `prompt`, `autor` o `nota`. Editar es crear una versión nueva.
- La única escritura sobre una fila existente es mover `activa`: desactivar la anterior y activar la nueva en la misma transacción. Cada activación deja un evento `activar_config_agente` (papel, de `id`, a `id`, autor), así se sabe qué estuvo activo y cuándo. (Alternativa descartada por más piezas: una tabla aparte de activaciones.)
- Volver atrás = activar una versión antigua.
- Un papel sin versión activa no ejecuta: `ConflictError` "el papel X no tiene configuración activa: ejecuta make setup".

Forma de `config` (la misma que cada papel de un preset):

```json
{
  "modelos": ["anthropic:claude-opus-5", "anthropic:claude-sonnet-5"],
  "ajustes": {"timeout": 120},
  "reintentos": 2,
  "limite_peticiones": 4,
  "prompt": "compilador.md"
}
```

- `modelos`: cadena de fallback, el primero es el principal. Al menos uno.
- `ajustes`: subconjunto de `ModelSettings` (`temperature`, `max_tokens`, `timeout`, `seed`). `timeout` es obligatorio; `temperature` se omite para modelos que no la aceptan (Claude Opus 4.7/4.8/5 rechazan los ajustes de muestreo; PydanticAI los quita y avisa).
- `reintentos`: presupuesto de reintentos de salida (`retries={'output': N}`).
- `limite_peticiones`: `UsageLimits(request_limit=...)`.
- `prompt`: fichero de `agentes/prompts/`.
- `cache` (opcional, `false` por defecto): caché de prompts de Anthropic en los modelos `anthropic:` de la cadena (7.3).

Validación al crear una versión (`schemas.Config`, Pydantic con `extra="forbid"`): cada modelo con prefijo `proveedor:` y construible con `infer_model` (si falta la clave del proveedor, 422); `reintentos` entre 0 y 5; `limite_peticiones` entre 1 y 20; `timeout` entre 5 y 600; el fichero de prompt existe.

### 4.2 Presets

`backend/app/features/agentes/presets/<nombre>.json`:

```json
{
  "descripcion": "Máxima calidad; proveedores distintos en cada pareja",
  "papeles": {
    "compilador_a": {"modelos": ["anthropic:claude-opus-5", "anthropic:claude-sonnet-5"], "ajustes": {"timeout": 120}, "reintentos": 2, "limite_peticiones": 4, "prompt": "compilador.md"},
    "compilador_b": {"modelos": ["openai:gpt-5", "google:gemini-3-pro-preview"], "ajustes": {"timeout": 120}, "reintentos": 2, "limite_peticiones": 4, "prompt": "compilador.md"},
    "extractor_1":  {"modelos": ["anthropic:claude-sonnet-5", "anthropic:claude-haiku-4-5"], "ajustes": {"temperature": 0, "timeout": 60}, "reintentos": 1, "limite_peticiones": 3, "prompt": "extractor.md", "cache": true},
    "extractor_2":  {"modelos": ["openai:gpt-5-mini", "google:gemini-3-flash-preview"], "ajustes": {"temperature": 0, "timeout": 60}, "reintentos": 1, "limite_peticiones": 3, "prompt": "extractor.md"},
    "asistente":    {"modelos": ["anthropic:claude-opus-5", "openai:gpt-5"], "ajustes": {"timeout": 90}, "reintentos": 1, "limite_peticiones": 3, "prompt": "asistente.md"}
  }
}
```

| Preset | Idea |
|---|---|
| `calidad.json` | el de arriba, por defecto. Los modelos principales son los de la migración inicial de `config_llm` |
| `barato.json` | modelos pequeños en todos los papeles (Sonnet/Haiku, `gpt-5-mini`, Gemini Flash) |
| `rapido.json` | como `barato` pero con `timeout` bajo y `reintentos` 1 |

Las cadenas de cada pareja (`compilador_a`/`_b`, `extractor_1`/`_2`) no comparten proveedor, ni siquiera en el fallback: así un fallo de un proveedor no hace que A y B, o las dos extracciones, acaben en el mismo modelo (P9, P20, P22). Los nombres existen en `KnownModelName` de la documentación local; se comprueban con `infer_model` al cargar el preset.

Aplicar un preset (`agentes.config.aplicar_preset`), por papel: si la versión activa ya tiene esa `config` y ningún `prompt` sobrescrito, no hace nada; si no, crea una versión (`autor = "preset:<nombre>"`) y la activa. `make setup` aplica `calidad` **solo a los papeles sin ninguna versión**: igual que las definiciones de proceso, no pisa lo que se cambió en ejecución.

### 4.3 Prompts

- Por defecto, `agentes/prompts/<fichero>.md`, versionados con git.
- Prompt efectivo = `config_agente.prompt` si no es `null`; si no, el fichero que nombra `config.prompt`.
- Se lee en cada llamada (un fichero pequeño; sin caché, así editar el `.md` en local vale sin reiniciar).
- Hash: `sha256(texto_efectivo)[:12]`, guardado en cada evento. Dos ejecuciones con el mismo hash usaron exactamente el mismo prompt, venga del fichero o de la base de datos.
- Lo variable (regla, símbolos, caso) va siempre en el mensaje de usuario, nunca en el prompt: el prompt es fijo y su hash significa algo. Además deja un prefijo estable para la caché implícita de los proveedores.

### 4.4 Endpoints

Sustituyen a `GET /llm/config` y `PUT /llm/config/{papel}` (avisar a Carlos).

| Método y ruta | Qué hace | Quién |
|---|---|---|
| `GET /agentes/config` | Versión activa de cada papel | cualquiera |
| `GET /agentes/{papel}/config/versiones` | Todas las versiones del papel, la más nueva primero | cualquiera |
| `POST /agentes/{papel}/config` | Cuerpo `{config, prompt?, nota?, activar=false}`. Crea la versión siguiente; `activar` la activa en la misma transacción | responsable |
| `POST /agentes/{papel}/config/{id}/activar` | Activa esa versión (también una antigua) | responsable |
| `POST /agentes/presets/{nombre}/aplicar` | Aplica un preset del repo (4.2) | responsable |
| `GET /agentes/{papel}/config/{id}/exportar` | Devuelve `{"papeles": {papel: config}}`, el formato de preset, más `prompt_texto` si la versión sobrescribe el prompt, para subir el experimento al repo | cualquiera |

`autor` sale de `UsuarioActual` (`X-Usuario-Id`). Errores: papel desconocido → 404; versión de otro papel → 404; config inválida → 422.

Comparar configuraciones después es una consulta sobre `eventos`:

```sql
select datos->>'config_agente_id' as config, count(*) as llamadas,
       avg(latencia_ms) as ms, sum(coste) as usd,
       avg((datos->>'reintentos')::int) as reintentos
from eventos where paso = 'agente' and datos->>'papel' = 'compilador_a'
group by 1;
```

## 5. Integración con el sandbox

| Dónde | Qué se llama | Cómo |
|---|---|---|
| `output_validator` del compilador | `sandbox.comprobar(codigo)` y `sandbox.ejecutar_lote(codigo, tests propios)`, vía `_errores_propios` | `await asyncio.to_thread(...)`; timeout del lote 10 s (el de `ejecutar_lote`); el fallo vuelve al modelo como `ModelRetry` |
| `validar` (puro, fuera del agente) | `ejecutar_lote` con todos los tests A+B y el histórico, sobre los dos códigos | `asyncio.to_thread(validar, ..., sandbox.ejecutar_lote)` tras el `gather`, como hoy. No reintenta: un fallo cruzado lo resuelve el responsable (P9) |
| tools del corrector (iteración 2) | `ejecutar_lote` sobre la instancia y las decisiones validadas | `asyncio.to_thread` dentro de la tool; error → `ModelRetry` |
| motor | `ejecutar` / `ejecutar_lote` | sin cambios, sin LLM |

Tiempos: el validador puede correr hasta `reintentos + 1` veces por compilación, cada una ≤ 10 s de sandbox, y cuenta dentro del límite de reloj de `ejecutar` (`timeout × limite_peticiones`). Con el preset `calidad`: 120 s × 4 = 8 min como techo absoluto por agente; lo normal son 30-60 s.

## 6. Coste y resiliencia

**Coste**
- `UsageLimits(request_limit=...)` por papel acota los reintentos y el bucle de tools. `cost_limit` existe pero es "best-effort" según la documentación (depende de que genai-prices conozca el modelo): no se usa como garantía.
- Modelos por niveles: los papeles de volumen (extracción, ~1.000 llamadas por lote) usan modelos pequeños; los de pocas llamadas (compilador, asistente) usan los grandes. Se cambia por preset, sin tocar código.
- Caché de prompts: solo donde se repite mucho el mismo prefijo, es decir, en la extracción (7.3). En compilador y asistente no compensa (pocas llamadas, prompts de 1-2 k tokens).
- Batch: la documentación local no describe las APIs batch de los proveedores. No se usa.
- `service_tier` (`'flex'` en OpenAI) está documentado; posible palanca para `barato.json`, no en v1.
- Precios de modelos nuevos: `pydantic_ai.prices.update_in_background()` al arrancar, opcional. Sin ella, `coste` puede ser `None` para modelos posteriores a la versión instalada.

**Resiliencia**
- `FallbackModel` pasa al siguiente modelo ante `ModelAPIError` (4xx/5xx). Los errores de validación no provocan fallback: reintentan con el mismo modelo (documentado así).
- `ajustes.timeout` acota cada intento de petición (OpenAI, Anthropic y Google lo aplican). El reloj total de un `run` no lo acota PydanticAI: lo hace `asyncio.timeout` en `ejecutar`.
- Los SDK de OpenAI y Anthropic reintentan solos 2 veces por defecto, lo que retrasa el fallback hasta 3 × `timeout`. En v1 se aceptan; si en pruebas el paso al siguiente modelo tarda demasiado, `fabrica` construye esos proveedores con `max_retries=0` (`AnthropicProvider(anthropic_client=AsyncAnthropic(max_retries=0))`, `OpenAIProvider(openai_client=AsyncOpenAI(max_retries=0))`, documentado) pasando `provider_factory` a `infer_model`.
- Si fallan todos los modelos: `FallbackExceptionGroup` → `AgenteError` → evento con `resultado = "error"` → la operación falla en cerrado:
  - compilar: la regla sigue en borrador, la anterior sigue activa, el proceso no se para (3.2 del plano);
  - asistente: 502; el responsable resuelve sin sugerencia;
  - extracción: la instancia queda en `REVISION` con motivo "modelo no disponible" y cuenta en la cola; nunca se decide sin símbolos.

## 7. Rendimiento, tokens y determinismo

### 7.1 Dónde se gastan los tokens

| Etapa | Cuándo llama al LLM | Llamadas | Orden de magnitud (estimación; se confirma con 7.4) |
|---|---|---|---|
| Compilar | Una vez por cambio de regla, nunca por instancia | 2 agentes × (1 + reparaciones) | ~5 k tokens por petición; la norma v3 entera (~12 reglas) ≈ 24-72 peticiones |
| Motor | Nunca | 0 | 0 tokens por instancia: ejecuta código compilado |
| Asistente | A demanda, por caso escalado, y una sola vez por caso (3.2) | 1-2 | ~5-15 k tokens por sugerencia (lleva el texto del fichero) |
| Extracción | Una vez por fichero, dos lectores | 540 ficheros × 2 = ~1.080 | ~2-3 k tokens por lectura de texto: **la etapa que domina coste y tiempo** |

Tiempo del motor, medido en local (macOS, un código de regla, `sandbox.ejecutar_lote`): 540 casos en ~40 ms en un solo subproceso; ~0,27 s si cada caso lleva las otras 539 instancias en `otras`. El coste está en arrancar el subproceso: `sandbox.ejecutar` caso a caso cuesta ~20 ms por caso. Hoy `decisiones.service.ejecutar` llama a `sandbox.ejecutar` por cada instancia y regla, dentro del bucle de eventos: con 540 instancias y ~12 reglas son ~6.500 subprocesos, ~2 minutos con la API bloqueada. Recomendación para Mateo (fuera de este plan): un `ejecutar_lote` por regla sobre todas las instancias pendientes, en `asyncio.to_thread`. Pasaría a ~12 subprocesos y unos segundos.

### 7.2 Determinismo por construcción

No se confía en `temperature=0`: la propia documentación dice que "incluso con `temperature` 0.0 los resultados no son totalmente deterministas" (`pydantic-ai-settings.md`). El determinismo sale de calcular cada artefacto de un LLM una vez, guardarlo y no volver a llamar:

| Artefacto | Se calcula | Se guarda en | Clave | Quién lo reutiliza |
|---|---|---|---|---|
| Símbolos de un fichero | una vez por fichero y lista de símbolos | `extracciones`, `instancias.simbolos` | hash del fichero (`ficheros.hash`) | motor, auditoría, recompilaciones (histórico), P10 |
| Código de una regla | una vez por texto de regla | `reglas.codigo_a/_b`, `tests_a/_b` | `reglas.hash` (texto + códigos) | motor, auditoría retroactiva |
| Sugerencia del asistente | una vez por caso y decisión vigente | evento `agente` (`datos.salida`) | instancia + decisión | cola del responsable |
| Configuración usada | por llamada | `config_agente` + `eventos.datos.config_agente_id` | `config_agente.id` + `prompt_hash` | comparar experimentos |

Consecuencia: repetir una ejecución o una auditoría (3.6, 3.7 del plano) lee símbolos y código guardados y ejecuta el motor, sin ningún LLM. El resultado es idéntico bit a bit porque las entradas lo son. Lo único que puede variar entre dos compilaciones del mismo texto es el código generado, y eso lo cubren P9 (A y B deben coincidir) y la revisión del responsable antes de activar.

### 7.3 Extracción eficiente

- **Texto antes que visión.** Un PDF con texto va al modelo como el texto de `pdftotext` guardado en `ficheros.texto` (sin tokens de imagen). Solo los escaneos (`texto` vacío) van como `BinaryContent`.
- **Modelos pequeños para texto.** `extractor_1`/`_2` usan modelos pequeños en todos los presets. Si los escaneos necesitan un modelo mayor, se añaden papeles `extractor_escaneo_1`/`_2` con su propia cadena; no antes de medirlo.
- **Nunca se extrae dos veces.** Antes de llamar, `extraccion.service` busca extracciones del mismo hash de fichero con los mismos símbolos. Un símbolo nuevo (P10) se extrae solo, sobre el texto guardado.
- **Caché de prompts (Anthropic).** El prefijo que se repite en las ~540 lecturas de un lector son las instrucciones y el esquema de salida (la tool de salida con los símbolos del proceso). PydanticAI documenta `AnthropicModelSettings.anthropic_cache_instructions` y `anthropic_cache_tool_definitions`, cada uno con un punto de caché; se activan con `"cache": true` en la config (2.3). Lo variable (el texto de la factura) va detrás, en el mensaje de usuario. OpenAI: la documentación solo describe caché con `CachePoint` para GPT-5.6 en adelante, así que en `gpt-5-mini` no contamos con ella. Gemini: exige crear el recurso de caché con el SDK de Google fuera de PydanticAI; no en v1. El efecto se mide en `result.usage.cache_read_tokens` (conviene añadirlo al evento). La documentación local no da el tamaño mínimo de prefijo cacheable: si el prefijo es demasiado corto, `cache_read_tokens` sale 0 y se apaga.
- **Sin Batch API**: no está en la documentación de PydanticAI.
- **Concurrencia acotada.** `extraccion.service` lanza todas las lecturas con `asyncio.gather`; el `ConcurrencyLimiter` por proveedor de `fabrica` deja pasar `TRACE_LLM_CONCURRENCIA` a la vez (documentado: `ConcurrencyLimitedModel`, `ConcurrencyLimiter(max_running=..., name=...)`). Con 8 por proveedor y ~3 s por lectura, 540 ficheros ≈ 540 / 8 × 3 s ≈ 3-4 minutos, con los dos lectores en paralelo porque van a proveedores distintos. Los 429 que aun así lleguen los reintenta el SDK y, si persisten, saltan al siguiente modelo.

### 7.4 Control del presupuesto

- Por ejecución: `UsageLimits(request_limit=...)` y `reintentos` de cada versión de config (sección 4). Una compilación no puede pasar de `limite_peticiones` peticiones por agente, pase lo que pase.
- Por proceso: `GET /procesos/{id}/metricas` (feature `trazas`, tarea 5) agrega `eventos`:
  - por etapa y papel: llamadas, errores, coste total, tokens, latencia p50 y p95 (`percentile_cont` de Postgres);
  - coste por instancia: coste de extracción y asistente / instancias distintas;
  - motor: tiempo por ejecución (necesita un evento `motor` por ejecución en `decisiones.service.ejecutar`, a acordar con Mateo).
- Para eso cada evento `agente` lleva `datos.proceso_id` (quien llama lo pasa en `datos`).
- El mismo endpoint da las cifras de la demo ("0 tokens por decisión; X € por factura extraída; compilar la norma costó Y €") y la evidencia del ADR (P23).

### 7.5 Opción a evaluar, no decidida: extractores compilados

La idea: aplicar a la extracción lo mismo que a las reglas. Un agente escribe, a partir de la lista de símbolos y unos textos de ejemplo de un mismo formato de documento, un parser determinista `extraer(texto) -> dict`; se valida como una regla (dos agentes, tests con los valores ya acordados por la doble extracción LLM de esos ejemplos) y se ejecuta en el sandbox. En ejecución: parser → validadores por tipo → si falla algo o falta un símbolo, lectura LLM como ahora.

| A favor | En contra |
|---|---|
| 0 tokens y milisegundos por fichero una vez compilado el formato | Hace falta agrupar ficheros por formato (por NIF del emisor o por huella del texto); con muchos formatos distintos compensa poco |
| Determinista de verdad, y cuenta la misma historia que las reglas: "todo lo que decide es código compilado" | Frágil ante formatos no vistos: sin el respaldo LLM, un cambio de plantilla rompe en silencio |
| Reutiliza sandbox, compilador y `validar` | Los escaneos siguen necesitando OCR o visión |
| | P20 descarta "parsers por plantilla"; esto solo encaja porque los parsers los generan y validan agentes, y hay que dejarlo escrito en el plano |
| | Las etiquetas de los tests salen de la extracción LLM: no elimina el LLM, lo mueve a la compilación |

Esfuerzo: ~1 día (clave de formato, contrato `extraer`, reutilizar compilador y `validar`, respaldo LLM, métricas de cobertura). Pista a favor: la rama `data-ingestion` de Álvaro ya extrae los 471 PDFs nativos con un parser escrito a mano (`ingesta/pdf/invoice.py`) y su auditoría no encontró discrepancias en los campos revisados: el texto de estos PDFs es regular.

Recomendación: **no antes de H2.** El lote 1 se cierra con la doble extracción LLM, que ya deja guardados los valores acordados. Después de H2, contar formatos distintos con esos datos: si ~20 formatos cubren más del 90 % de los ficheros, compilar extractores para el lote 2 y la demo; si no, no compensa.

## 8. Observabilidad

- **Fuente de verdad: `eventos`.** Es lo que consulta la aplicación, lo que se exporta y lo que se enseña en la demo ("por qué se decidió X"). No depende de ningún servicio externo.
- **OpenTelemetry / Logfire: opcional, apagado por defecto.** PydanticAI emite spans por petición y por tool con `Agent.instrument_all()` o `logfire.instrument_pydantic_ai()`; con `logfire.configure(send_to_logfire='if-token-present')` no se envía nada sin `LOGFIRE_TOKEN`. Sirve para depurar un compilador que reintenta raro, no para la trazabilidad del producto. Si se activa: `InstrumentationSettings(include_content=False)` para no sacar facturas ni prompts del sistema. Requiere el extra `logfire` (tarea 9). En v2 el formato por defecto es la versión 5, con el uso agregado en `gen_ai.aggregated_usage.*`.

## 9. Tareas (una por PR, en orden)

Paquete: **`pydantic-ai-slim[openai,anthropic,google]>=2.45,<3`** (2.45.0 es la última en PyPI a 2026-09-18; `uv.lock` fija la exacta). `slim` porque `pydantic-ai` completo trae además CLI, MCP, evals, web, retries y logfire, que no usamos.

| # | Rama | Quién | Ficheros | Hecho cuando | Tests |
|---|---|---|---|---|---|
| 1 | `feat/agentes-config` | Martín | `pyproject.toml` (añadir `pydantic-ai-slim`), `agentes/model.py`, `agentes/config.py`, `agentes/schemas.py`, `agentes/router.py`, `agentes/presets/*.json`, `agentes/prompts/*.md` (los `SISTEMA` actuales), migración `0005` (crea `config_agente`; `config_llm` se queda hasta la 8), `app/cli.py` (`presets aplicar <nombre> [--si-falta]`), `Makefile` (`setup` aplica `calidad --si-falta`), `.env.example` (`GEMINI_API_KEY` → `GOOGLE_API_KEY`, la variable de PydanticAI) | Los 6 endpoints de 4.4 responden; `make setup` dos veces no crea versiones de más; activar una versión antigua funciona; nunca hay dos activas | versiones y activación contra Postgres; índice único parcial; preset idempotente; exportar → aplicar da la misma config; config inválida → 422 |
| 2 | `feat/llm-ejecutar` | Martín | `llm/fabrica.py`, `llm/ejecutar.py`, `app/conftest.py` | `ejecutar` registra el evento completo en éxito y en error | `FunctionModel` con salida válida → evento con `modelo`, tokens, `config_agente_id`, `prompt_hash`; `FallbackModel(FunctionModel(falla con ModelAPIError), FunctionModel(ok))` → `modelo` es el segundo; todos fallan → `AgenteError` y evento `error`; límite de peticiones → error |
| 3 | `feat/compilador-pydantic-ai` | Martín | `agentes/compilador.py`, `agentes/tests/test_compilador.py`, `reglas/service.py` (commit de eventos al fallar) | `make compilar` compila la norma v3 igual que antes; los eventos traen la versión usada | 3.1 |
| 4 | `feat/asistente-pydantic-ai` | Martín | `agentes/asistente.py`, `agentes/tests/test_asistente.py` | `GET /instancias/{id}/sugerencia` igual que antes, pero devuelve la guardada si existe | 3.2 |
| 5 | `feat/metricas-agentes` | Martín | `trazas/service.py`, `trazas/router.py`, `trazas/schemas.py`, `main.py`; `datos.proceso_id` en los eventos | `GET /procesos/{id}/metricas` devuelve 7.4 para el proceso de facturas | eventos sintéticos → p50/p95 y coste por instancia correctos |
| 6 | `feat/simbolos-validables` | Álvaro con Mateo | `procesos/definicion.py`, `procesos/schemas.py`, `procesos/README.md`, `procesos/pago-facturas.json` (tipos `iban`, `nif`; `comprobaciones`) | el JSON de facturas declara sus tipos y su suma; `gastos-viaje.json` sigue cargando | carga con y sin `comprobaciones`; tipo desconocido → rechazo |
| 7 | `feat/extraccion-agentes` | Álvaro | `extraccion/extractor.py`, `extraccion/validadores.py`, `extraccion/service.py`, `agentes/prompts/extractor.md` | las 500 facturas pasan por doble extracción; ninguna llamada reintenta por un validador; repetir la extracción no llama a ningún modelo (caché por hash) | 3.3, y un test por validador (IBAN, NIF, suma) con casos buenos y malos |
| 8 | `chore/quitar-litellm` | Martín | borrar `llm/cliente.py`, `llm/model.py`, `llm/router.py`, `llm/schemas.py`; `main.py`; migración `0006` (borra `config_llm`); `pyproject.toml` (fuera `litellm`); `docs/guia-equipo.md` | `grep -ri litellm backend` vacío; `make test` en verde | suite completa |
| 9 | `feat/observabilidad-logfire` (opcional) | quien quiera | extra `logfire`, arranque condicionado a `LOGFIRE_TOKEN` | sin token no cambia nada | ninguno nuevo |
| 10 | `feat/corrector` (iteración 2) | Martín | `agentes/corrector.py`, `agentes/prompts/corrector.md`, papel `corrector` en los presets | F12 funciona con propuestas que pasan por A y B | 3.4 |

Qué tiene que adoptar Álvaro (tareas 6 y 7):
- No construir nada sobre `cliente.completar`: desaparece en la 8. Su rama `data-ingestion` aún declara `litellm` en `pyproject.toml`; al hacer rebase, que no lo use.
- Toda llamada a un LLM pasa por `llm.ejecutar` con un papel de `config_agente`. Si el OCR con Gemini (`ingesta/ocr/gemini.py`, hoy `httpx` directo con `GEMINI_API_KEY`) entra en el flujo, se convierte en un agente más (`output_type=str`, entrada `BinaryContent`) con su propio papel, para que quede en la traza y en los presets. Mientras sea un experimento fuera del flujo, puede quedarse como está.
- Validadores sin `ModelRetry` (sección 10).

## 10. Riesgos y qué no hacer

| No hacer | Por qué |
|---|---|
| Lanzar `ModelRetry` cuando falla un validador de extracción (IBAN, NIF, suma) | Le dices al modelo "este IBAN no cuadra, prueba otra vez" y el modelo aprende a devolver un IBAN que cuadre, no el que pone la factura. El validador deja de detectar errores y pasa a fabricar datos plausibles. La salida correcta es `REVISION` |
| Hacer obligatorio un campo de la salida de extracción | Un reintento por "falta el campo" empuja al modelo a rellenarlo. Todo `T \| None` |
| Pasar la `AsyncSession` en `deps` o usarla dentro de validadores o tools | A y B corren a la vez sobre la misma sesión; SQLAlchemy async no admite operaciones concurrentes en una sesión. Las `deps` llevan datos ya leídos |
| Llamar a `agente.run` fuera de `llm.ejecutar` | Se pierde la traza y el `config_agente_id`; deja de poder compararse |
| Meter en el prompt datos del caso | El hash deja de identificar el prompt y se rompe el prefijo estable |
| Ejecutar `sandbox` en el bucle de eventos | Bloquea la API hasta 10 s por lote. Siempre `asyncio.to_thread` |
| Actualizar o borrar filas de `config_agente` (salvo mover `activa`) | Se pierden experimentos y los eventos antiguos apuntan a una config que ya no es la que corrió |
| Usar tools diferidas (`requires_approval`), durable execution (Temporal, DBOS, Prefect) o `pydantic_graph` | La aprobación humana ya es la activación de reglas y la cola en Postgres; los runs duran segundos y se pueden repetir; el flujo ya está en nuestro código. Añadirían estado duplicado fuera de la base de datos |
| Usar `SpendLimits` (`pydantic_ai_harness`) | Es otro paquete y resuelve presupuestos diarios compartidos entre procesos, que no tenemos |
| Confiar en `cost_limit` como tope de gasto | La documentación dice que es aproximado; el tope real es `request_limit` y los límites del proveedor |
| Nombres de modelo sin prefijo (`'gpt-5'`) | En v2 lanzan `UserError` |

Riesgos:
- **Coincidencia por fallback.** Si cae el proveedor principal de A, A y B podrían acabar en la misma familia. Mitigado con cadenas disjuntas por pareja (4.2) y el aviso en el informe (3.1).
- **Cambios de versión menor.** La política de PydanticAI permite cambiar atributos de OpenTelemetry y añadir campos a los mensajes en versiones menores. No dependemos de ninguno: leemos `result.usage` y `result.response`.
- **Modelos que rechazan ajustes.** Claude Opus 5 no acepta `temperature`; PydanticAI la quita y avisa. Por eso los presets no la ponen en los papeles con Opus.

## 11. APIs sin confirmar en la documentación local

- **Que un timeout o un error de conexión llegue a `FallbackModel` como `ModelAPIError`.** La documentación dice que el fallback salta con `ModelAPIError` y que, al expirar `timeout`, "el cliente del proveedor lanza"; no dice si se envuelve. La tarea 2 lo comprueba; si no se envuelve, `fallback_on` acepta un manejador de excepciones propio.
- **Ajustes de un proveedor pasados en el `model_settings` del `run` con un `FallbackModel` mixto** (por ejemplo `anthropic_cache_instructions` con un modelo de OpenAI en la cadena). No documentado; por eso la caché se pone en los ajustes del propio `AnthropicModel` (documentado en "Per-Model Settings").
- **Si `anthropic_cache_tool_definitions` cubre la tool de salida** (la que lleva el esquema de símbolos) además de las tools de función. La documentación habla de "tool definitions" sin distinguir; se ve en `cache_read_tokens`.
- **Tamaño mínimo de prefijo para que la caché de Anthropic actúe.** No está en la documentación local.
- **Si una salida con fallback cuenta como una o varias peticiones en `request_limit`.** No documentado; los presets dejan una petición de margen.
- **APIs batch de los proveedores.** No aparecen en la documentación de PydanticAI.
- **`result.usage()`** como método: en v2 es la propiedad `result.usage`.

## 12. Referencias

Documentación local de PydanticAI (`.context/pydantic-ai/sections/`):

| Decisión | Sección |
|---|---|
| `Agent(...)`, `run(model=, instructions=, output_type=, model_settings=, usage_limits=, retries=)`, `override` | `pydantic-ai-agent.md` (`__init__`, `run`, `override`), `agents.md` |
| `output_validator`, `ModelRetry`, `ToolOutput`, `StructuredDict`, modos de salida | `output.md` |
| Presupuestos de reintento y qué se reintenta | `retries.md`, `agents.md` ("How output retries are enforced") |
| `FallbackModel`, `fallback_on`, ajustes por modelo, `FallbackExceptionGroup` | `model-providers.md` ("Fallback Model"), `pydantic-ai-models-fallback.md`, `pydantic-ai-exceptions.md` |
| `infer_model`, formato `proveedor:modelo`, ciclo de vida del cliente HTTP | `pydantic-ai-models.md`, `model-providers.md` |
| `ModelSettings` (`temperature`, `timeout`) y quién los soporta | `pydantic-ai-settings.md`, `timeouts.md` |
| `UsageLimits`, `RunUsage.cost`, precios | `agents.md` ("Usage Limits"), `pydantic-ai-usage.md` |
| `AgentRunResult.response`, `.usage`, `ModelResponse.model_name`, `.provider_name`, `RetryPromptPart` | `pydantic-ai-run.md`, `pydantic-ai-messages.md`, `retries.md` |
| `RunContext`, `deps_type` | `dependencies.md` |
| Tools del corrector | `function-tools.md`, `timeouts.md` |
| `BinaryContent` para escaneos | `multimodal-input.md` |
| Caché de prompts | `anthropic.md` ("Prompt Caching", "Cache Point Limits"), `openai.md` ("Prompt caching"), `google.md` ("Context caching") |
| Concurrencia por proveedor: `ConcurrencyLimitedModel`, `ConcurrencyLimiter` | `model-providers.md` ("HTTP Request Concurrency"), `pydantic-ai-concurrency.md` |
| `temperature` 0 no es determinista; qué modelos rechazan ajustes de muestreo | `pydantic-ai-settings.md`, `pydantic-ai-profiles.md` (`anthropic_disallows_sampling_settings`) |
| SDK retries y `max_retries=0` | `anthropic.md`, `openai.md`, `retries.md` |
| Tests: `TestModel`, `FunctionModel`, `AgentInfo`, `ALLOW_MODEL_REQUESTS` | `unit-testing.md`, `pydantic-ai-models-function.md`, `pydantic-ai-models-test.md` |
| OpenTelemetry, Logfire, `include_content=False` | `pydantic-logfire-debugging-and-monitoring.md` |
| Programmatic hand-off (nuestro patrón) frente a delegación y grafos | `multi-agent-applications.md` |
| Por qué no durable execution | `durable-execution.md` |
| Cambios de v2 (`openai:` = Responses, `ModelProfile` como `TypedDict`, extras) | `upgrade-guide.md`, `v1-v2-migration-map.md`, `version-policy.md` |
| Comparativas (escritas por Pydantic, con su sesgo) | `pydantic-ai-vs-langchain-langgraph.md`, `pydantic-ai-vs-crewai.md`, `pydantic-ai-vs-claude-agent-sdk.md`, `pydantic-ai-vs-openai-agents-sdk.md` |

Ideas tomadas de repos ganadores (`hackInfo/.context/repos-ganadores/`, `.docs/`). Ninguno usa PydanticAI; lo que se reutiliza es el diseño:
- `prosperai-challenge/src/prosper/llm.py`: timeout explícito por petición (15 s) en vez del de 600 s por defecto, y un modelo de reserva. → `ajustes.timeout` obligatorio y cadena de fallback.
- `prosperai-challenge/tests/test_llm_failure.py`: un test con un LLM que siempre falla comprueba que el sistema degrada sin romperse. → test de "todos los modelos fallan" en la tarea 2.
- `prosperai-challenge` `make mock-eval` (LLM determinista, 5 s, 0 tokens) y `tests/test_prompts.py` (tests sobre los prompts). → `FunctionModel` en todos los tests y un test que carga cada preset y cada prompt.
- `.docs/momentos-de-demo.md` C2 "fallar en cerrado y ruidoso" y C3 "el silencio alucina". → instancias en `REVISION` cuando no hay modelo o no hay texto, sin llamar al LLM.
- `.docs/tecnicas-ganadoras.md` 5 y 6 ("el LLM fuera del camino caliente", "el LLM conversa; otra cosa decide"). → ya es P7; este plan no lo cambia.
