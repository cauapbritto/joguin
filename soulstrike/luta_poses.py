"""Quadros-chave do modo LUTA (ângulos do esqueleto; veja luta_rig.py para as convenções).

Quadros no chão são plantados sozinhos (o pé mais baixo encosta no chão); os do ar levam
air=True e a altura vem do pulo. Cada lutador pode trocar um quadro em OVERRIDES.
"""

GUARD = dict(lean=6, turn=0.25, na=(30, 118), fa=(60, 108), nl=(24, -34, 0), fl=(-26, -12, 14))

POSES = {
    # parado: respira (2 quadros)
    "guarda": dict(GUARD),
    "guarda2": dict(GUARD, lean=8, dy=1, na=(28, 122), fa=(58, 112)),
    # andar: as pernas trocam de lugar (4 quadros)
    "andar1": dict(GUARD, nl=(30, -24, 0), fl=(-22, -16, 20)),
    "andar2": dict(GUARD, lean=7, nl=(8, -40, 10), fl=(-4, -26, 10)),
    "andar3": dict(GUARD, nl=(-18, -18, 20), fl=(28, -26, 0)),
    "andar4": dict(GUARD, lean=7, nl=(-2, -32, 10), fl=(12, -40, 0)),
    "agachado": dict(lean=14, turn=0.3, na=(40, 110), fa=(70, 100), nl=(72, -112, 0), fl=(14, -96, 30)),
    # pulo
    "pulo": dict(air=True, lean=4, turn=0.3, na=(50, 100), fa=(80, 90), nl=(70, -110, 20), fl=(30, -100, 40)),
    "queda": dict(air=True, lean=0, turn=0.3, na=(70, 70), fa=(100, 60), nl=(30, -50, 20), fl=(-10, -40, 40)),
    # SOCO: direto com o braço de trás (o quadril gira e o pé de trás fica na ponta)
    "soco1": dict(lean=12, turn=0.5, x=3, na=(10, 140), fa=(60, 70), nl=(32, -34, 0), fl=(-30, -6, 60)),
    "soco2": dict(lean=22, turn=0.95, x=8, na=(-10, 150), fa=(98, -4), stretch=1.22, nl=(38, -38, 0), fl=(-34, 0, 80),
                  smile=False),
    "soco3": dict(lean=10, turn=0.45, x=3, na=(15, 130), fa=(65, 80), nl=(28, -34, 0), fl=(-28, -8, 45)),
    # CHUTE: chute de frente com a perna de trás
    "chute1": dict(lean=-8, turn=0.2, x=2, na=(40, 100), fa=(80, 80), nl=(10, -8, 10), fl=(70, -120, 20)),
    "chute2": dict(lean=-30, turn=0.1, x=4, na=(30, 110), fa=(-20, 90), nl=(0, -6, 10), fl=(96, -2, 150), lstretch=1.12,
                   head=8),
    "chute3": dict(lean=-6, turn=0.2, x=2, na=(35, 108), fa=(70, 90), nl=(14, -16, 10), fl=(40, -90, 30)),
    # FORTE: a arma de perto, de cima para baixo com o braço da frente
    "forte1": dict(lean=-8, turn=0.35, na=(175, -40), fa=(40, 100), nl=(24, -30, 0), fl=(-28, -10, 30), head=-4),
    "forte2": dict(lean=24, turn=0.7, x=8, na=(100, -10), nstretch=1.12, fa=(-20, 80), nl=(40, -44, 0), fl=(-34, 0, 70)),
    "forte3": dict(lean=14, turn=0.5, x=5, na=(40, -10), fa=(20, 90), nl=(32, -38, 0), fl=(-30, -6, 50)),
    # agachado
    "soco_baixo": dict(lean=22, turn=0.8, x=4, na=(30, 110), fa=(96, -4), stretch=1.18, nl=(76, -116, 0),
                       fl=(10, -96, 40)),
    "rasteira1": dict(lean=28, turn=0.3, x=2, na=(60, 60), fa=(120, -20), nl=(84, -150, -50), fl=(50, -90, 20)),
    "rasteira2": dict(lean=36, turn=0.1, x=2, na=(110, -10), fa=(140, 0), nl=(86, -150, -50), fl=(88, -2, 160),
                      lstretch=1.12, dy=4),
    "defesa": dict(lean=-4, turn=0.35, na=(150, -128), fa=(130, -112), nl=(22, -30, 0), fl=(-24, -14, 30), head=6),
    "defesa_baixa": dict(lean=10, turn=0.35, na=(140, -126), fa=(120, -108), nl=(72, -112, 0), fl=(14, -96, 30)),
    # no ar
    "voadora": dict(air=True, lean=-24, turn=0.1, na=(40, 100), fa=(-30, 70), nl=(60, -110, 20), fl=(104, -4, 150),
                    lstretch=1.1),
    "soco_aereo": dict(air=True, lean=14, turn=0.8, na=(30, 110), fa=(118, -6), stretch=1.18, nl=(70, -110, 20),
                       fl=(20, -90, 40)),
    # apanhando
    "levou": dict(lean=-24, turn=0.4, na=(-50, 50), fa=(-25, 60), nl=(16, -18, 0), fl=(-24, -6, 20), head=-18,
                  hurt=True),
    "levou2": dict(lean=-36, turn=0.3, x=-4, na=(-70, 40), fa=(-45, 50), nl=(26, -16, 0), fl=(-30, 0, 20), head=-24,
                   hurt=True),
    "levou_baixo": dict(lean=32, turn=0.3, na=(10, 40), fa=(40, 30), nl=(30, -40, 0), fl=(-20, -20, 20), head=22,
                        hurt=True),
    "voando": dict(air=True, lean=-60, turn=0.3, na=(-110, 30), fa=(-80, 40), nl=(70, -40, 20), fl=(40, -30, 40),
                   head=-30, hurt=True),
    "caido": dict(lean=-90, turn=0.2, y=48, plant=False, na=(-70, -10), fa=(-100, 20), nl=(90, -8, 40),
                  fl=(84, -20, 50), head=-36, hurt=True),
    "levantando": dict(lean=20, turn=0.3, na=(50, 40), fa=(70, 30), nl=(80, -150, -50), fl=(0, -86, 40)),
    # fim de round
    "vitoria": dict(lean=-2, turn=0.85, na=(172, -20), fa=(30, 110), nl=(20, -20, 0), fl=(-20, -10, 20), smile=True),
    "vitoria2": dict(lean=-4, turn=0.85, dy=-1, na=(176, -10), fa=(26, 118), nl=(20, -20, 0), fl=(-20, -10, 20),
                     smile=True),
}

