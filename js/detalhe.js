(function (raiz) {
  const SocialFlow = raiz.SocialFlow;

  function parametro() {
    return new URLSearchParams(window.location.search).get("id") || "";
  }

  function definirTexto(id, texto) {
    const el = document.getElementById(id);
    if (el) el.textContent = texto;
  }

  function preencher(veiculo) {
    document.title = veiculo.marca + " " + veiculo.modelo + " · SocialFlow Auto";
    definirTexto("titulo-veiculo", veiculo.marca + " " + veiculo.modelo + " " + veiculo.versao);
    definirTexto("preco-veiculo", veiculo.preco);
    definirTexto("status-veiculo", veiculo.status_rotulo);
    document.getElementById("status-veiculo").className = "selo selo-" + veiculo.status;
    definirTexto("descricao-veiculo", veiculo.descricao);
    const ficha = document.getElementById("ficha");
    ficha.replaceChildren();
    [
      ["Código", veiculo.codigo],
      ["Ano", veiculo.ano_fabricacao + "/" + veiculo.ano_modelo],
      ["Quilometragem", veiculo.km_rotulo],
      ["Câmbio", veiculo.cambio_rotulo],
      ["Combustível", veiculo.combustivel_rotulo],
      ["Tipo", veiculo.tipo_rotulo],
      ["Cor", veiculo.cor]
    ].forEach(function (par) {
      const dt = document.createElement("dt");
      dt.textContent = par[0];
      const dd = document.createElement("dd");
      dd.textContent = par[1];
      ficha.appendChild(dt);
      ficha.appendChild(dd);
    });
    const galeria = document.getElementById("galeria");
    galeria.replaceChildren();
    const fotos = SocialFlow.fotosDoVeiculo(veiculo);
    fotos.forEach(function (imagem) {
      const img = document.createElement("img");
      img.src = imagem.url;
      img.alt = imagem.rotulo || (veiculo.marca + " " + veiculo.modelo);
      img.width = 640;
      img.height = 400;
      galeria.appendChild(img);
    });
    if (!fotos.length) galeria.appendChild(SocialFlow.foto(veiculo));
    const carros = document.getElementById("form-interesse").elements.veiculo_id;
    if (carros) carros.value = veiculo.id;
    document.getElementById("visita-veiculo").value = veiculo.id;
    document.body.dataset.veiculoFoco = veiculo.id;
    const visita = document.getElementById("abrir-visita");
    if (veiculo.status !== "disponivel") {
      visita.disabled = true;
      definirTexto("aviso-visita", "A visita só é pedida quando o veículo está disponível. O status atual é " + veiculo.status_rotulo + ".");
    }
  }

  async function opcoesInteresse(veiculoId) {
    const form = document.getElementById("form-interesse");
    if (!form) return;
    const carros = form.elements.veiculo_id;
    const consultores = form.elements.consultor_id;
    if (!carros.options.length) {
      const lista = await SocialFlow.api("/api/publico/veiculos");
      (lista.veiculos || []).forEach(function (item) {
        const opcao = document.createElement("option");
        opcao.value = item.id;
        opcao.textContent = item.marca + " " + item.modelo + " " + item.versao;
        carros.appendChild(opcao);
      });
    }
    if (consultores.options.length <= 1) {
      const equipe = await SocialFlow.api("/api/publico/consultores");
      (equipe.consultores || []).forEach(function (pessoa) {
        const opcao = document.createElement("option");
        opcao.value = pessoa.id;
        opcao.textContent = pessoa.nome;
        consultores.appendChild(opcao);
      });
    }
    if (veiculoId) carros.value = veiculoId;
  }

  async function iniciar() {
    document.querySelectorAll("[data-nav]").forEach(function (link) {
      if (link.dataset.nav === "vitrine") link.setAttribute("aria-current", "page");
    });
    const id = parametro();
    try {
      const ctx = await SocialFlow.preparar();
      SocialFlow.preencherLoja(ctx.loja);
    } catch (erro) {
      SocialFlow.avisar(SocialFlow.erro(erro), "erro");
    }
    if (!id) {
      definirTexto("titulo-veiculo", "Veículo não informado");
      return;
    }
    try {
      const dados = await SocialFlow.api("/api/publico/veiculos/" + encodeURIComponent(id));
      preencher(dados.veiculo);
      await opcoesInteresse(dados.veiculo.id);
      if (location.hash === "#visita") document.getElementById("dialogo-visita").showModal();
      if (location.hash === "#interesse") document.getElementById("dialogo-interesse").showModal();
    } catch (erro) {
      definirTexto("titulo-veiculo", "Veículo indisponível");
      definirTexto("descricao-veiculo", SocialFlow.erro(erro));
    }
    document.getElementById("fechar-interesse").addEventListener("click", function () {
      document.getElementById("dialogo-interesse").close();
    });
    document.getElementById("fechar-visita").addEventListener("click", function () {
      document.getElementById("dialogo-visita").close();
    });
    document.getElementById("abrir-interesse").addEventListener("click", function () {
      document.getElementById("dialogo-interesse").showModal();
    });
    document.getElementById("abrir-visita").addEventListener("click", function () {
      document.getElementById("dialogo-visita").showModal();
    });
    document.getElementById("perguntar").addEventListener("click", function () {
      if (raiz.SocialFlowConsultor) {
        raiz.SocialFlowConsultor.perguntar("Quero saber se este veículo combina com o que eu preciso.");
      }
    });
    document.getElementById("form-interesse").addEventListener("submit", async function (evento) {
      evento.preventDefault();
      const dados = new FormData(evento.target);
      try {
        const resposta = await SocialFlow.api("/api/publico/leads", {
          json: {
            nome: dados.get("nome"),
            telefone: dados.get("telefone"),
            email: dados.get("email"),
            consentimento: dados.get("consentimento") === "on",
            veiculo_id: dados.get("veiculo_id"),
            consultor_id: dados.get("consultor_id")
          }
        });
        document.getElementById("dialogo-interesse").close();
        SocialFlow.avisar(resposta.mensagem);
        const carro = dados.get("veiculo_id");
        evento.target.reset();
        evento.target.elements.veiculo_id.value = carro || document.body.dataset.veiculoFoco || "";
      } catch (erro) {
        SocialFlow.avisar(SocialFlow.erro(erro), "erro");
      }
    });
    document.getElementById("form-visita").addEventListener("submit", async function (evento) {
      evento.preventDefault();
      const dados = new FormData(evento.target);
      try {
        const resposta = await SocialFlow.api("/api/publico/agendamentos", {
          json: {
            nome: dados.get("nome"),
            telefone: dados.get("telefone"),
            email: dados.get("email"),
            consentimento: dados.get("consentimento") === "on",
            veiculo_id: dados.get("veiculo_id"),
            tipo: dados.get("tipo"),
            inicio: dados.get("inicio")
          }
        });
        document.getElementById("dialogo-visita").close();
        SocialFlow.avisar(resposta.mensagem);
      } catch (erro) {
        SocialFlow.avisar(SocialFlow.erro(erro), "erro");
      }
    });
  }

  document.addEventListener("DOMContentLoaded", iniciar);
})(window);
