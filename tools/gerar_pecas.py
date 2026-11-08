"""Gera as peças do cenário das fases desenhadas como os heróis: vendedores e ferreiros de cada
capítulo, as bancas (parte de trás e da frente), o baú, o armário de armas e a fogueira.

Uso:  python tools/gerar_pecas.py

Tudo sai em assets/pecas/ já no dobro de detalhe (arte base + Scale2x + volume + contorno fino,
o mesmo caminho dos heróis), no tamanho em que aparece na tela: o jogo não amplia.

  npc_<nome>_<pose><n>.png    vendedor/ferreiro de frente (parado 0-1, ataque 0-1), recortado
                              com a mesma caixa em todos os quadros (pés no meio de baixo)
  banca_<tipo>_<cap>_tras.png / _frente.png   a banca em duas camadas: o NPC fica no meio
  bau_<cap>_fechado.png / _aberto.png
  armario_<cap>.png           o móvel vazio (as armas da campanha são desenhadas por cima no jogo)
  fogueira_<cap>.png          a base (o fogo ou o vapor é desenhado no jogo, mexendo)
  carro_city.png, carro_uno.png, moto.png   os carros da turma de lado (os _vidro: vidro translúcido)
  estrada_*.png               casinhas, árvores e poste da beira da estrada na viagem
  garagem_*.png               painel de ferramentas, estante, troféus, carrinho, pneus e tambor
  mascote_<bicho>_<pose>.png  gato, cachorro e papagaio (sentado; andando/voando virado para a direita)
"""
import math
import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pygame  # noqa: E402

import gerar_sprites as G  # noqa: E402
from gerar_sprites import (EYE, WHITE, Canvas, Pose, arms, eyes, far_arm, hd_frame, head, legs,  # noqa: E402
                           shade, torso)
from pixel_hd import fine_outline, scale2x, volume  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "assets" / "pecas"
sh = shade
CHAPTERS = (1, 2, 3, 4)


def hd(base, keep=()):
    return fine_outline(volume(scale2x(base), G.shade, keep))


class B:
    """Desenho base em pixels grandes (vira o dobro de detalhe em ``hd``)."""

    def __init__(self, w, h):
        self.s = pygame.Surface((w, h), pygame.SRCALPHA)

    def r(self, x, y, w, h, c):
        if w > 0 and h > 0:
            self.s.fill(c, (x, y, w, h))

    def p(self, x, y, c):
        if 0 <= x < self.s.get_width() and 0 <= y < self.s.get_height():
            self.s.set_at((x, y), c)

    def poly(self, pts, c):
        pygame.draw.polygon(self.s, c, pts)

    def circ(self, c, r, col):
        pygame.draw.circle(self.s, col, c, r)

    def line(self, a, b, c, w=1):
        pygame.draw.line(self.s, c, a, b, w)


# ═════════════════════════════════════════════
#  Vendedores e ferreiros
# ═════════════════════════════════════════════
SKIN = (236, 190, 156)


