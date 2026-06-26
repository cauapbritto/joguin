(function () {
    "use strict";

    var player = new URLSearchParams(location.search).get("player") || "1";
    document.body.className = "player" + player;
    var prefix = "p" + player + "_";

    var activePointers = {};
    var joystickPointerId = null;
    var joystickActive = false;

    var baseEl = document.getElementById("joystick-base");
    var knobEl = document.getElementById("joystick-knob");
    var zoneEl = document.getElementById("joystick-zone");

    const DEADZONE = 15;
    const MAX_RADIUS = 50;

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

    // ── Game State Polling ──
    var csHeader = document.getElementById("cs-player-num");
    var charSelect = document.getElementById("char-select");
    var container = document.getElementById("container");
    if (csHeader) csHeader.textContent = player;

    function updateUI(state) {
        if (!charSelect || !container) return;
        if (state === "char_select") {
            charSelect.style.display = "flex";
            container.style.display = "none";
        } else {
            charSelect.style.display = "none";
            container.style.display = "flex";
        }
    }

    function pollGameState() {
        fetch(getBaseUrl() + "/api/game-state")
            .then(function (r) { return r.json(); })
            .then(function (data) { updateUI(data.state); })
            .catch(function () {});
    }
    pollGameState();
    setInterval(pollGameState, 1000);

    // ── Char Select Buttons ──
    function csButton(id, cmd) {
        var el = document.getElementById(id);
        if (!el) return;
        el.addEventListener("pointerdown", function (e) {
            e.preventDefault();
            send("press", cmd);
        });
        el.addEventListener("pointerup", function (e) {
            send("release", cmd);
        });
        el.addEventListener("pointercancel", function (e) {
            send("release", cmd);
        });
    }
    csButton("cs-prev", "char_left");
    csButton("cs-next", "char_right");
    csButton("cs-weapon-toggle", "weapon_toggle");
    csButton("cs-confirm", "confirm");

    // ── Joystick ──
    function handleJoystickMove(pointerId, clientX, clientY) {
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
            } else {
                knobEl.classList.remove("active");
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
        if (joystickPointerId === e.pointerId) {
            releaseJoystick();
        }
    });

    document.addEventListener("pointercancel", function (e) {
        if (joystickPointerId === e.pointerId) {
            releaseJoystick();
        }
    });

    // ── Action Buttons ──
    document.addEventListener("pointerdown", function (e) {
        var btn = e.target.closest("[data-key]");
        if (!btn) return;
        e.preventDefault();
        btn.setPointerCapture(e.pointerId);
        var key = btn.getAttribute("data-key");
        activePointers[e.pointerId] = { key: key, el: btn };
        btn.classList.add("active");
        send("press", key);
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
        if (e.target.closest("[data-key]") || e.target.closest("#joystick-zone") || e.target.closest("#char-select button")) {
            e.preventDefault();
        }
    }, { passive: false });

    document.addEventListener("touchmove", function (e) {
        e.preventDefault();
    }, { passive: false });

    // ── Status ──
    var statusEl = document.getElementById("status");
    if (statusEl) {
        statusEl.textContent = "Jogador " + player + " — " + getBaseUrl();
    }

    document.addEventListener("visibilitychange", function () {
        if (document.hidden) {
            releaseJoystick();
            sendReleaseAll();
        }
    });

    window.addEventListener("beforeunload", function () {
        sendReleaseAll();
    });
})();
