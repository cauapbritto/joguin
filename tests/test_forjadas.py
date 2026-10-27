"""Fusão no ferreiro e as 8 armas forjadas."""
import json
import unittest

from apoio import game
from test_campanha import campanha, inimigo, passo, pular_intro
from test_mercado import abrir, acampamento, apertar

from soulstrike import config, forged, progress
from soulstrike.campaign import CampaignRun
from soulstrike.data import RARE_WEAPONS, common_weapon, rarity
from soulstrike.forged import FORGED, FUSION_COST, RECIPES, recipe
from soulstrike.training import DummyAI
from soulstrike import weapon_art

R = RARE_WEAPONS


class ReceitaTest(unittest.TestCase):
    def test_oito_forjadas_uma_por_familia(self):
        self.assertEqual(len(FORGED), 8)
        self.assertEqual(set(RECIPES.values()), set(FORGED))
        self.assertTrue(all(w.forjada and rarity(w) == "forjada" for w in FORGED.values()))
        best_rare = max(w.damage for w in R.values() if not w.forjada and w.is_melee)
        self.assertGreater(FORGED["lamina_solar"].damage, best_rare)

    def test_familia_que_mais_aparece(self):
        w = [common_weapon("Arco"), common_weapon("Espada"), R["besta"]]
        self.assertEqual(recipe(w), ("arco_mil_almas", 1, None))
        w = [common_weapon("Cristal"), common_weapon("Cajado"), R["bola_neve"]]
        self.assertEqual(recipe(w), ("coracao_inverno", 2, "gelo"))
        w = [common_weapon("Granada"), common_weapon("Capacete"), R["machado"]]
        self.assertEqual(recipe(w)[0], "lamina_solar")    # empate: vale a família da rara

    def test_toda_forjada_tem_arte(self):
        game()
        weapon_art.load()
        for w in FORGED.values():
            self.assertIsNotNone(weapon_art.icon(w.name), w.name)


class FusaoTest(unittest.TestCase):
    def setUp(self):
        data = progress.load()
        data.pop("forjadas", None)
        progress.save(data)

    def test_fundir_no_ferreiro(self):
        match, inputs = acampamento(souls=1000)
        p = match.players[0]
        p.give_relic(R["besta"])
        p.forge["Arco"] = [2, None]
        p, menu = abrir(match, inputs[1], "ferreiro")
        entries = menu.entries()
        self.assertEqual(entries[-1].label, "FUNDIR AS 3 ARMAS")
        self.assertIn("???", entries[-1].desc)               # receita nova
        menu.index = len(entries) - 1
        apertar(match, inputs[1], "attack")
        self.assertIs(p.relic, FORGED["arco_mil_almas"])
        self.assertEqual(match.run.relics[1], "arco_mil_almas")
        self.assertEqual(p.forge, {"Arco das Mil Almas": [1, None]})   # as do herói voltaram ao +0
        self.assertEqual(match.run.souls, 1000 - FUSION_COST)
        self.assertIn("arco_mil_almas", forged.discovered())
        self.assertIsNone(menu._fusion_entry())                # forjada não entra em outra fusão
        match.run.begin_phase()
        back = CampaignRun.from_save(json.loads(json.dumps(match.run.to_save())))
        self.assertEqual(back.relics[1], "arco_mil_almas")
        self.assertEqual(back.fused_phase, 0)

    def test_uma_fusao_por_mercado(self):
        match, inputs = acampamento(souls=1000)
        match.run.fused_phase = match.run.phase_index
        p = match.players[0]
        p.give_relic(R["besta"])
        p, menu = abrir(match, inputs[1], "ferreiro")
        self.assertFalse(menu.entries()[-1].ok)


def masmorra(weapon_key, enemies=("esqueleto", "esqueleto", "esqueleto")):
    match, _ = campanha()
    pular_intro(match)
    p = match.players[0]
    p.give_relic(FORGED[weapon_key])
    p.x, p.y, p.facing = 500, 600, (1.0, 0.0)
    foes = []
    for k, kind in enumerate(enemies):
        e = inimigo(match, kind, 560 + k * 70, 600)
        match.controllers[e] = DummyAI()
        e.hp = e.max_hp = 2000
        foes.append(e)
    return match, p, foes


