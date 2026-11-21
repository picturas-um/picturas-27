#import "../template.typ": *

= Alternativas e Matriz de Comparação

== Alternativas consideradas

#tab([Alternativas consideradas],
  tabela(
    colunas: (1.6cm, 3.4cm, 1fr, 3cm, 2.4cm),
    tamanho: 8.5pt,
    [ID], [Nome / padrão], [Descrição breve], [Mantém ou altera o padrão global?], [Fonte],
    [ALT-1], [Manter o monólito de vídeo], [Conservar `video_tool`, `video_queue` e o despacho único; eventualmente ajustar o código interno sem alterar a fronteira do serviço], [Mantém o desvio atual — afasta-se do padrão global], [Solução de base, EV-01, EV-02, EV-05],
    [ALT-2], [Decompor por domínio em três microserviços], [Um worker e uma fila para efeitos, outro para legendagem, outro para extração de fotogramas; orquestrador compõe os estágios], [Mantém o padrão global e aproxima o vídeo dele], [EV-04, EV-06; recomendação indicativa da docência],
    [ALT-3], [Replicar o monólito], [Várias instâncias de `video_tool` atrás da mesma fila para aumentar a capacidade de processamento], [Mantém o desvio atual; altera apenas a escala], [Alternativa de elasticidade, EV-02],
  ),
)

== Análise de cada alternativa

*ALT-1 — Manter o monólito de vídeo*

#tabela-campos(
  [Coerência com o padrão global], [Afasta-se: as ferramentas de imagem têm uma fila e um serviço cada uma (EV-04), enquanto o vídeo concentrava três domínios num só componente (EV-01, EV-02)],
  [Efeito nos atributos de qualidade], [Manutenibilidade baixa (EV-03); fiabilidade baixa porque H-01 não é mitigada; comportamento temporal não melhora relativamente à base],
  [Vantagens potenciais], [Custo de migração nulo; uma única descodificação/codificação por vídeo e nenhuma coordenação extra no orquestrador (EV-05)],
  [Desvantagens ou riscos], [Qualquer alteração a um efeito obriga a reconstruir a imagem de 1,70 GB; a falha de um domínio afeta os restantes (H-01); não responde ao `CAND-1`],
  [Custo e risco de migração (a funcionalidade existente tem de ser preservada)], [Nenhum — é a situação atual. O risco é de não fazer nada perante as fragilidades identificadas],
)

*ALT-2 — Decompor por domínio em três microserviços*

#tabela-campos(
  [Coerência com o padrão global], [Alta: replica para o vídeo o padrão já usado pelas ferramentas de imagem (EV-04) e segue a sugestão da docência (EV-06); a fila `project_queue` e o exchange `picturas` mantêm-se],
  [Efeito nos atributos de qualidade], [Manutenibilidade alta (mudança confinada); fiabilidade alta (isolamento); comportamento temporal melhora no caminho de efeitos; utilização de disco degrada (3,92 GB no total)],
  [Vantagens potenciais], [Imagem de efeitos de 1,09 GB sem `torch`/`faster-whisper`; build e deploy independentes; falha de legendagem confinada; models do Whisper persistidos só no serviço que deles precisa],
  [Desvantagens ou riscos], [Três imagens, três filas e três conjuntos de dependências; risco de regressão no despacho e, sobretudo, na composição de pipelines mistos — materializado no bug corrigido descrito no capítulo 8],
  [Custo e risco de migração], [Médio: extrair três diretórios, atualizar `definitions.json`, `docker-compose.yaml` e o orquestrador, e remover o legado (`video_tool`, `video_queue`). O risco de regressão foi mitigado com testes unitários e de integração (31/31)],
)

*ALT-3 — Replicar o monólito*

