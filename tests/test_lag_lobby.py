"""Capítulo 2 da campanha (Lag Lobby): inimigos da Patrulha Cinza, laser e vento, o chefão Borba Jr
Corrompido, as armas novas, o caminho entre os capítulos e o Borba Jr Corrompido liberado."""
import random
import unittest

from apoio import FakeInput, game

from soulstrike import gadgets, progress
from soulstrike.boss import BORBA_STATS, BorbaBossAI
from soulstrike.campaign import (CHAPTER2_SOULS, CHAPTER_START, DUNGEON_1, DUNGEON_2, PHASES, CampaignMatch,
                                 CampaignRun)
from soulstrike.data import CHARACTERS, RARE_WEAPONS, roster
from soulstrike.enemies import AimLine
from soulstrike.hazards import Beam, LaserGrid, Wind
from soulstrike.session import Session, SlotSetup

KEYS = [c.key for c in CHARACTERS]
FASE = {p.key: i for i, p in enumerate(PHASES)}


def corrida(phase="recepcao", stage=DUNGEON_1, chars=("guerreiro", "atirador")):
    g = game()
    g.session = Session("campaign", [SlotSetup(i + 1, char=KEYS.index(c)) for i, c in enumerate(chars)])
    run = CampaignRun(g.session)
    run.phase_index = FASE[phase]
    run.begin_phase()
    run.stage = stage
    return g, run


def masmorra(phase="recepcao", stage=DUNGEON_1, relic=None, waves=False):
    g, run = corrida(phase, stage)
    if relic:
        run.relics[1] = relic
        run.held[1] = 2
    match = CampaignMatch(g, run)
    match.state, match.state_timer, match.banner = "fight", 0, None
    if not waves:
        match.wave = len(match.waves) - 1         # sem ondas novas atrapalhando
    else:
        match.state = "between"                   # o perigo continua entre as ondas
    for f in match.players:
        match.controllers[f] = FakeInput()
        f.max_hp = f.hp = 99999
    return match


def inimigo(match, kind, x, y):
    match._spawn(kind, x, y)
    return match.enemies[-1]


def passo(match, frames):
    for _ in range(frames):
        match.update()


class CapituloTest(unittest.TestCase):
    def test_tres_fases_no_capitulo_2(self):
        cap2 = [p.key for p in PHASES if p.chapter == 2]
        self.assertEqual(cap2, ["recepcao", "datacenter", "cobertura"])
        self.assertEqual(PHASES[CHAPTER_START[2]].key, "recepcao")

    def test_templo_fecha_o_capitulo_1(self):
        g, run = corrida("recepcao")
        run.phase_index = CHAPTER_START[2] - 1
        self.assertTrue(run.chapter_end)
        run.phase_index = FASE["cobertura"]
        self.assertTrue(run.last_phase)
        self.assertFalse(run.chapter_end)

    def test_comecar_no_capitulo_2_compensa(self):
        g, run = corrida()
        run.phase_index = 0
        before = {s: run.souls[s] for s in run.slots}
        run.start_at_chapter(2)
        self.assertEqual(run.phase_index, CHAPTER_START[2])
        self.assertEqual(run.start_chapter, 2)
        for s in run.slots:
            self.assertEqual(run.souls[s], before[s] + CHAPTER2_SOULS)
            self.assertGreaterEqual(len(run.upgrades[s]), 2)

    def test_chefao_e_perigos_nas_masmorras_certas(self):
        self.assertEqual(PHASES[FASE["datacenter"]].dungeons[0].hazard, "laser")
        self.assertEqual(PHASES[FASE["cobertura"]].dungeons[0].hazard, "vento")
        self.assertEqual(PHASES[FASE["cobertura"]].dungeons[1].boss, "borba")


class InimigosTest(unittest.TestCase):
    def test_todos_aparecem_e_lutam(self):
        match = masmorra()
        p = match.players[0]
        for k, kind in enumerate(("drone", "miliciano", "torreta", "miliciano_exo")):
            inimigo(match, kind, p.x + 200 + k * 60, p.y)
        hp = sum(f.hp for f in match.players)
        passo(match, 400)
        self.assertLess(sum(f.hp for f in match.players), hp)      # alguém levou dano

    def test_torreta_mira_antes_de_atirar(self):
        match = masmorra()
        p = match.players[0]
        inimigo(match, "torreta", p.x + 250, p.y)
        seen = False
        for _ in range(240):
            match.update()
            seen = seen or any(isinstance(e, AimLine) for e in match.effects)
        self.assertTrue(seen)


class PerigosTest(unittest.TestCase):
    def test_laser_avisa_e_depois_queima(self):
        match = masmorra("datacenter", waves=True)
        self.assertIsInstance(match.hazard, LaserGrid)
        match.hazard.timer = 9999
        p = match.players[0]
        match.hazard.beams = [Beam("h", p.y, match.arena.width)]
        hp = p.hp
        passo(match, Beam.WARN - 2)
        self.assertEqual(p.hp, hp)                                # só o aviso, ainda não doeu
        passo(match, 10)
        self.assertLess(p.hp, hp)

    def test_vento_empurra_e_parede_protege(self):
        match = masmorra("cobertura", waves=True)
        wind = match.hazard
        self.assertIsInstance(wind, Wind)
        wind.dir = (1.0, 0.0)
        wind.state, wind.timer = "blow", Wind.BLOW
        p = match.players[0]
        x0 = p.x
        for _ in range(60):
            if not wind.sheltered(p):
                match.update()
        if not wind.sheltered(p):
            self.assertGreater(p.x, x0 + 20)
        wind.sheltered = lambda f: True
        x1 = p.x
        p.steer(0, 0)
        wind.update(match)
        self.assertAlmostEqual(p.x, x1, delta=0.01)


