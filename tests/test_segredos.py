"""Segredos: os detalhezinhos escondidos (reações discretas, cacos na primeira vez e o caderno)."""
import unittest

import pygame

from apoio import game

from soulstrike import cacos, computador, config, progress, segredos
from soulstrike.casa import NAP_FRAMES, SCARE_HITS, STREAK_ANGRY
from test_casa import casa_da_turma, passo, reset_progress


def perto(p, rect, dy=12):
    p.x, p.y = rect.centerx, rect.bottom + dy


class Pote(unittest.TestCase):
    def setUp(self):
        reset_progress()

    def test_cacos_so_na_primeira_vez(self):
        self.assertTrue(segredos.find("wifi"))
        self.assertEqual(cacos.balance(), segredos.REWARD)
        self.assertFalse(segredos.find("wifi"))
        self.assertEqual(cacos.balance(), segredos.REWARD)
        self.assertEqual(segredos.found(), {"wifi"})

    def test_chave_desconhecida_nao_conta(self):
        self.assertFalse(segredos.find("nao_existe"))
        progress.save({segredos.KEY: ["nao_existe", "wifi", 3]})
        self.assertEqual(segredos.found(), {"wifi"})

    def test_caderno_mostra_achados_e_dicas(self):
        segredos.find("cochilo")
        pages = segredos.notebook()
        casa = pages["CASA"]
        self.assertIn((True, "COCHILO NO SOFÁ"), casa)
        self.assertTrue(all(text.startswith("???") for ok, text in casa if not ok))
        self.assertEqual(segredos.count(), (1, len(segredos.SECRETS)))

    def test_chaves_unicas_e_textos_curtos(self):
        keys = [s[0] for s in segredos.SECRETS]
        self.assertEqual(len(keys), len(set(keys)))
        for key, place, name, tip in segredos.SECRETS:
            self.assertIn(place, segredos.PLACES)
            self.assertLessEqual(len(name), 24, name)
            self.assertLessEqual(len("??? · " + tip), 40, tip)


class Casa(unittest.TestCase):
    def setUp(self):
        reset_progress()
        self.match, self.inputs = casa_da_turma(("guerreiro", "atirador"))
        self.p1, self.p2 = self.match.players

    def test_roteador_derruba_o_wifi(self):
        perto(self.p1, self.match.router)
        self.assertTrue(self.match.interact(self.p1))
        self.assertGreater(self.match.wifi_down, 0)
        self.assertTrue(segredos.is_found("wifi"))
        alb = [s for s in self.match.speakers if s.key == "albeguinio" and s.talk > 0]
        self.assertTrue(alb and alb[0].line == "JÁ REINICIOU O WI-FI?")
        pc = computador.make(self.match, self.p1, "pc", (0, 0))
        pc.open_app("navegador")
        self.assertEqual(pc.page_lines()[0], "SEM INTERNET")
        nb = computador.make(self.match, self.p1, "notebook", (0, 0))
        nb.run("wifi --reiniciar")
        for _ in range(60):
            nb.step()
        self.assertEqual(self.match.wifi_down, 0)

    def test_espantalho_balanca_e_reclama(self):
        perto(self.p1, self.match.scarecrow_rect)
        for _ in range(SCARE_HITS - 1):
            self.assertTrue(self.match.interact(self.p1))
        self.assertGreater(self.match.scarecrow.wobble, 0)
        self.assertFalse(segredos.is_found("espantalho"))
        self.match.interact(self.p1)
        self.assertTrue(segredos.is_found("espantalho"))
        view = pygame.Surface((config.SCREEN_W, config.SCREEN_H))
        self.match.scarecrow.draw(view, self.match.camera)

    def test_mangueira_molha_o_amigo(self):
        perto(self.p1, self.match.hose)
        self.p1.facing = (1.0, 0.0)
        self.p2.x, self.p2.y = self.match.hose.right + 80, self.match.hose.centery
        self.assertTrue(self.match.interact(self.p1))
        passo(self.match, self.inputs, 10)
        self.assertIn(self.p2, self.match.wet)
        self.assertTrue(segredos.is_found("mangueira"))

    def test_cochilo_do_lado_do_sofa(self):
        sofa = self.match.sofas[0]
        self.p1.x, self.p1.y = sofa.centerx, sofa.bottom + 20
        passo(self.match, self.inputs, NAP_FRAMES + 5)
        self.assertTrue(segredos.is_found("cochilo"))

    def test_insistir_na_conversa(self):
        s = next(s for s in self.match.speakers if s.key == "tanque")
        self.p1.x, self.p1.y = s.x, s.y + 30
        for _ in range(STREAK_ANGRY):
            s.say(self.match)
        self.assertEqual(s.line, "DE NOVO?!")
        self.assertTrue(segredos.is_found("de_novo"))

    def test_madrugada_boceja(self):
        old = segredos._hour
        segredos._hour = lambda: 3
        try:
            s = next(s for s in self.match.speakers if s.key == "ninja")
            s.say(self.match)
            self.assertIn(s.line, __import__("soulstrike.casa", fromlist=["SONO"]).SONO)
            s.say(self.match)
            self.assertIn(s.line, s.lines)
        finally:
            segredos._hour = old
        self.assertTrue(segredos.is_found("madrugada"))

    def test_caderno_no_computador(self):
        segredos.find("wifi")
        pc = computador.make(self.match, self.p1, "pc", (0, 0))
        self.assertIn(("caderno", "CADERNO"), pc.desktop_items())
        pc.open_app("caderno")
        surf = pygame.Surface((computador.INNER_W, computador.INNER_H))
        pc.draw_inner(surf, game().ui, surf.get_rect())


