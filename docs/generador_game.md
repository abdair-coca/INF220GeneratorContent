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

El script inyecta 6 placeholders en el template:

- `/*__ZONE_JS__*/` — el mapa, NPCs, interactuables y decoración de la zona exterior.
- `/*__ZONES_JS__*/` — el registro completo de zonas (`{ exterior, posada, ... }`)
  para juegos multi-escenario; en juegos sin `zones` se deriva solo `exterior`.
- `/*__LESSONS_JS__*/` — la misión (`challenges` con `validate`/`onSuccess`).
- `/*__BOOK_JS__*/` — las páginas del Libro desbloqueables.
- `/*__ASSETS_JS__*/` — subset del kit visual recortado por capítulo.
- `/*__ASSET_RENDERER_JS__*/` — renderer canónico inline leído desde
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
- `zones` (opcional): registro `{ zoneId: {...zona} }` de **interiores** para
  juegos multi-escenario. La zona exterior del `zone` se registra como
  `exterior`. Cada zona puede tener su propio `map`, `npcs`, `interactables`,
  `decor`, `doors` y `weather`. Para entrar/salir se usan interactables con
  `"type": "portal"` y campos `toZone` (zona destino), `spawnX`/`spawnY`
  (posición de aparición en la zona destino). El motor cambia de zona con
  `Game.enterZone()`; la guía dorada apunta al portal correcto si el reto
  activo vive en otra zona, y el radar lista los retos de todas las zonas.
  - **Tiles de interior**: `W` (pared, no caminable), `F` (piso, caminable),
    `C` (mueble, no caminable) además de los tiles exteriores (`G`, `g`, `P`,
    `H`, `T`, `D`).
- `lesson`: `id`, `title`, `concept`, `zone`, `story`, `introDialogue`,
  `objectives`, `challenges[]`.
- `book_pages`: páginas del Libro (`unlockedBy` para desbloqueo).

### Validadores y acciones data-driven

Los desafíos **no** guardan funciones JS en el JSON: referencian registros del
motor (`VALIDATORS` / `ACTIONS`) por `kind`. Así el generador emite código
consistente y el motor mantiene los errores educativos.

- `validator.kind`:
  - `structure` — POO estático: valida `classes` (nombre, `attrs` con `self.x`,
    `methods` con `self`, `returnText`), `instantiate` (crear objetos) y
    `calls` (llamar métodos). El spec se pasa por `requirements` del desafío.
    No ejecuta el código: verifica la forma, no el comportamiento.
  - `class_cases` — POO **ejecutable**: el motor interpreta `class`, `self`,
    instancias, `@classmethod`, name mangling de privados (`_Clase__atributo`),
    composición y `__str__`. El spec (`requirements.classes[]`) define por
    clase: `initArgs` (argumentos de `__init__`), `instances` (cuántos objetos
    crear; default 1), `methods[]` con `cases[]` (`args`/`expected`),
    `classMethods[]` (deben llevar `@classmethod`), y `privateAttrs[]` (deben
    declararse con `self.__atributo` y no accederse directamente desde fuera).
    Compara retornos con igualdad profunda (números, booleanos, strings,
    listas). Ver ejemplo abajo.
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

Ejemplo de desafío con validador **ejecutable** `class_cases` (verifica el
comportamiento, no solo la forma):

```json
{
  "id": "ej2_medida",
  "title": "La Medida del Claro",
  "target": "altar_medida",
  "objective": "Define la clase Rectangulo con __init__(base, altura), calcular_area() que retorne base * altura, calcular_perimetro() que retorne 2 * (base + altura) y es_cuadrado() que retorne True si base y altura son iguales.",
  "validator": { "kind": "class_cases" },
  "requirements": {
    "classes": [
      {
        "name": "Rectangulo",
        "initArgs": [5, 10],
        "methods": [
          { "name": "calcular_area", "cases": [ { "args": [], "expected": 50 } ] },
          { "name": "calcular_perimetro", "cases": [ { "args": [], "expected": 30 } ] },
          { "name": "es_cuadrado", "cases": [ { "args": [], "expected": false } ] }
        ]
      }
    ]
  },
  "successAction": { "kind": "station_transition", "id": "altar_medida" },
  "successDialogue": ["El marco mide el claro sin dudar."],
  "concepts": ["clases", "metodos", "atributos"]
}
```

> `class_cases` admite además `instances` (crear N objetos antes de probar,
> útil para `@classmethod` contadores), `classMethods: [{"name": "..."}]`
> (exige `@classmethod`), y `privateAttrs: ["__salario"]` (exige declararlo
> privado y acceder solo por métodos). El motor interpreta el subconjunto POO:
> clases, `__init__`, `self`, atributos, métodos, `@classmethod`, atributos de
> clase, name mangling y composición.

