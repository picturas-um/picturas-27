#import "../template.typ": *

= Trade-offs, Cenários de Qualidade e Prioridades

Os cenários seguintes partem das fragilidades observadas na solução de base (commit `0523102`) e
das evidências registadas no capítulo 2. Mantêm os identificadores `EV-01` a `EV-06` e a hipótese
`H-01` já apresentados, sem os alterar.

== Cenários de qualidade para a extensão de vídeo

#paisagem[
#tab([Cenários de qualidade],
  tabela(
    colunas: (1.2cm, 3.4cm, 2.6cm, 2.2cm, 2.2cm, 2.4cm, 2.2cm, 2.6cm, 3cm),
    tamanho: 7.5pt,
    [ID], [Fragilidade na base (EV-nn)], [Característica (ISO/IEC 25010)], [Fonte do estímulo], [Estímulo], [Artefacto], [Ambiente], [Resposta], [Medida da resposta],
    [QS-01], [EV-01, EV-03: efeitos leves e inferência de IA partilham o mesmo processo e as mesmas dependências], [Manutenibilidade → Modularidade, Reutilizabilidade], [Desenvolvedor], [Adicionar ou alterar um efeito no pipeline de vídeo], [Subsistema de processamento de vídeo (`Tools/video/`, `video_tool`, `video_queue`)], [Manutenção normal, sem carga], [A alteração fica confinada ao módulo do domínio; só esse serviço é reconstruído], [Número de ficheiros e serviços tocados; tamanho e tempo de build da imagem reconstruída; índice de manutenibilidade (Radon MI)],
    [QS-02], [EV-07: ecrã sobreposto bloqueia a aplicação; progresso apenas no browser e perdido com recarregamento], [Usabilidade → Operabilidade (feedback e controlo)], [Utilizador final], [Iniciar o processamento de um projeto e continuar a usar a aplicação, incluindo após recarregar a página], [Interface de processamento (frontend e `wsGateway`)], [Uso normal, com processamento em curso], [A interface continua utilizável; o progresso e o cancelamento sobrevivem ao recarregamento], [Período de bloqueio da interface (s); progresso recuperável após recarregamento (sim/não); cancelamento disponível após recarregamento (sim/não)],
    [QS-03], [EV-03: uma falha fatal na legendagem (OOM/SIGKILL) derruba o único worker e atrasa todos os vídeos], [Fiabilidade → Tolerância a falhas, Isolamento de falhas], [Falha de infraestrutura / worker], [O componente de legendagem termina anormalmente durante um lote], [Subsistema de processamento de vídeo], [Carga normal, vários vídeos na fila], [A falha afeta apenas o domínio da legendagem; os restantes trabalhos concluem], [Número de domínios parados (de 3); conclusão dos trabalhos dos outros domínios (sim/não)],
  ),
)
]

A medida do QS-01 é deliberadamente composta: isoladamente, "menos ficheiros tocados" poderia ser
obtido com uma alteração superficial. Exige-se também que a imagem reconstruída seja a do domínio
alterado e que o índice de manutenibilidade não diminua. A medição inicial é apresentada no
capítulo 10; os valores não são fixados aqui.

== Priorização dos cenários

#tab([Priorização dos cenários],
  tabela(
    colunas: (1.6cm, 4.8cm, 4.8cm, 2cm),
    [ID], [Importância para os stakeholders], [Dificuldade / risco técnico], [Prioridade],
    [QS-01], [Alta — afeta diretamente o custo e o risco de cada alteração futura ao processamento de vídeo, e é um dos exemplos indicados pela docência para esta fase], [Média — exige extrair três serviços e adaptar o orquestrador, mas reutiliza o padrão já aplicado às ferramentas de imagem (EV-04)], [1],
    [QS-02], [Alta — é a fragilidade mais visível para o utilizador: o bloqueio da interface e a perda do progresso após recarregar], [Alta — exige persistir estado e progresso no backend e rever o ciclo de vida da execução], [2],
    [QS-03], [Média — é um efeito colateral da fragmentação em processos distintos, não um objetivo autónomo da equipa], [Baixa — é obtida pela mesma decomposição do QS-01, sem trabalho adicional], [3],
  ),
)

