# Tarea: El Refugio Lógico — Los Objetos Perdidos (Práctica 5 · Clases, Objetos y Métodos)

> Task standalone para que un modelo cree el juego interactivo de la Práctica 5
> (Clases, Objetos y Métodos) con escenarios interiores (multi-zona), validación
> POO ejecutable y clima de escarcha. Todo lo nuevo de motor/generador debe vivir
> en **componentes reutilizables** (template, generador, kit visual) para que
> futuros juegos lo hereden.

---

## 1. Contexto del proyecto

- **Materia**: INF-220 · Programación Orientada a Objetos (UATF · Facultad de
  Ciencias Puras · Ing. Informática). Docente: Ph.D. Juan Ramiro Villa.
  Auxiliar: Univ. Abdair Magdiel Coca Carlo. Gestión 2026-02.
- **Repo raíz (FUENTES)**: `2026Semestre2` — contiene `tools/`, `public/`,
  `docs/`, `AGENTS.md`. **El subrepo `inf-220-g2/` es de ARTEFACTOS generados**
  (el usuario lo inicializa; no hacer `git init` allí).
- **Canon**: todos los juegos comparten la historia "El Refugio Lógico" definida
  en `public/juegos/story_arc.json` (universo, personajes, 5 capítulos, motor).
  Contenido siempre en **español**.

### Reglas de propiedad de archivos (obligatorias)

| Ubicación | Contenido |
|---|---|
| `public/juegos/juego_practica5_objetos.json` | JSON de lección (fuente) |
| `public/juegos/visual/el_refugio_visual_assets_v1.json` | assets nuevos (kit) |
| `public/juegos/game_engine_template.html` | motor (componente reutilizable) |
| `tools/game_generator.py` | generador (componente reutilizable) |
| `docs/generador_game.md` | estándares (actualizar) |
| `public/juegos/story_arc.json` | canon (agregar misión standalone) |
| `inf-220-g2/clases/Juego_practica5_objetos.html` | salida generada (artefacto) |

- **NO tocar** `inf-220-g2/practicas/` (carpeta del usuario).
- **NO tocar** `resueltos/` (fuera del repo).
- Los archivos de carrera (HTML generado) viven en `inf-220-g2/clases/`.
- No renumerar secciones; mantener `num` originales.
- **Textos de juego/UI en español** (canon y audiencia).

---

## 2. Fuente de contenido: Práctica 5

Documento fuente: `inf-220-g2/practicas/Practica_Nro_5_Clases_Objetos_Metodos.docx`.
Contiene **10 ejercicios** de Clases, Objetos y Métodos con estas reglas
generales:

- Cada clase incluye un constructor `__init__` que recibe e inicializa los
  atributos indicados en el diagrama de clase.
- Los métodos respetan exactamente nombres y funcionalidad del diagrama.
- Al final de cada archivo se crea al menos un objeto y se ejecutan todos los
  métodos mostrando resultados con `print()`.
- Código comentado: propósito de clase, atributos y métodos.

### Los 10 ejercicios (contratos exactos)

1. **Persona** — `Persona(nombre, edad)`; `saludar(): str` (incluye nombre);
   `es_mayor_de_edad(): bool` (True si edad >= 18). Crear dos objetos con datos
   distintos y probar ambos métodos.
2. **Rectángulo** — `Rectangulo(base, altura)`; `calcular_area(): float`;
   `calcular_perimetro(): float`; `es_cuadrado(): bool` (base == altura).
3. **CuentaBancaria** — `CuentaBancaria(titular, saldo_inicial)`;
   `depositar(monto): None` (rechaza montos <= 0); `retirar(monto): bool`
   (verifica saldo suficiente; True si éxito, False si no);
   `consultar_saldo(): float`. Probar depósito, retiro válido y retiro que excede.
4. **Producto** — `Producto(nombre, precio, stock)`;
   `vender(cantidad): bool` (solo si hay stock; reduce y True);
   `reponer_stock(cantidad): None`; `valor_inventario(): float` (precio*stock).
