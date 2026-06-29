"""Relatório consolidado do Experimento D (TEXTO, modelos locais) nos texto_real.

Confronta cada modelo D (lê TEXTO) com C (gpt-5-mini, IMAGEM), B (qwen imagem 1ª pág) e A
(determinístico, texto) — todos no recorte texto_real. Rode da raiz: python -m experimentos.d_texto_local.relatorio
"""

import json

from src import config

REL = config.RELATORIOS_DIR
REL_D = REL / "d"
SAIDAS = config.ROOT / "experimentos" / "d_texto_local" / "saidas"
CLASSE = "texto_real"

# Referências (modalidade explícita no rótulo) — incluídas só se o comparacao existir.
REFERENCIAS = [
    ("C:gpt-5-mini (IMAGEM, todas pág.)", REL / "c" / "comparacao_C_gpt-5-mini.json"),
    ("B:qwen3-vl-4b (IMAGEM, 1ª pág.)",   REL / "b" / "comparacao_B_qwen3-vl-4b.json"),
    ("A (determinístico, TEXTO)",          REL / "a" / "comparacao_A.json"),
]


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
    return taxas, geral, sum(ac.values()), sum(tot.values())


def _coluna(comp_path, classe_de, campos):
    """(taxas, geral, n_docs) no recorte texto_real de um comparacao.json."""
    comp = json.loads(comp_path.read_text(encoding="utf-8"))
    por_doc = [r for r in comp["por_doc"] if classe_de.get(r["arquivo"]) == CLASSE]
    taxas, geral, _, _ = _por_campo(por_doc, campos)
    return taxas, geral, len(por_doc)


def main() -> None:
    d_files = sorted(REL_D.glob("comparacao_D_*.json"))
    if not d_files:
        raise SystemExit(f"Nenhum comparacao_D_*.json em {REL_D}. Rode antes a extração + run_compare de cada modelo D.")

    campos = config.CAMPOS
    classe_de = {d["arquivo"]: d["classe"] for d in json.loads(config.TRIAGEM_JSON.read_text(encoding="utf-8"))}

    # Colunas: modelos D (texto) primeiro, depois referências existentes.
    colunas: list[tuple[str, dict, float | None, int]] = []
    resumos: list[tuple[str, dict]] = []
    for f in d_files:
        slug = f.stem[len("comparacao_D_"):]
        taxas, geral, n = _coluna(f, classe_de, campos)
        colunas.append((f"D:{slug} (TEXTO)", taxas, geral, n))
        ext_path = SAIDAS / f"_resumo_extracao_{slug}.json"
        resumos.append((slug, json.loads(ext_path.read_text(encoding="utf-8")) if ext_path.exists() else {}))
    for rotulo, path in REFERENCIAS:
        if path.exists():
            taxas, geral, n = _coluna(path, classe_de, campos)
            colunas.append((rotulo, taxas, geral, n))

    cabec = [rot for rot, _, _, _ in colunas]
    L = ["# Experimento D — extração por TEXTO em modelos locais (recorte texto_real)\n",
         "> ⚠️ **Modalidades diferentes:** **D** e **A** leem o **TEXTO** extraído do PDF; "
         "**B** e **C** leem a **IMAGEM** das páginas (B só a 1ª, C todas). Não é confronto de "
         "mesma entrada — é texto (local, grátis) vs. imagem (VLM/pago). Compare com isso em mente.\n",
         "> **Gabarito = extração antiga do Gemini (aproximada), não anotação humana.** "
         "Divergência ≠ erro — confira no olho.\n",
         "## Modelos D (resumo da extração)\n",
         "| Modelo D | Docs | Erros | Tokens (total) | Latência média | Validação (pyd/fb/err) | Custo |",
         "|---|---|---|---|---|---|---|"]
    for slug, ext in resumos:
        tok = ext.get("tokens", {})
        lat = ext.get("latencia_s", {})
        val = ext.get("validacao", {})
        L.append(f"| {slug} | {ext.get('n_docs_rodados','—')} | {ext.get('n_docs_com_erro','—')} | "
                 f"{tok.get('total','—')} | {lat.get('media','—')}s | "
                 f"{val.get('pydantic','—')}/{val.get('fallback','—')}/{val.get('erro','—')} | R$ 0,00 |")
    L.append("")

    L.append("## Acurácia por campo nos texto_real — D (texto) × C/B (imagem) × A (determinístico)\n")
    L.append("| Campo | " + " | ".join(cabec) + " |")
    L.append("|---|" + "|".join(["---"] * len(cabec)) + "|")
    for c in campos:
        L.append(f"| {c} | " + " | ".join(_fmt(taxas.get(c)) for _, taxas, _, _ in colunas) + " |")
    L.append(f"| **Geral (micro)** | " + " | ".join(f"**{_fmt(g)}**" for _, _, g, _ in colunas) + " |")
    L.append(f"| _docs pontuados_ | " + " | ".join(str(n) for _, _, _, n in colunas) + " |\n")

    L.append("## Divergências por modelo D (texto_real) — para conferência manual\n")
    for f in d_files:
        slug = f.stem[len("comparacao_D_"):]
        comp = json.loads(f.read_text(encoding="utf-8"))
        divs = [d for d in comp["divergencias"] if classe_de.get(d["arquivo"]) == CLASSE]
        L.append(f"### D:{slug} ({len(divs)} divergências)\n")
        L.append("| Doc | Campo | Valor D | Valor gabarito |")
        L.append("|---|---|---|---|")
        for d in divs:
            L.append(f"| {d['arquivo']} | {d['campo']} | `{d['valor_predito']}` | `{d['valor_gabarito']}` |")
        L.append("")

    REL_D.mkdir(parents=True, exist_ok=True)
    out_md = REL_D / "relatorio_D.md"
    out_md.write_text("\n".join(L), encoding="utf-8")

    print("Geral (texto_real): " + " | ".join(f"{rot}={_fmt(g)}(n={n})" for rot, _, g, n in colunas))
    print(f"Relatório: {out_md.relative_to(config.ROOT)}")


if __name__ == "__main__":
    main()
