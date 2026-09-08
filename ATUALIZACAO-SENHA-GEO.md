# Atualização — senha, recuperação e localização

## Alterações aplicadas

- O aviso de senha definitiva pede somente `Nova senha` e `Confirmar nova senha`.
- A troca pode ser adiada. O aviso reaparece em cada login e após duas navegações internas enquanto a conta permanecer temporária.
- A senha definitiva passa a aceitar de 4 a 128 caracteres no frontend e no backend.
- Apenas Diretoria e Suporte podem redefinir a senha de outra pessoa para `102030`.
- O bypass geral de geolocalização foi removido.
- Cada conta de Suporte tem sua própria opção `Exigir localização para minha conta`, ativada por padrão e registrada na auditoria.
- A exceção individual vale no registro comum e no QR Code, sem afetar qualquer outra conta.
- A tela de login usa o login preenchido para solicitar recuperação, sem pedir e-mail.
- A credencial de recuperação tem exatamente 8 caracteres alfanuméricos, é gerada com fonte criptográfica, vale 5 minutos e é de uso único.
- Somente o hash da credencial é salvo. O valor não aparece na API nem nos logs.
- O envio usa SMTP por variáveis de ambiente e possui resposta neutra e intervalo mínimo entre solicitações.

## Configuração no Render

Configure estas variáveis no serviço:

- `SMTP_HOST`
- `SMTP_PORT` (normalmente `587`)
- `SMTP_USER`
- `SMTP_PASSWORD`
- `SMTP_FROM`
- `SMTP_USE_TLS` (`true` para STARTTLS)

O arquivo `render.yaml` já declara esses campos. Os valores secretos devem ser preenchidos somente no painel do Render.

## Banco de dados

Não é necessária migração. As credenciais temporárias, limites de solicitação e preferências individuais de localização usam a tabela de configurações existente.

## Validação

- 22 testes automatizados aprovados.
- Backend compilado sem erro.
- Frontend React compilado para produção.
- Fluxos cobertos: autenticação temporária, senha mínima, recuperação por e-mail, expiração e uso único, permissões de redefinição, geofence individual do Suporte, ponto normal, QR Code, jornadas variáveis e Excel.

