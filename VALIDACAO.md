# Validação da entrega

Testes automatizados em banco SQLite isolado:

- Primeiro acesso, troca obrigatória, ocultação do login e bloqueio de painel para Professor.
- Entrada antecipada, tolerância de atraso, saída antecipada, idempotência e intervalo mínimo entre novas batidas.
- Jornada com seis marcações, tolerância em saída intermediária/final, par extra e novo ciclo após meia-noite.
- Pergunta de esquecimento e ocorrência de comparecimento após falta.
- Recusa de geolocalização ausente, imprecisa ou distante; aceitação de posição dentro do raio.
- Vigência de jornada movida para amanhã quando o dia já começou, sem alterar o snapshot existente.
- Excel com quatro abas, filtros, congelamento, falta mesclada e feriado; bloqueio de edição, download idêntico e reabertura com nova versão.
- Persistência do chamado aberto, resposta pelo Suporte, exclusão ao concluir, solicitação cadastral e auditoria da aprovação.
- Cancelamento de novo acesso e tomada de sessão após a janela de cinco segundos.
- Requisições simultâneas sem duplicação e inativação preservando cadastro.

Também foram conferidos no navegador o login centralizado, a tela Ponto com um único card, a navegação compacta e o modal de Pessoas. A compilação de produção do React foi executada.

As credenciais e registros usados na validação estão fora do pacote de entrega. Não foi realizada implantação em Render, conexão real ao Supabase nem validação presencial do GPS.
