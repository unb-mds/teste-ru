import { JSDOM } from "jsdom";
import { readFileSync } from "node:fs";

const RAIZ = new URL("..", import.meta.url).pathname;
const html = readFileSync(`${RAIZ}/index.html`, "utf8");
const app = readFileSync(`${RAIZ}/assets/app.js`, "utf8");
const dados = JSON.parse(readFileSync(`${RAIZ}/data/cardapio.json`, "utf8"));

let falhas = 0;
const ok = (cond, msg) => {
  console.log(`${cond ? "  ok  " : "  FALHOU  "} ${msg}`);
  if (!cond) falhas++;
};

async function montar({ hash = "", agora = "2026-09-02T12:00:00", storage = {} } = {}) {
  const dom = new JSDOM(html, {
    url: "https://exemplo.github.io/" + hash,
    runScripts: "outside-only",
    pretendToBeVisual: true,
  });
  const w = dom.window;
  // relogio fixo
  const Real = w.Date;
  const fixo = new Real(agora);
  class D extends Real {
    constructor(...a) { super(...(a.length ? a : [fixo.getTime()])); }
    static now() { return fixo.getTime(); }
  }
  w.Date = D;
  w.fetch = () => Promise.resolve({ ok: true, json: () => Promise.resolve(dados) });
  const guardado = { ...storage };
  Object.defineProperty(w, "localStorage", {
    value: {
      getItem: (k) => (k in guardado ? guardado[k] : null),
      setItem: (k, v) => { guardado[k] = String(v); },
    },
    configurable: true,
  });
  w.eval(app);
  await new Promise((r) => setTimeout(r, 30));
  return { w, doc: w.document, guardado };
}

const texto = (doc, sel) => (doc.querySelector(sel)?.textContent || "").trim();
const visivel = (doc, id) => !doc.getElementById(id).hidden;

console.log("\n# primeira visita (sem preferencia salva)");
{
  const { doc } = await montar();
  ok(visivel(doc, "selecao"), "mostra a selecao de campus");
  ok(!visivel(doc, "cardapio"), "nao mostra cardapio antes da escolha");
  const botoes = [...doc.querySelectorAll("#lista-campi button")];
  ok(botoes.length === 5, `oferece os cinco campi (${botoes.length})`);
  ok(botoes[0].textContent === "Darcy Ribeiro", "primeiro campus e Darcy Ribeiro");
}

console.log("\n# escolher um campus (RF01)");
{
  const { w, doc, guardado } = await montar();
  doc.querySelectorAll("#lista-campi button")[2].click();
  await new Promise((r) => setTimeout(r, 20));
  ok(guardado["ru-unb:campus"] === "gama", "a escolha e persistida");
  ok(w.location.hash.startsWith("#/gama/"), `a rota reflete o campus (${w.location.hash})`);
  ok(visivel(doc, "cardapio"), "passa a mostrar o cardapio");
  ok(texto(doc, "#campus-atual") === "Gama", "o topo mostra o campus atual");
}

console.log("\n# visita seguinte com preferencia salva (RF02)");
{
  const { w, doc } = await montar({ storage: { "ru-unb:campus": "darcy-ribeiro" } });
  ok(visivel(doc, "cardapio"), "abre direto no cardapio, sem perguntar");
  ok(texto(doc, "#campus-atual") === "Darcy Ribeiro", "usa o campus salvo");
  ok(w.location.hash === "#/darcy-ribeiro/2026-09-02/almoco",
     `abre em hoje e na refeicao do horario (${w.location.hash})`);
  const atual = doc.querySelector('#lista-dias button[aria-current="date"]');
  ok(atual && atual.getAttribute("aria-label").includes("hoje"), "o dia de hoje vem selecionado");
  const cats = [...doc.querySelectorAll(".categoria h2")].map((h) => h.firstChild.textContent);
  ok(cats[0] === "Salada 1" && cats.includes("Prato principal"),
     `categorias na ordem do PDF (${cats.slice(0, 3).join(" · ")})`);
}

console.log("\n# composicao, trilhas e alternativas (RF05)");
{
  const { doc } = await montar({ storage: { "ru-unb:campus": "darcy-ribeiro" } });
  const trilhas = [...doc.querySelectorAll(".trilha")].map((t) => t.textContent);
  ok(trilhas.includes("padrão") && trilhas.includes("ovolactovegetariano") &&
     trilhas.includes("vegetariano estrito"), `as tres trilhas aparecem (${trilhas.join(", ")})`);
  const itens = [...doc.querySelectorAll(".item-nome")].map((i) => i.textContent);
  ok(itens.some((i) => i.includes("Lasanha à bolonhesa")), "lista o prato principal do dia");
  const alerg = [...doc.querySelectorAll(".categoria")].find((c) =>
    c.textContent.includes("Lasanha à bolonhesa"));
  const tags = [...alerg.querySelectorAll(".alergenico")].map((t) => t.textContent);
  ok(tags.includes("leite") && tags.includes("trigo"), `alergenicos por prato (${tags.join(", ")})`);
}