class ChefaoTest(unittest.TestCase):
    def _chefe(self):
        match = masmorra("cobertura", DUNGEON_2)
        match._spawn("chefe", 800, 330)
        return match, match.boss, match.controllers[match.boss]

    def test_e_o_borba(self):
        match, boss, ai = self._chefe()
        self.assertIsInstance(ai, BorbaBossAI)
        self.assertGreaterEqual(BORBA_STATS.max_hp, 1500)

    def test_canhao_mostra_a_linha_e_atira(self):
        match, boss, ai = self._chefe()
        match.players[0].x, match.players[0].y = 800, 800
        ai.combo = ["cannon"]
        ai._next(boss, match)
        self.assertTrue(any(isinstance(e, AimLine) for e in match.effects))
        n = len(match.bullets)
        shot = False
        for _ in range(BorbaBossAI.WINDUPS["cannon"] + 10):
            match.update()
            shot = shot or len(match.bullets) > n
        self.assertTrue(shot)

    def test_terceiro_soco_abre_onda(self):
        from soulstrike.enemies import Shockwave
        match, boss, ai = self._chefe()
        match.players[0].x, match.players[0].y = 800, 460
        ai.combo = ["punch"]
        ai._next(boss, match)
        wave = False
        for _ in range(200):
            match.update()
            wave = wave or any(isinstance(e, Shockwave) for e in match.effects)
        self.assertTrue(wave)

    def test_luta_inteira_sem_erro(self):
        match, boss, ai = self._chefe()
        random.seed(3)
        passo(match, 1500)


class ArmasTest(unittest.TestCase):
    def _arma(self, key, phase):
        match = masmorra(phase, relic=key)
        p = match.players[0]
        p.weapon_index = next(i for i, w in enumerate(p.weapons) if w.name == RARE_WEAPONS[key].name)
        return match, p

    def test_rede_prende(self):
        match, p = self._arma("taser_rede", "recepcao")
        e = inimigo(match, "miliciano", p.x + 120, p.y)
        match.controllers.pop(e)
        shot = gadgets.NetShot(p, p.weapon, p.x, p.y, 1, 0, 10, 5)
        shot.on_hit(e, match)
        self.assertGreater(e.root_timer, 0)

    def test_plasma_carregado_atravessa(self):
        match, p = self._arma("rifle_plasma", "datacenter")
        shot = gadgets.PlasmaShot(p, p.weapon, p.x, p.y, 1, 0, 10, 5, power=1.0)
        self.assertEqual(shot.pierce, 99)

    def test_drone_de_bolso_solta_aliado(self):
        match, p = self._arma("drone_bolso", "datacenter")
        match.spawn_projectile(p, p.weapon, (1.0, 0.0), 6)
        self.assertTrue(any(isinstance(e, gadgets.AllyDrone) for e in match.effects))

    def test_teclado_terceiro_golpe_solta_teclas(self):
        match, p = self._arma("teclado_mecanico", "recepcao")
        n = len(match.bullets)
        for _ in range(3):
            gadgets.on_melee(p, p.weapon, match, 13)
        self.assertGreaterEqual(len(match.bullets) - n, 5)

    def test_escudo_empurra_ao_soltar(self):
        match, p = self._arma("escudo_choque", "datacenter")
        e = inimigo(match, "miliciano", p.x + 50, p.y)
        match.controllers.pop(e)
        p.facing = (1.0, 0.0)
        for _ in range(gadgets.GUARD_FULL):
            gadgets.shield_hold(p, match)
        hp = e.hp
        gadgets.shield_release(p, match)
        self.assertLess(e.hp, hp)
        self.assertGreater(e.knock[0], 0)


class DesbloqueioTest(unittest.TestCase):
    def setUp(self):
        self._old = progress.load()
        progress.save({})

    def tearDown(self):
        progress.save(self._old)

    def test_borba_corrompido_libera_no_fim_do_capitulo_2(self):
        keys = lambda: {c.key for c in roster()}
        self.assertNotIn("borba_corrompido", keys())
        self.assertTrue(progress.record_chapter1())
        self.assertIn("aryel_corrompido", keys())
        self.assertNotIn("borba_corrompido", keys())
        record, unlocked = progress.record_campaign(3600, "normal", 2)
        self.assertTrue(unlocked)
        self.assertIn("borba_corrompido", keys())

    def test_quem_comecou_no_capitulo_2_nao_bate_recorde(self):
        record, _ = progress.record_campaign(10, "normal", 1, full=False)
        self.assertFalse(record)
        self.assertIsNone(progress.best_time("normal"))


if __name__ == "__main__":
    unittest.main()
