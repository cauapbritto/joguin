"""Sprites desenhados dos lutadores da LUTA (recortados das folhas em assets/luta, veja
tools/recortar_luta.py: cada quadro vira assets/luta/<lutador>/rLcC.png, linha L e coluna C da folha).

As regras continuam usando o esqueleto (luta_rig/luta_poses) para as caixas de golpe; aqui é só a
imagem que aparece. Cada pose do esqueleto aponta para um ou mais quadros da folha:

- um quadro só: fica parado enquanto durar a pose;
- "loop": os quadros giram com o tempo (a guarda respirando);
- "once": os quadros andam uma vez e param no último (o levantar);
- "walk": os quadros seguem o passo do andar.
"""
from dataclasses import dataclass

import pygame

from . import config

DIR = config.ASSETS_DIR / "luta"
SCALE = 2.75                # as folhas são desenhadas pequenas

# pose do esqueleto -> quadro, ou (quadros, jeito, quadros de jogo por desenho)
ANIM = {
    "aryel": {
        "guarda": (("r0c0", "r0c1", "r0c2", "r0c3"), "loop", 9),
        "guarda2": (("r0c2", "r0c3", "r0c0", "r0c1"), "loop", 9),
        "andar1": (("r5c1", "r5c2", "r5c3", "r5c5", "r5c6", "r5c7", "r5c8", "r5c9"), "walk", 2),
        "agachado": "r8c0", "defesa_baixa": "r8c1", "soco_baixo": "r7c9",
        "rasteira1": "r3c5", "rasteira2": "r3c6",
        "pulo": "r2c7", "queda": "r2c8", "voadora": "r2c6", "soco_aereo": "r7c3",
        "soco1": "r1c1", "soco2": "r1c2", "soco3": "r1c3",
        "chute1": "r2c5", "chute2": "r2c0", "chute3": "r2c3",
        "forte1": "r6c2", "forte2": "r0c9", "forte3": "r0c9",
        "defesa": "r6c0",
        "levou": "r6c1", "levou2": "r6c2", "levou_baixo": "r8c3",
        "voando": "r4c4", "caido": "r4c0",
        "levantando": (("r4c5", "r4c6", "r4c7", "r4c8", "r4c9", "r3c0"), "once", 5),
        "vitoria": "r0c9", "vitoria2": "r0c9",
        "aposta1": "r1c8", "aposta2": "r0c9",
        "moto": "r6c4", "moto_grau": "r6c3",
    },
    "cauanzera": {
        "guarda": (("r0c0", "r0c1", "r0c2", "r0c3"), "loop", 9),
        "guarda2": (("r0c2", "r0c3", "r0c0", "r0c1"), "loop", 9),
        "andar1": (("r0c4", "r0c5", "r0c6", "r0c7", "r0c8", "r0c9"), "walk", 1.5),
        "agachado": "r2c8", "defesa_baixa": "r2c9", "soco_baixo": "r5c5",
        "rasteira1": "r5c4", "rasteira2": "r2c3",
        "pulo": "r3c2", "queda": "r3c3", "voadora": "r2c2", "soco_aereo": "r3c1",
        "soco1": "r1c6", "soco2": "r1c0", "soco3": "r1c7",
        "chute1": "r2c0", "chute2": "r2c1", "chute3": "r3c5",
        "forte1": "r4c4", "forte2": "r4c6", "forte3": "r4c6",
        "defesa": "r4c2",
        "levou": "r5c8", "levou2": "r5c9", "levou_baixo": "r6c4",
        "voando": "r6c7", "caido": "r6c9",
        "levantando": (("r6c8", "r6c6", "r6c5", "r6c3", "r6c2"), "once", 6),
        "vitoria": "r4c1", "vitoria2": "r4c1",
        "basquete1": "r4c3", "basquete2": "r3c1",
        "volei1": "r3c2", "volei2": "r1c4",
        "corrida1": "r5c5", "corrida2": "r5c0",
        "ombrada": "r3c8",
        "enterrada1": "r3c3", "enterrada2": "r3c2",
    },
}
WALK = ("andar1", "andar2", "andar3", "andar4")


@dataclass
class Frame:
    right: pygame.Surface
    left: pygame.Surface
    ax: float                   # onde fica o centro do corpo (x) na imagem virada para a direita
    bottom: int                 # linha dos pés, de cima para baixo
    hand: tuple = (0, 0)        # ponta da mão da frente (x, y) na imagem virada para a direita
    top: int = 0                # alto da cabeça

    def place(self, x, ground, facing):
        """(imagem, canto de cima à esquerda) para o lutador com o corpo em x e os pés em ground."""
        img = self.right if facing > 0 else self.left
        ax = self.ax if facing > 0 else img.get_width() - self.ax
        return img, (round(x - ax), round(ground - self.bottom))

    def hand_at(self, x, ground, facing):
        """Onde fica a mão da frente na tela."""
        return x + (self.hand[0] - self.ax) * facing, ground - self.bottom + self.hand[1]

    def top_at(self, ground):
        return ground - self.bottom + self.top


