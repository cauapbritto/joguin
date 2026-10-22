"""Craques do futebol: Faísca, Trovão, Ginga e Matador. Só aparecem no futebol e cada um tem uma
habilidade que vale o jogo todo e um SUPER próprio."""
import math
import random
import unittest

from apoio import GOL_D, MEIO, FakeInput, futebol, game, run

from soulstrike import config
from soulstrike.data import CHARACTERS, FIGHTERS, SOCCER_STARS, roster, roster_indices
from soulstrike.session import Session, SlotSetup
from soulstrike.soccer_powers import SOCCER_POWERS

KEYS = [c.key for c in CHARACTERS]


def com_bola(key, foe="guerreiro", humans=(1,)):
    """1 x 1: o craque (P1) com a bola no meio do campo, olhando para a direita."""
    match, inputs = futebol(chars=(KEYS.index(key), KEYS.index(foe)), humans=humans)
    p1, p2 = match.fighters
    p2.x, p2.y = 300, MEIO + 450
    p1.x, p1.y = 900, MEIO
    match.ball.x, match.ball.y = p1.x + 28, p1.y
    run(match, 3, inputs)
    assert match.possessor is p1
    p1.facing = (1.0, 0.0)
    return match, inputs, p1, p2


class ElencoTest(unittest.TestCase):
    def test_so_aparecem_no_futebol(self):
        self.assertEqual(set(SOCCER_STARS), {"faisca", "trovao", "ginga", "matador", "paredao"})
        batalha = {c.key for c in roster()}
        futebol_ = {c.key for c in roster(soccer=True)}
        self.assertFalse(batalha & set(SOCCER_STARS))
        self.assertTrue(set(SOCCER_STARS) <= futebol_)
        self.assertFalse({c.key for c in FIGHTERS} & set(SOCCER_STARS))

    def test_indices_antigos_nao_mudam(self):
        self.assertEqual(KEYS[:11], ["guerreiro", "atirador", "tanque", "ninja", "velocista", "aryel",
                                     "fantasma", "tita", "pirata", "geada", "aryel_corrompido"])
        for i in roster_indices(soccer=True):
            self.assertIs(roster(soccer=True)[roster_indices(soccer=True).index(i)], CHARACTERS[i])

    def test_selecao_do_duelo_nao_oferece_craque(self):
        from soulstrike.scenes.select import CharSelectScene
        g = game()
        g.session = Session("duel", [SlotSetup(1), SlotSetup(2)])
        scene = CharSelectScene(g)
        card = scene.cards[0]
        seen = set()
        for _ in range(len(CHARACTERS) + 2):
            scene._change_char(card, 1)
            seen.add(CHARACTERS[card.setup.char].key)
        self.assertFalse(seen & set(SOCCER_STARS))

    def test_selecao_do_futebol_chega_nos_craques_e_cabe_na_tela(self):
        from soulstrike.scenes.select import CharSelectScene
        g = game()
        g.session = Session("soccer2", [SlotSetup(s) for s in (1, 2, 3, 4)])
        scene = CharSelectScene(g)
        card = scene.cards[0]
        seen = set()
        for _ in range(len(CHARACTERS) + 2):
            scene._change_char(card, -1)
            seen.add(CHARACTERS[card.setup.char].key)
        self.assertTrue(set(SOCCER_STARS) <= seen)
        self.assertGreaterEqual(scene.tiles[0].left, 0)
        self.assertLessEqual(scene.tiles[-1].right, config.SCREEN_W)
        scene.draw(g.screen)

    def test_cpu_do_duelo_nunca_sorteia_craque(self):
        from soulstrike.scenes.select import _Card
        random.seed(4)
        choices = roster_indices()
        for _ in range(200):
            card = _Card(SlotSetup(2, cpu=True), choices)
            self.assertFalse(CHARACTERS[card.setup.char].soccer_only)