#tabela-campos(
  [Coerência com o padrão global], [Mantém a topologia global, mas conserva o desvio do vídeo: continua a ser um componente e uma fila para todos os domínios (EV-02)],
  [Efeito nos atributos de qualidade], [Fiabilidade ligeiramente melhor por redundância, mas H-01 subsiste dentro de cada réplica; manutenibilidade inalterada; eficiência de disco degrada linearmente com o número de réplicas],
  [Vantagens potenciais], [Aumenta a capacidade de processamento paralelo sem alterar o orquestrador nem os contratos das mensagens],
  [Desvantagens ou riscos], [Não resolve o acoplamento entre domínios: a imagem continua a carregar IA para um `trim` de 2 s; multiplica o consumo de disco e RAM; não responde ao `CAND-1`],
  [Custo e risco de migração], [Baixo para a configuração, alto para o consumo de recursos; é uma alternativa de escala, não de manutenibilidade, e por isso foi rejeitada],
)

== Matriz de comparação de padrões

A escala é *Alto / Médio / Baixo*, aplicada de forma consistente: «Alto» significa que o padrão
favorece fortemente o atributo na solução do PictuRAS. A referência é o padrão global já aplicado
às ferramentas de imagem.

#paisagem[
#tab([Matriz de comparação de padrões],
  tabela(
    colunas: (5.6cm, 4.2cm, 4cm, 4cm, 4cm),
    tamanho: 8.5pt,
    [Atributo de qualidade (ISO/IEC 25010)], [Padrão global atual (referência)], [Padrão atual do vídeo], [ALT-1], [ALT-2],
    [Relação com o padrão global], [—], [Afasta-se (EV-01, EV-02)], [Mantém o desvio], [Mantém e aproxima (EV-04, EV-06)],
    [Eficiência de desempenho: comportamento temporal], [Alto — uma passada por ferramenta, despachos paralelos (EV-04)], [Alto para vários efeitos standard: uma descodificação (EV-05)], [Alto — inalterado], [Médio — efeitos partilham uma passada, mas há encadeamento entre estágios; legendagem deixa de ser arrastada (H-01)],
    [Eficiência de desempenho: capacidade / elasticidade], [Alto — réplicas por ferramenta são independentes (EV-04)], [Baixo — único worker, trabalhos tendem a serializar-se (EV-02)], [Baixo — inalterado], [Alto — cada domínio pode escalar por separado],
    [Fiabilidade: tolerância a falhas / recuperabilidade], [Médio — falha isolada por ferramenta, depende do broker (EV-04)], [Baixo — ponto único de falha para os três domínios (H-01)], [Baixo — inalterado], [Alto — falha confinada a um domínio; o consumidor mantém a religação ao broker],
    [Manutenibilidade: modularidade / modificabilidade], [Alto — uma ferramenta, um módulo, uma imagem (EV-04)], [Baixo — três domínios no mesmo serviço e dependências misturadas (EV-01, EV-03)], [Baixo — inalterado], [Alto — mudança confinada ao domínio e imagem própria],
    [Segurança], [Médio — fronteira única no gateway; segredos no Compose são problema conhecido], [Médio — herda a fronteira global], [Médio — inalterado], [Médio — não altera a fronteira nem os segredos; fora do âmbito desta fase],
  ),
)
]

== Adequação do padrão atual

O padrão global é adequado: a separação por ferramenta e a comunicação por filas duráveis são o
que permite evoluírem o PictuRAS sem reescrever o processamento de imagens (EV-04). O padrão do
vídeo, por contraste, deixou de ser adequado para a extensão atual: ao concentrar três domínios
com naturezas diferentes num único serviço (EV-01, EV-03), sacrificou modularidade e isolamento de
falhas sem ganho equivalente — a vantagem da descodificação única é preservada dentro do domínio
de efeitos, que continua a aplicar vários filtros na mesma passada.

A ALT-1 não é aceitável porque deixa as fragilidades por resolver e não responde ao `CAND-1`. A
ALT-3 melhora a capacidade, mas não a modularidade e multiplica o custo de uma imagem já pesada;
é uma decisão de elasticidade, não de refactoring. A ALT-2 é a mais adequada: mantém o padrão
global, é a opção indicada pela docência (EV-06) e permite medir a melhoria com o mesmo método
antes e depois. O seu custo — mais imagens e mais coordenação no orquestrador — é explicitamente
assumido como trade-off no capítulo 10, e o risco de regressão na composição de estágios foi
tratado com evidência de integração antes de a decisão ser aceite.
