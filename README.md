# ner_trct — extração de 5 entidades de TRCT

Extrai 5 campos de **TRCT** (Termo de Rescisão do Contrato de Trabalho) a partir dos PDFs em
`data/amostras/`, com uma espinha compartilhada (triagem → dataset → comparador) e um experimento
por abordagem de extração.

| Campo | Âncora no formulário | Tipo |
|---|---|---|
| `nome_trabalhador`   | campo 11 (Nome)                | texto |
| `nome_empregador`    | campo 02 (Razão Social/Nome)   | texto |
| `ultima_remuneracao` | campo 23 (Remuneração Mês Ant.)| valor (float) |
| `data_admissao`      | campo 24 (Data de Admissão)    | data dd/mm/aaaa |
| `data_demissao`      | campo 26 (Data de Afastamento) | data dd/mm/aaaa |

Distinção central: **rodar ≠ pontuar**. A extração roda em *todos* os docs `texto_real`; a
pontuação só ocorre nos que têm gabarito válido. Docs sem gabarito geram saída normalmente e
ficam numa lista para conferência manual.

## Estrutura

```
ner_trct/
├── README.md  requirements.txt  .env.example  .gitignore
├── data/                       # entrada imutável + cache derivado (nunca resultado de experimento)
│   ├── amostras/               # 103 PDFs de TRCT
│   ├── baseline/               # gabarito aproximado: saida_json/ + resultados_trct.csv
│   └── intermediario/          # cache: texto/ (1 .txt/PDF), triagem.json, dataset.json
├── src/                        # espinha (sem código específico de experimento)
│   ├── config.py schemas.py pdf_text.py
│   ├── triagem.py dataset.py baseline.py
│   └── normalize.py compare.py metrics.py
├── pipeline/                   # orquestradores da espinha (servem a qualquer experimento)
│   ├── run_triagem.py run_dataset.py run_compare.py
├── experimentos/
│   ├── a_engenharia_dados/     # Experimento A: parser determinístico (sem LLM)
│   │   ├── extrair_trct.py run.py relatorio.py  +  saidas/
│   │   └── saidas/             # predicoes_A.json + 1 json/doc
│   └── b_modelos/              # Experimento B (LiteLLM) — a fazer
└── relatorios/
    ├── a/                      # comparacao_A.json + relatorio_A.md
    └── _validacao/             # comparacao_csv.json (smoke test do comparador)
```

Imports: `src/`, `pipeline/` e `experimentos/` são **pacotes**; rode tudo como módulo a partir de
`ner_trct/` (`python -m ...`). Sem `sys.path` remendado, sem instalação.

## Como rodar

Os scripts que leem PDF precisam de **PyMuPDF**, instalado na conda venv **`dl`**. Prefixe com
`PYTHONIOENCODING=utf-8` (encoding do console no Windows).

```bash
cd ner_trct
pip install -r requirements.txt          # na venv dl

# Espinha
conda run -n dl python -m pipeline.run_triagem      # -> data/intermediario/triagem.json  (texto_real=15, carimbo=30, scan=58)
conda run -n dl python -m pipeline.run_dataset      # -> data/intermediario/dataset.json   (a_rodar=15, pontuável=14, sem_gabarito=1)

# Experimento A (determinístico, sem LLM)
conda run -n dl python -m experimentos.a_engenharia_dados.run                        # -> saidas/predicoes_A.json
conda run -n dl python -m pipeline.run_compare --fonte json \
    --pred experimentos/a_engenharia_dados/saidas/predicoes_A.json \
    --out relatorios/a/comparacao_A.json                                             # pontua vs gabarito
conda run -n dl python -m experimentos.a_engenharia_dados.relatorio                  # -> relatorios/a/relatorio_A.md

# Validação do comparador (sem LLM, sem PDF): gemini vs referência do CSV
conda run -n dl python -m pipeline.run_compare --fonte csv                           # -> relatorios/_validacao/comparacao_csv.json
```

## Experimento A — parser determinístico (sem LLM)

Lê o PDF em modo de palavras com coordenadas (`get_text("words")`, porque o texto plano embaralha
as colunas), ancora cada campo pelo número impresso + rótulo e captura o valor na coluna (x)
correspondente. **Custo R$ 0,00.** Acurácia geral **0.7857** (14 docs pontuados); acerta 100% nos
formulários limpos — as divergências restantes são quase todas qualidade de OCR da fonte ou
artefato do gabarito (ver `relatorios/a/relatorio_A.md`).

