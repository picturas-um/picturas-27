#import "../template.typ": *

= Decisões Arquiteturais

== DA-1 — Decompor o processamento de vídeo por domínio e compor os estágios no orquestrador (cenário QS-01)

#tab([Decisão arquitetural DA-1],
  tabela-campos(
    [Contexto], [Na base (`0523102`) todos os efeitos de vídeo, a legendagem automática e a extração de fotogramas partilhavam o serviço `video_tool`, a fila `video_queue` e um `requirements.txt` que juntava Pillow/FFmpeg a `faster-whisper`/`torch` (EV-01, EV-02, EV-03). Qualquer alteração a um efeito obrigava a compreender e reconstruir o monólito, e uma falha na legendagem parava todos os vídeos. A fase é de refactoring: o comportamento funcional, incluindo a ordem dos efeitos e o progresso, tem de ser preservado.],
    [Tática(s) escolhida(s)], [TAT-01, TAT-02, TAT-03, TAT-05],
    [Estrutura / padrão que a realiza], [Três microserviços autónomos — `video_effects_tool`, `video_subtitles_tool`, `video_frames_tool` — com uma fila própria cada um no exchange `picturas` (`video_effects_queue`, `video_subtitles_queue`, `video_frames_queue`) e `requirements.txt` isolado. O orquestrador `projects` calcula `videoStages()` e encadeia a resposta de cada estágio na `project_queue`, avançando para o seguinte até esgotar o pipeline. Cada worker reporta a sua fatia do progresso com `base`/`span`.],
    [Alternativas consideradas e razão de rejeição], [ALT-1 (manter o monólito): rejeitada porque não resolve a fragilidade de acoplamento nem o ponto único de falha, apesar de ser a de menor risco imediato · ALT-3 (réplicas do monólito): rejeitada porque aumenta a capacidade sem aumentar a modularidade e multiplica o custo de build e disco de cada réplica],
    [Consequências positivas], [Mudança confinada a um domínio; imagem de efeitos reduzida de 1,70 GB para 1,09 GB; falha de legendagem isolada nos outros dois workers; alinhamento com o padrão já usado pelas ferramentas de imagem (EV-04); progresso agregado com `base`/`span` por estágio],
    [Consequências negativas / riscos], [Espaço total em disco sobe de 1,70 GB para 3,92 GB; três imagens e três filas aumentam a complexidade operacional; o encadeamento no orquestrador é um novo ponto de coordenação e foi onde surgiu a regressão dos pipelines mistos, depois corrigida],
    [Elementos arquiteturais afetados], [`Tools/video_effects/`, `Tools/video_subtitles/`, `Tools/video_frames/`; `rabbitMQ/definitions.json`; `docker-compose.yaml`; `projects/utils/video.js`, `projects/utils/project_msg.js`, `projects/routes/projects.js`; remoção de `Tools/video/`, `video_tool` e `video_queue`],
    [Origem e âmbito do _refactoring_], [Padrão do vídeo, alinhado com o padrão global; risco de regressão médio no despacho e alto no encadeamento de pipelines mistos — foi exigida evidência de integração antes de aceitar a decisão],
    [Classe (A/B/C)], [A — a alteração é estrutural e preserva o comportamento funcional; a correção do encadeamento restaura o comportamento da base, não acrescenta funcionalidade],
    [Implementação (_commits_ / _pull requests_)], [Merge `9976985` (refactor/video-modularity); `00fac4d`, `b3d851b`, `b424d82` (extração e limpeza); `cc53fac` (encadeamento de pipelines mistos e progresso agregado); `2ee32d7` (teste de integração de pipeline misto)],
    [Desvios face à decisão], [A vista «depois» do capítulo 9 reflete a implementação final. O plano inicial previa apenas o despacho por domínio; a execução revelou que pipelines mistos (efeito seguido de legendagem) exigiam composição explícita no orquestrador, pelo que TAT-03 passou a ser parte integrante da decisão. O plano previa também que o monólito excedia 3,5 GB; a medição real deu 1,70 GB e o relatório usa o valor medido],
  ),
)
