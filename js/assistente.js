(function (raiz) {
  const SocialFlow = raiz.SocialFlow;
  let sessao = sessionStorage.getItem("socialflow-auto.consultor") || "";
  let ultimoVeiculo = "";

  function log(papel, texto) {
    const caixa = document.getElementById("consultor-log");
    const bloco = document.createElement("p");
    bloco.className = "balao balao-" + papel;
    bloco.textContent = texto;
    caixa.appendChild(bloco);
    caixa.scrollTop = caixa.scrollHeight;
  }

  function preferenciasDoFormulario() {
    const form = document.getElementById("form-consultor");
    const dados = {};
    ["cambio", "tipo", "combustivel", "uso"].forEach(function (chave) {
      const valor = form.elements[chave] && form.elements[chave].value;
      if (valor) dados[chave] = valor;
    });
    if (form.elements.preco_max && form.elements.preco_max.value.trim()) {
      dados.preco_max = form.elements.preco_max.value.trim();
    }
    if (document.body.dataset.veiculoFoco) dados.veiculo_id = document.body.dataset.veiculoFoco;
    return dados;
  }

  function mostrarCards(destino, itens, titulo) {
    destino.replaceChildren();
    if (!itens || !itens.length) return;
    const h = document.createElement("h3");
    h.textContent = titulo;
    destino.appendChild(h);
    const grade = document.createElement("div");
    grade.className = "sugestoes";
    itens.forEach(function (item) {
      const card = SocialFlow.cartao(item, { motivos: item.motivos });
      if (item.href) {
        const acoes = document.createElement("p");
        acoes.className = "acoes";
        const visita = document.createElement("a");
        visita.className = "botao";
        visita.href = item.href + "#visita";
        visita.textContent = "Solicitar visita";
        acoes.appendChild(visita);
        card.querySelector(".card-corpo").appendChild(acoes);
      }
      grade.appendChild(card);
    });
    destino.appendChild(grade);
  }

  async function enviar(reiniciar) {
    const form = document.getElementById("form-consultor");
    const mensagem = form.elements.mensagem.value.trim();
    if (!reiniciar && !mensagem && !Object.keys(preferenciasDoFormulario()).length) {
      SocialFlow.avisar("Escreva uma preferência ou escolha um filtro.", "erro");
      return;
    }
    if (mensagem) log("visitante", mensagem);
    const botao = form.querySelector("button[type=submit]");
    botao.disabled = true;
    try {
      const resposta = await SocialFlow.api("/api/publico/consultor", {
        json: {
          mensagem: mensagem,
          preferencias: preferenciasDoFormulario(),
          sessao_id: sessao || null,
          reiniciar: Boolean(reiniciar)
        }
      });
      sessao = resposta.sessao_id;
      sessionStorage.setItem("socialflow-auto.consultor", sessao);
      document.getElementById("modo-consultor").textContent = resposta.modo_rotulo;
      const extra = (resposta.interpretacoes || []).concat(resposta.aviso_escopo ? [] : []).join(" ");
      log("consultor", resposta.texto + (extra ? " " + extra : "") + (resposta.aviso_ia ? " " + resposta.aviso_ia : ""));
      const resultado = document.getElementById("consultor-resultado");
      resultado.replaceChildren();
      mostrarCards(resultado, resposta.sugestoes, "Sugestões do estoque disponível");
      if (resposta.alternativas && resposta.alternativas.length) {
        const alt = document.createElement("div");
        resultado.appendChild(alt);
        mostrarCards(alt, resposta.alternativas, "Fora do uso pedido");
      }
      if (resposta.foco && resposta.foco.motivos) {
        const foco = document.createElement("p");
        foco.className = resposta.foco.disponivel ? "chamada" : "alerta";
        foco.textContent = resposta.foco.motivos.join(" ");
        resultado.prepend(foco);
      }
      ultimoVeiculo = (resposta.sugestoes[0] && resposta.sugestoes[0].id) || document.body.dataset.veiculoFoco || "";
      document.getElementById("form-encaminhar").hidden = false;
      form.elements.mensagem.value = "";
    } catch (erro) {
      SocialFlow.avisar(SocialFlow.erro(erro), "erro");
    } finally {
      botao.disabled = false;
    }
  }

  function iniciar() {
    const form = document.getElementById("form-consultor");
    if (!form) return;
    form.addEventListener("submit", function (evento) {
      evento.preventDefault();
      enviar(false);
    });
    document.getElementById("consultor-limpar").addEventListener("click", async function () {
      form.reset();
      sessionStorage.removeItem("socialflow-auto.consultor");
      if (sessao) {
        try {
          await SocialFlow.api("/api/publico/consultor/" + encodeURIComponent(sessao), { method: "DELETE", json: {} });
        } catch (erro) {
          SocialFlow.avisar(SocialFlow.erro(erro), "erro");
        }
      }
      sessao = "";
      document.getElementById("consultor-log").replaceChildren();
      document.getElementById("consultor-resultado").replaceChildren();
      document.getElementById("form-encaminhar").hidden = true;
    });
    document.getElementById("form-encaminhar").addEventListener("submit", async function (evento) {
      evento.preventDefault();
      const dados = new FormData(evento.target);
      try {
        const resposta = await SocialFlow.api("/api/publico/leads", {
          json: {
            nome: dados.get("nome"),
            telefone: dados.get("telefone"),
            email: dados.get("email"),
            consentimento: dados.get("consentimento") === "on",
            sessao_id: sessao,
            veiculo_id: ultimoVeiculo
          }
        });
        SocialFlow.avisar(resposta.mensagem);
        evento.target.reset();
      } catch (erro) {
        SocialFlow.avisar(SocialFlow.erro(erro), "erro");
      }
    });
    if (SocialFlow.contexto && SocialFlow.contexto.consultor_modo === "deterministico") {
      document.getElementById("modo-consultor").textContent = "Automação determinística — sem modelo generativo";
    }
  }

  document.addEventListener("DOMContentLoaded", iniciar);
  raiz.SocialFlowConsultor = { perguntar: function (texto) {
    const campo = document.getElementById("consultor-mensagem");
    if (!campo) return;
    campo.value = texto;
    document.getElementById("consultor").scrollIntoView();
    enviar(false);
  }};
})(window);
