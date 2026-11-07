"""Capítulo 4 da campanha (Mansão do Carimbo): os monstros da repartição, os perigos das salas
(fila, pilhas, calor, queda de energia e a reunião), as fases 10 a 12 e o caminho do capítulo 3 para
o 4."""
import random
import unittest

from apoio import FakeInput, game

from soulstrike import progress
from soulstrike.boss import BOSSES
from soulstrike.campaign import CHAPTER_START, DUNGEON_1, PHASES, STORY, CampaignMatch, CampaignRun
from soulstrike.data import CHARACTERS, PHASE_RELICS
from soulstrike.enemies import BRAINS, CREATURES
from soulstrike.hazards import HAZARDS, make_hazard
from soulstrike.mansao import FALTA_MULT, Blackout, CoffeeSplash, CookieNotice, FaltaMark, Heat, PieChart
from soulstrike.session import Session, SlotSetup

KEYS = [c.key for c in CHARACTERS]
FASE = {p.key: i for i, p in enumerate(PHASES)}
MANSAO = ("processo", "apenso", "carimbador", "impressora", "garrafa_termica", "tuiuiu_drone",
          "ponto_eletronico", "popup_iara", "projetor", "arquivo_aco")


def masmorra(phase="mansao_sede", dungeon=DUNGEON_1, chars=("guerreiro", "atirador")):
    g = game()
    g.session = Session("campaign", [SlotSetup(i + 1, char=KEYS.index(c)) for i, c in enumerate(chars)])
    run = CampaignRun(g.session)
    run.phase_index = FASE[phase]
    run.begin_phase()
    run.stage = dungeon
    match = CampaignMatch(g, run)
    match.state, match.state_timer, match.banner = "fight", 0, None
    match.wave = len(match.waves) - 1
    for f in match.players:
        match.controllers[f] = FakeInput()
        f.max_hp = f.hp = 99999
    return match


def passo(match, frames):
    for _ in range(frames):
        match.update()


def bater(match, e, who=None, dmg=5):
    who = who or match.players[0]
    e.take_damage(dmg, who.x, who.y, attacker=who, match=match)
    e.stun_timer = 0


class CapituloTest(unittest.TestCase):
    def test_tres_fases_no_capitulo_4(self):
        cap4 = [p.key for p in PHASES if p.chapter == 4]
        self.assertEqual(cap4, ["mansao_sede", "mansao_patio", "mansao_gabinete"])
        self.assertEqual(PHASES[CHAPTER_START[4]].key, "mansao_sede")
        self.assertEqual(PHASES[-1].dungeons[-1].boss, "cauanzera")
        self.assertIn("cauanzera", BOSSES)

    def test_perigos_e_sombras(self):
        rooms = {d.map_key: d for p in PHASES if p.chapter == 4 for d in p.dungeons}
        self.assertEqual({k: d.hazard for k, d in rooms.items() if d.hazard},
                         {"mansao_fila": "fila", "mansao_arquivo": "pilha", "mansao_patio": "calor",
                          "mansao_cpd": "energia", "mansao_reuniao": "reuniao"})
        shadows = {kind for d in rooms.values() for wave in d.waves for kind, _ in wave if kind.startswith("sombra:")}
        self.assertEqual(shadows, {"sombra:paredao", "sombra:faisca", "sombra:trovao"})

    def test_historia_e_loja_de_cada_fase(self):
        for p in PHASES:
            self.assertIn(p.key, STORY)
            self.assertIn(p.key, PHASE_RELICS)
        self.assertIn("fim_capitulo3", STORY)
        gancho = " ".join(text for _, _, text in STORY["fim_capitulo3"][2])
        self.assertIn("lasquinha", gancho)
        final = " ".join(text for _, _, text in STORY["final"][2])
        self.assertIn("CAUANZERA CORROMPIDO", final)

    def test_suite_vip_fecha_o_capitulo_3(self):
        g = game()
        g.session = Session("campaign", [SlotSetup(1, char=0)])
        run = CampaignRun(g.session)
        run.phase_index = FASE["suite_vip"]
        self.assertTrue(run.chapter_end)
        run.phase_index = FASE["mansao_gabinete"]
        self.assertTrue(run.last_phase)

    def test_comecar_no_capitulo_4(self):
        g = game()
        g.session = Session("campaign", [SlotSetup(1, char=0), SlotSetup(2, char=1)])
        run = CampaignRun(g.session)
        run.start_at_chapter(4)
        self.assertEqual(run.phase.key, "mansao_sede")
        for s in run.slots:
            self.assertEqual(len(run.upgrades[s]), 6)

    def test_campanha_salva_guarda_o_capitulo_4(self):
        g = game()
        g.session = Session("campaign", [SlotSetup(1, char=0)])
        run = CampaignRun(g.session)
        run.start_at_chapter(4)
        back = CampaignRun.from_save(run.to_save())
        self.assertEqual(back.start_chapter, 4)
        self.assertEqual(back.phase.key, "mansao_sede")


