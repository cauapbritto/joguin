"""P1 controlador: só a coroa pausa e mexe nas regras; os outros têm o menu pessoal (pedir pausa,
sair vira CPU); um controle novo assume uma CPU; as regras na escolha de personagens."""
import unittest
from unittest import mock

from apoio import game

from soulstrike import host, settings
from soulstrike.ai import FighterAI
from soulstrike.matches import BattleMatch, create_match
from soulstrike.scenes.play import PlayScene
from soulstrike.scenes.select import CharSelectScene
from soulstrike.session import Session, SlotSetup


class Botoes:
    """Controle falso: aperta ações só no quadro seguinte."""

    double_tap = None
    analog = None

    def __init__(self, slot):
        self.slot = slot
        self.layout = "battle"
        self.now = set()

    def set_layout(self, layout):
        self.layout = layout

    def pressed(self, action):
        return action in self.now

    def held(self, action):
        return False

    def axis(self):
        return 0.0, 0.0


class _Base(unittest.TestCase):
    def setUp(self):
        self.g = game()
        self.old_inputs = self.g.inputs
        self.g.inputs = {s: Botoes(s) for s in (1, 2, 3, 4)}
        patch = mock.patch.object(type(self.g), "connected_slots", lambda _self: {1, 2})
        patch.start()
        self.addCleanup(patch.stop)

    def tearDown(self):
        self.g.inputs = self.old_inputs

    def aperta(self, scene, slot, action):
        self.g.inputs[slot].now = {action}
        scene.update()
        self.g.inputs[slot].now = set()

    def duelo(self, mode="duel", p2_cpu=False):
        self.g.session = Session(mode, [SlotSetup(1, char=0), SlotSetup(2, char=1, cpu=p2_cpu)])
        return PlayScene(self.g, BattleMatch(self.g, self.g.session))


class PausaTest(_Base):
    def test_so_o_p1_pausa(self):
        scene = self.duelo()
        self.aperta(scene, 2, "pause")
        self.assertFalse(scene.paused)
        self.assertIn(2, scene.personal)          # o P2 ganha o menu pessoal
        self.aperta(scene, 1, "pause")
        self.assertTrue(scene.paused)

    def test_quem_esta_no_menu_pessoal_fica_parado(self):
        scene = self.duelo()
        self.aperta(scene, 2, "pause")
        fighter = host.fighter_of(scene.match, 2)
        self.assertIsInstance(scene.match.controllers[fighter], host.IdleInput)
        self.aperta(scene, 2, "cancel")
        self.assertNotIn(2, scene.personal)
        self.assertIs(scene.match.controllers[fighter], self.g.inputs[2])

    def test_pedir_pausa_avisa_o_p1(self):
        scene = self.duelo()
        self.aperta(scene, 2, "pause")
        self.aperta(scene, 2, "confirm")          # PEDIR PAUSA
        self.assertEqual(scene.request[0], 2)
        self.assertFalse(scene.paused)

    def test_sair_vira_cpu(self):
        scene = self.duelo()
        self.aperta(scene, 2, "pause")
        self.aperta(scene, 2, "down")
        self.aperta(scene, 2, "confirm")          # SAIR (VIRA CPU)
        fighter = host.fighter_of(scene.match, 2)
        self.assertIsInstance(scene.match.controllers[fighter], FighterAI)
        self.assertTrue(fighter.is_cpu)
        self.assertTrue(host.setup_of(self.g.session, 2).cpu)

    def test_controle_novo_assume_a_cpu(self):
        scene = self.duelo(mode="cpu", p2_cpu=True)
        self.aperta(scene, 2, "pause")
        fighter = host.fighter_of(scene.match, 2)
        self.assertIs(scene.match.controllers[fighter], self.g.inputs[2])
        self.assertFalse(fighter.is_cpu)
        self.assertIn("ENTROU", scene.joined[0])

    def test_no_treino_qualquer_um_pausa(self):
        self.g.session = Session("treino", [SlotSetup(1, char=0), SlotSetup(2, char=1)])
        self.assertTrue(host.anyone_pauses(self.g.session))
        self.g.session = Session("duel", [SlotSetup(1, char=0), SlotSetup(2, char=1, cpu=True)])
        self.assertTrue(host.anyone_pauses(self.g.session))       # jogando sozinho
        self.g.session = Session("duel", [SlotSetup(1, char=0), SlotSetup(2, char=1)])
        self.assertFalse(host.anyone_pauses(self.g.session))

    def test_coroa_passa_adiante(self):
        session = Session("duel2", [SlotSetup(1, char=0, cpu=True), SlotSetup(2, char=1), SlotSetup(3, char=2)])
        self.assertEqual(host.host_slot(session), 2)


