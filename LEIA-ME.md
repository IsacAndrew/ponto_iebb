# Livro-Ponto Digital — nova implementação

## Abrir no Windows

1. Extraia o ZIP inteiro para uma pasta do computador.
2. Dê dois cliques em **iniciar.bat**.
3. Entre com login **suporte** e senha temporária **102030**.
4. Você pode criar sua senha definitiva, com pelo menos 4 caracteres, no aviso exibido após entrar.

O inicializador prepara as dependências Python quando faltarem, inicia o servidor e abre o navegador. Ele procura Python instalado e também reconhece o Python incluído no Codex deste computador. Se nenhum estiver disponível, instale Python 3.12 ou superior. Na primeira execução, é necessária internet para baixar dependências. A interface React já está compilada no pacote: não precisa instalar Node.js para testar.

O servidor usa a porta 5050. Se estiver ocupada, procura outra até 5099. Feche a janela do inicializador para parar o sistema. O endereço local funciona neste computador. No celular, o uso normal será pelo endereço HTTPS da hospedagem.

## Primeiro teste

- Em **Pessoas**, abra Isac e cadastre sua Jornada, com dias e períodos. Salve antes de registrar ponto.
- A conta de Suporte pode controlar apenas a exigência de localização da própria conta em **Central do Suporte → Exigir localização para minha conta**. A opção começa ligada e cada alteração fica registrada na auditoria.
- Cadastre outra pessoa com login próprio e perfil adequado. A senha inicial dela será `102030`.
- Em **Pessoas → Presença do dia**, registre ou desmarque faltas.
- Em **Meu ponto**, consulte horários e solicite correções. Em **Registros**, os perfis administrativos podem consultar e corrigir, sempre com motivo.
- Em **Central do Suporte**, analise ocorrências e valide horas extras.
- Em **Falar com Suporte**, abra e responda chamados. Diretoria e Suporte atendem e concluem na Central do Suporte → Atendimento. Suporte não abre chamado para si mesmo.
- Em **Excel**, escolha o mês e confirme sua senha para fechar e baixar. É possível baixar novamente quantas vezes quiser.

O pacote não contém pessoas ou marcações de demonstração. Os testes automatizados e a conferência visual usaram bancos separados do banco que você criará.

## Localização

Centro inicial proposto: `-23.67637077, -46.76243126`, raio de **100 m**. A coordenada publicada para a escola coincide com o ponto aproximado informado no histórico. Ela fica **não confirmada** até Diretoria ou Suporte verificar o endereço/ponto no mapa em **Central do Suporte → Localização da escola**, informar a senha e marcar a confirmação para uso real.

Fontes consultadas:

- Endereço: [Diário Oficial de São Paulo, 30/10/2018](https://www.imprensaoficial.com.br/Certificacao/GatewayCertificaPDF.aspx?notarizacaoID=9534a127-3f37-4af9-8085-7818b39f2585).
- Coordenada publicada: [Escolas no Brasil — Batista Bíblico](https://www.escolasnobrasil.com/sudeste/batista-biblico-instituto-educacional-sao-paulo).

O navegador solicita alta precisão apenas ao registrar. O backend recalcula a distância e rejeita coordenadas inválidas, fora do raio ou com precisão acima do limite. O limite inicial de precisão é 100 m, ajustável pelo Suporte entre 1 e 100 m. A confirmação no local e o comportamento dos aparelhos da escola ainda precisam ser testados. A posição fornecida pelo navegador não constitui comprovação antifraude de GPS.

## Regras implementadas

**Jornadas e ponto.** Uma pessoa possui períodos por dia da semana, sem limite fixo de quatro batidas. Jornadas excepcionais podem valer somente em uma data. Novas vigências não alteram dias anteriores. Quando o dia já tem marcação, uma alteração que começaria hoje passa para amanhã. A grade de aulas é independente, usa Turma e não contém Sala.

Entradas são liberadas cinco minutos antes do previsto. O atraso desconta a tolerância: 07:06 para entrada 07:00 resulta em 1 minuto. Saídas até cinco minutos depois não geram extra; 15:06 para saída 15:00 resulta em 1 minuto extra. Saídas antecipadas contabilizam a diferença real. O total trabalhado usa os horários efetivos; o saldo aplica as tolerâncias. Portanto, total trabalhado menos previsto pode diferir do saldo apurado.

A confirmação de esquecimento considera a sequência: atraso superior a 60 minutos e proximidade da próxima marcação prevista; na última marcação, diferença de pelo menos três horas. Uma entrada apenas atrasada não gera a pergunta automaticamente. O atraso nunca impede a batida. Após as marcações previstas, só uma confirmação de hora extra abre um novo par entrada/saída. Extra calculada e extra adicional ficam pendentes de validação. Não se presume uma entrada extra retroativa. A virada de data inicia outro ciclo, sem reaproveitar uma saída faltante do dia anterior.

O botão bloqueia durante o envio; o servidor serializa alterações no banco, usa chave de idempotência e impede duas novas marcações em menos de 30 segundos. Uma repetição com a mesma chave retorna o resultado já salvo.

**Faltas e calendário.** Faltas registradas não bloqueiam comparecimento. Comparecimento após falta gera aviso e ocorrência. Feriados não geram negativo por ausência. Dias incompletos ficam sinalizados; seu saldo não é inventado nem somado como se fosse completo. A tela do Suporte identifica dias anteriores incompletos ao abrir a central.

**Acesso.** Professor e Colaborador acessam apenas dados próprios. Administração, Diretoria e Suporte acessam gestão. Diretoria não tem jornada obrigatória. Administração não gerencia contas de Diretoria/Suporte. Diretoria e Suporte possuem permissões completas de gestão e podem editar os próprios dados cadastrais. Senhas usam PBKDF2 com salt individual. Sessões usam cookie HttpOnly e expiram em 12 horas. Um novo acesso assume imediatamente a sessão, sem telas intermediárias. No mesmo navegador a sessão válida é reaproveitada; outro dispositivo invalida a sessão anterior. O servidor valida o estado da sessão em cada requisição. Tentativas de login têm limite por conta.

**Solicitações e auditoria.** Usuários comuns solicitam alteração cadastral ou correção, sem editar o registro. Aprovações, reprovações, correções diretas, jornadas, faltas e fechamento registram responsável, data, anterior, novo e motivo. Se os dados mudarem enquanto a solicitação está pendente, a aprovação é impedida para revisão. Para mostrar o login próprio, a senha é exigida novamente; sair do perfil descarta a revelação.

**Excel.** Quatro abas: Pontos - Geral, Resumo por funcionário, Resumo semanal e Alterações. Há filtros, cabeçalho fixo, marcações variáveis, jornada aplicável, total diário/semanal/mensal, atraso, extra, negativo, saldo, quantidade de batidas e identificação de testes. Valores de duração são minutos numéricos. Faltas são destacadas em vermelho e mescladas na região das batidas. Textos são protegidos contra fórmulas injetadas. O período semanal corresponde à semana iniciada na segunda-feira, considerando somente os dias do mês exportado.

**Fechamento.** A primeira exportação oficial fecha o mês com senha. A versão do arquivo é armazenada no banco e novos downloads devolvem o mesmo conteúdo. Diretoria/Suporte podem reabrir com senha e motivo. Correções e novo fechamento geram outra versão. O mês corrente também pode ser fechado: isso bloqueia inclusive novas batidas desse mês até reabertura. Não há folha de pagamento nem decisão financeira automática.

## Banco, segurança e hospedagem

No computador, os dados ficam em `data/ponto.db` (SQLite). Guarde essa pasta; ela não é descartada nas reinicializações. Não copie o banco com o servidor escrevendo nele. Para backup consistente, use o comando abaixo ou pare o servidor antes de copiar a pasta.

Para **GitHub → Render → Supabase/PostgreSQL**:

1. Crie um projeto Supabase e obtenha a conexão PostgreSQL do painel. Use conexão direta ou pooler compatível com sua rede. Com psycopg, a preparação automática de comandos está desativada para compatibilidade com o pooler em modo transação.
2. Defina `DATABASE_URL` no Render com formato `postgresql+psycopg://usuario:senha@host:5432/postgres?sslmode=require`. Codifique caracteres especiais da senha na URL. Não coloque credenciais no GitHub.
3. Suba os arquivos deste projeto para um repositório e crie o serviço Render usando o `Dockerfile` ou `render.yaml` incluído.
4. Configure `BOOTSTRAP_LOGIN=suporte` e uma `BOOTSTRAP_PASSWORD` escolhida por você. Depois da criação inicial, essas variáveis não redefinem contas existentes.
5. Para recuperação por e-mail, configure `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` e `SMTP_USE_TLS`. Nenhuma senha SMTP deve ser enviada ao GitHub.
6. O banco deve usar uma conexão de servidor com permissão de criar tabelas e ativar RLS. A inicialização cria as tabelas, ativa RLS e revoga acesso dos papéis `anon` e `authenticated` do Supabase. A aplicação usa a conexão PostgreSQL somente no backend. Não configure chave do banco no React.
7. Configure o monitor para `/health` no endereço HTTPS do serviço.

O Docker compila React e serve frontend/API no mesmo serviço. O backend recusa SQLite quando executado no Render. Dados e arquivos de fechamento ficam no PostgreSQL, não no disco efêmero do serviço.

Não houve deploy nem conexão a um Supabase real nesta entrega. A validação automatizada usa SQLite; configuração de conexão, permissões e disponibilidade do ambiente Render/Supabase exigem um teste nesse ambiente antes do uso da escola. Esta instalação é nova: não importa nem altera o banco dos sistemas anteriores.

## Desenvolvimento e backup

Arquivos separados em `backend/db.py`, `security.py`, `rules.py`, `main.py`, `excel.py`; interface em `frontend/src`. O código foi refeito, usando as versões anteriores como referência de interação e apresentação.

Para reconstruir React após alterações, instale Node.js e execute `preparar_frontend.bat`. O arquivo `pnpm-lock.yaml` também acompanha o projeto. Para desenvolvimento com atualização automática: execute o backend na porta 5050 e o Vite em 5173.

Testes:

```powershell
.venv\Scripts\python.exe -m pytest tests -q
```

Backup completo (destino escolhido por você):

```powershell
.venv\Scripts\python.exe -m backend.backup backups\livro-ponto.zip
```

O backup contém dados administrativos e hashes de senha. Guarde-o em local restrito. As mensagens de chamados concluídos deixam de existir no banco ativo; cópias anteriores em backups não são retroativamente apagadas. Para recuperação PostgreSQL, mantenha também backups nativos pelo DBeaver/pg_dump. O ZIP de JSON é uma cópia de dados; não há importador automático nesta versão.

Férias/recesso e integração de folha ficam fora desta etapa, conforme combinado.