class ProgressoTest(unittest.TestCase):
    def setUp(self):
        import os
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.old = os.environ.get("SOULSTRIKE_PROGRESS")
        os.environ["SOULSTRIKE_PROGRESS"] = os.path.join(self.tmp.name, "p.json")

    def tearDown(self):
        import os
        if self.old is None:
            os.environ.pop("SOULSTRIKE_PROGRESS", None)
        else:
            os.environ["SOULSTRIKE_PROGRESS"] = self.old
        self.tmp.cleanup()

    def test_capitulo_3_libera_o_4_e_a_campanha_acaba_no_4(self):
        self.assertFalse(progress.chapter_cleared(3))
        self.assertTrue(progress.record_chapter(3))
        self.assertTrue(progress.chapter_cleared(3))
        self.assertFalse(progress.chapter_cleared(4))
        record, unlocked = progress.record_campaign(900, "normal", 1)
        self.assertTrue(record and unlocked)
        self.assertTrue(progress.chapter_cleared(4))
        self.assertEqual(progress.best_time("normal"), 900)

    def test_menu_mostra_o_capitulo_4_depois_do_3(self):
        from soulstrike.scenes.menus import ModeScene
        g = game()
        modes = [m for _, ms in ModeScene(g).modes_of("campanha") for m in ms]
        self.assertNotIn("campaign4", modes)
        progress.record_chapter(3)
        modes = [m for _, ms in ModeScene(g).modes_of("campanha") for m in ms]
        self.assertIn("campaign4", modes)


