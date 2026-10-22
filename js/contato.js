(function (raiz) {
  const SocialFlow = raiz.SocialFlow;
  let opcoesProntas = false;

  function dialogo() {
    return document.getElementById("dialogo-contato");
  }

  function formulario() {
    return document.getElementById("form-contato");
  }

  function veiculoInicial(botao) {
    if (botao && botao.dataset.veiculo && botao.dataset.veiculo !== "atual") {
      return botao.dataset.veiculo;
    }
    if ((botao && botao.dataset.veiculo === "atual") || document.body.dataset.pagina === "veiculo") {
      return document.body.dataset.veiculoFoco || "";
    }
    return "";
  }

  async function garantirOpcoes() {
    const form = formulario();
    if (!form || opcoesProntas) return;
    const veiculos = await SocialFlow.api("/api/publico/veiculos");
    const equipe = await SocialFlow.api("/api/publico/consultores");
    const carros = form.elements.veiculo_id;
    const consultores = form.elements.consultor_id;
    (veiculos.veiculos || []).forEach(function (veiculo) {
      const opcao = document.createElement("option");
      opcao.value = veiculo.id;
      opcao.textContent = veiculo.marca + " " + veiculo.modelo + " " + veiculo.versao;
      carros.appendChild(opcao);
    });
    (equipe.consultores || []).forEach(function (pessoa) {
      const opcao = document.createElement("option");
      opcao.value = pessoa.id;
      opcao.textContent = pessoa.nome;
      consultores.appendChild(opcao);
    });
    opcoesProntas = true;
  }

  async function abrir(botao) {
    const caixa = dialogo();
    const form = formulario();
    if (!caixa || !form) return;
    try {
      await garantirOpcoes();
    } catch (erro) {
      SocialFlow.avisar(SocialFlow.erro(erro), "erro");
      return;
    }
    const escolhido = veiculoInicial(botao);
    form.elements.veiculo_id.value = escolhido;
    if (form.elements.veiculo_id.value !== escolhido) form.elements.veiculo_id.value = "";
    if (!caixa.open) caixa.showModal();
    const foco = form.querySelector("input, select, textarea");
    if (foco) foco.focus();
  }

  function iniciar() {
    const caixa = dialogo();
    const form = formulario();
    if (!caixa || !form) return;
    document.querySelectorAll("[data-abre-contato]").forEach(function (botao) {
      botao.addEventListener("click", function () { abrir(botao); });
    });
    document.querySelectorAll("[data-fecha-contato]").forEach(function (botao) {
      botao.addEventListener("click", function () { caixa.close(); });
    });
    form.addEventListener("submit", async function (evento) {
      evento.preventDefault();
      const dados = new FormData(form);
      const botao = form.querySelector("button[type=submit]");
      botao.disabled = true;
      try {
        const resposta = await SocialFlow.api("/api/publico/contatos", {
          json: {
            nome: dados.get("nome"),
            email: dados.get("email"),
            mensagem: dados.get("mensagem"),
            veiculo_id: dados.get("veiculo_id") || "",
            consultor_id: dados.get("consultor_id"),
            consentimento: dados.get("consentimento") === "on"
          }
        });
        caixa.close();
        form.reset();
        SocialFlow.avisar(resposta.mensagem);
      } catch (erro) {
        SocialFlow.avisar(SocialFlow.erro(erro), "erro");
      } finally {
        botao.disabled = false;
      }
    });
  }

  document.addEventListener("DOMContentLoaded", iniciar);
})(window);
