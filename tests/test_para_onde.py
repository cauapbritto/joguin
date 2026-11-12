"""PARA ONDE? o menu de escolher o capítulo ao entrar no carro, e os carros novos da viagem."""
import unittest
from types import SimpleNamespace

import pygame

from apoio import FakeInput, game

from soulstrike import casa_art, para_onde, progress
from soulstrike.scenes.viagem import CarTripScene


class _Assets:
    def play(self, *a, **k):
        pass


class _Match:
    assets = _Assets()


_P1 = SimpleNamespace(label="P1", color=(84, 162, 222), x=480, y=470, slot=1)


def _abre(current=1):
    picked = []
    menu = para_onde.ChapterPickMenu(_Match(), _P1, picked.append, current)
    inp = FakeInput()
    menu.handle(inp)                      # o quadro em que abriu
    return menu, inp, picked


def _aperta(menu, inp, action=None, stick=(0.0, 0.0)):
    inp._pressed.clear()
    inp.stick = stick
    if action:
        inp.tap(action)
    return menu.handle(inp)


class ParaOndeTest(unittest.TestCase):
    def setUp(self):
        progress.save({})

    def test_so_o_capitulo_1_sem_nada_zerado(self):
        self.assertTrue(para_onde.unlocked(1))
        self.assertFalse(para_onde.unlocked(2))
        progress.save({"capitulo1_zerado": True, "capitulo2_zerado": True})
        self.assertTrue(para_onde.unlocked(3))
        self.assertFalse(para_onde.unlocked(4))

    def test_escolhe_e_fecha(self):
        progress.save({"capitulo1_zerado": True})
        menu, inp, picked = _abre()
        _aperta(menu, inp, stick=(0.0, 1.0))      # desce para o 2
        self.assertFalse(_aperta(menu, inp, "attack"))
        self.assertEqual(picked, [2])

    def test_trancado_nao_vai(self):
        menu, inp, picked = _abre(current=3)
        self.assertTrue(_aperta(menu, inp, "attack"))
        self.assertEqual(picked, [])
        self.assertFalse(_aperta(menu, inp, "dodge"))

    def test_desenha(self):
        g = game()
        menu, _, _ = _abre()
        screen = pygame.Surface((960, 540), pygame.SRCALPHA)
        menu.draw(screen, g.ui, (480, 400))
        w = screen.get_bounding_rect().w
        self.assertGreater(w, 200)
        self.assertLess(w, 300)                   # janela pequena (era 380)


class CarrosTest(unittest.TestCase):
    def test_carros_novos_mesmo_ponto_no_chao(self):
        for fn in (casa_art.city_car, casa_art.uno_car, casa_art.moto):
            b = casa_art.bake(fn)
            self.assertLess(abs(b.dy + b.image.get_height() - 10), 12, fn.__name__)   # pé perto do y pedido
            self.assertLess(abs(b.dx + b.image.get_width() / 2), 20, fn.__name__)      # meio perto do x pedido

    def test_viagem_com_a_turma_atras_do_vidro(self):
        g = game()
        sprites = [g.assets.sprites[k] for k in ("guerreiro", "atirador")]
        for vehicle in ("city", "uno", "moto"):
            scene = CarTripScene(g, sprites, 2, lambda: None, vehicle=vehicle)
            self.assertTrue(scene.hd)
            self.assertIsNotNone(scene.glass)
            screen = pygame.Surface((960, 540))
            for t in (10, 300, 400):
                scene.ticks = t
                scene.draw(screen)
