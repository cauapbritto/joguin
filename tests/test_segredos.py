"""Segredos: os detalhezinhos escondidos (reações discretas, cacos na primeira vez e o caderno)."""
import unittest

import pygame

from apoio import game

from soulstrike import cacos, computador, config, progress, segredos
from soulstrike.casa import NAP_FRAMES, SCARE_HITS, STREAK_ANGRY
from test_casa import casa_da_turma, passo, reset_progress


def perto(p, rect, dy=12):
    p.x, p.y = rect.centerx, rect.bottom + dy


class Pote(unittest.TestCase):
    def setUp(self):
        reset_progress()

    def test_cacos_so_na_primeira_vez(self):
        self.assertTrue(segredos.find("wifi"))
        self.assertEqual(cacos.balance(), segredos.REWARD)
        self.assertFalse(segredos.find("wifi"))
        self.assertEqual(cacos.balance(), segredos.REWARD)
        self.assertEqual(segredos.found(), {"wifi"})

    def test_chave_desconhecida_nao_conta(self):
        self.assertFalse(segredos.find("nao_existe"))
        progress.save({segredos.KEY: ["nao_existe", "wifi", 3]})
        self.assertEqual(segredos.found(), {"wifi"})

    def test_caderno_mostra_achados_e_dicas(self):
        segredos.find("cochilo")
        pages = segredos.notebook()
        casa = pages["CASA"]
        self.assertIn((True, "COCHILO NO SOFÁ"), casa)
        self.assertTrue(all(text.startswith("???") for ok, text in casa if not ok))
        self.assertEqual(segredos.count(), (1, len(segredos.SECRETS)))

    def test_chaves_unicas_e_textos_curtos(self):
        keys = [s[0] for s in segredos.SECRETS]
        self.assertEqual(len(keys), len(set(keys)))
        for key, place, name, tip in segredos.SECRETS:
            self.assertIn(place, segredos.PLACES)
            self.assertLessEqual(len(name), 24, name)
            self.assertLessEqual(len("??? · " + tip), 40, tip)


class Casa(unittest.TestCase):
    def setUp(self):
        reset_progress()
        self.match, self.inputs = casa_da_turma(("guerreiro", "atirador"))
        self.p1, self.p2 = self.match.players

    def test_roteador_derruba_o_wifi(self):
        perto(self.p1, self.match.router)
        self.assertTrue(self.match.interact(self.p1))
        self.assertGreater(self.match.wifi_down, 0)
        self.assertTrue(segredos.is_found("wifi"))
        alb = [s for s in self.match.speakers if s.key == "albeguinio" and s.talk > 0]
        self.assertTrue(alb and alb[0].line == "JÁ REINICIOU O WI-FI?")
        pc = computador.make(self.match, self.p1, "pc", (0, 0))
        pc.open_app("navegador")
        self.assertEqual(pc.page_lines()[0], "SEM INTERNET")
        nb = computador.make(self.match, self.p1, "notebook", (0, 0))
        nb.run("wifi --reiniciar")
        for _ in range(60):
            nb.step()
        self.assertEqual(self.match.wifi_down, 0)

    def test_espantalho_balanca_e_reclama(self):
        perto(self.p1, self.match.scarecrow_rect)
        for _ in range(SCARE_HITS - 1):
            self.assertTrue(self.match.interact(self.p1))
        self.assertGreater(self.match.scarecrow.wobble, 0)
        self.assertFalse(segredos.is_found("espantalho"))
        self.match.interact(self.p1)
        self.assertTrue(segredos.is_found("espantalho"))
        view = pygame.Surface((config.SCREEN_W, config.SCREEN_H))
        self.match.scarecrow.draw(view, self.match.camera)

    def test_mangueira_molha_o_amigo(self):
        perto(self.p1, self.match.hose)
        self.p1.facing = (1.0, 0.0)
        self.p2.x, self.p2.y = self.match.hose.right + 80, self.match.hose.centery
        self.assertTrue(self.match.interact(self.p1))
        passo(self.match, self.inputs, 10)
        self.assertIn(self.p2, self.match.wet)
        self.assertTrue(segredos.is_found("mangueira"))

    def test_cochilo_do_lado_do_sofa(self):
        sofa = self.match.sofas[0]
        self.p1.x, self.p1.y = sofa.centerx, sofa.bottom + 20
        passo(self.match, self.inputs, NAP_FRAMES + 5)
        self.assertTrue(segredos.is_found("cochilo"))

    def test_insistir_na_conversa(self):
        s = next(s for s in self.match.speakers if s.key == "tanque")
        self.p1.x, self.p1.y = s.x, s.y + 30
        for _ in range(STREAK_ANGRY):
            s.say(self.match)
        self.assertEqual(s.line, "DE NOVO?!")
        self.assertTrue(segredos.is_found("de_novo"))

    def test_madrugada_boceja(self):
        old = segredos._hour
        segredos._hour = lambda: 3
        try:
            s = next(s for s in self.match.speakers if s.key == "ninja")
            s.say(self.match)
            self.assertIn(s.line, __import__("soulstrike.casa", fromlist=["SONO"]).SONO)
            s.say(self.match)
            self.assertIn(s.line, s.lines)
        finally:
            segredos._hour = old
        self.assertTrue(segredos.is_found("madrugada"))

    def test_caderno_no_computador(self):
        segredos.find("wifi")
        pc = computador.make(self.match, self.p1, "pc", (0, 0))
        self.assertIn(("caderno", "CADERNO"), pc.desktop_items())
        pc.open_app("caderno")
        surf = pygame.Surface((computador.INNER_W, computador.INNER_H))
        pc.draw_inner(surf, game().ui, surf.get_rect())


if __name__ == "__main__":
    unittest.main()
