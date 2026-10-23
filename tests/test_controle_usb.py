"""Controle USB (com leitor falso, sem precisar do aparelho) e troca de teclas do teclado."""
import unittest

import pygame
from apoio import game

from soulstrike import settings
from soulstrike.controls import (REBINDABLE, RESERVED_KEYS, PlayerInput, bind_key, build_keymap, current_key,
                                 default_key, key_label, move_label, reset_keys)
from soulstrike.gamepads import Gamepads, Pad
from soulstrike.scenes.menus import ControlsScene, ModeScene, OptionsScene, RebindScene, TitleScene


class LeitorFalso:
    name = "Controle de teste"

    def __init__(self):
        self.buttons = set()
        self.axes = {}

    def button(self, name):
        return name in self.buttons

    def axis(self, name):
        return self.axes.get(name, 0.0)


def controles(n=1):
    pads = Gamepads(enabled=False)
    leitores = [LeitorFalso() for _ in range(n)]
    pads.pads = [Pad(r) for r in leitores]
    return pads, leitores


def tecla(key):
    return pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode="")


class Limpo(unittest.TestCase):
    def setUp(self):
        game()
        settings.path().unlink(missing_ok=True)
        settings.load()

    def tearDown(self):
        settings.path().unlink(missing_ok=True)
        settings.load()
        g = game()
        g.gamepads = Gamepads(enabled=False)
        for inp in g.inputs.values():
            inp.set_layout("battle")


class ControleTest(Limpo):
    def test_botoes_viram_acoes_do_p1(self):
        pads, (r,) = controles()
        r.buttons = {"a"}
        held, pressed, _ = pads.poll()
        self.assertIn("p1_attack", pressed)
        self.assertIn("p1_confirm", held)
        held, pressed, _ = pads.poll()                    # segurando: não é "apertado" de novo
        self.assertIn("p1_attack", held)
        self.assertNotIn("p1_attack", pressed)

    def test_segundo_controle_e_o_p2(self):
        pads, (r1, r2) = controles(2)
        r2.buttons = {"x"}
        held, _, _ = pads.poll()
        self.assertIn("p2_special", held)
        self.assertEqual(pads.slots(), {1, 2})

    def test_opcao_comecar_no_p2(self):
        settings.change("controle_comeca_no_p2", True)
        pads, (r,) = controles()
        r.buttons = {"b"}
        held, _, _ = pads.poll()
        self.assertIn("p2_dodge", held)
        self.assertEqual(pads.slots(), {2})

    def test_quinto_controle_fica_de_fora(self):
        settings.change("controle_comeca_no_p2", True)
        pads, leitores = controles(4)
        for r in leitores:
            r.buttons = {"a"}
        held, _, _ = pads.poll()
        self.assertEqual(pads.slots(), {2, 3, 4})
        self.assertFalse(any(h.startswith("p5_") for h in held))

    def test_analogico_com_zona_morta(self):
        pads, (r,) = controles()
        r.axes = {"lx": 0.1, "ly": -0.1}
        _, _, axes = pads.poll()
        self.assertNotIn(1, axes)                         # parado: não anda sozinho
        r.axes = {"lx": 0.9, "ly": 0.0}
        held, _, axes = pads.poll()
        self.assertAlmostEqual(axes[1][0], 0.9)
        self.assertIn("p1_right", held)                   # bem inclinado também conta como seta

    def test_direcional_anda_na_diagonal(self):
        pads, (r,) = controles()
        r.buttons = {"up", "left"}
        _, _, axes = pads.poll()
        x, y = axes[1]
        self.assertAlmostEqual(x, -0.7071, places=3)
        self.assertAlmostEqual(y, -0.7071, places=3)

    def test_gatilhos(self):
        pads, (r,) = controles()
        r.axes = {"rt": 0.9, "lt": 0.2}
        held, _, _ = pads.poll()
        self.assertIn("p1_sprint", held)
        self.assertNotIn("p1_dodge", held)

    def test_menu_vira_teclas(self):
        pads, (r,) = controles()
        r.buttons = {"down"}
        pads.poll()
        self.assertEqual([e.key for e in pads.menu_events()], [pygame.K_DOWN])

    def test_controle_move_o_lutador(self):
        g = game()
        pads, (r,) = controles()
        g.gamepads = pads
        from soulstrike.matches import BattleMatch
        from soulstrike.scenes.play import PlayScene
        from soulstrike.session import Session, SlotSetup
        g.session = Session("cpu", [SlotSetup(1, char=0), SlotSetup(2, char=1, cpu=True)])
        match = BattleMatch(g, g.session)
        g.change(PlayScene(g, match))
        r.axes = {"lx": 1.0}
        g.step([])
        self.assertEqual(g.inputs[1].axis(), (1.0, 0.0))
        r.axes = {}
        r.buttons = {"start"}
        g.step([])
        self.assertTrue(g.scene.paused)

    def test_controle_navega_no_menu_principal(self):
        g = game()
        pads, (r,) = controles()
        g.gamepads = pads
        g.change(TitleScene(g))
        r.buttons = {"a"}                                 # JOGAR
        g.step([])
        self.assertIsInstance(g.scene, ModeScene)

    def test_controle_aparece_conectado_no_lobby(self):
        g = game()
        pads, _ = controles(2)
        g.gamepads = pads
        self.assertEqual(g.connected_slots(), {1, 2})
        self.assertEqual(g.device_of(2), "CONTROLE")
        self.assertEqual(g.device_of(3), "TECLADO")

    def test_opcoes_tem_a_vaga_do_controle(self):
        self.assertIn("controle_comeca_no_p2", [k for k, _, _ in OptionsScene.ROWS])


