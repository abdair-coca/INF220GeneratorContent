# AGENTS.md — INF-220 · 2026Semestre2

Context for AI agents working in this workspace. Read this first.

## What this project is

A system that generates **interactive UATF lab guides** ("GL02 format") as
self-contained HTML. Built for INF-220 (Programación Orientada a Objetos).
One source JSON defines a guide; `gl_generator.py` renders it into an HTML
page with a TOC, runnable Python cells (Pyodide), Mermaid diagrams, quizzes,
and print-to-PDF support.

The assistant/auxiliar is **Abdair Magdiel Coca Carlo**; docente is **Ph.D.
Juan Ramiro Villa**. Class is taught in Spanish — **all guide content
(JSON text, meta, diagram labels) is written in Spanish.**

## Canon narrativo: El Refugio Lógico (una sola historia para toda la materia)

Todas las guías y juegos comparten una única historia. Definición completa en
`public/juegos/story_arc.json` (incluye el arco por capítulos y las reglas del motor).

- **Premisa**: el viajero deja la "Ciudad de la Interfaz" (todo automatizado,
  la gente olvidó cómo funciona el mundo por dentro) y se adentra en "El Gran
  Backend", un bosque salvaje y complejo. Acompañado por su compañera de
  expedición **Teffy**, sobrevive leyendo un antiguo manual de supervivencia y
  construyendo todo con sus propias manos.
- **Capítulos** (cada uno = un nivel/lección):
  1. Los Planos del Viajero — Clases y Objetos (Campamento, Tienda, Fogata)
  2. El Resguardo frente a la Tormenta — Encapsulamiento (baúles seguros, getters/setters)
  3. Herramientas a Medida — Herencia y Polimorfismo (Herramienta → Hacha, CañaDePescar)
  4. El Ritmo de la Supervivencia — Pilas (LIFO), Colas (FIFO), Listas
  5. Los Senderos Ocultos — Árboles Binarios (in-order/pre-order) y Grafos (Dijkstra)

## Reglas del motor de juego ("El Motor del Bosque")

Aplican a todos los juegos HTML estilo RPG educativo (2D top-down).
`inf-220-g2/clases/Juego_funciones_02.html` es el **conejillo de indias**: ahí
se arma la plantilla perfecta que se replicará en los demás niveles/lecciones.

1. Física
   - Hitboxes inteligentes: colisión solo en el tronco de los árboles; el
     jugador camina "por detrás" de la copa (z-index / orden de dibujo).
   - Fricción y sobrecarga: cargar recursos pesados (madera) o empujar troncos
     reduce la velocidad de movimiento.
   - Partículas orgánicas: viento aleatorio mueve sutilmente humo y chispas.
2. Dinamismo (game feel)
   - Bucle `requestAnimationFrame` constante a 60 FPS.
   - Hit stop (~50 ms) + screen shake en impactos fuertes (talar, resolver reto).
   - Ciclo día/noche: oscurecer el lienzo (`ctx.globalAlpha`) y halos de luz
     alrededor del jugador y las fogatas; de noche es obligatorio estar cerca del fuego.
   - Animaciones de anticipación y recuperación en acciones (ej. golpe de hacha).
3. Lógica y arquitectura
   - Estado global tipo BD relacional: el nivel no guarda "la fogata está
     encendida"; `LevelManager` consulta el estado del objeto `Fogata` en el
     almacén de datos del jugador.
   - Máquinas de estados finitos para NPCs (ej. Teffy: Idle, Gathering, Cooking)
     con transiciones automáticas según las acciones del jugador.
   - Intérprete aislado (sandbox): detectar bucles infinitos a los 1000 ciclos y
     lanzar un error amigable en vez de congelar la pestaña.

### Multi-zona y portales (escenarios interiores)

El motor soporta **múltiples zonas** por juego (exterior + interiores). Cada
zona es un mapa propio con su clima, NPCs, interactuables y decoración.

- El JSON puede traer `zones: { posada: {...}, banco: {...}, ... }` además de
  `zone` (el exterior, registrado como `exterior`). Sin `zones`, el juego es
  single-zone (compatibilidad total con los juegos previos).
