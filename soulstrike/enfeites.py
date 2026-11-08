"""Enfeites da sala inicial e do corredor de cada capítulo (etapa 4 do hub).

Os enfeites vão sozinhos para os cantos: encostados nas paredes, longe das portas, da fogueira, do
baú e das bancas, um a cada poucos quadrados e nunca no meio do caminho (do outro lado sempre sobram
três quadrados livres). Os de parede (tocha, painel, quadro) não ocupam o chão. Cada corredor tem uma
placa com uma piada perto de onde o grupo chega.

Cada capítulo tem o seu jogo de peças:

* 1, a trilha: tochas, barris, caixotes, cogumelos e troncos;
* 2, a Lag Lobby: painel de rede, racks de servidor, cones com fita zebrada, bobinas de cabo e bebedouro;
* 3, a Clepalovers: quadros, cadeiras de espera, plantas, bebedouro e carrinho;
* 4, a Mansão do Carimbo: retratos de moldura dourada, pilhas de papel, arquivos, bustos e vasos."""
import math

import pygame

from . import casa_art as art
from . import lobbies, theme
from .casa_art import METAL, METAL_D, WOOD, WOOD_D, WOOD_L, box, glow, shade, shadow

T = lobbies.TILE
NEAR_MARKER = 2          # quadrados livres em volta de baú, fogueira, bancas e largada
NEAR_GATE = 3            # e em volta das portas
FREE_AHEAD = 3           # quadrados livres do lado de lá do enfeite (o caminho)
GAP = 3                  # distância mínima entre dois enfeites
MAX_FLOOR = 12
MAX_WALL = 6
WALL_GAP = 5             # peças de parede mais espaçadas (senão vira fileira)


# ─────────────────────────────────────────────
#  Onde vão
# ─────────────────────────────────────────────
def spots(rows):
    """Lugares dos enfeites no desenho ``rows`` (como em lobbies): ``(chão, parede)``.

    ``chão``: lista de ``(coluna, linha, lado)``, com o lado da parede em que o enfeite encosta
    (``"l"``, ``"r"``, ``"u"`` ou ``"d"``). ``parede``: ``(coluna, linha)`` do chão logo abaixo de
    uma parede de cima, onde a peça fica pendurada. Linhas e colunas já contam as linhas de folga do
    alto (as mesmas do mapa)."""
    grid = lobbies.grid_of(rows)
    h, w = len(grid), len(grid[0])

    def at(x, y):
        return grid[y][x] if 0 <= y < h and 0 <= x < w else " "

    def floor(x, y):
        return at(x, y) not in "# "

    keep = set()
    for y in range(h):
        for x in range(w):
            ch = grid[y][x]
            if ch in lobbies.MARKERS:
                r = NEAR_GATE if ch in "12" else NEAR_MARKER
                keep.update((x + dx, y + dy) for dx in range(-r, r + 1) for dy in range(-r, r + 1))

    def far(x, y, chosen):
        return all(max(abs(x - a), abs(y - b)) >= GAP for a, b, *_ in chosen)

    ground, wall = [], []
    free = [(x, y) for y in range(h) for x in range(w)
            if floor(x, y) and (x, y) not in keep and grid[y][x] not in lobbies.MARKERS]
    for x, y in free:
        flat = all(at(x + d, y - 1) == "#" and at(x + d, y - 2) in "# " for d in (-1, 0, 1))
        if flat and len(wall) < MAX_WALL and all(max(abs(x - a), abs(y - b)) >= WALL_GAP for a, b in wall):
            wall.append((x, y))
    for x, y in free:
        if any(max(abs(x - a), abs(y - b)) < 2 for a, b in wall):
            continue                       # nada embaixo da tocha (ou do quadro)
        for side, (dx, dy) in (("u", (0, -1)), ("d", (0, 1)), ("l", (-1, 0)), ("r", (1, 0))):
            if at(x + dx, y + dy) != "#":
                continue
            ahead = [(x - dx * k, y - dy * k) for k in range(1, FREE_AHEAD + 1)]
            # o caminho do outro lado e os vizinhos de lado ficam livres (nada de fechar passagem)
            sides = [(x + dy, y + dx), (x - dy, y - dx)]
            if all(floor(a, b) for a, b in ahead + sides) and len(ground) < MAX_FLOOR and far(x, y, ground):
                ground.append((x, y, side))
            break
    return ground, wall


