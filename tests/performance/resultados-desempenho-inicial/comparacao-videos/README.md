# Comparação de desempenho com um vídeo maior

Ensaio complementar no commit `052310226c51fa57a17101c7bd1ad795674aac95` (`0523102`).

| Vídeo | Tamanho | Duração | Resolução | Frequência |
| --- | ---: | ---: | ---: | ---: |
| `tests/fixtures/videos/clip.mp4` | 49 065 B | 4 s | 160 × 120 | 10 fps |
| `samples/video/sample_10s_720p.mp4` | 3 885 435 B (3,71 MiB) | 10 s | 1280 × 720 | 30 fps |

Os dois ficheiros têm vídeo H.264 e áudio AAC. Foi aplicado o mesmo corte de 0 a 2 s, com um único worker e o cenário de carga baixa. Para cada vídeo foram planeadas três chegadas por repetição, distribuídas por 6 s, com um fluxo ativo de cada vez. Os volumes foram repostos em cada repetição e foram feitos quatro fluxos de aquecimento com o mesmo vídeo. A consulta de estado usou o intervalo de 200 ms do ensaio original.

O ficheiro 720p tem cerca de 79 vezes mais bytes. A resolução, a duração de origem e a frequência de fotogramas também variam, pelo que esta comparação mede o efeito combinado dessas diferenças no fluxo de corte.

## Resultados

Concluíram 9 fluxos com o vídeo pequeno e 8 com o vídeo 720p, todos com download e sem falhas ou timeouts. Na terceira repetição em 720p, o cliente descartou uma chegada porque o fluxo anterior ainda estava ativo. As medianas abaixo usam os fluxos concluídos e estão em milissegundos.

| Operação | Pequeno (9 amostras) | 720p (8 amostras) |
| --- | ---: | ---: |
| Upload | 111,75 | 275,89 |
| Pedido de corte HTTP | 27,55 | 51,96 |
| Pedido até ao resultado | 666,98 | 1354,63 |
| Download | 3,53 | 20,02 |
| Processamento no worker | 404,90 | 1194,87 |

| Vídeo | Repetição | Amostras | Upload | Pedido HTTP | Até ao resultado | Download | Worker |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| pequeno | 1 | 3 | 109,50 | 26,65 | 664,58 | 3,62 | 404,90 |
| pequeno | 2 | 3 | 111,75 | 27,55 | 666,38 | 3,53 | 389,86 |
| pequeno | 3 | 3 | 117,83 | 29,80 | 669,42 | 3,32 | 410,15 |
| 720p | 1 | 3 | 253,70 | 44,75 | 1343,44 | 14,62 | 1016,16 |
| 720p | 2 | 3 | 262,36 | 51,86 | 1356,14 | 20,28 | 1202,26 |
| 720p | 3 | 2 | 319,23 | 68,56 | 2535,15 | 32,85 | 2293,83 |

O tempo até ao resultado inclui a espera até à próxima consulta de estado. Os dois vídeos foram repetidos nesta sessão para usar medições próximas no tempo.

## Reprodução

Executar na raiz do repositório.

```sh
destino=$(mktemp -d)
PERF_SCENARIOS=low PERF_REGRESSION=0 PERF_VIDEO=tests/fixtures/videos/clip.mp4 \
  tests/performance/benchmark/executar.sh 0523102 "$destino/pequeno"
PERF_SCENARIOS=low PERF_REGRESSION=0 PERF_VIDEO=samples/video/sample_10s_720p.mp4 \
  tests/performance/benchmark/executar.sh 0523102 "$destino/720p"
```

Os registos de cada repetição estão em [pequeno/](pequeno/) e [720p/](720p/).
