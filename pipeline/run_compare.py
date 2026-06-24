"""CLI avaliador genérico (reusado por A e B): pontua predição vs gabarito + divergências.

  --fonte csv   : pred = colunas *_gemini vs referência do CSV (3 campos; valida o comparador).
  --fonte json  : pred = JSON {basename: {campo}} vs saida_json (5 campos).
Rode a partir de ner_trct/:  python -m pipeline.run_compare [--fonte ...] [--pred ...] [--out ...]
"""

import argparse
import json
from pathlib import Path

from src import config
from src.baseline import carregar_csv, carregar_gabarito_json
from src.compare import comparar
from src.metrics import consolidar


def _rel(p: Path) -> Path:
    """Caminho relativo a ROOT quando possível; senão, absoluto (aceita --out relativo ou de fora)."""
    p = p.resolve()
    try:
        return p.relative_to(config.ROOT)
    except ValueError:
        return p


def _preparar_csv():
    referencia, gemini = carregar_csv()
    return gemini, referencia, config.CAMPOS_CSV_GEMINI, "csv: gemini vs referência (3 campos)"


def _preparar_json(pred_path: Path):
    if not pred_path.exists():
        raise SystemExit(f"Arquivo de predições não encontrado: {pred_path}")
    preds = json.loads(pred_path.read_text(encoding="utf-8"))
    gabarito, _ = carregar_gabarito_json()
    return preds, gabarito, config.CAMPOS, f"json: {pred_path.name} vs saida_json (5 campos)"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fonte", choices=["csv", "json"], default="csv")
    parser.add_argument("--pred", type=Path, default=None, help="JSON de predições (só --fonte json).")
    parser.add_argument("--out", type=Path, default=None, help="Caminho do relatório (default por fonte).")
    args = parser.parse_args()

    if args.fonte == "csv":
        preds, gabs, campos, rotulo = _preparar_csv()
        out = args.out or config.RELATORIOS_DIR / "_validacao" / "comparacao_csv.json"
    else:
        if args.pred is None:
            raise SystemExit("--fonte json exige --pred <arquivo.json>")
        preds, gabs, campos, rotulo = _preparar_json(args.pred)
        out = args.out or config.RELATORIOS_DIR / "comparacao.json"

    comparacao = comparar(preds, gabs, campos=campos)
    resumo = consolidar(comparacao, rotulo=rotulo)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"resumo": resumo, **comparacao}, ensure_ascii=False, indent=2),
                   encoding="utf-8")

    apc = resumo["acuracia_por_campo"]
    print(f"\n{'='*60}\n  {rotulo}\n{'='*60}")
    print(f"  docs pontuados: {resumo['n_docs_pontuados']}")
    for campo in campos:
        print(f"    {campo:<20}: {apc[campo]}  (n={apc['_n_por_campo'][campo]})")
    print(f"    {'GERAL':<20}: {apc['_geral']}")
    print(f"  por documento: {resumo['acuracia_por_documento']} | divergências: {resumo['n_divergencias']}")
    for d in comparacao["divergencias"][:15]:
        print(f"    {d['arquivo']} | {d['campo']} | {d['valor_predito']!r} | {d['valor_gabarito']!r}")
    if len(comparacao["divergencias"]) > 15:
        print(f"    ... (+{len(comparacao['divergencias']) - 15})")
    print(f"\nRelatório salvo em: {_rel(out)}")


if __name__ == "__main__":
    main()