5. **Estudiante** — `total_estudiantes: int` (**atributo de clase**);
   `__init__(nombre, registro_academico)` incrementa el total;
   `mostrar_datos(): str`; `Estudiante.obtener_total(): int` (**@classmethod**).
   Crear 3 objetos y mostrar el total final.
6. **Empleado** — `__salario: float` (**privado**); `__init__(nombre, salario)`;
   `get_salario(): float`; `aumentar_salario(porcentaje): None` (rechaza
   porcentajes negativos); `__str__(): str` (nombre y salario legibles).
   Probar aumentando dos veces con distintos porcentajes.
7. **CarritoDeCompras** — `total: float`, `cantidad_productos: int` (sin arrays ni listas);
   `agregar_producto(precio): None`; `quitar_producto(precio): bool` (valida cantidad > 0
   y total >= precio); `calcular_total(): float`; `vaciar_carrito(): None`. Acumulador escalar puro.
8. **Vehículo** — `Vehiculo(marca, modelo, velocidad_maxima)`; atributos
   `marca`, `modelo`, `velocidad_actual`, `velocidad_maxima`;
   `acelerar(incremento): None` (no supera velocidad_maxima);
   `frenar(decremento): None` (no baja de 0); `mostrar_info(): str`.
   Simular aceleraciones y frenados mostrando velocidad después de cada uno.
9. **Libro** — `Libro(titulo, autor)` con `disponible: bool` (True por defecto);
   `prestar(): bool` (True si estaba disponible, la marca no disponible; False
   si ya prestado sin cambios); `devolver(): None`; `__str__(): str` con estado
   (Disponible / Prestado).
10. **Estudiante y Fecha (composición)** — clase `Fecha(dia, mes, anio)` con
    `__str__(): str` (dd/mm/aaaa); clase `Estudiante(nombre, fecha_nacimiento)`
    que recibe un objeto `Fecha` ya construido; `mostrar_ficha(): str` combina
    nombre con fecha. Sin herencia, solo composición.

---

## 3. Historia: "El Refugio Lógico: Los Objetos Perdidos"

### Premisa

El viajero dejó la **Ciudad de la Interfaz**: un lugar donde todo está
automatizado y nadie sabe cómo funciona el mundo por dentro. Se adentró en el
**Gran Backend**, un bosque salvaje donde la ley es clara: *nada está
automatizado; para sobrevivir hay que entender la lógica y construirla con
código*.

En lo profundo del bosque, el viajero y **Alizon** tropiezan con las **ruinas
de la antigua Ciudad de la Interfaz**, sepultadas bajo el musgo y la escarcha.
No son edificios vacíos: es un **cementerio de objetos**. Máquinas
registradoras, armarios con inventarios, cartas de nómina, carretas, un único
manual de biblioteca… todo **inerte**. La gente de la ciudad los usaba sin
entenderlos — solo tocaban botones, solo la interfaz.

**Alizon confiesa**: ella también es de la ciudad. Recuerda estos objetos
funcionando. "Los usábamos sin entenderlos", dice. "Nunca supimos construir
ninguno. Hasta hoy."

**Urgencia**: la **escarcha** avanza desde las ruinas hacia el campamento. Cada
objeto que el viajero **reconstruye por dentro** — convirtiéndolo en una
**clase** con atributos y métodos — **vuelve a la vida y empuja la escarcha de
vuelta**.

**Frase-eje** (recurrente en diálogos): *"En la ciudad tocábamos los botones.
Acá construís el interior."*

### La metáfora pedagógica

| Concepto de la ciudad | Concepto POO |
|---|---|
| El botón que todos tocaban sin entender | La interfaz |
| El funcionamiento interno que nadie conocía | La clase: `__init__`, atributos, métodos |
| El objeto que cobra vida al entenderlo | La instancia creada y usada |
| Alizon *recuerda* el objeto funcionando | El contrato (lo que cada método debe devolver) |

### Escenarios (multi-zona)

