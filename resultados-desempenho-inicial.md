# PictuRAS · Medição inicial de desempenho (RAS TP2)

Referência confirmada **`052310226c51fa57a17101c7bd1ad795674aac95`** (`0523102`), em 20 de novembro de 2026. A execução usou um worktree destacado e projetos Compose dedicados, com rede e volumes próprios e apenas duas portas publicadas em loopback (`18443` para HTTPS e `18672` para a gestão do RabbitMQ).

## Principais resultados

- Em carga baixa, a mediana por repetição ficou entre 95 e 96 ms para o upload, 449 e 454 ms até ao resultado, e 3,05 e 3,38 ms para o download.
- Em carga mista, o p95 até ao resultado ficou entre 670 e 676 ms, com 115 cortes disponíveis por minuto na janela e zero falhas ou timeouts nas três repetições.
- Com o pico de 8 chegadas/s e 75 s de carga normal a seguir, o p95 dos cortes concluídos no prazo ficou entre 22,58 e 28,09 s. A fila só esvaziou quando cessaram as chegadas. A auditoria confirmou todos os 324 cortes aceites, incluindo os 127 com timeout no cliente.

## Ensaio

- **Máquina.** AMD Ryzen 7 5800HS, 8 núcleos e 16 CPUs lógicos, 14,52 GiB de RAM, Docker 29.10.0, Compose 5.5.1 e Node.js 22.22.1 no cliente. Um worker monolítico `video_tool` com prefetch de uma mensagem, uma instância do gateway e uma de `projects`, sem limites explícitos de CPU ou RAM nos contentores. Os IDs das imagens e os limites por contentor constam dos dados brutos.
- **Entrada.** `tests/fixtures/videos/clip.mp4`, 49 065 B, 4 s, 160 × 120, 10 fps, H.264 com áudio AAC. SHA-256 `4ce59a61d61e0778a03e61f9d9c138446b466d71faa7817a0a12006694e68e99`. Cada projeto recebe um único vídeo e um `trim` de 0 a 2 s.
- **Estado inicial.** Volumes recriados em cada repetição. Antes da medição, quatro fluxos de aquecimento a 1/s deixaram quatro utilizadores gratuitos, quatro projetos, quatro vídeos de origem e quatro resultados, com zero processos pendentes. Cada fluxo medido usa um novo utilizador e projeto. O custo de criação e preparação do projeto gera carga na aplicação, mas fica fora das latências das quatro operações cronometradas.
- **Carga.** Chegadas programadas por fase, com um limite de fluxos ativos iniciados nessa fase. Os pedidos em curso continuam ao mudar de fase. O cliente consulta o estado após o POST e espera 200 ms entre consultas. O timeout de inatividade HTTP é 30 s. A espera pelo resultado tem um limiar de 30 s desde o início do POST, verificado quando cada consulta termina.

| Cenário | Fases | Chegadas por segundo | Limite de utilizadores ativos por fase |
| --- | --- | --- | --- |
| Carga baixa | 6 s | 0,5 | 1 |
| Carga mista | 12 s | 2 | 12 |
| Pico e recuperação | Normal 6 s, pico 6 s, recuperação de 45 s e ensaio adicional de 75 s | 2, 8, 2 | 12, 48, 12 |

O p50 e o p95 usam o posto mais próximo superior. As latências de API incluem a transferência da resposta e consideram respostas bem-sucedidas. Cada resposta de polling é uma amostra da consulta de estado. O download usa a URL S3 assinada através do nginx. O tempo total do corte começa no POST e termina na primeira consulta que devolve o resultado. Inclui o atraso do polling. O débito conta cortes cujo primeiro resultado ficou disponível dentro da janela de chegadas e normaliza para um minuto. As taxas usam os fluxos iniciados como denominador. Chegadas descartadas antes de iniciar um fluxo têm contagem própria.

O MongoDB 4.4 registou operações reais com profiling de nível 2 após o aquecimento. Os tempos são inteiros em ms. Um p95 de 0 ms reflete essa resolução. Os campos `acquireWaitCount` permitem contar operações em que o MongoDB reportou espera por um bloqueio. A carga inclui consultas de presença e de quota executadas pela aplicação.

A espera no RabbitMQ é a diferença entre o instante imediatamente anterior a `channel.publish` e a entrada no callback do worker, correlacionada pelo ID da mensagem. Inclui transporte e entrega. O tempo do worker vai da entrada no callback ao fim de `process_video` para mensagens bem-sucedidas. O coletor consulta a fila a cada 0,5 s. O endpoint de gestão devolveu valores repetidos durante várias consultas consecutivas. O traço de publicação e entrada no callback permite reconstituir os pedidos ainda sem entrada no worker com resolução de evento. CPU e memória vêm de `docker stats`; o máximo de memória é o maior valor observado nas amostras, com resolução de cerca de 2 s.

