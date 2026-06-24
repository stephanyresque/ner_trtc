# Experimento C — modelo pago via gateway LiteLLM (lendo todas as páginas)

Extrai os 5 campos do TRCT a partir das **imagens de TODAS as páginas** do PDF, chamando um
**modelo pago via o gateway LiteLLM da empresa** (`http://litellm.datalawyer.local`). É "a B
trocando o produtor": reusa a espinha `src/` e o avaliador `pipeline/run_compare.py` sem alterá-los.
Modelo padrão: **`openai/gpt-5-mini`** (multimodal). Escopo: docs `carimbo` + `scan` + `texto_real`.

Diferenças vs. B (VLM local):
- **Gateway pago** em vez do vLLM local (sem GPU).
- **Todas as páginas** do PDF (B mandava só a 1ª) — `ultima_remuneracao` às vezes só aparece adiante.
- **Resposta estruturada de verdade:** `response_format=ExtracaoTRCT` + validação `model_validate_json`,
  com extrator de JSON robusto só como fallback. Registra `validacao` (pydantic/fallback/erro) por doc.
- **Custo real** (`response_cost` / `completion_cost`) em vez de `0.0` hardcoded; mede tokens e tempo.

## 1. Configurar o gateway (uma vez)

Os secrets ficam no `.env` **da raiz** do `ner_trct/` (o `.env.example` já tem os placeholders):

```bash
cd ner_trct
cp .env.example .env
# edite .env e preencha:
#   LITELLM_BASE_URL=http://litellm.datalawyer.local
#   LITELLM_API_KEY=sk-...
# (opcional) sobrescreva os defaults da C no mesmo .env:
#   MODELO=openai/gpt-5-mini   # modelo no gateway (formato <provider>/<modelo>)
#   PAGINAS=0                  # 0 = todas as páginas; >0 limita
#   DPI=200                    # resolução da rasterização
#   MAX_PX=2000                # lado maior máximo da imagem
```

Dependências do cliente (se rodar fora de um venv que já as tenha):

```bash
pip install -r experimentos/c_modelos_pagos/requirements.txt
```

## 2. Rodar C + pontuar + relatório (a partir de `ner_trct/`)

```bash
# extração nos 103 docs (1 json/doc + predicoes_C_gpt-5-mini.json + _resumo_extracao_gpt-5-mini.json)
# retoma sozinho o que já deu OK; use --do-zero para refazer tudo, --limit N para um teste rápido
python -m experimentos.c_modelos_pagos.run

# pontuar contra o gabarito (reusa o comparador da espinha)
python -m pipeline.run_compare --fonte json \
    --pred experimentos/c_modelos_pagos/saidas/predicoes_C_gpt-5-mini.json \
    --out  relatorios/c/comparacao_C_gpt-5-mini.json

# relatório (acurácia por campo/geral, quebra por classe, A vs C, custo/tempo/tokens, divergências)
MODELO=openai/gpt-5-mini python -m experimentos.c_modelos_pagos.relatorio
```

> No Windows/PowerShell, troque `MODELO=openai/gpt-5-mini python ...` por
> `$env:MODELO="openai/gpt-5-mini"; python -m experimentos.c_modelos_pagos.relatorio`
> (ou deixe o default, já que o módulo usa `openai/gpt-5-mini`).

## Notas

- **Nome de arquivo:** o `/` do modelo é saneado para o último segmento (`openai/gpt-5-mini` → `gpt-5-mini`).
- **Custo não repassado:** se o gateway não devolver `response_cost`, o resumo grava `custo_total_usd`
  como está e marca `custo_repassado_pelo_gateway=false` + `aviso_custo` — não falha por isso.
- **Saídas** em `experimentos/c_modelos_pagos/saidas/`; avaliação em `relatorios/c/`. `data/` nunca recebe resultado.
- **Trocar de modelo:** basta `MODELO=<provider>/<modelo>` no `.env` (ou no ambiente). Os nomes de
  arquivo e relatórios seguem o slug do modelo automaticamente.
