"""O MAPA do app: a fase ou a Casa num formato simples, que o celular desenha sem saber do jogo.

A partida que tem mapa (``fase.PhaseMatch`` e ``casa.HubMatch``) monta um ``PhoneMap`` em
``phone_map()``; a PlayScene publica no hub umas 6 vezes por segundo e o app busca no /api/mapa
enquanto o MAPA está aberto. Tudo em quadrados do mapa (o app escala para caber na tela):

    {"title", "sub", "w", "h",
     "boxes":   [{"x", "y", "w", "h", "fill", "line", "label", "mark", "done"}],   salas, corredores, cantos
     "marks":   [{"x", "y", "color", "kind", "label"}],    bancas, baú, portas (kind: dot, door, portal)
     "players": [{"x", "y", "slot", "color", "label", "down"}]}

Cores em "#rrggbb"; ``label`` e ``mark`` só com letras que a fonte do app tem (a mesma do jogo).
"""


def hex_color(color):
    return "#%02x%02x%02x" % tuple(int(c) for c in color[:3])


def _n(v):
    return round(float(v), 2)


class PhoneMap:
    def __init__(self, title, sub, w, h):
        self.data = {"title": title, "sub": sub, "w": _n(w), "h": _n(h), "boxes": [], "marks": [], "players": []}

    def box(self, x, y, w, h, fill=None, line=None, label=None, mark=None, done=False):
        self.data["boxes"].append({
            "x": _n(x), "y": _n(y), "w": _n(w), "h": _n(h),
            "fill": hex_color(fill) if fill else None, "line": hex_color(line) if line else None,
            "label": label, "mark": mark, "done": bool(done)})

    def mark(self, x, y, color, label=None, kind="dot"):
        self.data["marks"].append({"x": _n(x), "y": _n(y), "color": hex_color(color), "kind": kind,
                                   "label": label})

    def player(self, f, x, y):
        """Um ponto por jogador (na cor dele), com o apelido do app ou P1, P2..."""
        tag = f.tag_text() if hasattr(f, "tag_text") else getattr(f, "label", "")
        self.data["players"].append({"x": _n(x), "y": _n(y), "slot": getattr(f, "slot", 0) or 0,
                                     "color": hex_color(f.color), "label": tag,
                                     "down": not getattr(f, "alive_in_match", True)})

    def done(self):
        return self.data
