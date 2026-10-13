"""Estado compartilhado entre o servidor web (thread do Flask) e o jogo.

O celular manda, a cada mudança e de tempos em tempos, o ESTADO COMPLETO do
controle: botões segurados, analógico e um contador de apertos por botão, tudo
com um número de sequência. Pela rede os pedidos podem chegar fora de ordem;
o número de sequência garante que um pedido atrasado nunca desfaz um mais novo
(botão "preso"), e os contadores garantem que um toque rápido nunca se perde.

O jogo lê, uma vez por quadro, quais comandos estão segurados e quais foram
apertados desde o último quadro.
"""
import threading
import time

SLOTS = (1, 2, 3, 4)
ACTIONS = (
    "up", "down", "left", "right",
    "attack", "special", "dodge", "switch", "super", "dribble", "sprint", "mark",
    "char_left", "char_right", "weapon", "confirm", "cancel", "pause",
)
COMMANDS = frozenset(f"p{s}_{a}" for s in SLOTS for a in ACTIONS)

STALE_SECONDS = 4.0      # sem notícias do celular há esse tempo → desconectado
RELEASE_SECONDS = 20.0   # depois disso a vaga é liberada
INPUT_TIMEOUT = 1.0      # controle sem notícias há esse tempo → solta tudo (para por segurança)
LEGACY_AXIS_SECONDS = 0.6


class PadState:
    """Último estado do controle de uma vaga, como o celular mandou."""

    def __init__(self):
        self.sid = None          # sessão da página (muda quando a página recarrega)
        self.seq = -1            # maior número de sequência aplicado
        self.counts = {}         # botão → quantas vezes foi apertado nesta sessão
        self.held = set()
        self.axis = (0.0, 0.0)
        self.last = 0.0          # instante do último estado aplicado

    def clear(self):
        self.held = set()
        self.axis = (0.0, 0.0)

    @property
    def active(self):
        return bool(self.held) or self.axis != (0.0, 0.0)


class SlotInfo:
    def __init__(self):
        self.token = None
        self.last_seen = 0.0
        # Publicado pelo jogo para o celular espelhar
        self.char = 0
        self.weapon = 0
        self.ready = False
        self.team = None
        self.cooldown = 0.0   # 0..1 do super (futebol)
        self.stamina = 1.0    # 0..1 do fôlego da corrida (futebol)
        self.tired = False    # fôlego acabou: só volta a correr depois de recuperar um pouco

    @property
    def claimed(self):
        return self.token is not None

    def connected(self, now):
        return self.claimed and now - self.last_seen < STALE_SECONDS


