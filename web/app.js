/* Front-end das Árvores UnB Gama.
 * O Python (src/*.py) roda no navegador via Pyodide. Este arquivo só desenha
 * a árvore com D3 e anima os passos que as árvores em Python registram. */
"use strict";

const PYODIDE_URL = "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/";
const ARQUIVOS_PY = ["__init__.py", "normaliza.py", "carregaDados.py", "arvore_bst.py",
  "arvore_avl.py", "arvore_rubro_negra.py", "api.py"];

const ESPACO_X = 40;   // distância horizontal entre vizinhos em-ordem
const ESPACO_Y = 74;   // distância entre níveis
const LARG_NO = 72, ALT_NO = 26;

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => [...document.querySelectorAll(sel)];

let api = null;                     // módulo src.api (Python)
const estado = {
  arvores: { avl: null, rb: null, bst: null },
  metricas: null,
  tipo: "avl",                      // árvore em exibição
  arvoreTela: null,                 // árvore efetivamente desenhada
  posicoes: new Map(),              // id -> {x, y}
  selecionado: null,
  demo: false,
};

/* ------------------------------------------------------------------ Python */
const py = (nome, ...args) => JSON.parse(api[nome](...args));

async function iniciarPython() {
  const pyodide = await loadPyodide({ indexURL: PYODIDE_URL });
  $("#carregando-texto").textContent = "Carregando as árvores em Python…";
  const raiz = "/home/pyodide/projeto";
  pyodide.FS.mkdirTree(raiz + "/src");
  pyodide.FS.mkdirTree(raiz + "/data");
  const baixar = async (caminho) => {
    const r = await fetch(new URL(caminho, location.href), { cache: "no-cache" });
    if (!r.ok) throw new Error(`Não foi possível baixar ${caminho}`);
    return r.text();
  };
  await Promise.all([
    ...ARQUIVOS_PY.map(async (f) => pyodide.FS.writeFile(`${raiz}/src/${f}`, await baixar(`../src/${f}`))),
    baixar("../data/disciplinas.json").then((t) => pyodide.FS.writeFile(`${raiz}/data/disciplinas.json`, t)),
  ]);
  pyodide.runPython(`import sys; sys.path.insert(0, "${raiz}")`);
  api = pyodide.pyimport("src.api");
}

/* ------------------------------------------------------------------ Utilidades */
const normalizar = (s) => s.normalize("NFKD").replace(/[̀-ͯ]/g, "").toLowerCase()
  .replace(/[^a-z0-9]+/g, " ").trim();
const escapar = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const curto = (s, n) => (s.length > n ? s.slice(0, n - 1) + "…" : s);

let avisoTimer;
function avisar(msg) {
  const el = $("#aviso");
  el.textContent = msg;
  el.hidden = false;
  clearTimeout(avisoTimer);
  avisoTimer = setTimeout(() => (el.hidden = true), 3200);
}

function atualizarEstado(e) {
  estado.arvores = { avl: e.avl, rb: e.rb, bst: e.bst };
  estado.metricas = e.metricas;
  atualizarChips();
  atualizarGraficos();
}

/* ------------------------------------------------------------------ Desenho */
const svg = d3.select("#svg");
const camada = svg.append("g");
const gArestas = camada.append("g");
const gNos = camada.append("g");
const zoom = d3.zoom().scaleExtent([0.04, 3]).on("zoom", (ev) => camada.attr("transform", ev.transform));
svg.call(zoom).on("dblclick.zoom", null);

/** Posição x = ordem no percurso em-ordem; y = profundidade. */
function calcularLayout(raiz) {
  const nos = [], arestas = [];
  let indice = 0;
  (function visitar(no, prof, pai) {
    if (!no) return;
    visitar(no.esq, prof + 1, no);
    const item = { ...no, x: indice++ * ESPACO_X, y: prof * ESPACO_Y, pai: pai ? pai.id : null };
    delete item.esq; delete item.dir;
    nos.push(item);
    visitar(no.dir, prof + 1, no);
  })(raiz, 0, null);
  const mapa = new Map(nos.map((n) => [n.id, n]));
  nos.forEach((n) => { if (n.pai) arestas.push({ id: n.id, de: mapa.get(n.pai), para: n }); });
  return { nos, arestas, mapa };
}

