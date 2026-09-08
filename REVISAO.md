# Revisão de 04/09/2026

## Causas e correções

- Render/Supabase: o log confirma comandos preparados inexistentes/duplicados no psycopg. A conexão agora usa prepare_threshold=None, compatível com pooler em modo transação. Mantidos bloqueio transacional e idempotência; não há repetição automática de gravação com resultado incerto.
- Login: o fluxo anterior criava uma troca pendente mesmo no mesmo navegador. Login agora é imediato; reutiliza a sessão válida do navegador e substitui atomicamente a sessão em outro dispositivo, conforme a solicitação desta revisão.
- Lentidão: leituras comuns adquiriam o mutex global de escrita e a sessão era consultada a cada segundo. Leituras agora usam sessões sem mutex, a verificação periódica passa a 30 segundos e chamadas simultâneas iguais são compartilhadas.
- Ponto: diferença absoluta de uma hora disparava esquecimento inclusive em uma entrada simplesmente atrasada. A pergunta agora considera posição e próximo horário previsto. Dias ainda sem marcação usam a jornada vigente, evitando snapshot vazio desatualizado. A mesma chave é preservada em tentativas de envio.
- Localização: a configuração inicial realmente começa não confirmada. A confirmação salva permanece no banco. Pendência da escola é distinguida de erro de GPS do aparelho; não desativamos o raio de 100 metros. Diretoria/Suporte devem conferir uma vez em Central do Suporte → Localização da escola quando ainda estiver pendente.
- Meu ponto: perfis administrativos consultavam todas as pessoas sem identificação; agora a tela envia explicitamente o identificador próprio.
- Permissões: Diretoria/Suporte com acesso explícito às funções de gestão e edição dos próprios dados; Administração continua intermediária. Suporte atende na Central, sem chamado para si.
- Interface: Seja bem-vindo, saudação pelo primeiro nome, telefone formatado, verdes e branco, card do relatório centralizado. Gerador backend/excel.py preservado byte a byte.
- Erros inesperados retornam mensagem compreensível e referência para cruzar com o log; detalhes sensíveis de SQL não são expostos. HEAD / e /health aceitos.

## Validação

15 testes automatizados passaram: sessão/primeira senha, geofence, confirmação persistente, atraso, quatro e seis marcações, faltas, horas extras, idempotência concorrente, jornadas históricas, chamados, permissões, auditoria, fechamento e Excel. Build de produção React concluído.
Conferência em navegador local isolado em desktop 1280×720 e celular 390×844: login, sidebar, Ponto, Pessoas/modal, máscara de telefone, Meu ponto, Excel e Central/Atendimento. Nenhum banco real foi usado nos testes.
A correção PostgreSQL foi validada na configuração do driver; não houve conexão ao banco real do Render nem teste físico de GPS na escola. O redeploy ainda precisa ser feito no Render.

## Arquivos alterados

backend/db.py, backend/main.py, backend/rules.py, backend/security.py;
frontend/src/main.jsx, pages.jsx, people.jsx, ui.jsx, style.css;
frontend/dist (interface recompilada), tests/test_system.py, LEIA-ME.md e este relatório.

## Atualizar GitHub e Render

Envie o conteúdo do projeto atualizado para a raiz do repositório (backend, frontend/dist, frontend/src, arquivos de configuração e dependências). Não envie .env, data, .venv, node_modules ou bancos locais.
Se usar o serviço Python existente com backend na raiz:

Start Command: python -m uvicorn backend.main:app --host 0.0.0.0 --port $PORT
Build Command: pip install -r requirements.txt

A interface já está compilada em frontend/dist. Para serviço Docker, mantenha o Dockerfile; não é necessário cadastrar Start Command. Faça deploy do commit atualizado. A configuração DATABASE_URL permanece no Render. A correção de comandos preparados exige os novos arquivos do backend; mudar apenas o Start Command não corrige aquele erro.
