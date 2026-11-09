"""Skins da loja de CACOS: a roupa nova de um herói e o efeito que anda com ela.

A folha de cada skin sai de tools/gerar_skins.py (assets/characters/skins/<skin>.png). Aqui ficam o
nome, o preço (ou o cupom que dá a skin), o herói e o efeito desenhado em volta dele no jogo.
Skin é só enfeite: não muda dano, vida, energia nem arma. No futebol e no basquete vale o uniforme
do time (para os times não se confundirem).
"""
import math
from dataclasses import dataclass

import pygame

from . import cacos


@dataclass(frozen=True)
class Skin:
    key: str
    hero: str
    name: str
    price: int                 # 0 = só sai por cupom
    rarity: str                # "rara" (cupom) ou "loja"
    blurb: str
    color: tuple


SKINS = {s.key: s for s in (
    Skin("albeguinio_hacker", "albeguinio", "ALBEGUINIO HACKER SUPREMO", 0, "rara",
         "MOLETOM DE CÓDIGO VERDE, VISOR DE TELA E BITS CAINDO", (60, 230, 120)),
    Skin("cauanzera_cristal", "cauanzera", "CAUANZERA REI DO CRISTAL", 0, "rara",
         "CAPA, COROA DE CRISTAL E CACOS GIRANDO EM VOLTA", (120, 200, 255)),
    Skin("aryel_fogo", "aryel", "ARYEL ALMA DE FOGO", 0, "rara",
         "CABELO EM CHAMA, VEIOS DE LAVA E BRASAS SUBINDO", (255, 150, 50)),
    Skin("borba_ouro", "borba", "BORBA JR EXECUTIVO DE OURO", 0, "rara",
         "TERNO DOURADO, GRAVATA E MOEDAS BRILHANDO", (240, 200, 80)),
    Skin("fantasma_lencol", "fantasma", "FANTASMA LENÇOL DA VÓ", 300, "loja",
         "LENÇOL DE FLORZINHA COM BARRINHA DE CROCHÊ", (236, 110, 150)),
    Skin("atirador_cangaceiro", "atirador", "ATIRADOR CANGACEIRO", 300, "loja",
         "CHAPÉU DE COURO COM ESTRELA E CARTUCHEIRAS", (210, 160, 96)),
    Skin("tanque_obsidiana", "tanque", "TANQUE CAVALEIRO DE OBSIDIANA", 300, "loja",
         "ARMADURA PRETA, CHIFRES E VISOR VERMELHO", (170, 90, 255)),
    Skin("tita_momo", "tita", "TITÃ REI MOMO", 300, "loja",
         "COROA DE PENAS, LANTEJOULA E CONFETE", (250, 200, 50)),
)}


CACO_COLOR = (120, 200, 255)


def draw_caco(surf, x, y, ticks=0, size=6):
    """O ícone do caco: um caquinho de cristal azul com brilho (centro em x, y)."""
    s = size
    pygame.draw.polygon(surf, (44, 92, 186), [(x, y - s - 1), (x + s * 0.7, y), (x, y + s + 1), (x - s * 0.7, y)])
    pygame.draw.polygon(surf, (90, 170, 240), [(x, y - s), (x, y + s), (x - s * 0.6, y)])
    pygame.draw.polygon(surf, (180, 230, 255), [(x - 1, y - s + 2), (x - s * 0.5, y - 1), (x - 1, y - 1)])
    if ticks % 60 < 6:
        surf.fill((240, 252, 255), (round(x) - 2, round(y - s) - 2, 1, 3))
        surf.fill((240, 252, 255), (round(x) - 3, round(y - s) - 1, 3, 1))


def for_hero(hero):
    return [s for s in SKINS.values() if s.hero == hero]


def worn_skin(hero):
    """A skin vestida no herói (Skin) ou None."""
    key = cacos.worn(hero)
    return SKINS.get(key)


def dress(fighter, assets):
    """Veste no lutador a skin escolhida para o herói dele (se tiver e a folha existir)."""
    skin = worn_skin(fighter.stats.key)
    if skin is None:
        return False
    sprites = assets.skin_sprites(skin.key)
    if sprites is None:
        return False
    fighter.sprites = sprites
    fighter.skin = skin.key
    return True


# ─────────────────────────────────────────────
#  Efeitos em volta do herói (desenhados atrás dele)
# ─────────────────────────────────────────────
def _rnd(i, salt):
    """Número de 0 a 1 sempre igual para (i, salt): as partículas não pulam de lugar."""
    return (math.sin(i * 12.9898 + salt * 78.233) * 43758.5453) % 1


CODE, CODE_L = (60, 230, 120), (190, 255, 210)