const caminhoAresta = (a) => {
  const x1 = a.de.x, y1 = a.de.y + ALT_NO / 2, x2 = a.para.x, y2 = a.para.y - ALT_NO / 2;
  const my = (y1 + y2) / 2;
  return `M${x1},${y1} C${x1},${my} ${x2},${my} ${x2},${y2}`;
};

function rotuloNo(n, tipo) {
  return tipo === "rb" ? curto(n.rotulo, 11) : n.id;
}

function desenhar(raiz, tipo, duracao = 450) {
  estado.arvoreTela = raiz;
  $("#vazio").hidden = !!raiz;
  const { nos, arestas, mapa } = calcularLayout(raiz);
  const anteriores = estado.posicoes;
  estado.posicoes = new Map(nos.map((n) => [n.id, { x: n.x, y: n.y }]));
  const t = svg.transition().duration(duracao).ease(d3.easeCubicInOut);

  // Arestas
  gArestas.selectAll("path.aresta").data(arestas, (a) => a.id).join(
    (entra) => entra.append("path").attr("class", "aresta").attr("opacity", 0)
      .attr("d", (a) => {
        const p = anteriores.get(a.para.id) || anteriores.get(a.de.id) || a.de;
        const d = anteriores.get(a.de.id) || p;
        return caminhoAresta({ de: d, para: p });
      }),
    (atualiza) => atualiza,
    (sai) => sai.transition(t).attr("opacity", 0).remove(),
  ).attr("data-de", (a) => a.de.id)
    .transition(t).attr("opacity", 1).attr("d", caminhoAresta);

  // Nós
  const grupos = gNos.selectAll("g.no").data(nos, (n) => n.id).join(
    (entra) => {
      const g = entra.append("g").attr("class", "no").attr("opacity", 0)
        .attr("transform", (n) => {
          const p = anteriores.get(n.id) || (n.pai && anteriores.get(n.pai)) || n;
          return `translate(${p.x},${p.y - (anteriores.has(n.id) ? 0 : 18)})`;
        })
        .on("click", (ev, n) => { ev.stopPropagation(); abrirCartao(n.id); });
      g.append("rect").attr("x", -LARG_NO / 2).attr("y", -ALT_NO / 2)
        .attr("width", LARG_NO).attr("height", ALT_NO).attr("rx", ALT_NO / 2);
      g.append("text").attr("class", "rot");
      g.append("title");
      const b = g.append("g").attr("class", "badge").attr("transform", `translate(${LARG_NO / 2 - 2},${-ALT_NO / 2 + 1})`);
      b.append("circle").attr("r", 8.5);
      b.append("text");
      return g;
    },
    (atualiza) => atualiza,
    (sai) => sai.transition(t).attr("opacity", 0).attr("transform", (n) => {
      const p = anteriores.get(n.id) || n;
      return `translate(${p.x},${p.y + 24}) scale(.4)`;
    }).remove(),
  );

  grupos.attr("class", (n) => {
    const c = ["no", "tipo-" + tipo];
    if (n.cor) c.push(n.cor);
    if (n.fb !== undefined) c.push(Math.abs(n.fb) >= 2 ? "fb-alerta" : n.fb > 0 ? "fb-mais" : n.fb < 0 ? "fb-menos" : "fb-zero");
    if (n.id === estado.selecionado) c.push("selecionado");
    return c.join(" ");
  });
  grupos.select("text.rot").text((n) => rotuloNo(n, tipo));
  grupos.select("title").text((n) => `${n.id} — ${n.rotulo}`);
  grupos.select(".badge").attr("display", (n) => (n.fb === undefined ? "none" : null));
  grupos.select(".badge text").text((n) => (n.fb > 0 ? "+" + n.fb : n.fb));
  grupos.transition(t).attr("opacity", 1).attr("transform", (n) => `translate(${n.x},${n.y})`);

  estado.mapa = mapa;
}

function marcar({ atual = [], visitados = [], alerta = [], achados = [] } = {}) {
  const sets = { atual: new Set(atual), visitado: new Set(visitados), alerta: new Set(alerta), achado: new Set(achados) };
  gNos.selectAll("g.no")
    .classed("atual", (n) => sets.atual.has(n.id))
    .classed("visitado", (n) => sets.visitado.has(n.id))
    .classed("alerta", (n) => sets.alerta.has(n.id))
    .classed("achado", (n) => sets.achado.has(n.id))
    .classed("selecionado", (n) => n.id === estado.selecionado);
  const noCaminho = new Set([...sets.visitado, ...sets.atual, ...sets.achado]);
  gArestas.selectAll("path.aresta").classed("caminho", (a) => noCaminho.has(a.id) && noCaminho.has(a.de.id));
}

