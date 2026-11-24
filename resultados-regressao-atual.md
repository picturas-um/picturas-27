# PictuRAS — regressão funcional e de desempenho

**Versão de referência funcional:** `0523102` com as alterações locais registadas na campanha de 6 de novembro de 2026 (`R-20261106-200013-full`). **Versão avaliada:** `252fbc1`, em 24 de novembro de 2026. O código da aplicação e as asserções das suites foram mantidos tal como estavam nessa revisão.

A campanha verifica percursos já disponíveis na referência, incluindo contas, quotas, projetos, partilha, carregamento, processamento e obtenção de resultados. Os resultados dos casos acrescentados são apresentados à parte da comparação. Um teste que já passava na referência conta como comparável quando o mesmo nome de caso volta a surgir no JUnit da suite correspondente, ignorando os prefixos de identificação de requisitos. Uma correspondência por nome é uma forma de emparelhar resultados. Casos reestruturados, removidos ou excluídos da descoberta ficam fora desse denominador.

**Síntese.** Os 158 casos funcionais comparáveis passaram nas duas revisões. A carga mista atual produziu tempos superiores e débito inferior à referência histórica e ao controlo contemporâneo. O pico atual teve 167 timeouts, com um resultado íntegro posteriormente confirmado para cada um dos 216 pedidos aceites.

## Resultados funcionais

| Suite | Referência: aprovados / executados | Atual: aprovados / executados | Casos comuns aprovados / repetidos |
| --- | ---: | ---: | ---: |
| Node | 18/18 | 31/31 | 18/18 |
| Python | 83/83 | 62/64 | 58/58 |
| API | 36/36 | 36/36 | 36/36 |
| Integração | 30/30 | 31/31 | 30/30 |
| Playwright, ficheiros existentes | 11/11 | 11/11 | 11/11 |
| Segurança | 3/3 | 3/3 | 3/3 |
| Backup e restauro | 1/1 | 1/1 | 1/1 |
| Orçamento local de desempenho | 1/1 | 1/1 | 1/1 |
| **Total** | **183/183** | **176/178** | **158/158** |

A execução unitária (`R-20261124-092855-unit`) terminou com 93 aprovações e duas falhas de preparação. Os dois casos novos de `test_progress_recovery.py` tentam carregar o ficheiro do antigo worker monolítico a partir de `tests/Tools/video/video.py`, que não existe. A exceção ocorre antes das asserções sobre a emissão dos eventos. A suite Python atual divide os testes entre os três workers. Dos 83 nomes da referência, 25 já não aparecem com o mesmo nome nesta suite.

A campanha `make test-all` (`R-20261124-093205-full`) registou 165 aprovações e duas falhas. O Playwright completo terminou na descoberta (zero casos executados) porque `processing-recovery.spec.ts` importa `../helpers/live` a partir de um nível incorreto. A repetição explícita dos cinco ficheiros E2E que existiam na referência (`R-20261124-093553-e2e-existing`) recuperou as 11 aprovações. Os dois casos de recuperação no browser ficaram bloqueados e não entram no denominador de executados. A recolha de resultados distingue esse bloqueio das duas falhas Python, contabilizadas pelo runner em testes que chegaram a ser iniciados.

Nos percursos existentes, passaram os testes de contas e autenticação, quotas, subscrições, presets, projetos, partilha, uploads, edição e descarga de imagem, PDF, processamento de vídeo com áudio, legendas reais, fotogramas e ZIP. Passaram também os testes de concorrência, armazenamento e backup/restauro das três bases. O caso adicional de moldura seguida de legendagem passou na integração. A afirmação de preservação refere-se aos 158 casos emparelhados.

### Casos com falha conhecida

O comando `make test-known-failures` voltou a registar **0/13 aprovados**, tal como na referência. Os 12 casos de API reproduziram as falhas documentadas. No caso isolado de resiliência, o worker processou a primeira tarefa e o consumidor não reapareceu no prazo de 90 s após o reinício do RabbitMQ. Esta suite tem histórico próprio e fica fora do total da suite principal. Referência `R-20261106-194934-known-failures` e execução atual `R-20261124-093649-known-failures`.

## Orçamento local de desempenho

| Medição | Referência | Atual | Limite |
| --- | ---: | ---: | ---: |
| Leitura de projeto pela API, p95 | 31,64 ms | 59,01 ms | 2 000 ms |
| Redimensionamento de uma imagem até resultado | 265,92 ms | 280,34 ms | 30 000 ms |