La misión se juega en **5 zonas** (exterior + 4 interiores). Cada interior es
un **escenario nuevo** (mapa, paleta, clima y decoración propios) al que se
entra por un **portal**.

| Zona | Escenario | Objetos perdidos (retos) |
|---|---|---|
| `exterior` | Plaza de las Ruinas | Alma (Persona), La Medida (Rectángulo) |
| `posada` | La Posada (interior de hotel) | La Caja (CuentaBancaria), La Nómina (Empleado), La Ficha (Fecha+Estudiante) |
| `banco` | El Banco (interior) | El Almacén (Producto) |
| `escuela` | La Escuela del Manual (interior) | Estudiante (@classmethod), El Único Manual (Libro) |
| `taller` | El Taller (interior) | El Carro (CarritoDeCompras), La Carreta (Vehículo) |

**Lógica narrativa de la escarcha**: los altares exteriores están más
expuestos; los interiores son refugios que también se congelan desde adentro.
El orden secuencial estricto de la práctica justifica la progresión.

### Cierre narrativo

Con los 10 objetos vivos, el campamento es una mini-sociedad que funciona:
sabe quién es (`Persona`), mide su tierra (`Rectangulo`), guarda su tesoro
(`CuentaBancaria`), inventaría su comida (`Producto`), cuenta a sus aprendices
(`Estudiante`), paga con justicia (`Empleado`), se abastece
(`CarritoDeCompras`), se transporta (`Vehiculo`), conserva su único manual
(`Libro`) y recuerda a sus personas (`Fecha+Estudiante`).

Alizon, al final: *"La ciudad lo tenía todo y no entendía nada. Acá lo
construiste todo y lo entendés todo. Ahora el bosque no tiene secretos para tus
manos."*

Cliffhanger hacia el canon: **El Resguardo frente a la Tormenta —
Encapsulamiento** — algo se acerca desde el horizonte y los objetos del
campamento ahora necesitan **protegerse**.

### Diálogos de ejemplo (`successDialogue`)

- Alma: "El maniquí pronuncia tu nombre. La primera voz del refugio despierta."
- Caja: "La caja cantó al recibir un depósito. Alizon sonríe: 'Así sonaba en la
  ciudad, cuando aún la entendíamos'."
- Manual: "El libro se presta solo una vez y vuelve entero. La biblioteca
  respira de nuevo."
- Ficha: "La ficha une el nombre con su fecha. La expedición ya tiene memoria."
- Cierre (objeto 10): "Las diez piezas brillan en el claro. La escarcha se
  retira hacia las ruinas, y el sendero hacia lo profundo del bosque se abre."

Cada **portal** tiene un diálogo de entrada propio (la Posada susurra recuerdos
del hotel; el Banco huele a cajas fuertes; la Escuela guarda el eco del manual;
el Taller conserva olor a aceite y madera).

---

## 4. Fase 1 — Extender el motor (componentes reutilizables)

> Toda novedad del motor debe implementarse en `game_engine_template.html` (el
> template NO se copia por lección) y en `tools/game_generator.py`. Nada de
> parches solo para este juego.

### 4.A Multi-zona + portales (novedad principal)

Estado actual: `const ZONE = /*__ZONE_JS__*/` es global; `World` se construye
una vez en `startLesson`; las puertas solo abren el sendero (`abrirSendero`).
Diseño objetivo:

1. **Registro de zonas**: el generador inyecta
   `const ZONES = /*__ZONES_JS__*/` (objeto `{ exterior: {...}, posada: {...},
   ... }`) y mantiene `ZONE` = `ZONES.exterior` por compatibilidad.
2. **`World.load(zoneData)`**: método que reconstruye `rows`, `cols`, `tiles`,
   `flags`, `npcs`, `interactables`, `decor`, `doors` desde los datos de una
   zona. El constructor actual pasa a delegar en `load(ZONE)`.
