"""Produtor do Experimento D: extrai os 5 campos do TRCT a partir do TEXTO do PDF (modelo local de texto).

Lê o texto INTEIRO (cache em data/intermediario/texto ou extração na hora via src.pdf_text) e chama o
vLLM local por litellm, validando com Pydantic (extrator de JSON robusto como fallback). Custo = 0.0 (local).
"""

import json
import os
import re
import time
from pathlib import Path

import litellm
from dotenv import load_dotenv

from src import config
from src.pdf_text import extrair_texto
from src.schemas import ExtracaoTRCT
from experimentos.d_texto_local.prompts import SYSTEM_PROMPT, USER_PROMPT

litellm.drop_params = True
load_dotenv(Path(__file__).resolve().parent / ".env")    # vLLM local (mesmo padrão da B)

CAMPOS = config.CAMPOS


def _config() -> tuple[str, str, str]:
    return (os.getenv("VLLM_BASE_URL", "http://localhost:8000/v1"),
            os.getenv("VLLM_API_KEY", "EMPTY"),
            os.getenv("MODELO", "qwen3-4b"))


def carregar_texto(pdf_path) -> str:
    """Texto do PDF INTEIRO: usa o cache data/intermediario/texto/{basename}.txt; senão extrai na hora."""
    cache = config.TEXTO_DIR / f"{Path(pdf_path).stem}.txt"
    if cache.exists():
        texto = cache.read_text(encoding="utf-8").strip()
        if texto:
            return texto
    return extrair_texto(pdf_path)


def _extrair_json(content: str) -> dict:
    content = (content or "").strip()
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
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


def extrair_campos(pdf_path) -> tuple[dict, dict]:
    """Devolve (registro de 5 campos, meta {usage, custo_usd, latencia_s, modo, validacao, erro, n_chars})."""
    base_url, api_key, modelo = _config()
    texto = carregar_texto(pdf_path)
    user_content = f"{USER_PROMPT}\n\nTEXTO DO DOCUMENTO:\n{texto}"
    messages = [{"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content}]
    comum = dict(model=modelo, custom_llm_provider="openai", api_base=base_url, api_key=api_key,
                 messages=messages, temperature=0.0)

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

    return rec, {"usage": _extrair_usage(resp), "custo_usd": 0.0, "latencia_s": latencia,
                 "modo": modo, "validacao": validacao, "erro": erro, "n_chars": len(texto)}
