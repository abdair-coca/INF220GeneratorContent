#!/usr/bin/env python3
"""Generador de guías de laboratorio UATF - Formato UX moderno, HTML interactivo.

Uso:
    python gl_generator.py                # usa public/clases_guia/guia_contenido.json -> inf-220-g2/clases/guia_<codigo>.html
    python gl_generator.py mi_tema.json   # usa otro archivo de contenido JSON
    python gl_generator.py -o out.html    # nombre de salida custom
    python gl_generator.py --nuevo        # crea esqueleto JSON nuevo preguntando el tema
    python gl_generator.py --interactivo  # habilita celdas Pyodide + Mermaid (NO Titi)

Por defecto genera DOCUMENTOS puros compatibles con el sandbox de Titi:
HTML autocontenido con CSP estricta, sin scripts externos, sin storage; las
celdas se muestran estáticas y los diagramas como código. Los quizzes reportan
score a Titi vía postMessage TITI_SCORE. Con --interactivo se habilitan celdas
Pyodide y diagramas Mermaid (requiere CDN externos, para abrir standalone fuera
de Titi).

El contenido vive en un JSON. La estructura y el formato utilizan la plantilla UX:
portada hero con gradiente y chips, topbar sticky con marca, secciones numeradas,
bloques estilizados (definición, nota, ejemplo, figura),
autoevaluación multipregunta con sincronización de puntaje Titi vía postMessage y
rúbrica en tabla estilizada. Sin sidebar ni modo clase: el layout es una sola
columna (compatible con el reproductor HTML de Titi).
"""

import json
import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLASES_DIR = ROOT / "public" / "clases_guia"
RESULTADOS_DIR = ROOT / "public" / "resultados_guia"
SALIDA_DIR = ROOT / "inf-220-g2" / "clases"
DEFAULT_JSON = CLASES_DIR / "guia_contenido.json"


def esc(t):
    return html.escape(str(t))


def slug(s):
    return re.sub(r"\W+", "-", str(s).lower()).strip("-")


# ---------------------------------------------------------------------------
# Validación de esquema de guía — errores claros con contexto, advertencias
# de calidad (placeholders, celdas sin salida, nums duplicados). Se ejecuta
# antes de generar para que un JSON con bloques rotos falle con mensaje útil.
# ---------------------------------------------------------------------------
class SchemaError(ValueError):
    """Error de esquema del JSON de guía, con el campo afectado."""


TIPOS_VALIDOS = {
    "texto", "competencia", "lista", "pasos", "definicion", "nota", "ejemplo",
    "figura", "diagrama", "quiz", "simbolos", "sub", "celda",
}
PLACEHOLDERS = (
    "título del", "titulo del", "objetivo del", "diálogo de", "dialogo de",
    "línea de bienvenida", "linea de bienvenida", "pista 1", "pista 2",
    "escribe aquí", "escribe aqui", "xxxx", "lorem",
)


def _err(campo, mensaje):
    raise SchemaError(f"[{campo}] {mensaje}")


def _warn(mensaje):
    print(f"ADVERTENCIA: {mensaje}", file=sys.stderr)


def _requiere(b, ruta, campo):
    val = b.get(campo)
    if val is None or (isinstance(val, str) and not val.strip()):
        _err(f"{ruta}.{campo}", "campo requerido vacío")


def _validar_bloques(bloques, ruta):
    for i, b in enumerate(bloques):
        br = f"{ruta}[{i}]"
        tipo = b.get("tipo")
        if tipo not in TIPOS_VALIDOS:
            _err(br + ".tipo", f"tipo desconocido '{tipo}'. Válidos: {sorted(TIPOS_VALIDOS)}")
        if tipo in ("texto", "competencia"):
            _requiere(b, br, "texto")
            _warn_placeholder(b["texto"], f"{br}.texto")
        elif tipo == "lista":
            items = b.get("items")
            if not isinstance(items, list) or not items:
                _err(br + ".items", "debe ser una lista no vacía de strings")
            for j, it in enumerate(items):
                if not isinstance(it, str) or not it.strip():
                    _err(f"{br}.items[{j}]", "cada ítem debe ser un texto no vacío")
        elif tipo == "pasos":
            items = b.get("items")
            if not isinstance(items, list) or not items:
                _err(br + ".items", "debe ser una lista no vacía de pasos")
            for j, p in enumerate(items):
                if not isinstance(p, dict) or not (p.get("texto") or "").strip():
                    _err(f"{br}.items[{j}]", "cada paso requiere 'texto'")
        elif tipo == "definicion":
            _requiere(b, br, "titulo")
            _requiere(b, br, "texto")
        elif tipo in ("nota", "ejemplo", "figura"):
            _requiere(b, br, "texto")
            _warn_placeholder(b["texto"], f"{br}.texto")
        elif tipo == "diagrama":
            _requiere(b, br, "code")
        elif tipo == "quiz":
            _requiere(b, br, "pregunta")
            _warn_placeholder(b["pregunta"], f"{br}.pregunta")
            opciones = b.get("opciones")
            if not isinstance(opciones, list) or len(opciones) < 2:
                _err(br + ".opciones", "debe tener al menos 2 opciones")
            for j, o in enumerate(opciones):
                texto_o = o.get("texto") if isinstance(o, dict) else o
                if not isinstance(texto_o, str) or not texto_o.strip():
                    _err(f"{br}.opciones[{j}]", "opción vacía")
            correcta = b.get("correcta")
            if not isinstance(correcta, int) or not (0 <= correcta < len(opciones)):
                _err(br + ".correcta", f"debe ser un índice 0-based válido (0..{len(opciones) - 1})")
        elif tipo == "sub":
            _requiere(b, br, "titulo")
            _validar_bloques(b.get("bloques", []), br + ".bloques")
        elif tipo == "celda":
            _requiere(b, br, "in")
            if not (b.get("out") or "").strip():
                _warn(f"{br}.out vacío — los estudiantes no verán el resultado esperado")


def _warn_placeholder(texto, ruta):
    t = texto.lower().strip()
    if len(t) < 8 or any(p in t for p in PLACEHOLDERS):
        _warn(f"{ruta} parece contenido placeholder o demasiado corto: '{texto[:60]}'")


def validar_esquema(data, fuente):
    """Valida la estructura del JSON de guía antes de generar."""
    nombre = fuente.name
    meta = data.get("meta", {})
    for c in ("materia", "codigo", "titulo"):
        if not (meta.get(c) or "").strip():
            _err(f"meta.{c}", f"campo requerido vacío en {nombre}")

    secciones = data.get("secciones")
    if not isinstance(secciones, list) or not secciones:
        _err("secciones", "la guía debe tener al menos una sección")
    nums = set()
    for i, s in enumerate(secciones):
        num = s.get("num", "")
        if not num:
            _err(f"secciones[{i}].num", "sección sin número")
        if num in nums:
            _warn(f"secciones[{i}].num duplicado '{num}'")
        nums.add(num)
        if not (s.get("titulo") or "").strip():
            _err(f"secciones[{i}].titulo", "sección sin título")
        bloques = s.get("bloques")
        rubrica = s.get("rubrica")
        referencias = s.get("referencias")
        if bloques is None and rubrica is None and referencias is None:
            _err(f"secciones[{i}]", "debe llevar 'bloques', 'rubrica' o 'referencias'")
        if bloques is not None:
            if not isinstance(bloques, list):
                _err(f"secciones[{i}].bloques", "debe ser una lista de bloques")
            _validar_bloques(bloques, f"secciones[{i}].bloques")
        if rubrica is not None:
            if not isinstance(rubrica, list) or not rubrica:
                _err(f"secciones[{i}].rubrica", "debe ser una lista de criterios")
            for j, r in enumerate(rubrica):
                for c in ("criterio", "descripcion"):
                    if not (r.get(c) or "").strip():
                        _err(f"secciones[{i}].rubrica[{j}].{c}", "campo requerido vacío")
                if not isinstance(r.get("pts"), int) or r.get("pts") <= 0:
                    _err(f"secciones[{i}].rubrica[{j}].pts", "debe ser un entero positivo")
        if referencias is not None:
            if not isinstance(referencias, list) or not referencias:
                _err(f"secciones[{i}].referencias", "debe ser una lista de referencias")
            for j, ref in enumerate(referencias):
                if not isinstance(ref, str) or not ref.strip():
                    _err(f"secciones[{i}].referencias[{j}]", "referencia vacía")
    return data


# ---------------------------------------------------------------------------
# Tabla de símbolos de diagrama de flujo (SVG inline estilizado UX)
# ---------------------------------------------------------------------------