- Los `interactables` con `"type": "portal"` y campos `toZone`, `spawnX`,
  `spawnY` conectan zonas. Interactuar (E) con un portal llama
  `Game.enterZone()`, que recarga el mundo, reposiciona al jugador y aplica el
  clima de la zona.
- **Retorno al portal de entrada**: al salir de un interior hacia `exterior`,
  el jugador reaparece **junto al portal por el que entró**, no en el centro
  del mapa. El motor guarda `_lastPortal` al entrar y lo usa al volver.
- **Spawn seguro**: `_findWalkableSpawn()` garantiza que el jugador nunca
  quede atrapado en una pared — si el spawn cae en un tile no caminable,
  busca la celda caminable más cercana en espiral.
- **Tiles de interior**: `W` (pared, no caminable), `F` (piso, caminable),
  `C` (mueble, no caminable) además de los tiles exteriores.
- **Radar/guía multi-zona**: el radar lista los retos de todas las zonas; la
  guía dorada apunta al portal correcto si el reto activo vive en otra zona.

### Decoración interactiva (tecla F)

El mundo se siente vivo: hay decoración que se puede **activar** sin resolver
problemas, con la tecla **F** (no E).

- Los `decor` pueden llevar `interactable: true` + `stateDefault`/`stateOn`/
  `stateOff`/`prompt`. La tecla F alterna el estado del decor cercano con
  partículas y audio. Ejemplos: fogatas que se encienden/apagan, lámparas,
  cofres que se abren.
- `World.toggleDecor(id)`, `World.setDecorState(id, state)`,
  `World.litDecor(id)`; `InteractionSystem.findNearbyDecor(player)`;
  `Game._handleInteractDecor()`. El renderer muestra un prompt `F · <prompt>`
  junto al decor animable y emite humo/chispas en fogatas encendidas.
- Para dar vida al mundo: decorar los mapas (flores, arbustos, maderas,
  cajas, fogatas, lámparas) además de los altares de retos. Las casas deben
  quedar **cercanas entre sí** y tener **mobiliario interior** (mesa, silla,
  cama, estante, cofre, tapete, lámpara, fogata).
- **REGLA OBLIGATORIA DE COMPONENTES**: Todos los items, decoraciones y muebles
  se **DEBEN sacar exclusivamente de la galería de componentes**
  (`public/juegos/visual/el_refugio_assets_gallery.html` /
  `public/juegos/visual/el_refugio_visual_assets_v1.json`). Prohibido inventar
  ids de assets que no existan en la galería.

### Validadores POO (class_cases)

Además del validator estático `structure`, el motor tiene **`class_cases`**:
ejecuta el código del alumno en un intérprete Python en JS que soporta
`class`, `__init__`, `self`, instancias, `@classmethod`, atributos de clase,
name mangling de privados (`_Clase__atributo`), composición y `__str__`.

- El spec vive en `requirements.classes[]`: `name`, `initArgs`, `instances`
  (cuántos objetos crear; útil para contadores `@classmethod`), `methods[]`
  con `cases[]` (`args`/`expected`), `classMethods[]` (exigen `@classmethod`)
  y `privateAttrs[]` (exigen declaración privada).
- **Instancias distintas**: para probar una clase con datos distintos (ej.
  dos `Persona`), se usan **varias specs** con el mismo `name` e `initArgs`
  distintos. El audit acumula casos por `(clase, método)` a través de todas
  las specs; el autocompletado de `starterCode` **deduplica** la clase.
- **Composición**: `initArgs` puede contener `{"__ref": "Fecha", "args":
  [...]}` para instanciar un objeto auxiliar antes de construir el principal.
- El generador valida el esquema, autocompleta `example`/`starterCode`/`hints`
  (POO) y los incluye en `--audit`.
- **Diagramas de Clase UML (`classDiagram`) OBLIGATORIOS**: cada reto de POO
  debe mostrar su diagrama de clase en la consola de código. Se define en el
  JSON como `classDiagram: [{ className, attributes, methods, relation? }]`.
  El motor lo renderiza con formato UML y distintivos de visibilidad por color.
