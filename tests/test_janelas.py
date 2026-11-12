"""As janelas pequenas da Casa: tamanho, lugar na tela, corda solta de quem está numa janela e os
avisos com contagem (a turma saindo, o LIBERAR TUDO)."""
import math
import unittest

import pygame

from test_casa import casa_da_turma, passo, reset_progress
from test_computador import perto

from soulstrike import computador, janelas
from soulstrike.campaign import LEASH_Y
from soulstrike.casa import BookMenu, GarageMenu, next_verse
from soulstrike.guarda_roupa import WardrobeMenu
from soulstrike.loja import ShopMenu
from soulstrike.para_onde import ChapterPickMenu


def no_livro(match, f):
    f.x, f.y = match.book.x + 10, match.book.y + 50
    match.menus[f] = BookMenu(match, f, next_verse())
    return match.menus[f]


class TamanhoTest(unittest.TestCase):
    def setUp(self):
        reset_progress()

    def test_tudo_abre_com_no_maximo_metade_do_tamanho_antigo(self):
        match, _ = casa_da_turma()
        f = match.players[0]
        ui = match.game.ui
        book = BookMenu(match, f, next_verse())
        antes = {ShopMenu: (640, 384), WardrobeMenu: (640, 380),
                 BookMenu: (340, 66 + len(ui.wrap(book.text, 8, 300)) * 14 + 26),
                 ChapterPickMenu: (380, 240), GarageMenu: (360, 236)}
        menus = {ShopMenu: ShopMenu(match, f), WardrobeMenu: WardrobeMenu(match, f),
                 BookMenu: book,
                 ChapterPickMenu: ChapterPickMenu(match, f, lambda c: None), GarageMenu: GarageMenu(match, f)}
        for cls, menu in menus.items():
            w, h = menu.size(ui)
            ow, oh = antes[cls]
            if cls is not BookMenu:                     # o livro só fica mais estreito (o texto é o mesmo)
                self.assertLessEqual(w * h, ow * oh * 0.62, cls.__name__)
            self.assertLessEqual(w, 340, cls.__name__)
            menu.draw(match.game.screen, ui, match.camera, rect=pygame.Rect((10, 60), (w, h)))

    def test_janelas_juntas_nao_se_cobrem(self):
        match, inputs = casa_da_turma(("guerreiro", "atirador", "tanque"))
        p1, p2, p3 = match.players
        perto(match, "pc")
        self.assertTrue(match.interact(p1))
        no_livro(match, p2)
        p3.x, p3.y = p2.x + 20, p2.y
        match.menus[p3] = ShopMenu(match, p3)
        passo(match, inputs, 30)
        rects = [r for _, _, r, _ in janelas.layout(match, match.game.ui)]
        self.assertEqual(len(rects), 3)
        for i, a in enumerate(rects):
            self.assertTrue(match.game.screen.get_rect().contains(a))
            for b in rects[i + 1:]:
                self.assertFalse(a.colliderect(b), (a, b))
        match.draw(match.game.screen, match.game.ui)


class CordaTest(unittest.TestCase):
    def setUp(self):
        reset_progress()

    def test_quem_esta_no_pc_nao_segura_a_turma(self):
        match, inputs = casa_da_turma()
        p1, p2 = match.players
        perto(match, "pc")
        self.assertTrue(match.interact(p1))
        self.assertTrue(match.leash_free(p1))
        cx, cy = match.exit_rect.center                     # o P2 vai até o City, lá no quintal
        p2.x, p2.y = cx, cy + 110
        self.assertGreater(abs(p2.y - p1.y), LEASH_Y)
        passo(match, inputs, 90)
        self.assertLess(math.hypot(p2.x - cx, p2.y - (cy + 110)), 30)    # a corda não puxou ninguém
        self.assertIn(p1, match.menus)
        self.assertNotIn((p1.x, p1.y - 20), match.focus_points())       # a câmera vai com o P2
        # longe da turma, a janela do P1 gruda em cima do quadro dele
        match.draw(match.game.screen, match.game.ui)
        (_, _, rect, docked), = janelas.layout(match, match.game.ui)
        self.assertTrue(docked)
        # fechou: aparece do lado do grupo
        match.menus[p1].done = True
        passo(match, inputs, 2)
        self.assertNotIn(p1, match.menus)
        self.assertLess(math.hypot(p1.x - p2.x, p1.y - p2.y), 120)

    def test_fechar_perto_fica_onde_esta(self):
        match, inputs = casa_da_turma()
        p1, p2 = match.players
        perto(match, "pc")
        self.assertTrue(match.interact(p1))
        p2.x, p2.y = p1.x + 80, p1.y + 20
        where = (p1.x, p1.y)
        match.menus[p1].done = True
        passo(match, inputs, 2)
        self.assertLess(math.hypot(p1.x - where[0], p1.y - where[1]), 4)


class AvisosTest(unittest.TestCase):
    def setUp(self):
        reset_progress()

    def test_turma_no_city_fecha_a_janela_em_3_segundos(self):
        match, inputs = casa_da_turma()
        p1, p2 = match.players
        no_livro(match, p1)
        p2.x, p2.y = match.door_area.center
        passo(match, inputs, 5)
        self.assertTrue(match.leaving_in)
        self.assertIn("SAINDO", match.window_warning(p1))
        match.draw(match.game.screen, match.game.ui)
        passo(match, inputs, janelas.LEAVE_WARN)
        self.assertNotIn(p1, match.menus)
        self.assertTrue(match.passage.contains(p1))           # foi parar do lado do City
        p2.x, p2.y = match.door_area.center
        passo(match, inputs, 200)
        self.assertTrue(match.leaving or match.finished)

    def test_sair_do_carro_cancela_o_aviso(self):
        match, inputs = casa_da_turma()
        p1, p2 = match.players
        no_livro(match, p1)
        p2.x, p2.y = match.door_area.center
        passo(match, inputs, 5)
        self.assertTrue(match.leaving_in)
        p2.x, p2.y = match.book.x + 200, match.book.y + 80
        passo(match, inputs, 2)
        self.assertFalse(match.leaving_in)
        self.assertIn(p1, match.menus)

    def test_descer_para_a_garagem_espera_a_janela(self):
        match, inputs = casa_da_turma()
        p1, p2 = match.players
        no_livro(match, p2)
        _, _, (gx, gy), _ = next(d for d in match.doors if d[0] == "garagem")
        p1.x, p1.y = gx, gy + 30
        self.assertTrue(match.garage_near(p1))
        self.assertTrue(match.interact(p1))
        self.assertFalse(match.finished)
        self.assertIn("SAINDO", match.window_warning(p2))
        passo(match, inputs, janelas.LEAVE_WARN + 1)
        self.assertTrue(match.finished)
        self.assertTrue(match.going_down)

    def test_liberar_tudo_avisa_quem_esta_em_outra_janela(self):
        match, inputs = casa_da_turma()
        p1, p2 = match.players
        perto(match, "pc")
        self.assertTrue(match.interact(p1))
        no_livro(match, p2)
        match.menus[p1].unlock()
        self.assertFalse(match.freeing)
        self.assertIn(p2, match.menus)
        self.assertIn("LIBERANDO", match.window_warning(p2))
        self.assertIsNone(match.window_warning(p1))
        passo(match, inputs, janelas.FREE_WARN + 1)
        self.assertTrue(match.freeing)
        self.assertNotIn(p2, match.menus)
        self.assertTrue(computador.freed())


if __name__ == "__main__":
    unittest.main()
