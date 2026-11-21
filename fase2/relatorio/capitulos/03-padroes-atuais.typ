#import "../template.typ": *

= Padrões Arquiteturais Atuais

== Padrão global da solução

#tabela-campos(
  [Nome(s) do padrão / estilo], [Microserviços, orientado a eventos (mensageria com filas duráveis) e armazenamento partilhado por volume/S3],
  [Descrição], [O PictuRAS é composto por serviços pequenos e independentes — gateway, projetos, utilizadores, subscrições, armazenamento e uma ferramenta por efeito de imagem — que não se chamam diretamente: comunicam por mensagens no exchange `picturas` do RabbitMQ. Cada ferramenta consome a sua fila e devolve a resposta em `project_queue`; os ficheiros de _media_ não trafegam nas mensagens, mas num volume partilhado e no S3. O orquestrador `projects` é o único componente que conhece a pipeline e coordena os passos (EV-04).],
)

#tab([Decisões globais que condicionam o vídeo],
  tabela(
    colunas: (4.5cm, 2.6cm, 1fr),
    [Decisão global], [Evidência], [Efeito no vídeo],
    [Comunicação assíncrona por filas duráveis no exchange `picturas`], [EV-04], [O vídeo já usava mensageria, mas concentrada numa fila própria em vez de uma por domínio],
    [Volume partilhado `image_data` e estágios S3 (`src`, `out`, `preview`, `preview_cache`)], [EV-01, EV-02], [O worker de vídeo lê e escreve diretamente no mesmo armazenamento que as ferramentas de imagem, com a diferença de ser o único produtor de vídeo],
    [Orquestração centralizada do lote em `projects`, com registo prévio dos `Process`], [EV-05], [A ordem dos efeitos e a pertença ao item são decididas no orquestrador; o worker recebe o trabalho já planeado],
    [Progresso publicado em `ws_queue` e entregue ao browser pelo wsGateway], [EV-05, EV-07], [O feedback existe, mas na base era apenas em memória do browser e não agregado por domínio],
  ),
)

#tab([Benefícios e desafios do padrão global],
  tabela(
    colunas: (2cm, 1fr, 4.2cm, 2.4cm),
    tamanho: 8.5pt,
    [Tipo], [Descrição], [Característica / subcaracterística (ISO/IEC 25010)], [Facto / hipótese],
    [Benefício], [Cada ferramenta de imagem pode ser alterada e reconstruída sem afetar as restantes], [Manutenibilidade → Modularidade], [EV-04],
    [Benefício], [Ficheiros grandes não trafegam nas mensagens, reduzindo a utilização de memória e a latch da fila], [Eficiência de desempenho → Utilização de recursos], [EV-02],
    [Desafio], [A coordenação do lote depende do orquestrador e da correlação das respostas em `project_queue`], [Fiabilidade → Recuperabilidade], [EV-05],
  ),
)

== Padrão do processamento de vídeo

#tabela-campos(
  [Nome do padrão], [Monólito de processamento com despacho único (um worker, uma fila, uma imagem para todos os domínios)],
  [Descrição], [Na base, o serviço `video_tool` consome `video_queue` e executa, no mesmo processo, os filtros PIL/FFmpeg, a transcrição com Faster-Whisper e a extração de fotogramas (EV-01, EV-02, EV-03). Para cada vídeo, o orquestrador envia uma única mensagem com a pipeline completa; o worker descodifica uma vez, aplica os efeitos nos fotogramas e codifica novamente (EV-05).],
  [Contraste com o caminho de imagens], [As imagens seguem o padrão global: uma fila e um contentor por ferramenta, com o orquestrador a compor os passos um a um. O vídeo concentrava tudo num único componente e o orquestrador não compunha estágios — divergência que é o objeto do `CAND-1` (EV-04, EV-05).],
)

#tab([Benefícios e desafios do padrão do vídeo],
  tabela(
    colunas: (2cm, 1fr, 4.2cm, 2.4cm),
    tamanho: 8.5pt,
    [Tipo], [Descrição], [Característica / subcaracterística (ISO/IEC 25010)], [Facto / hipótese],
    [Benefício], [Uma só descodificação e codificação por vídeo, mesmo com vários efeitos standard na pipeline], [Eficiência de desempenho → Comportamento temporal], [EV-05],
    [Benefício], [Áudio preservado porque a codificação final é única e inclui AAC], [Funcionalidade — preservação de áudio], [EV-01],
    [Desafio], [Dependências de IA e de manipulação leve partilham o mesmo `requirements.txt` e a mesma imagem], [Manutenibilidade → Modularidade], [EV-03],
    [Desafio], [Uma falha no domínio de legendagem pode parar todos os trabalhos de vídeo], [Fiabilidade → Tolerância a falhas], [H-01],
  ),
)

== Relação entre o padrão global e o padrão do vídeo

#tab([Relação entre o padrão global e o padrão do vídeo],
  tabela(
    colunas: (2.4cm, 3cm, 3cm, 1.9cm, 2.6cm, 1.8cm),
    tamanho: 8pt,
    [Aspeto], [O que o padrão global prescreve], [O que o vídeo faz], [Segue / afasta-se], [Consequência], [Evidência],
    [Comunicação entre serviços], [Fila por ferramenta no exchange `picturas`], [Uma fila para os três domínios], [Afasta-se], [Ponto único de contenção e impossibilidade de escalar um domínio], [EV-02, EV-04],
    [Gestão de estado do lote], [Orquestrador compõe os passos e regista os `Process`], [Orquestrador envia a pipeline inteira num passo], [Afasta-se], [Menos pontos de coordenação, mas acoplamento entre domínios no worker], [EV-05],
    [Dependências e deployment], [Imagem e `requirements.txt` por ferramenta], [Uma imagem com Pillow e `faster-whisper`/`torch`], [Afasta-se], [Build e disco desproporcionais para efeitos triviais], [EV-03, EV-04],
    [Armazenamento], [Volume partilhado e estágios S3], [Mesmo volume e mesmos estágios], [Segue], [Resultados e origens são consistentes entre tipos de _media_], [EV-01, EV-02],
    [Tratamento de falhas], [Cada ferramenta falha isoladamente], [Falha partilhada por todos os domínios], [Afasta-se], [Risco de parar todo o processamento de vídeo; hipótese H-01], [H-01, EV-03],
  ),
)

O vídeo herda do padrão global a mensageria durável, o armazenamento partilhado e a posição do
orquestrador como único coordenação do lote. Destas decisões resultam as restrições que qualquer
alternativa tem de respeitar: a ordem dos efeitos pertence ao projeto, os ficheiros não viajam nas
mensagens e os resultados têm de continuar no mesmo esquema S3. O desvio está na granularidade —
um único worker e um único despacho em vez de um componente por ferramenta — e é precisamente dele
que nascem as fragilidades de manutenibilidade e de isolamento de falhas que alimentam os cenários
do capítulo 5. A alternativa escolhida no capítulo 4 não altera o padrão global: aproxima o vídeo
dele.
