"""Dobro de detalhe para a pixel art gerada (personagens e armas).

O desenho base continua sendo feito em pixels grandes; daqui sai a versão com o dobro de pixels,
do mesmo tamanho na tela: bordas arredondadas (Scale2x), volume em cada parte com luz de cima e
da esquerda, brilho no metal e contorno fino.
"""
import pygame

NEAR_TONE = 60            # diferença de cor (soma dos canais) até onde é o mesmo material
HD_SKIP = 10              # partes menores que isso (olho, botão, relógio) não ganham volume


def _grid(surf):
    w, h = surf.get_size()
    return [[tuple(surf.get_at((x, y))) for x in range(w)] for y in range(h)], w, h


def scale2x(src, guide=None):
    """Dobra a imagem arredondando os degraus das diagonais (algoritmo Scale2x / EPX).
    ``guide``: imagem que decide os arredondamentos (o uniforme usa o desenho normal, para a
    silhueta sair igualzinha e só a cor da roupa mudar)."""
    a, w, h = _grid(src)
    g = _grid(guide)[0] if guide is not None else a
    out = pygame.Surface((w * 2, h * 2), pygame.SRCALPHA)
    clear = (0, 0, 0, 0)

    def at(x, y):
        return g[y][x] if 0 <= x < w and 0 <= y < h else clear

    def src_at(x, y):
        return a[y][x] if 0 <= x < w and 0 <= y < h else clear
    for y in range(h):
        for x in range(w):
            e, b, d, f, hh = at(x, y), at(x, y - 1), at(x - 1, y), at(x + 1, y), at(x, y + 1)
            e0 = e1 = e2 = e3 = (x, y)
            if b != hh and d != f:
                if d == b:
                    e0 = (x - 1, y)
                if b == f:
                    e1 = (x + 1, y)
                if d == hh:
                    e2 = (x - 1, y)
                if hh == f:
                    e3 = (x + 1, y)
            out.set_at((2 * x, 2 * y), src_at(*e0))
            out.set_at((2 * x + 1, 2 * y), src_at(*e1))
            out.set_at((2 * x, 2 * y + 1), src_at(*e2))
            out.set_at((2 * x + 1, 2 * y + 1), src_at(*e3))
    return out


def volume(src, shade, keep=()):
    """Cada parte (pixels vizinhos da mesma cor) ganha borda clara em cima e à esquerda e escura
    embaixo e à direita, em dois degraus: a roupa e a pele deixam de ser chapadas.
    ``shade(cor, quanto)``: clareia/escurece (cada gerador tem o seu jeito de puxar o matiz).
    ``keep``: cores que não mudam (os olhos que acendem na alma corrompida)."""
    a, w, h = _grid(src)
    out = src.copy()
    keep = {tuple(k[:3]) for k in keep}

    def same(x, y, col):
        return 0 <= x < w and 0 <= y < h and a[y][x] == col

    def near(x, y, col):
        """Mesmo material: a cor vizinha é só um tom acima ou abaixo (dobra, costura)."""
        if not (0 <= x < w and 0 <= y < h):
            return False
        other = a[y][x]
        return other[3] > 0 and sum(abs(other[i] - col[i]) for i in range(3)) < NEAR_TONE
    region, sizes = {}, []
    for y in range(h):
        for x in range(w):
            if a[y][x][3] == 0 or (x, y) in region:
                continue
            col, todo, n = a[y][x], [(x, y)], 0
            region[x, y] = len(sizes)
            while todo:
                px_, py_ = todo.pop()
                n += 1
                for nx, ny in ((px_ + 1, py_), (px_ - 1, py_), (px_, py_ + 1), (px_, py_ - 1)):
                    if same(nx, ny, col) and (nx, ny) not in region:
                        region[nx, ny] = len(sizes)
                        todo.append((nx, ny))
            sizes.append(n)
    for y in range(h):
        for x in range(w):
            col = a[y][x]
            if col[3] == 0 or sizes[region[x, y]] < HD_SKIP or col[:3] in keep:
                continue
            amount = 0
            if not near(x, y - 1, col):
                amount += 14
            elif not near(x, y - 2, col):
                amount += 6
            if not near(x - 1, y, col):
                amount += 8
            if not near(x, y + 1, col):
                amount -= 16
            elif not near(x, y + 2, col):
                amount -= 7
            if not near(x + 1, y, col):
                amount -= 10
            if amount >= 22 and max(col[:3]) - min(col[:3]) < 36 and sum(col[:3]) > 420:
                out.set_at((x, y), (250, 250, 244, col[3]))           # metal: brilho no canto da luz
            elif amount:
                out.set_at((x, y), (*shade(col, amount), col[3]))
    return out


def fine_outline(src):
    """Contorno de 1 pixel do dobro (metade da grossura do contorno de sempre, na tela)."""
    w, h = src.get_size()
    out = src.copy()
    get = src.get_at
    for y in range(h):
        for x in range(w):
            if get((x, y))[3]:
                continue
            best, lit = None, True
            for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if 0 <= nx < w and 0 <= ny < h:
                    col = get((nx, ny))
                    if col[3]:
                        if ny != y + 1:
                            lit = False
                        if best is None or sum(col[:3]) < sum(best[:3]):
                            best = col
            if best is not None:
                k = 0.34 if lit else 0.2
                out.set_at((x, y), (int(best[0] * k) + 10, int(best[1] * k) + 7, int(best[2] * k) + 14, 255))
    return out
