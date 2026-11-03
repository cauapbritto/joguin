"""Extras da 1.9.0: vibração, revanche rápida no título e estatísticas."""
import unittest

import pygame
from apoio import game

from soulstrike import progress, rumble, settings, stats
from soulstrike.matches import BattleMatch, Result
from soulstrike.scenes.menus import TitleScene
from soulstrike.scenes.play import ResultsScene, VersusScene
from soulstrike.session import Session, SlotSetup


class PadsFalsos:
    def __init__(self):
        self.calls = []

    def rumble(self, slot, low, high, ms):
        self.calls.append(slot)
        return True


class VibracaoTest(unittest.TestCase):
    def setUp(self):
        self.g = game()
        self.pads = PadsFalsos()
        rumble.register(self.pads)
        self.addCleanup(rumble.register, self.g.gamepads)
        self.g.session = Session("cpu", [SlotSetup(1, char=0), SlotSetup(2, char=1, cpu=True)])
        self.match = BattleMatch(self.g, self.g.session)

    def test_apanhar_vibra_so_o_humano(self):
        p1, cpu = self.match.fighters
        rumble.hit(cpu, 10)
        rumble.hit(p1, 10)
        self.assertEqual(self.pads.calls, [1])

    def test_desligar_nas_opcoes(self):
        settings.change("vibracao", False)
        try:
            self.assertFalse(rumble.hit(self.match.fighters[0], 30))
        finally:
            settings.change("vibracao", True)
        self.assertEqual(self.pads.calls, [])


class RevancheTest(unittest.TestCase):
    def test_titulo_oferece_a_revanche(self):
        g = game()
        g.last_session = None
        self.assertNotIn("rematch", [v for _, v in TitleScene(g).menu.options])
        g.session = Session("duel", [SlotSetup(1, char=0), SlotSetup(2, char=1)])
        ResultsScene(g, Result("P1 VENCEU", (255, 255, 255), []))
        title = TitleScene(g)
        values = [v for _, v in title.menu.options]
        self.assertEqual(values[1], "rematch")
        title.menu.index = 1
        title.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=0, unicode="\r"))
        self.assertIsInstance(g.scene, VersusScene)
        self.assertEqual(g.session.mode, "duel")
        g.last_session = None

    def test_treino_nao_vira_revanche(self):
        g = game()
        g.last_session = None
        g.session = Session("treino", [SlotSetup(1, char=0), SlotSetup(2, char=1, cpu=True)])
        ResultsScene(g, Result("FIM", (255, 255, 255), []))
        self.assertIsNone(g.last_session)


class EstatisticasTest(unittest.TestCase):
    def setUp(self):
        data = progress.load()
        data.pop(stats.KEY, None)
        progress.save(data)
        self.g = game()

    def partida(self, mode="cpu", p1_ganha=True):
        self.g.session = Session(mode, [SlotSetup(1, char=0), SlotSetup(2, char=1, cpu=True)])
        match = BattleMatch(self.g, self.g.session)
        winner = match.fighters[0] if p1_ganha else match.fighters[1]
        match.result = Result("FIM", (255, 255, 255), [winner], score=(2, 0))
        return match

    def test_conta_partidas_herois_e_sequencia(self):
        for ganha in (True, True, True, False):
            match = self.partida(p1_ganha=ganha)
            stats.record(self.g.session, match)
        d = stats.load()
        self.assertEqual(d["partidas"]["duelos"], 4)
        self.assertEqual(d["contra_cpu"]["vitorias"], 3)
        self.assertEqual(d["contra_cpu"]["derrotas"], 1)
        self.assertEqual(d["contra_cpu"]["seguidas"], 0)
        self.assertEqual(d["maior_sequencia"]["valor"], 3)
        key, jogos, vitorias = stats.top_heroes(d)[0]
        self.assertEqual((jogos, vitorias), (4, 3))

    def test_treino_nao_conta(self):
        match = self.partida()
        self.g.session.mode = "treino"
        self.assertEqual(stats.record(self.g.session, match), [])
        self.assertEqual(stats.load(), {})

    def test_tela_desenha(self):
        from soulstrike.scenes.stats import StatsScene
        match = self.partida()
        stats.record(self.g.session, match)
        scene = StatsScene(self.g)
        scene.draw(self.g.screen)
