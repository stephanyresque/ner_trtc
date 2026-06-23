"""CLI: a partir da triagem, separa a_rodar / pontuavel / sem_gabarito em dataset.json.

Rode a partir de ner_trct/:  python -m pipeline.run_dataset
"""

import json

from src import config
from src.baseline import carregar_gabarito_json
from src.dataset import montar_dataset


def main() -> None:
    if not config.TRIAGEM_JSON.exists():
        raise SystemExit(f"{config.TRIAGEM_JSON} não existe. Rode antes: python -m pipeline.run_triagem")

    triagem = json.loads(config.TRIAGEM_JSON.read_text(encoding="utf-8"))
    gabarito_validos, gabaritos_invalidos = carregar_gabarito_json()

    ds = montar_dataset(triagem, gabarito_validos)
    ds["gabaritos_invalidos"] = gabaritos_invalidos

    config.INTERMEDIARIO_DIR.mkdir(parents=True, exist_ok=True)
    config.DATASET_JSON.write_text(json.dumps(ds, ensure_ascii=False, indent=2), encoding="utf-8")

    r = ds["resumo"]
    print(f"{'='*50}")
    print(f"  texto_real          : {r['n_texto_real']}")
    print(f"  -> a_rodar (todos)  : {r['n_a_rodar']}")
    print(f"  -> pontuável        : {r['n_pontuavel']}")
    print(f"  -> sem gabarito     : {r['n_sem_gabarito']}")
    print(f"  gabaritos inválidos : {len(gabaritos_invalidos)} (JSON vazio/1 byte)")
    print(f"{'='*50}")
    for d in ds["sem_gabarito"]:
        print(f"  sem gabarito: {d['arquivo']}")
    print(f"Dataset salvo em: {config.DATASET_JSON.relative_to(config.ROOT)}")


if __name__ == "__main__":
    main()
