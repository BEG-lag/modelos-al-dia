"""Fichas curadas a mano en ``data/curado/*.yaml`` y su validación.

Lo que ninguna API publica (planes de la app, qué puede hacer cada producto, agentes de
código) vive aquí, con fuente y fecha de verificación por dato.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from .proveedores import CLAVES

CAPACIDADES: dict[str, str] = {
    "razonamiento": "Razonamiento extendido",
    "busqueda_web": "Búsqueda web",
    "investigacion_profunda": "Investigación profunda",
    "generacion_imagen": "Genera imágenes",
    "generacion_video": "Genera video",
    "voz_tiempo_real": "Voz en tiempo real",
    "vision_archivos": "Lee imágenes y archivos",
    "memoria": "Memoria entre chats",
    "agente_navegador": "Agente que navega",
    "uso_computadora": "Usa la computadora",
    "agente_codigo": "Agente de código",
    "ejecucion_codigo": "Ejecuta código",
    "conectores_mcp": "Conectores / MCP",
    "modelos_abiertos": "Modelos de pesos abiertos",
}
CAPACIDADES_AGENTE: dict[str, str] = {
    "mcp": "MCP",
    "subagentes": "Subagentes",
    "ejecucion_en_nube": "Tareas en la nube",
    "pr_automaticos": "Abre PR",
    "revision_codigo": "Revisa código",
    "navegador": "Prueba en navegador",
    "hooks_extensiones": "Hooks y extensiones",
    "memoria_proyecto": "Memoria del proyecto",
    "sdk": "SDK",
}
ESTADOS = {"si", "parcial", "no", "brecha"}
ETIQUETAS = {None, "ESTIMADO", "SUPUESTO", "BRECHA"}
CATEGORIAS = {
    "insignia",
    "razonamiento",
    "equilibrado",
    "rapido",
    "codigo",
    "imagen",
    "video",
    "audio",
    "abierto",
    "embeddings",
    "agente",
    "otro",
}
ESTADOS_MODELO = {"vigente", "legado", "retirado", "preliminar"}


class _Cargador(yaml.SafeLoader):
    """YAML 1.1 lee 'no', 'yes', 'on' y 'off' como booleanos; aquí solo true y false lo son."""


_Cargador.yaml_implicit_resolvers = {
    k: [(tag, rx) for tag, rx in v if tag != "tag:yaml.org,2002:bool"]
    for k, v in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
_Cargador.add_implicit_resolver(
    "tag:yaml.org,2002:bool",
    re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$"),
    list("tTfF"),
)


def _carga(ruta: Path) -> Any:
    return yaml.load(ruta.read_text(encoding="utf-8"), Loader=_Cargador)


def _fecha(valor: Any) -> str | None:
    if isinstance(valor, date):
        return valor.isoformat()
    return str(valor) if valor else None


def _normaliza(obj: Any) -> Any:
    """YAML convierte fechas a ``date``; aquí todo vuelve a texto ISO."""
    if isinstance(obj, dict):
        return {k: _normaliza(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_normaliza(v) for v in obj]
    if isinstance(obj, date):
        return obj.isoformat()
    return obj


def proveedores(root: Path) -> dict[str, dict[str, Any]]:
    carpeta = root / "curado"
    salida = {}
    for clave in CLAVES:
        ruta = carpeta / f"{clave}.yaml"
        if ruta.exists():
            salida[clave] = _normaliza(_carga(ruta))
    return salida


def agentes_codigo(root: Path) -> dict[str, Any]:
    ruta = root / "curado" / "agentes-codigo.yaml"
    return _normaliza(_carga(ruta)) if ruta.exists() else {"productos": []}


# ------------------------------------------------------------------------ validación


def valida(root: Path) -> list[str]:
    """Lista de problemas encontrados (vacía si todo está bien)."""
    problemas: list[str] = []
    carpeta = root / "curado"
    for ruta in sorted(carpeta.glob("*.yaml")):
        if ruta.name.startswith("_"):
            continue
        texto = ruta.read_text(encoding="utf-8")
        if "\u2014" in texto:
            problemas.append(f"{ruta.name}: usa guion largo (U+2014)")
        try:
            datos = _normaliza(_carga(ruta))
        except yaml.YAMLError as exc:
            problemas.append(f"{ruta.name}: YAML inválido ({exc})")
            continue
        if ruta.stem == "agentes-codigo":
            problemas += _valida_agentes(ruta.name, datos)
        elif ruta.stem in CLAVES:
            problemas += _valida_proveedor(ruta.name, ruta.stem, datos)
        else:
            problemas.append(f"{ruta.name}: archivo no esperado en data/curado")
    return problemas


def _valida_capacidades(nombre: str, caps: Any, claves: dict[str, str]) -> list[str]:
    problemas = []
    if not isinstance(caps, dict):
        return [f"{nombre}: falta el bloque de capacidades"]
    for clave in claves:
        valor = caps.get(clave)
        if not isinstance(valor, dict):
            problemas.append(f"{nombre}: falta la capacidad '{clave}'")
        elif valor.get("estado") not in ESTADOS:
            problemas.append(f"{nombre}: estado inválido en '{clave}': {valor.get('estado')!r}")
    return problemas


def _valida_proveedor(nombre: str, clave: str, d: Any) -> list[str]:
    if not isinstance(d, dict):
        return [f"{nombre}: no es un mapa"]
    problemas = []
    if d.get("clave") != clave:
        problemas.append(f"{nombre}: 'clave' debe ser {clave!r}")
    if not _fecha(d.get("verificado")):
        problemas.append(f"{nombre}: falta 'verificado'")
    problemas += _valida_capacidades(nombre, d.get("capacidades"), CAPACIDADES)
    for plan in (d.get("app") or {}).get("planes") or []:
        if not plan.get("nombre"):
            problemas.append(f"{nombre}: plan sin nombre")
    ids = set()
    for m in d.get("modelos") or []:
        mid = m.get("id")
        if not mid:
            problemas.append(f"{nombre}: modelo sin id")
            continue
        if mid in ids:
            problemas.append(f"{nombre}: modelo repetido {mid}")
        ids.add(mid)
        if m.get("categoria") not in CATEGORIAS:
            problemas.append(f"{nombre}: categoría inválida en {mid}: {m.get('categoria')!r}")
        if m.get("estado") not in ESTADOS_MODELO:
            problemas.append(f"{nombre}: estado inválido en {mid}: {m.get('estado')!r}")
        if m.get("etiqueta") not in ETIQUETAS:
            problemas.append(f"{nombre}: etiqueta inválida en {mid}: {m.get('etiqueta')!r}")
        if not m.get("fuente"):
            problemas.append(f"{nombre}: {mid} sin fuente")
    return problemas


def _valida_agentes(nombre: str, d: Any) -> list[str]:
    if not isinstance(d, dict) or not isinstance(d.get("productos"), list):
        return [f"{nombre}: falta la lista 'productos'"]
    problemas = []
    claves = set()
    for p in d["productos"]:
        clave = p.get("clave")
        if not clave or clave in claves:
            problemas.append(f"{nombre}: clave vacía o repetida: {clave!r}")
        claves.add(clave)
        if not p.get("fuente"):
            problemas.append(f"{nombre}: {clave} sin fuente")
        if p.get("etiqueta") not in ETIQUETAS:
            problemas.append(f"{nombre}: etiqueta inválida en {clave}: {p.get('etiqueta')!r}")
        problemas += _valida_capacidades(
            f"{nombre}:{clave}", p.get("capacidades"), CAPACIDADES_AGENTE
        )
    return problemas
