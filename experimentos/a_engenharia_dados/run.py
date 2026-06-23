"""Experimento A: extração determinística dos 5 campos (sem LLM) nos docs a_rodar.

Rode a partir de ner_trct/:  python -m experimentos.a_engenharia_dados.run
"""

import json
from pathlib import Path

from src import config
from experimentos.a_engenharia_dados.extrair_trct import CAMPOS_SPEC, extrair_campos

SAIDAS = Path(__file__).resolve().parent / "saidas"
PREDICOES = SAIDAS / "predicoes_A.json"
RESUMO = SAIDAS / "_resumo_extracao.json"


def _salvar(path: Path, dados) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    if not config.DATASET_JSON.exists():
        raise SystemExit("Rode antes: python -m pipeline.run_triagem && python -m pipeline.run_dataset")

    ds = json.loads(config.DATASET_JSON.read_text(encoding="utf-8"))
    a_rodar = ds["a_rodar"]
    print(f"Docs a rodar (texto_real): {len(a_rodar)}\n")

    predicoes: dict[str, dict] = {}
    itens_resumo: list[dict] = []

    for i, doc in enumerate(a_rodar, start=1):
        basename = doc["arquivo"]
        print(f"[{i}/{len(a_rodar)}] {basename}")
        item = {"arquivo": basename, "erro": None}
        try:
            rec = extrair_campos(config.AMOSTRAS_DIR / doc["pdf"])
            predicoes[basename] = rec
            _salvar(SAIDAS / f"{basename}.json", rec)
            item["campos_faltando"] = [c for c in CAMPOS_SPEC if rec[c] is None or rec[c] == ""]
        except Exception as e:
            item["erro"] = str(e)
            predicoes[basename] = {c: (None if config.TIPO_CAMPO[c] == "valor" else "") for c in config.CAMPOS}
            print(f"    ERRO: {e}")
        itens_resumo.append(item)
        _salvar(PREDICOES, predicoes)        # incremental

    n_erro = sum(1 for it in itens_resumo if it["erro"])
    _salvar(RESUMO, {
        "experimento": "A — parser determinístico (sem LLM)",
        "custo_total_usd": 0.0,
        "custo_total_brl": 0.0,
        "n_docs_rodados": len(a_rodar),
        "n_docs_com_erro": n_erro,
        "n_sem_gabarito": ds["resumo"]["n_sem_gabarito"],
        "docs_sem_gabarito": [d["arquivo"] for d in ds["sem_gabarito"]],
        "itens": itens_resumo,
    })

    print(f"\n{'='*60}")
    print(f"  Rodados: {len(a_rodar)} | com erro: {n_erro} | custo: R$ 0,00 (sem LLM)")
    print(f"  Predições: {PREDICOES.relative_to(config.ROOT)}")
    print(f"{'='*60}")
    print("Próximo: python -m pipeline.run_compare --fonte json "
          f"--pred {PREDICOES.relative_to(config.ROOT)} --out relatorios/a/comparacao_A.json")


if __name__ == "__main__":
    main()
