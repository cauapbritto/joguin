"""Fase 3: CORRER (com fôlego) e MARCAR."""
import math
import unittest

from apoio import MEIO, futebol, run

from soulstrike import config


def _distancia_em(match, inputs, frames, *hold):
    p1 = match.fighters[0]
    x0 = p1.x
    inputs[1].stick = (1.0, 0.0)
    inputs[1].hold(*hold)
    run(match, frames, inputs)
    return p1.x - x0


class CorrerTest(unittest.TestCase):
    def _campo(self):
        match, inputs = futebol(humans=(1,))
        p1, p2 = match.fighters
        p1.x, p1.y = 300, 300
        p2.x, p2.y = 1400, 800
        match.ball.x, match.ball.y = 800, 900
        return match, inputs

    def test_correr_e_mais_rapido(self):
        andando = _distancia_em(*self._campo(), 60)
        correndo = _distancia_em(*self._campo(), 60, "sprint")
        self.assertGreater(correndo, andando * 1.25)

    def test_folego_acaba_e_volta(self):
        match, inputs = self._campo()
        p1 = match.fighters[0]
        _distancia_em(match, inputs, int(config.SPRINT_SECONDS * config.FPS) + 30, "sprint")
        self.assertTrue(p1.exhausted)
        self.assertFalse(p1.sprinting)
        inputs[1].release("sprint")
        inputs[1].stick = (0.0, 0.0)
        run(match, int(config.SPRINT_RECOVER_SECONDS * config.FPS * config.SPRINT_RESUME) + 10, inputs)
        self.assertFalse(p1.exhausted)

    def test_correndo_com_a_bola_ela_vai_mais_solta(self):
        def frente(sprint):
            match, inputs = futebol(humans=(1,))
            p1, p2 = match.fighters
            p1.x, p1.y = 300, 450
            p2.x, p2.y = 1400, 100
            match.ball.x, match.ball.y = 330, 450
            run(match, 3, inputs)
            self.assertIs(match.possessor, p1)
            inputs[1].stick = (1.0, 0.0)
            if sprint:
                inputs[1].hold("sprint")
            gaps = []
            for _ in range(80):
                run(match, 1, inputs)
                gaps.append(match.ball.x - p1.x)
            self.assertIs(match.possessor, p1)        # não perde a bola sozinho
            return sum(gaps[-30:]) / 30
        self.assertGreater(frente(True), frente(False) + 5)

    def test_correndo_e_mais_facil_roubar(self):
        self.assertLess(config.SPRINT_STEAL_FRAMES, config.STEAL_FRAMES)


class MarcarTest(unittest.TestCase):
    def test_vai_atras_da_bola_solta(self):
        match, inputs = futebol(humans=(1,))
        p1, p2 = match.fighters
        p1.x, p1.y = 700, 300
        p2.x, p2.y = 1500, 900
        match.ball.x, match.ball.y = 1000, 500
        inputs[1].hold("mark")
        run(match, 90, inputs)
        self.assertTrue(match.possessor is p1 or p1.distance_to(match.ball) < 50)

    def test_fica_entre_o_atacante_e_o_gol_sem_roubar(self):
        match, inputs = futebol(humans=(1,))
        p1, p2 = match.fighters                      # P1 defende o gol da esquerda
        p2.x, p2.y = 800, 300
        p2.facing = (-1.0, 0.0)
        match.ball.x, match.ball.y = 770, 300
        p1.x, p1.y = 1100, 700                       # começa longe, do lado errado
        run(match, 3, inputs)
        self.assertIs(match.possessor, p2)
        inputs[1].hold("mark")
        run(match, 150, inputs)                      # (com bola, a velocidade fica mais perto da média)
        gx, gy = match.goal_center(0)
        # P1 está no caminho entre o atacante e o gol
        ax, ay = gx - p2.x, gy - p2.y
        t = ((p1.x - p2.x) * ax + (p1.y - p2.y) * ay) / (ax * ax + ay * ay)
        px, py = p2.x + ax * t, p2.y + ay * t
        self.assertTrue(0 < t < 0.5)
        self.assertLess(math.hypot(p1.x - px, p1.y - py), 25)
        self.assertIs(match.possessor, p2)           # marcar sozinho não toma a bola

    def test_perto_do_gol_vira_goleiro(self):
        match, inputs = futebol(humans=(1,))
        p1, p2 = match.fighters
        p2.x, p2.y = 1500, MEIO + 450
        p1.x, p1.y = 300, MEIO + 300                 # vem de baixo, sem passar pela bola
        match.ball.x, match.ball.y = 260, MEIO - 150  # bola perto do gol da esquerda, parada
        inputs[1].hold("mark")
        run(match, 150, inputs)                      # (com bola, a velocidade fica mais perto da média)
        gx, gy = match.goal_center(0)
        # entre a bola e o centro do gol, perto do gol
        self.assertLess(p1.distance_to(match.ball) + math.hypot(p1.x - gx, p1.y - gy),
                        math.hypot(match.ball.x - gx, match.ball.y - gy) + 20)
        self.assertLess(math.hypot(p1.x - gx, p1.y - gy), 130)

    def test_cobertura_no_2x2(self):
        match, inputs = futebol(chars=(4, 2, 0, 7), humans=(1,))
        p1, p2, p3, p4 = match.fighters             # P1 e P3 no mesmo time
        p2.x, p2.y, p4.x, p4.y = 1500, 900, 1500, 100
        match.ball.x, match.ball.y = 1000, 450
        p3.x, p3.y = 980, 450                        # companheiro já está na bola
        p1.x, p1.y = 900, 200
        inputs[1].hold("mark")
        run(match, 90, inputs)
        self.assertGreater(p1.distance_to(match.ball), 150)   # não foi os dois na bola
        self.assertLess(p1.x, match.ball.x)                   # ficou atrás, cobrindo o gol

    def test_companheiro_com_a_bola_nao_mexe(self):
        match, _ = futebol(chars=(4, 2, 0, 7))
        p1, _, p3, _ = match.fighters
        match.possessor = p3
        self.assertIsNone(match.mark_target(p1))


if __name__ == "__main__":
    unittest.main()
