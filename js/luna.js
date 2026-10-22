(function (raiz) {
  const SocialFlow = raiz.SocialFlow;
  let sessao = sessionStorage.getItem("socialflow-auto.luna") || "";
  let enviando = false;
  let sugestoes = [];

  function caixa() {
    return document.getElementById("luna");
  }

  function painel() {
    return document.getElementById("luna-painel");
  }

  function campoMensagem() {
    return document.getElementById("luna-mensagem");
  }

  function logEl() {
    return document.getElementById("luna-log");
  }

  function rolar() {
    const rolagem = caixa().querySelector(".luna-rolagem");
    const log = logEl();
    if (log) log.scrollTop = log.scrollHeight;
    if (rolagem) rolagem.scrollTop = rolagem.scrollHeight;
  }

  function pausaNatural(texto) {
    const n = String(texto || "").length;
    return new Promise(function (ok) {
      window.setTimeout(ok, Math.min(1600, Math.max(700, 520 + n * 9)));
    });
  }

  function anexar(no, lado) {
    const linha = document.createElement("div");
    linha.className = "luna-linha " + (lado === "pessoa" ? "luna-linha-pessoa" : "luna-linha-fala");
    linha.appendChild(no);
    logEl().appendChild(linha);
    rolar();
    return no;
  }

  function falar(classe, texto) {
    const bloco = document.createElement("p");
    bloco.className = classe;
    bloco.textContent = texto;
    return anexar(bloco, classe.indexOf("luna-pessoa") >= 0 ? "pessoa" : "fala");
  }

  function mostrarDigitando() {
    removerDigitando();
    const bloco = document.createElement("p");
    bloco.className = "luna-fala luna-digitando";
    bloco.id = "luna-digitando";
    bloco.setAttribute("aria-label", "Luna está digitando");
    bloco.innerHTML = "<span></span><span></span><span></span>";
    anexar(bloco, "fala");
  }

  function removerDigitando() {
    const atual = document.getElementById("luna-digitando");
    if (!atual) return;
    const linha = atual.closest(".luna-linha");
    if (linha) linha.remove();
    else atual.remove();
  }

  function foto(item) {
    if (item.imagens && item.imagens[0] && item.imagens[0].url) return item.imagens[0].url;
    return "/assets/marca.jpg";
  }

  function nomeVeiculo(item) {
    return [item.marca, item.modelo, item.versao].filter(Boolean).join(" ");
  }

  function montarCards(itens, titulo) {
    if (!itens || !itens.length) return;
    const caixaCards = document.createElement("div");
    caixaCards.className = "luna-cards";
    if (titulo) {
      const rotulo = document.createElement("p");
      rotulo.className = "luna-cards-titulo";
      rotulo.textContent = titulo;
      caixaCards.appendChild(rotulo);
    }
    itens.forEach(function (item) {
      const card = document.createElement("a");
      card.className = "luna-card";
      card.href = item.href || ("/veiculo?id=" + encodeURIComponent(item.id));
      const img = document.createElement("img");
      img.src = foto(item);
      img.alt = nomeVeiculo(item);
      const corpo = document.createElement("span");
      corpo.innerHTML = "<strong></strong><small></small><em></em>";
      corpo.querySelector("strong").textContent = nomeVeiculo(item);
      corpo.querySelector("small").textContent = [
        item.ano_fabricacao && item.ano_modelo ? item.ano_fabricacao + "/" + item.ano_modelo : "",
        item.km_rotulo || ""
      ].filter(Boolean).join(" · ");
      corpo.querySelector("em").textContent = item.preco || "";
      card.appendChild(img);
      card.appendChild(corpo);
      caixaCards.appendChild(card);
    });
    anexar(caixaCards, "fala");
  }

  function montarComparacao(linhas) {
    if (!linhas || !linhas.length) return;
    const tabela = document.createElement("div");
    tabela.className = "luna-comparacao";
    linhas.forEach(function (linha) {
      const item = document.createElement("a");
      item.className = "luna-comp";
      item.href = "/veiculo?id=" + encodeURIComponent(linha.id);
      item.innerHTML = "<strong></strong><small></small>";
      item.querySelector("strong").textContent = linha.nome;
      item.querySelector("small").textContent = [
        linha.preco, linha.ano, linha.km, linha.cambio, linha.combustivel, linha.tipo
      ].filter(Boolean).join(" · ");
      tabela.appendChild(item);
    });
    anexar(tabela, "fala");
  }

  function montarSimulacao(dados) {
    if (!dados) return;
    const caixaSim = document.createElement("div");
    caixaSim.className = "luna-simulacao";
    const linhas = [
      ["Valor", dados.valor],
      ["Entrada", dados.entrada],
      ["Saldo", dados.saldo],
      ["Parcelas", dados.parcelas + "x de " + dados.parcela],
      ["Total", dados.total]
    ];
    linhas.forEach(function (par) {
      const p = document.createElement("p");
      p.innerHTML = "<span></span><strong></strong>";
      p.querySelector("span").textContent = par[0];
      p.querySelector("strong").textContent = String(par[1]);
      caixaSim.appendChild(p);
    });
    const nota = document.createElement("small");
    nota.textContent = dados.tem_juros ? "Valores com as condições informadas." : "Divisão matemática, sem juros cadastrados. Não é aprovação de crédito.";
    caixaSim.appendChild(nota);
    anexar(caixaSim, "fala");
  }

  function montarAcao(acao) {
    if (!acao || !acao.tipo) return;
    const botao = document.createElement("button");
    botao.type = "button";
    botao.className = "luna-acao" + (acao.tipo === "contato" ? " luna-acao-consultor" : "");
    botao.textContent = acao.rotulo || "Continuar";
    botao.addEventListener("click", function () {
      if (acao.tipo === "contato") {
        const alvo = document.querySelector("[data-abre-contato]");
        if (alvo) {
          if (acao.veiculo_id) alvo.dataset.veiculo = acao.veiculo_id;
          alvo.click();
          return;
        }
      }
      if ((acao.tipo === "detalhes" || acao.tipo === "agendamento") && acao.veiculo_id) {
        window.location.href = "/veiculo?id=" + encodeURIComponent(acao.veiculo_id);
        return;
      }
      campoMensagem().focus();
    });
    anexar(botao, "fala");
  }

  function preferenciasLocais() {
    const id = document.body.dataset.veiculoFoco;
    return id ? { veiculo_id: id } : {};
  }

  function marcarAberto(aberto) {
    const abrir = caixa().querySelector("[data-luna-abrir]");
    if (abrir) abrir.setAttribute("aria-expanded", aberto ? "true" : "false");
  }

  function abrirPainel() {
    const raizLuna = caixa();
    raizLuna.classList.remove("recolhida");
    raizLuna.classList.add("aberta");
    painel().hidden = false;
    marcarAberto(true);
  }

  function fecharPainel() {
    const raizLuna = caixa();
    raizLuna.classList.remove("aberta");
    painel().hidden = true;
    marcarAberto(false);
  }

  function recolher() {
    const raizLuna = caixa();
    raizLuna.classList.add("recolhida");
    raizLuna.classList.remove("aberta");
    painel().hidden = true;
    marcarAberto(false);
  }

  async function consultar(mensagem, opcoes) {
    const config = opcoes || {};
    if (enviando) return;
    enviando = true;
    const botao = document.querySelector("#luna-form button[type=submit]");
    caixa().classList.add("luna-em-conversa");
    if (config.mostrarPessoa !== false && mensagem) falar("luna-pessoa", mensagem);
    if (botao) botao.disabled = true;
    mostrarDigitando();
    try {
      if (!SocialFlow.csrf) await SocialFlow.preparar();
      const resposta = await SocialFlow.api("/api/publico/luna", {
        json: {
          mensagem: mensagem || "",
          intencao: config.intencao || null,
          preferencias: preferenciasLocais(),
          sessao_id: sessao || null,
          reiniciar: Boolean(config.reiniciar)
        }
      });
      sessao = resposta.sessao_id || sessao;
      if (sessao) sessionStorage.setItem("socialflow-auto.luna", sessao);
      const texto = resposta.texto || "Consultei o estoque da loja.";
      await pausaNatural(texto);
      removerDigitando();
      const bloco = falar("luna-fala", texto);
      if (resposta.aviso_ia) {
        const aviso = document.createElement("small");
        aviso.className = "luna-aviso";
        aviso.textContent = resposta.aviso_ia;
        bloco.appendChild(aviso);
      }
      const itens = resposta.sugestoes || [];
      sugestoes = itens;
      montarCards(itens);
      if (resposta.alternativas && resposta.alternativas.length) {
        montarCards(resposta.alternativas, "Opções próximas");
      }
      montarComparacao(resposta.comparacao);
      montarSimulacao(resposta.simulacao);
      montarAcao(resposta.acao);
    } catch (erro) {
      removerDigitando();
      falar("luna-fala", SocialFlow.erro(erro) || "Não consegui consultar agora. Pode repetir?");
    } finally {
      enviando = false;
      if (botao) botao.disabled = false;
    }
  }

  async function enviar(evento) {
    evento.preventDefault();
    const campo = campoMensagem();
    const mensagem = campo.value.trim();
    if (!mensagem) return;
    campo.value = "";
    await consultar(mensagem, { mostrarPessoa: true });
  }

  function acaoRapida(intencao) {
    abrirPainel();
    const campo = campoMensagem();
    const texto = campo.value.trim();
    if (texto) {
      campo.value = "";
      consultar(texto, { mostrarPessoa: true, intencao: intencao });
      return;
    }
    consultar("", { mostrarPessoa: false, intencao: intencao });
    campo.focus();
  }

  document.addEventListener("DOMContentLoaded", function () {
    const raizLuna = caixa();
    if (!raizLuna) return;
    raizLuna.querySelector("[data-luna-abrir]").addEventListener("click", function () {
      if (raizLuna.classList.contains("recolhida")) {
        raizLuna.classList.remove("recolhida");
        return;
      }
      abrirPainel();
    });
    raizLuna.querySelectorAll("[data-luna-recolher]").forEach(function (botao) {
      botao.addEventListener("click", function (evento) {
        evento.stopPropagation();
        recolher();
      });
    });
    const fechar = raizLuna.querySelector("[data-luna-fechar]");
    if (fechar) fechar.addEventListener("click", fecharPainel);
    document.getElementById("luna-form").addEventListener("submit", enviar);
    raizLuna.querySelectorAll("[data-luna-acao]").forEach(function (botao) {
      botao.addEventListener("click", function () {
        const mapa = { buscar: "busca", simular: "simulacao", comparar: "comparacao", detalhes: "detalhes" };
        acaoRapida(mapa[botao.getAttribute("data-luna-acao")] || "busca");
      });
    });
  });
})(window);
