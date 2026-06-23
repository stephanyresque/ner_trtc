"""Extração da camada de texto dos PDFs via PyMuPDF — usada só pela triagem (sem LLM)."""

from pathlib import Path

import fitz  # PyMuPDF


def extrair_texto(pdf_path: str | Path) -> str:
    """Concatena o texto de todas as páginas. '' se o PDF for imagem pura."""
    with fitz.open(pdf_path) as doc:
        partes = [page.get_text("text") for page in doc]
    return "\n".join(partes).strip()


def salvar_texto(basename: str, texto: str, texto_dir: Path) -> Path:
    texto_dir.mkdir(parents=True, exist_ok=True)
    destino = texto_dir / f"{basename}.txt"
    destino.write_text(texto, encoding="utf-8")
    return destino


def listar_pdfs(amostras_dir: Path) -> list[Path]:
    return sorted(amostras_dir.glob("*.pdf"))