if __name__ == "__main__":
    unittest.main()


class Campanha(unittest.TestCase):
    def setUp(self):
        reset_progress()

    def test_sombra_do_proprio_heroi_fala(self):
        from test_mansao import masmorra
        from soulstrike.campaign import DUNGEON_2
        match = masmorra("floresta", DUNGEON_2, chars=("velocista", "atirador"))
        e = match._spawn("sombra:velocista", 800, 700)
        self.assertTrue(segredos.is_found("espelho"))
        self.assertIn("CHEGUEI PRIMEIRO. DE NOVO.", [p.text for p in match.popups])
        self.assertTrue(e.alive_in_match)

    def test_sombra_de_outro_heroi_nao_fala(self):
        from test_mansao import masmorra
        from soulstrike.campaign import DUNGEON_2
        match = masmorra("floresta", DUNGEON_2, chars=("guerreiro", "atirador"))
        match._spawn("sombra:velocista", 800, 700)
        self.assertFalse(segredos.is_found("espelho"))

    def test_chefe_que_era_o_proprio_heroi(self):
        from test_mansao import masmorra
        from soulstrike.campaign import DUNGEON_2
        match = masmorra("cobertura", DUNGEON_2, chars=("borba", "atirador"))
        x, y = match.dungeon.boss_spot
        boss = match._spawn("chefe", *match.arena.at(x, y))
        match.controllers[boss].update(boss, match)
        self.assertTrue(segredos.is_found("espelho"))
        self.assertIn("EU ME INVENTEI DE NOVO?", [p.text for p in match.popups])

    def test_ultimo_inimigo_foge_tremendo(self):
        from test_mansao import masmorra
        match = masmorra("floresta")
        match.portals = []
        match.wave_size = 5
        import math
        cx, cy = match.arena.room.center if match.arena.room else (1000, 700)
        x, y = match.arena.free_spot(cx, cy, 20)
        e = match._spawn("diabrete", x, y)
        p = match.players[0]
        p.x, p.y = x - 60, y
        match.update()
        self.assertGreater(e.panic, 0)
        self.assertTrue(segredos.is_found("panico"))
        d0 = math.hypot(e.x - p.x, e.y - p.y)
        for _ in range(30):
            match.update()
        self.assertGreater(math.hypot(e.x - p.x, e.y - p.y), d0 + 20)

    def test_dois_inimigos_nao_entram_em_panico(self):
        from test_mansao import masmorra
        match = masmorra("floresta")
        match.portals = []
        match.wave_size = 5
        a = match._spawn("diabrete", 900, 700)
        match._spawn("diabrete", 1000, 700)
        match.update()
        self.assertFalse(getattr(a, "panic", 0))

    def test_parado_na_fila_chamam_a_senha(self):
        from test_mansao import masmorra
        match = masmorra("mansao_sede")
        fila = match.hazard
        rect, _ = fila.lanes[2]
        p = match.players[0]
        p.x, p.y = rect.centerx, rect.centery
        fila.timer = 9999
        for _ in range(fila.PATIENCE + 2):
            fila.update(match)
        self.assertTrue(segredos.is_found("senha"))
        self.assertTrue(any("SENHA" in t.text and "P1" in t.text for t in match.popups))

    def test_sala_do_laser_sem_arranhao(self):
        from test_mansao import masmorra
        from soulstrike.campaign import DUNGEON_1
        match = masmorra("procedimentos", DUNGEON_1)
        self.assertTrue(hasattr(match.hazard, "ever_hit"))
        match.hazard.fired = True
        match._clear()
        self.assertTrue(segredos.is_found("laser"))

    def test_laser_que_pegou_nao_conta(self):
        from test_mansao import masmorra
        from soulstrike.campaign import DUNGEON_1
        match = masmorra("procedimentos", DUNGEON_1)
        match.hazard.fired = True
        match.hazard.ever_hit.add(match.players[1])
        match._clear()
        self.assertFalse(segredos.is_found("laser"))

    def test_chefe_cansado_que_ninguem_bateu(self):
        from test_mansao import masmorra
        from soulstrike.campaign import DUNGEON_2
        match = masmorra("templo", DUNGEON_2)
        x, y = match.dungeon.boss_spot
        boss = match._spawn("chefe", *match.arena.at(x, y))
        brain = match.controllers[boss]
        brain._set(boss, "tired", 2)
        for _ in range(3):
            brain.update(boss, match)
        self.assertTrue(segredos.is_found("ninguem"))

    def test_toca_aqui_depois_de_levantar(self):
        from test_mansao import masmorra
        match = masmorra("floresta")
        a, b = match.players
        match.high_fives = [[frozenset((a, b)), set(), 90]]
        match._high_five(a)
        self.assertFalse(segredos.is_found("high_five"))
        match._high_five(b)
        self.assertTrue(segredos.is_found("high_five"))


