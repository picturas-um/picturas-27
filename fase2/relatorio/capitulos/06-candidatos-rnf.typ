#import "../template.typ": *

// Capítulo inteiro na horizontal (tabelas largas). Para voltar ao vertical, retirar o #paisagem[ ].
#paisagem[
= Candidatos a Requisitos Não Funcionais

Os dois candidatos escolhidos correspondem aos dois cenários mais prioritários do capítulo 5.
O `CAND-1` é o objeto deste relatório e segue a sugestão indicativa da docência para o PictuRAS
(guia da Fase 2, "Ideias (indicativas)"): dividir o processamento de vídeo em vários
microserviços, à semelhança do que já acontece com as ferramentas de imagem.

#tab([Candidatos a requisitos não funcionais da Fase 2],
  tabela(
    colunas: (1.6cm, 2.6cm, 3cm, 2.4cm, 2.8cm, 2.6cm, 2cm, 3cm, 2.8cm),
    tamanho: 7.5pt,
    [\#], [Característica / subcaracterística (ISO/IEC 25010)], [Fragilidade na base (evidência)], [Origem (padrão global / vídeo / interação)], [Impacto nos stakeholders (pertinência)], [Exigência técnica (complexidade)], [Cenário (`QS-nn`, cap. 5)], [Escala e método de medição (esboço)], [Pré-requisitos / efeitos colaterais],
    [CAND-1], [Manutenibilidade → Modularidade e Reutilizabilidade], [EV-01, EV-03: um único serviço e uma única fila agrupam filtros leves, legendagem com Whisper e extração de fotogramas; `requirements.txt` combina Pillow/FFmpeg com `faster-whisper`/`torch`], [Padrão do vídeo, alinhado com o padrão global usado pelas imagens (EV-04)], [Alta — reduz o custo e o risco de cada alteração futura; é um exemplo explícito da docência], [Média — três serviços, três filas e composição de estágios no orquestrador; reutiliza estrutura existente], [QS-01], [Ficheiros e serviços tocados por uma mudança; tamanho e build da imagem afetada; Radon MI; isolamento de falhas], [Sinergia com fiabilidade e tempo de build; conflito com espaço total em disco],
    [CAND-2], [Usabilidade → Operabilidade (feedback e controlo)], [EV-07: ecrã sobreposto bloqueia a aplicação durante o processamento; progresso apenas no browser e perdido com recarregamento], [Global (interação frontend ↔ gateway ↔ projetos)], [Alta — é a fragilidade mais visível para quem usa a aplicação], [Alta — exige persistência do estado e do progresso no backend], [QS-02], [Período de bloqueio da interface; recuperação do progresso e do cancelamento após recarregamento], [Pré-requisito: eventos de progresso fiáveis e persistentes, agora também emitidos pelos workers de vídeo],
  ),
)

== Quantificação

A escala e o método são fixados antes da alteração. Os valores medidos na base e os valores-alvo
são apresentados no capítulo 10, com a origem de cada um; não são estimativas introduzidas aqui.

#tab([Quantificação dos requisitos não funcionais],
  tabela(
    colunas: (4.2cm, 1fr, 1fr),
    [], [CAND-1], [CAND-2],
    [Escala (o que se mede e em que unidade)], [Número de ficheiros de código e de serviços que uma mudança de efeito obriga a alterar e reconstruir; tamanho da imagem Docker (GB); tempo de build limpo (s); Radon MI por módulo], [Duração do bloqueio da interface (s); progresso recuperável após recarregamento (sim/não); cancelamento disponível após recarregamento (sim/não)],
    [Cenário de medição], [Adicionar um efeito simples ao caminho de efeitos de vídeo e medir o âmbito da alteração; medir o build limpo de cada variante; provocar falha no worker de legendagem], [Iniciar o processamento de um projeto com vídeo e tentar interagir com a aplicação e recarregar a página],
    [Carga], [Um vídeo de teste curto; uma alteração de efeito por repetição; build sem cache], [Um projeto com vídeo em processamento, utilizador autenticado],
    [Ambiente], [Mesmo host, Compose project isolado, revisão `0523102` (base) e revisão final; mesmas imagens e parâmetros], [Mesmo browser e stack Compose, antes e depois da alteração],
    [Instrumento], [`git diff --stat`, `docker image inspect`, `time docker compose build`, `radon mi`, logs dos workers e contagem de domínios afetados], [Cronómetro de interação e observação do estado da interface após recarregamento],
    [Valor medido na base], [Ver capítulo 10: monólito de 1,70 GB; uma fila e um serviço para os três domínios; uma falha de legendagem parava o único worker], [Ver capítulo 10: bloqueio total da interface e perda do progresso com recarregamento (EV-07)],
    [Valor-alvo (e origem)], [Derivado da medição da base e da recomendação da docência: confinar a mudança a um domínio e reduzir a imagem reconstruída, sem perder a preservação funcional], [Derivado da medição da base: interface utilizável e progresso/cancelamento recuperáveis após recarregamento],
    [Valor mínimo aceitável (e origem)], [Nenhuma regressão funcional e nenhuma degradação do índice de manutenibilidade; todos os cenários de preservação funcional do capítulo 10 continuam a passar], [Nenhuma perda de funcionalidade existente; o processamento continua a concluir e a produzir os mesmos resultados],
  ),
)

== Relação entre os dois candidatos

São requisitos distintos e independentes: o `CAND-1` é interno (estrutura do processamento de
vídeo) e o `CAND-2` é visível ao utilizador (feedback e controlo durante a execução). Não há
relação de condição entre eles — melhorar a modularidade não garante, por si só, a recuperação do
progresso após recarregar. Há, contudo, uma dependência de instrumentação: o `CAND-2` precisa de
eventos de progresso emitidos de forma consistente pelos workers, e a decomposição do `CAND-1`
multiplica os pontos de emissão (três workers em vez de um). Por isso o progresso agregado, com
`base`/`span` por estágio, foi tratado como parte da preservação funcional do `CAND-1`. O
`CAND-1` afeta ainda a fiabilidade (isolamento de falhas) e a eficiência (tempo de build e espaço
em disco); o `CAND-2` afeta sobretudo a usabilidade e, indiretamente, a fiabilidade perceptiva.

== Evidência exploratória (se existir)

#tab([Evidência exploratória],
  tabela(
    colunas: (4cm, 5cm, 1fr),
    [Descrição], [Localização (_scripts_, dados, resultados)], [Como repetir],
    [Tamanho das imagens e tempo de build dos workers], [`docker images --format '{{.Repository}}\t{{.Size}}'`; `fase2/plano_membro_a_modularidade_video.md`], [Listar as imagens no mesmo host e comparar `video_tool` com os três workers],
    [Divisão do pipeline em estágios], [`projects/utils/video.js` (`videoStages()`), `projects/tests/video-pipeline.test.js`], [`node --test projects/tests/video-pipeline.test.js`],
    [Progresso agregado dos estágios], [`Tools/video_effects/video_effects.py`, `Tools/video_subtitles/video_subtitles.py`, `Tools/video_frames/video_frames.py` (parâmetros `base`/`span`); eventos `video-progress` observados na integração], [Executar um pipeline misto e recolher os eventos no socket; ver capítulo 10],
  ),
)
]