def blocked_cells(rows):
    """Quadrados de chão que os enfeites ocupam (para conferir que nada fica sem saída)."""
    ground, _ = spots(rows)
    return {(x, y) for x, y, _ in ground}


# ─────────────────────────────────────────────
#  Peças
# ─────────────────────────────────────────────
def torch(s, x, y):
    """Tocha presa na parede (x, y = pé da parede)."""
    glow(s, (x, y - 30), (90, 70), (255, 170, 70), 50)
    glow(s, (x, y - 30), (44, 36), (255, 200, 110), 70)
    box(s, METAL_D, x - 6, y - 14, 12, 4)
    box(s, WOOD_D, x - 3, y - 26, 6, 14)
    box(s, WOOD, x - 2, y - 26, 2, 14)
    pygame.draw.polygon(s, (240, 120, 40), [(x - 6, y - 26), (x + 6, y - 26), (x + 2, y - 42), (x - 1, y - 36)])
    pygame.draw.polygon(s, (255, 210, 90), [(x - 3, y - 26), (x + 3, y - 26), (x, y - 36)])


def barrel(s, x, y):
    shadow(s, x, y + 2, 30)
    box(s, (110, 70, 40), x - 13, y - 30, 26, 32)
    for bx, c in ((-13, (90, 56, 32)), (-6, (126, 82, 48)), (2, (126, 82, 48)), (9, (98, 62, 36))):
        box(s, c, x + bx, y - 30, 4, 32)
    for by in (-26, -6):
        box(s, METAL_D, x - 14, y + by, 28, 3)
    pygame.draw.ellipse(s, (140, 96, 58), (x - 13, y - 34, 26, 8))
    pygame.draw.ellipse(s, (100, 64, 36), (x - 9, y - 32, 18, 4))


def crates(s, x, y):
    shadow(s, x, y + 2, 44)
    for cx, cy, w in ((x - 20, y - 22, 24), (x + 2, y - 18, 20), (x - 12, y - 42, 20)):
        box(s, WOOD, cx, cy, w, w - 2)
        box(s, WOOD_L, cx, cy, w, 2)
        pygame.draw.rect(s, WOOD_D, (cx, cy, w, w - 2), 2)
        pygame.draw.line(s, WOOD_D, (cx + 2, cy + 2), (cx + w - 3, cy + w - 5), 2)


