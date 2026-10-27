(function (raiz) {
  const SocialFlow = raiz.SocialFlow = raiz.SocialFlow || {};
  SocialFlow.csrf = "";
  SocialFlow.contexto = null;
  let avisoTimer = 0;

  SocialFlow.esc = function (valor) {
    return String(valor == null ? "" : valor)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  };

  function mensagemDe(erro) {
    if (!erro) return "Não foi possível concluir.";
    const campos = erro.campos || (erro.dados && erro.dados.campos) || {};
    const textos = Object.keys(campos).map(function (chave) { return campos[chave]; });
    if (textos.length) return textos.join(" ");
    return erro.message || "Não foi possível concluir.";
  }

  SocialFlow.api = async function (caminho, opcoes) {
    const opts = opcoes || {};
    const headers = { "Accept": "application/json" };
    let body;
    if (opts.json !== undefined) {
      headers["Content-Type"] = "application/json";
      if (SocialFlow.csrf) headers["X-CSRF-Token"] = SocialFlow.csrf;
      body = JSON.stringify(opts.json);
    }
    let resposta;
    try {
      resposta = await fetch(caminho, {
        method: opts.method || (opts.json !== undefined ? "POST" : "GET"),
        headers: headers,
        body: body,
        credentials: "same-origin"
      });
    } catch (falha) {
      const erro = new Error("Não foi possível falar com o servidor local.");
      erro.cause = falha;
      throw erro;
    }
    const tipo = resposta.headers.get("content-type") || "";
    const dados = tipo.indexOf("json") >= 0 ? await resposta.json() : null;
    if (dados && dados.csrf) SocialFlow.csrf = dados.csrf;
    if (resposta.status === 403 && opts.json !== undefined && !opts._csrfRetry) {
      SocialFlow.csrf = "";
      await SocialFlow.preparar();
      return SocialFlow.api(caminho, Object.assign({}, opts, { _csrfRetry: true }));
    }
    if (!resposta.ok) {
      const erro = new Error((dados && dados.erro) || "Não foi possível concluir.");
      erro.status = resposta.status;
      erro.campos = (dados && dados.campos) || {};
      erro.dados = dados;
      throw erro;
    }
    return dados;
  };

  SocialFlow.preparar = async function () {
    const dados = await SocialFlow.api("/api/contexto");
    SocialFlow.contexto = dados;
    if (dados.loja && /^#[0-9a-fA-F]{3,8}$/.test(dados.loja.cor || "")) {
      document.documentElement.style.setProperty("--acento", dados.loja.cor);
    }
    return dados;
  };

  SocialFlow.avisar = function (mensagem, tipo) {
    const caixa = document.getElementById("aviso");
    if (!caixa) return;
    caixa.textContent = mensagem;
    caixa.className = "aviso " + (tipo === "erro" ? "erro" : "ok");
    window.clearTimeout(avisoTimer);
    avisoTimer = window.setTimeout(function () {
      caixa.textContent = "";
      caixa.className = "aviso";
    }, 5200);
  };

  SocialFlow.confirmar = function (titulo, texto) {
    const dialogo = document.getElementById("confirma");
    document.getElementById("confirma-titulo").textContent = titulo;
    document.getElementById("confirma-texto").textContent = texto;
    dialogo.showModal();
    return new Promise(function (resolve) {
      dialogo.addEventListener("close", function () {
        resolve(dialogo.returnValue === "sim");
      }, { once: true });
    });
  };

  SocialFlow.erro = mensagemDe;

  SocialFlow.lerFiltros = function () {
    try {
      return JSON.parse(localStorage.getItem("socialflow-auto.filtros") || "null");
    } catch (erro) {
      return null;
    }
  };

  SocialFlow.salvarFiltros = function (filtros) {
    localStorage.setItem("socialflow-auto.filtros", JSON.stringify(filtros));
  };

  SocialFlow.limparLocais = function () {
    localStorage.removeItem("socialflow-auto.filtros");
    sessionStorage.removeItem("socialflow-auto.consultor");
    sessionStorage.removeItem("socialflow-auto.luna");
  };

  function anguloDe(rotulo) {
    const texto = String(rotulo || "").toLowerCase();
    if (texto.indexOf("interior") >= 0) return "interior";
    if (texto.indexOf("traseira") >= 0) return "traseira";
    if (texto.indexOf("frente") >= 0) return "frente";
    return "foto";
  }

  function altFoto(veiculo, rotulo) {
    return veiculo.marca + " " + veiculo.modelo + ", " + anguloDe(rotulo);
  }

  SocialFlow.fotosDoVeiculo = function (veiculo) {
    return (veiculo.imagens || []).filter(function (imagem) {
      return imagem && imagem.url && !/\.gif$/i.test(imagem.url);
    });
  };

  SocialFlow.foto = function (veiculo) {
    const fotos = SocialFlow.fotosDoVeiculo(veiculo);
    const figura = document.createElement("figure");
    figura.className = "foto-carro";
    const img = document.createElement("img");
    const primeira = fotos[0];
    const frente = primeira ? primeira.url : "/assets/ilustracoes/" + (veiculo.tipo || "hatch") + ".svg";
    const altFrente = primeira
      ? altFoto(veiculo, primeira.rotulo)
      : "Ilustração do tipo de veículo, sem foto da unidade.";
    img.src = frente;
    img.alt = altFrente;
    img.width = 640;
    img.height = 400;
    figura.appendChild(img);
    if (fotos.length < 2) return figura;

    const gif = frente.replace(/\.(jpe?g|png|webp)$/i, ".gif");
    const reduzido = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const toque = window.matchMedia("(hover: none)").matches;
    let indice = 0;
    let timer = 0;
    let pedido = 0;

    function quadro(i) {
      const foto = fotos[i];
      img.onerror = null;
      img.src = foto.url;
      img.alt = altFoto(veiculo, foto.rotulo);
    }

    function frenteParada() {
      pedido += 1;
      window.clearInterval(timer);
      timer = 0;
      img.onerror = null;
      indice = 0;
      img.src = frente;
      img.alt = altFrente;
    }

    function ciclar() {
      if (timer) return;
      timer = window.setInterval(function () {
        indice = (indice + 1) % fotos.length;
        quadro(indice);
      }, 900);
    }

    function mover() {
      if (reduzido || timer) return;
      if (gif && gif !== frente) {
        const atual = ++pedido;
        img.onerror = function () {
          if (atual !== pedido) return;
          img.onerror = null;
          ciclar();
        };
        img.src = gif;
        img.alt = veiculo.marca + " " + veiculo.modelo + ", vários ângulos";
        return;
      }
      ciclar();
    }

    function avancar() {
      window.clearInterval(timer);
      timer = 0;
      pedido += 1;
      indice = (indice + 1) % fotos.length;
      quadro(indice);
    }

    figura.tabIndex = 0;
    figura.setAttribute("aria-label", "Fotos de " + veiculo.marca + " " + veiculo.modelo + ". Com o mouse ou o teclado, os outros ângulos entram em sequência.");
    if (!toque) {
      figura.addEventListener("mouseenter", mover);
      figura.addEventListener("mouseleave", function () {
        if (document.activeElement === figura) return;
        frenteParada();
      });
      figura.addEventListener("focus", mover);
      figura.addEventListener("blur", frenteParada);
    }
    figura.addEventListener("click", function (evento) {
      if (!toque && !reduzido) {
        if (figura.dataset.href) window.location.href = figura.dataset.href;
        return;
      }
      evento.preventDefault();
      evento.stopPropagation();
      avancar();
    });
    figura.addEventListener("keydown", function (evento) {
      if (evento.key !== "Enter" && evento.key !== " ") return;
      evento.preventDefault();
      avancar();
    });
    return figura;
  };

  function lerFavoritos() {
    try {
      const dados = JSON.parse(localStorage.getItem("socialflow-auto.favoritos") || "[]");
      return Array.isArray(dados) ? dados : [];
    } catch (erro) {
      return [];
    }
  }

  SocialFlow.favorito = function (id) {
    return lerFavoritos().indexOf(id) >= 0;
  };

  SocialFlow.alternarFavorito = function (id) {
    const lista = lerFavoritos().filter(function (item) { return item !== id; });
    if (!SocialFlow.favorito(id)) lista.push(id);
    localStorage.setItem("socialflow-auto.favoritos", JSON.stringify(lista));
  };

  function iconeCoracao(ativo) {
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("width", "18");
    svg.setAttribute("height", "18");
    svg.setAttribute("aria-hidden", "true");
    const traco = document.createElementNS("http://www.w3.org/2000/svg", "path");
    traco.setAttribute("d", "M12 20s-7-4.4-7-9a4 4 0 0 1 7-2 4 4 0 0 1 7 2c0 4.6-7 9-7 9z");
    traco.setAttribute("fill", ativo ? "currentColor" : "none");
    traco.setAttribute("stroke", "currentColor");
    traco.setAttribute("stroke-width", "1.7");
    traco.setAttribute("stroke-linejoin", "round");
    svg.appendChild(traco);
    return svg;
  }

  SocialFlow.cartao = function (veiculo, extra) {
    const artigo = document.createElement("article");
    artigo.className = "card-veiculo";
    const href = "/veiculo?id=" + encodeURIComponent(veiculo.id);
    const midia = document.createElement("div");
    midia.className = "card-midia";
    const figura = SocialFlow.foto(veiculo);
    figura.dataset.href = href;
    midia.appendChild(figura);
    const selo = document.createElement("p");
    selo.className = "selo selo-foto selo-" + veiculo.status;
    selo.textContent = veiculo.status_rotulo;
    midia.appendChild(selo);
    const favorito = document.createElement("button");
    favorito.type = "button";
    favorito.className = "favorito";
    function pintarFavorito() {
      const ativo = SocialFlow.favorito(veiculo.id);
      favorito.classList.toggle("ativo", ativo);
      favorito.setAttribute("aria-pressed", ativo ? "true" : "false");
      favorito.setAttribute(
        "aria-label",
        ativo
          ? "Remover " + veiculo.marca + " " + veiculo.modelo + " dos favoritos deste navegador"
          : "Guardar " + veiculo.marca + " " + veiculo.modelo + " nos favoritos deste navegador"
      );
      favorito.replaceChildren(iconeCoracao(ativo));
    }
    pintarFavorito();
    favorito.addEventListener("click", function (evento) {
      evento.preventDefault();
      evento.stopPropagation();
      SocialFlow.alternarFavorito(veiculo.id);
      pintarFavorito();
    });
    midia.appendChild(favorito);
    artigo.appendChild(midia);
    const corpo = document.createElement("div");
    corpo.className = "card-corpo";
    const titulo = document.createElement("h3");
    const link = document.createElement("a");
    link.href = href;
    link.textContent = veiculo.marca + " " + veiculo.modelo;
    titulo.appendChild(link);
    corpo.appendChild(titulo);
    const versao = document.createElement("p");
    versao.className = "meta";
    versao.textContent = veiculo.versao + " · " + veiculo.ano_fabricacao + "/" + veiculo.ano_modelo;
    corpo.appendChild(versao);
    const preco = document.createElement("p");
    preco.className = "preco";
    preco.textContent = veiculo.preco;
    corpo.appendChild(preco);
    const chips = document.createElement("ul");
    chips.className = "chips";
    [veiculo.cambio_rotulo, veiculo.combustivel_rotulo, veiculo.tipo_rotulo].forEach(function (texto) {
      if (!texto) return;
      const item = document.createElement("li");
      item.textContent = texto;
      chips.appendChild(item);
    });
    corpo.appendChild(chips);
    artigo.addEventListener("click", function (evento) {
      if (evento.target.closest("a, button, .foto-carro")) return;
      window.location.href = href;
    });
    if (extra && extra.motivos && extra.motivos.length) {
      const motivos = document.createElement("ul");
      motivos.className = "motivos";
      extra.motivos.forEach(function (motivo) {
        const item = document.createElement("li");
        item.textContent = motivo;
        motivos.appendChild(item);
      });
      corpo.appendChild(motivos);
    }
    artigo.appendChild(corpo);
    return artigo;
  };

  SocialFlow.preencherLoja = function (loja) {
    document.querySelectorAll("[data-loja]").forEach(function (el) {
      const campo = el.getAttribute("data-loja");
      if (loja[campo]) el.textContent = loja[campo];
    });
    const lista = document.getElementById("lista-servicos");
    if (lista && loja.servicos) {
      lista.replaceChildren();
      loja.servicos.forEach(function (servico) {
        const artigo = document.createElement("article");
        artigo.className = "servico";
        const h = document.createElement("h3");
        h.textContent = servico.titulo;
        const p = document.createElement("p");
        p.textContent = servico.texto;
        artigo.appendChild(h);
        artigo.appendChild(p);
        lista.appendChild(artigo);
      });
    }
  };
})(window);