class MonstrosTest(unittest.TestCase):
    def test_todos_registrados(self):
        for kind in MANSAO:
            self.assertIn(kind, CREATURES)
            self.assertIn(kind, BRAINS)

    def test_todos_aparecem_e_lutam(self):
        random.seed(7)
        match = masmorra()
        for k, kind in enumerate(MANSAO):
            match._spawn(kind, 300 + (k % 5) * 220, 400 + (k // 5) * 400)
        hp = sum(f.hp for f in match.players)
        passo(match, 600)
        self.assertLess(sum(f.hp for f in match.players), hp)

    def test_processo_vira_dois_apensos(self):
        match = masmorra()
        p = match.players[0]
        e = match.spawn_now("processo", p.x + 200, p.y)
        bater(match, e, dmg=9999)
        passo(match, 10)
        apensos = [x for x in match.alive_enemies if getattr(x, "kind", "") == "apenso"]
        self.assertEqual(len(apensos), 2)

    def test_carimbador_carimba_e_fica_preso(self):
        match = masmorra()
        p = match.players[0]
        e = match.spawn_now("carimbador", p.x + 150, p.y)
        brain = match.controllers[e]
        brain.cd = 0
        for _ in range(200):
            match.update()
            if brain.stuck:
                break
        self.assertGreater(brain.stuck, 0)
        self.assertGreater(e.vulnerability, 1.0)

    def test_impressora_atola_depois_de_tres_rajadas(self):
        match = masmorra()
        p = match.players[0]
        e = match.spawn_now("impressora", p.x + 250, p.y)
        brain = match.controllers[e]
        for _ in range(3):
            brain._fan(e, match, p)
        self.assertGreater(brain.jam, 0)
        self.assertGreater(e.vulnerability, 1.0)

    def test_ponto_marca_falta(self):
        match = masmorra()
        p = match.players[0]
        mark = FaltaMark(p, frames=10)
        match.add_effect(mark)
        p.falta = mark
        self.assertEqual(p.vulnerability, FALTA_MULT)
        passo(match, 12)
        self.assertEqual(p.vulnerability, 1.0)
        self.assertIsNone(p.falta)

    def test_popup_abre_cookies_e_bater_fecha(self):
        match = masmorra()
        p = match.players[0]
        e = match.spawn_now("popup_iara", p.x + 120, p.y)
        brain = match.controllers[e]
        brain.loading, brain.last_hp = 2, e.hp
        passo(match, 3)
        self.assertTrue(any(isinstance(n, CookieNotice) for n in match.notices))
        match.notices = []
        brain.loading, brain.last_hp = 30, e.hp
        bater(match, e)
        passo(match, 1)
        self.assertEqual(brain.loading, 0)
        self.assertFalse(match.notices)

    def test_pizza_queima_so_as_fatias_acesas(self):
        match = masmorra()
        p = match.players[0]
        owner = match.spawn_now("projetor", p.x + 400, p.y)
        chart = PieChart(owner, p.x, p.y, 5, 10, lit=range(6))
        self.assertTrue(chart.covers(p))
        chart = PieChart(owner, p.x, p.y, 5, 10, lit=())
        self.assertFalse(chart.covers(p))

    def test_cafe_avisa_e_queima(self):
        match = masmorra()
        p = match.players[0]
        p.max_hp = p.hp = 100
        owner = match.spawn_now("garrafa_termica", p.x + 300, p.y)
        match.add_effect(CoffeeSplash(owner, p.x, p.y, 10, 8))
        passo(match, 5)
        self.assertEqual(p.hp, 100)          # ainda é só o aviso
        passo(match, 8)
        self.assertLess(p.hp, 100)

    def test_arquivo_abre_as_gavetas(self):
        match = masmorra()
        p = match.players[0]
        e = match.spawn_now("arquivo_aco", p.x + 250, p.y)
        brain = match.controllers[e]
        brain.charging = True
        e.charge_timer = 0
        brain.act(e, match, p)
        self.assertEqual(e.vulnerability, 2.0)


class PerigosTest(unittest.TestCase):
    def test_registrados(self):
        for key in ("fila", "pilha", "calor", "energia", "reuniao"):
            self.assertIn(key, HAZARDS)

    def test_cada_sala_roda_com_o_perigo(self):
        random.seed(3)
        for phase in ("mansao_sede", "mansao_patio", "mansao_gabinete"):
            for d in range(2):
                match = masmorra(phase, DUNGEON_1 if d == 0 else 3)
                passo(match, 700)
                self.assertTrue(all(f.alive_in_match for f in match.players))

    def test_fila_arrasta_quem_esta_na_faixa(self):
        match = masmorra("mansao_sede")
        fila = match.hazard
        rect, (dx, dy) = fila.lanes[0]
        p = match.players[0]
        p.x, p.y = rect.centerx, rect.centery
        fila.state, fila.timer, fila.active = "move", 50, [0]
        x0 = p.x
        for _ in range(10):
            fila.update(match)
        self.assertGreater((p.x - x0) * dx, 10)

    def test_calor_enche_no_sol_e_baixa_na_sombra(self):
        match = masmorra("mansao_patio")
        heat = match.hazard
        self.assertIsInstance(heat, Heat)
        p = match.players[0]
        p.x, p.y = 1000, 560                    # sol
        while heat.in_shade(p):
            p.y += 40
        for _ in range(60):
            heat.update(match)
        hot = heat.heat[p]
        self.assertGreater(hot, 0)
        p.x, p.y = heat.shades[0].center
        for _ in range(60):
            heat.update(match)
        self.assertLess(heat.heat[p], hot)

    def test_no_breaks_trazem_a_luz(self):
        match = masmorra("mansao_patio", 3)
        dark = match.hazard
        self.assertIsInstance(dark, Blackout)
        p = match.players[0]
        for b in dark.boxes:
            p.x, p.y = b.x, b.y
            self.assertTrue(dark.interact(p, match))
        self.assertFalse(dark.off_boxes)

    def test_reuniao_puxa_para_o_meio(self):
        match = masmorra("mansao_gabinete")
        meeting = match.hazard
        p = match.players[0]
        p.x, p.y = 300, 300
        meeting.state, meeting.timer = "pull", 60
        d0 = abs(p.x - meeting.center[0]) + abs(p.y - meeting.center[1])
        for _ in range(20):
            meeting.update(match)
        self.assertLess(abs(p.x - meeting.center[0]) + abs(p.y - meeting.center[1]), d0)

    def test_sem_perigo_desconhecido(self):
        self.assertIsNone(make_hazard("nada", None))


def chefe():
    random.seed(2)
    match = masmorra("mansao_gabinete", 3)
    match.wave = -1
    match._start_wave(0)
    passo(match, 80)
    return match, match.boss, match.controllers[match.boss]


def pancada(match, e, frac):
    e.invulnerable_timer = 0
    e.hp = round(e.max_hp * frac)
    passo(match, 2)


class ChefeTest(unittest.TestCase):
    def test_tres_etapas_virada_e_tomada(self):
        match, boss, brain = chefe()
        self.assertEqual(brain.stage, 1)
        pancada(match, boss, 0.49)
        self.assertEqual(brain.stage, 2)
        self.assertIsNotNone(brain.iara)
        self.assertEqual(len(brain.cables), 4)
        self.assertEqual(boss.vulnerability, 0.0)
        passo(match, 80)
        self.assertGreaterEqual(boss.hp, boss.max_hp * 0.5 - 1)          # FIREWALL segura
        iara = brain.iara
        self.assertLess(iara.vulnerability, 1.0)
        for c in brain.cables:
            c.hp = 0
        passo(match, 12)
        self.assertGreater(iara.vulnerability, 1.0)                       # IARA exposta
        iara.hp = 0
        passo(match, 12)
        self.assertEqual(brain.stage, 3)
        self.assertTrue(brain.enraged)
        passo(match, 90)
        pancada(match, boss, 0.1)
        self.assertEqual(brain.stage, 4)
        self.assertTrue(boss.alive_in_match)
        passo(match, 700)
        self.assertEqual(len(brain.allies), 3)
        self.assertIsNotNone(brain.plug)
        self.assertTrue(boss.stunned)
        p = match.players[0]
        p.x, p.y = brain.plug.x, brain.plug.y + 30
        self.assertTrue(match.interact(p))
        passo(match, 20)
        self.assertFalse(boss.alive_in_match)
        self.assertTrue(match.slain_boss)

    def test_chefe_aparece_e_luta(self):
        random.seed(2)
        match = masmorra("mansao_gabinete", 3)
        match.wave = -1
        match._start_wave(0)
        passo(match, 200)
        self.assertIsNotNone(match.boss)
        self.assertEqual(match.boss.stats.key, "cauanzera_corrompido")
        hp = sum(f.hp for f in match.players)
        passo(match, 500)
        self.assertLess(sum(f.hp for f in match.players), hp)


if __name__ == "__main__":
    unittest.main()


class CreditosTest(unittest.TestCase):
    def test_creditos_tem_o_elenco_e_acabam_sozinhos(self):
        from soulstrike.scenes.campaign import CAST, CreditsScene
        names = [n for _, n, _ in CAST]
        self.assertIn("Cauã Pedrozo Brito", names)
        self.assertIn("João Francisco da Silva Malaquias", names)
        g = game()
        g.session = Session("campaign", [SlotSetup(1, char=0)])
        done = []
        scene = CreditsScene(g, lambda: done.append(True) or scene)
        g.change = lambda nxt: done.append(nxt)
        try:
            for _ in range(6000):
                scene.update()
                if done:
                    break
        finally:
            del g.change                  # volta o método de verdade (o jogo é o mesmo nos testes)
        self.assertTrue(done)
        scene.draw(g.screen)


class RecompensasTest(ProgressoTest):
    """Etapa 4: o que zerar o capítulo 4 libera."""

    def test_cauanzera_corrompido_jogavel(self):
        from soulstrike.data import SHADOW_CHARACTERS, UNLOCKABLES
        self.assertEqual(UNLOCKABLES["cauanzera_corrompido"], 4)
        self.assertIn("cauanzera_corrompido", SHADOW_CHARACTERS)
        self.assertIn("cauanzera_corrompido", KEYS)

    def test_mapas_de_cuiabrasa_so_depois_de_zerar(self):
        from soulstrike.arena import CUIABRASA_MAPS, MAPS_BY_KEY, basket_maps, battle_maps, soccer_maps
        for key in CUIABRASA_MAPS:
            self.assertIn(key, MAPS_BY_KEY)
        antes = {m.key for m in battle_maps()} | set(basket_maps()) | set(soccer_maps())
        self.assertFalse(antes & set(CUIABRASA_MAPS))
        progress.record_campaign(900, "normal", 1)
        depois = {m.key for m in battle_maps()} | set(basket_maps()) | set(soccer_maps())
        self.assertEqual(depois & set(CUIABRASA_MAPS), set(CUIABRASA_MAPS))

    def test_futebol_joga_no_campo_de_cuiabrasa(self):
        from soulstrike.matches import SoccerMatch
        g = game()
        g.session = Session("soccer1", [SlotSetup(1, char=0), SlotSetup(2, char=1, cpu=True)])
        g.session.map_key = "campo_cuiabrasa"
        match = SoccerMatch(g, g.session)
        self.assertEqual(match.arena.cfg.key, "campo_cuiabrasa")
        passo(match, 30)

    def test_selos_por_dificuldade(self):
        self.assertEqual(progress.seals(), set())
        progress.record_campaign(900, "dificil", 2)
        self.assertEqual(progress.seals(), {"dificil"})
        self.assertTrue(progress.record_rush("ibrahim"))
        self.assertFalse(progress.record_rush("ibrahim"))
        self.assertEqual(progress.rush_seals(), {"ibrahim"})

    def test_reuniao_dos_corrompidos_passa_pelos_4_chefes(self):
        from soulstrike.campaign import RUSH_PHASES
        self.assertEqual(len(RUSH_PHASES), 4)
        run = CampaignRun(Session("campaign", [SlotSetup(1, char=0)], rush=True))
        run.start_rush()
        seen = [run.phase_index]
        while not run.rush_last:
            run.next_rush()
            seen.append(run.phase_index)
        self.assertEqual(seen, list(RUSH_PHASES))
        self.assertEqual(PHASES[seen[-1]].dungeons[-1].boss, "cauanzera")
        self.assertEqual(run.start_chapter, 0)          # não conta recorde

    def test_menu_extras_depois_de_zerar(self):
        from soulstrike.scenes.menus import ModeScene
        g = game()
        progress.record_campaign(900, "normal", 1)
        todos = [m for _, ms in ModeScene(g).modes_of("campanha") for m in ms]
        self.assertIn("reuniao", todos)
        self.assertIn("cinema", todos)

    def test_cinema_abre(self):
        from soulstrike.scenes.campaign import CINEMA, CinemaScene
        self.assertTrue(all(key in STORY or key == "creditos" for _, keys in CINEMA for key in keys))
        g = game()
        g.session = Session("campaign", [SlotSetup(1, char=0)])
        scene = CinemaScene(g)
        scene.update()
        scene.draw(g.screen)

    def test_uniforme_nas_regras_e_no_desenho(self):
        from soulstrike import settings
        from soulstrike.fighter import draw_uniform
        self.assertFalse(progress.uniform_on())
        settings.change("uniforme", True)
        try:
            self.assertFalse(progress.uniform_on())     # só depois do capítulo 4
            progress.record_campaign(900, "normal", 1)
            self.assertTrue(progress.uniform_on())
            m = masmorra()
            self.assertTrue(all(f.uniform for f in m.players))
            self.assertFalse(any(e.uniform for e in m.alive_enemies))
            m.draw(game().screen, game().ui)
            import pygame
            surf = pygame.Surface((80, 120), pygame.SRCALPHA)
            for d in ("frente", "costas", "direita", "esquerda"):
                draw_uniform(surf, pygame.Rect(10, 10, 60, 100), d)
        finally:
            settings.change("uniforme", False)

    def test_iara_mascote_nos_acampamentos(self):
        from soulstrike.fase import PhaseMatch
        from soulstrike.mansao import IaraMascot
        g = game()
        g.session = Session("campaign", [SlotSetup(1, char=0)])
        run = CampaignRun(g.session)
        run.begin_phase()
        match = PhaseMatch(g, run)
        self.assertFalse(any(isinstance(e, IaraMascot) for e in match.effects))
        progress.record_campaign(900, "normal", 1)
        match = PhaseMatch(g, run)
        mascot = [e for e in match.effects if isinstance(e, IaraMascot)]
        self.assertEqual(len(mascot), 1)
        self.assertTrue(mascot[0].frames)
        for _ in range(700):
            match.update()
        self.assertIn(mascot[0], match.effects)
        self.assertLess(abs(mascot[0].x - match.players[0].x), 120)
        match.draw(g.screen, g.ui)
