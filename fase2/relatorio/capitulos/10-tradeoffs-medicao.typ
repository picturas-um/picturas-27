#import "../template.typ": *

= Trade-offs, Medição e Preservação Funcional

== Matriz de efeitos

#paisagem[
#tab([Matriz de efeitos da decisão],
  tabela(
    colunas: (1.8cm, 2.6cm, 3.4cm, 2.4cm, 2.4cm, 3.6cm, 1fr),
    tamanho: 8.5pt,
    [Decisão], [Desempenho], [Disponibilidade / Fiabilidade], [Segurança], [Manutenibilidade / Testabilidade], [Progresso], [Justificação],
    [DA-1], [↑ no caminho de efeitos; ↓ em espaço total de disco], [↑], [=], [↑↑], [\= / ↑], [Imagem de efeitos de 1,70 GB para 1,09 GB e falha confinada a um domínio; o total de imagens sobe para 3,92 GB. O progresso agregado por estágio preserva a continuidade da informação que o worker monolítico emitia],
  ),
)
]

A degradação identificada — espaço total em disco — é gerida explicitamente: aceita-se o aumento
de 1,70 GB para 3,92 GB porque o custo incide no armazenamento de imagens, que não é partilhado
entre domínios, e é compensado por builds menores e por falhas que não se propagam. Não há
degradação de segurança: a decisão não altera a fronteira de autenticação nem a configuração de
segredos, que permanecem como problema conhecido e fora do âmbito desta fase.

== Plano de medição

A escala e o método foram fixados no capítulo 6, antes da alteração. A medição foi repetida
nas duas variantes no mesmo host, com o mesmo vídeo de entrada e o mesmo comando, e os resultados
foram registados em `docs/REGRESSION_CHECKLIST.md`.

#tab([Plano de medição],
  tabela(
    colunas: (1.6cm, 3.2cm, 3cm, 2.6cm, 2.4cm, 2.8cm),
    tamanho: 8pt,
    [Cenário], [Cenário de teste e carga], [Ambiente (máquina, recursos, versões)], [O que se regista], [Repetições e agregação], [Onde ficam os _scripts_ e os dados],
    [QS-01 — CAND-1], [Mudança de efeito: adicionar/alterar um efeito leve no caminho de efeitos; observação do âmbito da alteração, do tamanho da imagem reconstruída e das dependências carregadas; ensaio de isolamento com falha no worker de legendagem], [Linux x86_64, 8 núcleos, 13 GiB RAM; Docker 29.10.0, Compose 5.8.0; revisões `0523102` e final], [Serviços e filas envolvidos; ficheiros e importações no worker; tamanho da imagem (GB); Radon MI; domínios parados após falha; sequência de eventos `video-progress`], [Uma medição por variante para tamanhos e estrutura; ensaio de isolamento e de progresso repetidos no stack em execução], [`git worktree`, `git diff --stat`, `docker images`, `radon mi`; `fase2/plano_membro_a_modularidade_video.md`; registos na checklist],
  ),
)

*Ambiente e instrumentos.* As imagens Docker foram medidas com `docker images --format
'{{.Repository}}:{{.Tag}}\t{{.Size}}'` no mesmo host. A estrutura das variantes foi obtida com
`git ls-tree -r --name-only 0523102 Tools/video/` e com a listagem dos três diretórios na revisão
final. O índice de manutenibilidade foi calculado com `radon mi` sobre os módulos das duas
variantes. O isolamento de falhas e o progresso foram observados no stack em execução, com o
pedido de um pipeline misto (`border` seguido de `subtitles`) e a recolha dos eventos
`video-progress` no socket. O vídeo de entrada é `tests/fixtures/videos/speech.mp4` (320×240,
6 s, H.264/AAC, com fala); o de verificação de progresso é `clip.mp4`. A não-regressão foi
avaliada com as suites referidas na secção de preservação
funcional, com os comandos e identificadores de execução registados na checklist.

*Tratamento das medições.* A métrica principal é o tamanho da imagem que tem de ser
reconstruída quando se altera o caminho de efeitos: é um valor verificável, comparável entre
variantes e diretamente ligado ao custo de manutenção. As contagens de serviços, filas e módulos
com responsabilidades misturadas são medidas de apoio. O Radon MI foi calculado mas não é usado
como métrica principal: todas as classificações foram `A` nas duas variantes, pelo que o índice
não distingue as alternativas neste projeto. O ensaio de isolamento é qualitativo (quantos
domínios param) e o de progresso verifica a monotonicidade e a posição do valor final. Não se
fixou um valor-alvo numérico na ausência de uma medição prévia: o objetivo derivado da medição
inicial é confinar a mudança a um domínio e reduzir a imagem reconstruída, mantendo a preservação
funcional.