A recuperação da fila exige pelo menos 1 s sem mensagens prontas para entrega e é medida a partir do fim do pico. O relatório distingue a observação durante a carga normal da drenagem após o fim das chegadas. Para cada operação HTTP, a recuperação da latência é o fim de duas janelas consecutivas de 3 s com pelo menos três respostas válidas em cada janela e p95 até 120% do p95 da janela normal. Um travessão indica que a condição não foi observada dentro da janela. A auditoria volta a consultar cada projeto cujo corte foi aceite e verifica a origem, a existência de um único resultado e a unicidade do ID visível. A versão com espera adicional consulta os resultados em falta a cada segundo, com um prazo de 180 s após a carga e a espera pelos últimos fluxos. Timeouts do cliente continuam a contar mesmo quando a auditoria encontra posteriormente o resultado.

## Resultados por repetição

### Carga baixa e carga mista

| Cenário | Métrica | Unidade | Amostras R1 / R2 / R3 | R1 | R2 | R3 |
| --- | --- | --- | --- | ---: | ---: | ---: |
| Carga baixa | Upload p50 | ms | 3 / 3 / 3 | 95,06 | 96,33 | 95,76 |
| Carga baixa | Pedido de corte p50 | ms | 3 / 3 / 3 | 24,81 | 23,69 | 24,43 |
| Carga baixa | Consulta de estado p50 | ms | 9 / 9 / 9 | 7,71 | 7,76 | 7,46 |
| Carga baixa | Download p50 | ms | 3 / 3 / 3 | 3,38 | 3,26 | 3,05 |
| Carga baixa | Corte até resultado disponível p50 | ms | 3 / 3 / 3 | 453,72 | 449,63 | 448,85 |
| Carga baixa | Cortes aceites | pedidos | 3 / 3 / 3 | 3 | 3 | 3 |
| Carga baixa | Fluxos concluídos | pedidos | 3 / 3 / 3 | 3 | 3 | 3 |
| Carga baixa | Fluxos falhados | pedidos | 3 / 3 / 3 | 0 | 0 | 0 |
| Carga baixa | Timeouts | pedidos | 3 / 3 / 3 | 0 | 0 | 0 |
| Carga baixa | Chegadas descartadas pelo cliente | pedidos | 3 / 3 / 3 | 0 | 0 | 0 |
| Carga baixa | Taxa de falhas | % | 3 / 3 / 3 | 0,00 | 0,00 | 0,00 |
| Carga baixa | Taxa de timeouts | % | 3 / 3 / 3 | 0,00 | 0,00 | 0,00 |
| Carga baixa | Publicação até entrada no worker p95 | ms | 3 / 3 / 3 | 1,44 | 1,72 | 1,52 |
| Carga baixa | Processamento do worker p95 | ms | 3 / 3 / 3 | 354,85 | 336,54 | 341,54 |
| Carga mista | Upload p50 | ms | 24 / 24 / 24 | 110,86 | 113,72 | 117,63 |
| Carga mista | Upload p95 | ms | 24 / 24 / 24 | 149,70 | 139,64 | 146,60 |
| Carga mista | Pedido de corte p50 | ms | 24 / 24 / 24 | 25,37 | 25,51 | 25,63 |
| Carga mista | Pedido de corte p95 | ms | 24 / 24 / 24 | 30,82 | 32,22 | 34,74 |
| Carga mista | Consulta de estado p50 | ms | 82 / 94 / 96 | 8,24 | 8,65 | 9,30 |
| Carga mista | Consulta de estado p95 | ms | 82 / 94 / 96 | 11,62 | 11,47 | 11,68 |
| Carga mista | Download p50 | ms | 24 / 24 / 24 | 2,75 | 2,91 | 2,94 |
| Carga mista | Download p95 | ms | 24 / 24 / 24 | 3,43 | 3,47 | 3,67 |
| Carga mista | Corte até resultado disponível p50 | ms | 24 / 24 / 24 | 454,97 | 660,65 | 664,52 |
| Carga mista | Corte até resultado disponível p95 | ms | 24 / 24 / 24 | 675,63 | 669,89 | 674,16 |
| Carga mista | Cortes aceites | pedidos | 24 / 24 / 24 | 24 | 24 | 24 |
| Carga mista | Fluxos concluídos | pedidos | 24 / 24 / 24 | 24 | 24 | 24 |
| Carga mista | Fluxos falhados | pedidos | 24 / 24 / 24 | 0 | 0 | 0 |
| Carga mista | Timeouts | pedidos | 24 / 24 / 24 | 0 | 0 | 0 |
| Carga mista | Chegadas descartadas pelo cliente | pedidos | 24 / 24 / 24 | 0 | 0 | 0 |
| Carga mista | Taxa de falhas | % | 24 / 24 / 24 | 0,00 | 0,00 | 0,00 |
| Carga mista | Taxa de timeouts | % | 24 / 24 / 24 | 0,00 | 0,00 | 0,00 |
| Carga mista | Cortes disponíveis por minuto na janela | cortes/min | 23 / 23 / 23 | 115,00 | 115,00 | 115,00 |
| Carga mista | Prontos para entrega, máximo amostrado | mensagens | 24 / 24 / 24 | 0 | 0 | 0 |
| Carga mista | Entregues sem ACK, máximo amostrado | mensagens | 24 / 24 / 24 | 1 | 1 | 1 |
| Carga mista | Total na fila, máximo amostrado | mensagens | 24 / 24 / 24 | 1 | 1 | 1 |
| Carga mista | Publicação até entrada no worker p95 | ms | 24 / 24 / 24 | 1,28 | 1,50 | 1,66 |
| Carga mista | Processamento do worker p95 | ms | 24 / 24 / 24 | 427,20 | 455,54 | 462,67 |
| Carga mista | CPU média amostrada video_tool | % de um CPU lógico | 5 / 5 / 5 | 88,29 | 91,43 | 93,88 |
| Carga mista | Memória máxima amostrada video_tool | MiB | 5 / 5 / 5 | 56,64 | 57,45 | 32,82 |
| Carga mista | CPU média amostrada api_gateway | % de um CPU lógico | 5 / 5 / 5 | 10,88 | 10,78 | 11,41 |
| Carga mista | Memória máxima amostrada api_gateway | MiB | 5 / 5 / 5 | 88,47 | 87,01 | 92,00 |
| Carga mista | CPU média amostrada projects | % de um CPU lógico | 5 / 5 / 5 | 39,03 | 39,04 | 40,23 |
| Carga mista | Memória máxima amostrada projects | MiB | 5 / 5 / 5 | 137,20 | 144,40 | 134,10 |
| Carga mista | MongoDB inserções p95 | ms | 96 / 96 / 96 | 0 | 0 | 0 |
| Carga mista | MongoDB atualizações p95 | ms | 288 / 288 / 288 | 0 | 0 | 0 |
| Carga mista | MongoDB consultas p95 | ms | 1052 / 1076 / 1080 | 0 | 0 | 0 |
| Carga mista | MongoDB operações com erro | operações | 1628 / 1652 / 1656 | 0 | 0 | 0 |
| Carga mista | MongoDB operações com espera por bloqueio registada | operações | 1628 / 1652 / 1656 | 0 | 0 | 0 |

