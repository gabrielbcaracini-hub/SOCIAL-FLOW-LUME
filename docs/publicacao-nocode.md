# Publicação no-code — pendente

Nenhuma plataforma visual foi conectada nem publicada a partir deste ambiente. Não há URL pública.

O SocialFlow Auto que está no repositório é a aplicação local em HTML, CSS e JavaScript, com API Python. Essa camada é a personalização que a disciplina pede para ir além dos blocos prontos. Ela sobe com `python -m socialflow`.

## Por que não foi feito aqui

Webflow, Framer, Softr e Glide pedem conta, navegador autenticado e, em vários planos, recurso pago para domínio ou código embutido. Este ambiente não tem essas credenciais. Inventar um projeto nessas ferramentas deixaria o README falso.

## Caminho manual, se você for publicar

1. Suba o processo Python em um endereço HTTPS que você controle. O navegador da vitrine precisa falar com a mesma origem da API, ou será necessário configurar CORS de propósito — hoje a API não envia `Access-Control-Allow-Origin`.
2. Na ferramenta visual, crie o site da Lume Veículos com as páginas institucionais se quiser.
3. Embuta a vitrine como código personalizado apontando para a origem real, ou publique os arquivos `index.html`, `veiculo.html`, `privacidade.html`, `css/`, `js/` e `assets/` e mantenha o Python atrás deles.
4. Não coloque `SOCIALFLOW_AI_API_KEY` em página, repositório ou bloco visível. Ela fica só no processo do servidor.
5. Antes de qualquer endereço público, troque as senhas de demonstração, retire o aviso de credenciais do README se ele for exposto, e sirva a aplicação só por HTTPS. O cookie atual não usa a marca `Secure` porque o uso previsto é `http://127.0.0.1`.
6. Confira o endereço no navegador, anote a URL real no README e só então mude o status desta página para concluído.

Até esses passos acontecerem, o status permanece **PENDENTE**.