SIMBOLOS_TABLA = """
<div class="table-container">
  <table class="styled-table">
    <thead>
      <tr>
        <th>Símbolo</th>
        <th>Nombre</th>
        <th>Uso y Descripción</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>
          <svg width="70" height="30" viewBox="0 0 70 30">
            <rect x="3" y="3" width="64" height="24" rx="12" fill="#eeecff" stroke="#5145cd" stroke-width="2"/>
            <text x="35" y="19" text-anchor="middle" font-size="10" fill="#172033" font-weight="700">Inicio/Fin</text>
          </svg>
        </td>
        <td><b>Terminal</b></td>
        <td>Marca el inicio o fin del algoritmo. Todo diagrama debe empezar y terminar aquí.</td>
      </tr>
      <tr>
        <td>
          <svg width="70" height="30" viewBox="0 0 70 30">
            <rect x="5" y="4" width="60" height="22" fill="#fff" stroke="#5145cd" stroke-width="2"/>
            <text x="35" y="19" text-anchor="middle" font-size="10" fill="#172033">Proceso</text>
          </svg>
        </td>
        <td><b>Proceso</b></td>
        <td>Operación de cálculo, asignación de variable o fórmula (ej. <i>s ← a + b</i>).</td>
      </tr>
      <tr>
        <td>
          <svg width="70" height="30" viewBox="0 0 70 30">
            <polygon points="12,4 66,4 58,26 4,26" fill="#fff" stroke="#5145cd" stroke-width="2"/>
            <text x="35" y="19" text-anchor="middle" font-size="9" fill="#172033">Leer/Mostrar</text>
          </svg>
        </td>
        <td><b>Entrada / Salida</b></td>
        <td>Lectura de datos desde teclado (<b>Leer</b>) o emisión en pantalla (<b>Mostrar</b>).</td>
      </tr>
      <tr>
        <td>
          <svg width="70" height="30" viewBox="0 0 70 30">
            <polygon points="35,2 66,15 35,28 4,15" fill="#eeecff" stroke="#5145cd" stroke-width="2"/>
            <text x="35" y="18" text-anchor="middle" font-size="8" fill="#172033" font-weight="700">¿Condición?</text>
          </svg>
        </td>
        <td><b>Decisión</b></td>
        <td>Evalúa una condición lógica y ramifica el flujo: siempre posee <b>una entrada</b> y <b>dos salidas</b> (Sí / No).</td>
      </tr>
      <tr>
        <td>
          <svg width="70" height="30" viewBox="0 0 70 30">
            <circle cx="35" cy="15" r="9" fill="#fff" stroke="#5145cd" stroke-width="2"/>
          </svg>
        </td>
        <td><b>Conector</b></td>
        <td>Enlaza partes del diagrama dentro de la misma página sin cruzar líneas.</td>
      </tr>
      <tr>
        <td>
          <svg width="70" height="30" viewBox="0 0 70 30">
            <line x1="10" y1="15" x2="52" y2="15" stroke="#5145cd" stroke-width="2"/>
            <polygon points="48,10 58,15 48,20" fill="#5145cd"/>
          </svg>
        </td>
        <td><b>Flecha de flujo</b></td>
        <td>Indica el sentido de ejecución. Nunca deben cruzarse ni quedar ramales huérfanos.</td>
      </tr>
    </tbody>
  </table>
</div>
"""

# ---------------------------------------------------------------------------
# Render de bloques
# ---------------------------------------------------------------------------

_cell_n = 0
_quiz_n = 0


def render_bloques(bloques, interactivo=False):
    """Renderiza una lista de bloques JSON utilizando las clases de la plantilla UX.

    `interactivo=False` (por defecto) genera un documento puro compatible con el
    sandbox de Titi: sin scripts CDN (Pyodide/Mermaid), celdas sin botones y
    diagramas como código plano. Con `interactivo=True` se habilitan las celdas
    ejecutables (requiere librerías externas, NO compatible con Titi).
    """
    global _cell_n, _quiz_n
    out = []
    for b in bloques:
        tipo = b.get("tipo")
        if tipo == "texto":
            out.append(f'<p class="muted">{esc(b["texto"])}</p>')
        elif tipo == "competencia":
            out.append(
                '<div class="box-info highlight">'
                '<b>Competencia de la práctica</b>'
                f'<p>{esc(b["texto"])}</p></div>'
            )
        elif tipo == "lista":
            items = "".join(f"<li>{esc(i)}</li>" for i in b["items"])
            out.append(f'<ul class="list-custom">{items}</ul>')
        elif tipo == "pasos":
            items = []
            for i, p in enumerate(b["items"], 1):
                cod = ""
                if p.get("codigo"):
                    cod = f'<div class="code-mini"><pre><code>{esc(p["codigo"])}</code></pre></div>'
                items.append(f"<li><p>{esc(p['texto'])}</p>{cod}</li>")
            out.append(f'<ol class="pasos">{"".join(items)}</ol>')
        elif tipo == "definicion":
            out.append(
                '<div class="box-info">'
                f'<b>DEFINICIÓN · {esc(b.get("titulo", ""))}</b>'
                f'<p>{esc(b["texto"])}</p></div>'
            )
        elif tipo == "nota":
            out.append(
                '<div class="box-info">'
                '<b>NOTA</b>'
                f'<p>{esc(b["texto"])}</p></div>'
            )
        elif tipo == "ejemplo":
            out.append(
                '<div class="box-info highlight">'
                '<b>EJEMPLO</b>'
                f'<p>{esc(b["texto"])}</p></div>'
            )
        elif tipo == "figura":
            out.append(
                '<div class="box-info">'
                '<b>▢ FIGURA</b>'
                f'<p>{esc(b["texto"])}</p></div>'
            )
        elif tipo == "diagrama":
            # Titi interpreta estos bloques con su runtime Mermaid interno.
            out.append(
                '<figure class="diagrama">'
                f'<figcaption>{esc(b.get("titulo", ""))}</figcaption>'
                f'<pre class="mermaid">{esc(b["code"])}</pre>'
                '</figure>'
            )
        elif tipo == "quiz":
            _quiz_n += 1
            qn = _quiz_n
            correcta_val = str(b["correcta"])
            opts_html = []
            for i, o in enumerate(b["opciones"]):
                letra = chr(65 + i) if i < 26 else str(i)
                if isinstance(o, dict):
                    texto_o = o.get("texto", "")
                    expl_o = o.get("explicacion", "")
                else:
                    texto_o = str(o)
                    expl_o = ""
                opts_html.append(
                    f'<button class="option" data-ans="{i}"'
                    f' data-expl="{esc(expl_o)}" type="button">'
                    f'<span class="letter">{letra}</span> {esc(texto_o)}'
                    '</button>'
                )
            expl_q = b.get("explicacion", "")
            out.append(
                f'<article class="quiz-card" data-q="{qn}" data-correct="{correcta_val}"'
                f' data-expl="{esc(expl_q)}">'
                f'<p class="question">{qn}. {esc(b["pregunta"])}</p>'
                f'<div class="options" role="group" aria-label="Opciones Pregunta {qn}">'
                f'{"".join(opts_html)}'
                '</div>'
                '<p class="feedback" aria-live="polite">Seleccioná una respuesta.</p>'
                '<p class="quiz-expl hidden" aria-live="polite"></p>'
                '</article>'
            )
        elif tipo == "simbolos":
            out.append(SIMBOLOS_TABLA)
        elif tipo == "sub":
            sub = render_bloques(b.get("bloques", []), interactivo)
            out.append(f'<h3 class="sub-head">{esc(b["titulo"])}</h3>{sub}')
        elif tipo == "celda":
            _cell_n += 1
            n = _cell_n
            cod = b["in"].rstrip()
            sal = esc(b.get("out", ""))
            if interactivo:
                out.append(
                    f'<div class="cell" id="cell-{n}">'
                    f'<div class="cell-in"><span class="cell-tag">In [{n}]:</span>'
                    f'<button class="btn-copy" data-codigo="{esc(cod)}" title="Copiar código">⧉ copiar</button>'
                    f'<button class="btn-run" data-n="{n}" data-codigo="{esc(cod)}" title="Ejecutar en el navegador">▶ ejecutar</button>'
                    f'<pre><code>{esc(cod)}</code></pre></div>'
                    f'<div class="cell-out"><span class="cell-tag">Out [{n}]:</span>'
                    f'<pre class="out-pre">{sal}</pre></div>'
                    '</div>'
                )
            else:
                # Documento puro (Titi): celda estática, sin botones ni librerías.
                out.append(
                    f'<div class="cell" id="cell-{n}">'
                    f'<div class="cell-in"><span class="cell-tag">In [{n}]:</span>'
                    f'<pre><code>{esc(cod)}</code></pre></div>'
                    f'<div class="cell-out"><span class="cell-tag">Out [{n}]:</span>'
                    f'<pre class="out-pre">{sal}</pre></div>'
                    '</div>'
                )
    return "".join(out)


