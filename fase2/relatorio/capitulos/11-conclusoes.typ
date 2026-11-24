#import "../template.typ": *

= Conclusões e Recomendações

== Adequação do padrão atual (global e do vídeo)

O padrão global do PictuRAS — microserviços, comunicação assíncrona por filas duráveis e ficheiros em volume partilhado/S3 — mostrou-se adequado para a extensão de vídeo: é ele que permite evoluir ferramentas de imagem e de vídeo sem reescrever o orquestrador (EV-04). O problema não estava no padrão, mas no desvio do caminho de vídeo em relação a ele (capítulo 3). Ao concentrar efeitos, legendagem e extração de fotogramas num único serviço, uma fila e um `requirements.txt` com IA (EV-01, EV-02, EV-03), a solução de base sacrificou modularidade e isolamento de falhas sem ganho equivalente. A ALT-2 (capítulo 4) aproximou o vídeo do padrão global sem o alterar e foi a decisão implementada.

A decomposição por domínio atingiu o objetivo do CAND-1 na métrica principal: o caminho de efeitos deixou de carregar `faster-whisper`/`torch` e a imagem a reconstruir passou de 1,70 GB para 1,09 GB. Ficou claro, porém, que separar os workers não basta: a coordenação das etapas teve de passar para o orquestrador, e foi nessa fronteira que a regressão dos pipelines mistos apareceu. A correção (`1fe42ba`) e a sua cobertura de integração (`85b99d4`) são parte da decisão, não acessórios dela — a lição é que o _refactoring_ de uma arquitetura orientada a eventos tem de ser avaliado pelo comportamento ponta a ponta, não apenas pela estrutura resultante.

== Sugestões de otimização

#tab([Sugestões de otimização resultantes da experiência],
  tabela(
    colunas: (3.4cm, 4cm, 1fr, 2.6cm),
    tamanho: 8.5pt,
    [Sugestão], [Atributo favorecido], [Razão / evidência nesta fase], [Prioridade sugerida],
    [Medir o tempo de build limpo por worker de forma sistemática], [Eficiência → Comportamento temporal; Manutenibilidade], [O tamanho da imagem é uma boa aproximação do custo de manutenção; o tempo de build fecha a medição, mas não foi recolhido de forma comparável nas duas variantes], [Média],
    [Especificar contratos de mensagem versionados entre o orquestrador e os três workers], [Manutenibilidade → Modificabilidade; Fiabilidade], [O bug dos pipelines mistos mostrou que a composição de etapas é um ponto de coordenação frágil; um contrato explícito reduz o risco de nova regressão], [Média],
    [Adicionar ensaios de caos por domínio ao conjunto de regressão], [Fiabilidade → Tolerância a falhas], [O isolamento da legendagem foi verificado uma vez; repeti-lo por worker e com o broker a reiniciar cobre os cenários de recuperação já identificados como risco conhecido], [Baixa],
    [Partilhar uma imagem base entre os três workers, mantendo `requirements.txt` separados], [Eficiência → Utilização de recursos; Manutenibilidade], [O custo assumido de 3,92 GB incidente sobre camadas comuns pode ser reduzido sem voltar a acoplar dependências de domínio], [Baixa],
  ),
)

== Considerações para evolução futura

A separação em três domínios cria espaço para decisões que antes eram impossíveis: escalar a legendagem (o estágio mais caro) independentemente dos efeitos, atualizar o modelo do Whisper sem reconstruir o worker de efeitos e adicionar um efeito leve sem mexer no código de IA. Cada uma destas decisões continua sujeita à restrição da fase seguinte: o contrato do lote e o esquema de resultados não devem mudar sem necessidade, porque os testes e o histórico de regressão dependem deles.

O custo assumido — 3,92 GB de imagens contra 1,70 GB no monólito — não desaparece. Se a equipa pretender reduzi-lo, a via natural é uma imagem base partilhada entre os três workers, mantendo os `requirements.txt` separados por domínio; essa otimização preserva a modularidade e ataca apenas a duplicação de camadas comuns. O progresso agregado com `base`/`span` é também uma base útil para futuras ferramentas de observação, que podem consumir os mesmos eventos sem exigir alteração nos workers.

== Trabalho futuro

O ensaio de isolamento da legendagem avaliou uma falha num domínio específico. No ensaio de regressão com reinício do broker, o worker de efeitos voltou a não recuperar o consumo no prazo de 90 s. A campanha de desempenho observou uma degradação de latência e débito em carga mista. Atribuir essa diferença a alterações concretas exige controlo adicional do ambiente e instrumentação por componente. A variante estendida de pico e o tempo de build limpo comparável ficam por avaliar.

Na campanha de regressão, os 158 casos comparáveis passaram na revisão final, incluindo os 30 casos de integração da referência. A edição e a descarga de vídeo pelo navegador continuam sem cobertura automatizada. A validação dos novos testes de recuperação requer a correção dos caminhos de importação identificados no capítulo 10. Para a Fase 3, o _refactoring_ facilita a integração de novos efeitos e de novos modelos de IA porque cada domínio tem uma fronteira própria e testes próprios; não elimina, contudo, o risco de regressão na coordenação de estágios, que continua a exigir testes ponta a ponta sempre que o despacho mudar.
