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
import unicodedata

from .. import settings

SLOTS = (1, 2, 3, 4)
ACTIONS = (
    "up", "down", "left", "right",
    "attack", "special", "dodge", "switch", "drop", "super", "dribble", "sprint", "mark",
    "char_left", "char_right", "weapon", "confirm", "cancel", "pause",
    "opt1", "opt2", "opt3",          # escolher uma das 3 melhorias (campanha)
)
COMMANDS = frozenset(f"p{s}_{a}" for s in SLOTS for a in ACTIONS)

STALE_SECONDS = 4.0      # sem notícias do celular há esse tempo → desconectado
RELEASE_SECONDS = 20.0   # depois disso a vaga é liberada
ORDER_CHARS = 120        # pedido da loja do celular (no computador, o texto digitado vai junto)
INPUT_TIMEOUT = 1.0      # controle sem notícias há esse tempo → solta tudo (para por segurança)
LEGACY_AXIS_SECONDS = 0.6
BUZZ_GAP = 0.25          # vibração do celular: no máximo uma a cada 250 ms por jogador
NICK_CHARS = 10          # apelido que o app manda (a TV mostra no lugar de P1)
# letras que a fonte do jogo desenha: o resto do apelido some (emoji, símbolos)
NICK_LETTERS = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ÁÀÂÃÉÊÍÓÔÕÚÜÇ -_.!?")
REACTIONS = ("gg", "kkk", "vem", "palmas")   # as reações rápidas do app (o balão em cima do boneco)
REACTION_GAP = 1.0       # no máximo uma reação por segundo por jogador
REACTION_SECONDS = 1.8   # quanto tempo o balão fica no ar