/* ------------------------------------------------------------------ Câmera */
function tamanhoTela() {
  const r = $("#svg").getBoundingClientRect();
  return { w: r.width || 800, h: r.height || 500 };
}

/** Enquadra a árvore. Com `escalaMinima`, árvores largas começam legíveis,
 *  centradas na raiz; o botão ⤢ mostra a árvore inteira. */
function ajustar(duracao = 600, escalaMinima = 0) {
  const pos = [...estado.posicoes.values()];
  const { w, h } = tamanhoTela();
  if (!pos.length) return;
  const minX = d3.min(pos, (p) => p.x) - LARG_NO, maxX = d3.max(pos, (p) => p.x) + LARG_NO;
  const minY = d3.min(pos, (p) => p.y) - 40, maxY = d3.max(pos, (p) => p.y) + 70;
  let k = Math.min(w / (maxX - minX), h / (maxY - minY), 1.3);
  let tx = w / 2 - k * (minX + maxX) / 2, ty = (h - k * (maxY - minY)) / 2 - k * minY;
  if (k < escalaMinima) {
    const raiz = estado.arvoreTela && estado.posicoes.get(estado.arvoreTela.id);
    k = escalaMinima;
    tx = w / 2 - k * raiz.x;
    ty = 70 - k * raiz.y;
  }
  svg.transition().duration(duracao).call(zoom.transform, d3.zoomIdentity.translate(tx, ty).scale(k));
}

function limparPlayer(texto = "Busque, insira ou remova uma disciplina para ver a árvore trabalhando.") {
  pausar();
  player.passos = []; player.i = 0;
  ["#p-tocar", "#p-proximo", "#p-fim"].forEach((s) => ($(s).disabled = true));
  $("#p-texto").textContent = texto;
  $("#p-contador").textContent = "";
  $("#p-barra").style.width = "0";
}

function focar(id, duracao = 450) {
  const p = estado.posicoes.get(id);
  if (!p) return;
  const { w, h } = tamanhoTela();
  const k = Math.max(d3.zoomTransform(svg.node()).k, 0.85);
  svg.transition("camera").duration(duracao)
    .call(zoom.transform, d3.zoomIdentity.translate(w / 2 - p.x * k, h * 0.4 - p.y * k).scale(k));
}

$("#ajustar").onclick = () => ajustar();
$("#zoom-mais").onclick = () => svg.transition().duration(250).call(zoom.scaleBy, 1.35);
$("#zoom-menos").onclick = () => svg.transition().duration(250).call(zoom.scaleBy, 1 / 1.35);
svg.on("click", () => fecharCartao());

/* ------------------------------------------------------------------ Player */
const player = { passos: [], i: 0, timer: null, tocando: false, tipo: "avl", visitados: new Set(), aoFim: null };
const atrasoBase = () => 900 / Number($("#p-vel").value);

function tocar(passos, { tipo = estado.tipo, aoFim = null, autoplay = true } = {}) {
  pausar();
  Object.assign(player, { passos, i: 0, tipo, visitados: new Set(), aoFim });
  ["#p-tocar", "#p-proximo", "#p-fim"].forEach((s) => ($(s).disabled = !passos.length));
  if (!passos.length) return;
  if (autoplay) retomar(); else aplicar(player.passos[0]);
}

function aplicar(p, rapido = false) {
  const dur = rapido ? 0 : Math.min(500, atrasoBase() * 0.75);
  if (p.arvore !== undefined) desenhar(p.arvore, player.tipo, dur);
  if (p.tipo === "info") player.visitados.clear();   // nova inserção na demonstração
  if (p.tipo === "visita") p.destaque.forEach((id) => player.visitados.add(id));
  const atual = p.tipo === "achado" ? [] : p.destaque;
  marcar({
    atual,
    visitados: [...player.visitados],
    alerta: p.tipo === "desbalanceado" ? p.destaque : [],
    achados: p.achados || (p.tipo === "achado" ? p.destaque : []),
  });
  $("#p-texto").textContent = p.descricao || "";
  $("#p-contador").textContent = `${player.i + 1}/${player.passos.length}`;
  $("#p-barra").style.width = `${((player.i + 1) / player.passos.length) * 100}%`;
  if (!rapido && $("#seguir").checked && p.destaque && p.destaque.length) focar(p.destaque[0], dur);
}