*Comparação antes/depois.* A campanha de regressão comparou a aplicação `0523102` com
`b8f44b3`. A referência funcional usa `25f4bd9`, que acrescenta os testes à aplicação
inicial. O executor em `tests/performance/benchmark/` instrumenta a fila e o worker que recebem
`trim` em cada variante. Os ensaios correram sequencialmente no mesmo host (Ryzen 7 5800HS,
Docker 29.10.0, Compose 5.5.1, Node.js 22.22.1), em stacks isoladas, com volumes recriados
e quatro fluxos de aquecimento por repetição.

Foram feitas três repetições por perfil e por revisão. Cada fluxo carrega um MP4, corta
de 0 a 2 s, consulta o resultado e descarrega-o. A carga baixa usa 0,5 fluxos/s durante 6 s,
também ensaiada com vídeo a 720p. A carga mista usa 2 fluxos/s durante 12 s. O pico tem
6 s a 2 fluxos/s, 6 s a 8 fluxos/s e uma recuperação a 2 fluxos/s durante 45 ou 75 s.
Recolheram-se latências, débito, timeouts, descartes e integridade dos resultados aceites.
Os percentis são calculados por repetição. A campanha de carga complementa a medição do QS-01.

== Resultados das medições

#paisagem[
#tab([Resultados das medições do QS-01 (CAND-1)],
  tabela(
    colunas: (1.6cm, 1fr, 2cm, 2cm, 2cm, 2cm),
    tamanho: 8.5pt,
    [Cenário], [Medição (o que se mede, unidade)], [Antes (_baseline_)], [Depois], [Valor-alvo], [Atingido?],
    [QS-01], [Serviços de vídeo e filas de despacho (número)], [1 serviço, 1 fila (`video_tool`, `video_queue`)], [3 serviços, 3 filas], [1 por domínio], [Sim],
    [QS-01], [Imagem a reconstruir ao alterar um efeito leve (GB)], [1,70], [1,09], [Inferior à base], [Sim — redução de 36%],
    [QS-01], [Total de imagens dos workers de vídeo (GB)], [1,70], [3,92 (1,09 + 1,74 + 1,09)], [Sem aumento (não atingido)], [Não — trade-off aceite],
    [QS-01], [`faster-whisper`/`torch` no `requirements.txt` do caminho de efeitos], [Sim], [Não], [Não], [Sim],
    [QS-01], [Domínios no worker de efeitos (número)], [3 (efeitos, legendas, fotogramas)], [1], [1], [Sim],
    [QS-01], [Radon MI nos módulos de vídeo (classe)], [A em todos], [A em todos], [Não degradar], [Sim — métrica não discriminativa],
    [QS-01], [Domínios parados quando a legendagem falha (de 3)], [1 (o único worker)], [1 (isolado nos outros dois)], [1], [Sim],
    [QS-01], [Progresso num pipeline misto (eventos `video-progress`)], [Não agregado por estágio], [`8,16,25,33,42,50,50,90,100` — monotónico, 100 apenas no fim], [Monotónico e final no fim], [Sim],
  ),
)
]

*Análise dos resultados.* A melhoria no QS-01 é demonstrável na métrica principal: alterar o
caminho de efeitos deixou de exigir a reconstrução de 1,70 GB e passou a exigir 1,09 GB, com a
remoção das dependências de IA desse serviço. A estrutura passou a ter uma fila e um contentor por
domínio, alinhada com o padrão global das ferramentas de imagem (EV-04). O ensaio de isolamento
confirmou a hipótese H-01 na base e a sua mitigação na variante final: uma falha de legendagem já
não impede os domínios de efeitos e de fotogramas. O progresso agregado manteve-se contínuo entre
estágios e com o valor final apenas no fim.

O resultado negativo é o espaço total em disco, que passou de 1,70 GB para 3,92 GB. Não é um
valor-alvo falhado escondido: foi identificado antes da decisão (capítulo 4), assumido como
trade-off no capítulo 5 e mantido visível na matriz de efeitos. O Radon MI não distinguiu as
variantes — todos os módulos, antes e depois, são classificados como `A` — e por isso não é
apresentado como evidência da melhoria.

=== Regressão de desempenho

#block(breakable: false)[
#tab([Desempenho local — API e processamento de imagem],
  tabela(
    colunas: (1fr, 2.4cm, 2.4cm, 2.4cm),
    [Medição], [Referência], [Final], [Limite],
    [Leitura de projeto, p95], [35,42 ms], [22,40 ms], [2 000 ms],
    [Redimensionamento até ao resultado], [258,84 ms], [247,69 ms], [30 000 ms],
  ),
)
]

O teste local ficou dentro dos dois limites nas duas revisões, com uma execução por revisão.

#block(breakable: false)[
#tab([Carga de vídeo — intervalo observado nas três repetições],
  tabela(
    colunas: (1fr, 3.2cm, 3.2cm),
    [Tempo até ao resultado], [Referência], [Final],
    [Carga baixa, p50], [449–453 ms], [452–461 ms],
    [Carga mista, p95], [670–674 ms], [460–678 ms],
    [Pico de 45 s, p95], [15,64–17,27 s], [8,64–9,30 s],
    [Pico de 75 s, p95], [13,42–13,68 s], [9,56–10,26 s],
    [Carga baixa a 720p, p50], [1,108–1,118 s], [0,688–0,709 s],
  ),
)
]

