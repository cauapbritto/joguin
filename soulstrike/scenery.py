"""Cenário dos mapas que não têm arte própria (Floresta, Calabouço, Templo Gelado e a Lag Lobby).

- O chão é pintado uma vez só, em "pixels" de 2x2 (a mesma escala dos personagens), com
  grama, trilhas, pedras, rachaduras, poças, neve... e guardado pronto.
- Cada mapa tem o seu estilo de parede (cerca viva, tijolos com musgo, blocos de gelo),
  também desenhado uma vez só por parede.
- O ambiente se mexe com pouca coisa por quadro: vaga-lumes, tochas e neve caindo.
"""
import math
import random

import pygame

U = 2                      # tamanho do "pixel" da pixel art no mundo
_FLOORS = {}               # chão pronto de cada mapa (pintar custa alguns milissegundos)
_WALLS = {}                # parede pronta por (mapa, retângulo)


def _shade(color, amount):
    return tuple(max(0, min(255, c + amount)) for c in color[:3])


def _mix(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


# ─────────────────────────────────────────────
#  Chão
# ─────────────────────────────────────────────
VOID = (7, 6, 10)            # fora das salas (masmorra): escuro


def paint_floor(key, size, theme=None, void=()):
    """Chão pronto do mapa (ou None se o mapa não tem cenário próprio).

    theme: qual cenário usar (os mapas da masmorra usam o do tema da fase, com outra semente);
    void: retângulos fora das salas, que ficam escuros."""
    painter = _PAINTERS.get(theme or key)
    if painter is None:
        return None
    if key not in _FLOORS:
        w, h = size
        small = pygame.Surface((w // U, h // U))
        painter(small, random.Random(f"chão:{key}"))
        for x, y, vw, vh in void:
            small.fill(VOID, (x // U, y // U, vw // U, vh // U))
        _FLOORS[key] = pygame.transform.scale(small, size)
    return _FLOORS[key]          # só é lido (a miniatura faz a própria cópia)


def _blob(surf, rng, x, y, r, color):
    """Mancha irregular: alguns círculos juntos."""
    for _ in range(4):
        pygame.draw.circle(surf, color, (x + rng.randint(-r // 2, r // 2), y + rng.randint(-r // 3, r // 3)),
                           max(1, int(r * rng.uniform(0.5, 1.0))))


def _floresta(s, rng):
    w, h = s.get_size()
    base = (32, 56, 30)
    s.fill(base)
    for _ in range(260):                                     # manchas de grama clara e escura
        c = _shade(base, rng.choice((-7, -4, 5, 9)))
        _blob(s, rng, rng.randrange(w), rng.randrange(h), rng.randint(6, 26), c)
    # trilhas de terra serpenteando pelo mapa
    dirt, dirt_d, dirt_l = (88, 68, 44), (66, 50, 34), (106, 84, 56)
    for start, end in (((0, h * 0.5), (w, h * 0.46)), ((w * 0.5, 0), (w * 0.52, h))):
        steps = 140
        phase = rng.uniform(0, math.tau)
        pts = []
        for i in range(steps + 1):
            t = i / steps
            x = start[0] + (end[0] - start[0]) * t
            y = start[1] + (end[1] - start[1]) * t
            bend = math.sin(t * math.tau * 1.5 + phase) * 26
            if start[0] == 0:
                y += bend
            else:
                x += bend
            pts.append((int(x), int(y)))
        for x, y in pts:
            pygame.draw.circle(s, dirt_d, (x, y), 12)
        for x, y in pts:
            pygame.draw.circle(s, dirt, (x, y), 10)
        for x, y in pts[::3]:
            s.set_at((x + rng.randint(-8, 8), y + rng.randint(-8, 8)), dirt_l)
            s.set_at((x + rng.randint(-8, 8), y + rng.randint(-8, 8)), dirt_d)
    # tufos de grama
    for _ in range(2600):
        x, y = rng.randrange(1, w - 1), rng.randrange(2, h)
        if s.get_at((x, y))[:3] in (dirt, dirt_d):
            continue
        c = rng.choice(((54, 90, 42), (64, 104, 48), (44, 76, 36)))
        s.set_at((x, y), c)
        s.set_at((x - 1, y - 1), c)
        s.set_at((x + 1, y - 1), c)
        if rng.random() < 0.5:
            s.set_at((x, y - 2), _shade(c, 14))
    # flores
    for _ in range(260):
        x, y = rng.randrange(2, w - 2), rng.randrange(2, h - 2)
        petal = rng.choice(((232, 226, 210), (226, 196, 80), (186, 132, 214), (220, 110, 110)))
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            s.set_at((x + dx, y + dy), petal)
        s.set_at((x, y), (250, 220, 90))
    # pedras
    for _ in range(90):
        x, y = rng.randrange(4, w - 4), rng.randrange(4, h - 4)
        rw, rh = rng.randint(3, 6), rng.randint(2, 4)
        pygame.draw.ellipse(s, (60, 64, 58), (x - 1, y + 1, rw + 2, rh + 1))
        pygame.draw.ellipse(s, (104, 108, 98), (x, y, rw, rh))
        s.set_at((x + 1, y), (150, 152, 140))
    # cogumelos vermelhos
    for _ in range(40):
        x, y = rng.randrange(3, w - 3), rng.randrange(4, h - 2)
        s.fill((226, 216, 196), (x, y, 1, 2))
        s.fill((196, 50, 46), (x - 1, y - 2, 3, 2))
        s.set_at((x, y - 2), (250, 240, 230))
    # folhas caídas
    for _ in range(420):
        s.set_at((rng.randrange(w), rng.randrange(h)), rng.choice(((150, 96, 40), (120, 76, 34), (170, 128, 52))))
    _vignette(s, (10, 20, 10), 46)


def _calabouco(s, rng):
    w, h = s.get_size()
    mortar = (22, 16, 14)
    s.fill(mortar)
    row_h = 16
    for row, y in enumerate(range(0, h, row_h)):
        x = -rng.randint(0, 20)
        while x < w:
            tw = rng.randint(14, 28)
            c = _shade((44, 34, 28), rng.randint(-8, 8))
            s.fill(c, (x + 1, y + 1, tw - 1, row_h - 1))
            s.fill(_shade(c, 12), (x + 1, y + 1, tw - 1, 1))          # luz no topo da pedra
            s.fill(_shade(c, -10), (x + 1, y + row_h - 1, tw - 1, 1))
            if rng.random() < 0.25:                                   # pedra gasta
                s.set_at((x + rng.randint(2, max(3, tw - 2)), y + rng.randint(3, row_h - 3)), _shade(c, -14))
            x += tw
    # rachaduras
    for _ in range(110):
        x, y = rng.randrange(w), rng.randrange(h)
        for _ in range(rng.randint(3, 7)):
            nx, ny = x + rng.randint(-3, 3), y + rng.randint(-3, 3)
            pygame.draw.line(s, (18, 12, 10), (x, y), (nx, ny))
            x, y = nx, ny
    # musgo
    for _ in range(70):
        x, y = rng.randrange(w), rng.randrange(h)
        for _ in range(rng.randint(8, 24)):
            s.set_at((x + rng.randint(-6, 6), y + rng.randint(-4, 4)),
                     rng.choice(((50, 62, 32), (60, 74, 36), (42, 52, 28))))
    # poças d'água
    for _ in range(16):
        x, y = rng.randrange(20, w - 20), rng.randrange(20, h - 20)
        pw, ph = rng.randint(12, 26), rng.randint(5, 9)
        pygame.draw.ellipse(s, (26, 30, 38), (x, y, pw, ph))
        pygame.draw.ellipse(s, (44, 52, 66), (x, y, pw, ph), 1)
        s.fill((96, 110, 130), (x + pw // 3, y + 2, 3, 1))
    # ossos e caveiras
    bone, bone_d = (196, 186, 164), (120, 110, 96)
    for _ in range(30):
        x, y = rng.randrange(6, w - 6), rng.randrange(6, h - 6)
        if rng.random() < 0.6:                              # osso deitado, com as pontas arredondadas
            s.fill(bone_d, (x, y + 1, 6, 1))
            s.fill(bone, (x, y, 6, 1))
            for ex in (x - 1, x + 6):
                s.set_at((ex, y - 1), bone)
                s.set_at((ex, y + 1), bone)
        else:                                               # osso na diagonal
            for i in range(5):
                s.set_at((x + i, y + i), bone)
                s.set_at((x + i, y + i + 1), bone_d)
            for ex, ey in ((x - 1, y), (x, y - 1), (x + 5, y + 4), (x + 4, y + 5)):
                s.set_at((ex, ey), bone)
    for _ in range(8):
        x, y = rng.randrange(6, w - 6), rng.randrange(6, h - 6)
        s.fill(bone, (x, y, 4, 3))
        s.fill(bone, (x + 1, y + 3, 2, 1))
        s.set_at((x + 1, y + 1), (30, 22, 20))
        s.set_at((x + 2, y + 1), (30, 22, 20))
    # ralos
    for _ in range(5):
        x, y = rng.randrange(10, w - 10), rng.randrange(10, h - 10)
        s.fill((14, 10, 10), (x, y, 8, 8))
        for k in range(1, 8, 2):
            s.fill((58, 52, 50), (x + k, y + 1, 1, 6))
    _vignette(s, (8, 4, 4), 40)


def _templo(s, rng):
    w, h = s.get_size()
    for gy in range(0, h, 16):
        for gx in range(0, w, 16):
            c = (44, 56, 70) if (gx // 16 + gy // 16) % 2 else (38, 49, 62)
            c = _shade(c, rng.randint(-3, 3))
            s.fill(c, (gx, gy, 16, 16))
            s.fill(_shade(c, 10), (gx, gy, 16, 1))
            s.fill(_shade(c, 6), (gx, gy, 1, 16))
            s.fill(_shade(c, -8), (gx, gy + 15, 16, 1))
            if rng.random() < 0.35:                                   # brilho do gelo polido
                k = rng.randint(2, 9)
                for i in range(5):
                    s.set_at((gx + k + i, gy + 10 - i), _shade(c, 20))
            if rng.random() < 0.06:                                   # rachadura fina e reta
                x, y = gx + rng.randint(2, 13), gy + rng.randint(2, 13)
                dx, dy = rng.choice(((1, 1), (1, -1), (2, 1), (1, 2)))
                for _ in range(rng.randint(2, 4)):
                    nx, ny = x + dx * rng.randint(1, 3), y + dy * rng.randint(1, 3)
                    pygame.draw.line(s, (126, 160, 190), (x, y), (nx, ny))
                    x, y = nx, ny
    # círculo de runas no meio (onde o chefão luta)
    cx, cy = w // 2, h // 2
    rune = (82, 150, 200)
    for r in (86, 78):
        pygame.draw.circle(s, rune, (cx, cy), r, 1)
    for k in range(24):
        a = k * math.tau / 24
        x0, y0 = cx + math.cos(a) * 78, cy + math.sin(a) * 78
        x1, y1 = cx + math.cos(a) * 86, cy + math.sin(a) * 86
        pygame.draw.line(s, rune, (x0, y0), (x1, y1))
    for k in range(6):
        a = k * math.tau / 6 + 0.3
        x, y = int(cx + math.cos(a) * 70), int(cy + math.sin(a) * 70)
        s.fill((120, 196, 236), (x - 1, y - 1, 3, 3))
    # montinhos de neve: baixos e compridos, com a sombra embaixo
    for _ in range(54):
        _drift(s, rng, rng.randrange(w), rng.randrange(h), rng.randint(12, 30))
    for _ in range(1600):
        s.set_at((rng.randrange(w), rng.randrange(h)), rng.choice(((120, 150, 178), (150, 180, 206))))
    # cristais de gelo
    for _ in range(24):
        x, y = rng.randrange(4, w - 4), rng.randrange(6, h - 2)
        for dy, half in ((-4, 0), (-3, 1), (-2, 1), (-1, 1), (0, 0)):
            s.fill((140, 210, 240), (x - half, y + dy, half * 2 + 1, 1))
        s.set_at((x, y - 3), (230, 248, 255))
    _vignette(s, (14, 20, 30), 40)


def _drift(s, rng, x, y, size):
    for k in range(rng.randint(2, 4)):
        ox = x + rng.randint(-size // 2, size // 2)
        ww = rng.randint(size // 2, size)
        hh = max(3, ww // rng.randint(2, 4))
        pygame.draw.ellipse(s, (120, 146, 170), (ox - ww // 2, y - hh // 2 + 1, ww, hh))
        pygame.draw.ellipse(s, (206, 222, 236), (ox - ww // 2, y - hh // 2, ww, hh - 1))
        s.fill((240, 248, 255), (ox - ww // 4, y - hh // 2, max(1, ww // 3), 1))


def _vignette(s, color, depth):
    """Escurece as bordas do mapa (a câmera não chega lá, mas a miniatura fica bonita)."""
    w, h = s.get_size()
    layer = pygame.Surface((w, h), pygame.SRCALPHA)
    for i in range(depth):
        a = int(110 * (1 - i / depth) ** 2)
        pygame.draw.rect(layer, (*color, a), (i, i, w - 2 * i, h - 2 * i), 1)
    s.blit(layer, (0, 0))


# ── Lag Lobby (capítulo 2): escritório limpo, branco e ciano, sujo pela Patrulha Cinza ──
LAG_CYAN = (64, 200, 230)
TAPE = ((236, 196, 40), (30, 28, 30))          # fita de isolamento: amarelo e preto


def _tape(s, rng, x, y, length, vertical=False):
    """Fita de isolamento esticada no chão (listras amarelas e pretas)."""
    for i in range(length):
        c = TAPE[(i // 3) % 2]
        if vertical:
            s.fill(c, (x, y + i, 3, 1))
        else:
            s.fill(c, (x + i, y, 1, 3))


def _crate(s, x, y):
    """Caixa de munição da Patrulha: verde-oliva com a tampa e a faixa amarela."""
    s.fill((22, 24, 18), (x + 1, y + 1, 12, 8))
    s.fill((78, 86, 54), (x, y, 12, 8))
    s.fill((104, 114, 72), (x, y, 12, 2))
    s.fill((206, 176, 44), (x + 2, y + 4, 8, 1))


def _lag_escritorio(s, rng):
    """Piso de escritório: placas claras com rejunte, tapetes de carpete azul e cabos no chão."""
    w, h = s.get_size()
    tile = 24
    for gy in range(0, h, tile):
        for gx in range(0, w, tile):
            c = _shade((176, 184, 194), rng.randint(-5, 5))
            s.fill(c, (gx, gy, tile, tile))
            s.fill(_shade(c, 14), (gx, gy, tile, 1))
            s.fill(_shade(c, -24), (gx, gy, 1, tile))
            if rng.random() < 0.18:                                   # reflexo da luz no piso
                for i in range(6):
                    s.set_at((gx + 4 + i, gy + 14 - i), _shade(c, 18))
    for _ in range(max(1, w * h // 120000)):                          # carpetes azuis
        cw, ch = rng.randint(60, 140), rng.randint(40, 90)
        x, y = rng.randrange(0, max(1, w - cw)), rng.randrange(0, max(1, h - ch))
        s.fill((70, 96, 140), (x, y, cw, ch))
        for _ in range(cw * ch // 30):
            s.set_at((x + rng.randrange(cw), y + rng.randrange(ch)), rng.choice(((80, 106, 150), (62, 86, 128))))
        pygame.draw.rect(s, (30, 44, 74), (x, y, cw, ch), 1)
    for _ in range(14):                                               # canaletas de cabo
        x, y = rng.randrange(w), rng.randrange(h)
        if rng.random() < 0.5:
            length = rng.randint(40, 160)
            s.fill((120, 128, 140), (x, y, length, 3))
            s.fill((150, 158, 170), (x, y, length, 1))
        else:
            length = rng.randint(40, 160)
            s.fill((120, 128, 140), (x, y, 3, length))
            s.fill((150, 158, 170), (x, y, 1, length))
    for _ in range(10):                                               # logo da Lag Lobby (ciano) riscado
        x, y = rng.randrange(20, w - 20), rng.randrange(20, h - 20)
        pygame.draw.circle(s, LAG_CYAN, (x, y), 6, 2)
        s.fill(LAG_CYAN, (x - 2, y - 2, 2, 5))
        pygame.draw.line(s, (40, 40, 44), (x - 8, y + 6), (x + 8, y - 6), 2)
    for _ in range(18):                                               # sujeira da Patrulha
        x, y = rng.randrange(w), rng.randrange(h)
        _tape(s, rng, x, y, rng.randint(20, 70), vertical=rng.random() < 0.5)
    for _ in range(10):
        _crate(s, rng.randrange(4, w - 16), rng.randrange(4, h - 12))
    for _ in range(40):                                               # pegadas de bota
        x, y = rng.randrange(w), rng.randrange(h)
        s.fill((140, 146, 156), (x, y, 2, 3))
        s.fill((140, 146, 156), (x + 3, y + 4, 2, 3))
    _vignette(s, (60, 66, 80), 30)


def _lag_datacenter(s, rng):
    """Data center: piso elevado escuro em placas, algumas vazadas (ventilação), faixa ciano."""
    w, h = s.get_size()
    tile = 20
    for gy in range(0, h, tile):
        for gx in range(0, w, tile):
            c = _shade((46, 52, 64), rng.randint(-3, 3))
            s.fill(c, (gx, gy, tile, tile))
            s.fill(_shade(c, 16), (gx, gy, tile, 1))
            s.fill(_shade(c, 8), (gx, gy, 1, tile))
            s.fill(_shade(c, -14), (gx, gy + tile - 1, tile, 1))
            if rng.random() < 0.22:                                   # placa vazada
                for yy in range(gy + 4, gy + tile - 3, 3):
                    for xx in range(gx + 4, gx + tile - 3, 3):
                        s.set_at((xx, yy), (22, 26, 34))
    for y in range(0, h, 120):                                        # faixas de guia no chão
        s.fill((30, 110, 130), (0, y + 2, w, 1))
    for _ in range(26):                                               # cabos soltos
        x, y = rng.randrange(w), rng.randrange(h)
        color = rng.choice(((40, 150, 200), (200, 80, 60), (220, 200, 70)))
        for _ in range(rng.randint(8, 20)):
            nx, ny = x + rng.randint(-3, 4), y + rng.randint(-2, 3)
            pygame.draw.line(s, color, (x, y), (nx, ny))
            x, y = nx, ny
    for _ in range(12):
        x, y = rng.randrange(w), rng.randrange(h)
        _tape(s, rng, x, y, rng.randint(20, 60), vertical=rng.random() < 0.5)
    for _ in range(8):                                                # veios roxos do fragmento
        x, y = rng.randrange(w), rng.randrange(h)
        for _ in range(rng.randint(6, 14)):
            nx, ny = x + rng.randint(-4, 4), y + rng.randint(-4, 4)
            pygame.draw.line(s, (130, 70, 200), (x, y), (nx, ny))
            x, y = nx, ny
    _vignette(s, (10, 14, 20), 40)


def _lag_garagem(s, rng):
    """Estacionamento: asfalto, vagas pintadas de branco, manchas de óleo e a faixa amarela."""
    w, h = s.get_size()
    s.fill((56, 58, 62))
    for _ in range(40):                                               # remendos de asfalto
        c = _shade((56, 58, 62), rng.randint(-10, 10))
        s.fill(c, (rng.randrange(w), rng.randrange(h), rng.randint(30, 90), rng.randint(20, 60)))
    for _ in range(w * h // 6):
        s.set_at((rng.randrange(w), rng.randrange(h)), _shade((60, 62, 66), rng.randint(-14, 14)))
    for y0 in (h // 5, h * 3 // 5):                                    # fileiras de vagas
        for x in range(30, w - 30, 46):
            s.fill((210, 210, 200), (x, y0, 2, 50))
        s.fill((210, 210, 200), (30, y0 + 50, w - 60, 2))
    s.fill((226, 190, 50), (0, h // 2 - 10, w, 3))                    # faixa amarela do meio
    for x in range(10, w, 40):
        s.fill((236, 236, 226), (x, h // 2 + 6, 20, 2))
    for _ in range(26):                                               # óleo
        x, y = rng.randrange(w), rng.randrange(h)
        pygame.draw.ellipse(s, _shade((34, 34, 42), rng.randint(-6, 6)), (x, y, rng.randint(10, 22), rng.randint(5, 10)))
    for _ in range(10):
        x, y = rng.randrange(w), rng.randrange(h)
        _tape(s, rng, x, y, rng.randint(30, 80), vertical=rng.random() < 0.3)
    for _ in range(6):
        _crate(s, rng.randrange(4, w - 16), rng.randrange(4, h - 12))
    _vignette(s, (20, 20, 24), 40)


def _lag_cobertura(s, rng):
    """Cobertura: placas de concreto, o H do heliponto no meio e ralos."""
    w, h = s.get_size()
    tile = 40
    for gy in range(0, h, tile):
        for gx in range(0, w, tile):
            c = _shade((112, 116, 120), rng.randint(-6, 6))
            s.fill(c, (gx, gy, tile, tile))
            s.fill(_shade(c, -20), (gx, gy, tile, 1))
            s.fill(_shade(c, -20), (gx, gy, 1, tile))
    for _ in range(w * h // 10):
        s.set_at((rng.randrange(w), rng.randrange(h)), rng.choice(((124, 128, 132), (100, 104, 108))))
    cx, cy = w // 2, h // 2
    pygame.draw.circle(s, (70, 74, 80), (cx, cy), 120)                # heliponto
    pygame.draw.circle(s, (232, 200, 60), (cx, cy), 120, 4)
    pygame.draw.circle(s, (232, 232, 226), (cx, cy), 104, 2)
    s.fill((232, 232, 226), (cx - 36, cy - 44, 12, 88))
    s.fill((232, 232, 226), (cx + 24, cy - 44, 12, 88))
    s.fill((232, 232, 226), (cx - 24, cy - 6, 48, 12))
    for _ in range(8):                                                # ralos e manchas de chuva
        x, y = rng.randrange(10, w - 10), rng.randrange(10, h - 10)
        s.fill((60, 62, 66), (x, y, 8, 8))
        for k in range(1, 8, 2):
            s.fill((140, 144, 150), (x + k, y + 1, 1, 6))
    for _ in range(18):
        x, y = rng.randrange(w), rng.randrange(h)
        pygame.draw.ellipse(s, (96, 100, 106), (x, y, rng.randint(20, 50), rng.randint(8, 18)))
    _vignette(s, (40, 44, 52), 36)


_PAINTERS = {"floresta": _floresta, "calabouco": _calabouco, "templo_gelado": _templo,
             "lag_escritorio": _lag_escritorio, "lag_datacenter": _lag_datacenter, "lag_garagem": _lag_garagem,
             "lag_cobertura": _lag_cobertura}
THEMED_MAPS = tuple(_PAINTERS)


# ─────────────────────────────────────────────
#  Paredes
# ─────────────────────────────────────────────
class _Style:
    """Parede temática. ``below``: quanto o desenho passa da base (sombra, pingentes)."""

    below = 6

    def __init__(self, key):
        self.key = key

    def render(self, w, h, seed):
        cache_key = (self.key, w, h, seed)
        if cache_key not in _WALLS:
            surf = pygame.Surface((w, h + self.below), pygame.SRCALPHA)
            self.paint(surf, w, h, random.Random(f"{self.key}:{seed}"))
            _WALLS[cache_key] = surf
        return _WALLS[cache_key]

    def paint(self, surf, w, h, rng):
        raise NotImplementedError


def _px(surf, x, y, color, n=1):
    surf.fill(color, (x * U, y * U, U * n, U))


class Hedge(_Style):
    """Floresta: cerca viva. Em cima a copa iluminada, na frente as folhas na sombra."""

    def paint(self, s, w, h, rng):
        s.fill((10, 20, 10, 200), (0, 6, w, h))                         # sombra no chão
        top_c, front_c, edge = (44, 84, 40), (24, 50, 26), (14, 30, 16)
        light, lighter, deep = (62, 108, 50), (84, 132, 62), (18, 40, 20)
        front = max(8, min(h // 2, 16))                                  # altura da "frente" da cerca
        pygame.draw.rect(s, edge, (0, 0, w, h), border_radius=6)
        pygame.draw.rect(s, top_c, (2, 2, w - 4, h - front - 2), border_radius=5)
        s.fill(front_c, (2, h - front, w - 4, front - 2))
        gw, gh = w // U, h // U
        split = (h - front) // U
        for _ in range(gw * gh // 4):                                    # tufos de folhas (2x2)
            x, y = rng.randrange(1, max(2, gw - 2)), rng.randrange(1, max(2, gh - 2))
            if y < split:
                c = lighter if rng.random() < 0.35 else light
            else:
                c = rng.choice((deep, _shade(front_c, 10)))
            _px(s, x, y, c)
            if rng.random() < 0.5:
                _px(s, x + 1, y, _shade(c, -10))
            if rng.random() < 0.3 and y + 1 < gh - 1:
                _px(s, x, y + 1, _shade(c, -16))
        for x in range(1, gw - 1, 3):                                    # copa recortada em cima
            _px(s, x, 0, edge, 2)
            _px(s, x, 1, lighter if rng.random() < 0.5 else light, 2)
        s.fill(_shade(top_c, -14), (2, h - front - 2, w - 4, 2))         # dobra entre copa e frente
        for _ in range(max(1, gw * gh // 260)):                          # algumas frutinhas
            _px(s, rng.randrange(2, max(3, gw - 2)), rng.randrange(1, max(2, split)), (206, 54, 64))


class DungeonStone(_Style):
    """Calabouço: tijolos de tamanhos variados, musgo escorrendo e rachaduras."""

    def paint(self, s, w, h, rng):
        s.fill((12, 6, 4, 220), (0, 6, w, h))
        mortar = (30, 14, 10)
        s.fill(mortar, (0, 0, w, h))
        row = 12
        for y in range(0, h, row):
            x = -rng.randint(0, 14)
            while x < w:
                bw = rng.randint(14, 26)
                c = _shade((96, 50, 38), rng.randint(-14, 10))
                rect = pygame.Rect(x + 1, y + 1, bw - 2, row - 2).clip(pygame.Rect(0, 0, w, h))
                if rect.w > 0 and rect.h > 0:
                    s.fill(c, rect)
                    s.fill(_shade(c, 22), (rect.x, rect.y, rect.w, 1))
                    s.fill(_shade(c, -22), (rect.x, rect.bottom - 1, rect.w, 1))
                x += bw
        s.fill((140, 80, 60), (0, 0, w, 2))                              # beirada de cima
        for _ in range(max(1, w // 40)):                                 # musgo escorrendo
            x = rng.randrange(0, max(1, w - 4))
            for k in range(rng.randint(3, 9)):
                s.fill((56, 78, 36), (x + rng.randint(-2, 2), 2 + k * 2, 3, 2))
        for _ in range(max(1, w * h // 4000)):                           # rachaduras
            x, y = rng.randrange(w), rng.randrange(h)
            for _ in range(4):
                nx, ny = x + rng.randint(-4, 4), y + rng.randint(1, 5)
                pygame.draw.line(s, (24, 10, 8), (x, y), (nx, ny))
                x, y = nx, ny
        pygame.draw.rect(s, (20, 8, 6), (0, 0, w, h), 1)


class IceBlock(_Style):
    """Templo Gelado: blocos de gelo com neve em cima e pingentes embaixo."""

    below = 14

    def paint(self, s, w, h, rng):
        s.fill((10, 18, 30, 200), (0, 6, w, h))
        top, bottom = (150, 196, 230), (82, 122, 168)
        for y in range(h):
            s.fill(_mix(top, bottom, y / max(1, h - 1)), (0, y, w, 1))
        for _ in range(max(1, (w + h) // 18)):                            # brilhos diagonais
            x, y = rng.randrange(w), rng.randrange(h)
            for i in range(rng.randint(4, 10)):
                if 0 <= x + i < w and 0 <= y - i < h:
                    s.set_at((x + i, y - i), (214, 236, 250))
        for _ in range(max(1, w * h // 900)):                            # bolhas presas no gelo
            s.fill((180, 214, 240), (rng.randrange(w), rng.randrange(h), 2, 2))
        pygame.draw.rect(s, (54, 84, 120), (0, 0, w, h), 2)
        # neve em cima, com a borda de baixo irregular
        s.fill((236, 244, 250), (0, 0, w, 4))
        for x in range(0, w, U):
            s.fill((236, 244, 250), (x, 4, U, U * rng.randint(0, 2)))
        s.fill((255, 255, 255), (0, 0, w, 1))
        # pingentes de gelo
        for x in range(rng.randint(2, 8), w - 3, rng.randint(9, 15)):
            length = rng.randint(4, 12)
            for i in range(length):
                width = max(1, 3 - i * 3 // length)
                s.fill((200, 230, 250), (x + (3 - width) // 2, h + i, width, 1))


class GlassWall(_Style):
    """Escritório: divisória de vidro azulado com moldura branca e a faixa ciano da Lag Lobby."""

    def paint(self, s, w, h, rng):
        s.fill((20, 26, 36, 140), (0, 6, w, h))
        frame, glass = (226, 230, 236), (120, 170, 200, 170)
        s.fill(glass, (0, 0, w, h))
        for _ in range(max(1, (w + h) // 30)):                           # reflexo no vidro
            x = rng.randrange(w)
            for i in range(min(h, 12)):
                if 0 <= x + i < w:
                    s.set_at((x + i, i), (210, 236, 250, 200))
        pygame.draw.rect(s, frame, (0, 0, w, h), 2)
        s.fill(frame, (0, 0, w, 3))
        if w >= h:
            s.fill(LAG_CYAN, (2, h // 2, w - 4, 2))
            for x in range(40, w - 10, 60):                              # montantes
                s.fill(frame, (x, 0, 2, h))
        else:
            s.fill(LAG_CYAN, (w // 2, 2, 2, h - 4))
            for y in range(40, h - 10, 60):
                s.fill(frame, (0, y, w, 2))
        if rng.random() < 0.3:                                           # fita de isolamento na frente
            for x in range(0, w, 6):
                s.fill(TAPE[(x // 6) % 2], (x, h - 6, 6, 3))


class ServerRack(_Style):
    """Data center: racks de servidor pretos, com as fileiras de LEDs (o ambiente faz piscar)."""

    def paint(self, s, w, h, rng):
        s.fill((6, 8, 12, 220), (0, 6, w, h))
        s.fill((28, 30, 38), (0, 0, w, h))
        s.fill((60, 64, 76), (0, 0, w, 3))
        pygame.draw.rect(s, (14, 16, 20), (0, 0, w, h), 2)
        unit = 10
        for y in range(6, h - 4, unit):
            s.fill((40, 44, 54), (4, y, w - 8, unit - 2))
            s.fill((22, 24, 30), (4, y + unit - 3, w - 8, 1))
            for x in range(8, w - 8, 8):
                s.fill(rng.choice(((40, 200, 120), (40, 160, 230), (60, 70, 80))), (x, y + 3, 2, 2))


class Barrier(_Style):
    """Estacionamento e cobertura: barreira de concreto com faixas amarelas e pretas."""

    def paint(self, s, w, h, rng):
        s.fill((14, 14, 18, 200), (0, 6, w, h))
        top, front = (176, 176, 170), (140, 140, 134)
        front_h = max(8, min(h // 2, 16))
        s.fill(top, (0, 0, w, h - front_h))
        s.fill(front, (0, h - front_h, w, front_h))
        s.fill((206, 206, 200), (0, 0, w, 2))
        for x in range(-front_h, w, 14):                                 # listras de aviso na frente
            for i in range(front_h):
                xx = x + i
                if 0 <= xx < w and (x // 14) % 2 == 0:
                    s.fill((226, 186, 40), (xx, h - front_h + i, 7, 1))
        for _ in range(max(1, w * h // 900)):
            s.set_at((rng.randrange(w), rng.randrange(max(1, h - front_h))), (150, 150, 146))
        pygame.draw.rect(s, (70, 70, 70), (0, 0, w, h), 1)


_STYLES = {"floresta": Hedge, "calabouco": DungeonStone, "templo_gelado": IceBlock,
           "lag_escritorio": GlassWall, "lag_datacenter": ServerRack, "lag_garagem": Barrier, "lag_cobertura": Barrier}


def wall_style(key):
    cls = _STYLES.get(key)
    return cls(key) if cls else None


# ─────────────────────────────────────────────
#  Ambiente animado
# ─────────────────────────────────────────────
def _glow(radius, color, strength):
    """Brilho redondo para somar na tela (luz da tocha, vaga-lume)."""
    surf = pygame.Surface((radius * 2, radius * 2))
    for r in range(radius, 0, -2):
        k = (1 - r / radius) ** 1.6 * strength
        pygame.draw.circle(surf, tuple(min(255, int(c * k)) for c in color), (radius, radius), r)
    return surf


class Ambience:
    """Efeitos leves que se mexem por cima do cenário. layer: "ground" (logo depois das
    paredes) ou "air" (por cima de todo mundo)."""

    def draw(self, view, cam, frame, layer):
        pass


class Fireflies(Ambience):
    COUNT = 40

    def __init__(self, size):
        rng = random.Random("vaga-lumes")
        w, h = size
        self.flies = [(rng.uniform(60, w - 60), rng.uniform(60, h - 60), rng.uniform(20, 70),
                       rng.uniform(0.006, 0.016), rng.uniform(0, math.tau), rng.uniform(0.03, 0.07))
                      for _ in range(self.COUNT)]
        self.glow = [_glow(10, (190, 240, 120), s) for s in (0.35, 0.7, 1.0)]

    def draw(self, view, cam, frame, layer):
        if layer != "air":
            return
        vw, vh = view.get_size()
        for hx, hy, r, speed, phase, blink in self.flies:
            light = 0.5 + 0.5 * math.sin(frame * blink + phase)
            if light < 0.25:
                continue
            x = hx + math.sin(frame * speed + phase) * r - cam.x
            y = hy + math.cos(frame * speed * 1.3 + phase) * r * 0.6 - cam.y
            if -12 < x < vw + 12 and -12 < y < vh + 12:
                g = self.glow[min(2, int(light * 3))]
                view.blit(g, (round(x) - 10, round(y) - 10), special_flags=pygame.BLEND_ADD)
                view.fill((236, 255, 180), (round(x), round(y), 2, 2))


class Torches(Ambience):
    """Tochas presas nas paredes, com a chama e a luz tremendo."""

    def __init__(self, walls):
        self.torches = []
        rng = random.Random("tochas")
        for wall in walls:
            r = wall.rect
            if not wall.visible:
                continue
            if r.w >= 150 and r.h <= 40:                              # parede deitada: tocha no meio
                for x in range(r.x + 100, r.right - 60, 400) if r.w > 600 else (r.centerx,):
                    self.torches.append((x, r.y + 2, rng.uniform(0, math.tau)))
            elif r.h >= 150 and r.w <= 40:                            # parede em pé: tocha na ponta
                self.torches.append((r.centerx, r.y + 14, rng.uniform(0, math.tau)))
        self.glow = [_glow(80, (255, 150, 60), s) for s in (0.28, 0.36, 0.44)]

    def draw(self, view, cam, frame, layer):
        if layer != "ground":
            return
        vw, vh = view.get_size()
        for wx, wy, phase in self.torches:
            x, y = wx - cam.x, wy - cam.y
            if not (-90 < x < vw + 90 and -90 < y < vh + 90):
                continue
            flicker = math.sin(frame * 0.21 + phase) + math.sin(frame * 0.53 + phase * 2) * 0.5
            g = self.glow[0 if flicker < -0.4 else 1 if flicker < 0.6 else 2]
            view.blit(g, (round(x) - 80, round(y) - 70), special_flags=pygame.BLEND_ADD)
            x, y = round(x), round(y)
            view.fill((40, 30, 28), (x - 3, y + 6, 6, 4))                # suporte de ferro
            view.fill((84, 56, 34), (x - 1, y - 2, 2, 9))                # cabo
            tall = 6 + round(flicker * 2)
            view.fill((210, 70, 30), (x - 3, y - 2 - tall, 6, tall))
            view.fill((250, 170, 60), (x - 2, y - tall, 4, tall - 2))
            view.fill((255, 240, 170), (x - 1, y - 3, 2, 2))


class Snow(Ambience):
    """Neve caindo devagar (sempre a mesma quantidade na tela, onde quer que a câmera esteja)."""

    COUNT = 70

    def __init__(self):
        rng = random.Random("neve")
        self.flakes = [(rng.uniform(0, 1), rng.uniform(0, 1), rng.uniform(0.35, 0.9), rng.uniform(0, math.tau),
                        rng.choice((1, 2, 2))) for _ in range(self.COUNT)]

    def draw(self, view, cam, frame, layer):
        if layer != "air":
            return
        vw, vh = view.get_size()
        for fx, fy, speed, phase, size in self.flakes:
            y = (fy * (vh + 20) + frame * speed) % (vh + 20) - 10
            x = (fx * vw + math.sin(frame * 0.02 + phase) * 14) % vw
            view.fill((230, 240, 250) if size == 2 else (190, 210, 230), (round(x), round(y), size, size))


class ServerLights(Ambience):
    """LEDs dos racks piscando e, de vez em quando, a luz vermelha de emergência girando."""

    def __init__(self, walls, emergency=True):
        rng = random.Random("leds")
        self.leds = []
        for wall in walls:
            r = wall.rect
            if not wall.visible or r.w > 900 or r.h > 900:
                continue
            for _ in range(max(2, (r.w * r.h) // 1400)):
                self.leds.append((rng.uniform(r.x + 6, r.right - 6), rng.uniform(r.y + 6, r.bottom - 6),
                                  rng.uniform(0.05, 0.2), rng.uniform(0, math.tau),
                                  rng.choice(((60, 255, 150), (80, 200, 255), (255, 80, 70)))))
        self.emergency = emergency
        self.glow = _glow(140, (255, 40, 30), 0.35)

    def draw(self, view, cam, frame, layer):
        if layer == "ground":
            vw, vh = view.get_size()
            for x, y, speed, phase, color in self.leds:
                if math.sin(frame * speed + phase) < 0.2:
                    continue
                sx, sy = x - cam.x, y - cam.y
                if 0 < sx < vw and 0 < sy < vh:
                    view.fill(color, (round(sx), round(sy), 2, 2))
        elif layer == "air" and self.emergency:
            # luz de emergência girando: um clarão vermelho que passa pela tela
            t = (frame % 240) / 240
            if t < 0.5:
                vw, vh = view.get_size()
                x = round(-140 + (vw + 280) * (t / 0.5))
                view.blit(self.glow, (x - 140, vh // 3 - 140), special_flags=pygame.BLEND_ADD)


class Papers(Ambience):
    """Cobertura: folhas e papéis voando devagar pela tela."""

    COUNT = 24

    def __init__(self):
        rng = random.Random("papel")
        self.bits = [(rng.uniform(0, 1), rng.uniform(0, 1), rng.uniform(0.6, 1.6), rng.uniform(0, math.tau))
                     for _ in range(self.COUNT)]

    def draw(self, view, cam, frame, layer):
        if layer != "air":
            return
        vw, vh = view.get_size()
        for fx, fy, speed, phase in self.bits:
            x = (fx * (vw + 40) + frame * speed) % (vw + 40) - 20
            y = (fy * vh + math.sin(frame * 0.04 + phase) * 16) % vh
            color = (236, 236, 228) if speed > 1 else (190, 196, 200)
            view.fill(color, (round(x), round(y), 3, 2))


def create_ambience(key, size, walls):
    if key == "floresta":
        return Fireflies(size)
    if key == "calabouco":
        return Torches(walls)
    if key == "templo_gelado":
        return Snow()
    if key in ("lag_escritorio", "lag_datacenter"):
        return ServerLights(walls, emergency=True)
    if key == "lag_cobertura":
        return Papers()
    return Ambience()
