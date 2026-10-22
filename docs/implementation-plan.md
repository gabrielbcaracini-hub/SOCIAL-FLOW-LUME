# Plano de implementação — SocialFlow Auto

## Decisão de produto

O repositório era um portal estático de estudo do CRAS (famílias, atendimentos, coletivos, benefícios eventuais e relatório RMA), com dados só no `localStorage`. Não havia Git, banco, autenticação nem servidor.

O produto passou a ser a **Lume Veículos**, loja fictícia dentro do **SocialFlow Auto**: vitrine, consultoria de escolha, atendimento comercial e pedido de visita ou test-drive. O segmento automotivo adapta o enunciado de “pequena empresa de serviços”. Não existe equipe de desenvolvimento na história da loja; a operação diária acontece no painel, sem alterar código.

Não havia dados reais para migrar. O seed antigo era fictício e socioassistencial (incluindo NIS de demonstração). Ele foi removido de propósito, sem cópia no repositório.

## O que foi reaproveitado

Técnica, não domínio:

- HTML semântico, link de pular conteúdo, `aria-current`, regiões e rótulos.
- CSS com `box-sizing`, seletores, unidades `rem`/`clamp`, grade, foco visível e media queries.
- Módulos JavaScript em função imediata, escape de texto e `localStorage` só para filtros da interface.
- Diálogo de confirmação e aviso temporário no painel.

## O que foi substituído

Todas as telas, scripts e regras de CRAS, PAIF, PAEFI, SCFV, RMA, famílias, atendimentos, coletivos e benefícios. A aparência verde institucional também saiu.

## Stack

Python 3 da biblioteca padrão e SQLite. Nesta máquina não há Node.js. A escolha evita dependência que não dá para instalar e reproduzir.

- Interface em HTML, CSS e JavaScript, servida pelo mesmo processo.
- Regras de catálogo, recomendação, agenda e validação em módulos testáveis.
- Sessão em cookie `HttpOnly`, CSRF, senha com scrypt e isolamento por `organization_id`.
- Chave de modelo generativo só no servidor, pela variável `SOCIALFLOW_AI_API_KEY`. Sem a chave, o consultor é automação determinística e diz isso na tela.

## No-code / low-code

Softr, Webflow, Framer e Glide exigem conta e publicação humana. Nenhuma foi operada aqui. O status da integração e da URL pública é **PENDENTE**. O passo a passo manual está em `docs/publicacao-nocode.md`. Não há link público.

O que existe de fato é a personalização em HTML, CSS e JavaScript e a configuração da loja no painel (textos, expediente, cor e quantidade de sugestões) sem editar código.

## Modelo

`organizations`, `users`, `business_settings`, `vehicles`, `vehicle_images`, `leads`, `appointments`, `chat_sessions`, `chat_messages`, `auth_sessions`, `client_contexts`, `audit_log`. Migração em `migrations/001_inicial.sql`.

A vitrine pública usa a organização de slug `lume`. Consulta e alteração administrativas usam a organização do usuário autenticado.

## Regras que os testes cobrem

- Recomendação só de veículo `disponivel` da mesma organização.
- Veículo vendido sai da vitrine e do consultor.
- Pedido de visita nasce `solicitado`. Confirmar ou reagendar recusa sobreposição de horário confirmado no mesmo veículo.
- Lead exige consentimento. O resumo é gerado no servidor. O texto livre do chat não é gravado.
- Vendedor não altera configuração. Usuário de outra loja não lê o estoque da Lume pelo painel.
- Cor de destaque precisa de contraste mínimo com texto branco.

## Status

| Entrega | Status |
| --- | --- |
| Vitrine, detalhe, filtros, consultor, lead, visita e painel | IMPLEMENTADO |
| Testes automatizados | TESTADO no ambiente local |
| Navegação no navegador | VALIDADO em http://127.0.0.1:8080, inclusive viewport de 390px |
| Softr, Webflow, Framer ou Glide | PENDENTE — exige conta humana |
| URL pública | PENDENTE — não publicada |
| Vídeo, roteiro e parte teórica da disciplina | Fora deste repositório |
