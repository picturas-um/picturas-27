#import "../template.typ": *

#set heading(numbering: "A.1.")
#counter(heading).update(0)

= Instruções de execução

== Pré-requisitos e arranque

#tab([Pré-requisitos e arranque],
  tabela(
    colunas: (4cm, 1fr),
    [Passo], [Comando / observação],
    [Requisitos], [Docker 29.10.0 ou superior com Compose, Node 26.x, Python 3.14 (com `.venv`), `ffmpeg`/`ffprobe` no `PATH`, `typst` para compilar o relatório; cerca de 15 GB de disco e 8 GB de RAM para o build inicial (15–30 min)],
    [Obter a base], [`git clone git@github.com:simaoaraujo27/picturas-27.git && cd picturas-27 && git checkout 0523102`],
    [Arrancar a stack], [`docker compose up -d --build` (na primeira execução; `docker compose up -d` nas seguintes)],
    [Aceder], [Abrir `https://localhost:8080` e aceitar o certificado autoassinado; RabbitMQ em `http://localhost:15672` (`user` / `password`)],
    [Parar e limpar], [`docker compose down` (parar) ou `docker compose down -v --remove-orphans` (parar e apagar volumes, incluindo dados S3 e MongoDB)],
    [Atenção], [Se a instalação anterior usar o esquema S3 antigo (um _bucket_ por utilizador), executar `docker compose down -v --remove-orphans` uma vez antes do primeiro arranque],
  ),
)

`users`, `subscriptions` e `apiGateway` usam _bind mount_ e recarregam com nodemon. O frontend é um build de produção e os serviços Python não têm _bind mount_: após alterações, reconstruir o serviço (`docker compose up -d --build <service>`). Em particular, uma alteração em `projects/` exige `docker compose up -d --build projects`; um `restart` não basta. Depois de reconstruir o frontend, `docker compose restart nginx`.

== Repetir os testes

#tab([Comandos de teste],
  tabela(
    colunas: (4.8cm, 1fr),
    [Suíte], [Comando e resultado esperado],
    [Orquestrador (Node)], [`node --test projects/tests/` → 20/20],
    [Workers de vídeo (Python)], [`.venv/bin/python -m pytest Tools/video_effects/tests Tools/video_subtitles/tests Tools/video_frames/tests -q` → 53/53; exige `ffmpeg`/`ffprobe` no host, sem Docker],
    [Integração funcional], [`TEST_REGISTRY_PATH=/tmp/opencode/created-users.jsonl node --test --test-concurrency=1 tests/functional/integration/*.test.js` → 31/31],
    [Regressão], [Registar cada execução em `docs/REGRESSION_CHECKLIST.md` segundo `tests/TEST_EXECUTION_PROTOCOL.md`: acrescentar entrada ao histórico e atualizar apenas as células dos casos realmente exercitados],
  ),
)

O caso que cobre a regressão dos pipelines mistos é
`[VID-01,VID-04,PIPE-01] mixed border and subtitles preserve both effects`
em `tests/functional/integration/processing.test.js`. Usa `tests/fixtures/videos/speech.mp4` (320×240, 6 s, com fala e áudio AAC), aplica `border` de 4 px vermelho seguido de `subtitles` e verifica dimensão 328×248, `[245,2,2]` no canto, aumento do canal verde médio pelas legendas queimadas e presença da faixa de áudio. O vídeo adicional `samples/video/speech_mandela_20s.webm` é opcional para inspeção manual e não é necessário para a suíte.

== Repetir as medições (antes e depois)

