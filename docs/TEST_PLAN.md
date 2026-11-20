# Plano de testes

## Ponto de partida

- `Tools/video_effects/tests/`, `Tools/video_subtitles/tests/`, `Tools/video_frames/tests/`: testes Pytest existentes para processamento de vídeo, legendas e extração de fotogramas.
- `projects/tests/`: testes `node:test` para pipelines, processamento em lote, extração de fotogramas e validação de vídeo, agora incluídos no executor principal.
- `tests/functional/unit/python/`, `tests/functional/api/` e `tests/functional/e2e/`: casos executáveis de efeitos, HTTP/integração e browser. Os testes de API usam `node:test` contra o stack real.
- `make test` executa Node, Pytest, API real e Playwright. `make test-all` acrescenta recuperação em serviços isolados e desempenho. Ambos registam os resultados na checklist e devolvem erro perante falhas ou suites vazias. A instalação está descrita em `tests/README.md`.

## Ordem de implementação

1. **Estabelecer uma base fiável.** Instalar as dependências, executar os testes Python e Node existentes e manter `projects/tests/` no executor principal. Registar falhas antes de adicionar casos. Usar imagens e vídeos pequenos e previsíveis em `tests/fixtures/`; criar utilizadores e projetos exclusivos por teste e limpar os dados no fim.
2. **Testes unitários — Pytest (`tests/functional/unit/python/`).** Testar parâmetros e resultados representativos dos efeitos de imagem, entradas inválidas, ordem dos efeitos de vídeo, limites de trim/speed, ausência de fala nas legendas, limites da extração de fotogramas e limpeza após falhas. Ampliar `Tools/video_effects/tests/`, `Tools/video_subtitles/tests/`, `Tools/video_frames/tests/` para vídeo, sem duplicar casos.
3. **Testes de API — node:test contra HTTP real (`tests/functional/api/`).** Cobrir autenticação/JWT e limites dos perfis; criação, leitura, alteração e remoção de projetos; validação do tipo e tamanho de uploads; ordem da pipeline do projeto; trim/speed dirigidos a um vídeo; processamento em lote e registo de resultados; quotas; falhas dos workers e do armazenamento. Usar o stack real para os percursos; simular dependências apenas nos testes específicos de falha, em processos separados.
4. **Integração entre serviços (`tests/functional/integration/`).** Com o Compose em execução, verificar o percurso gateway → projetos → armazenamento → RabbitMQ → workers → resultados, incluindo eventos de progresso em `ws_queue`. Cobrir um lote de imagens e um de vídeos com áudio, pré-visualização, legendas e extração de fotogramas. Confirmar que os originais ficam intactos e que falhas não deixam resultados parciais.
5. **Percursos do utilizador — Playwright (`tests/functional/e2e/`).** Começar por registo/login, criação de projeto, upload de imagem, edição da pipeline, processamento e download do resultado. Depois cobrir upload de vídeo, controlos exclusivos de vídeo, pré-visualização/progresso, legendas e fotogramas extraídos. Verificar a interface e as quotas dos perfis anónimo, gratuito e premium. Usar contas isoladas e esperar por estados/eventos da interface, sem pausas de duração fixa.
6. **Validação em CI.** Executar os testes unitários e de API em cada alteração; executar integração com Compose e Playwright num ambiente limpo. Guardar relatórios JUnit, traces e capturas de ecrã em caso de falha. Usar `make test-strict` como requisito apenas quando todas as suites selecionadas tiverem casos reais e as dependências estiverem instaladas.

## Comandos

```bash
make test-python                         # testes Pytest de vídeo existentes + novos testes Python
make test-node                           # testes do orquestrador incluídos no runner
make test-api                            # contratos HTTP
make test-integration                    # fluxos entre serviços
docker compose up -d --build             # necessário para integração e E2E
make test-e2e                            # Playwright: Chromium e Firefox
make test-all                            # inclui resiliência isolada e orçamento de desempenho
```

**Concluído quando:** cada percurso essencial tiver um teste automático aprovado, as falhas gerarem relatórios úteis, os testes puderem repetir-se com dados limpos e nenhuma suite apresentar `NO TESTS` ou `UNAVAILABLE` na validação final.
