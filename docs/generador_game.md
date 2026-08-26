# GeneradorGame — Estándares para crear juegos en Titi

> Documento de estándares para crear videojuegos/actividades HTML interactivas
> que corran en el sandbox de Titi y reporten score al sistema.
> Fuente viva de la skill global: `titi-html-authoring`.

## 1. Por qué estos estándares (contexto crítico)

Titi ejecuta las actividades HTML dentro de un iframe con:

```
sandbox="allow-scripts"   (SIN allow-same-origin)
```

El documento corre con un **origin opaco**. Eso significa que CUALQUIER acceso a
APIs de almacenamiento (`localStorage`, `sessionStorage`, `indexedDB`,
`document.cookie`) lanza `SecurityError` y **rompe el juego**. Este fue el bug
de clase que se corrigió (presentaciones y juegos que intentaban persistir).

No cambiar el sandbox a `allow-same-origin`: pierde el aislamiento de seguridad.

## 2. Reglas duras (obligatorias)

| Regla | Detalle |
|---|---|
| Autocontenido | CSS, JS e imágenes inline o `data:`. Prohibido `src` remoto, `link`, `iframe`, `object`, `embed`, `form`. |
| **Nada de storage** | `localStorage`/`sessionStorage`/`indexedDB`/`document.cookie`/Cache API. Estado de partida vive solo en variables en memoria. |
| **Nada de navegación** | `window.open`, `location.*`, `target="_blank"`. Links externos → texto plano `<code>`. |
| **Nada de red** | `fetch`, `XMLHttpRequest`, `WebSocket` (CSP `connect-src 'none'`). |
| CSP estricta | Incluir siempre (ver §4). |
| Score | Reportar con contrato `TITI_SCORE` (ver §3). |

## 3. Contrato TITI_SCORE (el score)

Cuando el juego termina (o el jugador resuelve la actividad), enviar el score
con la forma EXACTA:

```js
function reportarScoreTiti(score) {
  const finalScore = Math.max(0, Math.min(100, Math.round(Number(score) || 0)));
  try {
    window.parent.postMessage({
      source: 'titi-html',
      type: 'TITI_SCORE',
      score: finalScore,                       // 0..100, entero
      attemptToken: window.__TITI_ATTEMPT_TOKEN, // lo inyecta Titi
    }, '*');
  } catch (e) { /* ejecución standalone (debug): ignorar */ }
}
```

- `score` SIEMPRE 0..100 entero (sanitizado).
- El `attemptToken` lo provee Titi vía `window.__TITI_ATTEMPT_TOKEN`. No lo
  inventes ni lo borres.
- Se envía una vez por intento (el mejor score lo calcula Titi).
- Actividad no evaluable (solo documentación) → no enviar score; completado manual.

En el motor, el envío lo hace `TitiBridge.submitScore()` (modo `postmessage`
dentro del iframe). En Demo Mode (standalone) no se envía nada.

## 4. CSP estricta obligatoria

```html
<meta http-equiv="Content-Security-Policy"
      content="default-src 'none'; base-uri 'none'; connect-src 'none';
               form-action 'none'; frame-src 'none'; img-src data:;
               media-src data:; font-src data:; style-src 'unsafe-inline';
               script-src 'unsafe-inline'">
```

## 5. Técnicas de juego permitidas

| Técnica | ¿OK? | Nota |
|---|---|---|
| `<canvas>` 2D | ✅ | Plataformas, puzzle, clicker, top-down. |
| `requestAnimationFrame` (game loop) | ✅ | Bucle estándar. |
| Web Audio (sintetizado) | ✅ | Oscillators/`AudioContext`; sin archivos externos. |
| Inputs teclado / touch / click | ✅ | `addEventListener`. |
| `IntersectionObserver` / scroll | ✅ | Scrollspy, progreso de lectura. |
| Guardar progreso entre sesiones | ❌ | No hay storage; rediseñá sin persistencia. |
| Assets externos / sprites | ❌ | Inline `data:` o dibujado en canvas. |
| Multiplayer / online | ❌ | Sin fetch/WebSocket. |
| Fullscreen / popups / descargas | ❌ | Bloqueado por sandbox. |

## 6. Estructura de un juego Titi (plantilla base)

