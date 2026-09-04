#!/usr/bin/env python3
"""Generador de juegos Titi estilo "El Refugio Lógico" (RPG 2D educativo).

Convierte un JSON de lección + el kit visual en un HTML autocontenido listo
para el sandbox de Titi. El motor (World/Player/PythonEngine/UIManager/
Renderer) vive en public/juegos/game_engine_template.html; este script inyecta
la zona, la misión (LESSONS), las páginas del libro (BOOK_PAGES) y el subset
de assets visuales (ASSETS_JS) recortado por capítulo (chapter_asset_sets).

Uso:
    python tools/game_generator.py public/juegos/juego_gl01_clases.json
    python tools/game_generator.py public/juegos/juego_gl02_funciones.json -o inf-220-g2/clases/Juego_gl02_funciones.html

Sigue las reglas del sandbox de Titi: HTML autocontenido, CSP estricta, sin
storage, sin navegación, sin fetch. El score se reporta con el contrato
TITI_SCORE (window.__TITI_ATTEMPT_TOKEN).
"""

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JUEGOS_DIR = ROOT / "public" / "juegos"
SALIDA_DIR = ROOT / "inf-220-g2" / "clases"
TEMPLATE = JUEGOS_DIR / "game_engine_template.html"
STORY_ARC = JUEGOS_DIR / "story_arc.json"
VISUAL_KIT = JUEGOS_DIR / "visual" / "el_refugio_visual_assets_v1.json"
ASSET_RENDERER = JUEGOS_DIR / "visual" / "el_refugio_asset_renderer.js"

VALIDATORS_REGISTRY = {  # kinds soportados (ver template -> VALIDATORS)
    "print_call", "def_exists", "def_return", "function_cases", "structure", "class_cases",
}
ACTIONS_REGISTRY = {  # kinds soportados (ver template -> ACTIONS)
    "fogata", "tienda", "campamento", "station_transition",
}


def js_str(s):
    """Serializa una cadena Python a literal JS (con comillas dobles)."""
    return json.dumps(str(s), ensure_ascii=False)


def js_value(x):
    if isinstance(x, str):
        return js_str(x)
    if isinstance(x, bool):
        return "true" if x else "false"
    if x is None:
        return "null"
    if isinstance(x, (int, float)):
        return repr(x)
    if isinstance(x, list):
        return js_list(x)
    if isinstance(x, dict):
        return js_dict(x)
    raise TypeError(f"tipo no soportado para JS: {type(x)} ({x})")


def js_list(lst):
    return "[" + ", ".join(js_value(x) for x in lst) + "]"


def js_dict(d):
    """Serializa un dict simple a literal JS (valores recursivos)."""
    parts = []
    for k, v in d.items():
        parts.append(f"{js_str(k)}: " + js_value(v))
    return "{ " + ", ".join(parts) + " }"


def py_repr(x):
    """Repr estilo Python para mostrar valores en ejemplos generados:
    str con comillas dobles, listas con corchetes, True/False/None, números."""
    if isinstance(x, bool):
        return "True" if x else "False"
    if x is None:
        return "None"
    if isinstance(x, str):
        return '"' + x.replace("\\", "\\\\").replace('"', '\\"') + '"'
    if isinstance(x, list):
        return "[" + ", ".join(py_repr(v) for v in x) + "]"
    if isinstance(x, dict):
        return "{ " + ", ".join(f'"{k}": {py_repr(v)}' for k, v in x.items()) + " }"
    return repr(x)


def build_lessons_js(lesson):
    """Convierte la misión del JSON a la const LESSONS de JS, generando
    validate()/onSuccess() desde los registros VALIDATORS/ACTIONS."""
    ch_js = []
    for c in lesson["challenges"]:
        v = c["validator"]
        if v["kind"] not in VALIDATORS_REGISTRY:
            raise ValueError(f"validador desconocido: {v['kind']}")
        a = c["successAction"]
        if a["kind"] not in ACTIONS_REGISTRY:
            raise ValueError(f"acción desconocida: {a['kind']}")
        if v["kind"] in ("structure", "class_cases"):
            req_js = js_dict(c.get("requirements", {}))
            validate_js = "function(engine, code){ return VALIDATORS.%s(engine, code, this.requirements); }" % v["kind"]
        else:
            validator_spec = {kk: vv for kk, vv in v.items() if kk != "kind"}
            validate_js = (
                "function(engine, code){ return VALIDATORS.%s(engine, code, %s); }"
                % (v["kind"], js_dict(validator_spec))
            )
        action_spec = {kk: vv for kk, vv in a.items() if kk != "kind"}
        on_success_js = (
            "function(wa, w){ return ACTIONS.%s(wa, w, %s); }" % (a["kind"], js_dict(action_spec))
        )
        parts = [
            "id: " + js_str(c["id"]),
            "title: " + js_str(c["title"]),
            "target: " + js_str(c["target"]),
            "objective: " + js_str(c["objective"]),
            "example: " + js_str(c.get("example", "")),
            "starterCode: " + js_str(c.get("starterCode", "")),
            "hints: " + js_list(c["hints"]),
        ]
        if "classDiagram" in c:
            parts.append("classDiagram: " + js_value(c["classDiagram"]))
        if v["kind"] in ("structure", "class_cases"):
            parts.append("requirements: " + req_js)
        parts.append("validate: " + validate_js)
        parts.append("onSuccess: " + on_success_js)
        parts.append("successDialogue: " + js_list(c["successDialogue"]))
        parts.append("concepts: " + js_list(c["concepts"]))
        ch_js.append("{ " + ", ".join(parts) + " }")
    lesson_js = (
        "{\n"
        "  id: %s, title: %s, concept: %s, zone: %s, story: %s, introTarget: %s,\n"
        "  introDialogue: { speaker: %s, lines: %s },\n"
        "  objectives: %s,\n"
        "  progression: %s, completion: %s, ui: %s, storm: %s,\n"
        "  challenges: [\n    %s\n  ]\n"
        "}" % (
            js_str(lesson["id"]), js_str(lesson["title"]),
            js_str(lesson["concept"]), js_str(lesson["zone"]),
            js_list(lesson["story"]),
            js_str(lesson.get("introTarget", "sabio")),
            js_str(lesson["introDialogue"]["speaker"]),
            js_list(lesson["introDialogue"]["lines"]),
            js_dict(lesson["objectives"]),
            js_dict(lesson.get("progression", {})),
            js_dict(lesson.get("completion", {})),
            js_dict(lesson.get("ui", {})),
            js_dict(lesson.get("storm", {})),
            ",\n    ".join(ch_js),
        )
    )
    return "{\n  %s: %s\n}" % (js_str(lesson["id"]), lesson_js)


