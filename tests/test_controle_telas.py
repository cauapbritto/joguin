"""Controle USB passando pelas telas: o aperto que troca de tela não vale na tela nova, o B volta,
o resultado não some sozinho e a Casa não lê o progresso do disco a cada quadro (v1.56.2)."""
import json
import pathlib
import unittest

import pygame
from apoio import game

from soulstrike import progress, settings
from soulstrike.gamepads import Gamepads, Pad
from soulstrike.matches import Result
from soulstrike.scenes.menus import ModeScene, category_of
from soulstrike.scenes.play import ResultsScene
from soulstrike.scenes.select import CharSelectScene, LobbyScene
from soulstrike.session import Session, SlotSetup

# modos que passam pela tela do QR Code (a de conectar o celular)
COM_QR = ("campaign", "passeio", "duel", "duel2", "soccer1", "soccer2", "basket1", "basket2", "penaltis1",
          "penaltis")
DIRETO_NA_ESCOLHA = ("cpu", "treino", "treino_futebol", "treino_basquete", "treino_penaltis", "desafio_goleiro")


class _Leitor:
    """Controle de mentira: os botões em ``down`` estão apertados."""
    name = "Xbox Controller"

    def __init__(self):
        self.down = set()

    def button(self, b):
        return b in self.down

    def axis(self, a):
        return 0.0


class ControleNasTelasTest(unittest.TestCase):
    def setUp(self):
        self.g = game()
        settings.path().unlink(missing_ok=True)
        settings.load()
        self.antigos = self.g.gamepads
        self.leitor = _Leitor()
        pads = Gamepads(enabled=False)
        pads.pads = [Pad(self.leitor)]
        self.g.gamepads = pads
        self.g.session = None

    def tearDown(self):
        self.g.gamepads = self.antigos
        self.g.session = None
        settings.path().unlink(missing_ok=True)
        settings.load()

    def apertar(self, botao, quadros=3):
        self.leitor.down = {botao}
        self.g.update([])
        self.leitor.down = set()
        for _ in range(quadros):
            self.g.update([])

    def escolher_modo(self, modo):
        cena = ModeScene(self.g, category_of(modo))
        self.g.change(cena)
        self.g.update([])
        cena.menu.index = [v for _, v in cena.menu.options].index(modo)
        self.apertar("a")

    def test_a_do_controle_nao_pula_a_tela_do_qr(self):
        for modo in COM_QR:
            with self.subTest(modo=modo):
                self.escolher_modo(modo)
                self.assertIsInstance(self.g.scene, LobbyScene)

    def test_cpu_e_treino_nao_comecam_com_o_p1_pronto(self):
        for modo in DIRETO_NA_ESCOLHA:
            with self.subTest(modo=modo):
                self.escolher_modo(modo)
                cena = self.g.scene
                self.assertIsInstance(cena, CharSelectScene)
                p1 = next(c for c in cena.cards if c.slot == 1)
                self.assertFalse(p1.ready)

    def test_b_do_controle_volta_da_escolha_e_do_qr(self):
        self.escolher_modo("campaign")
        self.apertar("a")                       # tela do QR -> escolha de personagem
        self.assertIsInstance(self.g.scene, CharSelectScene)
        self.apertar("b")
        self.assertIsInstance(self.g.scene, LobbyScene)
        self.apertar("b")
        self.assertIsInstance(self.g.scene, ModeScene)

    def test_b_com_personagem_pronto_so_desmarca(self):
        self.escolher_modo("cpu")
        cena = self.g.scene
        p1 = next(c for c in cena.cards if c.slot == 1)
        p1.ready = True
        cena.countdown = 0
        self.leitor.down = {"b"}
        self.g.update([])
        self.leitor.down = set()
        self.assertIs(self.g.scene, cena)
        self.assertFalse(p1.ready)

    def test_cpu_e_treino_voltam_para_os_modos(self):
        self.escolher_modo("desafio_goleiro")
        self.apertar("b")
        self.assertIsInstance(self.g.scene, ModeScene)


class ResultadoTest(unittest.TestCase):
    def test_atacar_no_fim_da_partida_nao_pula_o_resultado(self):
        g = game()
        g.session = Session("duel", [SlotSetup(1), SlotSetup(2)])
        cena = ResultsScene(g, Result("P1 VENCEU", (255, 255, 255), []))
        g.change(cena)
        tecla_atacar = pygame.K_g                  # confirmar do P1 no teclado
        for _ in range(ResultsScene.GRACE - 1):
            g.update([pygame.event.Event(pygame.KEYDOWN, key=tecla_atacar, mod=0, unicode="")])
        self.assertIs(g.scene, cena)
        for _ in range(3):
            g.update([])
        g.update([pygame.event.Event(pygame.KEYDOWN, key=tecla_atacar, mod=0, unicode="")])
        self.assertIsNot(g.scene, cena)
        g.session = None


class ProgressoEmMemoriaTest(unittest.TestCase):
    def setUp(self):
        game()
        self.leituras = 0
        original = pathlib.Path.read_text

        def contar(caminho, *a, **k):
            if caminho == progress.path():
                self.leituras += 1
            return original(caminho, *a, **k)
        self.original = original
        pathlib.Path.read_text = contar

    def tearDown(self):
        pathlib.Path.read_text = self.original

    def test_le_o_disco_uma_vez_so(self):
        progress.save({"teste": 1})
        for _ in range(50):
            self.assertEqual(progress.load().get("teste"), 1)
        self.assertEqual(self.leituras, 1)

    def test_quem_mexe_na_copia_nao_estraga_a_guardada(self):
        progress.save({"lista": [1]})
        progress.load()["lista"].append(2)
        self.assertEqual(progress.load()["lista"], [1])

    def test_arquivo_mudado_por_fora_e_relido(self):
        progress.save({"teste": 1})
        progress.load()
        progress.path().write_text(json.dumps({"teste": 22, "mais": True}), encoding="utf-8")
        self.assertEqual(progress.load().get("teste"), 22)

    def test_save_atualiza_na_hora(self):
        progress.save({"teste": 1})
        progress.load()
        progress.save({"teste": 2})
        self.assertEqual(progress.load().get("teste"), 2)

    def test_casa_nao_le_o_disco_todo_quadro(self):
        from soulstrike.campaign import CampaignRun
        from soulstrike.scenes.campaign import hub_scene
        from soulstrike.scenes.menus import start_mode
        g = game()
        start_mode(g, "campaign")
        g.change(hub_scene(g, CampaignRun(g.session), story=False))
        for _ in range(10):
            g.update([])
            g.draw()
        self.leituras = 0
        for _ in range(60):
            g.update([])
            g.draw()
        self.assertLessEqual(self.leituras, 2)
        g.session = None


if __name__ == "__main__":
    unittest.main()
