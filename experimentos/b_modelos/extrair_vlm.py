"""Extrai os 5 campos lendo a IMAGEM do PDF via vLLM (OpenAI-compatible), agnóstico de modelo.

Renderiza a(s) página(s) em imagem base64 e pede o JSON dos 5 campos com guided json
(response_format); se o modelo não honrar, cai para prompt + parse robusto de JSON.
"""

import base64
import json
import os
import time
from pathlib import Path

import fitz  # PyMuPDF

CAMPOS = ["nome_trabalhador", "nome_empregador", "ultima_remuneracao", "data_admissao", "data_demissao"]

PAGINAS = int(os.getenv("PAGINAS", "1"))      # nº de páginas enviadas (limite image=2 no vLLM)
DPI = int(os.getenv("DPI", "200"))
MAX_PX = int(os.getenv("MAX_PX", "2000"))

SYSTEM_PROMPT = (
    "Você extrai dados de TRCT (Termo de Rescisão do Contrato de Trabalho) a partir da imagem "
    "do formulário e responde APENAS com um JSON. Nunca invente: campo ausente = string vazia."
)

USER_PROMPT = (
    "A imagem é um formulário TRCT padronizado, com campos numerados. Extraia exatamente estes "
    "5 campos e responda APENAS com um JSON válido (sem markdown, sem comentários):\n"
    "- nome_trabalhador: campo 11 \"Nome\" (o TRABALHADOR; NÃO use o campo 20 \"Nome da mãe\").\n"
    "- nome_empregador: campo 02 \"Razão Social/Nome\" (o EMPREGADOR; NÃO use o campo 11).\n"
    "- ultima_remuneracao: campo 23 \"Remuneração Mês Ant.\" (valor como aparece, ex.: 1.843,25).\n"
    "- data_admissao: campo 24 \"Data de Admissão\" (dd/mm/aaaa).\n"
    "- data_demissao: campo 26 \"Data de Afastamento\" (é a DEMISSÃO; NÃO use o campo 25 \"Aviso prévio\").\n"
    "Datas em dd/mm/aaaa; valor exatamente como no documento; \"\" se ausente; PROIBIDO inventar.\n"
    "Responda só o JSON com exatamente estas chaves: "
    '{"nome_trabalhador":"","nome_empregador":"","ultima_remuneracao":"","data_admissao":"","data_demissao":""}'
)


def _config() -> tuple[str, str, str]:
    try:
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).resolve().parent / ".env")
    except ImportError:
        pass
    return (os.getenv("VLLM_BASE_URL", "http://localhost:8000/v1"),
            os.getenv("VLLM_API_KEY", "EMPTY"),
            os.getenv("MODELO", "qwen3-vl-4b"))


def renderizar_paginas(pdf_path, paginas: int = PAGINAS, dpi: int = DPI, max_px: int = MAX_PX) -> list[str]:
    """Renderiza as primeiras `paginas` páginas em data-URI PNG (lado maior <= max_px)."""
    uris: list[str] = []
    with fitz.open(pdf_path) as doc:
        for page in list(doc)[:paginas]:
            r = page.rect
            zoom = min(dpi / 72.0, max_px / max(r.width, r.height))
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
            b64 = base64.b64encode(pix.tobytes("png")).decode()
            uris.append(f"data:image/png;base64,{b64}")
    return uris


def _extrair_json(content: str) -> dict:
    content = (content or "").strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    if "```" in content:
        bloco = content[content.find("```") + 3: content.rfind("```")].strip()
        if bloco.startswith("json"):
            bloco = bloco[4:].strip()
        try:
            return json.loads(bloco)
        except json.JSONDecodeError:
            pass
    i, j = content.find("{"), content.rfind("}")
    if i != -1 and j > i:
        return json.loads(content[i:j + 1])
    raise ValueError(f"sem JSON na resposta: {content[:200]!r}")


def _coerce(dados: dict) -> dict:
    return {c: ("" if dados.get(c) is None else str(dados.get(c)).strip()) for c in CAMPOS}


def extrair_campos(pdf_path) -> tuple[dict, dict]:
    """Devolve (registro de 5 campos, meta {usage, latencia_s, modo, erro, n_imagens})."""
    import litellm
    from src.schemas import ExtracaoTRCT
    litellm.drop_params = True

    base_url, api_key, modelo = _config()
    imagens = renderizar_paginas(pdf_path)
    blocos = [{"type": "text", "text": USER_PROMPT}] + \
             [{"type": "image_url", "image_url": {"url": u}} for u in imagens]
    messages = [{"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": blocos}]
    comum = dict(model=modelo, custom_llm_provider="openai", api_base=base_url, api_key=api_key,
                 messages=messages, temperature=0.0, max_tokens=1024)

    erro, modo = None, "guided_json"
    t0 = time.perf_counter()
    try:
        resp = litellm.completion(response_format=ExtracaoTRCT, **comum)
    except Exception:
        modo = "prompt_only"
        resp = litellm.completion(**comum)
    latencia = round(time.perf_counter() - t0, 3)

    try:
        rec = _coerce(_extrair_json(resp.choices[0].message.content))
    except Exception as e:
        rec, erro = {c: "" for c in CAMPOS}, f"parse: {e}"

    u = getattr(resp, "usage", None)
    usage = None if u is None else {
        "prompt_tokens": getattr(u, "prompt_tokens", None),
        "completion_tokens": getattr(u, "completion_tokens", None),
        "total_tokens": getattr(u, "total_tokens", None),
    }
    return rec, {"usage": usage, "latencia_s": latencia, "modo": modo, "erro": erro, "n_imagens": len(imagens)}
