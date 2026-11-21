#import "../template.typ": *

= Introdução

#orientacao[
  Uma a duas páginas, no máximo. O leitor deve perceber, sem ler o resto, o que é este documento e em que se baseia.
  Respondam a:
  - *Propósito da fase*: que requisitos não funcionais do PictuRAS se pretende melhorar, por _refactoring_ e sem novas
    funcionalidades, e porquê.
  - *_Baseline_*: em que versão do sistema se basearam (_commit_ de partida), a mesma em todos os exercícios. Este
    relatório *estende* os documentos de base; não os reescreve.
  - *Âmbito do que é apresentado*: este relatório reúne os contributos dos Exercícios 6 (Blocos 1 e 2) e 7. Reutiliza
    os respetivos _templates_: copiem o conteúdo já preenchido, *mantendo os IDs* (`EV`, `H`, `ALT`, `QS`, `CAND`,
    `TAT`, `DA`), porque é através deles que os capítulos se encadeiam.
  - *Organização do documento*: Partes II (diagnóstico), III (qualidade), IV (táticas, decisões, medição e resultados)
    e V (síntese).
]

== Propósito e âmbito
#preencher[Que RNF se pretende melhorar, em que parte da solução (extensão de vídeo, enquadrada no padrão global) e com que restrições (_refactoring_ que preserva o comportamento funcional).]

== _Baseline_ e repositório
#tab([Artefactos de partida],
  tabela(
    colunas: (5cm, 1fr),
    [Artefacto], [Versão / referência],
    [Documento de requisitos de base], [doc-ext-requisitos-2627.pdf],
    [Documento de solução arquitetural de base], [doc-sol-arquitetural.pdf],
    [Repositório de partida], [#preencher[URL e _commit_ de partida (`git rev-parse HEAD`)]],
    [Repositório entregue], [#preencher[URL e _commit_ da entrega]],
    [Diretrizes da Fase 2], [#preencher[versão]],
  ),
)

== Exercícios e versões usadas

#orientacao[
  Indiquem, para cada exercício, a versão do enunciado e do _template_ que usaram, e a versão do vosso documento que
  serviu de entrada ao exercício seguinte (Bloco 1 → Bloco 2 → Exercício 7). Isto garante que quem avalia consegue
  perceber a que regras o trabalho respondeu, caso os enunciados tenham sido atualizados durante a fase.
]

#tab([Exercícios que alimentam este relatório],
  tabela(
    colunas: (3.6cm, 2.2cm, 2cm, 2cm, 1fr),
    [Exercício], [Capítulos], [Enunciado], [Template], [Versão do documento da equipa],
    [Exercício 6, Bloco 1: padrões arquiteturais], [2, 3 e 4], [#preencher[1.1]], [#preencher[1.1]], [#preencher[v1.0]],
    [Exercício 6, Bloco 2: trade-offs, cenários e candidatos a RNF], [5 e 6], [#preencher[1.2]], [#preencher[1.2]], [#preencher[v1.0]],
    [Exercício 7: táticas arquiteturais], [7 a 10], [#preencher[3.0]], [#preencher[3.0]], [#preencher[v1.0]],
  ),
)

== Organização do documento
#preencher[Resumo, em poucas linhas, do que contém cada Parte e de como os IDs encadeiam os capítulos (`EV`/`H` → `ALT` → `QS`/`CAND` → `TAT` → `DA`).]
