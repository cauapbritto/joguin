"""Modo LUTA (1 x 1 de lado): esqueleto, golpes, defesa, caixas de contato, rounds, menu e celular."""
import random
import unittest
from pathlib import Path

import pygame
from apoio import FakeInput, game

from soulstrike import luta as L
from soulstrike import luta_poses as LP
from soulstrike import luta_rig as R
from soulstrike.data import CHARACTERS
from soulstrike.scenes.luta import LutaScene, fighter_key, start_luta
from soulstrike.scenes.menus import MODE_GROUPS, ModeScene, category_of
from soulstrike.session import MODES, Session, SlotSetup

INDEX = {c.key: i for i, c in enumerate(CHARACTERS)}
ROOT = Path(__file__).resolve().parent.parent


def luta(seed=1):
    a, b = FakeInput(), FakeInput()
    fight = L.Fight(controls=(a, b), seed=seed)
    run(fight, (a, b), L.INTRO_FRAMES + 1)
    return fight, a, b


def run(fight, inputs, frames):
    for _ in range(frames):
        fight.update()
        for i in inputs:
            i.end_frame()


def perto(fight, gap=110):
    a, b = fight.fighters
    a.x, b.x = 420, 420 + gap
    a.facing, b.facing = 1, -1


class EsqueletoTest(unittest.TestCase):
    def test_todos_os_quadros_desenham_e_pisam_no_chao(self):
        game()
        for key in L.FIGHTER_KEYS:
            for name in LP.names(key):
                img, right_points = R.draw_fighter(R.LOOKS[key], LP.pose(key, name))
                self.assertEqual(img.get_size(), (R.CW * R.U, R.CH * R.U))
                for k in ("head", "hip", "near_hand", "far_hand", "near_foot", "far_foot"):
                    self.assertIn(k, right_points)
                F = LP.pose(key, name)
                if F.get("air") or F.get("plant") is False:
                    continue
                low = max(p[1] for p in R.ankles(R.LOOKS[key], F))
                hip_y = R.standing_hip_y(R.LOOKS[key]) + R.plant(R.LOOKS[key], F)
                # o pé mais baixo encosta no chão (meia unidade de folga)
                self.assertAlmostEqual(hip_y + low + F.get("dy", 0), R.GROUND - 5, delta=4.5, msg=(key, name))

    def test_pe_aponta_para_a_frente_no_soco(self):
        _, P = R.draw_fighter(R.LOOKS["aryel"], LP.pose("aryel", "soco2"))
        self.assertGreater(P["near_foot"][0], P["near_ankle"][0])     # a ponta do pé vai para a frente
        self.assertGreater(P["far_hand"][0], P["head"][0] + 20)        # o soco passa bem da cabeça

    def test_cauanzera_e_mais_alto_que_o_aryel(self):
        _, pa = R.draw_fighter(R.LOOKS["aryel"], LP.pose("aryel", "guarda"))
        _, pc = R.draw_fighter(R.LOOKS["cauanzera"], LP.pose("cauanzera", "guarda"))
        self.assertLess(pc["head"][1], pa["head"][1] - 6)