### Pico com 45 s de recuperação

As três repetições ficaram sem pedidos em fila 46,78 s, 47,93 s e 49,91 s após o pico, incluindo o último segundo de confirmação. Nessa altura já tinha terminado a janela de chegadas à taxa normal. A janela de 75 s foi acrescentada para observar a recuperação enquanto a carga normal continua.

| Cenário | Métrica | Unidade | Amostras R1 / R2 / R3 | R1 | R2 | R3 |
| --- | --- | --- | --- | ---: | ---: | ---: |
| Pico e recuperação | Upload p50 | ms | 127 / 124 / 121 | 143,88 | 152,13 | 161,15 |
| Pico e recuperação | Upload p95 | ms | 127 / 124 / 121 | 245,05 | 299,62 | 356,92 |
| Pico e recuperação | Pedido de corte p50 | ms | 127 / 124 / 121 | 36,34 | 38,47 | 44,49 |
| Pico e recuperação | Pedido de corte p95 | ms | 127 / 124 / 121 | 153,60 | 189,68 | 240,66 |
| Pico e recuperação | Consulta de estado p50 | ms | 3888 / 4097 / 4503 | 10,26 | 10,57 | 11,21 |
| Pico e recuperação | Consulta de estado p95 | ms | 3888 / 4097 / 4503 | 42,16 | 46,42 | 59,85 |
| Pico e recuperação | Download p50 | ms | 127 / 124 / 121 | 3,06 | 3,21 | 3,32 |
| Pico e recuperação | Download p95 | ms | 127 / 124 / 121 | 4,30 | 4,35 | 5,26 |
| Pico e recuperação | Corte até resultado disponível p50 | ms | 127 / 124 / 121 | 4106,15 | 4244,37 | 5087,47 |
| Pico e recuperação | Corte até resultado disponível p95 | ms | 127 / 124 / 121 | 16681,04 | 17769,49 | 19450,36 |
| Pico e recuperação | Cortes aceites | pedidos | 127 / 124 / 121 | 127 | 124 | 121 |
| Pico e recuperação | Fluxos concluídos | pedidos | 127 / 124 / 121 | 127 | 124 | 121 |
| Pico e recuperação | Fluxos falhados | pedidos | 127 / 124 / 121 | 0 | 0 | 0 |
| Pico e recuperação | Timeouts | pedidos | 127 / 124 / 121 | 0 | 0 | 0 |
| Pico e recuperação | Chegadas descartadas pelo cliente | pedidos | 150 / 150 / 150 | 23 | 26 | 29 |
| Pico e recuperação | Taxa de falhas | % | 127 / 124 / 121 | 0,00 | 0,00 | 0,00 |
| Pico e recuperação | Taxa de timeouts | % | 127 / 124 / 121 | 0,00 | 0,00 | 0,00 |
| Pico e recuperação | Cortes disponíveis por minuto na janela | cortes/min | 123 / 118 / 111 | 129,47 | 124,21 | 116,84 |
| Pico e recuperação | Prontos para entrega, máximo amostrado | mensagens | 113 / 113 / 113 | 37 | 37 | 38 |
| Pico e recuperação | Entregues sem ACK, máximo amostrado | mensagens | 113 / 113 / 113 | 1 | 1 | 1 |
| Pico e recuperação | Total na fila, máximo amostrado | mensagens | 113 / 113 / 113 | 38 | 38 | 39 |
| Pico e recuperação | Publicação até entrada no worker p95 | ms | 127 / 124 / 121 | 16035,77 | 17072,31 | 18770,76 |
| Pico e recuperação | Processamento do worker p95 | ms | 127 / 124 / 121 | 544,08 | 566,16 | 615,72 |
| Pico e recuperação | CPU média amostrada video_tool | % de um CPU lógico | 28 / 28 / 28 | 115,45 | 116,32 | 117,10 |
| Pico e recuperação | Memória máxima amostrada video_tool | MiB | 28 / 28 / 28 | 89,55 | 81,98 | 71,90 |
| Pico e recuperação | CPU média amostrada api_gateway | % de um CPU lógico | 28 / 28 / 28 | 35,46 | 37,71 | 41,78 |
| Pico e recuperação | Memória máxima amostrada api_gateway | MiB | 28 / 28 / 28 | 175,80 | 191,20 | 175,20 |
| Pico e recuperação | CPU média amostrada projects | % de um CPU lógico | 28 / 28 / 28 | 66,61 | 67,56 | 72,23 |
| Pico e recuperação | Memória máxima amostrada projects | MiB | 28 / 28 / 28 | 175,30 | 191,90 | 254,40 |
| Pico e recuperação | Aceites com estado final auditado e correto | pedidos | 127 / 124 / 121 | 127 | 124 | 121 |
| Pico e recuperação | Aceites sem resultado final esperado | pedidos | 127 / 124 / 121 | 0 | 0 | 0 |
| Pico e recuperação | Resultados duplicados detetados na auditoria | pedidos | 127 / 124 / 121 | 0 | 0 | 0 |
| Pico e recuperação | Pedidos aceites com processamento repetido | pedidos | 127 / 124 / 121 | 0 | 0 | 0 |
| Pico e recuperação | Prontos para entrega, máximo reconstruído pelo traço | mensagens | 254 / 248 / 242 | 37 | 38 | 39 |
| Pico e recuperação | Recuperação da fila pela API de gestão (1 s sem pedidos prontos) | s | 89 / 89 / 89 | — | — | — |
| Pico e recuperação | Recuperação da fila pelo traço durante carga normal | s | 254 / 248 / 242 | — | — | — |
| Pico e recuperação | Recuperação da fila pelo traço incluindo a drenagem | s | 254 / 248 / 242 | 46,78 | 47,93 | 49,91 |
| Pico e recuperação | Recuperação da latência de upload | s | 127 / 124 / 121 | 24 | 24 | 30 |
| Pico e recuperação | Recuperação da latência de pedido de corte | s | 127 / 124 / 121 | 24 | 24 | 27 |
| Pico e recuperação | Recuperação da latência de consulta de estado | s | 3888 / 4097 / 4503 | 36 | 12 | 15 |
| Pico e recuperação | Recuperação da latência de download | s | 127 / 124 / 121 | 9 | 9 | 27 |

