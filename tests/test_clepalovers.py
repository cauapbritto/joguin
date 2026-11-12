"""Capítulo 3 da campanha (Clínica Clepalovers): monstros da clínica, a Daiwone, o piso molhado, o
laser em grade e o vapor, o chefe Albeguinio Corrompido, o caminho entre os capítulos e o
Albeguinio Corrompido liberado."""
import random
import unittest

from apoio import FakeInput, game

from soulstrike import progress
from soulstrike.abilities import ABILITIES
from soulstrike.boss import AlbeguinioBossAI, CableLink
from soulstrike.campaign import CHAPTER_START, DUNGEON_1, DUNGEON_2, PHASES, STORY, CampaignMatch, CampaignRun
from soulstrike.clinica import DAIWONE_HITS, DAIWONE_SOULS, ClayPuddle, Notice, Stamp
from soulstrike.data import CHARACTERS, SHADOW_CHARACTERS, UNLOCKABLES, roster
from soulstrike.hazards import LaserTiles, Steam, WetFloor
from soulstrike.matches import BattleMatch
from soulstrike.session import Session, SlotSetup

KEYS = [c.key for c in CHARACTERS]
FASE = {p.key: i for i, p in enumerate(PHASES)}
CLINICA = ("mascara_argila", "seringuinha", "rolinho_jade", "toalha_fantasma", "esteti_bot", "cadeira",
           "espelho_vivo", "grampeador", "maquina")


def corrida(phase="clinica_recepcao", stage=DUNGEON_1, chars=("guerreiro", "atirador")):
    g = game()
    g.session = Session("campaign", [SlotSetup(i + 1, char=KEYS.index(c)) for i, c in enumerate(chars)])
    run = CampaignRun(g.session)
    run.phase_index = FASE[phase]
    run.begin_phase()
    run.stage = stage
    return g, run


def masmorra(phase="clinica_recepcao", stage=DUNGEON_1, waves=False, chars=("guerreiro", "atirador")):
    g, run = corrida(phase, stage, chars)
    match = CampaignMatch(g, run)
    match.state, match.state_timer, match.banner = "fight", 0, None
    if not waves:
        match.wave = len(match.waves) - 1         # sem ondas novas atrapalhando
    else:
        match.state = "between"
    for f in match.players:
        match.controllers[f] = FakeInput()
        f.max_hp = f.hp = 99999
    return match


def passo(match, frames):
    for _ in range(frames):
        match.update()


def bater(match, e, who=None):
    who = who or match.players[0]
    e.take_damage(5, who.x, who.y, attacker=who, match=match)
    e.stun_timer = 0


class CapituloTest(unittest.TestCase):
    def test_tres_fases_no_capitulo_3(self):
        cap3 = [p.key for p in PHASES if p.chapter == 3]
        self.assertEqual(cap3, ["clinica_recepcao", "procedimentos", "suite_vip"])
        self.assertEqual(PHASES[CHAPTER_START[3]].key, "clinica_recepcao")
        self.assertEqual(PHASES[FASE["suite_vip"]].dungeons[-1].boss, "albeguinio")

    def test_cobertura_fecha_o_capitulo_2(self):
        g, run = corrida()
        run.phase_index = FASE["cobertura"]
        self.assertTrue(run.chapter_end)
        run.phase_index = FASE["suite_vip"]          # o capítulo 3 também fecha: depois vem a Mansão
        self.assertFalse(run.last_phase)
        self.assertTrue(run.chapter_end)

    def test_comecar_no_capitulo_3_compensa_mais(self):
        g, run = corrida()
        run.phase_index = 0
        before = {s: run.souls[s] for s in run.slots}
        run.start_at_chapter(3)
        self.assertEqual(run.phase.key, "clinica_recepcao")
        for s in run.slots:
            self.assertGreater(run.souls[s], before[s])
            self.assertEqual(len(run.upgrades[s]), 4)

    def test_historia_de_cada_fase(self):
        for p in PHASES:
            self.assertIn(p.key, STORY)
        self.assertIn("fim_capitulo2", STORY)
        final = " ".join(text for _, _, text in STORY["fim_capitulo3"][2])
        self.assertIn("fechou o caixa", final)

    def test_perigos_e_daiwone_nas_masmorras_certas(self):
        rooms = {d.map_key: d for p in PHASES if p.chapter == 3 for d in p.dungeons}
        self.assertEqual(rooms["clinica_espera"].hazard, "piso_molhado")
        self.assertEqual(rooms["clinica_laser"].hazard, "laser_grade")
        self.assertEqual(rooms["clinica_spa"].hazard, "vapor")
        self.assertEqual({k for k, d in rooms.items() if d.daiwone},
                         {"clinica_espera", "clinica_spa", "clinica_espelhos"})


