# PictuRAS — referência inicial repetida

A campanha mede a aplicação inicial `0523102`. A referência funcional usa `25f4bd9`, que acrescenta a suite de testes à mesma aplicação. As medições históricas permanecem no respetivo diretório de dados brutos.

**Ambiente da carga:** AMD Ryzen 7 5800HS with Radeon Graphics, Docker 29.10.0, Compose v5.5.1, Node.js 22.22.1. O worker monolítico é o único consumidor de vídeo.

## Carga e métricas

Cada fluxo cria uma conta e um projeto, carrega um vídeo, pede um corte de 0 a 2 s, consulta o resultado e descarrega-o. A entrada principal é um MP4 com 4 s, 160 × 120, H.264 e áudio AAC. Em 720p, usa-se o vídeo de 10 s do repositório. Cada repetição recria os volumes e executa quatro fluxos de aquecimento.

| Perfil | Carga programada | Limite de fluxos ativos por fase |
| --- | --- | ---: |
| Baixa | 0,5 fluxos/s por 6 s | 1 |
| Mista | 2 fluxos/s por 12 s | 12 |
| Pico | 2 fluxos/s por 6 s, 8 fluxos/s por 6 s e 2 fluxos/s durante a recuperação | 12 / 48 / 12 |

A recuperação dura 45 s no perfil padrão e 75 s no ensaio estendido. O cliente aguarda 200 ms entre consultas e regista os timeouts separadamente das chegadas descartadas antes de iniciar. O débito conta resultados produzidos durante a janela de chegadas. Os percentis usam o posto superior e são calculados por repetição. Em pico, o cliente audita a origem e unicidade do resultado de cada corte aceite.

## Resultados da referência

| Perfil | Repetições | Concluídos / aceites | Timeouts | Descartes | Resultados auditados / aceites |
| --- | ---: | ---: | ---: | ---: | ---: |
| Baixa | 3 | 9/9 | 0 | 0 | — |
| Mista | 3 | 72/72 | 0 | 0 | — |
| Pico, recuperação de 45 s | 3 | 381/381 | 0 | 69 | 381/381 |
| Pico, recuperação de 75 s | 3 | 576/576 | 0 | 54 | 576/576 |
| Baixa, vídeo 720p | 3 | 9/9 | 0 | 0 | — |

Os valores abaixo estão pela ordem R1 / R2 / R3. O tempo até ao resultado usa p50 em carga baixa e p95 nos restantes perfis. «—» indica que a métrica não foi recolhida ou que a condição de recuperação ficou por observar.

| Perfil | Corte até ao resultado (ms) | Worker p95 (ms) | Espera p95 (ms) | Débito (cortes/min) | Recuperação incluindo drenagem (s) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Baixa | 452,63 / 452,38 / 448,50 | 371,00 / 381,93 / 330,61 | 1,25 / 1,69 / 1,21 | — | — |
| Mista | 670,36 / 671,14 / 673,70 | 417,78 / 434,51 / 463,44 | 56,97 / 1,78 / 1,72 | 115,00 / 115,00 / 115,00 | — |
| Pico, recuperação de 45 s | 15642,87 / 16559,76 / 17273,69 | 500,70 / 538,26 / 547,45 | 14939,13 / 15921,64 / 16573,45 | 134,74 / 131,58 / 128,42 | 45,84 / 46,03 / 46,75 |
| Pico, recuperação de 75 s | 13415,25 / 13641,10 / 13676,44 | 450,95 / 453,74 / 452,28 | 12786,75 / 13052,83 / 13131,26 | 131,72 / 131,72 / 131,72 | 75,80 / 75,80 / 75,79 |
| Baixa, vídeo 720p | 1107,81 / 1111,16 / 1117,55 | 889,43 / 892,04 / 854,31 | 1,19 / 1,65 / 1,55 | — | — |

## Referência funcional

| Suite | Aprovados / executados |
| --- | ---: |
| Node.js | 18/18 |
| Python | 83/83 |
| API | 36/36 |
| Integração | 30/30 |
| Segurança | 3/3 |
| Playwright | 11/11 |
| Backup/restauro | 1/1 |
| Orçamento local | 1/1 |
| Falhas conhecidas (suite separada) | 0/13 |

## Evidência e reprodução

- A carga usa `tests/performance/benchmark/executar.sh` com Compose isolado, uma tolerância de 90 s no arranque do RabbitMQ e `PERF_REGRESSION=0`. A configuração preserva as taxas e os limites do cliente. As séries usam as opções padrão, `PERF_SCENARIOS=peak PERF_RECOVERY_SECONDS=75` e `PERF_SCENARIOS=low PERF_VIDEO=samples/video/sample_10s_720p.mp4`, respetivamente.
- [Dados e ambiente da carga repetida](tests/reports/comparacao-final/0523102) · [Dados da campanha histórica](tests/performance/resultados-desempenho-inicial) · [JUnit e logs da referência funcional](tests/reports/comparacao-final/25f4bd9/funcional).
- [Comparação com a versão final](resultados-regressao-atual.md).

A suite principal correu com `make test-all`. Os casos de falha conhecida correram com `make test-known-failures` depois da suite principal.

Os artefactos desta execução ficam em `tests/reports/`, que é ignorado pelo Git.
