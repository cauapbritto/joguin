"""CPU com dificuldade no futebol e no basquete, ajuda para quem toma lavada no basquete e
tamanho da partida de futebol (3, 5 ou 7 gols, ou por tempo com gol de ouro)."""
import unittest

from apoio import game

from soulstrike import config
from soulstrike.ai import BALL_DIFFICULTIES, BasketballAI, SoccerAI
from soulstrike.basketball import COMEBACK_GAP, BasketballMatch
from soulstrike.data import CHARACTERS
from soulstrike.matches import SoccerMatch
from soulstrike.session import Session, SlotSetup

KEYS = [c.key for c in CHARACTERS]


def futebol(difficulty="normal", length="3"):
    g = game()
    g.session = Session("soccer1", [SlotSetup(1, char=KEYS.index("guerreiro"), cpu=True),
                                    SlotSetup(2, char=KEYS.index("ninja"), cpu=True)],
                        difficulty=difficulty)
    g.session.soccer_length = length
    return SoccerMatch(g, g.session)


def basquete(difficulty="normal"):
    g = game()
    g.session = Session("basket2", [SlotSetup(i + 1, char=KEYS.index(c), cpu=True)
                                    for i, c in enumerate(("guerreiro", "ninja", "tanque", "geada"))],
                        difficulty=difficulty)
    return BasketballMatch(g, g.session)


class DificuldadeTest(unittest.TestCase):
    def test_dificil_e_mais_esperta_que_facil(self):
        easy, hard = BALL_DIFFICULTIES["facil"], BALL_DIFFICULTIES["dificil"]
        self.assertLess(easy["speed"], hard["speed"])
        self.assertGreater(easy["aim"], hard["aim"])
        for k in (0, 1):
            self.assertLess(easy["hit"][k], hard["hit"][k])

    def test_cpu_recebe_a_dificuldade_da_partida(self):
        easy, hard = futebol("facil"), futebol("dificil")
        self.assertIsInstance(easy.controllers[easy.fighters[0]], SoccerAI)
        self.assertEqual(easy.controllers[easy.fighters[0]].cfg, BALL_DIFFICULTIES["facil"])
        self.assertLess(easy.fighters[0].speed, hard.fighters[0].speed)
        b = basquete("dificil")
        ai = b.controllers[b.fighters[0]]
        self.assertIsInstance(ai, BasketballAI)
        self.assertEqual(ai.cfg, BALL_DIFFICULTIES["dificil"])


class ReacaoTest(unittest.TestCase):
    def test_perdendo_de_muito_ganha_ajuda(self):
        m = basquete()
        m.warmup = 0
        self.assertFalse(m.comeback(0))
        m.score = [0, COMEBACK_GAP]
        self.assertTrue(m.comeback(0))
        self.assertFalse(m.comeback(1))
        m.score = [1, COMEBACK_GAP]
        self.assertFalse(m.comeback(0))         # encostou: a ajuda some

    def test_super_volta_mais_rapido(self):
        m = basquete()
        m.warmup = 0
        m.score = [0, COMEBACK_GAP + 2]
        losing = next(f for f in m.fighters if f.team == 0)
        winning = next(f for f in m.fighters if f.team == 1)
        losing.super_cd = winning.super_cd = 1000
        for _ in range(60):
            m.step()
            m.frame += 1
        self.assertLess(losing.super_cd, winning.super_cd)


class TamanhoDaPartidaTest(unittest.TestCase):
    def test_primeiro_a_cinco(self):
        m = futebol(length="5")
        self.assertEqual(m.length_text, "PRIMEIRO A 5")
        for _ in range(4):
            m._goal(0)
        self.assertFalse(m.ending)
        m._goal(0)
        self.assertTrue(m.ending)
        self.assertEqual(m.result_team, 0)

    def test_por_tempo_quem_esta_na_frente_ganha(self):
        m = futebol(length="tempo")
        self.assertEqual(m.length_text, f"{config.SOCCER_MINUTES}:00")
        m._goal(1)
        m.freeze = 0
        m.clock = 1
        m._tick_clock()
        self.assertTrue(m.ending)
        self.assertEqual(m.result_team, 1)

    def test_empate_no_tempo_vira_gol_de_ouro(self):
        m = futebol(length="tempo")
        m.clock = 1
        m._tick_clock()
        self.assertTrue(m.golden_goal)
        self.assertFalse(m.ending)
        self.assertEqual(m.length_text, "GOL DE OURO")
        m._goal(0)
        self.assertTrue(m.ending)
        self.assertEqual(m.result_team, 0)

    def test_relogio_para_com_a_bola_parada(self):
        m = futebol(length="tempo")
        m.freeze = 30
        clock = m.clock
        m._tick_clock()
        self.assertEqual(m.clock, clock)


if __name__ == "__main__":
    unittest.main()
