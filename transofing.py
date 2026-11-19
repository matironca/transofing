#!/usr/bin/env python3
"""Descarga y convierte a texto las transcripciones de un curso de OpenFing."""

import re
import sys
import unicodedata
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE = "https://open.fing.edu.uy"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) transcripcion-descargador/1.0"}


def fetch(url: str) -> bytes:
    """Descarga una URL y devuelve el cuerpo como bytes. Lanza si falla."""
    req = Request(url, headers=HEADERS)
    with urlopen(req, timeout=60) as resp:
        return resp.read()


def fetch_text(url: str) -> str:
    return fetch(url).decode("utf-8", errors="replace")


def parse_course_url(arg: str) -> str:
    """Normaliza la URL al formato base del curso: .../courses/<slug>/"""
    m = re.search(r"/courses/([^/]+)/?", arg)
    if not m:
        sys.exit(
            f"ERROR: no pude extraer el curso de '{arg}'.\n"
            "Ejemplo esperado: https://open.fing.edu.uy/courses/ae/"
        )
    return f"{BASE}/courses/{m.group(1)}/"


def listar_clases(course_url: str) -> list[dict]:
    """Devuelve [{'numero': n, 'titulo': t}] a partir de la página del curso."""
    html = fetch_text(course_url)
    clases = {}
    # Enlaces de clases en el índice: .../courses/<slug>/N/ seguido del título
    patron = re.compile(
        r'href=https?://open\.fing\.edu\.uy/courses/[^/]+/(\d+)/'
        r'[^>]*>.*?clase-titulo>(.*?)</div>',
        re.DOTALL,
    )
    for numero, titulo in patron.findall(html):
        n = int(numero)
        if n not in clases:
            clases[n] = {"numero": n, "titulo": re.sub(r"<[^>]+>", "", titulo).strip()}
    return [clases[n] for n in sorted(clases)]


def url_transcripcion(class_url: str, numero: int) -> str | None:
    """Obtiene la URL del VTT de transcripción de una clase.

    Primero busca data-transcripcion-src en la página de la clase; si no está,
    prueba el patrón de URL de medios del sitio.
    """
    html = fetch_text(class_url)
    m = re.search(r'data-transcripcion-src=(/[^ >]+?)(?=[ >])', html)
    if m:
        return BASE + m.group(1)
    # Fallback: /media/<slug>/<slug>_<NN>_transcription.vtt
    slug = class_url.rstrip("/").split("/")[-1]
    return f"{BASE}/media/{slug}/{slug}_{numero:02d}_transcription.vtt"


def vtt_a_texto(vtt: str) -> str:
    """Convierte WebVTT a texto plano: párrafos precedidos por [HH:MM:SS]."""
    ts_re = re.compile(r"(\d{2}:\d{2}:\d{2})\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}")
    segmentos: list[str] = []
    for line in vtt.splitlines():
        line = line.strip()
        m = ts_re.match(line)
        if m:
            segmentos.append(f"\n[{m.group(1)}] ")
        elif line and line != "WEBVTT" and not line.startswith(("NOTE", "Kind:", "Language:", "STYLE", "REGION")):
            if segmentos:
                segmentos[-1] = segmentos[-1].rstrip() + " " + line
            else:
                segmentos.append(line + " ")
    texto = "".join(segmentos)
    texto = re.sub(r"\n{3,}", "\n\n", texto).strip()
    return texto


def sanitizar(nombre: str, max_len: int = 60) -> str:
    nombre = unicodedata.normalize("NFKD", nombre)
    nombre = "".join(c for c in nombre if not unicodedata.combining(c))
    nombre = re.sub(r"[^\w\s.-]", "", nombre).strip()
    nombre = re.sub(r"\s+", "-", nombre)
    return nombre[:max_len].strip("-.") or "clase"


def descargar_clase(clase: dict, curso_slug: str, destino: Path) -> bool:
    numero, titulo = clase["numero"], clase["titulo"]
    class_url = f"{BASE}/courses/{curso_slug}/{numero}/"
    try:
        vtt_url = url_transcripcion(class_url, numero)
    except (HTTPError, URLError) as e:
        print(f"  [WARN] No pude abrir la página de la clase {numero}: {e}")
        return False

    try:
        vtt = fetch_text(vtt_url)
    except HTTPError as e:
        if e.code == 404:
            print(f"  [SKIP] Clase {numero} ({titulo or 'sin título'}): no tiene transcripción.")
        else:
            print(f"  [WARN] Clase {numero}: error {e.code} al descargar la transcripción.")
        return False
    except (URLError, TimeoutError) as e:
        print(f"  [WARN] Clase {numero}: fallo de red ({e})")
        return False

    if not vtt.strip() or not vtt.strip().startswith("WEBVTT"):
        print(f"  [SKIP] Clase {numero}: el archivo descargado no parece una transcripción VTT.")
        return False

    sufijo = f"-{sanitizar(titulo)}" if titulo else ""
    archivo = destino / f"clase-{numero:02d}{sufijo}.txt"
    encabezado = (
        f"Transcripción - Clase {numero}: {titulo or '(sin título)'}\n"
        f"Fuente: {class_url}\n"
        f"Curso: https://open.fing.edu.uy/courses/{curso_slug}/\n"
        f"Licencia: Creative Commons (OpenFing)\n\n"
    )
    archivo.write_text(encabezado + vtt_a_texto(vtt) + "\n", encoding="utf-8")
    print(f"  [OK]   Clase {numero} ({titulo or 'sin título'}) -> {archivo.name}")
    return True


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("ERROR: falta la URL del curso. Consultá el README para el uso.")

    course_url = parse_course_url(sys.argv[1])
    curso_slug = course_url.rstrip("/").split("/")[-1]
    destino = Path("transcripciones") / curso_slug
    destino.mkdir(parents=True, exist_ok=True)
    print(f"Curso: {course_url}")
    print(f"Guardando en: {destino.resolve()}/\n")

    try:
        clases = listar_clases(course_url)
    except (HTTPError, URLError) as e:
        sys.exit(f"ERROR: no pude leer la página del curso: {e}")
    if not clases:
        sys.exit("ERROR: no encontré clases en la página del curso.")

    print(f"Clases encontradas: {len(clases)}\n")
    ok = sum(descargar_clase(c, curso_slug, destino) for c in clases)
    print(f"\nListo: {ok}/{len(clases)} transcripciones descargadas.")


if __name__ == "__main__":
    main()
