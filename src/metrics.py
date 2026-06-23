"""Agrega o resultado do comparador: acurácia por campo, geral (micro) e por documento."""


def _taxa(acertos: int, total: int) -> float | None:
    return round(acertos / total, 4) if total else None


def acuracia_por_campo(por_doc: list[dict], campos: list[str]) -> dict:
    acertos = {c: 0 for c in campos}
    totais = {c: 0 for c in campos}
    for registro in por_doc:
        for campo, info in registro["campos"].items():
            totais[campo] += 1
            acertos[campo] += int(bool(info["ok"]))

    resultado = {c: _taxa(acertos[c], totais[c]) for c in campos}
    resultado["_geral"] = _taxa(sum(acertos.values()), sum(totais.values()))
    resultado["_n_por_campo"] = totais
    return resultado


def acuracia_por_documento(por_doc: list[dict]) -> float | None:
    total = exatos = 0
    for registro in por_doc:
        campos = registro["campos"]
        if not campos:
            continue
        total += 1
        if all(info["ok"] for info in campos.values()):
            exatos += 1
    return _taxa(exatos, total)


def consolidar(comparacao: dict, rotulo: str | None = None) -> dict:
    campos = comparacao["campos"]
    por_doc = comparacao["por_doc"]
    return {
        "rotulo":                 rotulo,
        "n_docs_pontuados":       comparacao["n_docs_pontuados"],
        "acuracia_por_campo":     acuracia_por_campo(por_doc, campos),
        "acuracia_por_documento": acuracia_por_documento(por_doc),
        "n_divergencias":         len(comparacao["divergencias"]),
        "n_docs_so_no_gabarito":  len(comparacao["docs_so_no_gabarito"]),
        "n_docs_so_na_predicao":  len(comparacao["docs_so_na_predicao"]),
    }
