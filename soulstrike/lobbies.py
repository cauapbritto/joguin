"""Acampamentos da campanha (o "lobby" de cada fase), desenhados como texto.

Cada caractere é um quadrado de 40 px:

    #  parede (no estilo do tema: cerca viva, tijolo ou gelo)
    .  chão
       (espaço) fora do mapa: escuro, ninguém chega lá
    S  onde o grupo começa a fase
    a  onde o grupo volta depois da masmorra 1
    F  fogueira (cura um pouco quem fica perto)
    C  baú escondido (aparece depois da masmorra 1)
    1  entrada da masmorra 1 (na linha da parede)
    2  entrada da masmorra 2 (trancada até a masmorra 1 acabar)

Tudo o que não é parede nem "fora" é chão. As paredes viram poucos retângulos grandes
(quadrados vizinhos juntados), para a colisão e o desenho ficarem baratos.
"""

TILE = 40
MARKERS = "Sa FC12".replace(" ", "")

LOBBIES = {
    "floresta": ("ACAMPAMENTO DA CLAREIRA", (
        "########11############################22########",
        "#......#..#..........................#..#......#",
        "#......#..#..........................#..#......#",
        "#.......aa.....................................#",
        "#...####aa.......................####..........#",
        "#...####.........................####..........#",
        "#..............................................#",
        "#..............................................#",
        "#........##.......................##...........#",
        "#........##..........S....S.......##...........#",
        "#......................FF......................#",
        "#......................FF......................#",
        "#....................S....S....................#",
        "#..............................................#",
        "#.....####............................##########",
        "#.....####............................#........#",
        "#.....................................#......C.#",
        "#...............................####..#........#",
        "#...............................####..#........#",
        "#...............................####..#........#",
        "#..............................................#",
        "################################################",
    )),
    "calabouco": ("SALA DA GUARDA", (
        "            #11#                #22#            ",
        "            #..#                #..#            ",
        "            #..#                #..#            ",
        "            #..#                #..#            ",
        "            #..#                #..#            ",
        "    #########..##################..#########    ",
        "    #........aa............................#    ",
        "    #........aa............................#    ",
        "    #.....##........................##.....#    ",
        "    #.....##.........S....S.........##.....#    ",
        "    #..................FF..................#    ",
        "    #..................FF..................#    ",
        "    #................S....S................#    ",
        "    #.....##........................##.....#    ",
        "    #.....##........................##.....#    ",
        "    #......................................#    ",
        "    #......................................#    ",
        "    ##################################..####    ",
        "                                     #..####### ",
        "                                     #......C.# ",
        "                                     #........# ",
        "                                     ########## ",
    )),
    "templo_gelado": ("SALÃO DE GELO", (
        "        ##11##                    ##22##        ",
        "        #....#                    #....#        ",
        "        #....#                    #....#        ",
        "        #....#                    #....#        ",
        "  #######....######################....#######  ",
        "  #.......aa.................................#  ",
        "  #.......aa.................................#  ",
        "  #......##..........................##......#  ",
        "  #......##..........................##......#  ",
        "  #..........................................#  ",
        "  #..................S....S..................#  ",
        "  #.....................FF...................#  ",
        "  #.....................FF...................#  ",
        "  #..................S....S..................#  ",
        "  #............##..............##............#  ",
        "  #............##..............##............#  ",
        "  ####.......................................#  ",
        "  ####.......................................#  ",
        "  ###..#######################################  ",
        "  #.......#                                     ",
        "  #.....C.#                                     ",
        "  #########                                     ",
    )),
}


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
