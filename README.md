# Mineração de comentários no Clássico Mineiro

Projeto da disciplina **Técnicas para Análise de Mídias Sociais** sobre comentários públicos do YouTube relacionados a dez clássicos oficiais entre Atlético-MG e Cruzeiro, disputados entre fevereiro de 2025 e setembro de 2026.

> **Questão de pesquisa:** como o resultado dos clássicos está associado ao sentimento, aos assuntos discutidos e à estrutura das interações entre usuários no YouTube?

A entrega está consolidada em [`analysis.ipynb`](analysis.ipynb), notebook executado que reúne metodologia, tratamento dos dados, validações, análise de redes, NLP, visualizações, limitações e conclusão. Os dados intermediários e os resultados exportados também estão versionados para permitir a inspeção sem repetir a coleta na API ou a inferência do modelo.

## Principais resultados

- Foram analisados **58.910 comentários e respostas**, provenientes de 100 vídeos associados a 10 partidas.
- A proporção de comentários negativos passou de aproximadamente **31,1% no pré-jogo para 50,0% no pós-jogo**.
- Empates apresentaram a maior negatividade observada: cerca de **65,9%** de comentários negativos.
- A rede agregada contém **40.372 usuários** e **12.179 relações direcionadas** após o tratamento usado nas métricas; sua estrutura é esparsa, fragmentada e dissortativa.
- Menções a jogadores e treinadores aparecem em contextos mais negativos quando suas equipes não vencem, mas os resultados representam associações exploratórias, não relações causais.

## Estrutura do repositório

```text
.
├── analysis.ipynb                  análise completa e relatório principal
├── config/
│   └── settings.py                 parâmetros e caminhos do projeto
├── data/
│   ├── raw/                        partidas, vídeos e comentários coletados
│   ├── processed/                  bases tratadas, NLP e rede
│   ├── reference/                  entidades, aliases e participantes por jogo
│   └── validation/                 amostra cega para validação de sentimento
├── outputs/
│   ├── figures/                    visualizações exportadas
│   ├── networks/                   redes em GEXF e GraphML
│   └── tables/                     métricas e tabelas da análise
├── src/
│   ├── matches/                    snapshot auditável das partidas
│   ├── youtube/                    busca de vídeos e coleta de comentários
│   └── nlp/                        geração da amostra de validação manual
├── tests/                          testes de código e integridade da entrega
├── .env.example                    exemplo de configuração local
└── requirements.txt               dependências do ambiente
```

## Como consultar a entrega

Para apenas avaliar o trabalho, abra `analysis.ipynb` no GitHub, Jupyter ou VS Code. Todas as células estão executadas e os resultados estão salvos no próprio notebook.

Os principais produtos também podem ser consultados diretamente:

- `outputs/figures/`: gráficos prontos para visualização;
- `outputs/tables/`: resultados quantitativos em CSV/JSON;
- `outputs/networks/`: redes para NetworkX ou Gephi;
- `outputs/tables/nlp_metadata.json`: modelo, revisão e parâmetros da etapa de NLP;
- `outputs/collection_summary.json`: resumo e parâmetros da coleta.

## Instalação

Recomenda-se Python **3.11 ou 3.12**. Na raiz do repositório:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Para abrir o relatório:

```bash
jupyter lab analysis.ipynb
```

Os caminhos usados no notebook são relativos à raiz do projeto. Portanto, inicie o Jupyter nesse diretório.

## Reprodução e validação

Os dados e checkpoints necessários à análise já estão incluídos. Para validar o código e a consistência dos artefatos:

```bash
pytest -q
```

Para executar novamente todo o notebook, use **Run All** no Jupyter. A revisão exata do modelo de sentimento está fixada no notebook e registrada em `outputs/tables/nlp_metadata.json`. O checkpoint existente evita repetir a inferência dos 58.910 registros; se ele for removido, a primeira execução precisará baixar o modelo do Hugging Face e poderá levar bastante tempo em CPU.

### Refazer a coleta do YouTube

Essa etapa é opcional para avaliar a entrega. Ela depende de credenciais e pode produzir um snapshot diferente, pois vídeos, comentários e métricas da plataforma mudam ao longo do tempo.

```bash
cp .env.example .env
# edite .env e informe YOUTUBE_API_KEY ou credenciais OAuth

python -m src.matches.collect_matches
python -m src.youtube.search_videos
python -m src.youtube.collect_comments
```

A coleta é incremental, deduplica por `comment_id` e pode ser retomada após interrupções. A busca de vídeos reconstrói `videos.csv` de forma atômica. Respostas são obtidas pelo endpoint paginado `comments.list`, pois as respostas embutidas em `commentThreads.list` podem estar incompletas.

## Metodologia resumida

### Partidas e vídeos

`collect_matches.py` materializa um snapshot das dez partidas oficiais verificadas em 9 de setembro de 2026. As fontes permanecem registradas em `data/raw/matches.csv`. A seleção de vídeos usa consultas por confronto, data e competição, restringe a janela a três dias antes/depois do jogo, exige referência aos dois clubes e classifica os candidatos por relevância e engajamento.

### Período dos comentários

O período analítico é calculado pelo horário de cada comentário em relação ao início da partida: `pre_game`, `during_game` ou `post_game`. O término é estimado por `MATCH_DURATION_MINUTES` (120 minutos por padrão). As comparações principais usam pré/pós-jogo dentro da janela configurada.

### Conteúdo e redes

O notebook preserva o texto original, cria uma versão normalizada, classifica sentimento com `cardiffnlp/twitter-xlm-roberta-base-sentiment`, identifica temas por regras multilabel e reconhece entidades por aliases específicos de cada partida. A rede dirigida conecta o autor de uma resposta ao autor do comentário principal; pesos representam respostas repetidas no mesmo contexto.

### Validação manual

`src/nlp/create_validation_sample.py` gera uma amostra estratificada e cega de 600 comentários:

```bash
python -m src.nlp.create_validation_sample
```

A planilha de anotação fica em `data/validation/sentiment_manual_600.xlsx`; a chave automática permanece separada em `sentiment_validation_key.csv`.

## Configuração

As variáveis disponíveis estão documentadas em `.env.example`. Entre elas:

- `PRE_GAME_DAYS` e `POST_GAME_DAYS`: janela da coleta/análise;
- `MATCH_DURATION_MINUTES`: duração estimada da partida;
- `MAX_*_VIDEOS_PER_MATCH`: limite de vídeos por período;
- `MAX_COMMENTS_PER_VIDEO`: limite opcional de comentários;
- `ANONYMIZE_USERS` e `ANONYMIZATION_SALT`: pseudonimização dos IDs;
- `REQUEST_TIMEOUT` e `REQUEST_RETRIES`: comportamento das requisições.

`.env`, `secrets.json` e `token.json` são ignorados pelo Git e não devem ser enviados.

## Ética, privacidade e limitações

Os IDs de canais foram pseudonimizados com SHA-256 durante a coleta. O snapshot acadêmico preserva textos e nomes públicos de exibição para auditoria, portanto **não deve ser redistribuído como uma base pública sem uma etapa adicional de minimização e revisão ética**. Nunca use os dados para identificar usuários ou produzir rankings individuais.

Comentários do YouTube são uma amostra autoselecionada e não representam toda a torcida. A preferência clubística dos usuários é desconhecida; seleção de vídeos, algoritmos da plataforma e diferenças de volume entre partidas influenciam os resultados. Sentimento automático, temas e entidades também estão sujeitos a erro, sobretudo com sarcasmo, ironia, provocações e linguagem do futebol. As conclusões são observacionais e não demonstram causalidade.


