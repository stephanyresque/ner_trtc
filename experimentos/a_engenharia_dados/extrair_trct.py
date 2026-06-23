"""Parser determinístico de TRCT (Experimento A, sem LLM).

Lê o PDF em modo de PALAVRAS com coordenadas (get_text("words")) porque o texto plano
embaralha as colunas do formulário; ancora cada campo pelo NÚMERO impresso + rótulo e
captura o valor na coluna (x) correspondente, na linha logo abaixo do rótulo.
"""

import re
import unicodedata

import fitz  # PyMuPDF

from src.normalize import normalizar_data, normalizar_valor


def _norm(texto: str) -> str:
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )
    return sem_acento.upper()


# kw são prefixos (substring), robustos a truncamento de OCR ("Admissão" -> "Admissã") e a
# rótulos colados ("RazãoSocial/Nome"). A ancoragem por número desambigua campos homônimos
# (11 Nome vs 20 Nome da mãe; 26 Afastamento vs 25 Aviso prévio).
CAMPOS_SPEC = {
    "nome_empregador":    {"numeros": {"02", "2"}, "kw": ["RAZAO"],              "tipo": "nome"},
    "nome_trabalhador":   {"numeros": {"11"},      "kw": ["NOME"],               "tipo": "nome"},
    "ultima_remuneracao": {"numeros": {"23"},      "kw": ["REMUNERA"],           "tipo": "valor"},
    "data_admissao":      {"numeros": {"24"},      "kw": ["DATA", "ADMISS"],     "tipo": "data"},
    "data_demissao":      {"numeros": {"26"},      "kw": ["DATA", "AFASTAMEN"],  "tipo": "data"},
}

_NUM_CAMPO = re.compile(r"^\d{1,2}$")
_JUNK_NOME = re.compile(r"^[\d.,/\-]+$")
_DATA_RE = re.compile(r"\d{1,2}/\d{1,2}/\d{2,4}")
_VALOR_TOKEN = re.compile(r"^\d[\d.,]*\d$|^\d$")
# rótulos que às vezes vazam para a coluna do nome (NASCIMENTO/MÃE ficam de fora: são sobrenomes)
_LABELS_VAZADOS = {"BAIRRO", "ENDERECO", "MUNICIPIO", "CEP", "CTPS"}


def _palavras(page) -> list[dict]:
    out = []
    for x0, y0, x1, y1, texto, *_ in page.get_text("words"):
        if texto.strip():
            out.append({"x0": x0, "y0": y0, "x1": x1, "texto": texto, "norm": _norm(texto)})
    return out


def _linhas(palavras: list[dict], tol: float = 3.5) -> list[list[dict]]:
    """Agrupa palavras por proximidade de y; cada linha ordenada por x."""
    ps = sorted(palavras, key=lambda w: w["y0"])
    linhas: list[list[dict]] = []
    grupo: list[dict] = []
    for w in ps:
        if grupo and w["y0"] - grupo[0]["y0"] > tol:
            linhas.append(sorted(grupo, key=lambda z: z["x0"]))
            grupo = []
        grupo.append(w)
    if grupo:
        linhas.append(sorted(grupo, key=lambda z: z["x0"]))
    return linhas


def _achar_rotulo(linhas: list[list[dict]], numeros: set[str], kws: list[str]) -> dict | None:
    """Acha o número do campo + rótulo e devolve a coluna [x_left, x_right)."""
    for linha in linhas:
        for i, w in enumerate(linha):
            if w["norm"] not in numeros:
                continue
            seg_txt = " ".join(t["norm"] for t in linha[i + 1 : i + 7])
            if not all(kw in seg_txt for kw in kws):
                continue
            x_left = w["x0"]
            x_right = float("inf")
            for t in linha[i + 1 :]:                # próximo número de campo à direita
                if _NUM_CAMPO.match(t["norm"]) and t["x0"] > x_left + 5:
                    x_right = t["x0"]
                    break
            return {"x_left": x_left, "x_right": x_right, "label_y": w["y0"]}
    return None


def _coluna(palavras, label_y, x_left, x_right, y_win=18.0, tol_left=12.0) -> list[dict]:
    sel = [
        w for w in palavras
        if label_y < w["y0"] <= label_y + y_win and (x_left - tol_left) <= w["x0"] < x_right
    ]
    return sorted(sel, key=lambda w: w["x0"])


def _parse_nome(sel: list[dict]) -> str:
    s = re.sub(r"\([^)]*\)", " ", " ".join(w["texto"] for w in sel)).replace("|", " ")
    toks = [t for t in s.split() if not _JUNK_NOME.match(t)]
    if not toks:
        return ""
    toks[0] = re.sub(r"^[\d.\-/]+", "", toks[0])     # tira id colado: "08942-MARCELO" -> "MARCELO"
    if not toks[0]:
        toks = toks[1:]
    # remove tokens que vazaram de outros campos: começam com dígito ("1~3Bairro") ou são rótulos
    toks = [t for t in toks if not (t[:1].isdigit() or _norm(t) in _LABELS_VAZADOS)]
    return " ".join(toks).strip()


def _parse_data(sel: list[dict]) -> str:
    m = _DATA_RE.search(" ".join(w["texto"] for w in sel))
    return (normalizar_data(m.group(0)) or m.group(0)) if m else ""


def _parse_valor(sel: list[dict]):
    for w in sel:
        if _VALOR_TOKEN.match(w["texto"].strip()):
            v = normalizar_valor(w["texto"].strip())
            if v is not None:
                return v
    return None


_PARSERS = {"nome": _parse_nome, "data": _parse_data, "valor": _parse_valor}


def _vazio(valor) -> bool:
    return valor is None or valor == ""


def extrair_campos(pdf_path) -> dict:
    """Devolve o registro de 5 campos; varre as páginas, primeiro valor não-vazio por campo vence."""
    rec = {
        "nome_trabalhador": "",
        "nome_empregador": "",
        "ultima_remuneracao": None,
        "data_admissao": "",
        "data_demissao": "",
    }
    with fitz.open(pdf_path) as doc:
        for page in doc:
            palavras = _palavras(page)
            if not palavras:
                continue
            linhas = _linhas(palavras)
            for campo, spec in CAMPOS_SPEC.items():
                if not _vazio(rec[campo]):
                    continue
                pos = _achar_rotulo(linhas, spec["numeros"], spec["kw"])
                if pos is None:
                    continue
                sel = _coluna(palavras, pos["label_y"], pos["x_left"], pos["x_right"])
                if sel:
                    rec[campo] = _PARSERS[spec["tipo"]](sel)
    return rec
