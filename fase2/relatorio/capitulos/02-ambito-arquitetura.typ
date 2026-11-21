#import "../template.typ": *

= Âmbito e Vista da Arquitetura

== Preparação e ambiente

#tab([Preparação e ambiente],
  tabela-campos(
    [Commit de partida], [`0523102` — o mesmo em todos os capítulos e em todos os exercícios desta fase],
    [Comando(s) de arranque], [`git checkout 0523102` (worktree isolado para as medições) e `docker compose up -d --build`; em alternativa, `docker compose up -d --build` na árvore de trabalho com as alterações locais],
    [Ambiente (SO, CPU, RAM, versões de Docker e Compose)], [Linux x86_64, 8 núcleos, 13 GiB de RAM; Docker 29.10.0, Docker Compose 5.8.0; Node 26.13.1, Python 3.14.10; vídeos de teste `tests/fixtures/videos/speech.mp4` (320×240, 6 s, com fala) e `clip.mp4`; aceitação do certificado autoassinado em `https://localhost:8080`],
  ),
)

*Como é orquestrado o processamento em lote de imagens e de vídeos*

O utilizador define a pipeline no projeto e carrega os ficheiros: imagens em
`POST /:user/:project/img` e vídeos em `POST /:user/:project/video`, cada endpoint rejeitando o
tipo contrário. Ao premir _Apply_, o orquestrador `projects` regista todos os `Process` do lote
antes de enviar a primeira mensagem e percorre a pipeline por posição. Para imagens, envia uma
mensagem por (imagem, ferramenta) a uma fila de ferramenta de imagem e, a cada resposta em
`project_queue`, avança para a posição seguinte do mesmo item. Para vídeos, na base, enviava o
pipeline inteiro numa única mensagem a `video_queue`: o worker decodificava uma vez, aplicava os
efeitos nos fotogramas e codificava uma só vez. Houvesse imagens e vídeos no mesmo projeto, as
ferramentas só de vídeo (`trim`, `speed`, `subtitles`, `extract_frames`) eram ignoradas pelas
imagens. O progresso seguia para o browser por `ws_queue` e os resultados iam para o armazenamento
S3. EV-01 e EV-02 identificam os componentes e EV-05 o despacho num único envio.

== Fontes consultadas

#tab([Fontes consultadas],
  tabela(
    colunas: (5.5cm, 3cm, 1fr),
    [Fonte], [Versão / data], [Usada para],
    [`README.md`, `AGENTS.md`], [commit `0523102` / nova versão da equipa], [Arranque da stack, papéis dos serviços, regras de processamento e convenções de código],
    [`doc-ext-requisitos-2627.pdf`], [v27.1, novembro de 2026], [Requisitos funcionais e distinção entre tipos de _media_],
    [`doc-sol-arquitetural.pdf`], [v27.1, novembro de 2026], [Arquitetura de referência da Fase 1 e decisões já tomadas],
    [`fase2/fase-2-guidelines.pdf`], [novembro de 2026], [Regras da Fase 2 e lista indicativa de RNF; origem do `CAND-1` e do `CAND-2`],
    [Slides da aula 11 (_Arch. Styles_) e documento de apoio de padrões arquiteturais], [novembro de 2026], [Nomeação dos padrões e critérios da matriz do capítulo 4],
    [Código e configuração do repositório], [commit `0523102` e revisão final], [Evidências EV-01 a EV-07; medições do capítulo 10],
  ),
)

== Vista da arquitetura global

A vista seguinte mostra o padrão global da solução com o caminho do vídeo destacado a azul. Na
base, o vídeo parte do mesmo frontend e gateway que as imagens, mas diverge no orquestrador: em
vez de uma fila por ferramenta, entra numa fila única.

#figure(kind: image,
  image(width: 100%, "../images/arquitetura_global.png"),
  caption: [Vista da arquitetura global com o caminho do vídeo destacado],
)

*Ferramenta / notação:* PlantUML, diagrama de componentes UML (`docs/architecture/component-diagram-global.puml`),
convertido para PNG com `rsvg-convert`. O mesmo ficheiro é reutilizado no capítulo 9 com as
alterações das decisões DA-1 e DA-2.

