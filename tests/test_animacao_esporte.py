"""Animações do futebol (v1.7): só desenho, nenhuma regra muda."""
import unittest

from apoio import GOL_D, MEIO, futebol, run

from soulstrike import matches as M


class FutebolAnimacaoTest(unittest.TestCase):
    def test_chute_tem_tres_quadros_e_volta_ao_normal(self):
        match, _ = futebol()
        f = match.fighters[0]
        match.ball.reset(f.x + 30, f.y)
        f.facing = (1.0, 0.0)
        self.assertTrue(match.kick(f, (1.0, 0.0)))
        poses = []
        for _ in range(14):
            run(match, 1)
            poses.append(f._pose())
        self.assertIn(("chute", 1), poses)
        self.assertIn(("chute", 2), poses)
        self.assertNotEqual(poses[-1][0], "chute")

    def test_chute_forte_deixa_rastro(self):
        match, _ = futebol()
        f = match.fighters[0]
        match.ball.reset(f.x + 30, f.y)
        match.kick(f, (1.0, 0.0), loft=1.0)
        run(match, 3)
        self.assertTrue(match.ball.trail)

    def test_carrinho_deita_e_levanta(self):
        match, _ = futebol()
        f = match.fighters[1]
        f.block_timer = 8
        match._animate(f)
        self.assertEqual(f._pose(), ("carrinho", 0))
        self.assertNotEqual(f.spin, 0)
        f.block_timer = 0
        match._animate(f)
        self.assertEqual(f.spin, 0)

    def test_gol_estufa_a_rede_e_o_time_comemora(self):
        match, _ = futebol()
        f = match.fighters[0]
        match.last_touch = f
        match.ball.reset(GOL_D + 30, MEIO)
        run(match, 3)
        self.assertEqual(match.score[0], 1)
        self.assertGreater(match.goals[1].bulge, 0)
        self.assertGreater(f.celebrate, 0)
        run(match, M.NET_BULGE * 3)                       # (com a câmera lenta do gol)
        self.assertEqual(match.goals[1].bulge, 0)


if __name__ == "__main__":
    unittest.main()