#tab([Passos para repetir as medições do CAND-1],
  tabela(
    colunas: (4cm, 1fr),
    [Medição], [Procedimento],
    [Variantes], [Base: worktree destacado em `0523102` (`git worktree add --detach /tmp/opencode/base-radon 0523102`). Depois: revisão final `2ee32d7` na árvore de trabalho. Mesmo host, mesmos comandos],
    [Tamanho das imagens], [`docker images --format '{{.Repository}}:{{.Tag}}\t{{.Size}}'`; na base, `video_tool` = 1,70 GB; na variante final, `video_effects_tool` = 1,09 GB, `video_subtitles_tool` = 1,74 GB, `video_frames_tool` = 1,09 GB],
    [Estrutura e dependências], [`git ls-tree -r --name-only 0523102 Tools/video/`; `ls Tools/video_effects Tools/video_subtitles Tools/video_frames`; comparar os quatro `requirements.txt` e as filas em `rabbitMQ/definitions.json`],
    [Manutenibilidade], [`radon mi` (instalado no `.venv`) sobre `Tools/video/` na base e sobre os três diretórios na variante final. Todas as classificações são `A`, pelo que a métrica não distingue as variantes],
    [Progresso e isolamento], [Executar o caso de pipeline misto e recolher os eventos `video-progress` no socket (`8,16,25,33,42,50,50,90,100`); provocar falha no worker de legendas e verificar que os outros dois domínios concluem],
    [Benchmark de regressão system-wide], [`tests/performance/benchmark/executar.sh <commit> <directório-de-saída>` cria um worktree isolado, deteta automaticamente `video.py`/`video_queue` na base ou `video_effects.py`/`video_effects_queue` na variante final e grava ambiente, imagens, latências, débito, falhas e utilização de recursos. Usar `PERF_SCENARIOS`, `PERF_REPETITIONS` e `PERF_VIDEO` para escolher cenários, repetições e entrada. O worktree é removido no `trap` de saída],
    [Limpeza], [`git worktree remove /tmp/opencode/base-radon` quando as medições terminarem],
  ),
)

Os dados brutos da medição system-wide da base ficam em `tests/performance/resultados-desempenho-inicial/` e o resumo em `resultados-desempenho-inicial.md`; a comparação com um vídeo de 10 s a 720p está em `comparacao-videos/README.md`. O executor usa portas isoladas (`PERF_HTTPS_PORT=18443`, `PERF_RABBIT_PORT=18672`) e um nome de projeto Compose próprio, para não interferir com a stack de desenvolvimento.

== Compilar o relatório

Na pasta `fase2/relatorio/`: `typst compile --font-path fonts main.typ main.pdf`. Para rever alterações enquanto se escreve: `typst watch --font-path fonts main.typ`. Antes de entregar, `main.typ` deve ter `#mostrar-orientacoes.update(false)` e não podem restar marcadores de preenchimento.

= Glossário

#tabela(
  colunas: (4cm, 1fr),
  [Termo], [Definição],
  [Cenário de qualidade (`QS-nn`)], [Descrição verificável de um estímulo, do artefacto afetado, do ambiente, da resposta esperada e da respetiva medida; é a entrada das táticas e das decisões],
  [Evidência (`EV-nn`)], [Facto observável no código, na configuração ou num documento, com localização no commit de partida],
  [Hipótese (`H-nn`)], [Afirmação plausível ainda sem evidência direta, que deve ser confirmada por uma medição ou ensaio],
  [Candidato a RNF (`CAND-n`)], [Requisito não funcional escolhido para melhorar nesta fase, classificado segundo a ISO/IEC 25010],
  [Tática (`TAT-n`)], [Decisão de desenho que produz a resposta pretendida perante um estímulo; nesta fase, apenas de classe A (refactoring) ou B (alteração visível pretendida)],
  [Decisão arquitetural (`DA-n`)], [Registo ao estilo ADR com contexto, tática escolhida, estrutura, alternativas rejeitadas, consequências e implementação],
  [Radon MI], [Índice de manutenibilidade calculado pelo pacote Python `radon`; classes de `A` (melhor) a `C` (pior)],
  [Pipeline], [Lista ordenada de efeitos guardada no projeto e aplicada em lote a todos os media desse projeto],
  [Estágio], [Grupo de etapas consecutivas do pipeline executado por um worker; etapas de um mesmo estágio partilham uma descodificação/codificação],
  [`videoStages()`], [Função em `projects/utils/video.js` que converte o pipeline do projeto na sequência de estágios e determina o worker destinatário de cada um],
  [`project_queue`], [Fila de resposta dos workers para o orquestrador; é também usada para encadear o estágio seguinte com o resultado intermédio],
  [`ws_queue`], [Fila de eventos de progresso consumida pelo `wsGateway` e entregue ao browser por Socket.IO],
  [`base`/`span`], [Parâmetros que indicam a que parte da execução global corresponde o progresso de um estágio, permitindo agregação entre workers],
  [`Process`], [Registo de uma unidade de trabalho (media × efeito ou estágio) criado antes do despacho e concluído quando o resultado é publicado],
  [Estágios S3], [`src` (original), `out` (resultado), `preview` e `preview_cache`; os ficheiros não trafegam nas mensagens do RabbitMQ],
  [Pré-visualização], [Renderização parcial — para vídeo, apenas os primeiros `VIDEO_PREVIEW_SECONDS` (3 s) — usada para mostrar o resultado antes da execução completa],
)