- **PROHIBICIÓN ESTRICTA DE ARRAYS Y ESTRUCTURAS COMPLEJAS EN POO BÁSICA**:
  En los niveles y prácticas de POO inicial (Capítulos 1 a 3, Práctica 5),
  **está totalmente prohibido usar o pedir listas, arrays, tuplas o diccionarios**.
  Las colecciones se enseñan recién en el Capítulo 4 (Pilas, Colas, Listas).
  El estado de las clases debe ser puramente escalar (`int`, `float`, `str`, `bool`)
  o composición de objetos simples. El generador y `--audit` validan que el
  enunciado, las pistas y el código no mencionen ni requieran estructuras complejas.

### Clima

Cada zona lleva su propio `weather`. Modos: `none`, `rain`, `storm`
(requiere `lesson.storm.thresholds` para las fases) y `frost` (escarcha,
partículas de nieve + overlay azul-blanca parametrizado por zona con
`overlayColor`).

## Directory layout

```
2026Semestre2/                      ← project root — git repo de FUENTES (remote INF220GeneratorContent, rama main)
├── AGENTS.md                       ← this file
├── tools/                          ← generator scripts (Python 3.11, stdlib only)
│   ├── game_generator.py           ←   generates games (El Refugio Lógico RPG)
│   └── gl_generator.py             ←   generates class guides (GL01/02/03)
├── docs/                           ← project docs
│   ├── generador_game.md           ←   game-authoring standards (Titi sandbox rules)
│   └── screenshots/                ←   game screenshots (jf2_*.png, gl01_*.png)
├── public/                         ← source content JSONs
│   ├── clases_guia/                ←   class guides (guia_contenido.json, guia_contenido_gl01.json)
│   ├── resultados_guia/            ←   solved-exercises guides
│   └── juegos/                     ←   game canon + sources
│       ├── game_engine_template.html   ← motor "El Refugio Lógico" (NO se edita por lección)
│       ├── visual/                     ← kit visual data-driven (assets JSON + renderer + galería)
│       ├── story_arc.json              ← universo + arco narrativo
│       ├── juego_gl01_oficial.json     ← GL01 CAP 1 OFICIAL (funciones+selectivas; GL01 diagramas = teoría)
│       ├── juego_gl01_clases.json      ← GL01 Clases y Objetos (práctica extra)
│       ├── juego_gl02_funciones.json   ← GL02 Funciones (práctica extra)
│       ├── juego_practica4_refugio.json← Práctica 4 (funciones, hub de estaciones)
│       └── juego_practica5_objetos.json← Práctica 5 (POO, 5 zonas multi-escenario)
├── inf-220-g2/                     ← subrepo de ARTEFACTOS generados (user inits it, rama inf-220-g2-artifacts)
│   ├── clases/                     ← generated HTML (guia_gl0x.html, Juego_*.html)
│   ├── practicas/                  ← user drops practice docs here (user fills, we don't)
│   └── README.md
├── resueltos/                      ← OUTSIDE the repo: solved exercises HTML
└── graphify-out/                   ← knowledge graph (codegraph)
    ├── graph.html                  ←   interactive graph
    ├── graph.json                  ←   raw graph data
    └── GRAPH_REPORT.md             ←   audit report
```

### File ownership rules (user's explicit requirements)

- **Career files live inside `inf-220-g2/`** which is the only git repo.
- **Generated outputs (HTML guides) go to `inf-220-g2/clases/`.**
- **`inf-220-g2/practicas/`** is the user's folder — we do NOT put files there.
- **Solved exercises go to `resueltos/`** (sibling of `inf-220-g2`, outside repo).
- **The class guide must NOT contain solved exercises** — they live only in `resueltos/`.
- **Content JSONs live in `public/`** (`clases_guia/` and `resultados_guia/`).
- Never renumber guide sections when removing one; keep original `"num"` values
  (a gap like 04 → 06 is correct).

## gl_generator.py

Standalone script, stdlib only (json/html/re/sys/pathlib). No install needed.
Lives in `tools/`. Paths resolve from the project root (`ROOT = script.parent.parent`).

### CLI

