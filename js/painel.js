(function (raiz) {
  const SocialFlow = raiz.SocialFlow;
  let equipe = [];
  let papel = "";
  let secaoAtual = "indicadores";
  let filtroLeads = { status: "", veiculo_id: "" };
  let filtroVeiculos = { status: "" };

  function aplicarFiltrosNaTela() {
    const leadStatus = document.getElementById("filtro-lead-status");
    if (leadStatus) leadStatus.value = filtroLeads.status;
    const veiculoStatus = document.getElementById("filtro-veiculo-status");
    if (veiculoStatus) veiculoStatus.value = filtroVeiculos.status;
  }

  function abrirSecao(id, filtro) {
    const extras = filtro || {};
    if (id === "leads") {
      if (extras.limpar) filtroLeads = { status: "", veiculo_id: "" };
      else {
        if (extras.status !== undefined) filtroLeads.status = extras.status || "";
        if (extras.veiculo_id !== undefined) filtroLeads.veiculo_id = extras.veiculo_id || "";
        else if (extras.status !== undefined) filtroLeads.veiculo_id = "";
      }
    }
    if (id === "veiculos") {
      if (extras.limpar) filtroVeiculos = { status: "" };
      else if (extras.status !== undefined) filtroVeiculos.status = extras.status || "";
    }
    aplicarFiltrosNaTela();
    mostrar(id);
  }

  function mostrar(id) {
    secaoAtual = id;
    document.querySelectorAll("[data-secao-painel]").forEach(function (secao) {
      secao.hidden = secao.id !== "secao-" + id;
    });
    document.querySelectorAll("[data-abre]").forEach(function (botao) {
      if (botao.dataset.abre === id) botao.setAttribute("aria-current", "page");
      else botao.removeAttribute("aria-current");
    });
    if (id === "indicadores") carregarResumo();
    if (id === "veiculos") carregarVeiculos();
    if (id === "leads") carregarLeads();
    if (id === "agenda") carregarAgenda();
    if (id === "config") carregarConfig();
  }

  function iniciais(nome) {
    return String(nome || "")
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map(function (parte) { return parte.charAt(0); })
      .join("")
      .toUpperCase();
  }

  function entrarPainel(usuario) {
    document.getElementById("tela-entrada").hidden = true;
    document.getElementById("aplicacao").hidden = false;
    papel = usuario.papel;
    document.getElementById("quem-nome").textContent = usuario.nome;
    document.getElementById("quem-papel").textContent = usuario.papel_rotulo;
    document.getElementById("quem-iniciais").textContent = iniciais(usuario.nome);
    const config = document.getElementById("abre-config");
    const restaurar = document.getElementById("restaurar");
    const admin = usuario.papel === "admin";
    config.hidden = !admin;
    restaurar.hidden = !admin;
    mostrar("indicadores");
  }

  function textoVariacao(item) {
    if (!item) return { classe: "estavel", texto: "Mesmo período anterior", extra: "0%" };
    const sinal = item.delta > 0 ? "+" : "";
    const classe = item.delta > 0 ? "alta" : (item.delta < 0 ? "baixa" : "estavel");
    const extra = (item.delta > 0 ? "+" : "") + item.percentual + "%";
    if (item.delta === 0) return { classe: "estavel", texto: "Mesmo período anterior", extra: "0%" };
    return { classe: classe, texto: sinal + item.delta + " em relação ao período anterior", extra: extra };
  }

  function iconeKpi(tipo) {
    const mapa = {
      carro: '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M4 14.5h16l-1.1-4A2 2 0 0 0 17 9H7a2 2 0 0 0-1.9 1.5l-1.1 4z" fill="none" stroke="currentColor" stroke-width="1.6"/><circle cx="7.5" cy="16.8" r="1.3" fill="currentColor"/><circle cx="16.5" cy="16.8" r="1.3" fill="currentColor"/></svg>',
      reserva: '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M7 4.8h10v14.4l-5-2.4-5 2.4z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/></svg>',
      venda: '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M4 16.5 9.2 9l3.6 4.2L20 6.5" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>',
      lead: '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><circle cx="12" cy="8" r="2.6" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M6.2 18c.6-2.8 2.6-4.2 5.8-4.2s5.2 1.4 5.8 4.2" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>'
    };
    return mapa[tipo] || mapa.lead;
  }

  function montarKpi(titulo, valor, icone, comparativo, destino) {
    const card = document.createElement("button");
    card.type = "button";
    card.className = "kpi";
    card.setAttribute("aria-label", "Abrir " + titulo);
    const variacao = textoVariacao(comparativo);
    card.innerHTML =
      "<div class='kpi-topo'><span class='kpi-icone'>" + iconeKpi(icone) + "</span><span>" + SocialFlow.esc(titulo) + "</span></div>" +
      "<p class='kpi-valor'>" + SocialFlow.esc(String(valor)) + "</p>" +
      "<p class='kpi-nota " + variacao.classe + "'><small>" + SocialFlow.esc(variacao.texto) + "</small><strong>" + SocialFlow.esc(variacao.extra) + "</strong></p>";
    card.addEventListener("click", function () {
      abrirSecao(destino.secao, destino.filtro);
    });
    return card;
  }

  function graficoLinha(pontos) {
    const w = 640;
    const h = 196;
    const padL = 28;
    const padR = 18;
    const padT = 18;
    const padB = 32;
    const max = Math.max(6, ...pontos.map(function (p) { return p.total; }));
    const passo = pontos.length > 1 ? (w - padL - padR) / (pontos.length - 1) : 0;
    const xs = pontos.map(function (_, i) { return padL + i * passo; });
    const ys = pontos.map(function (p) { return padT + (1 - p.total / max) * (h - padT - padB); });
    const linha = pontos.map(function (p, i) {
      return (i ? "L" : "M") + xs[i].toFixed(1) + " " + ys[i].toFixed(1);
    }).join(" ");
    const grades = [0, 2, 4, 6].map(function (n) {
      const y = padT + (1 - n / max) * (h - padT - padB);
      return "<line x1='" + padL + "' y1='" + y + "' x2='" + (w - padR) + "' y2='" + y + "'></line>" +
        "<text x='0' y='" + (y + 4) + "'>" + n + "</text>";
    }).join("");
    const marcas = [0, Math.floor((pontos.length - 1) / 5), Math.floor((pontos.length - 1) * 2 / 5), Math.floor((pontos.length - 1) * 3 / 5), Math.floor((pontos.length - 1) * 4 / 5), pontos.length - 1]
      .filter(function (v, i, arr) { return pontos[v] && arr.indexOf(v) === i; })
      .map(function (i) {
        return "<text x='" + xs[i] + "' y='" + (h - 8) + "' text-anchor='middle'>" + SocialFlow.esc(pontos[i].rotulo) + "</text>";
      }).join("");
    let destaque = pontos.length - 1;
    for (let i = pontos.length - 1; i >= 0; i -= 1) {
      if (pontos[i].total) {
        destaque = i;
        break;
      }
    }
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 " + w + " " + h);
    svg.setAttribute("class", "grafico-linha");
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", "Leads recebidos no período");
    svg.innerHTML = "<g class='grades'>" + grades + "</g><path d='" + linha + "' fill='none'></path>" +
      (destaque >= 0 && pontos[destaque] ? "<circle cx='" + xs[destaque] + "' cy='" + ys[destaque] + "' r='4'></circle>" : "") +
      marcas;
    const caixa = document.createElement("div");
    caixa.className = "grafico-linha-caixa";
    caixa.appendChild(svg);
    if (destaque >= 0 && pontos[destaque]) {
      const marca = document.createElement("span");
      marca.className = "grafico-marca";
      marca.textContent = pontos[destaque].total + " leads";
      caixa.appendChild(marca);
    }
    return caixa;
  }

  function graficoRosca(fatias, total) {
    const r = 52;
    const circ = 2 * Math.PI * r;
    let offset = 0;
    const aneis = fatias.map(function (fatia) {
      const len = total ? (fatia.valor / total) * circ : 0;
      const trecho = "<circle cx='70' cy='70' r='" + r + "' stroke='" + fatia.cor + "' stroke-dasharray='" + len + " " + (circ - len) + "' stroke-dashoffset='" + (-offset) + "'></circle>";
      offset += len;
      return trecho;
    }).join("");
    const svg = "<svg viewBox='0 0 140 140' class='grafico-rosca' role='img' aria-label='Status dos veículos'>" +
      "<circle class='fundo' cx='70' cy='70' r='" + r + "'></circle>" + aneis +
      "<text x='70' y='68' text-anchor='middle' class='rosca-total'>" + total + "</text>" +
      "<text x='70' y='86' text-anchor='middle' class='rosca-legenda'>Total</text></svg>";
    const lista = document.createElement("ul");
    lista.className = "rosca-lista";
    fatias.forEach(function (fatia) {
      const li = document.createElement("li");
      const pct = total ? Math.round((fatia.valor / total) * 100) : 0;
      li.innerHTML = "<i style='background:" + fatia.cor + "'></i><span>" + SocialFlow.esc(fatia.rotulo) + "</span><strong>" + fatia.valor + "</strong><em>" + pct + "%</em>";
      li.tabIndex = 0;
      li.setAttribute("role", "button");
      li.addEventListener("click", function () {
        abrirSecao("veiculos", { status: fatia.status });
      });
      lista.appendChild(li);
    });
    const caixa = document.createElement("div");
    caixa.className = "grafico-rosca-caixa";
    caixa.innerHTML = svg;
    caixa.appendChild(lista);
    return caixa;
  }

  function rotuloLeadPainel(status, original) {
    return {
      novo: "Novo",
      negociacao: "Em atendimento",
      contatado: "Contato realizado",
      ganho: "Ganho",
      perdido: "Perdido"
    }[status] || original || status;
  }

  function quandoRelativo(texto) {
    const data = new Date(texto);
    if (Number.isNaN(data.getTime())) return texto || "—";
    const agora = new Date();
    const a = new Date(agora.getFullYear(), agora.getMonth(), agora.getDate());
    const b = new Date(data.getFullYear(), data.getMonth(), data.getDate());
    const diff = Math.round((a - b) / 86400000);
    const hora = data.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
    if (diff === 0) return "Hoje, " + hora;
    if (diff === 1) return "Ontem, " + hora;
    return data.toLocaleDateString("pt-BR", { day: "2-digit", month: "short" }) + ", " + hora;
  }

  async function carregarResumo() {
    const destino = document.getElementById("indicadores");
    destino.replaceChildren();
    destino.setAttribute("aria-busy", "true");
    const dias = document.getElementById("periodo-indicadores").value || "30";
    try {
      const dados = await SocialFlow.api("/api/admin/resumo?dias=" + encodeURIComponent(dias));
      equipe = dados.equipe;
      const comparativo = dados.comparativo || {};
      const kpis = document.createElement("div");
      kpis.className = "painel-grade-kpi";
      kpis.appendChild(montarKpi("Veículos disponíveis", dados.veiculos.disponivel, "carro", comparativo.disponivel, { secao: "veiculos", filtro: { status: "disponivel" } }));
      kpis.appendChild(montarKpi("Veículos reservados", dados.veiculos.reservado, "reserva", comparativo.reservado, { secao: "veiculos", filtro: { status: "reservado" } }));
      kpis.appendChild(montarKpi("Veículos vendidos", dados.veiculos.vendido, "venda", comparativo.vendido, { secao: "veiculos", filtro: { status: "vendido" } }));
      kpis.appendChild(montarKpi("Leads novos", dados.leads.novo, "lead", comparativo.leads_novos, { secao: "leads", filtro: { status: "novo" } }));
      destino.appendChild(kpis);

      const meio = document.createElement("div");
      meio.className = "painel-grade-meio";
      const cardLinha = document.createElement("article");
      cardLinha.className = "painel-card painel-card-clicavel";
      cardLinha.tabIndex = 0;
      cardLinha.setAttribute("role", "button");
      cardLinha.setAttribute("aria-label", "Abrir todos os leads");
      cardLinha.innerHTML = "<header class='painel-card-topo'><div><h2>Leads recebidos</h2><p>Quantidade de novos leads nos últimos " + dias + " dias</p></div><span class='painel-chip'>Últimos " + dias + " dias</span></header>";
      cardLinha.appendChild(graficoLinha(dados.serie_leads || []));
      cardLinha.addEventListener("click", function () {
        abrirSecao("leads", { limpar: true });
      });
      const cardRosca = document.createElement("article");
      cardRosca.className = "painel-card";
      cardRosca.innerHTML = "<header class='painel-card-topo'><div><h2>Status dos veículos</h2><p>Distribuição atual do estoque</p></div></header>";
      const totalEstoque = (dados.veiculos.disponivel || 0) + (dados.veiculos.reservado || 0) + (dados.veiculos.vendido || 0) + (dados.veiculos.indisponivel || 0);
      cardRosca.appendChild(graficoRosca([
        { rotulo: "Disponíveis", valor: dados.veiculos.disponivel || 0, cor: "#d09850", status: "disponivel" },
        { rotulo: "Reservados", valor: dados.veiculos.reservado || 0, cor: "#4c8dff", status: "reservado" },
        { rotulo: "Vendidos", valor: dados.veiculos.vendido || 0, cor: "#3ddc84", status: "vendido" },
        { rotulo: "Em análise", valor: dados.veiculos.indisponivel || 0, cor: "#6b7280", status: "indisponivel" }
      ], totalEstoque));
      meio.appendChild(cardLinha);
      meio.appendChild(cardRosca);
      destino.appendChild(meio);

      const baixo = document.createElement("div");
      baixo.className = "painel-grade-baixo";
      const procurados = document.createElement("article");
      procurados.className = "painel-card";
      procurados.innerHTML = "<header class='painel-card-topo'><div><h2>Veículos mais procurados</h2><p>Modelos com maior interesse dos leads</p></div></header>";
      if (!dados.mais_procurados.length) {
        const vazio = document.createElement("p");
        vazio.className = "vazio";
        vazio.textContent = "Ainda não há interesse registrado.";
        procurados.appendChild(vazio);
      } else {
        const lista = document.createElement("ol");
        lista.className = "lista-procurados";
        dados.mais_procurados.forEach(function (item, indice) {
          const li = document.createElement("li");
          li.innerHTML =
            "<span class='ordem'>" + (indice + 1) + "</span>" +
            "<img src='" + SocialFlow.esc(item.foto || "/assets/marca.jpg") + "' alt=''>" +
            "<span class='nome'><strong>" + SocialFlow.esc(item.nome || item.titulo) + "</strong><small>(" + SocialFlow.esc(String(item.ano_fabricacao || "—")) + " / " + SocialFlow.esc(String(item.ano_modelo || "—")) + ")</small></span>" +
            "<span class='interesse'>" + item.total + " interesses</span>" +
            "<button type='button' class='link-suave' data-ir-leads data-veiculo='" + SocialFlow.esc(item.id) + "'>Ver leads</button>";
          lista.appendChild(li);
        });
        procurados.appendChild(lista);
      }
      const recentes = document.createElement("article");
      recentes.className = "painel-card";
      recentes.innerHTML = "<header class='painel-card-topo'><div><h2>Leads recentes</h2><p>Últimos leads recebidos no sistema</p></div><button type='button' class='link-suave' data-ir-leads>Ver todos</button></header>";
      if (!(dados.leads_recentes || []).length) {
        const vazio = document.createElement("p");
        vazio.className = "vazio";
        vazio.textContent = "Nenhum lead recente.";
        recentes.appendChild(vazio);
      } else {
        const lista = document.createElement("ul");
        lista.className = "lista-recentes";
        dados.leads_recentes.forEach(function (lead) {
          const li = document.createElement("li");
          li.tabIndex = 0;
          li.setAttribute("role", "button");
          li.dataset.status = lead.status;
          li.innerHTML =
            "<span class='barra-iniciais'>" + SocialFlow.esc(iniciais(lead.nome)) + "</span>" +
            "<span class='nome'><strong>" + SocialFlow.esc(lead.nome) + "</strong></span>" +
            "<span class='carro'>" + SocialFlow.esc(lead.veiculo || "Sem veículo") + "</span>" +
            "<span class='quando'>" + SocialFlow.esc(quandoRelativo(lead.criado_em)) + "</span>" +
            "<span class='selo selo-" + SocialFlow.esc(lead.status) + "'>" + SocialFlow.esc(rotuloLeadPainel(lead.status, lead.status_rotulo)) + "</span>";
          li.addEventListener("click", function () {
            abrirSecao("leads", { status: lead.status || "novo" });
          });
          lista.appendChild(li);
        });
        recentes.appendChild(lista);
      }
      baixo.appendChild(procurados);
      baixo.appendChild(recentes);
      destino.appendChild(baixo);
      destino.querySelectorAll("[data-ir-leads]").forEach(function (botao) {
        botao.addEventListener("click", function (evento) {
          evento.stopPropagation();
          abrirSecao("leads", { status: "", veiculo_id: botao.getAttribute("data-veiculo") || "" });
        });
      });
    } catch (erro) {
      if (erro.status === 401) voltarLogin();
      else SocialFlow.avisar(SocialFlow.erro(erro), "erro");
    } finally {
      destino.setAttribute("aria-busy", "false");
    }
  }

  function linhaVeiculo(veiculo) {
    const tr = document.createElement("tr");
    [veiculo.codigo, veiculo.marca + " " + veiculo.modelo, veiculo.preco, veiculo.status_rotulo].forEach(function (texto) {
      const td = document.createElement("td");
      td.textContent = texto;
      tr.appendChild(td);
    });
    const acoes = document.createElement("td");
    const editar = document.createElement("button");
    editar.type = "button";
    editar.className = "secundario";
    editar.textContent = "Editar";
    editar.addEventListener("click", function () { preencherVeiculo(veiculo); });
    const vender = document.createElement("button");
    vender.type = "button";
    vender.className = "secundario";
    vender.textContent = "Marcar vendido";
    vender.addEventListener("click", function () { mudarStatus(veiculo, "vendido"); });
    acoes.appendChild(editar);
    acoes.appendChild(document.createTextNode(" "));
    acoes.appendChild(vender);
    tr.appendChild(acoes);
    return tr;
  }

  function preencherVeiculo(veiculo) {
    const form = document.getElementById("form-veiculo");
    form.elements.id.value = veiculo.id;
    form.elements.codigo.value = veiculo.codigo;
    form.elements.marca.value = veiculo.marca;
    form.elements.modelo.value = veiculo.modelo;
    form.elements.versao.value = veiculo.versao;
    form.elements.ano_fabricacao.value = veiculo.ano_fabricacao;
    form.elements.ano_modelo.value = veiculo.ano_modelo;
    form.elements.km.value = veiculo.km;
    form.elements.cambio.value = veiculo.cambio;
    form.elements.combustivel.value = veiculo.combustivel;
    form.elements.tipo.value = veiculo.tipo;
    form.elements.preco_reais.value = veiculo.preco.replace("R$", "").trim();
    form.elements.status.value = veiculo.status;
    form.elements.cor.value = veiculo.cor;
    form.elements.descricao.value = veiculo.descricao;
    form.scrollIntoView();
  }

  function payloadVeiculo(form) {
    const dados = new FormData(form);
    return {
      id: dados.get("id"),
      codigo: dados.get("codigo"),
      marca: dados.get("marca"),
      modelo: dados.get("modelo"),
      versao: dados.get("versao"),
      ano_fabricacao: Number(dados.get("ano_fabricacao")),
      ano_modelo: Number(dados.get("ano_modelo")),
      km: Number(dados.get("km")),
      cambio: dados.get("cambio"),
      combustivel: dados.get("combustivel"),
      tipo: dados.get("tipo"),
      preco_reais: dados.get("preco_reais"),
      status: dados.get("status"),
      cor: dados.get("cor"),
      descricao: dados.get("descricao")
    };
  }

  async function mudarStatus(veiculo, status) {
    const corpo = {
      codigo: veiculo.codigo,
      marca: veiculo.marca,
      modelo: veiculo.modelo,
      versao: veiculo.versao,
      ano_fabricacao: veiculo.ano_fabricacao,
      ano_modelo: veiculo.ano_modelo,
      km: veiculo.km,
      cambio: veiculo.cambio,
      combustivel: veiculo.combustivel,
      tipo: veiculo.tipo,
      preco_reais: veiculo.preco.replace("R$", "").trim(),
      status: status,
      cor: veiculo.cor,
      descricao: veiculo.descricao
    };
    await SocialFlow.api("/api/admin/veiculos/" + veiculo.id, { method: "PUT", json: corpo });
    SocialFlow.avisar("Status atualizado para " + status + ".");
    carregarVeiculos();
  }

  async function carregarVeiculos() {
    aplicarFiltrosNaTela();
    const corpo = document.querySelector("#tabela-veiculos tbody");
    corpo.replaceChildren();
    const dados = await SocialFlow.api("/api/admin/veiculos");
    const lista = filtroVeiculos.status
      ? dados.veiculos.filter(function (veiculo) { return veiculo.status === filtroVeiculos.status; })
      : dados.veiculos;
    const rotulos = { disponivel: "disponíveis", reservado: "reservados", vendido: "vendidos", indisponivel: "em análise" };
    const texto = document.getElementById("texto-veiculos");
    if (texto) {
      texto.textContent = filtroVeiculos.status
        ? "Mostrando " + lista.length + " veículo(s) " + (rotulos[filtroVeiculos.status] || filtroVeiculos.status) + "."
        : "Estoque desta loja, inclusive vendidos.";
    }
    if (!lista.length) {
      const tr = document.createElement("tr");
      const td = document.createElement("td");
      td.colSpan = 5;
      td.textContent = filtroVeiculos.status ? "Nenhum veículo neste status." : "Nenhum veículo cadastrado.";
      tr.appendChild(td);
      corpo.appendChild(tr);
      return;
    }
    lista.forEach(function (veiculo) { corpo.appendChild(linhaVeiculo(veiculo)); });
  }

  function opcoesEquipe(selecionado) {
    const select = document.createElement("select");
    const vazio = document.createElement("option");
    vazio.value = "";
    vazio.textContent = "Sem responsável";
    select.appendChild(vazio);
    equipe.forEach(function (pessoa) {
      const opcao = document.createElement("option");
      opcao.value = pessoa.id;
      opcao.textContent = pessoa.nome;
      select.appendChild(opcao);
    });
    select.value = selecionado || "";
    return select;
  }

  async function persistirLead(lead, status, responsavelId) {
    await SocialFlow.api("/api/admin/leads/" + lead.id, {
      method: "PATCH",
      json: {
        status: status,
        responsavel_id: responsavelId || "",
        notas: lead.notas || ""
      }
    });
    lead.status = status;
    lead.responsavel_id = responsavelId || "";
    SocialFlow.avisar("Lead atualizado. O dashboard usa o mesmo status.");
    await carregarLeads();
  }

  async function carregarLeads() {
    aplicarFiltrosNaTela();
    if (!equipe.length) {
      const resumo = await SocialFlow.api("/api/admin/resumo");
      equipe = resumo.equipe;
    }
    const corpo = document.querySelector("#tabela-leads tbody");
    corpo.replaceChildren();
    const dados = await SocialFlow.api("/api/admin/leads");
    let lista = dados.leads;
    if (filtroLeads.status) {
      lista = lista.filter(function (lead) { return lead.status === filtroLeads.status; });
    }
    if (filtroLeads.veiculo_id) {
      lista = lista.filter(function (lead) { return lead.veiculo_id === filtroLeads.veiculo_id; });
    }
    const rotulos = { novo: "novos", contatado: "contatados", negociacao: "em atendimento", ganho: "ganhos", perdido: "perdidos" };
    const texto = document.getElementById("texto-leads");
    if (texto) {
      if (filtroLeads.status) texto.textContent = "Mostrando " + lista.length + " lead(s) " + (rotulos[filtroLeads.status] || filtroLeads.status) + ". Ao mudar o status, o indicador do dashboard acompanha.";
      else texto.textContent = "O contato traz nome, telefone, e-mail, mensagem, carro e o consultor escolhido. Vendas vê os direcionados a si. A administração vê todos.";
    }
    if (!lista.length) {
      const tr = document.createElement("tr");
      const td = document.createElement("td");
      td.colSpan = 9;
      td.textContent = filtroLeads.status === "novo" ? "Nenhum lead novo no momento." : (filtroLeads.status ? "Nenhum lead neste status." : "Nenhum lead.");
      tr.appendChild(td);
      corpo.appendChild(tr);
      return;
    }
    lista.forEach(function (lead) {
      const tr = document.createElement("tr");
      [lead.nome, lead.email || "—", lead.resumo, lead.veiculo || "—", lead.origem_rotulo].forEach(function (textoCelula) {
        const td = document.createElement("td");
        td.textContent = textoCelula;
        tr.appendChild(td);
      });
      const tdFone = document.createElement("td");
      const fone = String(lead.telefone || "").trim();
      if (fone) {
        const liga = document.createElement("a");
        liga.href = "tel:" + fone.replace(/[^\d+]/g, "");
        liga.textContent = fone;
        tdFone.appendChild(liga);
      } else {
        tdFone.textContent = "—";
      }
      tr.insertBefore(tdFone, tr.children[1]);
      const tdConsultor = document.createElement("td");
      let responsavel = null;
      if (papel === "admin") {
        responsavel = opcoesEquipe(lead.responsavel_id);
        tdConsultor.appendChild(responsavel);
      } else {
        tdConsultor.textContent = lead.responsavel_nome || "—";
      }
      const tdStatus = document.createElement("td");
      const status = document.createElement("select");
      status.setAttribute("aria-label", "Status de " + lead.nome);
      ["novo", "contatado", "negociacao", "ganho", "perdido"].forEach(function (valor) {
        const opcao = document.createElement("option");
        opcao.value = valor;
        opcao.textContent = {"novo": "Novo", "contatado": "Contatado", "negociacao": "Negociação", "ganho": "Ganho", "perdido": "Perdido"}[valor];
        status.appendChild(opcao);
      });
      status.value = lead.status;
      tdStatus.appendChild(status);
      tr.insertBefore(tdConsultor, tr.children[5]);
      tr.appendChild(tdStatus);
      async function gravar() {
        try {
          await persistirLead(lead, status.value, responsavel ? responsavel.value : (lead.responsavel_id || ""));
        } catch (erro) {
          SocialFlow.avisar(SocialFlow.erro(erro), "erro");
        }
      }
      status.addEventListener("change", gravar);
      if (responsavel) responsavel.addEventListener("change", gravar);
      const tdAcao = document.createElement("td");
      const salvar = document.createElement("button");
      salvar.type = "button";
      salvar.className = "secundario";
      salvar.textContent = "Salvar";
      salvar.addEventListener("click", gravar);
      tdAcao.appendChild(salvar);
      tr.appendChild(tdAcao);
      corpo.appendChild(tr);
    });
  }

  async function carregarAgenda() {
    const lista = document.getElementById("lista-agenda");
    lista.replaceChildren();
    const dados = await SocialFlow.api("/api/admin/agendamentos");
    if (!dados.agendamentos.length) {
      lista.textContent = "Nenhum agendamento.";
      return;
    }
    dados.agendamentos.forEach(function (item) {
      const artigo = document.createElement("article");
      artigo.className = "card";
      const h = document.createElement("h3");
      h.textContent = item.veiculo + " · " + item.tipo_rotulo;
      const p = document.createElement("p");
      p.textContent = item.inicio.replace("T", " ") + " · " + item.status_rotulo + " · " + item.nome;
      artigo.appendChild(h);
      artigo.appendChild(p);
      if (item.outros_pedidos) {
        const alerta = document.createElement("p");
        alerta.className = "alerta";
        alerta.textContent = "Há " + item.outros_pedidos + " outro(s) pedido(s) solicitado(s) neste horário. Confirmar não é automático.";
        artigo.appendChild(alerta);
      }
      const acoes = document.createElement("div");
      acoes.className = "acoes";
      const hora = document.createElement("input");
      hora.type = "datetime-local";
      hora.value = item.inicio.slice(0, 16);
      hora.setAttribute("aria-label", "Novo horário para " + item.veiculo);
      function botao(rotulo, classe, acao) {
        const el = document.createElement("button");
        el.type = "button";
        el.className = classe;
        el.textContent = rotulo;
        el.addEventListener("click", async function () {
          try {
            const corpo = acao === "reagendar" ? { inicio: hora.value } : {};
            const resposta = await SocialFlow.api("/api/admin/agendamentos/" + item.id + "/" + acao, { json: corpo });
            SocialFlow.avisar(resposta.mensagem || "Agenda atualizada.");
            carregarAgenda();
          } catch (erro) {
            SocialFlow.avisar(SocialFlow.erro(erro), "erro");
          }
        });
        return el;
      }
      if (item.status === "solicitado") acoes.appendChild(botao("Confirmar", "principal", "confirmar"));
      if (item.status === "solicitado" || item.status === "confirmado" || item.status === "reagendado") {
        acoes.appendChild(hora);
        acoes.appendChild(botao("Reagendar", "secundario", "reagendar"));
        acoes.appendChild(botao("Cancelar", "perigo", "cancelar"));
      }
      if (item.status === "confirmado" || item.status === "reagendado") {
        acoes.appendChild(botao("Marcar realizado", "secundario", "realizar"));
      }
      artigo.appendChild(acoes);
      lista.appendChild(artigo);
    });
  }

  async function carregarConfig() {
    const dados = await SocialFlow.api("/api/admin/configuracoes");
    const loja = dados.loja;
    const form = document.getElementById("form-config");
    form.elements.nome.value = loja.nome;
    form.elements.descricao.value = loja.descricao;
    form.elements.telefone.value = loja.telefone;
    form.elements.email.value = loja.email;
    form.elements.endereco.value = loja.endereco;
    form.elements.cor.value = loja.cor;
    form.elements.privacidade.value = loja.privacidade;
    form.elements.max_sugestoes.value = loja.consultor.max_sugestoes;
    ["seg", "ter", "qua", "qui", "sex", "sab", "dom"].forEach(function (dia) {
      const faixa = loja.expediente[dia];
      form.elements[dia + "_abre"].value = faixa ? faixa[0] : "";
      form.elements[dia + "_fecha"].value = faixa ? faixa[1] : "";
    });
    const servicos = document.getElementById("servicos-config");
    servicos.replaceChildren();
    loja.servicos.forEach(function (servico, indice) {
      const bloco = document.createElement("div");
      bloco.className = "grade-campos";
      bloco.innerHTML = "<label class='campo'>Título do serviço " + (indice + 1) +
        "<input name='servico_titulo' value='" + SocialFlow.esc(servico.titulo) + "' required></label>" +
        "<label class='campo'>Texto<textarea name='servico_texto' required>" + SocialFlow.esc(servico.texto) + "</textarea></label>";
      servicos.appendChild(bloco);
    });
  }

  function voltarLogin() {
    document.getElementById("aplicacao").hidden = true;
    document.getElementById("tela-entrada").hidden = false;
  }

  async function iniciar() {
    document.getElementById("form-entrada").addEventListener("submit", async function (evento) {
      evento.preventDefault();
      const dados = new FormData(evento.target);
      try {
        const resposta = await SocialFlow.api("/api/entrar", {
          json: { email: dados.get("email"), senha: dados.get("senha") }
        });
        entrarPainel(resposta.usuario);
      } catch (erro) {
        SocialFlow.avisar(SocialFlow.erro(erro), "erro");
      }
    });
    document.querySelectorAll("[data-abre]").forEach(function (botao) {
      botao.addEventListener("click", function () {
        const id = botao.dataset.abre;
        if (id === "leads" || id === "veiculos") abrirSecao(id, { limpar: true });
        else mostrar(id);
      });
    });
    document.getElementById("filtro-lead-status").addEventListener("change", function (evento) {
      filtroLeads.status = evento.target.value;
      carregarLeads();
    });
    document.getElementById("filtro-veiculo-status").addEventListener("change", function (evento) {
      filtroVeiculos.status = evento.target.value;
      carregarVeiculos();
    });
    document.getElementById("periodo-indicadores").addEventListener("change", function () {
      if (secaoAtual === "indicadores") carregarResumo();
    });
    document.getElementById("ir-cadastrar-veiculo").addEventListener("click", function () {
      abrirSecao("veiculos", { limpar: true });
      const form = document.getElementById("form-veiculo");
      form.reset();
      form.elements.id.value = "";
      form.elements.codigo.focus();
      form.scrollIntoView({ behavior: "smooth", block: "start" });
    });
    document.getElementById("sair").addEventListener("click", async function () {
      await SocialFlow.api("/api/sair", { json: {} });
      voltarLogin();
    });
    document.getElementById("form-veiculo").addEventListener("submit", async function (evento) {
      evento.preventDefault();
      const corpo = payloadVeiculo(evento.target);
      const arquivo = evento.target.elements.imagem.files[0];
      try {
        if (arquivo) {
          corpo.imagem_base64 = await lerArquivo(arquivo);
        }
        if (corpo.id) {
          await SocialFlow.api("/api/admin/veiculos/" + corpo.id, { method: "PUT", json: corpo });
        } else {
          delete corpo.id;
          await SocialFlow.api("/api/admin/veiculos", { json: corpo });
        }
        evento.target.reset();
        SocialFlow.avisar("Veículo gravado. A vitrine usa o status disponível ou reservado.");
        carregarVeiculos();
      } catch (erro) {
        SocialFlow.avisar(SocialFlow.erro(erro), "erro");
      }
    });
    document.getElementById("novo-veiculo").addEventListener("click", function () {
      document.getElementById("form-veiculo").reset();
      document.getElementById("form-veiculo").elements.id.value = "";
    });
    document.getElementById("form-config").addEventListener("submit", async function (evento) {
      evento.preventDefault();
      const form = evento.target;
      const expediente = {};
      ["seg", "ter", "qua", "qui", "sex", "sab", "dom"].forEach(function (dia) {
        const abre = form.elements[dia + "_abre"].value;
        const fecha = form.elements[dia + "_fecha"].value;
        expediente[dia] = abre && fecha ? [abre, fecha] : null;
      });
      const titulos = form.querySelectorAll("[name=servico_titulo]");
      const textos = form.querySelectorAll("[name=servico_texto]");
      const servicos = [];
      titulos.forEach(function (campo, indice) {
        servicos.push({ titulo: campo.value, texto: textos[indice].value });
      });
      try {
        await SocialFlow.api("/api/admin/configuracoes", {
          method: "PUT",
          json: {
            nome: form.elements.nome.value,
            descricao: form.elements.descricao.value,
            telefone: form.elements.telefone.value,
            email: form.elements.email.value,
            endereco: form.elements.endereco.value,
            cor: form.elements.cor.value,
            privacidade: form.elements.privacidade.value,
            expediente: expediente,
            servicos: servicos,
            consultor: { max_sugestoes: Number(form.elements.max_sugestoes.value) }
          }
        });
        SocialFlow.avisar("Configuração gravada.");
      } catch (erro) {
        SocialFlow.avisar(SocialFlow.erro(erro), "erro");
      }
    });
    document.getElementById("restaurar").addEventListener("click", async function () {
      const ok = await SocialFlow.confirmar(
        "Restaurar demonstração",
        "Os veículos, leads e visitas desta loja voltam ao conjunto fictício inicial. Usuários locais são mantidos."
      );
      if (!ok) return;
      try {
        const resposta = await SocialFlow.api("/api/admin/restaurar-demonstracao", { json: {} });
        SocialFlow.avisar(resposta.mensagem);
        mostrar(secaoAtual);
      } catch (erro) {
        SocialFlow.avisar(SocialFlow.erro(erro), "erro");
      }
    });
    try {
      const ctx = await SocialFlow.preparar();
      if (ctx.usuario) entrarPainel(ctx.usuario);
    } catch (erro) {
      SocialFlow.avisar(SocialFlow.erro(erro), "erro");
    }
  }

  function lerArquivo(arquivo) {
    return new Promise(function (resolve, reject) {
      if (arquivo.size > 1500000) {
        reject(new Error("A imagem pode ter no máximo 1,5 MB."));
        return;
      }
      const leitor = new FileReader();
      leitor.onload = function () {
        const texto = String(leitor.result || "");
        resolve(texto.split(",")[1] || "");
      };
      leitor.onerror = function () { reject(new Error("Não foi possível ler a imagem.")); };
      leitor.readAsDataURL(arquivo);
    });
  }

  document.addEventListener("DOMContentLoaded", iniciar);
})(window);
