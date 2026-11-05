"""Pênaltis 1 x 1: um herói de cada lado, sem a tela da ordem, e a CPU entra se faltar o P2."""
import unittest

import pygame
from apoio import game

from soulstrike import stats
from soulstrike.data import CHARACTERS
from soulstrike.scenes import penalty as S
from soulstrike.scenes.menus import category_of
from soulstrike.session import MODES, Session, SlotSetup

INDEX = {c.key: i for i, c in enumerate(CHARACTERS)}


def sessao(p2_cpu=False):
    return Session("penaltis1", [SlotSetup(1, char=INDEX["matador"]),
                                 SlotSetup(2, char=INDEX["ninja"], cpu=p2_cpu)])


class Penaltis1x1Test(unittest.TestCase):
    def test_modo_no_menu_do_futebol(self):
        self.assertEqual(MODES["penaltis1"]["slots"], 2)
        self.assertTrue(MODES["penaltis1"]["penalty"])
        self.assertFalse(MODES["penaltis1"].get("teams", False))
        self.assertTrue(sessao().fill_cpu)
        self.assertEqual(category_of("penaltis1"), "futebol")
        self.assertEqual(stats.category("penaltis1"), "futebol")

    def test_um_contra_um_sem_tela_da_ordem(self):
        g = game()
        g.session = sessao()
        scene = S.start_penalties(g)
        self.assertEqual(scene.mode, "penaltis")          # a mesma disputa: 5 para cada lado e morte súbita
        self.assertEqual([len(t) for t in scene.teams], [1, 1])
        self.assertEqual(scene.teams[0][0].key, "matador")
        self.assertEqual(scene.teams[1][0].key, "ninja")
        self.assertEqual(scene.teams[0][0].slot, 1)
        self.assertEqual(scene.teams[1][0].slot, 2)
        self.assertNotEqual(scene.state, "ordem")
        # quem bate num lado é quem defende no outro
        kick = scene.kick
        self.assertEqual({kick.kicker.team, kick.keeper.team}, {0, 1})

    def test_sem_p2_a_cpu_vai_para_o_gol(self):
        g = game()
        g.session = sessao(p2_cpu=True)
        scene = S.start_penalties(g)
        self.assertTrue(scene.teams[1][0].cpu)
        self.assertFalse(scene.teams[0][0].cpu)
        scene.draw(pygame.Surface((960, 540)))


if __name__ == "__main__":
    unittest.main()
