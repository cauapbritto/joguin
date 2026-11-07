"""Hub da campanha: a Casa da turma (cantos da turma, vitrine que fala, livro, horta, portas
trancadas e a saída do quintal com a passagem coletiva)."""
import unittest

import pygame

from apoio import FakeInput, game

from soulstrike import casa, config, progress
from soulstrike.arena import MAPS_BY_KEY, Arena
from soulstrike.campaign import LEAVE_FRAMES, PASSAGE_FRAMES, CampaignRun
from soulstrike.casa import FALAS, HUB_MAP, VERSES, HubMatch
from soulstrike.data import CHARACTERS
from soulstrike.session import Session, SlotSetup

KEYS = [c.key for c in CHARACTERS]


class _Input(FakeInput):
    def set_layout(self, name):
        pass


def casa_da_turma(chars=("guerreiro", "atirador"), story=True, walk=False):
    g = game()
    g.session = Session("campaign", [SlotSetup(i + 1, char=KEYS.index(c)) for i, c in enumerate(chars)], walk=walk)
    run = CampaignRun(g.session)
    match = HubMatch(g, run, story, walk=walk)
    inputs = {}
    for f in match.players:
        inputs[f.slot] = match.controllers[f] = _Input()
    return match, inputs


def passo(match, inputs, frames=1):
    for _ in range(frames):
        match.update()
        for inp in inputs.values():
            inp.end_frame()


def reset_progress(**data):
    progress.save(data)


class MapaTest(unittest.TestCase):
    def test_mapa_da_casa_registrado_e_largada_livre(self):
        cfg = MAPS_BY_KEY[HUB_MAP]
        self.assertFalse(cfg.battle)
        self.assertEqual(len(cfg.markers["S"]), 4)
        arena = Arena(cfg, game().assets)
        for x, y in cfg.markers["S"]:
            self.assertTrue(arena.is_free(x, y, 12))

    def test_largada_livre_mesmo_com_os_moveis(self):
        reset_progress()
        match, _ = casa_da_turma(("guerreiro", "atirador", "ninja", "tanque"))
        for p in match.players:
            self.assertTrue(match.arena.is_free(p.x, p.y, 12), (p.x, p.y))

    def test_falas_curtas_e_cinco_por_personagem(self):
        for key, lines in FALAS.items():
            self.assertEqual(len(lines), 5, key)
            for line in lines:
                self.assertLessEqual(len(line), 40, line)
        for c in CHARACTERS:
            self.assertIn(c.key, FALAS)


class SaidaTest(unittest.TestCase):
    def test_todos_no_city_vao_de_carro_para_a_fase(self):
        reset_progress()
        from soulstrike.scenes.campaign import StoryScene
        from soulstrike.scenes.play import PlayScene
        from soulstrike.scenes.viagem import CarTripScene
        for story, kind in ((True, StoryScene), (False, PlayScene)):
            match, inputs = casa_da_turma(story=story)
            area = match.door_area
            for k, p in enumerate(match.players):
                p.x, p.y = area.x + 20 + 40 * k, area.bottom - 10
            passo(match, inputs, PASSAGE_FRAMES + LEAVE_FRAMES + 2)
            self.assertTrue(match.finished)
            self.assertEqual(match.run.frames, 0)              # o tempo na casa não conta
            scene = match.next_scene()
            self.assertIsInstance(scene, CarTripScene)
            self.assertEqual(scene.chapter, 1)
            self.assertIsInstance(scene.then(), kind)

    def test_a_saida_e_o_city(self):
        reset_progress()
        match, _ = casa_da_turma()
        r = match.exit_rect
        self.assertTrue(match.door_area.contains(r))
        self.assertFalse(match.arena.is_free(r.centerx, r.bottom - 6, 12))     # o carro é sólido
        self.assertNotIn("D", MAPS_BY_KEY[HUB_MAP].markers)                  # o buraco do quintal fechou

    def test_cena_do_carro_quebra_e_segue(self):
        reset_progress()
        from soulstrike.scenes import viagem
        match, _ = casa_da_turma()
        g = match.game
        went = []
        g.change = lambda s: went.append(s)          # o jogo é o mesmo dos outros testes: devolve no fim
        self.addCleanup(lambda: g.__dict__.pop("change", None))
        screen = pygame.Surface((config.SCREEN_W, config.SCREEN_H))
        for chapter in (1, 2, 3, 4):
            scene = viagem.CarTripScene(g, [p.sprites for p in match.players], chapter, lambda: "fase")
            speeds = []
            for _ in range(viagem.END + 2):
                scene.update()
                speeds.append(scene.speed)
                if scene.ticks % 40 == 0:
                    scene.draw(screen)
            self.assertTrue(scene.done)
            self.assertGreater(speeds[100], 0)
            self.assertEqual(speeds[viagem.PUFF + 5], 0)          # PUFF: parou
        self.assertEqual(went, ["fase"] * 4)


