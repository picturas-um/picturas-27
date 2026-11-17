#set document(title: "Usabilidade e fiabilidade — processamento em segundo plano: métricas e avaliação")
#set page(paper: "a4", margin: 2cm)
#set text(size: 11pt, lang: "pt")
#set heading(numbering: "1.1")

= Usabilidade — trabalho em segundo plano: métricas e avaliação

Documento de trabalho iniciado em 14 de novembro de 2026.

*Responsabilidade:* diagnóstico, quantificação, baseline, refactoring do frontend e não-regressão do requisito de usabilidade.

*Objetivo:* demonstrar, com medições reproduzíveis, que o utilizador passa a poder continuar a usar a aplicação enquanto um projeto é processado, sem alterar o comportamento funcional do processamento.

*Estado (14 de novembro de 2026):* alteração do frontend feita. Baseline e medição final recolhidas no mesmo dia, com o inspetor do browser e testes manuais (ver as secções de resultados). 

== Definir o que vai ser avaliado

*Classificação:* Usabilidade → Operabilidade, segundo a ISO/IEC 25010:2011. Ideia de partida das diretrizes da Fase 2: "Usabilidade — trabalho em segundo plano". As métricas abaixo são escolhas operacionais da equipa, não prescritas pela norma.

*Âmbito:* ecrã de processamento e interação do utilizador durante o processamento, em `frontend/app/dashboard/[pid]/page.tsx`.

*Decisão de âmbito (14 de novembro de 2026):* Desbloquear interface durante o processamento.

*Commit de partida:* a baseline foi medida no commit `c98fd47111162f2a4e24948fb80287e0a35c0f26` (resultado de `git rev-parse HEAD` na `main` do fork da equipa, a 14 de novembro de 2026). O documento de manutenibilidade usa `ab3ae9cf8efcfa444e9599f8e291551c5930c289`.

*Fragilidade indicada nas diretrizes (a confirmar no código e por observação):* durante o processamento, um ecrã sobreposto bloqueia toda a aplicação; o progresso existe apenas no browser e perde-se com um refresh.

*Observação nossa (baseline, 14 de novembro de 2026):* o ecrã sobreposto cobre a área de conteúdo do projeto, mas não a barra lateral, que continua utilizável.

*Não-regressão funcional:* o processamento de imagens e de vídeos deve manter-se igual. O refactoring visa só a operabilidade durante o processamento.

== Métricas

*Área da janela obstruída durante o processamento.* É a percentagem da janela coberta pelo elemento de processamento visível: largura × altura do elemento ÷ (`innerWidth` × `innerHeight`) × 100. Mede-se com o inspetor do browser (Ctrl+Shift+C), selecionando o elemento enquanto o processamento decorre e anotando as suas dimensões. Na baseline, o ecrã sobreposto ocupava 1280 × 695 px visíveis numa janela de 1536 × 695,2 px, ou seja, 83,3 %. Na versão final, o cartão ocupa 289,6 × 169,6 px, ou seja, 4,6 %. 

*Valor na base:* 83,3 %. *Valor final medido:* 4,6 %. 

== Preparar e recolher a baseline

*Ambiente:* Windows 11, Docker Desktop com `docker compose` (v5.5.1), navegador baseado em Chromium com as DevTools do Chrome (	157.0.8103.51), CPU e RAM por registar. Janela de teste: viewport de 1536 × 695,2 px CSS, com a barra lateral a ocupar 256 px; as capturas têm 1917 px de largura, o que sugere uma escala de 125 % do Windows.

*Comando de arranque:* `docker compose up -d --build`; Ctrl+Shift+R no browser depois de reconstruir o frontend.

*Projeto de teste:* projeto `test1` com três vídeos de 6,0 s, 10,0 s e 176,6 s (`sample`), com a ferramenta de legendagem automática aplicada. O vídeo longo faz o ecrã de processamento durar tempo suficiente para medir.

