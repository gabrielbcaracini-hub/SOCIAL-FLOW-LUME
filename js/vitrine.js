(function (raiz) {
  const SocialFlow = raiz.SocialFlow;

  function lerFormulario() {
    const form = document.getElementById("filtros");
    const dados = new FormData(form);
    const saida = {};
    dados.forEach(function (valor, chave) {
      if (String(valor).trim()) saida[chave] = String(valor).trim();
    });
    return saida;
  }

  function aplicarSalvos() {
    const salvos = SocialFlow.lerFiltros();
    const form = document.getElementById("filtros");
    if (!salvos || !form || !Object.keys(salvos).length) return false;
    Object.keys(salvos).forEach(function (chave) {
      if (form.elements[chave]) form.elements[chave].value = salvos[chave];
    });
    return true;
  }

  function consulta(filtros) {
    const params = new URLSearchParams(filtros);
    return "/api/publico/veiculos" + (params.toString() ? "?" + params.toString() : "");
  }

  function textoContagem(n) {
    return "Encontrados " + n + (n === 1 ? " veículo" : " veículos");
  }

  function sincronizarBusca() {
    const topo = document.getElementById("busca-topo");
    const campo = document.getElementById("q");
    if (topo && campo) topo.value = campo.value;
  }

  async function carregar() {
    const lista = document.getElementById("lista-veiculos");
    const vazio = document.getElementById("estado-vazio");
    const carregando = document.getElementById("estado-carregando");
    const contador = document.getElementById("contador-vitrine");
    const filtros = lerFormulario();
    if (Object.keys(filtros).length) SocialFlow.salvarFiltros(filtros);
    else localStorage.removeItem("socialflow-auto.filtros");
    sincronizarBusca();
    carregando.hidden = false;
    lista.replaceChildren();
    vazio.hidden = true;
    try {
      const dados = await SocialFlow.api(consulta(filtros));
      carregando.hidden = true;
      if (contador) contador.textContent = textoContagem(dados.veiculos.length);
      if (!dados.veiculos.length) {
        vazio.hidden = false;
        return;
      }
      dados.veiculos.forEach(function (veiculo) {
        lista.appendChild(SocialFlow.cartao(veiculo));
      });
    } catch (erro) {
      carregando.hidden = true;
      vazio.hidden = false;
      vazio.textContent = SocialFlow.erro(erro);
      if (contador) contador.textContent = "Contagem indisponível";
    }
  }

  function aceleraHero() {
    const palco = document.querySelector(".hero-foto");
    const carro = palco ? palco.querySelector(".hero-carro") : null;
    if (!palco || !carro) return;
    if (carro.tagName === "VIDEO") {
      palco.classList.add("assentou");
      return;
    }
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      palco.classList.add("assentou");
      return;
    }
    const disparar = function () {
      if (palco.classList.contains("em-acelera") || palco.classList.contains("assentou")) return;
      void carro.offsetWidth;
      palco.classList.add("em-acelera");
    };
    carro.addEventListener("animationend", function (evento) {
      if (evento.target !== carro || evento.animationName !== "hero-acelera") return;
      palco.classList.remove("em-acelera");
      palco.classList.add("assentou");
    });
    window.requestAnimationFrame(disparar);
  }

  function marcarNav(nome) {
    document.querySelectorAll("[data-nav]").forEach(function (link) {
      if (link.dataset.nav === nome) link.setAttribute("aria-current", "page");
      else link.removeAttribute("aria-current");
    });
  }

  function limparFiltros() {
    const form = document.getElementById("filtros");
    const nota = document.getElementById("nota-filtros");
    const topo = document.getElementById("busca-topo");
    if (form) form.reset();
    localStorage.removeItem("socialflow-auto.filtros");
    if (nota) nota.hidden = true;
    if (topo) topo.value = "";
  }

  function iniciarCarrossel() {
    const caixa = document.getElementById("carrossel-vitrine");
    if (!caixa) return;
    const slides = caixa.querySelectorAll("[data-carrossel-slide]");
    const bolinhas = caixa.querySelectorAll(".carrossel-bolinhas button");
    const janela = caixa.querySelector(".carrossel-janela");
    if (slides.length < 2) return;
    let indice = 0;
    let timer = 0;
    const reduzido = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    function mostrar(i) {
      indice = (i + slides.length) % slides.length;
      slides.forEach(function (slide, pos) {
        slide.classList.toggle("ativo", pos === indice);
      });
      if (bolinhas.length) {
        bolinhas.forEach(function (botao, pos) {
          botao.setAttribute("aria-selected", pos === indice ? "true" : "false");
        });
      }
    }

    function parar() {
      window.clearInterval(timer);
      timer = 0;
    }

    function andar(ms) {
      parar();
      if (reduzido) return;
      timer = window.setInterval(function () {
        mostrar(indice + 1);
      }, ms);
    }

    bolinhas.forEach(function (botao, pos) {
      botao.addEventListener("click", function () {
        mostrar(pos);
        andar(caixa.matches(":hover") ? 900 : 4200);
      });
    });

    caixa.addEventListener("mouseenter", function () { andar(900); });
    caixa.addEventListener("mouseleave", function () { andar(4200); });
    if (janela) {
      janela.addEventListener("focus", function () { andar(900); });
      janela.addEventListener("blur", function () { andar(4200); });
    }
    andar(4200);
  }

  function entrarConsulta() {
    const jaEstava = document.body.classList.contains("modo-consulta");
    document.body.classList.add("modo-consulta");
    marcarNav("consulta");
    if (!jaEstava) {
      limparFiltros();
      carregar();
    }
    window.scrollTo(0, 0);
  }

  function sairConsulta() {
    if (!document.body.classList.contains("modo-consulta")) return;
    document.body.classList.remove("modo-consulta");
    marcarNav("vitrine");
  }

  async function iniciar() {
    aceleraHero();
    iniciarCarrossel();
    const consultaInicial = window.location.hash === "#consulta";
    marcarNav(consultaInicial ? "consulta" : (document.body.dataset.pagina || "vitrine"));
    if (consultaInicial) document.body.classList.add("modo-consulta");
    try {
      const ctx = await SocialFlow.preparar();
      SocialFlow.preencherLoja(ctx.loja);
      SocialFlow.montarPerfilCrm(ctx.usuario);
    } catch (erro) {
      SocialFlow.avisar(SocialFlow.erro(erro), "erro");
    }
    const form = document.getElementById("filtros");
    if (!form) return;
    const linkConsulta = document.querySelector("[data-nav='consulta']");
    if (linkConsulta) {
      linkConsulta.addEventListener("click", function (evento) {
        evento.preventDefault();
        if (window.location.hash !== "#consulta") history.pushState(null, "", "#consulta");
        entrarConsulta();
      });
    }
    window.addEventListener("hashchange", function () {
      if (window.location.hash === "#consulta") entrarConsulta();
      else sairConsulta();
    });
    const restaurou = consultaInicial ? false : aplicarSalvos();
    const vindo = new URLSearchParams(window.location.search).get("q");
    if (vindo && form.elements.q) form.elements.q.value = vindo;
    sincronizarBusca();
    if (restaurou) {
      const nota = document.getElementById("nota-filtros");
      if (nota) nota.hidden = false;
    }
    const topo = document.getElementById("busca-topo");
    if (topo && topo.form) {
      topo.addEventListener("input", function () {
        form.elements.q.value = topo.value;
      });
      topo.form.addEventListener("submit", function (evento) {
        evento.preventDefault();
        form.elements.q.value = topo.value;
        form.requestSubmit();
      });
    }
    form.elements.q.addEventListener("input", sincronizarBusca);
    form.addEventListener("submit", function (evento) {
      evento.preventDefault();
      carregar();
    });
    document.getElementById("limpar-filtros").addEventListener("click", function () {
      form.reset();
      localStorage.removeItem("socialflow-auto.filtros");
      const nota = document.getElementById("nota-filtros");
      if (nota) nota.hidden = true;
      carregar();
    });
    try {
      const todos = await SocialFlow.api("/api/publico/veiculos");
      const marcas = document.getElementById("marca");
      const nomes = [];
      todos.veiculos.forEach(function (veiculo) {
        if (nomes.indexOf(veiculo.marca) < 0) nomes.push(veiculo.marca);
      });
      nomes.sort(function (a, b) { return a.localeCompare(b, "pt-BR"); });
      nomes.forEach(function (nome) {
        const opcao = document.createElement("option");
        opcao.value = nome;
        opcao.textContent = nome;
        marcas.appendChild(opcao);
      });
      if (SocialFlow.lerFiltros() && SocialFlow.lerFiltros().marca) {
        marcas.value = SocialFlow.lerFiltros().marca;
      }
    } catch (erro) {
      SocialFlow.avisar(SocialFlow.erro(erro), "erro");
    }
    carregar();
  }

  document.addEventListener("DOMContentLoaded", iniciar);
})(window);