def build_book_js(book_pages):
    items = []
    for p in book_pages:
        obj = {"id": p["id"], "title": p["title"]}
        if p.get("unlockedBy"):
            obj["unlockedBy"] = p["unlockedBy"]
        for f in ("what", "syntax", "example", "commonError", "tip"):
            if p.get(f):
                obj[f] = p[f]
        items.append(js_dict(obj))
    return "[\n  " + ",\n  ".join(items) + "\n]"


def build_zone_js(zone):
    return js_dict(zone)


def build_zones_js(zones):
    """Serializa el registro completo de zonas (exterior + interiores)."""
    items = ",\n  ".join(f"{js_str(zid)}: {js_dict(z)}" for zid, z in zones.items())
    return "{\n  " + items + "\n}"


def _all_zones(data):
    """Devuelve {zoneId: zoneData} con la zona exterior como 'exterior'."""
    zones = dict(data.get("zones") or {})
    exterior = data.get("zone")
    if exterior:
        zones["exterior"] = exterior
    if not zones:
        zones["exterior"] = {}
    return zones


def _zone_asset_ids(zone):
    ids = set()
    for n in zone.get("npcs", []):
        if n.get("asset"):
            ids.add(n["asset"])
    for it in zone.get("interactables", []):
        if it.get("asset"):
            ids.add(it["asset"])
        if it.get("markerAsset"):
            ids.add(it["markerAsset"])
    for d in zone.get("decor", []):
        if d.get("asset"):
            ids.add(d["asset"])
    return ids


def build_assets_js(manifest, chapter, zone, zones=None):
    """Recorta el manifest del kit visual al conjunto de assets del capítulo
    más los assets referenciados por las zonas. Devuelve un literal JS compacto."""
    sets = manifest.get("chapter_asset_sets", {})
    ids = set(sets.get(chapter, []))
    ids |= _zone_asset_ids(zone)
    for _zid, zdata in (zones or {}).items():
        ids |= _zone_asset_ids(zdata)
    ids |= {
        "tree_oak", "player_viajero", "npc_alizon", "npc_guardabosques",
        "campfire", "tent_blue", "workbench", "bush_flowers", "flowers_mixed",
        "grass_tufts",
    }
    all_assets = manifest.get("assets", {})
    assets = {aid: all_assets[aid] for aid in sorted(ids) if aid in all_assets}
    out = {
        "kit": manifest.get("kit", {}),
        "palette": manifest.get("palette", {}),
        "renderer_contract": manifest.get("renderer_contract", {}),
        "assets": assets,
        "effects": manifest.get("effects", {}),
    }
    return json.dumps(out, ensure_ascii=False, separators=(",", ":"))


# ---------------------------------------------------------------------------
# Validación de esquema — errores claros con contexto en vez de KeyError crudo
# ---------------------------------------------------------------------------
class SchemaError(ValueError):
    """Error de esquema del JSON de lección, con el campo afectado."""


def _err(campo, mensaje):
    raise SchemaError(f"[{campo}] {mensaje}")


def _validar_weather(weather, prefijo):
    """Valida la configuración de clima de una zona (none/rain/storm/frost)."""
    if not isinstance(weather, dict):
        _err(prefijo, "debe ser un objeto de configuración.")
    mode = weather.get("mode", "none")
    if not isinstance(mode, str) or mode not in {"none", "rain", "storm", "frost"}:
        _err(prefijo + ".mode", "debe ser 'none', 'rain', 'storm' o 'frost'.")
    numeric_limits = {
        "density": (0, 1),
        "dropCount": (0, 600),
        "dropLength": (0, 80),
        "dropSpeed": (0, 1500),
        "wind": (0, 1.5),
        "gust": (0, 0.75),
        "gustPeriod": (0, 30),
        "alpha": (0, 1),
    }
    for field, (minimum, maximum) in numeric_limits.items():
        if field not in weather:
            continue
        value = weather[field]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            _err(f"{prefijo}.{field}", "debe ser un número finito.")
        if value <= minimum or value > maximum:
            _err(f"{prefijo}.{field}", f"debe ser > {minimum} y <= {maximum}.")
    if "dropCount" in weather and not isinstance(weather["dropCount"], int):
        _err(prefijo + ".dropCount", "debe ser un entero positivo.")


