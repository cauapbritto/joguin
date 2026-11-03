"""Tela CONTROLE: perfis por controle, troca de botões, Nintendo/Joy-Con e modo teste."""
import unittest

import pygame
from apoio import game

from soulstrike import pad_profiles, settings
from soulstrike.gamepads import Gamepads, Pad
from soulstrike.scenes.menus import ControlsScene, TitleScene
from soulstrike.scenes.pad import PadScene


class Leitor:
    def __init__(self, name="Controle de teste"):
        self.name = name
        self.buttons = set()
        self.axes = {}

    def button(self, name):
        return name in self.buttons

    def axis(self, name):
        return self.axes.get(name, 0.0)


def tecla(key, pad=False):
    return pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode="", from_pad=pad)


class Base(unittest.TestCase):
    def setUp(self):
        game()
        settings.path().unlink(missing_ok=True)
        settings.load()

    def tearDown(self):
        settings.path().unlink(missing_ok=True)
        settings.load()
        game().gamepads = Gamepads(enabled=False)

    def conecta(self, *names):
        pads = Gamepads(enabled=False)
        leitores = [Leitor(n) for n in names]
        pads.pads = [Pad(r) for r in leitores]
        game().gamepads = pads
        return pads, leitores


class PerfisTest(Base):
    def test_familias(self):
        self.assertEqual(pad_profiles.family("Xbox Wireless Controller"), "xbox")
        self.assertEqual(pad_profiles.family("PS5 Controller"), "playstation")
        self.assertEqual(pad_profiles.family("DualSense Wireless Controller"), "playstation")
        self.assertEqual(pad_profiles.family("Nintendo Switch Pro Controller"), "nintendo")
        self.assertEqual(pad_profiles.family("Nintendo Switch Joy-Con (L/R)"), "nintendo")
        self.assertEqual(pad_profiles.family("Nintendo Switch Joy-Con (R)"), "joycon")
        self.assertEqual(pad_profiles.family("Joy-Con (L)"), "joycon")
        self.assertEqual(pad_profiles.family("USB Gamepad"), "xbox")

    def test_padrao_e_o_de_sempre(self):
        luta = pad_profiles.mapping("x", "luta")
        bola = pad_profiles.mapping("x", "bola")
        self.assertEqual((luta["a"], luta["b"], luta["x"], luta["y"]), ("attack", "dodge", "special", "switch"))
        self.assertEqual((bola["rt"], bola["lb"], bola["rb"], bola["y"]), ("sprint", "mark", "dribble", "super"))

    def test_trocar_botao_vira_meu_jeito_e_fica_salvo(self):
        pad_profiles.set_action("Meu", "bola", "rt", "attack")
        self.assertEqual(pad_profiles.preset("Meu"), "meu")
        settings.load()                                   # relê do arquivo
        self.assertEqual(pad_profiles.mapping("Meu", "bola")["rt"], "attack")
        self.assertEqual(pad_profiles.mapping("Meu", "bola")["a"], "attack")      # pode repetir
        self.assertEqual(pad_profiles.changed("Meu", "bola"), {"rt"})
        self.assertEqual(pad_profiles.mapping("Outro", "bola")["rt"], "sprint")   # outro controle não muda
        pad_profiles.set_preset("Meu", "padrao")
        self.assertEqual(pad_profiles.mapping("Meu", "bola")["rt"], "sprint")

    def test_joycon_sem_gatilho(self):
        name = "Nintendo Switch Joy-Con (L)"
        self.assertNotIn("lt", pad_profiles.buttons(name))
        self.assertEqual(pad_profiles.presets(name), ("padrao", "meu"))
        bola = pad_profiles.mapping(name, "bola")
        self.assertEqual(bola["rb"], "sprint")            # CORRER no SR
        self.assertEqual(bola["lb"], "mark")              # MARCAR no SL
        pads, (r,) = self.conecta(name)
        r.buttons = {"rb"}
        held, _, _ = pads.poll({1: "soccer"})
        self.assertIn("p1_sprint", held)

    def test_controle_usa_o_perfil_do_jogador(self):
        pads, (r,) = self.conecta("Meu")
        pad_profiles.set_action("Meu", "bola", "a", "sprint")
        r.buttons = {"a"}
        held, _, _ = pads.poll({1: "soccer"})
        self.assertIn("p1_sprint", held)
        self.assertIn("p1_confirm", held)                 # A continua confirmando nos menus
        self.assertNotIn("p1_attack", held)
        held, _, _ = pads.poll({1: "battle"})
        self.assertIn("p1_attack", held)                  # na luta vale o perfil de luta

    def test_zona_morta(self):
        pads, (r,) = self.conecta("Meu")
        r.axes = {"lx": 0.3}
        pads.poll()
        self.assertNotEqual(pads.pads[0].stick, (0.0, 0.0))
        pad_profiles.set_deadzone("Meu", 0.4)
        pads.poll()
        self.assertEqual(pads.pads[0].stick, (0.0, 0.0))
        self.assertEqual(pad_profiles.set_deadzone("Meu", 9), pad_profiles.DEADZONE_RANGE[1])


