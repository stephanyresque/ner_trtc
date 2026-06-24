"""Experiência C: extrai os 5 campos via gateway LiteLLM pago (1 modelo) nos docs carimbo+scan+texto_real.

Retoma execuções anteriores por padrão (não repaga docs já OK); --do-zero refaz tudo.
Rode a partir de ner_trct/:  python -m experimentos.c_modelos_pagos.run
"""

import argparse
import json
import time
from pathlib import Path

from src import config
from experimentos.c_modelos_pagos.extrair_pago import CAMPOS, _config, extrair_campos

SAIDAS = Path(__file__).resolve().parent / "saidas"
CLASSES_C = {"carimbo", "scan", "texto_real"}    # escopo completo (igual à B)


def _slug(modelo: str) -> str:
    return modelo.rsplit("/", 1)[-1]             # "openai/gpt-5-mini" -> "gpt-5-mini"


def _salvar(path: Path, dados) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")


def _montar_resumo(modelo: str, docs: list, itens: list, t_run: float) -> dict:
    def soma_tok(k):
        return sum((it.get("usage") or {}).get(k) or 0 for it in itens)
    lat = [it["latencia_s"] for it in itens if it.get("latencia_s") is not None]
    custo_total = round(sum(it.get("custo_usd") or 0.0 for it in itens), 6)
    repassado = any(it.get("custo_repassado") for it in itens)
    return {
        "experimento": f"C — modelo pago via LiteLLM ({modelo})",
        "modelo": modelo,
        "gateway": "litellm.datalawyer.local",
        "custo_total_usd": custo_total,
        "custo_repassado_pelo_gateway": repassado,
        "aviso_custo": None if repassado else
            "custo não repassado pelo gateway (response_cost ausente); custo_total_usd pode estar subestimado.",
        "n_docs_rodados": len(docs),
        "n_docs_com_erro": sum(1 for it in itens if it.get("erro")),
        "tokens": {"prompt": soma_tok("prompt_tokens"), "completion": soma_tok("completion_tokens"),
                   "total": soma_tok("total_tokens")},
        "latencia_s": {"total": round(sum(lat), 1) if lat else 0.0,
                       "media": round(sum(lat) / len(lat), 2) if lat else 0.0},
        "tempo_total_run_s": round(time.perf_counter() - t_run, 1),
        "validacao": {"pydantic": sum(1 for it in itens if it.get("validacao") == "pydantic"),
                      "fallback": sum(1 for it in itens if it.get("validacao") == "fallback"),
                      "erro": sum(1 for it in itens if it.get("validacao") == "erro")},
        "itens": itens,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--limit", type=int, default=None, metavar="N",
                        help="Processa só os N primeiros docs (debug).")
    parser.add_argument("--do-zero", action="store_true",
                        help="Ignora resultados anteriores e refaz tudo (padrão: retoma o que já deu OK).")
    args = parser.parse_args()

    if not config.TRIAGEM_JSON.exists():
        raise SystemExit(f"{config.TRIAGEM_JSON} não existe. Rode antes: python -m pipeline.run_triagem")

    base_url, api_key, modelo = _config()
    if not base_url or not api_key:
        raise SystemExit("LITELLM_BASE_URL/LITELLM_API_KEY ausentes — preencha ner_trct/.env (cp .env.example .env).")

    slug = _slug(modelo)
    triagem = json.loads(config.TRIAGEM_JSON.read_text(encoding="utf-8"))
    docs = [d for d in triagem if d.get("classe") in CLASSES_C]
    if args.limit:
        docs = docs[:args.limit]

    pred_path = SAIDAS / f"predicoes_C_{slug}.json"
    resumo_path = SAIDAS / f"_resumo_extracao_{slug}.json"

    feitos_rec, feitos_meta = {}, {}
    if not args.do_zero and pred_path.exists() and resumo_path.exists():
        feitos_rec = json.loads(pred_path.read_text(encoding="utf-8"))
        feitos_meta = {it["arquivo"]: it for it
                       in json.loads(resumo_path.read_text(encoding="utf-8")).get("itens", [])
                       if not it.get("erro")}
        n_reuso = len(set(feitos_meta) & set(feitos_rec))
        if n_reuso:
            print(f"[resume] {n_reuso} doc(s) já OK — refazendo só o restante (--do-zero para refazer tudo).")

    print(f"Modelo: {modelo} | docs a rodar: {len(docs)}\n")

    predicoes: dict[str, dict] = {}
    itens: list[dict] = []
    t_run = time.perf_counter()
    for i, d in enumerate(docs, start=1):
        b = d["arquivo"]
        if not args.do_zero and b in feitos_meta and b in feitos_rec:
            rec = feitos_rec[b]
            meta = {k: v for k, v in feitos_meta[b].items() if k not in ("arquivo", "classe")}
            print(f"[{i}/{len(docs)}] {b} ({d['classe']}) — reaproveitado")
        else:
            print(f"[{i}/{len(docs)}] {b} ({d['classe']})")
            try:
                rec, meta = extrair_campos(config.AMOSTRAS_DIR / d["pdf"])
            except Exception as e:
                rec = {c: "" for c in CAMPOS}
                meta = {"usage": None, "custo_usd": 0.0, "custo_repassado": False, "latencia_s": None,
                        "modo": None, "validacao": None, "erro": str(e), "n_imagens": 0}
                print(f"    ERRO: {e}")
        predicoes[b] = rec
        _salvar(SAIDAS / f"{b}.json", rec)
        itens.append({"arquivo": b, "classe": d["classe"], **meta})
        _salvar(pred_path, predicoes)                                   # incremental
        _salvar(resumo_path, _montar_resumo(modelo, docs, itens, t_run))  # incremental (permite resume)

    resumo = _montar_resumo(modelo, docs, itens, t_run)
    _salvar(resumo_path, resumo)

    print(f"\n{'='*60}")
    print(f"  Rodados: {len(docs)} | com erro: {resumo['n_docs_com_erro']}")
    print(f"  Custo total: US$ {resumo['custo_total_usd']:.6f}" +
          ("" if resumo["custo_repassado_pelo_gateway"] else "  (custo NÃO repassado pelo gateway)"))
    print(f"  Tokens (p/c/t): {resumo['tokens']['prompt']}/{resumo['tokens']['completion']}/{resumo['tokens']['total']}")
    print(f"  Tempo do run: {resumo['tempo_total_run_s']}s | latência média: {resumo['latencia_s']['media']}s/doc")
    print(f"  Validação: pydantic={resumo['validacao']['pydantic']} "
          f"fallback={resumo['validacao']['fallback']} erro={resumo['validacao']['erro']}")
    print(f"  Predições: {pred_path.relative_to(config.ROOT)}")
    print(f"{'='*60}")
    print(f"Próximo: python -m pipeline.run_compare --fonte json "
          f"--pred experimentos/c_modelos_pagos/saidas/predicoes_C_{slug}.json "
          f"--out relatorios/c/comparacao_C_{slug}.json")


if __name__ == "__main__":
    main()