function passoSeguinte() {
  if (player.i >= player.passos.length) return false;
  aplicar(player.passos[player.i]);
  player.i += 1;
  if (player.i >= player.passos.length) { finalizar(); return false; }
  return true;
}

function retomar() {
  player.tocando = true;
  $("#p-tocar").textContent = "⏸";
  const loop = () => {
    if (!player.tocando) return;
    if (passoSeguinte()) player.timer = setTimeout(loop, atrasoBase());
  };
  loop();
}

function pausar() {
  player.tocando = false;
  clearTimeout(player.timer);
  $("#p-tocar").textContent = "▶";
}

function finalizar() {
  pausar();
  $("#p-proximo").disabled = $("#p-fim").disabled = true;
  $("#p-tocar").textContent = "↺";
  const fn = player.aoFim;
  player.aoFim = null;
  if (fn) fn();
}

function pularFim() {
  pausar();
  const resto = player.passos.slice(player.i);
  const ultimoComArvore = [...resto].reverse().find((p) => p.arvore !== undefined);
  if (ultimoComArvore) desenhar(ultimoComArvore.arvore, player.tipo, 300);
  resto.forEach((p) => {
    if (p.tipo === "info") player.visitados.clear();
    if (p.tipo === "visita") p.destaque.forEach((id) => player.visitados.add(id));
  });
  player.i = player.passos.length - 1;
  aplicar(player.passos[player.i], true);
  player.i = player.passos.length;
  finalizar();
}

$("#p-tocar").onclick = () => {
  if (player.tocando) return pausar();
  if (player.i >= player.passos.length) {          // recomeçar
    player.i = 0; player.visitados = new Set();
    $("#p-proximo").disabled = $("#p-fim").disabled = false;
  }
  retomar();
};
$("#p-proximo").onclick = () => { pausar(); passoSeguinte(); };
$("#p-fim").onclick = pularFim;

/* ------------------------------------------------------------------ Visões */
function mostrarTipo(tipo, { redesenhar = true } = {}) {
  estado.tipo = tipo;
  $$("#visoes button").forEach((b) => b.classList.toggle("ativo", b.dataset.tipo === tipo));
  atualizarLegenda();
  atualizarChips();
  if (redesenhar) {
    sairDemo(false);
    fecharCartao();
    limparPlayer();
    desenhar(estado.arvores[tipo], tipo, 0);
    marcar();
    ajustar(0, tipo === "bst" ? 0 : 0.5);
  }
}

$$("#visoes button").forEach((b) => (b.onclick = () => mostrarTipo(b.dataset.tipo)));

function atualizarLegenda() {
  const l = {
    avl: `<span><i></i>nó (código)</span><span><i class="a"></i>fator ±2 → rotação</span><span><i class="c"></i>caminho</span><span><i class="ok"></i>encontrado</span>`,
    rb: `<span><i class="v"></i>vermelho</span><span><i class="p"></i>preto</span><span><i class="c"></i>caminho</span><span><i class="ok"></i>encontrado</span><span>ordenada por nome</span>`,
    bst: `<span><i></i>sem balanceamento</span><span><i class="c"></i>caminho</span><span><i class="ok"></i>encontrado</span>`,
  };
  $("#legenda").innerHTML = l[estado.tipo];
}

function atualizarChips() {
  if (!estado.metricas) return;
  const m = estado.metricas.arvores.find((a) => a.tipo === estado.tipo);
  const extra = estado.tipo === "rb" ? `<span class="chip">recolorações <b>${m.recoloracoes}</b></span>` : "";
  $("#chips").innerHTML = `
    <span class="chip">nós <b>${m.nos}</b></span>
    <span class="chip">altura <b>${m.altura}</b> <span title="altura mínima possível">(mín. ${estado.metricas.altura_minima})</span></span>
    <span class="chip">rotações <b>${m.rotacoes}</b></span>${extra}
    <span class="chip">comparações médias <b>${m.comparacoes_media}</b></span>`;
}

