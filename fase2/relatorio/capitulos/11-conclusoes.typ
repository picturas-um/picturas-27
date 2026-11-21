#import "../template.typ": *

= Conclusões e Recomendações

== Adequação do padrão atual (global e do vídeo)

O padrão global do PictuRAS — microserviços, comunicação assíncrona por filas duráveis e ficheiros em volume partilhado/S3 — mostrou-se adequado para a extensão de vídeo: é ele que permite evoluir ferramentas de imagem e de vídeo sem reescrever o orquestrador (EV-04). O problema não estava no padrão, mas no desvio do caminho de vídeo em relação a ele (capítulo 3). Ao concentrar efeitos, legendagem e extração de fotogramas num único serviço, uma fila e um `requirements.txt` com IA (EV-01, EV-02, EV-03), a solução de base sacrificou modularidade e isolamento de falhas sem obter vantagem equivalente. A ALT-2 (capítulo 4) aproximou o vídeo do padrão global sem o alterar e foi a decisão implementada.

A decomposição por domínio atingiu o objetivo do CAND-1 na métrica principal: o caminho de efeitos deixou de carregar `faster-whisper`/`torch` e a imagem a reconstruir passou de 1,70 GB para 1,09 GB. Ficou claro, porém, que separar os workers não basta: a coordenação das etapas teve de passar para o orquestrador, e foi nessa fronteira que a regressão dos pipelines mistos apareceu. A correção (`cc53fac`) e a sua cobertura de integração (`2ee32d7`) são parte da decisão, não acessórios dela — a lição é que o _refactoring_ de uma arquitetura orientada a eventos tem de ser avaliado pelo comportamento ponta a ponta, não apenas pela estrutura resultante.

== Sugestões de otimização

#tab([Sugestões de otimização resultantes da experiência],
  tabela(
    colunas: (3.4cm, 4cm, 1fr, 2.6cm),
    tamanho: 8.5pt,
    [Sugestão], [Atributo favorecido], [Razão / evidência nesta fase], [Prioridade sugerida],
    [Publicar o estado da execução no backend, com progresso e cancelamento recuperáveis], [Usabilidade → Operabilidade; Fiabilidade → Recuperabilidade], [Os eventos `base`/`span` dos três workers tornam o progresso reconstruível, mas hoje ainda dependem do estado do browser (EV-07, capítulo 10)], [Alta — é o CAND-2, cuja implementação e medição ficam registadas pelo membro responsável],
    [Medir o tempo de build limpo por worker de forma sistemática], [Eficiência → Comportamento temporal; Manutenibilidade], [O tamanho da imagem é uma boa aproximação do custo de manutenção; o tempo de build fecha a medição, mas não foi recolhido de forma comparável nas duas variantes], [Média],
    [Especificar contratos de mensagem versionados entre o orquestrador e os três workers], [Manutenibilidade → Modificabilidade; Fiabilidade], [O bug dos pipelines mistos mostrou que a composição de etapas é um ponto de coordenação frágil; um contrato explícito reduz o risco de nova regressão], [Média],
    [Adicionar ensaios de caos por domínio ao conjunto de regressão], [Fiabilidade → Tolerância a falhas], [O isolamento da legendagem foi verificado uma vez; repeti-lo por worker e com o broker a reiniciar cobre os cenários de recuperação já identificados como risco conhecido], [Baixa],
  ),
)

== Considerações para evolução futura

A separação em três domínios cria espaço para decisões que antes eram impossíveis: escalar a legendagem (o estágio mais caro) independentemente dos efeitos, atualizar o modelo do Whisper sem reconstruir o worker de efeitos e adicionar um efeito leve sem mexer no código de IA. Cada uma destas decisões continua sujeita à restrição da fase seguinte: o contrato do lote e o esquema de resultados não devem mudar sem necessidade, porque os testes e o histórico de regressão dependem deles.

O custo assumido — 3,92 GB de imagens contra 1,70 GB no monólito — não desaparece. Se a equipa pretender reduzi-lo, a via natural é uma imagem base partilhada entre os três workers, mantendo os `requirements.txt` separados por domínio; essa otimização preserva a modularidade e ataca apenas a duplicação de camadas comuns. O progresso agregado é também uma base útil para a Fase 3: um painel de acompanhamento ou a recuperação de execuções após recarregamento podem consumir os mesmos eventos sem exigir alteração nos workers.

== Trabalho futuro

Ficou por medir o `CAND-2` com o mesmo rigor do `CAND-1`: o bloqueio da interface e a recuperação do progresso e do cancelamento após recarregamento dependem de implementação e de valores a registar pelo membro responsável. A checklist e o capítulo 10 assinalam essa lacuna em vez de a preencher com estimativas. A hipótese H-01 foi confirmada na base e mitigada na variante final no ensaio de isolamento realizado, mas o comportamento sob falha do broker e sob carga sustentada não foi repetido após a decomposição — os dados de desempenho system-wide disponíveis são da revisão de base e servem apenas como referência de regressão.

A edição e a descarga de vídeo pelo navegador também ficam por cobrir automaticamente, bem como a repetição da suíte de integração por outro membro da equipa no commit final. Para a Fase 3, o _refactoring_ facilita a integração de novos efeitos e de novos modelos de IA porque cada domínio tem uma fronteira própria e testes próprios; não facilita, por si só, a recuperação de estado nem a experiência de acompanhamento, que exigem trabalho dedicado no backend e na interface.
