"""Aryel: Aposta (roleta GREEN / meio green / RED), Baixinho, esquiva de moto, Capacete e, no
futebol, o Grau de moto (3s de moto: corre muito, bola colada e quem ele atropela cai)."""
import random
import unittest

from apoio import FakeInput, GOL_D, MEIO, futebol, game, run

from soulstrike import config
from soulstrike.abilities import Aposta
from soulstrike.data import CHARACTERS
from soulstrike.matches import BattleMatch
from soulstrike.session import Session, SlotSetup

KEYS = [c.key for c in CHARACTERS]


def duelo(a="aryel", b="pirata"):
    g = game()
    g.session = Session("duel", [SlotSetup(1, char=KEYS.index(a)), SlotSetup(2, char=KEYS.index(b))])
    match = BattleMatch(g, g.session)
    match.intro = 0
    p1, p2 = match.fighters
    match.controllers.clear()
    match.controllers[p1] = FakeInput()
    match.controllers[p2] = FakeInput()
    p1.x, p1.y, p2.x, p2.y = 640, 700, 860, 700
    return match, p1, p2


def passo(match, frames):
    for _ in range(frames):
        match.update()


class ApostaTest(unittest.TestCase):
    def _aposta(self, roll):
        match, p1, p2 = duelo()
        old = random.random
        random.random = lambda: roll
        try:
            p1.use_ability(match, p2)
        finally:
            random.random = old
        return match, p1, p2

    def test_green_chove_moeda_no_inimigo(self):
        match, p1, p2 = self._aposta(0.05)
        hp1, hp2 = p1.hp, p2.hp
        passo(match, Aposta.SPIN + 80)
        self.assertLess(p2.hp, hp2 - Aposta.COIN_DAMAGE)          # mais de uma moeda acertou
        self.assertEqual(p1.hp, hp1)

    def test_meio_green_solta_as_bombas(self):
        match, p1, p2 = self._aposta(0.4)
        n = len(match.bullets)
        passo(match, Aposta.SPIN + 1)
        self.assertGreaterEqual(len(match.bullets) - n, 6)

    def test_red_estoura_nele(self):
        match, p1, p2 = self._aposta(0.9)
        hp1, hp2 = p1.hp, p2.hp
        passo(match, Aposta.SPIN + 20)
        self.assertEqual(hp1 - p1.hp, Aposta.SELF_DAMAGE)
        self.assertEqual(p2.hp, hp2)


class BaixinhoEMotoTest(unittest.TestCase):
    def test_baixinho_menor_que_os_outros(self):
        match, p1, p2 = duelo()
        self.assertLess(p1.radius, p2.radius)
        self.assertLess(p1.draw_scale, 1.0)

    def test_corrompido_continua_do_tamanho_normal(self):
        match, p1, p2 = duelo("aryel_corrompido")
        self.assertEqual(p1.radius, config.PLAYER_RADIUS)
        self.assertEqual(p1.stats.weapons[1].name, "Martelo")

    def test_esquiva_de_moto_vai_mais_longe(self):
        def distancia(key):
            match, p1, p2 = duelo(key)
            x0 = p1.x
            p1.dash((1.0, 0.0))
            passo(match, 30)
            return p1.x - x0, p1
        moto, aryel = distancia("aryel")
        normal, _ = distancia("guerreiro")
        self.assertGreater(moto, normal * 1.2)
        self.assertTrue(aryel.on_moto)

    def test_capacete(self):
        self.assertEqual(CHARACTERS[KEYS.index("aryel")].weapons[1].name, "Capacete")


class GrauDeMotoTest(unittest.TestCase):
    def _jogo(self):
        match, inputs = futebol(chars=(KEYS.index("aryel"), KEYS.index("tanque")), humans=(1,))
        p1, p2 = match.fighters
        p2.x, p2.y = 400, MEIO + 400
        p1.x, p1.y = 900, MEIO
        match.ball.x, match.ball.y = p1.x + 28, MEIO
        run(match, 3, inputs)
        return match, inputs, p1, p2

    def test_moto_corre_mais_com_a_bola_colada(self):
        match, inputs, p1, p2 = self._jogo()
        normal = p1.max_speed
        self.assertTrue(match.use_power(p1))
        self.assertGreater(p1.max_speed, normal * 1.5)
        inputs[1].stick = (1.0, 0.0)
        run(match, 60, inputs)
        self.assertIs(match.possessor, p1)                 # a bola foi junto
        self.assertGreater(p1.x, 900 + 60 * normal * 1.3)

    def test_atropela_quem_esta_com_a_bola(self):
        match, inputs, p1, p2 = self._jogo()
        match._release(p1, 600)
        p2.x, p2.y = 1200, MEIO
        match.ball.x, match.ball.y = p2.x + 26, MEIO
        run(match, 3, inputs)
        self.assertIs(match.possessor, p2)
        self.assertTrue(match.use_power(p1))
        inputs[1].stick = (1.0, 0.0)
        for _ in range(90):
            run(match, 1, inputs)
            if p2.stunned:
                break
        self.assertTrue(p2.stunned)
        self.assertIsNot(match.possessor, p2)

    def test_acaba_depois_de_3s(self):
        match, inputs, p1, p2 = self._jogo()
        self.assertTrue(match.use_power(p1))
        run(match, 3 * config.FPS + 2, inputs)
        self.assertEqual(p1.moto_timer, 0)


if __name__ == "__main__":
    unittest.main()
