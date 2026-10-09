"""Servidor Flask do controle pelo celular. Roda numa thread separada do jogo."""
import logging
import socket
import threading

from flask import Flask, Response, abort, jsonify, render_template, request, send_from_directory

from .. import config
from ..data import CHARACTERS, roster_for_web
from ..soccer_powers import SOCCER_POWERS
from .remote import hub

app = Flask(
    __name__,
    template_folder=str(config.WEB_DIR / "templates"),
    static_folder=str(config.WEB_DIR / "static"),
)
logging.getLogger("werkzeug").setLevel(logging.WARNING)

_previews = {}   # índice do personagem → PNG (gerado pelo jogo ao carregar)


def set_previews(previews):
    _previews.clear()
    _previews.update(previews)


def _slot_arg(source):
    try:
        return int(source.get("slot", 0))
    except (TypeError, ValueError):
        return 0


@app.route("/")
def index():
    return render_template("controller.html")


@app.route("/font.ttf")
def font():
    return send_from_directory(config.FONT_PATH.parent, config.FONT_PATH.name, max_age=86400)


@app.route("/sprite/<int:index>.png")
def sprite(index):
    data = _previews.get(index)
    if data is None:
        abort(404)
    return Response(data, mimetype="image/png", headers={"Cache-Control": "max-age=3600"})


@app.post("/press/<key>")
def press(key):
    hub.press(key)
    return "", 204


@app.post("/axis/<int:slot>")
def axis(slot):
    try:
        x = float(request.args.get("x", 0))
        y = float(request.args.get("y", 0))
    except ValueError:
        return "", 400
    hub.set_axis(slot, x, y)
    return "", 204


@app.post("/release/<key>")
def release(key):
    hub.release(key)
    return "", 204


@app.post("/release_all")
def release_all():
    slot = _slot_arg(request.args)
    if slot:
        hub.release_slot(slot)
    return "", 204


@app.get("/api/roster")
def roster():
    data = roster_for_web()
    for entry, stats in zip(data, CHARACTERS):
        power = SOCCER_POWERS[stats.key]
        entry["soccer_power"] = power.name
        entry["soccer_desc"] = power.description
    return jsonify(data)


@app.post("/api/join")
def join():
    data = request.get_json(silent=True) or {}
    slot = _slot_arg(data)
    if hub.join(slot, data.get("token")):
        return jsonify({"ok": True, "slot": slot})
    return jsonify({"ok": False}), 409


@app.post("/api/leave")
def leave():
    data = request.get_json(silent=True) or {}
    hub.leave(_slot_arg(data), data.get("token"))
    return "", 204


@app.get("/api/status")
def status():
    slot = _slot_arg(request.args)
    token = request.args.get("token")
    hub.touch(slot, token)
    return jsonify(hub.status(slot, token))


def local_ip():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def controller_url(slot):
    return f"http://{local_ip()}:{config.WEB_PORT}/?player={slot}"


def start_in_background():
    def run():
        try:
            app.run(host="0.0.0.0", port=config.WEB_PORT, debug=False, use_reloader=False, threaded=True)
        except OSError as exc:   # porta ocupada: o jogo segue sem controle remoto
            print(f"[controle remoto] servidor não iniciou: {exc}")

    thread = threading.Thread(target=run, name="controle-remoto", daemon=True)
    thread.start()
    print(f"[controle remoto] abra no celular: {controller_url(1)} (troque o número do jogador)")
    return thread