*Resultados da baseline (14 de novembro de 2026, código original):*
- Janela: 1536 × 695,2 px CSS; barra lateral de 256 px.
- Elemento de bloqueio: `div` com `absolute top-0 left-0 h-screen w-screen bg-black/70 z-50` (`frontend/app/dashboard/[pid]/page.tsx`, perto da linha 903). A caixa mede 1536 × 695,2 px e é cortada pelo `overflow-hidden` do `main` do layout, ficando visíveis 1280 × 695 px. 1280 ÷ 1536 = 83,3 % da janela.

#figure(
  image("evidencias_usabilidade/baseline-01-overlay-inspetor-58pct.png", width: 90%),
  caption: [Baseline: ecrã sobreposto a 58 %, com o inspetor a mostrar 1280 × 695 px visíveis.],
)

- Cartão do ecrã de processamento: 417,6 × 169,6 px.

#figure(
  image("evidencias_usabilidade/baseline-02-cartao-inspetor-56pct.png", width: 90%),
  caption: [Baseline: cartão do ecrã de processamento a 56 %, com o inspetor a mostrar 417,6 × 169,6 px.],
)

- A barra lateral não ficou escurecida e clicar em `test1` respondeu: a vista passou para a grelha de ficheiros e o ecrã de processamento voltou a aparecer, a 38 %.
- Fim do processamento na baseline: por registar.
- Evidência: ver as figuras desta secção.

== Refactoring

*Alteração feita na operabilidade (14 de novembro de 2026):* `frontend/app/dashboard/[pid]/page.tsx`, para o ecrã de processamento deixar de bloquear a interação. Nesta primeira alteração só mudaram classes CSS: o `div` exterior passou de `absolute top-0 left-0 h-screen w-screen bg-black/70 z-50 flex justify-center items-center` para `fixed bottom-4 right-4 z-50`; o `Card` perdeu `justify-center` e ganhou `shadow-lg`; a `Progress` passou de `w-96` a `w-64`. A alteração posterior da recuperabilidade é descrita na segunda parte deste documento.

*Decisões e alternativas consideradas:*
- Escolhida: cartão fixo no canto inferior direito, na própria página, que mantém a barra de progresso, a percentagem e o botão Cancelar.
- Alternativa: manter o ecrã sobreposto com botão de fechar. O problema de fundo mantém-se.

== Criar a verificação de não-regressão

*Funcional:* o processamento de imagens e de vídeos termina e o resultado é igual ao da baseline (número de ficheiros, nomes, tipos de resultado).

*Verificação da alteração inicial de apresentação:* a comparação entre `c98fd47` e `75986e6`, limitada a `frontend/app/dashboard/[pid]/page.tsx`, mostra três linhas alteradas, todas de `className`: o `div` exterior (de `absolute top-0 left-0 h-screen w-screen bg-black/70 z-50 flex justify-center items-center` para `fixed bottom-4 right-4 z-50`), o `Card` (sem `justify-center` e com `shadow-lg`) e a `Progress` (de `w-96` para `w-64`). Nesse commit a lógica de `processing`, `displayedProgress` e `cancelProcess` não foi tocada. Esta observação diz respeito à primeira parte; a recuperação após F5 altera essa lógica e requer os testes próprios descritos adiante. A comparação do código, por si só, não substitui a verificação funcional dos resultados.

```diff
-        <div className="absolute top-0 left-0 h-screen w-screen bg-black/70 z-50 flex justify-center items-center">
-          <Card className="p-4 flex flex-col justify-center items-center gap-4">
+        <div className="fixed bottom-4 right-4 z-50">
+          <Card className="p-4 flex flex-col items-center gap-4 shadow-lg">
...
-            <Progress value={displayedProgress} className="w-96" />
+            <Progress value={displayedProgress} className="w-64" />
```

== Medir a versão final e entregar evidência

Na versão de operabilidade (14 de novembro de 2026, mesmo projeto `test1` e mesma legendagem automática), o cartão de processamento ocupa 289,6 × 169,6 px, ou seja, 4,6 % da janela, contra 83,3 % na baseline. O resto do ecrã deixou de escurecer. Com o processamento em curso, abriram-se a grelha de ficheiros (14 %), o editor com a barra de ferramentas (9 %) e a janela Import (68 %). Estas medições não incluem a recuperação após refresh, tratada na segunda parte.

