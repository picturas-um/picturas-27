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
verificada com as suites Node, Python e de integração referidas na secção de preservação
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

*Comparação antes/depois.* As duas variantes usam o mesmo host, os mesmos comandos e a mesma
entrada; a revisão de base é `0523102` e a final é a árvore de trabalho com as alterações
integradas. O executor de desempenho em `tests/performance/benchmark/` deteta o layout da
variante (`Tools/video/video.py` + `video_queue` na base; `Tools/video_effects/` +
`video_effects_queue` na final) e ajusta a prontidão e a instrumentação à fila e ao contentor que
recebem `trim`, preservando a semântica dos _timestamps_ e a correlação dos eventos. Os dados
dessa medição de regressão system-wide são descritos na secção seguinte e não são usados como
prova do QS-01.

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
    [Medição], [Referência], [Atual], [Limite],
    [Leitura de projeto, p95], [31,64 ms], [59,01 ms], [2 000 ms],
    [Redimensionamento até ao resultado], [265,92 ms], [280,34 ms], [30 000 ms],
  ),
)
]

O teste local repetiu 20 leituras de projeto em lotes de quatro e o redimensionamento de um
PNG de 160 × 120. Ambos os tempos observados aumentaram e ficaram dentro do orçamento de
regressão. O teste forneceu uma medição por revisão. Os resultados dos ensaios de desempenho
complementam a avaliação de modularidade do QS-01.

#block(breakable: false)[
#tab([Carga de vídeo — referência e revisão avaliada],
  tabela(
    colunas: (1fr, 3cm, 3cm),
    [Medição], [Referência], [Atual],
    [Carga baixa · corte até ao resultado, p50], [0,45 s], [0,67–3,85 s],
    [Carga mista · corte até ao resultado, p95], [0,67–0,68 s], [20,84–21,97 s],
    [Carga mista · cortes disponíveis na janela], [115/min], [10–15/min],
    [Pico · timeouts / pedidos aceites], [0/372], [167/216],
    [Pico · chegadas descartadas pelo cliente], [78], [234],
    [Pico · recuperação da fila, incluindo drenagem], [47–50 s], [147–153 s],
  ),
)
]

A carga de vídeo usou o mesmo MP4, corte de 0 a 2 s e três repetições por perfil, com volumes
recriados. A tabela apresenta o intervalo entre repetições. Na carga mista, concluíram 44 fluxos
na versão atual, face a 72 na referência. O cliente descartou 28 chegadas na versão atual quando
atingiu o limite de fluxos ativos, face a zero na referência. Na auditoria posterior ao pico, cada
pedido aceite teve um resultado íntegro e único, incluindo os que excederam o prazo do cliente.
Num controlo adicional de uma repetição em `0523102`, no dia da campanha atual, o p95 de
carga mista foi de 11,10 s e o débito de 25 cortes/min. Ficou abaixo do desempenho histórico
e acima do observado na revisão atual. Este controlo mostra a variação entre campanhas e
mantém a diferença observada em carga mista. Os detalhes constam de `resultados-regressao-atual.md`.

#block(breakable: false)[
== Preservação funcional

Os *158 casos comparáveis passaram nas duas versões*. A comparação cruza os nomes dos casos
nos relatórios JUnit da referência (`0523102` com alterações locais, 6 de novembro de 2026)
e da revisão avaliada (`252fbc1`, 24 de novembro de 2026). Os totais incluem quantidades
diferentes de casos, sobretudo pela reorganização das suites Python.

#tab([Regressão funcional — casos aprovados / executados],
  tabela(
    colunas: (1fr, 2.5cm, 2.5cm, 2.8cm),
    [Suite], [Referência], [Atual], [Casos comuns],
    [Unitários Node / Python], [101/101], [93/95], [76/76],
    [API], [36/36], [36/36], [36/36],
    [Integração], [30/30], [31/31], [30/30],
    [Browser (Playwright)], [11/11], [11/11], [11/11],
    [Segurança, backup e orçamento local], [5/5], [5/5], [5/5],
    [*Total*], [*183/183*], [*176/178*], [*158/158*],
  ),
)
]

A API e os testes no browser repetiram os percursos de autenticação, contas, projetos, partilha,
carregamento e exportação de imagem. A integração repetiu verificação de quotas, armazenamento,
concorrência e processamento de imagem e vídeo, incluindo áudio, pré-visualização, legendas e
fotogramas. Também passou o caso acrescentado de moldura seguida de legendagem. O restauro das
três bases voltou a passar no ensaio isolado.

As duas falhas atuais ocorreram na preparação de novos testes Python de recuperação, que ainda
referenciam o worker removido. A suite completa do Playwright ficou bloqueada na descoberta por
uma importação incorreta no novo ficheiro de recuperação. Os onze casos existentes passaram
numa execução seletiva dos cinco ficheiros da referência. Os campos de validação da recuperação
afetados por estes bloqueios ficam por confirmar. Os 13 casos com falha conhecida voltaram a
falhar e são contabilizados à parte. O historial, os procedimentos e a desagregação
por suite constam de `resultados-regressao-atual.md` e `docs/REGRESSION_CHECKLIST.md`.

#tab([Preservação funcional e testes de regressão],
  tabela(
    colunas: (2.4cm, 3.8cm, 2.8cm, 3.2cm, 1fr),
    tamanho: 8.5pt,
    [Zona alterada], [Testes de regressão existentes], [Lacunas de teste], [Testes acrescentados], [Resultado (imagem e vídeo)],
    [Despacho e encadeamento de etapas de vídeo em `projects/` e workers especializados — DA-1], [`video-pipeline.test.js`, `process-batch.test.js` e integração de processamento, incluindo projetos mistos e extração após edição], [Isolamento entre filas com indisponibilidade de um worker; fluxo completo de vídeo no navegador], [Caso de encaminhamento para os três workers; caso de integração de pipeline misto `border` + `subtitles`; verificação do progresso agregado], [31/31 de integração na revisão avaliada. O caso de moldura seguida de legendagem conservou áudio, moldura e legendas.],
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