# ESPECIAL e SUPER de cada um
SPECIAL_POSES = {
    "aryel": {
        # APOSTA: joga a ficha da roleta para cima e espera
        "aposta1": dict(lean=0, turn=0.6, na=(60, 100), fa=(50, 110), nl=(20, -24, 0), fl=(-22, -10, 30)),
        "aposta2": dict(lean=-6, turn=0.75, na=(165, -20), fa=(40, 110), nl=(18, -20, 0), fl=(-22, -10, 30), head=-10,
                        smile=True),
        # GRAU DE MOTO: sentado na moto, mãos no guidão
        "moto": dict(air=True, lean=14, turn=0.2, na=(70, 10), fa=(76, 6), nl=(86, -92, 20), fl=(80, -96, 30),
                     head=4),
        "moto_grau": dict(air=True, lean=-6, turn=0.2, na=(84, -6), fa=(90, -10), nl=(86, -92, 20), fl=(80, -96, 30),
                          head=-6, smile=True),
    },
    "cauanzera": {
        # MULTIESPORTISTA 1: arremesso de basquete
        "basquete1": dict(lean=-4, turn=0.6, y=4, na=(140, -40), fa=(130, -30), nl=(30, -60, 0), fl=(-10, -50, 30)),
        "basquete2": dict(lean=4, turn=0.7, na=(150, 10), fa=(140, 16), nl=(10, -6, 40), fl=(-6, -4, 60)),
        # MULTIESPORTISTA 2: cortada de vôlei (no ar)
        "volei1": dict(air=True, lean=-16, turn=0.6, na=(178, -30), fa=(120, -10), nl=(40, -80, 30), fl=(0, -60, 40),
                       head=-8),
        "volei2": dict(air=True, lean=18, turn=0.9, na=(110, 0), fa=(40, 60), nl=(30, -60, 30), fl=(-10, -50, 40)),
        # MULTIESPORTISTA 3: 100 metros (arrancada)
        "corrida1": dict(lean=40, turn=0.3, na=(-40, 100), fa=(70, 100), nl=(60, -90, 0), fl=(-40, -20, 50)),
        "corrida2": dict(lean=40, turn=0.3, na=(60, 100), fa=(-40, 100), nl=(-30, -30, 40), fl=(70, -100, 0)),
        "ombrada": dict(lean=26, turn=0.1, x=8, na=(40, 90), fa=(60, 80), nl=(40, -40, 0), fl=(-40, 0, 70)),
        # ENTERRADA: sobe com a bola e enterra na cabeça do outro
        "enterrada1": dict(air=True, lean=-10, turn=0.7, na=(176, -10), fa=(170, -16), nl=(40, -90, 30),
                           fl=(-10, -40, 40)),
        "enterrada2": dict(air=True, lean=20, turn=0.8, na=(120, 20), fa=(110, 26), nl=(30, -70, 30), fl=(0, -50, 40)),
    },
}