#figure(
  image("evidencias_usabilidade/final-01-cartao-inspetor-5pct.png", width: 90%),
  caption: [Versão final: cartão no canto inferior direito a 5 %, com o inspetor a mostrar 289,6 × 169,6 px.],
)

#figure(
  image("evidencias_usabilidade/final-02-contentor-inspetor-8pct.png", width: 90%),
  caption: [Versão final: a 8 %, com o inspetor a mostrar (1280 × 640,8 px)],
)

#figure(
  image("evidencias_usabilidade/final-03-grelha-14pct.png", width: 90%),
  caption: [Versão final: grelha de ficheiros sem ecrã escurecido, com o processamento a 14 %.],
)

#figure(
  image("evidencias_usabilidade/final-04-editor-ferramentas-9pct.png", width: 90%),
  caption: [Versão final: editor com a barra de ferramentas e a legenda aplicada visíveis, com o processamento a 9 %.],
)

#figure(
  image("evidencias_usabilidade/final-05-import-aberto-68pct.png", width: 90%),
  caption: [Versão final: janela Import aberta durante o processamento, a 68 %.],
)

=== 14 de novembro de 2026 - Preparação da documentação

*Criação do documento.* A estrutura foi criada a partir do documento de manutenibilidade. A alteração do frontend foi feita em `frontend/app/dashboard/[pid]/page.tsx`.

*Baseline.* Mediu-se no código original, commit `c98fd47111162f2a4e24948fb80287e0a35c0f26`, com o projeto `test1` e a legendagem automática. O ecrã sobreposto cobria 83,3 % da janela (1280 × 695 px visíveis de 1536 × 695,2 px). Na área de conteúdo só o botão Cancelar respondeu, e a barra lateral continuou utilizável.

*Versão final.* Reconstruiu-se o frontend com `docker compose up -d --build`. O cartão fixo no canto ocupa 4,6 % da janela (289,6 × 169,6 px), o resto do ecrã deixou de escurecer e o utilizador pode mexer na interface do pictuRAS. 

*Apoio de AI* Claude ajudou na estrutura deste typ, tudo validado por nós.

=== Modelo de entrada futura

- *Data e responsável:* por preencher.
- *Tarefa e objetivo:* por preencher.
- *Commit e ambiente:* por preencher.
- *Procedimento e comandos:* por preencher.
- *Resultados e localização da evidência:* por preencher.
- *Decisão, limitações e próximo passo:* por preencher.
- *Apoio de IA e validação humana:* por preencher.

= Fiabilidade — persistência do progresso e do cancelamento: métricas e avaliação

Documento de trabalho acrescentado em 17 de novembro de 2026, relativo à implementação e aos testes isolados de 16 de novembro de 2026.

*Responsabilidade:* diagnóstico, persistência do estado de processamento, recuperação da interface após refresh e verificação de não-regressão do acompanhamento e do cancelamento.

*Objetivo:* permitir que, depois de F5 ou de voltar a abrir o projeto, o utilizador recupere o progresso e o controlo do cancelamento da execução em curso, consultando o estado persistido no backend, sem submeter novamente o processamento.

*Estado (17 de novembro de 2026):* implementação realizada e testes isolados concluídos. Os registos de 16 de novembro apresentam 14 testes Node e 2 testes Python com sucesso. Em 17 de novembro o utilizador comunicou que realizou testes manuais de refresh e de saída e regresso à aplicação, todos com sucesso. Esta validação manual fica registada por relato escrito, sem capturas ou gravação. A suite automática de browser continua por executar.

== Definir o que vai ser avaliado

*Classificação:* Fiabilidade → Recuperabilidade, segundo a ISO/IEC 25010:2011. A equipa desdobra a ideia "Usabilidade — trabalho em segundo plano", apresentada na página 3 das diretrizes da Fase 2, e trata a recuperação do progresso e do cancelamento como um requisito próprio de recuperabilidade. Esta separação e classificação são opções da equipa; as diretrizes não apresentam "Persistência do progresso e do cancelamento" como uma ideia autónoma. As métricas e os critérios abaixo são escolhas operacionais da equipa, não valores prescritos pela norma.

