"""Modo treino: as lições avançam, ninguém perde e a partida não acaba sozinha."""
import unittest

import pygame
from apoio import FakeInput, game

from soulstrike import config
from soulstrike.matches import create_match
from soulstrike.scenes.menus import MODE_TEXT, ModeScene
from soulstrike.scenes.select import CharSelectScene
from soulstrike.session import MODES, Session, SlotSetup
from soulstrike.training import DONE_FRAMES, LESSONS, DummyAI, TrainingMatch


def treino(char=0):
    g = game()
    g.session = Session("treino", [SlotSetup(1, char=char), SlotSetup(2, char=1, cpu=True)])
    match = create_match(g, g.session)
    inp = FakeInput()
    match.controllers[match.player] = inp
    return match, inp


def rodar(match, inp, frames):
    for _ in range(frames):
        before = match.frame
        match.update()
        if match.frame != before:
            inp.end_frame()


def pular_intro(match, inp):
    rodar(match, inp, config.ROUND_INTRO_FRAMES + 5)
    assert match.active


def perto_do_boneco(match):
    p, d = match.player, match.dummy
    p.x, p.y = d.x - 60, d.y
    p.facing = (1.0, 0.0)


class TreinoTest(unittest.TestCase):
    def test_cria_a_partida_certa(self):
        match, _ = treino()
        self.assertIsInstance(match, TrainingMatch)
        self.assertIsInstance(match.controllers[match.dummy], DummyAI)
        self.assertEqual(match.dummy.full_name, "BONECO DE TREINO")
        self.assertIn("treino", MODES)
        self.assertIn("treino", MODE_TEXT)

    def test_boneco_fica_parado(self):
        match, inp = treino()
        pular_intro(match, inp)
        x, y = match.dummy.x, match.dummy.y
        rodar(match, inp, 200)
        self.assertEqual((match.dummy.x, match.dummy.y), (x, y))
        self.assertEqual(match.player.hp, match.player.max_hp)

    def test_licao_de_andar(self):
        match, inp = treino()
        pular_intro(match, inp)
        inp.stick = (1.0, 0.0)
        rodar(match, inp, 60)
        self.assertTrue(match.done_timer > 0 or match.lesson == 1)
        inp.stick = (0.0, 0.0)
        rodar(match, inp, DONE_FRAMES + 30)
        self.assertEqual(match.lesson, 1)

    def test_licao_de_atacar_e_trocar(self):
        match, inp = treino()
        pular_intro(match, inp)
        match.lesson = 1
        match._begin_lesson()
        perto_do_boneco(match)
        inp.hold("attack")
        for _ in range(240):
            perto_do_boneco(match)
            rodar(match, inp, 1)
            if match.done_timer:
                break
        inp.release("attack")
        self.assertTrue(match.done_timer, "atacar o boneco não completou a lição")
        rodar(match, inp, DONE_FRAMES + 30)      # + quadros de pausa de impacto
        self.assertEqual(match.lesson, 2)
        inp.tap("switch")
        rodar(match, inp, 2)
        self.assertTrue(match.done_timer, "trocar de arma não completou a lição")

    def test_licao_de_esquiva_e_habilidade(self):
        match, inp = treino()
        pular_intro(match, inp)
        match.lesson = 4
        match._begin_lesson()
        inp.stick = (1.0, 0.0)
        inp.tap("dodge")
        rodar(match, inp, 3)
        self.assertTrue(match.done_timer, "esquivar não completou a lição")
        inp.stick = (0.0, 0.0)
        rodar(match, inp, DONE_FRAMES + 30)      # + quadros de pausa de impacto
        self.assertEqual(match.lesson, 5)
        perto_do_boneco(match)
        inp.tap("special")
        rodar(match, inp, 3)
        self.assertTrue(match.done_timer, "usar a habilidade não completou a lição")

    def test_licao_do_item(self):
        match, inp = treino()
        pular_intro(match, inp)
        self.assertEqual(match.pickups, [])
        match.lesson = 6
        match._begin_lesson()
        self.assertEqual(len(match.pickups), 1)
        item = match.pickups[0]
        for _ in range(60):
            match.player.x, match.player.y = item.x, item.y
            rodar(match, inp, 1)
            if match.done_timer:
                break
        self.assertTrue(match.done_timer)
        rodar(match, inp, DONE_FRAMES + 30)      # + quadros de pausa de impacto
        self.assertEqual(match.lesson, 7)        # a última: o arsenal (ver test_arsenal.py)

    def test_ninguem_perde_e_nao_acaba(self):
        match, inp = treino()
        pular_intro(match, inp)
        match.dummy.hp = 1
        match.player.hp = 1
        rodar(match, inp, 5)
        self.assertGreater(match.dummy.hp, 1)
        self.assertGreater(match.player.hp, 1)
        match.dummy.hp = 0                          # caiu mesmo assim: levanta
        rodar(match, inp, 5)
        self.assertGreater(match.dummy.hp, 0)
        rodar(match, inp, config.ROUND_SECONDS * config.FPS + 100)
        self.assertFalse(match.finished)
        self.assertEqual(match.time_left, config.ROUND_SECONDS * config.FPS)
        self.assertEqual(match.pickups, [])         # itens só na lição

    def test_desenha_todas_as_licoes(self):
        match, inp = treino()
        screen = game().screen
        for i in range(len(LESSONS) + 1):
            match.lesson = i
            match.done_timer = 0
            match.draw(screen, game().ui)
            match.done_timer = 5
            match.draw(screen, game().ui)
            match.draw_hud(screen, game().ui)

    def test_menu_leva_para_a_selecao(self):
        g = game()
        scene = ModeScene(g)
        g.scene = scene
        scene.menu.index = [v for _, v in scene.menu.options].index("treino")
        scene.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=0, unicode=""))
        self.assertIsInstance(g.scene, CharSelectScene)
        self.assertEqual(g.session.mode, "treino")
        self.assertTrue(g.session.slots[1].cpu)
        g.scene.draw(g.screen)
        g.scene.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode=""))
        self.assertIsInstance(g.scene, ModeScene)
        g.scene.draw(g.screen)


if __name__ == "__main__":
    unittest.main()