Partí de la plantilla blindada del proyecto:

```
public/juegos/game_engine_template.html   ← motor "El Refugio Lógico" (NO se edita por lección)
public/juegos/visual/                     ← kit visual data-driven (assets + renderer + galería)
public/juegos/story_arc.json              ← universo, personajes y arco narrativo conectado
public/juegos/juego_<codigo>_<tema>.json  ← zona + misión (LESSONS) + libro por lección
```

## 6.1 Generador de juegos (script) — estilo consistente + historia conectada

Todos los juegos comparten el mismo motor y se generan con un script (no se
copia el HTML a mano). El motor vive en el template; el script solo inyecta la
zona, la misión, el libro y el subset de assets visuales.

```
tools/
├── game_generator.py          ← genera los juegos (RPG 2D)
└── gl_generator.py            ← genera las guías de clase (GL01/02/03)
```

### Uso

```sh
python tools/game_generator.py public/juegos/juego_gl01_oficial.json -o inf-220-g2/clases/Juego_Capitulo_1.html   # cap 1 oficial
python tools/game_generator.py public/juegos/juego_gl01_clases.json                                            # práctica GL01 (Clases)
python tools/game_generator.py public/juegos/juego_gl02_funciones.json -o inf-220-g2/clases/Juego_funciones_01.html
python tools/game_generator.py --nuevo                                                                          # esqueleto JSON nuevo
```

- `--nuevo`: crea un esqueleto JSON de lección estándar en `public/juegos/` para
  editar (mismo flujo que `gl_generator.py --nuevo`).
- Antes de generar, el script **valida el esquema** del JSON y falla con un
  mensaje claro si algo no cumple (longitud del `map`, ids duplicados,
  `missionNode`/`target` que no existe, `validator.kind`/`successAction.kind`
  desconocidos, etc.).

El script inyecta 5 placeholders en el template:

- `/*__ZONE_JS__*/` → el mapa, NPCs, interactuables y decoración de la zona.
- `/*__LESSONS_JS__*/` → la misión (`challenges` con `validate`/`onSuccess`).
- `/*__BOOK_JS__*/` → las páginas del Libro desbloqueables.
- `/*__ASSETS_JS__*/` → subset del kit visual recortado por capítulo.
- `/*__ASSET_RENDERER_JS__*/` → renderer canónico inline leído desde
  `public/juegos/visual/el_refugio_asset_renderer.js`; el template instancia
  `window.JuegoArtAssetRenderer` sin mantener una copia paralela.

### JSON de lección (`juego_gl01_clases.json`)

- `meta`: código, título, duración, semestre.
- `chapter`: clave en `chapter_asset_sets` del kit (`clases_y_objetos`,
  `encapsulamiento`, `herencia_polimorfismo`, `pilas_colas_listas`,
  `arboles_grafos`). El generador recorta los assets a este set.
- `zone`: `rows`, `cols`, `map` (filas de igual longitud), `flags`, `npcs`
  (con `asset`), `interactables` (con `type`, `asset`, `missionNode`, `solid`,
  `sortOffset`), `decor` (con `kind` + `asset`), `doors`.
- `lesson`: `id`, `title`, `concept`, `zone`, `story`, `introDialogue`,
  `objectives`, `challenges[]`.
- `book_pages`: páginas del Libro (`unlockedBy` para desbloqueo).

### Validadores y acciones data-driven

Los desafíos **no** guardan funciones JS en el JSON: referencian registros del
motor (`VALIDATORS` / `ACTIONS`) por `kind`. Así el generador emite código
consistente y el motor mantiene los errores educativos.

- `validator.kind`:
  - `structure` — POO: valida `classes` (nombre, `attrs` con `self.x`,
    `methods` con `self`, `returnText`), `instantiate` (crear objetos) y
    `calls` (llamar métodos). El spec se pasa por `requirements` del desafío.
  - `def_return` — funciones: `defName`, `params`, `sampleArgs` y `expected`
    (o `contains` para texto). Soporta booleanos (`True`/`False`).
  - `def_exists` — solo existe la función con la firma pedida.
  - `print_call` — hay un `print()` con el texto esperado.