def render_seccion(sec, interactivo=False):
    num = sec.get("num", "")
    titulo = sec["titulo"]
    sec_id = f"sec-{num or slug(titulo)}"
    
    if "rubrica" in sec:
        filas = "".join(
            f"<tr><td><b>{esc(r['criterio'])}</b></td><td>{esc(r['descripcion'])}</td>"
            f'<td class="pts">{r["pts"]} pts</td></tr>'
            for r in sec["rubrica"]
        )
        total = sum(r["pts"] for r in sec["rubrica"])
        cuerpo = (
            '<div class="table-container">'
            '<table class="styled-table"><thead><tr><th>Criterio</th><th>Descripción</th>'
            f'<th style="width:100px;">Puntaje</th></tr></thead><tbody>{filas}</tbody>'
            f'<tfoot><tr><td colspan="2"><b>Total</b></td><td class="pts">{total} Pts</td></tr></tfoot></table></div>'
        )
    elif "referencias" in sec:
        items = "".join(f"<li>{esc(r)}</li>" for r in sec["referencias"])
        cuerpo = f'<ul class="list-custom">{items}</ul>'
    else:
        cuerpo = render_bloques(sec.get("bloques", []), interactivo)

    num_span = f'<span class="num">SECCIÓN {esc(num)}</span>' if num else ''
    return (
        f'<section class="section" id="{sec_id}">'
        f'<div class="head"><div>{num_span}<h2>{esc(titulo)}</h2></div></div>'
        f'{cuerpo}</section>'
    )


# ---------------------------------------------------------------------------
# Plantilla CSS UX
# ---------------------------------------------------------------------------

CSS = """
:root {
  --ink: #172033;
  --muted: #647083;
  --line: #dfe4ec;
  --paper: #ffffff;
  --soft: #f3f5fa;
  --violet: #5145cd;
  --violet-soft: #eeecff;
  --green: #087a55;
  --green-soft: #edf9f4;
  --red: #a62118;
  --red-soft: #fff2f1;
}

* {
  box-sizing: border-box;
}

html {
  scroll-behavior: smooth;
}

body {
  margin: 0;
  color: var(--ink);
  background: var(--soft);
  font-family: "Segoe UI", system-ui, -apple-system, sans-serif;
  font-size: 15px;
  line-height: 1.6;
}

button,
a {
  font: inherit;
}

button:focus-visible,
a:focus-visible {
  outline: 3px solid #9e97ff;
  outline-offset: 3px;
}

/* Topbar */
.topbar {
  position: sticky;
  top: 0;
  z-index: 50;
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 64px;
  padding: 10px max(14px, calc((100vw - 1200px) / 2));
  color: #fff;
  background: #151927;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.2);
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.mark {
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  border-radius: 10px;
  background: var(--violet);
  font-weight: 800;
}

.brand strong {
  display: block;
  font-size: 0.9rem;
}

.brand small {
  display: block;
  color: #bec5d4;
  font-size: 0.76rem;
}

.progress {
  position: fixed;
  top: 64px;
  left: 0;
  z-index: 60;
  width: 100%;
  height: 3px;
}

.progress i {
  display: block;
  width: 0%;
  height: 100%;
  background: #8279f1;
  transition: width 0.1s linear;
}

/* Layout */
.layout {
  width: min(1200px, 100%);
  margin: 0 auto;
  padding: 30px 22px 70px;
}

/* Main Content */
main {
  min-width: 0;
}

.hero {
  padding: clamp(24px, 4vw, 46px);
  border: 1px solid var(--line);
  border-radius: 18px;
  background: linear-gradient(135deg, #ffffff, #f0eeff);
  box-shadow: 0 16px 36px rgba(23, 32, 51, 0.08);
}

.eyebrow,
.num {
  color: var(--violet);
  font-size: 0.76rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

h1 {
  max-width: 800px;
  margin: 8px 0 12px;
  font-family: Georgia, serif;
  font-size: clamp(2rem, 4vw, 3.35rem);
  line-height: 1.08;
}

.lead {
  max-width: 68ch;
  margin: 0;
  color: var(--muted);
  font-size: 1.04rem;
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 22px;
}

.chip {
  padding: 5px 10px;
  border: 1px solid #d9d5ff;
  border-radius: 999px;
  color: #4439b0;
  background: rgba(255, 255, 255, 0.6);
  font-size: 0.82rem;
}

.meta-details {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
  margin-top: 20px;
  padding-top: 18px;
  border-top: 1px solid rgba(81, 69, 205, 0.15);
  font-size: 0.88rem;
  color: var(--muted);
}

.meta-details b {
  color: var(--ink);
}

.notice {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 12px;
  margin: 22px 0;
  padding: 17px 19px;
  border-left: 4px solid var(--violet);
  border-radius: 0 12px 12px 0;
  background: var(--violet-soft);
}

.notice p {
  margin: 0;
  color: #535c6c;
}

.notice strong {
  display: block;
  margin-bottom: 2px;
}

/* Sections */
.section {
  scroll-margin-top: 84px;
  margin-top: 23px;
  padding: clamp(21px, 4vw, 34px);
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--paper);
}

.head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 15px;
  margin-bottom: 16px;
}

.head h2 {
  margin: 2px 0 0;
  font-family: Georgia, serif;
  font-size: clamp(1.5rem, 3vw, 2rem);
  line-height: 1.25;
}

.sub-head {
  font-family: Georgia, serif;
  font-size: 1.25rem;
  margin: 26px 0 12px;
  color: var(--ink);
}

.time {
  white-space: nowrap;
  color: var(--muted);
  font-size: 0.82rem;
}

.muted {
  max-width: 72ch;
  color: var(--muted);
}

.box-info {
  margin: 18px 0;
  padding: 16px 18px;
  border: 1px solid var(--line);
  border-radius: 11px;
  background: #fafbfe;
}

.box-info.highlight {
  border-color: #c7c1ff;
  background: #f7f6ff;
}

.box-info b {
  display: block;
  margin-bottom: 4px;
  color: var(--violet);
  font-size: 0.85rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.box-info p {
  margin: 0;
}

.list-custom {
  margin: 12px 0 16px;
  padding-left: 20px;
}

.list-custom li {
  margin-bottom: 8px;
}

/* Tables */
.table-container {
  overflow-x: auto;
  margin: 18px 0;
  border: 1px solid var(--line);
  border-radius: 11px;
}

.styled-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.92rem;
  text-align: left;
}

.styled-table th {
  padding: 12px 14px;
  color: #fff;
  background: #151927;
  font-weight: 600;
}

.styled-table td {
  padding: 12px 14px;
  border-top: 1px solid var(--line);
  vertical-align: middle;
}

.styled-table tr:nth-child(even) td {
  background: #fcfdfe;
}

.styled-table .pts {
  text-align: center;
  font-weight: 700;
  color: var(--violet);
}

/* Code Cells */
.code-mini {
  background: #151927;
  border-radius: 8px;
  padding: 10px 14px;
  margin-top: 8px;
}

.code-mini pre {
  color: #d6dae3;
  font-family: 'Cascadia Code', 'Consolas', monospace;
  font-size: 13px;
  white-space: pre-wrap;
}

.cell {
  margin: 16px 0;
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid var(--line);
}

.cell-in {
  background: #151927;
  position: relative;
}

.cell-in .cell-tag,
.cell-out .cell-tag {
  display: inline-block;
  font-size: 12px;
  font-family: 'Cascadia Code', Consolas, monospace;
}

.cell-in .cell-tag {
  color: #a5b4fc;
  padding: 10px 14px 0;
}

.cell-out .cell-tag {
  color: var(--muted);
  padding: 8px 14px 0;
}

.cell-in pre {
  color: #e6e9f0;
  font-family: 'Cascadia Code', 'Consolas', monospace;
  font-size: 13px;
  padding: 8px 14px 14px;
  white-space: pre-wrap;
  word-break: break-word;
}

.cell-out {
  background: #f8fafc;
}

.cell-out .out-pre {
  font-family: 'Cascadia Code', 'Consolas', monospace;
  font-size: 12.5px;
  color: #333a46;
  padding: 4px 14px 12px;
  white-space: pre-wrap;
  word-break: break-word;
}

.cell-out canvas {
  max-width: 100%;
  height: auto;
  display: block;
  margin: 6px auto 12px;
  padding: 0 14px;
}

.btn-copy,
.btn-run {
  position: absolute;
  top: 8px;
  border: 1px solid #3a3f4b;
  background: #20232b;
  color: #c9cede;
  border-radius: 6px;
  font-size: 11.5px;
  padding: 4px 10px;
  cursor: pointer;
}

.btn-copy {
  right: 86px;
}

.btn-run {
  right: 10px;
  background: var(--violet);
  border-color: var(--violet);
  color: #fff;
}

.btn-run:hover {
  background: #4336be;
}

.btn-run:disabled {
  opacity: 0.6;
  cursor: wait;
}

/* Diagram Section */
.diagrama {
  margin: 20px 0;
  padding: 18px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: #fbfcfe;
}

.diagrama figcaption {
  font-size: 13px;
  color: var(--muted);
  font-weight: 700;
  letter-spacing: 0.4px;
  margin-bottom: 12px;
}

.diagrama .mermaid {
  display: flex;
  justify-content: center;
  overflow: auto;
  padding: 6px;
}

.diagrama .mermaid svg {
  max-width: 100%;
  height: auto;
}

/* Quiz / Self-Evaluation */
.quiz-card {
  margin-bottom: 24px;
  padding: 20px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: #fdfdff;
}

.question {
  margin: 0 0 13px;
  font-size: 1.05rem;
  font-weight: 700;
}

.options {
  display: grid;
  gap: 9px;
}

.option {
  display: flex;
  align-items: center;
  gap: 11px;
  width: 100%;
  min-height: 48px;
  padding: 10px 13px;
  border: 1px solid var(--line);
  border-radius: 9px;
  color: var(--ink);
  background: #fff;
  text-align: left;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
}

.option:hover:not(:disabled) {
  border-color: #aaa4ef;
  background: #faf9ff;
}

.option:disabled {
  cursor: default;
}

.letter {
  display: grid;
  place-items: center;
  width: 27px;
  height: 27px;
  border-radius: 7px;
  background: var(--soft);
  font-weight: 800;
  font-size: 0.85rem;
  flex-shrink: 0;
}

.option.ok {
  border-color: #59b99a;
  color: var(--green);
  background: var(--green-soft);
  font-weight: 600;
}

.option.bad {
  border-color: #e8a29c;
  color: var(--red);
  background: var(--red-soft);
}

.feedback {
  min-height: 24px;
  margin: 12px 0 0;
  color: var(--muted);
  font-weight: 650;
  font-size: 0.92rem;
}

.feedback.ok {
  color: var(--green);
}

.feedback.bad {
  color: var(--red);
}

.quiz-expl {
  margin: 8px 0 0;
  padding: 10px 12px;
  border-left: 3px solid var(--accent, #5145cd);
  background: rgba(81, 69, 205, 0.06);
  color: var(--muted);
  font-size: 0.9rem;
  line-height: 1.5;
  border-radius: 0 8px 8px 0;
}

.hidden {
  display: none !important;
}

/* Score Summary Box for Titi */
.score-card {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-top: 28px;
  padding: 20px clamp(16px, 3vw, 24px);
  border: 2px solid var(--violet);
  border-radius: 14px;
  background: linear-gradient(135deg, var(--violet-soft), #ffffff);
}

.score-info b {
  display: block;
  color: var(--violet);
  font-size: 0.8rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.score-info span {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--ink);
}

.score-badge {
  display: flex;
  align-items: center;
  gap: 12px;
}

.score-val {
  font-family: Georgia, serif;
  font-size: 2.3rem;
  font-weight: 800;
  color: var(--violet);
  line-height: 1;
}

.titi-status {
  font-size: 0.8rem;
  color: var(--muted);
}

footer {
  border-top: 1px solid var(--line);
  color: var(--muted);
  font-size: 0.85rem;
  padding: 24px 22px 50px;
  text-align: center;
}

#cargando-bar {
  position: fixed;
  bottom: 18px;
  right: 18px;
  z-index: 99;
  background: #151927;
  color: #fff;
  border-radius: 8px;
  padding: 10px 16px;
  font-size: 12.5px;
  display: none;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.3);
}

/* Responsive */
@media (max-width: 800px) {
  .topbar {
    padding: 10px 13px;
  }

  .brand small {
    display: none;
  }

  .layout {
    padding: 20px 14px 50px;
  }
}

@media print {
  .topbar,
  .progress,
  .btn-copy,
  .btn-run,
  #cargando-bar {
    display: none !important;
  }

  body {
    background: #fff;
  }

  .layout {
    display: block;
    width: 100%;
    padding: 0;
  }

  .hero,
  .section {
    box-shadow: none;
    break-inside: avoid;
  }
}

/* ---------- Overlay: Nota subida a Titi ---------- */
#titi-nota-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(21, 25, 39, 0.72);
  backdrop-filter: blur(3px);
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.25s ease;
}
#titi-nota-overlay.show {
  opacity: 1;
  pointer-events: auto;
}
#titi-nota-overlay .nota-box {
  background: #fff;
  border-radius: 16px;
  max-width: 380px;
  width: calc(100% - 48px);
  padding: 32px 28px;
  text-align: center;
  box-shadow: 0 18px 50px rgba(0, 0, 0, 0.35);
}
#titi-nota-overlay .nota-spinner {
  width: 44px;
  height: 44px;
  margin: 0 auto 18px;
  border: 4px solid #e5e2ff;
  border-top-color: #5b4df0;
  border-radius: 50%;
  animation: nota-spin 0.8s linear infinite;
}
#titi-nota-overlay .nota-box.done .nota-spinner {
  border-color: #2fb380;
  animation: none;
}
#titi-nota-overlay .nota-box.done .nota-spinner::after {
  content: "✓";
  display: block;
  font-size: 22px;
  line-height: 36px;
  color: #2fb380;
  font-weight: 700;
}
@keyframes nota-spin {
  to { transform: rotate(360deg); }
}
#titi-nota-overlay .nota-title {
  margin: 0 0 6px;
  font-size: 18px;
  font-weight: 700;
  color: #151927;
}
#titi-nota-overlay .nota-text {
  margin: 0 0 6px;
  font-size: 14px;
  color: #4a4f63;
}
#titi-nota-overlay .nota-score {
  font-size: 30px;
  font-weight: 800;
  color: #5b4df0;
  margin: 8px 0 18px;
}
#titi-nota-overlay .nota-btn {
  background: #5b4df0;
  color: #fff;
  border: 0;
  padding: 11px 22px;
  border-radius: 10px;
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
}
#titi-nota-overlay .nota-btn:hover {
  background: #4336be;
}
#titi-nota-overlay .nota-btn.hidden {
  display: none;
}

@media print {
  #titi-nota-overlay {
    display: none !important;
  }
}
"""

