"""Normalização campo a campo para a comparação: texto, data (dd/mm/aaaa) e valor (float)."""

import re
import unicodedata

from src import config


def _remover_acentos(texto: str) -> str:
    normalizado = unicodedata.normalize("NFD", texto)
    return "".join(ch for ch in normalizado if unicodedata.category(ch) != "Mn")


def normalizar_texto(valor) -> str | None:
    if valor is None:
        return None
    texto = _remover_acentos(str(valor)).upper()
    texto = re.sub(r"[.,;:/()\[\]{}\-]", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def normalizar_valor(valor) -> float | None:
    if valor is None or isinstance(valor, bool):
        return None
    if isinstance(valor, (int, float)):
        return round(float(valor), 2)

    s = re.sub(r"[^\d.,-]", "", str(valor).strip())
    if not s or s in {"-", ".", ","}:
        return None

    tem_virgula, tem_ponto = "," in s, "." in s
    if tem_virgula and tem_ponto:
        # o separador mais à direita é o decimal: pt-BR "1.380,01" ou US "1,380.01"
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif tem_virgula:
        s = s.replace(",", ".") if re.search(r",\d{2}$", s) else s.replace(",", "")
    elif tem_ponto:
        # grupos de exatamente 3 dígitos após o ponto = milhar ("1.000"); senão é decimal
        grupos = s.split(".")
        if len(grupos) >= 2 and all(len(g) == 3 for g in grupos[1:]):
            s = s.replace(".", "")

    try:
        return round(float(s), 2)
    except ValueError:
        return None


_DATA_BR = re.compile(r"^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})$")
_DATA_ISO = re.compile(r"^(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})$")


def normalizar_data(valor) -> str | None:
    if valor is None:
        return None
    s = str(valor).strip()
    if not s:
        return None

    m = _DATA_BR.match(s)
    if m:
        dia, mes, ano = m.groups()
    else:
        m = _DATA_ISO.match(s)
        if not m:
            return None
        ano, mes, dia = m.groups()

    if len(ano) == 2:
        ano = "20" + ano
    return f"{dia.zfill(2)}/{mes.zfill(2)}/{ano}"


_NORMALIZADORES = {"texto": normalizar_texto, "valor": normalizar_valor, "data": normalizar_data}


def normalizar_campo(campo: str, valor):
    return _NORMALIZADORES[config.TIPO_CAMPO[campo]](valor)
