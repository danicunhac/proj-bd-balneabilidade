# proj-bd-balneabilidade

## Sudema Scrapping Bronze

Este script faz scraping da página de qualidade das praias da Sudema e baixa todos os PDFs com os relatórios disponíveis.

## O que o script faz

- Acessa a página principal de relatórios de balneabilidade da Sudema.
- Localiza a tabela com os relatórios e extrai os links de download em PDF.
- Baixa cada PDF para a pasta `pdfs_sudema`.
- Garante nomes de arquivo seguros e trata recomeço de download em caso de falha.

## Como usar

1. Instale as dependências:

```bash
cd sudema-scrapping-bronze
pip install -r requirements.txt
```

2. Execute o script:

```bash
python main.py
```

3. Os PDFs serão salvos em `sudema-scrapping-bronze/pdfs_sudema`.

## Obtenção dos dados com IA

Após baixar os PDFs, podemos usar IA para extrair e estruturar os dados dos relatórios. Um exemplo de prompt para a análise dos relatórios de balneabilidade é:

> Você é um assistente especialista em análise de dados e relatórios ambientais. Analise o documento em PDF do Relatório de Balneabilidade da SUDEMA que acabei de enviar. A partir da página 2, cada página representa o mapa de monitoramento de uma ou mais praias. Sua tarefa é extrair as informações de cada ponto de coleta e estruturá-las estritamente no formato de uma tabela Markdown. Para cada página/mapa do relatório, identifique e extraia:
> 1. **Cidade**: O município listado no cabeçalho de cada mapa (ex: MATARACA - PB, CONDE - PB).
> 2. **Nome da Praia**: O nome ou nomes das praias em destaque no topo da página.
> 3. **Trecho / Ponto de Referência**: O local exato, ruas, foz de rios, divisas ou marcos geográficos descritos no mapa que indicam onde a coleta foi feita.
> 4. **Período de Amostragem**: O intervalo de datas de coleta que aparece na parte inferior de cada mapa (ex: 25/05/2026 a 28/05/2026).
> 5. **Status**: Analise visualmente o ícone/pin de localização presente no mapa e classifique estritamente assim:
>    - Se o ícone for VERDE, classifique como "PRÓPRIO".
>    - Se o ícone for VERMELHO, classifique como "IMPRÓPRIO".
> 6. **Classificação dos 100m**: Se o ponto estiver "PRÓPRIO", preencha com "Adequado para banho". Se estiver "IMPRÓPRIO", adicione o aviso: "Evitar o banho no raio de 100 metros à direita e à esquerda deste ponto".
>
> Formate a saída estritamente como uma tabela com o seguinte cabeçalho:
> | Cidade | Nome da Praia | Trecho / Ponto de Referência | Período de Amostragem | Status | Classificação dos 100m |
> Regras Adicionais:
> - Ignore a página 1 (introdução institucional) na listagem da tabela.
> - Se uma única página contiver mais de uma praia ou mais de um ponto de referência mapeado, crie uma linha separada na tabela para cada um deles para garantir a precisão.
> - Seja extremamente fiel aos nomes das ruas, períodos e referências textuais presentes em cada mapa.
> retorne em CSV

## Observações

- A extração de texto ou informações estruturadas do PDF pode ser feita com ferramentas de OCR/IA específicas após o download.
- Este repositório cuida apenas do scrapping e do download dos arquivos PDF.
