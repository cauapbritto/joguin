"""O que cada botão do controle faz, por controle (tela CONTROLE).

Cada controle é guardado pelo nome que o sistema dá a ele, com um perfil para a luta (duelo e
campanha) e outro para os esportes (futebol, basquete e pênaltis), porque o mesmo botão faz coisas
diferentes em cada um. START, BACK, o direcional e o analógico não mudam (ninguém fica sem pausar ou
sem voltar), e o A e o B continuam confirmando e voltando nos menus.
"""
from . import settings

BUTTONS = ("a", "b", "x", "y", "lb", "rb", "lt", "rt")     # os que dá para trocar
CONTEXTS = ("luta", "bola")
CONTEXT_LABELS = {"luta": "LUTA E CAMPANHA", "bola": "FUTEBOL E BASQUETE"}

# ações de cada contexto, na ordem da lista de escolha (o nome é o mesmo que o celular manda)
ACTIONS = {
    "luta": [("attack", "ATACAR"), ("special", "HABILIDADE"), ("switch", "TROCAR ARMA"), ("dodge", "ESQUIVA"),
             ("none", "NADA")],
    "bola": [("attack", "CHUTAR"), ("special", "PASSE"), ("super", "SUPER"), ("dodge", "CORTE"),
             ("sprint", "CORRER"), ("mark", "MARCAR"), ("dribble", "CONDUZIR COLADO"), ("none", "NADA")],
}
ACTION_LABELS = {ctx: dict(items) for ctx, items in ACTIONS.items()}

PRESETS = {
    "padrao": {
        "luta": {"a": "attack", "b": "dodge", "x": "special", "y": "switch", "lb": "none", "rb": "none",
                 "lt": "dodge", "rt": "none"},
        "bola": {"a": "attack", "b": "dodge", "x": "special", "y": "super", "lb": "mark", "rb": "dribble",
                 "lt": "dodge", "rt": "sprint"},
    },
    # atacar/chutar no gatilho direito, como nos jogos de tiro; o A vira habilidade/passe
    "gatilho": {
        "luta": {"a": "special", "b": "dodge", "x": "switch", "y": "switch", "lb": "none", "rb": "special",
                 "lt": "dodge", "rt": "attack"},
        "bola": {"a": "special", "b": "dodge", "x": "super", "y": "super", "lb": "mark", "rb": "dribble",
                 "lt": "sprint", "rt": "attack"},
    },
    # ombros e gatilhos trocados de lado
    "canhoto": {
        "luta": {"a": "attack", "b": "dodge", "x": "special", "y": "switch", "lb": "none", "rb": "none",
                 "lt": "none", "rt": "dodge"},
        "bola": {"a": "attack", "b": "dodge", "x": "special", "y": "super", "lb": "dribble", "rb": "mark",
                 "lt": "sprint", "rt": "dodge"},
    },
}
PRESET_ORDER = ("padrao", "gatilho", "canhoto", "meu")
PRESET_LABELS = {"padrao": "PADRÃO", "gatilho": "CHUTE NO GATILHO", "canhoto": "CANHOTO", "meu": "MEU JEITO"}

DEFAULT_DEADZONE = 0.22
DEADZONE_RANGE = (0.08, 0.5)

# nome escrito em cada botão, por família de controle (os símbolos do PlayStation são desenhados: pad_art.py)
LABELS = {
    "xbox": {"a": "A", "b": "B", "x": "X", "y": "Y", "lb": "LB", "rb": "RB", "lt": "LT", "rt": "RT",
             "back": "BACK", "start": "START", "ls": "L", "dpad": "+"},
    "playstation": {"a": "", "b": "", "x": "", "y": "", "lb": "L1", "rb": "R1", "lt": "L2", "rt": "R2",
                    "back": "SHARE", "start": "OPTIONS", "ls": "L", "dpad": "+"},
    "nintendo": {"a": "A", "b": "B", "x": "X", "y": "Y", "lb": "L", "rb": "R", "lt": "ZL", "rt": "ZR",
                 "back": "-", "start": "+", "ls": "L", "dpad": "+"},
    # Joy-Con deitado: os 4 botões viram setas (cada lado tem letras diferentes), SL e SR em cima
    "joycon": {"a": "↓", "b": "→", "x": "←", "y": "↑", "lb": "SL", "rb": "SR", "back": "-", "start": "+/-",
               "ls": "L"},
}
# Joy-Con sozinho não tem gatilho: o que ficava no gatilho vai para o SL e o SR
JOYCON_PADRAO = {
    "luta": {"a": "attack", "b": "dodge", "x": "special", "y": "switch", "lb": "dodge", "rb": "special",
             "lt": "none", "rt": "none"},
    "bola": {"a": "attack", "b": "dodge", "x": "special", "y": "super", "lb": "mark", "rb": "sprint",
             "lt": "none", "rt": "none"},
}
# nome para texto (a fonte não tem os símbolos do PlayStation)
TEXT_LABELS = {"playstation": {"a": "XIS", "b": "BOLA", "x": "QUADRADO", "y": "TRIÂNGULO"}}
FAMILY_NAMES = {"xbox": "XBOX", "playstation": "PLAYSTATION", "nintendo": "NINTENDO", "joycon": "JOY-CON"}


