# trace-it: guía del equipo

Cómo trabajamos en el repo de trace-it: ramas, commits, estructura del backend y cómo arrancarlo.
Qué construimos y por qué: `docs/plano-aplicacion.md`. Quién hace qué: `docs/plan-mvp.md`.

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
   uv run ruff check . && uv run pytest
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
chore: bump litellm
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
      usuarios/           # usuarios y usuario actual (cabecera X-Usuario-Id)
      procesos/           # procesos, símbolos, tipos de decisión
      ingesta/            # ficheros e instancias, extracción de texto
      fuentes/            # Excel y ERP
      extraccion/         # símbolos con doble extracción LLM
      reglas/             # reglas: alta, estados, activación
      agentes/            # compilador (dos agentes), sandbox, asistente de escalado
      decisiones/         # motor, histórico, auditoría, colas, exportar
      trazas/             # eventos de traza
      llm/                # cliente LiteLLM y modelo por papel
```

### Dentro de cada funcionalidad
| Fichero | Qué contiene |
|---|---|
| `model.py` | Tablas (SQLAlchemy) |
| `schemas.py` | Entrada y salida de la API (Pydantic) |
| `service.py` | Lógica de negocio. Recibe la sesión de base de datos |
| `router.py` | Endpoints. Finos: validan, llaman al servicio y devuelven |
| `tests/` | Tests de esa funcionalidad (`test_*.py`) |
| otros | Piezas propias, con nombre claro: `motor.py`, `sandbox.py`, `erp.py`… |

Reglas:
- Un router **no** hace consultas SQL: llama al servicio.
- Una funcionalidad puede importar el `model.py` o el `service.py` de otra, pero nunca su `router.py`.
- Los errores se lanzan con las clases de `app/common/exceptions.py` (`NotFoundError`, `ConflictError`…). La API los convierte en respuestas JSON.
- Lo que aún no está hecho lanza `NotImplementedYetError` (la API responde 501). Así el contrato existe y el frontend puede trabajar contra él.
- Los nombres de dominio van en español (`proceso`, `regla`, `instancia`), igual que en los documentos.

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
| Martín | `features/agentes/` (compilador, sandbox, asistente), `features/llm/` |
| Mateo | `features/reglas/`, `features/decisiones/` (motor, auditoría, API), `features/procesos/`, `features/usuarios/` |
| Álvaro | `features/ingesta/`, `features/fuentes/` (Excel, ERP), `features/extraccion/` |
| Carlos | `frontend/` |
| Varsovia | `docs/`, ADRs, demo |

Si necesitas cambiar algo en la carpeta de otra persona, habla antes con ella.