class FaiscaTest(unittest.TestCase):
    def _marcado(self, key):
        match, inputs, p1, p2 = com_bola(key)
        p2.x, p2.y = p1.x + 34, p1.y + 4                 # colado na bola
        return match, inputs, p1, p2

    def test_bola_protegida_demora_mais_para_tomar(self):
        def quadros_ate_perder(key):
            match, inputs, p1, p2 = self._marcado(key)
            for t in range(120):
                # o marcador fica mais perto da bola que o dono (é assim que se toma a bola)
                p1.x, p1.y = 900, MEIO
                match.ball.x, match.ball.y = 930, MEIO
                p2.x, p2.y = 936, MEIO
                match._update_possession()
                if match.possessor is not p1:
                    return t
            return 120
        normal, faisca = quadros_ate_perder("aryel"), quadros_ate_perder("faisca")
        self.assertLess(normal, 30)
        self.assertGreaterEqual(faisca, normal * 1.5)

    def test_drible_magico_ninguem_toma_e_atravessa(self):
        match, inputs, p1, p2 = self._marcado("faisca")
        self.assertTrue(match.use_power(p1))
        self.assertGreater(p1.magic_timer, 0)
        for _ in range(60):
            p2.x, p2.y = match.ball.x + 4, match.ball.y
            match.cut(p2, (-1.0, 0.0))                   # nem o corte cutuca a bola
            run(match, 1, inputs)
            self.assertIs(match.possessor, p1)
        self.assertFalse(p1.stun(30))                    # nem é derrubado

    def test_drible_magico_sem_bola_nao_gasta(self):
        match, inputs, p1, p2 = com_bola("faisca")
        match._release(p1, 30)
        match.ball.x += 200
        self.assertFalse(match.use_power(p1))
        self.assertEqual(p1.super_cd, 0)


class TrovaoTest(unittest.TestCase):
    def test_chute_trovao_derruba_e_segue(self):
        match, inputs, p1, p2 = com_bola("trovao")
        p1.x, p1.y = GOL_D - 900, MEIO
        match.ball.x, match.ball.y = p1.x + 28, MEIO
        p2.x, p2.y = p1.x + 300, MEIO                    # no caminho do gol
        p2.prev_pos = (p2.x, p2.y)
        run(match, 2, inputs)
        p1.facing = (1.0, 0.0)
        self.assertTrue(match.use_power(p1))
        for _ in range(30):
            run(match, 1, inputs)
            if p2.stunned:
                break
        self.assertTrue(p2.stunned)
        self.assertGreater(match.ball.vx, 9)             # passou por cima de quem derrubou
        for _ in range(120):
            run(match, 1, inputs)
            if match.score[0]:
                break
        self.assertEqual(match.score[0], 1)

    def test_cabeca_de_aco_alcanca_bola_mais_alta(self):
        def cabeceia(key):
            match, inputs = futebol(chars=(KEYS.index(key), 2), humans=(1,))
            p1, _ = match.fighters
            p1.x, p1.y = 900, MEIO
            ball = match.ball
            ball.x, ball.y, ball.z, ball.vz = 905, MEIO, 80, 0.0
            return match.header(p1, (1.0, 0.0)), math.hypot(ball.vx, ball.vy)
        self.assertFalse(cabeceia("guerreiro")[0])
        ok, speed = cabeceia("trovao")
        self.assertTrue(ok)
        self.assertGreater(speed, 8 * 1.3)