# ---------------------------------------------------------------------------
# Renderizador flowchart propio (autocontenido, sin CDN). Dibuja los
# diagramas de flujo (graph TD) como SVG inline. Funciona en Titi y standalone.
# ---------------------------------------------------------------------------
FLOW_RENDERER_JS = r"""
// ---------- Renderizador de diagramas de flujo (SVG, sin librerías) ----------
(function () {
  function parseFlow(code) {
    const lines = code.split('\n').map(l => l.trim()).filter(l => l && !/^(graph|flowchart)\s/i.test(l));
    const nodes = {};
    const edges = [];
    function cleanText(text) {
      text = text.trim();
      if ((text.startsWith('"') && text.endsWith('"')) ||
          (text.startsWith("'") && text.endsWith("'"))) {
        return text.slice(1, -1);
      }
      return text;
    }
    function parseNodeSegment(segment) {
      const idMatch = segment.match(/^\s*([A-Za-z0-9_]+)/);
      if (!idMatch) return null;
      const id = idMatch[1], rest = segment.slice(idMatch[0].length).trim();
      let m;
      m = rest.match(/^\(\s*\[([^]*?)\]\s*\)/);
      if (m) return { id, text: cleanText(m[1]), shape: 'terminal' };
      m = rest.match(/^\[\/\s*([^]*?)\s*\/\]/);
      if (m) return { id, text: cleanText(m[1]), shape: 'parallelogram' };
      m = rest.match(/^\{\s*([^]*?)\s*\}/);
      if (m) return { id, text: cleanText(m[1]), shape: 'diamond' };
      m = rest.match(/^\[\s*([^]*?)\s*\]/);
      if (m) return { id, text: cleanText(m[1]), shape: 'process' };
      m = rest.match(/^\(\s*([^]*?)\s*\)/);
      if (m) return { id, text: cleanText(m[1]), shape: 'process' };
      return { id, text: id, shape: 'rect' };
    }
    function setNode(node) {
      if (!nodes[node.id] || nodes[node.id].text === node.id) nodes[node.id] = node;
    }
    for (const line of lines) {
      const arrowAt = line.indexOf('-->');
      if (arrowAt !== -1) {
        const left = line.slice(0, arrowAt).trim();
        const right = line.slice(arrowAt + 3).trim();
        const labelMatch = left.match(/^([^]*?)\s*--\s*([^]*)$/);
        const fromNode = parseNodeSegment(labelMatch ? labelMatch[1].trim() : left);
        const toNode = parseNodeSegment(right);
        if (fromNode && toNode) {
          edges.push({ from: fromNode.id, to: toNode.id,
            label: labelMatch ? cleanText(labelMatch[2]) : '' });
          setNode(fromNode);
          setNode(toNode);
        }
      } else {
        const node = parseNodeSegment(line);
        if (node) setNode(node);
      }
    }
    return { nodes, edges };
  }

  function layout(g) {
    const ids = Object.keys(g.nodes);
    // Asignar capas siguiendo flujo, sin recursión: los ciclos vuelven a una
    // capa ya visitada y conservan dirección visual de arriba hacia abajo.
    const layer = {};
    const outgoing = {};
    const incoming = {};
    ids.forEach(id => { outgoing[id] = []; incoming[id] = 0; });
    g.edges.forEach(e => {
      outgoing[e.from].push(e.to);
      incoming[e.to]++;
    });
    const queue = ids.filter(id => incoming[id] === 0);
    if (!queue.length && ids.length) queue.push(ids[0]);
    queue.forEach(id => { layer[id] = 0; });
    for (let i = 0; i < queue.length; i++) {
      const from = queue[i];
      outgoing[from].forEach(to => {
        if (layer[to] === undefined) {
          layer[to] = layer[from] + 1;
          queue.push(to);
        }
      });
    }
    ids.forEach(id => { if (layer[id] === undefined) layer[id] = 0; });
    const maxLayer = Math.max(0, ...ids.map(id => layer[id]));
    // orden dentro de capa (orden de aparición)
    const byLayer = {};
    ids.forEach(id => { (byLayer[layer[id]] = byLayer[layer[id]] || []).push(id); });
    Object.keys(byLayer).forEach(k => byLayer[k].sort());
    return { layer, byLayer, maxLayer };
  }

  function measure(text, fontSize) {
    return Math.max(40, text.length * fontSize * 0.62 + 22);
  }

  function renderFlow(container) {
    const code = container.getAttribute('data-flow');
    if (!code) return;
    const g = parseFlow(code);
    const { layer, byLayer, maxLayer } = layout(g);
    const fontSize = 13, nodeH = 44, vGap = 46, hGap = 24;
    const pad = 20;
    const nw = {};
    Object.keys(g.nodes).forEach(id => nw[id] = measure(g.nodes[id].text, fontSize));
    const pos = {};
    const layerWidths = {};
    Object.keys(byLayer).forEach(k => {
      let x = 0;
      byLayer[k].forEach(id => {
        pos[id] = { x: x + nw[id] / 2, y: pad + Number(k) * (nodeH + vGap) + nodeH / 2 };
        x += nw[id] + hGap;
      });
      layerWidths[k] = Math.max(0, x - hGap);
    });
    // ancho/alto total
    const maxLayerWidth = Math.max(0, ...Object.values(layerWidths));
    let W = maxLayerWidth + pad * 2, H = pad * 2 + maxLayer * (nodeH + vGap) + nodeH;
    Object.keys(pos).forEach(id => { pos[id].x += pad; });
    H = Math.max(H, ...Object.keys(pos).map(id => pos[id].y + nodeH / 2 + pad));
    const svgNS = 'http://www.w3.org/2000/svg';
    const svg = document.createElementNS(svgNS, 'svg');
    svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
    svg.setAttribute('width', String(W));
    svg.setAttribute('role', 'img');
    svg.style.width = 'min(100%, ' + W + 'px)';
    svg.style.maxWidth = '100%';
    svg.style.height = 'auto';
    // edges
    for (const e of g.edges) {
      const a = pos[e.from], b = pos[e.to];
      const x1 = a.x, y1 = a.y + nodeH / 2;
      const x2 = b.x, y2 = b.y - nodeH / 2;
      const path = document.createElementNS(svgNS, 'path');
      const mx = (x1 + x2) / 2;
      const backward = b.y <= a.y;
      const routeX = Math.max(8, Math.min(x1, x2) - 28);
      const pathData = backward
        ? 'M ' + x1 + ' ' + y1 + ' C ' + routeX + ' ' + y1 + ', ' + routeX + ' ' + y2 + ', ' + x2 + ' ' + y2
        : 'M ' + x1 + ' ' + y1 + ' C ' + mx + ' ' + y1 + ', ' + mx + ' ' + y2 + ', ' + x2 + ' ' + y2;
      path.setAttribute('d', pathData);
      path.setAttribute('fill', 'none');
      path.setAttribute('stroke', '#5145cd');
      path.setAttribute('stroke-width', '1.6');
      svg.appendChild(path);
      // flecha
      const ang = Math.atan2(y2 - y1, x2 - x1);
      const aSize = 8;
      const ax = x2, ay = y2;
      const arrow = document.createElementNS(svgNS, 'path');
      arrow.setAttribute('d', 'M ' + ax + ' ' + ay + ' L ' + (ax - aSize * Math.cos(ang - 0.4)) + ' ' + (ay - aSize * Math.sin(ang - 0.4)) + ' M ' + ax + ' ' + ay + ' L ' + (ax - aSize * Math.cos(ang + 0.4)) + ' ' + (ay - aSize * Math.sin(ang + 0.4)));
      arrow.setAttribute('stroke', '#5145cd');
      arrow.setAttribute('stroke-width', '1.6');
      arrow.setAttribute('fill', 'none');
      svg.appendChild(arrow);
      // label
      if (e.label) {
        const txt = document.createElementNS(svgNS, 'text');
        txt.setAttribute('x', backward ? routeX : mx);
        txt.setAttribute('y', (y1 + y2) / 2 - 4);
        txt.setAttribute('text-anchor', 'middle');
        txt.setAttribute('font-size', '12');
        txt.setAttribute('fill', '#172033');
        txt.setAttribute('font-weight', '600');
        txt.textContent = e.label;
        svg.appendChild(txt);
      }
    }
    // nodos
    for (const id of Object.keys(g.nodes)) {
      const n = g.nodes[id], p = pos[id];
      const w = nw[id], h = nodeH, cx = p.x, cy = p.y;
      let shape;
      if (n.shape === 'terminal') {
        shape = '<ellipse cx="' + cx + '" cy="' + cy + '" rx="' + (w / 2 + 10) + '" ry="' + (h / 2 + 6) + '" fill="#eeecff" stroke="#5145cd" stroke-width="1.8"/>';
      } else if (n.shape === 'diamond') {
        shape = '<polygon points="' + (cx - w / 2) + ',' + cy + ' ' + cx + ',' + (cy - h / 2 - 6) + ' ' + (cx + w / 2) + ',' + cy + ' ' + cx + ',' + (cy + h / 2 + 6) + '" fill="#eeecff" stroke="#5145cd" stroke-width="1.8"/>';
      } else if (n.shape === 'parallelogram') {
        const skew = 14;
        shape = '<polygon points="' + (cx - w / 2 + skew) + ',' + (cy - h / 2) + ' ' + (cx + w / 2) + ',' + (cy - h / 2) + ' ' + (cx + w / 2 - skew) + ',' + (cy + h / 2) + ' ' + (cx - w / 2) + ',' + (cy + h / 2) + '" fill="#fff" stroke="#5145cd" stroke-width="1.8"/>';
      } else {
        shape = '<rect x="' + (cx - w / 2) + '" y="' + (cy - h / 2) + '" width="' + w + '" height="' + h + '" rx="6" fill="#fff" stroke="#5145cd" stroke-width="1.8"/>';
      }
      const gEl = document.createElementNS(svgNS, 'g');
      gEl.innerHTML = shape;
      const text = document.createElementNS(svgNS, 'text');
      text.setAttribute('x', cx);
      text.setAttribute('y', cy + fontSize * 0.35);
      text.setAttribute('text-anchor', 'middle');
      text.setAttribute('font-size', fontSize);
      text.setAttribute('fill', '#172033');
      text.setAttribute('font-family', 'Segoe UI, sans-serif');
      const words = n.text.split(/\s+/);
      const lines = [];
      let cur = '';
      for (const wd of words) { const t = cur ? cur + ' ' + wd : wd; if (t.length * fontSize * 0.62 > w - 12 && cur) { lines.push(cur); cur = wd; } else { cur = t; } }
      lines.push(cur);
      const lineH = fontSize + 3;
      const startY = cy - (lines.length - 1) * lineH / 2 + fontSize * 0.35;
      lines.forEach((ln, i) => {
        const ts = document.createElementNS(svgNS, 'tspan');
        ts.setAttribute('x', cx);
        ts.setAttribute('y', startY + i * lineH);
        ts.textContent = ln;
        text.appendChild(ts);
      });
      gEl.appendChild(text);
      svg.appendChild(gEl);
    }
    container.innerHTML = '';
    container.appendChild(svg);
  }

  document.querySelectorAll('.flowchart').forEach(renderFlow);
})();
"""

