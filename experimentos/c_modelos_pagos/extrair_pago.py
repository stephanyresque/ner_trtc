"""Produtor da Experiência C: extrai os 5 campos do TRCT via gateway LiteLLM pago (multimodal).

Renderiza TODAS as páginas do PDF em PNG base64, força response_format=ExtracaoTRCT e valida a
resposta com Pydantic (extrator de JSON robusto como fallback); mede custo e usage reais do LiteLLM.
"""

import base64
import json
import os
import time

import fitz  # PyMuPDF
import litellm
from dotenv import load_dotenv

from src import config
from src.schemas import ExtracaoTRCT
from experimentos.c_modelos_pagos.prompts import SYSTEM_PROMPT, USER_PROMPT

litellm.drop_params = True
load_dotenv(config.ROOT / ".env")        # secrets do gateway no .env da raiz (cp .env.example .env)

CAMPOS = config.CAMPOS                    # reusa a espinha; não duplica a lista de campos
PAGINAS = int(os.getenv("PAGINAS", "0"))  # 0 = todas as páginas (default da C)
DPI = int(os.getenv("DPI", "200"))
MAX_PX = int(os.getenv("MAX_PX", "2000"))


def _config() -> tuple[str, str, str]:
    return (os.getenv("LITELLM_BASE_URL"),
            os.getenv("LITELLM_API_KEY"),
            os.getenv("MODELO", "openai/gpt-5-mini"))


def renderizar_paginas(pdf_path, paginas: int = PAGINAS, dpi: int = DPI, max_px: int = MAX_PX) -> list[str]:
    """Renderiza as páginas em data-URI PNG (lado maior <= max_px). paginas<=0 => todas."""
    uris: list[str] = []
    with fitz.open(pdf_path) as doc:
        selecionadas = list(doc) if paginas <= 0 else list(doc)[:paginas]
        for page in selecionadas:
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


def _validar(content: str) -> tuple[dict, str]:
    """(registro de 5 campos, via). via='pydantic' direto; 'fallback' pelo extrator robusto."""
    try:
        return ExtracaoTRCT.model_validate_json((content or "").strip()).model_dump(), "pydantic"
    except Exception:
        dados = _extrair_json(content)
        coag = {c: ("" if dados.get(c) is None else str(dados.get(c)).strip()) for c in CAMPOS}
        return ExtracaoTRCT.model_validate(coag).model_dump(), "fallback"


def _extrair_usage(resp) -> dict | None:
    u = getattr(resp, "usage", None)
    if u is None:
        return None
    return {"prompt_tokens": getattr(u, "prompt_tokens", None),
            "completion_tokens": getattr(u, "completion_tokens", None),
            "total_tokens": getattr(u, "total_tokens", None)}


def _extrair_custo(resp) -> tuple[float, bool]:
    """(custo_usd, repassado). response_cost do gateway; senão completion_cost local; senão 0.0/False."""
    custo = (getattr(resp, "_hidden_params", None) or {}).get("response_cost")
    if custo:
        return float(custo), True
    try:
        c = litellm.completion_cost(completion_response=resp)
        if c:
            return float(c), True
    except Exception:
        pass
    return 0.0, False


def extrair_campos(pdf_path) -> tuple[dict, dict]:
    """Devolve (registro de 5 campos, meta {usage, custo_usd, custo_repassado, latencia_s, modo, validacao, erro, n_imagens})."""
    base_url, api_key, modelo = _config()
    if not base_url or not api_key:
        raise RuntimeError("LITELLM_BASE_URL/LITELLM_API_KEY ausentes — preencha ner_trct/.env (cp .env.example .env).")

    imagens = renderizar_paginas(pdf_path)
    blocos = [{"type": "text", "text": USER_PROMPT}] + \
             [{"type": "image_url", "image_url": {"url": u}} for u in imagens]
    messages = [{"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": blocos}]
    comum = dict(model=modelo, custom_llm_provider="openai", api_base=base_url, api_key=api_key,
                 messages=messages,
                 metadata={"projeto": "ner_trct_experimento_c", "tags": ["trct", "ner", "extracao"]})

    erro, modo, validacao = None, "guided_json", None
    t0 = time.perf_counter()
    try:
        resp = litellm.completion(response_format=ExtracaoTRCT, **comum)
    except Exception:
        modo = "prompt_only"
        resp = litellm.completion(**comum)
    latencia = round(time.perf_counter() - t0, 3)

    content = resp.choices[0].message.content
    if content is None:
        raise RuntimeError(f"content=None (finish_reason={resp.choices[0].finish_reason!r}).")

    try:
        rec, validacao = _validar(content)
    except Exception as e:
        rec, erro, validacao = {c: "" for c in CAMPOS}, f"parse: {e}", "erro"

    custo, repassado = _extrair_custo(resp)
    return rec, {"usage": _extrair_usage(resp), "custo_usd": custo, "custo_repassado": repassado,
                 "latencia_s": latencia, "modo": modo, "validacao": validacao,
                 "erro": erro, "n_imagens": len(imagens)}