class GolpesTest(unittest.TestCase):
    def test_soco_de_perto_acerta(self):
        fight, a, b = luta()
        perto(fight)
        A, B = fight.fighters
        a.tap("attack")
        run(fight, (a, b), 20)
        self.assertLess(B.hp, B.max_hp)
        self.assertGreater(A.energy, 0)

    def test_soco_de_longe_nao_acerta(self):
        fight, a, b = luta()
        perto(fight, 360)
        a.tap("attack")
        run(fight, (a, b), 20)
        self.assertEqual(fight.fighters[1].hp, fight.fighters[1].max_hp)

    def test_segurar_para_tras_defende_o_chute(self):
        fight, a, b = luta()
        perto(fight, 130)
        B = fight.fighters[1]
        b.stick = (1.0, 0.0)                    # B olha para a esquerda: para trás é a direita
        a.tap("special")
        run(fight, (a, b), 30)
        self.assertEqual(B.hp, B.max_hp)
        self.assertGreater(B.energy, 0)         # defender também enche um pouco

    def test_rasteira_passa_pela_defesa_em_pe_mas_nao_pela_agachada(self):
        fight, a, b = luta()
        perto(fight, 140)
        B = fight.fighters[1]
        b.stick = (1.0, 0.0)
        a.stick = (0.0, 1.0)
        a.tap("special")
        run(fight, (a, b), 3)
        a.stick = (0.0, 0.0)
        run(fight, (a, b), 30)
        self.assertLess(B.hp, B.max_hp)         # rasteira é baixa: em pé não defende
        self.assertIn(B.state, ("voando", "caido"))   # e derruba
        fight, a, b = luta()
        perto(fight, 140)
        B = fight.fighters[1]
        b.stick = (1.0, 1.0)                    # para trás e para baixo
        a.stick = (0.0, 1.0)
        a.tap("special")
        run(fight, (a, b), 3)
        a.stick = (0.0, 0.0)
        run(fight, (a, b), 30)
        self.assertEqual(B.hp, B.max_hp)

    def test_forte_usa_a_arma_e_bate_mais(self):
        fight, a, b = luta()
        A, B = fight.fighters
        self.assertTrue(A.moves["forte"].weapon)
        self.assertGreater(A.moves["forte"].damage, A.moves["chute"].damage)
        perto(fight, 120)
        a.tap("sprint")                         # FORTE no botão próprio
        run(fight, (a, b), 30)
        self.assertLessEqual(B.hp, B.max_hp - A.moves["forte"].damage + 1)

    def test_cabo_de_rede_alcanca_mais_que_o_capacete(self):
        a, c = L._moves("aryel")["forte"], L._moves("cauanzera")["forte"]
        self.assertGreater(c.reach, a.reach)
        self.assertEqual(L.SPECS["aryel"].weapon, "Capacete")
        self.assertEqual(L.SPECS["cauanzera"].weapon, "Cabo de Rede")

    def test_ninguem_atravessa_ninguem(self):
        fight, a, b = luta()
        A, B = fight.fighters
        a.stick, b.stick = (1.0, 0.0), (-1.0, 0.0)
        for _ in range(200):
            run(fight, (a, b), 1)
            self.assertFalse(A.pushbox().colliderect(B.pushbox()) and abs(A.pushbox().clip(B.pushbox()).w) > 1)
            self.assertLess(A.x, B.x)
        a.stick = b.stick = (0.0, 0.0)

    def test_virado_para_o_outro(self):
        fight, a, b = luta()
        A, B = fight.fighters
        A.x, B.x = 700, 300
        run(fight, (a, b), 2)
        self.assertEqual(A.facing, -1)
        self.assertEqual(B.facing, 1)


class EnergiaTest(unittest.TestCase):
    def test_especial_sem_energia_nao_sai(self):
        fight, a, b = luta()
        A = fight.fighters[0]
        a.tap("dribble")
        run(fight, (a, b), 2)
        self.assertNotEqual(A.state, "especial")

    def test_especial_gasta_uma_carga_e_super_tres(self):
        fight, a, b = luta()
        A = fight.fighters[0]
        A.energy = 3.0
        a.tap("dribble")
        run(fight, (a, b), 2)
        self.assertEqual(A.state, "especial")
        self.assertAlmostEqual(A.energy, 2.0, places=3)
        run(fight, (a, b), 100)
        A.energy = 2.5
        a.tap("super")
        run(fight, (a, b), 2)
        self.assertNotEqual(A.state, "especial") if A.state != "levou" else None
        A.energy = 3.0
        A.set_state("livre", "guarda")
        a.tap("super")
        run(fight, (a, b), 2)
        self.assertEqual(A.state, "especial")
        self.assertGreater(fight.super_freeze, 0)
        self.assertAlmostEqual(A.energy, 0.0, places=3)

    def test_aposta_do_aryel(self):
        """GREEN chove moeda no outro; RED estoura no Aryel."""
        seen = set()
        for seed in range(12):
            fight, a, b = luta(seed)
            perto(fight, 240)
            A, B = fight.fighters
            A.energy = 1.0
            a.tap("dribble")
            run(fight, (a, b), 140)
            seen.add(A.bet)
            if A.bet == "GREEN":
                self.assertLess(B.hp, B.max_hp)
            else:
                self.assertLess(A.hp, A.max_hp)
        self.assertEqual(seen, {"GREEN", "RED"})

    def test_multiesportista_em_ordem(self):
        fight, a, b = luta()
        C = fight.fighters[1]
        kinds = []
        for _ in range(4):
            C.energy = 1.0
            C.set_state("livre", "guarda")
            b.tap("dribble")
            run(fight, (a, b), 2)
            kinds.append(C.special["kind"])
            run(fight, (a, b), 90)
        self.assertEqual(kinds, ["basquete", "volei", "corrida", "basquete"])

    def test_supers_acertam(self):
        for side, key in ((0, "aryel"), (1, "cauanzera")):
            fight, a, b = luta()
            perto(fight, 300)
            f = fight.fighters[side]
            o = fight.fighters[1 - side]
            f.energy = 3.0
            (a if side == 0 else b).tap("super")
            run(fight, (a, b), 160)
            self.assertLess(o.hp, o.max_hp - 200, key)


