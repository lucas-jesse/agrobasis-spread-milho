(function () {
  "use strict";
  var REPO = ["https://raw.githubusercontent.com/lucas-jesse/agrobasis-spread-milho/main/", "https://cdn.jsdelivr.net/gh/lucas-jesse/agrobasis-spread-milho@main/"];
  var LIBS = ["https://cdn.jsdelivr.net/npm/echarts@5.5.1/dist/echarts.min.js", "https://unpkg.com/echarts@5.5.1/dist/echarts.min.js"];
  var COR = { vd: "#1E4812", vc: "#54931B", mr: "#C0782F", cz: "#6E7B8F", tx: "#1d2420", mt: "#6b756d", ln: "#E7ECE8", grade: "rgba(29,36,32,.07)" };
  var CATS = [["Muito ruim", "#8A3B2A"], ["Ruim", "#C0782F"], ["Regular", "#CFC7A3"], ["Boa", "#7FAE68"], ["Excelente", "#1E4812"]];
  var ORDEM = ["Plantio", "Emergência", "Elongação", "Embonecamento", "Floração", "Espigamento", "Formação de vagens", "Grão pastoso", "Grão dentado", "Queda de folhas", "Maturação", "Colheita"];
  var MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
  var DIA = 864e5, $ = function (id) { return document.getElementById(id); };
  var D, C, st = { cult: "milho", etapa: null }, charts = [];

  function br(v, c) { return v == null || !isFinite(v) ? "-" : v.toLocaleString("pt-BR", { minimumFractionDigits: c || 0, maximumFractionDigits: c || 0 }); }
  function pp(v) { return v == null || !isFinite(v) ? "-" : (v > 0 ? "+" : v < 0 ? "−" : "") + br(Math.abs(v), 0) + " p.p."; }
  function mobile() { return window.innerWidth < 560; }
  function marca() { return { type: "text", left: "center", top: "middle", rotation: 0.38, z: -10, silent: true, style: { text: "AgroBasis", fill: "rgba(30,72,18,0.065)", font: "700 " + (mobile() ? 44 : 72) + "px Sora, Geist, sans-serif" } }; }
  // posição no ano-calendário (ano fictício 2001), para sobrepor safras
  function doy(iso) { var d = new Date(iso + "T00:00:00Z"); return Date.UTC(2001, d.getUTCMonth(), d.getUTCDate()); }
  function dataBR(iso) { return iso.slice(8, 10) + "/" + iso.slice(5, 7); }
  function dataBRc(iso) { return dataBR(iso) + "/" + iso.slice(0, 4); }
  function ge(r) { return r[4] + r[5]; }
  function cci(r) { return (r[1] * 1 + r[2] * 2 + r[3] * 3 + r[4] * 4 + r[5] * 5) / 100; }
  function media(a) { var v = a.filter(function (x) { return x != null; }); return v.length ? v.reduce(function (s, x) { return s + x; }, 0) / v.length : null; }
  function anos() { var u = +C.ultimoAno; return [u - 5, u - 4, u - 3, u - 2, u - 1].map(String); }

  // valor de uma série [[iso, v]] no dia do ano t, por interpolação; extrapola 0 antes e 100 depois quando faz sentido
  function emProg(serie, t) {
    if (!serie || !serie.length) return null;
    var p = serie.map(function (x) { return [doy(x[0]), x[1]]; });
    if (t < p[0][0]) return p[0][1] <= 15 && p[0][0] - t < 60 * DIA ? 0 : null;
    if (t > p[p.length - 1][0]) return p[p.length - 1][1] >= 85 ? 100 : null;
    for (var i = 1; i < p.length; i++) if (t <= p[i][0]) return p[i - 1][1] + (p[i][1] - p[i - 1][1]) * (t - p[i - 1][0]) / (p[i][0] - p[i - 1][0]);
    return p[p.length - 1][1];
  }
  // condição mais próxima do dia t (até 4 dias de distância)
  // fimSafra: se a data pedida passou do fim das avaliações daquele ano, devolve a última avaliação da safra
  function emCond(lista, t, fimSafra) {
    var best = null, dd = 8 * DIA; (lista || []).forEach(function (r) { var k = Math.abs(doy(r[0]) - t); if (k < dd) { dd = k; best = r; } });
    if (!best && fimSafra && lista && lista.length) { var u = lista[lista.length - 1]; if (t > doy(u[0]) && t - doy(u[0]) < 60 * DIA) best = u; }
    return best;
  }

  var base = { textStyle: { fontFamily: "Geist, system-ui, sans-serif", color: COR.tx }, animationDuration: 450,
    tooltip: { confine: true, backgroundColor: "#fff", borderColor: COR.ln, borderWidth: 1, padding: [8, 12], textStyle: { color: COR.tx, fontSize: 12.5 }, extraCssText: "box-shadow:0 6px 20px rgba(0,0,0,.08);border-radius:10px" } };
  function legenda(x) { return Object.assign({ type: "scroll", top: 0, left: 0, right: 0, itemWidth: 14, itemHeight: 8, itemGap: 12, textStyle: { color: COR.mt, fontSize: 12 } }, x || {}); }
  function tl(m, n, v) { return '<div style="display:flex;justify-content:space-between;gap:16px"><span>' + m + n + "</span><b>" + v + "</b></div>"; }
  function eixoT(min, max) { return { type: "time", min: min, max: max, minInterval: 28 * DIA, axisLabel: { color: COR.mt, fontSize: 11, hideOverlap: true, formatter: function (v) { return MESES[new Date(v).getUTCMonth()]; } }, splitNumber: 6, axisLine: { lineStyle: { color: COR.ln } }, axisTick: { show: false }, splitLine: { show: false } }; }
  function eixoPct(extra) { return Object.assign({ type: "value", min: 0, max: 100, interval: 25, axisLabel: { color: COR.mt, fontSize: 11.5, formatter: "{value}%" }, splitLine: { lineStyle: { color: COR.grade } } }, extra || {}); }
  function faixa(lo, hi, cor) { return { name: "Faixa 5 anos", type: "custom", silent: true, z: 1, data: [0], itemStyle: { color: cor }, tooltip: { show: false }, renderItem: function (p, api) { var pts = hi.map(function (q) { return api.coord(q); }).concat(lo.slice().reverse().map(function (q) { return api.coord(q); })); return { type: "polygon", shape: { points: pts }, style: { fill: cor } }; } }; }
  var TRACO = "path://M0,3h6v2H0z M9,3h6v2H9z";

  // estatística dos 5 anos anteriores numa grade semanal
  function grade(fn, t0, t1) { var out = { lo: [], hi: [], md: [] }; for (var t = t0; t <= t1; t += 7 * DIA) { var v = anos().map(function (a) { return fn(a, t); }).filter(function (x) { return x != null; }); if (v.length >= 3) { out.lo.push([t, Math.min.apply(null, v)]); out.hi.push([t, Math.max.apply(null, v)]); out.md.push([t, media(v)]); } } return out; }
  function janela(series) { var ts = []; series.forEach(function (s) { (s || []).forEach(function (x) { ts.push(doy(x[0])); }); }); if (!ts.length) return [Date.UTC(2001, 0, 1), Date.UTC(2001, 11, 31)]; return [Math.min.apply(null, ts) - 7 * DIA, Math.max.apply(null, ts) + 7 * DIA]; }

  // 0) avanço da etapa: ano atual x ano passado x média e faixa de 5 anos
  function g0() {
    var P = C.progresso[st.etapa] || {}, u = C.ultimoAno, a1 = String(+u - 1);
    var w = janela(anos().concat([u]).map(function (a) { return P[a]; }));
    var g = grade(function (a, t) { return emProg(P[a], t); }, w[0], w[1]);
    var cur = (P[u] || []).map(function (x) { return [doy(x[0]), x[1], x[0]]; }), ant = (P[a1] || []).map(function (x) { return [doy(x[0]), x[1], x[0]]; });
    var nm = "Média " + anos()[0] + "-" + anos()[4];
    return Object.assign({}, base, { graphic: [marca()], legend: legenda({ data: [u, a1, { name: nm, icon: TRACO }, { name: "Faixa 5 anos", icon: "rect" }] }),
      grid: { left: 6, right: mobile() ? 12 : 44, top: 34, bottom: 6, containLabel: true }, xAxis: eixoT(w[0], w[1]), yAxis: eixoPct(),
      tooltip: Object.assign({}, base.tooltip, { trigger: "axis", formatter: function (ps) { var t = ps[0].value[0], d = new Date(t), h = '<div style="font-weight:600;margin-bottom:4px">' + st.etapa + " · " + ("0" + d.getUTCDate()).slice(-2) + "/" + MESES[d.getUTCMonth()] + "</div>"; ps.forEach(function (q) { if (q.seriesName !== "Faixa 5 anos" && q.value[1] != null) h += tl(q.marker, q.seriesName, br(q.value[1], 0) + "%"); }); return h; } }),
      series: [faixa(g.lo, g.hi, "rgba(84,147,27,.12)"),
        { name: nm, type: "line", data: g.md, symbol: "none", smooth: 0.2, lineStyle: { width: 1.8, color: COR.mr, type: [6, 4] }, itemStyle: { color: COR.mr } },
        { name: a1, type: "line", data: ant, symbol: "circle", symbolSize: 4, lineStyle: { width: 1.8, color: COR.cz }, itemStyle: { color: COR.cz } },
        { name: u, type: "line", data: cur, symbol: "circle", symbolSize: 7, lineStyle: { width: 3, color: COR.vd }, itemStyle: { color: COR.vd, borderColor: "#fff", borderWidth: 1.5 }, z: 5,
          endLabel: { show: !mobile() && cur.length > 0, formatter: function (q) { return br(q.value[1], 0) + "%"; }, color: COR.vd, fontWeight: 700, fontSize: 12 } }] });
  }

  // 1) boa + excelente: ano atual x ano passado x média e faixa
  function g1() {
    var K = C.condicao, u = C.ultimoAno, a1 = String(+u - 1);
    var w = janela(anos().concat([u]).map(function (a) { return (K[a] || []).map(function (r) { return [r[0], 0]; }); }));
    var g = grade(function (a, t) { var r = emCond(K[a], t); return r ? ge(r) : null; }, w[0], w[1]);
    var cur = (K[u] || []).map(function (r) { return [doy(r[0]), ge(r)]; }), ant = (K[a1] || []).map(function (r) { return [doy(r[0]), ge(r)]; });
    var nm = "Média " + anos()[0] + "-" + anos()[4];
    var vals = cur.concat(ant).map(function (x) { return x[1]; }).concat(g.lo.map(function (x) { return x[1]; })).concat(g.hi.map(function (x) { return x[1]; }));
    var mn = vals.length ? Math.max(0, Math.floor((Math.min.apply(null, vals) - 5) / 10) * 10) : 0, mx = vals.length ? Math.min(100, Math.ceil((Math.max.apply(null, vals) + 5) / 10) * 10) : 100;
    return Object.assign({}, base, { graphic: [marca()], legend: legenda({ data: [u, a1, { name: nm, icon: TRACO }, { name: "Faixa 5 anos", icon: "rect" }] }),
      grid: { left: 6, right: mobile() ? 12 : 40, top: 34, bottom: 6, containLabel: true }, xAxis: eixoT(w[0], w[1]), yAxis: eixoPct({ min: mn, max: mx, interval: null, splitNumber: 4 }),
      tooltip: Object.assign({}, base.tooltip, { trigger: "axis", formatter: function (ps) { var d = new Date(ps[0].value[0]), h = '<div style="font-weight:600;margin-bottom:4px">Boa ou excelente · ' + ("0" + d.getUTCDate()).slice(-2) + "/" + MESES[d.getUTCMonth()] + "</div>"; ps.forEach(function (q) { if (q.seriesName !== "Faixa 5 anos" && q.value[1] != null) h += tl(q.marker, q.seriesName, br(q.value[1], 0) + "%"); }); return h; } }),
      series: [faixa(g.lo, g.hi, "rgba(84,147,27,.12)"),
        { name: nm, type: "line", data: g.md, symbol: "none", smooth: 0.2, lineStyle: { width: 1.8, color: COR.mr, type: [6, 4] }, itemStyle: { color: COR.mr } },
        { name: a1, type: "line", data: ant, symbol: "circle", symbolSize: 4, lineStyle: { width: 1.8, color: COR.cz }, itemStyle: { color: COR.cz } },
        { name: u, type: "line", data: cur, symbol: "circle", symbolSize: 4, lineStyle: { width: 3, color: COR.vd }, itemStyle: { color: COR.vd }, z: 5,
          endLabel: { show: !mobile() && cur.length > 0, formatter: function (q) { return br(q.value[1], 0) + "%"; }, color: COR.vd, fontWeight: 700, fontSize: 12 } }] });
  }

  // 2) distribuição da condição: última semana x mesma semana do ano passado x média de 5 anos
  function g2() {
    var K = C.condicao, u = C.ultimoAno, ult = (K[u] || []).slice(-1)[0]; if (!ult) return null;
    var t = doy(ult[0]), a1 = String(+u - 1), r1 = emCond(K[a1], t, true);
    var rs = anos().map(function (a) { return emCond(K[a], t, true); }).filter(Boolean);
    var md = rs.length ? [0, 1, 2, 3, 4].map(function (i) { return media(rs.map(function (r) { return r[i + 1]; })); }) : null;
    var linhas = [[u + " (" + dataBR(ult[0]) + ")", ult.slice(1)]];
    if (r1) linhas.push([a1 + " (" + dataBR(r1[0]) + ")", r1.slice(1)]);
    if (md) linhas.push(["Média 5 anos", md]);
    return Object.assign({}, base, { graphic: [marca()], legend: legenda({ itemWidth: 10, itemHeight: 10 }),
      grid: { left: 6, right: 10, top: 34, bottom: 6, containLabel: true },
      xAxis: eixoPct({ axisLabel: { show: false } }),
      yAxis: { type: "category", inverse: true, data: linhas.map(function (l) { return l[0]; }), axisLabel: { color: COR.tx, fontSize: 12, fontWeight: 600 }, axisLine: { show: false }, axisTick: { show: false } },
      tooltip: Object.assign({}, base.tooltip, { trigger: "axis", axisPointer: { type: "shadow" }, formatter: function (ps) { var h = "<b>" + ps[0].name + "</b>"; ps.slice().reverse().forEach(function (q) { h += tl(q.marker, q.seriesName, br(q.value, 0) + "%"); }); return h; } }),
      series: CATS.map(function (c, i) { return { name: c[0], type: "bar", stack: "s", barWidth: "56%", itemStyle: { color: c[1] }, data: linhas.map(function (l) { return l[1][i]; }),
        label: { show: true, formatter: function (q) { return q.value >= 8 ? br(q.value, 0) : ""; }, color: i >= 3 || i === 0 ? "#fff" : COR.tx, fontSize: 11, fontWeight: 600 } }; }) });
  }

  // 3) boa + excelente na mesma semana do ano, desde 2010
  function g3() {
    var K = C.condicao, u = C.ultimoAno, ult = (K[u] || []).slice(-1)[0]; if (!ult) return null;
    var t = doy(ult[0]), anosT = Object.keys(K).sort(), lst = [];
    anosT.forEach(function (a) { var r = emCond(K[a], t, true); if (r) lst.push([a, ge(r)]); });
    var m = media(lst.filter(function (x) { return x[0] !== u; }).map(function (x) { return x[1]; }));
    return Object.assign({}, base, { graphic: [marca()],
      grid: { left: 6, right: 10, top: 18, bottom: 6, containLabel: true },
      xAxis: { type: "category", data: lst.map(function (x) { return x[0]; }), axisLabel: { color: COR.mt, fontSize: 11, formatter: function (v) { return mobile() ? "'" + v.slice(2) : v; } }, axisLine: { lineStyle: { color: COR.ln } }, axisTick: { show: false } },
      yAxis: eixoPct({ max: 100, interval: 25 }),
      tooltip: Object.assign({}, base.tooltip, { trigger: "axis", axisPointer: { type: "shadow" }, formatter: function (ps) { return "<b>" + ps[0].name + "</b>" + tl("", "Boa ou excelente", br(ps[0].value, 0) + "%"); } }),
      series: [{ type: "bar", barWidth: "62%", data: lst.map(function (x) { return { value: x[1], itemStyle: { color: x[0] === u ? COR.vd : "#8DB878", borderRadius: [4, 4, 0, 0] } }; }),
        label: { show: !mobile(), position: "top", fontSize: 10.5, color: COR.tx, formatter: function (q) { return br(q.value, 0); } },
        markLine: m != null ? { silent: true, symbol: "none", lineStyle: { color: COR.mr, type: [5, 4] }, label: { formatter: "média " + br(m, 0) + "%", color: COR.mr, fontSize: 11, position: "insideEndTop" }, data: [{ yAxis: m }] } : undefined }] });
  }

  // ---------------- indicadores ----------------
  function escolherEtapa() {
    var u = C.ultimoAno, best = null;
    Object.keys(C.progresso).forEach(function (e) { var s = C.progresso[e][u]; if (!s || !s.length) return; var x = s[s.length - 1]; if (!best || x[0] > best[1] || (x[0] === best[1] && x[1] < best[2])) best = [e, x[0], x[1]]; });
    return best ? best[0] : Object.keys(C.progresso)[0];
  }
  function kpis() {
    var u = C.ultimoAno, a1 = String(+u - 1), P = C.progresso[st.etapa] || {}, s = P[u] || [], x = s[s.length - 1];
    var fim = x ? doy(x[0]) : null, va = fim ? emProg(P[a1], fim) : null, vm = fim ? media(anos().map(function (a) { return emProg(P[a], fim); })) : null;
    $("kAl").textContent = st.etapa + (x ? " em " + dataBR(x[0]) : "");
    $("kA").innerHTML = x ? br(x[1], 0) + "<small>%</small>" : "-";
    $("kAs").innerHTML = x ? a1 + ": " + br(va, 0) + "% · média: " + br(vm, 0) + "%" : "sem dados nesta safra";
    var K = C.condicao[u] || [], r = K[K.length - 1], r0 = K[K.length - 2];
    if (r) {
      var ra = emCond(C.condicao[a1], doy(r[0]), true);
      $("kC").innerHTML = br(ge(r), 0) + "<small>%</small>";
      $("kCs").innerHTML = "em " + dataBR(r[0]) + (r0 ? (ge(r) === ge(r0) ? " · estável na semana" : ' · <i class="' + (ge(r) - ge(r0) > 0 ? "pos" : "neg") + '">' + pp(ge(r) - ge(r0)) + "</i> na semana") : "");
      $("kY").innerHTML = ra ? '<i style="font-style:normal" class="' + (ge(r) - ge(ra) >= 0 ? "pos" : "neg") + '">' + pp(ge(r) - ge(ra)) + "</i>" : "-";
      $("kYs").textContent = ra ? a1 + ": " + br(ge(ra), 0) + "% em " + dataBR(ra[0]) : " ";
      $("kI").textContent = br(cci(r), 2);
      $("kIs").textContent = "escala de 1 (muito ruim) a 5 (excelente)";
    } else { ["kC", "kY", "kI"].forEach(function (k) { $(k).textContent = "-"; }); $("kCs").textContent = $("kYs").textContent = $("kIs").textContent = "sem avaliação nesta safra"; }
    // frase de leitura
    var cult = C.nome.toLowerCase(), f = "";
    if (x) f = "<b>" + st.etapa + " do " + cult.replace(/^trigo/, "trigo") + " nos EUA em " + br(x[1], 0) + "%</b> na semana até " + dataBR(x[0]) + ", contra " + br(va, 0) + "% há um ano e " + br(vm, 0) + "% na média de 5 anos.";
    if (r) f += " Na avaliação de " + dataBR(r[0]) + ", " + br(ge(r), 0) + "% das lavouras estavam em condição boa ou excelente.";
    $("abxLead").querySelector("span").innerHTML = f.replace("do soja", "da soja");
  }

  function render() {
    $("abxTit").textContent = C.nome;
    $("abxMeta").textContent = "Estados Unidos · semana encerrada em " + dataBRc(D.ultima_semana);
    var etapas = ORDEM.filter(function (e) { return C.progresso[e]; });
    $("abxEtapa").innerHTML = etapas.map(function (e) { return '<button data-e="' + e + '" aria-pressed="' + (e === st.etapa) + '">' + e + "</button>"; }).join("");
    $("abxH0s").textContent = "% da área";
    var ult = (C.condicao[C.ultimoAno] || []).slice(-1)[0];
    $("abxH2s").textContent = ult ? "semana de " + dataBR(ult[0]) : "";
    $("abxH3s").textContent = ult ? "por volta de " + dataBR(ult[0]) : "";
    kpis();
    [g0(), g1(), g2(), g3()].forEach(function (o, i) { var card = $("abxG" + i).closest(".abx-card"); card.style.display = o ? "" : "none"; if (o) { charts[i].resize(); charts[i].setOption(o, true); } });
    var d = new Date(D.atualizado_em);
    $("abxAtu").textContent = "Atualizado em " + ("0" + d.getDate()).slice(-2) + "/" + ("0" + (d.getMonth() + 1)).slice(-2) + "/" + d.getFullYear();
  }

  function trocar(slug) {
    st.cult = slug; C = D.culturas[slug];
    var anosC = Object.keys(C.condicao), anosP = []; Object.keys(C.progresso).forEach(function (e) { anosP = anosP.concat(Object.keys(C.progresso[e])); });
    C.ultimoAno = String(Math.max.apply(null, anosC.concat(anosP).map(Number)));
    st.etapa = escolherEtapa();
    $("abxCult").querySelectorAll("button").forEach(function (b) { b.setAttribute("aria-pressed", String(b.dataset.c === slug)); });
    history.replaceState(null, "", "#" + slug);
    render();
  }

  function baixar(i) {
    var opt = [g0, g1, g2, g3][i](); if (!opt) return;
    var tit = ["Avanço da safra · " + st.etapa, "Lavouras em condição boa ou excelente", "Distribuição da condição", "Boa ou excelente na mesma semana, ano a ano"][i];
    opt.animation = false;
    opt.title = { text: tit + " · " + C.nome + " EUA", subtext: "USDA NASS Crop Progress · semana até " + dataBRc(D.ultima_semana), left: 8, top: 6, textStyle: { fontFamily: "Sora, Geist, sans-serif", fontSize: 15, fontWeight: 700, color: COR.vd }, subtextStyle: { fontSize: 12, color: COR.mt } };
    if (opt.legend) opt.legend = Object.assign({}, opt.legend, { top: 54, left: 8 });
    opt.grid = Object.assign({}, opt.grid, { top: (opt.legend ? 34 : 18) + 48, bottom: 30 });
    opt.graphic = [marca(), { type: "text", right: 12, bottom: 8, style: { text: "agrobasis.com.br · Fonte: USDA NASS", fill: "#9aa39c", font: "11px Geist, sans-serif" } }];
    charts[i].setOption(opt, true);
    var url = charts[i].getDataURL({ type: "png", pixelRatio: 2, backgroundColor: "#fff" });
    render();
    var a = document.createElement("a"); a.href = url; a.download = "agrobasis-safra-eua-" + st.cult + "-" + ["avanco", "condicao", "distribuicao", "historico"][i] + ".png"; document.body.appendChild(a); a.click(); a.remove();
  }

  function lib(i) { i = i || 0; return new Promise(function (ok, nok) { if (window.echarts) return ok(); var s = document.createElement("script"); s.src = LIBS[i]; s.onload = ok; s.onerror = function () { i + 1 < LIBS.length ? lib(i + 1).then(ok, nok) : nok(); }; document.head.appendChild(s); }); }
  function json(c, i) { i = i || 0; return fetch(REPO[i] + c + "?v=" + Math.floor(Date.now() / 18e5), { cache: "no-store" }).then(function (r) { if (!r.ok) throw 0; return r.json(); }).catch(function () { if (i + 1 < REPO.length) return json(c, i + 1); throw new Error("sem dados"); }); }

  Promise.all([lib(), json("dados/safra_eua.json")]).then(function (r) {
    D = r[1];
    var ordem = ["milho", "soja", "trigo_inverno", "trigo_primavera"].filter(function (k) { return D.culturas[k]; });
    $("abxCult").innerHTML = ordem.map(function (k) { return '<button data-c="' + k + '">' + D.culturas[k].nome + "</button>"; }).join("");
    charts = [0, 1, 2, 3].map(function (i) { return echarts.init($("abxG" + i)); });
    $("abxCult").addEventListener("click", function (e) { var b = e.target.closest("button"); if (b) trocar(b.dataset.c); });
    $("abxEtapa").addEventListener("click", function (e) { var b = e.target.closest("button"); if (!b) return; st.etapa = b.dataset.e; render(); });
    document.querySelectorAll("#abx .abx-dl").forEach(function (b) { b.addEventListener("click", function () { baixar(+b.dataset.dl); }); });
    var to, lw = window.innerWidth; window.addEventListener("resize", function () { clearTimeout(to); to = setTimeout(function () { charts.forEach(function (c) { c.resize(); }); if ((lw < 560) !== (window.innerWidth < 560)) render(); lw = window.innerWidth; }, 150); });
    var h = (location.hash || "").slice(1);
    trocar(D.culturas[h] ? h : "milho");
  }).catch(function (e) { if (window.console) console.error("AgroBasis safra:", e); $("abx").innerHTML = '<div class="abx-err">Não foi possível carregar os dados agora. Tente novamente em instantes.</div>'; });
})();