O teste executa 20 leituras em lotes de quatro e redimensiona um PNG de 160 × 120 para 80 × 60. Ambas as medições ficaram dentro dos limites existentes, embora nesta amostra os tempos tenham subido. Trata-se de uma execução por revisão, no mesmo modelo de CPU (Ryzen 7 5800HS) e com Node.js 22.22.1. O ensaio verifica os limites definidos e a execução do fluxo de imagem. A dimensão da amostra é insuficiente para atribuir a diferença ao refactoring.

Os valores vêm de `tests/reports/performance-referencia-20261106.json` e `tests/reports/performance.json`, emitidos pelo teste, às 20:02:35 UTC de 6 de novembro e às 09:35:50 UTC de 24 de novembro. Os resultados correspondem, respetivamente, a `R-20261106-200234-performance` e `R-20261124-093549-performance`.

## Ensaio de carga de vídeo

A referência de desempenho é a revisão destacada `0523102` de 20 de novembro. A revisão atual foi executada com o mesmo cliente de carga, vídeo de 4 s a 160 × 120, corte de 0 a 2 s e quatro fluxos de aquecimento por repetição. Cada fluxo cria conta e projeto, carrega o vídeo, submete o corte, consulta o resultado e descarrega o ficheiro. O ambiente Compose usa volumes novos em cada repetição. A consulta é feita a cada 200 ms entre respostas, com 30 s para observar o resultado.

| Perfil | Duração e chegadas | Limite de fluxos ativos por fase |
| --- | --- | ---: |
| Baixa | 6 s a 0,5 fluxos/s | 1 |
| Mista | 12 s a 2 fluxos/s | 12 |
| Pico e recuperação | 6 s a 2 fluxos/s, 6 s a 8 fluxos/s e 45 s a 2 fluxos/s | 12 / 48 / 12 |

O cliente verifica a unicidade e a origem do resultado dos cortes aceites. Na auditoria do pico, os resultados encontrados depois do timeout são contabilizados como íntegros e mantêm o timeout do cliente. O débito considera os cortes disponíveis na janela de chegadas. As latências são percentis por repetição pelo posto superior. A amostra do tempo até ao resultado contém os cortes cujo resultado foi observado durante a espera do cliente. A recuperação medida pelo traço conta desde o fim do pico até confirmar um segundo sem mensagens prontas, incluindo a drenagem.

### Medições por perfil

| Medição | Referência, R1 / R2 / R3 | Atual, R1 / R2 / R3 |
| --- | ---: | ---: |
| Baixa: corte até ao resultado, p50 (ms) | 453,72 / 449,63 / 448,85 | 670,61 / 671,07 / 3 851,14 |
| Baixa: fluxos concluídos (contagem) | 3 / 3 / 3 | 3 / 3 / 1 |
| Mista: corte até ao resultado, p95 (s) | 0,676 / 0,670 / 0,674 | 21,97 / 20,84 / 21,04 |
| Mista: cortes disponíveis na janela (cortes/min) | 115 / 115 / 115 | 10 / 15 / 15 |
| Mista: fluxos concluídos (contagem) | 24 / 24 / 24 | 14 / 15 / 15 |
| Pico: fluxos concluídos / aceites | 127/127 · 124/124 · 121/121 | 16/72 · 17/72 · 16/72 |
| Pico: timeouts (contagem) | 0 / 0 / 0 | 56 / 55 / 56 |
| Pico: chegadas descartadas (contagem) | 23 / 26 / 29 | 78 / 78 / 78 |
| Pico: resultados íntegros na auditoria | 127/127 · 124/124 · 121/121 | 72/72 · 72/72 · 72/72 |
| Pico: recuperação da fila, incluindo drenagem (s) | 46,78 / 47,93 / 49,91 | 146,69 / 153,17 / 146,97 |

Na carga baixa, a terceira repetição atual teve apenas uma amostra de corte. Duas das nove chegadas ficaram por iniciar, ambas nessa repetição. Na carga mista, as três repetições programaram 72 chegadas por versão. A referência iniciou e concluiu os 72 fluxos. A versão atual iniciou e concluiu 44, com 28 chegadas descartadas pelo cliente e zero timeouts. Na carga mista, o p95 da espera até à entrada no worker passou de 1,28–1,66 ms para 18,18–20,81 s. O p95 do processamento no worker passou de 427–463 ms para 3,65–3,90 s. A atribuição da diferença a uma alteração específica exige controlar os fatores de ambiente e medir os componentes individualmente.

