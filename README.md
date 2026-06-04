# proj-bd-balneabilidade

Este repositório reúne scripts para coletar e processar relatórios de balneabilidade da SUDEMA.

## Estrutura principal

- `bd_praias/index.py`
  - Faz scraping na página de qualidade das praias da SUDEMA.
  - Encontra os relatórios publicados e baixa os arquivos PDF.
  - Salva os PDFs em `bd_praias/pdfs_sudema/`.

- `bd_praias/process_all.py`
  - Processa os PDFs baixados e converte o conteúdo em CSV.
  - Usa a API do Gemini / Google GenAI para extrair dados dos relatórios.

- `bd_praias/data_csv/`
  - Contém os dados silver extraídos dos relatórios em formato CSV.
  - Esses arquivos já são dados estruturados prontos para análise.

## Como usar

1. Instale as dependências necessárias:

```bash
cd bd_praias
pip install requests beautifulsoup4
```

2. Execute o scraper SUDEMA:

```bash
python index.py
```

3. Os PDFs serão baixados para:

```bash
bd_praias/pdfs_sudema/
```

4. Para gerar os CSVs na pasta de dados silver:

```bash
python process_all.py
```

> Antes de executar `process_all.py`, configure a chave `API_KEY` e o `MODEL` no arquivo se você usar a API do Gemini.

## O que significa cada camada de dados

- `pdfs_sudema/`
  - Dados raw/bronze: os relatórios originais baixados diretamente do site da SUDEMA.

- `data_csv/`
  - Dados silver: os CSVs gerados a partir dos PDFs, contendo informação estruturada extraída dos relatórios.

## Observações

- `index.py` é o responsável pelo scraping no site da SUDEMA e pelo download dos PDFs.
- `data_csv/` não contém os relatórios originais, mas sim o resultado do processamento convertido em CSV.
- Se precisar atualizar ou refazer o scraping, basta rodar `python index.py` novamente.

## Prompt para IA

Use este prompt quando for pedir à IA para extrair os dados do PDF em formato CSV:

> Você é um assistente especialista em análise de dados e relatórios ambientais. Analise o documento em PDF do Relatório de Balneabilidade da SUDEMA que acabei de enviar. A partir da página 2, cada página representa o mapa de monitoramento de uma ou mais praias. Sua tarefa é extrair as informações de cada ponto de coleta e estruturá-las estritamente no formato CSV (separado por vírgula).
>
> Para cada página/mapa do relatório, identifique e extraia:
>
> - Cidade: O município listado no cabeçalho de cada mapa (ex: MATARACA - PB, CONDE - PB).
> - Nome da Praia: O nome ou nomes das praias em destaque no topo da página.
> - Trecho / Ponto de Referência: O local exato, ruas, foz de rios, divisas ou marcos geográficos descritos no mapa que indicam onde a coleta foi feita.
> - Período de Amostragem: O intervalo de datas de coleta que aparece na parte inferior de cada mapa (ex: 25/05/2026 a 28/05/2026).
> - Status: Analise visualmente o ícone/pin de localização presente no mapa e classifique estritamente assim:
>   - Se o ícone for VERDE, classifique como "PRÓPRIO".
>   - Se o ícone for VERMELHO, classifique como "IMPRÓPRIO".
> - Classificação dos 100m: Se o ponto estiver "PRÓPRIO", preencha com "Adequado para banho". Se estiver "IMPRÓPRIO", adicione o aviso: "Evitar o banho no raio de 100 metros à direita e à esquerda deste ponto".
>
> Retorne APENAS o conteúdo CSV puro, sem blocos de código markdown, sem explicações.
> O cabeçalho deve ser:
> Cidade,Nome da Praia,Trecho / Ponto de Referência,Período de Amostragem,Status,Classificação dos 100m
>
> Regras adicionais:
> - Ignore a página 1 (introdução institucional) na listagem.
> - Se uma única página contiver mais de uma praia ou mais de um ponto de referência mapeado, crie uma linha separada para cada um deles.
> - Seja extremamente fiel aos nomes das ruas, períodos e referências textuais presentes em cada mapa.
