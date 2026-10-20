"""Polimento: confirmação ao sair da campanha, barra do chefão, IP do celular sem internet e música do menu."""
import socket
import unittest
from unittest import mock

import pygame
from apoio import game
from test_campanha import ChefaoTest, campanha, pular_intro

from soulstrike import config, hud
from soulstrike.matches import BattleMatch
from soulstrike.net import server
from soulstrike.scenes.menus import TitleScene
from soulstrike.scenes.play import PlayScene
from soulstrike.session import Session, SlotSetup


def tecla(key):
    return pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode="")


def duelo():
    g = game()
    g.session = Session("cpu", [SlotSetup(1, char=0), SlotSetup(2, char=1, cpu=True)])
    return PlayScene(g, BattleMatch(g, g.session))


class SairDaCampanhaTest(unittest.TestCase):
    def _pausada(self):
        match, _ = campanha()
        pular_intro(match)
        scene = PlayScene(match.game, match)
        match.game.scene = scene
        scene._set_paused(True)
        return scene

    def test_sair_pede_confirmacao(self):
        scene = self._pausada()
        scene._choose("quit")
        self.assertTrue(scene.confirming)
        self.assertIs(scene.game.scene, scene)              # continua na partida
        self.assertEqual(scene.pause_menu.value, "back")    # o padrão é NÃO sair

    def test_desistir_volta_para_a_pausa(self):
        scene = self._pausada()
        scene._choose("quit")
        scene._choose("back")
        self.assertFalse(scene.confirming)
        self.assertTrue(scene.paused)
        self.assertIs(scene.game.scene, scene)

    def test_confirmar_sai_para_o_menu(self):
        scene = self._pausada()
        scene._choose("quit")
        scene._choose("quit_now")
        self.assertIsInstance(scene.game.scene, TitleScene)

    def test_despausar_esquece_a_confirmacao(self):
        scene = self._pausada()
        scene._choose("quit")
        scene.handle(tecla(pygame.K_ESCAPE))
        scene.handle(tecla(pygame.K_ESCAPE))
        self.assertTrue(scene.paused)
        self.assertFalse(scene.confirming)

    def test_tela_de_confirmacao_desenha(self):
        scene = self._pausada()
        scene._choose("quit")
        scene.draw(scene.game.screen)

    def test_duelo_sai_direto(self):
        scene = duelo()
        scene.game.scene = scene
        scene._set_paused(True)
        scene._choose("quit")
        self.assertIsInstance(scene.game.scene, TitleScene)


class BarraDoChefaoTest(unittest.TestCase):
    def _desenha(self, match):
        screen = pygame.Surface((config.SCREEN_W, config.SCREEN_H))
        hud.draw_campaign(screen, match.game.ui, match)
        return screen

    def test_desenha_normal_e_cansado(self):
        match, boss, ai = ChefaoTest._chefe(None)
        self._desenha(match)
        ai._set(boss, "tired", 50)
        ai.update(boss, match)
        self.assertGreater(boss.vulnerability, 1.0)
        for frame in range(12):                     # pisca: desenha nas duas cores
            match.frame = frame
            self._desenha(match)

    def test_risco_some_quando_a_vida_passa_dele(self):
        match, boss, _ = ChefaoTest._chefe(None)
        bar = pygame.Rect(0, 0, 440, 16)
        bar.midtop = (config.SCREEN_W // 2, 30)
        frame = bar.inflate(4, 4)
        mx = frame.x + 1 + round((frame.w - 2) * 0.5)

        boss.hp = boss.max_hp
        cheia = self._desenha(match).get_at((mx, frame.y - 2))
        boss.hp = boss.max_hp * 0.3
        passou = self._desenha(match).get_at((mx, frame.y - 2))
        self.assertNotEqual(cheia, passou)


class IpDoCelularTest(unittest.TestCase):
    def test_ip_com_rede(self):
        ip = server.local_ip()
        socket.inet_aton(ip)                         # é um IPv4 válido

    def test_sem_rota_para_a_internet_usa_a_rede_local(self):
        real = socket.socket

        class Falso:
            def __init__(self, *a):
                self.ip = None

            def connect(self, addr):
                if addr[0] == "8.8.8.8":
                    raise OSError("Network is unreachable")
                self.ip = "192.168.1.23"

            def getsockname(self):
                return (self.ip, 5555)

            def close(self):
                pass

        with mock.patch.object(server.socket, "socket", Falso):
            self.assertEqual(server.local_ip(), "192.168.1.23")
        self.assertIs(socket.socket, real)

    def test_sem_rota_nenhuma_usa_o_nome_do_computador(self):
        class SemRede:
            def __init__(self, *a):
                pass

            def connect(self, addr):
                raise OSError("Network is unreachable")

            def close(self):
                pass

        with mock.patch.object(server.socket, "socket", SemRede), \
                mock.patch.object(server.socket, "gethostbyname_ex",
                                  return_value=("pc", [], ["127.0.1.1", "10.0.0.7"])):
            self.assertEqual(server.local_ip(), "10.0.0.7")
        with mock.patch.object(server.socket, "socket", SemRede), \
                mock.patch.object(server.socket, "gethostbyname_ex", side_effect=OSError):
            self.assertEqual(server.local_ip(), "127.0.0.1")


class MusicaTest(unittest.TestCase):
    def test_musicas_existem(self):
        self.assertTrue((config.SOUNDS_DIR / "bgm.ogg").is_file())
        self.assertTrue((config.SOUNDS_DIR / "battle_bgm.mp3").is_file())

    def test_menu_toca_sem_erro(self):
        assets = game().assets
        assets._music = None
        assets.music("menu")
        self.assertEqual(assets._music, "menu")


if __name__ == "__main__":
    unittest.main()