O pico programou 450 chegadas em cada versão. Na revisão atual, 216 chegaram ao pedido de corte e foram aceites. Destes, 49 concluíram o fluxo no cliente e 167 excederam o prazo. As 234 restantes foram descartadas pelo cliente antes do arranque. Na referência houve 372 cortes aceites, todos concluídos no cliente, e 78 chegadas descartadas. A auditoria posterior confirmou um resultado íntegro e único por cada um dos 372 e dos 216 pedidos aceites, respetivamente. A variante histórica de recuperação com 75 s e o vídeo de 720p ficaram fora da repetição atual.

### Controlo contemporâneo da revisão de referência

| Medição | Referência histórica | Controlo de `0523102`, 24 de novembro | Atual |
| --- | ---: | ---: | ---: |
| Baixa: corte até ao resultado, p50 | 0,45 s | 0,90 s | 0,67–3,85 s |
| Mista: corte até ao resultado, p95 | 0,67–0,68 s | 11,10 s | 20,84–21,97 s |
| Mista: cortes disponíveis na janela | 115/min | 25/min | 10–15/min |

Depois da série atual, foi feita uma repetição de cada um destes dois perfis sobre `0523102`, no mesmo equipamento, com as mesmas regras de carga e a mesma tolerância no arranque. A carga mista de controlo concluiu 17 fluxos e descartou sete chegadas. O controlo ficou mais lento do que o histórico em ambos os perfis, sinal de que as condições entre campanhas influenciam a comparação. Em carga mista, a versão atual ficou ainda assim atrás do controlo em latência e débito. A amostra de controlo tem uma repetição por perfil, as imagens foram reconstruídas e a execução foi sequencial. Por isso, a dimensão da diferença observada não pode ser atribuída a uma alteração específica. Os dados do controlo ficam em `tests/reports/benchmark-0523102-controlo/`.

A primeira tentativa atual concluiu dois fluxos de carga baixa e descartou uma chegada. O healthcheck do RabbitMQ interrompeu o início da segunda repetição. Os dados ficaram em `tests/reports/benchmark-252fbc1/`. A repetição usou uma cópia temporária do executor e da configuração de isolamento com `start_period: 90s` em vez de 30 s. Esta tolerância aplica-se ao arranque, antes do aquecimento e da carga. A série de nove repetições terminou com código 0. Os dados brutos, as versões, os identificadores de imagens de contentor e o resumo completo ficam em `tests/reports/benchmark-252fbc1-repeticao/`.

```sh
bench=tests/performance/benchmark
perf_tmp=$(mktemp -d)
sed 's/start_period: 30s/start_period: 90s/' "$bench/compose-isolado.yaml" > "$perf_tmp/compose-isolado.yaml"
sed 's|[$]root/tests/performance/benchmark/compose-isolado.yaml|'"$perf_tmp"'/compose-isolado.yaml|g' \
  "$bench/executar.sh" > "$perf_tmp/executar.sh"
PERF_REGRESSION=0 bash "$perf_tmp/executar.sh" 252fbc1 tests/reports/benchmark-252fbc1-repeticao
python3 "$bench/resumir.py" tests/reports/benchmark-252fbc1-repeticao
PERF_REGRESSION=0 PERF_SCENARIOS='low mixed' PERF_REPETITIONS=1 \
  bash "$perf_tmp/executar.sh" 0523102 tests/reports/benchmark-0523102-controlo
```

## Evidência e reprodução

- [Histórico e checklist de regressão](docs/REGRESSION_CHECKLIST.md). O runner guarda XML JUnit e logs em `tests/reports/`, ignorado pelo Git.
- [Falhas conhecidas da referência](tests/KNOWN_FAILURES.md). Os 13 casos isolados são contabilizados fora da suite principal.
- [Medição inicial de desempenho](resultados-desempenho-inicial.md). A referência de carga usa o commit destacado `0523102`, com dados brutos preservados no repositório.

### Comandos da campanha funcional

```sh
make test-unit
make test-all
node_modules/.bin/playwright test --reporter=junit \
  accessibility.spec.ts authentication.spec.ts image-processing.spec.ts \
  projects.spec.ts video-processing.spec.ts
make test-known-failures
```

Os testes correram em Linux, com Node.js 22.22.1, Python 3.14.4, FFmpeg 8.0.1, Docker 29.10.0, Compose 5.5.1 e Playwright 1.65.0. O Playwright usou Chromium e Firefox e incluiu o caso de viewport móvel. A aplicação foi executada em Compose, com o gateway em `https://localhost:8080`.
