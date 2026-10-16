"""Campanha em masmorras: acampamento (lobby) com fogueira e entradas, masmorra 1, volta ao
acampamento com o baú escondido (armas raras), masmorra 2 e o teletransporte de fase."""
import unittest

from apoio import FakeInput, game

from soulstrike import projectiles as P
from soulstrike.arena import BATTLE_MAPS, MAPS_BY_KEY, Arena
from soulstrike.campaign import (DUNGEON_1, DUNGEON_2, LEAVE_FRAMES, LOBBY_BACK, PHASES, CampaignMatch, CampaignRun,
                                 LobbyMatch)
from soulstrike.data import CHARACTERS, RARE_WEAPONS
from soulstrike.dungeon import DONE_AT, Campfire
from soulstrike.lobbies import LOBBIES, parse
from soulstrike.session import Session, SlotSetup

KEYS = [c.key for c in CHARACTERS]


class _Input(FakeInput):
    def set_layout(self, name):
        pass


def corrida(chars=("guerreiro", "atirador"), phase=0, stage=0):
    g = game()
    slots = [SlotSetup(i + 1, char=KEYS.index(c)) for i, c in enumerate(chars)]
    g.session = Session("campaign", slots)
    run = CampaignRun(g.session)
    run.phase_index = phase
    run.begin_phase()
    run.stage = stage
    return g, run


def acampamento(chars=("guerreiro", "atirador"), phase=0, back=False):
    g, run = corrida(chars, phase, LOBBY_BACK if back else 0)
    match = LobbyMatch(g, run)
    inputs = {}
    for f in match.players:
        inputs[f.slot] = match.controllers[f] = _Input()
    return match, inputs


def passo(match, inputs, frames=1):
    for _ in range(frames):
        match.update()
        for inp in inputs.values():
            inp.end_frame()


