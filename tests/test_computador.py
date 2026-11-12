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
    """Marca a linha ``key`` (rolando a lista até ela) e toca no meio dela, como o dedo no celular."""
    rows = [k for k, _, _ in menu.rows()]
    if key in rows:
        menu.sel = rows.index(key)
    menu._layout()
    rect = next(r for r, k in menu.spots if k == key)
    return menu.click(*rect.center)


def toque(menu, key):
    """O mesmo toque vindo do celular: ``pc:tap:u,v`` (0 a 1 na cópia da tela)."""
    rows = [k for k, _, _ in menu.rows()]
    if key in rows:
        menu.sel = rows.index(key)
    menu._layout()
    rect = next(r for r, k in menu.spots if k == key)
    return menu.pick(f"pc:tap:{rect.centerx / INNER_W:.4f},{rect.centery / INNER_H:.4f}")


def roda(match, inputs, menu, key):
    """Escolhe o comando pronto na lista do terminal e espera ele terminar de responder."""
    clica(menu, key)
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

    def test_janela_tem_metade_do_tamanho_antigo(self):
        _, _, _, menu = self.abre()
        w, h = menu.size(None)
        self.assertLessEqual(w, 520 // 2 + 10)                  # era 520 x 316
        self.assertLessEqual(w * h, 520 * 316 // 2)

    def test_pc_abre_e_o_celular_ganha_a_copia_da_tela(self):
        match, inputs, p, menu = self.abre()
        self.assertIsInstance(menu, Computer)
        snap = menu.snapshot()
        self.assertEqual(snap["kind"], "pc")
        self.assertTrue(snap["screen"])
        self.assertFalse(snap["typing"])                        # nada se digita
        self.assertEqual(snap["fields"], [])
        passo(match, inputs, 2)
        self.assertTrue(hub._screens[p.slot].startswith(b"\x89PNG"))     # o celular pede em /api/tela.png
        self.assertEqual(match._screens[p.slot], menu.version)
        self.assertIsNone(hub.screen(p.slot, "token-errado"))
        # o outro jogador não abre o mesmo computador ao mesmo tempo
        q = match.players[1]
        q.x, q.y = p.x + 30, p.y
        self.assertIsNone(match.computer_near(q))

    def test_toque_no_celular_abre_o_navegador_e_volta(self):
        _, _, _, menu = self.abre()
        toque(menu, "open:navegador")
        self.assertEqual(menu.screen, "navegador")
        clica(menu, "pag:3")
        self.assertIn("www.padariadojoao.com", menu.reading[1])
        clica(menu, "ler:voltar")
        self.assertIsNone(menu.reading)
        clica(menu, "pag:4")
        self.assertIn("SOULWIKI", menu.reading[0])
        clica(menu, "ler:voltar")
        clica(menu, "close")
        self.assertEqual(menu.screen, "inicio")

    def test_arquivos_abrem_o_texto(self):
        _, _, _, menu = self.abre()
        clica(menu, "open:arquivos")
        clica(menu, "arq:0")
        self.assertEqual(menu.reading[0], FILES[0][0])
        self.assertTrue(menu.back())                             # ESQUIVA fecha o arquivo
        self.assertIsNone(menu.reading)
        self.assertTrue(menu.back())                             # e volta para o início
        self.assertEqual(menu.screen, "inicio")
        self.assertFalse(menu.back())                            # no início, ESQUIVA desliga

    def test_terminal_so_com_comandos_prontos(self):
        match, inputs, p, menu = self.abre()
        clica(menu, "open:terminal")
        self.assertTrue(ate(match, inputs, lambda: not menu.busy))
        self.assertEqual([k[4:] for k, _, _ in menu.rows()], list(computador.PC_MENU))
        roda(match, inputs, menu, "cmd:ls")
        texts = " ".join(t for t, _ in menu.lines)
        self.assertIn(FILES[0][0], texts)
        roda(match, inputs, menu, "cmd:cat leia-me.txt")
        self.assertIn("AJUDA", menu.lines[-1][0])
        roda(match, inputs, menu, "cmd:limpar")
        self.assertEqual(menu.lines, [])
        roda(match, inputs, menu, "cmd:exit")
        self.assertEqual(menu.screen, "inicio")
        clica(menu, "desligar")
        passo(match, inputs, 2)
        self.assertNotIn(p, match.menus)
        self.assertNotIn(p.slot, match._screens)              # o celular parou de receber a tela

    def test_toda_linha_cabe_na_janela(self):
        _, _, _, menu = self.abre()
        ui = menu.match.game.ui
        for c in computador.PC_MENU + computador.NB_MENU:
            menu.say("  " + c.upper())
        for name, text in computador.FILES:
            menu.say("  " + text)
        for text, _, _, _, _ in menu.queue:
            self.assertLessEqual(ui.assets.text_width(text, 8), INNER_W - 8, text)

    def test_controle_anda_na_lista_e_segurar_esquiva_fecha(self):
        match, inputs, p, menu = self.abre()
        inp = inputs[p.slot]
        passo(match, inputs, 2)
        self.assertEqual(menu.sel, 0)
        inp.stick = (0.0, 1.0)                                   # para baixo: NAVEGADOR
        passo(match, inputs)
        inp.stick = (0.0, 0.0)
        passo(match, inputs)
        self.assertEqual(menu.rows()[menu.sel][0], "open:navegador")
        inp.tap("attack")
        passo(match, inputs)
        self.assertEqual(menu.screen, "navegador")
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
        roda(match, inputs, menu, "cmd:liberar --tudo")
        self.assertTrue(menu.asking)
        self.assertEqual([k for k, _, _ in menu.rows()], ["cmd:s", "cmd:n"])
        self.assertFalse(computador.freed())
        toque(menu, "cmd:s")
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
        from soulstrike.garagem import GarageMatch
        below = GarageMatch(match.game, match.run)                # e os 4 corrompidos no salão da garagem
        self.assertIn("cauanzera_corrompido", {s.key for s in below.speakers})

    def test_responder_nao_deixa_tudo_como_estava(self):
        match, inputs, _, menu = self.abre()
        clica(menu, "open:terminal")
        self.assertTrue(ate(match, inputs, lambda: not menu.busy))
        roda(match, inputs, menu, "cmd:liberar --tudo")
        roda(match, inputs, menu, "cmd:n")
        passo(match, inputs, 30)
        self.assertFalse(computador.freed())
        self.assertFalse(match.freeing)

    def test_notebook_hacker_libera_tudo(self):
        match, inputs, _, nb = self.abre("notebook")
        self.assertIsInstance(nb, HackerNotebook)
        self.assertEqual(nb.screen, "login")
        self.assertEqual([k[6:] for k, _, _ in nb.rows()], list(computador.GUESSES))
        toque(nb, "senha:123456")
        self.assertTrue(ate(match, inputs, lambda: not nb.busy))
        self.assertEqual(nb.screen, "login")
        self.assertIn("SENHA ERRADA", " ".join(t for t, _ in nb.lines[-2:]))
        clica(nb, "senha:oi sumido")
        self.assertTrue(ate(match, inputs, lambda: nb.screen == "inicio" and not nb.busy))
        self.assertTrue(match.notebook_open)
        clica(nb, "open:alerta")
        self.assertEqual(nb.reading[0], "ALERTA")
        clica(nb, "vacuo")
        self.assertIsNone(nb.reading)
        clica(nb, "open:terminal")
        self.assertEqual(nb.screen, "terminal")
        self.assertTrue(ate(match, inputs, lambda: not nb.busy))
        clica(nb, f"cmd:{HACK}")
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
        for screen in ("inicio", "arquivos", "navegador", "terminal"):
            pc.go(screen)
            match.draw(g.screen, g.ui)
            pc.png(g.ui)
        pc.go("inicio")
        clica(pc, "open:arquivos")
        clica(pc, "arq:2")
        match.draw(g.screen, g.ui)
        for screen in ("login", "inicio", "terminal"):
            nb.go(screen)
            match.draw(g.screen, g.ui)
            nb.png(g.ui)
        nb.open_app("alerta")
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