/* ------------------------------------------------------------------ Cartão */
function abrirCartao(id) {
  const d = py("disciplina", id);
  if (!d) return;
  estado.selecionado = id;
  gNos.selectAll("g.no").classed("selecionado", (n) => n.id === id);
  const n = estado.mapa && estado.mapa.get(id);
  let infoNo = "";
  if (n && n.fb !== undefined) infoNo = `<dt>Nó AVL</dt><dd>altura ${n.altura} · fator ${n.fb > 0 ? "+" : ""}${n.fb}</dd>`;
  if (n && n.cor) infoNo = `<dt>Nó RB</dt><dd><span class="pilula-cor" style="background:var(--${n.cor === "vermelho" ? "vermelho" : "preto"})"></span>${n.cor}</dd>`;
  const c = $("#cartao");
  c.innerHTML = `
    <button class="fechar" aria-label="Fechar">×</button>
    <span class="codigo">${escapar(d.codigo)}</span>
    <h4>${escapar(d.nome)}</h4>
    <dl>
      <dt>Professores</dt><dd>${d.professores.map(escapar).join("<br>")}</dd>
      <dt>Carga</dt><dd>${d.carga_horaria ?? "—"} h</dd>
      <dt>Turmas</dt><dd>${d.numero_turmas ?? "—"}</dd>
      ${infoNo}
    </dl>
    <div class="acoes">
      <button class="botao pequeno" data-acao="caminho">Ver caminho</button>
      <button class="botao pequeno perigo" data-acao="remover">Remover</button>
    </div>`;
  c.hidden = false;
  c.querySelector(".fechar").onclick = fecharCartao;
  c.querySelector('[data-acao="caminho"]').onclick = () => animarBusca(d.codigo, estado.tipo);
  c.querySelector('[data-acao="remover"]').onclick = () => removerDisciplina(d.codigo);
}

function fecharCartao() {
  $("#cartao").hidden = true;
  estado.selecionado = null;
  gNos.selectAll("g.no").classed("selecionado", false);
}

/* ------------------------------------------------------------------ Buscas */
function garantirArvoreReal(tipo) {
  if (estado.tipo !== tipo || estado.demo || estado.arvoreTela !== estado.arvores[tipo]) mostrarTipo(tipo);
}

function animarBusca(codigo, tipo = "avl") {
  garantirArvoreReal(tipo);
  const r = py("buscar_codigo", codigo, tipo);
  const alvo = r.resultado;
  const chaveAlvo = alvo ? (tipo === "rb" ? normalizar(alvo.nome) : alvo.codigo) : codigo.toUpperCase();
  const passos = r.caminho.map((id) => {
    const n = estado.mapa.get(id);
    const chaveNo = tipo === "rb" ? normalizar(n.rotulo) : id;
    let descricao;
    if (alvo && id === alvo.codigo) descricao = `${id} encontrado em ${r.caminho.length} comparações`;
    else {
      const menor = chaveAlvo < chaveNo;
      const rot = tipo === "rb" ? `“${curto(n.rotulo, 26)}”` : id;
      descricao = `${tipo === "rb" ? "nome" : codigo.toUpperCase()} ${menor ? "<" : ">"} ${rot} → desce à ${menor ? "esquerda" : "direita"}`;
    }
    return { tipo: alvo && id === alvo.codigo ? "achado" : "visita", destaque: [id], descricao };
  });
  if (!alvo) passos.push({ tipo: "fim", destaque: [], descricao: `${codigo.toUpperCase()} não está na árvore (${r.caminho.length} comparações)` });
  tocar(passos, { tipo, aoFim: () => alvo && abrirCartao(alvo.codigo) });
  if (!alvo) avisar("Disciplina não encontrada.");
}

function animarVisitas(visitados, achados, tipo, descricaoFim) {
  garantirArvoreReal(tipo);
  const passos = visitados.map((id) => ({ tipo: "visita", destaque: [id], descricao: `Visitando ${id}` }));
  passos.push({ tipo: "fim", destaque: [], achados, descricao: descricaoFim });
  tocar(passos, { tipo });
}

function listarResultados(lista, titulo) {
  $("#resultados-cab").hidden = false;
  $("#resultados-cab").textContent = titulo;
  $("#resultados").innerHTML = lista.map((d) => `
    <li data-codigo="${escapar(d.codigo)}">
      <span class="codigo">${escapar(d.codigo)}</span>
      <div class="nome">${escapar(d.nome)}</div>
      <div class="prof">${escapar(d.professor || d.professores.join("; "))}</div>
    </li>`).join("");
  $$("#resultados li").forEach((li) => (li.onclick = () => animarBusca(li.dataset.codigo, estado.tipo === "rb" ? "rb" : "avl")));
}