En misiones abiertas se usa `validator.kind: "function_cases"` con una lista de
funciones (`defName`, `params`, `cases` con `args` y `expected`) y
`successAction.kind: "station_transition"`. El generador valida firmas, casos,
targets y estados `pending`/`active`/`completed` antes de emitir el HTML.
- `successAction.kind` (tema Refugio): `fogata` (enciende el hogar),
  `tienda` (arma la tienda), `campamento` (completa el campamento y abre el
  sendero). El `campamento` debe ser la acción del **último** desafío.

> **Nota — Capítulo 1 oficial y diagramas de flujo (GL01).** El motor valida
> **código Python** (`def_return`, `print_call`, `def_exists`, `structure`),
> no diagramas dibujados. Por eso el contenido de diagramas de flujo (GL01) se
> enseña como **teoría** en el Libro (`book_pages`) y en el diálogo, y los
> desafíos evaluables cubren funciones (GL02) y estructuras selectivas (GL03)
> con `def_return`/`print_call`. El `chapter` del JSON (`clases_y_objetos`)
> solo controla el recorte de assets visuales del kit, no el contenido
> conceptual.

Ejemplo de desafío con validador de estructura:

```json
{
  "id": "challenge1",
  "title": "El Fuego Inicial",
  "target": "fogata01",
  "objective": "Define una clase 'Fogata' con un método 'encender(self)' que devuelva 'Fuego encendido'.",
  "example": "class Fogata:\n    def encender(self):\n        return \"Fuego encendido\"\nmi_fuego = Fogata()\nmi_fuego.encender()",
  "hints": ["Usa la palabra clave class.", "Dentro, define def encender(self):"],
  "validator": { "kind": "structure" },
  "requirements": {
    "classes": [
      { "name": "Fogata", "methods": [ { "name": "encender", "returnText": "Fuego encendido" } ] }
    ],
    "instantiate": ["Fogata"],
    "calls": ["encender"]
  },
  "successAction": { "kind": "fogata", "id": "fogata01" },
  "successDialogue": ["Las ramas crujen y una luz cálida ilumina el claro."],
  "concepts": ["clases", "objetos", "metodos"]
}
```

### Kit visual (data-driven)

El motor renderiza TODO por assets del kit (`public/juegos/visual/el_refugio_visual_assets_v1.json`)
vía `JuegoArtAssetRenderer`:

- Cada asset define tamaño, ancla, hitbox, profundidad, estados (con frames
  animados opcionales) y metadata de luz/partículas/oclusión.
- El generador inyecta solo el subset del capítulo (evita inflar el HTML).
- `chapter_asset_sets` del kit mapea cada capítulo a sus assets.
- El renderer soporta `clipY`/`clipH` para dividir assets con oclusión
  (árboles: tronco en la pasada del mundo, copa encima del jugador).
- Los assets de personajes: `player_viajero`, `npc_alizon`,
  `npc_guardabosques` (derivado de Alizon por recolor programático).

### Historia conectada (`story_arc.json`)

Define el universo ("El Refugio Lógico"), los personajes persistentes (el
Viajero, Alizon, el Guardabosques) y un `chapters[]` con `lesson`/`id`/`title`/
`concept`/`historia`/`mision`/`cliffhanger` por lección. La continuidad vive en
el JSON (el sandbox no permite storage), y cada misión referencia su capítulo
para mantener el hilo narrativo.

> **Re-mapeo del arco.** El canon se alinea con el contenido real del curso: el
> **Capítulo 1** enseña funciones y estructuras selectivas (GL02/GL03) con los
> diagramas de flujo (GL01) como teoría, bajo el título "Los Planos del Viajero
> — La Lógica del Refugio". El resto del arco (encapsulamiento, herencia,
> pilas/colas, árboles/grafos) queda como POO posterior.

## 7. Validación ANTES de publicar (obligatoria)

```sh
node "C:\Users\abdai\.codex\skills\titi-html-authoring\assets\validate-titi-html.mjs" <juego.html> --check-score
```

Debe terminar en `✓ ... OK`. Si falla, corregí TODO lo que reporte.

El backend de Titi además valida en el servidor (`validateHtmlLessonResource`):
- `< 1 MB`, documento `<html>`, sin iframe/object/embed/link/form.
- Sin `src`/`poster`/`url()` externos (se ignora código dentro de `<script>`).
- Meta CSP propia permitida; otros `http-equiv` rechazados.
- `intentosMax` 1-10 solo si `evaluable`.