class CasaTest(unittest.TestCase):
    def test_vitrine_so_fala_no_botao(self):
        reset_progress()
        match, inputs = casa_da_turma()
        s = next(s for s in match.speakers if s.key == "cauanzera")
        p = match.players[0]
        p.x, p.y = s.x, s.y + 20
        passo(match, inputs, 30)
        self.assertIsNone(s.line)                 # chegou perto: só o "..."
        self.assertTrue(s.waiting)
        self.assertIs(match.speaker_near(p), s)
        self.assertTrue(match.interact(p))
        self.assertEqual(s.line, FALAS["cauanzera"][0])
        self.assertGreater(s.talk, 0)
        self.assertTrue(match.interact(p))        # apertou de novo: a próxima, na hora
        self.assertEqual(s.line, FALAS["cauanzera"][1])
        passo(match, inputs, casa.TALK_FRAMES + 2)
        self.assertEqual(s.talk, 0)
        self.assertEqual(s.line, FALAS["cauanzera"][1])   # não puxa outra sozinho

    def test_longe_nao_tem_conversa(self):
        reset_progress()
        match, inputs = casa_da_turma()
        p = match.players[0]
        p.x, p.y = match.exit_rect.centerx, match.exit_rect.y - 200
        passo(match, inputs, 3)
        self.assertIsNone(match.speaker_near(p))
        self.assertFalse(any(s.waiting for s in match.speakers))

    def test_moto_ganha_da_conversa(self):
        reset_progress()
        match, inputs = casa_da_turma()
        p = match.players[0]
        r = match.moto.rect
        p.x, p.y = r.centerx, r.bottom + 10
        self.assertIsNone(match.speaker_near(p))

    def test_corrompidos_so_depois_de_liberados(self):
        reset_progress()
        match, _ = casa_da_turma()
        keys = {s.key for s in match.speakers}
        self.assertNotIn("aryel_corrompido", keys)
        reset_progress(capitulo1_zerado=True)
        match, _ = casa_da_turma()
        keys = {s.key for s in match.speakers}
        self.assertIn("aryel_corrompido", keys)
        self.assertNotIn("borba_corrompido", keys)
        reset_progress()

    def test_livro_mostra_um_versiculo_por_vez(self):
        reset_progress()
        match, inputs = casa_da_turma()
        p = match.players[0]
        p.x, p.y = match.book.x, match.book.y + 40
        refs = []
        for _ in range(len(VERSES) + 1):
            self.assertTrue(match.interact(p))
            refs.append(match.menus[p].ref)
            del match.menus[p]
        self.assertEqual(refs[:5], [r for r, _ in VERSES])
        self.assertEqual(refs[5], VERSES[0][0])

    def test_regar_a_horta_e_a_flor_grande(self):
        reset_progress()
        match, inputs = casa_da_turma()
        p = match.players[0]
        for bed in match.beds:
            p.x, p.y = bed.rect.centerx, bed.rect.bottom + 20
            self.assertTrue(match.interact(p))
            self.assertGreater(bed.watered, 0)
        passo(match, inputs, 2)
        self.assertTrue(match.big_flower)

    def test_portas_abrem_com_o_progresso(self):
        reset_progress()
        self.assertFalse(any(casa.door_open(k) for k, _, _ in casa.DOORS if k != "garagem"))
        self.assertTrue(casa.door_open("garagem"))                   # a garagem fica sempre aberta
        reset_progress(capitulo1_zerado=True, capitulo2_zerado=True)
        self.assertTrue(casa.door_open("sotao"))
        self.assertTrue(casa.door_open("oficina"))
        self.assertFalse(casa.door_open("porao"))
        reset_progress(capitulo1_zerado=True, capitulo2_zerado=True, capitulo4_zerado=True, vezes_zerada=1)
        self.assertTrue(casa.door_open("porao"))
        match, _ = casa_da_turma()
        self.assertTrue(all(opened for _, opened, _, _ in match.doors))
        reset_progress()


class PasseioTest(unittest.TestCase):
    def test_passear_na_casa_pelo_menu(self):
        reset_progress()
        from soulstrike.scenes import menus
        from soulstrike.scenes.campaign import start_campaign
        g = game()
        went = []
        g.change = lambda s: went.append(s)
        self.addCleanup(lambda: g.__dict__.pop("change", None))
        self.assertIn("passeio", [m for _, modes in menus.MODE_GROUPS["campanha"] for m in modes])
        menus.start_mode(g, "passeio")
        self.assertTrue(g.session.walk)
        self.assertEqual(g.session.mode, "campaign")
        scene = start_campaign(g)
        self.assertIsInstance(scene.match, HubMatch)
        self.assertTrue(scene.match.walk)
        self.assertEqual(progress.saved_campaign(), None)          # o passeio não cria save

    def test_no_passeio_o_city_nao_sai(self):
        reset_progress()
        match, inputs = casa_da_turma(walk=True)
        area = match.door_area
        for k, p in enumerate(match.players):
            p.x, p.y = area.x + 20 + 40 * k, area.bottom - 10
        passo(match, inputs, PASSAGE_FRAMES + LEAVE_FRAMES + 2)
        self.assertFalse(match.finished)
        self.assertIsNone(match.objective())
        self.assertIn("PAUSE", match.objective_text)
        self.assertTrue(match.restart_scene().match.walk)

    def test_armadura_vale_no_passeio_em_qualquer_capitulo(self):
        reset_progress()
        match, _ = casa_da_turma(walk=True)
        match.run.phase_index = 6
        again = HubMatch(match.game, match.run, False, walk=True)
        self.assertTrue(again.armor_free)

    def test_minimapa_da_casa(self):
        reset_progress()
        match, _ = casa_da_turma(("guerreiro", "atirador", "ninja", "tanque"))
        rect = match.minimap_rect()
        self.assertLessEqual(rect.right, config.SCREEN_W)
        self.assertIn(rect.inflate(4, 4), match.hud_regions())
        screen = pygame.Surface((config.SCREEN_W, config.SCREEN_H))
        match.draw_hud(screen, match.game.ui)
        p = match.players[-1]                                 # o último desenhado fica por cima
        x = round(rect.x + 2 + p.x * (rect.w - 4) / match.arena.size[0])
        y = round(rect.y + 2 + (p.y - casa.OY) * (rect.w - 4) / match.arena.size[0])
        self.assertEqual(tuple(screen.get_at((x, y)))[:3], p.color[:3])   # o ponto do jogador na cor dele


if __name__ == "__main__":
    unittest.main()
