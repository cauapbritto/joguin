"""Canal rápido do app Android: UDP na mesma porta do controle pelo site (5000).

O app manda o mesmo estado do /api/input (botões segurados, analógico, contadores de apertos e
um número de sequência): pedido atrasado ou perdido não estraga nada, como no site. Cada estado
recebe de volta, na hora, um PULSO pequeno (menos de 600 bytes): fase, modo, vibração, fôlego,
munição, energia, almas e um número que muda quando o resto do status muda. Só aí o app busca
o /api/status inteiro por HTTP (a loja passa de 5 KB e não cabe num pacote).

A vibração não espera o próximo pedido: quando o jogo vibra um celular que fala por aqui, o
pulso sai sozinho no mesmo instante.

Para achar o jogo sem QR, o app pergunta na rede inteira (broadcast) e cada jogo aberto responde
com o nome do computador, a versão e as vagas. A pergunta vem "acolchoada" (maior que a
resposta), então ninguém usa o jogo para multiplicar tráfego contra outro aparelho.
"""
import ipaddress
import json
import os
import socket
import threading
import time
import zlib

from .. import __version__, config
from .remote import hub

PROTOCOL = 1              # muda quando o formato dos pacotes mudar (o app confere)
MAX_PACKET = 4096
DISCOVERY_MIN = 256       # tamanho mínimo da pergunta de descoberta (a resposta é menor que isso)
PEER_SECONDS = 4.0        # sem pacote do app há esse tempo: para de mandar a vibração sozinha
# campos do "me" que vão no pulso (mudam o tempo todo e não fazem o app buscar o status)
FAST_ME = ("cooldown", "stamina", "tired", "ammo", "mag", "reload", "energy", "emax", "ecost", "souls", "buzz")

start_error = None        # motivo de o canal rápido não ter aberto (o app usa só HTTP)
_sock = None
_peers = {}               # vaga -> (endereço, token, instante do último pacote)
_peers_lock = threading.Lock()


def pc_name():
    """Nome do computador como o app mostra na lista de jogos da rede."""
    try:
        name = socket.gethostname().split(".")[0]
    except OSError:
        name = ""
    return (name or "COMPUTADOR").upper()[:24]


def running():
    return _sock is not None


def _split(full):
    """(status sem os campos rápidos, campos rápidos do "me")."""
    slow = dict(full)
    me = dict(slow.pop("me", None) or {})
    fast = {k: me.pop(k) for k in FAST_ME if k in me}
    slow["me"] = me
    return slow, fast


def status_number(full):
    """Número que muda quando o status muda em algo que não vai no pulso."""
    slow, _ = _split(full)
    return zlib.crc32(json.dumps(slow, sort_keys=True, separators=(",", ":"), default=str).encode())


def pulse(slot, token, seq=None, tm=None):
    """Pulso para o app desta vaga: o que muda a cada quadro, mais o número do status inteiro."""
    full = hub.status(slot, token)
    _, fast = _split(full)
    me = full.get("me") or {}
    fast["owner"] = bool(me.get("owner"))
    fast["playing"] = bool(me.get("playing"))
    out = {"t": "p", "st": status_number(full), "phase": full["phase"], "mode": full["mode"], "hud": full["hud"],
           "me": fast}
    if seq is not None:
        out["seq"] = seq
    if tm is not None:
        out["tm"] = tm
    return out


def discovery_answer():
    """Resposta à pergunta "tem jogo aí?": nome do PC, versão, porta, modo e as 4 vagas."""
    full = hub.status()
    slots = full.get("slots", {})
    return {"t": "jogo", "v": PROTOCOL, "jogo": "soulstrike", "nome": pc_name(), "versao": __version__,
            "porta": config.WEB_PORT, "fase": full["phase"], "modo": full["mode"],
            "vagas": {s: [bool(v.get("claimed")), bool(v.get("connected"))] for s, v in slots.items()}}


def _encode(data):
    return json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _lan(ip):
    try:
        a = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return a.is_private or a.is_loopback or a.is_link_local


def answer(data, addr, size):
    """Resposta a um pacote do app (dict) ou None. ``size`` é o tamanho do pacote recebido."""
    if not isinstance(data, dict):
        return None
    kind = data.get("t")
    if kind == "oi":
        if size < DISCOVERY_MIN or not _lan(addr[0]):
            return None
        return discovery_answer()
    if kind == "in":
        from .server import handle_input
        code = handle_input(data)
        if code != 204:
            return {"t": "nao", "code": code, "seq": data.get("seq")}
        try:
            slot = int(data.get("slot", 0))
        except (TypeError, ValueError):
            return None
        token = data.get("token")
        with _peers_lock:
            _peers[slot] = (addr, token, time.monotonic())
        tm = data.get("tm")
        return pulse(slot, token, data.get("seq"), tm if isinstance(tm, (int, float)) else None)
    return None


def _send(data, addr):
    sock = _sock
    if sock is None:
        return
    try:
        sock.sendto(_encode(data), addr)
    except OSError:
        pass


def _on_buzz(slot):
    """O jogo vibrou esta vaga: o pulso vai na hora para o app (se ele fala por aqui)."""
    with _peers_lock:
        peer = _peers.get(slot)
    if peer is None or time.monotonic() - peer[2] > PEER_SECONDS:
        return
    addr, token, _ = peer
    _send(pulse(slot, token), addr)


def forget(slot):
    with _peers_lock:
        _peers.pop(slot, None)


def _loop(sock):
    from . import server
    while True:
        try:
            raw, addr = sock.recvfrom(MAX_PACKET)
        except OSError:                    # tempo esgotado (confere se fechou) ou aviso do Windows
            if _sock is not sock:
                return
            continue
        if not str(addr[0]).startswith(("127.", "::1", "::ffff:127.")):
            server.remote_seen = True      # um aparelho da rede chegou: a rede está liberada
        try:
            data = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            continue
        try:
            reply = answer(data, addr, len(raw))
        except Exception as exc:          # um pacote estranho nunca derruba o canal
            print(f"[canal rápido] pacote ignorado: {exc}")
            continue
        if reply is not None:
            _send(reply, addr)


def make_socket(host="0.0.0.0", port=None):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # sem SO_REUSEADDR: dois jogos abertos não dividem a porta (o segundo fica só com o HTTP dele)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    if os.name == "nt" and hasattr(socket, "SIO_UDP_CONNRESET"):
        # no Windows, mandar para um app que fechou faz o próximo recvfrom dar erro: desliga isso
        sock.ioctl(socket.SIO_UDP_CONNRESET, False)
    try:
        sock.bind((host, config.WEB_PORT if port is None else port))
    except OSError:
        sock.close()
        raise
    sock.settimeout(0.5)                   # a thread confere de tempos em tempos se o canal fechou
    return sock


def start(host="0.0.0.0", port=None):
    """Abre o canal rápido numa thread. Devolve a thread ou None (porta ocupada: o app usa HTTP)."""
    global _sock, start_error
    if _sock is not None:
        return None
    try:
        sock = make_socket(host, port)
    except OSError as exc:
        start_error = str(exc)
        print(f"[canal rápido] UDP não abriu: {exc} (o app usa só HTTP)")
        return None
    _sock = sock
    start_error = None
    hub.on_buzz = _on_buzz
    thread = threading.Thread(target=_loop, args=(sock,), name="canal-rapido", daemon=True)
    thread.start()
    return thread


def stop():
    global _sock
    sock, _sock = _sock, None
    if hub.on_buzz is _on_buzz:
        hub.on_buzz = None
    with _peers_lock:
        _peers.clear()
    if sock is not None:
        sock.close()