JS = """
// ---------- Barra de progreso de lectura ----------
const progressBar = document.getElementById('bar');
window.addEventListener('scroll', () => {
  if (!progressBar) return;
  const totalHeight = document.documentElement.scrollHeight - window.innerHeight;
  if (totalHeight > 0) {
    const progress = (window.scrollY / totalHeight) * 100;
    progressBar.style.width = Math.min(100, Math.max(0, progress)) + '%';
  }
});

// ---------- Autoevaluación Multipregunta & Integración Titi ----------
const quizCards = document.querySelectorAll('.quiz-card');
const scoreValEl = document.getElementById('score-val');
const scoreTextEl = document.getElementById('score-text');
const titiStatusEl = document.getElementById('titi-status');

let currentScore = 0;
const userAnswers = {};

function reportarScoreTiti(score, detail) {
  currentScore = score;
  try {
    window.parent.postMessage({
      source: 'titi-html',
      type: 'TITI_SCORE',
      score: score,
      detail: detail || {},
      attemptToken: window.__TITI_ATTEMPT_TOKEN,
    }, '*');
  } catch (err) {
    // Ejecución en ventana independiente
  }
}

function actualizarCalculoScore() {
  const totalQuizzes = quizCards.length;
  if (!totalQuizzes) return;

  let answeredCount = 0;
  let correctCount = 0;

  quizCards.forEach(card => {
    const qId = card.dataset.q;
    if (userAnswers[qId] !== undefined) {
      answeredCount++;
      if (userAnswers[qId].isCorrect) {
        correctCount++;
      }
    }
  });

  const scorePercent = Math.round((correctCount / totalQuizzes) * 100);
  
  if (scoreValEl) scoreValEl.textContent = scorePercent + '%';
  if (scoreTextEl) scoreTextEl.textContent = `Respondidas: ${answeredCount} / ${totalQuizzes} (${correctCount} correctas)`;
  if (titiStatusEl) {
    titiStatusEl.textContent = answeredCount === totalQuizzes
      ? '✓ Evaluación completada y enviada a Titi'
      : 'Sincronización activa con entorno Titi';
  }

  // Solo enviamos el score definitivo a Titi cuando la evaluación está completa.
  // Enviarlo en cada respuesta haría que Titi registre el score parcial de la
  // primera pregunta como si fuera la nota final.
  if (answeredCount === totalQuizzes) {
    reportarScoreTiti(scorePercent, {
      total: totalQuizzes,
      correct: correctCount,
      answered: answeredCount
    });
    mostrarOverlayNota(scorePercent);
  }
}

function mostrarOverlayNota(score) {
  const overlay = document.getElementById('titi-nota-overlay');
  const box = document.getElementById('titi-nota-box');
  if (!overlay || !box) return;
  const title = document.getElementById('nota-title');
  const text = document.getElementById('nota-text');
  const scoreEl = document.getElementById('nota-score');
  const btn = document.getElementById('nota-btn');
  box.classList.remove('done');
  scoreEl.classList.add('hidden');
  btn.classList.add('hidden');
  if (title) title.textContent = 'Subiendo nota a Titi…';
  if (text) text.textContent = 'Guardando tu resultado, espera un momento.';
  overlay.classList.add('show');
  setTimeout(() => {
    box.classList.add('done');
    if (title) title.textContent = '¡Nota subida a Titi!';
    if (text) text.textContent = 'Tu puntaje quedó registrado correctamente.';
    if (scoreEl) {
      scoreEl.textContent = score + '%';
      scoreEl.classList.remove('hidden');
    }
    btn.classList.remove('hidden');
  }, 1400);
}

document.addEventListener('click', (ev) => {
  if (ev.target && ev.target.id === 'nota-btn') {
    const overlay = document.getElementById('titi-nota-overlay');
    if (overlay) overlay.classList.remove('show');
    const card = document.getElementById('titi-score-card');
    if (card) card.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
});

quizCards.forEach(card => {
  const qId = card.dataset.q;
  const correctAnswer = card.dataset.correct;
  const options = card.querySelectorAll('.option');
  const feedbackEl = card.querySelector('.feedback');

  options.forEach(btn => {
    btn.addEventListener('click', () => {
      const selectedAns = btn.dataset.ans;
      const isCorrect = selectedAns === correctAnswer;

      userAnswers[qId] = { selected: selectedAns, isCorrect };

      const explEl = card.querySelector('.quiz-expl');
      if (explEl) {
        const expl = btn.dataset.expl || card.dataset.expl || '';
        if (expl) {
          explEl.textContent = expl;
          explEl.classList.remove('hidden');
        } else {
          explEl.classList.add('hidden');
        }
      }

      options.forEach(o => {
        o.disabled = true;
        o.classList.remove('ok', 'bad');
      });

      btn.classList.add(isCorrect ? 'ok' : 'bad');

      if (!isCorrect) {
        const correctBtn = card.querySelector(`.option[data-ans="${correctAnswer}"]`);
        if (correctBtn) correctBtn.classList.add('ok');
      }

      if (feedbackEl) {
        feedbackEl.className = 'feedback ' + (isCorrect ? 'ok' : 'bad');
        feedbackEl.textContent = isCorrect
          ? '✓ ¡Excelente! Respuesta correcta.'
          : '✗ Incorrecto. Revisa la teoría y vuelve a intentarlo.';
      }

      actualizarCalculoScore();
    });
  });
});

window.addEventListener('message', (ev) => {
  if (ev.data && (ev.data.type === 'TITI_GET_SCORE' || ev.data.type === 'GET_SCORE')) {
    actualizarCalculoScore();
  }
});

// ---------- carga de Pyodide (Python en el navegador) ----------
let _pyodide = null;

async function cargarPython() {
  if (_pyodide) return _pyodide;
  const bar = document.getElementById('cargando-bar');
  if (bar) {
    bar.style.display = 'block';
    bar.textContent = 'Cargando entorno Python (primera vez tarda unos segundos)…';
  }
  _pyodide = await loadPyodide();
  await _pyodide.loadPackage(['numpy', 'pandas', 'matplotlib', 'seaborn']);
  await _pyodide.runPythonAsync(PRELUDE);
  if (bar) {
    bar.textContent = 'Entorno Python listo. Las celdas ▶ ejecutan de verdad.';
    setTimeout(() => { bar.style.display = 'none'; }, 2500);
  }
  return _pyodide;
}

const PRELUDE = `
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('module://matplotlib_pyodide.html5_canvas_backend')
import matplotlib.pyplot as plt
import seaborn as sns

def load_iris():
    try:
        from sklearn.datasets import load_iris as _li
        return _li()
    except Exception:
        rng = np.random.default_rng(42)
        data = np.round(np.column_stack([
            rng.normal(5.01, 0.35, 150), rng.normal(3.43, 0.38, 150),
            rng.normal(3.76, 1.77, 150), rng.normal(1.20, 0.76, 150)]), 1)
        iris = type('Iris', (), {})()
        iris.data = data
        iris.target = np.repeat([0, 1, 2], 50)
        iris.target_names = np.array(['setosa', 'versicolor', 'virginica'])
        return iris
`;

async function ejecutar(n, codigo) {
  const cell = document.getElementById('cell-' + n);
  if (!cell) return;
  const outPre = cell.querySelector('.out-pre');
  const btn = cell.querySelector('.btn-run');
  btn.disabled = true;
  btn.textContent = '⏳ …';
  outPre.textContent = 'ejecutando…';
  const canvasAntes = new Set([...document.querySelectorAll('canvas')]);
  try {
    const p = await cargarPython();
    let prints = '';
    p.setStdout({ batched: (s) => { prints += s + '\\n'; } });
    const val = await p.runPythonAsync(codigo);
    p.globals.set('_last', val);
    const reprTxt = await p.runPythonAsync('repr(_last)');
    let texto = prints;
    if (reprTxt && String(reprTxt) !== 'None' && String(reprTxt) !== '') {
      texto += String(reprTxt);
    }
    outPre.textContent = texto || '(sin salida de texto — ver figura abajo)';
    const nuevos = [...document.querySelectorAll('canvas')].filter(c => !canvasAntes.has(c));
    for (const c of nuevos) {
      c.classList.add('plot-canvas');
      cell.querySelector('.cell-out').appendChild(c);
    }
  } catch (e) {
    outPre.textContent = String(e.message || e);
  } finally {
    btn.disabled = false;
    btn.textContent = '▶ ejecutar';
  }
}

document.addEventListener('click', (ev) => {
  const b = ev.target.closest('.btn-copy');
  if (b) {
    navigator.clipboard.writeText(b.dataset.codigo)
      .then(() => { b.textContent = '✓ copiado'; setTimeout(() => { b.textContent = '⧉ copiar'; }, 1500); });
  }
});

document.addEventListener('click', (ev) => {
  const b = ev.target.closest('.btn-run');
  if (b) ejecutar(Number(b.dataset.n), b.dataset.codigo);
});

"""

