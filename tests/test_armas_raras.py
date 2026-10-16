"""Armas raras de cada fase da campanha (o baú de cada fase tem as suas; as do Templo Gelado, a
última fase, são as roubadas) e o chefão mais difícil."""
import math
import unittest

from apoio import FakeInput, game

from soulstrike import projectiles as P
from soulstrike import weapon_art
from soulstrike.boss import ARMOR, BOSS_STATS, BossAI
from soulstrike.campaign import DUNGEON_1, DUNGEON_2, PHASES, CampaignMatch, CampaignRun, LobbyMatch, LOBBY_BACK
from soulstrike.data import CHARACTERS, PHASE_RELICS, RARE_WEAPONS
from soulstrike.session import Session, SlotSetup

KEYS = [c.key for c in CHARACTERS]
NOVAS = {"colmeia": P.Beehive, "arco_espinhos": P.Thorn, "lanterna": P.SoulBeam, "cranio": P.Skull,
         "foice_espectral": P.SpectralScythe, "estalactites": P.Icicles, "espelho": P.CrystalBeam,
         "bola_neve": P.Snowball, "raio_supremo": P.SupremeLightning}


def corrida(chars=("guerreiro", "atirador"), phase=0, stage=DUNGEON_1):
    g = game()
    g.session = Session("campaign", [SlotSetup(i + 1, char=KEYS.index(c)) for i, c in enumerate(chars)])
    run = CampaignRun(g.session)
    run.phase_index = phase
    run.begin_phase()
    run.stage = stage
    return g, run


def campo(weapon_key, phase=0):
    g, run = corrida(phase=phase)
    run.relics[1] = weapon_key
    run.held[1] = 2
    match = CampaignMatch(g, run)
    match.state, match.state_timer, match.banner = "fight", 0, None
    for f in match.players:
        match.controllers[f] = FakeInput()
    p1 = match.players[0]
    p1.x, p1.y = 400, 600 if phase == 0 else 340          # linha sem paredes no mapa
    return match, p1


def inimigo(match, kind, x, y):
    match._spawn(kind, x, y)
    e = match.enemies[-1]
    match.controllers.pop(e)
    return e


def passo(match, frames):
    for _ in range(frames):
        match._update_bullets()
        for eff in list(match.effects):
            eff.update(match)
        match.effects = [e for e in match.effects if e.alive]
        for f in match.fighters:
            f.update(match)


class BauPorFaseTest(unittest.TestCase):
    def test_cada_fase_tem_a_sua_lista(self):
        self.assertEqual([ph.key for ph in PHASES], list(PHASE_RELICS))
        todas = [k for ks in PHASE_RELICS.values() for k in ks]
        self.assertEqual(len(todas), len(set(todas)))                 # nenhuma repete entre as fases
        self.assertTrue(all(RARE_WEAPONS[k].roubada for k in PHASE_RELICS["templo"]))
        self.assertFalse(any(RARE_WEAPONS[k].roubada for k in PHASE_RELICS["floresta"] + PHASE_RELICS["calabouco"]))

    def test_bau_sorteia_da_fase(self):
        for i, ph in enumerate(PHASES):
            g, run = corrida(chars=("guerreiro", "atirador", "ninja", "geada"), phase=i, stage=LOBBY_BACK)
            match = LobbyMatch(g, run)
            match.launch_relics(match.chest)
            dados = [d.weapon for d in match.props if d.__class__.__name__ == "RelicDrop"]
            self.assertEqual(len(dados), 4)
            self.assertTrue(all(w in [RARE_WEAPONS[k] for k in PHASE_RELICS[ph.key]] for w in dados), ph.key)
            self.assertEqual(len(set(map(id, dados))), 4)                # todos diferentes

    def test_todas_tem_projetil_arte_e_texto(self):
        for key in [k for ks in PHASE_RELICS.values() for k in ks]:
            w = RARE_WEAPONS[key]
            self.assertIsNotNone(weapon_art.icon(w.name), key)
            self.assertTrue(w.note, key)
            if not w.is_melee:
                self.assertIsNot(P.projectile_class(w.style), P.Projectile, key)
        for key, cls in NOVAS.items():
            match, p1 = campo(key)
            proj = match.spawn_projectile(p1, p1.weapon, (1.0, 0.0), 10, None)
            self.assertIsInstance(proj, cls, key)


class FlorestaTest(unittest.TestCase):
    def test_colmeia_solta_enxame_que_pica(self):
        match, p1 = campo("colmeia")
        e = inimigo(match, "golem", 640, 600)
        hp = e.hp
        match.spawn_projectile(p1, p1.weapon, (1.0, 0.0), 6, e)
        passo(match, 150)
        self.assertTrue(any(isinstance(x, P.Swarm) for x in match.effects))
        self.assertLess(e.hp, hp - 6)

    def test_espinhos_em_leque_enraizam(self):
        match, p1 = campo("arco_espinhos")
        e = inimigo(match, "esqueleto", 600, 600)
        n = len(match.bullets)
        match.spawn_projectile(p1, p1.weapon, (1.0, 0.0), 7, e)
        self.assertEqual(len(match.bullets) - n, 3)
        passo(match, 30)
        self.assertGreater(e.root_timer, 0)

    def test_machado_acerta_em_volta(self):
        match, p1 = campo("machado")
        p1.weapon_index = 2
        front = inimigo(match, "esqueleto", 450, 600)
        back = inimigo(match, "esqueleto", 350, 600)
        hf, hb = front.hp, back.hp
        p1.facing = (1.0, 0.0)
        p1.attack(match, front)
        self.assertLess(front.hp, hf)
        self.assertLess(back.hp, hb)                                   # o de trás também