def validar_esquema(data, fuente, manifest=None):
    """Valida la estructura del JSON de lección antes de generar. Lanza
    SchemaError con contexto si algo no cumple el esquema documentado."""
    nombre = fuente.name

    for clave in ("meta", "chapter", "zone", "lesson"):
        if clave not in data:
            _err(clave, f"falta la clave '{clave}' en {nombre}")

    meta = data["meta"]
    for c in ("codigo", "titulo"):
        if not meta.get(c):
            _err("meta." + c, f"campo requerido vacío en {nombre}")

    zone = data["zone"]
    for c in ("rows", "cols", "map", "npcs", "interactables", "doors"):
        if c not in zone:
            _err("zone." + c, f"falta la clave '{c}' en la zona")

    mapa = zone["map"]
    filas = len(mapa)
    if filas != zone["rows"]:
        _err("zone.rows", f"map tiene {filas} filas pero zone.rows={zone['rows']}")
    ancho = len(mapa[0]) if mapa else 0
    if ancho != zone["cols"]:
        _err("zone.cols", f"map tiene {ancho} columnas pero zone.cols={zone['cols']}")
    for i, fila in enumerate(mapa):
        if len(fila) != ancho:
            _err("zone.map", f"fila {i} tiene {len(fila)} chars, se esperaba {ancho}")

    weather = zone.get("weather")
    if weather is not None:
        _validar_weather(weather, "zone.weather")

    def _ids_unicos(items, seccion, campo_id="id", requerido=True):
        vistos = set()
        for it in items:
            iid = it.get(campo_id)
            if not iid:
                if requerido:
                    _err(f"{seccion}.id", f"elemento sin '{campo_id}'")
                continue
            if iid in vistos:
                _err(seccion, f"id duplicado '{iid}'")
            vistos.add(iid)
        return vistos

    _ids_unicos(zone.get("npcs", []), "zone.npcs")
    _ids_unicos(zone.get("interactables", []), "zone.interactables")
    _ids_unicos(zone.get("decor", []), "zone.decor", requerido=False)
    _ids_unicos(zone.get("doors", []), "zone.doors")

    # Zonas adicionales (interiores). La zona exterior se llama 'exterior'.
    zonas = data.get("zones") or {}
    if zonas and not isinstance(zonas, dict):
        _err("zones", "debe ser un objeto { zoneId: {...} }.")
    interact_ids = {i["id"] for i in zone["interactables"]}
    for zid, zdata in zonas.items():
        pref = f"zones.{zid}"
        for c in ("rows", "cols", "map", "npcs", "interactables", "doors"):
            if c not in zdata:
                _err(pref + "." + c, f"falta la clave '{c}' en la zona")
        zmap = zdata["map"]
        if len(zmap) != zdata["rows"]:
            _err(pref + ".rows", f"map tiene {len(zmap)} filas pero rows={zdata['rows']}")
        zw = len(zmap[0]) if zmap else 0
        if zw != zdata["cols"]:
            _err(pref + ".cols", f"map tiene {zw} columnas pero cols={zdata['cols']}")
        for i, fila in enumerate(zmap):
            if len(fila) != zw:
                _err(pref + ".map", f"fila {i} tiene {len(fila)} chars, se esperaba {zw}")
        zwc = zdata.get("weather")
        if zwc is not None:
            _validar_weather(zwc, pref + ".weather")
        _ids_unicos(zdata.get("npcs", []), pref + ".npcs")
        _ids_unicos(zdata.get("interactables", []), pref + ".interactables")
        _ids_unicos(zdata.get("decor", []), pref + ".decor", requerido=False)
        _ids_unicos(zdata.get("doors", []), pref + ".doors")
        for it in zdata.get("interactables", []):
            if it.get("id"):
                interact_ids.add(it["id"])
            if it.get("type") == "portal":
                if not it.get("toZone") or it["toZone"] not in zonas and it["toZone"] != "exterior":
                    _err(pref + ".interactables", f"portal '{it.get('id')}' apunta a zona inexistente '{it.get('toZone')}'")
                if "spawnX" not in it or "spawnY" not in it:
                    _err(pref + ".interactables", f"portal '{it.get('id')}' debe definir spawnX/spawnY")

    lesson = data["lesson"]
    for c in ("id", "title", "concept", "zone", "story", "introDialogue",
              "objectives", "challenges"):
        if c not in lesson:
            _err("lesson." + c, f"falta la clave '{c}' en la lección")

    challenges = lesson["challenges"]
    if not challenges:
        _err("lesson.challenges", "la lección debe tener al menos 1 desafío")

    ch_ids = _ids_unicos(challenges, "lesson.challenges")

    npc_ids = {n["id"] for n in zone["npcs"]}
    for ch in challenges:
        cid = ch["id"]
        obj = (ch.get("objective") or "").strip()
        if len(obj) < 25:
            _err(f"lesson.challenges[{cid}].objective",
                 f"objetivo muy corto ({len(obj)} chars). Explica qué funciones definir y qué debe retornar cada una (mín. 25 chars).")
        target = ch.get("target")
        if not target:
            _err(f"lesson.challenges[{cid}].target", "campo requerido vacío.")
        if target not in interact_ids:
            _err(f"lesson.challenges[{cid}].target",
                 f"apunta a interactable '{target}' que no existe en la zona")
        v = ch.get("validator", {})
        if v.get("kind") not in VALIDATORS_REGISTRY:
            _err(f"lesson.challenges[{cid}].validator.kind",
                 f"kind desconocido: {v.get('kind')}. Válidos: {sorted(VALIDATORS_REGISTRY)}")
        a = ch.get("successAction", {})
        if a.get("kind") not in ACTIONS_REGISTRY:
            _err(f"lesson.challenges[{cid}].successAction.kind",
                  f"kind desconocido: {a.get('kind')}. Válidos: {sorted(ACTIONS_REGISTRY)}")
        if not a.get("id") or a.get("id") not in interact_ids:
            _err(f"lesson.challenges[{cid}].successAction.id", "debe apuntar a un interactable existente.")
        if v.get("kind") == "function_cases":
            specs = v.get("functions") or [v]
            if not isinstance(specs, list) or not specs:
                _err(f"lesson.challenges[{cid}].validator.functions", "debe contener funciones a verificar.")
            for s, fn_spec in enumerate(specs):
                if not fn_spec.get("defName") or not isinstance(fn_spec.get("params"), list):
                    _err(f"lesson.challenges[{cid}].validator.functions[{s}]", "requiere defName y params[].")
                cases = fn_spec.get("cases")
                if not isinstance(cases, list) or not cases:
                    _err(f"lesson.challenges[{cid}].validator.functions[{s}].cases", "debe contener al menos un caso oculto.")
                for n, case in enumerate(cases):
                    if not isinstance(case, dict) or not isinstance(case.get("args"), list) or "expected" not in case:
                        _err(f"lesson.challenges[{cid}].validator.functions[{s}].cases[{n}]", "requiere args[] y expected.")
                    if len(case["args"]) != len(fn_spec["params"]):
                        _err(f"lesson.challenges[{cid}].validator.functions[{s}].cases[{n}]", "cantidad de argumentos no coincide con params.")
        if v.get("kind") == "class_cases":
            reqs = ch.get("requirements") or {}
            clases = reqs.get("classes") or []
            if not isinstance(clases, list) or not clases:
                _err(f"lesson.challenges[{cid}].requirements.classes", "debe contener clases a verificar.")
            for ci, cls_spec in enumerate(clases):
                pref = f"lesson.challenges[{cid}].requirements.classes[{ci}]"
                if not cls_spec.get("name"):
                    _err(pref + ".name", "requiere nombre de clase.")
                for m in cls_spec.get("methods", []) or []:
                    if not m.get("name"):
                        _err(pref + ".methods", "cada método requiere nombre.")
                    cases = m.get("cases") or []
                    if not isinstance(cases, list) or not cases:
                        _err(pref + ".methods." + str(m.get("name")) + ".cases", "cada método requiere al menos un caso.")
                    for n, case in enumerate(cases):
                        if not isinstance(case, dict) or not isinstance(case.get("args"), list) or "expected" not in case:
                            _err(pref + ".methods." + str(m.get("name")) + f".cases[{n}]", "requiere args[] y expected.")

        # Validación de classDiagram (si fue provisto)
        cd = ch.get("classDiagram")
        if cd is not None:
            if not isinstance(cd, (list, dict, str)):
                _err(f"lesson.challenges[{cid}].classDiagram", "debe ser una lista de tarjetas, un objeto o string.")
            elif isinstance(cd, list):
                for cidx, card in enumerate(cd):
                    if not isinstance(card, dict) or not (card.get("className") or card.get("name")):
                        _err(f"lesson.challenges[{cid}].classDiagram[{cidx}]", "cada tarjeta requiere 'className'.")

        # Regla pedagógica: prohibido pedir o usar listas/arrays/estructuras complejas en niveles introductorios de POO
        ch_chapter = data.get("chapter", "")
        if ch_chapter in ("clases_y_objetos", "practica_5_objetos", "encapsulamiento", "herencia_polimorfismo") or "objeto" in str(lesson.get("id", "")).lower():
            import re
            FORBIDDEN_TERMS = ["lista", "listas", "array", "arrays", "arreglo", "arreglos", "diccionario", "diccionarios", "tupla", "tuplas"]
            for fterm in FORBIDDEN_TERMS:
                pat = r'\b' + re.escape(fterm) + r'\b'
                if re.search(pat, ch.get("objective", ""), re.IGNORECASE):
                    _err(f"lesson.challenges[{cid}].objective", f"prohibido el uso o mención de estructuras complejas ('{fterm}') en nivel introductorio.")
                for hi, htext in enumerate(ch.get("hints", [])):
                    if re.search(pat, htext, re.IGNORECASE):
                        _err(f"lesson.challenges[{cid}].hints[{hi}]", f"prohibido mencionar estructuras complejas ('{fterm}') en pistas.")

        if a.get("kind") == "station_transition":
            if a.get("id") != target:
                _err(f"lesson.challenges[{cid}].successAction.id", "debe coincidir con target en una transición de estación.")
            station = None
            for _z in _all_zones(data).values():
                for it in _z.get("interactables", []):
                    if it["id"] == target:
                        station = it
            if station is None:
                _err(f"lesson.challenges[{cid}].target", "la estación target no existe en ninguna zona.")
            if station.get("missionNode") != cid:
                _err(f"lesson.challenges[{cid}].target", "la estación target debe enlazar este desafío mediante missionNode.")

    if manifest:
        assets = manifest.get("assets", {})
        for _z in _all_zones(data).values():
            for section in ("npcs", "interactables", "decor"):
                for item in _z.get(section, []):
                    asset_id = item.get("asset")
                    if asset_id and asset_id not in assets:
                        _err(f"zone.{section}[{item.get('id', item.get('kind', '?'))}].asset", f"asset '{asset_id}' inexistente.")

    for _z in _all_zones(data).values():
        for it in _z["interactables"]:
            node = it.get("missionNode")
            if node and node not in ch_ids:
                _err(f"zone.interactables[{it['id']}].missionNode", f"apunta a desafío '{node}' inexistente.")
            if manifest:
                marker_id = it.get("markerAsset")
                if marker_id and marker_id not in manifest.get("assets", {}):
                    _err(f"zone.interactables[{it['id']}].markerAsset", f"asset '{marker_id}' inexistente.")
            state_map = it.get("stateMap")
            if state_map is not None:
                missing_states = {"pending", "active", "completed"} - set(state_map)
                if missing_states:
                    _err(f"zone.interactables[{it['id']}].stateMap", f"faltan estados: {sorted(missing_states)}")
                if manifest:
                    asset = manifest.get("assets", {}).get(it.get("asset"), {})
                    available = set(asset.get("states", {})) | set(asset.get("extraStates", {}))
                    unknown = set(state_map.values()) - available
                    if unknown:
                        _err(f"zone.interactables[{it['id']}].stateMap", f"estados no presentes en asset: {sorted(unknown)}")

    intro_target = lesson.get("introTarget")
    if intro_target and intro_target not in npc_ids and intro_target not in interact_ids:
        _err("lesson.introTarget", f"apunta a '{intro_target}' inexistente.")

    # El cierre (último desafío) debe usar campamento si hay sendero que abrir
    ultimo = challenges[-1]
    progression_mode = lesson.get("progression", {}).get("mode", "sequential")
    if progression_mode not in ("sequential", "free"):
        _err("lesson.progression.mode", "debe ser 'sequential' o 'free'.")
    if progression_mode == "free":
        mission_nodes = [it.get("missionNode") for it in zone["interactables"] if it.get("missionNode")]
        duplicates = sorted({node for node in mission_nodes if mission_nodes.count(node) > 1})
        missing = sorted(ch_ids - set(mission_nodes))
        extra = sorted(set(mission_nodes) - ch_ids)
        if duplicates or missing or extra:
            _err("zone.interactables.missionNode", f"progresión libre requiere cobertura 1:1; duplicados={duplicates}, faltantes={missing}, extra={extra}")
    if progression_mode != "free" and ultimo["successAction"].get("kind") != "campamento" and zone.get("doors"):
        _err("lesson.challenges[último].successAction.kind",
             "el desafío final debe usar kind 'campamento' para abrir el sendero")

    return data