def juntar(match, x, y):
    for k, p in enumerate(match.players):
        p.x, p.y = x - 15 + 30 * (k % 2), y + 30 * (k // 2)


class MapasTest(unittest.TestCase):
    def test_acampamentos_fechados_e_com_tudo(self):
        for theme, (name, rows) in LOBBIES.items():
            size, walls, void, markers = parse(rows)
            for ch, n in (("S", 4), ("a", 4), ("F", 4), ("C", 1), ("1", 2), ("2", 2)):
                self.assertEqual(len(markers.get(ch, ())), n, (theme, ch))
            arena = Arena(MAPS_BY_KEY[f"acampamento_{theme}"], game().assets)
            for x, y in markers["S"] + markers["a"] + markers["C"]:
                self.assertTrue(arena.is_free(x, y, 12), (theme, x, y))

    def test_variacoes_viram_arenas_do_duelo(self):
        keys = [m.key for m in BATTLE_MAPS]
        for key in ("floresta_ruinas", "calabouco_celas", "templo_patio"):
            self.assertIn(key, keys)
            arena = Arena(MAPS_BY_KEY[key], game().assets)
            for x, y in arena.cfg.spawns:
                self.assertTrue(arena.is_free(x, y, 16), (key, x, y))

    def test_masmorras_com_entrada_e_saida_livres(self):
        for phase in PHASES:
            self.assertEqual(len(phase.dungeons), 2)
            for d in phase.dungeons:
                arena = Arena(MAPS_BY_KEY[d.map_key], game().assets)
                for x, y in d.starts:
                    self.assertTrue(arena.is_free(x, y, 16), (d.map_key, x, y))
                self.assertTrue(arena.is_free(*d.exit_spot, 30), d.map_key)


class AcampamentoTest(unittest.TestCase):
    def test_comeco_da_fase_no_acampamento(self):
        match, _ = acampamento()
        self.assertTrue(match.lobby)
        self.assertEqual(match.gates[1].state, "open")
        self.assertEqual(match.gates[2].state, "locked")
        self.assertIn(match.gates[2].wall, match.arena.walls)       # grade fechada é parede
        self.assertNotIn(match.gates[1].wall, match.arena.walls)
        self.assertIsNone(match.chest)                              # o baú só aparece na volta
        self.assertEqual(match.enemies, [])

    def test_entrar_na_masmorra_1(self):
        match, inputs = acampamento()
        passo(match, inputs, 5)
        gate = match.gates[1]
        x, y = gate.entrance
        match.players[0].x, match.players[0].y = x, y + 60
        match.players[1].x, match.players[1].y = x + 400, y + 300
        passo(match, inputs, 20)
        self.assertFalse(match.leaving)                  # falta o P2
        juntar(match, x, y - 30)
        passo(match, inputs, 3)
        self.assertTrue(match.leaving)
        passo(match, inputs, LEAVE_FRAMES + 2)
        self.assertTrue(match.finished)
        scene = match.next_scene()
        self.assertIsInstance(scene.match, CampaignMatch)
        self.assertEqual(scene.match.dungeon_index, 0)

    def test_volta_abre_a_masmorra_2(self):
        match, inputs = acampamento(back=True)
        self.assertEqual(match.gates[1].state, "done")
        passo(match, inputs, 52)
        self.assertEqual(match.gates[2].state, "open")
        passo(match, inputs, 30)
        self.assertNotIn(match.gates[2].wall, match.arena.walls)
        self.assertIn(match.gates[1].wall, match.arena.walls)

    def test_fogueira_cura_ate_70_por_cento(self):
        match, inputs = acampamento()
        p1 = match.players[0]
        fire = next(p for p in match.props if isinstance(p, Campfire))
        juntar(match, fire.x + 50, fire.y + 30)
        p1.hp = 10
        passo(match, inputs, 60 * 30)
        self.assertEqual(p1.hp, round(p1.max_hp * Campfire.HEAL_TO))


class BauTest(unittest.TestCase):
    def test_bau_da_uma_arma_rara_para_cada_um(self):
        match, inputs = acampamento(chars=("guerreiro", "atirador", "ninja"), back=True)
        chest = match.chest
        self.assertIsNotNone(chest)
        juntar(match, chest.x - 40, chest.y + 10)
        passo(match, inputs, 3)
        inputs[1].tap("attack")
        passo(match, inputs, 1)
        self.assertEqual(chest.state, "opening")
        self.assertEqual(match.bullets, [])               # o ATACAR abriu o baú (não atirou)
        passo(match, inputs, DONE_AT + 10)
        self.assertEqual(chest.state, "open")
        relics = [p.relic for p in match.players]
        self.assertTrue(all(r is not None and r.rare for r in relics))
        self.assertEqual(len({r.name for r in relics}), 3)    # armas diferentes
        for p in match.players:
            self.assertIs(p.weapon, p.relic)                  # já vem na mão
            self.assertEqual(len(p.weapons), 3)
            self.assertEqual(match.run.relics[p.slot], next(k for k, w in RARE_WEAPONS.items() if w is p.relic))
        self.assertTrue(match.run.chest_open)

    def test_arma_rara_continua_nas_proximas_etapas(self):
        g, run = corrida(stage=DUNGEON_2)
        run.relics[1] = "besta"
        run.held[1] = 2
        match = CampaignMatch(g, run)
        p1 = match.players[0]
        self.assertIs(p1.relic, RARE_WEAPONS["besta"])
        self.assertIs(p1.weapon, RARE_WEAPONS["besta"])
        p1.switch_weapon()
        self.assertEqual(p1.weapon_index, 0)                   # TROCAR ARMA passa pelas três

    def test_bau_aberto_nao_volta_e_tentar_de_novo_devolve(self):
        g, run = corrida(stage=LOBBY_BACK)
        run.chest_open = True
        self.assertIsNone(LobbyMatch(g, run).chest)
        run.retry_phase()
        self.assertEqual(run.stage, 0)
        self.assertFalse(run.chest_open)


class ArmaNoChaoTest(unittest.TestCase):
    """Só dá para ter uma arma rara: pegando outra, a antiga fica no chão e dá para pegar de volta."""

    def _bau_com_besta(self):
        g, run = corrida(chars=("guerreiro", "atirador"), stage=LOBBY_BACK)
        run.relics[1] = "besta"                            # já tinha uma arma rara da fase anterior
        match = LobbyMatch(g, run)
        inputs = {}
        for f in match.players:
            inputs[f.slot] = match.controllers[f] = _Input()
        p1 = match.players[0]
        self.assertIs(p1.relic, RARE_WEAPONS["besta"])
        chest = match.chest
        juntar(match, chest.x - 40, chest.y + 10)
        passo(match, inputs, 3)
        inputs[1].tap("attack")
        passo(match, inputs, DONE_AT + 40)                 # abre, as armas voam e a antiga cai
        return match, inputs, p1

    def test_quarta_arma_deixa_a_antiga_no_chao(self):
        match, inputs, p1 = self._bau_com_besta()
        self.assertIsNot(p1.relic, RARE_WEAPONS["besta"])
        self.assertEqual(len(p1.weapons), 3)                   # continua com 3 armas
        self.assertEqual(len(match.ground), 1)
        item = match.ground[0]
        self.assertIs(item.weapon, RARE_WEAPONS["besta"])
        self.assertTrue(item.landed)

    def test_pega_de_volta_trocando(self):
        match, inputs, p1 = self._bau_com_besta()
        new = p1.relic
        item = match.ground[0]
        spot = (item.x, item.y)
        p1.x, p1.y = item.x + 20, item.y
        match.players[1].x += 300                              # o companheiro longe
        inputs[1].tap("attack")
        passo(match, inputs, 1)
        self.assertIs(p1.relic, RARE_WEAPONS["besta"])
        self.assertIs(p1.weapon, p1.relic)                     # volta para a mão
        self.assertEqual(match.run.relics[1], "besta")
        self.assertEqual(match.bullets, [])                    # o ATACAR pegou a arma (não atirou)
        self.assertEqual(len(match.ground), 1)
        swapped = match.ground[0]
        self.assertIs(swapped.weapon, new)                     # a outra ficou no lugar
        passo(match, inputs, swapped.TOSS + 2)
        self.assertLess(abs(swapped.x - spot[0]) + abs(swapped.y - spot[1]), 40)

    def test_companheiro_pode_pegar(self):
        match, inputs, p1 = self._bau_com_besta()
        p2 = match.players[1]
        mine = p2.relic
        item = match.ground[0]
        p1.x += 300
        p2.x, p2.y = item.x - 20, item.y
        inputs[2].tap("attack")
        passo(match, inputs, 1)
        self.assertIs(p2.relic, RARE_WEAPONS["besta"])
        self.assertIs(match.ground[0].weapon, mine)

    def test_nao_pega_enquanto_cai(self):
        match, inputs = acampamento(back=True)
        p1 = match.players[0]
        match.give_relic(p1, RARE_WEAPONS["canhao"])
        match.give_relic(p1, RARE_WEAPONS["bumerangue"])
        item = match.ground[0]
        self.assertFalse(item.can_pick(p1))
        passo(match, inputs, item.TOSS + 1)
        p1.x, p1.y = item.x, item.y
        self.assertTrue(item.can_pick(p1))
        match.draw(match.game.screen, match.game.ui)           # nome e "ATACAR: PEGAR" na tela


class ArmasRarasTest(unittest.TestCase):
    EXPECTED = {"besta": P.Bolt, "lanca_chamas": P.Flame, "bumerangue": P.Boomerang,
                "cajado_raio": P.Lightning, "canhao": P.CannonBall}

    def _campo(self, weapon_key):
        g, run = corrida(stage=DUNGEON_1)
        run.relics[1] = weapon_key
        run.held[1] = 2
        match = CampaignMatch(g, run)
        match.state, match.state_timer, match.banner = "fight", 0, None
        return match, match.players[0]

    def _inimigo(self, match, kind, x, y):
        match._spawn(kind, x, y)
        e = match.enemies[-1]
        match.controllers.pop(e)
        return e

    def test_cada_arma_rara_tem_seu_projetil_e_arte(self):
        from soulstrike import weapon_art
        for key, cls in self.EXPECTED.items():
            match, p1 = self._campo(key)
            proj = match.spawn_projectile(p1, p1.weapon, (1.0, 0.0), 10, None)
            self.assertIsInstance(proj, cls, key)
            self.assertIsNotNone(weapon_art.icon(RARE_WEAPONS[key].name), key)
            self.assertTrue(RARE_WEAPONS[key].note, key)

    def test_raio_pula_de_inimigo_em_inimigo(self):
        match, p1 = self._campo("cajado_raio")
        p1.x, p1.y = 400, 600
        a = self._inimigo(match, "golem", 600, 600)
        b = self._inimigo(match, "golem", 700, 620)
        c = self._inimigo(match, "golem", 790, 640)
        hps = [e.hp for e in (a, b, c)]
        p1.attack_cd = 0
        self.assertTrue(p1.attack(match, a))
        match._update_bullets()
        self.assertTrue(all(e.hp < hp for e, hp in zip((a, b, c), hps)))
        self.assertTrue(any(isinstance(e, P.LightningArc) for e in match.effects))

    def test_lanca_chamas_atravessa_e_gasta_rapido(self):
        match, p1 = self._campo("lanca_chamas")
        p1.x, p1.y = 400, 600
        a = self._inimigo(match, "golem", 470, 600)
        b = self._inimigo(match, "golem", 500, 612)
        ha, hb = a.hp, b.hp
        for _ in range(40):
            p1.attack(match, a)
            p1.update(match)
            match._update_bullets()
        self.assertLess(a.hp, ha)
        self.assertLess(b.hp, hb)
        self.assertLess(p1.ammo, p1.mag)

    def test_bumerangue_volta_para_a_mao(self):
        match, p1 = self._campo("bumerangue")
        p1.x, p1.y = 400, 600
        b = match.spawn_projectile(p1, p1.weapon, (1.0, 0.0), 15, None)
        far = 0
        for _ in range(200):
            match._update_bullets()
            far = max(far, b.x - p1.x)
            if not b.alive:
                break
        self.assertGreater(far, 150)
        self.assertFalse(b.alive)

    def test_canhao_explode(self):
        from soulstrike.entities import Explosion
        match, p1 = self._campo("canhao")
        p1.x, p1.y = 400, 600
        e = self._inimigo(match, "golem", 560, 600)
        hp = e.hp
        match.spawn_projectile(p1, p1.weapon, (1.0, 0.0), 26, e)
        for _ in range(40):
            match._update_bullets()
            for eff in match.effects:
                eff.update(match)
        self.assertTrue(any(isinstance(eff, Explosion) for eff in match.effects) or e.hp < hp)
        self.assertLess(e.hp, hp)

    def test_cada_arma_rara_tem_pente_proprio(self):
        match, p1 = self._campo("besta")
        p1.x, p1.y = 400, 600
        p1.attack_cd = 0
        target = self._inimigo(match, "golem", 800, 600)
        p1.attack(match, target)
        self.assertEqual(p1.ammo, p1.mag - 1)               # pente da besta
        p1.weapon_index = 0
        self.assertEqual(p1.ammo, p1.mag)                   # o arco continua cheio


class CampanhaInteiraTest(unittest.TestCase):
    def test_tres_fases_de_ponta_a_ponta(self):
        """Acampamento → masmorra 1 → acampamento (baú) → masmorra 2 → teletransporte, nas 3 fases."""
        from soulstrike.scenes.campaign import StoryScene, UpgradeScene, start_phase
        g, run = corrida()
        real = g.inputs
        g.inputs = {s: _Input() for s in (1, 2, 3, 4)}
        try:
            for phase in range(3):
                run.phase_index = phase
                scene = start_phase(g, run, story=False)
                for stage in range(4):
                    m = scene.match
                    ins = {f.slot: m.controllers[f] for f in m.players}
                    if isinstance(m, LobbyMatch):
                        passo(m, ins, 60)
                        if m.chest is not None:
                            juntar(m, m.chest.x - 40, m.chest.y + 10)
                            passo(m, ins, 2)
                            ins[1].tap("attack")
                            passo(m, ins, DONE_AT + 10)
                        gate = m.gates[m.target_gate]
                        juntar(m, gate.entrance[0], gate.entrance[1] - 30)
                        passo(m, ins, LEAVE_FRAMES + 10)
                    else:
                        m.state, m.state_timer, m.banner = "fight", 0, None
                        m.wave = len(m.waves) - 1
                        passo(m, ins, 80)
                        if m.state == "vote":
                            for inp in ins.values():
                                inp.tap("attack")
                            passo(m, ins, 120)
                        else:
                            juntar(m, m.exit.x, m.exit.y)
                            passo(m, ins, LEAVE_FRAMES + 10)
                    self.assertTrue(m.finished and m.won, (phase, stage, type(m).__name__))
                    scene = m.next_scene()
                self.assertIsInstance(scene, StoryScene if phase == 2 else UpgradeScene)
                self.assertTrue(all(run.relics.values()))
        finally:
            g.inputs = real


if __name__ == "__main__":
    unittest.main()