class CalabocoTest(unittest.TestCase):
    def test_lanterna_suga_vida(self):
        match, p1 = campo("lanterna", phase=1)
        e = inimigo(match, "golem", 600, p1.y)
        p1.hp -= 40
        hp1, hpe = p1.hp, e.hp
        for _ in range(60):
            p1.attack(match, e)
            p1.update(match)
            match._update_bullets()
        self.assertLess(e.hp, hpe)
        self.assertGreater(p1.hp, hp1)

    def test_cranio_da_medo(self):
        match, p1 = campo("cranio", phase=1)
        e = inimigo(match, "esqueleto", 650, p1.y)
        match.spawn_projectile(p1, p1.weapon, (1.0, 0.0), 14, e)
        passo(match, 60)
        self.assertGreater(e.fear_timer, 0)
        x0 = e.x
        e.steer(-1.0, 0.0)                                             # tenta vir para cima
        passo(match, 20)
        self.assertGreater(e.x, x0)                                    # mas foge
        self.assertFalse(e.attack(match, p1))

    def test_foice_atravessa_parede_e_volta(self):
        match, p1 = campo("foice_espectral", phase=1)
        b = match.spawn_projectile(p1, p1.weapon, (1.0, 0.0), 16, None)
        self.assertTrue(b.ghost)
        far = 0
        for _ in range(200):
            match._update_bullets()
            far = max(far, b.x - p1.x)
            if not b.alive:
                break
        self.assertGreater(far, 150)
        self.assertFalse(b.alive)


class TemploRoubadasTest(unittest.TestCase):
    def test_estalactites_caem_em_linha_e_congelam(self):
        match, p1 = campo("estalactites", phase=2)
        es = [inimigo(match, "esqueleto", 400 + 90 + k * 140, p1.y) for k in range(3)]
        hps = [e.hp for e in es]
        match.spawn_projectile(p1, p1.weapon, (1.0, 0.0), 30, None)
        passo(match, 70)
        self.assertTrue(all(e.hp < hp for e, hp in zip(es, hps)))
        self.assertTrue(any(e.frozen_timer > 0 for e in es if e.alive_in_match))

    def test_espelho_reflete_e_atravessa(self):
        match, p1 = campo("espelho", phase=2)
        a = inimigo(match, "golem", 520, p1.y)
        b = inimigo(match, "golem", 640, p1.y)
        ha, hb = a.hp, b.hp
        match.spawn_projectile(p1, p1.weapon, (1.0, 0.0), 26, None)
        passo(match, 2)
        self.assertLess(a.hp, ha)
        self.assertLess(b.hp, hb)
        beam = next(x for x in match.effects if isinstance(x, P.BeamFx))
        self.assertGreaterEqual(len(beam.points), 3)                   # refletiu pelo menos uma vez

    def test_bola_de_neve_cresce_arrasta_e_explode(self):
        match, p1 = campo("bola_neve", phase=2)
        e = inimigo(match, "esqueleto", 470, p1.y)
        hp = e.hp
        b = match.spawn_projectile(p1, p1.weapon, (1.0, 0.0), 12, None)
        x0 = e.x
        passo(match, 30)
        self.assertGreater(b.radius, 10)
        self.assertGreater(e.x, x0 + 40)                               # foi arrastado
        passo(match, 80)
        self.assertLess(e.hp, hp)

    def test_raio_supremo_pula_em_cinco(self):
        match, p1 = campo("raio_supremo", phase=2)
        es = [inimigo(match, "diabrete", 560 + k * 120, p1.y + (k % 2) * 40) for k in range(5)]
        hps = [e.hp for e in es]
        p1.attack_cd = 0
        p1.attack(match, es[0])
        match._update_bullets()
        self.assertTrue(all(e.hp < hp for e, hp in zip(es, hps)))


class ChefaoTest(unittest.TestCase):
    def _chefe(self):
        g, run = corrida(phase=len(PHASES) - 1, stage=DUNGEON_2)
        match = CampaignMatch(g, run)
        match.state, match.state_timer, match.banner = "fight", 0, None
        match.wave = len(match.waves) - 1
        match._spawn("chefe", 800, 330)
        return match, match.boss, match.controllers[match.boss]

    def test_mais_vida(self):
        self.assertGreaterEqual(BOSS_STATS.max_hp, 1500)

    def test_investida_sombria(self):
        match, boss, ai = self._chefe()
        for p in match.players:
            p.max_hp = p.hp = 99999
        p = match.players[0]
        p.x, p.y = 800, 800
        ai.combo = ["dash"]
        ai._next(boss, match)
        self.assertEqual(ai.state, "dash")
        y0 = boss.y
        seen = set()
        for _ in range(140):
            match.update()
            seen.add(ai.state)
        self.assertIn("dashing", seen)
        self.assertGreater(boss.y, y0 + 150)                           # atravessou em direção ao jogador

    def test_armadura_de_sombra_furioso(self):
        match, boss, ai = self._chefe()
        ai.enraged = True
        ai._set(boss, "walk", 50)
        hp = boss.hp
        boss.take_damage(100, match=match)
        self.assertEqual(hp - boss.hp, round(100 * ARMOR))
        ai._set(boss, "tired", 50)
        hp = boss.hp
        boss.take_damage(10, match=match)
        self.assertEqual(hp - boss.hp, 16)                             # cansado: a armadura quebra

    def test_chama_alma_corrompida(self):
        match, boss, ai = self._chefe()
        boss.hp = boss.max_hp // 2 - 1
        for _ in range(3):
            match.update()
        self.assertTrue(any(p.kind.startswith("sombra:") for p in match.portals))


if __name__ == "__main__":
    unittest.main()
