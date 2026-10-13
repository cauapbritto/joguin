"""Fase 5: teclas do futebol, duplo toque e comandos novos do celular."""
import unittest

import pygame
from apoio import game

from soulstrike.controls import PlayerInput
from soulstrike.net.remote import RemoteHub


class _Keys:
    def __init__(self, *down):
        self.down = set(down)

    def __getitem__(self, code):
        return code in self.down


def _frame(inp, down=(), pressed=(), now=0, remote_held=(), remote_pressed=()):
    inp.update(_Keys(*down), set(pressed), set(remote_held), set(remote_pressed), now)


class LayoutTest(unittest.TestCase):
    def test_futebol_tem_correr_e_marcar(self):
        inp = PlayerInput(1)
        inp.set_layout("soccer")
        _frame(inp, down=(pygame.K_LSHIFT, pygame.K_r))
        self.assertTrue(inp.held("sprint"))
        self.assertTrue(inp.held("mark"))
        self.assertFalse(inp.held("dodge"))           # SHIFT não corta enquanto corre
        _frame(inp, down=(pygame.K_SPACE,), pressed=(pygame.K_SPACE,))
        self.assertTrue(inp.pressed("dodge"))

    def test_duelo_volta_ao_normal(self):
        inp = PlayerInput(1)
        inp.set_layout("soccer")
        inp.set_layout("battle")
        _frame(inp, down=(pygame.K_LSHIFT,))
        self.assertTrue(inp.held("dodge"))
        self.assertFalse(inp.held("sprint"))

    def test_jogador_2_no_futebol(self):
        inp = PlayerInput(2)
        inp.set_layout("soccer")
        _frame(inp, down=(pygame.K_RSHIFT, pygame.K_RETURN, pygame.K_l))
        self.assertTrue(inp.held("sprint") and inp.held("mark") and inp.held("dribble"))

    def test_partida_escolhe_o_layout(self):
        g = game()
        from soulstrike.matches import SoccerMatch
        from soulstrike.session import Session, SlotSetup
        g.session = Session("soccer1", [SlotSetup(1, char=0), SlotSetup(2, char=1)])
        SoccerMatch(g, g.session)
        self.assertEqual(g.inputs[1].layout, "soccer")
        self.assertEqual(g.inputs[2].layout, "soccer")


class DuploToqueTest(unittest.TestCase):
    def tearDown(self):
        PlayerInput.double_tap_enabled = True

    def test_duplo_toque_no_teclado(self):
        inp = PlayerInput(1)
        _frame(inp, pressed=(pygame.K_d,), now=1000)
        _frame(inp, pressed=(pygame.K_d,), now=1150)
        self.assertEqual(inp.double_tap, (1, 0))

    def test_celular_nao_gera_duplo_toque(self):
        inp = PlayerInput(2)
        _frame(inp, remote_pressed=("p2_right",), now=1000)
        _frame(inp, remote_pressed=("p2_right",), now=1100)
        self.assertIsNone(inp.double_tap)              # analógico indo e voltando não esquiva

    def test_duplo_toque_desligado(self):
        PlayerInput.double_tap_enabled = False
        inp = PlayerInput(1)
        _frame(inp, pressed=(pygame.K_d,), now=1000)
        _frame(inp, pressed=(pygame.K_d,), now=1150)
        self.assertIsNone(inp.double_tap)


class ComandosNovosTest(unittest.TestCase):
    def test_celular_manda_correr_e_marcar(self):
        hub = RemoteHub()
        hub.apply_input(4, "s", 1, ["sprint", "mark"], {"sprint": 1, "mark": 1})
        held, _ = hub.poll()
        self.assertEqual(held, {"p4_sprint", "p4_mark"})


if __name__ == "__main__":
    unittest.main()