3. **Portal**: los `interactables` admiten `"type": "portal"` con campos
   `toZone`, `spawnX`, `spawnY`. Al interactuar con un portal, el juego cambia
   de zona. Para retoques menores de ancla puede usar `markerAsset` opcional.
4. **`Game.enterZone(zoneId, spawnX, spawnY)`**: hace `world.load(ZONES[zoneId])`,
   reposiciona al jugador en el spawn, resetea la cámara
   (`camera.x = camera.y = 0`), reconstruye `InteractionSystem` y `WorldActions`
   sobre el nuevo mundo, y cambia el clima/paleta según `zoneData.weather`.
5. **Tiles de interior**: agregar chars nuevos a `TILE_DEF` y a su render en el
   bucle de tiles (línea ~1029-1043): `W` (pared, no caminable), `F` (piso,
   caminable), `C` (mueble, no caminable). Paleta interior propia (colores
   cálidos de madera/techos).
6. **Radar multi-zona** (`renderRadar` y `renderGuide`): si el reto activo vive
   en otra zona, la guía dorada apunta al **portal** que lleva a esa zona; al
   entrar, apunta al altar interior. El radar lista los retos de **todas** las
   zonas (con su estado) y usa `markerAsset` para marcarlos.
7. **Clima por zona**: cada zona tiene su propio `weather` (los interiores
   pueden tener `mode: "none"` o una escarcha tenue). El render de fase de
   tormenta/escarcha debe leer el clima de la zona activa, no el de `ZONE`
   global (hoy usa `ZONE.weather` — cambiar a `world.weather` o equivalente).

### 4.B POO ejecutable — validator `class_cases`

El mini-intérprete actual (`PythonEngine`) no soporta `class`, y el validator
`structure` es estático (regex, sin ejecución). Para validar **comportamiento**
se añade un nuevo kind ejecutable:

1. **Parser**: `_safeParse` debe aceptar nodos `class` (nombre, métodos,
   `__init__`, decorador `@classmethod`, `__str__`) con su cuerpo indentado.
2. **Intérprete**: soportar binding de `self`, instancias con atributos,
   dispatch de métodos, **name mangling** `_Clase__atributo` para privados,
   paso de objetos como argumentos (composición), y `str(obj)` → `__str__`.
   Mantener el límite seguro de 1000 pasos y los errores educativos.
3. **Validator `class_cases`** en `VALIDATORS` (mismo estilo que
   `function_cases`): a partir de `spec.requirements` (o `spec` directo):
   - `initArgs` para instanciar; `methods[].cases[].args/expected` para llamar
     y comparar retorno con `engine._deepEqual`.
   - Soporta valores numéricos, booleanos (`True`/`False`), strings y listas.
   - Verifica que los métodos/atributos pedidos existan y que **los privados no
     se accedan directamente desde fuera** de la clase.
   - Verifica `@classmethod` (llamada por clase: `Estudiante.obtener_total()`).
   - Mensajes de error pedagógicos en español (estilo de los existentes:
     "devolvió X, se esperaba Y" + hint).
   - `__str__` se prueba con `str(objeto)` o `print(objeto)`.

### 4.C Escarcha

1. **`WeatherSystem`**: nuevo modo `"frost"` — partículas de nieve fina
   descendentes (reusa el pool de gotas con caída vertical lenta y color
   blanco-azulado; `_isRain` → generalizar `_active()` por modo).
2. **Overlay de fase por zona**: en el render de fase (hoy bloque `stormPhase`,
   línea ~1051) parametrizar color por zona/clima: escarcha azul-blanca en vez
   del púrpura de tormenta. Mantener `lesson.storm.thresholds` como disparador
   de fases (reusar `stormPhase()`).
3. **Generador**: aceptar `mode: "frost"` en `zone.weather` (validación de
   esquema) y documentar campos válidos (misma familia numérica que rain).

### 4.D Generador (`tools/game_generator.py`)

