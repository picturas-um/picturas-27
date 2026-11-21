#import "../template.typ": *

= Trade-offs, Medição e Preservação Funcional

#orientacao[
  *Origem:* Exercício 7, secção 5 do _template_ (e os riscos de preservação funcional do Bloco 2, secção 6).

  *Objetivo do capítulo:* mostrar que as decisões foram avaliadas além do atributo que melhoram (_trade-offs_), que a
  melhoria foi medida de forma comparável (antes e depois) e que o comportamento funcional foi preservado.

  A mesma medição é feita *antes e depois* do _refactoring_, no mesmo ambiente. *Não inventem valores* de _baseline_, alvo
  ou mínimo aceitável: fixam-se após a medição inicial. Guardem os _scripts_, os dados e o ambiente das medições para os
  reutilizar como _baseline_.
]

== Matriz de efeitos

#orientacao[
  Para cada decisão, indiquem se cada atributo *melhora* (↑), *degrada* (↓) ou fica *neutro* (=), e justifiquem. Incluam
  no mínimo quatro atributos, e entre eles a característica do outro cenário: uma melhoria num atributo costuma ter um
  custo noutro, e é isso que esta matriz deve revelar. Se uma decisão degradar um atributo, digam como a equipa vai
  gerir esse custo.
]

#paisagem[
#tab([Matriz de efeitos das decisões],
  tabela(
    colunas: (1.8cm, 2.6cm, 3.4cm, 2.4cm, 2.4cm, 3.6cm, 1fr),
    tamanho: 8.5pt,
    [Decisão], [Desempenho], [Disponibilidade / Fiabilidade], [Segurança], [Usabilidade], [Manutenibilidade / Testabilidade], [Justificação],
    [DA-1], [#preencher[↑ / ↓ / =]], [#preencher[…]], [#preencher[…]], [#preencher[…]], [#preencher[…]], [#preencher[…]],
    [DA-2], [#preencher[…]], [#preencher[…]], [#preencher[…]], [#preencher[…]], [#preencher[…]], [#preencher[…]],
  ),
)
]

== Interação entre DA-1 e DA-2

#tab([Interação entre as decisões],
  tabela(
    colunas: (2.2cm, 2.2cm, 4.4cm, 1fr),
    [Decisão A], [Decisão B], [Efeito (pré-requisito, sinergia ou conflito)], [Razão / evidência],
    [DA-1], [DA-2], [#preencher[…]], [#preencher[…]],
  ),
)

== Plano de  medição

Os capítulos 5 a 8 ainda não especificam QS-01, QS-02, os critérios de aceitação ou as decisões DA-1 e DA-2. A tabela apresenta dois ensaios já reproduzíveis, com uma associação provisória aos identificadores do template. A seleção da carga e da métrica principal de cada cenário depende da especificação final dos requisitos.

#tab([Plano de medição],
  tabela(
    colunas: (1.6cm, 3.2cm, 3cm, 2.6cm, 2.4cm, 2.8cm),
    tamanho: 8pt,
    [Cenário], [Cenário de teste e carga], [Ambiente (máquina, recursos, versões)], [O que se regista], [Repetições e agregação], [Onde ficam os _scripts_ e os dados],
    [QS-01], [Ensaio candidato de desempenho. Carga baixa: 0,5 fluxos/s durante 6 s, até 1 ativo. Carga mista: 2 fluxos/s durante 12 s, até 12 ativos.],
    [Compose isolado. Um consumidor de vídeo na referência. Máquina e versões descritas abaixo.],
    [Latências HTTP, corte, fila, worker e MongoDB (ms). Débito (cortes/min), falhas (%), CPU (%) e memória (MiB), conforme a carga.],
    [Três repetições por classe de carga. p50 em carga baixa, p50 e p95 para latências do cliente em carga mista.],
    [`carga.cjs` (`low`, `mixed`), `resumir.py`. Dados em `low-*/` e `mixed-*/`.],
    [QS-02], [Ensaio candidato de pico e recuperação. Fases normal, pico e recuperação a 2, 8 e 2 fluxos/s, durante 6, 6 e 45 s, com limites de 12, 48 e 12 fluxos ativos por fase. Variante de 75 s de recuperação.],
    [Mesmo ambiente. A gestão do RabbitMQ publica estatísticas com intervalo configurado de 1 s.],
    [Latências (ms), débito (cortes/min), recuperação (s), tamanho da fila (mensagens), timeouts, chegadas descartadas e resultados inconsistentes (contagens).],
    [Três repetições por janela de recuperação. Métricas por repetição e, quando aplicável, por fase.],
    [`carga.cjs` (`peak`), `resumir.py`. Dados em `peak-*/` e `pico-estendido/`.],
  ),
)

