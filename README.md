# SocialFlow Auto

Atendimento que consulta o estoque de verdade.

Plataforma local de vitrine, consultoria de escolha e gestão comercial para uma revendedora fictícia de veículos. A loja de demonstração se chama **Lume Veículos**.

## Problema

Uma revenda pequena atendia por mensagem solta. O cliente não via o que estava disponível, o vendedor repetia preço e característica, e a visita era combinada sem horário nem registro. O SocialFlow Auto publica o estoque, responde só com carros que existem e deixa a equipe confirmar a visita.

A disciplina *Padrões Web para No Code e Low Code* pede uma empresa de serviços. A Lume entra nesse enquadro pelos serviços de consultoria de escolha, atendimento comercial e agendamento de visita ou test-drive, além da venda. O segmento automotivo é uma adaptação desse cenário.

Vídeo, roteiro e texto teórico da faculdade ficam fora deste repositório.

## O que dá para fazer

1. Ver a vitrine, filtrar e ordenar.
2. Abrir o veículo, registrar interesse ou pedir visita. O pedido nasce como **solicitado**. Não há confirmação automática.
3. Falar com um consultor numa janela pequena, a partir do botão ou do item Consultor. A pessoa escolhe o carro e o nome de quem vai atender. A mensagem cai no painel, atribuída a esse consultor, e não confirma a visita sozinha.
4. Conversar com o consultor de estoque. Sem chave de modelo, a resposta é automação determinística e a tela diz isso. Ela não inventa carro, preço, desconto, financiamento nem garantia.
5. Entrar no painel, ver indicadores calculados dos registros, cadastrar veículo, mudar status, tratar lead e confirmar ou reagendar visita.
6. Ajustar nome, textos, expediente, cor e quantidade de sugestões sem editar código.

Dados de pessoas são fictícios. Não há CPF, endereço residencial nem dado de saúde. As fotos da vitrine são arquivos reais em `assets/veiculos/`, com fonte e licença em `data/creditos-fotos.md`. A legenda deixa claro quando a foto é do modelo ou da geração, e não da unidade anunciada.

## Como abrir

Requisito: Python 3.11 ou mais recente. Não há `pip install`.

```text
python -m socialflow
```

