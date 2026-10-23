"""Ritmo do jogo: 60 atualizações por segundo mesmo quando o PC não desenha 60 quadros."""
import unittest

import pygame
from apoio import game

from soulstrike.game import FrameBudget


def updates_per_second(frame_ms, seconds=5):
    """Quantas atualizações a lógica faz por segundo com quadros de frame_ms."""
    budget = FrameBudget(60)
    total, elapsed = 0, 0.0
    while elapsed < seconds * 1000:
        total += 1 + budget.spend(frame_ms)
        elapsed += frame_ms
    return total / seconds


class RitmoTest(unittest.TestCase):
    def test_pc_rapido_nao_ganha_atualizacao_extra(self):
        budget = FrameBudget(60)
        extras = sum(budget.spend(ms) for ms in [16, 17, 17] * 200)   # clock.tick alterna 16 e 17 ms
        self.assertLessEqual(extras, 1)

    def test_pc_lento_alcanca_o_relogio(self):
        for ms in (20, 25, 33.4, 40):
            self.assertAlmostEqual(updates_per_second(ms), 60, delta=1.5, msg=f"{ms} ms por quadro")

    def test_pc_muito_lento_fica_lento_mas_nao_trava(self):
        budget = FrameBudget(60)
        self.assertEqual(budget.spend(500), FrameBudget.MAX_CATCHUP)
        self.assertLessEqual(budget.spend(16.7), 1)                    # não acumula a dívida

    def test_engasgo_isolado(self):
        budget = FrameBudget(60)
        self.assertEqual(budget.spend(50), 2)                          # um quadro de 50 ms = 3 atualizações
        self.assertEqual(budget.spend(16.67), 0)


class AtualizarSemDesenharTest(unittest.TestCase):
    def test_update_sem_draw(self):
        g = game()
        ticks = g.clock_ticks
        g.update([])
        g.update([])
        g.draw()
        self.assertEqual(g.clock_ticks, ticks + 2)

    def test_f3_mostra_fps(self):
        g = game()
        g.step([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F3, mod=0, unicode="")])
        self.assertTrue(g.show_fps)
        g.draw()
        g.step([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F3, mod=0, unicode="")])
        self.assertFalse(g.show_fps)


if __name__ == "__main__":
    unittest.main()
