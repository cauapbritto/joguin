"""Cenário dos mapas que não têm arte própria (Floresta, Calabouço, Templo Gelado, a Lag Lobby e a
Clínica Clepalovers e a Mansão do Carimbo).

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
        # dobra arredondando os degraus (Scale2x): trilha, poça e pedra ficam com borda curva, no
        # mesmo dobro de detalhe dos personagens; depois um grão fino de 1 pixel tira o chapado
        big = pygame.transform.scale2x(small) if U == 2 else pygame.transform.scale(small, size)
        if big.get_size() != tuple(size):
            big = big.subsurface((0, 0, min(big.get_width(), size[0]), min(big.get_height(), size[1]))).copy()
            if big.get_size() != tuple(size):
                big = pygame.transform.scale(big, size)
        _grain(big, random.Random(f"grão:{key}"))
        _FLOORS[key] = big
    return _FLOORS[key]          # só é lido (a miniatura faz a própria cópia)


def _grain(surf, rng, density=60):
    """Grão fino no chão: um pixel em cada ``density`` um tom acima ou abaixo do que está lá."""
    w, h = surf.get_size()
    get, put = surf.get_at, surf.set_at
    for _ in range(w * h // density):
        x, y = rng.randrange(w), rng.randrange(h)
        r, g, b, _a = get((x, y))
        if r + g + b < 40:                       # o escuro de fora das salas fica liso
            continue
        k = 7 if rng.random() < 0.5 else -8
        put((x, y), (max(0, min(255, r + k)), max(0, min(255, g + k)), max(0, min(255, b + k))))


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


# ── Clínica Clepalovers (capítulo 3): porcelanato branco, rosa da marca e dourado ──
CLEPA = (255, 110, 190)
CLEPA_D = (184, 56, 128)
CLEPA_L = (255, 192, 226)
GOLD = (226, 186, 92)
CACO = (170, 90, 230)


def _heart(s, x, y, color, size=1):
    """Coraçãozinho da Clepalovers (o logo) em pixels."""
    for dx, dy in ((0, 0), (2, 0), (-1, 1), (0, 1), (1, 1), (2, 1), (3, 1), (0, 2), (1, 2), (2, 2), (1, 3)):
        s.fill(color, (x + dx * size, y + dy * size, size, size))


def _veins(s, rng, count, color=CACO):
    """Veios roxos do caco correndo pelo chão (a corrupção vazando das máquinas)."""
    w, h = s.get_size()
    for _ in range(count):
        x, y = rng.randrange(w), rng.randrange(h)
        for _ in range(rng.randint(8, 18)):
            nx, ny = x + rng.randint(-4, 4), y + rng.randint(-4, 4)
            pygame.draw.line(s, color, (x, y), (nx, ny))
            x, y = nx, ny


def _clinica(s, rng):
    """Recepção e consultórios: porcelanato branco polido em placas grandes, passadeira rosa,
    o coração da marca no chão, marcas de rodinha e os veios roxos do caco."""
    w, h = s.get_size()
    tile = 32
    for gy in range(0, h, tile):
        for gx in range(0, w, tile):
            c = _shade((232, 228, 232), rng.randint(-4, 4))
            s.fill(c, (gx, gy, tile, tile))
            s.fill(_shade(c, -26), (gx, gy, tile, 1))
            s.fill(_shade(c, -26), (gx, gy, 1, tile))
            if rng.random() < 0.25:                                   # brilho do piso encerado
                for i in range(8):
                    s.set_at((gx + 6 + i, gy + 20 - i), (252, 250, 252))
    for _ in range(max(1, w * h // 90000)):                           # passadeiras rosa
        cw, ch = rng.randint(70, 160), rng.randint(22, 34)
        if rng.random() < 0.5:
            cw, ch = ch, cw
        x, y = rng.randrange(0, max(1, w - cw)), rng.randrange(0, max(1, h - ch))
        rug = (246, 222, 236)
        s.fill(rug, (x, y, cw, ch))
        pygame.draw.rect(s, (238, 196, 220), (x, y, cw, ch), 1)
        pygame.draw.rect(s, (250, 236, 244), (x + 3, y + 3, cw - 6, ch - 6), 1)
        for _ in range(cw * ch // 40):
            s.set_at((x + rng.randrange(cw), y + rng.randrange(ch)), _shade(rug, rng.randint(-8, 3)))
    for _ in range(max(2, w * h // 70000)):                           # logo no chão
        _heart(s, rng.randrange(10, w - 20), rng.randrange(10, h - 20), CLEPA_L, 3)
    for _ in range(16):                                               # marcas de rodinha de maca
        x, y = rng.randrange(w), rng.randrange(h)
        length = rng.randint(30, 90)
        horizontal = rng.random() < 0.5
        for k in (0, 6):
            if horizontal:
                s.fill((206, 200, 208), (x, y + k, length, 1))
            else:
                s.fill((206, 200, 208), (x + k, y, 1, length))
    _veins(s, rng, 7)
    _vignette(s, (170, 120, 160), 26)


def _clinica_spa(s, rng):
    """Spa e sauna: deck de madeira clara em réguas, pedrinhas brancas nas bordas, toalhas
    dobradas e pétalas rosa caídas."""
    w, h = s.get_size()
    plank = 12
    for gy in range(0, h, plank):
        offset = rng.randrange(0, 60)
        c0 = _shade((176, 132, 92), rng.randint(-8, 8))
        s.fill(c0, (0, gy, w, plank))
        s.fill(_shade(c0, 20), (0, gy, w, 1))
        s.fill(_shade(c0, -34), (0, gy + plank - 1, w, 1))
        for x in range(-offset, w, rng.randint(70, 110)):             # emendas das réguas
            s.fill(_shade(c0, -40), (x, gy, 1, plank))
        for _ in range(w // 30):                                      # veio da madeira
            x = rng.randrange(w)
            s.fill(_shade(c0, -12), (x, gy + rng.randint(3, plank - 4), rng.randint(6, 18), 1))
    for _ in range(max(2, w * h // 60000)):                           # canteiros de pedrinha branca
        cx, cy = rng.randrange(20, w - 20), rng.randrange(20, h - 20)
        r = rng.randint(14, 26)
        pygame.draw.ellipse(s, (120, 116, 110), (cx - r, cy - r // 2, r * 2, r))
        for _ in range(r * 3):
            px, py = cx + rng.randint(-r + 2, r - 2), cy + rng.randint(-r // 2 + 2, r // 2 - 2)
            s.fill(rng.choice(((236, 234, 228), (210, 206, 200), (250, 248, 244))), (px, py, 2, 2))
        s.fill((80, 140, 70), (cx - 2, cy - 4, 3, 4))                 # bambuzinho
    for _ in range(10):                                               # toalhas dobradas
        x, y = rng.randrange(4, w - 20), rng.randrange(4, h - 14)
        s.fill((240, 238, 234), (x, y, 16, 9))
        s.fill(CLEPA_L, (x, y + 3, 16, 2))
        s.fill((200, 196, 196), (x, y + 8, 16, 1))
    for _ in range(60):                                               # pétalas
        x, y = rng.randrange(w), rng.randrange(h)
        s.fill(rng.choice((CLEPA, CLEPA_L, (250, 230, 240))), (x, y, 2, 1))
    for _ in range(6):                                                # poças de água
        x, y = rng.randrange(w), rng.randrange(h)
        pygame.draw.ellipse(s, (150, 120, 96), (x, y, rng.randint(20, 40), rng.randint(8, 14)))
    _veins(s, rng, 4)
    _vignette(s, (60, 40, 30), 30)


def _clinica_vip(s, rng):
    """Suíte VIP e sala dos espelhos: mármore escuro com veios rosados e as frisas douradas."""
    w, h = s.get_size()
    tile = 40
    for gy in range(0, h, tile):
        for gx in range(0, w, tile):
            c = _shade((52, 40, 56), rng.randint(-4, 4))
            s.fill(c, (gx, gy, tile, tile))
            s.fill(GOLD if (gx // tile + gy // tile) % 4 == 0 else _shade(c, -16), (gx, gy, tile, 1))
            s.fill(_shade(c, -16), (gx, gy, 1, tile))
    for _ in range(w * h // 900):                                     # veios do mármore
        x, y = rng.randrange(w), rng.randrange(h)
        color = rng.choice(((120, 90, 120), (150, 110, 140), (86, 66, 92)))
        for _ in range(rng.randint(3, 8)):
            nx, ny = x + rng.randint(-1, 4), y + rng.randint(-2, 2)
            pygame.draw.line(s, color, (x, y), (nx, ny))
            x, y = nx, ny
    cx, cy = w // 2, h // 2                                           # rosa dos ventos dourada no meio
    pygame.draw.circle(s, GOLD, (cx, cy), 48, 2)
    pygame.draw.circle(s, (120, 90, 50), (cx, cy), 44, 1)
    _heart(s, cx - 12, cy - 12, CLEPA_D, 6)
    for _ in range(40):                                               # glitter caído
        s.fill(rng.choice((GOLD, CLEPA_L, (255, 255, 255))), (rng.randrange(w), rng.randrange(h), 1, 1))
    _veins(s, rng, 6, (190, 110, 240))
    _vignette(s, (14, 8, 18), 40)


def _clinica_adm(s, rng):
    """Administrativo: carpete de escritório cinza-azulado, folhas espalhadas, boletos, post-its
    rosa e carimbos de PAGO no chão."""
    w, h = s.get_size()
    s.fill((96, 102, 118))
    for _ in range(w * h // 3):
        s.set_at((rng.randrange(w), rng.randrange(h)), _shade((96, 102, 118), rng.randint(-10, 10)))
    for gy in range(0, h, 48):                                        # placas do carpete
        s.fill((86, 92, 108), (0, gy, w, 1))
    for gx in range(0, w, 48):
        s.fill((86, 92, 108), (gx, 0, 1, h))
    for _ in range(w * h // 9000):                                    # papéis
        x, y = rng.randrange(w - 12), rng.randrange(h - 14)
        s.fill((70, 70, 84), (x + 1, y + 1, 10, 13))
        s.fill((240, 238, 230), (x, y, 10, 13))
        for k in range(2, 12, 2):
            s.fill((180, 180, 190), (x + 2, y + k, rng.randint(3, 7), 1))
        if rng.random() < 0.3:                                        # carimbo de PAGO
            pygame.draw.rect(s, (220, 60, 70), (x + 1, y + 4, 8, 5), 1)
    for _ in range(30):                                               # post-its
        s.fill(rng.choice((CLEPA_L, (255, 236, 120), (170, 230, 200))), (rng.randrange(w), rng.randrange(h), 4, 4))
    for _ in range(8):                                                # grampos e clipes
        x, y = rng.randrange(w), rng.randrange(h)
        s.fill((200, 204, 214), (x, y, 3, 1))
    _veins(s, rng, 9, (190, 110, 240))
    _vignette(s, (30, 30, 40), 34)


def _clinica_calcada(s, rng):
    """Calçada da fachada: pedra portuguesa em ondas preto e branco, o meio-fio e as vagas."""
    w, h = s.get_size()
    for y in range(h):
        for x in range(0, w, 2):
            wave = math.sin(x * 0.05 + math.sin(y * 0.03) * 2) * 10
            dark = (y + wave) % 56 < 7
            base = (150, 146, 152) if dark else (226, 224, 218)
            s.fill(_shade(base, rng.randint(-10, 10)), (x, y, 2, 1))
    for y in range(0, h, 3):                                          # rejunte das pedrinhas
        for x in range((y // 3) % 2 * 2, w, 4):
            if rng.random() < 0.35:
                s.set_at((x, y), (120, 118, 116))
    s.fill((150, 150, 146), (0, h - 22, w, 4))                        # meio-fio e o asfalto
    s.fill((56, 58, 62), (0, h - 18, w, 18))
    for x in range(10, w, 40):
        s.fill((236, 236, 226), (x, h - 9, 20, 2))
    for _ in range(14):                                               # pétalas e panfletos
        x, y = rng.randrange(w), rng.randrange(h - 30)
        s.fill(CLEPA_L, (x, y, 6, 4))
        _heart(s, x + 1, y, CLEPA, 1)
    _veins(s, rng, 4)
    _vignette(s, (30, 26, 34), 30)


# ── Mansão do Carimbo (capítulo 4): o palácio exagerado do órgão, em Cuiabrasa, a 47°C ──
IARA_C = (60, 230, 255)            # ciano da IARA (a corrupção deste capítulo)
IARA_CD = (20, 130, 170)
WINE = (150, 30, 44)               # tapete vermelho
WINE_D = (104, 18, 30)
REPART = (150, 168, 132)           # verde-repartição


def _wires(s, rng, count, color=IARA_C):
    """Cabos de rede ciano correndo pelo chão em ângulo reto (a IARA se espalhando pelo prédio)."""
    w, h = s.get_size()
    for _ in range(count):
        x, y = rng.randrange(w), rng.randrange(h)
        for _ in range(rng.randint(3, 6)):
            if rng.random() < 0.5:
                nx = max(0, min(w - 1, x + rng.randint(-60, 60)))
                pygame.draw.line(s, color, (x, y), (nx, y))
                x = nx
            else:
                ny = max(0, min(h - 1, y + rng.randint(-60, 60)))
                pygame.draw.line(s, color, (x, y), (x, ny))
                y = ny
        s.fill(_shade(color, 60), (x - 1, y - 1, 3, 3))               # conector na ponta


def _red_carpet(s, x, y, cw, ch):
    """Tapete vermelho com borda dourada."""
    s.fill(WINE, (x, y, cw, ch))
    pygame.draw.rect(s, GOLD, (x, y, cw, ch), 1)
    pygame.draw.rect(s, WINE_D, (x + 2, y + 2, cw - 4, ch - 4), 1)


def _sheet(s, rng, x, y):
    """Folha de papel caída, às vezes com o carimbo de INDEFERIDO."""
    s.fill((70, 66, 70), (x + 1, y + 1, 8, 10))
    s.fill((240, 238, 228), (x, y, 8, 10))
    for k in range(2, 9, 2):
        s.fill((178, 178, 186), (x + 1, y + k, rng.randint(3, 6), 1))
    if rng.random() < 0.35:
        pygame.draw.rect(s, (210, 50, 56), (x + 1, y + 3, 6, 4), 1)


def _mansao(s, rng):
    """Hall da Mansão do Carimbo: mármore em xadrez creme e verde-repartição, tapete vermelho de
    borda dourada até os guichês, papéis no chão e os cabos ciano da IARA."""
    w, h = s.get_size()
    tile = 24
    for gy in range(0, h, tile):
        for gx in range(0, w, tile):
            base = (232, 224, 204) if (gx // tile + gy // tile) % 2 == 0 else _shade(REPART, 10)
            c = _shade(base, rng.randint(-4, 4))
            s.fill(c, (gx, gy, tile, tile))
            s.fill(_shade(c, -22), (gx, gy, tile, 1))
            s.fill(_shade(c, -22), (gx, gy, 1, tile))
            if rng.random() < 0.3:                                    # veio do mármore
                x, y = gx + rng.randrange(tile), gy + rng.randrange(tile)
                for _ in range(rng.randint(3, 6)):
                    nx, ny = x + rng.randint(-1, 3), y + rng.randint(-2, 2)
                    pygame.draw.line(s, _shade(c, -16), (x, y), (nx, ny))
                    x, y = nx, ny
    cw = max(40, w // 8)                                              # passadeira vermelha no meio
    _red_carpet(s, w // 2 - cw // 2, 10, cw, h - 20)
    for _ in range(max(1, w * h // 120000)):                          # capachos dourados
        x, y = rng.randrange(10, max(11, w - 40)), rng.randrange(10, max(11, h - 20))
        s.fill((176, 140, 70), (x, y, 30, 14))
        pygame.draw.rect(s, (120, 90, 40), (x, y, 30, 14), 1)
    for _ in range(w * h // 14000):
        _sheet(s, rng, rng.randrange(w - 10), rng.randrange(h - 12))
    for _ in range(max(2, w * h // 60000)):                           # senhas de papel no chão
        x, y = rng.randrange(w - 6), rng.randrange(h - 4)
        s.fill((250, 240, 170), (x, y, 5, 3))
    _wires(s, rng, 5)
    _vignette(s, (60, 50, 30), 28)


def _mansao_arquivo(s, rng):
    """Arquivo geral: taco de madeira velho em espinha de peixe, caixas de processo, poeira e
    papel por todo lado."""
    w, h = s.get_size()
    s.fill((120, 82, 50))
    bw, bh = 12, 4
    for gy in range(0, h + bh, bh * 2):
        for gx in range(-bw, w + bw, bw):
            off = (gy // (bh * 2)) % 2 * (bw // 2)
            c = _shade((134, 92, 56), rng.randint(-14, 10))
            s.fill(c, (gx + off, gy, bw - 1, bh - 1))
            c2 = _shade((122, 84, 50), rng.randint(-14, 10))
            s.fill(c2, (gx + off + bw // 2, gy + bh, bw - 1, bh - 1))
    for _ in range(w * h // 9000):
        _sheet(s, rng, rng.randrange(w - 10), rng.randrange(h - 12))
    for _ in range(max(3, w * h // 50000)):                           # caixas-arquivo no chão
        x, y = rng.randrange(w - 16), rng.randrange(h - 12)
        s.fill((60, 40, 26), (x + 1, y + 1, 14, 10))
        s.fill((196, 160, 104), (x, y, 14, 10))
        s.fill((226, 196, 140), (x, y, 14, 2))
        s.fill((240, 238, 228), (x + 4, y + 4, 6, 3))
    for _ in range(w * h // 300):                                     # poeira
        s.set_at((rng.randrange(w), rng.randrange(h)), (150, 118, 86))
    _wires(s, rng, 4)
    _vignette(s, (40, 26, 16), 34)


def _mansao_patio(s, rng):
    """Pátio a 47°C: asfalto rachado que tremula de calor, vagas pintadas, grama seca amarela
    nos canteiros e um tuiuiú pintado na vaga do diretor."""
    w, h = s.get_size()
    s.fill((92, 88, 86))
    for _ in range(w * h // 3):
        s.set_at((rng.randrange(w), rng.randrange(h)), _shade((92, 88, 86), rng.randint(-12, 12)))
    for gy in range(40, h - 40, 160):                                 # fileiras de vagas
        for gx in range(20, w - 20, 50):
            s.fill((236, 230, 210), (gx, gy, 2, 50))
        s.fill((236, 230, 210), (20, gy + 50, w - 40, 2))
    for _ in range(max(3, w * h // 40000)):                           # rachaduras do sol
        x, y = rng.randrange(w), rng.randrange(h)
        for _ in range(rng.randint(5, 12)):
            nx, ny = x + rng.randint(-5, 5), y + rng.randint(-5, 5)
            pygame.draw.line(s, (60, 58, 58), (x, y), (nx, ny))
            x, y = nx, ny
    for _ in range(max(2, w * h // 70000)):                           # canteiros de grama seca
        x, y = rng.randrange(10, w - 70), rng.randrange(10, h - 40)
        cw, ch = rng.randint(40, 70), rng.randint(18, 30)
        s.fill((170, 160, 150), (x - 2, y - 2, cw + 4, ch + 4))
        s.fill((176, 156, 70), (x, y, cw, ch))
        for _ in range(cw * ch // 6):
            s.set_at((x + rng.randrange(cw), y + rng.randrange(ch)),
                     rng.choice(((200, 180, 90), (150, 130, 60), (120, 140, 60))))
    for _ in range(max(2, w * h // 90000)):                           # manchas de óleo
        _blob(s, rng, rng.randrange(w), rng.randrange(h), 6, (66, 62, 64))
    for y in range(0, h, 12):                                         # ondas de calor (claras)
        for x in range(0, w, 4):
            if math.sin(x * 0.06 + y * 0.9) > 0.94:
                s.fill((122, 116, 112), (x, y, 3, 1))
    _wires(s, rng, 3)
    _vignette(s, (120, 70, 20), 34)


def _mansao_cpd(s, rng):
    """CPD na antiga adega do porão: piso elevado de CPD em placas por cima do tijolo da adega.
    Faltam placas aqui e ali (aparece o tijolo e o ninho de cabos), e tem mancha de vinho velho."""
    w, h = s.get_size()
    tile = 24
    for gy in range(0, h, tile):
        for gx in range(0, w, tile):
            if rng.random() < 0.07:                                   # placa levantada: tijolo e cabos
                for by in range(gy, gy + tile, 6):
                    off = (by // 6) % 2 * 6
                    for bx in range(gx - 12, gx + tile, 12):
                        r = pygame.Rect(bx + off, by, 11, 5).clip((gx, gy, tile, tile))
                        if r.w > 0:
                            s.fill(_shade((96, 54, 40), rng.randint(-12, 8)), r)
                for _ in range(3):
                    y = gy + rng.randrange(3, tile - 3)
                    s.fill(rng.choice((IARA_C, IARA_CD, (230, 200, 60))), (gx, y, tile, 1))
                continue
            c = _shade((148, 152, 160), rng.randint(-6, 6))
            s.fill((40, 40, 48), (gx, gy, tile, tile))
            s.fill(c, (gx + 1, gy + 1, tile - 2, tile - 2))
            s.fill(_shade(c, 18), (gx + 1, gy + 1, tile - 2, 1))
            s.fill(_shade(c, -20), (gx + 1, gy + tile - 2, tile - 2, 1))
            if rng.random() < 0.2:                                    # placa perfurada (ventilação)
                for py in range(gy + 5, gy + tile - 4, 3):
                    for px in range(gx + 5, gx + tile - 4, 3):
                        s.set_at((px, py), (96, 100, 110))
    for _ in range(max(2, w * h // 60000)):                           # mancha de vinho
        _blob(s, rng, rng.randrange(w), rng.randrange(h), 7, (110, 50, 64))
    _wires(s, rng, 12)
    _vignette(s, (6, 10, 16), 46)


def _mansao_reuniao(s, rng):
    """Sala de reunião do comitê: carpete vinho com losangos dourados, copinhos de café e as
    folhas da pauta que ninguém leu."""
    w, h = s.get_size()
    s.fill((96, 36, 44))
    for _ in range(w * h // 3):
        s.set_at((rng.randrange(w), rng.randrange(h)), _shade((96, 36, 44), rng.randint(-8, 8)))
    step = 28
    for gy in range(0, h, step):
        for gx in range((gy // step) % 2 * step // 2, w, step):
            pts = [(gx, gy - 4), (gx + 4, gy), (gx, gy + 4), (gx - 4, gy)]
            pygame.draw.polygon(s, (150, 112, 60), pts, 1)
    for _ in range(w * h // 16000):
        _sheet(s, rng, rng.randrange(w - 10), rng.randrange(h - 12))
    for _ in range(14):                                               # copinhos de café
        x, y = rng.randrange(w - 4), rng.randrange(h - 4)
        s.fill((244, 244, 240), (x, y, 3, 3))
        s.set_at((x + 1, y + 1), (110, 70, 40))
    _wires(s, rng, 6)
    _vignette(s, (30, 8, 12), 38)


def _mansao_nucleo(s, rng):
    """Núcleo da IARA (o último andar): o mármore preto do gabinete tomado por trilhas de
    circuito ciano que correm como um rio até o trono do carimbo."""
    w, h = s.get_size()
    tile = 40
    for gy in range(0, h, tile):
        for gx in range(0, w, tile):
            c = _shade((26, 28, 38), rng.randint(-3, 3))
            s.fill(c, (gx, gy, tile, tile))
            s.fill(GOLD if (gx // tile + gy // tile) % 5 == 0 else _shade(c, -10), (gx, gy, tile, 1))
            s.fill(_shade(c, -10), (gx, gy, 1, tile))
    for _ in range(w * h // 1400):                                    # veios do mármore
        x, y = rng.randrange(w), rng.randrange(h)
        for _ in range(rng.randint(3, 7)):
            nx, ny = x + rng.randint(-1, 4), y + rng.randint(-2, 2)
            pygame.draw.line(s, (50, 54, 70), (x, y), (nx, ny))
            x, y = nx, ny
    for k in range(7):                                                # o "rio" de dados de cima a baixo
        x = w // 2 + int(math.sin(k * 1.7) * w * 0.35)
        y = 0
        while y < h:
            ny = y + rng.randint(10, 30)
            nx = max(4, min(w - 4, x + rng.choice((-12, 0, 0, 12))))
            pygame.draw.line(s, IARA_CD, (x, y), (x, ny))
            pygame.draw.line(s, IARA_CD, (x, ny), (nx, ny))
            if rng.random() < 0.3:
                s.fill(IARA_C, (x - 1, ny - 1, 3, 3))
            x, y = nx, ny
    cx, cy = w // 2, h // 2                                           # selo do carimbo no meio
    pygame.draw.circle(s, GOLD, (cx, cy), 40, 2)
    pygame.draw.circle(s, IARA_CD, (cx, cy), 34, 1)
    s.fill(GOLD, (cx - 10, cy - 6, 20, 4))
    s.fill(GOLD, (cx - 3, cy - 16, 6, 10))
    s.fill(GOLD, (cx - 6, cy - 22, 12, 6))
    _vignette(s, (2, 10, 16), 46)


def _mansao_jardim(s, rng):
    """Jardim da fachada: grama torrada de sol, caminho de pedra até a porta, a estátua do
    carimbo dourado no meio e um ipê amarelo soltando flor."""
    w, h = s.get_size()
    for y in range(0, h, 2):
        for x in range(0, w, 2):
            s.fill(_shade((150, 150, 70), rng.randint(-14, 10)), (x, y, 2, 2))
    for _ in range(w * h // 80):                                      # tufos secos
        s.set_at((rng.randrange(w), rng.randrange(h)), rng.choice(((190, 170, 80), (110, 120, 50))))
    pw = 46                                                           # caminho de pedra
    for y in range(0, h, 10):
        for x in range(w // 2 - pw, w // 2 + pw, 14):
            c = _shade((190, 182, 168), rng.randint(-14, 10))
            s.fill(c, (x + (y // 10) % 2 * 7, y, 12, 8))
    cx, cy = w // 2, h // 2                                           # estátua do carimbo dourado
    pygame.draw.circle(s, (170, 166, 156), (cx, cy), 26)
    pygame.draw.circle(s, (120, 116, 110), (cx, cy), 26, 1)
    s.fill(GOLD, (cx - 12, cy + 2, 24, 6))
    s.fill(_shade(GOLD, -40), (cx - 12, cy + 7, 24, 2))
    s.fill(GOLD, (cx - 4, cy - 10, 8, 12))
    s.fill(GOLD, (cx - 7, cy - 18, 14, 8))
    s.fill((252, 228, 150), (cx - 6, cy - 18, 4, 2))
    for _ in range(max(2, w * h // 60000)):                           # ipês com flor amarela caída
        x, y = rng.randrange(20, w - 20), rng.randrange(20, h - 20)
        for _ in range(40):
            s.fill(rng.choice(((250, 210, 40), (236, 180, 30))), (x + rng.randint(-14, 14), y + rng.randint(-8, 8), 2, 2))
    _wires(s, rng, 2)
    _vignette(s, (120, 80, 20), 30)


_PAINTERS = {"floresta": _floresta, "calabouco": _calabouco, "templo_gelado": _templo,
             "lag_escritorio": _lag_escritorio, "lag_datacenter": _lag_datacenter, "lag_garagem": _lag_garagem,
             "lag_cobertura": _lag_cobertura,
             "clinica": _clinica, "clinica_spa": _clinica_spa, "clinica_vip": _clinica_vip,
             "clinica_adm": _clinica_adm, "clinica_calcada": _clinica_calcada,
             "mansao": _mansao, "mansao_arquivo": _mansao_arquivo, "mansao_patio": _mansao_patio,
             "mansao_cpd": _mansao_cpd, "mansao_reuniao": _mansao_reuniao, "mansao_nucleo": _mansao_nucleo,
             "mansao_jardim": _mansao_jardim}
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
            _solidify(surf, w, h, random.Random(f"sólido:{self.key}:{seed}"))
            _WALLS[cache_key] = surf
        return _WALLS[cache_key]

    def paint(self, surf, w, h, rng):
        raise NotImplementedError


def _solidify(s, w, h, rng):
    """Acabamento de toda parede, no mesmo dobro de detalhe dos personagens: contorno fino de 1
    pixel (mais escuro que a cor que está ali), luz na beirada de cima e da esquerda, sombra na
    direita e no pé da parede, e um grão de 1 pixel para tirar o chapado."""
    full = s.get_size()
    solid = pygame.mask.from_surface(s, 250)            # a sombra no chão é translúcida e fica de fora
    if not solid.count():
        return
    hole = solid.copy()
    hole.invert()
    edge = pygame.mask.Mask(full)
    for off in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        edge.draw(hole, off)                            # vizinho vazio...
    border = pygame.mask.Mask(full, fill=True)
    border.erase(pygame.mask.Mask((full[0] - 2, full[1] - 2), fill=True), (1, 1))
    edge.draw(border, (0, 0))                           # ...ou a borda da folha
    edge = edge.overlap_mask(solid, (0, 0))
    lit = pygame.Surface(full, pygame.SRCALPHA)         # luz de cima e da esquerda, sombra embaixo
    lit.fill((255, 255, 255, 0))
    lit.fill((255, 255, 255, 255), (0, 0, full[0], 1))
    band = max(U * 3, min(h // 4, U * 6))
    for i in range(band):                               # pé da parede escurece aos poucos
        k = round(255 - 46 * (i + 1) / band)
        lit.fill((k, k, k, 255), (0, h - band + i, w, 1))
    lit.fill((222, 222, 222, 255), (w - U, 0, U, h))    # lado direito na sombra
    s.blit(lit, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
    s.fill((26, 22, 14), (1, 1, w - 2, U), special_flags=pygame.BLEND_RGB_ADD)
    s.fill((12, 10, 6), (1, 1, U, h - 2), special_flags=pygame.BLEND_RGB_ADD)
    line = edge.to_surface(setcolor=(150, 146, 158, 255), unsetcolor=(255, 255, 255, 255))
    s.blit(line, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
    get, put = s.get_at, s.set_at
    for _ in range(w * h // 45):
        x, y = rng.randrange(w), rng.randrange(h)
        if not solid.get_at((x, y)):
            continue
        r, g, b, a = get((x, y))
        k = 8 if rng.random() < 0.5 else -9
        put((x, y), (max(0, min(255, r + k)), max(0, min(255, g + k)), max(0, min(255, b + k)), a))


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


class ClinicWall(_Style):
    """Clínica: parede branca de painel liso, rodapé e faixa rosa da marca, frisos dourados."""

    def paint(self, s, w, h, rng):
        s.fill((40, 20, 40, 120), (0, 6, w, h))
        s.fill((244, 240, 244), (0, 0, w, h))
        s.fill((255, 255, 255), (0, 0, w, 3))
        s.fill((214, 206, 216), (0, h - 3, w, 3))
        if w >= h:
            s.fill(CLEPA, (0, h // 2 - 2, w, 4))
            s.fill(GOLD, (0, h // 2 + 2, w, 1))
            for x in range(30, w - 10, 70):                              # painéis
                s.fill((222, 214, 224), (x, 0, 1, h))
            if w > 120 and rng.random() < 0.5:                           # quadrinho de antes e depois
                x = rng.randrange(10, w - 40)
                s.fill(GOLD, (x, 4, 28, min(14, h - 8)))
                s.fill((240, 220, 200), (x + 2, 6, 11, min(10, h - 12)))
                s.fill((90, 50, 120), (x + 15, 6, 11, min(10, h - 12)))
        else:
            s.fill(CLEPA, (w // 2 - 2, 0, 4, h))
            s.fill(GOLD, (w // 2 + 2, 0, 1, h))
            for y in range(30, h - 10, 70):
                s.fill((222, 214, 224), (0, y, w, 1))
        pygame.draw.rect(s, (190, 180, 194), (0, 0, w, h), 1)


class SpaWall(_Style):
    """Spa: painel de ripas de madeira escura com bambus e uma vela acesa de vez em quando."""

    def paint(self, s, w, h, rng):
        s.fill((20, 10, 6, 140), (0, 6, w, h))
        s.fill((96, 62, 40), (0, 0, w, h))
        if w >= h:
            for x in range(0, w, 6):
                s.fill(_shade((110, 72, 46), rng.randint(-10, 10)), (x, 0, 5, h))
            s.fill((140, 98, 64), (0, 0, w, 3))
            for x in range(rng.randrange(10, 40), w - 10, rng.randint(60, 120)):
                s.fill((110, 170, 90), (x, 2, 3, h - 4))                 # bambu
                for y in range(4, h - 4, 10):
                    s.fill((80, 130, 64), (x, y, 3, 1))
        else:
            for y in range(0, h, 6):
                s.fill(_shade((110, 72, 46), rng.randint(-10, 10)), (0, y, w, 5))
            s.fill((140, 98, 64), (0, 0, 3, h))
        pygame.draw.rect(s, (54, 34, 22), (0, 0, w, h), 2)


class MirrorWall(_Style):
    """Sala dos espelhos e suíte VIP: espelhos em moldura dourada, com o reflexo azulado."""

    def paint(self, s, w, h, rng):
        s.fill((10, 4, 14, 160), (0, 6, w, h))
        s.fill(GOLD, (0, 0, w, h))
        s.fill((252, 228, 150), (0, 0, w, 2))
        s.fill((160, 120, 50), (0, h - 2, w, 2))
        inner = pygame.Rect(3, 3, w - 6, h - 6)
        if inner.w > 2 and inner.h > 2:
            s.fill((150, 170, 196), inner)
            for _ in range(max(1, (w + h) // 26)):                       # reflexos inclinados
                x = rng.randrange(inner.x, inner.right)
                for i in range(min(inner.h, 18)):
                    if inner.x <= x + i < inner.right and inner.y + i < inner.bottom:
                        s.set_at((x + i, inner.y + i), (226, 236, 250))
            if w >= h:
                for x in range(40, w - 10, 50):
                    s.fill(GOLD, (x, 0, 2, h))
            else:
                for y in range(40, h - 10, 50):
                    s.fill(GOLD, (0, y, w, 2))


class FileCabinet(_Style):
    """Administrativo: arquivos de aço cinza com as gavetas etiquetadas e pastas saindo."""

    def paint(self, s, w, h, rng):
        s.fill((10, 10, 16, 150), (0, 6, w, h))
        s.fill((150, 156, 168), (0, 0, w, h))
        s.fill((196, 202, 214), (0, 0, w, 3))
        drawer = 18
        if w >= h:
            for x in range(2, w - drawer + 2, drawer + 2):
                s.fill((128, 134, 148), (x, 4, drawer, h - 8))
                s.fill((236, 236, 228), (x + 5, 6, 8, 3))                # etiqueta
                s.fill((70, 74, 86), (x + 6, h // 2, 6, 2))              # puxador
                if rng.random() < 0.25:
                    s.fill(rng.choice((CLEPA_L, (255, 236, 120))), (x + 2, 2, 4, 6))   # pasta saindo
        else:
            for y in range(4, h - drawer + 2, drawer + 2):
                s.fill((128, 134, 148), (2, y, w - 4, drawer))
                s.fill((236, 236, 228), (w // 2 - 4, y + 3, 8, 3))
                s.fill((70, 74, 86), (w // 2 - 3, y + drawer // 2 + 2, 6, 2))
        pygame.draw.rect(s, (80, 84, 96), (0, 0, w, h), 1)


class MansionWall(_Style):
    """Mansão do Carimbo: parede creme com lambri de madeira embaixo, frisos dourados, quadros
    do Pantanal (tuiuiú, jacaré, pôr do sol) e o retrato de um carimbo."""

    def paint(self, s, w, h, rng):
        s.fill((30, 20, 10, 130), (0, 6, w, h))
        if 300 <= w <= 360 and 40 <= h <= 50:                            # guichê de atendimento
            s.fill((120, 76, 44), (0, 0, w, h))
            s.fill((150, 100, 60), (0, 0, w, 6))
            s.fill(GOLD, (0, 6, w, 2))
            for k, x in enumerate(range(16, w - 60, 110)):
                s.fill((180, 210, 220), (x, 10, 70, h - 18))             # vidro do guichê
                s.fill((220, 236, 244), (x + 4, 12, 10, 2))
                s.fill((30, 30, 36), (x + 25, h - 10, 20, 6))           # a fresta do papel
                s.fill((250, 250, 240), (x + 26, 1, 18, 4))              # plaquinha "GUICHÊ"
                s.fill((200, 40, 40) if rng.random() < 0.6 else (40, 160, 90), (x + 47, 1, 4, 4))
            pygame.draw.rect(s, (70, 44, 24), (0, 0, w, h), 1)
            return
        s.fill((236, 226, 200), (0, 0, w, h))
        s.fill((250, 244, 226), (0, 0, w, 3))
        if w >= h:
            wain = max(6, h // 2)
            s.fill((120, 76, 44), (0, h - wain, w, wain))                # lambri
            s.fill(GOLD, (0, h - wain, w, 2))
            for x in range(10, w - 6, 24):
                s.fill((96, 60, 34), (x, h - wain + 4, 1, wain - 6))
            if w > 110 and h >= 30 and rng.random() < 0.7:               # quadro do Pantanal
                qx = rng.randrange(10, w - 40)
                qh = min(14, h - wain - 6)
                if qh >= 8:
                    s.fill(GOLD, (qx, 4, 30, qh))
                    s.fill((250, 170, 80), (qx + 2, 6, 26, qh - 4))        # pôr do sol
                    s.fill((60, 120, 70), (qx + 2, 6 + (qh - 4) // 2, 26, (qh - 4) // 2 + 1))
                    s.fill((30, 30, 36), (qx + 14, 7, 2, qh - 6))         # tuiuiú
                    s.fill((210, 50, 50), (qx + 14, 9, 2, 1))
        else:
            s.fill((120, 76, 44), (0, 0, max(4, w // 3), h))
            s.fill(GOLD, (max(4, w // 3), 0, 2, h))
            for y in range(30, h - 10, 60):
                s.fill((214, 202, 172), (0, y, w, 1))
        pygame.draw.rect(s, (150, 120, 70), (0, 0, w, h), 1)


class ShelfWall(_Style):
    """Arquivo geral: estante de aço lotada de pastas de processo coloridas, caixas-arquivo e
    etiquetas com os números."""

    def paint(self, s, w, h, rng):
        s.fill((10, 8, 6, 150), (0, 6, w, h))
        s.fill((120, 126, 136), (0, 0, w, h))
        s.fill((170, 176, 186), (0, 0, w, 2))
        colors = ((226, 192, 120), (120, 170, 214), (226, 120, 110), (240, 210, 100), (150, 200, 140))
        if w >= h:
            shelf = 10
            for y in range(3, h - 3, shelf):
                x = 2
                while x < w - 4:
                    if rng.random() < 0.12:                              # caixa-arquivo deitada
                        bw = 12
                        s.fill((196, 160, 104), (x, y, bw, shelf - 2))
                        s.fill((240, 238, 228), (x + 3, y + 2, 5, 3))
                    else:
                        bw = rng.randint(2, 4)
                        s.fill(rng.choice(colors), (x, y + rng.randint(0, 2), bw, shelf - 2))
                    x += bw + 1
                s.fill((80, 84, 94), (0, y + shelf - 2, w, 2))           # prateleira
        else:
            for y in range(2, h - 4, 5):
                s.fill(rng.choice(colors), (2, y, w - 4, 4))
                s.fill((80, 84, 94), (2, y + 4, w - 4, 1))
        pygame.draw.rect(s, (60, 64, 72), (0, 0, w, h), 1)


CAR_COLORS = ((236, 236, 232), (180, 30, 40), (40, 60, 120), (60, 60, 66), (200, 200, 206))


class PatioWall(_Style):
    """Pátio: mureta de concreto quente com jardineira de cacto. Os blocos de 120x60 (ou 60x120)
    são carros estacionados (o oficial é branco com a faixa do órgão)."""

    def paint(self, s, w, h, rng):
        s.fill((20, 14, 10, 170), (0, 6, w, h))
        if (w, h) in ((120, 60), (60, 120)):
            body = rng.choice(CAR_COLORS)
            pygame.draw.rect(s, body, (0, 0, w, h), border_radius=10)
            pygame.draw.rect(s, _shade(body, -60), (0, 0, w, h), 2, border_radius=10)
            glass = (120, 160, 190)
            if w > h:
                s.fill(glass, (28, 6, 18, h - 12))
                s.fill(glass, (w - 34, 8, 12, h - 16))
                s.fill(_shade(body, 30), (50, 8, w - 90, h - 16))         # teto
                s.fill((250, 230, 120), (w - 4, 6, 3, 8))                 # faróis
                s.fill((250, 230, 120), (w - 4, h - 14, 3, 8))
                if body == CAR_COLORS[0]:
                    s.fill((60, 120, 90), (4, h // 2 - 2, w - 8, 4))      # faixa do órgão
            else:
                s.fill(glass, (6, 28, w - 12, 18))
                s.fill(glass, (8, h - 34, w - 16, 12))
                s.fill(_shade(body, 30), (8, 50, w - 16, h - 90))
                s.fill((250, 230, 120), (6, h - 4, 8, 3))
                s.fill((250, 230, 120), (w - 14, h - 4, 8, 3))
            return
        top, front = (196, 188, 176), (160, 152, 140)
        front_h = max(8, min(h // 2, 16))
        s.fill(top, (0, 0, w, h - front_h))
        s.fill(front, (0, h - front_h, w, front_h))
        s.fill((226, 220, 208), (0, 0, w, 2))
        if w >= h and h - front_h > 8:                                   # jardineira com cacto e terra
            s.fill((120, 80, 50), (3, 3, w - 6, h - front_h - 6))
            for x in range(8, w - 8, rng.randint(18, 30)):
                s.fill((80, 140, 70), (x, 2, 3, h - front_h - 6))
                s.fill((80, 140, 70), (x - 2, 5, 2, 3))
        pygame.draw.rect(s, (110, 104, 96), (0, 0, w, h), 1)


class CellarRack(_Style):
    """CPD na adega: racks de servidor velhos encaixados nas prateleiras de vinho. Os LEDs
    piscam (ambiente) e os barris de carvalho ainda estão no fundo."""

    def paint(self, s, w, h, rng):
        s.fill((6, 8, 12, 220), (0, 6, w, h))
        s.fill((60, 36, 24), (0, 0, w, h))                               # madeira da adega
        s.fill((96, 60, 40), (0, 0, w, 3))
        pygame.draw.rect(s, (30, 18, 12), (0, 0, w, h), 2)
        if w >= h:
            unit = 12
            for y in range(5, h - 4, unit):
                for x in range(4, w - 4, 26):
                    if rng.random() < 0.25:                              # barril (fundo redondo)
                        pygame.draw.circle(s, (120, 74, 40), (x + 10, y + 5), 5)
                        pygame.draw.circle(s, (70, 70, 76), (x + 10, y + 5), 5, 1)
                    else:                                                # servidor
                        s.fill((32, 34, 42), (x, y, 22, unit - 2))
                        s.fill((60, 64, 76), (x, y, 22, 1))
                        for lx in range(x + 3, x + 20, 5):
                            s.fill(rng.choice((IARA_C, (40, 200, 120), (60, 70, 80))), (lx, y + 4, 2, 2))
        else:
            for y in range(6, h - 6, 10):
                s.fill((32, 34, 42), (4, y, w - 8, 8))
                s.fill(IARA_C if rng.random() < 0.5 else (40, 200, 120), (6, y + 3, 2, 2))
        for _ in range(max(1, w // 60)):                                 # cabo ciano descendo
            x = rng.randrange(2, max(3, w - 2))
            s.fill(IARA_CD, (x, 0, 1, h))


class BoardroomWall(_Style):
    """Sala de reunião: lambri de madeira nobre com a tela do projetor. O bloco do meio da sala é
    a mesa de reunião comprida, com as cadeiras de couro em volta e as garrafinhas d'água."""

    def paint(self, s, w, h, rng):
        s.fill((10, 4, 4, 160), (0, 6, w, h))
        if w >= 300 and h >= 60:                                         # a mesa do comitê
            pygame.draw.rect(s, (30, 20, 16), (-6, -6, w + 12, h + 12), border_radius=14)
            pygame.draw.rect(s, (110, 64, 36), (0, 0, w, h), border_radius=12)
            pygame.draw.rect(s, (140, 88, 52), (4, 4, w - 8, h - 8), 2, border_radius=10)
            for x in range(30, w - 20, 50):                              # garrafinhas e pastas da pauta
                s.fill((200, 230, 250), (x, 10, 3, 6))
                s.fill((240, 238, 228), (x + 8, h - 18, 10, 8))
            s.fill((30, 32, 40), (w // 2 - 14, h // 2 - 6, 28, 12))       # o viva-voz
            s.fill(IARA_C, (w // 2 - 2, h // 2 - 2, 4, 4))
            return
        s.fill((96, 56, 32), (0, 0, w, h))
        s.fill((140, 90, 56), (0, 0, w, 3))
        if w >= h:
            for x in range(0, w, 30):
                s.fill((80, 46, 26), (x, 3, 1, h - 3))
                s.fill((110, 66, 40), (x + 4, 6, 22, h - 12))
            if 300 <= w <= 500 and h >= 24:                              # tela de projeção
                sx = w // 2 - 50
                s.fill((236, 236, 240), (sx, 4, 100, h - 8))
                pygame.draw.circle(s, (220, 60, 70), (sx + 30, 4 + (h - 8) // 2), min(8, (h - 8) // 2))
                s.fill((60, 160, 220), (sx + 55, 8, 8, h - 16))
                s.fill((240, 200, 80), (sx + 66, 12, 8, h - 20))
        else:
            for y in range(0, h, 30):
                s.fill((80, 46, 26), (3, y, w - 3, 1))
        pygame.draw.rect(s, (50, 28, 16), (0, 0, w, h), 1)


class CoreWall(_Style):
    """Núcleo da IARA: colunas de mármore preto com frisos dourados, enroladas nos cabos ciano.
    O bloco largo de cima é o trono do carimbo, onde mora o servidor da IARA."""

    def paint(self, s, w, h, rng):
        s.fill((0, 10, 16, 180), (0, 6, w, h))
        if w >= 240 and h >= 40:                                         # trono com o carimbo gigante
            s.fill((40, 30, 20), (0, 0, w, h))
            s.fill(GOLD, (0, 0, w, h - 10))
            s.fill((252, 228, 150), (0, 0, w, 3))
            s.fill((30, 32, 42), (20, 6, w - 40, h - 20))
            for x in range(26, w - 26, 8):
                s.fill(rng.choice((IARA_C, IARA_CD, (40, 200, 120))), (x, 10, 3, 3))
            s.fill(WINE, (w // 2 - 22, h - 10, 44, 10))                  # o assento
            s.fill((150, 96, 54), (w // 2 - 4, -2, 8, 8))                # cabo do carimbo por cima
            return
        s.fill((34, 36, 48), (0, 0, w, h))
        s.fill((70, 74, 92), (0, 0, w, 3))
        s.fill(GOLD, (0, 3, w, 2))
        s.fill(GOLD, (0, h - 5, w, 2))
        if w >= h:
            for x in range(0, w, 14):
                s.fill((50, 54, 70), (x, 6, 1, h - 12))
        else:
            for y in range(0, h, 14):
                s.fill((50, 54, 70), (2, y, w - 4, 1))
        for k in range(max(1, (w + h) // 40)):                           # cabos enrolados
            x = rng.randrange(0, max(1, w))
            for y in range(0, h, 2):
                xx = (x + y // 2) % max(1, w)
                s.set_at((xx, y), IARA_C if (y // 2) % 3 else IARA_CD)
        pygame.draw.rect(s, (14, 16, 22), (0, 0, w, h), 1)


class GardenWall(_Style):
    """Jardim da fachada: muro da mansão em reboco creme com grade de ferro preta e lanças
    douradas em cima, e uma touceira de capim ressecado no pé."""

    def paint(self, s, w, h, rng):
        s.fill((20, 14, 6, 140), (0, 6, w, h))
        s.fill((226, 212, 180), (0, 0, w, h))
        s.fill((240, 230, 206), (0, 0, w, 3))
        if w >= h:
            for x in range(2, w - 2, 6):
                s.fill((30, 30, 34), (x, 2, 2, max(2, h // 2)))
                s.fill(GOLD, (x, 0, 2, 2))
        else:
            for y in range(2, h - 2, 6):
                s.fill((30, 30, 34), (2, y, max(2, w // 2), 2))
        pygame.draw.rect(s, (160, 140, 100), (0, 0, w, h), 1)


_STYLES = {"floresta": Hedge, "calabouco": DungeonStone, "templo_gelado": IceBlock,
           "lag_escritorio": GlassWall, "lag_datacenter": ServerRack, "lag_garagem": Barrier, "lag_cobertura": Barrier,
           "clinica": ClinicWall, "clinica_spa": SpaWall, "clinica_vip": MirrorWall, "clinica_adm": FileCabinet,
           "clinica_calcada": ClinicWall,
           "mansao": MansionWall, "mansao_arquivo": ShelfWall, "mansao_patio": PatioWall, "mansao_cpd": CellarRack,
           "mansao_reuniao": BoardroomWall, "mansao_nucleo": CoreWall, "mansao_jardim": GardenWall}


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


class Sparkles(Ambience):
    """Clínica: brilhinhos rosa e dourados piscando pelo ar (o glitter da Clepalovers)."""

    COUNT = 34

    def __init__(self, colors=((255, 192, 226), (252, 228, 150), (255, 255, 255))):
        rng = random.Random("glitter")
        self.bits = [(rng.uniform(0, 1), rng.uniform(0, 1), rng.uniform(0.02, 0.06), rng.uniform(0, math.tau),
                      rng.choice(colors)) for _ in range(self.COUNT)]

    def draw(self, view, cam, frame, layer):
        if layer != "air":
            return
        vw, vh = view.get_size()
        for fx, fy, speed, phase, color in self.bits:
            light = math.sin(frame * speed + phase)
            if light < 0.55:
                continue
            x = round((fx * vw + frame * 0.15) % vw)
            y = round((fy * vh - frame * 0.25) % vh)
            view.fill(color, (x, y, 2, 2))
            if light > 0.9:                                           # cruzinha do brilho
                view.fill(color, (x - 2, y + 1, 1, 1))
                view.fill(color, (x + 3, y + 1, 1, 1))
                view.fill(color, (x + 1, y - 2, 1, 1))
                view.fill(color, (x + 1, y + 3, 1, 1))


class Steam(Ambience):
    """Spa: fiapos de vapor subindo devagar (o vapor de verdade, que tapa a visão, é o perigo)."""

    COUNT = 18

    def __init__(self):
        rng = random.Random("vapor")
        self.puffs = [(rng.uniform(0, 1), rng.uniform(0, 1), rng.uniform(0.3, 0.7), rng.randint(10, 22))
                      for _ in range(self.COUNT)]
        self.cache = {}

    def _puff(self, r):
        if r not in self.cache:
            s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            for k in range(r, 0, -2):
                pygame.draw.circle(s, (240, 240, 246, round(30 * (1 - k / r)) + 6), (r, r), k)
            self.cache[r] = s
        return self.cache[r]

    def draw(self, view, cam, frame, layer):
        if layer != "air":
            return
        vw, vh = view.get_size()
        for fx, fy, speed, r in self.puffs:
            x = (fx * vw + math.sin(frame * 0.01 + fy * 6) * 30) % vw
            y = (fy * (vh + 60) - frame * speed) % (vh + 60) - 30
            view.blit(self._puff(r), (round(x) - r, round(y) - r))


class HeatHaze(Ambience):
    """Pátio a 47°C: o ar tremulando de calor (faixas claras que sobem e ondulam devagar)."""

    def __init__(self):
        rng = random.Random("calor")
        self.bands = [(rng.uniform(0, 1), rng.uniform(0.2, 0.5), rng.uniform(0, math.tau)) for _ in range(9)]
        self.cache = {}

    def _band(self, w):
        if w not in self.cache:
            s = pygame.Surface((w, 6), pygame.SRCALPHA)
            for y, a in ((0, 10), (1, 18), (2, 24), (3, 18), (4, 10)):
                s.fill((255, 236, 200, a), (0, y, w, 1))
            self.cache[w] = s
        return self.cache[w]

    def draw(self, view, cam, frame, layer):
        if layer != "air":
            return
        vw, vh = view.get_size()
        band = self._band(vw)
        for fy, speed, phase in self.bands:
            y = (fy * (vh + 40) - frame * speed) % (vh + 40) - 20
            x = round(math.sin(frame * 0.03 + phase) * 6)
            view.blit(band, (x, round(y)))


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
    if key in ("clinica", "clinica_vip", "clinica_calcada"):
        return Sparkles()
    if key == "clinica_spa":
        return Steam()
    if key == "clinica_adm":
        return Papers()
    if key in ("mansao", "mansao_arquivo", "mansao_reuniao"):
        return Papers()
    if key == "mansao_cpd":
        return ServerLights(walls, emergency=False)
    if key == "mansao_nucleo":
        return Sparkles(colors=((60, 230, 255), (200, 250, 255), (252, 228, 150)))
    if key in ("mansao_patio", "mansao_jardim"):
        return HeatHaze()
    return Ambience()
