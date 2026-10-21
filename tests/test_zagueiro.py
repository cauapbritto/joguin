"""Defesa no futebol: o Zagueirão do Guerreiro, o Paredão, o corte e as respostas aos poderes de
ataque (enterrada, bola fantasma, chute trovão, hack, drible mágico, caneta)."""
import math
import unittest

from apoio import GOL_D, MEIO, futebol, run

from soulstrike import config
from soulstrike.arena import Pitch
from soulstrike.data import CHARACTERS
from soulstrike.soccer_powers import BallWall

KEYS = [c.key for c in CHARACTERS]
GOL_E = Pitch.goal_x(0)


def jogo(a, b, humans=(1,)):
    """1 x 1: P1 (time azul, defende o gol da esquerda) e P2 (vermelho), longe da bola."""
    match, inputs = futebol(chars=(KEYS.index(a), KEYS.index(b)), humans=humans)
    p1, p2 = match.fighters
    p1.x, p1.y = 600, MEIO
    p2.x, p2.y = 1600, MEIO + 400
    match.ball.x, match.ball.y = 1600, 200
    run(match, 2, inputs)
    return match, inputs, p1, p2


def da_bola(match, f, inputs, dx=26):
    match.ball.x, match.ball.y = f.x + dx, f.y
    match.ball.vx = match.ball.vy = 0.0
    run(match, 3, inputs)
    assert match.possessor is f


class ZagueiraoTest(unittest.TestCase):
    def test_so_no_proprio_campo(self):
        match, inputs, p1, p2 = jogo("guerreiro", "tanque")
        p1.x = GOL_D - 300
        self.assertFalse(match.use_power(p1))
        p1.x = 600
        self.assertTrue(match.use_power(p1))
        self.assertGreater(p1.zaga_timer, 0)
        p1.x = Pitch.W / 2 + 200                       # passou do meio: acaba
        run(match, 2, inputs)
        self.assertEqual(p1.zaga_timer, 0)

    def test_nao_cai_nem_trava(self):
        match, inputs, p1, p2 = jogo("guerreiro", "tanque")
        self.assertTrue(match.use_power(p1))
        self.assertFalse(p1.stun(60))
        self.assertFalse(p1.hack(60))
        self.assertFalse(p1.slow(60))

    def test_rouba_do_drible_magico_encostando(self):
        match, inputs, p1, p2 = jogo("guerreiro", "faisca", humans=(1, 2))
        p2.x, p2.y = 800, MEIO
        da_bola(match, p2, inputs, dx=-26)
        self.assertTrue(match.use_power(p2))           # drible mágico ligado
        self.assertTrue(match.use_power(p1))
        p1.x, p1.y = match.ball.x - 30, match.ball.y
        run(match, 2, inputs)
        self.assertIs(match.possessor, p1)

    def test_rouba_do_exoesqueleto(self):
        match, inputs, p1, p2 = jogo("guerreiro", "borba", humans=(1, 2))
        p2.x, p2.y = 800, MEIO
        da_bola(match, p2, inputs, dx=-26)
        self.assertTrue(match.use_power(p2))
        self.assertTrue(match.use_power(p1))
        p1.x, p1.y = match.ball.x - 30, match.ball.y
        run(match, 2, inputs)
        self.assertIs(match.possessor, p1)

    def test_mata_o_chute_trovao(self):
        match, inputs, p1, p2 = jogo("guerreiro", "trovao", humans=(1, 2))
        p2.x, p2.y = 1000, MEIO
        da_bola(match, p2, inputs, dx=-26)
        p2.facing = (-1.0, 0.0)
        p1.x, p1.y = 700, MEIO
        p1.prev_pos = (p1.x, p1.y)
        self.assertTrue(match.use_power(p1))
        self.assertTrue(match.use_power(p2))
        for _ in range(40):
            run(match, 1, inputs)
            if match.possessor is p1:
                break
        self.assertIs(match.possessor, p1)
        self.assertFalse(p1.stunned)
        self.assertEqual(match.ball.thunder_timer, 0)
        self.assertEqual(match.score, [0, 0])

    def test_bola_fantasma_para_nele(self):
        match, inputs, p1, p2 = jogo("guerreiro", "fantasma", humans=(1, 2))
        p2.x, p2.y = 1000, MEIO
        da_bola(match, p2, inputs, dx=-26)
        p1.x, p1.y = 600, MEIO
        self.assertTrue(match.use_power(p1))
        self.assertTrue(match.use_power(p2))
        ball = match.ball
        ball.vx, ball.vy = -13.0, 0.0                   # bola fantasma direto nele
        ball.y = MEIO
        for _ in range(60):
            run(match, 1, inputs)
            if match.possessor is p1:
                break
        self.assertIs(match.possessor, p1)
        self.assertEqual(ball.ghost_timer, 0)

    def test_caneta_no_zagueirao_vira_desarme(self):
        match, inputs, p1, p2 = jogo("guerreiro", "ginga", humans=(1, 2))
        p2.x, p2.y = 800, MEIO
        da_bola(match, p2, inputs, dx=-26)
        p2.facing = (-1.0, 0.0)
        p1.x, p1.y = 700, MEIO
        self.assertTrue(match.use_power(p1))
        self.assertTrue(match.use_power(p2))
        self.assertIs(match.possessor, p1)
        self.assertFalse(p1.stunned)

    def test_pegada_firme_rouba_mais_rapido(self):
        def quadros(key):
            match, inputs, p1, p2 = jogo(key, "tanque", humans=(1, 2))
            p2.x, p2.y = 900, MEIO
            da_bola(match, p2, inputs)
            for t in range(120):
                p2.x, p2.y = 900, MEIO
                match.ball.x, match.ball.y = 930, MEIO
                p1.x, p1.y = 936, MEIO
                match._update_possession()
                if match.possessor is p1:
                    return t
            return 120
        self.assertLessEqual(quadros("guerreiro") * 1.8, quadros("atirador"))