# ---------------------------------------------------------------------------
# Autocompletado pedagógico: example/starterCode/hints derivados del validador.
# Hace que un desafío quede bien explicado aunque el autor omita esos campos:
# los casos de prueba definen qué mostrar como ejemplo y qué firmas pedir.
# ---------------------------------------------------------------------------
def _firmas_validator(v):
    """Devuelve [(defName, params)] pedidas por el validador del desafío."""
    if v.get("kind") == "function_cases":
        return [(f["defName"], list(f.get("params", []))) for f in (v.get("functions") or [])]
    if v.get("kind") in ("def_return", "def_exists"):
        return [(v["defName"], list(v.get("params", [])))]
    return []


def _casos_validator(v):
    """Devuelve [(defName, params, caso)] con args/expected para derivar ejemplos."""
    casos = []
    if v.get("kind") == "function_cases":
        for f in (v.get("functions") or []):
            for c in f.get("cases", []):
                casos.append((f["defName"], f.get("params", []), c))
    elif v.get("kind") == "def_return":
        casos.append((v["defName"], v.get("params", []),
                      {"args": v.get("sampleArgs", []), "expected": v.get("expected")}))
    return casos


def _caso_borde(caso):
    """True si el caso toca límites (cero, negativos, vacíos, None, False)."""
    exp = caso.get("expected")
    if exp is None or exp == [] or exp == 0 or exp is False or exp == "":
        return True
    args = caso.get("args", [])
    return (any(isinstance(a, (int, float)) and a < 0 for a in args)
            or any(a == [] for a in args))


