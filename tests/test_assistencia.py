"""Fase 4: passe na direção apontada, chute corrigido para o gol e domínio assistido."""
import math
import unittest

from apoio import futebol, run

from soulstrike.soccer_assist import ASSIST_LEVELS, shot_assist


def _com_bola(match, inputs, p, x, y):
    match.ball.x, match.ball.y = x + 30, y
    p.x, p.y = x, y
    run(match, 3, inputs)
    assert match.possessor is p


class PasseTest(unittest.TestCase):
    def _dois_x_dois(self, assist="media"):
        match, inputs = futebol(chars=(4, 2, 0, 7), humans=(1,))
        match.assist = ASSIST_LEVELS[assist]
        p1, p2, p3, p4 = match.fighters
        p2.x, p2.y, p4.x, p4.y = 1500, 100, 1500, 800
        _com_bola(match, inputs, p1, 700, 450)
        return match, inputs, p1, p3

    def test_passe_vai_para_quem_esta_na_direcao(self):
        match, inputs, p1, p3 = self._dois_x_dois()
        p3.x, p3.y = 700, 150                       # companheiro em cima
        inputs[1].stick = (0.0, -1.0)
        self.assertTrue(match.pass_ball(p1, direction=(0.0, -1.0)))
        self.assertIs(match.ball.homing_player, p3)
        self.assertLess(match.ball.vy, -3)

    def test_ninguem_na_direcao_passe_para_o_espaco(self):
        match, inputs, p1, p3 = self._dois_x_dois()
        p3.x, p3.y = 700, 150                       # companheiro em cima, apontou para baixo
        self.assertTrue(match.pass_ball(p1, direction=(0.0, 1.0)))
        self.assertEqual(match.ball.homing_timer, 0)
        self.assertGreater(match.ball.vy, 3)

    def test_sem_direcao_vai_para_o_mais_perto(self):
        match, inputs, p1, p3 = self._dois_x_dois()
        p3.x, p3.y = 900, 450
        self.assertTrue(match.pass_ball(p1))
        self.assertIs(match.ball.homing_player, p3)

    def test_desligada_vai_reto(self):
        match, inputs, p1, p3 = self._dois_x_dois("desligada")
        p3.x, p3.y = 760, 150                       # quase na direção, mas sem ajuda
        self.assertTrue(match.pass_ball(p1, direction=(0.0, -1.0)))
        self.assertEqual(match.ball.homing_timer, 0)
        self.assertAlmostEqual(match.ball.vx, 0.0, places=3)


class ChuteTest(unittest.TestCase):
    def test_chute_quase_no_gol_e_corrigido(self):
        top, bottom = 370, 530
        d = (1.0, 0.0)
        aim = math.atan2(260 - 450, 600)            # sairia por cima da trave
        d = (math.cos(aim), math.sin(aim))
        fixed = shot_assist(1000, 450, d, 1580, top, bottom, ASSIST_LEVELS["media"].shot_cone)
        t = (1580 - 1000) / fixed[0]
        self.assertTrue(top <= 450 + fixed[1] * t <= bottom)

    def test_chute_no_gol_nao_muda(self):
        d = (1.0, 0.05)
        self.assertEqual(shot_assist(1000, 450, d, 1580, 370, 530, 18), d)

    def test_chute_muito_errado_nao_vira_gol(self):
        d = (0.0, 1.0)                               # chutou para o lado
        self.assertEqual(shot_assist(1000, 450, d, 1580, 370, 530, 18), d)

    def test_chute_de_longe_nao_e_corrigido(self):
        aim = math.atan2(-300, 1300)
        d = (math.cos(aim), math.sin(aim))
        self.assertEqual(shot_assist(200, 450, d, 1580, 370, 530, 30), d)

    def test_chute_do_jogador_usa_a_assistencia(self):
        match, inputs = futebol(humans=(1,))
        p1, p2 = match.fighters
        p2.x, p2.y = 300, 100
        _com_bola(match, inputs, p1, 1100, 450)
        p1.facing = (math.cos(-0.33), math.sin(-0.33))   # um pouco para fora
        self.assertTrue(match.kick(p1, loft=0.0, assist=True))
        ball = match.ball
        t = (1580 - ball.x) / ball.vx
        self.assertTrue(match.GOAL_TOP <= ball.y + ball.vy * t <= match.GOAL_BOTTOM)


class DominioTest(unittest.TestCase):
    def _passa_perto(self, assist, cpu=False):
        match, inputs = futebol(humans=() if cpu else (1,))
        match.assist = ASSIST_LEVELS[assist]
        p1, p2 = match.fighters
        p2.x, p2.y = 1500, 100
        p1.x, p1.y = 800, 450
        ball = match.ball
        ball.x, ball.y = 600, 450 + 42                 # vai passar a 42 px do jogador
        ball.vx = 5.0
        run(match, 60, inputs)
        return match.possessor is p1

    def test_dominio_assistido_puxa_a_bola(self):
        self.assertTrue(self._passa_perto("alta"))

    def test_sem_assistencia_a_bola_passa(self):
        self.assertFalse(self._passa_perto("desligada"))

    def test_cpu_nao_tem_assistencia(self):
        self.assertFalse(self._passa_perto("alta", cpu=True))


if __name__ == "__main__":
    unittest.main()
