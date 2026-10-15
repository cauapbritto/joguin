"""Servidor do controle pelo celular. Roda numa thread separada do jogo.

As páginas e arquivos saem do Flask. Os dois pedidos que o celular faz o tempo todo
(/api/input, várias vezes por segundo, e /api/status) são atendidos direto por um servidor
HTTP enxuto, sem passar pelo Flask: gastam bem menos processador, que o jogo divide com ele.
"""
import io
import json
import logging
import os
import socket
import socketserver
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote_to_bytes

from flask import Flask, Response, abort, jsonify, render_template, request, send_from_directory

from .. import config
from ..data import roster as available_characters, roster_for_web
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


def _static_version():
    """Muda quando os arquivos do controle mudam: o celular não usa uma versão velha do cache."""
    try:
        folder = config.WEB_DIR / "static"
        return str(int(max(p.stat().st_mtime for p in folder.iterdir())))
    except (OSError, ValueError):
        return "1"


@app.route("/")
def index():
    return render_template("controller.html", v=_static_version())


@app.route("/font.ttf")
def font():
    return send_from_directory(config.FONT_PATH.parent, config.FONT_PATH.name, max_age=86400)


@app.route("/sprite/<int:index>.png")
def sprite(index):
    data = _previews.get(index)
    if data is None:
        abort(404)
    return Response(data, mimetype="image/png", headers={"Cache-Control": "max-age=3600"})


def handle_input(data):
    """Aplica o estado completo do controle. Devolve o código HTTP (204, 400 ou 403)."""
    if not isinstance(data, dict):
        data = {}
    slot = _slot_arg(data)
    if not hub.touch(slot, data.get("token")):
        return 403
    try:
        seq = int(data.get("seq", 0))
        held = [str(a) for a in data.get("held", [])][:32]
        counts = {str(a): int(n) for a, n in dict(data.get("counts", {})).items()}
        x = float(data.get("x", 0))
        y = float(data.get("y", 0))
    except (TypeError, ValueError):
        return 400
    hub.apply_input(slot, str(data.get("sid", "")) or None, seq, held, counts, x, y)
    return 204


def status_payload(slot, token):
    hub.touch(slot, token)
    return hub.status(slot, token)


@app.post("/api/input")
def input_state():
    """Estado completo do controle (o celular manda a cada mudança e de tempos em tempos)."""
    return "", handle_input(request.get_json(silent=True) or {})


# Rotas antigas (páginas abertas antes da atualização ainda funcionam)
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
    for entry, stats in zip(data, available_characters()):
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
    return jsonify(status_payload(_slot_arg(request.args), request.args.get("token")))


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


class _Handler(BaseHTTPRequestHandler):
    """HTTP/1.1 com conexão mantida (o celular reaproveita a mesma conexão)."""

    protocol_version = "HTTP/1.1"
    server_version = "SoulStrike"
    sys_version = ""
    timeout = 30                      # conexão parada há tanto tempo é fechada (libera a thread)

    def log_message(self, *args):
        pass

    def _read_body(self):
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            n = 0
        return self.rfile.read(min(n, 1 << 20)) if n > 0 else b""

    def _reply(self, code, body=b"", ctype=None):
        self.send_response(code)
        if ctype:
            self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def do_POST(self):
        if self.path.split("?", 1)[0] == "/api/input":
            try:
                data = json.loads(self._read_body() or b"{}")
            except ValueError:
                data = {}
            self._reply(handle_input(data))
            return
        self._flask()

    def do_GET(self):
        path, _, query = self.path.partition("?")
        if path == "/api/status":
            q = parse_qs(query)
            try:
                slot = int(q.get("slot", ["0"])[0])
            except ValueError:
                slot = 0
            payload = status_payload(slot, q.get("token", [None])[0])
            self._reply(200, json.dumps(payload, separators=(",", ":")).encode(), "application/json")
            return
        self._flask()

    def do_HEAD(self):
        self._flask()

    def _flask(self):
        """Todo o resto (página, scripts, fonte, sprites, elenco, entrar e sair) vai para o Flask."""
        path, _, query = self.path.partition("?")
        body = self._read_body()
        env = {
            "REQUEST_METHOD": self.command,
            "SCRIPT_NAME": "",
            "PATH_INFO": unquote_to_bytes(path).decode("latin-1"),
            "QUERY_STRING": query,
            "SERVER_NAME": self.server.server_name,
            "SERVER_PORT": str(self.server.server_port),
            "SERVER_PROTOCOL": self.request_version,
            "REMOTE_ADDR": self.client_address[0],
            "CONTENT_TYPE": self.headers.get("Content-Type", ""),
            "CONTENT_LENGTH": str(len(body)),
            "wsgi.version": (1, 0),
            "wsgi.url_scheme": "http",
            "wsgi.input": io.BytesIO(body),
            "wsgi.errors": sys.stderr,
            "wsgi.multithread": True,
            "wsgi.multiprocess": False,
            "wsgi.run_once": False,
        }
        for key, value in self.headers.items():
            name = "HTTP_" + key.upper().replace("-", "_")
            if name not in ("HTTP_CONTENT_TYPE", "HTTP_CONTENT_LENGTH"):
                env[name] = f"{env[name]},{value}" if name in env else value
        answer = []

        def start_response(status, headers, exc_info=None):
            answer[:] = [status, headers]
            return chunks.append

        chunks = []
        result = app(env, start_response)
        try:
            for chunk in result:
                chunks.append(chunk)
        finally:
            if hasattr(result, "close"):
                result.close()
        status, headers = answer
        code, _, reason = status.partition(" ")
        self.send_response(int(code), reason)
        for key, value in headers:
            if key.lower() not in ("content-length", "connection", "transfer-encoding"):
                self.send_header(key, value)
        data = b"".join(chunks)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        if data and self.command != "HEAD":
            self.wfile.write(data)


class _Server(ThreadingHTTPServer):
    daemon_threads = True
    # No Windows, "reusar o endereço" deixa dois jogos abertos escutarem a mesma porta e os
    # celulares caírem no errado. Lá a porta fica exclusiva: o segundo jogo avisa que está ocupada.
    allow_reuse_address = os.name != "nt"

    def server_bind(self):
        if os.name == "nt" and hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        # sem o socket.getfqdn() do HTTPServer, que pode demorar segundos em algumas redes
        socketserver.TCPServer.server_bind(self)
        self.server_name, self.server_port = self.server_address[:2]


def make_server(host="0.0.0.0", port=config.WEB_PORT):
    return _Server((host, port), _Handler)


start_error = None     # motivo de o controle pelo celular não ter iniciado (aparece no menu)


def start_in_background():
    def run():
        global start_error
        try:
            srv = make_server()
        except OSError as exc:   # porta ocupada: o jogo segue sem controle remoto
            start_error = f"PORTA {config.WEB_PORT} JÁ ESTÁ EM USO"
            print(f"[controle remoto] servidor não iniciou: {exc}")
            return
        srv.serve_forever(poll_interval=0.5)

    thread = threading.Thread(target=run, name="controle-remoto", daemon=True)
    thread.start()
    print(f"[controle remoto] abra no celular: {controller_url(1)} (troque o número do jogador)")
    return thread
