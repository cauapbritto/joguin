"""Passe do futebol igual ao do basquete: sai na hora, sem carregar força, e vai teleguiado."""
import unittest

from apoio import Parado, futebol, run

from soulstrike import config


def _com_bola(match, inputs, p, x, y):
    match.ball.x, match.ball.y = x + 30, y
    p.x, p.y = x, y
    run(match, 3, inputs)
    assert match.possessor is p


class Correndo(Parado):
    def update(self, me, match):
        me.steer(0, 1)


class PasseTeleguiadoTest(unittest.TestCase):
    def _dois_x_dois(self):
        match, inputs = futebol(chars=(4, 2, 0, 7), humans=(1,))
        p1, p2, p3, p4 = match.fighters
        p2.x, p2.y, p4.x, p4.y = 1500, 100, 1500, 800
        _com_bola(match, inputs, p1, 600, 450)
        return match, inputs, p1, p3

    def test_aperto_sai_na_hora_sem_barra(self):
        match, inputs, p1, p3 = self._dois_x_dois()
        p3.x, p3.y = 900, 450
        inputs[1].tap("special")
        run(match, 1, inputs)
        self.assertIsNot(match.possessor, p1)
        self.assertIs(match.ball.homing_player, p3)
        self.assertEqual(p1.pass_charge, 0)

    def test_chega_no_companheiro_que_corre(self):
        match, inputs, p1, p3 = self._dois_x_dois()
        p3.x, p3.y = 950, 300
        self.assertTrue(match.pass_ball(p1, high=None, direction=(1.0, -0.4)))
        match.controllers[p3] = Correndo()           # corre para baixo enquanto a bola vem
        for _ in range(120):
            run(match, 1, inputs)
            if match.possessor is p3:
                break
        self.assertIs(match.possessor, p3)

    def test_passe_para_tras_nao_bate_em_quem_passou(self):
        match, inputs, p1, p3 = self._dois_x_dois()
        p1.facing = (1.0, 0.0)                       # bola na frente, companheiro atrás
        p3.x, p3.y = 300, 470
        self.assertTrue(match.pass_ball(p1, high=None, direction=(-1.0, 0.0)))
        for _ in range(90):
            run(match, 1, inputs)
            if match.possessor is not None:
                break
        self.assertIs(match.possessor, p3)

    def test_longe_vira_lancamento(self):
        match, inputs, p1, p3 = self._dois_x_dois()
        p3.x, p3.y = 600 + config.PASS_LOB_DIST + 80, 450
        self.assertTrue(match.auto_lob(p1, p3))

    def test_adversario_no_meio_vai_por_cima(self):
        match, inputs, p1, p3 = self._dois_x_dois()
        p3.x, p3.y = 900, 450
        p2 = match.fighters[1]
        self.assertFalse(match.auto_lob(p1, p3))
        p2.x, p2.y = 750, 455
        self.assertTrue(match.auto_lob(p1, p3))


if __name__ == "__main__":
    unittest.main()
