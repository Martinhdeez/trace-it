"""Command line: `uv run python -m app.cli cargar ../procesos/pago-facturas.json [--compilar]`."""

import argparse
import asyncio
import sys
from pathlib import Path

from pydantic import ValidationError

from app.core.database import engine, session_factory
from app.features.procesos.definicion import Definicion, cargar_definicion
from app.features.reglas import service as reglas


async def cargar(fichero: Path, compilar: bool) -> None:
    try:
        datos = Definicion.model_validate_json(fichero.read_text(encoding="utf-8"))
    except ValidationError as e:
        sys.exit(f"{fichero}: definición inválida\n{e}")
    async with session_factory() as session:
        carga = await cargar_definicion(session, datos)
        p = carga.proceso
        print(
            f"Proceso {p.nombre!r} (id {p.id}): {len(p.tipos_decision)} tipos de decisión, "
            f"{len(p.simbolos)} símbolos, {carga.reglas_nuevas} reglas nuevas, "
            f"{carga.usuarios_nuevos} usuarios nuevos"
        )
        if compilar:
            for regla in await reglas.listar(session, p.id, "borrador"):
                if (regla.informe or {}).get("valida"):
                    continue
                try:
                    r = await reglas.compilar(session, regla.id)
                    estado = "válida" if r.informe["valida"] else "con discrepancias"
                except Exception as e:  # one failing rule must not stop the others
                    await session.rollback()
                    estado = f"error: {str(e).splitlines()[0][:150]}"
                print(f"  regla {regla.id} ({regla.decision}): {estado} · {regla.texto[:70]}")
    await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    ordenes = parser.add_subparsers(dest="orden", required=True)
    orden = ordenes.add_parser("cargar", help="Load a process definition (JSON)")
    orden.add_argument("fichero", type=Path)
    orden.add_argument("--compilar", action="store_true", help="Compile the draft rules")
    args = parser.parse_args()
    asyncio.run(cargar(args.fichero, args.compilar))


if __name__ == "__main__":
    main()