*Âmbito:* recuperação do acompanhamento na página do projeto, com suporte no serviço `projects`, no API Gateway, no MongoDB e no worker de vídeo. O cartão global durante a navegação entre páginas pertence ao requisito de operabilidade e não é demonstrado por esta parte.

*Decisão de âmbito:* persistir o estado de cada nova execução e recuperá-lo por consulta ao backend. Reutilizar o cancelamento lógico existente, que invalida a execução e impede a publicação de resultados tardios; não acrescentar interrupção física do FFmpeg.

*Commit de partida:* `4110682`, que já inclui a alteração visual da primeira parte. Os testes foram executados sobre esse commit com alterações locais da recuperabilidade, conforme o histórico em `docs/REGRESSION_CHECKLIST.md`.

*Fragilidade indicada nas diretrizes:* o estado do processamento vive na página. Um refresh elimina o progresso apresentado e o acesso ao botão de cancelamento, mesmo que o trabalho continue no servidor.

*Observação nossa na baseline:* a inspeção do código identifica estado local React para `processing`, passos e percentagens dos vídeos. O cartão depende de `processing`, inicialmente falso. Sem reconstrução do estado no arranque, F5 perde o acompanhamento. Esta baseline resulta de análise estática; a reprodução manual e o respetivo tempo de recuperação não foram medidos nesta intervenção.

*Não-regressão funcional:* recuperar o acompanhamento não deve criar uma nova tarefa, consumir uma nova operação nem alterar o resultado da execução. Um pedido de cancelamento antigo não deve afetar outra execução do mesmo projeto.

== Métricas

*Recuperação do acompanhamento após F5.* Percentagem de ensaios com uma execução ativa em que o cartão reaparece com o mesmo token, progresso atualizado e cancelamento disponível para um utilizador autorizado. Fórmula: ensaios conformes ÷ ensaios de execução ativa × 100. *Meta de aceitação:* 100 % dos casos definidos. *Valor na base:* recuperação não implementada no código analisado; sem medição manual. *Valor final:* recuperação com sucesso nos testes manuais de refresh e saída/regresso comunicados pelo utilizador. O relato não quantifica repetições nem inclui inspeção dos tokens, pelo que não se apresenta uma percentagem medida de cumprimento de todos os critérios. A recuperação de uma nova leitura do estado também está coberta nos testes isolados.

*Tempo de recuperação do controlo.* Tempo entre o início do refresh e a apresentação do progresso e do botão de cancelamento, quando a execução continua ativa. *Valor na base:* sem mecanismo de recuperação. *Valor final:* por medir; limiar de aceitação por acordar. A consulta periódica está configurada para 2 segundos, mas esse intervalo não constitui uma medição nem uma garantia do tempo total de F5, que inclui carregamento da aplicação e rede.

*Submissões adicionais causadas pelo refresh.* Número de novos pedidos Apply originados apenas por recarregar a página. *Meta de aceitação:* 0. *Valor final:* por verificar no browser e nos pedidos de rede. A recuperação implementada usa `GET` de estado, sem reenviar Apply.

*Consistência da execução e do cancelamento.* Número de casos em que eventos atrasados ou pedidos de cancelamento antigos alteram uma execução diferente ou já terminada. *Meta de aceitação:* 0. *Valor final nos testes isolados:* 0 violações nos casos de token antigo, conclusão e cancelamento ensaiados. A validação concorrente na stack real permanece pendente.

== Preparar e recolher a baseline

*Ambiente da análise e dos testes isolados:* Windows, Node.js v24.15.0 e Python 3.14. Os testes Node usam o controlador de produção com um adaptador de atualizações Mongo em memória. Os testes Python compilam o método de progresso do worker a partir do código de produção e simulam o transporte de mensagens; não executam FFmpeg nem RabbitMQ.

*Ambiente do ensaio manual:* aplicação PictuRAS utilizada pelo responsável pelos testes. O relato de sucesso não inclui a configuração detalhada do ambiente, os tokens ou medições de tempo. A validação manual é distinta dos testes isolados de 16 de novembro e da suite automática de browser, que continua bloqueada no registo dessa execução.