# quadros que mudam de um lutador para outro
OVERRIDES = {
    "cauanzera": {
        # alto e de pernas compridas: o chute sobe mais
        "chute2": dict(POSES["chute2"], fl=(104, -2, 150), lean=-34),
        # o cabo de rede desce na diagonal: pega até quem está agachado
        "forte2": dict(POSES["forte2"], na=(80, -8)),
    },
}


# quadro de meio: valores que faltam num dos lados
_DEFAULTS = dict(lean=0, turn=0.25, x=0, dy=0, head=0, hair=0, stretch=1.0, nstretch=1.0, lstretch=1.0)
QUARTERS = 4


def blend(a, b, t):
    """Quadro entre a e b (t de 0 a 1): os ângulos andam juntos, o resto troca na metade."""
    out = {}
    for k in set(a) | set(b):
        va, vb = a.get(k, _DEFAULTS.get(k)), b.get(k, _DEFAULTS.get(k))
        if isinstance(va, tuple) and isinstance(vb, tuple) and len(va) == len(vb):
            out[k] = tuple(x + (y - x) * t for x, y in zip(va, vb))
        elif isinstance(va, (int, float)) and isinstance(vb, (int, float)) and not isinstance(va, bool) \
                and not isinstance(vb, bool):
            out[k] = va + (vb - va) * t
        else:
            pick = vb if t >= 0.5 else va
            if pick is not None:
                out[k] = pick
    return out


def blendable(char, a, b):
    """Dá para fazer quadro de meio entre os dois (os dois no chão ou os dois no ar, sem o deitado)."""
    if a == b:
        return False
    try:
        fa, fb = pose(char, a), pose(char, b)
    except KeyError:
        return False
    if bool(fa.get("air")) != bool(fb.get("air")):
        return False
    return fa.get("plant", True) is not False and fb.get("plant", True) is not False


def mid(a, b, q):
    """Nome do quadro de meio: q quartos do caminho de a até b."""
    return f"{a}~{b}~{q}"


def pose(char, name):
    if "~" in name:
        a, b, q = name.split("~")
        return blend(pose(char, a), pose(char, b), int(q) / QUARTERS)
    over = OVERRIDES.get(char, {})
    if name in over:
        return over[name]
    if name in POSES:
        return POSES[name]
    return SPECIAL_POSES[char][name]


def names(char):
    return list(POSES) + list(SPECIAL_POSES.get(char, {}))