# ---------------------------------------------------------------------------
# Plantilla JS para documento puro (modo no interactivo / Titi).
# Sin Pyodide ni CDN: solo menú, modo clase, scrollspy, quiz + score Titi.
# Titi renderiza Mermaid antes de cargar el documento en su iframe.
# ---------------------------------------------------------------------------

JS_STATIC = """
// ---------- Barra de progreso de lectura ----------
const progressBar = document.getElementById('bar');
window.addEventListener('scroll', () => {
  if (!progressBar) return;
  const totalHeight = document.documentElement.scrollHeight - window.innerHeight;
  if (totalHeight > 0) {
    const progress = (window.scrollY / totalHeight) * 100;
    progressBar.style.width = Math.min(100, Math.max(0, progress)) + '%';
  }
});

// ---------- Autoevaluación Multipregunta & Integración Titi ----------
const quizCards = document.querySelectorAll('.quiz-card');
const scoreValEl = document.getElementById('score-val');
const scoreTextEl = document.getElementById('score-text');
const titiStatusEl = document.getElementById('titi-status');

const userAnswers = {};

function reportarScoreTiti(score) {
  const finalScore = Math.max(0, Math.min(100, Math.round(Number(score) || 0)));
  try {
    window.parent.postMessage({
      source: 'titi-html',
      type: 'TITI_SCORE',
      score: finalScore,
      attemptToken: window.__TITI_ATTEMPT_TOKEN,
    }, '*');
  } catch (e) { /* ejecución standalone */ }
}

function actualizarCalculoScore() {
  const total = quizCards.length;
  if (!total) return;
  let answered = 0, correct = 0;
  quizCards.forEach(card => {
    const qId = card.dataset.q;
    if (userAnswers[qId] !== undefined) {
      answered++;
      if (userAnswers[qId].isCorrect) correct++;
    }
  });
  const pct = Math.round((correct / total) * 100);
  if (scoreValEl) scoreValEl.textContent = pct + '%';
  if (scoreTextEl) scoreTextEl.textContent = 'Respondidas: ' + answered + ' / ' + total + ' (' + correct + ' correctas)';
  if (titiStatusEl) {
    titiStatusEl.textContent = answered === total
      ? '\\u2713 Evaluaci\\u00f3n completada y enviada a Titi'
      : 'Sincronizaci\\u00f3n activa con entorno Titi';
  }
  // Solo reportamos el score final cuando la evaluación está completa, para
  // evitar que Titi registre el score parcial de la primera pregunta.
  if (answered === total) {
    reportarScoreTiti(pct);
    mostrarOverlayNota(pct);
  }
}

function mostrarOverlayNota(score) {
  const overlay = document.getElementById('titi-nota-overlay');
  const box = document.getElementById('titi-nota-box');
  if (!overlay || !box) return;
  const title = document.getElementById('nota-title');
  const text = document.getElementById('nota-text');
  const scoreEl = document.getElementById('nota-score');
  const btn = document.getElementById('nota-btn');
  box.classList.remove('done');
  scoreEl.classList.add('hidden');
  btn.classList.add('hidden');
  if (title) title.textContent = 'Subiendo nota a Titi…';
  if (text) text.textContent = 'Guardando tu resultado, espera un momento.';
  overlay.classList.add('show');
  setTimeout(() => {
    box.classList.add('done');
    if (title) title.textContent = '¡Nota subida a Titi!';
    if (text) text.textContent = 'Tu puntaje quedó registrado correctamente.';
    if (scoreEl) {
      scoreEl.textContent = score + '%';
      scoreEl.classList.remove('hidden');
    }
    btn.classList.remove('hidden');
  }, 1400);
}

document.addEventListener('click', (ev) => {
  if (ev.target && ev.target.id === 'nota-btn') {
    const overlay = document.getElementById('titi-nota-overlay');
    if (overlay) overlay.classList.remove('show');
    const card = document.getElementById('titi-score-card');
    if (card) card.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
});

quizCards.forEach(card => {
  const qId = card.dataset.q;
  const correctAnswer = card.dataset.correct;
  const options = card.querySelectorAll('.option');
  const feedbackEl = card.querySelector('.feedback');
  options.forEach(btn => {
    btn.addEventListener('click', () => {
      const selected = btn.dataset.ans;
      const isCorrect = selected === correctAnswer;
      userAnswers[qId] = { selected, isCorrect };
      const explEl = card.querySelector('.quiz-expl');
      if (explEl) {
        const expl = btn.dataset.expl || card.dataset.expl || '';
        if (expl) {
          explEl.textContent = expl;
          explEl.classList.remove('hidden');
        } else {
          explEl.classList.add('hidden');
        }
      }
      options.forEach(o => { o.disabled = true; o.classList.remove('ok', 'bad'); });
      btn.classList.add(isCorrect ? 'ok' : 'bad');
      if (!isCorrect) {
        const right = card.querySelector('.option[data-ans="' + correctAnswer + '"]');
        if (right) right.classList.add('ok');
      }
      if (feedbackEl) {
        feedbackEl.className = 'feedback ' + (isCorrect ? 'ok' : 'bad');
        feedbackEl.textContent = isCorrect
          ? '\\u2713 \\u00a1Excelente! Respuesta correcta.'
          : '\\u2717 Incorrecto. Revisa la teor\\u00eda y vuelve a intentarlo.';
      }
      actualizarCalculoScore();
    });
  });
});

window.addEventListener('message', (ev) => {
  if (ev.data && (ev.data.type === 'TITI_GET_SCORE' || ev.data.type === 'GET_SCORE')) {
    actualizarCalculoScore();
  }
});
"""