class Modos(unittest.TestCase):
    def setUp(self):
        reset_progress()

    def test_duelo_parado_passa_o_feno(self):
        from soulstrike.matches import STANDOFF_FRAMES, BattleMatch, Tumbleweed
        from soulstrike.session import Session, SlotSetup
        from apoio import FakeInput
        g = game()
        g.session = Session("duel", [SlotSetup(1, char=0), SlotSetup(2, char=1)])
        match = BattleMatch(g, g.session)
        for f in match.fighters:
            match.controllers[f] = FakeInput()
        for _ in range(config.ROUND_INTRO_FRAMES + STANDOFF_FRAMES + 5):
            match.update()
        self.assertTrue(any(isinstance(e, Tumbleweed) for e in match.effects))
        self.assertTrue(segredos.is_found("feno"))
        match.draw(g.screen, g.ui)

    def test_duelo_com_alguem_andando_nao_tem_feno(self):
        from soulstrike.matches import STANDOFF_FRAMES, BattleMatch
        from soulstrike.session import Session, SlotSetup
        from apoio import FakeInput
        g = game()
        g.session = Session("duel", [SlotSetup(1, char=0), SlotSetup(2, char=1)])
        match = BattleMatch(g, g.session)
        inp = FakeInput()
        for f in match.fighters:
            match.controllers[f] = FakeInput()
        match.controllers[match.fighters[0]] = inp
        inp.stick = (1.0, 0.0)
        for _ in range(config.ROUND_INTRO_FRAMES + STANDOFF_FRAMES + 5):
            match.update()
        self.assertFalse(segredos.is_found("feno"))

    def test_socio_da_trave(self):
        from apoio import futebol
        from soulstrike.matches import POST_CLUB
        match, _ = futebol()
        f = match.fighters[0]
        g = match.goals[1]
        for _ in range(POST_CLUB):
            match.last_touch = f
            ball = match.ball
            ball.x, ball.y = g.rect.x - 4, g.rect.y
            ball.vx, ball.vy = 1.0, 0.0
            match._post_check(ball, (-8.0, 0.0))
        self.assertTrue(segredos.is_found("trave"))

    def test_bola_devagar_nao_e_trave(self):
        from apoio import futebol
        match, _ = futebol()
        match.last_touch = match.fighters[0]
        g = match.goals[1]
        for _ in range(5):
            match.ball.x, match.ball.y = g.rect.x - 4, g.rect.y
            match._post_check(match.ball, (-1.0, 0.0))
        self.assertFalse(segredos.is_found("trave"))

    def test_de_tres_no_estouro(self):
        from test_basquete import arremesso, basquete
        match, _ = basquete()
        match.clock = 2 * config.FPS
        side = match.hoop_of(0)
        from soulstrike.arena import Court
        hx = Court.hoop_x(side)
        x = hx + (560 if side == 0 else -560)
        arremesso(match, 0, x, Court.MID_Y)
        self.assertGreater(match.score[0], 0)
        self.assertTrue(segredos.is_found("estouro"))

    def test_de_tres_no_meio_do_jogo_nao_conta(self):
        from test_basquete import arremesso, basquete
        from soulstrike.arena import Court
        match, _ = basquete()
        side = match.hoop_of(0)
        hx = Court.hoop_x(side)
        arremesso(match, 0, hx + (560 if side == 0 else -560), Court.MID_Y)
        self.assertFalse(segredos.is_found("estouro"))

    def test_penalti_foi_pra_cuiaba(self):
        from soulstrike import penalty as P
        from soulstrike.scenes import penalty as S
        from test_penaltis import cena
        teams = [[S.Taker("matador", 0, slot=1, cpu=False)], [S.Taker("paredao", 1)]]
        scene = cena(teams, inputs=(1,))
        scene._next_kick()
        k = scene.kick
        k.shot = P.Shot(0.5, 1.5, 30, kind="isolou")
        scene.rng.random = lambda: 0.0
        scene._resolve()
        self.assertTrue(getattr(k, "cuiaba", False))
        self.assertTrue(segredos.is_found("cuiaba"))
        for _ in range(40):
            scene.update()
            scene.draw(game().screen)
