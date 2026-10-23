"""Entrada dos jogadores: teclado e celular passam pela mesma interface."""
import math

import pygame

from . import config, settings

K = pygame
KEYMAP = {
    1: {
        "up": (K.K_w,), "down": (K.K_s,), "left": (K.K_a,), "right": (K.K_d,),
        "attack": (K.K_g,), "special": (K.K_f,), "dodge": (K.K_LSHIFT, K.K_SPACE),
        "switch": (K.K_q,), "super": (K.K_q,), "dribble": (K.K_e,),
        "char_left": (K.K_a,), "char_right": (K.K_d,), "weapon": (K.K_w, K.K_s),
        "confirm": (K.K_g,), "cancel": (K.K_f,),
    },
    2: {
        "up": (K.K_UP,), "down": (K.K_DOWN,), "left": (K.K_LEFT,), "right": (K.K_RIGHT,),
        "attack": (K.K_SEMICOLON, K.K_KP1), "special": (K.K_SLASH, K.K_KP2),
        "dodge": (K.K_PERIOD, K.K_KP3), "switch": (K.K_u, K.K_COMMA, K.K_KP0),
        "super": (K.K_u, K.K_COMMA, K.K_KP0), "dribble": (K.K_RSHIFT, K.K_KP4),
        "char_left": (K.K_LEFT,), "char_right": (K.K_RIGHT,), "weapon": (K.K_UP, K.K_DOWN),
        "confirm": (K.K_SEMICOLON, K.K_m, K.K_KP1), "cancel": (K.K_SLASH, K.K_KP2),
    },
}

# No futebol algumas teclas mudam: CORRER e MARCAR entram, e o corte sai do SHIFT
SOCCER_KEYMAP = {
    1: {"dodge": (K.K_SPACE,), "sprint": (K.K_LSHIFT,), "mark": (K.K_r,)},
    2: {"sprint": (K.K_RSHIFT,), "mark": (K.K_RETURN, K.K_KP5), "dribble": (K.K_l, K.K_KP4)},
}

# Teclas que o jogador pode trocar (tela TROCAR TECLAS): (id, rótulo, layout, ações que usam a tecla).
# Trocar uma tecla troca ela em todas as ações da família (ATACAR também confirma, A também
# escolhe o personagem da esquerda...). As linhas do futebol só valem no futebol; as do duelo valem
# no futebol também, menos onde o futebol tem tecla própria.
REBINDABLE = (
    ("up", "CIMA", "battle", ("up", "weapon")),
    ("down", "BAIXO", "battle", ("down", "weapon")),
    ("left", "ESQUERDA", "battle", ("left", "char_left")),
    ("right", "DIREITA", "battle", ("right", "char_right")),
    ("attack", "ATACAR / CHUTAR", "battle", ("attack", "confirm")),
    ("special", "HABILIDADE / PASSE", "battle", ("special", "cancel")),
    ("dodge", "ESQUIVA (DUELO)", "battle", ("dodge",)),
    ("switch", "TROCAR ARMA / SUPER", "battle", ("switch", "super")),
    ("soccer_dodge", "CORTE / CARRINHO (FUTEBOL)", "soccer", ("dodge",)),
    ("sprint", "CORRER (FUTEBOL)", "soccer", ("sprint",)),
    ("mark", "MARCAR (FUTEBOL)", "soccer", ("mark",)),
    ("dribble", "CONDUZIR COLADO (FUTEBOL)", "soccer", ("dribble",)),
)
REBIND_BY_ID = {r[0]: r for r in REBINDABLE}
# teclas que não dá para usar: pausam, voltam ou mudam a tela
RESERVED_KEYS = (K.K_ESCAPE, K.K_F11, K.K_F3, K.K_BACKSPACE, K.K_p, K.K_TAB)


def _base_keymap(slot, layout):
    keys = {a: tuple(c) for a, c in KEYMAP.get(slot, {}).items()}
    if layout == "soccer":
        keys.update(SOCCER_KEYMAP.get(slot, {}))
    return keys


def default_key(slot, row_id):
    """Tecla de fábrica de uma linha de REBINDABLE."""
    _, _, layout, family = REBIND_BY_ID[row_id]
    codes = _base_keymap(slot, layout).get(family[0], ())
    return codes[0] if codes else None


def custom_keys(slot):
    """Teclas trocadas pelo jogador: {id da linha: código} (só as válidas)."""
    saved = settings.get("teclas").get(str(slot), {})
    return {row: code for row, code in saved.items()
            if row in REBIND_BY_ID and isinstance(code, int) and code not in RESERVED_KEYS}


def current_key(slot, row_id):
    return custom_keys(slot).get(row_id, default_key(slot, row_id))


def build_keymap(slot, layout):
    """Mapa ação → teclas do jogador, já com as teclas que ele trocou."""
    keys = _base_keymap(slot, layout)
    soccer_own = SOCCER_KEYMAP.get(slot, {})
    allowed = {}                             # ação → teclas que o jogador deu a ela
    for row_id, code in custom_keys(slot).items():
        _, _, row_layout, family = REBIND_BY_ID[row_id]
        if row_layout == "soccer" and layout != "soccer":
            continue
        old = default_key(slot, row_id)
        for action in family:
            if layout == "soccer" and row_layout == "battle" and action in soccer_own:
                continue                     # o futebol tem tecla própria para essa ação
            codes = keys.get(action, ())
            codes = tuple(code if c == old else c for c in codes)
            if code not in codes:
                codes = (code,) + codes
            keys[action] = codes
            allowed.setdefault(action, set()).add(code)
    # tecla escolhida por alguém sai das teclas extras de fábrica (ex.: o ESPAÇO também esquiva
    # no P1; se o P2 escolheu o ESPAÇO, ele deixa de esquivar o P1)
    claimed = {c for s in (1, 2) for c in custom_keys(s).values()}
    for action, codes in keys.items():
        keys[action] = tuple(c for c in codes if c not in claimed or c in allowed.get(action, ()))
    return keys


