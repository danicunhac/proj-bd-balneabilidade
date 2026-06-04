"""
Processa todos os PDFs de pdfs_sudema e salva os CSVs em data_csv.
Pula PDFs que já possuem CSV correspondente em data_csv.
"""

import os
import sys
import time
from google import genai
from google.genai import types

# ── Configuração ──────────────────────────────────────────────
API_KEY = "AQ.xxxxxxxxxxxxxxxxxxxxxxxxx"
MODEL = "gemini-flash-latest"

PROMPT = """
Você é um assistente especialista em análise de dados e relatórios ambientais.
Analise o documento em PDF do Relatório de Balneabilidade da SUDEMA que acabei de enviar.
A partir da página 2, cada página representa o mapa de monitoramento de uma ou mais praias.
Sua tarefa é extrair as informações de cada ponto de coleta e estruturá-las estritamente
no formato CSV (separado por vírgula).

Para cada página/mapa do relatório, identifique e extraia:

- Cidade: O município listado no cabeçalho de cada mapa (ex: MATARACA - PB, CONDE - PB).
- Nome da Praia: O nome ou nomes das praias em destaque no topo da página.
- Trecho / Ponto de Referência: O local exato, ruas, foz de rios, divisas ou marcos
  geográficos descritos no mapa que indicam onde a coleta foi feita.
- Período de Amostragem: O intervalo de datas de coleta que aparece na parte inferior
  de cada mapa (ex: 25/05/2026 a 28/05/2026).
- Status: Analise visualmente o ícone/pin de localização presente no mapa e classifique
  estritamente assim:
    - Se o ícone for VERDE, classifique como "PRÓPRIO".
    - Se o ícone for VERMELHO, classifique como "IMPRÓPRIO".
- Classificação dos 100m: Se o ponto estiver "PRÓPRIO", preencha com "Adequado para banho".
  Se estiver "IMPRÓPRIO", adicione o aviso: "Evitar o banho no raio de 100 metros à direita
  e à esquerda deste ponto".

Retorne APENAS o conteúdo CSV puro, sem blocos de código markdown, sem explicações.
O cabeçalho deve ser:
Cidade,Nome da Praia,Trecho / Ponto de Referência,Período de Amostragem,Status,Classificação dos 100m

Regras Adicionais:
- Ignore a página 1 (introdução institucional) na listagem.
- Se uma única página contiver mais de uma praia ou mais de um ponto de referência mapeado,
  crie uma linha separada para cada um deles para garantir a precisão.
- Seja extremamente fiel aos nomes das ruas, períodos e referências textuais presentes
  em cada mapa.
- Use aspas duplas para envolver campos que contenham vírgulas.
"""

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_DIR = os.path.join(BASE_DIR, "pdfs_sudema")
CSV_DIR = os.path.join(BASE_DIR, "data_csv")


def csv_name_for_pdf(pdf_filename: str) -> str:
    """Converte 'relatorio-01-2026.pdf' → 'relatorio-01-2026.csv'"""
    return os.path.splitext(pdf_filename)[0] + ".csv"


def process_pdf(client, pdf_path: str, output_path: str):
    """Envia um PDF ao Gemini e salva o CSV resultante."""
    print(f"\n📄 Processando: {os.path.basename(pdf_path)}")
    file_size = os.path.getsize(pdf_path)
    print(f"   Tamanho: {file_size / (1024 * 1024):.1f} MB")

    # Upload
    print("   ☁️  Upload...")
    uploaded_file = client.files.upload(
        file=pdf_path,
        config=types.UploadFileConfig(mime_type="application/pdf"),
    )

    # Aguarda processamento
    while uploaded_file.state.name == "PROCESSING":
        print("   ⏳ Processando...")
        time.sleep(3)
        uploaded_file = client.files.get(name=uploaded_file.name)

    if uploaded_file.state.name == "FAILED":
        print("   ❌ Falhou no processamento. Pulando.")
        return False

    # Gera resposta
    print("   🤖 Analisando com Gemini...")
    max_retries = 5
    for attempt in range(1, max_retries + 1):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_uri(
                                file_uri=uploaded_file.uri,
                                mime_type="application/pdf",
                            ),
                            types.Part.from_text(text=PROMPT),
                        ],
                    )
                ],
            )
            break
        except Exception as e:
            if "429" in str(e) and attempt < max_retries:
                wait = 45 * attempt
                print(f"   ⚠️  Rate limit. Tentativa {attempt}/{max_retries}. Aguardando {wait}s...")
                time.sleep(wait)
            else:
                print(f"   ❌ Erro: {e}")
                return False

    csv_content = response.text.strip()

    # Remove blocos markdown residuais
    if csv_content.startswith("```"):
        lines = csv_content.split("\n")
        csv_content = "\n".join(lines[1:-1])

    # Salva
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(csv_content)

    n_lines = len(csv_content.splitlines()) - 1
    print(f"   ✅ Salvo: {os.path.basename(output_path)}  ({n_lines} linhas)")

    # Limpa arquivo do servidor
    try:
        client.files.delete(name=uploaded_file.name)
    except Exception:
        pass

    return True


def main():
    # Cria pasta data_csv se não existir
    os.makedirs(CSV_DIR, exist_ok=True)
    print(f"📁 Pasta de saída: {CSV_DIR}")

    # Lista PDFs
    pdfs = sorted(
        f for f in os.listdir(PDF_DIR) if f.lower().endswith(".pdf")
    )
    print(f"📋 Total de PDFs encontrados: {len(pdfs)}")

    # Filtra os que já possuem CSV
    to_process = []
    for pdf in pdfs:
        csv_file = csv_name_for_pdf(pdf)
        csv_path = os.path.join(CSV_DIR, csv_file)
        if os.path.isfile(csv_path):
            print(f"   ⏭️  Já existe: {csv_file}")
        else:
            to_process.append(pdf)

    if not to_process:
        print("\n🎉 Todos os PDFs já foram processados! Nada a fazer.")
        return

    print(f"\n🔄 PDFs a processar: {len(to_process)}")

    # Inicializa cliente Gemini
    client = genai.Client(api_key=API_KEY)

    ok = 0
    fail = 0
    for i, pdf in enumerate(to_process, 1):
        print(f"\n── [{i}/{len(to_process)}] ──────────────────────────────────")
        pdf_path = os.path.join(PDF_DIR, pdf)
        csv_file = csv_name_for_pdf(pdf)
        csv_path = os.path.join(CSV_DIR, csv_file)

        success = process_pdf(client, pdf_path, csv_path)
        if success:
            ok += 1
        else:
            fail += 1

        # Pausa entre requisições para evitar rate limit
        if i < len(to_process):
            print("   ⏸️  Aguardando 10s antes do próximo...")
            time.sleep(10)

    print(f"\n{'='*50}")
    print(f"✅ Processados com sucesso: {ok}")
    if fail:
        print(f"❌ Falhas: {fail}")
    print(f"📁 CSVs salvos em: {CSV_DIR}")


if __name__ == "__main__":
    main()
