"""A fase num mapa só, como no Soul Knight: as salas ligadas por corredores, tudo a pé.

Cada capítulo tem um formato (``SHAPES``): a cruz no 1, a torre subindo no 2, o corredor da
clínica no 3 e o pátio da mansão no 4. As três fases do capítulo usam o mesmo formato, espelhado
(``flips``). O do capítulo 1 segue o rascunho do Cauã (cinco salas):

* ABERTURA no meio: o portal da Casa da turma chega aqui; tem a lojinha e o altar;
* em cima, a MASMORRA 1 (corredor curto);
* à direita, a sala de luta do meio (MASMORRA 2), que embaixo leva à
* sala de RECOMPENSAS no canto (baú, fogueira, loja, ferreiro e armário);
* embaixo à esquerda, a MASMORRA FINAL (o corredor vai para a esquerda e desce): o portal da
  próxima fase ou, na 3ª fase do capítulo, o chefe.

As salas de luta são as masmorras de sempre (mesmos perigos, chefes e arte), cada uma com a sua
parede de borda; a passagem do corredor é um vão nessa parede, com uma grade (``RoomDoor``) que
fecha quando o grupo entra e só abre quando a sala fica limpa. A sala do meio de cada fase é uma
das ``arena.SALAS``. A abertura, a recompensa e os corredores saem de um desenho em texto (como os
de ``lobbies``), no cenário do acampamento da fase.

``PhaseLayout`` monta o desenho (é só geometria, fica guardado por fase), ``PhaseArena`` é a arena
da partida (chão de cada sala, paredes de cada cenário) e ``draw_minimap`` é o mapinha do canto."""
import math
import random
from dataclasses import dataclass, field

import pygame

from . import lobbies, scenery, theme
from .arena import MAPS_BY_KEY, Arena, MapConfig
from .entities import Entity, Particle, Wall, WallStyle

T = lobbies.TILE
HEAD = lobbies.HEADROOM
CW = 4                       # largura dos corredores (quadrados): o vão da porta tem 160 px
CALM = (18, 12)              # abertura e recompensa (quadrados por dentro)
MARGIN = 2                   # quadrados vazios em volta de tudo
SPACE = 3                    # distância mínima entre duas salas de luta
DOOR_DEPTH = 30              # a parede de borda das masmorras


@dataclass
class Room:
    key: str                 # abertura, luta1, luta2, recompensa, final
    cells: list              # [coluna, linha, largura, altura] em quadrados (sem as linhas de folga)
    dungeon: object = None   # campaign.Dungeon (salas de luta)
    order: int = 0           # 0, 1, 2: MASMORRA 1, 2 e 3 (a final)
    rect: pygame.Rect = None  # em pixels do mapa
    doors: list = field(default_factory=list)    # (lado, pygame.Rect) dos vãos na parede de borda

    @property
    def fight(self):
        return self.dungeon is not None

    @property
    def final(self):
        return self.key == "final"

    @property
    def cfg(self):
        return MAPS_BY_KEY[self.dungeon.map_key] if self.dungeon is not None else None


def px(c, r):
    """Canto de cima do quadrado (c, r) em pixels (as linhas de folga do alto já contadas)."""
    return c * T, (r + HEAD) * T


def cells_px(c, r, w, h):
    x, y = px(c, r)
    return pygame.Rect(x, y, w * T, h * T)


def _overlap(a, b, gap):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax - gap < bx + bw and bx - gap < ax + aw and ay - gap < by + bh and by - gap < ay + ah


# ─────────────────────────────────────────────
#  Um formato de mapa por capítulo
# ─────────────────────────────────────────────
# Cada formato devolve as salas e os corredores em quadrados (a abertura no canto (0, 0), depois
# tudo é deslocado para caber) e as portas das salas de luta: (sala, lado, corredor que chega).
# As três fases do capítulo usam o mesmo formato: a 1ª como foi desenhado, a 2ª espelhada na
# horizontal e a 3ª espelhada também na vertical (a torre só espelha de lado: ela sempre sobe).
SHAPES = {1: "cruz", 2: "torre", 3: "corredor", 4: "patio"}
GAP = 6                      # comprimento dos corredores entre duas salas