### Pico com 75 s de recuperação

Os três ensaios mantiveram pedidos na fila até ao fim da janela de 75 s. A fila ficou vazia durante a drenagem, entre 99,41 s e 128,61 s após o pico. A auditoria confirmou um resultado único para cada um dos 324 cortes aceites. O cliente atingiu o timeout em 127 desses cortes. Outros 306 fluxos programados ficaram por iniciar devido ao limite de concorrência do cliente.

Na primeira tentativa da R2, 84 cortes foram aceites, 52 tiveram timeout e 14 resultados ainda não eram visíveis no fim da auditoria. O estado final desses 14 cortes ficou indeterminado nessa tentativa. A R2 da tabela usa a repetição com auditoria até 180 s após a carga. Os dados da primeira tentativa foram preservados. [Primeira tentativa da R2](tests/performance/resultados-desempenho-inicial/pico-estendido/peak-2-primeira-auditoria/)

| Cenário | Métrica | Unidade | Amostras R1 / R2 / R3 | R1 | R2 | R3 |
| --- | --- | --- | --- | ---: | ---: | ---: |
| Pico e recuperação | Upload p50 | ms | 156 / 84 / 84 | 158,71 | 3991,02 | 4181,49 |
| Pico e recuperação | Upload p95 | ms | 156 / 84 / 84 | 371,79 | 6945,31 | 6100,31 |
| Pico e recuperação | Pedido de corte p50 | ms | 156 / 84 / 84 | 39,80 | 2461,43 | 2307,10 |
| Pico e recuperação | Pedido de corte p95 | ms | 156 / 84 / 84 | 244,68 | 3651,32 | 4141,80 |
| Pico e recuperação | Consulta de estado p50 | ms | 6338 / 3668 / 3663 | 12,15 | 198,79 | 208,67 |
| Pico e recuperação | Consulta de estado p95 | ms | 6338 / 3668 / 3663 | 111,46 | 1144,54 | 941,28 |
| Pico e recuperação | Download p50 | ms | 153 / 21 / 23 | 3,33 | 17,07 | 13,46 |
| Pico e recuperação | Download p95 | ms | 153 / 21 / 23 | 21,03 | 28,87 | 31,00 |
| Pico e recuperação | Corte até resultado disponível p50 | ms | 153 / 21 / 23 | 5520,21 | 18101,68 | 17498,12 |
| Pico e recuperação | Corte até resultado disponível p95 | ms | 153 / 21 / 23 | 22579,91 | 26519,29 | 28094,67 |
| Pico e recuperação | Cortes aceites | pedidos | 156 / 84 / 84 | 156 | 84 | 84 |
| Pico e recuperação | Fluxos concluídos | pedidos | 156 / 84 / 84 | 153 | 21 | 23 |
| Pico e recuperação | Fluxos falhados | pedidos | 156 / 84 / 84 | 3 | 63 | 61 |
| Pico e recuperação | Timeouts | pedidos | 156 / 84 / 84 | 3 | 63 | 61 |
| Pico e recuperação | Chegadas descartadas pelo cliente | pedidos | 210 / 210 / 210 | 54 | 126 | 126 |
| Pico e recuperação | Taxa de falhas | % | 156 / 84 / 84 | 1,92 | 75,00 | 72,62 |
| Pico e recuperação | Taxa de timeouts | % | 156 / 84 / 84 | 1,92 | 75,00 | 72,62 |
| Pico e recuperação | Cortes disponíveis por minuto na janela | cortes/min | 144 / 21 / 23 | 99,31 | 14,48 | 15,86 |
| Pico e recuperação | Prontos para entrega, máximo amostrado | mensagens | 172 / 170 / 170 | 37 | 56 | 57 |
| Pico e recuperação | Entregues sem ACK, máximo amostrado | mensagens | 172 / 170 / 170 | 1 | 1 | 1 |
| Pico e recuperação | Total na fila, máximo amostrado | mensagens | 172 / 170 / 170 | 38 | 57 | 58 |
| Pico e recuperação | Publicação até entrada no worker p95 | ms | 156 / 84 / 84 | 24570,66 | 84632,91 | 81034,60 |
| Pico e recuperação | Processamento do worker p95 | ms | 156 / 84 / 84 | 3086,10 | 3403,38 | 3364,38 |
| Pico e recuperação | CPU média amostrada video_tool | % de um CPU lógico | 43 / 42 / 42 | 117,10 | 109,97 | 121,09 |
| Pico e recuperação | Memória máxima amostrada video_tool | MiB | 43 / 42 / 42 | 78,50 | 83,96 | 79,87 |
| Pico e recuperação | CPU média amostrada api_gateway | % de um CPU lógico | 43 / 42 / 42 | 47,58 | 75,69 | 77,25 |
| Pico e recuperação | Memória máxima amostrada api_gateway | MiB | 43 / 42 / 42 | 167,30 | 199,30 | 187,80 |
| Pico e recuperação | CPU média amostrada projects | % de um CPU lógico | 43 / 42 / 42 | 79,16 | 157,82 | 153,68 |
| Pico e recuperação | Memória máxima amostrada projects | MiB | 43 / 42 / 42 | 168,30 | 170,10 | 162,90 |
| Pico e recuperação | Aceites com estado final auditado e correto | pedidos | 156 / 84 / 84 | 156 | 84 | 84 |
| Pico e recuperação | Aceites sem resultado final esperado | pedidos | 156 / 84 / 84 | 0 | 0 | 0 |
| Pico e recuperação | Resultados duplicados detetados na auditoria | pedidos | 156 / 84 / 84 | 0 | 0 | 0 |
| Pico e recuperação | Pedidos aceites com processamento repetido | pedidos | 156 / 84 / 84 | 0 | 0 | 0 |
| Pico e recuperação | Prontos para entrega, máximo reconstruído pelo traço | mensagens | 312 / 168 / 165 | 39 | 58 | 57 |
| Pico e recuperação | Recuperação da fila pela API de gestão (1 s sem pedidos prontos) | s | 148 / 147 / 146 | — | — | — |
| Pico e recuperação | Recuperação da fila pelo traço durante carga normal | s | 312 / 168 / 165 | — | — | — |
| Pico e recuperação | Recuperação da fila pelo traço incluindo a drenagem | s | 312 / 168 / 165 | 99,41 | 128,61 | 122,07 |
| Pico e recuperação | Recuperação da latência de upload | s | 156 / 84 / 84 | 27 | 60 | — |
| Pico e recuperação | Recuperação da latência de pedido de corte | s | 156 / 84 / 84 | 30 | 63 | — |
| Pico e recuperação | Recuperação da latência de consulta de estado | s | 6338 / 3668 / 3663 | — | 60 | 57 |
| Pico e recuperação | Recuperação da latência de download | s | 153 / 21 / 23 | 12 | — | — |
| Pico · normal | Upload p50 | ms | 12 / 12 / 12 | 123,91 | 629,40 | 773,12 |
| Pico · normal | Upload p95 | ms | 12 / 12 / 12 | 154,40 | 2531,94 | 2025,95 |
| Pico · normal | Pedido de corte p50 | ms | 12 / 12 / 12 | 27,57 | 714,45 | 478,06 |
| Pico · normal | Pedido de corte p95 | ms | 12 / 12 / 12 | 45,14 | 6192,54 | 5966,59 |
| Pico · normal | Consulta de estado p50 | ms | 48 / 122 / 116 | 9,82 | 337,26 | 304,60 |
| Pico · normal | Consulta de estado p95 | ms | 48 / 122 / 116 | 14,72 | 3505,42 | 3382,66 |
| Pico · normal | Download p50 | ms | 12 / 12 / 12 | 3,14 | 18,30 | 19,98 |
| Pico · normal | Download p95 | ms | 12 / 12 / 12 | 4,85 | 35,12 | 39,25 |
| Pico · normal | Corte até resultado disponível p50 | ms | 12 / 12 / 12 | 672,48 | 16140,72 | 13937,62 |
| Pico · normal | Corte até resultado disponível p95 | ms | 12 / 12 / 12 | 691,23 | 20752,77 | 20874,17 |
| Pico · normal | Fluxos concluídos | pedidos | 12 / 12 / 12 | 12 | 12 | 12 |
| Pico · normal | Fluxos falhados | pedidos | 12 / 12 / 12 | 0 | 0 | 0 |
| Pico · normal | Timeouts | pedidos | 12 / 12 / 12 | 0 | 0 | 0 |
| Pico · normal | Chegadas descartadas pelo cliente | pedidos | 12 / 12 / 12 | 0 | 0 | 0 |
| Pico · normal | Cortes disponíveis por minuto na janela | cortes/min | 10 / 1 / 2 | 100,00 | 10,00 | 20,00 |
| Pico · normal | Total na fila, máximo amostrado | mensagens | 12 / 11 / 12 | 1 | 4 | 3 |
| Pico · pico | Upload p50 | ms | 48 / 48 / 48 | 228,81 | 4731,92 | 4317,88 |
| Pico · pico | Upload p95 | ms | 48 / 48 / 48 | 361,29 | 6566,49 | 6100,31 |
| Pico · pico | Pedido de corte p50 | ms | 48 / 48 / 48 | 126,72 | 2976,18 | 2775,84 |
| Pico · pico | Pedido de corte p95 | ms | 48 / 48 / 48 | 238,62 | 3563,51 | 4141,80 |
| Pico · pico | Consulta de estado p50 | ms | 2107 / 1516 / 1530 | 13,56 | 482,26 | 539,38 |
| Pico · pico | Consulta de estado p95 | ms | 2107 / 1516 / 1530 | 88,39 | 1541,51 | 1295,47 |
| Pico · pico | Download p50 | ms | 48 / 9 / 11 | 3,55 | 11,87 | 11,80 |
| Pico · pico | Download p95 | ms | 48 / 9 / 11 | 5,32 | 24,47 | 30,16 |
| Pico · pico | Corte até resultado disponível p50 | ms | 48 / 9 / 11 | 9880,47 | 21032,73 | 21208,97 |
| Pico · pico | Corte até resultado disponível p95 | ms | 48 / 9 / 11 | 17208,70 | 28416,42 | 29735,42 |
| Pico · pico | Fluxos concluídos | pedidos | 48 / 48 / 48 | 48 | 9 | 11 |
| Pico · pico | Fluxos falhados | pedidos | 48 / 48 / 48 | 0 | 39 | 37 |
| Pico · pico | Timeouts | pedidos | 48 / 48 / 48 | 0 | 39 | 37 |
| Pico · pico | Chegadas descartadas pelo cliente | pedidos | 48 / 48 / 48 | 0 | 0 | 0 |
| Pico · pico | Cortes disponíveis por minuto na janela | cortes/min | 11 / 1 / 1 | 110,00 | 10,00 | 10,00 |
| Pico · pico | Total na fila, máximo amostrado | mensagens | 12 / 12 / 12 | 8 | 5 | 4 |
| Pico · recuperação | Upload p50 | ms | 96 / 24 / 24 | 146,70 | 1218,41 | 1526,23 |
| Pico · recuperação | Upload p95 | ms | 96 / 24 / 24 | 1000,74 | 7054,64 | 6162,09 |
| Pico · recuperação | Pedido de corte p50 | ms | 96 / 24 / 24 | 32,88 | 552,34 | 724,93 |
| Pico · recuperação | Pedido de corte p95 | ms | 96 / 24 / 24 | 371,13 | 3299,79 | 2235,90 |
| Pico · recuperação | Consulta de estado p50 | ms | 4183 / 2030 / 2017 | 11,63 | 48,25 | 41,98 |
| Pico · recuperação | Consulta de estado p95 | ms | 4183 / 2030 / 2017 | 130,12 | 708,11 | 717,07 |
| Pico · recuperação | Download p50 | ms | 93 / 0 / 0 | 3,29 | — | — |
| Pico · recuperação | Download p95 | ms | 93 / 0 / 0 | 22,21 | — | — |
| Pico · recuperação | Corte até resultado disponível p50 | ms | 93 / 0 / 0 | 5502,38 | — | — |
| Pico · recuperação | Corte até resultado disponível p95 | ms | 93 / 0 / 0 | 26436,60 | — | — |
| Pico · recuperação | Fluxos concluídos | pedidos | 96 / 24 / 24 | 93 | 0 | 0 |
| Pico · recuperação | Fluxos falhados | pedidos | 96 / 24 / 24 | 3 | 24 | 24 |
| Pico · recuperação | Timeouts | pedidos | 96 / 24 / 24 | 3 | 24 | 24 |
| Pico · recuperação | Chegadas descartadas pelo cliente | pedidos | 150 / 150 / 150 | 54 | 126 | 126 |
| Pico · recuperação | Cortes disponíveis por minuto na janela | cortes/min | 123 / 19 / 20 | 98,40 | 15,20 | 16,00 |
| Pico · recuperação | Total na fila, máximo amostrado | mensagens | 148 / 147 / 146 | 38 | 57 | 58 |