class EnterradaTest(unittest.TestCase):
    def _enterrada(self, defensor):
        match, inputs, p1, p2 = jogo("cauanzera", defensor, humans=(1, 2))
        p1.x, p1.y = GOL_D - 400, MEIO
        da_bola(match, p1, inputs)
        p2.x, p2.y = GOL_D - 70, MEIO                 # no ponto onde ele cai
        return match, inputs, p1, p2

    def test_alcance_menor(self):
        match, inputs, p1, p2 = jogo("cauanzera", "tanque")
        p1.x, p1.y = GOL_D - 520, MEIO
        da_bola(match, p1, inputs)
        self.assertFalse(match.use_power(p1))

    def test_sem_defesa_e_gol(self):
        match, inputs, p1, p2 = self._enterrada("tanque")
        self.assertTrue(match.use_power(p1))
        run(match, 90, inputs)
        self.assertEqual(match.score[0], 1)

    def test_toco_do_zagueirao(self):
        match, inputs, p1, p2 = self._enterrada("guerreiro")
        self.assertTrue(match.use_power(p2))
        self.assertTrue(match.use_power(p1))
        run(match, 90, inputs)
        self.assertEqual(match.score[0], 0)

    def test_toco_da_muralha(self):
        match, inputs, p1, p2 = self._enterrada("tanque")
        p2.x, p2.y = GOL_D - 400, MEIO + 400
        match.add_ball_wall(BallWall(GOL_D - 70, MEIO, 1, 6 * config.FPS))
        self.assertTrue(match.use_power(p1))
        run(match, 90, inputs)
        self.assertEqual(match.score[0], 0)


class GoleiroTest(unittest.TestCase):
    def test_bola_fantasma_para_no_goleiro(self):
        match, inputs, p1, p2 = jogo("tanque", "fantasma", humans=(1, 2))
        p1.x, p1.y = GOL_E + 120, MEIO
        p2.x, p2.y = 700, MEIO
        da_bola(match, p2, inputs, dx=-26)
        self.assertTrue(match.use_power(p2))
        ball = match.ball
        ball.y, ball.vx, ball.vy = MEIO, -13.0, 0.0
        inputs[1].hold("mark")
        for _ in range(80):
            p1.x, p1.y = GOL_E + 120, MEIO               # parado na frente do gol
            run(match, 1, inputs)
            if ball.ghost_timer == 0 or match.score[1]:
                break
        self.assertEqual(match.score[1], 0)
        self.assertEqual(ball.ghost_timer, 0)

    def test_hack_trava_menos_o_goleiro(self):
        match, inputs, p1, p2 = jogo("tanque", "albeguinio", humans=(1, 2))
        p1.x, p1.y = GOL_E + 120, MEIO
        p1.marking = True
        self.assertTrue(match.keeping(p1))
        inputs[1].hold("mark")
        self.assertTrue(match.use_power(p2))
        for _ in range(60):
            run(match, 1, inputs)
            if p1.hack_timer:
                break
        self.assertGreater(p1.hack_timer, 0)
        self.assertLessEqual(p1.hack_timer, round(2.5 * config.FPS * config.KEEPER_HACK))


