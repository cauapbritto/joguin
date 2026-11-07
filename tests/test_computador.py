"""Etapa 3b da Casa da turma: o PC do Cauanzera, o notebook do Albeguinio (com o LIBERAR TUDO), a
moto, a roleta e a padaria."""
import unittest
from unittest import mock

from test_casa import casa_da_turma, passo, reset_progress

from soulstrike import casa, computador, progress
from soulstrike.casa import HubMatch
from soulstrike.computador import FILES, HACK, INNER_W, INNER_H, Computer, HackerNotebook
from soulstrike.net.remote import hub


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


def clica(menu, key):
    """Clica (como o dedo ou a setinha) no meio do que faz ``key`` na tela de dentro."""
    menu._layout()
    rect = next(r for r, k in menu.spots if k == key)
    return menu.click(*rect.center)


def toque(menu, key):
    """O mesmo clique vindo do celular: ``pc:tap:u,v`` (0 a 1 na cópia da tela)."""
    menu._layout()
    rect = next(r for r, k in menu.spots if k == key)
    return menu.pick(f"pc:tap:{rect.centerx / INNER_W:.4f},{rect.centery / INNER_H:.4f}")


def digita(match, inputs, menu, text):
    """Digita no celular, ENVIAR, e espera o terminal terminar de responder."""
    menu.pick("pc:text:" + text)
    return ate(match, inputs, lambda: not menu.busy)