*Carga e estado inicial.* Cada fluxo cria uma conta gratuita e um projeto, carrega um MP4, aplica `trim` de 0 a 2 s, consulta o estado e descarrega o resultado. A entrada de referência é `clip.mp4` (4 s, 160 × 120, 10 fps, H.264/AAC, 49 065 B), gerada por `tests/fixtures/generate.py`. O cliente aguarda 200 ms entre consultas e verifica o limite de 30 s para obter resultado após cada consulta. As chegadas são programadas por fase. Quando se atinge o limite de fluxos ativos da fase, as novas chegadas são contabilizadas como descartadas. Os fluxos em curso prosseguem na transição entre fases. Os volumes são recriados a cada repetição e o aquecimento executa quatro fluxos a 1 fluxo/s.

*Ambiente e instrumentos.* A referência `0523102` foi medida num AMD Ryzen 7 5800HS (8 núcleos, 16 CPUs lógicos, 14,52 GiB de RAM), com Docker 29.10.0, Compose 5.5.1, Node.js 22.22.1 e MongoDB 4.4 com profiling de nível 2 após o aquecimento. O worker monolítico usa prefetch de uma mensagem. O gateway e `projects` têm uma instância cada, sem limites explícitos de CPU e memória nos contentores. Em `tests/performance/benchmark/`, `executar.sh` cria um worktree destacado e um projeto Compose isolado com `compose-isolado.yaml` (HTTPS e gestão do RabbitMQ em loopback, portas 18443 e 18672 por defeito). `instrumentar.py` insere marcadores em cópias das fontes. `recolher.py` consulta o broker com pausa de 0,5 s e recolhe amostras com `docker stats`. As versões, o SHA-256 da entrada, os IDs das imagens, os limites e os registos por repetição estão em `tests/performance/resultados-desempenho-inicial/`.

*Tratamento das medições.* As latências HTTP incluem a leitura da resposta e usam amostras bem-sucedidas de carregamento, submissão, consulta e descarga. O tempo total do corte decorre desde o início do POST até à primeira consulta que devolve o resultado e inclui o atraso da consulta periódica. A espera na fila vai da publicação à entrada no callback do worker. O tempo de execução vai desse ponto ao fim do processamento bem-sucedido, com correlação pelo ID da mensagem. O débito conta os resultados disponibilizados durante a janela de chegadas. As taxas de falha e timeout usam os fluxos iniciados como denominador. `resumir.py` calcula percentis pelo posto superior, CPU média amostrada em percentagem de um CPU lógico e memória máxima amostrada. O resumo conserva cada repetição e o número de amostras, com resultados por fase para as métricas aplicáveis ao pico e sem combinar as janelas de 45 s e 75 s.

*Recuperação e integridade.* O tempo de recuperação da fila começa no fim do pico e requer um segundo sem mensagens prontas para entrega. A série do RabbitMQ é complementada pelo traço de publicação e entrada no worker, que distingue recuperação durante a carga normal e drenagem após o fim das chegadas. Para cada operação HTTP, o critério do script exige duas janelas consecutivas de 3 s com pelo menos três respostas válidas em cada uma e p95 até 120% do p95 da fase normal. A auditoria consulta os projetos aceites, verifica a origem e a unicidade dos resultados e, na versão atual do script, aguarda até 180 s após a carga e a espera pelos últimos fluxos. Um resultado encontrado na auditoria mantém o eventual timeout registado pelo cliente.

