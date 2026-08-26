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
    "print_call", "def_exists", "def_return", "function_cases", "structure",
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
        if v["kind"] == "structure":
            req_js = js_dict(c.get("requirements", {}))
            validate_js = "function(engine, code){ return VALIDATORS.structure(engine, code, this.requirements); }"
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
        if v["kind"] == "structure":
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


def build_assets_js(manifest, chapter, zone):
    """Recorta el manifest del kit visual al conjunto de assets del capítulo
    más los assets referenciados por la zona. Devuelve un literal JS compacto."""
    sets = manifest.get("chapter_asset_sets", {})
    ids = set(sets.get(chapter, []))
    ids |= _zone_asset_ids(zone)
    ids |= {
        "tree_oak", "player_viajero", "npc_alizon", "npc_guardabosques",
        "campfire", "tent_blue", "workbench", "bush_flowers", "flowers_mixed",
        "grass_tufts",
    }
    all_assets = manifest.get("assets", {})
    assets = {aid: all_assets[aid] for aid in ids if aid in all_assets}
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

    lesson = data["lesson"]
    for c in ("id", "title", "concept", "zone", "story", "introDialogue",
              "objectives", "challenges"):
        if c not in lesson:
            _err("lesson." + c, f"falta la clave '{c}' en la lección")

    challenges = lesson["challenges"]
    if not challenges:
        _err("lesson.challenges", "la lección debe tener al menos 1 desafío")

    ch_ids = _ids_unicos(challenges, "lesson.challenges")

    interact_ids = {i["id"] for i in zone["interactables"]}
    npc_ids = {n["id"] for n in zone["npcs"]}
    for ch in challenges:
        cid = ch["id"]
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
        if a.get("kind") == "station_transition":
            if a.get("id") != target:
                _err(f"lesson.challenges[{cid}].successAction.id", "debe coincidir con target en una transición de estación.")
            station = next(it for it in zone["interactables"] if it["id"] == target)
            if station.get("missionNode") != cid:
                _err(f"lesson.challenges[{cid}].target", "la estación target debe enlazar este desafío mediante missionNode.")

    if manifest:
        assets = manifest.get("assets", {})
        for section in ("npcs", "interactables", "decor"):
            for item in zone.get(section, []):
                asset_id = item.get("asset")
                if asset_id and asset_id not in assets:
                    _err(f"zone.{section}[{item.get('id', item.get('kind', '?'))}].asset", f"asset '{asset_id}' inexistente.")

    for it in zone["interactables"]:
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
                "objective": "Objetivo del desafío.",
                "example": "",
                "starterCode": "",
                "hints": ["Pista 1.", "Pista 2."],
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
    book_pages = data.get("book_pages", [])
    chapter = data.get("chapter", "")

    assets_js = build_assets_js(manifest, chapter, zone)
    renderer_js = ASSET_RENDERER.read_text(encoding="utf-8")

    template = TEMPLATE.read_text(encoding="utf-8")
    missing = [
        p for p in ("/*__LESSONS_JS__*/", "/*__BOOK_JS__*/", "/*__ZONE_JS__*/", "/*__ASSETS_JS__*/", "/*__ASSET_RENDERER_JS__*/")
        if p not in template
    ]
    if missing:
        print(f"ERROR: template sin placeholders: {missing}", file=sys.stderr)
        sys.exit(1)

    lessons_js = build_lessons_js(lesson)
    book_js = build_book_js(book_pages)
    zone_js = build_zone_js(zone)

    page = (
        template
        .replace("/*__LESSONS_JS__*/", lessons_js)
        .replace("/*__BOOK_JS__*/", book_js)
        .replace("/*__ZONE_JS__*/", zone_js)
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