def clean_nick(text):
    """Apelido como a TV mostra: maiúsculas, só letras que a fonte tem, até NICK_CHARS. Vazio vira None."""
    if not isinstance(text, str):
        return None
    text = unicodedata.normalize("NFC", text).upper()
    out = "".join(ch if ch in NICK_LETTERS else " " for ch in text)
    out = " ".join(out.split())[:NICK_CHARS].strip()
    return out or None


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
        self.ammo = 0         # munição da arma na mão (duelo e campanha)
        self.mag = 0          # tamanho do pente (0 = arma sem munição, ex.: corpo a corpo)
        self.reload = 0.0     # 0..1 da recarga (0 = não está recarregando)
        self.buzz = [0, ""]   # vibração: [contador, padrão]; o celular vibra quando o contador muda
        self.buzz_at = -1.0   # quando foi a última (no máximo uma a cada BUZZ_GAP)
        self.options = []     # melhorias para escolher (campanha): [{name, desc, color}]
        self.choice = 0       # qual está marcada
        self.souls = None     # saldo de almas na campanha (None = fora da campanha)
        self.energy = 0       # energia da campanha (energia.py), a barra cheia e o custo da arma da mão
        self.emax = 0
        self.ecost = 0
        self.shop = None      # menu da banca aberto (MarketMenu.snapshot) ou None
        self.penalty = None   # pênaltis: {"role": "bate" / "defende" / "espera", "hero": nome} ou None
        self.hand = None      # arma na mão: {"name", "icon"} (o ATACAR do celular mostra o desenho e o nome)
        self.nick = None      # apelido mandado pelo app (a TV mostra no lugar de P1); sai junto com o celular
        self.reaction = None  # (índice em REACTIONS, instante) da última reação do app

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
        self.roster_size = 0       # quantos personagens o celular deve mostrar (muda ao liberar um)
        self.news = []             # resumo das novidades (o celular mostra com a tela de novidades aberta)
        self.news_page = None      # notícia aberta no plantão: {"index", "total", "title"}
        self._news_taps = []       # botões < PULAR > do celular na tela de novidades
        self.hud = "battle"         # disposição de botões do celular (battle, soccer, basket)
        self._orders = []          # pedidos da loja vindos do celular: (vaga, id do item, comprar?)
        self._screens = {}         # computador da Casa aberto: vaga -> PNG da tela (o celular toca nela)
        self._reactions = []       # reações do app desde o último quadro: (vaga, índice) para o som
        self._summary = None       # resumo da partida que acabou (resumo.py), na tela de resultado
        self._map = None           # mapa da fase ou da Casa para o celular (dict pronto para virar JSON)
        self.on_buzz = None        # chamado com a vaga quando ela vibra (o canal rápido do app avisa na hora)

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

    def order(self, slot, item, buy):
        """Pedido da loja do celular (marcar ou comprar um item, ou "fechar"). O jogo aplica no quadro."""
        if slot not in self._slots or not item:
            return False
        with self._lock:
            if self._slots[slot].shop is None:
                return False                  # a banca já fechou
            self._orders = (self._orders + [(slot, str(item)[:ORDER_CHARS], bool(buy))])[-16:]
            return True

    def set_screen(self, slot, png):
        """A tela do computador que esta vaga abriu, em PNG (None: fechou)."""
        with self._lock:
            if png is None:
                self._screens.pop(slot, None)
            else:
                self._screens[slot] = png

    def screen(self, slot, token):
        """PNG da tela do computador para o celular desta vaga (só com o token certo)."""
        with self._lock:
            info = self._slots.get(slot)
            if info is None or info.token != token:
                return None
            return self._screens.get(slot)

    def news_tap(self, slot, go):
        """Botão do celular na tela de novidades: "prev", "next" ou "skip". O jogo aplica no quadro."""
        if slot not in self._slots or go not in ("prev", "next", "skip"):
            return False
        with self._lock:
            if self._phase != "news":
                return False
            self._news_taps = (self._news_taps + [go])[-8:]
            return True

    def news_taps(self):
        """Toques do celular na tela de novidades desde o último quadro (e esvazia a fila)."""
        with self._lock:
            out, self._news_taps = self._news_taps, []
        return out

    def orders(self):
        """Pedidos da loja desde o último quadro (e esvazia a fila)."""
        with self._lock:
            out, self._orders = self._orders, []
        return out

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
                    other.nick = other.reaction = None
            if info.token != token:               # outro celular: o apelido do anterior não vale
                info.nick = info.reaction = None
            info.token = token
            info.last_seen = now
            return True

    def leave(self, slot, token):
        with self._lock:
            info = self._slots.get(slot)
            if info and info.token == token:
                info.token = None
                info.nick = info.reaction = None
        self.release_slot(slot)

    # ── apelido e reações do app ──────────────
    def set_nick(self, slot, token, nick):
        """O app mandou o apelido do jogador (vazio apaga). False se o token não é o desta vaga."""
        with self._lock:
            info = self._slots.get(slot)
            if info is None or info.token is None or info.token != token:
                return False
            info.nick = clean_nick(nick)
            info.last_seen = time.monotonic()
            return True

    def nick(self, slot):
        """Apelido de quem está nesta vaga pelo app, ou None (aí a TV mostra P1, P2...)."""
        info = self._slots.get(slot)
        if info is None or info.token is None:
            return None
        return info.nick

    def react(self, slot, token, kind):
        """Reação do app: True (vale), False (token errado) ou None (cedo demais, ou tipo que não existe)."""
        now = time.monotonic()
        with self._lock:
            info = self._slots.get(slot)
            if info is None or info.token is None or info.token != token:
                return False
            if not isinstance(kind, int) or isinstance(kind, bool) or not 0 <= kind < len(REACTIONS):
                return None
            if info.reaction is not None and now - info.reaction[1] < REACTION_GAP:
                return None
            info.reaction = (kind, now)
            info.last_seen = now
            self._reactions = (self._reactions + [(slot, kind)])[-8:]
            return True

    def reaction(self, slot):
        """(índice, idade em segundos) da reação desta vaga ainda no ar, ou None."""
        info = self._slots.get(slot)
        r = info.reaction if info is not None else None
        if r is None:
            return None
        age = time.monotonic() - r[1]
        return (r[0], age) if age < REACTION_SECONDS else None

    def reactions(self):
        """Reações chegadas desde o último quadro (e esvazia a fila): o jogo toca o som de cada uma."""
        with self._lock:
            out, self._reactions = self._reactions, []
        return out

    # ── resumo da partida e mapa (o jogo publica, o celular lê) ──
    def set_summary(self, summary):
        with self._lock:
            self._summary = summary

    def set_map(self, data):
        with self._lock:
            self._map = data

    def map_for(self, slot, token):
        """O mapa publicado (fase ou Casa) para o celular desta vaga, ou None (sem mapa ou token errado)."""
        with self._lock:
            info = self._slots.get(slot)
            if info is None or info.token is None or info.token != token:
                return None
            return self._map if self._phase in ("playing", "paused") else None

    def owns(self, slot, token):
        """O token é o do celular que está nesta vaga."""
        with self._lock:
            info = self._slots.get(slot)
            return info is not None and info.token is not None and info.token == token

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
            if phase != "results":
                self._summary = None          # o resumo é só da tela de resultado que o publicou
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
                if phase != "paused":
                    for info in self._slots.values():
                        info.shop = None
                        if phase != "penalty":
                            info.penalty = None

    def publish_slot(self, slot, **fields):
        """Atualiza o que o celular mostra: char, weapon, ready, team, cooldown, stamina, tired,
        munição (ammo, mag, reload), options e choice (melhorias da campanha), souls (saldo) e shop (banca aberta)."""
        with self._lock:
            info = self._slots[slot]
            for name, value in fields.items():
                if name not in ("char", "weapon", "ready", "team", "cooldown", "stamina", "tired",
                                "options", "choice", "ammo", "mag", "reload", "souls", "shop", "penalty",
                                "energy", "emax", "ecost", "hand"):
                    raise ValueError(name)
                setattr(info, name, value)

    def buzz(self, slot, pattern, force=False):
        """Vibra o celular desta vaga com um padrão (o celular conhece os nomes: hit, big_hit, score,
        super, call, tick, go, block, fall). No máximo uma a cada BUZZ_GAP, para não virar um zumbido sem fim;
        ``force`` passa por cima disso (avisos que não podem se perder, como o portal)."""
        now = time.monotonic()
        with self._lock:
            info = self._slots.get(slot)
            if info is None or not info.connected(now):
                return False
            if not force and now - info.buzz_at < BUZZ_GAP:
                return False
            info.buzz = [info.buzz[0] + 1, pattern]
            info.buzz_at = now
        notify = self.on_buzz
        if notify is not None:
            notify(slot)
        return True

    def status(self, slot=None, token=None):
        now = time.monotonic()
        with self._lock:
            mine = self._slots.get(slot)
            data = {
                "phase": self._phase,
                "mode": self._mode,
                "active": list(self._active),
                "banner": self._banner,
                "roster": self.roster_size,
                "hud": self.hud,
                "news": self.news if self._phase == "news" else [],
                "news_page": self.news_page if self._phase == "news" else None,
                "slots": {
                    str(s): {"claimed": i.claimed, "connected": i.connected(now)}
                    for s, i in self._slots.items()
                },
                "summary": self._summary if self._phase == "results" else None,
                "map": self._map is not None and self._phase in ("playing", "paused"),
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
                    "ammo": mine.ammo,
                    "mag": mine.mag,
                    "reload": round(mine.reload, 3),
                    "energy": mine.energy if self._mode == "campaign" else 0,
                    "emax": mine.emax if self._mode == "campaign" else 0,
                    "ecost": mine.ecost if self._mode == "campaign" else 0,
                    "buzz": list(mine.buzz),
                    "vibracao": bool(settings.get("vibracao")),   # a opção do jogo (o TESTAR do celular avisa)
                    "options": mine.options,
                    "choice": mine.choice,
                    "souls": mine.souls if self._mode == "campaign" else None,
                    "shop": mine.shop if self._mode == "campaign" else None,
                    "penalty": mine.penalty if self._phase == "penalty" else None,
                    "hand": mine.hand,
                    "nick": mine.nick,
                    "playing": slot in self._active,
                }
            return data



def hand_card(weapon):
    """A arma na mão como o botão ATACAR do celular mostra: nome e arquivo do desenho."""
    if weapon is None:
        return None
    from ..weapon_art import icon_file
    return {"name": weapon.name.upper(), "icon": icon_file(weapon.name)}


hub = RemoteHub()