class RemoteHub:
    def __init__(self):
        self._lock = threading.Lock()
        self._held = set()
        self._pressed = set()
        self._axes = {}            # vaga → (x, y, instante) do analógico (rota antiga)
        self._pads = {s: PadState() for s in SLOTS}
        self._slots = {s: SlotInfo() for s in SLOTS}
        self._phase = "menu"
        self._mode = "battle"
        self._active = (1, 2)
        self._banner = ""

    # ── entrada vinda do celular ──────────────
    def apply_input(self, slot, sid, seq, held, counts, x=0.0, y=0.0):
        """Aplica um estado completo do controle. Devolve False se foi ignorado."""
        pad = self._pads.get(slot)
        if pad is None or sid is None:
            return False
        prefix = f"p{slot}_"
        now = time.monotonic()
        with self._lock:
            if sid != pad.sid:                # página nova: recomeça a contagem
                pad.sid, pad.seq, pad.counts = sid, -1, {}
            # apertos: contadores só sobem, então qualquer pedido (mesmo atrasado) serve
            for action, n in counts.items():
                if prefix + action not in COMMANDS:
                    continue
                if n > pad.counts.get(action, 0):
                    pad.counts[action] = n
                    self._pressed.add(prefix + action)
            if seq <= pad.seq:
                return False                  # pedido atrasado: o estado dele já é velho
            pad.seq = seq
            pad.held = {a for a in held if prefix + a in COMMANDS}
            mag = (x * x + y * y) ** 0.5
            if mag > 1:
                x, y = x / mag, y / mag
            pad.axis = (x, y) if mag > 0.02 else (0.0, 0.0)
            pad.last = now
            return True

    def press(self, key):
        if key not in COMMANDS:
            return
        with self._lock:
            if key not in self._held:
                self._held.add(key)
                self._pressed.add(key)

    def release(self, key):
        with self._lock:
            self._held.discard(key)

    def set_axis(self, slot, x, y):
        if slot not in self._slots:
            return
        mag = (x * x + y * y) ** 0.5
        if mag > 1:
            x, y = x / mag, y / mag
        with self._lock:
            self._axes[slot] = (x, y, time.monotonic())

    def axes(self):
        """Analógicos atualizados há pouco (um celular que travou não fica andando sozinho)."""
        now = time.monotonic()
        with self._lock:
            out = {s: (x, y) for s, (x, y, t) in self._axes.items() if now - t < LEGACY_AXIS_SECONDS}
            for s, pad in self._pads.items():
                if pad.axis != (0.0, 0.0) and now - pad.last < INPUT_TIMEOUT:
                    out[s] = pad.axis
            return out

    def release_slot(self, slot):
        prefix = f"p{slot}_"
        with self._lock:
            self._held = {k for k in self._held if not k.startswith(prefix)}
            self._axes.pop(slot, None)
            pad = self._pads.get(slot)
            if pad is not None:
                pad.clear()

    def poll(self):
        """Chamado uma vez por quadro: (segurados, apertados desde o último poll)."""
        now = time.monotonic()
        with self._lock:
            held = set(self._held)
            for s, pad in self._pads.items():
                if pad.active and now - pad.last > INPUT_TIMEOUT:
                    pad.clear()               # celular sumiu: não fica correndo sozinho
                held.update(f"p{s}_{a}" for a in pad.held)
            pressed = frozenset(self._pressed)
            self._pressed.clear()
        return frozenset(held), pressed

    # ── vagas ────────────────────────────────
    def join(self, slot, token):
        if slot not in self._slots or not token:
            return False
        now = time.monotonic()
        with self._lock:
            info = self._slots[slot]
            free = (not info.claimed or info.token == token
                    or now - info.last_seen > RELEASE_SECONDS)
            if not free:
                return False
            # um celular ocupa só uma vaga por vez
            for other in self._slots.values():
                if other is not info and other.token == token:
                    other.token = None
            info.token = token
            info.last_seen = now
            return True

    def leave(self, slot, token):
        with self._lock:
            info = self._slots.get(slot)
            if info and info.token == token:
                info.token = None
        self.release_slot(slot)

    def touch(self, slot, token):
        with self._lock:
            info = self._slots.get(slot)
            if info and info.token == token:
                info.last_seen = time.monotonic()
                return True
            return False

    def connected_slots(self):
        now = time.monotonic()
        with self._lock:
            return {s for s, info in self._slots.items() if info.connected(now)}

    # ── publicado pelo jogo ──────────────────
    def set_phase(self, phase, mode=None, active=None, banner=""):
        with self._lock:
            self._phase = phase
            if mode is not None:
                self._mode = mode
            if active is not None:
                self._active = tuple(active)
            self._banner = banner
        if phase != "playing":
            with self._lock:
                self._held.clear()
                for pad in self._pads.values():
                    pad.held = set()

    def publish_slot(self, slot, **fields):
        """Atualiza o que o celular mostra: char, weapon, ready, team, cooldown, stamina, tired."""
        with self._lock:
            info = self._slots[slot]
            for name, value in fields.items():
                if name not in ("char", "weapon", "ready", "team", "cooldown", "stamina", "tired"):
                    raise ValueError(name)
                setattr(info, name, value)

    def status(self, slot=None, token=None):
        now = time.monotonic()
        with self._lock:
            mine = self._slots.get(slot)
            data = {
                "phase": self._phase,
                "mode": self._mode,
                "active": list(self._active),
                "banner": self._banner,
                "slots": {
                    str(s): {"claimed": i.claimed, "connected": i.connected(now)}
                    for s, i in self._slots.items()
                },
            }
            if mine is not None:
                data["me"] = {
                    "slot": slot,
                    "owner": mine.token is not None and mine.token == token,
                    "char": mine.char,
                    "weapon": mine.weapon,
                    "ready": mine.ready,
                    "team": mine.team,
                    "cooldown": round(mine.cooldown, 3),
                    "stamina": round(mine.stamina, 3),
                    "tired": mine.tired,
                    "playing": slot in self._active,
                }
            return data


hub = RemoteHub()
