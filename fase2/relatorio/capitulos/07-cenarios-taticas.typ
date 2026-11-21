#import "../template.typ": *

// Capítulo inteiro na horizontal (tabelas largas). Para voltar ao vertical, retirar o #paisagem[ ].
#paisagem[
= Cenários de Entrada e Táticas Candidatas

Os cenários e os candidatos são os do capítulo 5 e do capítulo 6; não são reescritos aqui.
Não foi necessário corrigir nenhuma medida da resposta após a medição inicial.

== Candidatos e cenários de entrada

#tab([Candidatos e cenários de entrada],
  tabela(
    colunas: (1.8cm, 2.2cm, 3cm, 1.8cm, 2.8cm, 3cm, 3.4cm, 3.4cm),
    tamanho: 8pt,
    [Candidato], [Cenário (`QS-nn`)], [Característica / subcaracterística (ISO/IEC 25010)], [Evidência], [Origem (padrão global / vídeo / interação)], [Estímulo a que a tática reage], [Resposta e medida (resumo)], [Escala e método (cap. 6)],
    [CAND-1], [QS-01], [Manutenibilidade → Modularidade, Reutilizabilidade], [EV-01, EV-03, EV-04], [Padrão do vídeo, alinhado com o global], [Pedido para adicionar ou alterar um efeito de vídeo; falha de um worker], [Mudança confinada a um módulo; rebuild de uma imagem; falha isolada], [Ficheiros/serviços tocados; tamanho e build da imagem; Radon MI; isolamento],
    [CAND-2], [QS-02], [Usabilidade → Operabilidade], [EV-07], [Global (frontend, gateway, projetos)], [Utilizador inicia processamento e quer continuar a usar a aplicação ou recarrega a página], [Interface utilizável; progresso e cancelamento recuperáveis], [Bloqueio da interface; recuperação do progresso e do cancelamento],
  ),
)

== Alterações feitas ao capítulo 5 (se existirem)

Não houve alterações. Os identificadores, as respostas e as medidas do capítulo 5 mantêm-se
inalterados após a medição inicial.

== Táticas candidatas

#tab([Táticas candidatas],
  tabela(
    colunas: (1.6cm, 1.8cm, 3.6cm, 3.4cm, 5cm, 3.4cm, 1.8cm),
    tamanho: 8pt,
    [ID], [Cenário], [Atributo → categoria], [Tática], [Como produz a resposta (estímulo → tática → resposta)], [Já existe na base? (evidência)], [Classe (A/B/C)],
    [TAT-01], [QS-01], [Manutenibilidade → modularizar], [Separar por domínio funcional], [Adicionar um efeito deixa de exigir compreender o código de legendagem e de extração: o domínio afetado é identificado pelo módulo que o contém], [Parcial — o global já separa ferramentas de imagem (EV-04); o vídeo é um monólito (EV-01)], [A],
    [TAT-02], [QS-01], [Manutenibilidade → reduzir acoplamento; Eficiência → gerir recursos], [Fila e contentor por domínio, com dependências isoladas], [Cada domínio tem o seu `requirements.txt` e a sua imagem: alterar um efeito leve reconstrói 1,09 GB em vez do monólito de 1,70 GB, e uma falha não arrasta os outros], [Parcial — uma fila e uma imagem para os três domínios (EV-02, EV-03)], [A],
    [TAT-03], [QS-01], [Manutenibilidade → controlar mudança; Fiabilidade → coordenar], [Compor os estágios no orquestrador, encadeando cada resposta em `project_queue`], [O orquestrador calcula os estágios do pipeline e despacha o seguinte quando o anterior responde; preserva a ordem dos efeitos mesmo quando pertencem a workers distintos], [Parcial — o despacho era feito num único envio ao worker monolítico (EV-05)], [A],
    [TAT-04], [QS-02], [Usabilidade → dar feedback], [Execução assíncrona com estado persistido no backend], [O pedido de processamento deixa de exigir que a interface espere: o estado da execução passa a ser consultável depois de recarregar a página], [Não — o progresso existe apenas no browser (EV-07)], [B],
    [TAT-05], [QS-02], [Usabilidade → dar feedback; Fiabilidade → observar], [Eventos de progresso agregados e reconstruíveis], [Cada worker reporta o seu avanço com `base`/`span`, permitindo reconstruir o progresso global mesmo quando vários estágios são executados por serviços diferentes], [Parcial — o monólito emitia progresso, mas não agregado por estágio (EV-05)], [B],
    [TAT-06], [QS-02], [Usabilidade → proteger o utilizador de erros], [Substituir o ecrã bloqueante por acompanhamento e cancelamento], [O utilizador mantém o controlo da aplicação e pode acompanhar ou cancelar a execução sem depender do estado transitório do browser], [Não — ecrã sobreposto bloqueia toda a aplicação (EV-07)], [B],
  ),
)

As táticas do QS-01 são de classe A: não alteram o comportamento funcional, apenas a estrutura do
processamento. As do QS-02 são de classe B porque a alteração visível à interface é precisamente o
objetivo da melhoria. Não foi incluída nenhuma tática de classe C (funcionalidade nova), como
adicionar novos efeitos ou expor um painel de administração de filas.
]
