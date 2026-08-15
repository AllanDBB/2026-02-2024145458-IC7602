#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "markdown>=3.6",
#     "pygments>=2.17",
#     "weasyprint>=62",
# ]
# ///
"""
md2pdf.py - Compila un documento Markdown al PDF con el formato del curso IC-7602.

Uso:
    ./scripts/md2pdf.py apuntes/2026-08-17-IC7602-2024145458-A1.md
    ./scripts/md2pdf.py entrada.md -o salida.pdf --fecha 2026-08-17

Requisitos:
    Solo `uv`. El shebang `uv run --script` resuelve las dependencias declaradas
    arriba en un entorno aislado; no hace falta instalar nada a mano.

Pasos que ejecuta el script (cada uno marcado en el codigo con "PASO n"):
    1. Leer y validar los argumentos de linea de comandos.
    2. Resolver los metadatos del documento (encabezado, fecha, ruta de salida).
    3. Convertir el Markdown a HTML con las extensiones necesarias.
    4. Armar el documento HTML completo (plantilla + estilos + @page dinamico).
    5. Renderizar el PDF con WeasyPrint.
    6. Verificar el nombre del archivo contra la convencion del curso.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

import markdown
from pygments.formatters import HtmlFormatter
from weasyprint import CSS, HTML

# Ruta de la hoja de estilos que define el formato visual del curso.
HOJA_DE_ESTILOS = Path(__file__).resolve().parent / "estilo-apuntes.css"

# Extensiones de python-markdown que habilitan tablas, bloques de codigo con
# resaltado, notas al pie, listas de tareas y atributos HTML dentro del Markdown.
EXTENSIONES_MARKDOWN = [
    "extra",         # tables, fenced_code, footnotes, attr_list, def_list, abbr
    "codehilite",    # syntax highlighting (needs pygments)
    "sane_lists",
    "admonition",
    "toc",
    "md_in_html",
]

CONFIGURACION_MARKDOWN = {
    "codehilite": {"guess_lang": False, "linenums": False},
    "toc": {"permalink": False},
}

# Nombre exigido por el programa del curso, por ejemplo:
#   2026-08-17-IC7602-200420157-A1.pdf
# Las letras corresponden a Apuntes, Examen, Proyecto, Tarea corta y Lectura.
CONVENCION_DE_NOMBRE = re.compile(r"^\d{4}-\d{2}-\d{2}-IC7602-\d+-[AEPTL]\d*\.pdf$")

# Una fecha al inicio del nombre del archivo manda sobre la fecha de hoy.
FECHA_EN_NOMBRE = re.compile(r"^(\d{4}-\d{2}-\d{2})")

PLANTILLA_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>{titulo}</title>
<style>{estilos_pagina}</style>
<style>{estilos_codigo}</style>
</head>
<body>
{contenido}
</body>
</html>
"""


def fallar(mensaje: str) -> None:
    """Print an error on stderr and abort with a non-zero exit code."""
    print(f"error: {mensaje}", file=sys.stderr)
    raise SystemExit(1)


def escapar_css(texto: str) -> str:
    """Escape a string so it can be embedded in a CSS `content: "..."` value."""
    return texto.replace("\\", "\\\\").replace('"', '\\"')


def construir_estilos_pagina(encabezado: str, fecha: str) -> str:
    """
    Generate the @page rule that carries the two dynamic values of the format:
    the source file name (top-left) and the document date (top-right).
    The static rules live in estilo-apuntes.css.
    """
    return (
        "@page {\n"
        f'    @top-left {{ content: "{escapar_css(encabezado)}"; }}\n'
        f'    @top-right {{ content: "{escapar_css(fecha)}"; }}\n'
        '    @bottom-center { content: counter(page) "/" counter(pages); }\n'
        "}\n"
    )


