#import "../template.typ": *

// Capítulo inteiro na horizontal (tabelas largas). Para voltar ao vertical, retirar o #paisagem[ ].
#paisagem[
= Candidatos a Requisitos Não Funcionais

#orientacao[
  *Origem:* Exercício 6, Bloco 2, secção 5 do _template_.

  *Objetivo do capítulo:* escolher *dois* requisitos não funcionais *distintos* a melhorar nesta fase, a partir dos
  cenários de qualidade mais prioritários do capítulo 5. Cada um é classificado segundo a ISO/IEC 25010 (característica e,
  quando aplicável, subcaracterística) e parte de uma fragilidade concreta da solução de base, com evidência.

  Cada candidato é depois especificado, implementado e avaliado por si, ainda que os dois possam estar relacionados.
  A coluna do cenário liga o candidato ao `QS-nn` do capítulo 5, que é a entrada do Exercício 7 (capítulo 7).
]

#tab([Candidatos a requisitos não funcionais da Fase 2],
  tabela(
    colunas: (1.6cm, 2.6cm, 3cm, 2.4cm, 2.8cm, 2.6cm, 2cm, 3cm, 2.8cm),
    tamanho: 7.5pt,
    [\#], [Característica / subcaracterística (ISO/IEC 25010)], [Fragilidade na base (evidência)], [Origem (padrão global / vídeo / interação)], [Impacto nos stakeholders (pertinência)], [Exigência técnica (complexidade)], [Cenário (`QS-nn`, cap. 5)], [Escala e método de medição (esboço)], [Pré-requisitos / efeitos colaterais],
    [CAND-1], [#preencher[…]], [#preencher[… (EV-nn)]], [#preencher[…]], [#preencher[…]], [#preencher[…]], [#preencher[QS-nn]], [#preencher[…]], [#preencher[…]],
    [CAND-2], [#preencher[…]], [#preencher[… (EV-nn)]], [#preencher[…]], [#preencher[…]], [#preencher[…]], [#preencher[QS-nn]], [#preencher[…]], [#preencher[…]],
  ),
)

== Quantificação

#orientacao[
  Indiquem a *escala* (o que se mede e em que unidade) e o *método de medição* (cenário, carga, ambiente e instrumento) de
  cada candidato. O objetivo é mostrar que o requisito é mensurável e que sabem como o medir.

  Os valores medidos na base, os valores-alvo e os valores mínimos aceitáveis *só são fixados após a medição inicial
  (_baseline_, capítulo 10)*. Não os inventem: preencham as três últimas linhas da tabela só depois de medir a base,
  indicando a origem de cada valor (e.g., medição, referência externa, necessidade de um _stakeholder_).
]

#tab([Quantificação dos requisitos não funcionais],
  tabela(
    colunas: (4.2cm, 1fr, 1fr),
    [], [CAND-1], [CAND-2],
    [Escala (o que se mede e em que unidade)], [#preencher[…]], [#preencher[…]],
    [Cenário de medição], [#preencher[…]], [#preencher[…]],
    [Carga], [#preencher[…]], [#preencher[…]],
    [Ambiente], [#preencher[…]], [#preencher[…]],
    [Instrumento], [#preencher[…]], [#preencher[…]],
    [Valor medido na base], [#preencher[após a medição inicial]], [#preencher[após a medição inicial]],
    [Valor-alvo (e origem)], [#preencher[…]], [#preencher[…]],
    [Valor mínimo aceitável (e origem)], [#preencher[…]], [#preencher[…]],
  ),
)

== Relação entre os dois candidatos

#preencher[Um é condição do outro? A melhoria de um pode degradar o outro? Que outros RNF podem ser afetados? (3 a 6 linhas)]

== Evidência exploratória (se existir)

#tab([Evidência exploratória],
  tabela(
    colunas: (4cm, 5cm, 1fr),
    [Descrição], [Localização (_scripts_, dados, resultados)], [Como repetir],
    [#preencher[…]], [#preencher[…]], [#preencher[…]],
  ),
)
]