Na carga mista, as duas revisões concluíram 72 fluxos e mantiveram 115 cortes/min na janela.
No pico de 45 s, os fluxos concluídos passaram de 381 para 423 e os descartes antes do início
de 69 para 27. No pico de 75 s, os fluxos concluídos passaram de 576 para 597 e os descartes
de 54 para 33. Em ambas as variantes de pico houve zero timeouts e a auditoria confirmou um
resultado íntegro por pedido aceite. A comparação mede revisões completas. A reconstrução das
imagens e a variação da carga do host limitam a atribuição dos ganhos a uma só alteração.
Os valores por repetição constam de `resultados-desempenho-inicial.md` e `resultados-regressao-atual.md`.

#block(breakable: false)[
== Preservação funcional

*Passaram nas duas versões 155 dos 158 casos emparelhados por nome no JUnit.*
Os totais incluem os casos exclusivos de cada revisão.

#tab([Regressão funcional — casos aprovados / executados],
  tabela(
    colunas: (1fr, 2.5cm, 2.5cm, 2.8cm),
    [Suite], [Referência], [Final], [Casos comuns],
    [Unitários Node / Python], [101/101], [94/96], [76/76],
    [API], [36/36], [36/36], [36/36],
    [Integração], [30/30], [30/31], [29/30],
    [Browser (Playwright)], [11/11], [9/11], [9/11],
    [Segurança, restauro e orçamento local], [5/5], [5/5], [5/5],
    [*Total*], [*183/183*], [*174/179*], [*155/158*],
  ),
)
]

Na integração, o caso de remoção de fundo excedeu o prazo e passou numa repetição isolada.
O total conserva o resultado da primeira passagem. No browser, o percurso de edição e descarga
de imagem excedeu o prazo e o teste da partilha de leitura não encontrou o botão «Apply».
Os resultados de preservação destes dois percursos ficam por confirmar.

Os dois casos Python de recuperação falharam na preparação ao procurar o worker antigo.
A descoberta do Playwright completo ficou bloqueada por uma importação no ficheiro de recuperação.
A tabela usa a execução separada dos cinco ficheiros existentes na referência. Os 13 casos de
falha conhecida voltaram a falhar nas duas versões e são contabilizados à parte.
Os registos constam de `resultados-regressao-atual.md` e `docs/REGRESSION_CHECKLIST.md`.

#tab([Preservação funcional e testes de regressão],
  tabela(
    colunas: (2.4cm, 3.8cm, 2.8cm, 3.2cm, 1fr),
    tamanho: 8.5pt,
    [Zona alterada], [Testes de regressão existentes], [Lacunas de teste], [Testes acrescentados], [Resultado (imagem e vídeo)],
    [Despacho e encadeamento de etapas de vídeo em `projects/` e workers especializados — DA-1], [`video-pipeline.test.js`, `process-batch.test.js` e integração de processamento, incluindo projetos mistos e extração após edição], [Isolamento entre filas com indisponibilidade de um worker; fluxo completo de vídeo no navegador], [Caso de encaminhamento para os três workers; caso de integração de pipeline misto `border` + `subtitles`; verificação do progresso agregado], [30/31 na suite de integração. O pipeline de moldura seguida de legendagem passou. A remoção de fundo passou na repetição isolada.],
  ),
)

#block(breakable: false)[
Os riscos abaixo decorrem da separação de filas e do encadeamento de etapas do DA-1 e foram
tratados antes de a decisão ser aceite.

#tab([Riscos para a preservação funcional e mitigação],
  tabela(
    colunas: (3.4cm, 3.2cm, 4cm, 3.2cm),
    tamanho: 8.5pt,
    [Risco], [Funcionalidade afetada (imagem / vídeo)], [Mitigação], [Teste de regressão],
    [Encaminhar um pedido para a fila errada ou perder a ordem das etapas ao encadear workers], [Vídeo com efeitos, legendas ou extração de fotogramas após edição], [Encaminhar por tipo de etapa (`videoStages()`) e avançar após a resposta da etapa anterior, usando o resultado intermédio como entrada], [`video-pipeline.test.js` verifica o encaminhamento; `processing.test.js` verifica o pipeline misto, os fotogramas da linha temporal editada e a exportação ZIP],
    [Publicar um resultado incompleto se uma etapa terminar antes do registo integral do lote ou se uma etapa falhar], [Aplicação em lote em projetos de vídeo ou mistos e preservação do resultado anterior], [Registar todos os processos antes do primeiro despacho e condicionar a publicação do lote à conclusão das etapas], [`process-batch.test.js` verifica o registo e a publicação; `RUN-02` verifica a preservação do resultado anterior em caso de falha],
    [Perder o progresso entre estágios de workers diferentes], [Feedback de progresso no browser], [Propagar `base`/`span` por estágio e agregar no orquestrador], [Eventos `video-progress` observados: 8, 16, 25, 33, 42, 50, 50, 90, 100],
  ),
)
]
