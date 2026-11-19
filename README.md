# transofing

Script que descarga las transcripciones de todas las clases de un curso de
[OpenFing](https://open.fing.edu.uy) y las convierte a texto plano legible con
timestamps.

## Requisitos

- Python 3.10 o superior.
- No requiere dependencias externas: solo usa la biblioteca estándar.

## Uso

```bash
./transofing.py <url del curso>
# o bien
python3 transofing.py <url del curso>
```

El script acepta exactamente **un argumento**: la URL del curso. Sirven tanto la
URL base como la URL de una clase en particular (se ignora el número de clase):

```bash
python3 transofing.py https://open.fing.edu.uy/courses/ae/
python3 transofing.py https://open.fing.edu.uy/courses/tsig-2026/
python3 transofing.py https://open.fing.edu.uy/courses/ae/3/
```

De la URL se extrae el identificador del curso (`/courses/<curso>/`). Si la URL
no tiene ese formato, el script termina con un error.

## Salida

Los archivos se guardan en `./transcripciones/<curso>/`, relativo al directorio
desde el que se ejecuta el script (el directorio se crea si no existe):

```
transcripciones/
└── ae/
    ├── clase-01-introduccion.txt
    ├── clase-02-...
    └── clase-NN-<titulo>.txt
```

Cada archivo comienza con un encabezado (título de la clase, URL de origen, URL
del curso y nota de licencia) y luego los párrafos precedidos por su timestamp:

```text
Transcripción - Clase 1: Introducción
Fuente: https://open.fing.edu.uy/courses/ae/1/
Curso: https://open.fing.edu.uy/courses/ae/
Licencia: Creative Commons (OpenFing)

[00:00:12] Contenido de la clase...
[00:00:35] ...
```

Detalles del nombre de archivo: el número de clase va con dos dígitos
(`clase-01`) y el título se normaliza (sin acentos, solo letras/números/guiones,
máximo 60 caracteres). Si la clase no tiene título, el archivo queda como
`clase-NN.txt`.

## Comportamiento en consola

El script informa el curso y el directorio de destino, la cantidad de clases
encontradas y el resultado de cada clase:

| Estado  | Significado                                                        |
|---------|--------------------------------------------------------------------|
| `[OK]`   | Transcripción descargada y guardada correctamente.                |
| `[SKIP]` | La clase no tiene transcripción (404) o el archivo no es VTT.      |
| `[WARN]` | Fallo de red o error HTTP al procesar la clase.                   |

Al finalizar muestra un resumen, por ejemplo `Listo: 24/24 transcripciones
descargadas.` Un error HTTP 404 en una clase no interrumpe el resto de las
descargas.

## Notas

- El sitio base (`BASE`) está definido como constante en `transofing.py`; el
  script no tiene flags, variables de entorno ni archivos de configuración.
- Las transcripciones descargadas son contenido de OpenFing publicado bajo
  licencia Creative Commons.
