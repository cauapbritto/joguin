(function () {
    "use strict";

    var player = parseInt(new URLSearchParams(location.search).get("player")) || 1;
    if (player < 1 || player > 4) player = 1;
    var prefix = "p" + player + "_";

    var charIndex = 0;
    var confirmed = false;
    var charactersData = [];
    var soccerMode = true;

    var activePointers = {};
    var joystickPointerId = null;
    var joystickActive = false;

    var baseEl = document.getElementById("joystick-base");
    var knobEl = document.getElementById("joystick-knob");
    var zoneEl = document.getElementById("joystick-zone");

    var charSelect = document.getElementById("char-select");
    var container = document.getElementById("container");
    var csPlayerNum = document.getElementById("cs-player-num");
    var csTeam = document.getElementById("cs-team");
    var csCharName = document.getElementById("cs-char-name");
    var csConfirm = document.getElementById("cs-confirm");
    var csWaiting = document.getElementById("cs-waiting");
    var sbPlayer = document.getElementById("sb-player");
    var sbTeam = document.getElementById("sb-team");

    var teamsLookup = {1: 0, 2: 1, 3: 0, 4: 1};
    var teamNames = ["AZUL", "VERMELHO"];
    var teamColors = ["#4a7aff", "#ff4444"];

    var DEADZONE = 0;
    var MAX_RADIUS = 0;

    function getBaseUrl() {
        return window.location.origin;
    }

    function send(action, key) {
        fetch(getBaseUrl() + "/" + action + "/" + prefix + key, {
            method: "POST",
            cache: "no-store"
        }).catch(function () {});
    }

    function sendReleaseAll() {
        fetch(getBaseUrl() + "/release_all", {
            method: "POST",
            cache: "no-store"
        }).catch(function () {});
    }

    function postJSON(path, data) {
        fetch(getBaseUrl() + path, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(data),
            cache: "no-store"
        }).catch(function () {});
    }

    // ── Character Select ──
    function updateCharDisplay() {
        if (charactersData.length === 0) return;
        var ch = charactersData[charIndex];
        csCharName.textContent = ch.name;
        var col = ch.color || [200,200,200];
        csCharName.style.color = "rgb(" + col.join(",") + ")";
    }

    function loadCharacters() {
        fetch(getBaseUrl() + "/api/characters")
            .then(function (r) { return r.json(); })
            .then(function (data) {
                charactersData = data;
                updateCharDisplay();
            })
            .catch(function () {});
    }

    function claimAndConfirm() {
        fetch(getBaseUrl() + "/api/claim/" + player, { method: "POST", cache: "no-store" })
            .then(function (r) {
                if (r.status === 409) {
                    csWaiting.textContent = "Jogador " + player + " já está ocupado!";
                    return null;
                }
                return r.json();
            })
            .then(function (data) {
                if (!data) return;
                postJSON("/api/select_char", {player: player, char_index: charIndex});
                sendDirect("POST", "/api/ready/" + player);
                confirmed = true;
                csConfirm.disabled = true;
                csConfirm.textContent = "PRONTO!";
                csWaiting.textContent = "Aguardando outros jogadores...";
            });
    }

    function sendDirect(method, path) {
        fetch(getBaseUrl() + path, { method: method, cache: "no-store" }).catch(function () {});
    }

    function showCharacterSelect() {
        charSelect.classList.remove("hidden");
        container.classList.add("hidden");
    }

    function showController() {
        charSelect.classList.add("hidden");
        container.classList.remove("hidden");
    }

    var superCdEl = document.getElementById("d-super-cooldown");
    var superBtnEl = document.getElementById("d-super");

    // ── Poll game status ──
    function pollStatus() {
        fetch(getBaseUrl() + "/api/status")
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data.game_state === "playing") {
                    showController();
                } else if (data.game_state === "char_select") {
                    if (!confirmed) showCharacterSelect();
                    else csWaiting.textContent = "Aguardando outros jogadores...";
                }

                var teamIdx = teamsLookup[player] || 0;
                var teamName = teamNames[teamIdx];
                var teamColor = teamColors[teamIdx];
                if (csTeam) { csTeam.textContent = "Time " + teamName; csTeam.style.color = teamColor; }
                if (sbTeam) { sbTeam.textContent = teamName; sbTeam.style.color = teamColor; }

                if (data.claimed && data.claimed.indexOf(player) >= 0 && !confirmed) {
                    confirmed = true;
                    csConfirm.disabled = true;
                    csConfirm.textContent = "PRONTO!";
                    csWaiting.textContent = "Aguardando outros jogadores...";
                }
            })
            .catch(function () {});
    }

    function pollSuperCooldown() {
        fetch(getBaseUrl() + "/api/super_cooldown")
            .then(function (r) { return r.json(); })
            .then(function (data) {
                var cd = data[String(player)] || 0;
                if (!superCdEl || !superBtnEl) return;
                if (cd > 0) {
                    var sec = Math.ceil(cd / 60);
                    superCdEl.textContent = sec + "s";
                    superCdEl.classList.add("show");
                    superBtnEl.style.opacity = "0.4";
                    superBtnEl.style.pointerEvents = "none";
                } else {
                    superCdEl.classList.remove("show");
                    superBtnEl.style.opacity = "";
                    superBtnEl.style.pointerEvents = "";
                }
            })
            .catch(function () {});
    }

    // ── Char Select Buttons ──
    document.getElementById("cs-prev").addEventListener("pointerdown", function (e) {
        e.preventDefault();
        if (confirmed || charactersData.length === 0) return;
        charIndex = (charIndex - 1 + charactersData.length) % charactersData.length;
        updateCharDisplay();
        postJSON("/api/select_char", {player: player, char_index: charIndex});
    });

    document.getElementById("cs-next").addEventListener("pointerdown", function (e) {
        e.preventDefault();
        if (confirmed || charactersData.length === 0) return;
        charIndex = (charIndex + 1) % charactersData.length;
        updateCharDisplay();
        postJSON("/api/select_char", {player: player, char_index: charIndex});
    });

    if (csConfirm) {
        csConfirm.addEventListener("pointerdown", function (e) {
            e.preventDefault();
            if (confirmed) return;
            claimAndConfirm();
        });
    }

    // ── Joystick ──
    function computeJoystickParams() {
        var rect = baseEl.getBoundingClientRect();
        var r = rect.width / 2;
        DEADZONE = r * 0.08;
        MAX_RADIUS = r * 0.82;
    }

    function handleJoystickMove(pointerId, clientX, clientY) {
        computeJoystickParams();
        var rect = baseEl.getBoundingClientRect();
        var cx = rect.left + rect.width / 2;
        var cy = rect.top + rect.height / 2;
        var dx = clientX - cx;
        var dy = clientY - cy;
        var dist = Math.sqrt(dx * dx + dy * dy);
        var angle = Math.atan2(dy, dx);
        var clampedDist = Math.min(dist, MAX_RADIUS);
        var kx = Math.cos(angle) * clampedDist;
        var ky = Math.sin(angle) * clampedDist;

        knobEl.style.transform = "translate(calc(-50% + " + kx + "px), calc(-50% + " + ky + "px))";

        var newActive = dist > DEADZONE;
        if (newActive !== joystickActive) {
            joystickActive = newActive;
            if (newActive) {
                knobEl.classList.add("active");
                baseEl.classList.add("active");
            } else {
                knobEl.classList.remove("active");
                baseEl.classList.remove("active");
            }
        }

        var up    = dy < -DEADZONE;
        var down  = dy >  DEADZONE;
        var left  = dx < -DEADZONE;
        var right = dx >  DEADZONE;

        if (up && !activePointers["__up"]) {
            activePointers["__up"] = true;
            send("press", "up");
        } else if (!up && activePointers["__up"]) {
            delete activePointers["__up"];
            send("release", "up");
        }
        if (down && !activePointers["__down"]) {
            activePointers["__down"] = true;
            send("press", "down");
        } else if (!down && activePointers["__down"]) {
            delete activePointers["__down"];
            send("release", "down");
        }
        if (left && !activePointers["__left"]) {
            activePointers["__left"] = true;
            send("press", "left");
        } else if (!left && activePointers["__left"]) {
            delete activePointers["__left"];
            send("release", "left");
        }
        if (right && !activePointers["__right"]) {
            activePointers["__right"] = true;
            send("press", "right");
        } else if (!right && activePointers["__right"]) {
            delete activePointers["__right"];
            send("release", "right");
        }
    }

    function releaseJoystick() {
        joystickPointerId = null;
        joystickActive = false;
        knobEl.classList.remove("active");
        baseEl.classList.remove("active");
        knobEl.style.transform = "translate(-50%, -50%)";
        ["__up", "__down", "__left", "__right"].forEach(function (k) {
            if (activePointers[k]) {
                delete activePointers[k];
                send("release", k.replace("__", ""));
            }
        });
    }

    zoneEl.addEventListener("pointerdown", function (e) {
        e.preventDefault();
        if (joystickPointerId !== null) return;
        joystickPointerId = e.pointerId;
        zoneEl.setPointerCapture(e.pointerId);
        handleJoystickMove(e.pointerId, e.clientX, e.clientY);
    });

    document.addEventListener("pointermove", function (e) {
        if (joystickPointerId !== e.pointerId) return;
        e.preventDefault();
        handleJoystickMove(e.pointerId, e.clientX, e.clientY);
    });

    document.addEventListener("pointerup", function (e) {
        if (joystickPointerId === e.pointerId) releaseJoystick();
    });

    document.addEventListener("pointercancel", function (e) {
        if (joystickPointerId === e.pointerId) releaseJoystick();
    });

    // ── Action Buttons ──
    var btnMap = {
        "d-chute": "attack",
        "d-passe": "special",
        "d-corte": "corte",
        "d-carrinho": "conducao",
        "d-super": "super",
    };

    Object.keys(btnMap).forEach(function (id) {
        var el = document.getElementById(id);
        var key = btnMap[id];
        if (!el) return;
        el.addEventListener("pointerdown", function (e) {
            e.preventDefault();
            var captureId = e.pointerId;
            el.setPointerCapture(captureId);
            el.classList.add("active");
            activePointers[captureId] = { key: key, el: el };
            send("press", key);
        });
    });

    document.addEventListener("pointerup", function (e) {
        var entry = activePointers[e.pointerId];
        if (!entry) return;
        entry.el.classList.remove("active");
        send("release", entry.key);
        delete activePointers[e.pointerId];
    });

    document.addEventListener("pointercancel", function (e) {
        var entry = activePointers[e.pointerId];
        if (!entry) return;
        entry.el.classList.remove("active");
        delete activePointers[e.pointerId];
        sendReleaseAll();
    });

    document.addEventListener("pointerleave", function (e) {
        var entry = activePointers[e.pointerId];
        if (!entry) return;
        entry.el.classList.remove("active");
        send("release", entry.key);
        delete activePointers[e.pointerId];
    });

    document.addEventListener("touchstart", function (e) {
        e.preventDefault();
    }, { passive: false });

    document.addEventListener("touchmove", function (e) {
        e.preventDefault();
    }, { passive: false });

    document.addEventListener("visibilitychange", function () {
        if (document.hidden) { releaseJoystick(); sendReleaseAll(); }
    });

    window.addEventListener("beforeunload", function () { sendReleaseAll(); });

    // ── Init ──
    if (csPlayerNum) csPlayerNum.textContent = player;
    loadCharacters();
    showCharacterSelect();
    pollStatus();
    setInterval(pollStatus, 1000);
    setInterval(pollSuperCooldown, 500);

    var statusEl = document.getElementById("status");
    if (statusEl) statusEl.textContent = "Jogador " + player + " — " + getBaseUrl();
})();