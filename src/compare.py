"""Comparador genérico: pontua predição vs gabarito campo a campo (basename -> {campo: valor})."""

from src import config
from src.normalize import normalizar_campo


def comparar_doc(arquivo: str, pred: dict, gab: dict, campos: list[str]) -> dict:
    resultado_campos: dict[str, dict] = {}
    for campo in campos:
        gab_norm = normalizar_campo(campo, gab.get(campo, ""))
        if gab_norm is None or gab_norm == "":
            continue  # campo sem valor no gabarito fica fora do denominador
        pred_norm = normalizar_campo(campo, pred.get(campo, ""))
        resultado_campos[campo] = {
            "ok":        pred_norm == gab_norm,
            "pred":      pred.get(campo, ""),
            "gab":       gab.get(campo, ""),
            "pred_norm": pred_norm,
            "gab_norm":  gab_norm,
        }
    return {"arquivo": arquivo, "campos": resultado_campos}


def comparar(preds: dict, gabs: dict, campos: list[str] | None = None) -> dict:
    """Pontua só os documentos presentes nos dois lados; lista divergências e os de fora."""
    campos = campos or config.CAMPOS
    arquivos_comuns = sorted(set(preds) & set(gabs))
    por_doc: list[dict] = []
    divergencias: list[dict] = []

    for arquivo in arquivos_comuns:
        registro = comparar_doc(arquivo, preds[arquivo], gabs[arquivo], campos)
        por_doc.append(registro)
        for campo, info in registro["campos"].items():
            if not info["ok"]:
                divergencias.append({
                    "arquivo":        arquivo,
                    "campo":          campo,
                    "valor_predito":  info["pred"],
                    "valor_gabarito": info["gab"],
                })

    return {
        "campos":              campos,
        "por_doc":             por_doc,
        "divergencias":        divergencias,
        "n_docs_pontuados":    len(arquivos_comuns),
        "docs_so_no_gabarito": sorted(set(gabs) - set(preds)),
        "docs_so_na_predicao": sorted(set(preds) - set(gabs)),
    }
