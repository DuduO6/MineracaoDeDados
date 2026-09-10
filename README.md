# Mineração de comentários no Clássico Mineiro

Projeto reproduzível da disciplina **Técnicas para Análise de Mídias Sociais**. A questão central é: *como o resultado dos clássicos entre Atlético-MG e Cruzeiro influencia o sentimento, os assuntos discutidos e a estrutura de interação entre torcedores no YouTube?*

Esta entrega implementa as Fases 1–4: configuração, identificação auditável dos dez jogos oficiais mais recentes, seleção de vídeos e coleta paginada de comentários/respostas. Processamento, redes, NLP e visualizações permanecem deliberadamente para as fases seguintes.

## Estrutura

```text
config/settings.py                 configurações por ambiente
data/raw/matches.csv               partidas e fontes
data/raw/videos.csv                vídeos selecionados
data/raw/comments.csv              comentários originais e respostas
src/matches/collect_matches.py     snapshot verificável de partidas
src/youtube/youtube_client.py      cliente HTTP, paginação e retentativas
src/youtube/search_videos.py       busca, filtros, ranking e seleção
src/youtube/collect_comments.py    coleta incremental e retomável
outputs/collection_summary.json    metadados gerados durante a execução
tests/                             testes sem consumir quota
```

## Instalação

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edite `.env` e substitua `YOUR_API_KEY_HERE` por uma chave da **YouTube Data API v3**. Como alternativa, remova essa linha e coloque credenciais OAuth de aplicativo instalado em `secrets.json`; o primeiro comando abrirá o consentimento do Google e criará `token.json`. Esses arquivos nunca devem ser versionados. Variáveis opcionais incluem `PRE_GAME_DAYS`, `POST_GAME_DAYS`, `MAX_PRE_GAME_VIDEOS_PER_MATCH`, `MAX_POST_GAME_VIDEOS_PER_MATCH`, `MAX_COMMENTS_PER_VIDEO`, `ANONYMIZE_USERS` e `ANONYMIZATION_SALT`. Vazio em `MAX_COMMENTS_PER_VIDEO` significa coletar tudo. Para publicação, defina um salt secreto e estável.

## Execução

Na raiz do repositório:

```bash
python -m src.matches.collect_matches
python -m src.youtube.search_videos
python -m src.youtube.collect_comments
pytest
```

A coleta de comentários grava cada registro imediatamente, deduplica por `comment_id` e pode ser executada novamente após interrupção. A busca de vídeos reconstitói `videos.csv` de forma atômica. Respostas são consultadas pelo endpoint paginado `comments.list`, pois as respostas embutidas em `commentThreads.list` não são necessariamente completas. Falhas transitórias usam backoff exponencial; vídeos com comentários desativados e demais erros entram no resumo.

## Identificação dos jogos

`collect_matches.py` contém uma fotografia conferida em **2026-09-09**, ordenada do jogo mais recente para o mais antigo e sem o amistoso FC Series de janeiro de 2025. Cada linha conserva sua URL verificável; predominam relatos oficiais do Clube Atlético Mineiro, e a partida de 01/09/2026 também usa a CBF. O arquivo inclui `match_datetime` além dos campos pedidos, com horário de Brasília e deslocamento UTC, para distinguir objetivamente publicações no dia do jogo.

O módulo não raspa silenciosamente uma página sujeita a mudanças: ele valida e materializa o snapshot auditável. Antes de reproduzir o estudo em data posterior, revise a lista e as fontes, pois novos clássicos podem alterar os dez mais recentes.

## Período do vídeo e período do comentário

`video_period` descreve quando o vídeo foi publicado. A análise usa `comment_period`, calculado pela data/hora de cada comentário em relação a `match_datetime`: antes do início (`pre_game`), entre o início e o término estimado (`during_game`) e depois do término (`post_game`). A duração é configurada por `MATCH_DURATION_MINUTES` (120 por padrão), pois a API não fornece o instante do apito final. `within_comment_window` identifica comentários entre três dias antes e três dias depois do término estimado; comparações principais excluem `during_game` e registros fora dessa janela.

## Metodologia de seleção de vídeos

Para cada jogo são feitas consultas com mandante/visitante, data, competição e termos de pré/pós-jogo. A API limita os resultados à janela de três dias antes e depois. O código exige referências a ambos os clubes, rejeita termos associados a videogame, base, feminino, histórico e Shorts, remove duplicatas pelo ID e pontua relevância direta, termos do clássico, visualizações e comentários. São mantidos no máximo cinco vídeos por período e partida. A publicação é comparada ao horário real do jogo; título não decide sozinho o período.

Essa é uma amostragem orientada à relevância, não uma amostra aleatória. A consulta responsável por encontrar cada vídeo fica registrada em `search_query`.

## Formatos dos CSVs

Exemplo abreviado de partida:

```csv
match_id,match_date,match_datetime,competition,season,home_team,away_team,home_score,away_score,winner
2026-09-01-cam-cru,2026-09-01,2026-09-01T21:00:00-03:00,Copa do Brasil - quartas de final (volta),2026,Atlético-MG,Cruzeiro,2,1,Atlético-MG
```

Exemplo de vídeo:

```csv
video_id,match_id,title,...,published_at,period,views,likes,comment_count,url,search_query
abc123,2026-09-01-cam-cru,Título do vídeo,...,2026-09-01T23:10:00Z,post_game,1000,50,20,https://www.youtube.com/watch?v=abc123,consulta usada
```

Exemplo de resposta:

```csv
comment_id,video_id,match_id,author_channel_id,author_name,text,...,is_reply,parent_comment_id,parent_author_channel_id,period,team_result_context
r1,abc123,2026-09-01-cam-cru,hash,Usuário,Texto,...,true,c1,hash_do_autor_pai,post_game,atletico_win
```

O texto original é preservado. Com `ANONYMIZE_USERS=True` (padrão), identificadores de canal são convertidos em SHA-256; nomes públicos ainda existem no arquivo bruto para auditoria e deverão ser removidos dos produtos destinados à publicação.

## Limitações dos dados

Comentários do YouTube não representam toda a torcida: são uma amostra autoselecionada, e não é possível saber com segurança para qual clube cada usuário torce. A escolha dos vídeos e os algoritmos da plataforma influenciam o público e as interações; vídeos diferentes atraem públicos diferentes. Comentários podem ser removidos, contas excluídas e comentários desativados. O volume varia muito entre partidas. Futuras classificações automáticas de sentimento estarão sujeitas a erros, sobretudo com ironia e sarcasmo.

O projeto não coleta e-mail, localização privada nem dados pessoais desnecessários. Ainda assim, comentários públicos podem conter autodeclarações pessoais; a etapa de publicação deve aplicar minimização adicional e nunca divulgar nomes em rankings.