def phase_in_chapter(phase):
    """0, 1 ou 2: a posição da fase dentro do capítulo dela."""
    from .campaign import PHASES
    same = [p.key for p in PHASES if p.chapter == phase.chapter]
    return same.index(phase.key) if phase.key in same else 0


def flips(shape, index):
    """(espelha de lado, espelha de cima para baixo) da fase ``index`` do capítulo."""
    if shape == "torre":
        return (index % 2 == 1, False)
    return (index >= 1, index == 2)


def _push(box, others, axis, step):
    """Empurra a sala até ela não encostar nas outras (SPACE de folga)."""
    while any(_overlap(box, o, SPACE) for o in others):
        box[axis] += step


def _cruz(size):
    """Capítulo 1: a abertura no meio e as salas em volta (o desenho do Cauã)."""
    aw, ah = CALM
    w1, h1 = size["luta1"]
    l1 = [aw // 2 - w1 // 2, -GAP - h1, w1, h1]
    mid = ah // 2
    w2, h2 = size["luta2"]
    l2 = [aw + 8, mid - h2 // 2, w2, h2]
    _push(l2, [l1], 0, 1)                         # a sala do meio não encosta na masmorra 1
    rw, rh = CALM
    rew = [l2[0] + w2 // 2 - rw // 2, l2[1] + h2 + GAP, rw, rh]
    wf, hf = size["final"]
    vx = -12                                     # o corredor que desce para a sala final
    fin = [vx - 3 - wf, ah - 2, wf, hf]
    door_f = fin[1] + hf - 8                     # porta da final: no lado direito, perto de baixo
    corridors = [
        [aw // 2 - CW // 2, -GAP, CW, GAP],                     # abertura ↔ masmorra 1
        [aw, mid - CW // 2, l2[0] - aw, CW],                    # abertura ↔ sala do meio
        [l2[0] + w2 // 2 - CW // 2, l2[1] + h2, CW, GAP],       # sala do meio ↔ recompensa
        [vx, mid - CW // 2, -vx, CW],                           # abertura → esquerda
        [vx, mid - CW // 2, CW, door_f + CW - (mid - CW // 2)],  # ... desce
        [fin[0] + wf, door_f, vx - fin[0] - wf, CW],            # ... e entra na sala final
    ]
    rooms = {"abertura": [0, 0, aw, ah], "luta1": l1, "luta2": l2, "recompensa": rew, "final": fin}
    doors = [("luta1", "baixo", 0), ("luta2", "esquerda", 1), ("luta2", "baixo", 2), ("final", "direita", 5)]
    return rooms, corridors, doors


def _torre(size):
    """Capítulo 2 (Lag Lobby): um prédio, em linha reta subindo andar por andar: térreo (abertura),
    masmorra 1, a loja (recompensa), masmorra 2 e a cobertura (a final). Os andares ficam um pouco
    para um lado e para o outro, como uma escada."""
    order = ["abertura", "luta1", "recompensa", "luta2", "final"]
    dims = {"abertura": CALM, "recompensa": CALM, **size}
    rooms, corridors, doors = {}, [], []
    bottom, sway = 0, (0, 6, -4, 5, 0)
    for i, k in enumerate(order):
        w, h = dims[k]
        rooms[k] = [sway[i] - w // 2, bottom - h, w, h]
        bottom -= h + GAP
    for i in range(4):
        low, high = rooms[order[i]], rooms[order[i + 1]]
        left, right = max(low[0], high[0]) + 2, min(low[0] + low[2], high[0] + high[2]) - 2
        c = (left + right) // 2 - CW // 2
        corridors.append([c, high[1] + high[3], CW, GAP])
        if order[i] in ("luta1", "luta2"):
            doors.append((order[i], "cima", i))
        if order[i + 1] in ("luta1", "luta2", "final"):
            doors.append((order[i + 1], "baixo", i))
    return rooms, corridors, doors


def _corredor(size):
    """Capítulo 3 (Clepalovers): o corredor comprido da clínica, da recepção (abertura) até o fim
    (a final), passando pelas alas 1 e 2; a farmácia (recompensa) fica de lado, embaixo, saindo
    do corredor entre as duas alas."""
    aw, ah = CALM
    mid = ah // 2
    rooms = {"abertura": [0, 0, aw, ah]}
    corridors, doors = [], []
    x = aw
    for k, gap in (("luta1", GAP), ("luta2", 12), ("final", GAP)):
        w, h = size[k]
        corridors.append([x, mid - CW // 2, gap, CW])
        rooms[k] = [x + gap, mid - h // 2, w, h]
        doors.append((k, "esquerda", len(corridors) - 1))
        x += gap + w
    doors.insert(1, ("luta1", "direita", 1))
    doors.insert(3, ("luta2", "direita", 2))
    l1, l2 = rooms["luta1"], rooms["luta2"]
    branch = l1[0] + l1[2] + 6 - CW // 2           # no meio do corredor entre as alas
    rw, rh = CALM
    top = max(l1[1] + l1[3], l2[1] + l2[3]) + GAP
    rooms["recompensa"] = [branch + CW // 2 - rw // 2, top, rw, rh]
    corridors.append([branch, mid + CW // 2, CW, top - mid - CW // 2])
    return rooms, corridors, doors


def _patio(size):
    """Capítulo 4 (a mansão): o pátio no meio e as salas em volta. Do portão (abertura) sobe-se
    ao pátio; a masmorra 1 de um lado, a 2 do outro e o chefe no salão do fundo. O baú
    (recompensa) fica ao lado do portão."""
    pw, ph = 20, 14
    patio = [0, 0, pw, ph]
    stub = 4
    w1, h1 = size["luta1"]
    w2, h2 = size["luta2"]
    wf, hf = size["final"]
    l1 = [-stub - w1, ph // 2 - h1 // 2, w1, h1]
    l2 = [pw + stub, ph // 2 - h2 // 2, w2, h2]
    fin = [pw // 2 - wf // 2, -stub - hf, wf, hf]
    _push(fin, [l1, l2], 1, -1)                  # o salão largo não encosta nas masmorras
    aw, ah = CALM
    gate = [pw // 2 - aw // 2, max(l1[1] + l1[3], l2[1] + l2[3]) + SPACE + 1, aw, ah]
    rw, rh = CALM
    rew = [gate[0] - stub - rw, gate[1], rw, rh]
    corridors = [
        patio,
        [pw // 2 - CW // 2, ph, CW, gate[1] - ph],               # portão ↔ pátio
        [-stub, ph // 2 - CW // 2, stub, CW],                    # pátio ↔ masmorra 1
        [pw, ph // 2 - CW // 2, stub, CW],                       # pátio ↔ masmorra 2
        [pw // 2 - CW // 2, fin[1] + hf, CW, -fin[1] - hf],     # pátio ↔ salão do chefe
        [gate[0] - stub, gate[1] + ah // 2 - CW // 2, stub, CW],  # portão ↔ baú
    ]
    rooms = {"abertura": gate, "luta1": l1, "luta2": l2, "recompensa": rew, "final": fin}
    doors = [("luta1", "direita", 2), ("luta2", "esquerda", 3), ("final", "baixo", 4)]
    return rooms, corridors, doors


SHAPE_BUILDERS = {"cruz": _cruz, "torre": _torre, "corredor": _corredor, "patio": _patio}


class PhaseLayout:
    """Onde fica cada sala, cada corredor e cada porta da fase (só geometria)."""

    _cache = {}

    @classmethod
    def of(cls, phase):
        if phase.key not in cls._cache:
            cls._cache[phase.key] = cls(phase)
        return cls._cache[phase.key]

    def __init__(self, phase):
        self.phase = phase
        self.scenery = lobbies.LOBBY_SCENERY.get(phase.theme, phase.theme)
        first, last = phase.dungeons
        fights = {"luta1": first, "luta2": phase.middle, "final": last}
        size = {k: (MAPS_BY_KEY[d.map_key].size[0] // T, MAPS_BY_KEY[d.map_key].size[1] // T)
                for k, d in fights.items()}
        self.shape = SHAPES.get(phase.chapter, "cruz")
        self.flip = flips(self.shape, phase_in_chapter(phase))
        rooms, corridors, doors = SHAPE_BUILDERS[self.shape](size)
        flip_x, flip_y = self.flip
        boxes = list(rooms.values()) + corridors
        for b in boxes:                                  # o mesmo desenho, espelhado
            if flip_x:
                b[0] = -(b[0] + b[2])
            if flip_y:
                b[1] = -(b[1] + b[3])
        swap = {"esquerda": "direita", "direita": "esquerda", "cima": "baixo", "baixo": "cima"}
        doors = [(k, swap[side] if (flip_x and side in ("esquerda", "direita"))
                  or (flip_y and side in ("cima", "baixo")) else side, i) for k, side, i in doors]
        dx = MARGIN - min(b[0] for b in boxes) + 1
        dy = MARGIN - min(b[1] for b in boxes) + 1
        for b in boxes:
            b[0] += dx
            b[1] += dy
        self.cols = max(b[0] + b[2] for b in boxes) + MARGIN + 1
        self.lines = max(b[1] + b[3] for b in boxes) + MARGIN + 1
        self.corridors = [tuple(c) for c in corridors]
        self.rooms = {}
        for k in ("abertura", "luta1", "luta2", "recompensa", "final"):
            d = fights.get(k)
            order = ("luta1", "luta2", "final").index(k) if d else 0
            self.rooms[k] = Room(k, tuple(rooms[k]), d, order, cells_px(*rooms[k]))
        self._doors(doors)
        self.rows = self._draw()
        self.size, self.grid_walls, _void, self.markers = lobbies.parse(self.rows)

    # ── portas das salas de luta ─────────────
    def _doors(self, doors):
        for key, side, i in doors:
            room, c = self.rooms[key], self.corridors[i]
            r = room.rect
            if side in ("cima", "baixo"):
                rect = self._door_h(c, r.y if side == "cima" else r.bottom - DOOR_DEPTH)
            else:
                rect = self._door_v(c, r.x if side == "esquerda" else r.right - DOOR_DEPTH)
            room.doors.append((side, rect))

    @staticmethod
    def _door_h(corridor, y):
        x, _ = px(corridor[0], 0)
        return pygame.Rect(x, y, corridor[2] * T, DOOR_DEPTH)

    @staticmethod
    def _door_v(corridor, x):
        _, y = px(0, corridor[1])
        return pygame.Rect(x, y, DOOR_DEPTH, corridor[3] * T)

    # ── desenho em texto (abertura, recompensa e corredores) ──
    def _draw(self):
        W, H = self.cols, self.lines
        grid = [[" "] * W for _ in range(H)]
        owned = set()                                # quadrados das salas de luta (paredes próprias)
        for room in self.rooms.values():
            c0, r0, w, h = room.cells
            cells = {(c, r) for c in range(c0, c0 + w) for r in range(r0, r0 + h)}
            if room.fight:
                owned |= cells
            else:
                for c, r in cells:
                    grid[r][c] = "."
        for c0, r0, w, h in self.corridors:
            for c in range(c0, c0 + w):
                for r in range(r0, r0 + h):
                    if (c, r) not in owned:
                        grid[r][c] = "."
        for r in range(H):
            for c in range(W):
                if grid[r][c] != " " or (c, r) in owned:
                    continue
                if any(0 <= r + j < H and 0 <= c + i < W and grid[r + j][c + i] == "."
                       for i in (-1, 0, 1) for j in (-1, 0, 1)):
                    grid[r][c] = "#"
        # marcadores: largada, bancas, baú, fogueira, armário e as bocas dos corredores
        a = self.rooms["abertura"].cells
        rw = self.rooms["recompensa"].cells
        marks = {"S": [(a[0] + 7, a[1] + 7), (a[0] + 10, a[1] + 7), (a[0] + 7, a[1] + 9), (a[0] + 10, a[1] + 9)],
                 "L": [(a[0] + 3, a[1] + 2), (rw[0] + 3, rw[1] + 2)],
                 "X": [(a[0] + 14, a[1] + 2)],
                 "R": [(rw[0] + 3, rw[1] + 8)],
                 "C": [(rw[0] + 14, rw[1] + 3)],
                 "K": [(rw[0] + 14, rw[1] + 8)],
                 "F": [(rw[0] + 8, rw[1] + 6), (rw[0] + 9, rw[1] + 6), (rw[0] + 8, rw[1] + 7), (rw[0] + 9, rw[1] + 7)],
                 "a": [(rw[0] + 8, rw[1] + 1), (rw[0] + 9, rw[1] + 1)]}
        for ch, cells in marks.items():
            for c, r in cells:
                grid[r][c] = ch
        for c0, r0, w, h in self.corridors:            # bocas: nada de enfeite na frente
            ends = ([(c, r0) for c in range(c0, c0 + w)] + [(c, r0 + h - 1) for c in range(c0, c0 + w)]
                    if h > w else [(c0, r) for r in range(r0, r0 + h)] + [(c0 + w - 1, r) for r in range(r0, r0 + h)])
            for c, r in ends:
                if grid[r][c] == ".":
                    grid[r][c] = "1"
        return ["".join(row) for row in grid]

    # ── consultas ────────────────────────────
    @property
    def fight_rooms(self):
        return [r for r in self.rooms.values() if r.fight]

    def room_at(self, x, y):
        """A sala onde fica o ponto (None no corredor)."""
        for room in self.rooms.values():
            area = room.rect if room.fight else room.rect.inflate(T, T)
            if area.collidepoint(x, y):
                return room
        return None

    def calm_regions(self):
        """Pedaços de chão no cenário do acampamento: a abertura, a recompensa e os corredores
        (com a parede em volta, que fica por cima)."""
        out = []
        for k in ("abertura", "recompensa"):
            out.append((k, cells_px(*self.rooms[k].cells).inflate(2 * T, 2 * T)))
        for i, (c, r, w, h) in enumerate(self.corridors):
            rect = cells_px(c, r, w, h)
            out.append((f"corredor{i}", rect.inflate(2 * T, 0) if h > w else rect.inflate(0, 2 * T)))
        return out


def _cut(rect, holes):
    """O retângulo da parede menos os vãos das portas (só corta ao longo do comprimento)."""
    pieces = [pygame.Rect(rect)]
    for hole in holes:
        out = []
        for p in pieces:
            if not p.colliderect(hole):
                out.append(p)
                continue
            if p.w >= p.h:
                if hole.x > p.x:
                    out.append(pygame.Rect(p.x, p.y, hole.x - p.x, p.h))
                if hole.right < p.right:
                    out.append(pygame.Rect(hole.right, p.y, p.right - hole.right, p.h))
            else:
                if hole.y > p.y:
                    out.append(pygame.Rect(p.x, p.y, p.w, hole.y - p.y))
                if hole.bottom < p.bottom:
                    out.append(pygame.Rect(p.x, hole.bottom, p.w, p.bottom - hole.bottom))
        pieces = out
    return pieces


class _Shifted:
    """Câmera vista do canto de uma sala (o ambiente de cada sala foi feito no tamanho dela)."""

    def __init__(self, cam, ox, oy):
        self.x, self.y = cam.x - ox, cam.y - oy
        self.zoom = getattr(cam, "zoom", 1.0)


class PhaseArena(Arena):
    """A arena da fase inteira: cada sala com o chão e as paredes do próprio cenário."""

    def __init__(self, layout, assets):
        phase = layout.phase
        self.layout = layout
        self.cfg = MapConfig(f"fase_{phase.key}", phase.name, layout.size, walls=[], spawns=layout.markers["S"],
                             battle=False, theme=layout.scenery, markers=layout.markers)
        self.width, self.height = layout.size
        self.walls = []
        calm = scenery.wall_style(layout.scenery) or WallStyle(*self.cfg.wall_colors)
        for x, y, w, h in layout.grid_walls:
            self._wall((x, y, w, h), calm)
        self.regions = []                       # (chão pronto, onde)
        self.ambiences = []                     # (ambiente, retângulo da sala)
        for key, rect in layout.calm_regions():
            floor = scenery.paint_floor(f"fase:{phase.key}:{key}", rect.size, layout.scenery)
            self.regions.append((floor if floor is not None else _plain(rect.size, self.cfg.floor), rect.topleft))
        for room in layout.fight_rooms:
            cfg = room.cfg
            style = scenery.wall_style(cfg.scenery) or WallStyle(*cfg.wall_colors)
            holes = [r for _, r in room.doors]
            local = []
            for x, y, w, h in cfg.walls:
                for piece in _cut(pygame.Rect(x, y, w, h).move(room.rect.topleft), holes):
                    self._wall(piece, style)
                    local.append(Wall(piece.x - room.rect.x, piece.y - room.rect.y, piece.w, piece.h))
            floor = scenery.paint_floor(cfg.key, cfg.size, cfg.theme)
            self.regions.append((floor if floor is not None else _plain(cfg.size, cfg.floor), room.rect.topleft))
            self.ambiences.append((scenery.create_ambience(cfg.scenery, cfg.size, local), room.rect))
        for k in ("abertura", "recompensa"):
            rect = layout.rooms[k].rect
            self.ambiences.append((scenery.create_ambience(layout.scenery, rect.size, []), rect))
        for wall in self.walls:
            wall.prepare()
        self.floor = None
        self.room = pygame.Rect(0, 0, self.width, self.height)

    def _wall(self, rect, style):
        x, y, w, h = rect
        wall = Wall(x, y, w, h)
        wall.style = style
        self.walls.append(wall)

    def draw_floor(self, surf, camera, view_size):
        view = pygame.Rect(int(camera.x), int(camera.y), *view_size)
        surf.fill(scenery.VOID)
        for floor, (x, y) in self.regions:
            area = pygame.Rect(x, y, *floor.get_size())
            if area.colliderect(view):
                surf.blit(floor, (x - view.x, y - view.y))

    def draw_ambience(self, surf, camera, frame, layer):
        view = pygame.Rect(int(camera.x), int(camera.y), *surf.get_size())
        for amb, rect in self.ambiences:
            if rect.colliderect(view):
                amb.draw(surf, _Shifted(camera, rect.x, rect.y), frame, layer)

    def thumbnail(self, size):
        full = pygame.Surface((self.width, self.height))

        class _Origin:
            x = y = 0
        self.draw_floor(full, _Origin, full.get_size())
        self.draw_walls(full, _Origin)
        return pygame.transform.smoothscale(full, size)


def _plain(size, colors):
    s = pygame.Surface(size)
    s.fill(colors[0])
    return s


# ─────────────────────────────────────────────
#  Porta da sala de luta
# ─────────────────────────────────────────────
DOOR_LIFT = 22               # quadros da grade descendo (ou subindo)
DOOR_ORANGE = (240, 160, 60)
DOOR_SEALED = (150, 70, 200)


class RoomDoor(Entity):
    """Grade no vão da parede de uma sala de luta.

    "open": passagem livre; "closed": fechou porque o grupo entrou (borda laranja, até a sala ficar
    limpa); "sealed": a sala final, trancada até as outras salas de luta ficarem limpas (roxa)."""

    flat = True

    def __init__(self, room, side, rect, state="open"):
        r = pygame.Rect(rect)
        super().__init__(r.centerx, r.centery)
        self.room = room
        self.side = side
        self.rect = r
        self.state = state
        self.bars = 0.0 if state == "open" else 1.0
        self.wall = Wall(r.x, r.y, r.w, r.h, visible=False)
        self.age = 0

    @property
    def across(self):
        """A grade atravessa na horizontal (porta em cima ou embaixo)?"""
        return self.side in ("baixo", "cima")

    @property
    def closed(self):
        return self.state != "open"

    @property
    def front(self):
        """Ponto do lado de fora da porta (no corredor)."""
        step = {"baixo": (0, 60), "cima": (0, -60), "esquerda": (-60, 0), "direita": (60, 0)}[self.side]
        return self.rect.centerx + step[0], self.rect.centery + step[1]

    def sync_wall(self, arena):
        blocking = self.bars > 0.5
        present = self.wall in arena.walls
        if blocking and not present:
            arena.walls.append(self.wall)
        elif not blocking and present:
            arena.walls.remove(self.wall)

    def update(self, match):
        self.age += 1
        target = 0.0 if self.state == "open" else 1.0
        if self.bars != target:
            step = 1 / DOOR_LIFT
            self.bars = max(target, self.bars - step) if target < self.bars else min(target, self.bars + step)
            if self.age % 4 == 0:
                match.dust(self.rect.centerx + random.uniform(-30, 30), self.rect.bottom, 1)
        self.sync_wall(match.arena)
        if self.state == "closed" and self.age % 6 == 0:
            x = random.uniform(self.rect.x, self.rect.right)
            y = random.uniform(self.rect.y, self.rect.bottom)
            match.particles.append(Particle(x, y, 0, random.uniform(-0.8, -0.3), DOOR_ORANGE, 18, 2))

    def draw(self, surf, camera):
        if self.bars <= 0:
            return
        r = self.rect.move(-round(camera.x), -round(camera.y))
        color = DOOR_SEALED if self.state == "sealed" else DOOR_ORANGE
        clip = surf.get_clip()
        if self.across:
            drop = max(1, round(r.h * self.bars))
            area = pygame.Rect(r.x, r.bottom - drop, r.w, drop)
        else:
            drop = max(1, round(r.w * self.bars))
            area = pygame.Rect(r.x, r.y, drop, r.h)
        surf.set_clip(area.clip(clip))
        surf.fill((22, 20, 28), r)
        if self.across:
            for x in range(r.x + 4, r.right - 2, 10):
                surf.fill((122, 118, 132), (x, r.y, 4, r.h))
                surf.fill((180, 176, 190), (x, r.y, 1, r.h))
            surf.fill((90, 86, 100), (r.x, r.centery - 2, r.w, 4))
        else:
            for y in range(r.y + 4, r.bottom - 2, 10):
                surf.fill((122, 118, 132), (r.x, y, r.w, 4))
                surf.fill((180, 176, 190), (r.x, y, r.w, 1))
            surf.fill((90, 86, 100), (r.centerx - 2, r.y, 4, r.h))
        surf.set_clip(clip)
        pulse = 0.6 + 0.4 * math.sin(self.age * 0.15)
        edge = tuple(round(c * pulse) for c in color)
        pygame.draw.rect(surf, edge, r, 3)


# ─────────────────────────────────────────────
#  Mini mapa
# ─────────────────────────────────────────────
MINI_W, MINI_H = 118, 100    # tamanho máximo (pixels da tela)
MINI_HERE = (240, 200, 90)
MINI_SEEN = (150, 150, 170)
MINI_DARK = (30, 30, 40)
MINI_PATH = (110, 110, 130)


def minimap_rect(layout, right, top):
    scale = _mini_scale(layout)
    c0, r0, c1, r1 = _extent(layout)
    w = round((c1 - c0) * scale) + 12
    h = round((r1 - r0) * scale) + 12
    return pygame.Rect(right - w, top, w, h)


def _extent(layout):
    boxes = [r.cells for r in layout.rooms.values()] + list(layout.corridors)
    return (min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[0] + b[2] for b in boxes), max(b[1] + b[3] for b in boxes))


def _mini_scale(layout):
    c0, r0, c1, r1 = _extent(layout)
    return min((MINI_W - 12) / (c1 - c0), (MINI_H - 12) / (r1 - r0))


def draw_minimap(screen, ui, layout, visited, here, rect, portal=False):
    """O mapinha: só as salas e os corredores. A sala onde o grupo está fica dourada, as já
    visitadas cinza cheio e as que faltam só no contorno, com um "?"."""
    scale = _mini_scale(layout)
    c0, r0, _, _ = _extent(layout)
    bg = pygame.Surface(rect.size, pygame.SRCALPHA)
    bg.fill((8, 8, 14, 170))
    screen.blit(bg, rect.topleft)
    pygame.draw.rect(screen, (90, 90, 110), rect, 1)

    def box(c, r, w, h):
        x = rect.x + 6 + (c - c0) * scale
        y = rect.y + 6 + (r - r0) * scale
        return pygame.Rect(round(x), round(y), max(1, round(w * scale)), max(1, round(h * scale)))

    for corridor in layout.corridors:
        screen.fill(MINI_PATH, box(*corridor))
    for key, room in layout.rooms.items():
        r = box(*room.cells)
        if key == here:
            pygame.draw.rect(screen, MINI_HERE, r)
            pygame.draw.rect(screen, (255, 240, 180), r, 1)
        elif key in visited:
            pygame.draw.rect(screen, MINI_SEEN, r)
        else:
            pygame.draw.rect(screen, MINI_DARK, r)
            pygame.draw.rect(screen, MINI_SEEN, r, 1)
            ui.text(screen, "?", theme.XS, (200, 200, 220), r.center, shadow=False)
        if key == "final" and portal:
            pygame.draw.circle(screen, (200, 170, 255), r.center, 3)
