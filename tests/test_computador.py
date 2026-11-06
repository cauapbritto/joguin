"""Etapa 3b da Casa da turma: o PC do Cauanzera, o notebook do Albeguinio (com o LIBERAR TUDO), a
moto, a roleta e a padaria."""
import unittest

from test_casa import casa_da_turma, passo, reset_progress

from soulstrike import casa, computador, progress
from soulstrike.casa import HubMatch
from soulstrike.computador import HACK, Computer, HackerNotebook


def perto(match, kind):
    """Põe o P1 em frente à mesa do computador ``kind``."""
    _, rect, _ = next(c for c in match.computers if c[0] == kind)
    p = match.players[0]
    p.x, p.y = rect.centerx - 40, rect.bottom + 14
    return p


def ate(match, inputs, cond, limit=1500):
    for _ in range(limit):
        if cond():
            return True
        passo(match, inputs)
    return cond()


class ComputadorTest(unittest.TestCase):
    def setUp(self):
        reset_progress()

    def tearDown(self):
        reset_progress()

    def test_pc_abre_e_mostra_no_celular(self):
        match, inputs = casa_da_turma()
        p = perto(match, "pc")
        self.assertTrue(match.arena.is_free(p.x, p.y, 12))
        self.assertTrue(match.interact(p))
        menu = match.menus[p]
        self.assertIsInstance(menu, Computer)
        snap = menu.snapshot()
        self.assertEqual(snap["kind"], "pc")
        self.assertEqual(snap["action"], "ABRIR")
        self.assertEqual([i["id"] for i in snap["items"]], ["arquivos", "terminal", "navegador", "desligar"])
        self.assertEqual(snap["items"][0]["info"]["type"], "tela")
        # o celular escolhe e abre; VOLTAR volta para a área de trabalho
        self.assertTrue(menu.pick("navegador"))
        menu.buy()
        self.assertEqual(menu.screen, "navegador")
        self.assertTrue(menu.pick("pag:3"))
        self.assertIn("PADARIA DO JOÃO", " ".join(menu.screen_lines()))
        self.assertIn("voltar", [i["id"] for i in menu.snapshot()["items"]])
        self.assertFalse(menu.pick("voltar"))
        self.assertEqual(menu.screen, "desktop")
        # o outro jogador não abre o mesmo computador ao mesmo tempo
        q = match.players[1]
        q.x, q.y = p.x + 30, p.y
        self.assertIsNone(match.computer_near(q))

    def test_desligar_fecha_pelo_controle(self):
        match, inputs = casa_da_turma()
        p = perto(match, "pc")
        match.interact(p)
        menu = match.menus[p]
        menu.pick("desligar")
        passo(match, inputs, 2)
        inputs[p.slot].tap("attack")
        passo(match, inputs, 2)
        self.assertNotIn(p, match.menus)

    def test_terminal_do_pc_libera_tudo(self):
        match, inputs = casa_da_turma()
        p = perto(match, "pc")
        match.interact(p)
        menu = match.menus[p]
        menu.pick("terminal")
        menu.buy()
        self.assertTrue(ate(match, inputs, lambda: not menu.busy))
        menu.pick("cmd:liberar --tudo")
        menu.buy()
        self.assertTrue(ate(match, inputs, lambda: menu.asking))
        self.assertFalse(computador.freed())
        menu.pick("sim")
        menu.buy()
        self.assertTrue(ate(match, inputs, lambda: match.freeing > 0))
        self.assertTrue(computador.freed())
        for k in range(1, progress.LAST_CHAPTER + 1):
            self.assertTrue(progress.chapter_cleared(k))
        self.assertFalse(progress.load().get("vezes_zerada"))      # não conta como campanha zerada
        self.assertTrue(all(casa.door_open(k) for k, _, _ in casa.DOORS))
        self.assertTrue(ate(match, inputs, lambda: match.finished))
        self.assertTrue(match.reload)
        scene = match.next_scene()
        self.assertIsInstance(scene.match, HubMatch)              # a casa volta, com tudo aberto
        self.assertTrue(all(opened for _, opened, _, _ in scene.match.doors))
        self.assertIn("cauanzera_corrompido", {s.key for s in scene.match.speakers})

    def test_responder_nao_deixa_tudo_como_estava(self):
        match, inputs = casa_da_turma()
        p = perto(match, "pc")
        match.interact(p)
        menu = match.menus[p]
        menu.pick("terminal")
        menu.buy()
        self.assertTrue(ate(match, inputs, lambda: not menu.busy))
        menu.pick("cmd:liberar --tudo")
        menu.buy()
        self.assertTrue(ate(match, inputs, lambda: menu.asking))
        menu.pick("nao")
        menu.buy()
        passo(match, inputs, 30)
        self.assertFalse(computador.freed())
        self.assertFalse(match.freeing)

    def test_notebook_hacker_libera_tudo(self):
        match, inputs = casa_da_turma()
        p = perto(match, "notebook")
        self.assertTrue(match.arena.is_free(p.x, p.y, 12))
        self.assertTrue(match.interact(p))
        nb = match.menus[p]
        self.assertIsInstance(nb, HackerNotebook)
        self.assertEqual(nb.screen, "login")
        nb.buy()                                                    # digita a senha
        self.assertTrue(ate(match, inputs, lambda: nb.screen == "desktop" and not nb.busy))
        self.assertTrue(match.notebook_open)
        nb.pick("terminal")
        nb.buy()
        self.assertEqual(nb.screen, "terminal")
        self.assertTrue(ate(match, inputs, lambda: not nb.busy))
        self.assertTrue(nb.pick(f"cmd:{HACK}"))
        nb.buy()
        self.assertEqual(nb.snapshot()["action"], "AGUARDE")
        frames = 0
        while not match.freeing and frames < 1500:
            passo(match, inputs)
            frames += 1
        self.assertTrue(computador.freed())
        self.assertGreater(frames, 4 * 60)                          # a invasão tem animação longa
        texts = " ".join(t for t, _ in nb.lines)
        self.assertIn("SENHA ENCONTRADA: oi sumido", texts)
        self.assertIn("TUDO LIBERADO", texts)

    def test_desenha_as_telas(self):
        match, inputs = casa_da_turma()
        g = match.game
        p = perto(match, "pc")
        match.interact(p)
        pc = match.menus[p]
        q = match.players[1]
        _, rect, _ = next(c for c in match.computers if c[0] == "notebook")
        q.x, q.y = rect.centerx - 40, rect.bottom + 14
        match.interact(q)
        nb = match.menus[q]
        for screen in ("desktop", "arquivos", "navegador", "terminal"):
            pc.screen = screen
            match.draw(g.screen, g.ui)
        for screen in ("login", "desktop", "alerta", "terminal"):
            nb.screen = screen
            match.draw(g.screen, g.ui)
        match.freeing = 60
        match.draw(g.screen, g.ui)


