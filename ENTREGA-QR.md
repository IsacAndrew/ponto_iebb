# Entrega de manutenção e QR individual — 05/09/2026

## Implementação

- Título do navegador `Ponto Eletrônico`, login sem relógio decorativo e favicon configurável em Configurações para Suporte/Diretoria.
- Sidebar agrupada e renomeada conforme a especificação. Central de Suporte e Atendimentos separados e restritos ao Suporte.
- Meus Registros inicia no dia atual, cria colunas dinâmicas por marcação e expande os detalhes do dia.
- Marcações apresenta pessoas uma vez, pesquisa e histórico individual; Presença do dia foi movida para essa área e a visão inicial lista os eventos de hoje.
- Usuários preserva o cadastro, permite admissão retroativa, copia todos os períodos de um dia para destinos selecionados e oferece QR individual.
- Solicitações separa pendentes e aprovadas, com filtros de período e nome.
- Meu Perfil mostra o login diretamente e somente a jornada vigente e as futuras.
- Excel preservado byte a byte. Apenas a interface removeu calendário e número da versão e separou responsável, data e horário.

## QR

O token tem 384 bits aleatórios, não contém login/senha, fica associado à pessoa no servidor e não cria cookie. Cada pessoa tem um único QR ativo. Regenerar apaga o mapeamento do token anterior na mesma transação. Abrir o link executa somente GET e não marca ponto. O POST usa a mesma função de marcação, jornada, anomalia, geofence, idempotência, ocorrências e auditoria do acesso normal.

Para testar: Usuários → abrir cadastro → QR Code → Gerar QR → Imprimir. Leia em um navegador sem sessão. A tela deve mostrar nome real, relógio e um botão. Abrir não altera registros; tocar solicita localização. Após sucesso, a tela confirma por cerca de três segundos. Regenerar e conferir que o cartão anterior retorna QR inválido.

## Causas técnicas preservadas/corrigidas

- O login duplo vinha do fluxo de troca pendente que tratava o próprio navegador como concorrente; o login atual reaproveita seu cookie válido ou substitui atomicamente a outra sessão.
- A falha de marcação do Render vinha de prepared statements incompatíveis com o pooler PostgreSQL em modo transação; o driver continua com `prepare_threshold=None`.
- A pergunta indevida usava apenas distância absoluta do horário; agora considera a posição na sequência e a proximidade da próxima marcação.
- A localização começava deliberadamente não confirmada e, antes da correção do banco, a gravação podia falhar. Ela agora permanece salva; pendência da escola e precisão do aparelho são erros distintos. O raio não foi enfraquecido.
- Leituras não disputam o mutex de gravação; sessões são verificadas a cada 30 s, chamadas idênticas simultâneas são compartilhadas e jornadas/feriados são reutilizados na mesma requisição.

## Permissões

- Suporte e Diretoria: gestão, correção própria/direta, solicitações, QR, favicon e redefinição de senha.
- Administração: cadastro, jornada, marcações, presença e Excel; sem redefinição de senha, análise de solicitações superiores, Central ou Atendimentos.
- Central de Suporte, ocorrências e Atendimentos: somente Suporte.
- Professor/Colaborador: ponto, registros próprios, perfil e abertura de chamado.

## Banco e configuração

Nenhuma migration ou coluna foi criada. QR e favicon usam a tabela `settings` existente; rótulos usam o JSON histórico da pessoa. A nova dependência é `qrcode[pil]==8.2`. Não é necessária variável de ambiente nova. Para o QR impresso abrir corretamente, o sistema deve estar publicado no endereço HTTPS definitivo do Render no momento da geração.

## Validação

- 19 testes Python passaram: autenticação, sessão concorrente, primeiro acesso, permissões, 2/4/6 marcações, tolerância, esquecimento, extras, geofence, histórico, ausência, chamados, Excel, QR sem cookie, abertura sem registro, troca de token, imagem, rótulos e admissão retroativa.
- Build React concluído: 1.578 módulos.
- Navegador desktop: login, título, sidebar, Ponto, Usuários, área QR e Marcações conferidos.
- Gerador `backend/excel.py` comparado byte a byte com a entrada e preservado.
- O teste usou banco isolado; GPS físico e banco real do Render dependem do ambiente e devem ser conferidos após deploy.

## Arquivos alterados

- backend/main.py, backend/security.py
- frontend/index.html
- frontend/src/main.jsx, pages.jsx, people.jsx, qr.jsx, style.css
- frontend/dist
- requirements.txt, tests/test_system.py
- ENTREGA-QR.md
