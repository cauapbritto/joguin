"""Mapas da campanha desenhados como texto: as salas calmas da fase e a Casa da turma.

Cada caractere é um quadrado de 40 px:

    #  parede (no estilo do tema: cerca viva, tijolo ou gelo)
    .  chão
       (espaço) fora do mapa: escuro, ninguém chega lá
    S  onde o grupo começa a fase
    a  ponto de chegada na recompensa (os enfeites com piada ficam por perto)
    F  fogueira (cura um pouco quem fica perto)
    C  baú escondido
    1  passagem de corredor (marca a ponta onde ele encosta numa sala)
    L  loja (na abertura, a lojinha)
    R  ferreiro
    K  armário de armas
    X  altar das maldições

O desenho da fase inteira (abertura, salas de luta, recompensa e corredores) é montado em
mapa_fase.py e passa por ``parse`` daqui. Tudo o que não é parede nem "fora" é chão. As paredes
viram poucos retângulos grandes (quadrados vizinhos juntados), para a colisão e o desenho ficarem
baratos.
"""

TILE = 40
MARKERS = "SaFC12LRKX"

# cenário (chão e paredes) de cada fase nas salas calmas e nos corredores, quando não é o do próprio nome
LOBBY_SCENERY = {"lag_estacionamento": "lag_garagem", "lag_copa": "lag_escritorio", "lag_reuniao": "lag_escritorio",
                 "clinica_fachada": "clinica_calcada", "clinica_vestiario": "clinica_spa",
                 "clinica_antessala": "clinica_vip",
                 "mansao_fachada": "mansao_jardim", "mansao_copa": "mansao", "mansao_escadaria": "mansao_reuniao"}

def _grid(rows):
    width = max(len(r) for r in rows)
    return [r.ljust(width) for r in rows]


def _merge(grid, wanted):
    """Junta os quadrados com ``wanted(ch)`` em retângulos (faixas na linha, depois na coluna)."""
    runs = []
    for y, row in enumerate(grid):
        x = 0
        while x < len(row):
            if wanted(row[x]):
                start = x
                while x < len(row) and wanted(row[x]):
                    x += 1
                runs.append((start, x, y))
            else:
                x += 1
    rects = []
    open_ = {}                                    # (x0, x1) → [x0, y0, x1, y1] ainda crescendo
    for x0, x1, y in runs:
        key = (x0, x1)
        r = open_.get(key)
        if r is not None and r[3] == y:
            r[3] = y + 1
        else:
            if r is not None:
                rects.append(r)
            open_[key] = [x0, y, x1, y + 1]
    rects.extend(open_.values())
    return [(x0 * TILE, y0 * TILE, (x1 - x0) * TILE, (y1 - y0) * TILE) for x0, y0, x1, y1 in rects]


HEADROOM = 3                 # linhas a mais em cima: as entradas não ficam escondidas atrás do HUD


def _headroom(grid):
    """Acrescenta linhas no alto: em cima das entradas fica o túnel escuro; o resto continua a parede."""
    top = grid[0]
    row = "".join(" " if ch in "12" else ("#" if ch == "#" else " ") for ch in top)
    return [row] * HEADROOM + grid


def grid_of(rows):
    """O desenho como ele vira mapa: linhas do mesmo tamanho e as linhas de folga no alto."""
    return _headroom(_grid(rows))


def parse(rows):
    """Texto → (tamanho, paredes, áreas de fora, marcadores {letra: [(x, y) do centro de cada quadrado]})."""
    grid = _headroom(_grid(rows))
    size = (len(grid[0]) * TILE, len(grid) * TILE)
    walls = _merge(grid, lambda ch: ch == "#")
    void = _merge(grid, lambda ch: ch == " ")
    markers = {}
    for y, row in enumerate(grid):
        for x, ch in enumerate(row):
            if ch in MARKERS:
                markers.setdefault(ch, []).append((x * TILE + TILE // 2, y * TILE + TILE // 2))
    return size, walls, void, markers


def cells_rect(points):
    """Retângulo (x, y, w, h) que cobre os quadrados marcados (centros em ``points``)."""
    xs = [x for x, _ in points]
    ys = [y for _, y in points]
    half = TILE // 2
    return (min(xs) - half, min(ys) - half, max(xs) - min(xs) + TILE, max(ys) - min(ys) + TILE)


# ─────────────────────────────────────────────
#  Hub: Casa da turma (onde a campanha começa)
# ─────────────────────────────────────────────
# A casa em cima (chão de tábuas e papel de parede) e o quintal embaixo (grama e cerca viva), com a
# garagem no canto do quintal. D: a saída para a aventura, no muro de baixo do quintal.
CASA = ("CASA DA TURMA", (
    "################################################",
    "#..............................................#",
    "#..............................................#",
    "#..............................................#",
    "#..............................................#",
    "#..............................................#",
    "#..............................................#",
    "#..............................................#",
    "#..............................................#",
    "#..............................................#",
    "#..............................................#",
    "#.....................SSSS.....................#",
    "#..............................................#",
    "#..............................................#",
    "####################........####################",
))
QUINTAL = (
    "#..............................................#",
    "#..............................................#",
    "#..............................................#",
    "#.................................###########..#",
    "#.................................###########..#",
    "#..............................................#",
    "#..............................................#",
    "#..............................................#",
    "#####################DDDDDD#####################",
)
CASA_TOP = 2                 # linhas escuras em cima (a parede de cima não fica atrás do HUD)
CASA_BOTTOM = 3              # e embaixo: o túnel escuro depois da saída
CASA_SPLIT = (CASA_TOP + len(CASA[1])) * TILE      # onde a casa acaba e o quintal começa (px)


def casa_parse():
    """Como ``parse``, mas a casa e o quintal juntam as paredes cada um por si (a parede da casa é
    papel de parede; a do quintal, cerca viva). Devolve (tamanho, paredes, fora, marcadores)."""
    width = len(CASA[1][0])
    house = [" " * width] * CASA_TOP + list(CASA[1])
    yard = list(QUINTAL) + [" " * width] * CASA_BOTTOM
    grid = house + yard
    size = (width * TILE, len(grid) * TILE)
    split = len(house)
    walls = _merge(house, lambda ch: ch == "#")
    walls += [(x, y + split * TILE, w, h) for x, y, w, h in _merge(yard, lambda ch: ch == "#")]
    void = _merge(grid, lambda ch: ch == " ")
    markers = {}
    for y, row in enumerate(grid):
        for x, ch in enumerate(row):
            if ch in "SD":
                markers.setdefault(ch, []).append((x * TILE + TILE // 2, y * TILE + TILE // 2))
    return size, walls, void, markers