class ParedaoTest(unittest.TestCase):
    def test_antecipa_no_proprio_campo(self):
        match, inputs, p1, p2 = jogo("paredao", "faisca", humans=(1, 2))
        p2.x, p2.y = 900, MEIO + 200
        da_bola(match, p2, inputs, dx=-26)
        self.assertTrue(match.use_power(p2))           # nem o drible mágico segura
        p1.x, p1.y = 400, MEIO - 200
        self.assertTrue(match.use_power(p1))
        self.assertIs(match.possessor, p1)
        self.assertLess(p1.distance_to(match.ball), 50)

    def test_nao_antecipa_no_campo_adversario(self):
        match, inputs, p1, p2 = jogo("paredao", "tanque", humans=(1, 2))
        p2.x, p2.y = GOL_D - 300, MEIO
        da_bola(match, p2, inputs, dx=-26)
        p1.x, p1.y = GOL_D - 700, MEIO
        self.assertFalse(match.use_power(p1))
        self.assertEqual(p1.super_cd, 0)

    def test_corpo_fechado(self):
        match, inputs, p1, p2 = jogo("paredao", "fantasma", humans=(1, 2))
        ball = match.ball
        ball.ghost_timer, ball.ghost_team = 60, p2.team
        self.assertFalse(match._ghost_passes(p1))


class CorteTest(unittest.TestCase):
    def test_corte_vai_na_bola_e_cutuca(self):
        match, inputs, p1, p2 = jogo("atirador", "tanque", humans=(1, 2))
        p2.x, p2.y = 900, MEIO
        da_bola(match, p2, inputs, dx=26)
        p1.x, p1.y = 870, MEIO - 60                      # perto, mas sem encostar
        p1.facing = (-1.0, 0.0)                          # olhando para o outro lado
        inputs[1].tap("dodge")
        for _ in range(config.CUT_POKE_FRAMES + 2):
            run(match, 1, inputs)
            if match.possessor is not p2:
                break
        self.assertIsNot(match.possessor, p2)
        self.assertIs(match.last_touch, p1)

    def test_corte_segue_o_analogico(self):
        match, inputs, p1, p2 = jogo("atirador", "tanque")
        inputs[1].stick = (0.0, 1.0)
        y = p1.y
        inputs[1].tap("dodge")
        run(match, config.CUT_FRAMES, inputs)
        self.assertGreater(p1.y, y + 20)

    def test_corte_com_a_bola_foge_do_marcador(self):
        match, inputs, p1, p2 = jogo("atirador", "tanque", humans=(1, 2))
        da_bola(match, p1, inputs)
        p1.facing = (1.0, 0.0)
        p2.x, p2.y = p1.x + 60, p1.y - 40               # marcador em cima (y menor)
        y = p1.y
        match.cut(p1)
        run(match, config.CUT_FRAMES, inputs)
        self.assertGreater(p1.y, y + 10)                 # cortou para baixo, longe dele
        self.assertIs(match.possessor, p1)

    def test_corte_do_zagueirao_derruba(self):
        match, inputs, p1, p2 = jogo("guerreiro", "tanque", humans=(1, 2))
        p2.x, p2.y = 900, MEIO
        da_bola(match, p2, inputs, dx=26)
        p1.x, p1.y = 840, MEIO
        self.assertTrue(match.use_power(p1))
        match.cut(p1, (1.0, 0.0))
        run(match, 8, inputs)
        self.assertTrue(p2.stunned)
        self.assertIsNot(match.possessor, p2)


class GanchoTest(unittest.TestCase):
    def test_gancho_tira_do_drible_magico(self):
        match, inputs, p1, p2 = jogo("pirata", "faisca", humans=(1, 2))
        p2.x, p2.y = 900, MEIO
        da_bola(match, p2, inputs, dx=26)
        self.assertTrue(match.use_power(p2))
        p1.x, p1.y = 700, MEIO
        self.assertTrue(match.use_power(p1))
        self.assertIsNot(match.possessor, p2)


if __name__ == "__main__":
    unittest.main()