class GingaTest(unittest.TestCase):
    def test_conducao_colada_correndo_sem_perder_velocidade(self):
        def corrida(key):
            match, inputs, p1, p2 = com_bola(key)
            inputs[1].stick = (1.0, 0.0)
            inputs[1].hold("sprint")
            gaps, x0 = [], p1.x
            for _ in range(50):
                run(match, 1, inputs)
                gaps.append(match.ball.x - p1.x)
            self.assertIs(match.possessor, p1)
            return sum(gaps[-20:]) / 20, p1.x - x0
        ginga_gap, ginga_dist = corrida("ginga")
        aryel_gap, aryel_dist = corrida("aryel")
        self.assertLess(ginga_gap, aryel_gap - 8)           # a bola não fica solta na frente
        self.assertLess(ginga_gap, 40)
        self.assertGreaterEqual(ginga_dist, aryel_dist * 0.97)     # e corre igual (sem freio de condução)

    def test_caneta_deixa_tonto_e_sai_com_a_bola(self):
        match, inputs, p1, p2 = com_bola("ginga")
        p2.x, p2.y = p1.x + 100, p1.y
        self.assertTrue(match.use_power(p1))
        self.assertTrue(p2.stunned)
        self.assertGreater(match.ball.x, p2.x)              # a bola passou por ele
        for _ in range(40):
            run(match, 1, inputs)
            if match.possessor is p1:
                break
        self.assertIs(match.possessor, p1)
        self.assertGreater(p1.x, p2.x)                      # e ele saiu do outro lado

    def test_caneta_sem_marcador_nao_gasta(self):
        match, inputs, p1, p2 = com_bola("ginga")
        self.assertFalse(match.use_power(p1))
        self.assertEqual(p1.super_cd, 0)


class MatadorTest(unittest.TestCase):
    def _chute_torto(self, key, dist):
        match, inputs, p1, p2 = com_bola(key)
        match.assist = match.assist.__class__(**{**match.assist.__dict__, "shot_cone": 0})  # sem assistência
        p1.x, p1.y = GOL_D - dist, MEIO
        match.ball.x, match.ball.y = p1.x + 28, MEIO
        run(match, 2, inputs)
        aim = math.radians(-35)                              # 35 graus para fora
        self.assertTrue(match.kick(p1, (math.cos(aim), math.sin(aim)), assist=True))
        ball = match.ball
        t = (GOL_D - ball.x) / ball.vx
        return match.GOAL_TOP <= ball.y + ball.vy * t <= match.GOAL_BOTTOM

    def test_na_area_o_chute_vai_no_gol(self):
        self.assertTrue(self._chute_torto("matador", 220))
        self.assertFalse(self._chute_torto("aryel", 220))
        self.assertFalse(self._chute_torto("matador", 800))  # fora da área, não

    def test_faro_de_gol_puxa_a_bola_solta(self):
        match, inputs, p1, p2 = com_bola("matador")
        match._release(p1, 1)
        match.ball.x, match.ball.y = p1.x + 60, p1.y + 200
        match.ball.vx = match.ball.vy = 0.0
        run(match, 2, inputs)
        self.assertTrue(match.use_power(p1))
        for _ in range(120):
            run(match, 1, inputs)
            if match.possessor is p1:
                break
        self.assertIs(match.possessor, p1)


class CpuTest(unittest.TestCase):
    def test_cpu_joga_com_os_quatro(self):
        g = game()
        random.seed(9)
        used = set()
        for _ in range(2):
            g.session = Session("soccer2", [SlotSetup(s, char=KEYS.index(k), cpu=True)
                                            for s, k in zip((1, 2, 3, 4), SOCCER_STARS)])
            from soulstrike.matches import SoccerMatch
            match = SoccerMatch(g, g.session)
            for _ in range(60 * 40):
                match.update()
                for f in match.fighters:
                    if f.super_cd == f.power.cooldown - 1:
                        used.add(f.stats.key)
                if match.finished:
                    break
            match.draw(g.screen, g.ui)
        self.assertGreaterEqual(len(used), 2, used)

    def test_cpu_sabe_quando_usar_cada_super(self):
        match, inputs, p1, p2 = com_bola("faisca")
        p2.x, p2.y = p1.x + 90, p1.y
        self.assertTrue(p1.power.worth_using(p1, match))
        match, inputs, p1, p2 = com_bola("ginga")
        p2.x, p2.y = p1.x + 90, p1.y
        self.assertTrue(p1.power.worth_using(p1, match))
        match, inputs, p1, p2 = com_bola("trovao")
        p1.x, p1.y = GOL_D - 500, MEIO
        self.assertTrue(p1.power.worth_using(p1, match))
        match, inputs, p1, p2 = com_bola("matador")
        match._release(p1, 1)
        match.ball.x += 150
        self.assertTrue(p1.power.worth_using(p1, match))


if __name__ == "__main__":
    unittest.main()
