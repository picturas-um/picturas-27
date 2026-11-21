#import "../template.typ": *

= Utilização de IA

== Ferramentas, modelos e configuração

#tabela(
  colunas: (3.5cm, 1fr),
  [Ferramenta / modelo], [Configuração e utilização (_skills_, instruções de projeto, MCP, …)],
  [OpenCode · Big Pickle (`opencode/big-pickle`)], [Agente de codificação usado na análise do repositório, na redação deste relatório e nas alterações de código e de testes. Trabalha na raiz do repositório, com acesso a ficheiros, terminal e histórico Git],
  [Instruções de projeto (`AGENTS.md`)], [Regras seguidas pelo agente: arquitetura e fluxos do PictuRAS, convenções de código e mensagens, idioma inglês no código, preservação de finais de linha e protocolo de testes com atualização da checklist],
  [Subagentes `explore` e `general`], [Usados para pesquisas rápidas e paralelas no código (localização de rotas, filas, workers e testes), com resultados devolvidos ao agente principal e por ele verificados],
  [Ferramenta de geração de imagens], [Usada para apoio visual nos esquemas do relatório; os diagramas finais foram desenhados em SVG e convertidos com `rsvg-convert` para manter notação e escala consistentes entre as vistas «antes» e «depois»],
  [Pesquisa e recolha na Web], [Consultas pontuais a documentação e a páginas públicas para confirmar sintaxe e comandos; nenhum conteúdo do relatório depende de fonte externa não verificável no repositório],
)

As secções seguintes descrevem o que foi efetivamente usado nesta entrega. O agente não teve acesso aos documentos preenchidos dos Exercícios 6 e 7 da equipa, pelo que os capítulos foram escritos a partir do código, do histórico Git, das guidelines da Fase 2 e das medições recolhidas; os identificadores foram mantidos para preservar a cadeia entre capítulos.

== Tarefas apoiadas e validação

#tab([Tarefas apoiadas por IA e validação],
  tabela(
    colunas: (2.6cm, 2.4cm, 2.4cm, 2.8cm, 2.8cm),
    tamanho: 8.5pt,
    [Ferramenta / modelo / _skill_], [Tarefa apoiada (capítulo)], [O que foi aceite], [O que foi rejeitado e porquê], [Como foi validado pela equipa],
    [OpenCode · Big Pickle], [Exploração do código e da arquitetura (caps. 2–4)], [Identificação dos componentes, filas e fluxos; classificação dos padrões e das diferenças entre imagens e vídeo], [Afirmações sem evidência verificável no commit `0523102`], [Cada facto foi ligado a um `EV`; as inferências foram marcadas como `H-01`; os ficheiros e linhas citados foram reabertos],
    [OpenCode · Big Pickle], [Redação dos cenários, candidatos e táticas (caps. 5–7)], [Estrutura das tabelas, redação das medidas e manutenção dos IDs `EV`, `H`, `QS`, `CAND`, `TAT`, `ALT`], [Valores-alvo inventados e reutilização do ensaio de desempenho system-wide como RNF], [As escalas foram fixadas antes da alteração; o capítulo 10 isola a evidência de desempenho como suporte e não como `QS`],
    [OpenCode · Big Pickle], [Implementação e correção do pipeline misto (caps. 8–10)], [`videoStages()` no orquestrador, encadeamento por `project_queue` e progresso com `base`/`span` nos três workers; teste de integração `border` + `subtitles`], [A tentativa inicial com `brightness` como efeito de contraste — multiplicativo, sem efeito visível em `speech.mp4`, que é preto puro], [Testes: 20/20 Node, 53/53 Python e 31/31 integração; comandos e ID de execução registados em `docs/REGRESSION_CHECKLIST.md`; commits `cc53fac` e `2ee32d7`],
    [OpenCode · Big Pickle], [Medições e sua interpretação (cap. 10)], [Tamanhos das imagens, contagem de domínios, Radon MI e sequência de eventos `video-progress`; comparação antes/depois no mesmo host], [A estimativa de >3,5 GB para o monólito, que constava no plano inicial; a classificação MI como prova de melhoria], [Valores substituídos pelos medidos (`1,70 GB`; `1,09 + 1,74 + 1,09 GB`); Radon executado nas duas variantes, com `A` em todos os módulos, e por isso apresentado como métrica não discriminativa],
    [Geração de imagens + `rsvg-convert`], [Diagramas das vistas e da sequência (caps. 2 e 9)], [Duas vistas com a mesma notação, escala e legenda, com os elementos do DA-1 a verde], [Imagens decorativas sem legenda ou sem correspondência com o código], [Os SVG foram gerados por script a partir dos componentes reais e convertidos para PNG; as figuras e legendas foram revistas no PDF compilado],
    [OpenCode · Big Pickle], [Estrutura e compilação do relatório], [Capítulos 1 a 12 e anexos no _template_ Typst, com os IDs preservados e as caixas de orientação desligadas na entrega], [Texto de _placeholder_, expressões acidentais noutros idiomas e orientações visíveis no documento final], [`typst compile --font-path fonts main.typ` executado; pesquisas por marcadores de preenchimento e por ficheiros temporários antes de fechar a versão],
  ),
)

== Análise crítica

O que correu bem: o agente percorreu rapidamente um repositório grande, localizou os pontos de coordenação entre `projects`, RabbitMQ e os workers e produziu uma primeira versão coerente da cadeia `EV → QS → CAND → TAT → DA`. Também foi útil na mecânica — gerar tabelas Typst, manter a consistência dos identificadores e reparar o encadeamento de estágios com um teste que falharia se a ordem dos efeitos se perdesse.

Onde errou e como foi detetado: (i) propôs `brightness` para demonstrar a composição de efeitos com legendagem, mas o vídeo de teste é preto e o filtro é multiplicativo; a asserção não teria distinguido os pipelines, pelo que se trocou por `border` (vermelho, 4 px), com verificação de dimensão, cor do canto e pixéis de legenda; (ii) assumiu que o monólito excedia 3,5 GB, valor que não resistiu a `docker images` — passou a constar o valor medido de 1,70 GB; (iii) usou inicialmente o ensaio de desempenho system-wide como se fosse a medição dos RNF, o que foi corrigido ao separar a evidência de suporte do QS-01/QS-02; (iv) escreveu identificadores `ALT-01`/`ALT-03` divergentes dos `ALT-1`/`ALT-3` do capítulo 4 e deixou passar caracteres acidentais noutros idiomas, todos detetados por pesquisa no texto e corrigidos antes da compilação final; (v) a primeira atualização da checklist não apanhou IDs com hífen, o que foi visto na contagem de células e repetido com expressão corrigida.

A prática adotada pela equipa foi não aceitar nada do agente sem uma verificação independente: afirmações sobre o sistema apoiam-se em ficheiros do commit de base, números vêm de comandos executados e guardados, código passa pelos testes e o relatório só é considerado pronto depois de compilar e de uma leitura final das tabelas. O agente apoiou a análise e a escrita, mas a responsabilidade pelo conteúdo entregue — incluindo o gerado por IA — é da equipa.
