"""Cruzamento no 2x2: da ponta, no último terço, para o companheiro entrando na área."""
import math
import unittest

from apoio import futebol, run

from soulstrike import config
from soulstrike.ai import SoccerAI


def _ponta(humans=(1, 3)):
    """P1 (time azul, ataca para a direita) com a bola na ponta; P3 entrando na área."""
    match, inputs = futebol(chars=(4, 2, 0, 7), humans=humans)
    p1, p2, p3, p4 = match.fighters
    p2.x, p2.y, p4.x, p4.y = 400, 800, 300, 100          # adversários longe
    p1.x, p1.y = 1250, 180
    match.ball.x, match.ball.y = 1280, 180
    run(match, 3, inputs)
    assert match.possessor is p1
    p3.x, p3.y = 1330, 430
    p3.prev_pos = (1327, 430)                             # correndo para o gol
    return match, inputs, p1, p3


def _texts(match):
    return [p.text for p in match.popups]


class CruzamentoTest(unittest.TestCase):
    def test_passe_alto_da_ponta_vira_cruzamento_na_cabeca(self):
        match, inputs, p1, p3 = _ponta()
        self.assertTrue(match.pass_ball(p1, high=True))
        self.assertIn("CRUZAMENTO", _texts(match))
        ball = match.ball
        hit = None
        for _ in range(90):
            prev_z = ball.z
            ball.update(match)
            if prev_z > config.CROSS_HEIGHT >= ball.z and ball.vz < 0:
                hit = (ball.x, ball.y)
                break
        self.assertIsNotNone(hit, "a bola não chegou na altura da cabeça")
        x, y = hit
        self.assertTrue(match.in_cross_zone(0, x, y), f"chegou fora da área: {hit}")

    def test_passe_normal_da_ponta_vira_cruzamento_rasteiro(self):
        match, inputs, p1, p3 = _ponta()
        self.assertTrue(match.pass_ball(p1, high=False))
        self.assertIn("CRUZAMENTO", _texts(match))
        self.assertIs(match.ball.homing_player, p3)
        self.assertEqual(match.ball.z, 0)
        self.assertAlmostEqual(math.hypot(match.ball.vx, match.ball.vy), config.CROSS_LOW_POWER, places=3)

    def test_apontar_para_tras_e_recuo(self):
        match, inputs, p1, p3 = _ponta()
        self.assertTrue(match.pass_ball(p1, direction=(-1.0, 0.0)))
        self.assertNotIn("CRUZAMENTO", _texts(match))

    def test_no_meio_do_campo_nao_cruza(self):
        match, inputs, p1, p3 = _ponta()
        p1.y = match.ball.y = 450
        self.assertIsNone(match.cross_receiver(p1, [p3]))

    def test_ninguem_na_area_nao_cruza(self):
        match, inputs, p1, p3 = _ponta()
        p3.x, p3.y = 900, 450
        p3.prev_pos = (900, 450)
        self.assertIsNone(match.cross_receiver(p1, [p3]))

    def test_1x1_nao_cruza(self):
        match, inputs = futebol(humans=(1,))
        p1, _ = match.fighters
        p1.x, p1.y = 1250, 180
        self.assertIsNone(match.cross_receiver(p1, []))

    def test_cabecada_na_area_vai_no_gol(self):
        match, inputs, p1, p3 = _ponta()
        match.possessor = None
        p3.x, p3.y = 1420, 420
        p3.facing = (0.0, 1.0)                            # olhando para o lado
        ball = match.ball
        ball.x, ball.y, ball.z = 1425, 420, 40
        self.assertTrue(match.header(p3))
        t = (1580 - ball.x) / ball.vx
        self.assertTrue(match.GOAL_TOP <= ball.y + ball.vy * t <= match.GOAL_BOTTOM)

    def test_cabecada_no_gol_passa_por_baixo_do_travessao(self):
        match, inputs, p1, p3 = _ponta()
        match.possessor = None
        p1.x, p1.y = 300, 100
        p3.x, p3.y = 1440, 440
        ball = match.ball
        ball.x, ball.y, ball.z, ball.vz = 1445, 440, 40, -1.0
        self.assertTrue(match.header(p3, (1.0, 0.0)))
        for _ in range(60):
            run(match, 1, inputs)
            if match.score[0]:
                break
        self.assertEqual(match.score[0], 1)

    def test_cpu_entra_na_area_quando_o_companheiro_vai_para_a_ponta(self):
        match, inputs, p1, p3 = _ponta(humans=(1,))
        match.controllers[p3] = SoccerAI()
        p3.x, p3.y = 1000, 600
        p3.prev_pos = (1000, 600)
        for _ in range(90):
            p1.x, p1.y = 1250, 180                        # P1 segura a bola na ponta
            match.possessor = p1
            run(match, 1, inputs)
        self.assertTrue(match.in_cross_zone(0, p3.x, p3.y), (p3.x, p3.y))


if __name__ == "__main__":
    unittest.main()
