"""Paredes que se encostam viram uma forma só (cantos fechados), sem mudar a colisão."""
import unittest

import pygame

import apoio  # noqa: F401  (janela falsa e progresso temporário)
from soulstrike import scenery
from soulstrike.entities import Wall
from soulstrike.scenery import wall_style


def _paredes(*rects, key="clinica"):
    style = wall_style(key)
    ws = []
    for r in rects:
        w = Wall(*r)
        w.style = style
        ws.append(w)
    return ws


class JuntarTest(unittest.TestCase):
    def test_canto_em_l_junta_e_peca_solta_nao(self):
        canto = _paredes((0, 0, 300, 40), (0, 40, 40, 200))
        solta = _paredes((600, 600, 80, 40))[0]
        solta.style = canto[0].style
        scenery.join_walls(canto + [solta])
        self.assertTrue(all(w.joined for w in canto))
        self.assertFalse(solta.joined)
        self.assertEqual(canto[0].rect, pygame.Rect(0, 0, 300, 40))      # colisão igual

    def test_o_desenho_cobre_o_retangulo_e_a_sombra(self):
        canto = _paredes((0, 0, 300, 40), (0, 40, 40, 200))
        scenery.join_walls(canto)
        for w in canto:
            self.assertTrue(w.area.contains(w.rect))
            self.assertGreaterEqual(w.area.bottom, w.rect.bottom + scenery.JOIN_BELOW)

    def test_sem_emenda_no_canto(self):
        """O pixel do canto, visto pelos dois pedaços, é o mesmo."""
        canto = _paredes((0, 0, 300, 40), (0, 40, 40, 200))
        scenery.join_walls(canto)
        a, b = canto
        x, y = 20, 46                       # dentro da vertical, logo abaixo da horizontal
        pa = a._drawn.get_at((x - a.rect.x - a.draw_offset[0], y - a.rect.y - a.draw_offset[1]))
        pb = b._drawn.get_at((x - b.rect.x - b.draw_offset[0], y - b.rect.y - b.draw_offset[1]))
        self.assertEqual(pa, pb)

    def test_frente_da_parede_embaixo_do_trecho(self):
        """Embaixo do trecho horizontal aparece a frente (a faixa do estilo), não o topo liso."""
        canto = _paredes((0, 0, 300, 40), (0, 40, 40, 200))
        scenery.join_walls(canto)
        a = canto[0]
        top = a._drawn.get_at((150 - a.draw_offset[0], 4 - a.draw_offset[1]))
        face = [a._drawn.get_at((150 - a.draw_offset[0], y - a.draw_offset[1])) for y in range(14, 40)]
        self.assertTrue(any(c != top for c in face))


if __name__ == "__main__":
    unittest.main()