class RegrasAoVivoTest(_Base):
    def test_tamanho_da_partida_nao_da_vitoria_na_hora(self):
        self.g.session = Session("soccer1", [SlotSetup(1, char=0), SlotSetup(2, char=1, cpu=True)])
        match = create_match(self.g, self.g.session)
        match.score = [3, 1]
        host.set_length(match, "3")
        self.assertEqual(match.win_score, 4)
        host.set_length(match, "tempo")
        self.assertIsNone(match.win_score)
        self.assertTrue(match.clock)

    def test_regras_do_futebol(self):
        self.g.session = Session("soccer1", [SlotSetup(1, char=0), SlotSetup(2, char=1, cpu=True)])
        match = create_match(self.g, self.g.session)
        keys = [r[0] for r in host.rules(self.g, match)]
        self.assertEqual(keys, ["partida", "assist", "cpu"])
        host.change_rule(self.g, match, "cpu", "dificil")
        self.assertEqual(self.g.session.difficulty, "dificil")

    def test_campanha_nao_tem_regras(self):
        self.g.session = Session("campaign", [SlotSetup(1, char=0)])
        self.assertEqual(host.rules(self.g, None), [])


class RegrasNaEscolhaTest(_Base):
    def escolha(self):
        self.g.session = Session("duel", [SlotSetup(1, char=0), SlotSetup(2, char=1)])
        return CharSelectScene(self.g)

    def test_start_do_p1_abre_as_regras(self):
        scene = self.escolha()
        self.aperta(scene, 2, "pause")
        self.assertFalse(scene.rules_open)
        self.aperta(scene, 1, "pause")
        self.assertTrue(scene.rules_open)
        mapa = scene.map_index
        char = scene.cards[0].setup.char
        self.aperta(scene, 1, "char_right")
        self.assertNotEqual(scene.map_index, mapa)      # mexeu no mapa, não no personagem
        self.assertEqual(scene.cards[0].setup.char, char)
        self.aperta(scene, 1, "pause")
        self.assertFalse(scene.rules_open)

    def test_armas_por_round(self):
        scene = self.escolha()
        antes = settings.get("armas_por_round")
        self.aperta(scene, 1, "pause")
        labels = [r[0] for r in scene.rule_rows()]
        scene.rules_row = labels.index("ARMAS")
        self.aperta(scene, 1, "char_left")
        self.assertNotEqual(settings.get("armas_por_round"), antes)
        settings.change("armas_por_round", antes)

    def test_nao_comeca_com_as_regras_abertas(self):
        scene = self.escolha()
        for c in scene.cards:
            c.ready = True
        self.aperta(scene, 1, "pause")
        scene.rules_open = True
        for _ in range(3):
            scene.update()
        self.assertEqual(scene.countdown, 0)


class MenuSoDoP1Test(unittest.TestCase):
    def test_so_o_controle_do_p1_navega(self):
        g = game()
        pads = g.gamepads.pads

        class Pad:
            def __init__(self, pressed):
                self.pressed = pressed
        try:
            g.gamepads.pads = [Pad({"down"}), Pad({"up"})]
            with mock.patch.object(settings, "get", side_effect=lambda k, *a: False
                                   if k == "controle_comeca_no_p2" else settings.DEFAULTS.get(k)):
                keys = [e.key for e in g.gamepads.menu_events()]
                todos = [e.key for e in g.gamepads.menu_events(every_pad=True)]
        finally:
            g.gamepads.pads = pads
        import pygame
        self.assertEqual(keys, [pygame.K_DOWN])
        self.assertEqual(sorted(todos), sorted([pygame.K_DOWN, pygame.K_UP]))
