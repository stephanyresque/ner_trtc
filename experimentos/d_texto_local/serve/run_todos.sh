#!/usr/bin/env bash
# Roda o Experimento D ponta a ponta no SERVIDOR (host): para cada modelo sobe o vLLM, extrai,
# pontua e derruba (libera VRAM); ao final gera o relatório consolidado (D + C/B/A).
# Uso:  HF_TOKEN=hf_... bash experimentos/d_texto_local/serve/run_todos.sh
set -euo pipefail

# ----------------------------- editar aqui -----------------------------
MODELOS=(                       # "perfil:served_name" (served_name = --served-model-name do compose)
  "qwen35:qwen3-4b"
  "gemma3:gemma-3-4b-it"
)
REPO=/mnt/hd/ceia/user_stephany/ner_trct
CLIENT_IMG=trct-d-client
TIMEOUT=600                     # segundos de espera p/ o vLLM ficar pronto
# -----------------------------------------------------------------------

COMPOSE="docker compose -f experimentos/d_texto_local/serve/docker-compose.yml"
ENVFILE=experimentos/d_texto_local/.env
cd "$REPO"

dk() { docker run --rm --network host -v "$REPO:/app" -w /app --env-file "$ENVFILE" "$@"; }

PERFIL_ATUAL=""
derrubar() {
  if [[ -n "$PERFIL_ATUAL" ]]; then
    echo ">> derrubando perfil '$PERFIL_ATUAL' (liberando VRAM)"
    $COMPOSE --profile "$PERFIL_ATUAL" down || true
    PERFIL_ATUAL=""
  fi
}
trap derrubar EXIT              # garante o down mesmo se algo falhar no meio

esperar_vllm() {
  local nome="$1" t=0
  echo ">> aguardando o vLLM servir '$nome' (timeout ${TIMEOUT}s)"
  while (( t < TIMEOUT )); do
    if curl -s localhost:8000/v1/models 2>/dev/null | grep -q "\"$nome\""; then
      echo ">> vLLM pronto: $nome"; return 0
    fi
    sleep 5; t=$((t + 5))
  done
  echo "ERRO: vLLM não serviu '$nome' em ${TIMEOUT}s." >&2
  return 1
}

echo ">> build do cliente ($CLIENT_IMG)"
docker build -t "$CLIENT_IMG" -f experimentos/d_texto_local/client/Dockerfile experimentos/d_texto_local

for par in "${MODELOS[@]}"; do
  PERFIL="${par%%:*}"
  NOME="${par##*:}"
  SLUG="${NOME##*/}"
  echo
  echo "============================================================"
  echo "  Modelo D: $NOME  (perfil $PERFIL)"
  echo "============================================================"

  PERFIL_ATUAL="$PERFIL"
  $COMPOSE --profile "$PERFIL" up -d
  esperar_vllm "$NOME"

  echo ">> extração"
  dk -e MODELO="$NOME" "$CLIENT_IMG" python -m experimentos.d_texto_local.run

  echo ">> pontuação"
  dk "$CLIENT_IMG" python -m pipeline.run_compare --fonte json \
    --pred "experimentos/d_texto_local/saidas/predicoes_D_${SLUG}.json" \
    --out  "relatorios/d/comparacao_D_${SLUG}.json"

  derrubar
done

echo
echo ">> relatório consolidado (D + C/B/A)"
dk "$CLIENT_IMG" python -m experimentos.d_texto_local.relatorio

echo ">> concluído. Relatório em relatorios/d/relatorio_D.md"
