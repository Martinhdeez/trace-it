# trace-it: guía del equipo

Cómo trabajamos en el repo de trace-it: ramas, commits, estructura del backend y cómo arrancarlo.
Qué construimos y por qué: `docs/application-blueprint.md`. Quién hace qué: `docs/mvp-plan.md`.

## Arranque rápido

Requisitos: Docker y [uv](https://docs.astral.sh/uv/).

```bash
make setup      # .env, Postgres + backend, migraciones y proceso "Invoice payment" con sus usuarios
```
API en http://localhost:8000/docs (con el 8000 ocupado: `BACKEND_PORT=8001 make setup`). Entra con `martin@trace-it.local` (`manager`).

| Comando | Qué hace |
|---|---|
| `make compile` | Compila las reglas en borrador (necesita claves de LLM en `.env`) |
| `make erp` | Arranca el ERP del reto |
| `make test` | Tests del backend contra el Postgres local |
| `make down` | Para los contenedores (los datos se quedan) |
| `make reset-db` | **Borra la base de datos** |

Los procesos son ficheros JSON en `processes/` (formato en `processes/README.md`). `make setup` se puede repetir: no duplica nada ni toca reglas activas.

## 1. Git

### Ramas
| Rama | Para qué | Quién escribe |
|---|---|---|
| `main` | Versión estable, la que se enseña | Solo se une desde `dev` cuando todo funciona |
| `dev` | Integración: aquí se juntan todas las funcionalidades | Solo por pull request |
| `feat/<funcionalidad>` | Una funcionalidad nueva | Una persona (o pareja) |
| `fix/<problema>` | Arreglo | Quien lo arregla |
| `docs/<tema>` | Solo documentación | Cualquiera |

Nombres cortos, en minúsculas y con guiones: `feat/cliente-erp`, `feat/compilador-reglas`, `fix/iva-redondeo`.

### Flujo
1. Partir siempre de `dev` actualizado:
   ```bash
   git switch dev && git pull
   git switch -c feat/cliente-erp
   ```
2. Commits pequeños y frecuentes (ver formato abajo).
3. Antes de abrir el PR, traer lo último de `dev` y comprobar que todo pasa:
   ```bash
   git fetch && git rebase origin/dev
   cd backend && uv run ruff check . && uv run ruff format --check . && uv run pytest
   ```
4. Subir la rama y abrir un pull request contra `dev`:
   ```bash
   git push -u origin feat/cliente-erp
   gh pr create --base dev --fill
   ```
5. Otra persona revisa y aprueba. Se une con **squash merge**, así cada funcionalidad queda en `dev` como un solo commit.
6. Borrar la rama tras unirla.

### Reglas
- Nunca hacer push directo a `dev` ni a `main`.
- Nunca `git push --force` sobre ramas compartidas. En tu propia rama, solo `--force-with-lease`.
- Nada de secretos en el repo: las claves van en `.env`, que no se sube. Ver `.env.example`.
- Un PR = una funcionalidad. Si crece mucho, se parte.
- Si tocas un contrato compartido (modelo, esquema o firma de otro módulo), avisa en el grupo antes.

### Formato de commit
Conventional Commits, en inglés, en imperativo:
```
feat(reglas): add cross-test runner for compiled rules
fix(erp): retry on ORA-00600 before renewing token
docs: add team guide
test(motor): cover priority when several rules fire
chore: bump pydantic-ai
```
Tipos: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`. El ámbito entre paréntesis es la carpeta de la feature.

## 2. Estructura del backend

Organizado **por funcionalidad**, no por tipo de fichero. Todo lo de una funcionalidad vive en su carpeta.

```
backend/
  pyproject.toml          # dependencias (uv)
  alembic/                # migraciones de base de datos
  app/
    main.py               # crea la app FastAPI y monta los routers
    models.py             # importa todos los modelos (lo necesita Alembic)
    core/                 # infraestructura: configuración, base de datos
    common/               # utilidades compartidas: errores
    features/
      users/              # usuarios y usuario actual (cabecera X-User-Id)
      processes/          # procesos, símbolos, tipos de decisión
      ingestion/          # ficheros e instancias, extracción de texto
      sources/            # fuentes de verdad: hojas de cálculo y sistemas externos (ERP)
      extraction/         # símbolos con doble extracción LLM
      rules/              # reglas: alta, estados, activación
      agents/             # agentes (compilador A/B, asistente), sandbox, config por versiones, presets y prompts
      decisions/          # motor, histórico, auditoría, colas, exportar
      traces/             # eventos de traza
      llm/                # runtime de PydanticAI: modelo desde la config, ejecución y traza
```

### Dentro de cada funcionalidad
| Fichero | Qué contiene |
|---|---|
| `model.py` | Tablas (SQLAlchemy) |
| `schemas.py` | Entrada y salida de la API (Pydantic) |
| `service.py` | Lógica de negocio. Recibe la sesión de base de datos |
| `router.py` | Endpoints. Finos: validan, llaman al servicio y devuelven |
| `tests/` | Tests de esa funcionalidad (`test_*.py`) |
| otros | Piezas propias, con nombre claro: `engine.py`, `sandbox.py`, `erp.py`… |

Reglas:
- Un router **no** hace consultas SQL: llama al servicio.
- Una funcionalidad puede importar el `model.py` o el `service.py` de otra, pero nunca su `router.py`.
- Los errores se lanzan con las clases de `app/common/exceptions.py` (`NotFoundError`, `ConflictError`…). La API los convierte en respuestas JSON.
- Lo que aún no está hecho lanza `NotImplementedYetError` (la API responde 501). Así el contrato existe y el frontend puede trabajar contra él.
- Todo el código va en inglés (identificadores, base de datos, API, mensajes, prompts): ver `docs/CONVENTIONS.md` y su glosario.

### Agentes (LLM)
Todos los agentes usan PydanticAI v2. Arquitectura, configuración por versiones y tareas: `docs/agents-plan.md`.
- Toda llamada a un LLM pasa por `features/llm/ejecutar.py`, con un papel de `config_agente`: así queda en la traza con su versión de configuración, coste y latencia.
- Los prompts son ficheros en `features/agents/prompts/`. Los datos del caso van en el mensaje, nunca en el prompt.
- En la extracción, un validador que falla manda la instancia a `REVIEW`; nunca se devuelve al modelo con `ModelRetry`.
- Tests sin red: `FunctionModel`/`TestModel` con `agente.override(...)`.
- **Antes de escribir código de PydanticAI, consulta `.context/pydantic-ai/`** (empieza por `START-HERE.md` y `SECTIONS.md`, y abre solo la sección que necesites). Vale para personas y para asistentes de código: la API cambió mucho en la v2 y lo que recuerda un modelo suele ser de la v1. `llms-full.txt` (5,5 MB, la documentación entera) no está en el repo: descárgalo de https://ai.pydantic.dev/llms-full.txt si lo necesitas para buscar.

## 3. Arrancar en local

Requisitos: Docker y [uv](https://docs.astral.sh/uv/).

```bash
cp .env.example .env              # pon tus claves de LLM
docker compose up --build         # Postgres + backend en http://localhost:8000
```
- Documentación de la API: http://localhost:8000/docs
- Las migraciones se aplican solas al arrancar el backend.
- Si el puerto 8000 está ocupado: `BACKEND_PORT=8001 docker compose up --build`.

Trabajar sin Docker para el backend (más rápido para tests):
```bash
docker compose up db -d
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
uv run pytest
uv run ruff check . && uv run ruff format .
```

ERP del reto (en otra terminal):
```bash
cd .context/500-sombras-de-alberto && make erp
```

### Cambiar la base de datos
1. Edita o crea el `model.py` de tu funcionalidad. Si la tabla es nueva, impórtala en `app/models.py`.
2. Genera la migración y **revísala** antes de subirla:
   ```bash
   uv run alembic revision --autogenerate -m "add campo x a reglas"
   ```
3. Si dos personas generan migraciones a la vez, habrá dos "heads". Se resuelve con `uv run alembic merge heads` y se avisa en el grupo.

## 4. Quién toca qué
| Persona | Carpetas |
|---|---|
| Martín | `features/agents/` (compilador, sandbox, asistente, config de agentes), `features/llm/` |
| Mateo | `features/rules/`, `features/decisions/` (motor, auditoría, API), `features/processes/`, `features/users/` |
| Álvaro | `features/ingestion/`, `features/sources/` (Excel, ERP), `features/extraction/` |
| Carlos | `frontend/` |
| Varsovia | `docs/`, ADRs, demo |

Si necesitas cambiar algo en la carpeta de otra persona, habla antes con ella.