*Comparação antes/depois.* Fixar a revisão de cada variante e a dos scripts. Repetir com o mesmo equipamento, vídeo e SHA-256, perfil, corte, taxas, limites do cliente, aquecimento, janelas, timeouts, profiling e regras de agregação. Registar alterações às imagens e configuração introduzidas pelo próprio refactoring. O executor atual usa `video_tool` e `video_queue`. Para medir o corte nos workers separados, é necessário adaptar a verificação de prontidão, os pontos de instrumentação e a recolha à fila e ao contentor que recebem `trim`, preservando a semântica dos timestamps e a correlação dos eventos. O plano em `fase2/plano_membro_a_modularidade_video.md` também prevê índice de manutenibilidade com Radon, tamanho das imagens, tempo de build limpo e isolamento de falhas. Ficam por fixar os módulos, as condições de build, as repetições e os critérios desse ensaio adicional.

== Resultados das medições

A referência experimental foi recolhida em 20 de novembro de 2026 sobre a revisão `0523102`. As três repetições de cada perfil de carga e as variantes de pico de 45 s e 75 s estão documentadas em `resultados-desempenho-inicial.md`, com dados brutos em `tests/performance/resultados-desempenho-inicial/`. O ensaio complementar com vídeo de 10 s a 720p variou a entrada sobre a mesma revisão e está documentado em `comparacao-videos/README.md` dentro desse diretório.

#tab([Resultados das medições],
  tabela(
    colunas: (1.6cm, 1fr, 2cm, 2cm, 2cm, 2cm, 2cm),
    tamanho: 8.5pt,
    [Cenário], [Medição (o que se mede, unidade)], [Antes (_baseline_)], [Depois], [Valor-alvo], [Mínimo aceitável], [Atingido?],
    [QS-01], [Latência (ms) e débito (cortes/min) no ensaio candidato.], [Referência disponível. Métrica final pendente.], [Pendente], [Pendente (cap. 6)], [Pendente (cap. 6)], [Pendente],
    [QS-02], [Recuperação (s) e integridade (contagens) no ensaio candidato.], [Referência disponível. Métrica final pendente.], [Pendente], [Pendente (cap. 6)], [Pendente (cap. 6)], [Pendente],
  ),
)

*Análise dos resultados por requisito não funcional.* Pendente da seleção das métricas e das medições posteriores. Na comparação, considerar o atraso da consulta periódica, as chegadas descartadas pelo cliente e a resolução da API de gestão do broker. A carga baixa inicial ficou sem amostras de recursos devido ao formato da saída do coletor. Na variante de 75 s, a primeira tentativa da segunda repetição teve 14 cortes aceites cujo estado permaneceu indeterminado no prazo da auditoria. A série publicada usa a repetição com prazo de 180 s e conserva os dados da primeira tentativa. Estas condições devem ficar explícitas ao selecionar a série comparável.

== Preservação funcional

- *Testes unitários e de componente.* `projects/tests/` verifica limites de carregamento de vídeo por perfil, encaminhamento das etapas, validação de manifestos e registo, cancelamento e publicação de resultados em lote. As suites em `Tools/video_effects/tests/`, `Tools/video_subtitles/tests/` e `Tools/video_frames/tests/` usam FFmpeg para verificar efeitos, corte e velocidade com áudio, pré-visualização, legendagem com reconhecimento simulado, extração PNG/JPEG e preservação do original ou do resultado anterior em caso de falha. `tests/functional/unit/python/test_image_effects.py` compara efeitos de imagem com os equivalentes aplicados a fotogramas.
- *API e integração.* `tests/functional/api/` verifica contratos HTTP de autenticação, quotas, subscrições, presets, projetos, partilha, uploads e pedidos de processamento. `tests/functional/integration/` verifica filas, armazenamento, quotas e concorrência no stack real. `processing.test.js` cobre aplicação ordenada de efeitos a múltiplas imagens, invalidação da pré-visualização, corte e velocidade com áudio, eventos de progresso, legendagem com e sem fala, extração após edição, exportação ZIP, projetos mistos e falha intermédia com preservação do resultado anterior.
- *End-to-end.* O Playwright usa a aplicação em `https://localhost:8080` por defeito e um worker de teste, conforme `playwright.config.ts`. Em `tests/functional/e2e/`, os casos abrangem autenticação, criação e partilha de projetos, edição e descarga de imagens, exportação PDF, acessibilidade e layout móvel. Há um caso de autenticação e abertura de projeto em Firefox. O caso de vídeo verifica que ferramentas exclusivas de imagem e a exportação PDF ficam ocultas. A edição e descarga de vídeo pelo navegador ficam por cobrir.
- *Validação de regressões.* O `Makefile` e `scripts/regression.py` disponibilizam `make test-unit`, `make test-api`, `make test-integration` e `make test-e2e`. `make test-all` executa a suite principal, incluindo segurança, resiliência e o orçamento local de desempenho. A checklist em `docs/REGRESSION_CHECKLIST.md` liga os IDs de requisito aos casos e ao histórico. Após o refactoring, comparar os resultados por requisito e caso executado, registar revisão, ambiente e artefactos e aplicar `tests/TEST_EXECUTION_PROTOCOL.md`. Os 13 casos isolados em `tests/known_failures/` têm histórico próprio em `tests/KNOWN_FAILURES.md` e ficam fora dos totais da suite principal.

