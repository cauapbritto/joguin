"""Fase 2: bloqueio de corpo, chutão e carrinho de bloqueio."""
import math
import unittest

from apoio import futebol, run

from soulstrike import config
from soulstrike.soccer_assist import closest_approach, segment_contact


class GeometriaTest(unittest.TestCase):
    def test_contato_continuo(self):
        # passou "por dentro" do círculo entre dois quadros: o contato é detectado
        self.assertAlmostEqual(segment_contact(0, 0, 100, 0, 50, 0, 10), 0.4)
        self.assertIsNone(segment_contact(0, 0, 100, 0, 50, 30, 10))
        self.assertEqual(segment_contact(48, 0, 60, 0, 50, 0, 10), 0.0)

    def test_aproximacao(self):
        t, d = closest_approach(0, 0, 10, 0, 100, 20, 30)
        self.assertAlmostEqual(t, 10)
        self.assertAlmostEqual(d, 20)


class BloqueioTest(unittest.TestCase):
    def _chute_em(self, offset_y, speed=12.0):
        match, _ = futebol()
        p1, p2 = match.fighters
        p1.x, p1.y = 300, 200                 # longe da jogada
        p2.x, p2.y = 1200, 450
        ball = match.ball
        ball.x, ball.y = 1100, 450 + offset_y
        ball.vx, ball.vy = speed, 0.0
        match.last_touch = p1
        return match, p2, ball

    def test_chute_forte_nao_atravessa(self):
        for offset in (0, 12, 22):
            match, p2, ball = self._chute_em(offset)
            run(match, 30)
            self.assertTrue(p2.block_hit, f"atravessou com desvio {offset}")
            self.assertLess(ball.x, p2.x + 40)

    def test_bloqueio_espirra_para_o_lado(self):
        match, p2, ball = self._chute_em(0)
        for _ in range(30):
            run(match, 1)
            if p2.block_hit:
                break
        speed = math.hypot(ball.vx, ball.vy)
        self.assertLess(speed, 12 * 0.5)                # perdeu força
        self.assertGreater(abs(ball.vy), abs(ball.vx))  # foi para o lado, não de volta

    def test_bola_lenta_so_rebate(self):
        match, p2, ball = self._chute_em(0, speed=4.0)
        run(match, 40)
        self.assertFalse(p2.block_hit)


class ChutaoTest(unittest.TestCase):
    def test_chutao_afasta_do_proprio_gol(self):
        match, inputs = futebol(humans=(1,))
        p1, p2 = match.fighters
        p2.x, p2.y = 1300, 200
        p1.x, p1.y = 200, 450                   # P1 defende o gol da esquerda (x=20)
        ball = match.ball
        ball.x, ball.y = 300, 470
        ball.vx = -7.0                           # chute vindo para o gol
        inputs[1].hold("attack")                 # apertou um pouco antes da bola chegar
        run(match, 20, inputs)
        self.assertGreater(ball.vx, 3)           # foi para frente
        self.assertIs(match.last_touch, p1)

    def test_cabecada_no_proprio_campo_afasta(self):
        match, _ = futebol()
        p1, p2 = match.fighters
        p1.x, p1.y = 200, 450
        p1.facing = (-1.0, 0.0)                   # olhando para o próprio gol
        ball = match.ball
        ball.x, ball.y, ball.z = 205, 450, 40
        self.assertTrue(match.header(p1))
        self.assertGreater(ball.vx, 0)

    def test_cabecada_respeita_a_recarga(self):
        match, _ = futebol()
        p1, _ = match.fighters
        p1.x, p1.y = 800, 450
        ball = match.ball
        ball.x, ball.y, ball.z = 805, 450, 30
        self.assertTrue(match.header(p1, (1.0, 0.0)))
        ball.x, ball.y, ball.z, ball.vz = 805, 450, 30, 0.0
        self.assertFalse(match.header(p1, (1.0, 0.0)))   # não cabeceia todo quadro

    def test_sem_chutao_no_campo_adversario(self):
        match, _ = futebol()
        p1, _ = match.fighters
        p1.x, p1.y = 1300, 450
        match.ball.x, match.ball.y = 1330, 450
        self.assertFalse(match.can_clear(p1))
        self.assertFalse(match.clear_ball(p1))


class CarrinhoTest(unittest.TestCase):
    def test_carrinho_bloqueia_chute_ao_lado(self):
        match, inputs = futebol(humans=(2,))
        p1, p2 = match.fighters
        p1.x, p1.y = 300, 200
        p2.x, p2.y = 1300, 450
        ball = match.ball
        ball.x, ball.y = 1060, 510                # vai passar 60 px ao lado do corpo
        ball.vx = 11.0
        inputs[2].tap("dodge")
        run(match, 1, inputs)
        self.assertGreater(p2.block_timer, 0)
        run(match, 30, inputs)
        self.assertTrue(p2.block_hit)
        self.assertFalse(p2.stunned)

    def test_carrinho_errado_fica_no_chao(self):
        match, inputs = futebol(humans=(2,))
        p1, p2 = match.fighters
        p1.x, p1.y = 300, 200
        p2.x, p2.y = 1300, 450
        ball = match.ball
        ball.x, ball.y, ball.vx = 1060, 520, 11.0
        inputs[2].tap("dodge")
        run(match, 1, inputs)
        ball.vx = ball.vy = 0.0                   # a bola "sumiu" do caminho
        ball.x, ball.y = 300, 800
        stunned = False
        for _ in range(config.BLOCK_FRAMES * 2 + 2):
            run(match, 1, inputs)
            stunned = stunned or p2.stunned
        self.assertTrue(stunned)

    def test_sem_bola_vindo_e_corte_normal(self):
        match, inputs = futebol(humans=(2,))
        _, p2 = match.fighters
        p2.x, p2.y = 1300, 450
        match.ball.x, match.ball.y = 300, 300
        inputs[2].tap("dodge")
        run(match, 1, inputs)
        self.assertEqual(p2.block_timer, 0)
        self.assertGreater(p2.dash_cd, 0)


if __name__ == "__main__":
    unittest.main()