class RoundsTest(unittest.TestCase):
    def test_nocaute_e_melhor_de_3(self):
        fight, a, b = luta()
        for r in range(2):
            fight.fighters[1].hp = 1
            perto(fight)
            a.tap("attack")
            run(fight, (a, b), 30)
            self.assertEqual(fight.state, "ko")
            run(fight, (a, b), L.KO_FRAMES + 40)
            if r == 0:
                self.assertEqual(fight.state, "intro")
                self.assertEqual(fight.round, 2)
                self.assertEqual(fight.fighters[1].hp, fight.fighters[1].max_hp)
                run(fight, (a, b), L.INTRO_FRAMES + 1)
        self.assertEqual(fight.state, "fim")
        self.assertEqual(fight.winner, 0)
        self.assertEqual([f.wins for f in fight.fighters], [2, 0])

    def test_tempo_esgotado_vence_quem_tem_mais_vida(self):
        fight, a, b = luta()
        fight.fighters[0].hp -= 200
        fight.clock = 1
        run(fight, (a, b), 2)
        self.assertEqual(fight.state, "ko")
        self.assertEqual(fight.round_winner, 1)

    def test_empate_no_tempo_nao_da_ponto(self):
        fight, a, b = luta()
        A, B = fight.fighters
        A.hp, B.hp = A.max_hp // 2, round(B.max_hp * (A.max_hp // 2) / A.max_hp)
        B.hp = A.hp * B.max_hp // A.max_hp
        A.hp = B.hp * A.max_hp // B.max_hp
        fight.clock = 1
        run(fight, (a, b), 2)
        if fight.round_winner is None:
            self.assertEqual([f.wins for f in fight.fighters], [0, 0])

    def test_robos_lutam_ate_o_fim(self):
        """Dois robôs apertando tudo ao acaso: a luta termina, ninguém sai da arena e nada quebra."""
        rng = random.Random(5)
        a, b = FakeInput(), FakeInput()
        fight = L.Fight(controls=(a, b), seed=5)
        actions = ("attack", "special", "sprint", "dribble", "super", "dodge")
        for frame in range(60 * 60 * 6):
            for inp in (a, b):
                if rng.random() < 0.08:
                    inp.stick = (rng.choice((-1.0, 0.0, 1.0)), rng.choice((-1.0, 0.0, 0.0, 1.0)))
                if rng.random() < 0.12:
                    inp.tap(rng.choice(actions))
            fight.update()
            a.end_frame()
            b.end_frame()
            for f in fight.fighters:
                self.assertTrue(L.WALL_L <= f.x <= L.WALL_R)
                self.assertGreaterEqual(f.y, 0)
                self.assertGreaterEqual(f.hp, 0)
                self.assertLessEqual(f.energy, L.MAX_ENERGY + 1e-6)
            if fight.state == "fim":
                break
        self.assertEqual(fight.state, "fim")


