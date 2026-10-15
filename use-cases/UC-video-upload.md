# UC-VID-000 — Carregar Vídeo para um Projeto

## 0. Identificação

| Campo | Valor |
|---|---|
| Grupo / Equipa | Grupo 1 |
| Autores | Eduardo Freitas, Francisco Contente, Luís Pires, Rui Castro |
| Data | 2026-10-15 |
| Versão do documento | v1.0 |
| Unidade Curricular | Requisitos e Arquiteturas de Software — MEI, Universidade do Minho |

## 1.0 Funcionalidade — Carregamento de vídeo

| Campo | Valor |
|---|---|
| Funcionalidade | Carregar um vídeo para um projeto PictuRAS, validar o ficheiro e os limites do perfil, e disponibilizá-lo na biblioteca do projeto para reprodução e utilização nas ferramentas de vídeo. |
| Perfil(s) de utilizador abrangido(s) | Registado (gratuito) e Premium. O perfil anónimo pode carregar imagens, mas não vídeos. O Registado está sujeito aos limites de 200 MB e 10 minutos; o Premium, aos limites de 2 GB e 60 minutos. |
| Justificação no contexto do MVP | O carregamento é o ponto de entrada comum às funcionalidades de vídeo. Legendas (UC-VID-001), recorte (UC-VID-002) e concatenação (UC-VID-003) dependem de vídeos disponíveis no projeto. Este caso de uso especifica a seleção, validação, armazenamento e disponibilização de um vídeo externo, incluindo os limites por perfil e a preservação dos ficheiros já existentes. |

## 2.0 Caso de Uso 00 — Carregar um vídeo para um projeto

### 2.0.1 Cabeçalho

| Secção | Detalhes |
|---|---|
| ID do Caso de Uso | UC-VID-000 |
| Nome | Carregar um vídeo para um projeto |
| Versão | v1.0 |
| Autor | Luís Pires |
| Data | 2026-10-15 |
| Objetivo | Permitir a um utilizador Registado ou Premium adicionar um vídeo suportado a um projeto, guardando-o de forma íntegra e apresentando-o na biblioteca para reprodução e utilização posterior. |
| Âmbito | Interface de projetos do PictuRAS, API Gateway, Project Service, serviço de armazenamento de ficheiros (SeaweedFS / Image Storage), serviço de utilizadores para consulta do perfil e metadados de vídeo (ffprobe). |
| Ator Principal | Utilizador autenticado com perfil Registado ou Premium e permissão para editar o projeto. |
| Stakeholders e Interesses | - Utilizador Registado: carregar vídeos dentro dos limites do plano e utilizá-los nas ferramentas disponíveis.<br>- Utilizador Premium: carregar vídeos de maior dimensão e duração.<br>- Proprietário do projeto: manter os ficheiros e metadados corretos, sem substituir conteúdos existentes.<br>- Equipa de Desenvolvimento/DevOps: validar entradas, preservar a consistência do projeto e limpar ficheiros temporários.<br>- Administrador do sistema: proteger os ficheiros e impedir acesso ou alterações não autorizados. |
| Pré-condições | - O utilizador tem sessão iniciada e pode editar o projeto.<br>- O projeto existe e a sua versão atual é conhecida pela interface.<br>- O serviço de utilizadores, o serviço de projetos e o armazenamento estão disponíveis.<br>- O perfil do utilizador é Registado ou Premium. |
| Trigger | O utilizador seleciona ou arrasta um ficheiro de vídeo para a área de carregamento de um projeto e confirma o carregamento. |

### 2.0.2 Fluxo Principal

| Passo | Ação do Ator | Resposta do Sistema |
|---|---|---|
| 1 | Abre um projeto e seleciona um ficheiro de vídeo (`.mp4` ou `.webm`) na área de carregamento. | Apresenta o ficheiro na lista de itens a carregar, com o nome e uma pré-visualização. |
| 2 | Confirma o carregamento. | Verifica a sessão, a permissão de edição e a versão do projeto. Recebe o ficheiro como multipart/form-data e guarda-o temporariamente para validação. |
| 3 | — | Consulta o perfil do utilizador e valida a extensão, o tamanho máximo aplicável, a existência de uma pista de vídeo válida, a duração e os codecs permitidos (RN1–RN3). |
| 4 | — | Verifica se já existe no projeto um ficheiro com o mesmo nome. Se os controlos forem válidos, calcula o hash SHA-256 e envia o vídeo para o armazenamento, associado ao projeto e à área de origem (`src`). |
| 5 | — | Adiciona ao projeto a referência do ficheiro, o identificador no armazenamento, o hash e os metadados técnicos (duração, codecs, resolução, taxa de fotogramas, dimensão e formato). Atualiza a versão do projeto de forma consistente (RN4, RN5). |
| 6 | — | Elimina o ficheiro temporário local e responde com sucesso e a nova versão do projeto. |
| 7 | Continua a utilizar o projeto. | Atualiza a biblioteca e disponibiliza o vídeo para reprodução e para as ferramentas de vídeo compatíveis. |

