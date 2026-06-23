"""Triagem dos PDFs em texto_real / carimbo / scan pela presença de âncoras do TRCT."""

import re
import unicodedata

from src import config


def _normalizar_para_busca(texto: str) -> str:
    sem_acento = "".join(
        ch for ch in unicodedata.normalize("NFD", texto) if unicodedata.category(ch) != "Mn"
    )
    return re.sub(r"\s+", " ", sem_acento.upper())


_ANCORAS = [re.compile(p) for p in config.ANCORAS_TRCT]
_BOILERPLATE = [re.compile(p) for p in config.BOILERPLATE_PJE]


def _casar(padroes: list[re.Pattern], texto_norm: str) -> list[str]:
    return [p.pattern for p in padroes if p.search(texto_norm)]


def classificar(texto: str) -> dict:
    """Classifica um documento e devolve a classe + os sinais que a justificam."""
    texto = texto or ""
    texto_norm = _normalizar_para_busca(texto)

    ancoras = _casar(_ANCORAS, texto_norm)
    boilerplate = _casar(_BOILERPLATE, texto_norm)

    if len(texto.strip()) < config.LIMIAR_SCAN_CHARS:
        classe = "scan"
    elif len(ancoras) >= config.MIN_ANCORAS_TRCT:
        classe = "texto_real"
    else:
        classe = "carimbo"

    return {
        "classe": classe,
        "n_chars": len(texto.strip()),
        "ancoras_trct": ancoras,
        "boilerplate_pje": boilerplate,
    }
