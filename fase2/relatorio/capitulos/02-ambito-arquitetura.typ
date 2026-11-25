#import "../template.typ": *

= Âmbito e Vista da Arquitetura

== Preparação e ambiente

O PictuRAS permite criar projetos de imagem e vídeo, definir uma sequência de operações e aplicá-la em lote. A análise deste capítulo toma como referência a aplicação em `0523102`. A evolução do subsistema de vídeo em `b8f44b3` é apresentada no capítulo 9.

#tab([Preparação e ambiente],
  tabela-campos(
    [Commit de partida], [`052310226c51fa57a17101c7bd1ad795674aac95`. A suite funcional de referência foi executada em `25f4bd9`, que acrescenta os testes à mesma aplicação.],
    [Arranque local], [`git worktree add --detach ../picturas-base 0523102`. A partir desse diretório, `docker compose up -d --build`. A interface é servida em `https://localhost:8080` com certificado autoassinado.],
    [Ambiente registado], [Linux x86_64, AMD Ryzen 7 5800HS (8 núcleos e 16 CPUs lógicos), 14,52 GiB de RAM, Docker 29.10.0, Compose 5.5.1 e Node.js 22.22.1 no cliente de carga. Evidência em `tests/reports/comparacao-final/0523102/normal/ambiente.txt`.],
    [Isolamento dos ensaios], [O executor de `tests/performance/benchmark/` cria um worktree e um projeto Compose próprios, com volumes novos por repetição. A campanha usou as portas locais 18443 (HTTPS) e 18672 (gestão do RabbitMQ), com 90 s de tolerância no arranque do broker.],
  ),
)

*Como é orquestrado o processamento em lote de imagens e de vídeos*

O projeto guarda a sequência ordenada de operações. O orquestrador distingue as imagens dos vídeos pelo campo `media_type` e seleciona as operações aplicáveis a cada ficheiro. Ao premir _Apply_, `projects` prepara os originais em `image_data` e regista todos os `Process` do lote antes do primeiro envio. Para cada imagem, despacha a primeira operação e encadeia as seguintes a partir das respostas em `project_queue`. Para cada vídeo, a base envia a sequência completa numa mensagem para `video_queue`. O worker publica progresso e devolve a referência à saída. O orquestrador guarda os resultados em S3 e disponibiliza os do lote concluído (EV-01, EV-02, EV-04, EV-05 e EV-08).

== Fontes consultadas

#tab([Fontes consultadas],
  tabela(
    colunas: (6cm, 2.6cm, 1fr),
    [Fonte], [Versão], [Uso no capítulo],
    [`README.md` e `docker-compose.yaml`], [`0523102`], [Arranque da stack, serviços e volumes.],
    [`nginx/nginx.conf`, gateways, `projects/`, `Tools/video/` e `rabbitMQ/definitions.json`], [`0523102`], [Fronteiras, encaminhamento, processamento e resultados.],
    [`fase2/doc-ext-requisitos-2627.pdf`], [Cópia do repositório], [Requisitos da extensão de vídeo e restrições por tipo de ficheiro.],
    [`fase2/fase-2-guidelines.pdf`], [Cópia do repositório], [Âmbito da Fase 2 e ideia indicativa de separação do processamento de vídeo (EV-06).],
    [`docs/architecture/component-diagram-global.puml`], [Relatório da Fase 2], [Fonte do diagrama global.],
    [`resultados-desempenho-inicial.md` e `resultados-regressao-atual.md`], [Campanha de novembro de 2026], [Ambiente observado e revisões das medições.],
  ),
)

#paisagem[
== Vista da arquitetura global

O nginx encaminha a interface Next.js em `/`, a API HTTP em `/api-gateway/`, a ligação Socket.IO em `/socket.io` e o acesso S3 em `/s3/`. O API Gateway encaminha os pedidos para os serviços de negócio, incluindo as operações de projeto que exigem autenticação. `users` gere contas e quotas, `subscriptions` gere planos e pagamentos simulados e `projects` gere projetos, ficheiros, operações e execuções. Cada um destes serviços usa a sua instância MongoDB (EV-07).

Os workers recebem referências a ficheiros pela mensageria. Os ficheiros de trabalho circulam pelo volume `image_data`. A fachada `img_storage` gere objetos e URLs no SeaweedFS, nos estágios `src`, `out`, `preview` e `preview_cache` (EV-02, EV-04 e EV-08). Na base, as operações de imagem são distribuídas por filas de ferramentas. O caminho de vídeo concentra os seus três domínios num worker e numa fila (EV-01 a EV-04).

#figure(
  image(width: 73%, "../images/arquitetura_global.svg"),
  caption: [Componentes da solução de base com o caminho de vídeo destacado],
)

*Notação.* Componentes UML em PlantUML. Fonte em `docs/architecture/component-diagram-global.puml`.

