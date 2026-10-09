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
  var views = ["join", "wait", "select", "pad"];

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

  function buzz() { if (navigator.vibrate) navigator.vibrate(8); }

  function capture(el, id) {
    try { el.setPointerCapture(id); } catch (e) { /* ponteiro já liberado */ }
  }

  // ── comandos ───────────────────────────────
  var held = {};

  function press(action) {
    if (!slot || held[action]) return;
    held[action] = true;
    post("/press/p" + slot + "_" + action).catch(function () {});
  }

  function release(action) {
    if (!slot || !held[action]) return;
    delete held[action];
    post("/release/p" + slot + "_" + action).catch(function () {});
  }

  function releaseAll() {
    held = {};
    if (slot) post("/release_all?slot=" + slot).catch(function () {});
  }

  function tap(action) {
    press(action);
    setTimeout(function () { release(action); }, 70);
  }

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

  // ── analógico ──────────────────────────────
  var zone = $("stick-zone");
  var base = $("stick-base");
  var knob = $("stick-knob");
  var stickId = null;
  var origin = null;
  var dirs = { up: false, down: false, left: false, right: false };

  function setDir(name, on) {
    if (dirs[name] === on) return;
    dirs[name] = on;
    if (on) press(name); else release(name);
  }

  var axisSent = { x: 0, y: 0 }, axisTimer = null, axisWant = { x: 0, y: 0 };
  function flushAxis() {
    axisTimer = null;
    axisSent = { x: axisWant.x, y: axisWant.y };
    post("/axis/" + slot + "?x=" + axisWant.x.toFixed(2) + "&y=" + axisWant.y.toFixed(2)).catch(function () {});
  }
  function sendAxis(x, y) {
    if (!slot) return;
    axisWant = { x: x, y: y };
    var changed = Math.abs(x - axisSent.x) + Math.abs(y - axisSent.y) > 0.08 || (x === 0 && y === 0);
    if (changed && axisTimer === null) axisTimer = setTimeout(flushAxis, 33);
  }
  // reenvia de tempos em tempos enquanto segura (o jogo ignora analógico parado há muito tempo)
  setInterval(function () { if (stickId !== null) flushAxis(); }, 250);

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
    // analógico de verdade: direção livre e intensidade proporcional
    var power = active ? Math.min(1, (dist - r * 0.18) / (max - r * 0.18)) : 0;
    sendAxis(nx * power, ny * power);
    setDir("left", active && nx < -0.38);
    setDir("right", active && nx > 0.38);
    setDir("up", active && ny < -0.38);
    setDir("down", active && ny > 0.38);
  }

  zone.addEventListener("pointerdown", function (e) {
    if (stickId !== null) return;
    e.preventDefault();
    stickId = e.pointerId;
    capture(zone, e.pointerId);
    // o analógico aparece onde o polegar encostou
    var zr = zone.getBoundingClientRect();
    var size = base.offsetWidth;
    var left = Math.max(8, Math.min(e.clientX - zr.left - size / 2, zr.width - size - 8));
    var top = Math.max(56, Math.min(e.clientY - zr.top - size / 2, zr.height - size - 8));
    base.style.left = left + "px";
    base.style.top = top + "px";
    base.style.bottom = "auto";
    var br = base.getBoundingClientRect();
    origin = { x: br.left + br.width / 2, y: br.top + br.height / 2 };
    base.classList.add("live");
    moveStick(e.clientX, e.clientY);
  });

  zone.addEventListener("pointermove", function (e) {
    if (e.pointerId !== stickId) return;
    e.preventDefault();
    moveStick(e.clientX, e.clientY);
  });

  function endStick(e) {
    if (e.pointerId !== stickId) return;
    stickId = null;
    knob.style.transform = "";
    base.classList.remove("live");
    Object.keys(dirs).forEach(function (d) { setDir(d, false); });
    sendAxis(0, 0);
  }
  zone.addEventListener("pointerup", endStick);
  zone.addEventListener("pointercancel", endStick);

  document.addEventListener("touchmove", function (e) { e.preventDefault(); }, { passive: false });
  document.addEventListener("contextmenu", function (e) { e.preventDefault(); });
  document.addEventListener("visibilitychange", function () { if (document.hidden) releaseAll(); });
  window.addEventListener("pagehide", releaseAll);

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
    $("ability").innerHTML = mode === "soccer"
      ? "<b>SUPER: " + (ch.soccer_power || "") + "</b>" + (ch.soccer_desc || "")
      : "<b>" + ch.ability.toUpperCase() + "</b>" + ch.ability_desc;
    $("weapon").style.display = mode === "soccer" ? "none" : "";
    $("weapon").textContent = "ARMA: " + weapon.name.toUpperCase() + (weapon.melee ? " · CORPO A CORPO" : " · DISTÂNCIA");
    var ready = $("ready-btn");
    ready.classList.toggle("is-ready", me.ready);
    ready.textContent = me.ready ? "PRONTO! (TOQUE P/ CANCELAR)" : "PRONTO";
    ready.dataset.tap = me.ready ? "cancel" : "confirm";
    document.querySelectorAll("#view-select .arrow, #weapon").forEach(function (b) { b.disabled = me.ready; });
  }

  // ── estado do jogo ─────────────────────────
  var WAIT_TEXT = {
    menu: ["Conectado", "Aguardando o anfitrião escolher o modo de jogo."],
    lobby: ["Conectado", "Tudo certo! O anfitrião vai avançar para a escolha de personagens."],
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
    bind("mode", mode === "soccer" ? "FUTEBOL" : "DUELO");
    var phase = status.phase;
    $("results-actions").classList.toggle("on", phase === "results" && me.playing);

    if ((phase === "playing" || phase === "paused") && me.playing) {
      show("pad");
      $("pad-hint").textContent = mode === "soccer"
        ? "segure chutar/passe para levantar a bola"
        : "mova · toque 2x para esquivar";
      document.querySelectorAll(".battle-only").forEach(function (e) { e.classList.toggle("on", mode !== "soccer"); });
      document.querySelectorAll(".soccer-only").forEach(function (e) { e.classList.toggle("on", mode === "soccer"); });
      $("paused").classList.toggle("on", phase === "paused");
      var ch = roster[me.char];
      $("super-label").textContent = ch && ch.soccer_power ? ch.soccer_power : "SUPER";
      var cd = me.cooldown || 0;
      $("super-btn").classList.toggle("cooling", cd > 0);
      $("super-meter").style.width = Math.round((1 - cd) * 100) + "%";
      return;
    }
    if (phase === "select" && me.playing) {
      show("select");
      renderSelect(me, mode);
      return;
    }
    show("wait");
    if (phase === "results") {
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

  function markTaken() {
    if (!status) return;
    document.querySelectorAll(".slot").forEach(function (b) {
      var s = status.slots[b.dataset.slot];
      b.classList.toggle("taken", !!(s && s.connected && !(status.me && status.me.owner && b.dataset.slot == slot)));
    });
  }

  function refresh() {
    var q = "/api/status?slot=" + (slot || 0) + "&token=" + encodeURIComponent(token);
    return fetch(q, { cache: "no-store" })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        failures = 0;
        $("offline").classList.remove("on");
        status = data;
        render();
      })
      .catch(function () {
        failures += 1;
        if (failures > 3) $("offline").classList.add("on");
      });
  }

  fetch("/api/roster").then(function (r) { return r.json(); }).then(function (data) {
    roster = data;
    render();
  }).catch(function () {});

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
