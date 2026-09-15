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
