# scripts

## md2pdf.py

Compila un documento Markdown al PDF con el formato usado en el curso: página A4,
encabezado con el nombre del archivo `.md` a la izquierda y la fecha a la derecha,
y pie de página centrado con `página/total`.

### Requisitos

Únicamente [`uv`](https://docs.astral.sh/uv/). El script declara sus dependencias
(`markdown`, `pygments`, `weasyprint`) con metadata PEP 723, así que `uv` las
resuelve en un entorno aislado la primera vez que se ejecuta. No hay que instalar
nada de forma global.

### Uso

```sh
./scripts/md2pdf.py apuntes/2026-08-17-IC7602-2024145458-A1.md
```

Genera `apuntes/2026-08-17-IC7602-2024145458-A1.pdf`.

Opciones:

| Opción | Efecto |
|---|---|
| `-o`, `--salida` | Ruta del PDF de salida (por defecto, el mismo nombre con extensión `.pdf`). |
| `--fecha` | Fecha del encabezado en `YYYY-MM-DD`. Por defecto usa la del nombre del archivo y, si no la tiene, la de hoy. |
| `--encabezado` | Texto del encabezado izquierdo (por defecto, el nombre del archivo `.md`). |

El script advierte —sin fallar— cuando el nombre del PDF no sigue la convención de
entrega `YYYY-MM-DD-IC7602-[carné]-A{número}.pdf`, para no compilar por error un
archivo con nombre inválido.

### Formato y estilos

Las reglas visuales están en `estilo-apuntes.css`, junto al script; ahí se ajustan
márgenes, tipografías, tablas y bloques de código sin tocar la lógica de `md2pdf.py`.

### Notas al escribir el Markdown

- Las listas anidadas necesitan **4 espacios** de indentación.
- Las rutas de imágenes se resuelven relativas al `.md`, así que los diagramas se
  pueden guardar en una carpeta junto al documento.
- `<div class="salto-pagina"></div>` fuerza un salto de página.