def resolver_fecha(entrada: Path, fecha_indicada: str | None) -> str:
    """
    Resolve the header date, in order of precedence:
    explicit --fecha > date prefix of the file name > today.
    """
    if fecha_indicada:
        try:
            dt.date.fromisoformat(fecha_indicada)
        except ValueError:
            fallar(f"invalid --fecha value '{fecha_indicada}', expected YYYY-MM-DD")
        return fecha_indicada

    coincidencia = FECHA_EN_NOMBRE.match(entrada.stem)
    if coincidencia:
        return coincidencia.group(1)

    return dt.date.today().isoformat()


def analizar_argumentos() -> argparse.Namespace:
    analizador = argparse.ArgumentParser(
        description="Compila un archivo Markdown a PDF con el formato del curso IC-7602.",
    )
    analizador.add_argument("entrada", type=Path, help="archivo .md de entrada")
    analizador.add_argument(
        "-o", "--salida", type=Path, default=None,
        help="ruta del PDF de salida (por defecto: mismo nombre con extension .pdf)",
    )
    analizador.add_argument(
        "--fecha", default=None,
        help="fecha del encabezado en formato YYYY-MM-DD (por defecto: la del nombre del archivo, o la de hoy)",
    )
    analizador.add_argument(
        "--encabezado", default=None,
        help="texto del encabezado izquierdo (por defecto: el nombre del archivo .md)",
    )
    return analizador.parse_args()


def main() -> None:
    # --- PASO 1: leer y validar los argumentos -----------------------------
    argumentos = analizar_argumentos()
    entrada: Path = argumentos.entrada

    if not entrada.is_file():
        fallar(f"input file not found: {entrada}")
    if entrada.suffix.lower() != ".md":
        fallar(f"input file must have a .md extension, got: {entrada.suffix or 'none'}")
    if not HOJA_DE_ESTILOS.is_file():
        fallar(f"stylesheet not found next to the script: {HOJA_DE_ESTILOS}")

    # --- PASO 2: resolver metadatos del documento --------------------------
    salida: Path = argumentos.salida or entrada.with_suffix(".pdf")
    encabezado: str = argumentos.encabezado or entrada.name
    fecha: str = resolver_fecha(entrada, argumentos.fecha)

    if salida.resolve() == entrada.resolve():
        fallar("output path would overwrite the Markdown source")
    salida.parent.mkdir(parents=True, exist_ok=True)

    # --- PASO 3: convertir Markdown a HTML ---------------------------------
    try:
        texto = entrada.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        fallar(f"input file is not valid UTF-8: {entrada}")

    contenido = markdown.markdown(
        texto,
        extensions=EXTENSIONES_MARKDOWN,
        extension_configs=CONFIGURACION_MARKDOWN,
    )

    # --- PASO 4: armar el HTML completo ------------------------------------
    # El resaltado de sintaxis se genera aqui para que la hoja de estilos del
    # curso solo contenga el formato y no las clases de pygments.
    estilos_codigo = HtmlFormatter(style="friendly").get_style_defs(".codehilite")
    documento = PLANTILLA_HTML.format(
        titulo=entrada.stem,
        estilos_pagina=construir_estilos_pagina(encabezado, fecha),
        estilos_codigo=estilos_codigo,
        contenido=contenido,
    )

    # --- PASO 5: renderizar el PDF -----------------------------------------
    # base_url apunta al directorio del .md para que las imagenes y los enlaces
    # relativos (diagramas, capturas) se resuelvan correctamente.
    try:
        HTML(string=documento, base_url=str(entrada.resolve().parent)).write_pdf(
            target=str(salida),
            stylesheets=[CSS(filename=str(HOJA_DE_ESTILOS))],
        )
    except OSError as excepcion:
        fallar(f"could not write the PDF: {excepcion}")

    print(f"PDF generado: {salida}")

    # --- PASO 6: verificar la convencion de nombres del curso --------------
    # Es solo una advertencia: el script tambien sirve para documentos que no
    # son entregas (borradores, apuntes personales, README, etc.).
    if not CONVENCION_DE_NOMBRE.match(salida.name):
        print(
            f"advertencia: '{salida.name}' no sigue el formato del curso "
            "YYYY-MM-DD-IC7602-[carne]-A{numero}.pdf",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