class TelaTest(Base):
    def test_titulo_abre_a_tela_do_controle(self):
        g = game()
        self.conecta("Xbox Wireless Controller")
        g.change(TitleScene(g))
        g.scene.menu.index = [v for _, v in g.scene.menu.options].index("controls")
        g.scene.handle(tecla(pygame.K_RETURN))
        self.assertIsInstance(g.scene, PadScene)
        g.scene.handle(tecla(pygame.K_k))
        self.assertIsInstance(g.scene, ControlsScene)
        g.scene.handle(tecla(pygame.K_c))
        self.assertIsInstance(g.scene, PadScene)

    def test_trocar_um_botao_pela_tela(self):
        g = game()
        self.conecta("Nintendo Switch Pro Controller")
        scene = PadScene(g)
        g.scene = scene
        scene.handle(tecla(pygame.K_PAGEDOWN))            # aba FUTEBOL E BASQUETE
        self.assertEqual(scene.ctx, "bola")
        scene.side, scene.row = 1, 0                      # ZR
        self.assertEqual(scene.button, "rt")
        scene.handle(tecla(pygame.K_RETURN))
        self.assertIsNotNone(scene.picking)
        scene.draw(g.screen)
        scene.picking = [a for a, _ in pad_profiles.ACTIONS["bola"]].index("attack")
        scene.handle(tecla(pygame.K_RETURN))
        self.assertIsNone(scene.picking)
        self.assertEqual(pad_profiles.mapping(scene.name, "bola")["rt"], "attack")
        scene.handle(tecla(pygame.K_TAB))                 # próximo perfil
        self.assertEqual(pad_profiles.preset(scene.name), "padrao")

    def test_nintendo_tem_a_na_direita(self):
        g = game()
        self.conecta("Nintendo Switch Pro Controller")
        scene = PadScene(g)
        self.assertEqual(scene.right_column(), ["rt", "rb", "x", "y", "a", "b"])
        self.conecta("Xbox Wireless Controller")
        self.assertEqual(scene.right_column(), ["rt", "rb", "y", "x", "b", "a"])

    def test_modo_teste_e_desenhos(self):
        g = game()
        for name in ("Xbox Wireless Controller", "PS5 Controller", "Nintendo Switch Pro Controller",
                     "Nintendo Switch Joy-Con (R)"):
            pads, (r,) = self.conecta(name)
            scene = PadScene(g)
            g.scene = scene
            for ctx in (0, 1):
                scene.context = ctx
                scene.draw(g.screen)
            scene.handle(tecla(pygame.K_c))
            self.assertTrue(scene.testing)
            scene.handle(tecla(pygame.K_ESCAPE, pad=True))   # botão do controle não sai do teste
            self.assertTrue(scene.testing)
            r.buttons = {"b"}
            pads.poll()
            scene.update()
            self.assertEqual(scene.last_test, "b")
            scene.draw(g.screen)
            r.buttons = {"start"}
            for _ in range(45):
                pads.poll()
                scene.update()
            self.assertFalse(scene.testing)

    def test_sem_controle_mostra_aviso(self):
        g = game()
        g.gamepads = Gamepads(enabled=False)
        scene = PadScene(g)
        scene.draw(g.screen)
        scene.handle(tecla(pygame.K_RETURN))
        self.assertIsNone(scene.picking)
        self.assertTrue(scene.message)


if __name__ == "__main__":
    unittest.main()
