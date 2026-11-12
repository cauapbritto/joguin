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
  var views = ["join", "wait", "select", "pad", "choose", "shop", "penalty", "pc"];

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

  // Vibração por evento: o jogo manda [contador, padrão] e o celular vibra quando o contador muda.
  // O iPhone não tem navigator.vibrate: aí nada acontece (e nada quebra). O botão VIBRAR vale aqui também.
  var BUZZ_PATTERNS = {
    hit: [30], big_hit: [70], score: [80, 40, 80], super: [20],
    call: [60, 80, 60, 80, 60], tick: [15], go: [140]
  };
  var lastBuzz = null;
  function vibrateFor(b) {
    if (!b || b.length < 2) return;
    var first = lastBuzz === null;
    if (b[0] === lastBuzz) return;
    lastBuzz = b[0];
    if (first) return;                 // ao abrir a página não vibra pelo que já passou
    if (!navigator.vibrate || (hud && hud.vibrate === false)) return;
    var pattern = BUZZ_PATTERNS[b[1]];
    if (pattern) navigator.vibrate(pattern);
  }

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

  // ── tela de novidades: < PULAR > ──
  document.querySelectorAll("[data-news]").forEach(function (el) {
    el.addEventListener("pointerdown", function (e) {
      e.preventDefault();
      buzz();
      el.classList.add("down");
      newsTap(el.dataset.news);
    });
    ["pointerup", "pointercancel", "pointerleave"].forEach(function (t) {
      el.addEventListener(t, function () { el.classList.remove("down"); });
    });
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
  var faceChar = null;

  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

  // nome embaixo do botão (8 px, sempre legível) e o desenho dentro em escala inteira: 48 no grande, 32 nos outros
  function setLabel(b, size) {
    var lbl = b.querySelector(".pbl");
    if (lbl && b.dataset.label && lbl.textContent !== b.dataset.label) lbl.textContent = b.dataset.label;
    b.style.setProperty("--is", (size >= 96 ? 48 : 32) + "px");
  }

  function layoutButtons() {
    var zr = btnZone.getBoundingClientRect();
    if (!zr.width || !zr.height) return;
    var vh = window.innerHeight;
    var big = clamp(vh * 0.31, 84, 128);
    document.querySelectorAll(".pad-set").forEach(function (set) {
      var hasOuter = !!set.querySelector('.pb:not(.hidden)[data-pos="ww"], .pb:not(.hidden)[data-pos="nn"]');
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
          badge.style.top = Math.max(0, y - size / 2 - 22) + "px";          // contador em cima; o nome vai embaixo
        }
        if (!b.dataset.label) b.dataset.label = (b.querySelector(".pbl") || b).textContent;
        setLabel(b, size);
      });
    });
  }
  window.addEventListener("resize", layoutButtons);
  window.addEventListener("orientationchange", function () { setTimeout(layoutButtons, 250); });

  var fingers = {};       // dedo → botão que ele está segurando
  var holdCount = {};     // ação → quantos dedos estão nela

  function padButtons() {
    return Array.prototype.slice.call(document.querySelectorAll(".pad-set.on .pb:not(.hidden)"));
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
    var por = $("portrait");
    if (!por.classList.contains("ic")) {                 // herói em escala inteira no pedestal
      por.classList.add("ic");
      por.dataset.max = "3";
      por.dataset.pad = "16";
      por.addEventListener("load", function () { fitIcon(por); });
    }
    if (por.getAttribute("src") !== "/sprite/" + me.char + ".png") por.src = "/sprite/" + me.char + ".png";
    $("char-name").textContent = ch.name.toUpperCase();
    var maxHp = 250, maxSpeed = 5, maxDmg = 28;
    var rows = mode === "soccer"
      ? [["VELOCIDADE", ch.speed / maxSpeed]]
      : [["VIDA", ch.hp / maxHp], ["VELOCIDADE", ch.speed / maxSpeed],
         ["DANO", Math.max.apply(null, ch.weapons.map(function (w) { return w.damage; })) / maxDmg]];
    $("stats").innerHTML = rows.map(function (r) {
      var pct = Math.max(10, Math.round(Math.min(1, r[1]) * 10) * 10);      // em quadradinhos de 10%
      return "<span>" + r[0] + '</span><span class="bar"><i style="width:' + pct + "%;--seg:" + (1000 / pct) + '%"></i></span>';
    }).join("");
    var weapon = ch.weapons[me.weapon] || ch.weapons[0];
    var gun = ch.weapons.filter(function (w) { return !w.melee; })[0];
    var basket = mode === "soccer" && status && status.hud === "basket";
    $("ability").innerHTML = basket
      ? "<b>SUPER: " + (ch.basket_power || "") + "</b>" + (ch.basket_desc || "") +
        (ch.basket_passive ? "<br><b>SEMPRE:</b>" + ch.basket_passive : "")
      : mode === "soccer"
      ? "<b>SUPER: " + (ch.soccer_power || "") + "</b>" + (ch.soccer_desc || "") +
        (ch.soccer_passive ? "<br><b>SEMPRE: " + ch.soccer_passive.toUpperCase() + "</b>" + ch.soccer_passive_desc : "")
      : "<b>" + ch.ability.toUpperCase() + "</b>" + ch.ability_desc +
        (gun && gun.note ? "<br><b>" + gun.name.toUpperCase() + " (" + gun.mag + " TIROS)</b>" + gun.note : "");
    $("weapon").style.display = mode === "soccer" ? "none" : "";
    var wkey = weapon.name + "|" + weapon.icon;
    var wb = $("weapon");
    if (wb.dataset.key !== wkey) {
      wb.dataset.key = wkey;
      wb.textContent = "";
      if (weapon.icon) {
        var ws = el("span", "slotpic");
        ws.appendChild(pixImg("/arma/" + weapon.icon, { max: 1, pad: 4 }));
        wb.appendChild(ws);
      }
      wb.appendChild(document.createTextNode(weapon.name.toUpperCase() + (weapon.melee ? " · PERTO" : " · TIRO")));
    }
    var ready = $("ready-btn");
    ready.classList.toggle("is-ready", me.ready);
    ready.textContent = me.ready ? "PRONTO! (TOQUE P/ CANCELAR)" : "PRONTO";
    ready.dataset.tap = me.ready ? "cancel" : "confirm";
    document.querySelectorAll("#view-select .arrow, #weapon").forEach(function (b) { b.disabled = me.ready; });
  }

  // desenho da melhoria pelo que ela faz
  function upgradeIcon(o) {
    var t = ((o.name || "") + " " + (o.desc || "")).toUpperCase();
    if (/VIDA|PELE|CURA|REGENER/.test(t)) return "coracao";
    if (/ALMA/.test(t)) return "alma";
    if (/ENERGIA|RAIO/.test(t)) return "raio";
    if (/DANO|GOLPE|TIRO|ATIRA|PENTE|GATILHO/.test(t)) return "atacar";
    if (/ESQUIV|VELOC|RÁPID|CORR/.test(t)) return "esquiva";
    return "habilidade";
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
      b.style.setProperty("--ic", "url(/static/ic/i_" + upgradeIcon(o) + ".png)");
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
  // também), COMPRAR compra. As doações viram uma linha só, que abre a escolha de quem recebe,
  // e os três encantos de uma arma viram uma linha só, com os encantos em botões no detalhe.
  // Cada linha mostra a imagem da arma; no ferreiro, o detalhe mostra a arma de agora e no que ela vira.
  var shopOpen = null;       // tipo da banca aberta (loja, ferreiro, altar)
  var shopPick = null;       // linha marcada aqui no celular
  var shopServerPick = null; // último item marcado que o jogo mandou
  var shopKey = "";
  var shopKeyPick = null;
  var cacosPage = "home";              // loja de cacos no celular: "home" (seções) ou "skins"
  var cupomText = "";
  var giftTo = null;
  var shopData = null;
  var shopEnergy = [0, 0];   // energia e barra cheia de quem está na banca
  var encPick = {};          // arma → id do encanto marcado

  function shopRow(id) {
    if (!id) return id;
    if (id.indexOf("doar:") === 0) return "doar";
    if (id.indexOf("encanto:") === 0) return id.slice(0, id.lastIndexOf(":"));
    return id;
  }

  function shopRows(shop) {
    var rows = [], seen = {};
    shop.items.forEach(function (it) {
      var row = shopRow(it.id);
      if (row === "doar") {
        if (!seen.doar) {
          seen.doar = { id: "doar", label: "DOAR ALMAS", cost: it.cost, ok: true, afford: it.afford,
                        color: "#c8aaff", desc: "passa almas para um companheiro", items: [it],
                        info: { sub: "PARA UM AMIGO" } };
          rows.push(seen.doar);
        }
      } else if (row !== it.id) {          // encantos da mesma arma
        if (!seen[row]) {
          seen[row] = { id: row, label: it.info.weapon.name, cost: it.cost, ok: it.ok, afford: it.afford,
                        color: it.info.weapon.color, desc: it.desc, items: [], info: it.info };
          rows.push(seen[row]);
        }
        seen[row].items.push(it);
      } else {
        rows.push(it);
      }
    });
    return rows;
  }

  // o id que vai para o jogo quando a linha está marcada
  function rowItem(r) {
    if (!r) return null;
    if (r.id === "doar") return r.items[0].id;
    if (r.items) {
      var pick = encPick[r.id];
      return r.items.some(function (it) { return it.id === pick; }) ? pick : r.items[0].id;
    }
    return r.id;
  }

  function rowEntry(r) {
    if (!r || !r.items || r.id === "doar") return r;
    var id = rowItem(r);
    return r.items.filter(function (it) { return it.id === id; })[0];
  }

  function order(item, buy) {
    post("/api/shop", { slot: slot, token: token, item: item, buy: !!buy }).catch(function () {});
    setTimeout(refresh, 90);
  }

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined && text !== null) e.textContent = text;
    return e;
  }

  // ── desenhos em pixel: sempre em escala inteira (1x, 2x, 3x...), do tamanho que couber ──
  // Vale para qualquer arma (as de hoje e as novas), skin ou pet, de qualquer formato.
  function fitIcon(img) {
    var box = img.parentElement;
    if (!box || !img.naturalWidth) return;
    var pad = +(img.dataset.pad || 8), dv = +(img.dataset.div || 1), max = +(img.dataset.max || 4);
    var bw = box.clientWidth - pad, bh = box.clientHeight - pad;
    if (bw <= 0 || bh <= 0) return;
    var nw = img.naturalWidth / dv, nh = img.naturalHeight / dv;
    var k = Math.min(bw / nw, bh / nh, max);
    k = k >= 1 ? Math.floor(k) : 1 / Math.ceil(1 / k);       // grande demais: reduz por um divisor inteiro
    img.style.width = Math.round(nw * k) + "px";
    img.style.height = Math.round(nh * k) + "px";
  }
  function fitIcons(root) {
    (root || document).querySelectorAll("img.ic").forEach(fitIcon);
  }
  window.addEventListener("resize", function () { setTimeout(function () { fitIcons(); }, 60); });

  function pixImg(src, opts) {
    var img = el("img", "ic");
    opts = opts || {};
    if (opts.div) img.dataset.div = opts.div;
    if (opts.max) img.dataset.max = opts.max;
    if (opts.pad !== undefined) img.dataset.pad = opts.pad;
    img.alt = "";
    img.draggable = false;
    img.addEventListener("load", function () { fitIcon(img); });
    img.src = src;
    return img;
  }

  // retratos das skins chegam ampliados 3x: o encaixe volta ao pixel de verdade
  function picDiv(src) { return src && src.indexOf("/skin/") === 0 ? 3 : 1; }

  // imagem da arma num quadrinho (silhueta quando a receita da fusão ainda é segredo)
  function weaponPic(card, cls, secret, max) {
    var box = el("span", cls + (secret ? " sil" : ""));
    if (card && card.color) box.style.setProperty("--r", card.color);
    if (card && card.icon) box.appendChild(pixImg("/arma/" + card.icon, { max: max || 3, pad: 6 }));
    return box;
  }

  function levelPips(level) {
    var pips = el("span", "lvls");
    for (var k = 0; k < 3; k++) pips.appendChild(el("i", k < level ? "f" : ""));
    return pips;
  }

  function rowThumb(r) {
    var info = r.info || {};
    if (info.type === "arma" || info.type === "forja" || info.type === "encanto") return weaponPic(info.weapon, "thumb");
    if (info.type === "fusao") return weaponPic(info.next, "thumb", !info.known);
    var box = el("span", "thumb");
    if (info.img) {
      box.appendChild(pixImg(info.img, { div: picDiv(info.img), max: 3, pad: 6 }));
      return box;
    }
    var kinds = { pocao: 1, energia: 1, arma: 1, trocar: 1, "continue": 1, doar: 1 };
    box.appendChild(el("i", "pxi " + (info.type === "cupom" ? "cupom" : kinds[r.id] ? r.id : "outro")));
    return box;
  }

  function rowLabel(r) {
    var info = r.info || {};
    if (info.type === "forja" || info.type === "encanto") {
      var w = info.weapon;
      return w.name + (w.level ? " +" + w.level : "") + (w.enchant ? " " + w.enchant : "");
    }
    if (info.type === "fusao") return "FUNDIR AS 3";
    if (info.hero && r.label.indexOf(info.hero + " ") === 0) return r.label.slice(info.hero.length + 1);   // a skin sem o nome do herói
    return r.label;
  }

  // carimbo curto do que não dá para comprar
  function stampOf(r) {
    var sub = ((r.info && r.info.sub) || "").toUpperCase();
    if (sub.indexOf("CHEIA") >= 0) return "CHEIA";
    if (sub.indexOf("VENDIDA") >= 0) return "VENDIDA";
    if (sub.indexOf("JÁ TEM") >= 0 && sub.indexOf("GRUPO") < 0) return "JÁ É SUA";
    if (sub && sub.length <= 10) return sub;
    return "NO MÁXIMO";
  }

  function card(r, unit) {
    var info = r.info || {};
    var w = info.weapon || (info.type === "fusao" ? info.next : null);
    var off = !(r.ok && r.afford);
    var b = el("button", "shop-item" + (r.id === shopPick ? " on" : "") + (off ? " off" : ""));
    b.style.setProperty("--c", r.color);
    b.style.setProperty("--r", w ? w.color : r.color);
    var thumb = rowThumb(r);
    b.appendChild(thumb);
    var rar = w ? w.rarity : info.tier === "rara" ? "RARA" : null;
    if (rar && rar !== "COMUM") b.appendChild(el("span", "rar", info.type === "fusao" ? "FORJADA" : rar));
    if (info.type === "forja" || info.type === "encanto") b.appendChild(levelPips(info.weapon.level));
    if (!r.ok && r.cost && !info.state) thumb.appendChild(el("span", "carimbo", stampOf(r)));
    b.appendChild(el("span", "name", rowLabel(r)));
    var price = el("span", "price");
    if (info.state) {                                       // loja de CACOS e armário: etiqueta (300, VESTIDA, CUPOM...)
      b.dataset.tier = info.tier || "";
      b.dataset.state = info.state;
      if (info.mine) b.dataset.mine = "1";
      if (info.state === "comprar") price.appendChild(el("b", "gem"));
      price.appendChild(document.createTextNode(info.tag || ""));
    } else if (r.cost) {
      price.appendChild(el("b", "gem"));
      price.appendChild(document.createTextNode(r.cost));
    } else {
      price.textContent = shopData && shopData.kind === "altar" ? "ESCOLHER" : "GRÁTIS";
    }
    b.appendChild(price);
    return b;
  }

  // barra em 10 quadradinhos: o que tem agora em branco e o ganho piscando em verde
  function segs(before, after, max) {
    var s = el("span", "segs");
    var on = Math.max(0, Math.min(10, Math.round(before / max * 10)));
    var up = after ? Math.max(0, Math.min(10, Math.round(after / max * 10)) - on) : 0;
    if (after && after > before && !up) up = on < 10 ? 1 : 0;
    for (var k = 0; k < 10; k++) s.appendChild(el("i", k < on ? "on" : k < on + up ? "up" : ""));
    return s;
  }

  function statLine(grid, name, before, after, max) {
    grid.appendChild(el("span", "k", name));
    if (typeof before !== "number") {
      var v0 = el("span", "v", before);
      v0.style.gridColumn = "span 2";
      grid.appendChild(v0);
      return;
    }
    grid.appendChild(segs(before, after, max || 60));
    var v = el("span", "v", String(before));
    if (after !== undefined && after !== null && after !== before) {
      v.appendChild(document.createTextNode(" "));
      v.appendChild(el("span", "up", String(after)));
    }
    grid.appendChild(v);
  }

  function energyText(card) {
    if (!card || card.energy === null || card.energy === undefined) return null;
    if (!card.energy) return "GRÁTIS";
    return card.energy + " POR " + (card.melee ? "GOLPE" : "TIRO");
  }

  function titleLine(name, tag, color) {
    var line = el("div", "dline");
    var b = el("b", "", name);
    if (name.length > 17) b.style.fontSize = "8px";              // nome comprido desce para 8 px em vez de cortar
    b.style.color = color;
    line.appendChild(b);
    if (tag) {
      var t = el("span", "tagr", tag);
      t.style.color = color;
      line.appendChild(t);
    }
    return line;
  }

  function pedestal(children) {
    var p = el("div", "pedestal");
    children.forEach(function (c) { p.appendChild(c); });
    return p;
  }

  function renderDetail(r, cur) {
    var box = $("shop-detail");
    box.innerHTML = "";
    box.style.removeProperty("--r");
    if (!r) return;
    var info = r.info || {};
    var grid;
    if (info.type === "arma") {
      var w = info.weapon;
      box.style.setProperty("--r", w.color);
      box.appendChild(pedestal([weaponPic(w, "box glow", false, 3)]));
      box.appendChild(titleLine(w.name, w.rarity + " · " + (w.melee ? "PERTO" : "TIRO"), w.color));
      if (info.owner) box.appendChild(el("span", "dnote", "DO " + info.owner));
      grid = el("div", "cmp");
      statLine(grid, "DANO", w.damage);
      if (w.mag) statLine(grid, "PENTE", w.mag, null, 30);
      if (energyText(w)) statLine(grid, "ENERGIA", energyText(w));
      box.appendChild(grid);
      if (info.out) {
        var hand = el("div", "hand");
        hand.appendChild(el("span", "", "TROCA"));
        hand.appendChild(weaponPic(info.out, "slotpic out", false, 1));
        hand.appendChild(el("em", "seta", ">"));
        hand.appendChild(weaponPic(w, "slotpic in", false, 1));
        hand.appendChild(el("span", "", "SAI: " + info.out.name));
        box.appendChild(hand);
      }
    } else if (info.type === "forja" || info.type === "encanto") {
      var it = info.type === "encanto" ? (cur.info || info) : info;
      var now = it.weapon, next = it.next;
      var color = now.color;
      box.style.setProperty("--r", color);
      var pics = [weaponPic(now, "box sm", false, 2)];
      if (next) {
        pics.push(el("em", "seta", ">"));
        var pic = weaponPic(next, "box glow" + (next.enchant ? " fx-" + it.enchant.key : ""), false, 3);
        pic.appendChild(el("span", "badge", "+" + next.level));
        pics.push(pic);
      }
      box.appendChild(pedestal(pics));
      var label = now.name + (now.level ? " +" + now.level : "");
      box.appendChild(titleLine(next ? label + " > +" + next.level + (next.enchant ? " " + next.enchant : "")
                                     : label + " · NO MÁXIMO", now.rarity, color));
      if (info.type === "encanto") {
        var chips = el("div", "chips");
        r.items.forEach(function (opt) {
          var en = opt.info.enchant;
          var c = el("button", "chip" + (opt.id === cur.id ? " on" : ""));
          c.style.setProperty("--c", en.color);
          c.appendChild(el("span", "", en.name));
          c.appendChild(el("small", "", en.desc));
          c.addEventListener("pointerdown", function (e) {
            e.preventDefault();
            buzz();
            encPick[r.id] = opt.id;
            $("shop-note").textContent = "";
            order(opt.id, false);
            renderShop(shopData);
          });
          chips.appendChild(c);
        });
        box.appendChild(chips);
      }
      grid = el("div", "cmp");
      statLine(grid, "DANO", now.damage, next ? next.damage : null);
      if (now.mag) statLine(grid, "PENTE", now.mag, next ? next.mag : null, 30);
      if (energyText(now)) statLine(grid, "ENERGIA", energyText(now));
      box.appendChild(grid);
    } else if (info.type === "fusao") {
      var out = info.next;
      box.style.setProperty("--r", out.color);
      var mini = el("span", "mini");
      info.inputs.forEach(function (c) { mini.appendChild(weaponPic(c, "slotpic", false, 1)); });
      var big = weaponPic(out, "box" + (info.known ? " glow" : ""), !info.known, 2);
      if (info.known && out.level) big.appendChild(el("span", "badge", "+" + out.level));
      box.appendChild(pedestal([mini, el("em", "seta", ">"), big]));
      var name = info.known ? out.name + (out.level ? " +" + out.level : "")
                            : "???" + (info.family ? " TIPO " + info.family : "");
      box.appendChild(titleLine(name, "FORJADA", out.color));
      if (info.note) box.appendChild(el("p", "dnote", info.note));
      if (info.known) {
        grid = el("div", "cmp");
        statLine(grid, "DANO", out.damage);
        if (energyText(out)) statLine(grid, "ENERGIA", energyText(out));
        box.appendChild(grid);
      }
      box.appendChild(el("p", "dnote", "AS 3 SOMEM E AS SUAS VOLTAM AO +0."));
    } else if (info.type === "skin") {      // loja de CACOS e armário: a skin ou o pet
      box.style.setProperty("--r", r.color);
      var sp = el("span", "box");
      sp.style.height = "100%";
      if (info.img) sp.appendChild(pixImg(info.img, { div: picDiv(info.img), max: 3, pad: 4 }));
      box.appendChild(pedestal([sp]));
      box.lastChild.style.flex = "1 1 120px";
      box.lastChild.style.maxHeight = "none";
      box.appendChild(titleLine(r.label, info.rarity, r.color));
      box.appendChild(el("p", "dnote", info.hero + " · " + (r.desc || "").toUpperCase()));
      if (info.sub) box.appendChild(el("p", "dnote", info.sub));
    } else if (info.type === "cupom") {     // loja de CACOS: digitar o cupom
      box.style.setProperty("--r", r.color);
      var nb2 = el("b", "", "INSERIR CUPOM");
      nb2.style.color = r.color;
      box.appendChild(nb2);
      var input = el("input", "cupom-input");
      input.id = "cupom-input";
      input.type = "text";
      input.maxLength = 40;
      input.placeholder = "DIGITE O CUPOM";
      input.autocomplete = "off";
      input.autocapitalize = "characters";
      input.spellcheck = false;
      input.value = cupomText;
      input.addEventListener("input", function () { cupomText = input.value; });
      input.addEventListener("keydown", function (e) {
        if (e.key === "Enter") { e.preventDefault(); sendCupom(); }
      });
      box.appendChild(input);
      box.appendChild(el("p", "dnote", "CADA CUPOM VALE UMA VEZ E DÁ CACOS. ALGUNS DÃO UMA SKIN RARA JUNTO."));
      if (info.note) box.appendChild(el("p", "dnote cupom-note", info.note));
    } else if (info.type === "tela") {      // computador da casa: o que está na tela agora
      var tela = el("div", "tela tela-" + (info.look || "pc"));
      (info.lines || []).forEach(function (line) { tela.appendChild(el("div", "tl", line || " ")); });
      box.appendChild(tela);
    } else {
      var px = el("span", "box");
      px.appendChild(el("i", "pxi " + ({ pocao: 1, energia: 1, arma: 1, trocar: 1, "continue": 1, doar: 1 }[r.id] ? r.id : "outro")));
      px.firstChild.style.width = px.firstChild.style.height = "48px";
      px.firstChild.style.backgroundSize = "48px";
      box.appendChild(pedestal([px]));
      box.appendChild(titleLine(r.label, info.sub || "", r.color));
      box.appendChild(el("p", "dnote", (r.desc || "").toUpperCase()));
    }
    fitIcons(box);
  }

  function shopUnit() {
    return (shopData && shopData.unit) || "ALMAS";
  }

  function sendCupom() {
    var code = (cupomText || "").trim();
    if (!code) {
      $("shop-note").textContent = "DIGITE O CUPOM";
      return;
    }
    var input = $("cupom-input");
    if (input) input.blur();
    order("cupom:" + code, true);
    cupomText = "";
    shopKey = "";
    $("shop-note").textContent = "CUPOM ENVIADO";
    if (navigator.vibrate) navigator.vibrate([10, 40, 20]);
  }

  function renderShop(shop) {
    shopData = shop;
    var rows = shopRows(shop);
    var view = $("view-shop");
    if (shopOpen !== shop.kind) {          // acabou de abrir
      shopOpen = shop.kind;
      cacosPage = !shop.picked || shop.picked === "cupom" ? "home" : shop.picked.indexOf("pet:") === 0 ? "pets" : "skins";
      shopPick = shopRow(shop.picked);
      shopServerPick = shop.picked;
      encPick = {};
      if (shopPick !== shop.picked && shopPick !== "doar") encPick[shopPick] = shop.picked;
      giftTo = null;
      view.classList.remove("gifting");
      $("shop-note").textContent = "";
    } else if (shop.picked !== shopServerPick) {
      shopServerPick = shop.picked;        // mexeram pelo analógico na TV
      if (shop.kind === "cacos" && shop.picked !== "cupom")
        cacosPage = shop.picked.indexOf("pet:") === 0 ? "pets" : "skins";
      var row = shopRow(shop.picked);
      if (rowItem(rows.filter(function (r) { return r.id === shopPick; })[0]) !== shop.picked &&
          !view.classList.contains("gifting")) {
        shopPick = row;
        if (row !== shop.picked && row !== "doar") encPick[row] = shop.picked;
      }
    }
    if (!rows.some(function (r) { return r.id === shopPick; })) shopPick = rows.length ? rows[0].id : null;
    view.dataset.kind = shop.kind;
    $("shop-title").textContent = shop.title;
    $("shop-souls").textContent = shop.souls;
    $("shop-unit").textContent = shopUnit();
    var energy = $("shop-energy");
    energy.hidden = !(shopEnergy[1] > 0) || shop.kind === "altar";
    $("shop-energy-n").textContent = shopEnergy[0];
    $("shop-energy-max").textContent = "/" + shopEnergy[1];
    var cur = rowEntry(rows.filter(function (r) { return r.id === shopPick; })[0]);
    var key = JSON.stringify(rows) + "|" + shopPick + "|" + (cur ? cur.id : "") + "|" + shop.souls + "|" + cacosPage;
    if (document.activeElement && document.activeElement.id === "cupom-input" && shopPick === "cupom" &&
        shopKeyPick === "cupom") key = shopKey;   // não apaga o que está sendo digitado
    if (key !== shopKey) {
      shopKey = key;
      shopKeyPick = shopPick;
      var list = $("shop-list");
      list.innerHTML = "";
      list.dataset.page = shop.kind === "cacos" ? cacosPage : "";
      if (shop.kind === "cacos") cacosHead(list, shop, rows);
      var shown = 0;
      rows.forEach(function (r) {
        if (shop.kind === "cacos" && (r.id === "cupom" || !r.info || r.info.section !== cacosPage)) return;
        var b = card(r);
        b.addEventListener("pointerdown", function (e) {
          e.preventDefault();
          buzz();
          shopPick = r.id;
          $("shop-note").textContent = "";
          order(rowItem(r), false);
          renderShop(shopData);
        });
        list.appendChild(b);
        shown += 1;
      });
      // grade que cabe sem rolar: 2, 3, 4 ou 5 colunas conforme a quantidade; rola só se passar de 3 linhas
      var cols = shop.kind === "armario" ? (innerWidth < 760 ? 4 : 5) : shop.kind === "cacos" && cacosPage !== "home" ? 4 :
                 shown <= 4 ? 2 : shown <= 9 ? 3 : 4;
      if (shop.kind === "cacos" && cacosPage === "home") cols = 2;
      var lines = Math.ceil(shown / cols);
      var head = list.querySelectorAll(".wide").length;          // cupom e "< SEÇÕES" em faixas baixas no topo
      list.classList.toggle("has-head", head > 0);
      list.style.setProperty("--head", head || 1);
      list.style.setProperty("--cols", cols);
      list.style.setProperty("--rowh", lines > (head ? 2 : 3) ? "112px" : "minmax(0, 1fr)");
      renderNpc(shop.npc);
      renderDetail(rows.filter(function (r) { return r.id === shopPick; })[0], cur);
      fitIcons(list);
      var on = list.querySelector(".on");
      if (on && on.scrollIntoView) on.scrollIntoView({ block: "nearest" });
    }
    var buy = $("shop-buy");
    buy.disabled = !cur || !cur.ok || !cur.afford;
    var verb = shop.action ? shop.action : shop.kind === "altar" ? "ESCOLHER" : shopPick === "doar" ? "DOAR…" :
      cur && cur.id === "fundir" ? "FUNDIR" : cur && cur.info && cur.info.type === "encanto" ? "ENCANTAR" :
      shop.kind === "ferreiro" ? "FORJAR" : "COMPRAR";
    var buyKey = verb + "|" + (cur && cur.cost && !shop.action && shopPick !== "doar" ? cur.cost : "");
    if (buy.dataset.key !== buyKey) {            // o preço vai dentro do botão: COMPRAR ◆ 40
      buy.dataset.key = buyKey;
      buy.textContent = verb;
      if (buyKey.split("|")[1]) {
        buy.appendChild(el("b", "gem"));
        buy.appendChild(document.createTextNode(cur.cost));
      }
      // nome longo (USAR CUPOM, COMPRAR ◆ 40...) desce para 8 px em vez de estourar
      buy.style.fontSize = "";
      requestAnimationFrame(function () { if (buy.scrollWidth > buy.clientWidth + 1) buy.style.fontSize = "8px"; });
    }
    var note = $("shop-note");
    if (cur && !cur.ok) note.textContent = (cur.info && cur.info.sub) || "INDISPONÍVEL";
    else if (shop.action) note.textContent = "";
    else if (cur && !cur.afford) note.textContent = "FALTAM " + (cur.cost - shop.souls) + " " + shopUnit();
    else if (note.textContent !== "PEDIDO ENVIADO" && note.textContent.indexOf("DOOU") !== 0) note.textContent = "";
    renderGift(shop);
  }

  // quem atende a banca (mascate, ferreiro, soldador...): 2 quadros, em 2x, com a falinha
  function renderNpc(npc) {
    var box = $("shop-npc");
    box.hidden = !npc;
    if (!npc) return;
    if (box.dataset.name !== npc.name) {
      box.dataset.name = npc.name;
      ["npc-a", "npc-b"].forEach(function (id, i) {
        var img = $(id);
        img.onload = function () {
          var k = Math.max(1, Math.min(2, Math.floor((box.clientHeight - 60) / img.naturalHeight)));
          img.style.width = img.naturalWidth * k + "px";
          img.style.height = img.naturalHeight * k + "px";
        };
        img.src = "/npc/" + npc.name + "_" + i + ".png";
      });
    }
    $("shop-fala").textContent = npc.fala || "";
    $("shop-npc-name").textContent = npc.label || "";
  }

  // loja de cacos: botão do cupom no topo e, na tela inicial, um card por seção
  function cacosHead(list, shop, rows) {
    var cup = rows.filter(function (r) { return r.id === "cupom"; })[0];
    if (cup) {
      var b = el("button", "shop-item wide cacos-cupom" + (shopPick === "cupom" ? " on" : ""), "INSERIR CUPOM");
      b.addEventListener("pointerdown", function (e) {
        e.preventDefault(); buzz(); shopPick = "cupom"; $("shop-note").textContent = "";
        order("cupom", false); renderShop(shopData);
      });
      list.appendChild(b);
    }
    if (cacosPage !== "home") {
      var back = el("button", "shop-item wide cacos-back", "< SEÇÕES");
      back.addEventListener("pointerdown", function (e) {
        e.preventDefault(); buzz(); cacosPage = "home"; shopKey = null; renderShop(shopData);
      });
      list.appendChild(back);
      return;
    }
    function part(name) { return rows.filter(function (r) { return r.info && r.info.section === name; }); }
    function mineOf(list) {
      return list.filter(function (r) { return r.info.state === "tirar" || r.info.state === "vestir"; }).length;
    }
    var skins = part("skins"), pets = part("pets");
    var ms = mineOf(skins), mp = mineOf(pets);
    [["skins", "SKINS", skins, skins.length + " ROUPAS · " + ms + (ms === 1 ? " SUA" : " SUAS")],
     ["pets", "PETS", pets, pets.length + " BICHINHOS · " + mp + (mp === 1 ? " SEU" : " SEUS")]].forEach(function (sec) {
      var b = el("button", "shop-item cacos-sec", "");
      b.dataset.sec = sec[0];
      b.style.setProperty("--r", sec[0] === "pets" ? "#3ccf8a" : "#b48cff");
      var pics = el("span", "pics");
      sec[2].slice(0, 3).forEach(function (r) {
        var im = el("img"); im.src = r.info.img; im.alt = ""; im.draggable = false; pics.appendChild(im);
      });
      b.appendChild(pics);
      b.appendChild(el("span", "name", sec[1]));
      b.appendChild(el("small", "", sec[3]));
      b.addEventListener("pointerdown", function (e) {
        e.preventDefault(); buzz();
        cacosPage = sec[0]; shopKey = null;
        if (sec[2].length && !sec[2].some(function (r) { return r.id === shopPick; })) {
          shopPick = sec[2][0].id; order(shopPick, false);
        }
        renderShop(shopData);
      });
      list.appendChild(b);
    });
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

  // ── computador da Casa: a cópia da tela vem em PNG; o toque vira clique lá na TV ──
  var pcOpen = false;
  var pcData = null;
  var pcVersion = -1;
  var pcLoaded = 0;
  var pcSent = "";
  var pcBufTimer = null;

  function pcFit() {
    var stage = $("pc-stage"), img = $("pc-screen");
    var ratio = (pcData && pcData.ratio) || 1.9;
    var w = stage.clientWidth, h = stage.clientHeight - 14;
    if (w <= 0 || h <= 0) return;
    if (w / h > ratio) w = h * ratio; else h = w / ratio;
    img.style.width = Math.floor(w) + "px";
    img.style.height = Math.floor(h) + "px";
  }

  function renderPc(pc) {
    var view = $("view-pc");
    var first = !pcOpen;
    pcOpen = true;
    pcData = pc;
    $("pc-title").textContent = pc.title;
    var now = Date.now();
    if (first || pc.version !== pcVersion || now - pcLoaded > 1500) {   // tela nova (ou o cristal girando)
      pcVersion = pc.version;
      pcLoaded = now;
      $("pc-screen").src = "/api/tela.png?slot=" + slot + "&token=" + encodeURIComponent(token) + "&v=" + pc.version + "_" + now;
    }
    view.classList.toggle("typing", !!pc.typing);
    var names = { terminal: "TERMINAL", url: "ENDEREÇO", senha: "SENHA" };
    $("pc-field").textContent = names[pc.focus] || "";
    var input = $("pc-input");
    input.type = pc.focus === "senha" ? "password" : "text";
    if (!pc.typing && document.activeElement === input) input.blur();
    if (first) { input.value = ""; pcSent = ""; }
    $("pc-hint").textContent = pc.typing ? "TOQUE NA LINHA DE BAIXO PARA DIGITAR" : "TOQUE NA TELA PARA CLICAR";
    pcFit();
  }

  function pcField(u, v) {
    var hit = null;
    ((pcData && pcData.fields) || []).forEach(function (f) {
      if (u >= f[0] && u <= f[0] + f[2] && v >= f[1] && v <= f[1] + f[3]) hit = f[4];
    });
    return hit;
  }

  $("pc-screen").addEventListener("click", function (e) {
    var r = e.currentTarget.getBoundingClientRect();
    var u = (e.clientX - r.left) / r.width, v = (e.clientY - r.top) / r.height;
    if (u < 0 || u > 1 || v < 0 || v > 1) return;
    buzz();
    order("pc:tap:" + u.toFixed(4) + "," + v.toFixed(4), false);
    if (pcField(u, v)) {                      // campo de texto: o teclado sobe no mesmo toque
      var input = $("pc-input");
      input.value = "";
      pcSent = "";
      $("view-pc").classList.add("typing");
      input.focus();
    }
  });
  window.addEventListener("resize", function () { if (pcOpen) pcFit(); });

  $("pc-input").addEventListener("focus", function () { $("view-pc").classList.add("keyboard"); });
  $("pc-input").addEventListener("blur", function () {
    $("view-pc").classList.remove("keyboard");
    setTimeout(pcFit, 60);
  });
  $("pc-input").addEventListener("input", function () {   // a TV mostra o que está sendo digitado
    if (pcBufTimer) return;
    pcBufTimer = setTimeout(function () {
      pcBufTimer = null;
      var text = $("pc-input").value;
      if (text !== pcSent) { pcSent = text; order("pc:buf:" + text, false); }
    }, 120);
  });
  $("pc-type").addEventListener("submit", function (e) {
    e.preventDefault();
    var input = $("pc-input");
    if (pcBufTimer) { clearTimeout(pcBufTimer); pcBufTimer = null; }
    order("pc:text:" + input.value, false);
    input.value = "";
    pcSent = "";
    if (pcData && pcData.focus !== "terminal") input.blur();   // no terminal o teclado fica aberto
  });

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
  onPress($("pc-close"), function () { $("pc-input").blur(); order("fechar", false); });
  onPress($("pc-back"), function () { order("voltar", false); });
  onPress($("shop-buy"), function () {
    if (shopPick === "cupom") {
      sendCupom();
      return;
    }
    if (shopPick === "doar") {
      giftTo = null;
      $("view-shop").classList.add("gifting");
      renderGift(shopData);
      return;
    }
    order(rowItem(shopRows(shopData).filter(function (r) { return r.id === shopPick; })[0]) || shopPick, true);
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
    if (typeof me.char === "number" && me.char >= 0 && me.char !== faceChar) {   // rostinho do herói na etiqueta
      faceChar = me.char;
      document.body.style.setProperty("--face", "url(/sprite/" + me.char + ".png)");
    }
    if (!me.owner) {
      if (joined) { joined = false; join(slot).catch(function () {}); }
      show("join");
      markTaken();
      return;
    }
    var mode = status.mode;
    var modeName = mode === "soccer" ? (status.hud === "basket" ? "BASQUETE" : "FUTEBOL") : mode === "campaign" ? "CAMPANHA" : "DUELO";
    if (mode !== "campaign" && (me.team === 0 || me.team === 1)) {
      modeName += " · TIME " + (me.team === 0 ? "AZUL" : "VERMELHO");   // 2 x 2
    }
    bind("mode", modeName);
    var phase = status.phase;
    $("results-actions").classList.toggle("on", phase === "results" && me.playing);
    $("story-actions").classList.toggle("on", phase === "story" && me.playing);
    if (status.roster && status.roster !== roster.length) loadRoster();   // personagem novo liberado

    if (phase === "playing" && me.playing && me.shop && me.shop.screen) {
      if (!$("view-pc").classList.contains("on")) releaseAll();
      show("pc");
      renderPc(me.shop);
      return;
    }
    pcOpen = false;
    if (phase === "playing" && me.playing && me.shop) {
      if (!$("view-shop").classList.contains("on")) releaseAll();   // nada fica segurado com a loja aberta
      show("shop");
      shopEnergy = [me.energy || 0, me.emax || 0];
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
      document.querySelectorAll(".campaign-only").forEach(function (e) { e.classList.toggle("hidden", mode !== "campaign"); });
      useHud(status.hud || (soccerMode ? "soccer" : "battle"));
      $("pad-hint").textContent = soccerMode ? "empurre até a borda para correr" : "mova o analógico";
      document.querySelectorAll(".battle-only").forEach(function (e) { e.classList.toggle("on", mode !== "soccer"); });
      document.querySelectorAll(".soccer-only").forEach(function (e) { e.classList.toggle("on", mode === "soccer"); });
      $("paused").classList.toggle("on", phase === "paused");
      var ch = roster[me.char];
      var sb = $("super-btn");
      var superName = (ch && ch.soccer_power ? ch.soccer_power : "SUPER").toUpperCase();
      if (sb.dataset.label !== superName) sb.dataset.label = superName;
      renderHand(me, ch);
      layoutButtons();
      var cd = me.cooldown || 0;
      sb.style.setProperty("--p", (1 - cd).toFixed(3));
      sb.classList.toggle("cooling", cd > 0);
      sb.classList.toggle("ready", cd <= 0);
      renderAmmo(me, mode);
      renderSouls(me);
      vibrateFor(me.buzz);
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
    renderNewsPage(phase === "news" ? status.news_page : null);
    if (phase === "news") {
      bind("wait-title", status.banner || "Novidades");
      bind("wait-text", status.news_page ? "Os botões daqui também viram as notícias." :
                                           "Na TV: setas ou ENTER para escolher.");
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

  // ATACAR mostra o desenho e o nome da arma que está na mão; HABILIDADE, o nome da habilidade do herói
  var handKey = "";
  function renderHand(me, ch) {
    var atk = document.querySelector('.battle-only [data-act="attack"]');
    var skill = document.querySelector('.battle-only [data-act="special"]');
    var hand = me.hand || null;
    var key = hand ? hand.name + "|" + hand.icon : "";
    if (atk && key !== handKey) {
      handKey = key;
      var img = $("atk-icon");
      img.onload = function () {               // desenho em escala inteira dentro do botão
        var box = parseInt(getComputedStyle(atk).getPropertyValue("--is"), 10) || 48;
        var n = Math.max(img.naturalWidth, img.naturalHeight);
        var k = n <= box ? Math.floor(box / n) : 1 / Math.ceil(n / box);
        img.style.width = Math.round(img.naturalWidth * k) + "px";
        img.style.height = Math.round(img.naturalHeight * k) + "px";
      };
      img.src = hand && hand.icon ? "/arma/" + hand.icon : "/static/ic/i_atacar.png";
      atk.dataset.label = hand ? shortName(hand.name) : "ATACAR";
    }
    if (skill && ch && ch.ability) skill.dataset.label = shortName(ch.ability.toUpperCase());
  }

  // nome curto para caber embaixo do botão (até 14 letras): corta nas palavras
  function shortName(name) {
    if (name.length <= 14) return name;
    var out = "";
    name.split(" ").some(function (w) {
      if ((out ? out.length + 1 : 0) + w.length > 14) return true;
      out = out ? out + " " + w : w;
      return false;
    });
    var words = (out || name.slice(0, 14)).split(" ");
    while (words.length > 1 && /^(DE|DA|DO|DAS|DOS|E)$/.test(words[words.length - 1])) words.pop();   // não termina em "DAS"
    return words.join(" ");
  }

  function renderAmmo(me, mode) {
    var btn = document.querySelector('.battle-only [data-act="attack"]');
    var badge = $("ammo-badge");
    if (!btn || !badge) return;
    var mag = me.mag || 0;
    var emax = me.emax || 0, cost = me.ecost || 0;
    btn.classList.toggle("has-energy", emax > 0 && mag <= 0 && cost > 0);
    if (mode === "campaign" && emax > 0 && mag <= 0 && cost > 0) {
      // arma forte da campanha: o contador mostra a energia (cada tiro gasta "cost")
      var en = me.energy || 0;
      btn.classList.add("has-ammo");
      btn.classList.remove("reloading", "extra");
      btn.style.setProperty("--a", Math.min(1, en / emax).toFixed(3));
      badge.classList.add("on");
      badge.classList.remove("reloading");
      badge.classList.toggle("empty", en < cost);
      var etext = en < cost ? "SEM ENERGIA" : "ENERGIA " + en;
      if (badge.textContent !== etext) badge.textContent = etext;
      return;
    }
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

  function renderNewsPage(page) {
    $("news-page").classList.toggle("on", !!page);
    $("news-actions").classList.toggle("on", !!page);
    if (!page) return;
    var count = page.index ? "NOTÍCIA " + page.index + " DE " + page.total : "AS MANCHETES DE HOJE";
    if ($("news-page-count").textContent !== count) $("news-page-count").textContent = count;
    var title = page.index ? page.title : page.total + " novidades: aperte > para começar";
    if ($("news-page-title").textContent !== title) $("news-page-title").textContent = title;
  }

  function newsTap(go) {
    if (!slot) return;
    post("/api/news", { slot: slot, token: token, go: go }).catch(function () {});
    setTimeout(refresh, 90);
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
