"""``TABLAS.md``: las mismas comparativas que la página, en markdown, para leerlas en GitHub."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import curado
from . import vista as v
from .proveedores import PROVEEDORES

ICONO = {"si": "✅", "parcial": "🟡", "no": "⚪", "brecha": "❓"}
SITE = "https://beg-lag.github.io/modelos-al-dia/"


def _celda(texto: Any) -> str:
    return str(texto if texto is not None else "").replace("|", "\\|").replace("\n", " ").strip()


def _estado(valor: Any) -> str:
    if valor is True:
        return "si"
    if valor is False:
        return "no"
    return valor if valor in ICONO else "brecha"


def _etq(valor: str | None) -> str:
    return {
        "ESTIMADO": " [ESTIMADO]",
        "SUPUESTO": " [SUPUESTO]",
        "BRECHA": " [BRECHA DE DATO]",
    }.get(valor or "", "")


def _tabla(cabecera: list[str], filas: list[list[Any]]) -> str:
    lineas = ["| " + " | ".join(cabecera) + " |", "|" + "|".join("---" for _ in cabecera) + "|"]
    lineas += ["| " + " | ".join(_celda(c) for c in fila) + " |" for fila in filas]
    return "\n".join(lineas)


def _modelo(m: dict[str, Any] | None) -> str:
    if not m:
        return "·"
    nombre = f"**{m.get('nombre') or m.get('id')}**{_etq(m.get('etiqueta'))}"
    datos = []
    if m.get("contexto_tokens"):
        datos.append(f"{v.tokens(m['contexto_tokens'])} ctx")
    if m.get("precio_entrada") is not None or m.get("precio_salida") is not None:
        datos.append(f"{v.precio(m.get('precio_entrada'))}/{v.precio(m.get('precio_salida'))}")
    if m.get("fuente"):
        nombre = f"[{nombre}]({m['fuente']})"
    return nombre + (f"<br>{' · '.join(datos)}" if datos else "")


def generar(root: Path) -> str:
    datos = v.carga(root)
    provs = [p.clave for p in PROVEEDORES]
    nombres = [f"{p.producto} ({p.nombre})" for p in PROVEEDORES]
    partes = [
        "<!-- Archivo generado por `modelos-al-dia build`. No se edita a mano. -->",
        "# Tablas comparativas",
        "",
        f"Datos al **{v.fecha_larga(datos['actualizado'])}**. Versión interactiva: <{SITE}>.",
        "Precios de API en USD por millón de tokens (entrada/salida). Cada dato liga a su fuente.",
        "Etiquetas: [ESTIMADO], [SUPUESTO] y [BRECHA DE DATO] marcan lo que no está confirmado.",
        "",
        "## 1. Modelo insignia y app",
        "",
    ]
    filas = []
    for r in v.resumen(datos):
        p = r["proveedor"]
        precio_app = (
            f"Gratis; de {v.usd(r['precio_min'])} a {v.usd(r['precio_max'])}/mes"
            if r["precio_min"]
            else "s/d"
        )
        filas.append(
            [
                f"**{p.producto}** ({r['ficha'].get('proveedor') or p.nombre})",
                _modelo(r["insignia"]),
                precio_app,
                r["vigentes"],
                v.fecha_corta(r["ficha"].get("verificado")),
            ]
        )
    partes.append(
        _tabla(["App", "Modelo insignia", "Planes", "Modelos vigentes (API)", "Verificado"], filas)
    )

    partes += ["", "## 2. Comparativa por categoría", ""]
    partes.append(
        _tabla(
            ["Categoría", *nombres],
            [
                [f"**{f['etiqueta']}**"] + [_modelo(f["celdas"][k]) for k in provs]
                for f in v.comparativa(datos)
            ],
        )
    )

    partes += [
        "",
        "## 3. Qué puede hacer cada uno",
        "",
        "✅ sí · 🟡 parcial · ⚪ no · ❓ sin dato",
        "",
    ]
    filas = []
    for f in v.capacidades(datos):
        fila = [f"**{f['etiqueta']}**"]
        for k in provs:
            cap = f["celdas"][k]
            est = _estado(cap.get("estado"))
            fila.append(
                f"{ICONO[est]} {cap.get('detalle') or ''}{_etq(cap.get('etiqueta'))}".strip()
            )
        filas.append(fila)
    partes.append(_tabla(["Capacidad", *nombres], filas))

    partes += ["", "## 4. Planes de la app (USD al mes)", ""]
    for p in PROVEEDORES:
        ficha = datos["fichas"].get(p.clave) or {}
        planes = (ficha.get("app") or {}).get("planes") or []
        partes += [f"### {p.producto}", ""]
        partes.append(
            _tabla(
                ["Plan", "USD/mes", "Incluye"],
                [
                    [
                        f"[{pl.get('nombre')}]({pl['fuente']})"
                        if pl.get("fuente")
                        else pl.get("nombre"),
                        pl.get("precio_usd_mes") if pl.get("precio_usd_mes") is not None else "s/d",
                        f"{pl.get('incluye') or ''}{_etq(pl.get('etiqueta'))}",
                    ]
                    for pl in planes
                ],
            )
        )
        partes.append("")

    partes += ["## 5. Agentes de código", ""]
    caps = curado.CAPACIDADES_AGENTE
    filas = []
    for prod in v.agentes(datos):
        c = prod.get("capacidades") or {}
        version = prod.get("_version")
        nombre = (
            f"[**{prod.get('nombre')}**]({prod.get('fuente')})"
            if prod.get("fuente")
            else prod.get("nombre")
        )
        filas.append(
            [
                f"{nombre}{_etq(prod.get('etiqueta'))}<br>{prod.get('empresa')}"
                + (f"<br>`{version['version']}`" if version else ""),
                ", ".join(prod.get("superficies") or []),
                ", ".join(prod.get("modelos") or []),
                prod.get("precio"),
                *[ICONO[_estado((c.get(k) or {}).get("estado"))] for k in caps],
            ]
        )
    partes.append(_tabla(["Producto", "Dónde corre", "Modelos", "Precio", *caps.values()], filas))

    partes += ["", "## 6. Catálogo de la API: modelos de texto vigentes", ""]
    for p in PROVEEDORES:
        modelos = [
            m
            for m in datos["catalogo"]
            if m["proveedor"] == p.clave and m["estado"] == "vigente" and m["tipo"] == "texto"
        ][:15]
        partes += [f"### {p.nombre}", ""]
        partes.append(
            _tabla(
                [
                    "Modelo",
                    "Lanzamiento",
                    "Contexto",
                    "Salida máx.",
                    "$ entrada",
                    "$ salida",
                    "Entrada",
                ],
                [
                    [
                        f"`{m['id']}`",
                        v.fecha_corta(m["lanzamiento"]),
                        v.tokens(m["contexto"]),
                        v.tokens(m["salida_max"]),
                        v.precio(m["precio_entrada"]),
                        v.precio(m["precio_salida"]),
                        v.modalidades(m["entrada"]),
                    ]
                    for m in modelos
                ],
            )
        )
        partes.append("")
    partes.append(
        "Fuente: [models.dev](https://models.dev) y [OpenRouter](https://openrouter.ai/models). "
        "Lista completa (imagen, video, audio, embeddings y obsoletos) en la página y en `data/catalogo.json`."
    )

    partes += ["", "## 7. Novedades de los últimos 30 días", ""]
    recientes = v.novedades_recientes(datos, dias=30)
    partes.append(
        _tabla(
            ["Fecha", "Proveedor", "Origen", "Nota"],
            [
                [
                    v.fecha_corta(n["fecha"], n["precision"]),
                    v.nombre_proveedor(n["proveedor"]),
                    "API" if n["origen"] == "api" else "Blog",
                    f"[{n['titulo']}]({n['url']})",
                ]
                for n in recientes
            ],
        )
    )
    partes.append("")
    return "\n".join(partes)


def escribe_tablas(root: Path, destino: Path) -> None:
    destino.write_text(generar(root), encoding="utf-8")