def _autoejemplo(v):
    """Deriva un ejemplo 'fn(args) -> resultado' de los casos de prueba:
    un caso normal y un caso límite, para que el alumno vea el contrato."""
    casos = _casos_validator(v)
    if not casos:
        return ""
    normales = [c for c in casos if not _caso_borde(c[2])]
    elegidos = []
    if normales:
        elegidos.append(normales[0])
    bordes = [c for c in casos if _caso_borde(c[2])]
    if bordes:
        elegidos.append(bordes[0])
    lineas = []
    for n, (fn, _params, caso) in enumerate(elegidos[:2], 1):
        args = ", ".join(py_repr(a) for a in caso.get("args", []))
        lineas.append(f"Ejemplo {n}\n{fn}({args}) -> {py_repr(caso.get('expected'))}")
    return "\n\n".join(lineas)


def _autostarter(v):
    """Deriva el esqueleto 'def fn(...): return None' de cada función pedida."""
    firmas = _firmas_validator(v)
    if not firmas:
        return ""
    bloques = []
    for nombre, params in firmas:
        bloques.append(f"def {nombre}({', '.join(params)}):\n    return None")
    return "\n\n".join(bloques)


def _autohints(v, hints):
    """Garantiza al menos 3 pistas. Respeta las del autor y completa con
    pistas genéricas útiles (firma, casos límite, return) cuando faltan."""
    auto = []
    firmas = _firmas_validator(v)
    if firmas:
        nombres = ", ".join(n for n, _ in firmas)
        auto.append(f"Definí las funciones pedidas con la firma exacta: {nombres}.")
    if any(p for _n, p in firmas):
        auto.append("Validá los casos límite (cero, negativos, listas vacías) antes de calcular.")
    auto.append("Cada función debe devolver su resultado con return, sin usar print.")
    resultado = list(hints)
    for h in auto:
        if len(resultado) >= 3:
            break
        if h not in resultado:
            resultado.append(h)
    return resultado