### Diagramas de Clase UML (`classDiagram`)

Todo reto de POO (`structure`, `class_cases`) debe incorporar su diagrama de clases UML bajo el campo `classDiagram` para que el estudiante visualice el contrato antes de programar:

```json
"classDiagram": [
  {
    "className": "Persona",
    "attributes": [
      "- nombre: str",
      "- edad: int"
    ],
    "methods": [
      "+ __init__(nombre, edad)",
      "+ saludar(): str",
      "+ es_mayor_de_edad(): bool"
    ]
  }
]
```

- **Soporte multi-clase**: permite varias tarjetas (ej. `Fecha` y `Estudiante`) con relaciones opcionales (`"relation": "──◆"`).
- **Visibilidad visual**: en la consola del juego se renderiza como tarjeta UML con distintivos de color:
  - `-` (rojo): atributo o método privado / protegido.
  - `+` (verde): método o atributo público.
  - `~` (amarillo): atributo o método de clase (`@classmethod`).
- **Autocompletado**: si el autor omite `classDiagram`, `game_generator.py` deriva automáticamente un esquema básico a partir de `requirements.classes`.
- **Auditoría**: `game_generator.py --audit` marca error si algún desafío de POO carece de diagrama de clases.

### Regla Pedagógica Estricta: Prohibición de Arrays y Estructuras Complejas

En todos los niveles y prácticas de POO introductoria (`clases_y_objetos`, `practica_5_objetos`, `encapsulamiento`, `herencia_polimorfismo`):

1. **NO usar listas, arrays, tuplas, conjuntos ni diccionarios** dentro de las clases de los ejercicios ni en sus firmas.
2. **El enunciado/objetivo y las pistas JAMÁS deben pedir listas ni arrays**: el estudiante solo debe manejar tipos primitivos escalares (`int`, `float`, `str`, `bool`) o composición simple de instancias.
3. **Fundamento pedagógico**: las estructuras de datos (listas, pilas, colas) corresponden formalmente al **Capítulo 4** ("El Ritmo de la Supervivencia"). Exigirlas antes rompe la curva de aprendizaje y satura cognitivamente al alumno.
4. **Validación automática**: el generador valida el esquema y audita con expresiones regulares la ausencia de términos como `lista`, `array`, `arreglo`, `diccionario`, `tupla` en los textos del reto.

### Clima (`zone.weather` / `zones.<id>.weather`)

Cada zona puede llevar su propio clima. Modos válidos: `none`, `rain`
(lluvia), `storm` (tormenta, requiere `lesson.storm.thresholds` para las
fases) y `frost` (escarcha/nieve fina). La escarcha usa el mismo sistema de
fases que la tormenta pero con overlay azul-blanca (`overlayColor` opcional en
la config de la zona). Campos numéricos: `density`, `dropCount`, `dropLength`,
`dropSpeed`, `wind`, `gust`, `gustPeriod`, `alpha`, `color`. Los interiores
suelen usar `mode: "none"`.

### Autocompletado pedagógico y auditoría de calidad

El generador **deriva contenido explicativo del validador** cuando el autor lo
omite, para que ningún desafío salga sin ejemplo o sin esqueleto:

- `example` vacío → se arma `fn(args) -> resultado` con un caso normal y un
  caso límite de `function_cases` (o `sampleArgs`/`expected` en `def_return`).
  En `class_cases` se deriva `Clase(initArgs)` + `Clase.metodo(args) -> valor`.
- `starterCode` vacío → esqueleto `def fn(param): return None` por función; en
  `class_cases` se deriva `class X:` con `__init__` y `return None` por método.
- `hints` con menos de 3 → se completan con pistas genéricas (firma exacta,
  casos límite, usar `return` en vez de `print`).

Los valores **explícitos del autor siempre ganan**: el autocompletado solo
toca campos vacíos. Al generar se avisa por stderr qué campos se llenaron.

Antes de publicar una lección nueva corré la auditoría:

```
python tools/game_generator.py public/juegos/juego_gl04_tema.json --audit
```

Reporta por desafío: longitud del `objective` (mín. 25), presencia de
`example`/`starterCode`, cantidad de `hints` y nº de casos por función (o por
método en `class_cases`). Sale
con código **1** si algún desafío incumple el mínimo (objetivo corto, sin
ejemplo, sin esqueleto, <2 pistas, <2 casos), lo que corta CI/release.

Regla práctica: si el `example` autogenerado no te aclara el ejercicio, el
`objective` o los `cases` están mal planteados.

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
- [ ] Corrió `game_generator.py <json> --audit` y reportó 0 problemas.
- [ ] Todo desafío tiene `objective` ≥25 chars y `example` ilustrativo.
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