$("#form-codigo").onsubmit = (ev) => {
  ev.preventDefault();
  const c = $("#in-codigo").value.trim();
  if (c) animarBusca(c.split(" ")[0], "avl");
};

$("#form-faixa").onsubmit = (ev) => {
  ev.preventDefault();
  const de = $("#in-de").value.trim() || "A", ate = $("#in-ate").value.trim() || "Z";
  const r = py("buscar_faixa", de, ate);
  listarResultados(r.resultados, `${r.resultados.length} disciplinas entre ${de.toUpperCase()} e ${ate.toUpperCase()} · ${r.visitados.length} nós visitados`);
  animarVisitas(r.visitados, r.resultados.map((d) => d.codigo), "avl",
    `${r.resultados.length} encontradas visitando ${r.visitados.length} de ${estado.metricas.n} nós`);
};

$("#form-prof").onsubmit = (ev) => {
  ev.preventDefault();
  const r = py("buscar_professor", $("#in-prof").value);
  listarResultados(r.resultados, `${r.resultados.length} disciplinas do professor`);
  if (r.resultados.length) {
    garantirArvoreReal(estado.tipo === "bst" ? "avl" : estado.tipo);
    marcar({ achados: r.resultados.map((d) => d.codigo) });
    $("#p-texto").textContent = `${r.resultados.length} disciplinas destacadas na árvore`;
  }
};

// Autocompletar por nome (Rubro-Negra)
let sugestaoAtiva = -1, ultimaPrefixo = null;
function realcar(nome, termo) {
  const n = normalizar(nome), t = normalizar(termo);
  if (!t || !n.startsWith(t)) return escapar(nome);
  // Conta caracteres do original até cobrir o prefixo normalizado.
  let i = 0, cont = 0;
  while (i < nome.length && cont < t.length) { cont += normalizar(nome[i]).length || (nome[i] === " " ? 1 : 0); i++; }
  return `<mark>${escapar(nome.slice(0, i))}</mark>${escapar(nome.slice(i))}`;
}
function sugerir() {
  const termo = $("#in-nome").value;
  const ul = $("#sugestoes");
  if (!normalizar(termo)) { ul.hidden = true; $("#dica-nome").textContent = "Autocompletar: busca por faixa na RB ordenada por nome."; return; }
  const r = py("buscar_prefixo", termo);
  ultimaPrefixo = r;
  sugestaoAtiva = -1;
  $("#dica-nome").textContent = `${r.resultados.length} resultado(s) · ${r.visitados.length} nós visitados na Rubro-Negra (Enter anima)`;
  ul.innerHTML = r.resultados.slice(0, 10).map((d) =>
    `<li data-codigo="${escapar(d.codigo)}"><span class="codigo">${escapar(d.codigo)}</span><span>${realcar(d.nome, termo)}</span></li>`).join("")
    || `<li class="nada">Nenhuma disciplina começa assim</li>`;
  ul.hidden = false;
  $$("#sugestoes li[data-codigo]").forEach((li) => (li.onmousedown = (ev) => {
    ev.preventDefault();
    ul.hidden = true;
    animarBusca(li.dataset.codigo, "rb");
  }));
}
let sugerirTimer;
$("#in-nome").addEventListener("input", () => { clearTimeout(sugerirTimer); sugerirTimer = setTimeout(sugerir, 90); });
$("#in-nome").addEventListener("blur", () => setTimeout(() => ($("#sugestoes").hidden = true), 120));
$("#in-nome").addEventListener("focus", () => { if (normalizar($("#in-nome").value)) sugerir(); });
$("#in-nome").addEventListener("keydown", (ev) => {
  const itens = $$("#sugestoes li[data-codigo]");
  if (ev.key === "ArrowDown" || ev.key === "ArrowUp") {
    ev.preventDefault();
    if (!itens.length) return;
    sugestaoAtiva = (sugestaoAtiva + (ev.key === "ArrowDown" ? 1 : -1) + itens.length) % itens.length;
    itens.forEach((li, i) => li.classList.toggle("ativo", i === sugestaoAtiva));
  } else if (ev.key === "Enter") {
    ev.preventDefault();
    $("#sugestoes").hidden = true;
    if (sugestaoAtiva >= 0 && itens[sugestaoAtiva]) return animarBusca(itens[sugestaoAtiva].dataset.codigo, "rb");
    const r = ultimaPrefixo || py("buscar_prefixo", $("#in-nome").value);
    listarResultados(r.resultados, `${r.resultados.length} nomes com esse início · ${r.visitados.length} nós visitados`);
    animarVisitas(r.visitados, r.resultados.map((d) => d.codigo), "rb",
      `${r.resultados.length} nomes encontrados visitando ${r.visitados.length} nós da Rubro-Negra`);
  } else if (ev.key === "Escape") $("#sugestoes").hidden = true;
});