class TeclasTest(Limpo):
    def test_padrao_igual_ao_de_antes(self):
        self.assertEqual(key_label(1, "attack"), "G")
        self.assertEqual(key_label(2, "attack"), ";")
        self.assertEqual(key_label(1, "sprint"), "SHIFT")
        self.assertEqual(key_label(2, "sprint"), "SHIFT DIR")
        self.assertEqual(key_label(1, "soccer_dodge"), "ESPAÇO")
        self.assertEqual(move_label(2), "SETAS")
        self.assertEqual(build_keymap(1, "battle")["attack"], (pygame.K_g,))

    def test_trocar_ataque_troca_tambem_o_confirmar(self):
        ok, _ = bind_key(1, "attack", pygame.K_h)
        self.assertTrue(ok)
        keys = build_keymap(1, "battle")
        self.assertEqual(keys["attack"], (pygame.K_h,))
        self.assertEqual(keys["confirm"], (pygame.K_h,))
        self.assertEqual(settings.load()["teclas"]["1"]["attack"], pygame.K_h)   # salvo no arquivo

    def test_tecla_ocupada_troca_de_lugar(self):
        bind_key(1, "attack", pygame.K_f)                 # F era a habilidade
        self.assertEqual(current_key(1, "attack"), pygame.K_f)
        self.assertEqual(current_key(1, "special"), pygame.K_g)

    def test_tecla_do_outro_jogador_e_recusada(self):
        ok, msg = bind_key(1, "attack", pygame.K_SEMICOLON)
        self.assertFalse(ok)
        self.assertIn("JOGADOR 2", msg)

    def test_teclas_do_jogo_sao_recusadas(self):
        for code in RESERVED_KEYS:
            ok, _ = bind_key(1, "attack", code)
            self.assertFalse(ok)

    def test_extra_de_fabrica_sai_quando_outro_escolhe(self):
        self.assertIn(pygame.K_m, build_keymap(2, "battle")["confirm"])    # M também confirma no P2
        ok, _ = bind_key(1, "attack", pygame.K_m)
        self.assertTrue(ok)
        self.assertNotIn(pygame.K_m, build_keymap(2, "battle")["confirm"])
        self.assertEqual(build_keymap(1, "battle")["attack"], (pygame.K_m,))

    def test_tecla_principal_do_outro_no_futebol_e_recusada(self):
        ok, _ = bind_key(2, "attack", pygame.K_SPACE)       # ESPAÇO é o corte do P1 no futebol
        self.assertFalse(ok)

    def test_tecla_do_futebol_so_vale_no_futebol(self):
        bind_key(1, "sprint", pygame.K_c)
        self.assertEqual(build_keymap(1, "soccer")["sprint"], (pygame.K_c,))
        self.assertNotIn("sprint", build_keymap(1, "battle"))
        self.assertIn(pygame.K_LSHIFT, build_keymap(1, "battle")["dodge"])  # SHIFT continua esquivando no duelo

    def test_esquiva_do_duelo_nao_mexe_no_corte_do_futebol(self):
        bind_key(1, "dodge", pygame.K_c)
        self.assertEqual(build_keymap(1, "soccer")["dodge"], (pygame.K_SPACE,))

    def test_restaurar(self):
        bind_key(1, "attack", pygame.K_h)
        reset_keys(1)
        for row_id, _, _, _ in REBINDABLE:
            self.assertEqual(current_key(1, row_id), default_key(1, row_id))

    def test_jogador_usa_a_tecla_nova(self):
        bind_key(1, "attack", pygame.K_h)
        inp = PlayerInput(1)

        class Keys:
            def __getitem__(self, code):
                return code == pygame.K_h
        inp.update(Keys(), {pygame.K_h}, set(), set(), 0)
        self.assertTrue(inp.pressed("attack"))

    def test_arquivo_com_tecla_invalida_e_ignorado(self):
        settings.change("teclas", {"1": {"attack": "G", "nao_existe": 5, "special": pygame.K_ESCAPE}})
        self.assertEqual(current_key(1, "attack"), pygame.K_g)
        self.assertEqual(current_key(1, "special"), pygame.K_f)