#### Evolução da fila no pico de 75 s

Cada célula mostra `prontos / entregues sem ACK` na amostra disponível mais próxima, no máximo 1 s antes do instante indicado. Os valores negativos correspondem ao período anterior ao fim do pico. A fila ainda cresceu após o fim do pico de chegadas, enquanto pedidos em curso completavam o upload e a preparação do corte.

| Segundos desde o fim do pico | R1 | R2 | R3 |
| ---: | ---: | ---: | ---: |
| -9 | 0 / 0 | 0 / 0 | 0 / 0 |
| -3 | 7 / 1 | 3 / 1 | 2 / 1 |
| 0 | 7 / 1 | 4 / 1 | 3 / 1 |
| 10 | 37 / 1 | 4 / 1 | 3 / 1 |
| 20 | 18 / 1 | 2 / 1 | 2 / 1 |
| 30 | 8 / 1 | 45 / 1 | 57 / 1 |
| 45 | 9 / 1 | 52 / 1 | 50 / 1 |
| 60 | 10 / 1 | 47 / 1 | 44 / 1 |
| 74 | 10 / 1 | 49 / 1 | 48 / 1 |

## Regressão funcional

| Suite | Resultado | Cobertura exercitada |
| --- | --- | --- |
| Pytest do worker em `0523102` | 74 passaram | Corte, velocidade, áudio, efeitos, pré-visualização, legendas com modelo simulado, extração e atomicidade em falha. [JUnit](tests/performance/resultados-desempenho-inicial/video.xml) |
| Integração atual contra a API de `0523102` | 6 passaram | Corte e velocidade com áudio e original preservados, eventos de pré-visualização, vídeo sem áudio com legendas, extração de frames e ZIP, projeto misto, falha de processamento com preservação do resultado anterior. [TAP](tests/performance/resultados-desempenho-inicial/api-regressao.tap) |
| Node atual com os módulos de `0523102` | 18 passaram, 1 incompatível | Validação por perfil, ordenação e extração, registo em lote e proteção contra commit tardio após cancelamento. O caso de routing novo falha porque `resolveVideoWorkerTool` ainda não existe e a referência usa uma única `video_queue`. [TAP](tests/performance/resultados-desempenho-inicial/node-regressao.tap) |
| Pytest atual dos três workers separados | 3 suites bloqueadas na recolha | As suites importam `InvalidSpeed` de `effects` e `process_video` de `frame_extraction` e `subtitles`. A referência tem essas interfaces em `video_processor.py`. [Efeitos](tests/performance/resultados-desempenho-inicial/video_effects-compatibilidade.log) · [Frames](tests/performance/resultados-desempenho-inicial/video_frames-compatibilidade.log) · [Legendas](tests/performance/resultados-desempenho-inicial/video_subtitles-compatibilidade.log) |

