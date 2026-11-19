"""Sprites desenhados dos lutadores da LUTA (recortados da folha em assets/luta, veja
tools/recortar_luta.py).

As regras continuam usando o esqueleto (luta_rig/luta_poses) para as caixas de golpe; aqui é só a
imagem que aparece. Cada pose do esqueleto aponta para um desenho da folha. Poses que a folha não
tem saem de um desenho com um ajuste: "baixo" achata (agachado), "tomba" inclina para trás (apanhou)
e "pula" sobe um pouco (o passo do andar).
"""
from dataclasses import dataclass

import pygame

from . import config

DIR = config.ASSETS_DIR / "luta"
SCALE = 1.25                # a folha é desenhada menor que a tela da luta

# pose do esqueleto -> (desenho, ajuste)
COMMON = {
    "guarda": ("guarda", None), "guarda2": ("guarda", "respira"),
    "andar1": ("guarda", None), "andar2": ("guarda", "pula"), "andar3": ("guarda", None), "andar4": ("guarda", "pula"),
    "agachado": ("guarda", "baixo"),
    "pulo": ("pulo", None), "queda": ("pulo", None),
    "soco1": ("guarda", None), "soco2": ("soco", None), "soco3": ("soco", None),
    "chute1": ("guarda", "baixo"), "chute2": ("chute", None), "chute3": ("chute", None),
    "forte1": ("defesa", None), "forte2": ("forte", None), "forte3": ("forte", None),
    "soco_baixo": ("soco", "baixo"),
    "rasteira1": ("chute", None), "rasteira2": ("chute", None),
    "defesa": ("defesa", None), "defesa_baixa": ("defesa", "baixo"),
    "voadora": ("pulo", None), "soco_aereo": ("pulo", None),
    "levou": ("guarda", "tomba"), "levou2": ("guarda", "tomba2"), "levou_baixo": ("guarda", "baixo_tomba"),
    "voando": ("caido", None), "caido": ("caido", None), "levantando": ("caido", None),
    "vitoria": ("vitoria", None), "vitoria2": ("vitoria", "respira"),
}
PER_CHAR = {
    "aryel": {
        "levantando": ("tonto", None),
        "aposta1": ("defesa", None), "aposta2": ("vitoria", None),
        "moto": ("corrida", None), "moto_grau": ("corrida", "empina"),
    },
    "cauanzera": {
        "soco_baixo": ("soco_baixo", "baixo"),
        "rasteira1": ("chute", None), "rasteira2": ("chute", None),
        "voando": ("tonto", None), "caido": ("tonto", None), "levantando": ("caido", None),
        "vitoria": ("forte", None), "vitoria2": ("forte", "respira"),
        "basquete1": ("forte", None), "basquete2": ("especial", None),
        "volei1": ("pulo", None), "volei2": ("forte", None),
        "corrida1": ("soco_baixo", None), "corrida2": ("soco_baixo", "pula"),
        "ombrada": ("especial", None),
        "enterrada1": ("forte", None), "enterrada2": ("pulo", None),
    },
}


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
    return (DIR / key / "guarda.png").exists()


def _raw(key, name):
    ck = (key, name)
    if ck not in _RAW:
        img = pygame.image.load(str(DIR / key / f"{name}.png"))
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
    rect = mask.get_bounding_rects()
    if not rect:
        return img.get_width() / 2, img.get_height()
    box = rect[0].unionall(rect[1:]) if len(rect) > 1 else rect[0]
    top = box.y
    half = box.y + box.h // 2
    total = xs = 0
    for y in range(top, half, 2):
        for x in range(box.x, box.right, 2):
            if mask.get_at((x, y)):
                total += 1
                xs += x
    ax = xs / total if total else box.centerx
    return ax, box.bottom


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


def _adjust(img, how):
    if how in ("baixo", "baixo_tomba"):
        img = pygame.transform.scale(img, (img.get_width(), round(img.get_height() * 0.74)))
    if how in ("tomba", "baixo_tomba"):
        img = pygame.transform.rotate(img, 9)
    elif how == "tomba2":
        img = pygame.transform.rotate(img, 16)
    elif how == "empina":
        img = pygame.transform.rotate(img, 12)
    return img


def frame(key, view, scale=SCALE):
    """Quadro desenhado para a pose (ou quadro de meio "a~b~q") do lutador."""
    if "~" in view:
        a, b, q = view.split("~")
        view = b if int(q) >= 2 else a
    name, how = PER_CHAR.get(key, {}).get(view) or COMMON.get(view) or ("guarda", None)
    ck = (key, name, how, scale)
    fr = _FRAMES.get(ck)
    if fr is None:
        img = _raw(key, name)
        img = pygame.transform.scale(img, (round(img.get_width() * scale), round(img.get_height() * scale)))
        img = _adjust(img, how)
        ax, bottom = _anchor(img)
        lift = {"pula": 3, "respira": 1}.get(how, 0) * scale
        hand, top = _reach(img)
        fr = Frame(img, pygame.transform.flip(img, True, False), ax, bottom + lift, hand, top)
        _FRAMES[ck] = fr
    return fr


def head(key, size):
    """Rosto para o HUD: o alto do desenho de guarda."""
    img = _raw(key, "guarda")
    w, h = img.get_size()
    rect = pygame.mask.from_surface(img).get_bounding_rects()[0]
    side = round(rect.w * 0.62)
    ax, _ = _anchor(img)
    box = pygame.Rect(round(ax - side * 0.42), rect.y - 2, side, side).clip(img.get_rect())
    return pygame.transform.smoothscale(img.subsurface(box).copy(), (size, size))