MERMAID_STANDALONE_JS = """
if (window.mermaid) {
  mermaid.initialize({
    startOnLoad: false,
    securityLevel: 'strict',
    theme: 'base',
    themeVariables: {
      primaryColor: '#eeecff',
      primaryBorderColor: '#5145cd',
      primaryTextColor: '#172033',
      lineColor: '#5145cd',
      fontFamily: 'Segoe UI, sans-serif'
    },
    flowchart: { curve: 'basis', padding: 10, nodeSpacing: 32, rankSpacing: 40, htmlLabels: false }
  });
  mermaid.run({ nodes: document.querySelectorAll('.mermaid') });
}
"""

GUIA_SKELETON = {
    "meta": {
        "materia": "INF-220 · Programación Orientada a Objetos",
        "codigo": "GLXX",
        "facultad": "UATF · Facultad de Ciencias Puras · Ing. Informática",
        "titulo": "Título de la Guía",
        "subtitulo": "Práctica N.º X · Una frase que resuma qué logra el estudiante.",
        "semestre": "Ing. Informática · 2º semestre · Gestión 2026-02",
        "duracion": "3 h de laboratorio",
        "docente": "Docente: Ph.D. Juan Ramiro Villa · Auxiliar: Univ. Abdair Magdiel Coca Carlo"
    },
    "convenciones": "Explica cómo se trabaja la guía (dónde se ejecuta el código, qué se entrega).",
    "secciones": [
        {
            "num": "01",
            "titulo": "Competencia y objetivos",
            "bloques": [
                {"tipo": "texto", "texto": "Competencia de la práctica"},
                {"tipo": "competencia", "texto": "Redacta la competencia: qué habilidad construye el estudiante al terminar."},
                {"tipo": "texto", "texto": "Objetivos específicos"},
                {"tipo": "lista", "items": [
                    "Comprender el concepto central de la práctica.",
                    "Aplicar el concepto en ejercicios guiados.",
                    "Resolver un ejercicio nuevo de forma autónoma."
                ]}
            ]
        },
        {
            "num": "02",
            "titulo": "Requisitos y preparación",
            "bloques": [
                {"tipo": "lista", "items": [
                    "Navegador moderno (Chrome, Firefox, Edge o Safari).",
                    "Lectura previa de la guía anterior."
                ]},
                {"tipo": "nota", "texto": "Podés ejecutar las celdas de Python en el navegador con ▶ ejecutar."}
            ]
        },
        {
            "num": "03",
            "titulo": "Conceptos previos",
            "bloques": [
                {"tipo": "definicion", "titulo": "Concepto", "texto": "Definición precisa del concepto que se practica."},
                {"tipo": "nota", "texto": "Ampliá con un detalle, trampa común o aclaración."}
            ]
        },
        {
            "num": "04",
            "titulo": "Laboratorio Práctico interactivo",
            "bloques": [
                {"tipo": "celda", "in": "print('Hola, INF-220')", "out": "Hola, INF-220"}
            ]
        },
        {
            "num": "05",
            "titulo": "Autoevaluación",
            "bloques": [
                {
                    "tipo": "quiz",
                    "pregunta": "Pregunta conceptual sobre la práctica",
                    "opciones": [
                        {"texto": "Opción incorrecta", "explicacion": "Por qué esta opción está mal."},
                        {"texto": "Opción correcta", "explicacion": "Por qué esta es la correcta."},
                        {"texto": "Otra opción incorrecta", "explicacion": "Por qué esta opción está mal."}
                    ],
                    "correcta": 1,
                    "explicacion": "Explicación general opcional que se muestra al responder."
                }
            ]
        },
        {
            "num": "06",
            "titulo": "Práctica en clase",
            "bloques": [
                {"tipo": "lista", "items": ["Enunciado del ejercicio 1.", "Enunciado del ejercicio 2."]}
            ]
        },
        {
            "num": "07",
            "titulo": "Entregable",
            "bloques": [
                {"tipo": "nota", "texto": "Formato de entrega y fecha límite."}
            ]
        },
        {
            "num": "08",
            "titulo": "Rúbrica de evaluación",
            "rubrica": [
                {"criterio": "Criterio", "descripcion": "Descripción del criterio", "pts": 40},
                {"criterio": "Criterio", "descripcion": "Descripción del criterio", "pts": 60}
            ]
        },
        {
            "num": "09",
            "titulo": "Referencias",
            "referencias": ["Referencia bibliográfica o documentación oficial."]
        }
    ]
}


