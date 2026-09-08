# Ajustes adicionais — ponto e resposta

- Testada a sequência exata do Suporte: 07:30, 11:00, 12:00, 17:30. Quatro marcações aceitas e dia completo.
- Jornada nova depois de uma batida continua valendo no dia seguinte, preservando histórico. Agora há aviso persistente no cadastro e contador da sequência na tela Ponto.
- Consulta de jornada reaproveitada dentro de cada requisição: relatório mensal consulta jornadas uma vez por pessoa, não uma vez por dia. Cache não persiste entre requisições.
- Localização aguarda melhora de precisão por até 8 segundos e usa leitura de no máximo 15 segundos. Termina imediatamente quando a precisão é suficiente; backend mantém limite e raio de 100 m. Erro mostra precisão informada pelo aparelho.
- Nenhuma garantia de GPS preciso em desktop: alta precisão é uma solicitação ao navegador. Se o aparelho não conseguir, continua bloqueado corretamente. Não foi criado bypass de produção.

Validação: 17 testes Python, build React e teste JavaScript de seleção da leitura e encerramento. Sem medição no Render ou no computador físico da escola. Não é possível confirmar a causa da jornada remota sem ver a vigência e as marcações daquele dia.

Envio web: extraia github-atualizacao.zip e envie backend e frontend na raiz do repositório. O pacote não inclui banco, credenciais nem dependências instaladas. Depois faça redeploy. Esta entrega está em outputs; a pasta instalada anterior não foi sobrescrita nesta rodada.