def mushrooms(s, x, y):
    for dx, size, c in ((-10, 8, (200, 50, 50)), (4, 11, (220, 60, 56)), (14, 6, (190, 80, 60))):
        box(s, (236, 226, 200), x + dx - 2, y - size, 4, size)
        pygame.draw.ellipse(s, c, (x + dx - size, y - size - size // 2 - 2, size * 2, size + 2))
        for k in range(2):
            box(s, (250, 240, 230), x + dx - size // 2 + k * size // 2, y - size - size // 3, 2, 2)
    for dx in (-16, -2, 10, 20):
        box(s, (70, 120, 50), x + dx, y - 4, 2, 5)


def log(s, x, y):
    shadow(s, x, y + 2, 56)
    box(s, (100, 66, 40), x - 26, y - 14, 52, 14)
    box(s, (130, 88, 52), x - 26, y - 14, 52, 3)
    for k in range(4):
        box(s, (84, 54, 32), x - 22 + k * 13, y - 9, 8, 2)
    pygame.draw.ellipse(s, (170, 128, 80), (x + 20, y - 15, 10, 15))
    pygame.draw.ellipse(s, (130, 92, 56), (x + 22, y - 11, 6, 7))
    pygame.draw.ellipse(s, (60, 120, 50), (x - 12, y - 18, 12, 6))


def net_panel(s, x, y):
    """Painel de rede na parede, com os cabos pendurados."""
    box(s, (40, 42, 50), x - 18, y - 36, 36, 18)
    box(s, (60, 62, 72), x - 18, y - 36, 36, 2)
    for k in range(6):
        box(s, (20, 20, 24), x - 15 + k * 5, y - 30, 4, 4)
        box(s, (90, 240, 120) if k % 3 else (240, 200, 60), x - 14 + k * 5, y - 24, 2, 2)
    for k, c in enumerate(((60, 130, 220), (230, 200, 60), (60, 130, 220), (220, 70, 70))):
        pygame.draw.arc(s, c, (x - 16 + k * 7, y - 30, 10, 26), math.pi, math.tau, 2)


def rack(s, x, y):
    """Rack de servidor com as luzinhas."""
    shadow(s, x, y + 2, 40)
    box(s, (34, 36, 44), x - 17, y - 66, 34, 68)
    box(s, (54, 56, 66), x - 17, y - 66, 34, 3)
    for k in range(7):
        yy = y - 60 + k * 9
        box(s, (58, 60, 70), x - 14, yy, 28, 7)
        box(s, (24, 24, 28), x - 12, yy + 2, 14, 3)
        box(s, (90, 240, 120) if (k * 7) % 3 else (240, 80, 70), x + 6, yy + 2, 2, 2)
        box(s, (90, 180, 250), x + 10, yy + 2, 2, 2)
    box(s, (20, 20, 24), x - 17, y - 2, 34, 4)


def cone(s, x, y):
    shadow(s, x + 6, y + 2, 40)
    box(s, (40, 40, 44), x - 12, y - 4, 24, 4)
    pygame.draw.polygon(s, (240, 120, 40), [(x - 9, y - 4), (x + 9, y - 4), (x + 2, y - 30), (x - 2, y - 30)])
    box(s, (250, 250, 250), x - 6, y - 18, 12, 4)
    for k in range(5):                                       # fita zebrada caída do lado
        box(s, (240, 210, 40) if k % 2 == 0 else (30, 30, 30), x + 8 + k * 5, y - 14 + k * 2, 5, 3)


def spool(s, x, y):
    shadow(s, x, y + 2, 36)
    pygame.draw.ellipse(s, (130, 90, 56), (x - 17, y - 34, 10, 36))
    box(s, (40, 110, 200), x - 12, y - 28, 24, 24)
    for k in range(5):
        box(s, (60, 140, 230), x - 12, y - 27 + k * 5, 24, 2)
    pygame.draw.ellipse(s, (150, 104, 64), (x + 7, y - 34, 10, 36))
    pygame.draw.ellipse(s, (100, 66, 40), (x + 10, y - 20, 4, 8))


def cooler(s, x, y):
    """Bebedouro com o garrafão."""
    shadow(s, x, y + 2, 30)
    box(s, (220, 224, 230), x - 12, y - 40, 24, 42)
    box(s, (190, 196, 204), x - 12, y - 40, 3, 42)
    box(s, (40, 120, 220), x - 4, y - 30, 3, 4)
    box(s, (220, 60, 60), x + 2, y - 30, 3, 4)
    box(s, (150, 156, 166), x - 8, y - 18, 16, 4)
    pygame.draw.ellipse(s, (140, 200, 240), (x - 10, y - 66, 20, 28))
    pygame.draw.ellipse(s, (190, 230, 250), (x - 6, y - 62, 6, 14))
    box(s, (120, 180, 220), x - 4, y - 42, 8, 4)


def clinic_frame(s, x, y):
    """Quadro da Clepalovers: um coração rosa e SORRIA."""
    box(s, (250, 250, 248), x - 18, y - 38, 36, 26)
    pygame.draw.rect(s, (220, 150, 190), (x - 18, y - 38, 36, 26), 2)
    pygame.draw.circle(s, (240, 110, 170), (x - 4, y - 30), 4)
    pygame.draw.circle(s, (240, 110, 170), (x + 4, y - 30), 4)
    pygame.draw.polygon(s, (240, 110, 170), [(x - 8, y - 29), (x + 8, y - 29), (x, y - 20)])


def waiting_chairs(s, x, y):
    shadow(s, x, y + 2, 70)
    box(s, METAL_D, x - 34, y - 6, 68, 3)
    for k in range(3):
        cx = x - 32 + k * 22
        box(s, (230, 120, 170), cx, y - 18, 20, 10)
        box(s, (200, 90, 140), cx, y - 30, 20, 13)
        box(s, (250, 160, 200), cx, y - 30, 20, 2)
        box(s, METAL_D, cx + 2, y - 8, 2, 8)
        box(s, METAL_D, cx + 16, y - 8, 2, 8)


def plant(s, x, y):
    art.plant(s, x, y)


def cart(s, x, y):
    """Carrinho da clínica com frascos."""
    shadow(s, x, y + 2, 36)
    box(s, METAL, x - 15, y - 34, 30, 3)
    box(s, METAL, x - 15, y - 16, 30, 3)
    box(s, METAL_D, x - 15, y - 34, 2, 32)
    box(s, METAL_D, x + 13, y - 34, 2, 32)
    for k, c in enumerate(((240, 140, 190), (140, 200, 240), (250, 250, 250))):
        box(s, c, x - 11 + k * 9, y - 44, 6, 10)
        box(s, (200, 200, 210), x - 10 + k * 9, y - 46, 4, 2)
    box(s, (240, 240, 244), x - 10, y - 24, 20, 8)
    for wx in (x - 12, x + 10):
        pygame.draw.circle(s, (40, 40, 44), (wx, y), 3)


def gold_portrait(s, x, y):
    """Retrato de moldura dourada da Mansão: um figurão de terno, sério."""
    box(s, (190, 150, 60), x - 16, y - 44, 32, 34)
    box(s, (230, 196, 100), x - 16, y - 44, 32, 2)
    box(s, (60, 46, 40), x - 12, y - 40, 24, 26)
    pygame.draw.circle(s, (200, 170, 140), (x, y - 32), 5)
    box(s, (30, 30, 40), x - 8, y - 26, 16, 12)
    box(s, (240, 240, 240), x - 1, y - 26, 2, 6)


def papers(s, x, y):
    """Pilhas de papel com o carimbo em cima."""
    shadow(s, x, y + 2, 46)
    for k, (dx, hgt) in enumerate(((-14, 30), (2, 22), (14, 14))):
        for j in range(0, hgt, 3):
            box(s, (244, 240, 228) if (j // 3) % 2 else (226, 222, 210), x + dx - 9, y - j - 4, 18, 3)
    box(s, (170, 40, 40), x - 18, y - 40, 8, 6)
    box(s, WOOD_D, x - 16, y - 46, 4, 6)
    box(s, (200, 50, 50), x + 4, y - 24, 6, 2)


def cabinet(s, x, y):
    art.file_cabinet(s, x - 20, y - 72)


def bust(s, x, y):
    """Busto de mármore num pedestal."""
    shadow(s, x, y + 2, 30)
    box(s, (210, 206, 200), x - 10, y - 30, 20, 32)
    box(s, (236, 232, 226), x - 10, y - 30, 20, 3)
    box(s, (190, 186, 180), x - 13, y - 34, 26, 5)
    pygame.draw.ellipse(s, (226, 222, 216), (x - 14, y - 48, 28, 16))
    pygame.draw.circle(s, (236, 232, 226), (x, y - 56), 8)
    box(s, (200, 196, 190), x - 4, y - 56, 2, 2)
    box(s, (200, 196, 190), x + 2, y - 56, 2, 2)


def vase(s, x, y):
    shadow(s, x, y + 2, 26)
    pygame.draw.ellipse(s, (40, 70, 140), (x - 11, y - 30, 22, 30))
    box(s, (40, 70, 140), x - 6, y - 38, 12, 10)
    box(s, (210, 180, 90), x - 11, y - 18, 22, 3)
    box(s, (220, 220, 230), x - 3, y - 26, 2, 8)
    for dx, c in ((-6, (230, 80, 90)), (0, (250, 220, 90)), (6, (230, 80, 90))):
        box(s, (60, 120, 60), x + dx, y - 48, 2, 10)
        pygame.draw.circle(s, c, (x + dx + 1, y - 50), 3)


def joke_sign(s, x, y, lines, colors):
    """Placa de pé com duas linhas (a piada do corredor)."""
    board, ink = colors
    shadow(s, x, y + 2, 26)
    box(s, WOOD_D, x - 2, y - 30, 4, 32)
    w = max(art._ctx["ui"].assets.text_width(t, theme.XS) for t in lines) + 16 if art._ctx.get("ui") else 120
    box(s, shade(board, -40), x - w // 2 - 2, y - 60, w + 4, 34)
    box(s, board, x - w // 2, y - 58, w, 30)
    box(s, shade(board, 30), x - w // 2, y - 58, w, 2)
    for k, t in enumerate(lines):
        art._text(s, t, theme.XS, ink, (x, y - 50 + k * 13))


# por capítulo: peças de parede, peças de chão (encostadas), a piada e as cores da placa
CHAPTERS = {
    1: ((torch,), (barrel, crates, mushrooms, log),
        ("ACAMPAMENTO FECHADO", "SIGA EM FRENTE"), ((170, 120, 70), (40, 24, 12))),
    2: ((net_panel,), (rack, cone, spool, cooler),
        ("SUPORTE LAG LOBBY", "AGUARDE NA LINHA"), ((240, 210, 40), (30, 30, 30))),
    3: ((clinic_frame,), (waiting_chairs, plant, cooler, cart),
        ("SENHA 999", "ATENDENDO A 001"), ((250, 230, 240), (180, 60, 120))),
    4: ((gold_portrait,), (papers, cabinet, bust, vase),
        ("PROIBIDO PASSAR", "SEM CARIMBO"), ((236, 230, 210), (130, 30, 30))),
}
# onde ninguém passa, em volta do pé de cada peça (dx, dy, w, h)
FOOT = {barrel: (-14, -10, 28, 14), crates: (-22, -12, 44, 16), mushrooms: (-14, -8, 28, 10),
        log: (-26, -12, 54, 14), rack: (-17, -12, 34, 16), cone: (-12, -8, 24, 10),
        spool: (-17, -12, 34, 16), cooler: (-13, -12, 26, 16), waiting_chairs: (-34, -12, 68, 16),
        plant: (-10, -10, 20, 14), cart: (-15, -10, 30, 14), papers: (-24, -10, 46, 14),
        cabinet: (-20, -14, 40, 18), bust: (-13, -10, 26, 14), vase: (-11, -8, 22, 12),
        joke_sign: (-4, -6, 8, 8)}


def chapter_set(chapter):
    return CHAPTERS.get(chapter, CHAPTERS[1])


def layout(rows, chapter, joke=True):
    """O que vai em cada lugar: lista de ``(peça, x, y, args, chão)`` em pixels do mapa (x, y = o pé
    da peça). A placa da piada vai no lugar de chão mais perto de onde o grupo chega."""
    ground, wall = spots(rows)
    walls, floors, lines, colors = chapter_set(chapter)
    grid = lobbies.grid_of(rows)
    arrive = [(x, y) for y, row in enumerate(grid) for x, ch in enumerate(row) if ch in ("a" if joke else "S")]
    out = []
    sign_at = None
    if joke and arrive and ground:
        ax = sum(x for x, _ in arrive) / len(arrive)
        ay = sum(y for _, y in arrive) / len(arrive)
        # a placa é larga: só encostada em parede de cima ou de baixo, de preferência a de baixo
        wide = [k for k in range(len(ground)) if ground[k][2] in "ud"] or list(range(len(ground)))
        sign_at = min(wide, key=lambda k: (math.hypot(ground[k][0] - ax, ground[k][1] - ay)
                                           + (0 if ground[k][2] == "d" else 3)))
    for k, (x, y, side) in enumerate(ground):
        px, py = x * T + T // 2, y * T + T // 2 + 10
        px += {"l": -6, "r": 6}.get(side, 0)
        py += {"u": -10, "d": 4}.get(side, 0)
        if k == sign_at:
            out.append((joke_sign, px, py, (lines, colors), True))
        else:
            out.append((floors[k % len(floors)], px, py, (), True))
    for k, (x, y) in enumerate(wall):
        out.append((walls[k % len(walls)], x * T + T // 2, y * T + 2, (), False))
    return out


def furnish(match, rows, chapter, joke=True):
    """Põe os enfeites na partida (sala inicial ou corredor): cada um vira um móvel desenhado, com o
    pé que ninguém atravessa."""
    from .casa import Decor, _bake
    from .entities import Wall
    art.use(match.assets)
    for fn, x, y, args, on_floor in layout(rows, chapter, joke):
        baked = _bake(fn, *args)
        match.props.append(Decor(x, y, baked, flat=not on_floor, foot_y=y))
        if on_floor:
            dx, dy, w, h = FOOT[fn]
            match.arena.walls.append(Wall(x + dx, y + dy, w, h, visible=False))


# ─────────────────────────────────────────────
#  Salas de luta: móveis no nível dos heróis e poças de luz
# ─────────────────────────────────────────────
ROOM_MAX = 6             # móveis por sala de luta
ROOM_GAP = 4             # quadrados entre dois móveis
ROOM_DOOR = 3            # quadrados livres em volta das portas
# por capítulo: (peça, bloqueia o chão?), a cor da luz e a força dela
ROOM_SETS = {
    1: ((("sala_arvore_0", True), ("sala_pedras", False), ("sala_arvore_1", True), ("sala_moita", False),
         ("sala_tronco", True), ("sala_arvore_2", True)), (90, 104, 44), 70),
    2: ((("sala_rack", True), ("sala_mesa_pc", True), ("sala_vaso_costela", False), ("sala_caixas", True),
         ("sala_bebedouro", False), ("sala_vaso_espada", False)), (60, 80, 120), 60),
    3: ((("sala_cadeiras", True), ("sala_vaso_orquidea", False), ("sala_biombo", True), ("sala_carrinho", False),
         ("sala_cadeiras", True), ("sala_vaso_orquidea", False)), (110, 50, 90), 55),
    4: ((("sala_relogio", True), ("sala_poltrona", True), ("sala_vaso_samambaia", False), ("sala_aparador", True),
         ("sala_busto", True), ("sala_poltrona", True)), (110, 80, 36), 60),
}


def room_spots(room_rect, walls, doors, avoid=()):
    """Lugares para os móveis numa sala de luta: quadrados livres encostados numa parede, longe das
    portas, dos pontos ``avoid`` e uns dos outros, e com o caminho do outro lado livre (pixels do
    mapa, o pé no meio do quadrado)."""
    def blocked(r):
        return any(r.colliderect(w) for w in walls)

    cols, rows = room_rect.w // T, room_rect.h // T
    out = []
    for r in range(rows):
        for c in range(cols):
            cell = pygame.Rect(room_rect.x + c * T, room_rect.y + r * T, T, T)
            if blocked(cell.inflate(-4, -4)):
                continue
            if any(cell.inflate(2 * ROOM_DOOR * T, 2 * ROOM_DOOR * T).colliderect(d) for d in doors):
                continue
            if any(cell.inflate(4 * T, 4 * T).collidepoint(p) for p in avoid):
                continue
            touch = [(dx, dy) for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)) if blocked(cell.move(dx * T, dy * T).inflate(-4, -4))]
            if len(touch) != 1:
                continue                                  # só encostado numa parede (canto fecha passagem)
            dx, dy = touch[0]
            ahead = [cell.move(-dx * T * k, -dy * T * k) for k in (1, 2)]
            if any(blocked(a.inflate(-4, -4)) or not room_rect.contains(a) for a in ahead):
                continue
            if all(max(abs(cell.centerx - x) // T, abs(cell.bottom - 8 - y) // T) >= ROOM_GAP for x, y in out):
                out.append((cell.centerx, cell.bottom - 8))
            if len(out) >= ROOM_MAX:
                return out
    return out


class LightPool:
    """Poça de luz no chão da sala (somada à cor do chão, por baixo de todo mundo)."""

    flat = True
    alive = True

    def __init__(self, x, y, rx, ry, color, strength):
        self.x, self.y = x, y
        self.img = _pool(rx, ry, color, strength)

    @property
    def sort_y(self):
        return self.y

    def update(self, match):
        pass

    def draw(self, surf, cam):
        surf.blit(self.img, (round(self.x - cam.x - self.img.get_width() // 2),
                             round(self.y - cam.y - self.img.get_height() // 2)), special_flags=pygame.BLEND_RGB_ADD)


_POOLS = {}


def _pool(rx, ry, color, strength):
    key = (rx, ry, color, strength)
    if key not in _POOLS:
        s = pygame.Surface((rx * 2, ry * 2))
        s.fill((0, 0, 0))
        n = 14
        for k in range(n, 0, -1):
            f = (1 - k / n) ** 1.5 * strength / 100
            c = tuple(min(255, int(v * f)) for v in color)
            one = pygame.Surface((rx * 2, ry * 2))
            one.fill((0, 0, 0))
            pygame.draw.ellipse(one, c, (rx - rx * k / n, ry - ry * k / n, 2 * rx * k / n, 2 * ry * k / n))
            s.blit(one, (0, 0), special_flags=pygame.BLEND_RGB_MAX)
        _POOLS[key] = s
    return _POOLS[key]


def furnish_rooms(match, layout, chapter):
    """Mobília das salas de luta do capítulo (peças prontas de assets/pecas) e as poças de luz.
    As peças grandes ganham um pé que ninguém atravessa; as pequenas (vaso, pedra, moita) não."""
    from . import pecas
    from .entities import Wall
    pieces, color, strength = ROOM_SETS.get(chapter, ROOM_SETS[1])
    if pecas.image(pieces[0][0]) is None:
        return
    for i, room in enumerate(layout.fight_rooms):
        rect = room.rect
        walls = [w.rect for w in match.arena.walls if w.rect.colliderect(rect.inflate(2 * T, 2 * T))]
        avoid = [(rect.centerx, rect.centery)]
        for k, (x, y) in enumerate(room_spots(rect, walls, [d for _, d in room.doors], avoid)):
            name, solid = pieces[(k + i) % len(pieces)]
            img = pecas.image(name)
            match.props.append(_Piece(x, y, img))
            if solid:
                w = max(20, img.get_width() - 20)
                match.arena.walls.append(Wall(x - w // 2, y - 14, w, 16, visible=False))
        for k, (fx, fy) in enumerate(((0.3, 0.35), (0.72, 0.62), (0.45, 0.8))):
            match.props.append(LightPool(rect.x + rect.w * fx, rect.y + rect.h * fy, 130 - k * 15, 70 - k * 8,
                                         color, strength))


class _Piece:
    """Um móvel pronto parado no chão (x, y = o pé, no meio), com a sombra."""

    alive = True

    def __init__(self, x, y, img):
        self.x, self.y = x, y
        self.img = img

    @property
    def sort_y(self):
        return self.y

    def update(self, match):
        pass

    def draw(self, surf, cam):
        from . import pecas
        sx, sy = round(self.x - cam.x), round(self.y - cam.y)
        w = int(self.img.get_width() * 0.8)
        surf.blit(pecas.shadow(w, max(8, w // 4), 80), (sx - w // 2, sy - max(8, w // 4) // 2 - 2))
        surf.blit(self.img, self.img.get_rect(midbottom=(sx, sy)))
