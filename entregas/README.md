# Projeto da Disciplina BD - Balneabilidade do litoral paraibano

## Entregas

### Marco C1 - Escopo + fonte escolhida + dicionário de dados

#### Escopo

**Problema de dados**

O monitoramento de balneabilidade do litoral paraibano é publicado pela SUDEMA em relatórios semanais em PDF, com mapas e pins de status por ponto de coleta. Para cidadãos, gestores públicos e pesquisadores, responder perguntas do tipo “esta praia está própria hoje?”, “quais trechos estão impróprios na última rodada?” ou “como o status evoluiu nas últimas semanas?” exige abrir vários arquivos manualmente, sem consulta unificada nem comparação temporal simples.

**Solução proposta**

1. **Extração (bronze):** scraping da página pública da SUDEMA, download e versionamento local dos PDFs (`bd_praias/index.py` → `pdfs_sudema/`).
2. **Transformação (silver):** extração estruturada do conteúdo dos mapas (pontos de coleta, status visual, período) via modelo multimodal, gerando CSV por relatório (`bd_praias/process_all.py` → `data_csv/`).
3. **Carga (gold, C3):** transformação dos CSVs em documentos MongoDB alinhados ao modelo conceitual (C2), com índices para as consultas definidas abaixo.
4. **Consumo (C4):** aplicação web que executa consultas reais no MongoDB (filtros, agregações, visualizações). Como extensão desejada, um assistente em linguagem natural pode interpretar perguntas do usuário, mapear para consultas permitidas e devolver texto e gráficos no chat, com cache em memória de respostas repetidas (sem persistir histórico de conversas nesta fase).

**Por que documentos / MongoDB**

Cada edição semanal do relatório forma um agregado natural: metadados da rodada (número, ano, período de amostragem) e um array de pontos de coleta lidos em conjunto nas análises. O volume é moderado, o esquema pode evoluir se o layout dos PDFs mudar, e o padrão de acesso é consultas analíticas por cidade, praia, status e semana — não transações ACID entre muitas entidades normalizadas. Um modelo relacional exigiria várias tabelas e joins para reproduzir o que um único documento `Relatório` com `pontosColeta` embutidos entrega em uma leitura; o MongoDB simplifica esse padrão e suporta agregações (`$match`, `$unwind`, `$group`) diretamente sobre arrays embutidos.

#### Fonte escolhida

| Aspecto | Descrição |
|--------|-----------|
| **Origem** | Superintendência de Administração do Meio Ambiente da Paraíba (SUDEMA) — relatórios de qualidade das águas balneares |
| **URL** | https://sudema.pb.gov.br/qualidade-do-ambiente/qualidade-dos-mares |
| **Forma de acesso** | Web scraping da tabela HTML de relatórios + download HTTP dos links “Acessar” (PDF). Não há API oficial documentada |
| **Formato na fonte** | PDF (mapas por página a partir da página 2; página 1 institucional) |
| **Licença / uso** | Dados públicos de interesse ambiental; uso acadêmico com citação da SUDEMA como fonte original |
| **LGPD** | Não há dados pessoais identificáveis nos relatórios analisados — apenas municípios, praias, referências geográficas de pontos de coleta e classificação de balneabilidade. Não se aplica tratamento de dados pessoais; declaração explícita de ausência de PII |
| **Idioma** | Português (pt-BR) |
| **Frequência de atualização** | Publicação semanal de novas edições na página (ex.: “21º Relatório / 2026”) |
| **Volume observado no repositório** | ~22 PDFs em `pdfs_sudema/`; ~21 CSVs estruturados em `data_csv/` (edições de 2026 processadas) |
| **Tamanho típico** | PDFs entre ~8 MB e ~17 MB por edição |
| **Pipeline atual no repositório** | Bronze: `index.py`; Silver: `process_all.py` (Google Gemini, chave via variável de ambiente) |

#### Dicionário de dados

Metadados estruturais dos campos extraídos na camada silver (CSV) e previstos na camada gold (MongoDB).

| Campo | Tipo | Descrição | Exemplo |
|-------|------|-----------|---------|
| `cidade` | string | Município indicado no cabeçalho do mapa da página | `JOÃO PESSOA - PB` |
| `nome_praia` | string | Nome(s) da(s) praia(s) em destaque no mapa; pode agrupar mais de uma praia na mesma página | `MANAÍRA E TAMBAÚ` |
| `trecho_referencia` | string | Localização do ponto de coleta (rua, foz, divisas, marco geográfico) | `Avenida Senador Ruy Carneiro` |
| `periodo_amostragem` | string | Intervalo de datas da rodada de coleta, como no rodapé do mapa | `25/05/2026 a 28/05/2026` |
| `status` | string (enum) | Classificação do pin no mapa: verde = próprio, vermelho = impróprio | `PRÓPRIO`, `IMPRÓPRIO` |
| `classificacao_100m` | string | Recomendação associada ao status (banho adequado ou aviso de 100 m) | `Adequado para banho` |
| `relatorio_id` | string | Identificador derivado do nome do arquivo PDF/CSV | `relatorio-21-2026` |
| `numero_relatorio` | int | Número da edição no ano (extraído do título na página) | `21` |
| `ano` | int | Ano da edição | `2026` |

**Regras de extração (silver)**

- Ignora a página 1 (conteúdo institucional).
- Uma linha por combinação praia + trecho/ponto quando a página contém múltiplos pontos.
- Campos com vírgula no texto são envolvidos em aspas duplas no CSV.

**Campos derivados planejados na transformação gold (C3)**

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `data_inicio` | date | Data inicial parseada de `periodo_amostragem` |
| `data_fim` | date | Data final parseada de `periodo_amostragem` |
| `slug_cidade` | string | Normalização para filtros (ex.: `joao-pessoa-pb`) |

#### Requisitos de dados (perguntas que a aplicação responde)

Lista de 5 a 8 perguntas que orientam modelagem (C2), consultas MongoDB (C3) e visualizações (C4):

1. Quais **pontos de coleta** estão **impróprios** no **relatório mais recente** disponível?
2. Em um **município** escolhido (ex.: João Pessoa), como o **status de cada trecho** evoluiu **semana a semana** ao longo de 2026?
3. Qual **município** concentra o **maior número de pontos impróprios** na rodada mais recente?
4. A praia **Manaíra/Tambaú** (ou outra praia selecionada) esteve imprópria em **quantas edições** de relatório em 2026?
5. Qual a **distribuição** de pontos **próprios vs impróprios** por **edição semanal** (visão agregada do litoral)?
6. Quais trechos aparecem como **impróprios em duas ou mais semanas consecutivas**?
7. Liste todos os pontos **impróprios** em **Pitimbú** (ou município filtrado) nas últimas N edições disponíveis.
8. Para um **trecho específico** (ex.: Seixas — Rua dos Pescadores), em quais **semanas** ele foi classificado como impróprio e em quais como próprio?

---

### Marco C2 - Modelo conceitual UML + mapeamento para MongoDB

### Marco C3 - Pipeline ETL carregando no MongoDB + consultas

### Marco C4 - Aplicação de visualização + apresentação + registro de software