def bind_key(slot, row_id, code):
    """Troca a tecla de uma linha. Se ela já era de outra linha do mesmo jogador (e do mesmo
    tipo de partida), as duas trocam de lugar. Devolve (ok, mensagem)."""
    if code in RESERVED_KEYS:
        return False, "ESSA TECLA É DO JOGO (PAUSA, VOLTAR OU TELA)"
    layout = REBIND_BY_ID[row_id][2]
    other = 2 if slot == 1 else 1
    for rid, _, lay, _ in REBINDABLE:
        if current_key(other, rid) == code and (lay == layout or "battle" in (lay, layout)):
            return False, f"JÁ É DO JOGADOR {other}"
    teclas = {k: dict(v) for k, v in settings.get("teclas").items()}
    mine = teclas.setdefault(str(slot), {})
    old = current_key(slot, row_id)
    for rid, _, lay, _ in REBINDABLE:
        if rid != row_id and lay == layout and current_key(slot, rid) == code:
            mine[rid] = old                  # troca de lugar com a linha que usava essa tecla
    mine[row_id] = code
    for rid in list(mine):
        if mine[rid] == default_key(slot, rid):
            del mine[rid]                    # voltou ao padrão: não precisa guardar
    settings.change("teclas", teclas)
    return True, ""


def reset_keys(slot=None):
    teclas = {k: dict(v) for k, v in settings.get("teclas").items()}
    for s in ([slot] if slot else [1, 2]):
        teclas.pop(str(s), None)
    settings.change("teclas", teclas)


_KEY_NAMES = {"left shift": "SHIFT", "right shift": "SHIFT DIR", "space": "ESPAÇO", "return": "ENTER",
              "up": "↑", "down": "↓", "left": "←", "right": "→", "left ctrl": "CTRL", "right ctrl": "CTRL DIR",
              "left alt": "ALT", "right alt": "ALT GR", "keypad enter": "ENTER NUM"}


def key_name(code):
    if code is None:
        return "-"
    name = pygame.key.name(code)
    if not name:
        return f"#{code}"
    if name.startswith("[") and name.endswith("]"):
        return name[1:-1].upper() + " NUM"
    return _KEY_NAMES.get(name, name.upper())


def key_label(slot, row_id):
    return key_name(current_key(slot, row_id))


def move_label(slot):
    keys = [current_key(slot, r) for r in ("up", "left", "down", "right")]
    if keys == [K.K_UP, K.K_LEFT, K.K_DOWN, K.K_RIGHT]:
        return "SETAS"
    return " ".join(key_name(k) for k in keys)


DIRECTIONS = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}


class PlayerInput:
    """Estado dos comandos de um jogador neste quadro (teclado + celular)."""

    double_tap_enabled = True       # duplo toque numa seta = esquiva/corte (opção no menu)

    def __init__(self, slot):
        self.slot = slot
        self.keys = build_keymap(slot, "battle")
        self.layout = "battle"
        self.prefix = f"p{slot}_"
        self._held = set()
        self._pressed = set()
        self._last_tap = {}
        self.double_tap = None
        self.analog = None
        self._kb_dirs = (0, 0)

    def set_layout(self, layout):
        """'soccer' troca algumas teclas (CORRER, MARCAR); qualquer outro valor volta ao normal."""
        self.layout = layout
        self.keys = build_keymap(self.slot, layout)

    def update(self, keys_down, keys_pressed, remote_held, remote_pressed, now_ms, analog=None):
        self.analog = analog
        held, pressed = set(), set()
        for action, codes in self.keys.items():
            if any(keys_down[c] for c in codes):
                held.add(action)
            if any(c in keys_pressed for c in codes):
                pressed.add(action)
        # direções do teclado ficam separadas: o celular manda o analógico de verdade
        self._kb_dirs = (("right" in held) - ("left" in held), ("down" in held) - ("up" in held))
        kb_pressed = set(pressed)
        n = len(self.prefix)
        for key in remote_held:
            if key.startswith(self.prefix):
                held.add(key[n:])
        for key in remote_pressed:
            if key.startswith(self.prefix):
                pressed.add(key[n:])
                held.add(key[n:])
        self._held, self._pressed = held, pressed

        # duplo toque numa seta do teclado = esquiva (no celular há botão; o analógico
        # cruzando a mesma direção duas vezes não pode virar esquiva sem querer)
        self.double_tap = None
        if not self.double_tap_enabled:
            return
        for d in DIRECTIONS:
            if d in kb_pressed:
                if now_ms - self._last_tap.get(d, -10_000) < config.DOUBLE_TAP_MS:
                    self.double_tap = DIRECTIONS[d]
                    self._last_tap[d] = -10_000
                else:
                    self._last_tap[d] = now_ms

    def held(self, action):
        return action in self._held

    def pressed(self, action):
        return action in self._pressed

    def axis(self):
        dx, dy = self._kb_dirs
        mag = math.hypot(dx, dy)
        if mag:
            return dx / mag, dy / mag
        # analógico do celular: 360 graus e meia velocidade com o polegar perto do centro
        if self.analog and (abs(self.analog[0]) > 0.05 or abs(self.analog[1]) > 0.05):
            return self.analog
        # direções vindas do celular sem analógico (página antiga)
        dx = self.held("right") - self.held("left")
        dy = self.held("down") - self.held("up")
        mag = math.hypot(dx, dy)
        if mag:
            return dx / mag, dy / mag
        return 0.0, 0.0
