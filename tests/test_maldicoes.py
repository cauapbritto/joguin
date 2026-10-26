"""Desafios da campanha: a maldição do altar deixa a fase mais difícil e dá +1 melhoria no fim."""
import json
import random
import unittest

import pygame
from test_campanha import campanha, inimigo, passo, pular_intro
from test_mercado import abrir, acampamento, apertar

from soulstrike import market as M
from soulstrike.campaign import CampaignRun
from soulstrike.scenes.campaign import UpgradeScene


class AltarTest(unittest.TestCase):
    def test_escolher_maldicao_no_altar(self):
        match, inputs = acampamento(back=False)
        p, menu = abrir(match, inputs[1], "altar")
        apertar(match, inputs[1], stick=(0.0, 1.0))      # inimigos fortes
        apertar(match, inputs[1], "attack")
        self.assertEqual(match.run.curse, "fortes")
        self.assertTrue(menu.entries()[1].label.startswith(">"))
        match.run.begin_phase()
        back = CampaignRun.from_save(json.loads(json.dumps(match.run.to_save())))
        self.assertEqual(back.curse, "fortes")


class EfeitoTest(unittest.TestCase):
    def test_inimigos_fortes_e_rapidos(self):
        normal, _ = campanha()
        e0 = inimigo(normal, "esqueleto", 600, 600)
        forte, _ = campanha()
        forte.run.curse = "fortes"
        e1 = inimigo(forte, "esqueleto", 600, 600)
        self.assertEqual(e1.max_hp, round(e0.max_hp * M.CURSE_HP))
        rapido, _ = campanha()
        rapido.run.curse = "rapidos"
        e2 = inimigo(rapido, "esqueleto", 600, 600)
        self.assertAlmostEqual(e2.speed, e0.speed * M.CURSE_SPEED)

    def test_sem_itens_de_vida(self):
        random.seed(5)
        match, _ = campanha()
        pular_intro(match)
        match.run.curse = "sem_vida"
        for k in range(40):
            e = inimigo(match, "golem", 600 + k, 600)
            e.hp = 0
            passo(match, 1)
        self.assertTrue(match.pickups)
        self.assertFalse(any(p.kind == "vida" for p in match.pickups))


class RecompensaTest(unittest.TestCase):
    def test_melhoria_a_mais(self):
        match, _ = campanha()
        run = match.run
        run.curse = "rapidos"
        scene = UpgradeScene(match.game, run, lambda: scene)
        scene.locked = {s: True for s in run.slots}
        for _ in range(50):
            scene.update()
        self.assertTrue(all(len(run.upgrades[s]) == 2 for s in run.slots))
        self.assertIsNone(run.curse)


if __name__ == "__main__":
    unittest.main()
