"""Estado compartilhado entre o servidor web (thread do Flask) e o jogo.

O celular manda "apertou"/"soltou" para comandos como ``p1_attack``. O jogo lê,
uma vez por quadro, quais teclas estão seguradas e quais foram apertadas desde o
último quadro — assim um toque rápido nunca se perde entre dois quadros.
"""
import threading
import time

SLOTS = (1, 2, 3, 4)
ACTIONS = (
    "up", "down", "left", "right",
    "attack", "special", "dodge", "switch", "super", "dribble",
    "char_left", "char_right", "weapon", "confirm", "cancel", "pause",
)
COMMANDS = frozenset(f"p{s}_{a}" for s in SLOTS for a in ACTIONS)

STALE_SECONDS = 4.0      # sem notícias do celular há esse tempo → desconectado
RELEASE_SECONDS = 20.0   # depois disso a vaga é liberada


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
        self._axes = {}            # vaga → (x, y, instante) do analógico do celular
        self._slots = {s: SlotInfo() for s in SLOTS}
        self._phase = "menu"
        self._mode = "battle"
        self._active = (1, 2)
        self._banner = ""

    # ── entrada vinda do celular ──────────────
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
            return {s: (x, y) for s, (x, y, t) in self._axes.items() if now - t < 0.6}

    def release_slot(self, slot):
        prefix = f"p{slot}_"
        with self._lock:
            self._held = {k for k in self._held if not k.startswith(prefix)}
            self._axes.pop(slot, None)

    def poll(self):
        """Chamado uma vez por quadro: (segurados, apertados desde o último poll)."""
        with self._lock:
            held = frozenset(self._held)
            pressed = frozenset(self._pressed)
            self._pressed.clear()
        return held, pressed

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

    def publish_slot(self, slot, **fields):
        """Atualiza o que o celular mostra: char, weapon, ready, team, cooldown."""
        with self._lock:
            info = self._slots[slot]
            for name, value in fields.items():
                if name not in ("char", "weapon", "ready", "team", "cooldown"):
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
                    "playing": slot in self._active,
                }
            return data


hub = RemoteHub()
