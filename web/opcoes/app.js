(function () {
  "use strict";
  // ---------------- dados e configuração ----------------
  var REPO = ["https://raw.githubusercontent.com/lucas-jesse/agrobasis-spread-milho/main/", "https://cdn.jsdelivr.net/gh/lucas-jesse/agrobasis-spread-milho@main/"];
  var LIBS = ["https://cdn.jsdelivr.net/npm/echarts@5.5.1/dist/echarts.min.js", "https://unpkg.com/echarts@5.5.1/dist/echarts.min.js"];
  var DIA = 864e5;
  var LETRA = { F: 1, G: 2, H: 3, J: 4, K: 5, M: 6, N: 7, Q: 8, U: 9, V: 10, X: 11, Z: 12 };
  var MES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
  // fator = unidades de cotação por unidade física (saca ou arroba); tam = unidades de cotação por contrato
  var ATIVOS = [
    { id: "soja", nome: "Soja", sub: "CBOT · US$/bu", bolsa: "CBOT", usd: true, un: "US$/bu", fis: "saca", fator: 60 / 27.2155, tam: 5000, vol: 18, passo: 0.10, dec: 4, fonte: "soja" },
    { id: "milho_cbot", nome: "Milho", sub: "CBOT · US$/bu", bolsa: "CBOT", usd: true, un: "US$/bu", fis: "saca", fator: 60 / 25.4012, tam: 5000, vol: 24, passo: 0.05, dec: 4, fonte: "milho" },
    { id: "trigo", nome: "Trigo", sub: "CBOT · US$/bu", bolsa: "CBOT", usd: true, un: "US$/bu", fis: "saca", fator: 60 / 27.2155, tam: 5000, vol: 28, passo: 0.05, dec: 4, fonte: "trigo" },
    { id: "milho_b3", nome: "Milho", sub: "B3 · R$/saca", bolsa: "B3", usd: false, un: "R$/sc", fis: "saca", fator: 1, tam: 450, vol: 25, passo: 0.5, dec: 2, fonte: "ccm" },
    { id: "boi", nome: "Boi gordo", sub: "B3 · R$/@", bolsa: "B3", usd: false, un: "R$/@", fis: "arroba", fator: 1, tam: 330, vol: 15, passo: 1, dec: 2, fonte: null },
    { id: "cafe", nome: "Café arábica", sub: "B3 · US$/saca", bolsa: "B3", usd: true, un: "US$/sc", fis: "saca", fator: 1, tam: 100, vol: 35, passo: 5, dec: 2, fonte: null }
  ];
  var TIPOS = { cp: ["Compra de put", 1, "p"], vp: ["Venda de put", -1, "p"], cc: ["Compra de call", 1, "c"], vc: ["Venda de call", -1, "c"] };
  var ESTR = [
    { id: "put", nome: "Put de proteção", d: "Garante um preço mínimo e mantém a alta", pernas: [["cp", 1]] },
    { id: "collar", nome: "Collar", d: "Piso pago com a venda de uma call: custo menor, alta limitada", pernas: [["cp", 0.95], ["vc", 1.07]] },
    { id: "putspread", nome: "Put spread", d: "Proteção mais barata, válida até um limite de queda", pernas: [["cp", 1], ["vp", 0.9]] },
    { id: "call", nome: "Call de proteção", d: "Para quem compra: garante um preço máximo", pernas: [["cc", 1]] },
    { id: "travaalta", nome: "Trava de alta", d: "Ganha com a alta até um limite, custo menor", pernas: [["cc", 1], ["vc", 1.1]] },
    { id: "straddle", nome: "Straddle", d: "Aposta em movimento forte, para qualquer lado", pernas: [["cc", 1], ["cp", 1]] }
  ];
  var GATE = { url: "https://docs.google.com/forms/d/e/1FAIpQLSdEFj2pbF7hSAq-DSDvFjIHa73OV7rh46ao84jJJCmX-nsqfw/formResponse", nome: "entry.761004068", cidade: "entry.721602119", tel: "entry.1189307774", prof: "entry.1630365227", chave: "agrobasis_simulador_opcoes_acesso_liberado" };

  var D = {}, A = ATIVOS[0], CONTRATOS = [], st = { estr: "put", un: "saca", legs: [], liberado: false, mostrar: false }, charts = [];
  var $ = function (id) { return document.getElementById(id); };

  // ---------------- formatação ----------------
  function num(s) {
    if (typeof s !== "string") return NaN; s = s.trim().replace(/\s|R\$|US\$|%/g, ""); if (!s) return NaN;
    if (s.indexOf(",") >= 0) return parseFloat(s.replace(/\./g, "").replace(",", "."));
    if (/^-?\d{1,3}(\.\d{3})+$/.test(s)) return parseFloat(s.replace(/\./g, ""));
    return parseFloat(s);
  }
  function br(v, c) { return v == null || !isFinite(v) ? "-" : v.toLocaleString("pt-BR", { minimumFractionDigits: c, maximumFractionDigits: c }); }
  function brIn(v, c) { return isFinite(v) ? br(v, c).replace(/\./g, "") : ""; }
  function dataBR(d) { return ("0" + d.getUTCDate()).slice(-2) + "/" + ("0" + (d.getUTCMonth() + 1)).slice(-2) + "/" + d.getUTCFullYear(); }
  function isoD(d) { return d.toISOString().slice(0, 10); }
  function sinal(v, c) { return (v > 0 ? "+" : v < 0 ? "−" : "") + br(Math.abs(v), c); }
  function mobile() { return window.innerWidth < 560; }

  // ---------------- datas de vencimento ----------------
  function feriadoUS(d) { var m = d.getUTCMonth() + 1, dd = d.getUTCDate(), wd = d.getUTCDay(); if ((m === 1 && dd === 1) || (m === 7 && dd === 4) || (m === 12 && dd === 25) || (m === 6 && dd === 19)) return true; if (m === 11 && wd === 4 && dd >= 22 && dd <= 28) return true; return false; }
  function util(d, fer) { var wd = d.getUTCDay(); return wd !== 0 && wd !== 6 && !(fer && fer(d)); }
  // CBOT (opções padrão): última sexta-feira que antecede, em pelo menos 2 dias úteis, o último dia útil do mês anterior ao do contrato
  function vencOpcaoCBOT(ano, mes) {
    var d = new Date(Date.UTC(ano, mes - 1, 0));
    while (!util(d, feriadoUS)) d = new Date(d - DIA);
    for (var k = 0; k < 2;) { d = new Date(d - DIA); if (util(d, feriadoUS)) k++; }
    while (d.getUTCDay() !== 5) d = new Date(d - DIA);
    while (!util(d, feriadoUS)) d = new Date(d - DIA);
    return d;
  }
  // B3 (milho, boi): dia 15 do mês de vencimento, ou o dia útil seguinte
  function vencB3(ano, mes) { var d = new Date(Date.UTC(ano, mes - 1, 15)); while (!util(d)) d = new Date(d.getTime() + DIA); return d; }
  function rotulo(ano, mes) { return MES[mes - 1].replace(/^./, function (c) { return c.toUpperCase(); }) + "/" + String(ano).slice(-2); }

  function montarContratos() {
    var hoje = Date.now(), out = [];
    function add(cod, F) { var l = cod.charAt(cod.length - 3), ano = 2000 + +cod.slice(-2), mes = LETRA[l]; var v = A.bolsa === "CBOT" ? vencOpcaoCBOT(ano, mes) : vencB3(ano, mes); if (v.getTime() > hoje) out.push({ cod: cod, rot: rotulo(ano, mes), F: F, venc: v }); }
    if (A.fonte === "soja" && D.soja) Object.keys(D.soja.cbot).forEach(function (k) { add(k, D.soja.cbot[k].cents_bu / 100); });
    if ((A.fonte === "milho" || A.fonte === "trigo") && D.manha) ((D.manha.cbot[A.fonte] || {}).contratos || []).forEach(function (c) { add(c.contrato, (c.preco || c.ajuste_anterior) / 100); });
    if (A.fonte === "ccm" && D.ccm) Object.keys(D.ccm.curva).forEach(function (k) { add(k, D.ccm.curva[k]); });
    out.sort(function (a, b) { return a.venc - b.venc; });
    CONTRATOS = out;
    var sel = $("sopContrato"); sel.innerHTML = "";
    out.forEach(function (c, i) { sel.appendChild(new Option(c.rot + " · " + c.cod + " · opção vence " + dataBR(c.venc), i)); });
    sel.appendChild(new Option("Outro vencimento (digitar)", "m"));
    sel.value = out.length ? (out.length > 1 && (out[0].venc - hoje) < 20 * DIA ? 1 : 0) : "m";
  }

  function dolarEm(t) {
    if (!D.soja || !D.soja.dolar) return ultimaPtax();
    var p = Object.keys(D.soja.dolar).map(function (k) { return [Date.parse(D.soja.dolar[k].vencimento + "T00:00:00Z"), D.soja.dolar[k].brl]; }).sort(function (a, b) { return a[0] - b[0]; });
    if (!p.length) return ultimaPtax();
    if (t <= p[0][0]) return p[0][1];
    for (var i = 1; i < p.length; i++) if (t <= p[i][0]) return p[i - 1][1] + (p[i][1] - p[i - 1][1]) * (t - p[i - 1][0]) / (p[i][0] - p[i - 1][0]);
    return p[p.length - 1][1];
  }
  function ultimaPtax() { var v = D.cambio && D.cambio.ptax && D.cambio.ptax.valores; return v && v.length ? v[v.length - 1] : 5.5; }

  // ---------------- Black-76 ----------------
  function N(x) { var t = 1 / (1 + 0.2316419 * Math.abs(x)), d = 0.3989422804014327 * Math.exp(-x * x / 2); var p = d * t * (0.319381530 + t * (-0.356563782 + t * (1.781477937 + t * (-1.821255978 + t * 1.330274429)))); return x >= 0 ? 1 - p : p; }
  function phi(x) { return 0.3989422804014327 * Math.exp(-x * x / 2); }
  function b76(F, K, s, T, r, tipo) {
    if (T <= 0 || s <= 0) { var iv = tipo === "c" ? Math.max(F - K, 0) : Math.max(K - F, 0); return { v: iv, d: tipo === "c" ? (F > K ? 1 : 0) : (F < K ? -1 : 0), g: 0, th: 0, ve: 0 }; }
    var sq = Math.sqrt(T), d1 = (Math.log(F / K) + s * s * T / 2) / (s * sq), d2 = d1 - s * sq, df = Math.exp(-r * T);
    var v = tipo === "c" ? df * (F * N(d1) - K * N(d2)) : df * (K * N(-d2) - F * N(-d1));
    return { v: v, d: tipo === "c" ? df * N(d1) : -df * N(-d1), g: df * phi(d1) / (F * s * sq), ve: df * F * phi(d1) * sq / 100, th: (-F * df * phi(d1) * s / (2 * sq) + r * v) / 365 };
  }
  // volatilidade implícita por bisseção a partir do prêmio de mercado
  function volImp(P, F, K, T, r, tipo) {
    var lo = 0.005, hi = 3, intr = Math.exp(-r * T) * (tipo === "c" ? Math.max(F - K, 0) : Math.max(K - F, 0));
    if (!(P > intr) || T <= 0) return null;
    for (var i = 0; i < 80; i++) { var m = (lo + hi) / 2; if (b76(F, K, m, T, r, tipo).v > P) hi = m; else lo = m; }
    return (lo + hi) / 2;
  }

  // ---------------- leitura das entradas ----------------
  function entradas() {
    var F = num($("sopF").value), v = $("sopVenc").value ? Date.parse($("sopVenc").value + "T00:00:00Z") : NaN;
    var hoje = Date.UTC(new Date().getFullYear(), new Date().getMonth(), new Date().getDate());
    return { F: F, T: isFinite(v) ? Math.max(0, (v - hoje) / DIA / 365) : NaN, dias: isFinite(v) ? Math.round((v - hoje) / DIA) : NaN, r: num($("sopR").value) / 100, fx: A.usd ? num($("sopFx").value) : 1, vol: num($("sopVol").value) };
  }
  function contratosSugeridos(vol) { var porC = A.tam / A.fator; return Math.max(1, Math.round(vol / porC)); }
  function arred(x) { var p = A.passo; return +(Math.round(x / p) * p).toFixed(4); }

  // ---------------- pernas ----------------
  function aplicarEstrategia(id) {
    st.estr = id; var e = ESTR.filter(function (x) { return x.id === id; })[0], E = entradas();
    var n = isFinite(E.vol) && E.vol > 0 ? contratosSugeridos(E.vol) : 1;
    st.legs = e.pernas.map(function (p) { return { tipo: p[0], K: isFinite(E.F) ? arred(E.F * p[1]) : NaN, vol: A.vol, n: n, pm: NaN }; });
    $("sopEstr").querySelectorAll(".sop-e").forEach(function (b) { b.setAttribute("aria-pressed", String(b.dataset.e === id)); });
    desenharPernas(); atualizar();
  }
  function desenharPernas() {
    var dec = A.usd && A.bolsa === "CBOT" ? 2 : A.dec;
    $("sopLegs").innerHTML = st.legs.map(function (l, i) {
      var opts = Object.keys(TIPOS).map(function (k) { return '<option value="' + k + '"' + (k === l.tipo ? " selected" : "") + ">" + TIPOS[k][0] + "</option>"; }).join("");
      return '<div class="sop-leg" data-i="' + i + '">' +
        '<div class="sop-tipo"><label>Operação</label><select data-k="tipo">' + opts + "</select></div>" +
        '<div><label>Strike ' + A.un + '</label><input data-k="K" inputmode="decimal" value="' + brIn(l.K, dec) + '"></div>' +
        '<div><label>Volatilidade %</label><input data-k="vol" inputmode="decimal" value="' + brIn(l.vol, 1) + '"></div>' +
        '<div><label>Contratos</label><input data-k="n" inputmode="numeric" value="' + l.n + '"></div>' +
        '<div><label>Prêmio de mercado</label><input data-k="pm" inputmode="decimal" placeholder="opcional" value="' + (isFinite(l.pm) ? brIn(l.pm, A.bolsa === "CBOT" ? 4 : A.dec) : "") + '"></div>' +
        '<div class="sop-out" id="sopOut' + i + '"></div>' +
        '<button type="button" class="sop-del" data-del="' + i + '" aria-label="Remover perna"><i data-lucide="x"></i></button></div>';
    }).join("");
    $("sopAdd").disabled = st.legs.length >= 4;
    if (window.lucide) lucide.createIcons();
  }

  // cálculo completo da posição
  function calcular() {
    var E = entradas();
    if (!(E.F > 0) || !isFinite(E.T) || !isFinite(E.r) || !(E.fx > 0) || !st.legs.length) return null;
    var nBase = 0, legs = [];
    for (var i = 0; i < st.legs.length; i++) {
      var l = st.legs[i], tp = TIPOS[l.tipo]; if (!(l.K > 0) || !(l.n > 0)) return null;
      var iv = isFinite(l.pm) && l.pm > 0 ? volImp(l.pm, E.F, l.K, E.T, E.r, tp[2]) : null;
      var s = iv || l.vol / 100, g = b76(E.F, l.K, s, E.T, E.r, tp[2]);
      var prem = isFinite(l.pm) && l.pm > 0 ? l.pm : g.v;
      legs.push({ tipo: l.tipo, c: tp[2], sg: tp[1], K: l.K, n: l.n, s: s, iv: iv, teor: b76(E.F, l.K, l.vol / 100, E.T, E.r, tp[2]).v, prem: prem, g: g });
      nBase = Math.max(nBase, l.n);
    }
    var custoU = legs.reduce(function (a, l) { return a + l.sg * l.n * l.prem; }, 0) / nBase; // por unidade de cotação, positivo = paga
    var conv = A.fator * E.fx; // unidade de cotação -> R$ por unidade física
    function payoff(FT) { return legs.reduce(function (a, l) { return a + l.sg * l.n * (l.c === "c" ? Math.max(FT - l.K, 0) : Math.max(l.K - FT, 0)); }, 0) / nBase - custoU; }
    function hoje(FT) { return legs.reduce(function (a, l) { return a + l.sg * l.n * b76(FT, l.K, l.s, E.T, E.r, l.c).v; }, 0) / nBase - custoU; }
    var lado = legs.some(function (l) { return l.tipo === "cp"; }) ? "vende" : legs.some(function (l) { return l.tipo === "cc"; }) ? "compra" : null;
    if (st.estr === "straddle" || st.estr === "travaalta") lado = null; // estratégias de posição, sem lado de proteção
    function efetivo(FT) { return lado === "compra" ? FT - payoff(FT) : FT + payoff(FT); }
    // malha de preços para pontos de equilíbrio, piso e teto
    var lo = E.F * 0.4, hi = E.F * 1.8, pts = 400, grid = [];
    for (var k = 0; k <= pts; k++) grid.push(lo + (hi - lo) * k / pts);
    var be = [];
    for (k = 1; k < grid.length; k++) { var a = payoff(grid[k - 1]), b = payoff(grid[k]); if ((a < 0 && b >= 0) || (a > 0 && b <= 0)) be.push(grid[k - 1] + (grid[k] - grid[k - 1]) * Math.abs(a) / (Math.abs(a) + Math.abs(b))); }
    var piso = null, teto = null;
    if (lado) {
      var e0 = efetivo(grid[0]), e1 = efetivo(grid[1]), eN = efetivo(grid[pts]), eM = efetivo(grid[pts - 1]);
      if (Math.abs(e1 - e0) < 1e-9 * E.F + 1e-9) piso = e0;
      if (Math.abs(eN - eM) < 1e-9 * E.F + 1e-9) teto = eN;
    }
    var dl = 0, gm = 0, th = 0, ve = 0;
    legs.forEach(function (l) { dl += l.sg * l.n * l.g.d; gm += l.sg * l.n * l.g.g; th += l.sg * l.n * l.g.th * A.tam; ve += l.sg * l.n * l.g.ve * A.tam; });
    var maxP = Math.max(payoff(grid[0]), payoff(grid[pts])), ganhoIlim = payoff(grid[pts]) > payoff(grid[pts - 1]) + 1e-9 || payoff(grid[0]) > payoff(grid[1]) + 1e-9;
    var perdaIlim = payoff(grid[pts]) < payoff(grid[pts - 1]) - 1e-9 || payoff(grid[0]) < payoff(grid[1]) - 1e-9;
    var minP = Math.min.apply(null, grid.map(payoff));
    return { E: E, legs: legs, nBase: nBase, custoU: custoU, conv: conv, payoff: payoff, hoje: hoje, efetivo: efetivo, lado: lado, be: be, piso: piso, teto: teto,
      totalMoeda: custoU * nBase * A.tam, dl: dl, gm: gm, th: th, ve: ve, perdaMax: perdaIlim ? null : minP, ganhoIlim: ganhoIlim, sacas: nBase * A.tam / A.fator };
  }

  // ---------------- interface: atualização ----------------
  function fmtCot(v) { return A.bolsa === "CBOT" ? "US$ " + br(v, 4) : (A.usd ? "US$ " : "R$ ") + br(v, A.dec); }
  function fmtFis(v, c) { return "R$ " + br(v, c == null ? 2 : c); } // em reais por unidade física
  function unFis() { return A.fis === "arroba" ? "/@" : "/sc"; }
  function premTxt(v) { return A.bolsa === "CBOT" ? "US$ " + br(v, 4) + "/bu <span>(" + br(v * 100, 2) + " ¢)</span>" : (A.usd ? "US$ " : "R$ ") + br(v, A.dec) + "<span>" + A.un.replace(/^R\$|^US\$/, "") + "</span>"; }

  function atualizar() {
    var E = entradas(), porC = A.tam / A.fator;
    $("sopVolHint").textContent = isFinite(E.vol) && E.vol > 0 ? "≈ " + br(E.vol / porC, 2) + " contrato(s) de " + br(porC, 0) + " " + (A.fis === "arroba" ? "arrobas" : "sacas") : " ";
    $("sopVhint").textContent = isFinite(E.dias) ? (E.dias >= 0 ? E.dias + " dias até o vencimento" : "data já passou") : " ";
    var R = calcular();
    st.legs.forEach(function (l, i) {
      var o = $("sopOut" + i); if (!o) return;
      var x = R && R.legs[i];
      if (!x) { o.innerHTML = '<span>preencha os campos</span>'; return; }
      o.innerHTML = "<b>" + premTxt(x.teor) + "</b><span>prêmio teórico" + (x.iv ? " · vol. implícita " + br(x.iv * 100, 1) + "%" : "") + "</span>";
    });
    var nLeg = st.legs.length ? Math.max.apply(null, st.legs.map(function (l) { return l.n || 0; })) : 0;
    $("sopLegHint").textContent = nLeg && isFinite(E.vol) ? "As pernas cobrem " + br(nLeg * porC, 0) + " " + (A.fis === "arroba" ? "arrobas" : "sacas") + " (" + br(nLeg * porC / E.vol * 100, 0) + "% do volume informado)." : " ";
    if (st.mostrar && st.liberado) resultado(R);
  }

  function resultado(R) {
    if (!R) { $("sopRes").style.display = "none"; return; }
    $("sopRes").style.display = "";
    var E = R.E, paga = R.custoU >= 0, cfis = R.custoU * R.conv, uf = unFis();
    // veredito em uma frase
    var est = ESTR.filter(function (x) { return x.id === st.estr; })[0], frase;
    if (R.lado === "vende" && R.piso != null) frase = "<b>Preço mínimo garantido de " + fmtFis(R.piso * R.conv) + uf + "</b>" + (A.usd ? " (" + fmtCot(R.piso) + (A.bolsa === "CBOT" ? "/bu" : "/sc") + ")" : "") + " no vencimento" + (R.teto != null ? ", com preço máximo de " + fmtFis(R.teto * R.conv) + uf : ", mantendo o ganho se o mercado subir") + ". Custo de " + (paga ? fmtFis(cfis) : "crédito de " + fmtFis(-cfis)) + uf + ".";
    else if (R.lado === "compra" && R.teto != null) frase = "<b>Preço máximo de compra de " + fmtFis(R.teto * R.conv) + uf + "</b> no vencimento, aproveitando se o mercado cair. Custo de " + fmtFis(cfis) + uf + ".";
    else frase = "<b>" + (est ? est.nome : "Estratégia") + "</b> com " + (paga ? "custo de " + fmtFis(cfis) : "crédito de " + fmtFis(-cfis)) + uf + (R.be.length ? " e ponto de equilíbrio em " + R.be.map(function (b) { return fmtCot(b); }).join(" e ") : "") + ".";
    $("sopVeredito").innerHTML = '<i data-lucide="shield-check"></i><div>' + frase + "</div>";
    // indicadores
    var k = [];
    k.push(["Custo por " + A.fis, (paga ? "" : "−") + fmtFis(Math.abs(cfis)) + "<small>" + uf + "</small>", A.bolsa === "CBOT" ? "US$ " + br(Math.abs(R.custoU), 4) + "/bu · " + br(Math.abs(R.custoU) * 100, 2) + " ¢" : (paga ? "prêmio líquido pago" : "crédito líquido recebido")]);
    var tot = R.totalMoeda * (A.usd ? E.fx : 1);
    k.push(["Custo total", (paga ? "" : "−") + "R$ " + br(Math.abs(tot), 0), (A.usd ? "US$ " + br(Math.abs(R.totalMoeda), 0) + " · " : "") + R.nBase + " contrato(s), " + br(R.sacas, 0) + " " + (A.fis === "arroba" ? "@" : "sc")]);
    if (R.lado === "vende" && R.piso != null) k.push(["Preço mínimo", fmtFis(R.piso * R.conv) + "<small>" + uf + "</small>", fmtCot(R.piso) + " no futuro, sem basis"]);
    else if (R.lado === "compra" && R.teto != null) k.push(["Preço máximo", fmtFis(R.teto * R.conv) + "<small>" + uf + "</small>", fmtCot(R.teto) + " no futuro, sem basis"]);
    else k.push(["Equilíbrio", R.be.length ? R.be.map(function (b) { return br(b, A.bolsa === "CBOT" ? 2 : A.dec); }).join(" e ") : "-", "futuro no vencimento, " + A.un]);
    if (R.lado === "vende" && R.teto != null) k.push(["Preço máximo", fmtFis(R.teto * R.conv) + "<small>" + uf + "</small>", "a alta acima do strike vendido fica com o comprador"]);
    else k.push(["Perda máxima", R.perdaMax == null ? "ilimitada" : "R$ " + br(Math.abs(R.perdaMax * R.nBase * A.tam * (A.usd ? E.fx : 1)), 0), R.perdaMax == null ? "há venda de opção descoberta" : "no vencimento, na pior hipótese"]);
    $("sopKpis").innerHTML = k.map(function (x) { return '<div class="sop-k"><span>' + x[0] + "</span><b>" + x[1] + "</b><em>" + x[2] + "</em></div>"; }).join("");
    // gregas
    var porC = A.tam / A.fator, mo = A.usd ? E.fx : 1;
    $("sopGregas").innerHTML = [
      ["Delta", sinal(R.dl, 2) + " contr.", "equivale a " + sinal(R.dl * porC, 0) + " " + (A.fis === "arroba" ? "@" : "sc") + "; quanto a posição se move com o futuro"],
      ["Gamma", sinal(R.gm, 4), "quanto o delta muda a cada 1 " + A.un.split("/")[0] + " no futuro"],
      ["Theta", (R.th < 0 ? "−" : "+") + "R$ " + br(Math.abs(R.th * mo), 0) + "/dia", "ganho ou perda por dia só pela passagem do tempo"],
      ["Vega", (R.ve < 0 ? "−" : "+") + "R$ " + br(Math.abs(R.ve * mo), 0), "por 1 ponto percentual de volatilidade"]
    ].map(function (g) { return '<div class="sop-g"><span>' + g[0] + "</span><b>" + g[1] + "</b><em>" + g[2] + "</em></div>"; }).join("");
    // cenários
    var lin = [-20, -10, -5, 0, 5, 10, 20].map(function (p) {
      var FT = E.F * (1 + p / 100), po = R.payoff(FT), ef = R.efetivo(FT);
      return "<tr" + (p === 0 ? ' class="atual"' : "") + "><td>" + (p === 0 ? "Sem mudança" : (p > 0 ? "Alta de " : "Queda de ") + Math.abs(p) + "%") + "</td><td>" + fmtCot(FT) + "</td><td class=\"" + (po >= 0 ? "pos" : "neg") + "\">" + sinal(po * R.conv, 2) + "</td><td class=\"" + (po >= 0 ? "pos" : "neg") + "\">" + sinal(po * R.nBase * A.tam * mo, 0) + "</td>" + (R.lado ? "<td>" + fmtFis(FT * R.conv) + "</td><td><b>" + fmtFis(ef * R.conv) + "</b></td>" : "") + "</tr>";
    }).join("");
    $("sopCen").innerHTML = "<thead><tr><th>Futuro no vencimento</th><th>" + A.un + "</th><th>Opções R$" + uf + "</th><th>Opções total R$</th>" + (R.lado ? "<th>Sem proteção R$" + uf + "</th><th>" + (R.lado === "compra" ? "Custo final" : "Com proteção") + " R$" + uf + "</th>" : "") + "</tr></thead><tbody>" + lin + "</tbody>";
    // unidades do gráfico
    var temNat = A.bolsa === "CBOT" || A.usd;
    $("sopUn").style.display = temNat ? "" : "none";
    $("sopUn").innerHTML = '<button data-u="saca" aria-pressed="' + (st.un === "saca") + '">R$' + uf + "</button><button data-u=\"nat\" aria-pressed=\"" + (st.un === "nat") + "\">" + A.un + "</button>";
    $("sopH1").textContent = R.lado === "compra" ? "Seu custo de compra no vencimento" : R.lado === "vende" ? "Seu preço de venda no vencimento" : "Posição no vencimento";
    charts[0].setOption(g0(R), true); charts[1].setOption(g1(R), true);
    $("sopCap0").textContent = R.lado ? "Linha cinza: o preço acompanhando o futuro, sem proteção. Linha verde: o mesmo preço somado ao resultado das opções. Não inclui basis, corretagem e custos de margem." + (A.usd ? " Conversão com dólar de R$ " + br(E.fx, 4) + "." : "") : "Estratégia sem lado de proteção definido: o gráfico mostra o resultado das opções.";
    $("sopCap1").textContent = "Resultado das opções por " + A.fis + ", já descontado o prêmio. Linha cheia: no vencimento. Tracejada: hoje, com o prazo e a volatilidade atuais.";
    if (window.lucide) lucide.createIcons();
  }

  // ---------------- gráficos ----------------
  var COR = { vd: "#1E4812", vc: "#54931B", mr: "#C0782F", cz: "#6E7B8F", tx: "#1d2420", mt: "#6b756d", ln: "#E7ECE8", grade: "rgba(29,36,32,.07)" };
  var base = { textStyle: { fontFamily: "Geist, Arial, sans-serif", color: COR.tx }, animationDuration: 350,
    tooltip: { trigger: "axis", confine: true, backgroundColor: "#fff", borderColor: COR.ln, borderWidth: 1, padding: [8, 12], textStyle: { color: COR.tx, fontSize: 12.5 }, extraCssText: "box-shadow:0 6px 20px rgba(0,0,0,.08);border-radius:10px" } };
  function marca() { return { type: "text", left: "center", top: "middle", rotation: 0.38, z: -10, silent: true, style: { text: "AgroBasis", fill: "rgba(30,72,18,0.065)", font: "700 " + (mobile() ? 44 : 64) + "px Sora, Geist, sans-serif" } }; }
  function fy(R) { return st.un === "saca" || !(A.bolsa === "CBOT" || A.usd) ? function (v) { return v * R.conv; } : function (v) { return v; }; }
  function decY() { return st.un === "saca" || !(A.bolsa === "CBOT" || A.usd) ? 2 : A.bolsa === "CBOT" ? 4 : A.dec; }
  function malha(R) { var lo = R.E.F * 0.7, hi = R.E.F * 1.3, out = []; for (var k = 0; k <= 120; k++) out.push(lo + (hi - lo) * k / 120); return out; }
  function eixoX(R) { var c = A.bolsa === "CBOT" ? 2 : A.dec; return { type: "value", min: R.E.F * 0.7, max: R.E.F * 1.3, name: "futuro no vencimento (" + A.un + ")", nameLocation: "middle", nameGap: 28, nameTextStyle: { color: COR.mt, fontSize: 11 }, axisLabel: { color: COR.mt, fontSize: 11, formatter: function (v) { return br(v, c); }, hideOverlap: true, showMinLabel: false, showMaxLabel: false }, splitLine: { show: false }, axisLine: { lineStyle: { color: COR.ln } } }; }
  function eixoY() { var d = decY(); return { type: "value", scale: true, splitNumber: 5, axisLabel: { color: COR.mt, fontSize: 11, formatter: function (v) { return br(v, d > 2 ? 2 : 0); } }, splitLine: { lineStyle: { color: COR.grade } } }; }
  function tl(m, n, v) { return '<div style="display:flex;justify-content:space-between;gap:16px"><span>' + m + n + "</span><b>" + v + "</b></div>"; }
  function txY(v) { return st.un === "saca" || !(A.bolsa === "CBOT" || A.usd) ? "R$ " + br(v, 2) + unFis() : fmtCot(v); }
  function g0(R) {
    var f = fy(R), xs = malha(R), sem = xs.map(function (x) { return [x, f(x)]; }), com = xs.map(function (x) { return [x, f(R.lado ? R.efetivo(x) : R.payoff(x))]; });
    var ml = [{ xAxis: R.E.F, lineStyle: { color: COR.cz, type: [4, 4] }, label: { formatter: "hoje " + br(R.E.F, A.bolsa === "CBOT" ? 2 : A.dec), position: "insideEndTop", color: COR.mt, fontSize: 10.5 } }];
    if (R.piso != null) ml.push({ yAxis: f(R.piso), lineStyle: { color: COR.vd, type: [6, 4] }, label: { formatter: "mínimo " + txY(f(R.piso)), position: "insideStartTop", color: COR.vd, fontWeight: 700, fontSize: 11 } });
    if (R.teto != null) ml.push({ yAxis: f(R.teto), lineStyle: { color: COR.mr, type: [6, 4] }, label: { formatter: "máximo " + txY(f(R.teto)), position: "insideStartBottom", color: COR.mr, fontWeight: 700, fontSize: 11 } });
    var series = [];
    if (R.lado) series.push({ name: "Sem proteção", type: "line", data: sem, symbol: "none", lineStyle: { width: 1.6, color: "#A9B2AB" }, itemStyle: { color: "#A9B2AB" } });
    series.push({ name: R.lado ? "Com a estratégia" : "Resultado", type: "line", data: com, symbol: "none", lineStyle: { width: 3, color: COR.vd }, itemStyle: { color: COR.vd }, z: 5, markLine: { silent: true, symbol: "none", data: ml } });
    return Object.assign({}, base, { graphic: [marca()], legend: { top: 0, left: 0, itemWidth: 14, itemHeight: 8, textStyle: { color: COR.mt, fontSize: 12 } },
      grid: { left: 6, right: 14, top: 32, bottom: 34, containLabel: true }, xAxis: eixoX(R), yAxis: eixoY(),
      tooltip: Object.assign({}, base.tooltip, { formatter: function (ps) { var h = "<b>Futuro a " + fmtCot(ps[0].value[0]) + "</b>"; ps.forEach(function (q) { h += tl(q.marker, q.seriesName, txY(q.value[1])); }); return h; } }),
      series: series });
  }
  function g1(R) {
    var f = fy(R), xs = malha(R), ven = xs.map(function (x) { return [x, f(R.payoff(x))]; }), hj = xs.map(function (x) { return [x, f(R.hoje(x))]; });
    var pos = ven.map(function (p) { return [p[0], Math.max(p[1], 0)]; }), neg = ven.map(function (p) { return [p[0], Math.min(p[1], 0)]; });
    var bes = R.be.filter(function (b) { return b >= R.E.F * 0.7 && b <= R.E.F * 1.3; }).map(function (b) { return { coord: [b, 0], value: br(b, A.bolsa === "CBOT" ? 2 : A.dec) }; });
    return Object.assign({}, base, { graphic: [marca()], legend: { top: 0, left: 0, itemWidth: 14, itemHeight: 8, textStyle: { color: COR.mt, fontSize: 12 }, data: ["No vencimento", { name: "Hoje", icon: "path://M0,3h6v2H0z M9,3h6v2H9z" }] },
      grid: { left: 6, right: 14, top: 32, bottom: 34, containLabel: true }, xAxis: eixoX(R), yAxis: eixoY(),
      tooltip: Object.assign({}, base.tooltip, { formatter: function (ps) { var h = "<b>Futuro a " + fmtCot(ps[0].value[0]) + "</b>"; ps.forEach(function (q) { if (q.seriesName.charAt(0) !== "_") h += tl(q.marker, q.seriesName, txY(q.value[1])); }); return h; } }),
      series: [
        { name: "_pos", type: "line", data: pos, symbol: "none", lineStyle: { width: 0 }, areaStyle: { color: "rgba(84,147,27,.16)" }, silent: true, tooltip: { show: false } },
        { name: "_neg", type: "line", data: neg, symbol: "none", lineStyle: { width: 0 }, areaStyle: { color: "rgba(192,120,47,.14)" }, silent: true, tooltip: { show: false } },
        { name: "Hoje", type: "line", data: hj, symbol: "none", lineStyle: { width: 1.6, color: COR.cz, type: [6, 4] }, itemStyle: { color: COR.cz } },
        { name: "No vencimento", type: "line", data: ven, symbol: "none", lineStyle: { width: 2.8, color: COR.vd }, itemStyle: { color: COR.vd }, z: 5,
          markPoint: bes.length ? { symbol: "circle", symbolSize: 9, itemStyle: { color: "#fff", borderColor: COR.vd, borderWidth: 2 }, label: { show: true, position: "top", distance: 6, color: COR.vd, fontSize: 11, fontWeight: 700, formatter: function (q) { return "equilíbrio " + q.value; } }, data: bes } : undefined,
          markLine: { silent: true, symbol: "none", data: [{ yAxis: 0, lineStyle: { color: "#b9c0bb", type: "solid", width: 1 }, label: { show: false } }, { xAxis: R.E.F, lineStyle: { color: COR.cz, type: [4, 4] }, label: { formatter: "hoje", position: "insideEndTop", color: COR.mt, fontSize: 10.5 } }] } }
      ] });
  }
  function baixar(i) {
    var R = calcular(); if (!R) return;
    var opt = [g0, g1][i](R), tit = [$("sopH1").textContent, "Resultado da estratégia"][i];
    var est = ESTR.filter(function (x) { return x.id === st.estr; })[0];
    opt.animation = false;
    opt.title = { text: tit + " · " + A.nome + " " + A.bolsa, subtext: (est ? est.nome + " · " : "") + R.legs.map(function (l) { return TIPOS[l.tipo][0].toLowerCase() + " " + br(l.K, A.bolsa === "CBOT" ? 2 : A.dec); }).join(", "), left: 8, top: 6, textStyle: { fontFamily: "Sora, Geist, sans-serif", fontSize: 15, fontWeight: 700, color: COR.vd }, subtextStyle: { color: COR.mt, fontSize: 12 } };
    opt.legend = Object.assign({}, opt.legend, { top: 54, left: 8 }); opt.grid = Object.assign({}, opt.grid, { top: 84, bottom: 50 });
    opt.graphic = [marca(), { type: "text", right: 12, bottom: 8, style: { text: "agrobasis.com.br · Simulador de Opções (Black-76)", fill: "#9aa39c", font: "11px Geist, sans-serif" } }];
    charts[i].setOption(opt, true);
    var url = charts[i].getDataURL({ type: "png", pixelRatio: 2, backgroundColor: "#fff" });
    resultado(R);
    var a = document.createElement("a"); a.href = url; a.download = "agrobasis-opcoes-" + A.id + "-" + ["preco", "resultado"][i] + ".png"; document.body.appendChild(a); a.click(); a.remove();
  }

  // ---------------- troca de ativo e contrato ----------------
  function escolherAtivo(id) {
    A = ATIVOS.filter(function (x) { return x.id === id; })[0];
    $("sopAtivos").querySelectorAll(".sop-chip").forEach(function (b) { b.setAttribute("aria-pressed", String(b.dataset.a === id)); });
    $("sopFlab").textContent = "Preço do futuro (" + A.un + ")";
    $("sopVolUn").textContent = A.fis === "arroba" ? "arrobas" : "sacas";
    $("sopFxBox").style.display = A.usd ? "" : "none";
    $("sopRlab").textContent = A.usd ? "Juros em dólar ao ano" : "Juros em real ao ano";
    var r = $("sopR"); r.value = A.usd ? "4,0" : br(D.cambio && D.cambio.selic && D.cambio.selic.meta_aa || 13.75, 2); r.dataset.auto = "1";
    $("sopRhint").textContent = A.usd ? "taxa de referência em dólar (SOFR), ajuste se quiser" : "Selic meta do Banco Central";
    $("sopVol").value = A.fis === "arroba" ? "1.000" : A.bolsa === "CBOT" ? brIn(Math.round(A.tam / A.fator * 2 / 100) * 100, 0) : "5.000";
    montarContratos(); escolherContrato();
  }
  function escolherContrato() {
    var v = $("sopContrato").value, c = v === "m" ? null : CONTRATOS[+v];
    var dec = A.bolsa === "CBOT" ? 4 : A.dec;
    if (c) {
      $("sopF").value = brIn(c.F, dec); $("sopF").dataset.auto = "1";
      $("sopVenc").value = isoD(c.venc); $("sopVenc").dataset.auto = "1";
      var fonte = A.fonte === "soja" ? D.soja && D.soja.atualizado_em : A.fonte === "ccm" ? D.ccm && D.ccm.atualizado_em : D.manha && D.manha.gerado_em_brt;
      $("sopFhint").textContent = "fechamento" + (fonte ? " de " + String(fonte).slice(0, 10).replace(/(\d{4})-(\d\d)-(\d\d)/, "$3/$2/$1") : "") + ", pode editar";
      $("sopVhint").textContent = "";
    } else {
      $("sopF").dataset.auto = "0"; $("sopVenc").dataset.auto = "0";
      if (!$("sopVenc").value) $("sopVenc").value = isoD(new Date(Date.now() + 90 * DIA));
      $("sopFhint").textContent = "digite o preço do futuro";
    }
    if (A.usd) {
      var t = Date.parse($("sopVenc").value + "T00:00:00Z"), fx = A.bolsa === "CBOT" || A.id === "cafe" ? dolarEm(t) : ultimaPtax();
      $("sopFx").value = brIn(fx, 4); $("sopFx").dataset.auto = "1";
      $("sopFxHint").textContent = "dólar futuro da B3 na data, pode editar";
    }
    aplicarEstrategia(st.estr);
  }

  // ---------------- cadastro ----------------
  function liberar() { st.liberado = true; st.mostrar = true; $("sopGate").style.display = "none"; atualizar(); charts.forEach(function (c) { c.resize(); }); atualizar(); $("sopRes").scrollIntoView({ behavior: "smooth", block: "start" }); }
  function enviarGate() {
    var n = $("sopGNome").value.trim(), c = $("sopGCid").value.trim(), t = $("sopGTel").value.trim(), p = $("sopGProf").value.trim(), ok = $("sopGOk").checked, er = $("sopGateErr");
    if (!n || !c || !t || !p || !ok) { er.textContent = !ok && n && c && t && p ? "É necessário aceitar o uso dos dados para continuar." : "Preencha todos os campos e aceite o uso dos dados para continuar."; er.style.display = "block"; return; }
    er.style.display = "none"; $("sopGBtn").disabled = true; $("sopGSt").style.display = "block";
    var b = new URLSearchParams(); b.append(GATE.nome, n); b.append(GATE.cidade, c); b.append(GATE.tel, t); b.append(GATE.prof, p);
    fetch(GATE.url, { method: "POST", mode: "no-cors", headers: { "Content-Type": "application/x-www-form-urlencoded" }, body: b.toString() })
      .then(function () { try { localStorage.setItem(GATE.chave, "1"); } catch (e) {} $("sopGSt").textContent = "Pronto!"; setTimeout(liberar, 300); })
      .catch(function () { $("sopGBtn").disabled = false; $("sopGSt").style.display = "none"; er.textContent = "Não foi possível enviar seus dados agora. Tente novamente em instantes."; er.style.display = "block"; });
  }
  function verResultado() {
    if (!calcular()) { $("sopLegHint").textContent = "Preencha o preço do futuro, o vencimento e as pernas para ver o resultado."; return; }
    if (st.liberado) { liberar(); return; }
    $("sopGate").style.display = ""; $("sopGate").scrollIntoView({ behavior: "smooth", block: "start" });
  }

  // ---------------- carga ----------------
  function json(c, i) { i = i || 0; return fetch(REPO[i] + c + "?v=" + Math.floor(Date.now() / 18e5), { cache: "no-store" }).then(function (r) { if (!r.ok) throw 0; return r.json(); }).catch(function () { return i + 1 < REPO.length ? json(c, i + 1) : null; }); }
  function lib(i) { i = i || 0; return new Promise(function (ok, nok) { if (window.echarts) return ok(); var s = document.createElement("script"); s.src = LIBS[i]; s.onload = ok; s.onerror = function () { i + 1 < LIBS.length ? lib(i + 1).then(ok, nok) : nok(); }; document.head.appendChild(s); }); }

  function iniciar() {
    try { st.liberado = localStorage.getItem(GATE.chave) === "1"; } catch (e) {}
    $("sopAtivos").innerHTML = ATIVOS.map(function (a) { return '<button type="button" class="sop-chip" data-a="' + a.id + '">' + a.nome + "<small>" + a.sub + "</small></button>"; }).join("");
    $("sopEstr").innerHTML = ESTR.map(function (e) { return '<button type="button" class="sop-e" data-e="' + e.id + '"><b>' + e.nome + "</b><span>" + e.d + "</span></button>"; }).join("");
    charts = [echarts.init($("sopG0")), echarts.init($("sopG1"))];
    $("sopAtivos").addEventListener("click", function (e) { var b = e.target.closest(".sop-chip"); if (b) escolherAtivo(b.dataset.a); });
    $("sopEstr").addEventListener("click", function (e) { var b = e.target.closest(".sop-e"); if (b) aplicarEstrategia(b.dataset.e); });
    $("sopContrato").addEventListener("change", escolherContrato);
    ["sopF", "sopVenc", "sopR", "sopFx", "sopVol"].forEach(function (id) { $(id).addEventListener("input", function () { this.dataset.auto = "0"; atualizar(); }); });
    $("sopVenc").addEventListener("change", function () { if (A.usd && $("sopFx").dataset.auto === "1") { $("sopFx").value = brIn(dolarEm(Date.parse(this.value + "T00:00:00Z")), 4); } atualizar(); });
    $("sopVol").addEventListener("change", function () { var E = entradas(); if (E.vol > 0) { var n = contratosSugeridos(E.vol); st.legs.forEach(function (l) { l.n = n; }); desenharPernas(); atualizar(); } });
    $("sopLegs").addEventListener("input", function (e) { var el = e.target, row = el.closest(".sop-leg"); if (!row) return; var l = st.legs[+row.dataset.i], k = el.dataset.k; l[k] = k === "tipo" ? el.value : k === "n" ? Math.max(0, Math.round(num(el.value))) : num(el.value); atualizar(); });
    $("sopLegs").addEventListener("change", function (e) { if (e.target.dataset.k === "tipo") { st.estr = "livre"; $("sopEstr").querySelectorAll(".sop-e").forEach(function (b) { b.setAttribute("aria-pressed", "false"); }); atualizar(); } });
    $("sopLegs").addEventListener("click", function (e) { var b = e.target.closest("[data-del]"); if (!b) return; st.legs.splice(+b.dataset.del, 1); st.estr = "livre"; $("sopEstr").querySelectorAll(".sop-e").forEach(function (x) { x.setAttribute("aria-pressed", "false"); }); desenharPernas(); atualizar(); });
    $("sopAdd").addEventListener("click", function () { if (st.legs.length >= 4) return; var E = entradas(); st.legs.push({ tipo: "cp", K: isFinite(E.F) ? arred(E.F) : NaN, vol: A.vol, n: st.legs[0] ? st.legs[0].n : 1, pm: NaN }); st.estr = "livre"; $("sopEstr").querySelectorAll(".sop-e").forEach(function (x) { x.setAttribute("aria-pressed", "false"); }); desenharPernas(); atualizar(); });
    $("sopUn").addEventListener("click", function (e) { var b = e.target.closest("button"); if (!b) return; st.un = b.dataset.u; atualizar(); });
    $("sopVer").addEventListener("click", verResultado);
    $("sopGBtn").addEventListener("click", enviarGate);
    document.querySelectorAll("#abp-ferramenta .sop-dl").forEach(function (b) { b.addEventListener("click", function () { baixar(+b.dataset.dl); }); });
    var to; window.addEventListener("resize", function () { clearTimeout(to); to = setTimeout(function () { charts.forEach(function (c) { c.resize(); }); if (st.mostrar && st.liberado) atualizar(); }, 150); });
    var datas = [D.soja && D.soja.atualizado_em, D.ccm && D.ccm.atualizado_em].filter(Boolean);
    $("sopAtu").textContent = datas.length ? "Preços de fechamento: CBOT " + (D.soja ? D.soja.atualizado_em.slice(0, 10) : "-") + " · B3 " + (D.ccm ? D.ccm.atualizado_em.slice(0, 10) : "-") : "";
    escolherAtivo("soja");
    if (window.lucide) lucide.createIcons(); else window.addEventListener("load", function () { window.lucide && lucide.createIcons(); });
  }

  Promise.all([lib(), json("dados/curva_soja.json"), json("dados/curva_ccm.json"), json("dados/manha.json"), json("dados/cambio.json")]).then(function (r) {
    D = { soja: r[1], ccm: r[2], manha: r[3], cambio: r[4] }; iniciar();
  }).catch(function () { D = {}; if (window.echarts) iniciar(); else $("abp-ferramenta").insertAdjacentHTML("afterbegin", '<p class="sop-hint">Não foi possível carregar os gráficos agora. Recarregue a página.</p>'); });
})();
