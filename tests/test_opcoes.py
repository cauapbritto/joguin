"""Tela de opções: valores salvos, volumes aplicados, tremor desligável e opções da linha de comando."""
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

import pygame
from apoio import game

from soulstrike import settings
from soulstrike.camera import Camera
from soulstrike.controls import PlayerInput
from soulstrike.scenes.menus import OptionsScene, TitleScene

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import main  # noqa: E402


def tecla(key):
    return pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode="")


class OpcoesBase(unittest.TestCase):
    def setUp(self):
        game()
        settings.path().unlink(missing_ok=True)
        settings.load()
        PlayerInput.double_tap_enabled = True

    def tearDown(self):
        settings.path().unlink(missing_ok=True)
        settings.load()
        PlayerInput.double_tap_enabled = True


class ArquivoTest(OpcoesBase):
    def test_padrao_sem_arquivo(self):
        self.assertEqual(settings.load(), settings.DEFAULTS)

    def test_salva_e_carrega(self):
        settings.change("volume_musica", 0.4)
        settings.change("tremor", False)
        self.assertEqual(settings.load()["volume_musica"], 0.4)
        self.assertFalse(settings.get("tremor"))

    def test_arquivo_estragado_volta_ao_padrao(self):
        settings.path().parent.mkdir(parents=True, exist_ok=True)
        settings.path().write_text("{nada disso é json", encoding="utf-8")
        self.assertEqual(settings.load(), settings.DEFAULTS)

    def test_valores_estranhos_sao_corrigidos(self):
        settings.path().write_text(json.dumps({"volume_geral": 7, "volume_efeitos": -1, "tremor": "sim",
                                               "vsync": 0, "chave_velha": 1}), encoding="utf-8")
        values = settings.load()
        self.assertEqual(values["volume_geral"], 1.0)
        self.assertEqual(values["volume_efeitos"], 0.0)
        self.assertTrue(values["tremor"])                   # texto não vira booleano
        self.assertTrue(values["vsync"])
        self.assertNotIn("chave_velha", values)

    def test_volume_fica_entre_0_e_1(self):
        self.assertEqual(settings.change("volume_geral", 1.3), 1.0)
        self.assertEqual(settings.change("volume_geral", -0.2), 0.0)


class VolumeTest(OpcoesBase):
    def test_efeito_usa_o_volume_das_opcoes(self):
        assets = game().assets
        sound = mock.Mock()
        sound.get_num_channels.return_value = 0
        with mock.patch.dict(assets.sounds, {"teste": sound}):
            settings.change("volume_geral", 0.5)
            settings.change("volume_efeitos", 0.5)
            assets.play("teste", 0.8)
        sound.set_volume.assert_called_once_with(0.8 * 0.25)
        sound.play.assert_called_once()

    def test_efeitos_mudos(self):
        assets = game().assets
        sound = mock.Mock()
        sound.get_num_channels.return_value = 0
        with mock.patch.dict(assets.sounds, {"teste": sound}):
            settings.change("volume_efeitos", 0.0)
            assets.play("teste", 0.8)
        sound.set_volume.assert_called_once_with(0.0)

    def test_musica_muda_na_hora(self):
        assets = game().assets
        settings.change("volume_musica", 0.5)
        with mock.patch.object(pygame.mixer, "get_init", return_value=True), \
                mock.patch.object(pygame.mixer.music, "set_volume") as set_volume:
            assets.apply_music_volume()
        set_volume.assert_called_once()
        self.assertAlmostEqual(set_volume.call_args[0][0], 0.3 * 0.5)


class TremorTest(OpcoesBase):
    def test_tremor_desligado(self):
        cam = Camera((2000, 2000), 0.6)
        settings.change("tremor", False)
        cam.shake(8)
        self.assertEqual(cam._shake, 0)
        settings.change("tremor", True)
        cam.shake(8)
        self.assertEqual(cam._shake, 8)


class TelaDeOpcoesTest(OpcoesBase):
    def _tela(self):
        g = game()
        scene = OptionsScene(g)
        g.scene = scene
        return g, scene

    def test_setas_mudam_o_volume(self):
        _, scene = self._tela()
        scene.handle(tecla(pygame.K_LEFT))
        scene.handle(tecla(pygame.K_LEFT))
        self.assertEqual(settings.get("volume_geral"), 0.8)
        scene.handle(tecla(pygame.K_RIGHT))
        self.assertEqual(settings.get("volume_geral"), 0.9)
        self.assertEqual(settings.load()["volume_geral"], 0.9)        # ficou salvo

    def test_desce_e_alterna(self):
        _, scene = self._tela()
        for _ in range(5):
            scene.handle(tecla(pygame.K_DOWN))
        self.assertEqual(scene.key, "tremor")
        scene.handle(tecla(pygame.K_RETURN))
        self.assertFalse(settings.get("tremor"))
        scene.handle(tecla(pygame.K_DOWN))
        scene.handle(tecla(pygame.K_RETURN))
        self.assertFalse(settings.get("duplo_toque"))
        self.assertFalse(PlayerInput.double_tap_enabled)

    def test_tela_cheia_alterna_e_salva(self):
        g, scene = self._tela()
        scene.index = [k for k, _, _ in OptionsScene.ROWS].index("tela_cheia")
        before = g.fullscreen
        scene.handle(tecla(pygame.K_RETURN))
        self.assertEqual(g.fullscreen, not before)
        self.assertEqual(settings.get("tela_cheia"), g.fullscreen)
        scene.handle(tecla(pygame.K_RETURN))
        self.assertEqual(g.fullscreen, before)

    def test_clique_no_lado_esquerdo_abaixa(self):
        g, scene = self._tela()
        scene.draw(g.screen)
        row = scene.rects[1]                         # música
        scene.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(row.x + 5, row.centery)))
        self.assertEqual(settings.get("volume_musica"), 0.9)
        scene.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(row.right - 5, row.centery)))
        self.assertEqual(settings.get("volume_musica"), 1.0)

    def test_esc_volta_ao_titulo(self):
        g, scene = self._tela()
        scene.handle(tecla(pygame.K_ESCAPE))
        self.assertIsInstance(g.scene, TitleScene)

    def test_titulo_abre_opcoes(self):
        g = game()
        title = TitleScene(g)
        g.scene = title
        title.menu.index = [v for _, v in title.menu.options].index("options")
        title.handle(tecla(pygame.K_RETURN))
        self.assertIsInstance(g.scene, OptionsScene)

    def test_desenha(self):
        g, scene = self._tela()
        for i in range(len(OptionsScene.ROWS)):
            scene.index = i
            scene.draw(g.screen)


class LinhaDeComandoTest(OpcoesBase):
    def test_padrao(self):
        self.assertEqual(main.display_options([]), (True, True))

    def test_opcoes_salvas(self):
        settings.change("tela_cheia", False)
        settings.change("vsync", False)
        self.assertEqual(main.display_options([]), (False, False))

    def test_linha_de_comando_manda(self):
        self.assertEqual(main.display_options(["--janela", "--sem-vsync"]), (False, False))


if __name__ == "__main__":
    unittest.main()
