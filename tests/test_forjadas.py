"""Fusão no ferreiro, as 8 forjadas puras e as 41 novas (híbridas, secretas e de assinatura)."""
import json
import unittest

from apoio import game
from test_campanha import campanha, inimigo, passo, pular_intro
from test_mercado import abrir, acampamento, apertar

from soulstrike import config, forged, progress
from soulstrike.campaign import CampaignRun
from soulstrike.data import RARE_WEAPONS, common_weapon, rarity
from soulstrike.forged import FORGED, FUSION_COST, PURE, RECIPES, recipe
from soulstrike.training import DummyAI
from soulstrike import weapon_art

R = RARE_WEAPONS


class ReceitaTest(unittest.TestCase):
    def test_oito_forjadas_uma_por_familia(self):
        self.assertEqual(len(FORGED), 8 + 41)                 # as 8 puras e as 41 novas
        self.assertEqual(set(RECIPES.values()), PURE)
        self.assertTrue(all(w.forjada and rarity(w) == "forjada" for w in FORGED.values()))
        best_rare = max(w.damage for w in R.values() if not w.forjada and w.is_melee)
        self.assertGreater(FORGED["lamina_solar"].damage, best_rare)

    def test_familia_que_mais_aparece(self):
        w = [common_weapon("Arco"), common_weapon("Espada"), R["besta"]]
        self.assertEqual(recipe(w), ("arco_mil_almas", 1, None))
        w = [common_weapon("Cristal"), common_weapon("Orbe"), R["bola_neve"]]
        self.assertEqual(recipe(w), ("coracao_inverno", 2, "gelo"))     # gelo + alma: sem híbrida, sai a pura
        w = [common_weapon("Granada"), common_weapon("Capacete"), R["machado"]]
        self.assertEqual(recipe(w)[0], "lamina_solar")    # empate: vale a família da rara

    def test_toda_forjada_tem_arte(self):
        game()
        weapon_art.load()
        for w in FORGED.values():
            self.assertIsNotNone(weapon_art.icon(w.name), w.name)