- `VALIDATORS_REGISTRY`: agregar `"class_cases"`.
- `ACTIONS_REGISTRY`: mantener `station_transition` (y el resto).
- **Validación de esquema**: 
  - Si el JSON trae `zones` (objeto), validar cada zona (rows/cols/map con
    longitudes consistentes, ids únicos por zona, npcs/interactables/decor/
    doors).
  - Para `class_cases`: validar `requirements`/spec (clases, `initArgs`,
    `methods`, `cases` con `args`/`expected`, `classmethod`, `privateAttrs`).
  - Validar `portal`: `toZone` debe existir en `zones`; `spawnX/spawnY` dentro
    del mapa destino.
- **Inyección**: emitir `/*__ZONES_JS__*/` (todas las zonas) y mantener
  `/*__ZONE_JS__*/` = zona exterior. `build_zone_js` debe poder serializar una
  zona individual; nuevo helper para el registro completo.
- **Assets**: `_zone_asset_ids` y `build_assets_js` deben agregar los ids de
  **todas** las zonas (recorrer `zones`) + los del capítulo.
- **Autocompletado pedagógico**: extender `_autoejemplo`, `_autostarter` y
  `_autohints` para `class_cases` (generar ejemplo a partir de `initArgs` +
  primer caso de cada método; esqueleto `class`/`__init__`; pistas de POO).
- **`--audit`**: incluir métricas de `class_cases` (casos por método, ejemplo,
  hints). Falla con código 1 si algún desafío incumple los mínimos.

### 4.E Docs

- `docs/generador_game.md`: documentar multi-zona/portales (`zones`, `portal`,
  `toZone`, `spawnX/spawnY`), validator `class_cases` (con ejemplo), modo
  `frost`, y el flujo para crear juegos multi-escenario.

---

## 5. Fase 2 — Kit visual (`el_refugio_visual_assets_v1.json`)

Agregar al kit (data-driven, estilo pixel-art del proyecto):

- **10 assets de objetos perdidos** (con estados `pendiente`/`reconstruido`):
  maniquí (Persona), marco (Rectángulo), caja registradora (CuentaBancaria),
  estante (Producto), pizarra (Estudiante), cofre (Empleado), carretilla
  (Carrito), carreta (Vehículo), libro (Libro), archivo/ficha (Fecha+Estudiante).
- **Assets de interior**: pared, piso, muebles genéricos (mesa, silla,
  lámpara), puertas interiores. Estilo cálido de madera.
- **Assets de portales/edificios** para el exterior: fachadas de la Posada, el
  Banco, la Escuela y el Taller (con estado de puerta).
- **Markers**: reusar el patrón `marker_*` (uno por reto) para el radar
  multi-zona.
- Nuevo `chapter_asset_set`: `practica_5_objetos` (incluye jugador, Alizon,
  árboles, y los assets nuevos).
- Actualizar `public/juegos/visual/el_refugio_assets_gallery.html` si el
  formato lo requiere (galería lee el manifest).

---

## 6. Fase 3 — Crear el juego (`public/juegos/juego_practica5_objetos.json`)

### `meta`

```json
{
  "materia": "INF-220 · Programación Orientada a Objetos",
  "codigo": "PRACTICA5",
  "facultad": "UATF · Facultad de Ciencias Puras · Ing. Informática",
  "titulo": "El Refugio Lógico: Los Objetos Perdidos",
  "subtitulo": "Diez objetos de la Ciudad de la Interfaz, reconstruidos por dentro con clases, objetos y métodos.",
  "semestre": "Ing. Informática · 2º semestre · Gestión 2026-02",
  "duracion": "Práctica abierta",
  "docente": "Docente: Ph.D. Juan Ramiro Villa · Auxiliar: Univ. Abdair Magdiel Coca Carlo"
}
```

### Estructura

