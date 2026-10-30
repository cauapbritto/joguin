(function () {
  "use strict";

  var params = new URLSearchParams(location.search);
  var slot = parseInt(params.get("player"), 10) || 0;
  if (slot < 1 || slot > 4) slot = 0;
  var token = loadToken();
  var roster = [];
  var status = null;
  var joined = false;
  var failures = 0;

  var $ = function (id) { return document.getElementById(id); };
  var views = ["join", "wait", "select", "pad", "choose", "shop", "penalty"];

  function loadToken() {
    var t = null;
    try { t = localStorage.getItem("ss_token"); } catch (e) { /* modo privado */ }
    if (!t) {
      t = Math.random().toString(36).slice(2) + Date.now().toString(36);
      try { localStorage.setItem("ss_token", t); } catch (e) { /* ignora */ }
    }
    return t;
  }

  function show(name) {
    if (name !== "pad" && editing) closeHudEditor(true);
    views.forEach(function (v) { $("view-" + v).classList.toggle("on", v === name); });
    document.body.classList.toggle("in-pad", name === "pad");
  }

  function bind(key, text) {
    document.querySelectorAll('[data-bind="' + key + '"]').forEach(function (el) { el.textContent = text; });
  }

  function post(path, body) {
    return fetch(path, {
      method: "POST",
      keepalive: true,
      cache: "no-store",
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined
    });
  }

  function buzz() { if (navigator.vibrate && !(hud && hud.vibrate === false)) navigator.vibrate(8); }

  function capture(el, id) {
    try { el.setPointerCapture(id); } catch (e) { /* ponteiro já liberado */ }
  }

  // ── comandos ───────────────────────────────
  // O celular manda o ESTADO COMPLETO do controle (botões segurados, analógico e quantas
  // vezes cada botão foi apertado), numerado. Pedidos que chegam fora de ordem pela rede
  // não deixam botão "preso", e um toque rápido nunca se perde.
  var held = {};
  var counts = {};
  var axis = { x: 0, y: 0 };
  var sid = Math.random().toString(36).slice(2);
  var seq = 0;
  var sendTimer = null;
  var rtt = null;          // tempo de ida e volta médio (ms)
  var netFails = 0;

  function flush() {
    if (sendTimer !== null) { clearTimeout(sendTimer); sendTimer = null; }
    if (!slot) return;
    seq += 1;
    var t0 = performance.now();
    post("/api/input", {
      slot: slot, token: token, sid: sid, seq: seq,
      held: Object.keys(held), counts: counts,
      x: Math.round(axis.x * 100) / 100, y: Math.round(axis.y * 100) / 100
    }).then(function (r) {
      if (!r.ok && r.status !== 204) return;
      var ms = performance.now() - t0;
      rtt = rtt === null ? ms : rtt * 0.8 + ms * 0.2;
      netFails = 0;
    }).catch(function () { netFails += 1; });
  }

  function schedule(delay) {
    if (sendTimer === null) sendTimer = setTimeout(flush, delay);
  }

  // enquanto algo está segurado, reenvia sempre: se a rede engasgar, o jogo continua
  // com o último comando; sem notícias por 1 s ele solta tudo por segurança
  setInterval(function () {
    if (slot && (Object.keys(held).length || axis.x || axis.y)) flush();
  }, 100);

  function press(action) {
    if (!slot || held[action]) return;
    held[action] = true;
    counts[action] = (counts[action] || 0) + 1;
    flush();
  }

  function release(action) {
    if (!slot || !held[action]) return;
    delete held[action];
    flush();
  }

  function releaseAll() {
    held = {};
    axis = { x: 0, y: 0 };
    if (typeof clearPadButtons === "function") clearPadButtons();
    if (slot) {
      flush();
      post("/release_all?slot=" + slot).catch(function () {});
    }
  }

  function tap(action) {
    if (!slot) return;
    counts[action] = (counts[action] || 0) + 1;
    flush();
  }

  function renderNet() {
    var el = $("net");
    if (!el) return;
    var cls = "net-bad", text = "sem sinal";
    if (netFails < 3 && rtt === null) {
      cls = ""; text = "--";
    } else if (netFails < 3) {
      text = Math.round(rtt) + " ms";
      cls = rtt < 80 ? "net-good" : rtt < 180 ? "net-mid" : "net-bad";
    }
    el.className = "net " + cls;
    el.textContent = "● " + text;
  }
  setInterval(renderNet, 500);

  // ── vaga ───────────────────────────────────
  function join(n) {
    return post("/api/join", { slot: n, token: token }).then(function (r) {
      if (r.ok) {
        slot = n;
        joined = true;
        document.body.dataset.slot = n;
        history.replaceState(null, "", "?player=" + n);
        bind("tag", "P" + n);
        return true;
      }
      $("join-note").textContent = "O jogador " + n + " já está em uso. Escolha outro.";
      return false;
    });
  }

  document.querySelectorAll(".slot").forEach(function (b) {
    b.addEventListener("click", function () {
      buzz();
      join(parseInt(b.dataset.slot, 10)).then(function (ok) { if (ok) refresh(); });
    });
  });

  $("change-slot").addEventListener("click", function () {
    post("/api/leave", { slot: slot, token: token });
    joined = false;
    slot = 0;
    show("join");
  });

  // ── botões de toque (um aperto) e de segurar ──
  document.querySelectorAll("[data-tap]").forEach(function (el) {
    el.addEventListener("pointerdown", function (e) {
      e.preventDefault();
      buzz();
      el.classList.add("down");
      tap(el.dataset.tap);
    });
    ["pointerup", "pointercancel", "pointerleave"].forEach(function (t) {
      el.addEventListener(t, function () { el.classList.remove("down"); });
    });
  });

  var holdPointers = {};
  document.querySelectorAll("[data-hold]").forEach(function (el) {
    el.addEventListener("pointerdown", function (e) {
      e.preventDefault();
      capture(el, e.pointerId);
      holdPointers[e.pointerId] = el;
      el.classList.add("down");
      buzz();
      press(el.dataset.hold);
    });
  });

  function endHold(e) {
    var el = holdPointers[e.pointerId];
    if (!el) return;
    delete holdPointers[e.pointerId];
    el.classList.remove("down");
    release(el.dataset.hold);
  }
  document.addEventListener("pointerup", endHold);
  document.addEventListener("pointercancel", endHold);

  // ── botões em arco ─────────────────────────
  // Ficam em volta do ponto onde o polegar direito descansa, do mais usado (grande, no
  // canto) para os menos usados (em volta). O toque vale para o botão mais próximo, mesmo
  // um pouco fora dele, e dá para deslizar o dedo de um botão para outro sem levantar.
  var btnZone = $("btn-zone");
  var ANGLES = { w: 180, nw: 132, n: 84, ww: 156, nn: 108 };
  var MAGNET = 26;        // px fora do botão que ainda contam como toque nele
  var KEEP = 40;          // deslizando: até onde o dedo pode sair do botão sem soltar
  var soccerMode = false;

  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

  function fitLabel(el, text, size, maxFs) {
    var lines = text.indexOf(" ") > 0 ? text.split(" ") : [text];
    var longest = Math.max.apply(null, lines.map(function (l) { return l.length; }));
    var margin = el.classList.contains("pb-super") ? 26 : 16;          // o anel do SUPER ocupa espaço
    var fs = clamp(Math.floor((size - margin) / longest), 6, maxFs);   // fonte pixel: 1 caractere ≈ 1em
    var target = el.querySelector("span") || el;
    target.textContent = lines.join("\n");
    el.style.setProperty("--fs", fs + "px");
  }

  function layoutButtons() {
    var zr = btnZone.getBoundingClientRect();
    if (!zr.width || !zr.height) return;
    var vh = window.innerHeight;
    var big = clamp(vh * 0.31, 84, 128);
    document.querySelectorAll(".pad-set").forEach(function (set) {
      var hasOuter = !!set.querySelector('[data-pos="ww"], [data-pos="nn"]');
      var mid = hasOuter ? clamp(vh * 0.21, 60, 88) : clamp(vh * 0.24, 66, 98);
      var small = clamp(vh * 0.175, 52, 72);
      var gap = clamp(vh * 0.032, 10, 16);
      var pad = clamp(vh * 0.05, 14, 26);
      var ox = zr.width - pad - big / 2;
      var oy = zr.height - pad - big / 2;
      var ring1 = big / 2 + mid / 2 + gap;
      var ring2 = ring1 + mid / 2 + small / 2 + gap * 0.6;
      set.querySelectorAll(".pb").forEach(function (b) {
        var pos = b.dataset.pos;
        var size = pos === "main" ? big : (pos === "ww" || pos === "nn") ? small : mid;
        var x = ox, y = oy;
        if (pos !== "main") {
          var a = ANGLES[pos] * Math.PI / 180;
          var r = (pos === "ww" || pos === "nn") ? ring2 : ring1;
          x = ox + Math.cos(a) * r;
          y = oy - Math.sin(a) * r;
        }
        if (hud && hud.lefty) x = zr.width - x;          // canhoto: o arco espelhado
        var own = hud && set.classList.contains("on") ? hud.btns[b.dataset.act] : null;
        if (own) {                                       // CONFIGURAR HUD: posição e tamanho do jogador
          size = clamp(size * (own.s || 1), 40, 200);
          if (own.x !== undefined) {
            x = clamp(own.x * zr.width, size / 2, zr.width - size / 2);
            y = clamp(own.y * zr.height, size / 2, zr.height - size / 2);
          }
        }
        b.dataset.x = x;
        b.dataset.y = y;
        b.style.left = x + "px";
        b.style.top = y + "px";
        b.style.setProperty("--s", size + "px");
        if (pos === "main" && set.classList.contains("battle-only")) {
          var badge = $("ammo-badge");           // contador de munição logo abaixo do ATACAR
          badge.style.left = x + "px";
          badge.style.top = Math.min(zr.height - 26, y + size / 2 - 6) + "px";
        }
        if (!b.dataset.label) b.dataset.label = (b.querySelector("span") || b).textContent;
        fitLabel(b, b.dataset.label, size, pos === "main" ? 15 : 10);
      });
    });
  }
  window.addEventListener("resize", layoutButtons);
  window.addEventListener("orientationchange", function () { setTimeout(layoutButtons, 250); });

  var fingers = {};       // dedo → botão que ele está segurando
  var holdCount = {};     // ação → quantos dedos estão nela

  function padButtons() {
    return Array.prototype.slice.call(document.querySelectorAll(".pad-set.on .pb"));
  }

  function edgeDistance(b, x, y) {
    var r = b.getBoundingClientRect();
    return Math.hypot(x - (r.left + r.width / 2), y - (r.top + r.height / 2)) - r.width / 2;
  }

  function pickButton(x, y, current) {
    var best = null, bestD = 1e9;
    padButtons().forEach(function (b) {
      var d = edgeDistance(b, x, y);
      if (d < bestD) { bestD = d; best = b; }
    });
    if (current) {
      if (best !== current && bestD <= 0) return best;           // entrou em outro botão
      return edgeDistance(current, x, y) <= KEEP ? current : null;
    }
    return bestD <= MAGNET ? best : null;
  }

  function grab(b) {
    var a = b.dataset.act;
    holdCount[a] = (holdCount[a] || 0) + 1;
    if (holdCount[a] === 1) { b.classList.add("down"); press(a); }
  }

  function letGo(b) {
    var a = b.dataset.act;
    holdCount[a] = Math.max(0, (holdCount[a] || 0) - 1);
    if (holdCount[a] === 0) { b.classList.remove("down"); release(a); }
  }

  function setFinger(id, b) {
    var old = fingers[id] || null;
    if (old === b) return;
    if (old) letGo(old);
    if (b) { grab(b); buzz(); fingers[id] = b; } else { delete fingers[id]; }
  }

  function clearPadButtons() {
    fingers = {};
    holdCount = {};
    padButtons().forEach(function (b) { b.classList.remove("down"); });
  }

  btnZone.addEventListener("pointerdown", function (e) {
    e.preventDefault();
    capture(btnZone, e.pointerId);
    if (editing) { editGrabButton(e); return; }
    setFinger(e.pointerId, pickButton(e.clientX, e.clientY, null));
  });
  btnZone.addEventListener("pointermove", function (e) {
    if (editing) { editDrag(e); return; }
    if (!(e.pointerId in fingers)) return;
    e.preventDefault();
    setFinger(e.pointerId, pickButton(e.clientX, e.clientY, fingers[e.pointerId]));
  });
  ["pointerup", "pointercancel"].forEach(function (t) {
    btnZone.addEventListener(t, function (e) {
      if (editing) { editDrop(e); return; }
      setFinger(e.pointerId, null);
    });
  });

  // ── analógico ──────────────────────────────
  var zone = $("stick-zone");
  var base = $("stick-base");
  var knob = $("stick-knob");
  var stickId = null;
  var origin = null;
  var dirs = { up: false, down: false, left: false, right: false };

  var running = false;
  function setRun(on) {
    if (running === on) return;
    running = on;
    base.classList.toggle("run", on);
    if (on) { press("sprint"); buzz(); } else release("sprint");
  }

  function setDir(name, on) {
    if (dirs[name] === on) return;
    dirs[name] = on;
    if (on) press(name); else release(name);
  }

  function sendAxis(x, y) {
    if (!slot) return;
    var changed = Math.abs(x - axis.x) + Math.abs(y - axis.y) > 0.04 || (x === 0 && y === 0);
    axis = { x: x, y: y };
    if (x === 0 && y === 0) flush();
    else if (changed) schedule(33);
  }

  function moveStick(x, y) {
    var r = base.offsetWidth / 2;
    var dx = x - origin.x;
    var dy = y - origin.y;
    var dist = Math.hypot(dx, dy);
    var max = r * 0.75;
    var k = dist > max ? max / dist : 1;
    knob.style.transform = "translate(" + dx * k + "px," + dy * k + "px)";
    var nx = dist ? dx / dist : 0;
    var ny = dist ? dy / dist : 0;
    var active = dist > r * 0.18;
    // futebol: empurrar até a borda do analógico = CORRER (o polegar direito fica livre)
    setRun(soccerMode && dist > r * 1.0);
    // analógico de verdade: direção livre e intensidade proporcional
    var power = active ? Math.min(1, (dist - r * 0.18) / (max - r * 0.18)) : 0;
    sendAxis(nx * power, ny * power);
    setDir("left", active && nx < -0.38);
    setDir("right", active && nx > 0.38);
    setDir("up", active && ny < -0.38);
    setDir("down", active && ny > 0.38);
  }

  function placeStick(cx, cy) {
    // põe o centro do analógico em (cx, cy) da zona, sem sair da tela
    var zr = zone.getBoundingClientRect();
    var size = base.offsetWidth;
    var left = Math.max(8, Math.min(cx - size / 2, zr.width - size - 8));
    var top = Math.max(56, Math.min(cy - size / 2, zr.height - size - 8));
    base.style.left = left + "px";
    base.style.top = top + "px";
    base.style.bottom = "auto";
    return { x: (left + size / 2) / zr.width, y: (top + size / 2) / zr.height };
  }

  zone.addEventListener("pointerdown", function (e) {
    if (editing) { e.preventDefault(); capture(zone, e.pointerId); editGrabStick(e); return; }
    if (stickId !== null) return;
    e.preventDefault();
    stickId = e.pointerId;
    capture(zone, e.pointerId);
    // o analógico aparece onde o polegar encostou (ou fica parado no lugar, se for FIXO)
    var zr = zone.getBoundingClientRect();
    if (!(hud && hud.fixed)) placeStick(e.clientX - zr.left, e.clientY - zr.top);
    var br = base.getBoundingClientRect();
    origin = { x: br.left + br.width / 2, y: br.top + br.height / 2 };
    base.classList.add("live");
    moveStick(e.clientX, e.clientY);
  });

  zone.addEventListener("pointermove", function (e) {
    if (editing) { editDrag(e); return; }
    if (e.pointerId !== stickId) return;
    e.preventDefault();
    moveStick(e.clientX, e.clientY);
  });

  function endStick(e) {
    if (editing) { editDrop(e); return; }
    if (e.pointerId !== stickId) return;
    stickId = null;
    knob.style.transform = "";
    base.classList.remove("live");
    Object.keys(dirs).forEach(function (d) { setDir(d, false); });
    setRun(false);
    sendAxis(0, 0);
  }
  zone.addEventListener("pointerup", endStick);
  zone.addEventListener("pointercancel", endStick);

  document.addEventListener("touchmove", function (e) { e.preventDefault(); }, { passive: false });
  document.addEventListener("contextmenu", function (e) { e.preventDefault(); });
  document.addEventListener("visibilitychange", function () { if (document.hidden) releaseAll(); });
  window.addEventListener("pagehide", releaseAll);

  // ── CONFIGURAR HUD ─────────────────────────
  // Cada jogador arruma o controle do seu jeito: arrasta os botões e o analógico, muda o
  // tamanho (70% a 150%) e a transparência, analógico fixo ou solto, lado de canhoto e
  // vibração. Fica salvo neste celular, separado por modo (duelo/campanha, futebol, basquete).
  var HUD_PREFIX = "ss_hud_";
  var hud = null;
  var hudName = null;
  var editing = false;
  var editSel = null;        // "stick" ou a ação do botão escolhido
  var editPointer = null;
  var STICK_SIZE = 140, KNOB_SIZE = 56;

  function hudDefaults() {
    return { btns: {}, stick: null, stickScale: 1, fixed: false, opacity: 1, lefty: false, vibrate: true };
  }

  function loadHud(name) {
    var h = hudDefaults();
    try {
      var saved = JSON.parse(localStorage.getItem(HUD_PREFIX + name) || "null");
      if (saved && typeof saved === "object") Object.keys(h).forEach(function (k) { if (k in saved) h[k] = saved[k]; });
    } catch (e) { /* modo privado ou salvo estragado: usa o padrão */ }
    return h;
  }

  function saveHud() {
    try { localStorage.setItem(HUD_PREFIX + hudName, JSON.stringify(hud)); } catch (e) { /* ignora */ }
  }

  function useHud(name) {
    if (name === hudName || editing) return;
    hudName = name;
    hud = loadHud(name);
    applyHud();
  }

  function applyHud() {
    if (!hud) return;
    document.body.classList.toggle("lefty", !!hud.lefty);
    $("view-pad").style.setProperty("--hud-op", hud.opacity);
    var sz = Math.round(STICK_SIZE * hud.stickScale), kz = Math.round(KNOB_SIZE * hud.stickScale);
    base.style.width = base.style.height = sz + "px";
    knob.style.width = knob.style.height = kz + "px";
    knob.style.margin = (-kz / 2) + "px 0 0 " + (-kz / 2) + "px";
    var zr = zone.getBoundingClientRect();
    if (hud.stick && zr.width) placeStick(hud.stick.x * zr.width, hud.stick.y * zr.height);
    else { base.style.left = ""; base.style.top = ""; base.style.bottom = ""; }
    if (stickId === null) {
      var br = base.getBoundingClientRect();
      origin = { x: br.left + br.width / 2, y: br.top + br.height / 2 };
    }
    layoutButtons();
    renderHudBar();
  }

  function editButton(act) {
    return document.querySelector('.pad-set.on .pb[data-act="' + act + '"]');
  }

  function selectEdit(what) {
    editSel = what;
    padButtons().forEach(function (b) { b.classList.toggle("editing-sel", b.dataset.act === what); });
    base.classList.toggle("editing-sel", what === "stick");
    renderHudBar();
  }

  function editGrabButton(e) {
    var b = pickButton(e.clientX, e.clientY, null);
    if (!b) { selectEdit(null); return; }
    buzz();
    selectEdit(b.dataset.act);
    editPointer = e.pointerId;
  }

  function editGrabStick(e) {
    buzz();
    selectEdit("stick");
    editPointer = e.pointerId;
    editDrag(e);
  }

  function editDrag(e) {
    if (e.pointerId !== editPointer || !editSel) return;
    e.preventDefault();
    if (editSel === "stick") {
      var zr = zone.getBoundingClientRect();
      hud.stick = placeStick(e.clientX - zr.left, e.clientY - zr.top);
      return;
    }
    var br = btnZone.getBoundingClientRect();
    var own = hud.btns[editSel] || (hud.btns[editSel] = { s: 1 });
    own.x = clamp((e.clientX - br.left) / br.width, 0, 1);
    own.y = clamp((e.clientY - br.top) / br.height, 0, 1);
    layoutButtons();
  }

  function editDrop(e) {
    if (e.pointerId === editPointer) editPointer = null;
  }

  function resize(step) {
    if (editSel === "stick") {
      hud.stickScale = Math.round(clamp(hud.stickScale + step, 0.7, 1.5) * 10) / 10;
    } else if (editSel) {
      var own = hud.btns[editSel] || (hud.btns[editSel] = { s: 1 });
      own.s = Math.round(clamp((own.s || 1) + step, 0.7, 1.5) * 10) / 10;
    }
    applyHud();
  }

  function renderHudBar() {
    if (!hud) return;
    var sel = editSel === "stick" ? "ANALÓGICO"
      : editSel ? ((editButton(editSel) || {}).dataset || {}).label || editSel.toUpperCase() : null;
    var scale = editSel === "stick" ? hud.stickScale : editSel ? ((hud.btns[editSel] || {}).s || 1) : null;
    $("hud-sel").textContent = sel ? sel + " · " + Math.round(scale * 100) + "%" : "TOQUE EM UM BOTÃO";
    $("hud-smaller").disabled = $("hud-bigger").disabled = !sel;
    $("hud-op").textContent = Math.round(hud.opacity * 100) + "%";
    $("hud-fixed").textContent = hud.fixed ? "ANALÓG. FIXO" : "ANALÓG. SOLTO";
    $("hud-lefty").classList.toggle("is-on", !!hud.lefty);
    $("hud-vibrate").classList.toggle("is-on", hud.vibrate !== false);
  }

  function openHudEditor() {
    if (!hud) return;
    releaseAll();                    // nada fica segurado enquanto arruma
    if (stickId !== null) { stickId = null; knob.style.transform = ""; base.classList.remove("live"); }
    editing = true;
    document.body.classList.add("editing");
    selectEdit(null);
  }

  function closeHudEditor(keep) {
    if (keep) saveHud(); else hud = loadHud(hudName);
    editing = false;
    editPointer = null;
    document.body.classList.remove("editing");
    selectEdit(null);
    applyHud();
  }

  function hudButton(id, fn) {
    $(id).addEventListener("pointerdown", function (e) {
      e.preventDefault();
      e.stopPropagation();
      if ($(id).disabled) return;
      buzz();
      fn();
    });
  }
  hudButton("hud-btn", openHudEditor);
  hudButton("hud-smaller", function () { resize(-0.1); });
  hudButton("hud-bigger", function () { resize(0.1); });
  hudButton("hud-op-down", function () { hud.opacity = Math.round(clamp(hud.opacity - 0.1, 0.3, 1) * 10) / 10; applyHud(); });
  hudButton("hud-op-up", function () { hud.opacity = Math.round(clamp(hud.opacity + 0.1, 0.3, 1) * 10) / 10; applyHud(); });
  hudButton("hud-fixed", function () { hud.fixed = !hud.fixed; applyHud(); });
  hudButton("hud-lefty", function () {
    hud.lefty = !hud.lefty;
    Object.keys(hud.btns).forEach(function (k) { var b = hud.btns[k]; if (b.x !== undefined) b.x = 1 - b.x; });
    hud.stick = null;                // o analógico volta para o canto do outro lado
    applyHud();
  });
  hudButton("hud-vibrate", function () { hud.vibrate = hud.vibrate === false; renderHudBar(); });
  hudButton("hud-reset", function () { hud = hudDefaults(); selectEdit(null); applyHud(); });
  hudButton("hud-cancel", function () { closeHudEditor(false); });
  hudButton("hud-save", function () { closeHudEditor(true); });
  window.addEventListener("resize", function () { setTimeout(applyHud, 50); });

  // ── espelho da seleção de personagem ──────
  function renderSelect(me, mode) {
    var ch = roster[me.char];
    if (!ch) return;
    $("portrait").src = "/sprite/" + me.char + ".png";
    $("char-name").textContent = ch.name.toUpperCase();
    var maxHp = 250, maxSpeed = 5, maxDmg = 28;
    var rows = mode === "soccer"
      ? [["VELOCIDADE", ch.speed / maxSpeed]]
      : [["VIDA", ch.hp / maxHp], ["VELOCIDADE", ch.speed / maxSpeed],
         ["DANO", Math.max.apply(null, ch.weapons.map(function (w) { return w.damage; })) / maxDmg]];
    $("stats").innerHTML = rows.map(function (r) {
      return "<span>" + r[0] + '</span><span class="bar"><i style="width:' + Math.round(r[1] * 100) + '%"></i></span>';
    }).join("");
    var weapon = ch.weapons[me.weapon] || ch.weapons[0];
    var gun = ch.weapons.filter(function (w) { return !w.melee; })[0];
    $("ability").innerHTML = mode === "soccer"
      ? "<b>SUPER: " + (ch.soccer_power || "") + "</b>" + (ch.soccer_desc || "") +
        (ch.soccer_passive ? "<br><b>SEMPRE: " + ch.soccer_passive.toUpperCase() + "</b>" + ch.soccer_passive_desc : "")
      : "<b>" + ch.ability.toUpperCase() + "</b>" + ch.ability_desc +
        (gun && gun.note ? "<br><b>" + gun.name.toUpperCase() + " (" + gun.mag + " TIROS)</b>" + gun.note : "");
    $("weapon").style.display = mode === "soccer" ? "none" : "";
    $("weapon").textContent = "ARMA: " + weapon.name.toUpperCase() + (weapon.melee ? " · CORPO A CORPO" : " · DISTÂNCIA");
    var ready = $("ready-btn");
    ready.classList.toggle("is-ready", me.ready);
    ready.textContent = me.ready ? "PRONTO! (TOQUE P/ CANCELAR)" : "PRONTO";
    ready.dataset.tap = me.ready ? "cancel" : "confirm";
    document.querySelectorAll("#view-select .arrow, #weapon").forEach(function (b) { b.disabled = me.ready; });
  }

  // ── campanha: escolha de melhoria ──────────
  function renderChoose(me) {
    var opts = me.options || [];
    document.querySelectorAll("#view-choose .opt").forEach(function (b, i) {
      var o = opts[i];
      b.style.visibility = o ? "" : "hidden";
      if (!o) return;
      b.querySelector("b").textContent = o.name;
      b.querySelector("span").textContent = o.desc;
      b.style.setProperty("--c", "rgb(" + o.color.join(",") + ")");
      b.classList.toggle("on", i === me.choice);
      b.disabled = !!me.ready;
    });
    document.body.classList.toggle("locked", !!me.ready);
    var ok = $("choose-ok");
    ok.classList.toggle("is-ready", !!me.ready);
    ok.textContent = me.ready ? "PRONTO! (TOQUE P/ TROCAR)" : "CONFIRMAR";
    ok.dataset.tap = me.ready ? "cancel" : "confirm";
  }

  // ── campanha: loja no celular ──────────────
  // Só abre depois do ATACAR perto da banca. Um toque marca o item (aparece marcado na TV
  // também), COMPRAR compra. As doações viram uma linha só, que abre a escolha de quem recebe.
  var shopOpen = null;       // tipo da banca aberta (loja, ferreiro, altar)
  var shopPick = null;       // item marcado aqui no celular
  var shopServerPick = null; // último marcado que o jogo mandou
  var shopKey = "";
  var giftTo = null;
  var shopData = null;

  function shopRow(id) { return id && id.indexOf("doar:") === 0 ? "doar" : id; }

  function shopRows(shop) {
    var rows = [], gift = null;
    shop.items.forEach(function (it) {
      if (shopRow(it.id) === "doar") {
        if (!gift) {
          gift = { id: "doar", label: "DOAR " + it.cost + " ALMAS", cost: it.cost, ok: true,
                   afford: it.afford, color: "#c8aaff", desc: "passa almas para um companheiro" };
          rows.push(gift);
        }
      } else {
        rows.push(it);
      }
    });
    return rows;
  }

  function order(item, buy) {
    post("/api/shop", { slot: slot, token: token, item: item, buy: !!buy }).catch(function () {});
    setTimeout(refresh, 90);
  }

  function renderShop(shop) {
    shopData = shop;
    var rows = shopRows(shop);
    if (shopOpen !== shop.kind) {          // acabou de abrir
      shopOpen = shop.kind;
      shopPick = shopRow(shop.picked);
      shopServerPick = shop.picked;
      giftTo = null;
      $("view-shop").classList.remove("gifting");
      $("shop-note").textContent = "";
    } else if (shop.picked !== shopServerPick) {
      shopServerPick = shop.picked;        // mexeram pelo analógico na TV
      if (shopRow(shop.picked) !== shopPick && !$("view-shop").classList.contains("gifting")) {
        shopPick = shopRow(shop.picked);
      }
    }
    if (!rows.some(function (r) { return r.id === shopPick; })) shopPick = rows.length ? rows[0].id : null;
    $("shop-title").textContent = shop.title;
    $("shop-souls").textContent = shop.souls;
    var key = JSON.stringify(rows) + "|" + shopPick;
    if (key !== shopKey) {
      shopKey = key;
      var list = $("shop-list");
      list.innerHTML = "";
      rows.forEach(function (r) {
        var b = document.createElement("button");
        b.className = "shop-item" + (r.id === shopPick ? " on" : "") + (r.ok && r.afford ? "" : " off");
        b.style.setProperty("--c", r.color);
        b.innerHTML = "<span></span><i></i>";
        b.firstChild.textContent = r.label;
        b.lastChild.textContent = r.cost ? r.cost : "";
        b.addEventListener("pointerdown", function (e) {
          e.preventDefault();
          buzz();
          shopPick = r.id;
          $("shop-note").textContent = "";
          order(r.id === "doar" ? shopData.items.filter(function (it) { return shopRow(it.id) === "doar"; })[0].id : r.id, false);
          renderShop(shopData);
        });
        list.appendChild(b);
      });
    }
    var cur = rows.filter(function (r) { return r.id === shopPick; })[0];
    var name = $("shop-name");
    name.textContent = cur ? cur.label : "";
    name.style.setProperty("--c", cur ? cur.color : "");
    $("shop-desc").textContent = cur ? cur.desc.toUpperCase() : "";
    $("shop-cost").textContent = cur && cur.cost ? cur.cost + " ALMAS" : cur ? "GRÁTIS" : "";
    $("shop-left").textContent = cur && cur.cost && cur.afford ? "SOBRAM " + (shop.souls - cur.cost) : "";
    var buy = $("shop-buy");
    buy.disabled = !cur || !cur.ok || !cur.afford;
    buy.textContent = shop.kind === "altar" ? "ESCOLHER" : cur && cur.id === "doar" ? "DOAR…" : "COMPRAR";
    if (cur && !cur.ok) $("shop-note").textContent = "INDISPONÍVEL";
    else if (cur && !cur.afford) $("shop-note").textContent = "FALTAM " + (cur.cost - shop.souls) + " ALMAS";
    renderGift(shop);
  }

  function renderGift(shop) {
    var mates = shop.mates || [];
    var gift = shop.items.filter(function (it) { return shopRow(it.id) === "doar"; })[0];
    var list = $("gift-list");
    var key = JSON.stringify(mates) + "|" + giftTo;
    if (list.dataset.key !== key) {
      list.dataset.key = key;
      list.innerHTML = "";
      mates.forEach(function (m) {
        var b = document.createElement("button");
        b.className = "gift-card" + (m.slot === giftTo ? " on" : "");
        b.dataset.slot = m.slot;
        b.innerHTML = "<b></b><span></span><em></em>";
        b.children[0].textContent = m.label + " · " + m.name;
        b.children[1].textContent = m.souls + " ALMAS";
        b.children[2].textContent = "FICA COM " + (m.souls + (gift ? gift.cost : 0));
        b.addEventListener("pointerdown", function (e) {
          e.preventDefault();
          buzz();
          giftTo = m.slot;
          renderGift(shopData);
        });
        list.appendChild(b);
      });
    }
    var ok = $("gift-ok");
    ok.disabled = giftTo === null || !gift || !gift.afford;
    ok.textContent = giftTo === null ? "DOAR" : "DOAR PARA P" + giftTo;
  }

  function onPress(el, fn) {
    el.addEventListener("pointerdown", function (e) {
      e.preventDefault();
      if (el.disabled) return;
      buzz();
      el.classList.add("down");
      fn();
    });
    ["pointerup", "pointercancel", "pointerleave"].forEach(function (t) {
      el.addEventListener(t, function () { el.classList.remove("down"); });
    });
  }

  onPress($("shop-close"), function () { order("fechar", false); });
  onPress($("shop-buy"), function () {
    if (shopPick === "doar") {
      giftTo = null;
      $("view-shop").classList.add("gifting");
      renderGift(shopData);
      return;
    }
    order(shopPick, true);
    $("shop-note").textContent = "PEDIDO ENVIADO";
    if (navigator.vibrate) navigator.vibrate([10, 40, 20]);
  });
  onPress($("gift-back"), function () { $("view-shop").classList.remove("gifting"); });
  onPress($("gift-ok"), function () {
    order("doar:" + giftTo, true);
    $("view-shop").classList.remove("gifting");
    $("shop-note").textContent = "DOOU PARA P" + giftTo;
    if (navigator.vibrate) navigator.vibrate([10, 40, 20]);
  });

  // ── estado do jogo ─────────────────────────
  var WAIT_TEXT = {
    menu: ["Conectado", "Aguardando o anfitrião escolher o modo de jogo."],
    lobby: ["Conectado", "Tudo certo! O anfitrião vai avançar para a escolha de personagens."],
    choose: ["Conectado", "Os jogadores estão escolhendo as melhorias."],
    paused: ["Pausado", ""],
  };

  function render() {
    if (!status) return;
    var me = status.me || {};
    if (!me.owner) {
      if (joined) { joined = false; join(slot).catch(function () {}); }
      show("join");
      markTaken();
      return;
    }
    var mode = status.mode;
    var modeName = mode === "soccer" ? "FUTEBOL" : mode === "campaign" ? "CAMPANHA" : "DUELO";
    if (mode !== "campaign" && (me.team === 0 || me.team === 1)) {
      modeName += " · TIME " + (me.team === 0 ? "AZUL" : "VERMELHO");   // 2 x 2
    }
    bind("mode", modeName);
    var phase = status.phase;
    $("results-actions").classList.toggle("on", phase === "results" && me.playing);
    $("story-actions").classList.toggle("on", phase === "story" && me.playing);
    if (status.roster && status.roster !== roster.length) loadRoster();   // personagem novo liberado

    if (phase === "playing" && me.playing && me.shop) {
      if (!$("view-shop").classList.contains("on")) releaseAll();   // nada fica segurado com a loja aberta
      show("shop");
      renderShop(me.shop);
      return;
    }
    shopOpen = null;
    if (phase === "penalty" && me.playing && me.penalty) {
      if (!$("view-penalty").classList.contains("on")) releaseAll();
      show("penalty");
      renderPenalty(me.penalty);
      return;
    }
    if ((phase === "playing" || phase === "paused") && me.playing) {
      show("pad");
      soccerMode = mode === "soccer";
      document.body.classList.toggle("soccer", soccerMode);
      document.querySelectorAll(".battle-only").forEach(function (e) { e.classList.toggle("on", mode !== "soccer"); });
      document.querySelectorAll(".soccer-only").forEach(function (e) { e.classList.toggle("on", mode === "soccer"); });
      useHud(status.hud || (soccerMode ? "soccer" : "battle"));
      $("pad-hint").textContent = soccerMode ? "empurre até a borda para correr" : "mova o analógico";
      document.querySelectorAll(".battle-only").forEach(function (e) { e.classList.toggle("on", mode !== "soccer"); });
      document.querySelectorAll(".soccer-only").forEach(function (e) { e.classList.toggle("on", mode === "soccer"); });
      $("paused").classList.toggle("on", phase === "paused");
      var ch = roster[me.char];
      var sb = $("super-btn");
      var superName = (ch && ch.soccer_power ? ch.soccer_power : "SUPER").toUpperCase();
      if (sb.dataset.label !== superName) sb.dataset.label = superName;
      layoutButtons();
      var cd = me.cooldown || 0;
      sb.style.setProperty("--p", (1 - cd).toFixed(3));
      sb.classList.toggle("cooling", cd > 0);
      sb.classList.toggle("ready", cd <= 0);
      renderAmmo(me, mode);
      renderSouls(me);
      var vote = me.vote || 0;                 // 1 = falta confirmar o teletransporte, 2 = confirmado
      var vb = $("vote-btn");
      vb.classList.toggle("on", vote > 0 && phase === "playing");
      vb.classList.toggle("is-ready", vote === 2);
      var vtext = vote === 2 ? "PRONTO! ESPERANDO OS OUTROS" : "TELETRANSPORTE DE FASE";
      if (vb.textContent !== vtext) vb.textContent = vtext;
      vb.disabled = vote === 2;
      var st = $("stick-stamina");
      st.style.setProperty("--st", (me.stamina === undefined ? 1 : me.stamina).toFixed(3));
      st.classList.toggle("tired", !!me.tired);
      return;
    }
    if (phase === "select" && me.playing) {
      show("select");
      renderSelect(me, mode);
      return;
    }
    if (phase === "choose" && me.playing) {
      show("choose");
      renderChoose(me);
      return;
    }
    show("wait");
    renderNews(phase === "news" ? status.news || [] : []);
    if (phase === "news") {
      bind("wait-title", status.banner || "Novidades");
      bind("wait-text", "Na TV: setas ou ENTER para virar as páginas.");
    } else if (phase === "story") {
      bind("wait-title", status.banner || "História");
      bind("wait-text", me.playing ? "Acompanhe a história na tela." : "");
    } else if (phase === "results") {
      bind("wait-title", status.banner || "Fim de jogo");
      bind("wait-text", me.playing ? "Escolha no jogo ou use os botões abaixo." : "");
    } else if (!me.playing && (phase === "select" || phase === "playing")) {
      bind("wait-title", "Fora desta partida");
      bind("wait-text", "Este modo não usa o jogador " + slot + ". Aguarde a próxima.");
    } else {
      var t = WAIT_TEXT[phase] || WAIT_TEXT.menu;
      bind("wait-title", t[0]);
      bind("wait-text", t[1]);
    }
  }

  // pênaltis: tocar numa casa da grade deixa o analógico apontado para ela (o canto vale na hora
  // do chute para quem bate, e na hora do PULAR para o goleiro). O meio é o analógico solto.
  var penCell = "0,1", penRole = null;
  function renderPenalty(pen) {
    var role = pen.role || "espera";
    if (role !== penRole) {
      penRole = role;
      setPenCell("0,1");
    }
    $("view-penalty").classList.toggle("espera", role === "espera");
    $("pen-bate").classList.toggle("on", role === "bate");
    $("pen-defende").classList.toggle("on", role === "defende");
    var title = role === "bate" ? "VOCÊ BATE" : role === "defende" ? "VOCÊ DEFENDE" : "PÊNALTIS";
    $("pen-title").textContent = title + " · " + (pen.hero || "");
    $("pen-hint").textContent = role === "bate" ? "TOQUE NO CANTO · SÓ VOCÊ VÊ"
      : role === "defende" ? "TOQUE NO LADO DO PULO" : "";
  }
  function setPenCell(cell) {
    penCell = cell;
    document.querySelectorAll(".pen-cell").forEach(function (b) { b.classList.toggle("on", b.dataset.cell === cell); });
    var parts = cell.split(",");
    var col = parseInt(parts[0], 10), row = parseInt(parts[1], 10);
    sendAxis(col, 1 - row);
  }
  document.querySelectorAll(".pen-cell").forEach(function (b) {
    onPress(b, function () { setPenCell(b.dataset.cell); });
  });

  // saldo de almas da campanha; quando aumenta, um "+N" sobe ao lado
  var lastSouls = null, gainTimer = 0;
  function renderSouls(me) {
    var box = $("souls");
    var on = me.souls !== null && me.souls !== undefined;
    box.classList.toggle("on", on);
    if (!on) { lastSouls = null; return; }
    var n = me.souls;
    if (lastSouls !== null && n !== lastSouls) {
      var gain = $("souls-gain");
      var diff = n - lastSouls;
      gain.textContent = (diff > 0 ? "+" : "") + diff;
      gain.classList.toggle("spent", diff < 0);
      gain.classList.remove("pop");
      void gain.offsetWidth;                   // reinicia a animação
      gain.classList.add("pop");
      box.classList.add("bump");
      clearTimeout(gainTimer);
      gainTimer = setTimeout(function () { box.classList.remove("bump"); }, 260);
    }
    lastSouls = n;
    var text = String(n);
    if ($("souls-n").textContent !== text) $("souls-n").textContent = text;
  }

  function renderAmmo(me, mode) {
    var btn = document.querySelector('.battle-only [data-act="attack"]');
    var badge = $("ammo-badge");
    if (!btn || !badge) return;
    var mag = me.mag || 0;
    var on = mode !== "soccer" && mag > 0;
    btn.classList.toggle("has-ammo", on);
    badge.classList.toggle("on", on);
    if (!on) return;
    var reloading = (me.reload || 0) > 0;
    var ammo = me.ammo || 0;
    btn.classList.toggle("reloading", reloading);
    btn.classList.toggle("extra", !reloading && ammo > mag);
    btn.style.setProperty("--a", (reloading ? me.reload : Math.min(1, ammo / mag)).toFixed(3));
    badge.classList.toggle("reloading", reloading);
    badge.classList.toggle("empty", !reloading && ammo <= 0);
    var text = reloading ? "RECARGA" : ammo <= 0 ? "VAZIO" : ammo + "/" + mag;
    if (badge.textContent !== text) badge.textContent = text;
  }

  function renderNews(lines) {
    var list = $("news-list");
    var key = lines.join("\n");
    if (list.dataset.key === key) return;
    list.dataset.key = key;
    list.innerHTML = "";
    lines.forEach(function (line) {
      var li = document.createElement("li");
      li.textContent = line;
      list.appendChild(li);
    });
  }

  function markTaken() {
    if (!status) return;
    document.querySelectorAll(".slot").forEach(function (b) {
      var s = status.slots[b.dataset.slot];
      b.classList.toggle("taken", !!(s && s.connected && !(status.me && status.me.owner && b.dataset.slot == slot)));
    });
  }

  function refresh() {
    var q = "/api/status?slot=" + (slot || 0) + "&token=" + encodeURIComponent(token);
    var t0 = performance.now();
    return fetch(q, { cache: "no-store" })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var ms = performance.now() - t0;          // o status também mede o sinal
        rtt = rtt === null ? ms : rtt * 0.8 + ms * 0.2;
        netFails = 0;
        failures = 0;
        $("offline").classList.remove("on");
        status = data;
        render();
      })
      .catch(function () {
        netFails += 1;
        failures += 1;
        if (failures > 3) $("offline").classList.add("on");
      });
  }

  var loadingRoster = false;
  function loadRoster() {
    if (loadingRoster) return;
    loadingRoster = true;
    fetch("/api/roster", { cache: "no-store" }).then(function (r) { return r.json(); }).then(function (data) {
      roster = data;
      loadingRoster = false;
      render();
    }).catch(function () { loadingRoster = false; });
  }
  loadRoster();

  if (slot) {
    document.body.dataset.slot = slot;
    bind("tag", "P" + slot);
    join(slot).then(function (ok) { if (!ok) show("join"); refresh(); });
  } else {
    show("join");
    refresh();
  }
  setInterval(refresh, 400);
})();
