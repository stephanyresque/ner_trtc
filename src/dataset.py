"""Monta o dataset a partir da triagem: separa o que RODA (todos texto_real) do que PONTUA."""


def montar_dataset(triagem: list[dict], gabarito_validos: dict) -> dict:
    texto_real = [d for d in triagem if d.get("classe") == "texto_real"]

    a_rodar: list[dict] = []
    pontuavel: list[dict] = []
    sem_gabarito: list[dict] = []

    for d in texto_real:
        basename = d["arquivo"]
        registro = {"arquivo": basename, "pdf": d.get("pdf")}
        a_rodar.append(registro)
        (pontuavel if basename in gabarito_validos else sem_gabarito).append(registro)

    return {
        "a_rodar": a_rodar,
        "pontuavel": pontuavel,
        "sem_gabarito": sem_gabarito,
        "resumo": {
            "n_texto_real":   len(texto_real),
            "n_a_rodar":      len(a_rodar),
            "n_pontuavel":    len(pontuavel),
            "n_sem_gabarito": len(sem_gabarito),
        },
    }