#tab([Legenda da vista da arquitetura],
  tabela(
    colunas: (5cm, 1fr),
    [Elemento (cor, forma ou estilo)], [Significado],
    [Caixas azuis `#DCEAF7`], [Serviços de entrada e fronteira: nginx, frontend, API Gateway e wsGateway],
    [Caixas cinzentas claras], [Serviços de negócio e ferramentas de processamento],
    [Caixas verdes `#E8F5E9`], [Infraestrutura: RabbitMQ, MongoDB, S3 e volumes partilhados],
    [A seta a tracejado espessa para `video_queue`], [Caminho do vídeo na solução de base — diverge do caminho das imagens no orquestrador e converge de novo no S3],
  ),
)

== Sequência de um pedido completo

#figure(kind: image,
  image(width: 100%, "../images/sequencia_pedido.png"),
  caption: [Sequência do processamento em lote de um projeto com vídeos],
)

#tab([Passos do pedido completo],
  tabela(
    colunas: (3cm, 3.6cm, 1fr, 3.4cm),
    [Passo], [Origem → Destino], [Mensagem / _endpoint_ / fila], [Evidência],
    [Carregamento do vídeo], [Frontend → nginx → API Gateway → `projects` → S3], [`POST /:user/:project/video`; validação em `projects/utils/video.js`; armazenamento no estágio `src`], [EV-01: `Projects/utils/video.js` e a rota de upload — origem do vídeo e validação por perfil],
    [Definição do _pipeline_], [Frontend → `projects`], [Escrita da lista ordenada de efeitos no projeto; `trim`/`speed` com `params.imgId` aplicam-se a um vídeo, `subtitles` e `extract_frames` ao projeto inteiro], [EV-05: `projects/utils/video.js` — categorias `VIDEO_ONLY_TOOLS` e `PER_VIDEO_TOOLS`],
    [_Apply_], [`projects` → RabbitMQ → worker de vídeo], [Registo prévio de todos os `Process`; na base, um único envio à fila `video_queue` com a pipeline completa], [EV-02: `rabbitMQ/definitions.json` e `docker-compose.yaml` — `video_queue` e `video_tool`],
    [Progresso], [Worker → `ws_queue` → wsGateway → browser], [Eventos `video-progress` com a percentagem da execução], [EV-05: publicação em `ws_queue` no worker monolítico],
    [Resultado], [Worker → `image_data` / S3 → `project_queue` → `projects` → browser], [MP4/H.264 com áudio no estágio `out`, ou manifesto/contact sheet no caso de `extract_frames`; conclusão do `Process` e notificação ao utilizador], [EV-03: `Tools/video/` — único componente que escreve os três tipos de saída],
  ),
)

As afirmações sobre o estado atual apoiam-se nas seguintes evidências, todas verificáveis no
commit `0523102`:

- *EV-01:* `Tools/video/` — diretório único que contém os filtros de imagem, a legendagem e a
  extração de fotogramas; mostra que os três domínios partilham o mesmo componente.
- *EV-02:* `rabbitMQ/definitions.json` e `docker-compose.yaml` — apenas `video_queue` e o serviço
  `video_tool` para todo o processamento de vídeo.
- *EV-03:* `Tools/video/requirements.txt` — `Pillow`/FFmpeg convivem com `faster-whisper`,
  `ctranslate2` e `torch` no mesmo contentor.
- *EV-04:* `rabbitMQ/definitions.json` e `docker-compose.yaml` — as ferramentas de imagem têm
  cada uma a sua fila e o seu serviço; é o padrão global que o vídeo não seguia.
- *EV-05:* `projects/routes/projects.js` (commit `0523102`) — o despacho de vídeo enviava a
  pipeline inteira numa única mensagem ao worker.
- *EV-06:* `fase2/fase-2-guidelines.pdf`, secção "Ideias (indicativas)", p. 2 — sugestão da
  docência de dividir o processamento de vídeo em vários microserviços, à semelhança das
  ferramentas de imagem; origem do `CAND-1`.
- *EV-07:* `fase2/fase-2-guidelines.pdf`, mesma secção — descrição da fragilidade de usabilidade
  (ecrã bloqueante, progresso perdido com recarregamento); origem do `CAND-2`.

Algumas afirmações não dispõem de evidência direta no código e são registadas como hipóteses:

- *H-01:* uma falha fatal na legendagem (OOM/SIGKILL) arrasta os restantes trabalhos de vídeo,
  porque todos partilham o mesmo processo e a mesma fila. A confirmação é o ensaio de isolamento
  de falhas do capítulo 10.
