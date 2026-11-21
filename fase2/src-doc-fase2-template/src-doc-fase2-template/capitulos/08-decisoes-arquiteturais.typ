#import "../template.typ": *

= Decisões Arquiteturais

#orientacao[
  *Origem:* Exercício 7, secção 3 do _template_.

  Uma decisão por cenário (`DA-1` para `QS-01`, `DA-2` para `QS-02`). Cada decisão é um pequeno registo, ao estilo ADR: o
  contexto, a tática escolhida, a estrutura ou padrão que a realiza, as alternativas consideradas e a razão da sua
  rejeição, as consequências positivas e negativas, e os elementos arquiteturais afetados.

  Só vale a pena registar uma decisão se havia *alternativas reais* (as táticas do capítulo 7 que não foram escolhidas).
  Justifiquem a escolha pelo cenário e pelas restrições da fase: rejeitem as táticas de classe C, porque a fase é de
  _refactoring_, e avaliem o risco de regressão do âmbito da alteração.

  *Depois de implementada*, completem cada decisão com as referências da implementação (_commits_ ou _pull requests_ no
  repositório entregue) e com os desvios face ao que foi decidido, explicando porquê. A vista «depois» do capítulo 9
  deve corresponder ao que foi efetivamente implementado.
]

== DA-1 — #preencher[título] (cenário #preencher[QS-01])

#tab([Decisão arquitetural DA-1],
  tabela-campos(
    [Contexto], [#preencher[fragilidade, cenário, restrições (_refactoring_, preservar comportamento)]],
    [Tática(s) escolhida(s)], [#preencher[TAT-nn]],
    [Estrutura / padrão que a realiza], [#preencher[e.g., réplicas do _worker_; _Circuit Breaker_; … ou «n/a»]],
    [Alternativas consideradas e razão de rejeição], [#preencher[TAT-nn: …] · #preencher[TAT-nn: …]],
    [Consequências positivas], [#preencher[…]],
    [Consequências negativas / riscos], [#preencher[…]],
    [Elementos arquiteturais afetados], [#preencher[serviços, filas, ficheiros de configuração, módulos]],
    [Origem e âmbito do _refactoring_], [#preencher[padrão global / padrão do vídeo / interação; risco de regressão]],
    [Classe (A/B/C)], [#preencher[A ou B; justificação]],
    [Implementação (_commits_ / _pull requests_)], [#preencher[referências no repositório entregue]],
    [Desvios face à decisão], [#preencher[o que mudou na implementação e porquê, ou «nenhum»]],
  ),
)

== DA-2 — #preencher[título] (cenário #preencher[QS-02])

#tab([Decisão arquitetural DA-2],
  tabela-campos(
    [Contexto], [#preencher[…]],
    [Tática(s) escolhida(s)], [#preencher[TAT-nn]],
    [Estrutura / padrão que a realiza], [#preencher[…]],
    [Alternativas consideradas e razão de rejeição], [#preencher[…]],
    [Consequências positivas], [#preencher[…]],
    [Consequências negativas / riscos], [#preencher[…]],
    [Elementos arquiteturais afetados], [#preencher[…]],
    [Origem e âmbito do _refactoring_], [#preencher[…]],
    [Classe (A/B/C)], [#preencher[…]],
    [Implementação (_commits_ / _pull requests_)], [#preencher[…]],
    [Desvios face à decisão], [#preencher[…]],
  ),
)