def mascate(p):
    """Cap. 1, loja: mascate de chapéu de aba larga, bigode, lenço no pescoço e colete verde."""
    c = Canvas()
    skin = (214, 160, 118)
    vest, shirt, pants, boots = (70, 120, 80), (232, 222, 196), (90, 70, 54), (60, 40, 30)
    hat, scarf, mus = (120, 84, 50), (200, 60, 60), (70, 44, 30)
    x, y, w, h = p.torso
    hx, hy, hw, hh = p.head
    legs(c, p, pants, boots)
    far_arm(c, p, shirt, skin)
    torso(c, p, vest, belt=(70, 44, 28), buckle=(220, 190, 90))
    if p.dir == "frente":
        c.rect(x + 3, y, w - 6, h, shirt)
        c.px(x + 4, y + 3, (200, 170, 90))
        c.px(x + 4, y + 5, (200, 170, 90))
        c.rect(x + 2, y, w - 4, 2, scarf)
        c.px(x + w // 2, y + 2, scarf)
    arms(c, p, shirt, skin, cuff=vest)
    head(c, p, skin)
    if p.dir != "costas":
        eyes(c, p)
        if p.dir == "frente":
            c.rect(hx + 2, hy + 7, hw - 4, 2, mus)
            c.px(hx + 1, hy + 8, mus)
            c.px(hx + hw - 2, hy + 8, mus)
            c.rect(hx + 4, hy + 9, 2, 1, (150, 70, 60))
    c.rect(hx - 3, hy + 1, hw + 6, 2, hat)
    c.rect(hx - 3, hy + 1, hw + 6, 1, shade(hat, 30))
    c.rect(hx + 1, hy - 3, hw - 2, 4, hat)
    c.rect(hx + 1, hy, hw - 2, 1, (60, 40, 26))
    return c


def _hammer(c, p, raised):
    if c.hand is None:
        return
    hx, hy = round(c.hand[0]), round(c.hand[1])
    wood, iron, iron_l = (120, 76, 40), (84, 86, 100), (170, 174, 190)
    if raised:
        c.rect(hx, hy - 6, 1, 6, wood)
        c.rect(hx - 2, hy - 9, 5, 3, iron)
        c.rect(hx - 2, hy - 9, 5, 1, iron_l)
    else:
        c.rect(hx, hy, 1, 5, wood)
        c.rect(hx - 2, hy + 5, 5, 3, iron)
        c.rect(hx - 2, hy + 5, 5, 1, iron_l)
        if p.kind == "ataque":
            for dx, dy in ((-4, 4), (4, 3), (-3, 8), (5, 7), (0, 9)):
                c.px(hx + dx, hy + dy, (255, 214, 90))


def ferreiro(p):
    """Cap. 1, ferreiro: ruivo de barba cheia, careca em cima, avental de couro, camisa cinza de
    manga arregaçada, braços grossos e martelo."""
    c = Canvas()
    beard, beard_d, beard_l = (178, 66, 30), (120, 40, 22), (222, 112, 52)
    shirt, apron, apron_d = (118, 116, 128), (124, 78, 44), (92, 56, 32)
    pants, boots = (64, 52, 48), (46, 34, 30)
    x, y, w, h = p.torso
    hx, hy, hw, hh = p.head
    legs(c, p, pants, boots, wide=True)
    far_arm(c, p, shirt, SKIN, thick=3)
    torso(c, p, shirt, belt=(70, 44, 28), buckle=(200, 170, 90))
    if p.dir == "frente":
        c.rect(x + 1, y + 1, w - 2, h + 3, apron)
        c.rect(x + 1, y + 1, w - 2, 1, shade(apron, 24))
        c.rect(x + 2, y + 4, w - 4, 2, apron_d)
        c.px(x + 3, y + 3, (170, 174, 190))
        c.px(x + 3, y + 2, (170, 174, 190))
        c.px(x + 1, y, apron_d)
        c.px(x + w - 2, y, apron_d)
    arms(c, p, shirt, SKIN, thick=3, cuff=shade(SKIN, -20))
    _hammer(c, p, raised=p.kind == "ataque" and p.frame == 0)
    head(c, p, SKIN)
    if p.dir != "costas":
        eyes(c, p)
        c.rect(hx, hy + 3, 1, 3, beard)
        c.rect(hx + hw - 1, hy + 3, 1, 3, beard)
        c.rect(hx + 1, hy + 2, hw - 2, 1, beard_d)
        c.rect(hx + 1, hy + 2, 3, 1, beard)
        c.rect(hx + hw - 4, hy + 2, 3, 1, beard)
        c.rect(hx + 2, hy + 1, 2, 1, shade(SKIN, 40))
        c.rect(hx, hy + 7, hw, 3, beard)
        c.rect(hx + 1, hy + 10, hw - 2, 2, beard)
        c.rect(hx + 3, hy + 12, hw - 6, 1, beard_d)
        c.rect(hx + 2, hy + 7, hw - 4, 1, beard_l)
        c.rect(hx + 4, hy + 8, 2, 1, (110, 34, 28))
        c.px(hx + 2, hy + 9, beard_l)
        c.px(hx + hw - 3, hy + 10, beard_d)
    return c


def soldador(p):
    """Cap. 2, ferreiro: macacão azul com faixa refletiva, máscara de solda (levantada parado,
    abaixada soldando), barba ruiva, luva grossa e maçarico."""
    c = Canvas()
    suit, suit_d, stripe = (52, 86, 150), (34, 56, 104), (236, 200, 60)
    mask, mask_l, lens = (40, 44, 50), (78, 84, 94), (90, 220, 160)
    beard, boots, glove = (196, 92, 40), (40, 36, 40), (150, 110, 70)
    x, y, w, h = p.torso
    hx, hy, hw, hh = p.head
    legs(c, p, suit, boots, wide=True)
    far_arm(c, p, suit, glove, thick=3)
    torso(c, p, suit, belt=suit_d)
    c.rect(x, y + h - 3, w, 1, stripe)
    c.rect(x + w // 2, y, 1, h - 3, suit_d)
    c.rect(x + 1, y + 1, 3, 2, suit_d)
    c.px(x + 2, y + 1, stripe)
    arms(c, p, suit, glove, thick=3, cuff=stripe)
    if c.hand:
        tx, ty = round(c.hand[0]), round(c.hand[1])
        c.rect(tx, ty, 1, 4, (70, 70, 80))
        c.rect(tx - 1, ty + 4, 3, 1, (190, 60, 50))
        if p.kind == "ataque":
            c.px(tx, ty + 5, (180, 230, 255))
            c.px(tx + 1, ty + 6, (230, 250, 255))
    head(c, p, SKIN)
    if p.kind == "ataque":
        c.rect(hx - 1, hy + 1, hw + 2, hh, mask)
        c.rect(hx, hy + 2, hw, 1, mask_l)
        c.rect(hx + 2, hy + 4, hw - 4, 2, lens)
        c.px(hx + 2, hy + 4, (220, 255, 240))
    else:
        eyes(c, p)
        c.rect(hx - 1, hy - 3, hw + 2, 4, mask)
        c.rect(hx, hy - 3, hw, 1, mask_l)
        c.rect(hx + 2, hy - 2, hw - 4, 1, lens)
        c.rect(hx + 1, hy + 7, hw - 2, 3, beard)
        c.rect(hx + 3, hy + 7, hw - 6, 1, shade(beard, 30))
        c.rect(hx + 4, hy + 8, 2, 1, (120, 40, 30))
    return c


def tecnico(p):
    """Cap. 2, loja: técnico de TI da Lag Lobby. Polo cinza com logo roxo, crachá, fone num ouvido,
    óculos e cabelo preto curto."""
    c = Canvas()
    skin = (196, 140, 104)
    polo, pants, shoes, hair = (120, 126, 140), (50, 56, 76), (30, 30, 36), (30, 26, 28)
    x, y, w, h = p.torso
    hx, hy, hw, hh = p.head
    legs(c, p, pants, shoes)
    far_arm(c, p, polo, skin)
    torso(c, p, polo, belt=(40, 40, 46), buckle=(170, 170, 180))
    c.rect(x + 2, y + 1, 2, 2, (150, 90, 210))
    c.rect(x + w - 4, y + 3, 2, 3, (240, 240, 240))
    c.px(x + w - 3, y + 2, (220, 60, 60))
    c.rect(x + w // 2 - 1, y, 2, 2, shade(polo, -24))
    arms(c, p, polo, skin, cuff=shade(polo, -20))
    head(c, p, skin)
    c.rect(hx, hy - 1, hw, 3, hair)
    c.rect(hx, hy + 2, 1, 2, hair)
    c.rect(hx + hw - 1, hy + 2, 1, 2, hair)
    eyes(c, p)
    c.rect(hx + 1, hy + 4, hw - 2, 1, (40, 40, 46))
    c.rect(hx - 1, hy + 4, 2, 3, (40, 40, 46))
    c.px(hx - 1, hy + 3, (150, 90, 210))
    c.rect(hx + 4, hy + 9, 2, 1, (150, 80, 70))
    return c


def atendente(p):
    """Cap. 3, loja: atendente da Clepalovers. Jaleco rosa-claro, coque, brinco e prancheta."""
    c = Canvas()
    skin = (226, 176, 140)
    coat, coat_d, pants, shoes, hair = (250, 214, 228), (226, 160, 190), (240, 236, 240), (232, 120, 170), (92, 52, 34)
    x, y, w, h = p.torso
    hx, hy, hw, hh = p.head
    legs(c, p, pants, shoes)
    far_arm(c, p, coat, skin)
    torso(c, p, coat)
    c.rect(x + w // 2, y, 1, h + 2, coat_d)
    c.rect(x, y + h, w, 2, coat)
    c.rect(x + 1, y + 2, 2, 1, (232, 120, 170))
    arms(c, p, coat, skin, cuff=coat_d)
    if c.hand:
        tx, ty = round(c.hand[0]), round(c.hand[1])
        c.rect(tx - 1, ty - 1, 4, 5, (150, 110, 70))
        c.rect(tx, ty, 2, 3, (250, 250, 250))
    head(c, p, skin)
    c.rect(hx, hy - 1, hw, 3, hair)
    c.rect(hx, hy + 2, 1, 4, hair)
    c.rect(hx + hw - 1, hy + 2, 1, 4, hair)
    c.rect(hx + 3, hy - 4, 4, 3, hair)
    c.px(hx + 4, hy - 4, shade(hair, 30))
    eyes(c, p)
    c.px(hx - 1, hy + 6, (240, 200, 80))
    c.rect(hx + 4, hy + 9, 2, 1, (210, 80, 110))
    return c


def esteticista(p):
    """Cap. 3, ferreiro: técnico dos aparelhos de estética. Macacão lilás, luva azul, óculos de
    proteção na testa e chave de fenda que solta faísca rosa."""
    c = Canvas()
    skin = (170, 116, 84)
    suit, gl, boots, hair = (170, 140, 210), (90, 160, 230), (60, 50, 70), (24, 20, 22)
    x, y, w, h = p.torso
    hx, hy, hw, hh = p.head
    legs(c, p, suit, boots, wide=True)
    far_arm(c, p, suit, gl, thick=3)
    torso(c, p, suit, belt=(90, 80, 110), buckle=(230, 230, 240))
    c.rect(x + 1, y + 2, 3, 2, shade(suit, -30))
    c.px(x + 2, y + 2, (250, 250, 250))
    arms(c, p, suit, gl, thick=3, cuff=shade(suit, -30))
    if c.hand:
        tx, ty = round(c.hand[0]), round(c.hand[1])
        c.rect(tx, ty, 1, 4, (220, 220, 230))
        c.rect(tx - 1, ty - 1, 3, 2, (232, 120, 170))
        if p.kind == "ataque":
            c.px(tx + 1, ty + 5, (255, 150, 220))
            c.px(tx - 1, ty + 6, (255, 220, 250))
    head(c, p, skin)
    c.rect(hx, hy - 1, hw, 3, hair)
    c.rect(hx, hy + 1, hw, 2, (60, 60, 70))
    c.rect(hx + 2, hy + 1, 2, 1, (150, 220, 250))
    c.rect(hx + hw - 4, hy + 1, 2, 1, (150, 220, 250))
    eyes(c, p)
    c.rect(hx + 4, hy + 9, 2, 1, (110, 60, 50))
    return c


def mordomo(p):
    """Cap. 4, loja: mordomo da mansão. Fraque preto, colete cinza, gravata borboleta, luva branca,
    cabelo grisalho penteado, bigode fino e bandeja com cloche."""
    c = Canvas()
    skin = (232, 196, 170)
    coat, vest, pants, shoes, hair = (28, 28, 36), (110, 110, 120), (34, 34, 42), (16, 16, 20), (190, 190, 196)
    glove = (246, 246, 246)
    x, y, w, h = p.torso
    hx, hy, hw, hh = p.head
    legs(c, p, pants, shoes)
    far_arm(c, p, coat, glove)
    torso(c, p, coat)
    c.rect(x + 3, y, w - 6, h - 1, vest)
    c.rect(x + w // 2 - 1, y, 2, h - 1, (250, 250, 250))
    c.rect(x + w // 2 - 2, y, 4, 1, (150, 30, 40))
    c.px(x + w // 2, y + 3, (220, 190, 90))
    c.rect(x - 1, y + h - 1, 2, 4, coat)
    c.rect(x + w - 1, y + h - 1, 2, 4, coat)
    arms(c, p, coat, glove, cuff=(250, 250, 250))
    if c.hand:
        tx, ty = round(c.hand[0]), round(c.hand[1])
        c.rect(tx - 3, ty - 1, 7, 1, (200, 200, 210))
        c.rect(tx - 2, ty - 3, 5, 2, (220, 220, 230))
    head(c, p, skin)
    c.rect(hx, hy - 1, hw, 2, hair)
    c.rect(hx + hw - 3, hy - 1, 3, 3, hair)
    c.rect(hx, hy + 1, 1, 3, hair)
    eyes(c, p)
    c.rect(hx + 3, hy + 8, hw - 6, 1, (120, 120, 126))
    return c


def ourives(p):
    """Cap. 4, ferreiro: ourives. Colete de veludo vinho, camisa branca, lupa de joalheiro num olho,
    cabelo branco e alicate fino."""
    c = Canvas()
    skin = (236, 200, 172)
    vest, shirt, pants, shoes, hair = (110, 30, 48), (244, 240, 232), (50, 44, 40), (30, 22, 18), (236, 236, 240)
    x, y, w, h = p.torso
    hx, hy, hw, hh = p.head
    legs(c, p, pants, shoes)
    far_arm(c, p, shirt, skin)
    torso(c, p, vest, belt=(60, 20, 30), buckle=(230, 190, 80))
    c.rect(x + w // 2 - 1, y, 2, h - 2, shirt)
    c.px(x + 2, y + 2, (230, 190, 80))
    c.rect(x + 2, y + 3, 3, 1, (230, 190, 80))
    arms(c, p, shirt, skin, cuff=shirt)
    if c.hand:
        tx, ty = round(c.hand[0]), round(c.hand[1])
        c.rect(tx, ty, 1, 4, (150, 150, 160))
        c.px(tx + 1, ty + 4, (150, 150, 160))
        if p.kind == "ataque":
            c.px(tx, ty + 5, (250, 220, 120))
            c.px(tx + 2, ty + 6, (255, 250, 200))
    head(c, p, skin)
    c.rect(hx, hy - 1, hw, 2, hair)
    c.rect(hx, hy + 1, 1, 4, hair)
    c.rect(hx + hw - 1, hy + 1, 1, 4, hair)
    eyes(c, p)
    c.rect(hx + hw - 5, hy + 3, 4, 4, (40, 40, 46))
    c.rect(hx + hw - 4, hy + 4, 2, 2, (170, 220, 240))
    c.rect(hx + 3, hy + 8, hw - 6, 1, hair)
    return c


# quem fica em cada banca, por capítulo
NPCS = {
    ("loja", 1): mascate, ("ferreiro", 1): ferreiro,
    ("loja", 2): tecnico, ("ferreiro", 2): soldador,
    ("loja", 3): atendente, ("ferreiro", 3): esteticista,
    ("loja", 4): mordomo, ("ferreiro", 4): ourives,
}
NPC_FRAMES = (("parado", 0), ("parado", 1), ("ataque", 0), ("ataque", 1))


def npc_frames(fn):
    """Os quadros de frente do NPC, todos recortados com a mesma caixa (os pés ficam no meio de
    baixo, então o jogo desenha pelo meio da base sem tremer)."""
    imgs = [hd_frame(fn(Pose("frente", kind, i, True)), [EYE, WHITE]) for kind, i in NPC_FRAMES]
    box = imgs[0].get_bounding_rect()
    for img in imgs[1:]:
        box.union_ip(img.get_bounding_rect())
    w, h = imgs[0].get_size()
    half = max(w // 2 - box.left, box.right - w // 2)        # caixa simétrica: o meio fica no meio
    box = pygame.Rect(w // 2 - half, box.top, 2 * half, h - box.top)
    return [img.subsurface(box).copy() for img in imgs]


# ═════════════════════════════════════════════
#  Bancas (64 x 56 na base): parte de trás, NPC, parte da frente
# ═════════════════════════════════════════════
GLOWS = [(255, 150, 50), (255, 230, 120), (255, 170, 80), (255, 210, 110), (64, 200, 230), (150, 230, 255),
         (255, 150, 220), (250, 240, 200), (230, 190, 80)]


def _counter(b, top, top_l, body, joint, trim=None):
    """Balcão da frente (comum a todas as bancas): tampo, corpo com juntas e cantoneiras."""
    b.r(4, 36, 56, 16, body)
    b.r(3, 34, 58, 3, top)
    b.r(3, 34, 58, 1, top_l)
    for x in range(10, 58, 12):
        b.r(x, 38, 1, 13, joint)
    if trim:
        b.r(4, 36, 3, 3, trim)
        b.r(57, 36, 3, 3, trim)
        b.r(4, 49, 56, 1, trim)


def _awning(b, stripes, post=(92, 60, 36)):
    for x in (2, 58):
        b.r(x, 6, 4, 46, post)
        b.r(x, 6, 1, 46, sh(post, 40))
    for k in range(8):
        b.r(k * 8, 0, 8, 8, stripes[k % 2])
        b.poly([(k * 8, 8), (k * 8 + 8, 8), (k * 8 + 4, 11)], stripes[k % 2])
    b.r(0, 0, 64, 1, sh(stripes[0], 30))


def banca_tras(kind, cap):
    b = B(64, 56)
    if cap == 1 and kind == "ferreiro":
        b.r(4, 10, 56, 30, (70, 48, 34))                         # parede de tábuas
        for y in range(12, 40, 5):
            b.r(4, y, 56, 1, (56, 38, 26))
        for i, x in enumerate(range(8, 56, 8)):                  # ferramentas penduradas
            b.r(x, 13, 1, 9, (120, 80, 44))
            b.r(x - 1, 12 + (i % 2) * 8, 3, 2, (150, 154, 168))
        b.r(4, 24, 12, 16, (140, 70, 50))                        # forja de tijolo
        for y in range(25, 40, 3):
            for x in range(4 + (y % 2) * 2, 16, 4):
                b.r(x, y, 3, 2, (170, 90, 64))
        b.r(7, 28, 6, 5, (40, 20, 16))
        b.r(8, 30, 4, 3, (255, 150, 50))
        b.r(9, 31, 2, 2, (255, 230, 120))
    elif cap == 1:
        b.r(6, 12, 52, 28, (96, 70, 46))                         # prateleira da carroça
        for y in (18, 27, 36):
            b.r(6, y, 52, 2, (130, 96, 60))
        cols = ((210, 60, 60), (110, 170, 255), (160, 230, 120), (240, 200, 90))
        for row, y in enumerate((13, 22, 31)):
            for k, x in enumerate(range(9, 56, 7)):
                c = cols[(row + k) % 4]
                b.r(x, y + 1, 4, 4, c)
                b.r(x + 1, y, 2, 1, (230, 230, 240))
                b.p(x, y + 1, sh(c, 50))
    elif cap == 2 and kind == "loja":
        b.r(34, 10, 26, 26, (36, 40, 52))                        # rack de servidor atrás do técnico
        for y in range(12, 34, 4):
            b.r(36, y, 22, 3, (50, 56, 70))
            for x in range(38, 56, 5):
                b.p(x, y + 1, (170, 90, 230) if (x + y) % 3 else (64, 200, 230))
        b.r(3, 4, 26, 50, (30, 34, 44))                          # máquina de venda
        b.r(4, 5, 24, 48, (210, 216, 226))
        b.r(4, 5, 24, 2, (64, 200, 230))
        b.r(6, 9, 15, 30, (40, 60, 80))                          # vitrine
        for row in range(4):
            for col in range(3):
                c = ((210, 60, 60), (110, 170, 255), (110, 220, 200))[(row + col) % 3]
                b.r(7 + col * 5, 11 + row * 7, 3, 4, c)
                b.r(7, 15 + row * 7, 14, 1, (150, 160, 176))
        b.r(7, 10, 2, 28, (90, 120, 150))                        # reflexo do vidro
        b.r(23, 9, 3, 6, (64, 200, 230))                         # botões
        for y in range(17, 29, 3):
            b.r(23, y, 3, 2, (60, 64, 76))
        b.r(6, 43, 15, 6, (20, 22, 28))                          # onde cai o produto
        b.r(23, 42, 3, 4, (60, 64, 76))
    elif cap == 2:
        b.r(4, 8, 56, 28, (56, 60, 72))                          # painel de furos com ferramentas
        for y in range(10, 36, 4):
            for x in range(6, 60, 4):
                b.p(x, y, (40, 44, 54))
        b.r(4, 8, 56, 2, (90, 96, 110))
        b.r(14, 12, 2, 10, (150, 154, 168))                      # chave inglesa
        b.r(13, 11, 4, 3, (150, 154, 168))
        b.r(22, 12, 1, 9, (220, 60, 50))                         # alicate
        b.r(24, 12, 1, 9, (220, 60, 50))
        b.r(22, 20, 3, 3, (150, 154, 168))
        b.r(44, 12, 10, 6, (40, 44, 50))                         # máscara reserva pendurada
        b.r(46, 14, 6, 2, (90, 220, 160))
        b.r(5, 18, 7, 34, (180, 60, 50))                         # cilindros de gás
        b.r(5, 18, 7, 2, (210, 90, 70))
        b.r(7, 15, 3, 3, (90, 92, 100))
        b.r(53, 22, 6, 30, (60, 120, 200))
        b.r(53, 22, 6, 2, (110, 160, 230))
        b.r(55, 19, 2, 3, (90, 92, 100))
    elif cap == 3 and kind == "loja":
        b.r(4, 8, 56, 28, (238, 206, 220))                       # parede rosa com prateleiras
        b.r(4, 8, 56, 1, (250, 230, 238))
        for y in (16, 26):
            b.r(4, y, 18, 2, (250, 250, 250))
            b.r(42, y, 18, 2, (250, 250, 250))
            for k, x in enumerate(range(6, 21, 4)):
                c = ((232, 120, 170), (250, 250, 250), (180, 150, 220), (130, 210, 220))[k % 4]
                b.r(x, y - 5, 3, 5, c)
                b.r(x + 1, y - 6, 1, 1, (210, 190, 120))
                b.r(x + 38, y - 4, 3, 4, ((180, 150, 220), (232, 120, 170))[k % 2])
        b.circ((32, 18), 9, (210, 190, 120))                     # espelho redondo com lâmpadas
        b.circ((32, 18), 7, (196, 222, 236))
        b.line((28, 14), (31, 11), (250, 250, 255))
        for a in range(8):
            ang = a * math.tau / 8
            b.p(round(32 + math.cos(ang) * 9), round(18 + math.sin(ang) * 9), (250, 240, 200))
    elif cap == 3:
        b.r(3, 4, 18, 40, (236, 236, 242))                       # aparelho de estética
        b.r(3, 4, 18, 2, (250, 250, 255))
        b.r(5, 8, 14, 10, (40, 44, 60))
        b.r(6, 9, 12, 2, (255, 150, 220))
        b.r(6, 12, 8, 1, (130, 210, 220))
        b.r(6, 14, 10, 1, (130, 210, 220))
        b.r(5, 22, 14, 4, (210, 200, 222))
        for x in (6, 10, 14):
            b.r(x, 23, 2, 2, (232, 120, 170))
        b.line((20, 10), (30, 6), (200, 200, 210), 2)            # braço articulado com ponteira
        b.line((30, 6), (36, 14), (200, 200, 210), 2)
        b.r(35, 14, 3, 4, (232, 120, 170))
        b.r(26, 10, 34, 26, (226, 196, 230))                     # painel lilás de ferramentas
        b.r(26, 10, 34, 1, (240, 220, 246))
        for k, x in enumerate(range(42, 58, 5)):
            b.r(x, 13, 1, 9 + (k % 2) * 3, (150, 150, 160))
            b.r(x - 1, 12, 3, 2, (90, 160, 230))
        b.r(3, 44, 18, 8, (200, 196, 210))
        b.r(5, 50, 3, 2, (60, 60, 70))
        b.r(16, 50, 3, 2, (60, 60, 70))
    elif cap == 4 and kind == "loja":
        b.r(4, 6, 56, 30, (84, 38, 28))                          # estante de mogno
        b.r(4, 6, 56, 2, (220, 180, 80))
        for y in (15, 25):
            b.r(4, y, 56, 2, (120, 56, 40))
            b.r(4, y + 2, 56, 1, (60, 26, 20))
        for row, y in enumerate((9, 19, 29)):
            for k, x in enumerate(range(7, 58, 6)):
                if (k + row) % 5 == 2:
                    continue
                c = ((40, 110, 70), (170, 110, 40), (120, 30, 40), (210, 210, 220))[(k + row) % 4]
                b.r(x, y, 3, 6, c)
                b.r(x + 1, y - 1, 1, 1, sh(c, -40))
                b.p(x, y + 1, sh(c, 50))
        b.r(4, 6, 2, 30, (220, 180, 80))
        b.r(58, 6, 2, 30, (220, 180, 80))
    else:
        b.r(4, 6, 56, 30, (220, 180, 80))                        # painel de veludo com moldura de ouro
        b.r(6, 8, 52, 26, (100, 24, 40))
        b.r(10, 12, 44, 10, (30, 26, 34))                        # vitrine de joias
        b.r(10, 12, 44, 1, (150, 160, 180))
        gems = ((90, 200, 120), (220, 60, 80), (80, 140, 240), (250, 250, 255), (180, 90, 220))
        for k, x in enumerate(range(13, 52, 8)):
            b.r(x, 16, 4, 4, gems[k % 5])
            b.p(x, 16, (255, 255, 255))
            b.r(x - 1, 20, 6, 1, (220, 180, 80))
        b.r(14, 26, 36, 2, (220, 180, 80))
        b.r(20, 24, 4, 2, (240, 210, 120))
        b.r(40, 24, 4, 2, (240, 210, 120))
    return hd(b.s, keep=GLOWS)


def banca_frente(kind, cap):
    b = B(64, 56)
    if cap == 1:
        stripes = ((176, 52, 48), (70, 60, 70)) if kind == "ferreiro" else ((70, 150, 96), (228, 220, 196))
        _awning(b, stripes)
        _counter(b, (150, 100, 58), (186, 132, 80), (110, 70, 40), (84, 52, 30), trim=(150, 154, 168))
        if kind == "ferreiro":
            b.r(36, 28, 16, 4, (80, 82, 96))                     # bigorna
            b.r(34, 28, 4, 2, (80, 82, 96))
            b.r(40, 32, 8, 3, (64, 66, 78))
            b.r(36, 28, 16, 1, (150, 154, 170))
            b.r(14, 31, 10, 3, (210, 80, 40))                    # barra em brasa
            b.r(15, 31, 8, 1, (255, 170, 80))
        else:
            b.r(10, 28, 14, 6, (150, 110, 60))                   # cesto de frutas
            for k, c in enumerate(((220, 60, 60), (250, 190, 60), (120, 190, 70))):
                b.circ((13 + k * 4, 28), 2, c)
            b.r(40, 26, 12, 8, (236, 226, 196))                  # caderninho de preços
            b.r(41, 28, 10, 1, (120, 90, 60))
            b.r(41, 30, 7, 1, (120, 90, 60))
            b.r(56, 12, 4, 6, (60, 50, 40))                      # lanterna
            b.r(57, 13, 2, 4, (255, 210, 110))
    elif cap == 2 and kind == "loja":
        b.r(32, 36, 28, 16, (70, 74, 84))                        # balcãozinho de aço do técnico
        b.r(31, 34, 30, 3, (120, 126, 140))
        b.r(31, 34, 30, 1, (170, 176, 190))
        b.r(34, 38, 1, 13, (50, 52, 60))
        b.r(57, 38, 1, 13, (50, 52, 60))
        b.r(38, 27, 14, 7, (40, 40, 46))                         # notebook aberto
        b.r(39, 28, 12, 5, (64, 200, 230))
        b.r(36, 33, 18, 1, (90, 92, 100))
        b.r(54, 30, 4, 4, (240, 240, 240))                       # caneca
        b.r(54, 30, 4, 1, (150, 90, 210))
    elif cap == 2:
        b.r(3, 34, 58, 3, (120, 126, 140))                       # mesa de solda
        b.r(3, 34, 58, 1, (170, 176, 190))
        b.r(4, 37, 56, 4, (70, 74, 84))
        for x in (6, 54):
            b.r(x, 41, 4, 11, (50, 52, 60))
        b.r(4, 46, 56, 2, (50, 52, 60))
        b.r(14, 29, 10, 5, (90, 94, 108))                        # morsa
        b.r(12, 28, 14, 2, (130, 136, 150))
        b.r(36, 30, 16, 4, (150, 156, 170))                      # chapa soldada com o cordão
        for x in range(37, 51, 3):
            b.r(x, 31, 2, 1, (255, 170, 80))
    elif cap == 3 and kind == "loja":
        _counter(b, (250, 248, 250), (255, 255, 255), (244, 236, 242), (226, 206, 220), trim=(232, 120, 170))
        b.r(4, 42, 56, 2, (232, 120, 170))                       # faixa rosa
        b.r(8, 26, 6, 8, (180, 150, 220))                        # vaso com flores
        for k, (fx, fy) in enumerate(((9, 23), (12, 22), (11, 25))):
            b.r(fx, fy, 2, 2, ((255, 150, 220), (250, 240, 200), (232, 120, 170))[k])
        b.r(46, 29, 8, 5, (40, 44, 60))                          # maquininha de cartão
        b.r(47, 30, 6, 2, (130, 210, 220))
    elif cap == 3:
        _counter(b, (220, 220, 230), (246, 246, 250), (200, 196, 210), (170, 166, 184), trim=(90, 160, 230))
        b.r(36, 28, 16, 6, (170, 140, 210))                      # maleta de ferramentas lilás
        b.r(36, 28, 16, 1, (200, 180, 230))
        b.r(42, 26, 4, 2, (90, 80, 110))
        b.r(12, 30, 6, 4, (255, 150, 220))                       # cristal rosa que ele está ajustando
        b.r(13, 28, 4, 2, (255, 220, 250))
    elif cap == 4 and kind == "loja":
        _counter(b, (150, 70, 46), (190, 104, 66), (110, 46, 34), (80, 32, 24), trim=(220, 180, 80))
        b.r(4, 40, 56, 1, (220, 180, 80))
        b.r(10, 22, 2, 12, (220, 180, 80))                       # candelabro
        b.r(7, 26, 8, 1, (220, 180, 80))
        for x in (7, 10, 14):
            b.r(x, 23, 1, 3, (250, 250, 240))
            b.p(x, 22, (250, 240, 200))
        b.r(8, 33, 6, 1, (220, 180, 80))
        b.r(42, 28, 12, 6, (210, 210, 220))                      # cloche de prata
        b.r(44, 26, 8, 2, (230, 230, 240))
        b.r(47, 25, 2, 1, (230, 230, 240))
        b.r(40, 33, 16, 1, (170, 170, 180))
    else:
        _counter(b, (150, 70, 46), (190, 104, 66), (110, 46, 34), (80, 32, 24), trim=(220, 180, 80))
        b.r(48, 20, 2, 14, (60, 60, 66))                         # luminária de joalheiro
        b.r(42, 18, 10, 4, (40, 110, 70))
        b.r(43, 21, 8, 1, (250, 240, 200))
        b.r(46, 33, 6, 1, (60, 60, 66))
        b.r(12, 30, 8, 4, (230, 190, 80))                        # barras de ouro
        b.r(14, 28, 8, 2, (230, 190, 80))
        b.r(26, 31, 4, 3, (250, 250, 255))                       # anel
        b.p(27, 30, (80, 140, 240))
    return hd(b.s, keep=GLOWS)


# onde o NPC fica na banca (pixels de tela a partir do meio)
NPC_DX = {("loja", 2): 32}


# ═════════════════════════════════════════════
#  Sala de recompensas: baú, armário e fogueira de cada capítulo
# ═════════════════════════════════════════════
def bau(cap, aberto):
    b = B(34, 30)
    gold = (236, 196, 80)
    if cap == 1:                                                  # baú de madeira com cintas
        wood, wd, wl, iron = (140, 86, 46), (100, 60, 32), (178, 118, 66), (70, 70, 82)
        b.r(3, 14, 28, 14, wood)
        b.r(3, 14, 28, 1, wl)
        for x in (3, 15, 27):
            b.r(x, 14, 4, 14, iron)
        b.r(3, 26, 28, 2, wd)
        if not aberto:
            b.r(3, 6, 28, 8, wl)
            b.r(5, 4, 24, 3, wl)
            b.r(5, 4, 24, 1, sh(wl, 20))
            for x in (3, 15, 27):
                b.r(x, 5, 4, 9, iron)
            b.r(15, 12, 4, 5, gold)
            b.r(16, 14, 2, 2, (120, 90, 30))
        else:
            b.r(3, 1, 28, 7, wd)
            b.r(5, 0, 24, 2, wd)
            for x in (3, 15, 27):
                b.r(x, 0, 4, 8, iron)
            b.r(4, 9, 26, 5, (170, 30, 40))
            b.r(8, 10, 18, 3, gold)
    elif cap == 2:                                                # cofre de aço da Lag Lobby
        body, light, dark = (92, 100, 116), (150, 160, 178), (46, 50, 60)
        b.r(3, 4, 28, 25, dark)
        b.r(4, 5, 26, 23, body)
        b.r(4, 5, 26, 1, light)
        b.r(5, 26, 4, 3, dark)
        b.r(25, 26, 4, 3, dark)
        if aberto:
            b.r(6, 7, 20, 18, (20, 18, 26))
            b.r(8, 20, 16, 3, gold)
            b.r(26, 5, 7, 23, body)                               # porta aberta para o lado
            b.r(26, 5, 1, 23, light)
            b.circ((30, 16), 2, (200, 206, 216))
        else:
            b.r(6, 7, 22, 18, sh(body, 10))
            b.circ((17, 16), 5, (200, 206, 216))                 # roda do segredo
            b.circ((17, 16), 3, (120, 126, 140))
            b.r(17, 11, 1, 3, (230, 236, 244))
            b.r(25, 8, 2, 2, (64, 200, 230))                     # luz ciano
            b.r(8, 22, 6, 1, (64, 200, 230))
    elif cap == 3:                                                # maleta de beleza rosa
        pink, pd, pl, white = (232, 140, 180), (190, 100, 140), (250, 190, 214), (250, 248, 250)
        b.r(2, 13, 30, 15, pink)
        b.r(2, 13, 30, 1, pl)
        b.r(2, 26, 30, 2, pd)
        b.r(2, 19, 30, 1, white)
        for x in (3, 29):
            b.r(x, 13, 2, 15, (210, 190, 120))
        if not aberto:
            b.r(2, 7, 30, 6, pl)
            b.r(13, 4, 8, 3, (210, 190, 120))                    # alça
            b.r(14, 5, 6, 1, (0, 0, 0, 0))
            b.r(15, 11, 4, 4, (210, 190, 120))
        else:
            b.r(2, 1, 30, 7, pd)                                 # tampa com espelho
            b.r(4, 2, 26, 5, (196, 222, 236))
            b.line((7, 6), (11, 2), (250, 250, 255))
            b.r(4, 9, 26, 4, white)
            for k, x in enumerate(range(6, 29, 4)):
                b.r(x, 9, 2, 3, ((255, 150, 220), (180, 150, 220), gold)[k % 3])
    else:                                                         # arca de mogno com ouro
        wood, wd, wl = (110, 46, 34), (74, 30, 22), (150, 70, 46)
        b.r(2, 14, 30, 14, wood)
        b.r(2, 14, 30, 1, wl)
        b.r(2, 26, 30, 2, wd)
        for x in (2, 30):
            b.r(x, 14, 2, 14, gold)
        b.r(2, 20, 30, 1, gold)
        b.r(3, 28, 3, 2, gold)
        b.r(28, 28, 3, 2, gold)
        if not aberto:
            b.r(2, 7, 30, 7, wl)
            b.r(4, 4, 26, 4, wl)
            b.r(4, 4, 26, 1, sh(wl, 30))
            b.r(2, 7, 30, 1, gold)
            b.r(14, 10, 6, 7, gold)
            b.r(16, 12, 2, 3, (90, 60, 20))
            b.r(8, 9, 3, 3, (80, 140, 240))                     # pedras na tampa
            b.r(23, 9, 3, 3, (220, 60, 80))
        else:
            b.r(2, 1, 30, 7, wd)
            b.r(2, 7, 30, 1, gold)
            b.r(3, 9, 28, 5, (40, 20, 60))                       # forro de veludo
            b.r(6, 10, 22, 3, gold)
    out = hd(b.s, keep=[gold, (64, 200, 230), (255, 150, 220)])
    if aberto:                                                    # luz saindo de dentro
        glow = pygame.Surface(out.get_size(), pygame.SRCALPHA)
        for k in range(10, 0, -1):
            pygame.draw.polygon(glow, (255, 230, 140, 10),
                                [(34 - k * 2, 22), (34 + k * 2, 22), (34 + k * 3, 0), (34 - k * 3, 0)])
        out.blit(glow, (0, 0))
    return out


ARMARIO = {   # moldura, fundo, porta, detalhe (dobradiça, puxador, placa)
    1: ((122, 80, 48), (74, 50, 34), (88, 56, 34), (220, 190, 90)),       # madeira
    2: ((70, 80, 96), (30, 34, 44), (50, 56, 70), (64, 200, 230)),        # rack de servidor
    3: ((236, 200, 220), (210, 190, 214), (250, 228, 238), (232, 120, 170)),   # armário rosa de vestiário
    4: ((96, 40, 30), (50, 22, 18), (70, 30, 24), (220, 180, 80)),        # cristaleira de mogno
}


def armario(cap):
    """O armário de armas aberto, sem as armas (o jogo pendura as da campanha nos ganchos)."""
    wood, back, door, trim = ARMARIO[cap]
    b = B(52, 48)
    wd, wl = sh(wood, -30), sh(wood, 30)
    b.r(6, 4, 40, 42, wd)
    b.r(4, 2, 44, 4, wl)
    b.r(4, 2, 44, 1, sh(wl, 20))
    b.r(9, 7, 34, 28, back)
    if cap == 2:                                                 # luzinhas do servidor no fundo
        for y in range(9, 34, 5):
            b.r(9, y, 34, 1, sh(back, 14))
            b.p(41, y + 2, (170, 90, 230))
    elif cap == 3:                                               # grade de ventilação
        for y in range(9, 34, 3):
            b.r(11, y, 30, 1, sh(back, -16))
    else:
        for x in range(9, 43, 6):
            b.r(x, 7, 1, 28, sh(back, -10))
    b.r(0, 6, 7, 38, door)                                       # portas abertas
    b.r(45, 6, 7, 38, door)
    if cap == 4:                                                 # vidro da cristaleira
        b.r(1, 8, 5, 34, (150, 180, 200))
        b.r(46, 8, 5, 34, (150, 180, 200))
        b.line((2, 12), (4, 9), (230, 240, 250))
        b.line((47, 12), (49, 9), (230, 240, 250))
    else:
        b.r(1, 8, 5, 15, sh(door, -16))
        b.r(1, 25, 5, 15, sh(door, -16))
        b.r(46, 8, 5, 15, sh(door, -16))
        b.r(46, 25, 5, 15, sh(door, -16))
    b.p(5, 24, trim)
    b.p(46, 24, trim)
    b.r(9, 36, 34, 8, wood)                                      # gaveta
    b.r(9, 36, 34, 1, wl)
    b.r(23, 39, 6, 2, trim)
    b.r(16, 0, 20, 4, sh(wood, -50))                             # plaquinha
    b.r(18, 1, 16, 2, trim)
    if cap == 4:
        b.r(4, 2, 44, 1, trim)
        b.r(6, 44, 40, 1, trim)
    return hd(b.s, keep=[(220, 190, 90), (64, 200, 230), (220, 180, 80), (170, 90, 230)])


def fogueira(cap):
    """A base da fogueira: o jogo põe o fogo (ou o vapor, no capítulo 3) mexendo por cima."""
    if cap == 1:                                                  # roda de pedras com lenha cruzada
        b = B(34, 18)
        b.circ((17, 10), 7, (40, 30, 26))
        for k in range(10):
            a = k * math.tau / 10
            x, y = round(17 + math.cos(a) * 14), round(10 + math.sin(a) * 6)
            stone = ((120, 116, 128), (100, 98, 110), (136, 130, 140))[k % 3]
            b.r(x - 2, y - 1, 5, 4, stone)
            b.r(x - 2, y - 1, 5, 1, sh(stone, 30))
        b.line((8, 12), (25, 7), (110, 70, 40), 3)
        b.line((9, 7), (26, 12), (126, 80, 44), 3)
        b.r(13, 9, 8, 2, (255, 150, 50))
        return hd(b.s, keep=[(255, 150, 50)])
    if cap == 2:                                                  # tambor de óleo com fogo
        b = B(22, 30)
        drum, dd, dl = (60, 110, 160), (40, 76, 116), (100, 150, 200)
        b.r(3, 6, 16, 23, drum)
        b.r(3, 6, 16, 1, dl)
        for y in (12, 20):
            b.r(3, y, 16, 2, dd)
        b.r(2, 4, 18, 3, (60, 62, 70))
        b.r(4, 5, 14, 1, (255, 150, 50))
        b.r(6, 15, 7, 3, (236, 200, 60))                          # adesivo
        b.r(7, 16, 2, 1, (40, 40, 46))
        b.r(4, 26, 14, 1, (150, 80, 50))                          # ferrugem
        return hd(b.s, keep=[(255, 150, 50)])
    if cap == 3:                                                  # difusor de vapor da clínica
        b = B(20, 24)
        b.r(5, 16, 10, 7, (250, 248, 250))
        b.r(4, 21, 12, 2, (226, 206, 220))
        b.r(6, 8, 8, 9, (236, 236, 242))
        b.r(6, 8, 8, 1, (255, 255, 255))
        b.r(8, 5, 4, 3, (210, 200, 222))
        b.r(7, 12, 6, 2, (255, 150, 220))                         # anel de luz rosa
        b.r(8, 18, 4, 1, (130, 210, 220))
        return hd(b.s, keep=[(255, 150, 220), (130, 210, 220)])
    b = B(48, 40)                                                 # lareira de mármore
    marble, md, ml = (226, 222, 216), (180, 176, 172), (246, 244, 240)
    b.r(2, 2, 44, 4, ml)                                          # tampo
    b.r(2, 5, 44, 1, md)
    b.r(4, 6, 40, 33, marble)
    for (x0, y0), (x1, y1) in (((6, 10), (12, 20)), ((36, 8), (42, 18)), ((8, 28), (14, 36)), ((38, 26), (34, 36))):
        b.line((x0, y0), (x1, y1), md)                            # veios do mármore
    b.r(12, 12, 24, 27, (30, 22, 22))                             # boca da lareira
    b.r(12, 12, 24, 2, (20, 14, 14))
    b.r(14, 33, 20, 3, (110, 70, 40))                             # lenha
    b.r(16, 31, 16, 2, (126, 80, 44))
    b.r(15, 34, 18, 1, (255, 150, 50))
    b.r(10, 38, 28, 2, (60, 56, 60))                              # grade
    b.r(20, 6, 8, 3, (220, 180, 80))                              # brasão dourado
    return hd(b.s, keep=[(255, 150, 50), (220, 180, 80)])


# ═════════════════════════════════════════════
#  Carros da turma (de lado, virados para a direita) e a beira da estrada da viagem
# ═════════════════════════════════════════════
def _bez(p0, p1, p2, n=10):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]) for t in [i / n for i in range(n + 1)]]


def _wheel(out, cx, cy, r, rim=(200, 204, 212), spokes=4, hub=(120, 124, 134)):
    pygame.draw.circle(out, (18, 18, 22), (cx, cy), r + 1)
    pygame.draw.circle(out, (40, 40, 46), (cx, cy), r)
    pygame.draw.arc(out, (72, 72, 80), (cx - r + 2, cy - r + 2, 2 * r - 4, 2 * r - 4), 0.6, 2.4, 2)
    pygame.draw.circle(out, sh(rim, -40), (cx, cy), r - 5)
    pygame.draw.circle(out, rim, (cx, cy), r - 6)
    for k in range(spokes):
        a = k * 2 * math.pi / spokes + 0.4
        pygame.draw.line(out, sh(rim, -70), (cx, cy), (cx + math.cos(a) * (r - 7), cy + math.sin(a) * (r - 7)), 2)
    pygame.draw.circle(out, hub, (cx, cy), 3)


CITY_AZUL = ((80, 102, 130), (52, 66, 86), (132, 154, 182))      # azul acinzentado do City do João
GLASS_MARK = ((200, 20, 200), (240, 60, 240))                    # cor de marcar o vidro (vira translúcido)
CITY_WHEELS = (44, 144)
UNO_WHEELS = (28, 98)
MOTO_WHEELS = (20, 112)


def city(glass=(40, 50, 62), glass_l=(150, 172, 190)):
    """Honda City sedã 2026 do João, azul acinzentado: teto em arco, farol de LED fino, coluna B
    preta, vinco lateral e aro de 5 raios."""
    b = B(92, 36)
    M, D, L = CITY_AZUL
    chrome = (206, 210, 218)
    top = (_bez((4, 16), (10, 13.5), (20, 13)) + _bez((20, 13), (27, 4), (40, 3.5))
           + _bez((40, 3.5), (52, 3.5), (63, 15)) + _bez((63, 15), (78, 16.5), (88, 20)))
    body = [(round(x), round(y)) for x, y in top] + [(89, 25), (88, 29), (3, 29), (2, 22)]
    b.poly(body, M)
    b.poly([(2, 24), (89, 25), (88, 29), (3, 29)], D)
    win = ([(round(x), round(y)) for x, y in _bez((23, 14), (29, 6), (40, 5.5))]
           + [(round(x), round(y)) for x, y in _bez((40, 5.5), (51, 5.5), (60, 15))])
    b.poly(win + [(60, 15.5), (23, 14.5)], glass)
    b.line((23, 14.8), (61, 15.8), chrome)
    b.r(44, 5, 2, 11, (26, 26, 30))
    b.line((29, 8), (31, 14), M, 2)
    b.line((49, 14), (53, 7), glass_l)
    b.line((35, 14), (38, 8), glass_l)
    b.line((5, 17), (86, 21), L)
    b.line((10, 25), (80, 25), sh(D, -8))
    b.r(45, 16, 1, 9, D)
    b.r(61, 16, 1, 9, D)
    b.r(29, 15, 1, 10, D)
    b.r(39, 18, 3, 1, chrome)
    b.r(55, 18, 3, 1, chrome)
    b.poly([(59, 13), (63, 13), (62, 16), (59, 16)], D)
    b.poly([(82, 19), (88, 20), (89, 22), (83, 21)], (236, 240, 246))
    b.r(84, 21, 4, 1, (250, 250, 255))
    b.poly([(3, 16), (7, 16), (7, 18), (3, 18)], (168, 36, 44))
    b.r(84, 26, 5, 2, (40, 40, 46))
    b.r(2, 26, 5, 2, (40, 40, 46))
    for cx in (22, 72):
        b.circ((cx, 28), 9, (24, 24, 28))
    out = hd(b.s, keep=[(250, 250, 255), *GLASS_MARK])
    for cx in CITY_WHEELS:
        cy = 56
        pygame.draw.circle(out, (18, 18, 22), (cx, cy), 15)
        pygame.draw.circle(out, (40, 40, 46), (cx, cy), 14)
        pygame.draw.arc(out, (70, 70, 78), (cx - 13, cy - 13, 26, 26), 0.6, 2.4, 2)
        pygame.draw.circle(out, (150, 154, 164), (cx, cy), 10)
        pygame.draw.circle(out, (204, 208, 216), (cx, cy), 9)
        for k in range(5):
            a0 = k * 2 * math.pi / 5 - math.pi / 2 + 0.63
            pts = [(cx + math.cos(a0 - 0.32) * 3, cy + math.sin(a0 - 0.32) * 3),
                   (cx + math.cos(a0 - 0.42) * 8.5, cy + math.sin(a0 - 0.42) * 8.5),
                   (cx + math.cos(a0 + 0.42) * 8.5, cy + math.sin(a0 + 0.42) * 8.5),
                   (cx + math.cos(a0 + 0.32) * 3, cy + math.sin(a0 + 0.32) * 3)]
            pygame.draw.polygon(out, (44, 46, 54), pts)
        pygame.draw.circle(out, (120, 124, 134), (cx, cy), 3)
        pygame.draw.circle(out, (220, 40, 50), (cx, cy), 1)
    return out


def uno(glass=(44, 56, 70), glass_l=(150, 172, 190)):
    """Fiat Uno Mille branco: caixote alto, traseira reta em pé, para-choque preto grosso, faixinha
    lateral e calota de 4 furos."""
    b = B(74, 36)
    W_, D, L = (238, 238, 232), (196, 196, 190), (252, 252, 248)
    b.poly([(2, 27), (2, 12), (4, 6), (7, 5), (44, 5), (57, 15), (70, 17), (72, 27)], W_)
    b.r(2, 22, 70, 5, D)
    b.poly([(19, 14), (19, 7), (33, 7), (33, 14)], glass)
    b.poly([(35, 14), (35, 7), (44, 7), (52, 14)], glass)
    b.poly([(4, 14), (6, 7), (14, 7), (14, 14)], glass)
    b.r(14, 6, 5, 9, W_)
    b.r(33, 6, 2, 9, (30, 30, 34))
    b.line((23, 13), (26, 8), glass_l)
    b.line((39, 13), (42, 8), glass_l)
    b.r(7, 4, 37, 1, L)
    b.r(3, 19, 68, 1, (40, 40, 44))
    b.r(34, 15, 1, 8, D)
    b.r(18, 15, 1, 8, D)
    b.r(31, 17, 3, 1, (150, 150, 156))
    b.r(68, 17, 4, 3, (250, 244, 200))
    b.r(2, 15, 2, 6, (200, 40, 44))
    b.r(2, 20, 2, 1, (240, 150, 40))
    b.r(1, 24, 72, 4, (34, 34, 38))
    b.r(51, 12, 4, 3, D)
    base = pygame.transform.scale(b.s, (62, 36))                   # o Uno é curtinho
    for cx in (14, 49):
        pygame.draw.circle(base, (24, 24, 28), (cx, 28), 8)
    out = hd(base, keep=[(250, 244, 200), *GLASS_MARK])
    for cx in UNO_WHEELS:
        _wheel(out, cx, 56, 13, rim=(180, 184, 190), spokes=4)
    return out


def moto():
    """Moto esportiva do Aryel, laranja: carenagem, tanque com faixa, banco preto, escapamento
    cromado, garfo dourado e rodas de 5 raios."""
    b = B(66, 40)
    O, Ol, K = (236, 120, 40), (252, 170, 90), (30, 30, 36)
    b.line((50, 14), (56, 30), (210, 170, 60), 2)
    b.poly([(14, 18), (30, 14), (44, 12), (52, 8), (58, 12), (52, 20), (40, 24), (22, 24)], O)
    b.poly([(28, 14), (40, 10), (46, 12), (34, 16)], Ol)
    b.r(30, 16, 12, 1, (250, 250, 250))
    b.poly([(12, 16), (28, 14), (26, 12), (10, 13)], K)
    b.poly([(2, 12), (12, 13), (12, 16), (4, 16)], O)
    b.r(2, 12, 3, 2, (220, 50, 50))
    b.poly([(52, 8), (58, 4), (60, 6), (56, 11)], (120, 160, 200))
    b.r(56, 11, 3, 2, (250, 244, 200))
    b.poly([(22, 24), (40, 24), (38, 30), (26, 30)], (70, 70, 80))
    b.r(26, 26, 10, 2, (120, 120, 130))
    b.line((26, 30), (8, 28), (210, 214, 222), 3)
    b.line((14, 22), (10, 30), K, 2)
    for cx in (10, 56):
        b.circ((cx, 31), 8, (24, 24, 28))
    out = hd(b.s, keep=[(250, 244, 200), (250, 250, 250)])
    for cx in MOTO_WHEELS:
        _wheel(out, cx, 62, 14, rim=(60, 60, 66), spokes=5, hub=(210, 170, 60))
    return out


def com_vidro(fn):
    """O carro com o vidro meio transparente (na viagem dá para ver a turma lá dentro): desenha de
    novo com o vidro numa cor de marcar e deixa translúcido o que mudou."""
    car, marked = fn(), fn(*GLASS_MARK)
    w, h = car.get_size()
    for y in range(h):
        for x in range(w):
            c = car.get_at((x, y))
            if c.a and c != marked.get_at((x, y)):
                car.set_at((x, y), (c.r, c.g, c.b, 85))
    return car


def casinha(v):
    b = B(52, 46)
    walls = ((222, 196, 150), (176, 200, 214), (236, 214, 170), (200, 170, 190))[v % 4]
    roof = ((168, 74, 58), (120, 70, 60), (150, 90, 60))[v % 3]
    b.r(4, 18, 44, 28, walls)
    for y in range(20, 46, 4):
        b.r(4, y, 44, 1, sh(walls, -10))
    b.poly([(0, 19), (26, 3), (52, 19)], roof)
    for x in range(4, 50, 6):
        b.line((x, 19), (min(26, x + 10), max(3, 19 - (x + 10) * 16 // 26)), sh(roof, -20))
    b.r(38, 4, 5, 9, (150, 110, 90))
    b.r(9, 24, 12, 10, (96, 140, 180))
    b.r(9, 24, 12, 1, (220, 230, 240))
    b.r(14, 24, 1, 10, walls)
    b.r(8, 34, 14, 2, sh(walls, -30))
    for k in range(4):
        b.r(9 + k * 3, 32, 2, 2, ((230, 80, 90), (250, 200, 80))[k % 2])
    b.r(30, 28, 10, 18, (120, 82, 54))
    b.p(38, 37, (220, 190, 90))
    b.r(28, 44, 14, 2, (170, 170, 170))
    return hd(b.s)


def arvore(v):
    b = B(28, 44)
    b.r(12, 28, 4, 16, (96, 66, 44))
    g = ((60, 120, 64), (70, 136, 70), (52, 110, 60))[v % 3]
    for cx, cy, r in ((14, 14, 10), (7, 22, 7), (21, 22, 7), (14, 25, 8)):
        b.circ((cx, cy), r, g)
    b.circ((10, 11), 3, sh(g, 30))
    return hd(b.s)


def poste():
    b = B(14, 60)
    b.r(6, 6, 2, 54, (120, 124, 132))
    b.r(6, 6, 8, 2, (120, 124, 132))
    b.r(10, 8, 4, 3, (250, 230, 160))
    return hd(b.s, keep=[(250, 230, 160)])



# ═════════════════════════════════════════════
#  Garagem lá embaixo
# ═════════════════════════════════════════════
def painel_ferramentas():
    """Painel de furos com as ferramentas penduradas (vai preso na parede)."""
    b = B(70, 40)
    b.r(0, 0, 70, 40, (150, 110, 70))
    b.r(0, 0, 70, 2, (180, 140, 96))
    for yy in range(4, 40, 5):
        for xx in range(4, 70, 5):
            b.p(xx, yy, (110, 80, 50))
    b.r(6, 6, 2, 18, (200, 40, 40))                                  # chave inglesa
    b.r(4, 6, 6, 4, (180, 184, 196))
    b.r(14, 6, 2, 16, (120, 80, 50))                                 # martelo
    b.r(12, 5, 7, 4, (90, 92, 100))
    b.r(24, 6, 3, 14, (240, 200, 40))                                # chave de fenda
    b.r(25, 20, 1, 6, (190, 196, 210))
    b.r(32, 6, 10, 2, (180, 184, 196))                               # alicate
    b.r(32, 8, 2, 12, (180, 184, 196))
    b.r(40, 8, 2, 12, (180, 184, 196))
    for i in range(5):                                               # jogo de chaves
        b.r(48 + i * 4, 6, 2, 8 + i * 2, (180, 184, 196))
    b.circ((58, 30), 6, (60, 60, 66))                                # rolo de fio
    b.circ((58, 30), 3, (150, 110, 70))
    b.r(8, 30, 30, 6, (60, 62, 70))                                  # furadeira
    b.r(8, 30, 10, 6, (240, 200, 40))
    return hd(b.s)


def estante_trofeus():
    """Estante de madeira: a prateleira de cima vazia (o jogo põe os troféus) e a de baixo com o
    capacete, a placa UNO, o galão e a caixa."""
    b = B(80, 44)
    b.r(0, 2, 80, 40, (96, 62, 38))
    b.r(2, 4, 76, 18, (60, 40, 26))
    b.r(2, 24, 76, 16, (60, 40, 26))
    b.r(0, 21, 80, 3, (130, 88, 52))
    b.r(0, 2, 80, 2, (130, 88, 52))
    b.r(6, 28, 14, 10, (220, 60, 60))                                # capacete
    b.r(8, 30, 10, 6, (250, 250, 250))
    b.r(26, 30, 20, 8, (40, 70, 150))                                # placa UNO
    b.r(28, 32, 16, 2, (250, 250, 250))
    b.r(52, 26, 6, 12, (236, 120, 40))                               # galão
    b.r(62, 28, 12, 10, (60, 60, 66))                                # caixa
    b.r(62, 28, 12, 2, (90, 92, 100))
    return hd(b.s)


def trofeu(gold=True):
    b = B(12, 14)
    g = (236, 196, 80) if gold else (200, 204, 212)
    b.r(2, 10, 8, 4, (80, 60, 40))
    b.r(4, 7, 4, 3, g)
    b.r(0, 0, 12, 7, g)
    b.r(2, 1, 3, 4, sh(g, 40))
    return hd(b.s, keep=[(236, 196, 80)])


def carrinho_ferramentas():
    b = B(26, 30)
    b.r(1, 4, 24, 22, (200, 40, 44))
    b.r(1, 4, 24, 2, (236, 90, 90))
    for y in (9, 14, 19):
        b.r(3, y, 20, 4, (170, 30, 36))
        b.r(11, y + 1, 4, 1, (210, 214, 222))
    b.circ((4, 28), 2, (30, 30, 34))
    b.circ((22, 28), 2, (30, 30, 34))
    b.r(0, 1, 26, 3, (60, 60, 66))
    b.r(4, 0, 6, 1, (180, 184, 196))
    b.r(14, 0, 4, 1, (240, 200, 40))
    return hd(b.s)


def pilha_pneus():
    b = B(24, 26)
    for i in range(3):
        y = 18 - i * 7
        pygame.draw.ellipse(b.s, (28, 28, 32), (1, y, 22, 8))
        pygame.draw.ellipse(b.s, (50, 50, 56), (1, y, 22, 4))
        pygame.draw.ellipse(b.s, (14, 14, 18), (7, y + 1, 10, 3))
    return hd(b.s)


def tambor_oleo():
    b = B(16, 22)
    b.r(1, 2, 14, 19, (40, 90, 160))
    b.r(1, 6, 14, 1, (30, 70, 130))
    b.r(1, 15, 14, 1, (30, 70, 130))
    b.r(1, 2, 14, 2, (70, 120, 190))
    b.r(4, 8, 8, 5, (250, 250, 250))
    b.r(5, 9, 6, 1, (220, 60, 60))
    b.r(10, 3, 2, 1, (30, 30, 34))
    return hd(b.s)



# ═════════════════════════════════════════════
#  Mascotes da Casa (do tamanho certo perto de um herói)
# ═════════════════════════════════════════════
def gato(pose="sentado"):
    """Gato laranja de peito branco: sentado de frente ou andando de lado (virado para a direita)."""
    b = B(20, 18)
    o, od, w = (226, 140, 60), (184, 100, 40), (250, 244, 236)
    eye, glint = (90, 170, 80), (250, 250, 220)
    if pose == "sentado":
        b.r(5, 8, 10, 9, o)
        b.r(7, 12, 6, 5, w)
        b.r(5, 2, 10, 7, o)
        b.poly([(5, 3), (6, 0), (8, 2)], o)
        b.poly([(12, 2), (14, 0), (15, 3)], o)
        b.p(6, 1, (240, 160, 160))
        b.p(13, 1, (240, 160, 160))
        b.r(6, 4, 2, 1, od)
        b.r(12, 4, 2, 1, od)
        b.r(7, 5, 2, 2, eye)
        b.r(11, 5, 2, 2, eye)
        b.p(7, 5, glint)
        b.p(11, 5, glint)
        b.p(10, 7, (230, 120, 130))
        b.r(9, 8, 3, 1, w)
        b.r(15, 12, 3, 2, o)
        b.r(17, 9, 2, 4, o)
        b.p(17, 9, od)
        b.r(6, 16, 3, 1, w)
        b.r(11, 16, 3, 1, w)
    else:
        b.r(4, 7, 12, 6, o)
        b.r(4, 12, 2, 5, o)
        b.r(8, 12, 2, 5, od)
        b.r(12, 12, 2, 5, o)
        b.r(14, 12, 2, 4, od)
        for x in (6, 10):
            b.r(x, 7, 1, 5, od)
        b.r(13, 2, 6, 6, o)
        b.poly([(13, 3), (14, 0), (16, 2)], o)
        b.poly([(17, 2), (18, 0), (19, 3)], o)
        b.r(16, 4, 2, 2, eye)
        b.p(19, 6, (230, 120, 130))
        b.r(16, 7, 3, 1, w)
        b.r(1, 4, 3, 2, o)
        b.r(0, 2, 2, 3, o)
    return hd(b.s, keep=[eye, glint])


def cachorro(pose="sentado"):
    """Vira-lata caramelo de coleira vermelha: sentado de frente ou andando de lado."""
    b = B(24, 20)
    c, cd, cl, w = (198, 140, 70), (150, 96, 46), (226, 178, 110), (240, 224, 196)
    if pose == "sentado":
        b.r(6, 9, 12, 10, c)
        b.r(9, 12, 6, 7, w)
        b.r(6, 1, 12, 9, c)
        b.r(4, 2, 3, 7, cd)
        b.r(17, 2, 3, 7, cd)
        b.r(9, 6, 6, 4, cl)
        b.r(11, 6, 2, 2, (30, 26, 28))
        b.r(8, 4, 2, 2, (40, 30, 26))
        b.r(14, 4, 2, 2, (40, 30, 26))
        b.p(8, 4, (250, 250, 250))
        b.p(14, 4, (250, 250, 250))
        b.r(11, 9, 2, 2, (230, 100, 110))
        b.r(9, 10, 6, 1, (200, 50, 50))
        b.p(12, 11, (240, 200, 80))
        b.r(7, 18, 3, 1, cl)
        b.r(14, 18, 3, 1, cl)
        b.r(18, 14, 4, 2, c)
        b.r(20, 11, 2, 4, c)
    else:
        b.r(4, 7, 14, 7, c)
        b.r(5, 13, 2, 6, c)
        b.r(9, 13, 2, 6, cd)
        b.r(13, 13, 2, 6, c)
        b.r(16, 13, 2, 5, cd)
        b.r(8, 12, 6, 2, w)
        b.r(16, 2, 7, 7, c)
        b.r(21, 5, 3, 3, cl)
        b.p(23, 5, (30, 26, 28))
        b.r(15, 3, 2, 6, cd)
        b.r(19, 4, 2, 2, (40, 30, 26))
        b.p(19, 4, (250, 250, 250))
        b.r(16, 8, 3, 1, (200, 50, 50))
        b.r(1, 4, 3, 2, c)
        b.r(0, 2, 2, 3, c)
    return hd(b.s, keep=[(250, 250, 250)])


def papagaio(pose="pousado"):
    """Papagaio verde de testa azul e rosto amarelo: pousado (sem o poleiro) ou voando."""
    b = B(18, 20)
    g, gd, gl, y, r, bl = (60, 170, 70), (34, 120, 50), (120, 210, 100), (250, 210, 60), (220, 60, 50), (60, 120, 220)
    if pose == "pousado":
        b.r(8, 2, 6, 6, g)
        b.r(9, 3, 4, 2, y)
        b.r(8, 1, 4, 2, bl)
        b.r(12, 4, 3, 3, (60, 60, 64))
        b.p(14, 6, (40, 40, 44))
        b.r(10, 4, 1, 1, (30, 30, 30))
        b.p(10, 3, (250, 250, 250))
        b.r(6, 8, 8, 10, g)
        b.r(5, 9, 3, 8, gd)
        b.r(6, 15, 3, 3, r)
        b.r(7, 17, 4, 3, gd)
        b.r(8, 17, 2, 3, bl)
        b.r(8, 17, 1, 2, (110, 110, 120))
        b.r(11, 17, 1, 2, (110, 110, 120))
    else:
        b.r(6, 10, 8, 6, g)
        b.r(13, 10, 3, 3, g)
        b.r(15, 11, 2, 2, (60, 60, 64))
        b.r(13, 10, 2, 1, y)
        b.poly([(7, 10), (2, 2), (12, 9)], gd)
        b.poly([(8, 10), (5, 3), (11, 9)], gl)
        b.r(3, 4, 3, 2, r)
        b.r(1, 13, 6, 2, bl)
    return hd(b.s, keep=[(250, 250, 250)])


def main():
    pygame.init()
    OUT.mkdir(parents=True, exist_ok=True)
    done = set()
    for (kind, cap), fn in NPCS.items():
        if fn.__name__ not in done:
            done.add(fn.__name__)
            for (pose, i), img in zip(NPC_FRAMES, npc_frames(fn)):
                pygame.image.save(img, str(OUT / f"npc_{fn.__name__}_{pose}{i}.png"))
        pygame.image.save(banca_tras(kind, cap), str(OUT / f"banca_{kind}_{cap}_tras.png"))
        pygame.image.save(banca_frente(kind, cap), str(OUT / f"banca_{kind}_{cap}_frente.png"))
    for cap in CHAPTERS:
        for aberto in (False, True):
            pygame.image.save(bau(cap, aberto), str(OUT / f"bau_{cap}_{'aberto' if aberto else 'fechado'}.png"))
        pygame.image.save(armario(cap), str(OUT / f"armario_{cap}.png"))
        pygame.image.save(fogueira(cap), str(OUT / f"fogueira_{cap}.png"))
    pygame.image.save(city(), str(OUT / "carro_city.png"))
    pygame.image.save(com_vidro(city), str(OUT / "carro_city_vidro.png"))
    pygame.image.save(uno(), str(OUT / "carro_uno.png"))
    pygame.image.save(com_vidro(uno), str(OUT / "carro_uno_vidro.png"))
    pygame.image.save(moto(), str(OUT / "moto.png"))
    for v in range(4):
        pygame.image.save(casinha(v), str(OUT / f"estrada_casa_{v}.png"))
    for v in range(3):
        pygame.image.save(arvore(v), str(OUT / f"estrada_arvore_{v}.png"))
    pygame.image.save(poste(), str(OUT / "estrada_poste.png"))
    for name, fn in (("garagem_painel", painel_ferramentas), ("garagem_estante", estante_trofeus),
                     ("garagem_carrinho", carrinho_ferramentas), ("garagem_pneus", pilha_pneus),
                     ("garagem_tambor", tambor_oleo)):
        pygame.image.save(fn(), str(OUT / f"{name}.png"))
    pygame.image.save(trofeu(True), str(OUT / "garagem_trofeu_ouro.png"))
    pygame.image.save(trofeu(False), str(OUT / "garagem_trofeu_prata.png"))
    for name, img in (("mascote_gato_sentado", gato()), ("mascote_gato_andando", gato("andando")),
                      ("mascote_cachorro_sentado", cachorro()), ("mascote_cachorro_andando", cachorro("andando")),
                      ("mascote_papagaio_sentado", papagaio()), ("mascote_papagaio_andando", papagaio("voando"))):
        pygame.image.save(img, str(OUT / f"{name}.png"))
    print("peças em", OUT)


if __name__ == "__main__":
    main()