```json
{
  "meta": { ... },
  "chapter": "practica_5_objetos",
  "zone": { /* exterior: rows, cols, map, flags, weather, npcs, interactables, decor, doors */ },
  "zones": {
    "exterior": { /* igual que zone (o reference) */ },
    "posada":   { "rows": ..., "cols": ..., "map": [...], "flags": {...}, "weather": {...}, "npcs": [...], "interactables": [...], "decor": [...], "doors": [...] },
    "banco":    { ... },
    "escuela":  { ... },
    "taller":   { ... }
  },
  "lesson": {
    "id": "practica5_objetos",
    "title": "El Refugio Lógico: Los Objetos Perdidos",
    "concept": "clases, objetos y métodos",
    "zone": "exterior",
    "introTarget": "alizon",
    "story": ["..."],
    "introDialogue": { "speaker": "Alizon", "lines": ["..."] },
    "objectives": { "intro": "...", "objeto_alma": "...", "..." },
    "progression": { "mode": "sequential", "strict": true },
    "completion": { "score": 100 },
    "ui": { "bookTitle": "Manual de Supervivencia", "editorLabel": "OBJETOS · TALLER DE RECONSTRUCCIÓN", "showDuration": false },
    "storm": { "thresholds": [ {maxSolved:2, phase:"solved_0_2"}, {maxSolved:5, phase:"solved_3_5"}, {maxSolved:8, phase:"solved_6_8"}, {maxSolved:9, phase:"solved_9"}, {maxSolved:10, phase:"solved_10"} ] },
    "challenges": [ ... 10 desafíos ... ]
  },
  "book_pages": [ ... 9 páginas ... ]
}
```

### Los 10 desafíos (`challenges[]`)

Cada uno con `id`, `title`, `target` (altar en su zona), `objective` (>= 25
chars, contrato completo con casos límite), `example`, `starterCode`, `hints`
(>= 3), `validator: {"kind":"class_cases"}` + spec/requirements, `successAction:
{"kind":"station_transition","id":"<altar>"}`, `successDialogue`, `concepts`.

**Casos límite por ejercicio** (obligatorios, además del caso feliz):

| Reto | Casos límite |
|---|---|
| alma | `es_mayor_de_edad` con 17 (False) y 18 (True); `saludar` incluye el nombre |
| medida | área/perímetro con base=altura (es_cuadrado True); valores decimales |
| caja | `depositar(0)` y `depositar(-5)` rechazados (saldo intacto); `retirar` mayor que saldo → False y saldo intacto |
| almacen | `vender(cantidad > stock)` → False y stock intacto; `valor_inventario` con stock 0 |
| escuela | `obtener_total()` después de crear 3 estudiantes → 3 (y con 0 → 0) |
| nomina | `aumentar_salario(-10)` rechazado (salario intacto); `__str__` legible; `get_salario` |
| carro | `quitar_producto` con precio > total → False; `calcular_total` con carrito vacío → 0; descuento correcto |
| carreta | `acelerar` no supera `velocidad_maxima`; `frenar` no baja de 0 |
| manual | `prestar()` dos veces → segunda False; `__str__` muestra Disponible/Prestado |
| ficha | `Fecha.__str__` formato dd/mm/aaaa; `mostrar_ficha` combina nombre y fecha |

### `book_pages` (teoría POO, el Libro/Manual)

Páginas desbloqueables con `unlockedBy` (concepto) y campos `what`, `syntax`,
`example`, `commonError`, `tip`:

1. ¿Qué es una clase? (el plano de un objeto)
2. `__init__` y `self` (cómo nace un objeto)
3. Atributos (lo que cada objeto guarda)
4. Métodos (lo que cada objeto sabe hacer)
5. Retorno de valores (el contrato)
6. `@classmethod` y atributos de clase (memoria compartida)
7. Encapsulamiento (el candado del cofre)
8. Composición (objetos que contienen objetos)
9. `__str__` (cómo se presenta un objeto)

---

## 7. Fase 4 — Canon (`story_arc.json`)

Agregar la misión como **práctica standalone** (fuera de la secuencia de los 5
capítulos), con entrada en `chapters` o sección de prácticas que incluya:
`id`, `title` ("Los Objetos Perdidos"), `concept` ("clases, objetos y
métodos"), `historia`, `mision`, `cliffhanger` (hacia El Resguardo frente a la
Tormenta / encapsulamiento). Mantener la continuidad del universo y personajes.

