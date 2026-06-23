# Experimento B — VLM local lendo a imagem do TRCT (vLLM, custo R$ 0)

Extrai os 5 campos do TRCT a partir da **imagem** do PDF, com modelos de visão abertos servidos
**localmente** via vLLM (endpoint OpenAI-compatible). Roda **um modelo de cada vez** (12 GB):
`qwen3-vl-4b` (Qwen/Qwen3-VL-4B-Instruct) e `glm-ocr` (zai-org/GLM-OCR, modo extração via chat+schema).
Escopo: docs `carimbo` + `scan` + `texto_real`. Mesmo código para os dois — troca só `.env` e o perfil.

Tudo roda no servidor Ubuntu (1x RTX 4070 Ti). Bibliotecas só em container; nada no base do host.
Caminho do repo no servidor: `/mnt/hd/ceia/user_stephany/ner_trct` (ajuste os mounts se diferir).

## 1. Servir o modelo (vLLM)

```bash
cd experimentos/b_modelos/serve
docker compose --profile qwen up -d          # ou: --profile glm   (GLM pode pedir tag nova: VLLM_TAG=nightly ...)
curl -s localhost:8000/v1/models             # checar: deve listar qwen3-vl-4b (ou glm-ocr)
# ... rodar o experimento (passos 2-4) ...
docker compose --profile qwen down           # derrubar
```

## 2. Cliente Python (container dedicado)

```bash
# build (uma vez); contexto = experimentos/b_modelos
docker build -t trct-b-client -f experimentos/b_modelos/client/Dockerfile experimentos/b_modelos
```

`--network host` faz o cliente alcançar o vLLM em `localhost:8000`; `--env-file` injeta `.env`.
Defina o modelo no `.env` (`MODELO=qwen3-vl-4b` ou `glm-ocr`) antes de rodar.

## 3. Rodar B + pontuar + relatório (a partir da raiz do repo)

```bash
REPO=/mnt/hd/ceia/user_stephany/ner_trct
DK="docker run --rm --network host -v $REPO:/app -w /app --env-file experimentos/b_modelos/.env trct-b-client"

# extração (1 json/doc + predicoes_B_<MODELO>.json + _resumo_extracao_<MODELO>.json)
$DK python -m experimentos.b_modelos.run

# pontuar contra o gabarito (reusa o comparador da espinha)
$DK python -m pipeline.run_compare --fonte json \
    --pred experimentos/b_modelos/saidas/predicoes_B_qwen3-vl-4b.json \
    --out  relatorios/b/comparacao_B_qwen3-vl-4b.json

# relatório (acurácia por campo/geral, quebra por classe, A vs B nos texto_real, divergências)
$DK python -m experimentos.b_modelos.relatorio
```

## 4. Trocar para o GLM

```bash
cd experimentos/b_modelos/serve && docker compose --profile qwen down
sed -i 's/^MODELO=.*/MODELO=glm-ocr/' ../.env
docker compose --profile glm up -d           # se preciso: VLLM_TAG=nightly docker compose --profile glm up -d
# repetir o passo 3 trocando qwen3-vl-4b por glm-ocr nos nomes de arquivo
```

## Notas

- **VRAM (12 GB):** Qwen3-VL-4B ~8 GB em fp16; GLM-OCR ~0.9B (folgado). Flags de caber:
  `--gpu-memory-utilization 0.90 --max-model-len 8192 --limit-mm-per-prompt image=2`.
- **Versões:** Qwen3-VL exige vLLM ≥ 0.11.0; GLM-OCR pode exigir tag mais nova (transformers ≥ 5) —
  suba o GLM com `VLLM_TAG=...`. Se o vLLM recusar `--limit-mm-per-prompt image=2`, use `'{"image":2}'`.
- **Páginas:** envia só a 1ª página por padrão (`PAGINAS` no env; respeita o limite image=2).
- **Custo de API = R$ 0** (modelo local); este experimento **não** usa o gateway LiteLLM.
- Saídas em `experimentos/b_modelos/saidas/`; avaliação em `relatorios/b/`. `data/` nunca recebe resultado.
