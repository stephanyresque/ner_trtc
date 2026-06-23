"""Relatório do Experimento B: acurácia geral + quebra por classe + A vs B nos texto_real.

Lê relatorios/b/comparacao_B_<MODELO>.json (de run_compare) e a triagem.
Rode a partir de ner_trct/:  MODELO=qwen3-vl-4b python -m experimentos.b_modelos.relatorio
"""

import json
import os
from pathlib import Path

from src import config

MODELO = os.getenv("MODELO", "qwen3-vl-4b")
REL_B = config.RELATORIOS_DIR / "b"
COMPARACAO = REL_B / f"comparacao_B_{MODELO}.json"
SAIDAS = config.ROOT / "experimentos" / "b_modelos" / "saidas"
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
                         f"--pred experimentos/b_modelos/saidas/predicoes_B_{MODELO}.json "
                         f"--out relatorios/b/comparacao_B_{MODELO}.json")

    comp = json.loads(COMPARACAO.read_text(encoding="utf-8"))
    campos, por_doc = comp["campos"], comp["por_doc"]
    classe_de = {d["arquivo"]: d["classe"] for d in json.loads(config.TRIAGEM_JSON.read_text(encoding="utf-8"))}
    ext_path = SAIDAS / f"_resumo_extracao_{MODELO}.json"
    ext = json.loads(ext_path.read_text(encoding="utf-8")) if ext_path.exists() else {}

    taxas, geral, _ = _por_campo(por_doc, campos)
    por_classe = {c: [r for r in por_doc if classe_de.get(r["arquivo"]) == c] for c in CLASSES}

    # A vs B nos texto_real
    b_txt, b_txt_geral, _ = _por_campo(por_classe["texto_real"], campos)
    a_path = config.RELATORIOS_DIR / "a" / "comparacao_A.json"
    a_txt, a_txt_geral = ({}, None)
    if a_path.exists():
        a = json.loads(a_path.read_text(encoding="utf-8"))
        a_doc = [r for r in a["por_doc"] if classe_de.get(r["arquivo"]) == "texto_real"]
        a_txt, a_txt_geral, _ = _por_campo(a_doc, a["campos"])

    tok = ext.get("tokens", {})
    lat = ext.get("latencia_s", {})
    L = [f"# Experimento B — VLM local lendo a imagem do TRCT (`{MODELO}`)\n",
         "> **Gabarito = extração antiga do Gemini (aproximada), não anotação humana.** Nos `scan` o "
         "Gemini também leu a imagem; divergência ≠ erro — confira uma amostra no olho.\n",
         "**Método:** lê a imagem do PDF com um VLM aberto servido localmente via vLLM. "
         "**Custo de API: R$ 0,00** (modelo local).\n",
         f"- **Modelo:** {MODELO}  ·  **custo_api:** R$ 0,00",
         f"- **Docs rodados:** {ext.get('n_docs_rodados', '—')}  ·  **com erro:** {ext.get('n_docs_com_erro', 0)}",
         f"- **Docs pontuados (com gabarito):** {comp['n_docs_pontuados']}",
         f"- **Tokens (prompt/compl/total):** {tok.get('prompt','—')}/{tok.get('completion','—')}/{tok.get('total','—')}",
         f"- **Latência:** total {lat.get('total','—')}s · média {lat.get('media','—')}s/doc\n",
         "## Acurácia geral (concordância com o gabarito)\n",
         "| Campo | Acurácia |", "|---|---|"]
    for c in campos:
        L.append(f"| {c} | {_fmt(taxas[c])} |")
    L.append(f"| **Geral (micro)** | **{_fmt(geral)}** |\n")

    L.append("## Quebra por classe\n")
    L.append("| Classe | Docs pontuados | Acurácia geral |")
    L.append("|---|---|---|")
    for c in CLASSES:
        _, g, n_inst = _por_campo(por_classe[c], campos)
        L.append(f"| {c} | {len(por_classe[c])} | {_fmt(g)} |")
    L.append("")

    L.append("## A (determinístico) vs B nos 14 texto_real\n")
    L.append("| Campo | A | B |")
    L.append("|---|---|---|")
    for c in campos:
        L.append(f"| {c} | {_fmt(a_txt.get(c))} | {_fmt(b_txt.get(c))} |")
    L.append(f"| **Geral** | **{_fmt(a_txt_geral)}** | **{_fmt(b_txt_geral)}** |\n")

    L.append(f"## Divergências ({len(comp['divergencias'])}) — para conferência manual\n")
    L.append("| Doc | Classe | Campo | Valor B | Valor gabarito |")
    L.append("|---|---|---|---|---|")
    for d in comp["divergencias"]:
        L.append(f"| {d['arquivo']} | {classe_de.get(d['arquivo'],'?')} | {d['campo']} | "
                 f"`{d['valor_predito']}` | `{d['valor_gabarito']}` |")
    L.append("")

    REL_B.mkdir(parents=True, exist_ok=True)
    (REL_B / f"relatorio_B_{MODELO}.md").write_text("\n".join(L), encoding="utf-8")

    print(f"Geral: {_fmt(geral)} | por classe: " +
          ", ".join(f"{c}={_fmt(_por_campo(por_classe[c], campos)[1])}(n={len(por_classe[c])})" for c in CLASSES))
    print(f"A vs B (texto_real): A={_fmt(a_txt_geral)} | B={_fmt(b_txt_geral)}")
    print(f"Relatório: {(REL_B / f'relatorio_B_{MODELO}.md').relative_to(config.ROOT)}")


if __name__ == "__main__":
    main()
