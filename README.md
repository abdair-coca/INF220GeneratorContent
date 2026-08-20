# INF220GeneratorContent

Contenido fuente del generador de guías y juegos interactivos para la materia
**INF-220 · Programación Orientada a Objetos** (UATF · Facultad de Ciencias
Puras · Ing. Informática), gestionada por el auxiliar Abdair Magdiel Coca
Carlo y el docente Ph.D. Juan Ramiro Villa.

## Contenido

- `tools/` — generadores Python (stdlib):
  - `game_generator.py` — genera los juegos RPG "El Refugio Lógico".
  - `gl_generator.py` — genera las guías de clase GL01/02/03.
- `public/` — JSONs fuente:
  - `clases_guia/` — guías de clase.
  - `resultados_guia/` — guías resueltas.
  - `juegos/` — canon narrativo, kit visual y JSONs de los juegos.
- `docs/` — estándares de authoring (juegos y guías).

## Uso rápido

```sh
# Generar la guía de clase (GL01/02/03)
python tools/gl_generator.py public/clases_guia/guia_contenido_gl01.json

# Generar el juego Capítulo 1 oficial
python tools/game_generator.py public/juegos/juego_gl01_oficial.json \
  -o inf-220-g2/clases/Juego_Capitulo_1.html

# Esqueleto de juego nuevo
python tools/game_generator.py --nuevo
```

> **Nota:** `inf-220-g2/` (las clases generadas del curso) y `resueltos/`
> (ejercicios resueltos) son repos/carpetas aparte y no se versionan aquí.

## Canon: El Refugio Lógico

Toda la materia comparte una única historia: el viajero deja la "Ciudad de la
Interfaz" y se adentra en "El Gran Backend" con su compañera Teffy, dominando
la lógica con sus propias manos. Definición completa en
`public/juegos/story_arc.json`.
