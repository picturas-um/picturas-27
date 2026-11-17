# Fiabilidade: recuperação do progresso e do cancelamento

Classificação: ISO/IEC 25010:2011, Fiabilidade → Recuperabilidade.

## Alteração

O estado de Apply deixa de depender dos contadores e eventos Socket.IO da página.
Cada nova execução guarda `processingState` no projeto MongoDB, com token,
estado, total de passos inicial, passos de imagem concluídos, percentagens por
vídeo, datas e causa conhecida de falha. Estados: `processing`, `completed`,
`failed` e `cancelled`; projetos sem execução registada devolvem `idle`.

`GET /:user/:project/process/status`, exposto pelo API Gateway, devolve apenas
o estado público da execução, a percentagem, a versão do projeto e a permissão
de cancelamento. A resposta usa `Cache-Control: no-store` e respeita as partilhas
do projeto. Um leitor pode acompanhar; só o proprietário ou um editor pode cancelar.

A página consulta este endpoint na montagem, incluindo F5, e a cada 2 segundos.
As consultas continuam após perda de rede e quando a janela recupera o foco.
Em caso de erro mantém-se o último progresso conhecido, com aviso de ligação;
não se assume que a tarefa terminou. Não é necessário guardar tokens de sessão
ou uma cópia do processamento em `localStorage`.

O worker de vídeo envia também progresso correlacionado para `project_queue`.
O orquestrador persiste-o sem confundir preview com Apply. Atualizações repetidas
não contam duas vezes e percentagens atrasadas não fazem regredir o progresso.
O indicador só atinge 100% depois do commit dos resultados. Os trabalhos de
Apply mantêm a barreira de conclusão até guardar o resultado ou registar o sucessor.
Novas submissões e alterações de media/pipeline são rejeitadas durante a execução,
para evitar eliminar trabalhos ou alterar o significado do progresso recuperado.

O cancelamento recupera a versão atual e envia `X-Process-Token`. O backend
rejeita um pedido dirigido a outra execução ou a uma execução já concluída.
A confirmação altera o estado persistido; um erro do pedido mantém os controlos
e o acompanhamento. A devolução de quota existente só ocorre depois da escrita
condicional de cancelamento, para não devolver quota por um conflito de versão.

## Validação e limites da evidência

- `projects/tests/processing-recovery.test.js`: recuperação a partir de uma nova
  leitura, progresso misto, duplicação e ordem dos eventos, estados terminais,
  permissões, preservação do progresso durante outras escritas e cancelamento
  antigo. Usa o controlador real com um adaptador de atualizações Mongo em memória.
- `projects/tests/process-batch.test.js`: regressão das barreiras de lote e do
  commit atrasado após cancelamento.
- `tests/python/unit/test_progress_recovery.py`: contrato do método de progresso
  do worker, compilado do código de produção; transporte simulado, sem FFmpeg/broker.
- `tests/e2e/processing-recovery.spec.ts`: cenários de F5, erro de cancelamento e
  estados terminais com a página React real e transporte de estado/cancelamento
  simulado. Exige o ambiente de testes existente para sessão/projeto.

As execuções e resultados constam de `docs/REGRESSION_CHECKLIST.md`.
Resultado final dos testes isolados: 14 testes Node e 2 testes Python passaram.
A verificação de tipos do frontend (`tsc --noEmit --incremental false`),
as verificações de sintaxe JavaScript e `git diff --check` também passaram.
Neste ambiente o daemon Docker está indisponível e Playwright não está instalado;
os testes de browser e a integração real MongoDB/RabbitMQ/FFmpeg estão por executar.

## Verificação manual na stack

1. Reconstruir `projects`, `api_gateway`, `video_tool` e `frontend` com
   `docker compose up -d --build projects api_gateway video_tool frontend`.
   Reiniciar Nginx após reconstruir o frontend: `docker compose restart nginx`.
2. Iniciar Apply num projeto com um vídeo suficientemente demorado. Registar
   o token e o progresso devolvidos por `/process/status`.
3. Premir F5. Confirmar que o cartão reaparece com o mesmo token, progresso
   atualizado e botão de cancelamento disponível, sem reenviar Apply.
4. Cancelar. Confirmar estado `cancelled`, desaparecimento do cartão e ausência
   de resultados tardios da execução cancelada. Repetir F5.
5. Repetir deixando concluir. Confirmar `completed`, 100% e resultados disponíveis.
6. Simular falha de processamento e repetir F5: mostrar `failed` e a causa conhecida.
7. Interromper a rede durante o acompanhamento ou cancelamento. Confirmar aviso,
   manutenção do último progresso e recuperação automática quando a rede regressa.

## Âmbito

A recuperação aplica-se a execuções iniciadas com esta versão. Não reconstrói
percentagens de tarefas antigas sem estado persistido. O cancelamento reutiliza
a invalidação lógica de execução existente; não acrescenta interrupção física
do FFmpeg. A persistência do cartão fora da página do projeto pertence ao
requisito separado de operabilidade e não é demonstrada por esta alteração.
