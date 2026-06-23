"""Experimento B: extrai os 5 campos lendo a imagem do PDF (VLM local) nos docs carimbo+scan+texto_real.

Rode a partir de ner_trct/ (no container cliente):  python -m experimentos.b_modelos.run
"""

import json
from pathlib import Path

from src import config
from experimentos.b_modelos.extrair_vlm import CAMPOS, _config, extrair_campos

SAIDAS = Path(__file__).resolve().parent / "saidas"
CLASSES_B = {"carimbo", "scan", "texto_real"}


def _salvar(path: Path, dados) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    if not config.TRIAGEM_JSON.exists():
        raise SystemExit(f"{config.TRIAGEM_JSON} não existe. Rode antes: python -m pipeline.run_triagem")

    _, _, modelo = _config()
    triagem = json.loads(config.TRIAGEM_JSON.read_text(encoding="utf-8"))
    docs = [d for d in triagem if d.get("classe") in CLASSES_B]
    pred_path = SAIDAS / f"predicoes_B_{modelo}.json"
    print(f"Modelo: {modelo} | docs a rodar: {len(docs)}\n")

    predicoes: dict[str, dict] = {}
    itens: list[dict] = []
    for i, d in enumerate(docs, start=1):
        b = d["arquivo"]
        print(f"[{i}/{len(docs)}] {b} ({d['classe']})")
        try:
            rec, meta = extrair_campos(config.AMOSTRAS_DIR / d["pdf"])
        except Exception as e:
            rec = {c: "" for c in CAMPOS}
            meta = {"usage": None, "latencia_s": None, "modo": None, "erro": str(e), "n_imagens": 0}
            print(f"    ERRO: {e}")
        predicoes[b] = rec
        _salvar(SAIDAS / f"{b}.json", rec)
        itens.append({"arquivo": b, "classe": d["classe"], **meta})
        _salvar(pred_path, predicoes)        # incremental

    def _soma_tok(k):
        return sum((it["usage"] or {}).get(k) or 0 for it in itens)
    lat = [it["latencia_s"] for it in itens if it.get("latencia_s") is not None]
    _salvar(SAIDAS / f"_resumo_extracao_{modelo}.json", {
        "experimento": f"B — VLM local ({modelo})",
        "modelo": modelo,
        "custo_api": 0.0,
        "n_docs_rodados": len(docs),
        "n_docs_com_erro": sum(1 for it in itens if it.get("erro")),
        "tokens": {"prompt": _soma_tok("prompt_tokens"), "completion": _soma_tok("completion_tokens"),
                   "total": _soma_tok("total_tokens")},
        "latencia_s": {"total": round(sum(lat), 1) if lat else 0.0,
                       "media": round(sum(lat) / len(lat), 2) if lat else 0.0},
        "itens": itens,
    })

    n_erro = sum(1 for it in itens if it.get("erro"))
    print(f"\n{'='*60}")
    print(f"  Rodados: {len(docs)} | com erro: {n_erro} | custo_api: R$ 0,00 (modelo local)")
    print(f"  Predições: {pred_path.relative_to(config.ROOT)}")
    print(f"{'='*60}")
    print(f"Próximo: python -m pipeline.run_compare --fonte json "
          f"--pred {pred_path.relative_to(config.ROOT)} --out relatorios/b/comparacao_B_{modelo}.json")


if __name__ == "__main__":
    main()
