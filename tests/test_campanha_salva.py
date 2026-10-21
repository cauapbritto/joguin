"""Campanha salva no começo de cada fase: continua depois de fechar o jogo."""
import json
import unittest

import pygame
from apoio import game

from soulstrike import progress
from soulstrike.campaign import PHASES, CampaignRun, LobbyMatch
from soulstrike.scenes.campaign import CampaignEndScene, start_phase
from soulstrike.scenes.menus import ModeScene
from soulstrike.scenes.play import PlayScene
from soulstrike.session import Session, SlotSetup
from soulstrike.upgrades import UPGRADES


def enter():
    return pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=0, unicode="")


def campanha():
    session = Session("campaign", [SlotSetup(1, char=2, weapon=1), SlotSetup(2, char=5)], difficulty="dificil")
    run = CampaignRun(session)
    up = sorted(UPGRADES)[0]
    run.phase_index = 1
    run.add_upgrade(1, up)
    run.hp_ratio = {1: 0.5, 2: 0.9}
    run.kills = {1: 12, 2: 3}
    run.damage = {1: 900, 2: 120}
    run.held = {1: 1, 2: 0}
    run.frames = 5000
    run.continues = 2
    return run


def pelo_arquivo(run):
    run.begin_phase()
    return json.loads(json.dumps(run.to_save()))      # passa pelo JSON como no progresso.json


class CampanhaSalvaTest(unittest.TestCase):
    def setUp(self):
        progress.clear_campaign()

    tearDown = setUp

    def test_ida_e_volta(self):
        run = campanha()
        back = CampaignRun.from_save(pelo_arquivo(run))
        self.assertIsNotNone(back)
        self.assertEqual(back._state(), run._state())
        self.assertEqual(back.session.difficulty, "dificil")
        self.assertEqual([(s.slot, s.char, s.weapon) for s in back.session.slots], [(1, 2, 1), (2, 5, 0)])
        self.assertTrue(back.session.campaign)

    def test_arquivo_estranho_e_ignorado(self):
        data = pelo_arquivo(campanha())
        ruins = []
        for change in (lambda d: d.update(versao=99),
                       lambda d: d.update(dificuldade="impossivel"),
                       lambda d: d["estado"].update(phase_index=len(PHASES)),
                       lambda d: d["estado"]["upgrades"].update({"1": ["nao_existe"]}),
                       lambda d: d["estado"]["relics"].update({"1": "espada_falsa"}),
                       lambda d: d["estado"]["kills"].pop("2"),
                       lambda d: d["jogadores"][0].update(char=999),
                       lambda d: d["jogadores"].append({"slot": 1, "char": 0, "weapon": 0}),
                       lambda d: d.pop("estado")):
            bad = json.loads(json.dumps(data))
            change(bad)
            ruins.append(CampaignRun.from_save(bad))
        self.assertEqual(ruins, [None] * len(ruins))
        self.assertIsNone(CampaignRun.from_save({}))

    def test_comecar_fase_salva(self):
        g = game()
        run = campanha()
        g.session = run.session
        start_phase(g, run, story=False)
        saved = progress.saved_campaign()
        self.assertIsNotNone(saved)
        self.assertEqual(saved["estado"]["phase_index"], 1)

    def test_menu_continua(self):
        g = game()
        self.assertNotIn("continue", [v for _, v in ModeScene(g).menu.options])
        run = campanha()
        g.session = run.session
        start_phase(g, run, story=False)
        g.session = None
        scene = ModeScene(g)
        g.scene = scene
        self.assertEqual(scene.menu.value, "continue")       # primeira opção
        scene.draw(g.screen)
        scene.handle(enter())
        self.assertIsInstance(g.scene, PlayScene)
        match = g.scene.match
        self.assertIsInstance(match, LobbyMatch)
        self.assertEqual(match.run.phase_index, 1)
        self.assertEqual(g.session.difficulty, "dificil")
        p1 = next(f for f in match.players if f.slot == 1)
        self.assertEqual(p1.hp, round(p1.max_hp * 0.5))
        for _ in range(30):
            g.step([])

    def test_zerar_apaga_o_salvo(self):
        g = game()
        run = campanha()
        g.session = run.session
        start_phase(g, run, story=False)
        CampaignEndScene(g, run)
        self.assertIsNone(progress.saved_campaign())

    def test_salvo_ruim_nao_aparece(self):
        progress.save_campaign({"versao": 1, "lixo": True})
        self.assertNotIn("continue", [v for _, v in ModeScene(game()).menu.options])


if __name__ == "__main__":
    unittest.main()