```
python tools/gl_generator.py                                # default: public/clases_guia/guia_contenido.json
python tools/gl_generator.py public/clases_guia/guia_contenido_gl01.json          # explicit source
python tools/gl_generator.py public/resultados_guia/guia_contenido_gl01_resueltos.json -o resueltos/gl01_resueltos.html
python tools/gl_generator.py --nuevo                        # create a new guide skeleton (prompts for topic)
```

- Output defaults to `inf-220-g2/clases/guia_<slug(codigo)>.html`.
- Use `-o <path>` to override (e.g. into `resueltos/`).
- **Valida el esquema** antes de generar (tipos de bloque, quizzes con
  `correcta` 0-based válido, celdas con `in`, placeholders, secciones con
  `bloques`/`rubrica`/`referencias`) y falla con mensaje claro si algo no cumple.
- `--nuevo` crea un esqueleto de guía en `public/clases_guia/` (pregunta tema,
  código y título). El esqueleto ya incluye quiz con `explicacion` y celdas con
  `out`.
- **Quizzes**: cada opción puede ser un string o `{"texto", "explicacion"}`;
  la pregunta puede llevar `"explicacion"`. Al responder se muestra la
  explicación (la de la opción elegida, o la de la pregunta como fallback)
  para que el estudiante aprenda por qué.

## game_generator.py

Genera los juegos RPG ("El Refugio Lógico") desde un JSON de lección + el kit
visual. Vive en `tools/`. Inyecta 5 placeholders en el template
`public/juegos/game_engine_template.html`:

- `/*__ZONE_JS__*/` → el mapa exterior (NPCs, interactuables, decoración).
- `/*__ZONES_JS__*/` → el registro completo de zonas (exterior + interiores)
  para juegos multi-escenario.
- `/*__LESSONS_JS__*/` → la misión (challenges con validate/onSuccess).
- `/*__BOOK_JS__*/` → páginas del Libro.
- `/*__ASSETS_JS__*/` → subset del kit visual (recortado por capítulo).

### CLI

```
python tools/game_generator.py public/juegos/juego_gl01_oficial.json -o inf-220-g2/clases/Juego_Capitulo_1.html   # CAP 1 OFICIAL
python tools/game_generator.py public/juegos/juego_gl01_clases.json                                            # práctica (Clases)
python tools/game_generator.py public/juegos/juego_gl02_funciones.json -o inf-220-g2/clases/Juego_funciones_01.html
python tools/game_generator.py --nuevo                    # esqueleto JSON de lección nueva
python tools/game_generator.py public/juegos/juego_gl04_tema.json --audit   # auditoría de calidad (no genera)
```

Output defaults to `inf-220-g2/clases/Juego_<lesson_id>.html`. El generador
**valida el esquema** del JSON antes de generar (longitud del `map`, ids
únicos, `target` existente, `validator.kind`/`successAction.kind` válidos,
objetivo de cada desafío con ≥25 chars) y falla con mensaje claro si algo no
cumple.

### Autocompletado pedagógico (los ejercicios se explican solos)

Si el autor omite `example`, `starterCode` o deja menos de 3 `hints`, el
generador los **deriva del validador** (no toca valores explícitos):

- `example` → se construye `fn(args) -> resultado` tomando un caso normal y un
  caso límite de `validator.function_cases` (o `sampleArgs`/`expected`).
- `starterCode` → esqueleto `def fn(param): return None` para cada función pedida.
- `hints` → se completan hasta 3 con pistas genéricas (firma exacta, casos
  límite, usar `return` en vez de `print`).

Al generar se avisa por stderr qué campos se autocompletaron.

### `--audit` (calidad pedagógica)

Reporta por desafío: longitud de `objective`, si tiene `example`/`starterCode`,
cantidad de `hints` y nº de casos de prueba. Sale con código **1** si algún
desafío no cumple los estándares mínimos (objetivo corto, sin ejemplo en
`function_cases`/`def_return`, sin `starterCode`, <2 pistas, <2 casos).
Usalo antes de entregar una lección nueva.

### Validadores y acciones (data-driven)

