# Testes de regressão

A checklist em `docs/REGRESSION_CHECKLIST.md` liga os requisitos aos testes e aos resultados. `tests/TEST_EXECUTION_PROTOCOL.md` define como as IAs devem registar execuções. Os comandos abaixo fazem esse registo automaticamente, incluindo falhas.

## Preparação

```bash
python3 -m venv .venv
.venv/bin/pip install -r tests/requirements-python.txt -r Tools/video_effects/requirements.txt
npm install --no-package-lock
npx playwright install chromium firefox
docker compose up -d
make test-fixtures
```

São necessários ffmpeg/ffprobe no host. A suite foi executada com Node 22 e Python 3.14. Os testes de API e browser usam a aplicação real em `https://localhost:8080`; a API também usa os serviços locais e Docker para preparar dados específicos, inspecionar persistência e limpar apenas os IDs criados pela suite. Não apontar esta suite para um serviço de produção.

## Execução

| Comando | Testes |
| --- | --- |
| `make test` | Node existente + Python + API real + browser |
| `make test-all` | Suite principal completa: tudo acima + serviços isolados para recuperação + desempenho local |
| `make test-known-failures` | 13 testes que falham, fora dos totais; nos casos não cobertos pelo PDF mantêm as expectativas anteriores; o comando devolve erro |
| `make test-unit` | Node e Python, incluindo processamento real com ffmpeg |
| `make test-node` | Orquestração e validação Node |
| `make test-python` | Workers de vídeo e comparação dos efeitos de imagem/vídeo |
| `make test-api` | Contratos HTTP de contas, projetos, processamento e uploads |
| `make test-integration` | Filas, workers, S3, quotas e processamento entre serviços |
| `make test-e2e` | Playwright: Chromium, Firefox e viewport móvel |
| `make test-security` | Autenticação, autorização, WebSocket e URLs de media |
| `make test-resilience` | Broker/worker e backup/restauro de Mongo em contentores temporários |
| `make test-performance` | 20 pedidos em lotes de 4 e processamento de uma pequena imagem |

Os 13 cenários isolados estão auditados em `tests/KNOWN_FAILURES.md`. Podem ser repetidos sem entrar na validação principal. A auditoria indica onde o PDF define uma regra e onde se mantém a expectativa anterior.

`make test-strict` é equivalente a `make test`: uma suite vazia, indisponível ou com falhas já produz código de saída diferente de zero. O runner continua para as categorias seguintes após uma falha, para recolher o máximo de informação. A API usa `node:test`, tal como os testes existentes de `projects`; Jest/Supertest não são necessários para estes testes contra o stack real.

## Organização e resultados

- `projects/tests/`: validação e orquestração Node.
- `Tools/video_effects/tests/`, `Tools/video_subtitles/tests/` e `Tools/video_frames/tests/`: efeitos de vídeo, legendas com reconhecimento simulado e extração de frames.
- `tests/functional/unit/python/`: efeitos reais de imagem comparados com as implementações do vídeo.
- `tests/functional/api/auth/`, `tests/functional/api/projects/`, `tests/functional/api/processing/`, `tests/functional/api/uploads/`: contratos HTTP por domínio.
- `tests/functional/integration/`: processamento, quotas, armazenamento e concorrência entre serviços.
- `tests/functional/security/`: acesso, autorização, WebSocket e URLs de media.
- `tests/functional/e2e/`: autenticação, projetos, edição de imagem/vídeo e acessibilidade, em ficheiros com testes reais.
- `tests/known_failures/`: testes isolados que reproduzem falhas do código recebido.
- `tests/functional/resilience/`: contentores e rede temporários; não reinicia os serviços da aplicação em uso.
- `tests/performance/local-budget.test.js`: orçamento local de regressão.
- `tests/performance/benchmark/`: ensaios de carga isolados, recolha de métricas e reprodução da referência. [Relatório inicial](../resultados-desempenho-inicial.md)
- `tests/helpers/`: clientes HTTP, sockets, verificações de media e dados de teste.
- `tests/fixtures/generate.py`: gera imagens em `images/`, vídeos em `videos/` e entradas inválidas em `invalid/`. Os ficheiros gerados são ignorados pelo Git.
- `tests/reports/`: XML JUnit, logs, screenshots, traces e lista dos IDs criados. Estes artefactos são ignorados pelo Git.

O runner associa os IDs nos nomes dos testes (por exemplo `[AUTH-01]`) à coluna **Última execução**. Uma execução de várias suites agrega os resultados: uma falha num dos testes mantém o requisito em `FAIL`, mesmo que outra suite passe. Os testes que não foram executados não recebem `PASS`. Cobertura e resultado permanecem separados.

Cada suite usa um registo próprio de contas criadas. A limpeza remove apenas esses IDs e os respetivos projetos, objetos S3, ficheiros, presets e subscrições, mesmo quando os testes falham. Se a limpeza falhar, a execução devolve erro e mantém o registo para recuperação:

```bash
node scripts/cleanup-test-data.js tests/reports/<execucao>-users.jsonl
```

## Limites configuráveis

`TEST_PROCESS_TIMEOUT_MS` controla a espera por resultados (90 s por defeito). O teste de reconhecimento real de fala permite 240 s e pode precisar de descarregar o modelo Whisper no primeiro uso. Falhar por timeout não prova que o ficheiro seja inválido: consultar os logs do worker.

O ensaio local usa `TEST_API_P95_MS=2000` e `TEST_IMAGE_PROCESS_MS=30000`. Regista hardware, dataset, paralelismo e medições em `tests/reports/performance.json`. Estes valores são orçamentos iniciais de regressão, ajustáveis após medição no ambiente de CI.

O backup/restauro verifica as três bases em contentores isolados. Objetos S3 não fazem parte de `mongodump`; a recuperação completa de media exige uma política de backup própria para o armazenamento.

## Registo da atividade

**2026-11-04, 15:20 WET · commit de partida `0523102`.** Analisados `AGENTS.md`, Compose, Dockerfiles, gestores de dependências e testes preexistentes. Criados os diretórios, configurações e comandos acima, sem alterar lógica da aplicação nem adicionar casos. `bash -n`, `node --check jest.config.cjs`, leitura JSON de `package.json` e `make -n` passaram. O runner normal identificou Python como `UNAVAILABLE` (Pytest não instalado neste ambiente) e API/E2E como `NO TESTS`; o modo estrito terminou com código 1 e um argumento inválido com código 2. Não foram validadas execuções Jest/Playwright porque as dependências ainda não estão instaladas. Estado Git: novos ficheiros de testes/configuração, `.gitignore` e `package.json` alterados; `docs/` já era trabalho anterior não relacionado.