== Atributos de qualidade por ordem de prioridade

+ Manutenibilidade → Modularidade (QS-01) — é o objetivo explícito do refactoring e condiciona a
  capacidade de responder aos outros cenários sem introduzir regressões.
+ Usabilidade → Operabilidade (QS-02) — é o segundo RNF escolhido, independente do primeiro, e
  traduz a necessidade de feedback e controlo durante a execução.
+ Fiabilidade → Tolerância a falhas (QS-03) — resulta da separação de processos e é registada como
  consequência positiva, não como candidato a RNF.

A ordem é coerente com a priorização: os dois primeiros atributos dão origem a `CAND-1` e
`CAND-2` no capítulo 6; o terceiro é acompanhado como efeito colateral.

== Pré-requisitos e efeitos colaterais entre atributos

#tab([Pré-requisitos e efeitos colaterais entre atributos],
  tabela(
    colunas: (2.8cm, 2.8cm, 4cm, 1fr),
    [Atributo A], [Atributo B], [Efeito (pré-requisito, sinergia ou conflito)], [Razão / evidência],
    [Manutenibilidade (modularidade)], [Fiabilidade (isolamento de falhas)], [Sinergia], [Processos e filas distintos impedem que uma falha na legendagem interrompa os efeitos; ver EV-03 e a medição de isolamento no capítulo 10],
    [Manutenibilidade (modularidade)], [Eficiência de desempenho (tempo de build)], [Sinergia], [O caminho de efeitos deixa de carregar `faster-whisper`/`torch`: a imagem passa de 1,70 GB para 1,09 GB],
    [Manutenibilidade (modularidade)], [Eficiência de desempenho (utilização de disco)], [Conflito], [O total de imagens sobe de 1,70 GB para 3,92 GB (1,09 + 1,74 + 1,09 GB); o custo é aceite em troca de builds e falhas confinadas],
    [Usabilidade (feedback)], [Fiabilidade (eventos de progresso)], [Pré-requisito], [Para recuperar o progresso após recarregar, o backend tem de receber e persistir os eventos `video-progress` dos workers, não apenas o browser],
  ),
)

== Recomendações de melhoria à solução atual

#tab([Recomendações de melhoria],
  tabela(
    colunas: (1fr, 2.6cm, 3cm, 1.8cm, 2.2cm),
    tamanho: 8.5pt,
    [Recomendação], [Atributo(s)], [Padrão a que se refere (global / vídeo)], [Esforço], [Risco de regressão],
    [Separar os domínios de efeitos, legendagem e extração de fotogramas em serviços e filas próprios], [Manutenibilidade, Fiabilidade], [Padrão do vídeo, alinhado com o global (EV-04)], [Médio], [Médio],
    [Isolar as dependências em `requirements.txt` por serviço, removendo IA do caminho de efeitos], [Manutenibilidade, Eficiência], [Padrão do vídeo], [Baixo], [Baixo],
    [Fazer o orquestrador compor os estágios, encadeando a resposta de cada worker na fila `project_queue`], [Manutenibilidade, Fiabilidade], [Interação (orquestrador ↔ workers)], [Médio], [Alto],
    [Persistir o progresso e o estado da execução no backend, com recuperação após recarregamento], [Usabilidade, Fiabilidade], [Global (frontend, gateway, projetos)], [Alto], [Médio],
  ),
)

A terceira recomendação é a que apresenta maior risco e foi efetivamente onde a implementação
encontrou uma regressão: a separação dos workers, por si só, não preserva o comportamento dos
pipelines mistos. O detetado e a correção são descritos nos capítulos 8 e 10.
