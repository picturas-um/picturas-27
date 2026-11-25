# PictuRAS — comparação de regressão antes/depois

**Antes:** aplicação `0523102`, com a suite funcional de `25f4bd9`. **Depois:** `b8f44b3`, com workers de vídeo especializados, persistência do progresso e corte direto num único processo FFmpeg quando o pipeline contém apenas cortes.

**Regressão funcional.** Passaram nas duas versões 155 dos 158 casos emparelhados.

**Pico de 45 s.** O p95 até ao resultado passou de 15,64–17,27 s para 8,64–9,30 s. Os fluxos concluídos passaram de 381 para 423.

**Vídeo 720p.** A mediana até ao resultado passou de 1,108–1,118 s para 0,688–0,709 s.

## Regressão funcional

Os casos foram emparelhados pelo nome nos relatórios JUnit, retirando o prefixo com os identificadores dos requisitos. Os totais incluem os casos exclusivos de cada revisão.

| Suite | Antes | Depois | Comuns aprovados nas duas versões |
| --- | ---: | ---: | ---: |
| Node.js | 18/18 | 31/31 | 18/18 |
| Python | 83/83 | 63/65 | 58/58 |
| API | 36/36 | 36/36 | 36/36 |
| Integração | 30/30 | 30/31 | 29/30 |
| Segurança | 3/3 | 3/3 | 3/3 |
| Playwright | 11/11 | 9/11 | 9/11 |
| Backup/restauro | 1/1 | 1/1 | 1/1 |
| Orçamento local | 1/1 | 1/1 | 1/1 |
| **Total** | **183/183** | **174/179** | **155/158** |

### Casos comuns com resultados diferentes

- Integração · real image worker bg_remove_ai produces a decodable result · pass → failure.
- Playwright · edit resize apply and download actual browser results · pass → failure.
- Playwright · read-only shared project disables editing controls · pass → failure.

**Falhas conhecidas, fora do total:** 0/13 antes e 0/13 depois.

Dois casos Python de recuperação falharam na preparação ao procurar o ficheiro do worker monolítico. As restantes contagens vêm do JUnit desta execução.

A descoberta da suite Playwright completa ficou bloqueada na versão final. A tabela usa a execução separada dos cinco ficheiros já existentes na referência.

O caso de remoção de fundo excedeu o prazo na suite de integração e passou numa repetição isolada. O total conserva o resultado da primeira passagem.

No browser, a edição de imagem não devolveu resultado dentro do prazo e o teste da partilha de leitura não encontrou o botão Apply. A campanha regista ambas as falhas.

### Orçamento local de API e imagem

| Medição | Antes | Depois | Limite |
| --- | ---: | ---: | ---: |
| Leitura de projeto, p95 | 35,42 ms | 22,40 ms | 2000 ms |
| Redimensionamento até ao resultado | 258,84 ms | 247,69 ms | 30000 ms |

Uma execução por revisão. O caso consulta o projeto 20 vezes em lotes de quatro e redimensiona um PNG de 160 × 120.

## Desempenho de vídeo

Cada célula apresenta R1 / R2 / R3. O perfil de baixa carga usa p50 até ao resultado. Os restantes usam p95. As duas variantes de pico têm durações de recuperação diferentes. As latências incluem os resultados que o cliente chegou a observar. Os timeouts estão na tabela seguinte.

| Perfil | Corte antes (ms) | Corte depois (ms) | Worker antes, p95 (ms) | Worker depois, p95 (ms) | Débito antes / depois (cortes/min) |
| --- | ---: | ---: | ---: | ---: | --- |
| Baixa | 452,63 / 452,38 / 448,50 | 460,78 / 452,39 / 458,57 | 371,00 / 381,93 / 330,61 | 355,07 / 323,09 / 307,02 | — → — |
| Mista | 670,36 / 671,14 / 673,70 | 678,46 / 670,31 / 459,53 | 417,78 / 434,51 / 463,44 | 382,16 / 382,49 / 313,93 | 115,00 / 115,00 / 115,00 → 115,00 / 115,00 / 115,00 |
| Pico, recuperação de 45 s | 15642,87 / 16559,76 / 17273,69 | 8636,78 / 9085,17 / 9302,17 | 500,70 / 538,26 / 547,45 | 344,61 / 355,99 / 361,71 | 134,74 / 131,58 / 128,42 → 148,42 / 147,37 / 146,32 |
| Pico, recuperação de 75 s | 13415,25 / 13641,10 / 13676,44 | 9735,84 / 9560,48 / 10261,85 | 450,95 / 453,74 / 452,28 | 381,05 / 367,50 / 385,64 | 131,72 / 131,72 / 131,72 → 136,55 / 137,24 / 135,86 |
| Baixa, vídeo 720p | 1107,81 / 1111,16 / 1117,55 | 688,27 / 693,15 / 708,67 | 889,43 / 892,04 / 854,31 | 543,27 / 524,55 / 627,94 | — → — |