### 2.0.3 Fluxos Alternativos

| Fluxo | Descrição |
|---|---|
| FA1 — Vários ficheiros selecionados | A interface envia cada ficheiro individualmente e em sequência, atualizando a versão do projeto após cada carregamento aceite. Se um ficheiro falhar, apresenta o erro associado a esse ficheiro; os carregamentos anteriores concluídos mantêm-se. |
| FA2 — Vídeo sem áudio | O vídeo é aceite se cumprir as restantes validações. Os metadados registam ausência de pista de áudio; ferramentas que necessitam de áudio, como a geração de legendas, aplicam as suas próprias regras. |
| FA3 — Recuperação após falha de versão | Se a versão do projeto enviada pelo cliente estiver desatualizada, o sistema rejeita o carregamento, informa da versão atual e permite atualizar o projeto antes de tentar novamente. |
| FA4 — Carregamento por projeto partilhado | Um colaborador com permissão de edição pode carregar o vídeo conforme as permissões de partilha do projeto. A associação do ficheiro continua a ser feita ao projeto proprietário. |

### 2.0.4 Exceções

| Condição | Comportamento do Sistema |
|---|---|
| E1 — Utilizador anónimo ou perfil não elegível | Recusa o carregamento do vídeo, informa que é necessária uma conta Registada ou Premium e não altera o projeto. |
| E2 — Ficheiro ausente ou extensão não suportada | Rejeita o pedido e informa que deve ser selecionado um ficheiro MP4 ou WebM. Não altera o projeto. |
| E3 — Tamanho acima do limite do perfil | Rejeita o ficheiro antes de o guardar no armazenamento do projeto e indica o limite aplicável: 200 MB para Registado ou 2 GB para Premium. |
| E4 — Vídeo inválido, corrompido ou sem pista de vídeo | A inspeção falha; o sistema rejeita o ficheiro, informa que não foi possível ler um vídeo válido e limpa o ficheiro temporário. |
| E5 — Codec incompatível com a extensão | Rejeita o ficheiro e indica a combinação aceite: MP4 com H.264 e áudio AAC (ou sem áudio); WebM com VP8 e áudio Vorbis (ou sem áudio). |
| E6 — Duração acima do limite do perfil | Rejeita o ficheiro e indica o limite aplicável: 10 minutos para Registado ou 60 minutos para Premium. |
| E7 — Nome já utilizado no projeto | Rejeita o carregamento e informa que já existe um ficheiro com esse nome. O utilizador pode renomear o ficheiro e tentar novamente. |
| E8 — Projeto inexistente ou sem permissão de edição | Recusa o pedido e não grava o vídeo nem altera o projeto. |
| E9 — Conflito de versão do projeto | Não associa o vídeo ao projeto; se o ficheiro já tiver chegado ao armazenamento, elimina essa cópia. Devolve a versão atual para sincronização. |
| E10 — Armazenamento indisponível ou erro ao guardar | Informa que o carregamento falhou, elimina o temporário e qualquer objeto incompleto, e mantém o projeto inalterado. |
| E11 — Interrupção ou falha de rede durante o envio | Apresenta uma falha para o ficheiro afetado. O projeto não deve apresentar um item incompleto; o utilizador pode tentar novamente. |

### 2.0.5 Pós-condições

| Tipo | Resultado |
|---|---|
| Garantia de Sucesso | O projeto contém uma nova referência ao vídeo validado, o objeto está guardado no armazenamento e os metadados e o hash correspondem ao ficheiro recebido. O vídeo aparece na biblioteca do projeto, disponível para reprodução e para as ferramentas de vídeo que aceitem o seu formato. A versão do projeto foi atualizada e o ficheiro temporário foi eliminado. |
| Garantia Mínima | Em caso de rejeição ou falha, nenhum vídeo incompleto fica disponível no projeto. Os itens existentes não são modificados, os temporários e objetos parciais são removidos e o utilizador recebe uma indicação do motivo e da ação possível. |