O primeiro ensaio Node bloqueou um caso adicional devido aos caminhos de importação do runner. A repetição com acesso aos módulos originais de `models` e `controllers` passou esse caso. A regressão via API selecionou os seis casos de vídeo relevantes e excluiu 21 casos desse ficheiro, incluindo a transcrição de fala com o modelo real e a cadeia de efeitos de imagem. As restantes suites de API, interface, segurança e resiliência ficaram fora desta regressão focada. [Checklist e histórico](docs/REGRESSION_CHECKLIST.md)

## Reprodução e dados brutos

Executar na raiz da pasta de trabalho, com Docker Compose, Node, Python, FFmpeg/ffprobe e as dependências de teste existentes. Se os ficheiros de teste não estiverem gerados, usar `.venv/bin/python tests/fixtures/generate.py` e confirmar o SHA-256 do vídeo. Os comandos abaixo escrevem num novo destino.

```sh
tests/performance/benchmark/executar.sh 0523102 /tmp/picturas-medicao
tests/performance/benchmark/regressao-unitaria.sh 0523102 /tmp/picturas-medicao

PERF_REGRESSION=0 PERF_SCENARIOS=peak PERF_RECOVERY_SECONDS=75 \
  tests/performance/benchmark/executar.sh 0523102 /tmp/picturas-medicao/pico-estendido

python3 tests/performance/benchmark/resumir.py /tmp/picturas-medicao
python3 tests/performance/benchmark/resumir.py /tmp/picturas-medicao/pico-estendido peak
python3 tests/performance/benchmark/resumir.py /tmp/picturas-medicao/pico-estendido fila
```

