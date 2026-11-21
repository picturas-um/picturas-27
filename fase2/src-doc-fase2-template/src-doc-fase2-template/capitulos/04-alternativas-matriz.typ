#import "../template.typ": *

= Alternativas e Matriz de Comparação

#orientacao[
  *Origem:* Exercício 6, Bloco 1, secção 3 do _template_.

  *Objetivo do capítulo:* comparar o padrão atual com alternativas relevantes *para o processamento de vídeo*, de forma
  fundamentada, e concluir se o padrão atual é adequado. Entre duas e três alternativas. O padrão global é o contexto da
  comparação: indiquem sempre se cada alternativa o *mantém* ou o *altera*.

  *Restrição da fase:* é de _refactoring_. As alternativas têm de preservar o comportamento funcional; por isso, o
  custo e o risco de migração têm de ser analisados para cada uma. Consultem os slides da aula 11 e o documento de apoio
  de padrões arquiteturais; se for relevante, incluam uma alternativa ao próprio padrão global como termo de comparação.
]

== Alternativas consideradas

#tab([Alternativas consideradas],
  tabela(
    colunas: (1.6cm, 3.4cm, 1fr, 3cm, 2.4cm),
    tamanho: 8.5pt,
    [ID], [Nome / padrão], [Descrição breve], [Mantém ou altera o padrão global?], [Fonte],
    [ALT-1], [#preencher[…]], [#preencher[…]], [#preencher[Mantém / Altera / Afasta-se parcialmente]], [#preencher[…]],
    [ALT-2], [#preencher[…]], [#preencher[…]], [#preencher[…]], [#preencher[…]],
    [ALT-3 (opcional)], [#preencher[…]], [#preencher[…]], [#preencher[…]], [#preencher[…]],
  ),
)

== Análise de cada alternativa

#orientacao[
  Copiem o bloco abaixo para cada alternativa. Para cada uma, descrevam a coerência com o padrão global, o efeito nos
  atributos de qualidade, as vantagens, as desvantagens ou riscos, e o custo e risco de migração. Evitem listas
  genéricas: cada ponto deve referir algo concreto da solução do PictuRAS (e citar evidência `EV-nn` ou hipótese `H-nn`).
]

*ALT-1 — #preencher[nome]*

#tabela-campos(
  [Coerência com o padrão global], [#preencher[…]],
  [Efeito nos atributos de qualidade], [#preencher[…]],
  [Vantagens potenciais], [#preencher[…]],
  [Desvantagens ou riscos], [#preencher[…]],
  [Custo e risco de migração (a funcionalidade existente tem de ser preservada)], [#preencher[…]],
)

*ALT-2 — #preencher[nome]*

#tabela-campos(
  [Coerência com o padrão global], [#preencher[…]],
  [Efeito nos atributos de qualidade], [#preencher[…]],
  [Vantagens potenciais], [#preencher[…]],
  [Desvantagens ou riscos], [#preencher[…]],
  [Custo e risco de migração], [#preencher[…]],
)

== Matriz de comparação de padrões

#orientacao[
  Atribuam um nível a cada atributo para o padrão global (referência), para o padrão atual do vídeo e para cada
  alternativa. A escala é à vossa escolha (e.g., Alto / Médio / Baixo) e deve ser a mesma em toda a matriz.

  *Justifiquem cada célula* com evidência da solução (`EV-nn` ou `H-nn`) numa frase curta, logo na própria célula: as
  avaliações sem fundamento não são valorizadas. A matriz inclui o padrão global como referência para se ver o que
  cada alternativa ganha ou perde em relação a ele. Os atributos e subcaracterísticas seguem a ISO/IEC 25010; podem
  acrescentar linhas para outros atributos relevantes.
]

#paisagem[
#tab([Matriz de comparação de padrões],
  tabela(
    colunas: (5.6cm, 4.2cm, 4cm, 4cm, 4cm),
    tamanho: 8.5pt,
    [Atributo de qualidade (ISO/IEC 25010)], [Padrão global atual (referência)], [Padrão atual do vídeo], [ALT-1], [ALT-2],
    [Relação com o padrão global], [—], [#preencher[Segue / Afasta-se]], [#preencher[Mantém / Altera]], [#preencher[Mantém / Altera]],
    [Eficiência de desempenho: comportamento temporal], [#preencher[nível — justificação (EV-nn)]], [#preencher[…]], [#preencher[…]], [#preencher[…]],
    [Eficiência de desempenho: capacidade / elasticidade], [#preencher[…]], [#preencher[…]], [#preencher[…]], [#preencher[…]],
    [Fiabilidade: tolerância a falhas / recuperabilidade], [#preencher[…]], [#preencher[…]], [#preencher[…]], [#preencher[…]],
    [Manutenibilidade: modularidade / modificabilidade], [#preencher[…]], [#preencher[…]], [#preencher[…]], [#preencher[…]],
    [Segurança], [#preencher[…]], [#preencher[…]], [#preencher[…]], [#preencher[…]],
    [Usabilidade: operabilidade], [#preencher[…]], [#preencher[…]], [#preencher[…]], [#preencher[…]],
  ),
)
]

== Adequação do padrão atual

#preencher[Justificação de por que o padrão atual (global e do vídeo) é mais ou menos adequado do que as alternativas, considerando os requisitos não funcionais identificados (5 a 10 linhas).]
