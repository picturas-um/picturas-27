#import "../template.typ": *

// Capítulo inteiro na horizontal (tabelas largas). Para voltar ao vertical, retirar o #paisagem[ ].
#paisagem[
= Cenários de Entrada e Táticas Candidatas

#orientacao[
  *Origem:* Exercício 7, secções 1 e 2 do _template_.

  *Objetivo do capítulo:* partir dos dois cenários já caracterizados e identificar as táticas arquiteturais que os podem
  melhorar. Os cenários vêm do capítulo 5 e os candidatos do capítulo 6 (`QS-nn`, `CAND-n`) e *não são reescritos*: o
  capítulo 5 é o único sítio onde os cenários se caracterizam. Se tiverem de corrigir uma medida da resposta, corrijam-na
  no capítulo 5 e registem a alteração na secção 7.2.

  Nas tabelas seguintes, `QS-01` e `QS-02` designam os cenários de `CAND-1` e `CAND-2`: substituam-nos pelos IDs reais.
]

== Candidatos e cenários de entrada

#tab([Candidatos e cenários de entrada],
  tabela(
    colunas: (1.8cm, 2.2cm, 3cm, 1.8cm, 2.8cm, 3cm, 3.4cm, 3.4cm),
    tamanho: 8pt,
    [Candidato], [Cenário (`QS-nn`)], [Característica / subcaracterística (ISO/IEC 25010)], [Evidência], [Origem (padrão global / vídeo / interação)], [Estímulo a que a tática reage], [Resposta e medida (resumo)], [Escala e método (cap. 6)],
    [CAND-1], [#preencher[QS-nn]], [#preencher[…]], [#preencher[EV-nn]], [#preencher[…]], [#preencher[…]], [#preencher[…]], [#preencher[…]],
    [CAND-2], [#preencher[QS-nn]], [#preencher[…]], [#preencher[EV-nn]], [#preencher[…]], [#preencher[…]], [#preencher[…]], [#preencher[…]],
  ),
)

== Alterações feitas ao capítulo 5 (se existirem)

#tab([Alterações aos cenários],
  tabela(
    colunas: (2cm, 1fr, 4cm),
    [Cenário], [O que mudou e porquê], [Onde foi atualizado],
    [#preencher[QS-nn]], [#preencher[…]], [#preencher[…]],
  ),
)

== Táticas candidatas

#orientacao[
  Identifiquem *pelo menos três táticas por cenário*, de categorias de atributo adequadas (e.g., Desempenho → gerir
  recursos; Disponibilidade → recuperar de falhas). Para cada tática, expliquem como produz a resposta pretendida
  (estímulo → tática → resposta) e se já existe, total ou parcialmente, na base (com evidência).

  Classifiquem cada tática: *A* = _refactoring_ puro; *B* = alteração visível que é o objeto da melhoria; *C* =
  funcionalidade nova, a *rejeitar* nesta fase. Táticas de classe C podem constar da lista, mas não podem ser escolhidas.
]

#tab([Táticas candidatas],
  tabela(
    colunas: (1.6cm, 1.8cm, 3.6cm, 3.4cm, 5cm, 3.4cm, 1.8cm),
    tamanho: 8pt,
    [ID], [Cenário], [Atributo → categoria], [Tática], [Como produz a resposta (estímulo → tática → resposta)], [Já existe na base? (evidência)], [Classe (A/B/C)],
    [TAT-01], [QS-01], [#preencher[e.g., Desempenho → gerir recursos]], [#preencher[…]], [#preencher[…]], [#preencher[Sim / Parcial / Não — EV-nn]], [#preencher[A]],
    [TAT-02], [QS-01], [#preencher[…]], [#preencher[…]], [#preencher[…]], [#preencher[…]], [#preencher[…]],
    [TAT-03], [QS-01], [#preencher[…]], [#preencher[…]], [#preencher[…]], [#preencher[…]], [#preencher[…]],
    [TAT-04], [QS-02], [#preencher[…]], [#preencher[…]], [#preencher[…]], [#preencher[…]], [#preencher[…]],
    [TAT-05], [QS-02], [#preencher[…]], [#preencher[…]], [#preencher[…]], [#preencher[…]], [#preencher[…]],
    [TAT-06], [QS-02], [#preencher[…]], [#preencher[…]], [#preencher[…]], [#preencher[…]], [#preencher[…]],
  ),
)
]
