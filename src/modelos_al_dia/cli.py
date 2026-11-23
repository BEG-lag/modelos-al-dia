"""Línea de comandos: ``modelos-al-dia update | build | check | stats``."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date
from pathlib import Path

from . import __version__, store


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="modelos-al-dia", description=__doc__)
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--data", type=Path, default=store.DATA_DIR, help="carpeta de datos")
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    upd = sub.add_parser("update", help="lee las fuentes y actualiza data/")
    upd.add_argument("--today", type=date.fromisoformat, default=None, help="AAAA-MM-DD")

    build = sub.add_parser("build", help="reconstruye el sitio (docs/) y TABLAS.md")
    build.add_argument("--out", type=Path, default=Path("docs"))
    build.add_argument("--tablas", type=Path, default=Path("TABLAS.md"))

    sub.add_parser("check", help="valida las fichas curadas de data/curado")
    sub.add_parser("stats", help="resumen de los datos guardados")

    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    if args.command == "update":
        from .pipeline import actualizar

        hoy = args.today or date.today()
        reporte = actualizar(args.data, hoy)
        print(f"update {hoy}: {len(reporte.ok)} fuentes ok")
        for nombre, error in reporte.fallas.items():
            print(f"  falló {nombre}: {error}")
        print(f"  cambios: {', '.join(reporte.cambios) or 'ninguno'}")
        return 1 if reporte.fallas and not reporte.ok else 0

    if args.command == "build":
        from .site import construir_sitio
        from .tablas import escribe_tablas

        resumen = construir_sitio(args.data, args.out)
        escribe_tablas(args.data, args.tablas)
        print(f"sitio en {args.out}: {resumen}; tablas en {args.tablas}")
        return 0

    if args.command == "check":
        from .curado import valida

        problemas = valida(args.data)
        for p in problemas:
            print(f"  {p}")
        print("fichas curadas: " + ("OK" if not problemas else f"{len(problemas)} problemas"))
        return 1 if problemas else 0

    if args.command == "stats":
        for clave, valor in store.lee(args.data, store.META, {}).items():
            print(f"{clave}: {valor}")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
