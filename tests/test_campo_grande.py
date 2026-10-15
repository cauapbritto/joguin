"""Campo de futebol maior: medidas saem do Pitch, chute e lançamento vão longe, e a câmera
nunca perde a bola (quem sai da tela vira uma setinha na borda)."""
import math
import unittest

from apoio import GOL_D, MEIO, futebol, run

from soulstrike import config
from soulstrike.arena import Pitch


def parar(match, frames=400):
    """Roda até a bola parar (ou alguém dominar)."""
    ball = match.ball
    for _ in range(frames):
        run(match, 1)
        if match.possessor is not None or (math.hypot(ball.vx, ball.vy) < 0.3 and ball.z == 0):
            break
    return ball


class MedidasTest(unittest.TestCase):
    def test_campo_maior_que_o_antigo(self):
        match, _ = futebol()
        self.assertGreaterEqual(match.arena.width, 1600 * 1.35)
        self.assertGreaterEqual(match.arena.height, 900 * 1.35)
        self.assertEqual((match.arena.width, match.arena.height), (Pitch.W, Pitch.H))

    def test_gols_no_meio_das_linhas_de_fundo(self):
        match, _ = futebol()
        self.assertAlmostEqual((match.GOAL_TOP + match.GOAL_BOTTOM) / 2, match.arena.height / 2)
        self.assertEqual(match.goal_x(0), Pitch.EDGE)
        self.assertEqual(match.goal_x(1), match.arena.width - Pitch.EDGE)
        for goal in match.goals:
            self.assertEqual((goal.rect.top, goal.rect.bottom), (match.GOAL_TOP, match.GOAL_BOTTOM))

    def test_boca_do_gol_aberta_e_resto_fechado(self):
        match, _ = futebol()
        walls = match.arena.walls
        for x in (Pitch.LINE - 10, match.arena.width - Pitch.LINE + 10):
            self.assertFalse(any(w.overlaps_circle(x, MEIO, 4) for w in walls), "gol fechado")
            self.assertTrue(any(w.overlaps_circle(x, MEIO - Pitch.GOAL, 4) for w in walls), "fundo aberto")

    def test_largada_espelhada(self):
        a, b, c, d = Pitch.spawns()
        self.assertEqual(a[0] + b[0], Pitch.W)
        self.assertEqual(a[1] + c[1], Pitch.H)
        self.assertEqual((c[0], d[0]), (a[0], b[0]))

    def test_gol_na_linha_nova(self):
        match, _ = futebol()
        ball = match.ball
        ball.x, ball.y, ball.vx = GOL_D - 40, MEIO, 8.0
        run(match, 20)
        self.assertEqual(match.score, [1, 0])


class AlcanceTest(unittest.TestCase):
    def _com_bola(self, humans=(1,), chars=(4, 2)):
        match, inputs = futebol(chars=chars, humans=humans)
        p1 = match.fighters[0]
        for f in match.fighters[1:]:
            f.x, f.y = 300, MEIO + 500                 # todo mundo longe da linha da bola
        p1.x, p1.y = 200, MEIO
        match.ball.x, match.ball.y = 230, MEIO
        run(match, 3, inputs)
        assert match.possessor is p1
        p1.facing = (1.0, 0.0)
        return match, inputs, p1

    def test_chute_rasteiro_atravessa_meio_campo(self):
        match, _, p1 = self._com_bola()
        x0 = match.ball.x
        self.assertTrue(match.kick(p1, (1.0, 0.0)))
        ball = parar(match)
        self.assertGreater(ball.x - x0, 850)               # no campo antigo eram uns 640

    def test_chute_alto_cheio_cai_longe(self):
        match, _, p1 = self._com_bola()
        x0 = match.ball.x
        self.assertTrue(match.kick(p1, (1.0, 0.0), loft=1.0))
        ball = match.ball
        while ball.airborne:
            run(match, 1)
        self.assertGreater(ball.x - x0, 680)               # primeiro quique

    def test_lancamento_chega_no_companheiro_do_outro_lado(self):
        match, inputs, p1 = self._com_bola(humans=(1, 3), chars=(4, 2, 0, 7))
        p3 = match.fighters[2]
        p3.x, p3.y = p1.x + 1050, MEIO - 200                # bem longe, parado
        p3.prev_pos = (p3.x, p3.y)
        self.assertTrue(match.pass_ball(p1, high=True, direction=(1.0, -0.2)))
        self.assertIs(match.ball.receiver, p3)
        for _ in range(240):
            run(match, 1, inputs)
            if match.possessor is not None:
                break
        self.assertIs(match.possessor, p3)

    def test_passe_alto_para_o_espaco_vai_mais_longe_segurando_mais(self):
        def queda(power):
            match, _, p1 = self._com_bola()
            x0 = match.ball.x
            match.pass_ball(p1, high=True, direction=(1.0, 0.0), power=power)
            ball = match.ball
            while ball.airborne:
                run(match, 1)
            return ball.x - x0
        perto, longe = queda(0.15), queda(1.0)
        self.assertGreater(longe, perto + 300)
        self.assertGreater(longe, 820)
        lo, hi = config.LOB_SPACE
        self.assertAlmostEqual(longe, hi, delta=60)

    def test_adversario_no_caminho_corta_o_lancamento(self):
        match, inputs, p1 = self._com_bola(humans=(1, 3), chars=(4, 2, 0, 7))
        p3 = match.fighters[2]
        p3.x, p3.y = p1.x + 600, MEIO
        match.pass_ball(p1, high=True, direction=(1.0, 0.0))
        self.assertIs(match.ball.receiver, p3)
        match._body_block(match.fighters[1], 30)             # bateu num adversário
        self.assertIsNone(match.ball.receiver)


class CameraTest(unittest.TestCase):
    def test_bola_sempre_na_tela(self):
        match, _ = futebol(chars=(4, 2, 0, 7))
        p1, p2, p3, p4 = match.fighters
        p1.x, p1.y = 80, 80
        p2.x, p2.y = Pitch.W - 80, Pitch.H - 80
        p3.x, p3.y = 80, Pitch.H - 80
        p4.x, p4.y = Pitch.W - 80, 80
        match.ball.x, match.ball.y = Pitch.W - 300, MEIO
        for _ in range(120):
            match.update()
        g = match.game
        match.draw(g.screen, g.ui)                    # a câmera só sabe onde desenhou depois de desenhar
        sx, sy = match.camera.to_screen(match.ball.x, match.ball.y)
        self.assertTrue(0 <= sx <= config.SCREEN_W and 0 <= sy <= config.SCREEN_H, (sx, sy))

    def test_setas_de_quem_saiu_da_tela(self):
        match, _ = futebol(chars=(4, 2, 0, 7))
        p1 = match.fighters[0]
        p1.x, p1.y = 80, 80
        match.ball.x, match.ball.y = Pitch.W - 200, MEIO
        for _ in range(90):
            match.update()
        g = match.game
        match.draw(g.screen, g.ui)
        sx, sy = match.camera.to_screen(p1.x, p1.y)
        self.assertFalse(0 <= sx <= config.SCREEN_W and 0 <= sy <= config.SCREEN_H)


if __name__ == "__main__":
    unittest.main()
