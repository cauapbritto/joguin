"""Basquete: ponte aérea (alley-oop) sem SUPER e o corte de quem pula na frente."""
import unittest

from apoio import run
from test_basquete import basquete


def preparar(match):
    passer = next(f for f in match.fighters if f.team == 0)
    mate = next(f for f in match.fighters if f.team == 0 and f is not passer)
    side = match.hoop_of(0)
    hx, hy = match.hoop_pos(side)
    sign = 1 if hx < 1000 else -1
    passer.x, passer.y = hx + sign * 650, hy
    mate.x, mate.y = hx + sign * 260, hy + 120
    mate.vx, mate.vy = -sign * 3.0, -1.0           # correndo para o aro
    match.ball.reset(passer.x, passer.y)
    match._give(passer)
    return passer, mate, (hx, hy)


class PonteAereaTest(unittest.TestCase):
    def test_passe_para_quem_corre_para_a_cesta_vira_alley_oop(self):
        match, _ = basquete()
        passer, mate, _ = preparar(match)
        self.assertTrue(match.pass_ball(passer, (mate.x - passer.x, mate.y - passer.y)))
        self.assertIsNotNone(match.alley)
        self.assertTrue(match.alley["plain"])
        for _ in range(80):
            mate.steer(0, 0)
            match.update()
            if mate.dunking or match.holder is mate:
                break
        self.assertTrue(mate.dunking or match.holder is mate)

    def test_parado_nao_vira_alley_oop(self):
        match, _ = basquete()
        passer, mate, _ = preparar(match)
        mate.vx = mate.vy = 0.0
        match.pass_ball(passer, (mate.x - passer.x, mate.y - passer.y))
        self.assertIsNone(match.alley)

    def test_quem_pula_na_frente_corta(self):
        match, _ = basquete()
        passer, mate, _ = preparar(match)
        foe = next(f for f in match.fighters if f.team == 1)
        match.pass_ball(passer, (mate.x - passer.x, mate.y - passer.y))
        ball = match.ball
        stolen = False
        for _ in range(60):
            foe.x, foe.y = ball.x, ball.y
            if not foe.jump:
                match.jump(foe)
            match.update()
            if match.holder is foe:
                stolen = True
                break
        self.assertTrue(stolen)


if __name__ == "__main__":
    unittest.main()