- `validator.kind`: `structure` (POO: classes/attrs/methods/instantiate/calls),
  `def_return`, `def_exists`, `print_call` (funciones), `function_cases`
  (multi-función con casos `args[]`/`expected`; el más expresivo y el que
  permite el autocompletado pedagógico), `class_cases` (POO **ejecutable**:
  instancia clases y compara retornos de métodos; ver "Validadores POO").
- `successAction.kind` (tema Refugio): `fogata`, `tienda`, `campamento`,
  `station_transition`.
  `campamento` abre el sendero y debe ser el desafío final.

### Cómo escribir un buen desafío (juego)

El generador autocompleta `example`/`starterCode`/`hints`, pero la **calidad
pedagógica la pone el autor** en 3 campos:

1. **`objective` (≥25 chars, siempre)**: explica el contrato completo — qué
   función/es definir, qué reciben, qué calculan y qué devuelven en los casos
   límite (cero, negativos, vacíos). No asumas que el título alcanza.
2. **`validator` con casos de prueba**: usá `function_cases` y pensá los casos
   **límite** además del caso feliz (negativos, cero, listas vacías, `None`).
   Con ≥3 casos por función el ejercicio es robusto y el `example` autogenerado
   queda ilustrativo. Menos de 2 casos hace que una solución "a medida" pase.
3. **`hints` (opcional)**: guiá el razonamiento (qué descomponer, qué límites
   validar), no pegues el código de la solución. El generador completa hasta 3
   si dejás menos.
4. **`classDiagram` (obligatorio en POO)**: todo desafío de clases debe incluir
   su diagrama de clase UML con atributos y firmas completas de métodos.
5. **Sin arrays ni estructuras complejas (Capítulos 1 a 3)**: en retos de POO
   básica, jamás pedir listas o diccionarios. Usar únicamente atributos
   escalares (`int`, `float`, `str`, `bool`) o composición simple. El generador
   falla si se intenta violar esta restricción.

Regla práctica: si el `example` autogenerado no te aclara el ejercicio, el
`objective` o los `cases` están mal planteados. Corré
`python tools/game_generator.py <json> --audit` antes de entregar.

> **Cap 1 oficial (`juego_gl01_oficial.json`)** = funciones + selectivas
> (GL02/GL03). Los diagramas de flujo (GL01) se enseñan como teoría en el
> Libro porque el motor valida código Python, no diagramas dibujados. Usa
> `def_return`/`print_call` en los desafíos.

### JSON de lección

`meta` + `chapter` (clave de `chapter_asset_sets` del kit) + `zone` (npcs e
interactables/decor con `asset`) + `lesson` (challenges con `validator`,
`requirements` para `structure`, `successAction`) + `book_pages`.
Detalle completo en `docs/generador_game.md`.

### Kit visual y Galería de Componentes

`public/juegos/visual/el_refugio_visual_assets_v1.json` define todos los assets
data-driven (estados, frames animados, hitbox, colisión, luz, partículas, oclusión).
El motor los renderiza con `JuegoArtAssetRenderer`.

**Catálogo visual interactivo**: `public/juegos/visual/el_refugio_assets_gallery.html`.

> **REGLA MANDATORIA DE ASSETS**:
> **Todos los elementos que se coloquen en un juego (`decor`, `interactables`, `portals`, `stations`, `npcs`) se DEBEN extraer estrictamente de esta galería de componentes.**
> - Antes de diseñar o agregar elementos a cualquier `juego_*.json`, abrir o consultar `el_refugio_assets_gallery.html` / `el_refugio_visual_assets_v1.json` para verificar el `id` exacto del asset, sus estados disponibles (`states` / `extraStates`), tamaños, hitboxes y animaciones.
> - Está **PROHIBIDO** inventar nombres o IDs de assets que no existan en el kit.
> - Si se requiere un nuevo componente o animación, debe incorporarse primero al kit visual (`el_refugio_visual_assets_v1.json`), sincronizarse con la galería y luego utilizarse en el juego.

### JSON schema