---

## 8. Fase 5 — Generar y verificar

```sh
# Auditoría pedagógica antes de generar
python tools/game_generator.py public/juegos/juego_practica5_objetos.json --audit

# Generar el juego (valida esquema, autocompleta, inyecta zonas/assets)
python tools/game_generator.py public/juegos/juego_practica5_objetos.json \
  -o inf-220-g2/clases/Juego_practica5_objetos.html
```

Verificación manual (browser / Playwright):
1. Abrir el HTML: el mundo exterior renderiza con la Plaza de las Ruinas y las
   fachadas de los 4 edificios.
2. Hablar con Alizon; seguir el orden secuencial (radar apunta al altar activo).
3. **Entrar a cada edificio** por su portal: el jugador aparece dentro, la
   cámara se resetea, el clima interior se aplica, la guía apunta al altar
   interior. Resolver los retos de esa zona.
4. Volver al exterior por el portal de salida (spawn correcto).
5. Resolver los 10 retos con soluciones correctas e incorrectas (los errores
   deben ser claros: "devolvió X, se esperaba Y").
6. Verificar privados: acceso directo a `__salario` desde fuera debe fallar.
7. Verificar `@classmethod`: `Estudiante.obtener_total()` funciona.
8. Escarcha: overlay azul-blanca retrocede por fases al resolver.
9. Contrato `TITI_SCORE` al completar (100) dentro del iframe de Titi.
10. Validador externo:
    `node "...\titi-html-authoring\assets\validate-titi-html.mjs" <juego.html> --check-score`
    → salida OK.

Regenerar `graphify-out/` (codegraph) si la estructura cambia
significativamente (los cambios de template/generador son estructurales).

---

## 9. Definition of done

- [ ] `docs/generador_game.md` documenta multi-zona, `class_cases` y `frost`.
- [ ] `game_engine_template.html`: multi-zona/portales, `class_cases`, `frost`,
      tiles de interior, radar multi-zona — todo reutilizable por otros juegos.
- [ ] `game_generator.py`: inyecta `ZONES`, valida portales/clases, registra
      `class_cases`, autocompleta, audita. `--audit` con 0 problemas.
- [ ] Kit visual: 10 assets de objetos + interiores + fachadas + markers +
      `chapter_asset_set` `practica_5_objetos`.
- [ ] `juego_practica5_objetos.json` con 5 zonas y 10 desafíos `class_cases`
      con casos límite y `objective` >= 25 chars.
- [ ] `story_arc.json` con la misión standalone.
- [ ] `inf-220-g2/clases/Juego_practica5_objetos.html` generado y verificado
      en browser: entradas/salidas de los 4 edificios, 10 retos resueltos,
      escarcha por fases, `TITI_SCORE` correcto.
- [ ] `validate-titi-html.mjs --check-score` → OK.
- [ ] Textos en español sin mojibake (UTF-8 real).
- [ ] Sin storage / sin navegación / sin fetch / CSP estricta presente.
- [ ] Microcommits por cambio coherente (motor, generador, kit, JSON, canon,
      docs) con mensajes conventional commits.

---

## 10. Gotchas de entorno (Windows / PowerShell)

- `python` en PATH es 3.11; graphify usa OTRO intérprete (ver
  `graphify-out/.graphify_python`).
- PowerShell `>` escribe UTF-16 — escribir archivos con Python
  (`write_text(..., encoding="utf-8")`) o la herramienta Write, nunca con
  redirección de shell.
- `python -c` con comillas anidadas rompe en PowerShell — usar script temporal
  en `%TEMP%\opencode\`.
- No `git init` dentro de `inf-220-g2/`.
- Al regenerar el template/generador, verificar que los juegos existentes
  (Capítulo 1, funciones 01/02, práctica 4) **siguen generándose** sin errores
  (compatibilidad retroactiva: `zones` opcional).