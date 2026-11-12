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
    """Bolsa de 3 armas quaisquer: com vaga, a nova só entra; cheia, troca pela da mão (que cai no chão)."""

    def _p1(self, chars=("guerreiro", "atirador")):
        match, _ = campanha(chars)
        pular_intro(match)
        p1 = match.players[0]
        p1.x, p1.y = 500, 600
        return match, p1

    def test_com_vaga_a_arma_entra_na_bolsa(self):
        match, p1 = self._p1()
        katana = common_weapon("Katana")
        item = no_chao(match, katana, 520, 600)
        self.assertTrue(match.interact(p1))
        self.assertEqual([w.name for w in p1.weapons], ["Arco", "Espada", "Katana"])
        self.assertIs(p1.weapon, katana)
        self.assertNotIn(item, match.ground)
        self.assertEqual(match.ground, [])
        self.assertEqual(match.run.bags[1], ["comum:Arco", "comum:Espada", "comum:Katana"])

    def test_bolsa_cheia_troca_pela_da_mao_que_fica_no_chao(self):
        match, p1 = self._p1()
        no_chao(match, RARE_WEAPONS["besta"], 520, 600)
        match.interact(p1)
        p1.weapon_index = 0                                     # Arco na mão
        no_chao(match, common_weapon("Pistola"), 520, 600)
        match.interact(p1)
        self.assertEqual([w.name for w in p1.weapons], ["Pistola", "Espada", RARE_WEAPONS["besta"].name])
        self.assertEqual([g.weapon.name for g in match.ground], ["Arco"])     # a do herói não some
        self.assertTrue(match.ground[0].by_player)
        self.assertEqual(match.run.bags[1][2], "rara:besta")

    def test_qualquer_tipo_cabe_ate_tres_rara(self):
        match, p1 = self._p1()
        match.drop_held(p1)
        match.drop_held(p1)
        self.assertEqual(p1.bag, [])
        self.assertEqual(p1.weapon.name, "Soco")                # bolsa vazia = soco
        for key in ("besta", "canhao", "bumerangue"):
            no_chao(match, RARE_WEAPONS[key], 520, 600)
            match.interact(p1)
        self.assertEqual(len(p1.bag), 3)
        self.assertTrue(all(w.rare for w in p1.weapons))

    def test_amigo_pega_a_arma_do_seu_heroi(self):
        match, p1 = self._p1()
        p2 = match.players[1]
        p1.weapon_index = 0
        match.drop_held(p1)                                     # larga o Arco
        arco = match.ground[0]
        arco.t = arco.TOSS
        arco.x, arco.y = arco.end
        p2.x, p2.y = arco.x + 10, arco.y
        self.assertTrue(match.interact(p2))
        self.assertIn("Arco", [w.name for w in p2.weapons])
        self.assertNotIn("Arco", [w.name for w in p1.weapons])

    def test_arma_que_o_jogador_largou_nunca_some_sozinha(self):
        match, p1 = self._p1()
        match.drop_held(p1)
        mine = match.ground[0]
        for k in range(C.MAX_GROUND + 6):
            item = GroundWeapon(common_weapon("Katana"), (100, 100), (100 + k, 100))
            match.ground.append(item)
            match.props.append(item)
        match.drop_held(match.players[1])                       # a limpeza roda ao cair arma nova
        self.assertEqual(len([g for g in match.ground if not g.by_player]), C.MAX_GROUND)
        self.assertIn(mine, match.ground)

    def test_arma_pega_passa_para_a_proxima_etapa_e_fica_salva(self):
        match, p1 = self._p1(("guerreiro", "atirador"))
        no_chao(match, common_weapon("Pistola"), 520, 600)
        match.interact(p1)
        match.run.carry(match)
        match.run.begin_phase()
        data = json.loads(json.dumps(match.run.to_save()))
        back = CampaignRun.from_save(data)
        self.assertEqual(back.bags[1], ["comum:Arco", "comum:Espada", "comum:Pistola"])
        match2, _ = campanha(("guerreiro", "atirador"))
        f = match2.players[0]
        back.prepare(f)
        self.assertEqual([w.name for w in f.weapons], ["Arco", "Espada", "Pistola"])

    def test_save_antigo_vira_bolsa(self):
        match, _ = campanha(("guerreiro", "atirador"))
        match.run.begin_phase()
        data = json.loads(json.dumps(match.run.to_save()))
        del data["estado"]["bags"]
        data["versao"] = 2
        data["estado"]["relics"] = {"1": "besta", "2": None}
        data["estado"]["loadouts"] = {"1": ["Katana"], "2": None}
        back = CampaignRun.from_save(data)
        self.assertEqual(back.bags[1], ["comum:Arco", "comum:Katana", "rara:besta"])
        self.assertIsNone(back.bags[2])
        data["estado"]["relics"] = {"1": "espada_falsa", "2": None}
        self.assertIsNone(CampaignRun.from_save(data))

    def test_bolsa_estranha_no_save_e_recusada(self):
        match, _ = campanha()
        match.run.begin_phase()
        data = json.loads(json.dumps(match.run.to_save()))
        data["estado"]["bags"] = {"1": ["comum:Arco"] * 5}              # nem com a Mochila Grande cabem 5
        self.assertIsNone(CampaignRun.from_save(data))


if __name__ == "__main__":
    unittest.main()