## Triagem (critério já validado)

Não é "tem camada de texto?", e sim "o texto contém os campos do TRCT?". ~30 PDFs têm texto, mas é
só o carimbo do PJe sobre um formulário que é imagem. O detector procura âncoras do formulário
(PIS/PASEP, Razão Social, Remuneração, Data de Admissão, cabeçalhos de seção) ignorando o
boilerplate do PJe. Classes: `texto_real` / `carimbo` / `scan`. Botões de ajuste em
`src/config.py` (`MIN_ANCORAS_TRCT`, `LIMIAR_SCAN_CHARS`, `ANCORAS_TRCT`).

## Gabarito (referência aproximada)

`data/baseline/saida_json/*.json` (1 por PDF) e `resultados_trct.csv` são a extração antiga do
**Gemini** — referência **aproximada**, não anotação humana. Por isso o comparador, além da
acurácia, sempre emite a lista de divergências `(doc, campo, valor_predito, valor_gabarito)` para
conferência manual. JSONs vazios/de 1 byte contam como "sem gabarito". O CSV traz colunas `*_gemini`
só para 3 campos (remuneração, admissão, demissão) — usadas para validar o comparador sem LLM.
Casamento PDF↔JSON↔CSV por **basename completo** (`numero_hash`); nem todo PDF tem gabarito.

---

## Padrão de uso do LiteLLM (necessário para o Experimento B) ⭐

O gateway LiteLLM é o caminho dos outros experimentos do repo. **Forma preferida** (`litellm.completion`,
usada em `contestacoes_porto` e `avaliacao_peticoes`):

```python
import os
from pathlib import Path
from dotenv import load_dotenv
import litellm

litellm.drop_params = True   # descarta params não suportados por certos modelos

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")
LITELLM_BASE_URL = os.getenv("LITELLM_BASE_URL")
LITELLM_API_KEY  = os.getenv("LITELLM_API_KEY")

response = litellm.completion(
    model=modelo,                       # ex.: "openai/gpt-5-mini", "gemini/gemini-2.5-flash"
    custom_llm_provider="openai",       # SEMPRE "openai" — o gateway fala protocolo OpenAI
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": texto},
    ],
    api_base=LITELLM_BASE_URL,
    api_key=LITELLM_API_KEY,
    response_format=ExtracaoTRCT,       # structured output (src/schemas.py)
    metadata={"projeto": "ner_trct", "tags": ["ner", "trct", "trabalhista"]},
)
content = response.choices[0].message.content   # checar None -> finish_reason
```

Forma alternativa (SDK OpenAI apontado ao gateway, usada em `dados_capa_pii`):
```python
from openai import OpenAI
client = OpenAI(api_key=LITELLM_API_KEY, base_url=LITELLM_BASE_URL)
response = client.chat.completions.create(model="openai/gpt-5-mini", messages=[...],
    extra_body={"metadata": {"projeto": "...", "tags": [...]}})
```

### Pontos-chave
- **Base URL / auth:** `LITELLM_BASE_URL` + `LITELLM_API_KEY` num `.env` (ver `.env.example`).
  Default no repo: `http://litellm.datalawyer.local` (host interno — **exige VPN**).
- **`custom_llm_provider="openai"`** é fixo: o gateway é OpenAI-compatível para qualquer provider.
- **Modelos** (prefixo = roteamento no gateway): `openai/gpt-5-mini`, `openai/gpt-4.1-mini`,
  `gemini/gemini-2.5-flash`, `groq/openai/gpt-oss-120b`, `openrouter/deepseek/deepseek-v3.2-cheap`.
- **Structured output:** classe Pydantic em `response_format=`; com `drop_params=True` modelos que
  não suportam ignoram o parâmetro.
- **Token:** lidos de `response.usage` → `{prompt_tokens, completion_tokens, total_tokens}` salvos
  por registro. **Custo (USD) não é calculado em código** — fica no painel do gateway, agregado por
  `metadata.projeto`/`tags` (por isso sempre preencher `metadata`).
- O Experimento B deve reusar o **mesmo comparador** (`python -m pipeline.run_compare --fonte json`)
  contra o gabarito, com A como baseline de custo zero.
