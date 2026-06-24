"""Relatório da Experiência C: acurácia (geral/campo/classe) + custo/tempo/tokens reais + A vs C.

Lê relatorios/c/comparacao_C_<slug>.json (de run_compare) e o _resumo_extracao da extração.
Rode a partir de ner_trct/:  MODELO=openai/gpt-5-mini python -m experimentos.c_modelos_pagos.relatorio
"""

import json
import os

from src import config

MODELO = os.getenv("MODELO", "openai/gpt-5-mini")
SLUG = MODELO.rsplit("/", 1)[-1]
REL_C = config.RELATORIOS_DIR / "c"
COMPARACAO = REL_C / f"comparacao_C_{SLUG}.json"
SAIDAS = config.ROOT / "experimentos" / "c_modelos_pagos" / "saidas"
CLASSES = ("texto_real", "carimbo", "scan")


def _fmt(v) -> str:
    return "—" if v is None else (f"{v:.4f}" if isinstance(v, float) else str(v))


def _por_campo(por_doc, campos):
    ac = {c: 0 for c in campos}
    tot = {c: 0 for c in campos}
    for r in por_doc:
        for campo, info in r["campos"].items():
            tot[campo] += 1
            ac[campo] += int(bool(info["ok"]))
    taxas = {c: (round(ac[c] / tot[c], 4) if tot[c] else None) for c in campos}
    geral = round(sum(ac.values()) / sum(tot.values()), 4) if sum(tot.values()) else None
    return taxas, geral, sum(tot.values())


def main() -> None:
    if not COMPARACAO.exists():
        raise SystemExit(f"{COMPARACAO} não existe. Rode antes: python -m pipeline.run_compare --fonte json "
                         f"--pred experimentos/c_modelos_pagos/saidas/predicoes_C_{SLUG}.json "
                         f"--out relatorios/c/comparacao_C_{SLUG}.json")

    comp = json.loads(COMPARACAO.read_text(encoding="utf-8"))
    campos, por_doc = comp["campos"], comp["por_doc"]
    classe_de = {d["arquivo"]: d["classe"] for d in json.loads(config.TRIAGEM_JSON.read_text(encoding="utf-8"))}
    ext_path = SAIDAS / f"_resumo_extracao_{SLUG}.json"
    ext = json.loads(ext_path.read_text(encoding="utf-8")) if ext_path.exists() else {}

    taxas, geral, _ = _por_campo(por_doc, campos)
    por_classe = {c: [r for r in por_doc if classe_de.get(r["arquivo"]) == c] for c in CLASSES}

    # A (determinístico) vs C (pago) nos texto_real
    c_txt, c_txt_geral, _ = _por_campo(por_classe["texto_real"], campos)
    a_path = config.RELATORIOS_DIR / "a" / "comparacao_A.json"
    a_txt, a_txt_geral = ({}, None)
    if a_path.exists():
        a = json.loads(a_path.read_text(encoding="utf-8"))
        a_doc = [r for r in a["por_doc"] if classe_de.get(r["arquivo"]) == "texto_real"]
        a_txt, a_txt_geral, _ = _por_campo(a_doc, a["campos"])

    tok = ext.get("tokens", {})
    lat = ext.get("latencia_s", {})
    custo = ext.get("custo_total_usd", 0.0)
    repassado = ext.get("custo_repassado_pelo_gateway", False)
    custo_txt = f"US$ {custo:.6f}" + ("" if repassado else " (NÃO repassado pelo gateway — subestimado)")
    val = ext.get("validacao", {})

    L = [f"# Experimento C — modelo pago via gateway LiteLLM (`{MODELO}`)\n",
         "> **Gabarito = extração antiga do Gemini (aproximada), não anotação humana.** "
         "Divergência ≠ erro — confira uma amostra no olho.\n",
         "**Método:** envia TODAS as páginas do PDF (PNG) ao gateway LiteLLM pago, com "
         "`response_format=ExtracaoTRCT` validado por Pydantic.\n",
         f"- **Modelo:** {MODELO}  ·  **custo total:** {custo_txt}",
         f"- **Docs rodados:** {ext.get('n_docs_rodados', '—')}  ·  **com erro:** {ext.get('n_docs_com_erro', 0)}",
         f"- **Docs pontuados (com gabarito):** {comp['n_docs_pontuados']}",
         f"- **Tokens (prompt/compl/total):** {tok.get('prompt','—')}/{tok.get('completion','—')}/{tok.get('total','—')}",
         f"- **Latência:** total {lat.get('total','—')}s · média {lat.get('media','—')}s/doc · "
         f"tempo do run {ext.get('tempo_total_run_s','—')}s",
         f"- **Validação:** pydantic {val.get('pydantic','—')} · fallback {val.get('fallback','—')} · "
         f"erro {val.get('erro','—')}\n",
         "## Acurácia geral (concordância com o gabarito)\n",
         "| Campo | Acurácia |", "|---|---|"]
    for c in campos:
        L.append(f"| {c} | {_fmt(taxas[c])} |")
    L.append(f"| **Geral (micro)** | **{_fmt(geral)}** |\n")

    L.append("## Quebra por classe\n")
    L.append("| Classe | Docs pontuados | Acurácia geral |")
    L.append("|---|---|---|")
    for c in CLASSES:
        _, g, _ = _por_campo(por_classe[c], campos)
        L.append(f"| {c} | {len(por_classe[c])} | {_fmt(g)} |")
    L.append("")

    L.append("## A (determinístico) vs C (pago) nos texto_real\n")
    L.append("| Campo | A | C |")
    L.append("|---|---|---|")
    for c in campos:
        L.append(f"| {c} | {_fmt(a_txt.get(c))} | {_fmt(c_txt.get(c))} |")
    L.append(f"| **Geral** | **{_fmt(a_txt_geral)}** | **{_fmt(c_txt_geral)}** |\n")

    L.append(f"## Divergências ({len(comp['divergencias'])}) — para conferência manual\n")
    L.append("| Doc | Classe | Campo | Valor C | Valor gabarito |")
    L.append("|---|---|---|---|---|")
    for d in comp["divergencias"]:
        L.append(f"| {d['arquivo']} | {classe_de.get(d['arquivo'],'?')} | {d['campo']} | "
                 f"`{d['valor_predito']}` | `{d['valor_gabarito']}` |")
    L.append("")

    REL_C.mkdir(parents=True, exist_ok=True)
    out_md = REL_C / f"relatorio_C_{SLUG}.md"
    out_md.write_text("\n".join(L), encoding="utf-8")

    print(f"Geral: {_fmt(geral)} | por classe: " +
          ", ".join(f"{c}={_fmt(_por_campo(por_classe[c], campos)[1])}(n={len(por_classe[c])})" for c in CLASSES))
    print(f"Custo total: {custo_txt} | tokens: {tok.get('total','—')} | tempo run: {ext.get('tempo_total_run_s','—')}s")
    print(f"Relatório: {out_md.relative_to(config.ROOT)}")


if __name__ == "__main__":
    main()