As portas de loopback podem ser alteradas com `PERF_HTTPS_PORT` e `PERF_RABBIT_PORT`. Cada execução cria um nome Compose próprio e um worktree temporário. Os scripts definem a carga, os timeouts e o isolamento de portas. [Cliente](tests/performance/benchmark/carga.cjs) · [Override do Compose](tests/performance/benchmark/compose-isolado.yaml)

Cada diretório de repetição contém `warmup.jsonl`, `api.jsonl` com tempos, estados e auditoria, `rabbit.jsonl` com amostras da fila, `worker.log` com IDs e timestamps dos eventos, `stats.jsonl` com recursos por serviço, `*-mongo.jsonl` ou `*-mongo.jsonl.gz` com o profiler, `*-inicial.log` com as contagens iniciais, `images.txt` e `limites.txt`. O primeiro ensaio de carga baixa ficou sem amostras de `docker stats` devido ao formato da saída em streaming. O coletor foi corrigido antes das medições de recursos em carga mista e pico. [Dados brutos](tests/performance/resultados-desempenho-inicial/) · [Ambiente](tests/performance/resultados-desempenho-inicial/ambiente.txt)

Houve dois bloqueios antes do aquecimento da janela estendida. O primeiro comando de build omitia as dependências declaradas pelo Compose. Foi corrigido para usar `build --with-dependencies`. No arranque da repetição 2, o healthcheck do RabbitMQ esgotou as tentativas ainda durante a inicialização. Foi acrescentado um período de tolerância de 30 s antes de retomar as repetições em falta. [Build](tests/performance/resultados-desempenho-inicial/pico-estendido-arranque-interrompido/peak-1/startup.log) · [Healthcheck](tests/performance/resultados-desempenho-inicial/pico-estendido/arranque-repeticao-2-interrompido.log)

