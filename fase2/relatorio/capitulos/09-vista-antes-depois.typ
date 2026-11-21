#import "../template.typ": *

= Vista Arquitetural Antes e Depois

As duas vistas usam o mesmo tipo de diagrama de componentes UML, a mesma orientação (esquerda → direita), os mesmos grupos de contexto e uma legenda com as mesmas cores. O que muda é o número de filas e de contentores de processamento de vídeo e a forma como o orquestrador compõe os estágios. A vista «antes» é o diagrama `docs/architecture/component-diagram-video.puml` da solução de base (`0523102`); a vista «depois» é o desenho da implementação final, com os elementos introduzidos pelo DA-1 a verde.

== Antes

#figure(kind: image,
  image(width: 100%, "../images/vista_antes.png"),
  caption: [Vista do subsistema de vídeo antes das decisões: um worker, uma fila, três domínios],
)

== Depois

#figure(kind: image,
  image(width: 100%, "../images/vista_depois.png"),
  caption: [Vista do subsistema de vídeo depois do DA-1: uma fila e um worker por domínio; a verde, os elementos introduzidos],
)

== Legenda e notas

#tab([Legenda das duas vistas],
  tabela(
    colunas: (5cm, 1fr),
    [Elemento (cor, forma ou estilo)], [Significado],
    [Caixas azuis `#DCEAF7`], [Interface e serviços de entrada e fronteira: frontend/nginx, API Gateway, `projects`, `wsGateway` — inalterados entre as duas vistas],
    [Caixas cinzentas claras], [Serviços e infraestrutura de negócio: `img_storage`, MongoDB, SeaweedFS/S3, volume partilhado `image_data` — inalterados],
    [Caixas verdes `#C8E6C9` na vista «depois»], [«tática: separar por domínio» (TAT-01/TAT-02) — filas e workers novos: `video_effects_queue`/`video_effects_tool`, `video_subtitles_queue`/`video_subtitles_tool`, `video_frames_queue`/`video_frames_tool`],
    [Setas a tracejado], [Mensagens AMQP no exchange `picturas` (despacho, resposta em `project_queue`, eventos `video-progress` em `ws_queue`)],
    [Setas contínuas cinzentas], [Acesso a ficheiros no volume partilhado ou no S3],
  ),
)

#tab([Diferenças entre as vistas],
  tabela(
    colunas: (3.4cm, 4.2cm, 4.2cm, 1fr),
    tamanho: 8.5pt,
    [Aspeto], [Antes], [Depois], [Decisão / tática],
    [Fila de despacho de vídeo], [`video_queue`, única para os três domínios], [`video_effects_queue`, `video_subtitles_queue`, `video_frames_queue`], [DA-1 / TAT-01, TAT-02],
    [Contentores de processamento], [`video_tool`, um processo com Pillow, FFmpeg, Faster-Whisper e `torch`], [Três serviços com `requirements.txt` próprio; `torch`/Whisper só no de legendas], [DA-1 / TAT-02],
    [Composição do pipeline], [`projects` enviava a pipeline inteira num único envio], [`projects` calcula `videoStages()` e encadeia a resposta de cada estágio em `project_queue`], [DA-1 / TAT-03],
    [Progresso], [Publicado pelo worker monolítico, sem separação por estágio], [Publicado pelos três workers com `base`/`span`, agregado pelo orquestrador], [DA-1 / TAT-05],
    [Isolamento de falhas], [Uma falha na legendagem parava o único worker], [Falha confinada ao worker de legendas; os outros dois continuam], [DA-1 / TAT-02],
  ),
)

O que permanece igual é tão importante como o que muda: o pedido continua a entrar pelo mesmo gateway, o orquestrador `projects` continua a ser o único coordenador do lote, os ficheiros continuam a não viajar nas mensagens e os resultados continuam nos mesmos estágios S3. A alteração é, portanto, de granularidade e de composição — precisamente o tipo de mudança que uma fase de _refactoring_ permite — e não de comportamento funcional. A vista «antes» mostra a sequência completa num único bloco de processamento; a vista «depois» mostra os três blocos ligados por `project_queue`, que é onde a regressão dos pipelines mistos ocorreu e foi corrigida (`cc53fac`), com a cobertura de integração correspondente (`2ee32d7`).
