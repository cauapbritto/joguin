"""Campanha: inimigos derrubam armas de outros heróis, troca no chão e cor da raridade."""
import json
import random
import unittest

from test_campanha import campanha, inimigo, passo, pular_intro

from soulstrike import campaign as C
from soulstrike.campaign import CampaignRun
from soulstrike.data import RARE_WEAPONS, RARITY_COLORS, common_weapon, rarity, rarity_color
from soulstrike.dungeon import GroundWeapon


def no_chao(match, weapon, x, y):
    item = GroundWeapon(weapon, (x, y), (x, y))
    item.t = item.TOSS
    match.ground.append(item)
    match.props.append(item)
    return item


class RaridadeTest(unittest.TestCase):
    def test_cores(self):
        self.assertEqual(rarity(common_weapon("Katana")), "comum")
        self.assertEqual(rarity(RARE_WEAPONS["besta"]), "rara")
        self.assertEqual(rarity(RARE_WEAPONS["bola_neve"]), "roubada")
        self.assertEqual(rarity_color(RARE_WEAPONS["besta"]), RARITY_COLORS["rara"])
        self.assertEqual(len(set(RARITY_COLORS.values())), len(RARITY_COLORS))


class DerrubarTest(unittest.TestCase):
    def test_elite_costuma_derrubar_arma_que_ninguem_tem(self):
        random.seed(3)
        match, _ = campanha()
        pular_intro(match)
        drops = 0
        for k in range(20):
            e = inimigo(match, "golem", 600 + k, 600)
            e.hp = 0
            passo(match, 1)
        drops = len(match.ground)
        self.assertGreater(drops, 2)
        self.assertLessEqual(drops, C.MAX_GROUND)
        mine = {w.name for p in match.players for w in p.weapons}
        names = [g.weapon.name for g in match.ground]
        self.assertFalse(mine & set(names))
        self.assertEqual(len(names), len(set(names)))
        self.assertTrue(all(not g.weapon.rare for g in match.ground))


class TrocaTest(unittest.TestCase):
    def test_pegar_comum_troca_a_do_mesmo_tipo(self):
        match, _ = campanha(("guerreiro", "atirador"))
        pular_intro(match)
        p1 = match.players[0]
        p1.x, p1.y = 500, 600
        katana = common_weapon("Katana")
        item = no_chao(match, katana, 520, 600)
        self.assertTrue(match.interact(p1))
        self.assertEqual([w.name for w in p1.base_weapons], ["Arco", "Katana"])
        self.assertIs(p1.weapon, katana)
        self.assertNotIn(item, match.ground)
        self.assertEqual([g.weapon.name for g in match.ground], ["Espada"])     # a dele ficou no chão
        self.assertEqual(match.run.loadouts[1], ["Arco", "Katana"])

    def test_pegar_rara_vai_na_vaga_rara(self):
        match, _ = campanha()
        pular_intro(match)
        p1 = match.players[0]
        p1.x, p1.y = 500, 600
        no_chao(match, RARE_WEAPONS["besta"], 520, 600)
        match.interact(p1)
        self.assertIs(p1.relic, RARE_WEAPONS["besta"])
        self.assertEqual(match.run.relics[1], "besta")

    def test_arma_pega_passa_para_a_proxima_etapa_e_fica_salva(self):
        match, _ = campanha()
        pular_intro(match)
        p1 = match.players[0]
        p1.x, p1.y = 500, 600
        no_chao(match, common_weapon("Pistola"), 520, 600)
        match.interact(p1)
        match.run.carry(match)
        match.run.begin_phase()
        data = json.loads(json.dumps(match.run.to_save()))
        back = CampaignRun.from_save(data)
        self.assertEqual(back.loadouts[1], ["Pistola", "Espada"])
        self.assertIsNone(back.loadouts[2])
        match2, _ = campanha()
        f = match2.players[0]
        f.loadout = None
        back.prepare(f)
        self.assertEqual(f.base_weapons[0].name, "Pistola")

    def test_save_antigo_sem_armas_comuns_ainda_carrega(self):
        match, _ = campanha()
        match.run.begin_phase()
        data = json.loads(json.dumps(match.run.to_save()))
        del data["estado"]["loadouts"]
        self.assertIsNotNone(CampaignRun.from_save(data))
        data["estado"]["loadouts"] = {"1": ["Espada", "Arco"], "2": None}     # ordem errada
        self.assertIsNone(CampaignRun.from_save(data))


if __name__ == "__main__":
    unittest.main()
