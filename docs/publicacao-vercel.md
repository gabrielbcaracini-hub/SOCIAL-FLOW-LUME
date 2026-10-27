# Publicar o SocialFlow Auto na Vercel

A Vercel entrega **HTTPS** no endereço `https://….vercel.app`. Ela **não** sobe o XAMPP nem o `python -m socialflow` contínuo. O site estático vai para a CDN; as rotas `/api/*` e `/midia/*` passam pela função Python em `api/index.py`.

## O que você precisa criar (conta humana)

1. Conta na [Vercel](https://vercel.com).
2. Um **MySQL na nuvem** (PlanetScale, Railway, Aiven, TiDB Cloud ou equivalente). O MariaDB do XAMPP da sua casa não é alcançável pela Vercel.
3. (Opcional) chave Gemini só se a Luna for reescrever texto na demo pública.

## Banco

Importe `migrations/mysql/001_inicial.sql` e `migrations/mysql/002_tokens.sql` no MySQL da nuvem. Na primeira invocação fria a função tenta `preparar_banco` (seed da Lume). Se o schema já existir vazio, o seed cria a loja.

Fotos **enviadas pelo painel** não ficam no disco da Vercel (sistema de arquivos efêmero). Use o estoque já semeado com arquivos de `/assets`. Cadastro com upload novo é para o ambiente local.

O vídeo `assets/hero-renault.mp4` tem cerca de 4 MB e cabe no deploy Hobby.

## Variáveis na Vercel (Settings → Environment Variables)

Não commite estes valores.

```text
SOCIALFLOW_DB_DRIVER=mysql
SOCIALFLOW_MYSQL_HOST=
SOCIALFLOW_MYSQL_PORT=3306
SOCIALFLOW_MYSQL_USER=
SOCIALFLOW_MYSQL_PASSWORD=
SOCIALFLOW_MYSQL_DATABASE=socialflow
SOCIALFLOW_ADMIN_PASSWORD=
SOCIALFLOW_SELLER_PASSWORD=
SOCIALFLOW_CONSULTOR_PASSWORD=
SOCIALFLOW_AI_API_KEY=
```

`VERCEL=1` já é definido pela plataforma: o cookie de sessão sai com `Secure` e o upload de foto é recusado.

## Deploy

Na pasta do projeto, com a CLI da Vercel logada:

```text
npx vercel
```

Ou: GitHub → Import Project na Vercel, raiz deste repositório.

Confira depois: `/` (vitrine), `/privacidade`, `/painel` (login), um lead com consentimento. Vendedor não deve gravar veículo.

## Limites

- Função Hobby: cerca de 10 segundos. Luna + Gemini no cold start pode falhar; sem chave a Luna local continua.
- Rate limit continua em memória (cada instância).
- Restaurar demonstração continua ativo para a banca; não use isso como loja real.