class CantosTest(unittest.TestCase):
    def setUp(self):
        reset_progress()

    def test_moto_da_grau(self):
        match, inputs = casa_da_turma()
        p = match.players[0]
        moto = match.moto
        p.x, p.y = moto.x, moto.rect.bottom + 16
        self.assertTrue(match.arena.is_free(p.x, p.y, 12))
        self.assertTrue(match.interact(p))
        passo(match, inputs, 20)
        self.assertGreater(moto.tilt, 15)
        match.draw(match.game.screen, match.game.ui)
        passo(match, inputs, casa.GRAU_FRAMES)
        self.assertEqual(moto.tilt, 0)

    def test_roleta_gira_e_para_em_green_ou_red(self):
        match, inputs = casa_da_turma()
        p = match.players[0]
        r = match.roulette
        p.x, p.y = r.x, r.rect.bottom + 14
        self.assertTrue(match.arena.is_free(p.x, p.y, 12))
        self.assertTrue(match.interact(p))
        self.assertTrue(r.spinning)
        self.assertTrue(ate(match, inputs, lambda: not r.spinning, 600))
        self.assertIn(r.last, ("GREEN", "RED"))
        self.assertEqual(r.last, r.result())

    def test_padaria_da_senha_e_pao(self):
        match, inputs = casa_da_turma()
        p = match.players[0]
        b = match.bakery
        p.x, p.y = b.rect.centerx, b.rect.bottom + 14
        self.assertTrue(match.arena.is_free(p.x, p.y, 12))
        self.assertTrue(match.interact(p))
        self.assertEqual(b.ticket, 1)
        texts = [t.text for t in match.popups]
        self.assertIn("SENHA 001", texts)
        passo(match, inputs, casa.BREAD_FRAMES + 1)
        self.assertIn("PÃO QUENTINHO SAINDO!", [t.text for t in match.popups])


if __name__ == "__main__":
    unittest.main()