_RAW = {}
_FRAMES = {}


def available(key):
    return (DIR / key / "r0c0.png").exists()


def _raw(key, cell):
    ck = (key, cell)
    if ck not in _RAW:
        img = pygame.image.load(str(DIR / key / f"{cell}.png"))
        try:
            img = img.convert_alpha()
        except pygame.error:            # sem tela ainda (testes)
            pass
        _RAW[ck] = img
    return _RAW[ck]


def _anchor(img):
    """Centro do corpo: média dos pixels da metade de cima (cabeça e tronco), que não mexe tanto
    quanto braços e pernas; e a linha mais baixa com desenho (os pés)."""
    mask = pygame.mask.from_surface(img)
    rects = mask.get_bounding_rects()
    if not rects:
        return img.get_width() / 2, img.get_height()
    box = rects[0].unionall(rects[1:])
    total = xs = 0
    for y in range(box.y, box.y + box.h // 2, 2):
        for x in range(box.x, box.right, 2):
            if mask.get_at((x, y)):
                total += 1
                xs += x
    return (xs / total if total else box.centerx), box.bottom


def _reach(img):
    """Mão da frente: o ponto mais à direita da metade de cima do desenho; e o alto da cabeça."""
    mask = pygame.mask.from_surface(img)
    rects = mask.get_bounding_rects()
    if not rects:
        return (img.get_width(), img.get_height() / 2), 0
    box = rects[0].unionall(rects[1:])
    best = None
    for y in range(box.y, box.y + round(box.h * 0.6)):
        for x in range(box.right - 1, box.x - 1, -1):
            if mask.get_at((x, y)):
                if best is None or x > best[0]:
                    best = (x, y)
                break
    return best or (box.right, box.centery), box.y


def cells(key, view):
    """(quadros, jeito, quadros de jogo por desenho) da pose; quadros de meio "a~b~q" usam a pose
    mais perto."""
    if "~" in view:
        a, b, q = view.split("~")
        view = b if int(q) >= 2 else a
    table = ANIM.get(key, {})
    entry = table.get(view)
    if entry is None and view in WALK:
        entry = table.get("andar1")
    if entry is None:
        entry = table.get("guarda", "r0c0")
    if isinstance(entry, str):
        return (entry,), "once", 1
    return entry


def pick(key, view, t=0, phase=0.0):
    """Qual quadro da folha aparece agora."""
    seq, how, speed = cells(key, view)
    if len(seq) == 1:
        return seq[0]
    if how == "walk":
        return seq[int(phase * speed) % len(seq)]
    i = int(t // speed)
    return seq[i % len(seq)] if how == "loop" else seq[min(i, len(seq) - 1)]


def frame(key, view, t=0, phase=0.0, scale=SCALE):
    """Quadro desenhado para a pose do lutador (t = quadros na pose; phase = passo do andar)."""
    cell = pick(key, view, t, phase)
    ck = (key, cell, scale)
    fr = _FRAMES.get(ck)
    if fr is None:
        img = _raw(key, cell)
        img = pygame.transform.scale(img, (round(img.get_width() * scale), round(img.get_height() * scale)))
        ax, bottom = _anchor(img)
        hand, top = _reach(img)
        fr = Frame(img, pygame.transform.flip(img, True, False), ax, bottom, hand, top)
        _FRAMES[ck] = fr
    return fr


def frame_of(f, scale=SCALE):
    """Quadro do lutador f (da luta) agora."""
    return frame(f.key, f.view, getattr(f, "t", 0), getattr(f, "walk_phase", 0.0), scale)


_OBJ = {}


def has_objects():
    return (DIR / "objetos" / "moto.png").exists()


def obj(name, width, angle=0, flip=False):
    """Objeto da folha de objetos (armas, moto, bolas) com width px de largura, virado (flip) e
    girado (angle em graus, de 10 em 10 para o cache não crescer)."""
    angle = round(angle / 10) * 10 % 360
    ck = (name, round(width), angle, flip)
    img = _OBJ.get(ck)
    if img is None:
        img = _raw("objetos", name)
        w = max(2, round(width))
        h = max(2, round(img.get_height() * w / img.get_width()))
        img = pygame.transform.smoothscale(img, (w, h)) if w < img.get_width() else pygame.transform.scale(img, (w, h))
        if flip:
            img = pygame.transform.flip(img, True, False)
        if angle:
            img = pygame.transform.rotate(img, angle)
        if len(_OBJ) > 400:
            _OBJ.clear()
        _OBJ[ck] = img
    return img


def head(key, size):
    """Rosto para o HUD: o alto do primeiro quadro de guarda."""
    img = _raw(key, "r0c0")
    rect = pygame.mask.from_surface(img).get_bounding_rects()[0]
    side = round(rect.w * 0.66)
    ax, _ = _anchor(img)
    box = pygame.Rect(round(ax - side * 0.5), rect.y - 1, side, side).clip(img.get_rect())
    return pygame.transform.scale(img.subsurface(box).copy(), (size, size))
