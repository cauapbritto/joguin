"""As salas de luta mobiliadas: móveis do capítulo encostados nas paredes, poças de luz no chão, e
nada disso fechando porta ou caminho."""
import unittest

from test_fase_mapa import alcance, fase

from soulstrike import enfeites
from soulstrike.campaign import PHASES


def _first_of_each_chapter():
    first = {}
    for i, phase in enumerate(PHASES):
        first.setdefault(phase.chapter, i)
    return sorted(first.items())


class SalasTest(unittest.TestCase):
    def test_moveis_e_luz_em_toda_sala_de_luta(self):
        for chapter, k in _first_of_each_chapter():
            match, _ = fase(k)
            names = {n for n, _ in enfeites.ROOM_SETS[chapter][0]}
            for room in match.layout.fight_rooms:
                pieces = [p for p in match.props if isinstance(p, enfeites._Piece) and room.rect.collidepoint(p.x, p.y)]
                pools = [p for p in match.props if isinstance(p, enfeites.LightPool)
                         and room.rect.collidepoint(p.x, p.y)]
                self.assertGreaterEqual(len(pieces), 2, (chapter, room.key))
                self.assertEqual(len(pools), 3, (chapter, room.key))
            self.assertTrue(names, chapter)

    def test_moveis_longe_das_portas(self):
        for chapter, k in _first_of_each_chapter():
            match, _ = fase(k)
            pieces = [p for p in match.props if isinstance(p, enfeites._Piece)]
            for room in match.layout.fight_rooms:
                for _, door in room.doors:
                    near = door.inflate(2 * enfeites.T, 2 * enfeites.T)
                    self.assertFalse(any(near.collidepoint(p.x, p.y) for p in pieces), (chapter, room.key))

    def test_portas_e_salas_alcancaveis_com_os_moveis(self):
        for chapter, k in _first_of_each_chapter():
            match, _ = fase(k)
            for door in match.doors:
                door.state, door.bars = "open", 0.0
                door.sync_wall(match.arena)
            reach = alcance(match.arena, (match.players[0].x, match.players[0].y))
            pts = [(x * 20, y * 20) for x, y in reach]
            for room in match.layout.fight_rooms:
                for _, door in room.doors:
                    self.assertTrue(any(door.inflate(40, 40).collidepoint(p) for p in pts), (chapter, room.key))
                inside = sum(1 for p in pts if room.rect.collidepoint(p))
                total = (room.rect.w // 20) * (room.rect.h // 20)
                self.assertGreater(inside / total, 0.6, (chapter, room.key))

    def test_sem_arte_nao_mobilia(self):
        from soulstrike import pecas
        old = dict(pecas._cache)
        try:
            for name, _ in enfeites.ROOM_SETS[1][0]:
                pecas._cache[name] = None
            match, _ = fase(0)
            self.assertFalse(any(isinstance(p, enfeites._Piece) for p in match.props))
        finally:
            pecas._cache.clear()
            pecas._cache.update(old)


if __name__ == "__main__":
    unittest.main()
