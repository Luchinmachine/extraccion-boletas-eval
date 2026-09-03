"""PDF -> texto plano. Sin OCR: los PDFs sinteticos tienen capa de texto."""
from __future__ import annotations
from pathlib import Path
import pymupdf


def texto_de_pdf(ruta: Path) -> str:
    with pymupdf.open(ruta) as doc:
        return "\n".join(p.get_text() for p in doc)


def cargar_corpus(carpeta: Path) -> dict[str, str]:
    return {p.name: texto_de_pdf(p) for p in sorted(carpeta.glob("*.pdf"))}
