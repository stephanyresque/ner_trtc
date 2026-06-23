"""Carga do gabarito (saida_json) e das colunas do CSV em registros por basename."""

import csv
import json
from pathlib import Path

from src import config


def _gabarito_valido(dados) -> bool:
    if not isinstance(dados, dict):
        return False
    return any(str(dados.get(c, "")).strip() for c in config.CAMPOS)


def carregar_gabarito_json(json_dir: Path = config.BASELINE_JSON_DIR) -> tuple[dict, list]:
    """(validos, invalidos): JSONs vazios/1 byte/sem campos contam como sem gabarito."""
    validos: dict[str, dict] = {}
    invalidos: list[str] = []

    for path in sorted(Path(json_dir).glob("*.json")):
        basename = path.stem
        try:
            texto = path.read_text(encoding="utf-8").strip()
            dados = json.loads(texto) if texto else None
        except (json.JSONDecodeError, OSError):
            dados = None

        if not _gabarito_valido(dados):
            invalidos.append(basename)
            continue
        validos[basename] = {c: dados.get(c, "") for c in config.CAMPOS}

    return validos, invalidos


def carregar_csv(csv_path: Path = config.BASELINE_CSV) -> tuple[dict, dict]:
    """(referencia, gemini) por basename; ignora colunas de token e caminho."""
    referencia: dict[str, dict] = {}
    gemini: dict[str, dict] = {}

    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        for linha in csv.DictReader(f, delimiter="\t"):
            caminho = (linha.get("caminho_trct") or "").strip()
            if not caminho:
                continue
            basename = Path(caminho).stem
            referencia[basename] = {c: (linha.get(c) or "") for c in config.CAMPOS}
            gemini[basename] = {c: (linha.get(f"{c}_gemini") or "") for c in config.CAMPOS_CSV_GEMINI}

    return referencia, gemini