```json
{
  "meta": {
    "materia": "INF-220 · Programación Orientada a Objetos",
    "codigo": "GL01",
    "facultad": "UATF · Facultad de Ciencias Puras · Ing. Informática",
    "titulo": "Guide title",
    "subtitulo": "One-line subtitle",
    "semestre": "Ing. Informática · 2º semestre · Gestión 2026-02",
    "duracion": "3 h de laboratorio",
    "docente": "Docente: Ph.D. Juan Ramiro Villa · Auxiliar: Univ. Abdair Magdiel Coca Carlo"
  },
  "convenciones": "Plain text shown as a banner under the title.",
  "secciones": [
    {
      "num": "01",
      "titulo": "Section title",
      "bloques": [ ... ]
    }
  ]
}
```

### Block types (`"tipo"` in `bloques`)

| tipo | fields | renders as |
|------|--------|-----------|
| `texto` | `texto` | paragraph |
| `competencia` | `texto` | competency box |
| `lista` | `items[]` | bullet list |
| `pasos` | `items[]` ({texto, codigo?}) | numbered steps, optional code snippet |
| `definicion` | `titulo`, `texto` | dark definition box |
| `nota` | `texto` | note box |
| `ejemplo` | `texto` | example box |
| `figura` | `texto` | figure placeholder |
| `diagrama` | `titulo`, `code` | Mermaid flowchart (interactive, zoom/pan) |
| `quiz` | `pregunta`, `opciones[]`, `correcta`, `explicacion?` | self-check; `correcta` = **0-based index**; cada opción puede ser string o `{"texto","explicacion"}` y la pregunta puede llevar `explicacion` (se muestra al responder) |
| `simbolos` | — | table of flowchart symbols (inline SVG) |
| `sub` | `titulo`, `bloques[]` | subsection heading + nested blocks |
| `celda` | `in`, `out?` | runnable Python cell (Pyodide) `In[n]/Out[n]` |

Sections may instead carry `"rubrica": [{"criterio","descripcion","pts"}]`
or `"referencias": [string]`.

### Rendering behavior

- **Mermaid** library is injected only if some `diagrama` block exists.
- **Pyodide** (`v0.26.4`) is injected only if some `celda` block exists
  (checked recursively through `sub` blocks via `contiene_tipo`).
- A `prelude` defines `load_iris()` with a synthetic fallback so iris demos
  run even without scikit-learn on the browser.
- Mermaid syntax used for flowcharts: stadium `(["Inicio"])`, parallelogram
  `[/"Leer n"/]`, decision `{"¿condición?"}`, labeled edges `-- "Sí" -->`.

## Workflow to create a new guide

1. Write the content JSON in `public/clases_guia/` (Spanish content).
2. Run `python tools/gl_generator.py public/clases_guia/guia_contenido_<tema>.json`.
3. Verify: open the produced HTML, check diagrams/quizzes render.
4. Solved-exercise material goes in a separate JSON under
   `public/resultados_guia/`, rendered with `-o resueltos/guia_<tema>_resueltos.html`.
5. Regenerate `graphify-out/` (codegraph) when structure changes significantly:
   `/graphify` on the project root.

## Workflow to create a new game (chapter)

1. Write the content JSON in `public/juegos/juego_<codigo>_<tema>.json`
   (Spanish content, with `chapter` key + `zone`/`lesson`/`book_pages`).
   Use `python tools/game_generator.py --nuevo` for a standard skeleton.
2. Run `python tools/game_generator.py public/juegos/juego_<tema>.json`
   (the generator validates the schema before generating).
3. Verify: open the produced HTML, check the world renders, resolve the
   mission, and the TITI_SCORE contract fires inside the Titi iframe.
4. Generated game goes to `inf-220-g2/clases/Juego_<lesson_id>.html`.

## Environment gotchas (Windows / PowerShell)

- `python` on PATH is 3.11. The graphify venv (`uv tool graphifyy`) is a
  DIFFERENT interpreter; always run graphify through the interpreter saved in
  `graphify-out/.graphify_python`.
- PowerShell `>` redirection writes UTF-16 — write files via Python
  (`write_text(..., encoding="utf-8")`) or the Write tool, never shell redirect.
- `python -c` with nested quotes breaks in PowerShell — write a temp script
  to `%TEMP%\opencode\` instead.
- Never `git init` inside `inf-220-g2/` — the user does that.
