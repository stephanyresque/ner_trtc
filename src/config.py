"""Configuração da espinha: paths, os 5 campos do TRCT e os parâmetros da triagem."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DATA = ROOT / "data"
AMOSTRAS_DIR = DATA / "amostras"
BASELINE_DIR = DATA / "baseline"
BASELINE_JSON_DIR = BASELINE_DIR / "saida_json"      # gabarito aproximado (Gemini antigo)
BASELINE_CSV = BASELINE_DIR / "resultados_trct.csv"

INTERMEDIARIO_DIR = DATA / "intermediario"           # cache derivado (nunca resultado de experimento)
TEXTO_DIR = INTERMEDIARIO_DIR / "texto"
TRIAGEM_JSON = INTERMEDIARIO_DIR / "triagem.json"
DATASET_JSON = INTERMEDIARIO_DIR / "dataset.json"

RELATORIOS_DIR = ROOT / "relatorios"                 # avaliações de cada experimento

# --- Os 5 campos e como normalizar cada um na comparação ---
CAMPOS = [
    "nome_trabalhador",
    "nome_empregador",
    "ultima_remuneracao",
    "data_admissao",
    "data_demissao",
]

TIPO_CAMPO = {
    "nome_trabalhador":   "texto",
    "nome_empregador":    "texto",
    "ultima_remuneracao": "valor",
    "data_admissao":      "data",
    "data_demissao":      "data",
}

ANCORA_FORMULARIO = {
    "nome_trabalhador":   "campo 11 (Nome)",
    "nome_empregador":    "campo 02 (Razão Social/Nome)",
    "ultima_remuneracao": "campo 23 (Remuneração Mês Ant.)",
    "data_admissao":      "campo 24 (Data de Admissão)",
    "data_demissao":      "campo 26 (Data de Afastamento)",
}

# O CSV só traz variante *_gemini para estes 3 campos (não há nome_*_gemini).
CAMPOS_CSV_GEMINI = ["ultima_remuneracao", "data_admissao", "data_demissao"]

# --- Triagem: texto_real / carimbo / scan ---
# Critério: não é "tem texto?", e sim "o texto tem os campos do TRCT?". Muitos PDFs têm
# texto, mas é só o carimbo do PJe sobre um formulário que é imagem.
LIMIAR_SCAN_CHARS = 40        # abaixo disso: sem camada de texto útil -> scan
MIN_ANCORAS_TRCT = 2          # nº mínimo de âncoras distintas para texto_real

# Padrões (regex já normalizados: sem acento, caixa alta). Os cabeçalhos de seção
# ("DO EMPREGADOR" etc.) entram porque o OCR de alguns fornecedores corrompe os rótulos
# de campo mas preserva os cabeçalhos.
ANCORAS_TRCT = [
    r"PIS\s*/?\s*PASEP",
    r"RAZAO SOCIAL",
    r"REMUNERACAO",
    r"DATA DE ADMISSAO",
    r"DATA DE AFASTAMENTO",
    r"CAUSA DO AFASTAMENTO",
    r"CATEGORIA DO TRABALHADOR",
    r"TERMO DE RESCISAO",
    r"\bCBO\b",
    r"\bCNPJ\s*/?\s*CEI\b",
    r"DADOS DO CONTRATO",
    r"DO EMPREGADOR",
    r"DO TRABALHADOR",
]

# Boilerplate do PJe — registrado na triagem só para auditoria.
BOILERPLATE_PJE = [
    r"ASSINADO ELETRONICAMENTE POR",
    r"JUNTADO EM",
    r"NUMERO DO DOCUMENTO",
    r"CONSULTE.{0,40}AUTENTICIDADE",
]

CLASSES_TRIAGEM = ("texto_real", "carimbo", "scan")