### 2.0.6 Regras de Negócio e Restrições

| ID | Regra |
|---|---|
| RN1 | O carregamento de vídeo está disponível apenas para utilizadores autenticados com perfil Registado (`free`) ou Premium. O perfil anónimo não pode carregar vídeos. |
| RN2 | Limites para vídeos externos: Registado — tamanho máximo de 200 MB e duração máxima de 10 minutos; Premium — tamanho máximo de 2 GB e duração máxima de 60 minutos. O ficheiro tem de cumprir ambos os limites. Estes limites são aplicados ao carregamento externo e não são reaplicados a vídeos gerados no projeto por outras operações. |
| RN3 | Formatos e codecs aceites: MP4 com vídeo H.264 e áudio AAC, ou sem áudio; WebM com vídeo VP8 e áudio Vorbis, ou sem áudio. A extensão e os codecs têm de corresponder. Tem de existir uma pista de vídeo legível e uma duração válida. |
| RN4 | Cada nome de ficheiro tem de ser único dentro do projeto. O sistema não substitui automaticamente ficheiros existentes. |
| RN5 | Cada carregamento associa o vídeo ao projeto e guarda os metadados identificados, incluindo hash SHA-256, tamanho, formato, duração, codecs, resolução e taxa de fotogramas. A atualização do projeto respeita a versão esperada, evitando perda de alterações concorrentes. |
| RN6 | O acesso ao carregamento exige autenticação e permissão de edição no projeto, incluindo quando este é acedido através de partilha. Os vídeos ficam protegidos pelas regras de acesso do projeto e pela proteção de transporte e armazenamento definida para o sistema. |
| RN7 | O carregamento não conta como operação diária de processamento de vídeo e não cria uma tarefa assíncrona de processamento. Cada ficheiro selecionado é carregado e validado individualmente. |
| RN8 | Ficheiros temporários locais são eliminados após sucesso ou falha. Se a gravação no armazenamento tiver sucesso mas a atualização do projeto falhar, o objeto órfão é removido. |
| RN9 | Um vídeo carregado com sucesso passa a poder ser selecionado pelas ferramentas de vídeo, que aplicam os seus próprios requisitos adicionais, limites e regras de acesso. |

### 2.0.7 Assunções

| ID | Assunção |
|---|---|
| A1 | A interface de carregamento existente, que aceita imagens, vídeos MP4/WebM e ficheiros ZIP de imagens, será reutilizada; este caso de uso trata especificamente do ramo de vídeo. |
| A2 | Os limites e codecs definidos em RN2 e RN3 refletem a implementação atual do Project Service e são a base do MVP. |
| A3 | A inspeção técnica do vídeo é efetuada no servidor com uma ferramenta equivalente a ffprobe; o cliente não é fonte de autoridade para duração ou codecs. |
| A4 | Os vídeos gerados por recorte, concatenação ou incorporação de legendas já são adicionados ao projeto pelas respetivas operações e não passam novamente pelo fluxo de carregamento externo. |
| A5 | A interface pode permitir selecionar vários ficheiros de uma vez, mas a API processa cada ficheiro numa chamada individual; não existe garantia de atomicidade para o conjunto. |

### 2.0.8 Questões em Aberto

| ID | Questão em aberto |
|---|---|
| Q1 | Devem ser aceites outros formatos ou codecs de vídeo além de MP4 (H.264/AAC) e WebM (VP8/Vorbis)? |
| Q2 | Deve o sistema permitir retomar envios interrompidos de ficheiros grandes, em particular até 2 GB no perfil Premium? |
| Q3 | Deve existir uma quota de armazenamento por projeto ou utilizador além dos limites por ficheiro definidos por perfil? |
| Q4 | Em carregamentos de vários ficheiros, deve a interface oferecer uma operação explícita para repetir apenas os ficheiros que falharam? |

## 3. Esboço de requisitos derivados

### 3.1 Requisitos de Sistema