*Legenda.* Azul para interface e entrada, lilás para negócio, verde-azulado para vídeo,
verde-claro para imagem e cinzento para infraestrutura. As linhas tracejadas representam AMQP.
As linhas contínuas representam HTTP, Socket.IO ou acesso a dados, de acordo com a etiqueta.

]

== Sequência de um pedido completo

A figura resume o fluxo de um vídeo na base. O frontend comunica com os gateways através do nginx. A coluna de armazenamento representa o S3 nas operações de origem e publicação e o volume partilhado na preparação e leitura dos ficheiros pelo worker.

#figure(
  image(width: 100%, "../images/sequencia_pedido.svg"),
  caption: [Sequência simplificada do carregamento à disponibilização de um resultado de vídeo],
)

#tab([Passos do pedido completo em `0523102`],
  tabela(
    colunas: (2.6cm, 3.3cm, 1fr, 1.8cm),
    [Passo], [Origem → destino], [Interface e efeito], [Evidência],
    [Carregamento], [Browser → API Gateway → `projects` → `img_storage`], [`POST /:user/:project/video`. O serviço valida o ficheiro e os limites do perfil e guarda o original em `src`. As imagens usam `POST /:user/:project/img`.], [EV-08],
    [Pipeline], [Browser → API Gateway → `projects`], [`POST /:user/:project/reorder` grava a sequência. `trim` e `speed` selecionam um vídeo por `params.imgId`. A legendagem e a extração aplicam-se aos vídeos do projeto.], [EV-05, EV-08],
    [_Apply_], [`projects` → RabbitMQ → `video_tool`], [`POST /:user/:project/process`. O original é copiado de S3 para `image_data`. Após o registo do lote, segue uma mensagem por vídeo com as operações aplicáveis.], [EV-02, EV-05],
    [Progresso], [`video_tool` → RabbitMQ → wsGateway → browser], [`video-progress` em `ws_queue` durante o processamento. O gateway entrega os eventos por Socket.IO.], [EV-05, EV-07],
    [Saída e consulta], [`video_tool` → `projects` → S3 → browser], [O worker escreve em `image_data` e responde em `project_queue`. `projects` publica em `out` e agrega os resultados do lote. `GET /:user/:project/process/url` disponibiliza os URLs da execução consolidada.], [EV-01, EV-05, EV-08],
  ),
)

*Evidências da solução de base.* As referências ao código correspondem à revisão `0523102`.

- *EV-01.* `Tools/video/video.py` e `Tools/video/video_processor.py` concentram efeitos, legendagem e extração de fotogramas. Os efeitos comuns partilham uma passagem de descodificação e codificação quando são consecutivos. A legendagem e a extração podem introduzir etapas internas.
- *EV-02.* `docker-compose.yaml`, serviço `video_tool`, e `rabbitMQ/definitions.json`, ligação de `video_queue`, mostram o consumidor único na base e os volumes `image_data` e `whisper_models`.
- *EV-03.* `Tools/video/Dockerfile` instala FFmpeg e `Tools/video/requirements.txt` inclui Pillow e Faster-Whisper. Estas dependências são reunidas na mesma imagem.
- *EV-04.* `docker-compose.yaml` e `rabbitMQ/definitions.json` identificam serviços e filas por ferramenta de imagem, ligados ao exchange direto `picturas`.
- *EV-05.* `projects/utils/video.js` define as operações por tipo de ficheiro e por vídeo. Em `projects/routes/projects.js`, a rota de processamento usa `dispatchProcessBatch` e o consumidor `process_msg` coordena as respostas e a publicação. `projects/utils/processBatch.js` garante que o registo antecede o envio. `Tools/video/video.py` publica o progresso.
- *EV-06.* `fase2/fase-2-guidelines.pdf`, «Ideias (indicativas)», sugere separar o processamento de vídeo segundo o padrão das ferramentas de imagem.
- *EV-07.* `nginx/nginx.conf`, `apiGateway/routes/`, `wsGateway/` e `docker-compose.yaml` mostram as rotas de entrada, os gateways e as três instâncias MongoDB.
- *EV-08.* `projects/utils/video.js`, `projects/routes/projects.js` e `imageStorageService/` sustentam a validação de vídeo, os caminhos de carregamento, os estágios de armazenamento e a consulta da execução consolidada. Na extração completa, o manifesto é convertido em resultados de imagem. A pré-visualização pode devolver uma folha de contacto.

*H-01.* Se uma falha fatal na legendagem terminar o consumidor único da base, os restantes pedidos de vídeo ficam por atender enquanto o consumidor estiver indisponível. O ensaio de isolamento do capítulo 10 verifica o efeito desta falha.

Na revisão final, `projects/utils/video.js` agrupa as operações em estágios, e `projects/routes/projects.js` encadeia as respostas. Os serviços `video_effects_tool`, `video_subtitles_tool` e `video_frames_tool` e as respetivas filas estão no Compose e nas definições RabbitMQ. Em `b8f44b3`, um estágio composto só por cortes segue o caminho direto de FFmpeg em `Tools/video_effects/effects.py`.
