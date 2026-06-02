import re
from pathlib import Path

import numpy as np
import pandas as pd
import pdfplumber
from PIL import Image


ARQUIVO_PDF = Path("balneabilidade-212026-compressed.pdf")
NOME_CSV = Path("dados_balneabilidade_sudema.csv")
RESOLUCAO = 150
PASTA_MODELOS_OCR = Path(".easyocr")
LEITOR_OCR = None
CIDADES_PB = [
    "BAIA DA TRAICAO",
    "BAÍA DA TRAIÇÃO",
    "JOAO PESSOA",
    "JOÃO PESSOA",
    "RIO TINTO",
    "MATARACA",
    "LUCENA",
    "CABEDELO",
    "CONDE",
    "PITIMBU",
]


def normalizar_texto(texto):
    return re.sub(r"\s+", " ", texto or "").strip()


def remover_acentos(texto):
    tabela = str.maketrans("ÁÀÂÃÉÊÍÓÔÕÚÜÇáàâãéêíóôõúüç", "AAAAEEIOOOUUCaaaaeeiooouuc")
    return texto.translate(tabela)


def extrair_periodo(texto):
    padrao = r"Periodo de Amostragem:\s*(\d{2}/\d{2}/\d{4})\s*a\s*(\d{2}/\d{2}/\d{4})"
    texto_sem_acento = texto.replace("Período", "Periodo")
    encontrado = re.search(padrao, texto_sem_acento, flags=re.IGNORECASE)
    if not encontrado:
        return "", ""
    return encontrado.group(1), encontrado.group(2)


def obter_leitor_ocr():
    global LEITOR_OCR

    if LEITOR_OCR is not None:
        return LEITOR_OCR

    try:
        import easyocr
    except ImportError:
        return ""

    PASTA_MODELOS_OCR.mkdir(exist_ok=True)
    LEITOR_OCR = easyocr.Reader(
        ["pt", "en"],
        gpu=False,
        verbose=False,
        model_storage_directory=str(PASTA_MODELOS_OCR),
        user_network_directory=str(PASTA_MODELOS_OCR),
    )
    return LEITOR_OCR


def executar_ocr(imagem):
    leitor = obter_leitor_ocr()
    if not leitor:
        return ""

    resultado = leitor.readtext(
        np.asarray(imagem.convert("RGB")),
        detail=0,
        paragraph=True,
        decoder="beamsearch",
    )
    return normalizar_texto(" ".join(resultado))


def formatar_nome(texto):
    ajustes = {
        "Baia": "Baía",
        "Traicao": "Traição",
        "Joao": "João",
    }
    nome = remover_acentos(normalizar_texto(texto)).title()
    for original, ajustado in ajustes.items():
        nome = re.sub(rf"\b{original}\b", ajustado, nome)
    return nome


def interpretar_titulo_mapa(texto):
    texto_limpo = normalizar_texto(texto)
    texto_busca = remover_acentos(texto_limpo).upper()
    texto_busca = texto_busca.replace("-", " ")
    texto_busca = re.sub(r"\bPB\b", "", texto_busca)
    texto_busca = normalizar_texto(texto_busca)
    texto_busca = re.sub(r"^BALNEABILIDADE\s+DAS\s+PRAIAS\s+", "", texto_busca)

    cidade_encontrada = ""
    posicao_cidade = -1

    for cidade in CIDADES_PB:
        cidade_busca = remover_acentos(cidade).upper()
        posicao = texto_busca.rfind(cidade_busca)
        if posicao > posicao_cidade:
            cidade_encontrada = cidade
            posicao_cidade = posicao

    if not cidade_encontrada:
        return "", ""

    praias = texto_busca[:posicao_cidade]
    return formatar_nome(praias), formatar_nome(cidade_encontrada)


def componentes_conectados(mascara):
    altura, largura = mascara.shape
    visitados = np.zeros_like(mascara, dtype=bool)
    componentes = []

    for y, x in np.argwhere(mascara):
        if visitados[y, x]:
            continue

        pilha = [(int(y), int(x))]
        visitados[y, x] = True
        xs = []
        ys = []

        while pilha:
            cy, cx = pilha.pop()
            xs.append(cx)
            ys.append(cy)

            for ny in range(max(0, cy - 1), min(altura, cy + 2)):
                for nx in range(max(0, cx - 1), min(largura, cx + 2)):
                    if mascara[ny, nx] and not visitados[ny, nx]:
                        visitados[ny, nx] = True
                        pilha.append((ny, nx))

        componentes.append(
            {
                "x0": min(xs),
                "y0": min(ys),
                "x1": max(xs) + 1,
                "y1": max(ys) + 1,
                "area": len(xs),
            }
        )

    return componentes