| ID | Requisito | Tipo | Prioridade | Novo/Alt | Origem | Como verificar |
|---|---|---|---|---|---|---|
| REQ-VID-UPLOAD-001 | O sistema deve permitir a um utilizador Registado ou Premium selecionar um ficheiro MP4 ou WebM e carregá-lo para um projeto que pode editar. | F | Deve ter | ALT | Trigger; Passos 1–2; RN1, RN6 | Dado um utilizador elegível com permissão de edição, quando seleciona um MP4/WebM válido, então o pedido de carregamento é aceite. |
| REQ-VID-UPLOAD-002 | O sistema deve rejeitar o carregamento de vídeo por utilizador anónimo ou perfil não elegível, sem alterar o projeto. | F | Deve ter | ALT | E1; RN1 | Dado um utilizador anónimo, quando tenta carregar vídeo, então recebe uma mensagem de acesso requerido e o projeto mantém-se inalterado. |
| REQ-VID-UPLOAD-003 | O sistema deve aplicar os limites de tamanho e duração por perfil: 200 MB/10 minutos para Registado e 2 GB/60 minutos para Premium. | F | Deve ter | ALT | RN2; E3; E6 | Para cada perfil, submeter ficheiros no limite e acima de cada limite; os primeiros são aceites e os segundos rejeitados com o limite indicado. |
| REQ-VID-UPLOAD-004 | O sistema deve aceitar MP4 com H.264 e AAC (ou sem áudio) e WebM com VP8 e Vorbis (ou sem áudio), e rejeitar vídeos ilegíveis, sem pista de vídeo ou com codecs incompatíveis. | F | Deve ter | ALT | RN3; E2; E4; E5 | Submeter exemplos válidos e inválidos de cada formato e verificar que só os válidos são adicionados ao projeto. |
| REQ-VID-UPLOAD-005 | O sistema deve impedir nomes de ficheiro duplicados dentro do mesmo projeto, sem substituir o ficheiro existente. | F | Deve ter | ALT | RN4; E7 | Carregar um vídeo e repetir com o mesmo nome; o segundo pedido é recusado e o primeiro permanece disponível. |
| REQ-VID-UPLOAD-006 | O sistema deve guardar o vídeo e os seus metadados no projeto, incluindo hash SHA-256, tamanho, formato, duração, codecs, resolução e taxa de fotogramas. | F | Deve ter | NOVO | Passos 4–5; RN5 | Após um carregamento válido, comparar os metadados apresentados/guardados com o ficheiro e verificar o hash. |
| REQ-VID-UPLOAD-007 | O sistema deve atualizar a versão do projeto de forma consistente e rejeitar um carregamento baseado numa versão desatualizada, removendo qualquer objeto que não tenha sido associado ao projeto. | F | Deve ter | ALT | Passo 5; FA3; E9; RN5, RN8 | Enviar dois pedidos concorrentes com a mesma versão; apenas uma alteração é consolidada e o pedido em conflito não deixa objeto órfão. |
| REQ-VID-UPLOAD-008 | O sistema deve verificar autenticação e permissão de edição antes de associar o vídeo ao projeto, respeitando as permissões de partilha. | F | Deve ter | ALT | Pré-condições; FA4; E8; RN6 | O proprietário e um colaborador com edição conseguem carregar; utilizador sem permissão é recusado sem alterar o projeto. |
| REQ-VID-UPLOAD-009 | O sistema deve eliminar ficheiros temporários e objetos parciais após sucesso, rejeição ou falha do carregamento. | NF (Integridade) | Deve ter | NOVO | Passos 4–6; E4; E9–E11; RN8 | Simular sucesso, erro de validação, falha de armazenamento e conflito de versão; não ficam temporários nem objetos não referenciados. |
| REQ-VID-UPLOAD-010 | Após um carregamento bem-sucedido, o vídeo deve aparecer na biblioteca do projeto e ficar disponível para reprodução e seleção pelas ferramentas de vídeo. | F | Deve ter | ALT | Passo 7; Garantia de Sucesso; RN9 | Carregar um vídeo válido, atualizar a biblioteca, reproduzi-lo e confirmar que pode ser selecionado numa ferramenta compatível. |
| REQ-VID-UPLOAD-011 | O sistema deve permitir selecionar vários ficheiros e comunicar o resultado de cada carregamento individual, preservando os ficheiros cujo envio já terminou com sucesso. | F | Deveria ter | ALT | FA1; A5; RN7 | Selecionar vários ficheiros e provocar uma falha num deles; os restantes concluídos ficam no projeto e a falha é identificada pelo nome. |
| REQ-VID-UPLOAD-012 | O carregamento de vídeo não deve consumir quota diária de processamento nem criar uma tarefa de processamento assíncrona. | F | Deve ter | NOVO | RN7 | Carregar um vídeo e confirmar que o saldo de operações não muda e que não é criada tarefa de vídeo. |

