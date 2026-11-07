"""Os enfeites de cada capítulo na abertura, nos corredores e na sala de recompensas da fase."""
import unittest
from collections import deque

from test_masmorra import corrida

from soulstrike import enfeites, lobbies
from soulstrike.campaign import PHASES
from soulstrike.casa import Decor
from soulstrike.fase import PhaseMatch
from soulstrike.mapa_fase import PhaseLayout

ROOMS = [(phase.key, PhaseLayout.of(phase).rows) for phase in PHASES]


def reachable(grid, start, blocked):
    h, w = len(grid), len(grid[0])
    seen, todo = {start}, deque([start])
    while todo:
        x, y = todo.popleft()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= ny < h and 0 <= nx < w and (nx, ny) not in seen and grid[ny][nx] not in "# " \
                    and (nx, ny) not in blocked:
                seen.add((nx, ny))
                todo.append((nx, ny))
    return seen


class EnfeitesTest(unittest.TestCase):
    def test_enfeites_nao_fecham_caminho(self):
        for name, rows in ROOMS:
            grid = lobbies.grid_of(rows)
            blocked = enfeites.blocked_cells(rows)
            start = next((x, y) for y, row in enumerate(grid) for x, ch in enumerate(row) if ch == "S")
            before = reachable(grid, start, set())
            after = reachable(grid, start, blocked)
            self.assertEqual(before - blocked, after, name)
            for y, row in enumerate(grid):                  # nenhum enfeite em cima de porta ou marcador
                for x, ch in enumerate(row):
                    if ch in lobbies.MARKERS:
                        self.assertNotIn((x, y), blocked, (name, ch))

    def test_cada_fase_tem_enfeites_e_a_piada(self):
        for phase in PHASES:
            rows = PhaseLayout.of(phase).rows
            ground, wall = enfeites.spots(rows)
            self.assertGreaterEqual(len(ground), 4, phase.key)
            self.assertGreaterEqual(len(wall), 2, phase.key)
            pieces = [fn for fn, *_ in enfeites.layout(rows, phase.chapter)]
            self.assertEqual(pieces.count(enfeites.joke_sign), 1, phase.key)
            walls, floors, _, _ = enfeites.chapter_set(phase.chapter)
            self.assertTrue(set(pieces) - {enfeites.joke_sign} <= set(walls) | set(floors), phase.key)

    def test_partida_com_enfeites_e_largada_livre(self):
        seen = set()
        for k, phase in enumerate(PHASES):
            if phase.chapter in seen:
                continue
            seen.add(phase.chapter)
            g, run = corrida(phase=k)
            match = PhaseMatch(g, run)
            decor = [p for p in match.props if isinstance(p, Decor)]
            self.assertTrue(decor, phase.key)
            for p in match.players:
                self.assertTrue(match.arena.is_free(p.x, p.y, 12), phase.key)
            match.update()
            match.draw(g.screen, g.ui)


if __name__ == "__main__":
    unittest.main()