*Comando de arranque:* `docker compose up -d`. Reconstruir os serviços alterados e reiniciar Nginx depois da reconstrução do frontend:

```powershell
docker compose up -d --build projects api_gateway video_tool frontend
docker compose restart nginx
```

*Projeto de teste:* os testes manuais foram realizados pelo utilizador na aplicação; o projeto e os ficheiros usados não foram identificados no relato. Para repetir o procedimento, usar uma execução suficientemente demorada para observar progresso, fazer F5 e sair e voltar à aplicação. O projeto `test1` da primeira parte pode servir de referência para uma repetição documentada, sem se assumir que foi o projeto usado nesta validação.

*Resultados da baseline por inspeção do código:*
- O progresso depende de contadores e eventos Socket.IO recebidos pela página aberta.
- O estado local não é reconstruído após F5 e o cartão de cancelamento deixa de estar disponível.
- Os registos de processamento e os tokens já existentes no backend não expõem, por si só, um estado público completo com percentagem e permissão de cancelamento para recuperação da página.
- Capturas e medições manuais da baseline de recuperação: por registar.

== Refactoring

*Alteração feita:* acrescentou-se `processingState` ao projeto MongoDB. Cada execução guarda token, estado, total inicial de passos, passos de imagem concluídos, progresso por vídeo, datas e causa conhecida de falha. Os estados são `processing`, `completed`, `failed` e `cancelled`; sem execução registada, a consulta devolve `idle`.

*Recuperação no frontend:* a página consulta o estado ao montar, incluindo após F5, e a cada 2 segundos. O endpoint do serviço `projects` é `GET /:user/:project/process/status`, encaminhado pelo API Gateway. A resposta inclui progresso, token, versão do projeto e `canCancel`, com `Cache-Control: no-store`. A recuperação não depende de voltar a receber os eventos que ocorreram enquanto a página esteve fechada.

*Persistência do progresso:* o worker de vídeo envia progresso correlacionado para `project_queue`, além dos eventos existentes de WebSocket. O orquestrador guarda as percentagens e os passos de imagem. Eventos repetidos não incrementam o mesmo passo duas vezes e percentagens atrasadas não fazem o valor recuar. O indicador só chega a 100 % depois do commit dos resultados. As tarefas mantêm uma barreira de conclusão até guardar a saída ou registar o passo seguinte.

*Recuperação do cancelamento:* o frontend consulta a versão atual e envia `X-Process-Token` com o pedido. O backend rejeita o pedido se o token já não corresponder à execução ativa ou se esta tiver terminado. A invalidação e o estado `cancelled` ficam persistidos; a devolução de quota existente só ocorre depois de a escrita condicional ser aceite.

*Falhas e permissões:* uma falha de consulta conserva o último progresso conhecido e apresenta aviso de ligação. Uma falha de cancelamento não esconde definitivamente os controlos. A consulta respeita as permissões do projeto: leitura permite acompanhar, edição permite cancelar. Indisponibilidade dos resultados anteriores não bloqueia o acompanhamento. Novas submissões e alterações de media ou pipeline são recusadas enquanto a execução está ativa, para preservar a correspondência entre progresso e trabalho iniciado.

*Decisões e alternativas consideradas:*
- Escolhida: estado persistido no MongoDB e consulta periódica ao backend, reutilizando os serviços e a execução existentes.
- Alternativa: guardar apenas o estado no navegador. Pode conservar uma percentagem antiga, sem confirmar que o trabalho continua ativo, terminou ou foi cancelado.
- Alternativa: usar apenas eventos WebSocket. Os eventos emitidos durante o refresh podem perder-se para a página e não reconstituem, por si só, o estado atual.

== Criar a verificação de não-regressão

*Funcional:* manter o processamento e os resultados de imagens e vídeos. A recuperação deve acompanhar a mesma execução; os estados terminais não podem reaparecer como trabalho ativo e um cancelamento atrasado não pode afetar outra execução.