Abra [http://127.0.0.1:8080](http://127.0.0.1:8080). Não abra o HTML direto pelo disco: a página e a API precisam da mesma origem.

Opcional: copie `.env.example` para `.env` antes da primeira semeadura. Se o banco já existir, mudar a senha no `.env` não altera o usuário gravado. Para recomeçar do zero, apague `data/socialflow.sqlite` e suba de novo. No painel, a administração também pode usar **Restaurar demonstração**, que repõe estoque, leads e visitas desta loja e mantém os usuários.

### Contas locais

Valem só neste ambiente. Não são senha de produção.

| Papel | E-mail | Senha inicial |
| --- | --- | --- |
| Administração | marina.costa@lume.demo | Lume-Demo-2026 |
| Vendas | ricardo.nunes@lume.demo | Lume-Venda-2026 |
| Vendas | camila.duarte@lume.demo | Lume-Consulta-2026 |

Vendas opera estoque, leads e agenda. Cada consultor de vendas vê os contatos direcionados a ele. A administração vê todos. Só a administração muda a configuração da loja e restaura a demonstração.

Se o banco já existia antes da Camila Duarte, o próximo `python -m socialflow` cria essa conta com a senha acima (ou `SOCIALFLOW_CONSULTOR_PASSWORD`). Isso não troca a senha de quem já estava gravado.

## Consultor

A frase da pessoa é interpretada por regras (orçamento, câmbio, tipo, combustível, quilometragem, uso). A busca usa somente veículos **disponíveis** da Lume. Até três sugestões voltam com o motivo ligado ao cadastro. Se nada couber, a resposta diz qual filtro esvaziou a busca. “Automático” aceita automático, CVT e automatizado. “CVT” sozinho é específico.

O texto livre da conversa não é gravado. Ficam as preferências já estruturadas e os identificadores sugeridos. Dá para apagar essa conversa no próprio consultor.

A IA padrão é o **Gemini**. A chave fica só no servidor (`SOCIALFLOW_AI_API_KEY`, `GEMINI_API_KEY` ou `GOOGLE_API_KEY`) e nunca vai para o navegador. Sem chave, consultor e Luna continuam na automação do estoque. Com chave, o Gemini só reescreve o texto dos veículos e fatos já escolhidos. Se a resposta não bater com esses dados, ela é descartada.

## Luna

A Luna é a assistente da vitrine. O balão e o painel continuam no canto direito. O backend interpreta a intenção, consulta o estoque real, compara veículos, faz divisão matemática de valores e encaminha para o consultor quando a pessoa pede atendimento humano.

Arquivos principais:

- `socialflow/luna.py` — intenções, filtros, comparação, simulação e dados da loja
- `socialflow/servicos.py` e `socialflow/servidor.py` — `POST /api/publico/luna`
- `socialflow/ia.py` — redação opcional via Gemini (`generateContent`)
- `js/luna.js` e `css/socialflow.css` — conversa, cards, digitação e ações

A chave de IA, se existir, permanece só no servidor. Sem ela, a Luna continua funcional com as regras do estoque. A simulação não inventa juros nem aprova crédito. Reservar, avaliar usado e confirmar visita continuam dependendo da equipe.

## Agenda

Horário de Brasília, deslocamento fixo UTC−3, de hora em hora, dentro do expediente. Dois pedidos solicitados podem coincidir. Confirmar ou reagendar recusa outro horário já confirmado ou reagendado do mesmo veículo.

## Stack

HTML, CSS e JavaScript no navegador. Python da biblioteca padrão e SQLite no servidor. Nesta máquina não há Node.js; a stack foi escolhida para rodar sem pacote externo.

Não houve publicação em Softr, Webflow, Framer ou Glide. Essas ferramentas pedem conta humana. O passo a passo, ainda não executado, está em `docs/publicacao-nocode.md`. **Não existe URL pública.**

## Arquitetura

```text
index.html, veiculo.html, painel.html, privacidade.html
css/socialflow.css
js/                     interface
socialflow/             regras, validação, sessão, consultor
migrations/001_inicial.sql
data/socialflow.sqlite  criado na primeira execução
docs/                   plano, publicação pendente, capturas
tests/
```

A organização pública é a de slug `lume`. O painel só enxerga a organização do usuário autenticado. Senha com scrypt, cookie `HttpOnly`, token CSRF e limite de tentativas em login, consultor e formulários.

O plano de migração está em `docs/implementation-plan.md`.

## Testes

Comando executado na raiz do projeto:

```text
python -m unittest discover -s tests -v
```

Resultado real desta entrega: **35 testes unitários da Luna e da API, mais a suíte existente — OK**.

Cobrem filtro e preço, recomendação que ignora vendido e outra loja, horário e conflito, consentimento, lead, visita, CRUD que some da vitrine ao vender, imagem inválida, CSRF e ausência do domínio antigo nas telas.

Não há typecheck separado: o projeto não usa anotações obrigatórias nem mypy instalado. A checagem feita foi importar e executar os testes.

## Capturas

Feitas no navegador local, não são mock:

- `docs/screenshots/vitrine.png`
- `docs/screenshots/vitrine-estreita.png` — conteúdo medido a 390px de largura, uma coluna, sem estouro horizontal. A imagem ainda mostra área vazia ao lado porque a janela capturada era mais larga que essa coluna.

## Verificação manual

No navegador embutido, em `http://127.0.0.1:8080`:

- a vitrine listou o estoque e omitiu o sedã vendido;
- o filtro sedã até R$ 140.000 deixou Corolla e Civic;
- o detalhe do Corolla abriu e o interesse de Helena Prado entrou no painel;
- o consultor, ao ouvir “picape diesel”, respondeu que não havia veículo e apontou o combustível;
- o login de Marina Costa mostrou 8 disponíveis, 1 reservado, 1 vendido e o Corolla com 2 interesses;
- o status desse lead foi gravado como contatado;
- a 390px a grade ficou em uma coluna e a página não estourou na horizontal.

Essa verificação deixou o lead `helena.navegador@exemplo.demo` como contatado. **Restaurar demonstração** devolve o conjunto inicial.

## Segurança e limites

- Cookie sem marca `Secure`, porque o uso previsto é HTTP local.
- Sem troca de senha na tela.
- Sem multiempresa operacional: o banco já separa por organização, mas só a Lume aparece na vitrine.
- Sem WhatsApp, cobrança ou publicação.
- Upload aceita PNG, JPEG e WebP até 1,5 MB. SVG é recusado.

## O que veio do sistema anterior

O portal de assistência social (famílias, atendimentos, coletivos, benefícios e relatório) foi substituído. Permaneceram técnicas: HTML semântico, CSS com box model, seletores e unidades relativas, foco visível, módulos JavaScript e persistência local só para os filtros da vitrine. O estoque e os leads ficam no SQLite.