## 8. Integración con el flujo Titi

1. Creá una lección con `formatoContenido: "HTML"`.
2. Subí el archivo con `upsert_lesson_html` (MCP titi-authoring) o
   `POST /api/authoring/lessons/:id/html`.
3. `evaluable: true` + `intentosMax` (1-10) para que el score se registre.
4. Publicá la lección (`POST /lessons/:id/publish`).
5. El estudiante la ve en `/learn`, resuelve, y la **tarjeta "Tu nota"** muestra
   su mejor puntaje.

## 9. Checklist final antes de entregar

- [ ] Pasa `validate-titi-html.mjs --check-score` (salida OK).
- [ ] CSP estricta presente.
- [ ] Sin storage / sin navegación / sin fetch / sin `_blank`.
- [ ] `TitiBridge.submitScore` envía `TITI_SCORE` con `__TITI_ATTEMPT_TOKEN`.
- [ ] En modo libre, score configurado se envía una sola vez al resolver todos los retos.
- [ ] Score sanitizado 0..100.
- [ ] Autocontenido (< 1 MB).
- [ ] Probado dentro del iframe de Titi (no solo abriendo el archivo).
- [ ] Textos UTF-8 reales (sin mojibake `Ã`/`â€`/`Â`/`ðŸ`).
- [ ] Cámara centra el mundo cuando es menor que el viewport.

## 10. Encoding UTF-8 y centrado del canvas (bugs corregidos)

### 10.1 Mojibake en textos acentuados y emojis

El contenido en español (á é í ó ú ñ ¿ ¡) y los emojis deben guardarse como UTF-8
real. Si se guardan mal, se ven así (mojibake): `Ã¡`, `Ã­`, `â€”`, `ðŸŽ¯`.

**Causa:** los bytes UTF-8 se interpretaron como CP1252/Latin-1 al guardar o copiar.

**Reglas para evitarlo:**
- Guardar siempre con `encoding="utf-8"` explícito (jamás redirección de
  PowerShell `>` que escribe UTF-16, ni editores que persistan Latin-1).
- Verificar antes de publicar que no queden patrones `Ã`, `â€`, `Â`, `ðŸ`.
- Nota: el JSON del kit visual es UTF-8 válido; si un editor muestra
  reemplazos (`�`) puede ser solo la consola de Windows (CP850/1252), no el archivo.

### 10.2 Canvas / cámara pegada a la izquierda

Cuando el mundo (en tiles) es más chico que el viewport, la cámara se clavaba en
`(0, 0)` y el juego quedaba pegado arriba a la izquierda con un vacío negro a la
derecha/abajo.

**Regla:** en `Camera.follow()`, si `worldPxW <= viewW` el mundo debe centrarse
con `offset = (viewW - worldPxW) / 2` (igual en Y); solo recortar
(`clamp 0..world - view`) cuando el mundo es más grande que la vista.

**Gotcha (segundo bug):** `follow()` debe llamarse **cada frame, incluso con un
modal o diálogo abierto**. Si solo se llama cuando no hay modal, el `targetX/Y`
queda *stale* tras un `resize` (p. ej. el iframe de Titi ajustando su tamaño) y
el mundo se dibuja fuera de la pantalla. Solución: mover `camera.follow(...)`
fuera del bloque `if (!anyModalOpen)` del loop.

## 11. Referencias

- Template del motor: `public/juegos/game_engine_template.html`
- Kit visual: `public/juegos/visual/` (assets JSON + renderer + galería)
- Juego oficial cap 1: `public/juegos/juego_gl01_oficial.json` →
  `inf-220-g2/clases/Juego_Capitulo_1.html`
- Ejemplos de práctica: `inf-220-g2/clases/Juego_funciones_02.html` (GL01),
  `inf-220-g2/clases/Juego_funciones_01.html` (GL02)
- Generadores: `tools/game_generator.py`, `tools/gl_generator.py`
- Skill global: `C:\Users\abdai\.codex\skills\titi-html-authoring\SKILL.md`
- Validador: `assets/validate-titi-html.mjs`