def _nuevo_esqueleto():
    """Crea un esqueleto de guía nuevo en public/clases_guia/ preguntando el tema."""
    tema = input("Tema de la guía (ej. funciones): ").strip()
    if not tema:
        tema = "tema"
    codigo = input("Código de la guía (ej. GL04): ").strip().upper() or "GLXX"
    titulo = input("Título (ej. Estructuras de Control): ").strip()
    destino = CLASES_DIR / f"guia_contenido_{slug(tema)}.json"
    if destino.exists():
        print(f"ERROR: ya existe {destino}", file=sys.stderr)
        sys.exit(1)
    skeleton = json.loads(json.dumps(GUIA_SKELETON))  # copia profunda
    skeleton["meta"]["codigo"] = codigo
    if titulo:
        skeleton["meta"]["titulo"] = titulo
    destino.write_text(json.dumps(skeleton, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Esqueleto creado -> {destino}")
    print("Edítalo y luego genera con: python tools/gl_generator.py " + str(destino))


def main():
    args = sys.argv[1:]
    salida = None
    fuente = DEFAULT_JSON
    # Modo Titi por defecto: sin CDN, con renderer SVG inline. El modo
    # interactivo se solicita explícitamente para abrir el HTML standalone.
    interactivo = "--interactivo" in args
    if "--interactivo" in args:
        args.remove("--interactivo")
    if "--estatico" in args:
        args.remove("--estatico")
    if "--nuevo" in args:
        args.remove("--nuevo")
        _nuevo_esqueleto()
        return
    i = 0
    while i < len(args):
        a = args[i]
        if a == "-o" and i + 1 < len(args):
            salida = args[i + 1]
            i += 2
            continue
        if not a.startswith("-"):
            fuente = Path(a)
        i += 1

    if not fuente.exists():
        print(f"ERROR: no existe {fuente}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(fuente.read_text(encoding="utf-8"))
    try:
        data = validar_esquema(data, fuente)
    except SchemaError as e:
        print(f"ERROR de esquema en {fuente}: {e}", file=sys.stderr)
        sys.exit(1)
    meta = data["meta"]

    global _cell_n, _quiz_n
    _cell_n = 0
    _quiz_n = 0

    secciones_html_list = []
    for s in data["secciones"]:
        sec_html = render_seccion(s, interactivo)
        # Si la sección contenía quizzes, agregar la tarjeta de score al final de esa sección
        secciones_html_list.append(sec_html)

    # Si hubo algún quiz en toda la guía, inyectar el titi-score-card al final de la última sección con quizzes
    if _quiz_n > 0:
        score_card_html = (
            f'<div class="score-card" id="titi-score-card">'
            f'<div class="score-info">'
            f'<b>Estado de Autoevaluación Titi</b>'
            f'<span id="score-text">Respondidas: 0 / {_quiz_n}</span>'
            f'<div class="titi-status" id="titi-status">Sincronización activa con entorno Titi</div>'
            f'</div>'
            f'<div class="score-badge">'
            f'<div class="score-val" id="score-val">0%</div>'
            f'</div>'
            f'</div>'
        )
        full_html_str = "".join(secciones_html_list)
        last_idx = full_html_str.rfind('</article>')
        if last_idx != -1:
            end_pos = last_idx + len('</article>')
            secciones_html = full_html_str[:end_pos] + score_card_html + full_html_str[end_pos:]
        else:
            secciones_html = full_html_str + score_card_html
    else:
        secciones_html = "".join(secciones_html_list)

    hero = (
        '<section class="hero" id="inicio">'
        f'<div class="eyebrow">{esc(meta["codigo"])} · {esc(meta.get("duracion", "Laboratorio"))}</div>'
        f'<h1>{esc(meta["titulo"])}</h1>'
        f'<p class="lead">{esc(meta.get("subtitulo", ""))}</p>'
        '<div class="chips">'
        f'<span class="chip">{esc(meta.get("semestre", "2.º semestre"))}</span>'
        '<span class="chip">Gestión 2026-02</span>'
        '</div>'
        '<div class="meta-details">'
        f'<div><b>Asignatura:</b> {esc(meta["materia"])}</div>'
        f'<div><b>Institución:</b> {esc(meta.get("facultad", ""))}</div>'
        f'<div><b>Información:</b> {esc(meta.get("docente", ""))}</div>'
        '</div></section>'
    )

    conv_text = data.get("convenciones", "")
    conv = ""
    if conv_text:
        conv = (
            '<aside class="notice">'
            '<div aria-hidden="true">💡</div>'
            '<div>'
            '<strong>Antes de comenzar</strong>'
            f'<p>{esc(conv_text)}</p>'
            '</div></aside>'
        )

    def contiene_tipo(bloques, tipo):
        for b in bloques:
            if b.get("tipo") == tipo:
                return True
            if b.get("bloques") and contiene_tipo(b["bloques"], tipo):
                return True
        return False

    todos = [b for s in data["secciones"] for b in s.get("bloques", [])]
    usa_celdas = contiene_tipo(todos, "celda")
    usa_diagramas = contiene_tipo(todos, "diagrama")

    scripts = ""
    if interactivo:
        if usa_celdas:
            scripts += "<script src='https://cdn.jsdelivr.net/pyodide/v0.26.4/full/pyodide.js'></script>"
        if usa_diagramas:
            scripts += "<script src='https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js'></script>"

    codigo_mark = esc(meta.get("codigo", "GL"))

    if interactivo:
        csp_str = "default-src 'self' 'unsafe-inline' data: blob: https:; script-src 'unsafe-inline' 'unsafe-eval' https:; style-src 'unsafe-inline' https:; img-src data: blob: https:; font-src data: https:; connect-src https:;"
    else:
        csp_str = "default-src 'none'; base-uri 'none'; connect-src 'none'; form-action 'none'; frame-src 'none'; img-src data:; media-src data:; font-src data:; style-src 'unsafe-inline'; script-src 'unsafe-inline';"

    nota_overlay = ""
    if _quiz_n > 0:
        nota_overlay = (
            '<div id="titi-nota-overlay">'
            '<div class="nota-box" id="titi-nota-box">'
            '<div class="nota-spinner"></div>'
            '<p class="nota-title" id="nota-title">Subiendo nota a Titi…</p>'
            '<p class="nota-text" id="nota-text">Guardando tu resultado, espera un momento.</p>'
            '<div class="nota-score hidden" id="nota-score"></div>'
            '<button class="nota-btn hidden" id="nota-btn" type="button">Continuar</button>'
            '</div></div>'
        )

    page = (
        "<!DOCTYPE html><html lang='es'><head><meta charset='utf-8'>"
        f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<meta http-equiv='Content-Security-Policy' content=\"{csp_str}\">"
        f"<title>{esc(meta['titulo'])} · {esc(meta['codigo'])}</title>"
        f"<style>{CSS}</style></head><body>"
        '<header class="topbar">'
        '<div class="brand">'
        f'<div class="mark">{codigo_mark}</div>'
        '<div>'
        f'<strong>{esc(meta["materia"])} · Guía de laboratorio</strong>'
        f'<small>{esc(meta.get("facultad", ""))}</small>'
        '</div></div>'
        '</header>'
        '<div class="progress" aria-hidden="true"><i id="bar"></i></div>'
        f'<div class="layout">'
        f'<main>{hero}{conv}{secciones_html}</main></div>'
        f'<footer>Generado con gl_generator.py · formato UX · {esc(meta.get("facultad", ""))}</footer>'
        f'<div id="cargando-bar"></div>{scripts}'
        f'<script>{(JS if interactivo else JS_STATIC) + (MERMAID_STANDALONE_JS if interactivo and usa_diagramas else "")}</script>'
        f'{nota_overlay}'
        "</body></html>"
    )

    cod = slug(meta["codigo"]) or "guia"
    salida = salida or SALIDA_DIR / f"guia_{cod}.html"
    Path(salida).write_text(page, encoding="utf-8")
    print(f"OK -> {salida}")


if __name__ == "__main__":
    main()
