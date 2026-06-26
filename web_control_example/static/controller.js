(function () {
    "use strict";

    const activePointers = {};  // pointerId -> key

    function getBaseUrl() {
        return window.location.origin;
    }

    function send(action, key) {
        const url = getBaseUrl() + "/" + action + "/" + key;
        fetch(url, { method: "POST", cache: "no-store" }).catch(function () {});
    }

    function sendReleaseAll() {
        const url = getBaseUrl() + "/release_all";
        fetch(url, { method: "POST", cache: "no-store" }).catch(function () {});
    }

    // ── Pointer Events (unifica mouse + toque) ──
    document.addEventListener("pointerdown", function (e) {
        const btn = e.target.closest("[data-key]");
        if (!btn) return;
        e.preventDefault();
        btn.setPointerCapture(e.pointerId);
        const key = btn.getAttribute("data-key");
        activePointers[e.pointerId] = { key: key, el: btn };
        btn.classList.add("active");
        send("press", key);
    });

    document.addEventListener("pointerup", function (e) {
        const entry = activePointers[e.pointerId];
        if (!entry) return;
        entry.el.classList.remove("active");
        send("release", entry.key);
        delete activePointers[e.pointerId];
    });

    document.addEventListener("pointercancel", function (e) {
        const entry = activePointers[e.pointerId];
        if (!entry) return;
        entry.el.classList.remove("active");
        delete activePointers[e.pointerId];
        sendReleaseAll();
    });

    document.addEventListener("pointerleave", function (e) {
        const entry = activePointers[e.pointerId];
        if (!entry) return;
        entry.el.classList.remove("active");
        send("release", entry.key);
        delete activePointers[e.pointerId];
    });

    // Previne gestos padrão do navegador na área de jogo
    document.addEventListener("touchstart", function (e) {
        if (e.target.closest("[data-key]")) {
            e.preventDefault();
        }
    }, { passive: false });

    document.addEventListener("touchmove", function (e) {
        e.preventDefault();
    }, { passive: false });

    // ── Status de conexão ──
    var statusEl = document.getElementById("status");
    if (statusEl) {
        statusEl.textContent = "Conectado a " + getBaseUrl();
    }

    // Recuperação: se a página perder foco, libera tudo
    document.addEventListener("visibilitychange", function () {
        if (document.hidden) {
            sendReleaseAll();
        }
    });

    window.addEventListener("beforeunload", function () {
        sendReleaseAll();
    });
})();
