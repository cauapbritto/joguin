"""Vaga de equipamento: um por herói, troca deixando o velho no chão, e os 12 efeitos."""
import json
import unittest

from apoio import FakeInput  # noqa: F401  (prepara o pygame sem janela)
from test_armas_raras import campo, inimigo
from test_mercado import abrir, acampamento, apertar

from soulstrike import energia, equipamento
from soulstrike.campaign import CampaignRun
from soulstrike.data import RARE_WEAPONS, common_weapon


def no_chao(match, key, x, y):
    item = match.drop_gear(match.players[0], key, at=(x, y))
    item.t = item.TOSS
    item.x, item.y = item.end
    return item


class VagaTest(unittest.TestCase):
    def test_doze_equipamentos(self):
        self.assertEqual(len(equipamento.GEAR), 12)
        for key in equipamento.GEAR:
            self.assertEqual(equipamento.icon(key).get_size(), (27, 27))

    def test_pegar_troca_e_o_velho_fica_no_chao(self):
        match, p = campo("besta")
        item = no_chao(match, "amuleto", p.x + 20, p.y)
        self.assertTrue(match.interact(p))
        self.assertEqual(p.gear, "amuleto")
        self.assertEqual(p.energy_max, energia.ENERGY_MAX + equipamento.AMULET)
        self.assertNotIn(item, match.gear_items)
        no_chao(match, "cracha", p.x + 20, p.y)
        cd = p.cd_mult
        match.interact(p)
        self.assertEqual(p.gear, "cracha")
        self.assertEqual(p.energy_max, energia.ENERGY_MAX)          # o amuleto saiu
        self.assertAlmostEqual(p.cd_mult, cd * equipamento.BADGE_CD)
        self.assertEqual([g.key for g in match.gear_items], ["amuleto"])
        self.assertEqual(match.run.gear[1], "cracha")

    def test_fica_salvo_e_volta_na_proxima_etapa(self):
        match, p = campo("besta")
        match.equip(p, "coracao")
        hp = p.max_hp
        match.run.carry(match)
        back = CampaignRun.from_save(json.loads(json.dumps(match.run.to_save())))
        self.assertEqual(back.gear[1], "coracao")
        match2, q = campo("besta")
        q.gear, q.max_hp = None, q.stats.max_hp
        back.prepare(q)
        self.assertEqual(q.gear, "coracao")
        self.assertEqual(q.max_hp, hp)
        data = json.loads(json.dumps(match.run.to_save()))
        data["estado"]["gear"]["1"] = "nao_existe"
        self.assertIsNone(CampaignRun.from_save(data))

    def test_mochila_da_quarta_vaga_e_tirar_derruba(self):
        match, p = campo("besta")
        match.equip(p, "mochila")
        match.give_weapon(p, common_weapon("Katana"))
        self.assertEqual(len(p.weapons), 4)
        match.equip(p, "pilha")
        self.assertEqual(len(p.weapons), 3)
        self.assertIn("Katana", [g.weapon.name for g in match.ground])

    def test_luva_presa_bota_ampulheta(self):
        match, p = campo("besta")
        rifle = common_weapon("Rifle")                                    # arma do Atirador
        self.assertEqual(energia.cost(p, rifle), 1)
        match.equip(p, "luva")
        self.assertEqual(energia.cost(p, rifle), 0)
        self.assertGreater(energia.cost(p, RARE_WEAPONS["canhao"]), 0)      # rara continua gastando
        match.equip(p, "presa")
        p.energy, p.hp = 0, 50
        alvo = inimigo(match, "esqueleto", p.x + 300, p.y)
        alvo.hp = 1
        alvo.take_damage(5, attacker=p, match=match)
        self.assertEqual((p.energy, p.hp), (3, 52))
        match.equip(p, "bota")
        p.energy = 0
        energia.on_perfect_dodge(p, match)
        self.assertEqual(p.energy, 2 * energia.PERFECT_DODGE)
        match.equip(p, "ampulheta")
        p.energy = 0
        energia.on_ability(p)
        self.assertEqual(p.energy, 30)
        p.energy = 0
        energia.on_ability(p)
        self.assertEqual(p.energy, 0)                                     # uma vez só

    def test_capa_segura_o_golpe_uma_vez(self):
        match, p = campo("besta")
        match.equip(p, "capa")
        p.hp = 5
        p.take_damage(50, match=match)
        self.assertEqual(p.hp, 1)
        p.invulnerable_timer = 0
        p.take_damage(50, match=match)
        self.assertLessEqual(p.hp, 0)

    def test_pilha_enche_parado(self):
        match, p = campo("besta")
        match.equip(p, "pilha")
        p.energy = 0
        p.input = (0.0, 0.0)
        for _ in range(equipamento.BATTERY_EVERY * 2):
            match._regen_energy()
        self.assertEqual(p.energy, 2)

    def test_coldre_recarrega_a_que_sai(self):
        match, p = campo("besta")
        match.equip(p, "coldre")
        p.weapon_index = 0
        clip = p.clip(p.weapon)
        clip.ammo = 1
        arco = p.weapon
        p.switch_weapon()
        self.assertEqual(p.clip(arco).ammo, p.mag_of(arco))

    def test_loja_vende_equipamento(self):
        match, inputs = acampamento(souls=200)
        p, menu = abrir(match, inputs[1], "loja")
        menu.pick("equipamento")
        apertar(match, inputs[1], "attack")
        self.assertEqual(len(match.gear_items), 1)
        self.assertEqual(match.run.souls[1], 200 - equipamento.SHOP_COST)

    def test_bau_solta_um_equipamento(self):
        from test_masmorra import BauTest
        t = BauTest()
        match, _ = t._abrir()
        self.assertEqual(len(match.gear_items), 1)

    def test_hud_mostra_o_equipamento(self):
        match, p = campo("besta")
        match.equip(p, "talisma")
        for _ in range(3):
            match.update()
        match.draw(match.game.screen, match.game.ui)


if __name__ == "__main__":
    unittest.main()