def autocompletar_leccion(lesson):
    """Completa example/starterCode/hints de cada desafío desde su validador
    cuando el autor los dejó vacíos. No toca valores explícitos.
    Devuelve [(challenge_id, [campos_autocompletados])]."""
    autollenos = []
    for ch in lesson["challenges"]:
        v = ch.get("validator", {})
        relleno = set()
        if not ch.get("example"):
            ej = _autoejemplo(v)
            if not ej and v.get("kind") == "class_cases":
                ej = _autoejemplo_class(ch.get("requirements") or {})
            if ej:
                ch["example"] = ej
                relleno.add("example")
        if not ch.get("starterCode"):
            st = _autostarter(v)
            if not st and v.get("kind") == "class_cases":
                st = _autostarter_class(ch.get("requirements") or {})
            if st:
                ch["starterCode"] = st
                relleno.add("starterCode")
        if not ch.get("classDiagram") and v.get("kind") in ("class_cases", "structure"):
            cd = _autoclassdiagram(ch)
            if cd:
                ch["classDiagram"] = cd
                relleno.add("classDiagram")
        antes = len(ch.get("hints", []))
        ch["hints"] = _autohints(v, ch.get("hints", []))
        if len(ch["hints"]) > antes:
            relleno.add("hints")
        if relleno:
            autollenos.append((ch["id"], sorted(relleno)))
    return autollenos


def _autoclassdiagram(ch):
    """Deriva un diagrama de clase UML básico a partir de requirements si no se definió."""
    reqs = ch.get("requirements") or {}
    classes = reqs.get("classes") or []
    if not classes:
        return None
    cards = []
    vistas = set()
    for cs in classes:
        cname = cs.get("name")
        if not cname or cname in vistas:
            continue
        vistas.add(cname)
        attrs = []
        for pa in (cs.get("privateAttrs") or []):
            attrs.append(f"- __{pa}")
        if cs.get("initArgs"):
            attrs.append(f"- atributos ({len(cs['initArgs'])} params)")
        methods = []
        for m in (cs.get("methods") or []):
            prefix = "~" if m.get("classMethod") else "+"
            methods.append(f"{prefix} {m['name']}()")
        cards.append({
            "className": cname,
            "attributes": attrs,
            "methods": methods
        })
    return cards if cards else None


def _autoejemplo_class(reqs):
    """Deriva un ejemplo POO: instancia la clase con initArgs y muestra el
    resultado de un caso de cada método."""
    clases = (reqs.get("classes") or [])
    if not clases:
        return ""
    lineas = []
    for cs in clases:
        args = ", ".join(py_repr(a) for a in (cs.get("initArgs") or []))
        lineas.append(f"{cs['name']}({args})")
        for m in (cs.get("methods") or [])[:2]:
            casos = (m.get("cases") or [])
            if casos:
                c = casos[0]
                cargs = ", ".join(py_repr(a) for a in (c.get("args") or []))
                lineas.append(f"{cs['name']}.{m['name']}({cargs}) -> {py_repr(c.get('expected'))}")
    return "\n".join(lineas)


def _autostarter_class(reqs):
    """Deriva un esqueleto de clase: class + __init__ con self.attr.
    Deduplica clases repetidas (varias specs prueban instancias distintas)
    fusionando los métodos únicos por nombre."""
    clases = (reqs.get("classes") or [])
    if not clases:
        return ""
    # Fusionar specs de la misma clase: usar initArgs de la primera y
    # conservar métodos únicos (primera aparición por nombre).
    unidas = {}
    for cs in clases:
        nombre = cs.get("name")
        if not nombre:
            continue
        if nombre not in unidas:
            unidas[nombre] = {
                "name": nombre,
                "initArgs": cs.get("initArgs"),
                "initParams": cs.get("initParams"),
                "methods": {},
            }
        for m in (cs.get("methods") or []):
            unidas[nombre]["methods"].setdefault(m.get("name"), m)
    bloques = []
    for cs in unidas.values():
        params = (cs.get("initParams") or [])
        if not params and cs.get("initArgs"):
            params = [f"param{i}" for i in range(len(cs["initArgs"]))]
        lineas = [f"class {cs['name']}:"]
        if params:
            lineas.append(f"    def __init__(self, {', '.join(params)}):")
            for p in params:
                if p == "self":
                    continue
                lineas.append(f"        self.{p} = {p}")
            lineas.append("")
        for m in cs["methods"].values():
            if m.get("name") == "__init__":
                continue
            cargs = ((m.get("cases") or [{}])[0].get("args") or []) if (m.get("cases") or []) else []
            ps = ["self"] + [f"arg{i}" for i in range(len(cargs))]
            if m.get("classMethod"):
                ps = ["cls"] + ps[1:]
                lineas.append("    @classmethod")
            lineas.append(f"    def {m['name']}({', '.join(ps)}):")
            lineas.append("        return None")
        bloques.append("\n".join(lineas))
    return "\n\n".join(bloques)