class TelaDeTeclasTest(Limpo):
    def _tela(self):
        g = game()
        scene = RebindScene(g)
        g.scene = scene
        return g, scene

    def test_troca_pela_tela(self):
        g, scene = self._tela()
        scene.row = [r[0] for r in REBINDABLE].index("attack")
        scene.handle(tecla(pygame.K_RETURN))
        self.assertTrue(scene.waiting)
        scene.handle(tecla(pygame.K_h))
        self.assertFalse(scene.waiting)
        self.assertEqual(current_key(1, "attack"), pygame.K_h)
        self.assertIn(pygame.K_h, g.inputs[1].keys["attack"])         # já vale no jogo

    def test_esc_cancela_a_espera(self):
        _, scene = self._tela()
        scene.handle(tecla(pygame.K_RETURN))
        scene.handle(tecla(pygame.K_ESCAPE))
        self.assertFalse(scene.waiting)
        self.assertEqual(current_key(1, "up"), pygame.K_w)

    def test_restaurar_pela_tela(self):
        _, scene = self._tela()
        bind_key(2, "attack", pygame.K_h)
        scene.col = 1
        scene.row = len(REBINDABLE)
        scene.handle(tecla(pygame.K_RETURN))
        self.assertEqual(current_key(2, "attack"), pygame.K_SEMICOLON)

    def test_controles_abre_a_tela_e_mostra_as_teclas(self):
        g = game()
        bind_key(1, "attack", pygame.K_h)
        self.assertIn(("ATACAR / CHUTAR", "H", ";"), ControlsScene.rows())
        scene = ControlsScene(g)
        g.scene = scene
        scene.handle(tecla(pygame.K_k))
        self.assertIsInstance(g.scene, RebindScene)

    def test_desenha(self):
        g, scene = self._tela()
        bind_key(1, "attack", pygame.K_h)
        scene.draw(g.screen)
        scene.waiting = True
        scene.message = "TESTE"
        scene.draw(g.screen)


if __name__ == "__main__":
    unittest.main()
