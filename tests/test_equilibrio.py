"""Equilíbrio: velocidade com bola, Hack no 1 x 1, Exoesqueleto, Investida e Muralha que devolve tiros."""
import unittest

from apoio import game

from soulstrike import config
from soulstrike.abilities import Exoesqueleto, Hacker
from soulstrike.data import CHARACTERS
from soulstrike.entities import Barrier, Bullet, Hack
from soulstrike.matches import BattleMatch, SoccerMatch, TeamBattleMatch
from soulstrike.session import Session, SlotSetup
from soulstrike.training import DummyAI

KEYS = [c.key for c in CHARACTERS]


def duelo(a, b, mode="duel"):
    g = game()
    g.session = Session(mode, [SlotSetup(1, char=KEYS.index(a), cpu=True), SlotSetup(2, char=KEYS.index(b), cpu=True)])
    match = BattleMatch(g, g.session)
    for f in match.fighters:
        match.controllers[f] = DummyAI()       # parados (o teste mexe neles)
    match.intro = 0
    return match


class VelocidadeComBolaTest(unittest.TestCase):
    def test_lentos_e_rapidos_ficam_mais_perto(self):
        self.assertAlmostEqual(config.ball_mode_speed(2), 2.75)
        self.assertAlmostEqual(config.ball_mode_speed(4.5), 4.0)
        self.assertAlmostEqual(config.ball_mode_speed(3.5), 3.5)

    def test_so_no_futebol_e_no_basquete(self):
        g = game()
        g.session = Session("soccer1", [SlotSetup(1, char=KEYS.index("tanque"), cpu=True),
                                        SlotSetup(2, char=KEYS.index("velocista"), cpu=True)])
        tanque, velocista = SoccerMatch(g, g.session).fighters
        self.assertAlmostEqual(tanque.speed, 2.75)
        self.assertAlmostEqual(velocista.speed, 4.0)
        a, b = duelo("tanque", "velocista").fighters
        self.assertEqual((a.speed, b.speed), (2, 4.5))


class DueloTest(unittest.TestCase):
    def test_hack_mais_curto_no_1x1(self):
        match = duelo("albeguinio", "guerreiro")
        hacker, alvo = match.fighters
        hacker.ability.activate(hacker, match, alvo)
        hack = next(e for e in match.effects if isinstance(e, Hack))
        self.assertEqual(hack.freeze, 3 * config.FPS)
        self.assertFalse(TeamBattleMatch.single_duel)
        self.assertEqual(Hacker.FREEZE, 5 * config.FPS)

    def test_exoesqueleto_dura_quatro_segundos_e_meio(self):
        self.assertEqual(Exoesqueleto.FRAMES, round(4.5 * config.FPS))

    def test_investida_deixa_tonto(self):
        match = duelo("guerreiro", "atirador")
        g, alvo = match.fighters
        g.x, g.y, alvo.x, alvo.y = 400, 500, 480, 500
        g.facing = (1.0, 0.0)
        g.use_ability(match, alvo)
        for _ in range(20):
            match.update()
            if alvo.stunned:
                break
        self.assertTrue(alvo.stunned)

    def test_muralha_devolve_o_tiro(self):
        match = duelo("tanque", "atirador")
        tanque, atirador = match.fighters
        tanque.x, tanque.y, atirador.x, atirador.y = 400, 500, 700, 500
        match.add_effect(Barrier(tanque, 440, 500, 1, 0, 4 * config.FPS))
        match.bullets.append(Bullet(atirador, 470, 494, -1, 0, 10, 10, (255, 255, 255)))
        hp = atirador.hp
        for _ in range(60):
            match._update_bullets()
        self.assertLess(atirador.hp, hp)
        self.assertEqual(tanque.hp, tanque.max_hp)


if __name__ == "__main__":
    unittest.main()