console.log("\n# refeicoes separadas (RF04)");
{
  const { w, doc } = await montar({ storage: { "ru-unb:campus": "darcy-ribeiro" } });
  const abas = [...doc.querySelectorAll("#lista-refeicoes button")];
  ok(abas.length === 3, "tres abas de refeicao");
  abas[0].click();
  await new Promise((r) => setTimeout(r, 20));
  ok(w.location.hash.endsWith("/cafe-da-manha"), "trocar de refeicao muda a rota");
  ok(w.location.hash.includes("2026-09-02"), "trocar de refeicao preserva o dia");
  ok(texto(doc, "#campus-atual") === "Darcy Ribeiro", "trocar de refeicao preserva o campus");
  const cats = [...doc.querySelectorAll(".categoria h2")].map((h) => h.firstChild.textContent);
  ok(cats.includes("Panificação"), `mostra o cafe da manha (${cats.slice(0, 3).join(" · ")})`);
}

console.log("\n# navegacao por data (RF03)");
{
  const { w, doc } = await montar({ storage: { "ru-unb:campus": "darcy-ribeiro" } });
  const dias = [...doc.querySelectorAll("#lista-dias button")];
  ok(dias.length === 7, `sete dias no Darcy (${dias.length})`);
  dias[0].click();
  await new Promise((r) => setTimeout(r, 20));
  ok(w.location.hash.includes("2026-08-31"), `a data vai para a rota (${w.location.hash})`);
}

console.log("\n# campus que nao serve a semana toda");
{
  const { doc } = await montar({ storage: { "ru-unb:campus": "fazenda-agua-limpa" } });
  const dias = [...doc.querySelectorAll("#lista-dias button")];
  ok(dias.length === 5, `Fazenda Agua Limpa mostra 5 dias (${dias.length})`);
  const jantar = [...doc.querySelectorAll("#lista-refeicoes button")].find((b) =>
    b.textContent === "Jantar");
  ok(jantar.disabled, "a aba de jantar fica desabilitada (nao e servido la)");
}

console.log("\n# link compartilhado tem precedencia e nao sobrescreve a preferencia");
{
  const { doc, guardado } = await montar({
    hash: "#/gama/2026-09-03/jantar",
    storage: { "ru-unb:campus": "darcy-ribeiro" },
  });
  ok(texto(doc, "#campus-atual") === "Gama", "a URL vence o campus salvo");
  ok(guardado["ru-unb:campus"] === "darcy-ribeiro", "a preferencia de quem recebeu o link nao muda");
}

console.log("\n# semana desatualizada (frescor)");
{
  const { doc } = await montar({ agora: "2026-09-14T12:00:00",
    storage: { "ru-unb:campus": "darcy-ribeiro" } });
  ok(visivel(doc, "aviso-semana"), "avisa que nao e a semana atual");
  ok(doc.querySelectorAll(".categoria").length === 0, "nao exibe o cardapio velho sem pedido");
  doc.querySelector("#aviso-semana button").click();
  await new Promise((r) => setTimeout(r, 20));
  ok(doc.querySelectorAll(".categoria").length > 0, "'ver mesmo assim' revela o cardapio");
}

console.log("\n# alergenico indeterminado nunca vira 'sem alergenico'");
{
  const { doc } = await montar({ hash: "#/darcy-ribeiro/2026-09-02/jantar" });
  const ind = [...doc.querySelectorAll(".indeterminado")];
  ok(ind.length > 0, `mostra aviso de indeterminado (${ind.length} itens)`);
  ok(ind[0].textContent.includes("não identificados"), "o texto diz que nao foi identificado");
  ok(ind[0].querySelector("a").href.endsWith(".pdf"), "oferece o PDF oficial como saida");
}

console.log("\n# ancora de acessibilidade nao e confundida com rota");
{
  const { w, doc } = await montar({ storage: { "ru-unb:campus": "darcy-ribeiro" } });
  doc.querySelector(".pular").dispatchEvent(new w.Event("click", { cancelable: true, bubbles: true }));
  await new Promise((r) => setTimeout(r, 20));
  ok(visivel(doc, "cardapio"), "pular para o conteudo nao volta para a selecao de campus");
  ok(w.location.hash.startsWith("#/darcy-ribeiro/"), `a rota se mantem (${w.location.hash})`);

  const { doc: doc2 } = await montar({ hash: "#conteudo",
    storage: { "ru-unb:campus": "darcy-ribeiro" } });
  ok(visivel(doc2, "cardapio"), "chegar com #conteudo na URL ainda mostra o cardapio");
}

console.log("\n# dados indisponiveis");
{
  const dom = new JSDOM(html, { url: "https://exemplo.github.io/", runScripts: "outside-only" });
  dom.window.fetch = () => Promise.resolve({ ok: false, status: 404 });
  dom.window.eval(app);
  await new Promise((r) => setTimeout(r, 30));
  ok(!dom.window.document.getElementById("erro").hidden, "mostra estado de erro");
  ok(dom.window.document.querySelector("#erro a").href.includes("ru.unb.br"),
     "aponta para a fonte oficial");
}

console.log(falhas ? `\n${falhas} verificacao(oes) falharam` : "\nTodas as verificacoes passaram");
process.exit(falhas ? 1 : 0);
