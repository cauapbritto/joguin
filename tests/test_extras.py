"""Etapa 7: tranco no gol e último fôlego na campanha solo."""
import unittest

from apoio import futebol
from test_campanha import campanha

from soulstrike.campaign import LAST_BREATH_FRAMES
from soulstrike.matches import GOAL_HITSTOP, GOAL_SLOWMO


class TrancoNoGolTest(unittest.TestCase):
    def test_gol_para_e_desacelera(self):
        match, _ = futebol()
        match._goal(0)
        self.assertEqual(match.hitstop, GOAL_HITSTOP)
        self.assertEqual(match.slowmo, GOAL_SLOWMO)
        frame = match.frame
        for _ in range(GOAL_HITSTOP):
            match.update()
        self.assertEqual(match.frame, frame)              # congelado
        for _ in range(GOAL_SLOWMO):
            match.update()
        self.assertEqual(match.frame - frame, GOAL_SLOWMO // 2)   # metade da velocidade

    def test_gol_que_decide_tambem_funciona(self):
        match, _ = futebol()
        for _ in range(10):
            match._goal(1)
            if getattr(match, "result_team", None) is not None:
                break
        for _ in range(400):
            match.update()
        self.assertTrue(match.finished)


class UltimoFolegoTest(unittest.TestCase):
    def test_sozinho_segura_um_golpe_fatal(self):
        match, _ = campanha(chars=("guerreiro",))
        p = match.players[0]
        p.invulnerable_timer = p.dash_timer = 0
        p.take_damage(p.hp + 50, match=match)
        self.assertEqual(p.hp, 1)
        self.assertTrue(match.breath_used)
        self.assertEqual(p.invulnerable_timer, LAST_BREATH_FRAMES)
        p.invulnerable_timer = 0
        p.take_damage(50, match=match)                    # só uma vez por masmorra
        self.assertEqual(p.hp, 0)

    def test_em_dupla_nao_tem(self):
        match, _ = campanha(chars=("guerreiro", "atirador"))
        p = match.players[0]
        p.invulnerable_timer = p.dash_timer = 0
        p.take_damage(p.hp + 50, match=match)
        self.assertEqual(p.hp, 0)

    def test_cada_masmorra_tem_o_seu(self):
        match, _ = campanha(chars=("guerreiro",), dungeon=1)
        self.assertFalse(match.breath_used)


if __name__ == "__main__":
    unittest.main()