def auditar_calidad(lesson, chapter=""):
    """Reporte de calidad pedagógica por desafío (objetivo claro, casos
    suficientes, ejemplo y esqueleto presentes, diagrama de clase en POO y sin
    estructuras complejas no autorizadas). Devuelve cantidad de problemas."""
    problemas = 0
    for ch in lesson["challenges"]:
        cid = ch["id"]
        v = ch.get("validator", {})
        flags = []
        if len((ch.get("objective") or "").strip()) < 25:
            flags.append("objetivo corto (<25 chars)")
            problemas += 1
        if not ch.get("example") and v.get("kind") in ("function_cases", "def_return", "class_cases"):
            flags.append("sin ejemplo")
            problemas += 1
        if not ch.get("starterCode"):
            flags.append("sin starterCode")
            problemas += 1
        if len(ch.get("hints", [])) < 2:
            flags.append("pocas pistas (<2)")
            problemas += 1
        if v.get("kind") in ("class_cases", "structure"):
            if not ch.get("classDiagram"):
                flags.append("sin classDiagram (obligatorio para POO)")
                problemas += 1
        if chapter in ("clases_y_objetos", "practica_5_objetos", "encapsulamiento", "herencia_polimorfismo") or "objeto" in str(lesson.get("id", "")).lower():
            import re
            FORBIDDEN_TERMS = ["lista", "listas", "array", "arrays", "arreglo", "arreglos", "diccionario", "diccionarios", "tupla", "tuplas"]
            texto_total = " ".join([ch.get("objective", "")] + ch.get("hints", []) + ch.get("concepts", []))
            for term in FORBIDDEN_TERMS:
                if re.search(r'\b' + re.escape(term) + r'\b', texto_total, re.IGNORECASE):
                    flags.append(f"estructura compleja no permitida ('{term}')")
                    problemas += 1
        if v.get("kind") == "class_cases":
            reqs = ch.get("requirements") or {}
            por_metodo = {}
            for cs in (reqs.get("classes") or []):
                for m in (cs.get("methods") or []):
                    key = (cs["name"], m["name"])
                    por_metodo.setdefault(key, 0)
                    por_metodo[key] += len((m.get("cases") or []))
            for (cname, mname), total in sorted(por_metodo.items()):
                if total < 2:
                    flags.append(f"{cname}.{mname}: <2 casos de prueba")
                    problemas += 1
        if v.get("kind") == "function_cases":
            for f in (v.get("functions") or []):
                if len(f.get("cases", [])) < 2:
                    flags.append(f"{f['defName']}: <2 casos de prueba")
                    problemas += 1
        estado = (f"objective={len((ch.get('objective') or '').strip())}c "
                  f"diagram={'sí' if ch.get('classDiagram') else 'no'} "
                  f"example={'sí' if ch.get('example') else 'no'} "
                  f"starterCode={'sí' if ch.get('starterCode') else 'no'} "
                  f"hints={len(ch.get('hints', []))}")
        print(f"  [{cid}] {ch['title']}")
        print(f"      {estado}")
        for flag in flags:
            print(f"      ! {flag}")
    return problemas


# ---------------------------------------------------------------------------
# Esqueleto de lección nueva (--nuevo)
# ---------------------------------------------------------------------------
SKELETON = {
    "meta": {
        "materia": "INF-220 · Programación Orientada a Objetos",
        "codigo": "GLXX",
        "titulo": "Título del Capítulo",
        "duracion": "3 h de laboratorio",
        "semestre": "Ing. Informática · 2º semestre · Gestión 2026-02"
    },
    "chapter": "clases_y_objetos",
    "zone": {
        "rows": 14,
        "cols": 20,
        "map": [
            "TTTTTTTTTTTTTTTTTTTT",
            "TPPPPPPPPPPPPPPPPPPT",
            "TPPPPPPPPPPPPPPPPPPT",
            "TPPPPPPPPPPPPPPPPPPT",
            "TPPPPPPPPPPPPPPPPPPT",
            "TPPPPPPPPPPPPPPPPPPT",
            "TPPPPPPPPPPPPPPPPPPT",
            "TPPPPPPPPPPPPPPPPPPT",
            "TPPPPPPPPPPPPPPPPPPT",
            "TPPPPPPPPPPPPPPPPPPT",
            "TPPPPPPPPPDPPPPPPPPT",
            "TGGGGGGGGGGGGGGGGGGT",
            "TGGGGGGGGGGGGGGGGGGT",
            "TTTTTTTTTTTTTTTTTTTT"
        ],
        "flags": {
            "fogataLit": False,
            "tiendaArmada": False,
            "campamentoListo": False,
            "senderoAbierto": False
        },
        "npcs": [
            {
                "id": "alizon", "x": 128, "y": 224, "w": 26, "h": 28,
                "sprite": "alizon", "asset": "npc_alizon", "name": "Alizon",
                "style": "blue", "dialogue": ["Diálogo de Alizon."]
            }
        ],
        "interactables": [
            {
                "id": "fogata01", "type": "fogata", "asset": "campfire",
                "x": 304, "y": 76, "w": 32, "h": 32,
                "missionNode": "challenge1",
                "solid": {"x": 5, "y": 20, "w": 22, "h": 12}, "sortOffset": 30
            }
        ],
        "decor": [],
        "doors": [
            {"id": "sendero", "x": 320, "y": 320, "tileRow": 10, "tileCol": 10}
        ]
    },
    "lesson": {
        "id": "mi_leccion",
        "title": "Capítulo X · Título",
        "concept": "mi_concepto",
        "zone": "claro_del_bosque",
        "story": ["Historia del capítulo."],
        "introDialogue": {
            "speaker": "El Guardabosques",
            "lines": ["Línea de bienvenida."]
        },
        "objectives": {
            "intro": "Habla con El Guardabosques.",
            "challenge1": "Resuelve el primer desafío."
        },
        "challenges": [
            {
                "id": "challenge1",
                "title": "Título del Desafío",
                "target": "fogata01",
                "objective": "Define la función mi_funcion(x) que retorna <resultado>. Explica el contrato: qué recibe, qué calcula y qué devuelve en los casos límite (cero, negativos, vacíos).",
                "example": "",
                "starterCode": "",
                "hints": [
                    "Usa return para devolver el resultado, no print.",
                    "Validá primero los casos límite (cero, negativos, vacíos).",
                    "Probá tu función con los valores del ejemplo antes de ejecutar."
                ],
                "validator": {
                    "kind": "def_return",
                    "defName": "mi_funcion",
                    "params": ["x"],
                    "sampleArgs": [1],
                    "expected": "1"
                },
                "successAction": {"kind": "fogata", "id": "fogata01"},
                "successDialogue": ["Mensaje de éxito."],
                "concepts": ["funciones"]
            }
        ]
    },
    "book_pages": []
}


