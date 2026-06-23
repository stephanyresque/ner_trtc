"""CLI: extrai o texto de cada PDF, classifica (texto_real/carimbo/scan) e salva triagem.json.

Rode a partir de ner_trct/:  python -m pipeline.run_triagem
"""

import json

from src import config
from src.pdf_text import extrair_texto, listar_pdfs, salvar_texto
from src.triagem import classificar


def main() -> None:
    pdfs = listar_pdfs(config.AMOSTRAS_DIR)
    if not pdfs:
        print(f"[AVISO] Nenhum PDF em {config.AMOSTRAS_DIR}")
        return

    print(f"PDFs encontrados: {len(pdfs)}\n")
    registros: list[dict] = []
    contagem = {c: 0 for c in config.CLASSES_TRIAGEM}

    for i, pdf in enumerate(pdfs, start=1):
        try:
            texto = extrair_texto(pdf)
        except Exception as e:
            texto = ""
            print(f"[{i}/{len(pdfs)}] {pdf.stem}  -> ERRO ao ler ({e}); tratando como scan")

        salvar_texto(pdf.stem, texto, config.TEXTO_DIR)
        info = classificar(texto)
        info["arquivo"] = pdf.stem
        info["pdf"] = pdf.name
        registros.append(info)
        contagem[info["classe"]] += 1
        print(f"[{i}/{len(pdfs)}] {pdf.stem}  -> {info['classe']:<10} "
              f"(âncoras={len(info['ancoras_trct'])}, chars={info['n_chars']})")

    config.INTERMEDIARIO_DIR.mkdir(parents=True, exist_ok=True)
    config.TRIAGEM_JSON.write_text(
        json.dumps(registros, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"\n{'='*50}")
    for classe in config.CLASSES_TRIAGEM:
        print(f"  {classe:<12}: {contagem[classe]}")
    print(f"{'='*50}")
    print(f"Triagem salva em: {config.TRIAGEM_JSON.relative_to(config.ROOT)}")


if __name__ == "__main__":
    main()