class ForjadasTest(unittest.TestCase):
    def test_lamina_solar_solta_onda_e_gira_no_terceiro(self):
        match, p, foes = masmorra("lamina_solar")
        for _ in range(3):
            p.attack_cd = 0
            p.attack(match, foes[0])
        self.assertEqual(sum(1 for b in match.bullets if b.weapon.style == "solar"), 3)
        passo(match, 20)
        self.assertLess(foes[2].hp, 2000)                    # a onda atravessa e chega no último

    def test_martelo_cai_raio_e_atordoa(self):
        match, p, foes = masmorra("martelo_trovao")
        p.attack(match, foes[0])
        self.assertTrue(all(f.hp < 2000 for f in foes))
        self.assertTrue(foes[2].stunned)

    def test_martelo_arremessa_no_terceiro_e_volta(self):
        match, p, foes = masmorra("martelo_trovao")
        far = foes[2]
        far.x = p.x + 300                                    # longe da batida no chão
        for _ in range(3):
            p.attack_cd = 0
            p.attack(match, foes[0])
        hammers = [b for b in match.bullets if b.weapon.style == "trovao"]
        self.assertEqual(len(hammers), 1)
        p.attack_cd = 0
        for _ in range(3):
            p.attack(match, foes[0])
            p.attack_cd = 0
        self.assertEqual(sum(1 for b in match.bullets if b.weapon.style == "trovao"), 1)   # um de cada vez
        hp = far.hp
        passo(match, 60)
        self.assertLess(far.hp, hp)                           # o martelo chega no de longe
        self.assertTrue(hammers[0].returning)
        passo(match, 120)
        self.assertFalse(hammers[0].alive)                    # voltou para a mão
        self.assertNotIn(hammers[0], match.bullets)

    def test_martelo_arremessado_persegue_tres_inimigos(self):
        match, p, foes = masmorra("martelo_trovao")
        for k, f in enumerate(foes):                         # longe da batida no chão e espalhados
            f.x, f.y = p.x + 320 + 90 * k, p.y + (-150 if k == 1 else 140 * (k == 2))
            match.arena.resolve(f)
        p.forged_count = 2
        p.attack_cd = 0
        p.attack(match, foes[0])
        hammer = next(b for b in match.bullets if b.weapon.style == "trovao")
        self.assertEqual(len(hammer.targets), 3)
        hp = [f.hp for f in foes]
        for _ in range(150):
            passo(match, 1)
            if hammer.returning:
                break
        self.assertTrue(all(f.hp < h for f, h in zip(foes, hp)), "o martelo não acertou os três")
        self.assertTrue(hammer.returning)

    def test_martelo_sem_alvo_vai_longe(self):
        match, p, foes = masmorra("martelo_trovao")
        for f in foes:
            f.x = p.x + 2000
        p.forged_count = 2
        p.attack_cd = 0
        p.attack(match, foes[0])
        hammer = next(b for b in match.bullets if b.weapon.style == "trovao")
        self.assertEqual(hammer.targets, [])
        x0 = hammer.x
        best = 0
        for _ in range(60):
            passo(match, 1)
            best = max(best, abs(hammer.x - x0))
        self.assertGreater(best, 450)                        # antes ia uns 340 px

    def test_arco_das_mil_almas_solta_doze(self):
        match, p, foes = masmorra("arco_mil_almas")
        p.bow_draw = 999
        p.bow_target = foes[0]
        p._release_bow(match)
        self.assertEqual(len(match.bullets), 12)
        self.assertEqual({b.target for b in match.bullets}, set(foes))
        passo(match, 60)
        self.assertTrue(all(f.hp < 2000 for f in foes))

    def test_canhao_do_vazio_puxa_e_explode(self):
        match, p, foes = masmorra("canhao_vazio")
        p.attack(match, foes[1])
        far = foes[2]
        far.x = foes[1].x + 150
        x0 = far.x
        passo(match, 30)
        self.assertLess(far.x, x0)
        passo(match, 2 * config.FPS + 20)
        self.assertLess(far.hp, 2000)

    def test_coracao_do_inverno_congela_e_estoura(self):
        match, p, foes = masmorra("coracao_inverno", ("esqueleto",))
        e = foes[0]
        for _ in range(3):
            p.attack_cd = 0
            p.attack(match, e)
            passo(match, 8)
        self.assertGreater(e.frozen_timer, 0)
        hp = e.hp
        p.attack_cd = 0
        p.attack(match, e)
        passo(match, 20)
        self.assertEqual(e.frozen_timer, 0)
        self.assertLess(e.hp, hp - 30)

    def test_dragao_queima_e_dura_tres_segundos(self):
        match, p, foes = masmorra("lanca_dragao")
        p.attack(match, foes[0])
        passo(match, 60)
        self.assertTrue(any(f.burn_timer > 0 or f.hp < 2000 for f in foes))
        self.assertTrue(match.bullets)
        passo(match, 3 * config.FPS)
        self.assertFalse(match.bullets)

    def test_cetro_pula_em_todos_e_cresce(self):
        match, p, foes = masmorra("cetro_tempestade")
        p.attack(match, foes[0])
        first = 2000 - foes[2].hp
        self.assertGreater(first, 0)
        for _ in range(120):                                  # segura ATACAR
            p.attack(match, foes[0])
            match.update()
        hp = foes[2].hp
        p.attack_cd = 0
        p.attack(match, foes[0])
        self.assertGreater(hp - foes[2].hp, first)

    def test_foice_cura_e_da_dano_por_abate(self):
        match, p, foes = masmorra("foice_ceifador", ("esqueleto",))
        e = foes[0]
        e.hp = 1
        p.hp = 50
        p.attack(match, e)
        self.assertGreater(p.hp, 50)
        self.assertAlmostEqual(p.reaper, 0.05)


if __name__ == "__main__":
    unittest.main()