def _bits(surf, rect, t):
    for i in range(7):
        x = rect.left - 10 + _rnd(i, 1) * (rect.width + 20)
        y = rect.top + ((_rnd(i, 2) * rect.height + t * 0.8) % (rect.height + 10)) - 6
        color = CODE if i % 3 else CODE_L
        if (i + t // 20) % 2:
            surf.fill(color, (round(x), round(y), 2, 5))                   # 1
        else:
            pygame.draw.rect(surf, color, (round(x), round(y), 4, 5), 1)  # 0


def _cristais(surf, rect, t):
    cx, cy = rect.centerx, rect.bottom - rect.height * 0.45
    for i in range(5):
        a = t * 0.04 + i * (2 * math.pi / 5)
        x, y = cx + math.cos(a) * (rect.width * 0.62), cy + math.sin(a) * 9
        if math.sin(a) > 0:
            continue                                                       # os da frente: desenhados depois
        _shard(surf, x, y, (44, 92, 186))


def _cristais_front(surf, rect, t):
    cx, cy = rect.centerx, rect.bottom - rect.height * 0.45
    for i in range(5):
        a = t * 0.04 + i * (2 * math.pi / 5)
        if math.sin(a) <= 0:
            continue
        _shard(surf, cx + math.cos(a) * (rect.width * 0.62), cy + math.sin(a) * 9, (180, 230, 255))


def _shard(surf, x, y, color):
    pygame.draw.polygon(surf, color, [(x, y - 5), (x + 3, y), (x, y + 5), (x - 3, y)])
    surf.set_at((round(x), round(y - 3)), (240, 252, 255))


EMBER = ((255, 236, 150), (255, 170, 50), (232, 90, 30))


def _brasas(surf, rect, t):
    for i in range(9):
        life = (t * 0.9 + _rnd(i, 3) * 60) % 60
        x = rect.left + 6 + _rnd(i, 4) * (rect.width - 12) + math.sin((t + i * 9) * 0.1) * 3
        y = rect.bottom - 10 - life * 1.1
        size = 2 if life < 30 else 1
        surf.fill(EMBER[i % 3], (round(x), round(y), size, size))


GOLD, GOLD_L = (222, 176, 66), (255, 230, 140)


def _moedas(surf, rect, t):
    for i in range(4):
        life = (t * 0.6 + _rnd(i, 5) * 80) % 80
        x = rect.left - 6 + _rnd(i, 6) * (rect.width + 12)
        y = rect.bottom - 14 - life * 0.7
        w = max(1, round(abs(math.cos(t * 0.12 + i)) * 3))
        pygame.draw.ellipse(surf, GOLD, (round(x) - w, round(y) - 3, w * 2 + 1, 7))
        surf.set_at((round(x), round(y) - 2), GOLD_L)
    if t % 40 < 8:
        x, y = rect.left + _rnd(t // 40, 7) * rect.width, rect.top + 10 + _rnd(t // 40, 8) * rect.height * 0.5
        surf.fill(GOLD_L, (round(x) - 2, round(y), 5, 1))
        surf.fill(GOLD_L, (round(x), round(y) - 2, 1, 5))


def _poeira(surf, rect, t):
    for i in range(5):
        x = rect.left - 8 + ((_rnd(i, 9) * (rect.width + 16) + t * 0.5) % (rect.width + 16))
        surf.fill((196, 160, 110), (round(x), rect.bottom - 3 - (i % 3), 2, 1))


def _obsidiana(surf, rect, t):
    for i in range(6):
        life = (t * 0.7 + _rnd(i, 10) * 50) % 50
        x = rect.centerx + math.cos(i * 1.1 + t * 0.03) * (rect.width * 0.45)
        y = rect.bottom - 6 - life * 0.9
        surf.fill((150, 70, 220) if life < 25 else (100, 50, 160), (round(x), round(y), 2, 2))


PENAS = ((236, 60, 90), (250, 200, 50), (60, 200, 120), (60, 150, 240), (200, 80, 220))


def _confete(surf, rect, t):
    for i in range(10):
        life = (t * 0.8 + _rnd(i, 11) * 70) % 70
        x = rect.left - 10 + _rnd(i, 12) * (rect.width + 20) + math.sin(t * 0.08 + i) * 3
        y = rect.top - 10 + life
        surf.fill(PENAS[i % 5], (round(x), round(y), 2 if i % 2 else 1, 1 if i % 2 else 2))


def _florzinha(surf, rect, t):
    if t % 90 < 30:                                                        # um "uuu" de vez em quando
        x, y = rect.right + 2, rect.top + 6 - (t % 90) * 0.3
        for k in range(3):
            surf.fill((220, 220, 236), (round(x + k * 4), round(y + math.sin(t * 0.3 + k) * 1.5), 2, 2))


BACK = {"albeguinio_hacker": _bits, "cauanzera_cristal": _cristais, "aryel_fogo": _brasas,
        "borba_ouro": _moedas, "atirador_cangaceiro": _poeira, "tanque_obsidiana": _obsidiana,
        "tita_momo": _confete, "fantasma_lencol": _florzinha}
FRONT = {"cauanzera_cristal": _cristais_front}


def draw_back(surf, skin, rect, ticks):
    fn = BACK.get(skin)
    if fn is not None:
        fn(surf, rect, ticks)


def draw_front(surf, skin, rect, ticks):
    fn = FRONT.get(skin)
    if fn is not None:
        fn(surf, rect, ticks)