class MonstrosTest(unittest.TestCase):
    def test_todos_aparecem_e_lutam(self):
        random.seed(5)
        match = masmorra()
        p = match.players[0]
        for k, kind in enumerate(CLINICA):
            match._spawn(kind, 300 + (k % 5) * 220, 400 + (k // 5) * 400)
        hp = sum(f.hp for f in match.players)
        passo(match, 600)
        self.assertLess(sum(f.hp for f in match.players), hp)
        self.assertTrue(p.alive_in_match)

    def test_botox_congela_a_habilidade(self):
        match = masmorra()
        p = match.players[0]
        e = match.spawn_now("seringuinha", p.x + 200, p.y)
        p.ability_cd = 0
        match.spawn_projectile(e, e.weapon, e.direction_to(p), 5)
        for _ in range(80):
            match.update()
            if p.botox_timer:
                break
        self.assertGreater(p.botox_timer, 0)
        self.assertGreater(p.ability_cd, 60)

    def test_cadeira_puxa_e_bater_solta(self):
        match = masmorra()
        p = match.players[0]
        chair = match.spawn_now("cadeira", p.x + 180, p.y)
        brain = match.controllers[chair]
        brain.dir = chair.direction_to(p)
        brain._grab(chair, match)
        self.assertIs(brain.held, p)
        self.assertGreater(p.root_timer, 0)
        for _ in range(brain.RELEASE):
            bater(match, chair)
            match.update()
        passo(match, 2)
        self.assertIsNone(brain.held)

    def test_espelho_solta_reflexo(self):
        match = masmorra()
        p = match.players[0]
        mirror = match.spawn_now("espelho_vivo", p.x + 300, p.y)
        brain = match.controllers[mirror]
        brain._reflect(mirror, match)
        copy = brain.copy
        self.assertTrue(copy.kind.startswith("reflexo:"))
        self.assertLess(copy.max_hp, p.stats.max_hp)
        passo(match, 120)

    def test_maquina_solta_no_maximo_dois(self):
        match = masmorra()
        p = match.players[0]
        machine = match.spawn_now("maquina", p.x + 400, p.y)
        brain = match.controllers[machine]
        for _ in range(6):
            brain.cd = 0
            passo(match, brain.WINDUP + 4)
        self.assertLessEqual(len([e for e in brain.made if e.alive_in_match]), 2)
        self.assertGreaterEqual(len(brain.made), 1)


class DaiwoneTest(unittest.TestCase):
    def _daiwone(self):
        match = masmorra()
        p = match.players[0]
        self.blocker = match.spawn_now("cabo", 1450, 1050)       # segura a sala (a Daiwone não conta)
        d = match.spawn_now("daiwone", p.x + 300, p.y)
        d.max_hp = d.hp = 9999
        return match, d, match.controllers[d]

    def test_digita_e_manda_o_oi_sumido(self):
        match, d, brain = self._daiwone()
        brain.cd = 0
        passo(match, brain.TYPE + 10)
        self.assertTrue(match.notices)
        self.assertIsInstance(match.notices[0], Notice)
        self.assertEqual(match.notices[0].text, "oi sumido")

    def test_bater_cancela_a_digitacao(self):
        match, d, brain = self._daiwone()
        brain.cd = 0
        passo(match, 10)
        self.assertGreater(brain.typing, 0)
        bater(match, d)
        passo(match, brain.TYPE + 10)
        self.assertFalse(match.notices)

    def test_tres_acertos_ela_foge_com_almas(self):
        match, d, brain = self._daiwone()
        p = match.players[0]
        before = match.run.wallet(p.slot)
        for _ in range(DAIWONE_HITS):
            bater(match, d, p)
            passo(match, 2)
        self.assertTrue(brain.leaving)
        self.assertEqual(match.run.wallet(p.slot), before + DAIWONE_SOULS)
        passo(match, 90)
        self.assertNotIn(d, match.enemies)
        self.assertNotIn(d, match.fighters)

    def test_nao_segura_a_sala(self):
        match, d, brain = self._daiwone()
        self.blocker.hp = 0
        passo(match, 1)
        self.assertEqual(match.fighting_enemies(), [])
        passo(match, 3)
        self.assertEqual(match.state, "clear")
        self.assertTrue(brain.leaving)

    def test_chega_no_meio_da_primeira_onda(self):
        g, run = corrida()
        match = CampaignMatch(g, run)
        for f in match.players:
            f.max_hp = f.hp = 99999
            match.controllers[f] = FakeInput()
        match._start_wave(0)
        match.state = "fight"
        self.assertIsNotNone(match.daiwone_at)
        match.daiwone_at = match.frame + 1
        passo(match, 3)
        self.assertIsNotNone(match.daiwone)


class PerigosTest(unittest.TestCase):
    def test_piso_molhado_escorrega(self):
        match = masmorra(waves=True)
        wet = match.hazard
        self.assertIsInstance(wet, WetFloor)
        p = match.players[0]
        x, y, r = wet.puddles[0]
        p.x, p.y = x, y
        wet.last[p] = (x - 3, y)
        wet.update(match)
        self.assertGreater(p.x, x)

    def test_laser_avisa_e_depois_queima(self):
        match = masmorra("procedimentos", waves=True)
        laser = match.hazard
        self.assertIsInstance(laser, LaserTiles)
        p = match.players[0]
        laser.lit, laser.age, laser.hit = [laser.cell_of(p)], 0, set()
        hp = p.hp
        passo(match, LaserTiles.WARN - 2)
        self.assertEqual(p.hp, hp)
        passo(match, 6)
        self.assertLess(p.hp, hp)

    def test_vapor_fecha_nos_registros(self):
        match = masmorra("procedimentos", DUNGEON_2, waves=True)
        steam = match.hazard
        self.assertIsInstance(steam, Steam)
        p = match.players[0]
        for valve in list(steam.valves):
            p.x, p.y = valve.x + 10, valve.y
            self.assertTrue(match.interact(p))
        self.assertFalse(steam.open_valves)
        passo(match, 200)
        self.assertLess(steam.density, 0.1)


class ChefeTest(unittest.TestCase):
    def _chefe(self):
        match = masmorra("suite_vip", DUNGEON_2)
        match._spawn("chefe", 800, 330)
        return match, match.boss, match.controllers[match.boss]

    def test_e_o_albeguinio(self):
        match, boss, ai = self._chefe()
        self.assertIsInstance(ai, AlbeguinioBossAI)

    def test_carimbo_marca_o_chao_antes(self):
        match, boss, ai = self._chefe()
        p = match.players[0]
        p.x, p.y = 800, 700
        ai.combo = ["carimbo"]
        ai._next(boss, match)
        stamps = [e for e in match.effects if isinstance(e, Stamp)]
        self.assertTrue(stamps)
        hp = p.hp
        passo(match, 120)
        self.assertLess(p.hp, hp)

    def test_agenda_solta_argila(self):
        match, boss, ai = self._chefe()
        ai.combo = ["agenda"]
        ai._next(boss, match)
        passo(match, AlbeguinioBossAI.WINDUPS["agenda"] + 4)
        self.assertTrue(any(isinstance(e, ClayPuddle) for e in match.effects))

    def test_harmonizacao_so_cai_cortando_os_cabos(self):
        match, boss, ai = self._chefe()
        boss.hp = boss.max_hp // 2 - 1
        passo(match, 3)
        self.assertTrue(ai.harmony)
        self.assertEqual(len(ai.cables), 3)
        self.assertTrue(any(isinstance(e, CableLink) for e in match.effects))
        self.assertLess(boss.vulnerability, 0.5)
        for cable in ai.cables:
            cable.hp = 0
        passo(match, 3)
        self.assertFalse(ai.harmony)

    def test_luta_inteira_sem_erro(self):
        match, boss, ai = self._chefe()
        random.seed(7)
        passo(match, 600)
        boss.hp = boss.max_hp // 2 - 1
        passo(match, 600)
        for cable in ai.cables:
            cable.hp = 0
        boss.hp = boss.max_hp // 6
        passo(match, 600)
        self.assertTrue(ai.enraged)


class LargarArmaTest(unittest.TestCase):
    """LARGAR ARMA é um comando próprio (LB, touchpad do PlayStation, R, botão do celular)."""

    def _apertar(self, match, p, action, frames=1):
        inp = match.controllers[p]
        inp.hold(action)
        for _ in range(frames):
            match.update()
            inp._pressed.clear()
        inp.release(action)
        match.update()

    def test_largar_tira_a_arma_rara(self):
        from soulstrike.data import RARE_WEAPONS
        match = masmorra()
        p = match.players[0]
        match.give_relic(p, RARE_WEAPONS["besta"])
        self.assertIs(p.weapon, RARE_WEAPONS["besta"])
        n = len(match.ground)
        self._apertar(match, p, "drop")
        self.assertNotIn(RARE_WEAPONS["besta"], p.weapons)
        self.assertNotIn("rara:besta", match.run.bags[p.slot])
        self.assertEqual(len(match.ground), n + 1)

    def test_arma_de_outro_sai_da_bolsa(self):
        match = masmorra()
        p = match.players[0]
        rifle = next(c for c in CHARACTERS if c.key == "atirador").weapons[0]
        match.give_common(p, rifle)
        self.assertIs(p.weapon, rifle)
        self._apertar(match, p, "drop")
        self.assertNotIn(rifle, p.weapons)
        self.assertEqual(p.base_weapons, p.stats.weapons)

    def test_segurar_trocar_so_troca(self):
        from soulstrike.data import RARE_WEAPONS
        match = masmorra()
        p = match.players[0]
        match.give_relic(p, RARE_WEAPONS["besta"])
        before = p.weapon_index
        self._apertar(match, p, "switch", 40)      # segurar TROCAR ARMA não larga mais
        self.assertNotEqual(p.weapon_index, before)
        self.assertIn(RARE_WEAPONS["besta"], p.weapons)

    def test_arma_propria_tambem_sai(self):
        match = masmorra()
        p = match.players[0]
        mine = p.weapon
        n = len(match.ground)
        self.assertTrue(match.drop_held(p))
        self.assertEqual(len(match.ground), n + 1)
        self.assertNotIn(mine, p.weapons)


class AlbeguinioCorrompidoTest(unittest.TestCase):
    def setUp(self):
        self._old = progress.load()
        progress.save({})

    def tearDown(self):
        progress.save(self._old)

    def test_libera_so_no_fim_do_capitulo_3(self):
        keys = lambda: {c.key for c in roster()}
        self.assertEqual(UNLOCKABLES["albeguinio_corrompido"], 3)
        self.assertIn("albeguinio_corrompido", SHADOW_CHARACTERS)
        self.assertTrue(progress.record_chapter(2))
        self.assertIn("borba_corrompido", keys())
        self.assertNotIn("albeguinio_corrompido", keys())
        record, unlocked = progress.record_campaign(5000, "normal", 2)
        self.assertTrue(unlocked)
        self.assertIn("albeguinio_corrompido", keys())

    def test_fechamento_do_mes_carimba_o_adversario(self):
        g = game()
        g.session = Session("duel", [SlotSetup(1, char=KEYS.index("albeguinio_corrompido")),
                                     SlotSetup(2, char=KEYS.index("atirador"))])
        match = BattleMatch(g, g.session)
        match.intro = 0
        a, b = match.fighters
        self.assertEqual(type(a.ability).__name__, "FechamentoDoMes")
        self.assertIn("albeguinio_corrompido", ABILITIES)
        a.x, a.y, b.x, b.y = 500, 600, 800, 600
        match.update()                                 # a arena acerta as posições
        hp = b.hp
        a.use_ability(match, b)
        self.assertEqual(len([e for e in match.effects if isinstance(e, Stamp)]), 3)
        for _ in range(80):
            match.update()
        self.assertLess(b.hp, hp)


if __name__ == "__main__":
    unittest.main()