*Casos de verificação:*
- F5 durante processamento: recuperar token, progresso e cancelamento, sem novo Apply.
- Conclusão enquanto a página está fechada: ao reabrir, reconhecer `completed` e não mostrar cancelamento ativo.
- Falha ou cancelamento antes de reabrir: recuperar o estado terminal correto e a causa conhecida, quando aplicável.
- Erro de rede ou de cancelamento: conservar o último estado conhecido e recuperar o acompanhamento quando a ligação regressa.
- Eventos repetidos ou atrasados: não duplicar passos nem alterar uma execução diferente.
- Utilizador sem permissão de edição: acompanhar apenas quando autorizado, sem poder cancelar.

*Testes implementados:*
- `projects/tests/processing-recovery.test.js`: 11 casos isolados de recuperação, progresso, estados terminais, permissões, preservação do estado e proteção da execução ativa.
- `projects/tests/process-batch.test.js`: 3 casos existentes de barreira de lote e commit atrasado após cancelamento.
- `tests/python/unit/test_progress_recovery.py`: 2 casos do contrato de mensagem de progresso do worker e do isolamento do preview.
- `tests/e2e/processing-recovery.spec.ts`: 2 cenários de browser, com transporte de estado/cancelamento simulado e sessão/projeto reais. Estão por executar; não equivalem a um ensaio completo do backend real.

*Comandos dos testes isolados:*

```powershell
node --test --test-reporter=junit `
  projects/tests/processing-recovery.test.js `
  projects/tests/process-batch.test.js
python -m unittest `
  tests/python/unit/test_progress_recovery.py -v