| Perfil | Concluídos / aceites | Timeouts | Descartes | Auditoria íntegra / aceites |
| --- | --- | ---: | ---: | --- |
| Baixa | 9/9 → 9/9 | 0 → 0 | 0 → 0 | — → — |
| Mista | 72/72 → 72/72 | 0 → 0 | 0 → 0 | — → — |
| Pico, recuperação de 45 s | 381/381 → 423/423 | 0 → 0 | 69 → 27 | 381/381 → 423/423 |
| Pico, recuperação de 75 s | 576/576 → 597/597 | 0 → 0 | 54 → 33 | 576/576 → 597/597 |
| Baixa, vídeo 720p | 9/9 → 9/9 | 0 → 0 | 0 → 0 | — → — |

| Pico | Espera p95 antes → depois (ms) | Recuperação incluindo drenagem antes → depois (s) |
| --- | --- | --- |
| 45 s | 14939,13 / 15921,64 / 16573,45 → 8193,06 / 8515,74 / 8762,51 | 45,84 / 46,03 / 46,75 → 45,77 / 45,78 / 45,77 |
| 75 s | 12786,75 / 13052,83 / 13131,26 → 9121,44 / 8971,89 / 9729,27 | 75,80 / 75,80 / 75,79 → 75,84 / 75,84 / 75,81 |

## Como foi executada a comparação

Cada fluxo cria uma conta e um projeto, carrega um vídeo, pede um corte de 0 a 2 s, consulta o resultado e descarrega-o. A entrada principal é um MP4 com 4 s, 160 × 120, H.264 e áudio AAC. Em 720p, usa-se o vídeo de 10 s do repositório. Cada repetição recria os volumes e executa quatro fluxos de aquecimento.

| Perfil | Carga programada | Limite de fluxos ativos por fase |
| --- | --- | ---: |
| Baixa | 0,5 fluxos/s por 6 s | 1 |
| Mista | 2 fluxos/s por 12 s | 12 |
| Pico | 2 fluxos/s por 6 s, 8 fluxos/s por 6 s e 2 fluxos/s durante a recuperação | 12 / 48 / 12 |

A recuperação dura 45 s no perfil padrão e 75 s no ensaio estendido. O cliente aguarda 200 ms entre consultas e regista os timeouts separadamente das chegadas descartadas antes de iniciar. O débito conta resultados produzidos durante a janela de chegadas. Os percentis usam o posto superior e são calculados por repetição. Em pico, o cliente audita a origem e unicidade do resultado de cada corte aceite.

**Ambiente da versão final:** AMD Ryzen 7 5800HS with Radeon Graphics, Docker 29.10.0, Compose v5.5.1, Node.js 22.22.1. Os ensaios correram em stacks Compose isoladas e por ordem sequencial. Para cada revisão, os logs registam o SHA-256 do vídeo, a configuração, os IDs das imagens de contentor e as amostras de latência e recursos. Os resultados comparam revisões completas. A reconstrução das imagens e a variação da carga do host limitam a atribuição das diferenças a uma alteração específica.

- [Protocolo e dados de referência](resultados-desempenho-inicial.md) · [Dados de desempenho e ambiente finais](tests/reports/comparacao-final/b8f44b3) · [JUnit e logs finais](tests/reports/comparacao-final/b8f44b3/funcional) · [Checklist](docs/REGRESSION_CHECKLIST.md).

A suite principal correu com `make test-all`. Os casos de falha conhecida correram com `make test-known-failures` depois da suite principal.

Os artefactos desta execução ficam em `tests/reports/`, que é ignorado pelo Git.
