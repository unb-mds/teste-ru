/* Cardápio do RU da UnB — interface.
   Lê data/cardapio.json, um snapshot da semana corrente gerado pelo pipeline.
   Nenhuma requisição sai deste domínio. */

(function () {
  "use strict";

  var CHAVE_CAMPUS = "ru-unb:campus";
  var REFEICOES = [
    { tipo: "cafe-da-manha", nome: "Café da manhã", ate: 9.5 },
    { tipo: "almoco", nome: "Almoço", ate: 15 },
    { tipo: "jantar", nome: "Jantar", ate: 24 }
  ];
  var TRILHAS = {
    padrao: "padrão",
    ovolactovegetariano: "ovolactovegetariano",
    "vegetariano-estrito": "vegetariano estrito"
  };
  var SEMANA_CURTA = ["dom", "seg", "ter", "qua", "qui", "sex", "sáb"];

  var dados = null;
  var verMesmoAssim = false;
  var el = {};

  /* ---------- datas ---------- */

  function comoData(iso) {
    var p = String(iso).split("-");
    return new Date(+p[0], +p[1] - 1, +p[2]);
  }

  function comoIso(data) {
    var mes = String(data.getMonth() + 1).padStart(2, "0");
    var dia = String(data.getDate()).padStart(2, "0");
    return data.getFullYear() + "-" + mes + "-" + dia;
  }

  function hoje() {
    return comoIso(new Date());
  }

  function porExtenso(iso) {
    var d = comoData(iso);
    return d.toLocaleDateString("pt-BR", {
      weekday: "long",
      day: "numeric",
      month: "long"
    });
  }

  /* ---------- preferência ---------- */

  function lerPreferencia() {
    try {
      return window.localStorage.getItem(CHAVE_CAMPUS);
    } catch (e) {
      return null;
    }
  }

  function salvarPreferencia(id) {
    try {
      window.localStorage.setItem(CHAVE_CAMPUS, id);
    } catch (e) {
      /* navegação privada: a escolha vale só para esta visita */
    }
  }

  /* ---------- rota ---------- */

  function lerRota() {
    var partes = window.location.hash.replace(/^#\/?/, "").split("/");
    return {
      campus: partes[0] || null,
      data: partes[1] || null,
      refeicao: partes[2] || null
    };
  }

  function irPara(campus, data, refeicao, substituir) {
    var destino = "#/" + [campus, data, refeicao].filter(Boolean).join("/");
    if (window.location.hash === destino) {
      return desenhar();
    }
    if (substituir) {
      window.history.replaceState(null, "", destino);
      desenhar();
    } else {
      window.location.hash = destino;
    }
  }

  /* ---------- consultas aos dados ---------- */

  function acharCampus(id) {
    if (!dados) return null;
    for (var i = 0; i < dados.campi.length; i++) {
      if (dados.campi[i].id === id) return dados.campi[i];
    }
    return null;
  }

  function acharDia(campus, data) {
    if (!campus) return null;
    for (var i = 0; i < campus.dias.length; i++) {
      if (campus.dias[i].data === data) return campus.dias[i];
    }
    return null;
  }

  function acharRefeicao(dia, tipo) {
    if (!dia) return null;
    for (var i = 0; i < dia.refeicoes.length; i++) {
      if (dia.refeicoes[i].tipo === tipo) return dia.refeicoes[i];
    }
    return null;
  }

  function refeicaoDoHorario() {
    var agora = new Date();
    var hora = agora.getHours() + agora.getMinutes() / 60;
    for (var i = 0; i < REFEICOES.length; i++) {
      if (hora < REFEICOES[i].ate) return REFEICOES[i].tipo;
    }
    return "jantar";
  }

  function semanaCobreHoje() {
    if (!dados || !dados.semana || !dados.semana.inicio) return false;
    var agora = hoje();
    return agora >= dados.semana.inicio && agora <= dados.semana.fim;
  }

  /* ---------- desenho ---------- */

  function limpar(no) {
    while (no.firstChild) no.removeChild(no.firstChild);
  }

  function criar(tag, classe, texto) {
    var no = document.createElement(tag);
    if (classe) no.className = classe;
    if (texto != null) no.textContent = texto;
    return no;
  }

  function mostrar(secao) {
    el.selecao.hidden = secao !== "selecao";
    el.cardapio.hidden = secao !== "cardapio";
    el.erro.hidden = secao !== "erro";
    el.topo.hidden = secao !== "cardapio";
  }

  function erro(titulo, detalhe) {
    limpar(el.erro);
    el.erro.appendChild(criar("h2", null, titulo));
    el.erro.appendChild(criar("p", null, detalhe));
    var link = criar("a", null, "Consultar o cardápio oficial");
    link.href = (dados && dados.fonte) || "https://ru.unb.br/cardapio-refeitorio/";
    link.rel = "noopener";
    el.erro.appendChild(link);
    mostrar("erro");
  }

  function desenharSelecao() {
    limpar(el.listaCampi);
    dados.campi.forEach(function (campus) {
      var item = document.createElement("li");
      var botao = criar("button", null, campus.nome);
      botao.type = "button";
      botao.addEventListener("click", function () {
        salvarPreferencia(campus.id);
        irPara(campus.id, null, null);
      });
      item.appendChild(botao);
      el.listaCampi.appendChild(item);
    });
    mostrar("selecao");
  }

  function desenharDias(campus, dataAtual, refeicao) {
    limpar(el.listaDias);
    var agora = hoje();
    campus.dias.forEach(function (dia) {
      var data = comoData(dia.data);
      var botao = criar("button");
      botao.type = "button";
      botao.appendChild(criar("span", "semana", SEMANA_CURTA[data.getDay()]));
      botao.appendChild(criar("span", "numero", String(data.getDate())));
      botao.appendChild(
        criar("span", "hoje-marca", dia.data === agora ? "hoje" : " ")
      );
      botao.setAttribute(
        "aria-label",
        porExtenso(dia.data) + (dia.data === agora ? " (hoje)" : "")
      );
      if (dia.data === dataAtual) botao.setAttribute("aria-current", "date");
      botao.addEventListener("click", function () {
        irPara(campus.id, dia.data, refeicao);
      });
      el.listaDias.appendChild(document.createElement("li")).appendChild(botao);
    });
  }

  function desenharRefeicoes(campus, dia, tipoAtual) {
    limpar(el.listaRefeicoes);
    REFEICOES.forEach(function (refeicao) {
      var existe = !!acharRefeicao(dia, refeicao.tipo);
      var botao = criar("button", null, refeicao.nome);
      botao.type = "button";
      if (!existe) {
        botao.disabled = true;
        botao.title = "Não servido neste dia";
      }
      if (refeicao.tipo === tipoAtual) botao.setAttribute("aria-current", "true");
      botao.addEventListener("click", function () {
        irPara(campus.id, dia.data, refeicao.tipo);
      });
      el.listaRefeicoes.appendChild(document.createElement("li")).appendChild(botao);
    });
  }

  function desenharItem(item, urlPdf) {
    var linha = document.createElement("li");
    var nome = criar("div", "item-nome");
    if (item.alternativa) nome.appendChild(criar("span", "ou", "ou"));
    nome.appendChild(document.createTextNode(item.nome));
    linha.appendChild(nome);

    if (item.alergenicos_status === "indeterminado") {
      var aviso = criar("div", "indeterminado");
      aviso.appendChild(
        document.createTextNode("Alergênicos não identificados — ")
      );
      var link = criar("a", null, "ver cardápio oficial");
      link.href = urlPdf;
      link.rel = "noopener";
      aviso.appendChild(link);
      linha.appendChild(aviso);
    } else if (item.alergenicos.length) {
      var faixa = criar("div", "alergenicos");
      item.alergenicos.forEach(function (nomeAlergenico) {
        faixa.appendChild(criar("span", "alergenico", nomeAlergenico));
      });
      linha.appendChild(faixa);
    }
    return linha;
  }

  function desenharComposicao(refeicao, urlPdf) {
    limpar(el.composicao);
    refeicao.categorias.forEach(function (categoria) {
      var bloco = criar("section", "categoria");
      var titulo = criar("h2", null, categoria.nome);
      if (categoria.trilha) {
        titulo.appendChild(
          criar("span", "trilha", TRILHAS[categoria.trilha] || categoria.trilha)
        );
      }
      bloco.appendChild(titulo);
      var lista = criar("ul", "itens");
      categoria.itens.forEach(function (item) {
        lista.appendChild(desenharItem(item, urlPdf));
      });
      bloco.appendChild(lista);
      el.composicao.appendChild(bloco);
    });
  }

  function desenharAvisoSemana() {
    var aviso = el.avisoSemana;
    limpar(aviso);
    if (semanaCobreHoje()) {
      aviso.hidden = true;
      return false;
    }
    aviso.hidden = false;
    aviso.appendChild(
      criar("strong", null, "Esta não é a semana atual.")
    );
    aviso.appendChild(
      document.createTextNode(
        "O cardápio publicado pela UnB cobre " +
          porExtenso(dados.semana.inicio) +
          " a " +
          porExtenso(dados.semana.fim) +
          "."
      )
    );
    if (!verMesmoAssim) {
      var botao = criar("button", null, "Ver mesmo assim");
      botao.type = "button";
      botao.addEventListener("click", function () {
        verMesmoAssim = true;
        desenhar();
      });
      aviso.appendChild(botao);
    }
    return true;
  }

  function desenharColeta() {
    if (!dados.gerado_em) return;
    var quando = new Date(dados.gerado_em);
    el.coleta.textContent =
      "Coletado em " +
      quando.toLocaleString("pt-BR", {
        day: "2-digit",
        month: "2-digit",
        hour: "2-digit",
        minute: "2-digit"
      }) +
      ".";
  }

  function desenhar() {
    if (!dados) return;
    var rota = lerRota();

    if (rota.campus === "escolher") return desenharSelecao();

    var idCampus = rota.campus || lerPreferencia();
    var campus = acharCampus(idCampus);
    if (!campus) return desenharSelecao();

    if (!campus.dias.length) {
      return erro(
        "Sem cardápio para " + campus.nome,
        "A coleta mais recente não trouxe nenhum dia para este campus."
      );
    }

    /* dia: o da rota, senão hoje, senão o primeiro da semana */
    var dia = acharDia(campus, rota.data) || acharDia(campus, hoje()) || campus.dias[0];
    /* refeição: a da rota, senão a sugerida pelo horário, senão a primeira do dia */
    var tipo = rota.refeicao;
    var refeicao = acharRefeicao(dia, tipo);
    if (!refeicao) refeicao = acharRefeicao(dia, refeicaoDoHorario());
    if (!refeicao) refeicao = dia.refeicoes[0];

    if (
      rota.campus !== campus.id ||
      rota.data !== dia.data ||
      (refeicao && rota.refeicao !== refeicao.tipo)
    ) {
      return irPara(campus.id, dia.data, refeicao ? refeicao.tipo : null, true);
    }

    el.campusAtual.textContent = campus.nome;
    el.linkPdf.href = campus.pdf || dados.fonte;
    mostrar("cardapio");

    var foraDaSemana = desenharAvisoSemana();
    desenharDias(campus, dia.data, refeicao ? refeicao.tipo : null);
    desenharRefeicoes(campus, dia, refeicao ? refeicao.tipo : null);

    if (foraDaSemana && !verMesmoAssim) {
      limpar(el.composicao);
      el.observacao.textContent = "";
      desenharColeta();
      return;
    }

    if (!refeicao) {
      limpar(el.composicao);
      el.composicao.appendChild(
        criar(
          "p",
          "vazio",
          "Nenhuma refeição servida em " + porExtenso(dia.data) + " neste campus."
        )
      );
      el.observacao.textContent = "";
      desenharColeta();
      return;
    }

    desenharComposicao(refeicao, campus.pdf || dados.fonte);
    el.observacao.textContent = refeicao.observacao || "";
    desenharColeta();
    document.title =
      refeicao.nome + " · " + campus.nome + " · Cardápio do RU";
  }

  /* ---------- início ---------- */

  function iniciar() {
    [
      ["topo", "topo"],
      ["selecao", "selecao"],
      ["cardapio", "cardapio"],
      ["erro", "erro"],
      ["listaCampi", "lista-campi"],
      ["listaDias", "lista-dias"],
      ["listaRefeicoes", "lista-refeicoes"],
      ["composicao", "composicao"],
      ["campusAtual", "campus-atual"],
      ["avisoSemana", "aviso-semana"],
      ["observacao", "observacao"],
      ["coleta", "coleta"],
      ["linkPdf", "link-pdf"]
    ].forEach(function (par) {
      el[par[0]] = document.getElementById(par[1]);
    });

    document.getElementById("trocar-campus").addEventListener("click", function () {
      window.location.hash = "#/escolher";
    });
    window.addEventListener("hashchange", desenhar);

    fetch("data/cardapio.json", { cache: "no-cache" })
      .then(function (resposta) {
        if (!resposta.ok) throw new Error("HTTP " + resposta.status);
        return resposta.json();
      })
      .then(function (conteudo) {
        dados = conteudo;
        desenhar();
      })
      .catch(function () {
        erro(
          "Cardápio indisponível",
          "Não foi possível carregar os dados desta semana."
        );
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", iniciar);
  } else {
    iniciar();
  }
})();
