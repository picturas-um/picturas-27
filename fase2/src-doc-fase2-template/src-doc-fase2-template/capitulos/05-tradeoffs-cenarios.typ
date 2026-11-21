#import "../template.typ": *

= Trade-offs, Cenários de Qualidade e Prioridades

#orientacao[
  *Origem:* Exercício 6, Bloco 2, secção 4 do _template_ (sem a justificação detalhada da matriz, que não faz parte
  deste relatório).

  *Objetivo do capítulo:* transformar o diagnóstico dos capítulos 2 a 4 em cenários de qualidade concretos e
  verificáveis, priorizá-los e perceber como os atributos se afetam uns aos outros.

  *Princípio central:* a caracterização dos cenários de qualidade *deve basear-se na identificação de fragilidades do
  sistema atual*. Cada cenário parte de uma fragilidade concreta, com evidência (`EV-nn`), observada na solução de
  base (e.g., uma falha sem recuperação, um ponto de contenção, uma dependência rígida). Um cenário sem fragilidade
  identificada é uma preferência, não uma necessidade. Reutilizem os `EV`, `H` e `ALT` já usados, sem os alterar.

  *Este é o único sítio onde os cenários de qualidade se caracterizam:* os capítulos 6 a 10 usam-nos sem os reescrever.
]

== Cenários de qualidade para a extensão de vídeo

#orientacao[
  Para cada fragilidade relevante, escrevam um cenário com os *seis elementos*:
  - *fonte do estímulo*: quem ou o que o origina (utilizador, serviço, falha de infraestrutura);
  - *estímulo*: o evento a que o sistema tem de reagir;
  - *artefacto*: a parte do sistema afetada;
  - *ambiente*: em que condições (carga normal, pico, degradado);
  - *resposta*: o que o sistema deve fazer;
  - *medida da resposta*: como se verifica, com métrica e escala. Definem-na vocês e tem de ser *verificável*.

  A coluna *Fragilidade* liga o cenário à evidência que o justifica. Não inventem valores de _baseline_, alvo ou
  mínimo: esses fixam-se após a medição inicial. A medida da resposta indica o que se mede, não o valor a atingir.
]

#paisagem[
#tab([Cenários de qualidade],
  tabela(
    colunas: (1.2cm, 3.4cm, 2.6cm, 2.2cm, 2.2cm, 2.4cm, 2.2cm, 2.6cm, 3cm),
    tamanho: 7.5pt,
    [ID], [Fragilidade na base (EV-nn)], [Característica (ISO/IEC 25010)], [Fonte do estímulo], [Estímulo], [Artefacto], [Ambiente], [Resposta], [Medida da resposta],
    [QS-01], [#preencher[… (EV-nn)]], [#preencher[…]], [#preencher[…]], [#preencher[…]], [#preencher[…]], [#preencher[…]], [#preencher[…]], [#preencher[…]],
    [QS-02], [#preencher[… (EV-nn)]], [#preencher[…]], [#preencher[…]], [#preencher[…]], [#preencher[…]], [#preencher[…]], [#preencher[…]], [#preencher[…]],
    [QS-03], [#preencher[… (EV-nn)]], [#preencher[…]], [#preencher[…]], [#preencher[…]], [#preencher[…]], [#preencher[…]], [#preencher[…]], [#preencher[…]],
  ),
)
]

#orientacao[
  *Priorização.* Avaliem cada cenário em duas dimensões: a *importância para os stakeholders* (quem sofre com a
  fragilidade e quanto) e a *dificuldade ou risco técnico* de a resolver. Justifiquem cada avaliação em poucas palavras
  e atribuam uma ordem de prioridade (1 = mais prioritário). Os dois cenários mais prioritários, e que dão origem aos
  candidatos a RNF do capítulo 6, são os mais importantes e viáveis, não necessariamente os mais fáceis.
]

#tab([Priorização dos cenários],
  tabela(
    colunas: (1.6cm, 4.8cm, 4.8cm, 2cm),
    [ID], [Importância para os stakeholders], [Dificuldade / risco técnico], [Prioridade],
    [QS-01], [#preencher[Alta / Média / Baixa — porquê]], [#preencher[Alta / Média / Baixa — porquê]], [#preencher[1..N]],
    [QS-02], [#preencher[…]], [#preencher[…]], [#preencher[…]],
    [QS-03], [#preencher[…]], [#preencher[…]], [#preencher[…]],
  ),
)

== Atributos de qualidade por ordem de prioridade

#orientacao[
  Com base nos cenários mais importantes, ordenem os atributos de qualidade (ISO/IEC 25010) do mais para o menos
  prioritário, indicando os cenários que justificam cada posição. A ordem tem de ser coerente com a tabela de
  priorização acima.
]

+ #preencher[Atributo — cenários QS-nn; justificação]
+ #preencher[Atributo — …]
+ #preencher[Atributo — …]

== Pré-requisitos e efeitos colaterais entre atributos

#orientacao[
  Os atributos não são independentes. Identifiquem os pares em que melhorar um é *pré-requisito* do outro (e.g.,
  observabilidade antes de otimizar desempenho), em que há *sinergia*, ou em que há *conflito* (melhorar um degrada
  o outro). Expliquem a razão e, se possível, citem evidência.
]

#tab([Pré-requisitos e efeitos colaterais entre atributos],
  tabela(
    colunas: (2.8cm, 2.8cm, 4cm, 1fr),
    [Atributo A], [Atributo B], [Efeito (pré-requisito, sinergia ou conflito)], [Razão / evidência],
    [#preencher[…]], [#preencher[…]], [#preencher[…]], [#preencher[…]],
    [#preencher[…]], [#preencher[…]], [#preencher[…]], [#preencher[…]],
  ),
)

== Recomendações de melhoria à solução atual

#orientacao[
  Recomendações concretas que respondem às fragilidades identificadas, indicando o atributo que melhoram, o padrão
  (global ou vídeo) a que se aplicam, o esforço estimado e o risco de regressão. Esta fase é de _refactoring_: as
  recomendações têm de poder ser aplicadas sem acrescentar funcionalidades.
]

#tab([Recomendações de melhoria],
  tabela(
    colunas: (1fr, 2.6cm, 3cm, 1.8cm, 2.2cm),
    tamanho: 8.5pt,
    [Recomendação], [Atributo(s)], [Padrão a que se refere (global / vídeo)], [Esforço], [Risco de regressão],
    [#preencher[…]], [#preencher[…]], [#preencher[…]], [#preencher[Baixo / Médio / Alto]], [#preencher[Baixo / Médio / Alto]],
    [#preencher[…]], [#preencher[…]], [#preencher[…]], [#preencher[…]], [#preencher[…]],
  ),
)