def buttons(name):
    """Botões que este controle tem e dá para trocar."""
    if family(name) == "joycon":
        return ("a", "b", "x", "y", "lb", "rb")
    return BUTTONS


def presets(name):
    """Perfis que fazem sentido neste controle (o Joy-Con não tem gatilho para o CHUTE NO GATILHO)."""
    return ("padrao", "meu") if family(name) == "joycon" else PRESET_ORDER


def default(name, context):
    return dict(JOYCON_PADRAO[context] if family(name) == "joycon" else PRESETS["padrao"][context])


def family(name):
    """xbox, playstation, nintendo ou joycon (um Joy-Con sozinho, deitado), pelo nome do controle.

    O par de Joy-Cons junto (L/R) funciona como um controle Pro. Controle genérico = xbox."""
    n = (name or "").lower()
    if ("joy-con" in n or "joycon" in n) and not any(w in n for w in ("l/r", "pair", "par")):
        if any(w in n for w in ("(l)", "(r)", " l)", " r)", "left", "right")):
            return "joycon"
    if any(w in n for w in ("nintendo", "switch", "pro controller", "joy-con", "joycon")):
        return "nintendo"
    if any(w in n for w in ("playstation", "ps3", "ps4", "ps5", "dualshock", "dualsense", "sony")):
        return "playstation"
    return "xbox"


def label(name, button):
    return LABELS[family(name)].get(button, button.upper())


def text_label(name, button):
    fam = family(name)
    return TEXT_LABELS.get(fam, {}).get(button) or LABELS[fam].get(button, button.upper())


def _key(name):
    return (name or "controle")[:40]


def _saved(name):
    return settings.get("controles").get(_key(name), {})


def preset(name):
    p = _saved(name).get("perfil")
    return p if p in presets(name) else "padrao"


def mapping(name, context):
    """{botão: ação} deste controle no contexto ('luta' ou 'bola')."""
    saved = _saved(name)
    p = preset(name)
    if p == "padrao":
        return default(name, context)
    if p == "meu":
        base = default(name, context)
        custom = saved.get(context)
        if isinstance(custom, dict):
            valid = ACTION_LABELS[context]
            base.update({b: a for b, a in custom.items() if b in BUTTONS and a in valid})
        return base
    return dict(PRESETS[p][context])


def deadzone(name):
    value = _saved(name).get("zona")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return max(DEADZONE_RANGE[0], min(DEADZONE_RANGE[1], float(value)))
    return DEFAULT_DEADZONE


def _store(name, **changes):
    all_pads = dict(settings.get("controles"))
    entry = dict(all_pads.get(_key(name), {}))
    entry.update(changes)
    all_pads[_key(name)] = entry
    settings.change("controles", all_pads)


def set_preset(name, value):
    _store(name, perfil=value)


def set_action(name, context, button, action):
    """Troca o que um botão faz. Vira o perfil MEU JEITO (partindo do perfil que estava)."""
    current = {ctx: mapping(name, ctx) for ctx in CONTEXTS}
    current[context][button] = action
    _store(name, perfil="meu", luta=current["luta"], bola=current["bola"])


def set_deadzone(name, value):
    value = round(max(DEADZONE_RANGE[0], min(DEADZONE_RANGE[1], value)), 2)
    _store(name, zona=value)
    return value


def changed(name, context):
    """Botões que fazem algo diferente do padrão (ficam dourados na tela)."""
    current = mapping(name, context)
    base = default(name, context)
    return {b for b in buttons(name) if current[b] != base[b]}


def buttons_with(name, context, action):
    current = mapping(name, context)
    return [b for b in buttons(name) if current[b] == action]


def context_of(layout):
    return "bola" if layout == "soccer" else "luta"