def _nuevo_esqueleto():
    """Genera un JSON de lección nuevo a partir del esqueleto estándar."""
    nombre = input("Nombre del archivo (ej. juego_gl04_tema.json): ").strip()
    if not nombre:
        nombre = "juego_glXX_tema.json"
    if not nombre.endswith(".json"):
        nombre += ".json"
    destino = JUEGOS_DIR / nombre
    if destino.exists():
        print(f"ERROR: ya existe {destino}", file=sys.stderr)
        sys.exit(1)
    destino.write_text(
        json.dumps(SKELETON, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Esqueleto creado -> {destino}")
    print("Edítalo y luego genera con: python tools/game_generator.py " + str(destino))


def main():
    args = sys.argv[1:]
    salida = None
    fuente = None
    nuevo = False
    audit = "--audit" in args
    if audit:
        args.remove("--audit")
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--nuevo":
            nuevo = True
            i += 1
            continue
        if a == "-o" and i + 1 < len(args):
            salida = args[i + 1]
            i += 2
            continue
        if not a.startswith("-"):
            fuente = Path(a)
        i += 1
    if nuevo:
        _nuevo_esqueleto()
        return
    if fuente is None:
        fuente = JUEGOS_DIR / "juego_gl01_clases.json"
    if not fuente.exists():
        print(f"ERROR: no existe {fuente}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(fuente.read_text(encoding="utf-8"))
    manifest = json.loads(VISUAL_KIT.read_text(encoding="utf-8"))
    try:
        data = validar_esquema(data, fuente, manifest)
    except SchemaError as e:
        print(f"ERROR de esquema en {fuente}: {e}", file=sys.stderr)
        sys.exit(1)
    meta = data["meta"]
    zone = data["zone"]
    lesson = data["lesson"]

    # Modo auditoría: reporta la calidad pedagógica de cada desafío y sale
    # con código distinto de cero si alguno no cumple los estándares mínimos.
    if audit:
        print("AUDITORÍA de calidad de desafíos:", fuente.name)
        import copy
        lesson_probe = copy.deepcopy(lesson)
        autocompletar_leccion(lesson_probe)
        problemas = auditar_calidad(lesson_probe, chapter=data.get("chapter", ""))
        print(f"Problemas detectados: {problemas}")
        sys.exit(1 if problemas else 0)

    autollenos = autocompletar_leccion(lesson)
    if autollenos:
        resumen = ", ".join(f"{cid}({','.join(campos)})" for cid, campos in autollenos)
        print(f"Auto-completado (autor omitió estos campos): {resumen}", file=sys.stderr)

    book_pages = data.get("book_pages", [])
    chapter = data.get("chapter", "")
    zonas = _all_zones(data)

    assets_js = build_assets_js(manifest, chapter, zone, zonas)
    renderer_js = ASSET_RENDERER.read_text(encoding="utf-8")

    template = TEMPLATE.read_text(encoding="utf-8")
    missing = [
        p for p in ("/*__LESSONS_JS__*/", "/*__BOOK_JS__*/", "/*__ZONE_JS__*/", "/*__ZONES_JS__*/", "/*__ASSETS_JS__*/", "/*__ASSET_RENDERER_JS__*/")
        if p not in template
    ]
    if missing:
        print(f"ERROR: template sin placeholders: {missing}", file=sys.stderr)
        sys.exit(1)

    lessons_js = build_lessons_js(lesson)
    book_js = build_book_js(book_pages)
    zone_js = build_zone_js(zone)
    zones_js = build_zones_js(zonas)

    page = (
        template
        .replace("/*__LESSONS_JS__*/", lessons_js)
        .replace("/*__BOOK_JS__*/", book_js)
        .replace("/*__ZONE_JS__*/", zone_js)
        .replace("/*__ZONES_JS__*/", zones_js)
        .replace("/*__ASSETS_JS__*/", assets_js)
        .replace("/*__ASSET_RENDERER_JS__*/", renderer_js)
    )

    cod = lesson["id"] or "juego"
    salida = salida or SALIDA_DIR / f"Juego_{cod}.html"
    Path(salida).write_text(page, encoding="utf-8")
    print(f"OK -> {salida} ({Path(salida).stat().st_size} bytes)")
    print("LECCIÓN:", lesson["title"], "· zona:", zone.get("cols"), "x", zone.get("rows"))


if __name__ == "__main__":
    main()
