#import "../template.typ": *

= Âmbito e Vista da Arquitetura

#orientacao[
  *Origem:* Exercício 6, Bloco 1, secções 0 e 1 do _template_ (preparação, fontes, vista global e sequência).

  *Objetivo do capítulo:* situar o leitor. Mostra como a solução foi lançada, em que fontes se baseia a análise e como é
  a arquitetura da solução de base, com o caminho do vídeo em destaque. É a base factual dos capítulos seguintes.

  *Foco:* a *extensão de vídeo, enquadrada no padrão global* da solução. Não analisem o vídeo isoladamente: o que o vídeo
  faz só se percebe à luz do que a solução faz como um todo.

  *Rigor:* cada afirmação sobre o sistema atual cita uma evidência (`EV-nn`) ou é assumida como hipótese (`H-nn`). A
  secção 2.4 explica como se escreve uma evidência.
]

== Preparação e ambiente

#orientacao[
  Registem como a solução foi lançada, para que outra pessoa a consiga repetir e obtenha o mesmo resultado. Indiquem
  sempre o _commit_ de partida (o mesmo em todos os capítulos), os comandos exatos e o ambiente de execução. Se algum
  passo falhou ou exigiu um ajuste, escrevam-no: é informação útil para quem repetir o processo.

  A descrição do processamento em lote que se segue à tabela deve ser escrita pela equipa, com palavras próprias, e
  mostrar que perceberam o fluxo completo, do _Apply_ ao resultado, para imagens e vídeos.
]

#tab([Preparação e ambiente],
  tabela-campos(
    [Commit de partida], [#preencher[hash]],
    [Comando(s) de arranque], [#preencher[e.g., `docker compose up -d --build`]],
    [Ambiente (SO, CPU, RAM, versões de Docker e Compose)], [#preencher[…]],
  ),
)

*Como é orquestrado o processamento em lote de imagens e de vídeos* (5 a 8 linhas):

#preencher[Descrição, com palavras da equipa, do que acontece desde o _Apply_ até ao resultado, para um projeto com imagens e vídeos, e de como o sistema distingue os dois tipos de _media_.]

== Fontes consultadas

#orientacao[
  Listem os documentos e o código que sustentam a análise, com a versão ou a data de cada um (_commit_, número de versão,
  data de acesso) e para que foram usados. Isto permite ao leitor perceber de onde vêm as afirmações e detetar
  fontes desatualizadas. Incluam os documentos de apoio da unidade curricular que influenciaram a análise.
]

#tab([Fontes consultadas],
  tabela(
    colunas: (5.5cm, 3cm, 1fr),
    [Fonte], [Versão / data], [Usada para],
    [`README.md`, `AGENTS.md`], [#preencher[commit]], [#preencher[…]],
    [`doc-ext-requisitos-2627.pdf`], [#preencher[…]], [#preencher[…]],
    [`doc-sol-arquitetural.pdf`], [#preencher[…]], [#preencher[…]],
    [Slides da aula 11 (_Arch. Styles_) e documento de apoio de padrões arquiteturais], [#preencher[…]], [#preencher[…]],
    [#preencher[outra fonte]], [#preencher[…]], [#preencher[…]],
  ),
)

== Vista da arquitetura global

#orientacao[
  A vista mostra o *padrão global* da solução (serviços, filas, armazenamento, fronteiras) com o *caminho do vídeo
  destacado*, de modo a que se veja onde o vídeo segue o resto do sistema e onde se afasta dele.

  Usem a notação e a ferramenta que preferirem (C4 de contentores, componentes UML, PlantUML, Mermaid, draw.io), mas
  incluam sempre uma *legenda* e indiquem a ferramenta. O diagrama tem de ser legível no documento impresso e
  consistente com o que foi observado na solução em execução, não apenas com a documentação.
]

#figure(kind: image,
  figura-pendente[vista da arquitetura global com o caminho do vídeo destacado (`images/arquitetura_global.png`)],
  caption: [Vista da arquitetura global com o caminho do vídeo destacado],
)

*Ferramenta / notação:* #preencher[…]

#tab([Legenda da vista da arquitetura],
  tabela(
    colunas: (5cm, 1fr),
    [Elemento (cor, forma ou estilo)], [Significado],
    [#preencher[…]], [#preencher[e.g., caminho do vídeo]],
    [#preencher[…]], [#preencher[…]],
  ),
)

== Sequência de um pedido completo

#orientacao[
  Descrevam, passo a passo, o que acontece num pedido completo para um projeto com vídeos: carregamento → definição do
  _pipeline_ → _Apply_ → progresso → resultado. O diagrama de sequência mostra a ordem das interações; a tabela
  identifica, para cada passo, quem fala com quem e através de que mensagem, _endpoint_ ou fila.

  *O que é uma evidência (`EV-nn`).* Uma evidência é a referência *verificável* que sustenta uma afirmação sobre o
  sistema atual. Deve permitir que outra pessoa, no _commit_ de partida, confirme o que afirmam sem ter de adivinhar.
  Pode ser:
  - *código*, com ficheiro e linhas (e.g., `video.py:8-9`);
  - *configuração*, com ficheiro e linha (e.g., `docker-compose.yml`, definição de uma fila ou de um volume);
  - *mensagem* observada (e.g., conteúdo de uma mensagem na fila, resposta de um _endpoint_);
  - *medição* ou *registo de execução*, com o comando usado e o resultado;
  - *documento*, com a secção (e.g., `doc-sol-arquitetural.pdf`, secção 3).

  Regras: o ID é sequencial (`EV-01`, `EV-02`, …), único, e nunca se reutiliza. Como o relatório não tem um registo
  separado, *descrevam a evidência no sítio onde a usam pela primeira vez* (formato: `EV-nn`: localização — o que
  mostra); nas ocorrências seguintes basta o ID. Uma afirmação sem evidência não é um facto: marquem-na como
  *hipótese* (`H-nn`) e indiquem como a confirmar ou refutar.
]

#figure(kind: image,
  figura-pendente[diagrama de sequência do processamento em lote de um projeto com vídeos (`images/sequencia_pedido.png`)],
  caption: [Sequência do processamento em lote de um projeto com vídeos],
)

#tab([Passos do pedido completo],
  tabela(
    colunas: (3cm, 3.6cm, 1fr, 3.4cm),
    [Passo], [Origem → Destino], [Mensagem / _endpoint_ / fila], [Evidência],
    [Carregamento do vídeo], [#preencher[…]], [#preencher[…]], [#preencher[EV-01: localização — o que mostra]],
    [Definição do _pipeline_], [#preencher[…]], [#preencher[…]], [#preencher[EV-nn]],
    [_Apply_], [#preencher[…]], [#preencher[…]], [#preencher[EV-nn]],
    [Progresso], [#preencher[…]], [#preencher[…]], [#preencher[EV-nn]],
    [Resultado], [#preencher[…]], [#preencher[…]], [#preencher[EV-nn]],
  ),
)