```

== Medir a versão final e entregar evidência

*Resultados registados em 16 de novembro de 2026:* 14 testes Node e 2 testes Python passaram, sem falhas nos casos executados. A verificação de tipos do frontend, as verificações de sintaxe JavaScript e `git diff --check` também passaram. Os resultados são de validação isolada, sem uma nova execução desses testes na preparação deste documento.

*Validação manual comunicada em 17 de novembro de 2026:*
- *Responsável:* utilizador que realizou os testes e comunicou os resultados; não se trata de uma execução pelo assistente.
- *Refresh:* o utilizador recarregou a página e confirmou o funcionamento com sucesso. *Resultado:* Passa — manual comunicado.
- *Saída e regresso:* o utilizador saiu e voltou à aplicação e confirmou o funcionamento com sucesso. *Resultado:* Passa — manual comunicado. Este relato não especifica um ensaio de logout/login.
- *Evidência:* declaração escrita do responsável pelos testes, registada neste documento. Não foram recolhidas capturas, gravação de vídeo, tempos ou contagem de repetições.
- *Cobertura:* sucesso dos percursos de recuperação descritos. O relato não discrimina ensaios de cancelamento antigo, falha de processamento, perda de rede ou permissões; esses casos mantêm os resultados isolados ou as verificações pendentes indicadas nas respetivas secções.

*Localização da evidência automática:* histórico em `docs/REGRESSION_CHECKLIST.md`, entradas `R-20261116-121315-recovery-node`, `R-20261116-121315-recovery-python` e `R-20261116-121316-recovery-browser`. Os casos têm os IDs `UI-04.1`, `UI-04.2` e `UI-04.3`. A execução automática de browser ficou `BLOCKED` por falta de Playwright e indisponibilidade do daemon Docker nessa execução. O sucesso manual comunicado posteriormente não altera o resultado histórico da suite automática não executada.

*Evidência visual da recuperabilidade:* não recolhida nesta validação. Uma gravação de vídeo permitiria mostrar a sequência de refresh ou saída/regresso, mas não foi produzida. A evidência disponível é o registo escrito dos testes manuais comunicados. As capturas de 14 de novembro comprovam a alteração visual da primeira parte e não foram reutilizadas como prova de F5.

*Procedimento para repetir e aprofundar a medição no browser:*
+ Iniciar Apply e registar projeto, token, estado e percentagem antes de F5.
+ Recarregar a página, medir o tempo até recuperar o controlo e confirmar o mesmo token e o estado atual; a percentagem pode ter avançado enquanto a página recarrega.
+ Confirmar nos pedidos de rede que a recuperação consulta o estado sem repetir Apply.
+ Cancelar a execução recuperada; confirmar `cancelled`, desaparecimento do cartão e ausência de resultados tardios publicados. Repetir F5.
+ Repetir deixando terminar e confirmar `completed`, 100 % e os resultados.
+ Ensaiar falha e perda de rede; confirmar a recuperação dos estados e a manutenção dos controlos adequados.
+ Guardar capturas antes/depois, resultados e tempos no registo de execução, distinguindo casos aprovados, falhados e bloqueados.

*Limitações:* a recuperação aplica-se a execuções iniciadas com esta versão. Não reconstrói percentagens de tarefas antigas sem `processingState`. O refresh e a saída/regresso tiveram sucesso segundo o relato manual do utilizador. Os tempos de F5, a inspeção dos pedidos e tokens, a suite automática de browser e os ensaios específicos de falha e concorrência continuam por validar na stack real. A disponibilização do cartão em toda a aplicação e a interrupção física do FFmpeg não são demonstradas por estes testes.

=== 16 e 17 de novembro de 2026 — Implementação e documentação

*Criação da parte de recuperabilidade.* A implementação e os testes isolados foram realizados em 16 de novembro. Em 17 de novembro a documentação foi integrada neste ficheiro, seguindo a estrutura de diagnóstico, métricas, baseline, refactoring, não-regressão e evidência usada na parte de operabilidade.

*Baseline.* A análise do commit `4110682` identificou a dependência do estado local da página e a ausência de recuperação do acompanhamento. Não foi registado um ensaio manual de F5 da baseline nesta intervenção.

*Versão final.* Estado persistido no backend e consulta de recuperação implementados. Validação isolada: 16 testes passaram. Validação manual comunicada pelo utilizador: refresh e saída/regresso com sucesso. Tempos e evidência visual não recolhidos.

*Apoio de IA e validação humana.* Codex apoiou a implementação, os testes isolados e a redação desta parte. O utilizador realizou os testes manuais de refresh e saída/regresso e comunicou sucesso; o assistente registou esse relato sem repetir os testes. Não foi produzida evidência visual desses percursos.

=== Modelo de entrada futura

- *Data e responsável:* por preencher.
- *Tarefa e objetivo:* por preencher.
- *Commit e ambiente:* por preencher.
- *Procedimento e comandos:* por preencher.
- *Resultados, tempos e localização da evidência:* por preencher.
- *Decisão, limitações e próximo passo:* por preencher.
- *Apoio de IA e validação humana:* por preencher.

= Referências de trabalho

== Enunciado e referência normativa

- Ferreira, André; Fernandes, João M.; Regedor, Miguel; Sousa, Paulo (2026). *Diretrizes Fase 2 — Melhoria de Req. Não Funcionais do PictuRAS: Especificação, refactoring e avaliação*. Versão 1, 4 de novembro de 2026. Requisitos e Arquiteturas de Software, Mestrado em Engenharia Informática, Universidade do Minho. Ficheiro no repositório: `fase2/fase-2-guidelines.pdf`. Páginas 2–3: escolha e classificação dos requisitos, ideias indicativas e avaliação esperada.
- ISO/IEC (2011). *ISO/IEC 25010:2011 — Systems and software engineering — Systems and software Quality Requirements and Evaluation (SQuaRE) — System and software quality models*. 1.ª edição, março de 2011. Referência de classificação: Usabilidade → Operabilidade; Fiabilidade → Recuperabilidade. Usa-se a edição de 2011 por ser a indicada nas diretrizes da Fase 2. #link("https://www.iso.org/standard/35733.html")[Ficha oficial da norma].

== Documentação interna e evidências

- *Histórico de execução e catálogo de regressão*. `docs/REGRESSION_CHECKLIST.md`. Regista os testes executados, os respetivos resultados e o bloqueio histórico da suite automática de browser. A validação manual comunicada em 17 de novembro está registada na secção de evidência deste documento.
- *Fiabilidade: recuperação do progresso e do cancelamento*. `fase2/documentacao/recuperabilidade-notas.md`. Notas internas de implementação e procedimento de verificação; documento auxiliar, não uma fonte externa independente nem substituto dos registos de execução.