class ReceitasNovasTest(unittest.TestCase):
    def test_41_novas_com_arte_dica_e_tipo(self):
        game()
        weapon_art.load()
        novas = [k for k in FORGED if k not in PURE]
        self.assertEqual(len(novas), 41)
        for k in novas:
            w = FORGED[k]
            self.assertTrue(w.forjada and w.note, k)
            self.assertIsNotNone(weapon_art.icon(w.name), k)
            self.assertTrue(forged.hint(k), k)
            self.assertTrue(forged.kind_label(k), k)
        self.assertEqual(len(forged.recipe_book(set())), 49)

    def test_secreta_vem_antes_de_tudo(self):
        w = [R["lanca_chamas"], R["macarico"], R["secador"]]
        self.assertEqual(recipe(w)[0], "bafo_dragao")
        w = [common_weapon("Cristal"), R["cajado_gelo"], R["bola_neve"]]
        self.assertEqual(recipe(w)[0], "era_do_gelo")

    def test_hibrida_duas_de_uma_e_uma_de_outra(self):
        w = [common_weapon("Katana"), common_weapon("Faca"), R["lanca_chamas"]]
        self.assertEqual(recipe(w), ("katana_brasa", 1, None))
        w = [common_weapon("Granada"), R["canhao"], R["cajado_raio"]]
        self.assertEqual(recipe(w)[0], "granada_tesla")

    def test_assinatura_do_heroi(self):
        from soulstrike.data import CHARACTERS
        from soulstrike.forjadas_novas import SIGNATURES

        class Dono:
            pass
        for c in CHARACTERS:
            if c.key not in SIGNATURES:
                continue
            dono = Dono()
            dono.stats = c
            w = list(c.weapons) + [R["besta"]]
            self.assertEqual(recipe(w, dono)[0], SIGNATURES[c.key], c.key)
            self.assertNotEqual(recipe(list(c.weapons) + [common_weapon("Katana")], dono)[0], SIGNATURES[c.key])
        self.assertEqual(len(SIGNATURES), 17)

    def test_cada_forjada_nova_funciona(self):
        for k in [k for k in FORGED if k not in PURE]:
            match, p, _ = masmorra(k, enemies=())
            e = inimigo(match, "golem", p.x + (50 if FORGED[k].is_melee else 140), p.y)
            e.hp = e.max_hp = 100000
            for _ in range(3):
                p.attack_cd = 0
                p.face(e)
                p.attack(match, e)
                for _ in range(20):
                    match._update_bullets()
                    for eff in list(match.effects):
                        eff.update(match)
                    match.effects = [x for x in match.effects if x.alive]
            self.assertLess(e.hp, e.max_hp, k)

    def test_livro_de_receitas_no_ferreiro(self):
        match, inputs = acampamento(souls=100)
        p, menu = abrir(match, inputs[1], "ferreiro")
        book = next(e for e in menu.entries() if e.key == "livro")
        self.assertIn("/49", book.label)
        first = book.desc
        menu.index = len(menu.entries()) - 1
        apertar(match, inputs[1], "attack")
        self.assertNotEqual(next(e for e in menu.entries() if e.key == "livro").desc, first)    # outra dica


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
        self.assertEqual(entries[-2].label, "FUNDIR AS 3 ARMAS")
        self.assertIn("???", entries[-2].desc)               # receita nova
        self.assertEqual(entries[-1].key, "livro")           # e o livro de receitas, sempre por último
        menu.index = len(entries) - 2
        apertar(match, inputs[1], "attack")
        self.assertIs(p.weapon, FORGED["espada_primeiro"])
        self.assertEqual(match.run.bags[1], ["rara:espada_primeiro"])
        self.assertEqual(p.forge, {"Espada do Primeiro Guerreiro": [1, None]})   # as do herói voltaram ao +0
        self.assertEqual(match.run.souls[1], 1000 - FUSION_COST)
        self.assertIn("espada_primeiro", forged.discovered())    # as 2 do guerreiro + rara: assinatura
        self.assertIsNone(menu._fusion_entry())                # forjada não entra em outra fusão
        self.assertEqual(p.weapons, (FORGED["espada_primeiro"],))  # as três viraram uma só
        self.assertFalse(p.switch_weapon())                   # nada para trocar
        match.run.begin_phase()
        back = CampaignRun.from_save(json.loads(json.dumps(match.run.to_save())))
        self.assertEqual(back.bags[1], ["rara:espada_primeiro"])
        self.assertEqual(back.fused_phase, 0)

    def test_fusao_usa_as_3_da_bolsa_e_a_forjada_ocupa_uma_vaga(self):
        match, inputs = acampamento(souls=1000)
        p = match.players[0]
        p.give_relic(R["besta"])
        p, menu = abrir(match, inputs[1], "ferreiro")
        menu.index = len(menu.entries()) - 2
        apertar(match, inputs[1], "attack")
        forjada = p.weapon
        self.assertTrue(forjada.forjada)
        self.assertEqual(p.weapons, (forjada,))
        apertar(match, inputs[1], "dodge")
        n = len(match.ground)
        maca, katana, pistola = common_weapon("Maça"), common_weapon("Katana"), common_weapon("Pistola")
        match.give_common(p, maca)                             # cabem mais 2 ao lado da forjada
        match.give_common(p, katana)
        self.assertEqual(p.weapons, (forjada, maca, katana))
        self.assertEqual(len(match.ground), n)
        match.give_common(p, pistola)                          # bolsa cheia: troca pela da mão
        self.assertEqual(p.weapons, (forjada, maca, pistola))
        self.assertEqual(len(match.ground), n + 1)             # a katana caiu no chão
        p.weapon_index = 0
        match.drop_held(p)                                     # larga a forjada: ela vai para o chão
        self.assertEqual(p.weapons, (maca, pistola))
        self.assertIn(forjada, [g.weapon for g in match.ground])

    def test_sem_bolsa_cheia_nao_funde(self):
        match, inputs = acampamento(souls=1000)
        p, menu = abrir(match, inputs[1], "ferreiro")
        self.assertIsNone(menu._fusion_entry())

    def test_forjada_com_comum_ao_lado_sobrevive_ao_save(self):
        match, inputs = acampamento(souls=1000)
        p = match.players[0]
        p.give_relic(R["besta"])
        p, menu = abrir(match, inputs[1], "ferreiro")
        menu.index = len(menu.entries()) - 2
        apertar(match, inputs[1], "attack")
        apertar(match, inputs[1], "dodge")
        forjada = p.weapon
        pistola, katana = common_weapon("Pistola"), common_weapon("Katana")
        match.give_common(p, pistola)
        match.give_common(p, katana)
        self.assertEqual(p.weapons, (forjada, pistola, katana))
        match.run.carry(match)
        back = CampaignRun.from_save(json.loads(json.dumps(match.run.to_save())))
        self.assertEqual(back.bags[1][1:], ["comum:Pistola", "comum:Katana"])
        f = match.players[0]
        f.bag = None
        back.prepare(f)
        self.assertEqual(f.weapons, (forjada, pistola, katana))

    def test_uma_fusao_por_mercado(self):
        match, inputs = acampamento(souls=1000)
        match.run.fused_phase = match.run.phase_index
        p = match.players[0]
        p.give_relic(R["besta"])
        p, menu = abrir(match, inputs[1], "ferreiro")
        self.assertFalse(menu.entries()[-2].ok)


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

    def test_martelo_com_tiro_de_inimigo_no_ar(self):
        # tiro de inimigo, chefe ou habilidade não tem arma: o 3º golpe não pode fechar o jogo
        match, p, foes = masmorra("martelo_trovao")
        match.spawn_bullet(foes[0], 0, 1, 1, 1)
        p.forged_count = 2
        p.attack_cd = 0
        p.attack(match, foes[0])
        self.assertEqual(sum(1 for b in match.bullets if getattr(getattr(b, "weapon", None), "style", "") == "trovao"), 1)

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