class ComputadorTest(unittest.TestCase):
    def setUp(self):
        reset_progress()

    def tearDown(self):
        reset_progress()

    def abre(self, kind="pc"):
        match, inputs = casa_da_turma()
        p = perto(match, kind)
        self.assertTrue(match.arena.is_free(p.x, p.y, 12))
        self.assertTrue(match.interact(p))
        return match, inputs, p, match.menus[p]

    def test_pc_abre_e_o_celular_ganha_a_copia_da_tela(self):
        match, inputs, p, menu = self.abre()
        self.assertIsInstance(menu, Computer)
        snap = menu.snapshot()
        self.assertEqual(snap["kind"], "pc")
        self.assertTrue(snap["screen"])
        self.assertFalse(snap["typing"])
        passo(match, inputs, 2)
        self.assertTrue(hub._screens[p.slot].startswith(b"\x89PNG"))     # o celular pede em /api/tela.png
        self.assertEqual(match._screens[p.slot], menu.version)
        self.assertIsNone(hub.screen(p.slot, "token-errado"))
        # o outro jogador não abre o mesmo computador ao mesmo tempo
        q = match.players[1]
        q.x, q.y = p.x + 30, p.y
        self.assertIsNone(match.computer_near(q))

    def test_toque_no_celular_abre_o_navegador_e_o_x_fecha(self):
        _, _, _, menu = self.abre()
        toque(menu, "open:navegador")
        self.assertEqual(menu.screen, "navegador")
        clica(menu, "pag:3")
        self.assertIn("PADARIA DO JOÃO", " ".join(menu.page_lines()))
        clica(menu, "close")
        self.assertEqual(menu.screen, "desktop")

    def test_endereco_digitado_leva_ao_site_ou_ao_404(self):
        _, _, _, menu = self.abre()
        clica(menu, "open:navegador")
        toque(menu, "focus:url")
        self.assertEqual(menu.snapshot()["focus"], "url")
        self.assertTrue(any(f[4] == "url" for f in menu.snapshot()["fields"]))
        menu.pick("pc:text:www.soulwiki.com")
        self.assertIn("BESTIÁRIO", " ".join(menu.page_lines()))
        clica(menu, "focus:url")
        menu.pick("pc:text:google.com")
        self.assertIsNone(menu.page)
        self.assertIn("ERRO 404", " ".join(menu.page_lines()))

    def test_a_tv_mostra_o_que_esta_sendo_digitado(self):
        _, _, _, menu = self.abre()
        clica(menu, "open:terminal")
        version = menu.version
        menu.pick("pc:buf:aju")
        self.assertEqual(menu.buffer, "aju")
        self.assertGreater(menu.version, version)
        self.assertEqual(menu.suggestions(), ["ajuda"])

    def test_terminal_comandos_de_verdade(self):
        match, inputs, p, menu = self.abre()
        clica(menu, "open:terminal")
        self.assertEqual(menu.focus, "terminal")
        self.assertTrue(ate(match, inputs, lambda: not menu.busy))
        digita(match, inputs, menu, "ls")
        texts = " ".join(t for t, _ in menu.lines)
        self.assertIn(FILES[0][0], texts)
        digita(match, inputs, menu, "xyz")
        self.assertIn("COMANDO NÃO ENCONTRADO", menu.lines[-1][0])
        digita(match, inputs, menu, "limpar")
        self.assertEqual(menu.lines, [("", menu.lines[0][1])] if menu.lines else [])
        digita(match, inputs, menu, "exit")
        self.assertEqual(menu.screen, "desktop")
        clica(menu, "open:terminal")
        digita(match, inputs, menu, "desligar")
        passo(match, inputs, 2)
        self.assertNotIn(p, match.menus)
        self.assertNotIn(p.slot, match._screens)              # o celular parou de receber a tela

    def test_teclado_da_tela_e_sugestao(self):
        match, inputs, _, menu = self.abre()
        clica(menu, "open:terminal")
        self.assertTrue(ate(match, inputs, lambda: not menu.busy))
        for key in ("osk:a", "osk:j"):
            clica(menu, key)
        self.assertEqual(menu.buffer, "aj")
        clica(menu, "osk:apagar")
        self.assertEqual(menu.buffer, "a")
        clica(menu, "osk:sug:ajuda")                           # sugestão completa o comando
        self.assertEqual(menu.buffer, "ajuda")
        clica(menu, "osk:enter")
        self.assertTrue(ate(match, inputs, lambda: not menu.busy))
        self.assertIn("ajuda", " ".join(t for t, _ in menu.lines))

    def test_setinha_do_controle_e_segurar_esquiva_fecha(self):
        match, inputs, p, menu = self.abre()
        inp = inputs[p.slot]
        passo(match, inputs, 2)
        menu._layout()
        target = next(r for r, k in menu.spots if k == "open:arquivos").center
        for _ in range(200):                                   # leva a setinha até ARQUIVOS
            dx, dy = target[0] - menu.cursor[0], target[1] - menu.cursor[1]
            if abs(dx) < 6 and abs(dy) < 6:
                break
            inp.stick = (max(-1, min(1, dx / 20)), max(-1, min(1, dy / 20)))
            passo(match, inputs)
        inp.stick = (0.0, 0.0)
        inp.tap("attack")
        passo(match, inputs)
        self.assertEqual(menu.screen, "arquivos")
        for _ in range(computador.CLOSE_HOLD + 2):
            inp.hold("dodge")
            passo(match, inputs)
        self.assertNotIn(p, match.menus)

    def test_fechar_tudo_no_celular(self):
        match, inputs, p, menu = self.abre()
        with mock.patch.object(hub, "orders", return_value=[(p.slot, "fechar", False)]):
            match.phone_shop()
        self.assertNotIn(p, match.menus)

    def test_terminal_do_pc_libera_tudo(self):
        match, inputs, _, menu = self.abre()
        clica(menu, "open:terminal")
        self.assertTrue(ate(match, inputs, lambda: not menu.busy))
        digita(match, inputs, menu, "liberar --tudo")
        self.assertTrue(menu.asking)
        self.assertEqual(menu.suggestions(), ["s", "n"])
        self.assertFalse(computador.freed())
        menu.pick("pc:text:s")
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
        match, inputs, _, menu = self.abre()
        clica(menu, "open:terminal")
        self.assertTrue(ate(match, inputs, lambda: not menu.busy))
        digita(match, inputs, menu, "liberar --tudo")
        digita(match, inputs, menu, "n")
        passo(match, inputs, 30)
        self.assertFalse(computador.freed())
        self.assertFalse(match.freeing)

    def test_notebook_hacker_libera_tudo(self):
        match, inputs, _, nb = self.abre("notebook")
        self.assertIsInstance(nb, HackerNotebook)
        self.assertEqual(nb.screen, "login")
        toque(nb, "focus:senha")
        nb.pick("pc:text:senha errada")
        self.assertTrue(ate(match, inputs, lambda: not nb.busy))
        self.assertEqual(nb.screen, "login")
        clica(nb, "focus:senha")
        nb.pick("pc:text:Oi Sumido")
        self.assertTrue(ate(match, inputs, lambda: nb.screen == "desktop" and not nb.busy))
        self.assertTrue(match.notebook_open)
        clica(nb, "open:terminal")
        self.assertEqual(nb.screen, "terminal")
        self.assertTrue(ate(match, inputs, lambda: not nb.busy))
        nb.pick(f"pc:text:{HACK}")
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
        match, inputs, _, pc = self.abre()
        g = match.game
        q = match.players[1]
        _, rect, _ = next(c for c in match.computers if c[0] == "notebook")
        q.x, q.y = rect.centerx - 40, rect.bottom + 14
        match.interact(q)
        nb = match.menus[q]
        for screen in ("desktop", "arquivos", "navegador", "terminal"):
            pc.screen = screen
            for focus in (None, "terminal"):
                pc.focus = focus
                match.draw(g.screen, g.ui)
                pc.png(g.ui)
        pc.page = None
        pc.screen = "navegador"
        match.draw(g.screen, g.ui)
        for screen in ("login", "desktop", "alerta", "terminal"):
            nb.screen = screen
            match.draw(g.screen, g.ui)
            nb.png(g.ui)
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
