import os
import re
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# URL principal da Sudema onde ficam os links dos relatórios
URL_SUDEMA = "https://sudema.pb.gov.br/qualidade-do-ambiente/qualidade-dos-mares"

# Nome da pasta onde os PDFs serão salvos localmente
PASTA_DESTINO = "pdfs_sudema"

def nome_seguro(texto):
    match = re.search(r"(\d{1,2})\s*/\s*(\d{4})", texto)
    if match:
        numero, ano = match.groups()
        return f"relatorio-{int(numero):02d}-{ano}"

    texto = texto.strip().lower()
    texto = texto.replace("º", "").replace("°", "")
    texto = re.sub(r"[^\w\s-]", "", texto, flags=re.UNICODE)
    texto = re.sub(r"\s+", "-", texto)
    texto = re.sub(r"-+", "-", texto)
    return texto.strip("-")

def extrair_relatorios_da_tabela(soup):
    relatorios = []

    for tabela in soup.find_all("table"):
        primeira_linha = tabela.find("tr")
        if primeira_linha is None:
            continue

        cabecalhos = [
            coluna.get_text(" ", strip=True).lower()
            for coluna in primeira_linha.find_all(["th", "td"])
        ]

        if "relatório" not in " ".join(cabecalhos) or "arquivo" not in " ".join(cabecalhos):
            continue

        for linha in tabela.find_all("tr")[1:]:
            colunas = linha.find_all("td")
            if len(colunas) < 2:
                continue

            nome_relatorio = colunas[0].get_text(" ", strip=True)
            links = colunas[1].find_all("a", href=True)
            link_pdf = next(
                (link for link in links if link.get_text(" ", strip=True).lower() == "acessar"),
                links[0] if links else None
            )

            if not nome_relatorio or link_pdf is None:
                continue

            url_pdf = urljoin(URL_SUDEMA, link_pdf["href"])
            nome_arquivo = f"{nome_seguro(nome_relatorio)}.pdf"
            relatorios.append((nome_relatorio, url_pdf, nome_arquivo))

        if relatorios:
            break

    return relatorios

def baixar_pdf(url_pdf, caminho_arquivo_local, headers, tentativas=6):
    caminho_temporario = f"{caminho_arquivo_local}.part"

    for tentativa in range(1, tentativas + 1):
        try:
            headers_download = headers.copy()
            modo_arquivo = 'wb'

            if os.path.exists(caminho_temporario):
                bytes_baixados = os.path.getsize(caminho_temporario)
                headers_download["Range"] = f"bytes={bytes_baixados}-"
                modo_arquivo = 'ab'

            with requests.get(url_pdf, headers=headers_download, timeout=(15, 180), stream=True) as resposta_pdf:
                resposta_pdf.raise_for_status()

                if modo_arquivo == 'ab' and resposta_pdf.status_code != 206:
                    modo_arquivo = 'wb'

                with open(caminho_temporario, modo_arquivo) as f:
                    for bloco in resposta_pdf.iter_content(chunk_size=1024 * 64):
                        if bloco:
                            f.write(bloco)

            os.replace(caminho_temporario, caminho_arquivo_local)
            return True
        except requests.RequestException as e:
            if tentativa == tentativas:
                print(f"    [Erro] Falha ao baixar o arquivo {os.path.basename(caminho_arquivo_local)}: {e}")
                return False

            pausa = tentativa * 5
            print(f"    [!] Tentativa {tentativa} falhou. Tentando novamente em {pausa}s...")
            time.sleep(pausa)

    return False

def baixar_relatorios_sudema():
    # Cria a pasta de destino caso ela ainda não exista
    if not os.path.exists(PASTA_DESTINO):
        os.makedirs(PASTA_DESTINO)
        print(f"[+] Pasta '{PASTA_DESTINO}' criada com sucesso.")

    # Headers para simular um navegador comum e evitar bloqueios do servidor da Sudema
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    print("Acessando a página da Sudema para buscar relatórios...")
    try:
        resposta = requests.get(URL_SUDEMA, headers=headers, timeout=15)
        resposta.raise_for_status()
    except requests.RequestException as e:
        print(f"[Erro] Falha ao acessar o site: {e}")
        return

    # Realiza o parse do HTML da página
    soup = BeautifulSoup(resposta.text, 'html.parser')
    relatorios = extrair_relatorios_da_tabela(soup)

    print(f"Foram encontrados {len(relatorios)} relatórios na tabela da página.")

    # Loop para verificar e baixar os arquivos
    for nome_relatorio, url_pdf, nome_arquivo in relatorios:
        caminho_arquivo_local = os.path.join(PASTA_DESTINO, nome_arquivo)

        # Se o arquivo já existir na pasta local, o script ignora e vai para o próximo
        if os.path.exists(caminho_arquivo_local):
            print(f"[-] Arquivo já existente (ignorado): {nome_arquivo}")
            continue

        # Se o arquivo não existir, inicia o download
        print(f"[+] Baixando {nome_relatorio}: {nome_arquivo}...")
        baixou = baixar_pdf(url_pdf, caminho_arquivo_local, headers)

        if baixou:
            print(f"    -> Salvo com sucesso: {caminho_arquivo_local}")

if __name__ == "__main__":
    baixar_relatorios_sudema()