def detectar_icones(imagem):
    rgb = np.asarray(imagem.convert("RGB"))
    vermelho = rgb[:, :, 0]
    verde = rgb[:, :, 1]
    azul = rgb[:, :, 2]

    mascaras = {
        "propria": (verde > 145) & (vermelho < 95) & (azul < 110),
        "impropria": (vermelho > 160) & (verde < 100) & (azul < 110),
    }
    icones = []

    for status, mascara in mascaras.items():
        for comp in componentes_conectados(mascara):
            largura = comp["x1"] - comp["x0"]
            altura = comp["y1"] - comp["y0"]

            if comp["area"] < 40 or largura < 6 or altura < 6:
                continue

            # Ignora logos e textos coloridos do rodape.
            if comp["y0"] > imagem.height * 0.90:
                continue

            # Ignora os icones da legenda, que ficam no canto inferior esquerdo.
            if comp["x0"] < imagem.width * 0.35 and comp["y0"] > imagem.height * 0.72:
                continue

            icones.append({**comp, "status": status})

    return sorted(fundir_icones_proximos(icones), key=lambda item: (item["y0"], item["x0"]))


def fundir_icones_proximos(icones):
    fundidos = []

    for icone in sorted(icones, key=lambda item: item["area"], reverse=True):
        cx = (icone["x0"] + icone["x1"]) / 2
        cy = (icone["y0"] + icone["y1"]) / 2
        existente = None

        for candidato in fundidos:
            ccx = (candidato["x0"] + candidato["x1"]) / 2
            ccy = (candidato["y0"] + candidato["y1"]) / 2
            if icone["status"] == candidato["status"] and abs(cx - ccx) < 25 and abs(cy - ccy) < 25:
                existente = candidato
                break

        if existente is None:
            fundidos.append(dict(icone))
            continue

        existente["x0"] = min(existente["x0"], icone["x0"])
        existente["y0"] = min(existente["y0"], icone["y0"])
        existente["x1"] = max(existente["x1"], icone["x1"])
        existente["y1"] = max(existente["y1"], icone["y1"])
        existente["area"] += icone["area"]

    return fundidos


def recortar_texto_proximo(imagem, icone):
    margem = 12
    largura_texto = 260
    altura_texto = 80
    x0 = max(0, icone["x0"] - 15)
    y0 = max(0, icone["y0"] - altura_texto // 2)
    x1 = min(imagem.width, icone["x1"] + largura_texto)
    y1 = min(imagem.height, icone["y1"] + altura_texto)

    if x1 - x0 < 40 or y1 - y0 < 20:
        return ""

    recorte = imagem.crop((x0, y0, x1 + margem, y1 + margem))
    return executar_ocr(recorte)


def extrair_titulo_e_cidade(imagem):
    recorte = imagem.crop((int(imagem.width * 0.35), 0, imagem.width, int(imagem.height * 0.28)))
    texto = executar_ocr(recorte)
    praias, cidade = interpretar_titulo_mapa(texto)
    return texto, praias, cidade


def extrair_dados():
    registros = []

    with pdfplumber.open(ARQUIVO_PDF) as pdf:
        for indice, pagina in enumerate(pdf.pages, start=1):
            texto_pdf = normalizar_texto(pagina.extract_text() or "")
            data_inicio, data_fim = extrair_periodo(texto_pdf)

            if indice == 1:
                continue

            imagem = pagina.to_image(resolution=RESOLUCAO).original
            titulo_mapa, praias_mapa, cidade = extrair_titulo_e_cidade(imagem)
            icones = detectar_icones(imagem)

            for numero_ponto, icone in enumerate(icones, start=1):
                largura_icone = icone["x1"] - icone["x0"]
                altura_icone = icone["y1"] - icone["y0"]
                texto_proximo = recortar_texto_proximo(imagem, icone)

                registros.append(
                    {
                        "pagina": indice,
                        "ponto_na_pagina": numero_ponto,
                        "periodo_inicio": data_inicio,
                        "periodo_fim": data_fim,
                        "cidade": cidade,
                        "praias_mapa": praias_mapa,
                        "titulo_mapa_ocr": titulo_mapa,
                        "nome_praia_ou_ponto_ocr": texto_proximo,
                        "situacao": icone["status"],
                        "icone": "verde" if icone["status"] == "propria" else "vermelho",
                        "icone_x": round((icone["x0"] + largura_icone / 2) / imagem.width, 4),
                        "icone_y": round((icone["y0"] + altura_icone / 2) / imagem.height, 4),
                        "observacao": "" if texto_proximo else "OCR nao identificou texto; revise pelo mapa.",
                    }
                )

    return pd.DataFrame(registros)


def main():
    if not ARQUIVO_PDF.exists():
        print(f"Erro: o arquivo '{ARQUIVO_PDF}' nao foi encontrado na pasta.")
        return

    print(f"Lendo o arquivo: {ARQUIVO_PDF}...")
    df = extrair_dados()
    df.to_csv(NOME_CSV, index=False, encoding="utf-8")

    print("\n--- Previa dos dados ---")
    print(df.head(20).to_string(index=False))
    print(f"\nSucesso! Arquivo salvo como: {NOME_CSV}")

    if not obter_leitor_ocr():
        print(
            "\nAviso: easyocr nao esta instalado na venv. "
            "Instale com: .venv/bin/pip install easyocr"
        )


if __name__ == "__main__":
    main()