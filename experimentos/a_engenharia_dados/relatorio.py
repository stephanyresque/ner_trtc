"""Renderiza relatorios/a/relatorio_A.md a partir do comparacao_A.json (de run_compare).

Rode a partir de ner_trct/ (depois de run_compare):  python -m experimentos.a_engenharia_dados.relatorio
"""

import json

from src import config

SAIDAS = config.ROOT / "experimentos" / "a_engenharia_dados" / "saidas"
REL_A = config.RELATORIOS_DIR / "a"
COMPARACAO = REL_A / "comparacao_A.json"


def _fmt(v) -> str:
    return "—" if v is None else (f"{v:.4f}" if isinstance(v, float) else str(v))


def main() -> None:
    if not COMPARACAO.exists():
        raise SystemExit(f"{COMPARACAO} não existe. Rode antes: python -m pipeline.run_compare "
                         "--fonte json --pred experimentos/a_engenharia_dados/saidas/predicoes_A.json "
                         "--out relatorios/a/comparacao_A.json")

    comp = json.loads(COMPARACAO.read_text(encoding="utf-8"))
    resumo = comp["resumo"]
    apc = resumo["acuracia_por_campo"]
    resumo_ext = SAIDAS / "_resumo_extracao.json"
    ext = json.loads(resumo_ext.read_text(encoding="utf-8")) if resumo_ext.exists() else {}
    ds = json.loads(config.DATASET_JSON.read_text(encoding="utf-8"))
    sem_gab = [d["arquivo"] for d in ds.get("sem_gabarito", [])]

    L = ["# Experimento A — extração determinística de TRCT (sem LLM)\n",
         "**Método:** parser determinístico sobre as coordenadas do PDF (PyMuPDF, modo *words*). "
         "Nenhuma chamada de LLM em nenhuma etapa.\n",
         "- **Custo:** R$ 0,00 / US$ 0,00 (sem LLM)",
         f"- **Docs rodados (texto_real):** {ext.get('n_docs_rodados', '—')}",
         f"- **Docs pontuados (com gabarito):** {resumo['n_docs_pontuados']}",
         f"- **Sem gabarito (saída gerada, fora do score):** {len(sem_gab)} — "
         + (", ".join(sem_gab) if sem_gab else "nenhum"),
         f"- **Docs com erro de execução:** {ext.get('n_docs_com_erro', 0)}\n",
         "## Acurácia (concordância com o gabarito aproximado)\n",
         "| Campo | Acurácia | n |", "|---|---|---|"]
    for campo in config.CAMPOS:
        L.append(f"| {campo} | {_fmt(apc[campo])} | {apc['_n_por_campo'][campo]} |")
    L.append(f"| **Geral (micro)** | **{_fmt(apc['_geral'])}** | — |")
    L.append(f"| Por documento (todos os campos certos) | {_fmt(resumo['acuracia_por_documento'])} | — |\n")

    L.append(f"## Divergências ({len(comp['divergencias'])}) — para conferência manual\n")
    L.append("> O gabarito é a extração antiga do Gemini (referência **aproximada**). Divergência ≠ erro "
             "do parser: muitas vêm de OCR da própria fonte (palavras coladas, erro de 1 caractere, "
             "formulário degradado) ou de artefato do gabarito.\n")
    L.append("| Doc | Campo | Valor A | Valor gabarito |")
    L.append("|---|---|---|---|")
    for d in comp["divergencias"]:
        L.append(f"| {d['arquivo']} | {d['campo']} | `{d['valor_predito']}` | `{d['valor_gabarito']}` |")
    L.append("")

    REL_A.mkdir(parents=True, exist_ok=True)
    (REL_A / "relatorio_A.md").write_text("\n".join(L), encoding="utf-8")

    print(f"Acurácia geral: {_fmt(apc['_geral'])} | docs pontuados: {resumo['n_docs_pontuados']} "
          f"| divergências: {len(comp['divergencias'])} | custo: R$ 0,00")
    print(f"Relatório: {(REL_A / 'relatorio_A.md').relative_to(config.ROOT)}")


if __name__ == "__main__":
    main()