### Objetivo de otimização e instrumentação posterior

O objetivo específico de otimização ficou em aberto. A medição já fornece referências para tempo do corte, espera e execução no worker, débito e recursos. A imagem Docker do worker monolítico mede 1 707 637 814 B pelo campo `.Size`, cerca de 1,59 GiB. Um ensaio dedicado a queries, índices ou transações depende da identificação das operações a alterar. [Imagem do worker](tests/performance/resultados-desempenho-inicial/imagem-worker.txt)

Para o ensaio final, manter o vídeo e intervalo de corte, a carga, os critérios de recuperação, o modo de profiling e a cadência de amostragem. Aplicar os marcadores a cópias das fontes e montá-las no ambiente isolado. Marcar a publicação imediatamente antes de `channel.publish`, o início na entrada do callback e o fim após a função de processamento. Manter o ID de mensagem e projeto para juntar os eventos. Se o corte passar para um worker especializado, apontar os marcadores, os nomes de contentores e a amostragem RabbitMQ à fila que recebe `trim`. Comparar imagens de contentor pelos IDs e registar as versões de runtime, pois algumas imagens de base usam tags móveis. [Instrumentação](tests/performance/benchmark/instrumentar.py)


## Comparação com um vídeo de maior resolução

Foi feito um ensaio complementar de carga baixa com o vídeo original e um vídeo de 10 s em 720p. [Comparação e dados brutos](tests/performance/resultados-desempenho-inicial/comparacao-videos/README.md)