/* ------------------------------------------------------------------ Inserir / remover */
function aplicarModificacao(r, verbo) {
  if (r.erro) return avisar(r.erro);
  const tipo = estado.tipo;
  const passos = r.passos[tipo];
  atualizarEstado(py("estado"));
  sairDemo(false);
  fecharCartao();
  tocar(passos, {
    tipo,
    aoFim: () => {
      desenhar(estado.arvores[tipo], tipo, 300);
      marcar(verbo === "inserida" ? { achados: [r.disciplina.codigo] } : {});
      if (verbo === "inserida") focar(r.disciplina.codigo);
      $("#p-texto").textContent = `${r.disciplina.codigo} ${verbo}. ${resumoPassos(r.passos[tipo])}`;
    },
  });
  preencherDatalist();
}

function resumoPassos(passos) {
  const rot = passos.filter((p) => p.tipo === "rotacao").length;
  const rec = passos.filter((p) => p.tipo === "recolorir").length;
  const partes = [`${rot} rotação(ões)`];
  if (estado.tipo === "rb") partes.push(`${rec} recoloração(ões)`);
  return partes.join(", ") + ".";
}

$("#form-inserir").onsubmit = (ev) => {
  ev.preventDefault();
  const dados = Object.fromEntries(new FormData(ev.target).entries());
  const r = py("inserir", JSON.stringify(dados));
  if (!r.erro) ev.target.reset();
  aplicarModificacao(r, r.nova ? "inserida" : "atualizada");
};

$("#exemplo").onclick = () => {
  const f = $("#form-inserir");
  const usados = new Set([...estado.posicoes.keys()]);
  let n = 900 + Math.floor(Math.random() * 99);
  while (usados.has(`FGA0${n}`)) n++;
  f.codigo.value = `FGA0${n}`;
  f.nome.value = ["Estruturas de Dados 3", "Árvores Balanceadas Aplicadas", "Tópicos em Algoritmos", "Laboratório de Grafos"][n % 4];
  f.professores.value = "Professor Exemplo";
  f.carga_horaria.value = 60;
  f.numero_turmas.value = 1;
};

function removerDisciplina(codigo) {
  const r = py("remover", codigo);
  aplicarModificacao(r, "removida");
}

$("#form-remover").onsubmit = (ev) => {
  ev.preventDefault();
  const c = $("#in-remover").value.trim().split(" ")[0];
  if (c) removerDisciplina(c);
  ev.target.reset();
};

/* ------------------------------------------------------------------ Demonstração */
$("#demo-n").oninput = () => ($("#demo-n-val").textContent = $("#demo-n").value);
$("#demo-iniciar").onclick = () => {
  const tipo = $("#demo-tipo").value, n = Number($("#demo-n").value), ordem = $("#demo-ordem").value;
  const r = py("demonstracao", tipo, n, ordem);
  mostrarTipo(tipo, { redesenhar: false });
  fecharCartao();
  estado.demo = true;
  estado.posicoes = new Map();
  desenhar(null, tipo, 0);
  svg.call(zoom.transform, d3.zoomIdentity.translate(tamanhoTela().w / 2, 60));
  $("#faixa-demo").hidden = false;
  $("#faixa-demo-texto").textContent = `Demonstração: ${n} disciplinas, ${$("#demo-ordem").selectedOptions[0].text.toLowerCase()}`;
  tocar(r.passos, { tipo, aoFim: () => ajustar() });
};

function sairDemo(redesenhar = true) {
  if (!estado.demo) return;
  estado.demo = false;
  $("#faixa-demo").hidden = true;
  if (redesenhar) mostrarTipo(estado.tipo);
}
$("#sair-demo").onclick = () => sairDemo(true);