*Evidência preliminar.* Na revisão `0523102`, passaram 74 testes Python do worker original e seis casos selecionados de integração pela API. Nessa seleção ficaram de fora 21 casos, incluindo a cadeia de efeitos de imagem e a transcrição com o modelo real. Dos testes atuais de Node aplicados aos módulos dessa revisão, passaram 18 e um foi incompatível com a fila única da base. As três suites Python dos workers separados ficaram bloqueadas na recolha por divergências de interfaces. Os registos constam de `video.xml`, `api-regressao.tap`, `node-regressao.tap` e dos logs de compatibilidade em `tests/performance/resultados-desempenho-inicial/`. O histórico de 20 de novembro também regista 19 casos Node e 62 Python aprovados em `9976985` com alterações locais. A validação final requer uma revisão identificada e os resultados das suites aplicáveis a essa revisão.

#tab([Preservação funcional e testes de regressão],
  tabela(
    colunas: (2.4cm, 3.8cm, 2.8cm, 3.2cm, 1fr),
    tamanho: 8.5pt,
    [Zona alterada], [Testes de regressão existentes], [Lacunas de teste], [Testes acrescentados], [Resultado (imagem e vídeo)],
    [Despacho e encadeamento de etapas de vídeo em `projects/` e workers especializados. Associação a DA-1 ou DA-2 pendente.],
    [`video-pipeline.test.js`, `process-batch.test.js` e integração de processamento, incluindo projetos mistos e extração após edição.],
    [Isolamento entre filas com indisponibilidade de um worker. Fluxo completo de vídeo no navegador.],
    [Caso unitário de encaminhamento para os três workers em `projects/tests/video-pipeline.test.js`.],
    [Final pendente.],
    [Restante âmbito das decisões pendente de especificação.],
    [Suites de API, integração e E2E da checklist, a selecionar conforme o âmbito confirmado.],
    [Pendente], [Pendente], [Final pendente.],
  ),
)

Os riscos abaixo decorrem da separação de filas e do encadeamento de etapas descritos em `fase2/plano_membro_a_modularidade_video.md`. A associação formal às decisões do capítulo 8 fica pendente.

#tab([Riscos para a preservação funcional e mitigação],
  tabela(
    colunas: (3.4cm, 3.2cm, 4cm, 3.2cm),
    tamanho: 8.5pt,
    [Risco], [Funcionalidade afetada (imagem / vídeo)], [Mitigação], [Teste de regressão],
    [Encaminhar um pedido para a fila errada ou perder a ordem das etapas ao encadear workers.],
    [Vídeo com efeitos, legendas ou extração de fotogramas após edição.],
    [Encaminhar por tipo de etapa e avançar após a resposta da etapa anterior, usando o resultado intermédio como entrada.],
    [`video-pipeline.test.js` verifica o encaminhamento. `processing.test.js` verifica os fotogramas da linha temporal editada e a exportação ZIP.],
    [Publicar um resultado incompleto se uma etapa terminar antes do registo integral do lote ou se uma etapa falhar.],
    [Aplicação em lote em projetos de vídeo ou mistos e preservação do resultado anterior.],
    [Registar todos os processos antes do primeiro despacho e condicionar a publicação do lote à conclusão das etapas.],
    [`process-batch.test.js` verifica o registo e a publicação. `processing.test.js` verifica a preservação do resultado anterior em caso de falha.],
  ),
)
