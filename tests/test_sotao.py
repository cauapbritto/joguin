"""Sótão da Casa: a porta abre ao zerar o capítulo 1, o álbum da turma e a caixa NÃO MEXER."""
import unittest

import pygame
from test_casa import casa_da_turma, passo, reset_progress

from soulstrike import album, segredos
from soulstrike.arena import MAPS_BY_KEY
from soulstrike.casa import SOTAO_DOOR, HubMatch, door_open
from soulstrike.sotao import HATCH, SECRET_BOX, SOTAO_MAP, TABLE, SotaoMatch


def _no_sotao(chars=("guerreiro", "atirador")):
    match, inputs = casa_da_turma(chars, walk=True)
    return SotaoMatch(match.game, match.run, walk=True), inputs


def _junto(p, x, y):
    p.x, p.y = x, y + 20


class SotaoTest(unittest.TestCase):
    def tearDown(self):
        reset_progress()

    def test_mapa_registrado_e_largada_livre(self):
        reset_progress(capitulo1_zerado=True)
        cfg = MAPS_BY_KEY[SOTAO_MAP]
        self.assertFalse(cfg.battle)
        sotao, _ = _no_sotao(("guerreiro", "atirador", "ninja", "tanque"))
        for f in sotao.players:
            self.assertTrue(sotao.arena.is_free(f.x, f.y, 12))

    def test_porta_trancada_nao_sobe(self):
        reset_progress()
        self.assertFalse(door_open("sotao"))
        match, _ = casa_da_turma(walk=True)
        p = match.players[0]
        p.x, p.y = SOTAO_DOOR
        self.assertIsNone(match.room_near(p))

    def test_atacar_na_porta_aberta_sobe_todo_mundo_e_volta(self):
        reset_progress(capitulo1_zerado=True)
        from soulstrike.scenes.escada import StairsTripScene
        match, _ = casa_da_turma(walk=True)
        p = match.players[0]
        p.x, p.y = SOTAO_DOOR
        self.assertEqual(match.room_near(p), "sotao")
        self.assertTrue(match.interact(p))
        self.assertEqual(match.going_to, "sotao")
        while not match.finished:
            match.update()
        trip = match.next_scene()
        self.assertIsInstance(trip, StairsTripScene)
        up = trip.then().match
        self.assertIsInstance(up, SotaoMatch)
        self.assertTrue(up.walk)
        # o alçapão volta para a Casa, na porta do sótão
        q = up.players[0]
        q.x, q.y = HATCH.center
        self.assertTrue(up.hatch_near(q))
        self.assertTrue(up.interact(q))
        while not up.finished:
            up.update()
        back = up.next_scene().then().match
        self.assertIsInstance(back, HubMatch)
        for f in back.players:
            self.assertLess(abs(f.x - SOTAO_DOOR[0]), 120)
            self.assertTrue(back.arena.is_free(f.x, f.y, 12))

    def test_mesinha_abre_o_album_com_as_4_fotos(self):
        reset_progress(capitulo1_zerado=True)
        sotao, inputs = _no_sotao()
        p = sotao.players[0]
        _junto(p, *TABLE)
        self.assertTrue(sotao.interact(p))
        menu = sotao.menus[p]
        self.assertIsInstance(menu, album.AlbumMenu)
        self.assertEqual([k for _, k in menu.pages], list(album.FIXED))
        screen = pygame.Surface((960, 540))
        sotao.draw(screen, sotao.game.ui)

    def test_caixa_nao_mexer_so_abre_com_todo_mundo(self):
        reset_progress(capitulo1_zerado=True)
        sotao, inputs = _no_sotao()
        a, b = sotao.players[:2]
        _junto(a, *SECRET_BOX)
        _junto(b, SECRET_BOX[0] - 30, SECRET_BOX[1])
        sotao.interact(a)
        self.assertFalse(sotao.box_open)
        self.assertGreater(sotao.box.wobble, 0)
        passo(sotao, inputs, 20)
        sotao.interact(b)
        self.assertTrue(sotao.box_open)
        self.assertTrue(segredos.is_found("nao_mexer"))
        self.assertIsInstance(sotao.menus[b], album.DrawingMenu)

    def test_caixa_apertada_separado_nao_abre(self):
        reset_progress(capitulo1_zerado=True)
        sotao, inputs = _no_sotao()
        a, b = sotao.players[:2]
        _junto(a, *SECRET_BOX)
        _junto(b, SECRET_BOX[0] - 30, SECRET_BOX[1])
        sotao.interact(a)
        passo(sotao, inputs, 200)
        sotao.interact(b)
        self.assertFalse(sotao.box_open)


class FotosTest(unittest.TestCase):
    def tearDown(self):
        reset_progress()

    def test_foto_da_campanha_vai_para_o_album_e_para_no_limite(self):
        reset_progress()
        screen = pygame.Surface((960, 540))
        screen.fill((200, 40, 40))

        class M:
            frame = 0
            photo_at = None

        m = M()
        album.request(m, 5)
        self.assertIsNone(album.maybe_snap(m, screen))
        m.frame = 5
        name = album.maybe_snap(m, screen)
        self.assertIsNotNone(name)
        self.assertEqual(album.shots(), [name])
        self.assertEqual(album.shot_image(name).get_size(), album.SHOT_SIZE)
        self.assertIn(("campanha", name), album.pages(None))
        for _ in range(album.MAX_SHOTS + 3):
            album.save_shot(screen)
        self.assertLessEqual(len(album.shots()), album.MAX_SHOTS)
        self.assertLessEqual(len(list(album.folder().glob("*.png"))), album.MAX_SHOTS)

    def test_as_4_fotos_da_turma_desenham(self):
        sotao, _ = _no_sotao()
        for key in album.FIXED:
            img = album.fixed_photo(key, sotao.assets, sotao.game.ui)
            self.assertEqual(img.get_size(), (album.IW, album.IH))
        self.assertEqual(album.kid_drawing().get_size(), (150, 100))


if __name__ == "__main__":
    unittest.main()