/* ------------------------------------------------------------------ Comparar */
$$("#ordens button").forEach((b) => (b.onclick = () => {
  $$("#ordens button").forEach((x) => x.classList.toggle("ativo", x === b));
  atualizarEstado(py("reconstruir", b.dataset.ordem));
  mostrarTipo(estado.tipo);
  avisar(`Árvores reconstruídas com entrada ${b.textContent.toLowerCase()}.`);
}));

function atualizarGraficos() {
  const m = estado.metricas;
  if (!m) return;
  const ordem = ["bst", "avl", "rb"];
  const arv = Object.fromEntries(m.arvores.map((a) => [a.tipo, a]));
  const grafico = (titulo, sub, campo, marca) => {
    const max = Math.max(1, ...ordem.map((t) => arv[t][campo]), marca || 0);
    return `<div class="grafico"><h5>${titulo}<small>${sub}</small></h5>${ordem.map((t) => `
      <div class="barra-linha"><span>${arv[t].nome.replace(" simples", "")}</span>
        <div class="barra-trilho"><div class="barra-valor ${t}" style="width:${(arv[t][campo] / max) * 100}%"></div>
        ${marca ? `<div class="barra-marca" style="left:${(marca / max) * 100}%" title="mínimo possível"></div>` : ""}</div>
        <span class="barra-num">${arv[t][campo]}</span></div>`).join("")}</div>`;
  };
  $("#graficos").innerHTML =
    grafico("Altura", `mínimo possível ${m.altura_minima} (linha verde)`, "altura", m.altura_minima) +
    grafico("Comparações médias por busca", "menor é melhor", "comparacoes_media") +
    grafico("Rotações na construção", "custo do balanceamento", "rotacoes") +
    grafico("Recolorações", "só na Rubro-Negra", "recoloracoes");
  const bst = arv.bst, avl = arv.avl, rb = arv.rb;
  $("#leitura").innerHTML = `Com ${m.n} disciplinas em ordem <b>${{ json: "do JSON", ordenada: "crescente", aleatoria: "aleatória" }[m.ordem]}</b>, ` +
    `a BST chegou a altura <b>${bst.altura}</b>, enquanto a AVL ficou em <b>${avl.altura}</b> (limite teórico ${m.limite_avl}) ` +
    `e a Rubro-Negra em <b>${rb.altura}</b> (limite ${m.limite_rb}, altura negra ${rb.altura_negra}). ` +
    `Uma busca na BST faz em média ${bst.comparacoes_media} comparações, contra ${avl.comparacoes_media} na AVL.`;
}

/* ------------------------------------------------------------------ Abas, tema */
$$(".aba").forEach((b) => (b.onclick = () => {
  $$(".aba").forEach((x) => x.classList.toggle("ativa", x === b));
  $$(".conteudo-aba").forEach((s) => s.classList.toggle("ativa", s.id === "aba-" + b.dataset.aba));
}));

function lerTema() { try { return localStorage.getItem("tema"); } catch { return null; } }
function salvarTema(t) { try { localStorage.setItem("tema", t); } catch { /* sem armazenamento */ } }
if (lerTema()) document.documentElement.dataset.theme = lerTema();
$("#tema").onclick = () => {
  const escuroAgora = getComputedStyle(document.documentElement).colorScheme.includes("dark");
  const novo = escuroAgora ? "light" : "dark";
  document.documentElement.dataset.theme = novo;
  salvarTema(novo);
};

function preencherDatalist() {
  const lista = py("listar", "avl");
  $("#lista-codigos").innerHTML = lista.map((d) => `<option value="${escapar(d.codigo)}">${escapar(d.nome)}</option>`).join("");
}

window.addEventListener("resize", () => { if (!player.tocando) ajustar(0); });

/* ------------------------------------------------------------------ Início */
(async function iniciar() {
  try {
    await iniciarPython();
    atualizarEstado(py("estado"));
    preencherDatalist();
    mostrarTipo("avl");
    const tela = $("#carregando");
    tela.classList.add("saindo");
    setTimeout(() => tela.remove(), 450);
  } catch (erro) {
    console.error(erro);
    $("#carregando-texto").textContent = "Erro ao carregar: " + erro.message;
  }
})();