### 3.2 Impacto no sistema existente

| Elemento existente afetado | Impacto (Manter / Estender / Alterar) | Descrição do impacto | Requisitos relacionados |
|---|---|---|---|
| Interface de carregamento do projeto | Manter | Reutiliza a área de seleção atual, que aceita vídeos MP4 e WebM e mostra pré-visualizações. | REQ-VID-UPLOAD-001, REQ-VID-UPLOAD-011 |
| API do Project Service | Manter | Reutiliza o endpoint de carregamento multipart, permissões do projeto, controlo de versão e associação do item ao projeto. | REQ-VID-UPLOAD-001, REQ-VID-UPLOAD-005, REQ-VID-UPLOAD-007, REQ-VID-UPLOAD-008 |
| Validação técnica e perfil de utilização | Manter | Reutiliza a consulta do perfil, limites por perfil, inspeção com ffprobe e validação de codecs. | REQ-VID-UPLOAD-002, REQ-VID-UPLOAD-003, REQ-VID-UPLOAD-004 |
| Image Storage / SeaweedFS | Manter | Reutiliza o armazenamento de objetos na área de origem (`src`) e a referência do objeto guardada no projeto. | REQ-VID-UPLOAD-006, REQ-VID-UPLOAD-009 |
| Ferramentas de vídeo | Estender | Passam a consumir vídeos externos após carregamento validado, mantendo os requisitos próprios de cada operação. | REQ-VID-UPLOAD-010 |

### 3.3 Matriz de Rastreabilidade

| Elemento do Caso de Uso | Descrição abreviada | Requisito(s) de Sistema |
|---|---|---|
| Trigger / Passos 1–2 | Seleção e envio do vídeo | REQ-VID-UPLOAD-001, REQ-VID-UPLOAD-008 |
| Passo 3 | Perfil, formato, tamanho, codecs e duração | REQ-VID-UPLOAD-002, REQ-VID-UPLOAD-003, REQ-VID-UPLOAD-004 |
| Passo 4 | Nome único e armazenamento do objeto | REQ-VID-UPLOAD-005, REQ-VID-UPLOAD-006, REQ-VID-UPLOAD-009 |
| Passos 5–6 | Associação ao projeto, versão e limpeza | REQ-VID-UPLOAD-006, REQ-VID-UPLOAD-007, REQ-VID-UPLOAD-009 |
| Passo 7 | Disponibilização na biblioteca | REQ-VID-UPLOAD-010 |
| FA1 | Vários carregamentos independentes | REQ-VID-UPLOAD-011 |
| FA2 | Vídeo sem áudio | REQ-VID-UPLOAD-004 |
| FA3 / E9 | Conflito de versão | REQ-VID-UPLOAD-007, REQ-VID-UPLOAD-009 |
| FA4 / E8 | Permissões de projeto partilhado | REQ-VID-UPLOAD-008 |
| E1 | Perfil sem acesso | REQ-VID-UPLOAD-002 |
| E2–E6 | Formato, tamanho, codec, vídeo inválido ou duração | REQ-VID-UPLOAD-003, REQ-VID-UPLOAD-004 |
| E7 | Nome duplicado | REQ-VID-UPLOAD-005 |
| E10–E11 | Falha de armazenamento ou rede | REQ-VID-UPLOAD-009 |
| RN1–RN2 | Perfis e limites do carregamento externo | REQ-VID-UPLOAD-002, REQ-VID-UPLOAD-003 |
| RN3–RN4 | Formatos e unicidade do nome | REQ-VID-UPLOAD-004, REQ-VID-UPLOAD-005 |
| RN5–RN6 | Metadados, consistência e permissões | REQ-VID-UPLOAD-006, REQ-VID-UPLOAD-007, REQ-VID-UPLOAD-008 |
| RN7–RN9 | Sem quota de processamento; vídeo disponível para ferramentas | REQ-VID-UPLOAD-010, REQ-VID-UPLOAD-012 |
| Garantia de Sucesso | Vídeo íntegro e utilizável no projeto | REQ-VID-UPLOAD-006, REQ-VID-UPLOAD-010 |
| Garantia Mínima | Sem ficheiros incompletos ou alterações indevidas | REQ-VID-UPLOAD-005, REQ-VID-UPLOAD-007, REQ-VID-UPLOAD-009 |
