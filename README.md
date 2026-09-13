# Ponto IEBB · versão 3.0

Sistema de registro de jornada do Instituto Educacional Batista Bíblico. Backend em
Python/FastAPI e interface React/JavaScript/CSS, com navegação adaptada a celular e computador.

## Funcionalidades

- Login, recuperação por e-mail, troca de senha e seleção de até dois perfis.
- Cadastro de pessoas, admissão, desligamento, jornadas com vigência e grade de professores.
- Registro de ponto com horário do servidor, localização e proteção contra envio duplicado.
- Acesso por QR institucional, histórico, faltas, horas extras e correções auditadas.
- Solicitações de ajuste, ocorrências, atendimento de suporte e calendário escolar.
- Exportação de registros, resumos e professores para Excel.
- Configurações de localização, QR, favicon e armazenamento.

Novas contas e redefinições usam a senha padrão `102030`, por escolha da escola.
A troca é opcional em Meu perfil; uma nova senha deve ter de 8 a 128 caracteres.
Contas existentes mantêm suas senhas e podem acessar o ponto sem troca obrigatória.

## Executar no Linux

Requisitos: Python 3.12 ou superior e Node.js 22.12 ou superior. Em uma instalação
Fedora, os pacotes podem ser instalados com `sudo dnf install python3 nodejs npm`.

Na pasta do projeto:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
```

Edite `.env` e defina `BOOTSTRAP_PASSWORD` com uma senha privada para o primeiro acesso.
O login inicial é `suporte`. Essa configuração só cria uma conta se o banco estiver
vazio; nunca substitui a senha de uma conta existente. A localização da escola deve
ser conferida em Configurações antes de liberar marcações.

```bash
cd frontend
npm ci
npm run build
cd ..
python start.py
```

Abra `http://127.0.0.1:5050`. O banco local fica em `data/ponto.db`, ignorado pelo Git.
Para desenvolvimento da interface, execute `npm run dev` em outro terminal dentro
de `frontend`; o Vite encaminha `/api` ao backend na porta 5050.

## Organização

```text
backend/
  main.py           inicialização, cabeçalhos HTTP e arquivos da interface
  routes/           autenticação, pessoas, ponto, solicitações, suporte e relatórios
  schemas.py        validação dos contratos críticos da API
  db.py             modelos e transações
  rules.py          regras de jornada e apuração
  security.py       senhas, sessões e permissões
  excel.py          relatórios
  backup.py         cópia dos registros em JSON/ZIP
migrations/         revisões versionadas do banco
frontend/src/
  app.jsx           sessão e navegação
  components/       acesso inicial e painel de ponto
  pages/            telas por responsabilidade
  people.jsx        cadastro e configuração de jornadas
  ui.jsx            controles compartilhados e cliente da API
  styles/           apresentação da versão 3.0
tests/              testes das regras, permissões e migrações
frontend/e2e/       testes em navegador com banco descartável
```

## Banco existente e migração

A revisão `0001` aceita o esquema da versão 2.0 e preserva seus registros. Antes de
adotar um banco existente, mantenha um backup externo e valide em uma cópia. A migração
confere a presença das colunas esperadas, cria tabelas ausentes e registra a revisão.
Ela é executada na inicialização e pode ser repetida. Não há limpeza automática.
Um esquema diferente do esperado provoca um erro explícito para análise.

```bash
python -m backend.backup backups/ponto-antes-da-atualizacao.zip
alembic current
```

O ZIP contém dados privados e hashes de credenciais; guarde-o fora do repositório.
Para PostgreSQL, prefira também um backup nativo do provedor. O utilitário ZIP não
implementa restauração automática; restauração e ensaio de recuperação exigem uma
cópia isolada. Não há downgrade destrutivo automático da revisão inicial.

## Verificações

```bash
ruff check backend migrations tests
ruff format --check backend migrations tests
python -m pytest -q
cd frontend
npm run format:check
npm run build
npx playwright install chromium
npm run test:e2e
```

Os testes Python criam um SQLite descartável. Para testar PostgreSQL, use um banco
exclusivo chamado `ponto_test` e forneça `PONTO_TEST_POSTGRES`. Esse banco terá suas
tabelas de aplicação apagadas durante os testes. `DATABASE_URL` de produção nunca é
usado pela suíte. Os testes de navegador iniciam seu próprio servidor na porta 5051.

O GitHub Actions executa backend em SQLite/PostgreSQL, compilação e testes de navegador.

## GitHub e Render

O serviço é construído pelo `Dockerfile`: o Node compila a interface e a imagem final
executa apenas Python. O arquivo `render.yaml` descreve o serviço e suas variáveis.

No serviço existente do Render, confira:

1. Repositório `IsacAndrew/ponto_iebb`, branch `main`, ambiente Docker.
2. `DATABASE_URL` com PostgreSQL e as credenciais privadas já configuradas no painel.
3. `BOOTSTRAP_PASSWORD` se o banco estiver vazio; SMTP se quiser recuperar acesso por e-mail.
4. Health check `/health`; a resposta inclui `version: 3.0.0` e verifica o banco.
5. Deploy automático após os testes de CI, se essa opção estiver disponível no serviço.

Um push não confirma por si só que o Render publicou a aplicação. Consulte o status
do deploy e `/health` para confirmar. Nenhum segredo deve ser colocado no GitHub.

## Comportamentos e limites conhecidos

- A localização depende da permissão e precisão informadas pelo aparelho. Use HTTPS
  no serviço remoto. Coordenadas do navegador não equivalem a comprovação antifraude.
- Jornadas são diurnas: cada período precisa terminar depois de começar, na mesma data.
- A regra de tolerância da versão anterior foi preservada. Mudanças de cálculo devem
  ser acordadas com a escola e cobertas por testes.
- Gravações continuam serializadas para preservar a consistência com as regras antigas.
  Essa escolha deve ser reavaliada com um teste de carga representativo da escola.
- A função de limpeza completa continua restrita ao Suporte, exige senha e confirmação
  explícita e também remove o histórico. Nunca use essa função para atualizar a versão.
- Registro offline não é confirmado: a interface só mostra sucesso após a resposta do servidor.