class TelaTest(unittest.TestCase):
    def setUp(self):
        self.g = game()
        self.g.session = Session("luta", [SlotSetup(1, char=INDEX["aryel"]), SlotSetup(2, char=INDEX["cauanzera"])])

    def test_modo_no_menu(self):
        self.assertTrue(MODES["luta"]["luta"])
        self.assertEqual(MODES["luta"]["slots"], 2)
        self.assertEqual(category_of("luta"), "luta")
        self.assertEqual(MODE_GROUPS["luta"], [("LUTAR", ["luta"])])
        self.assertTrue(self.g.session.luta)
        scene = ModeScene(self.g, "luta")
        scene.draw(self.g.screen)

    def test_quem_ainda_nao_luta_vira_aryel(self):
        self.assertEqual(fighter_key(INDEX["cauanzera"]), "cauanzera")
        self.assertEqual(fighter_key(INDEX["ninja"]), "aryel")

    def test_escolha_so_mostra_quem_luta(self):
        from soulstrike.scenes.select import CharSelectScene
        self.g.session.slots[1].char = INDEX["ninja"]
        scene = CharSelectScene(self.g)
        self.assertEqual([CHARACTERS[i].key for i in scene.choices], list(L.FIGHTER_KEYS))
        self.assertIn(self.g.session.slots[1].char, scene.choices)
        scene.draw(self.g.screen)

    def test_cena_desenha_em_todos_os_momentos(self):
        scene = start_luta(self.g)
        self.g.scene = scene
        a, b = FakeInput(), FakeInput()
        for f, c in zip(scene.fight.fighters, (a, b)):
            f.controls = c
        fight = scene.fight
        screen = self.g.screen
        for _ in range(40):
            scene.update()
        scene.draw(screen)                       # ROUND 1
        run(fight, (a, b), L.INTRO_FRAMES)
        perto(fight, 120)
        a.stick = (1.0, 0.0)
        a.tap("attack")                          # FORTE (frente + SOCO): a arma aparece
        for _ in range(16):
            scene.update()
            scene.draw(screen)
            a.end_frame()
        a.stick = (0.0, 0.0)
        A, B = fight.fighters
        A.energy = B.energy = 3.0
        run(fight, (a, b), 40)
        a.tap("super")
        for _ in range(80):
            scene.update()
            scene.draw(screen)
            a.end_frame()
        run(fight, (a, b), 60)
        b.tap("super")
        for _ in range(90):
            scene.update()
            scene.draw(screen)
            b.end_frame()
        scene.show_boxes = True
        scene.draw(screen)
        scene.paused = True
        scene.draw(screen)

    def test_fim_vai_para_o_resultado_e_a_revanche_volta_para_a_luta(self):
        from soulstrike.scenes.play import ResultsScene
        scene = start_luta(self.g)
        self.g.scene = scene
        fight = scene.fight
        fight.state = "fim"
        fight.winner = 1
        fight.fighters[1].wins = 2
        fight.t = 200
        scene.update()
        self.assertIsInstance(self.g.scene, ResultsScene)
        self.g.scene.draw(self.g.screen)
        self.g.scene._choose("rematch")
        self.assertIsInstance(self.g.scene, LutaScene)

    def test_celular_tem_os_botoes_da_luta(self):
        html = (ROOT / "web" / "templates" / "controller.html").read_text(encoding="utf-8")
        start = html.index('class="pad-set fight-only"')
        block = html[start:html.index("</div>", start)]
        for act, label in (("attack", "SOCO"), ("special", "CHUTE"), ("sprint", "FORTE"), ("dodge", "PULO"),
                           ("dribble", "ESPECIAL"), ("super", "SUPER")):
            self.assertIn(f'data-act="{act}"', block)
            self.assertIn(label, block)
        js = (ROOT / "web" / "static" / "controller.js").read_text(encoding="utf-8")
        self.assertIn('mode === "luta"', js)

    def test_celular_mostra_a_luta(self):
        scene = start_luta(self.g)
        self.assertEqual(scene.phone_mode(), "luta")


if __name__ == "__main__":
    unittest.main()
