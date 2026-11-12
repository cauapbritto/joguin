"""Campanha em masmorras: as salas de luta (CampaignMatch avulsa), o baú com as armas raras, a
fogueira e as armas no chão. O mapa da fase inteira fica em test_fase_mapa."""
import math
import unittest

from apoio import FakeInput, com_rara, game

from soulstrike import projectiles as P
from soulstrike.arena import BATTLE_MAPS, MAPS_BY_KEY, Arena
from soulstrike.campaign import (DUNGEON_1, DUNGEON_2, LOBBY_BACK, PASSAGE_FRAMES,
                                 PHASES, TELEPORT_FRAMES, CampaignMatch, CampaignRun)
from soulstrike.fase import PhaseMatch
from soulstrike.data import CHARACTERS, RARE_WEAPONS
from soulstrike.dungeon import DONE_AT, Campfire
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
    """A fase inteira (a abertura e a sala de recompensas ficam no mesmo mapa)."""
    g, run = corrida(chars, phase)
    match = PhaseMatch(g, run)
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
    def test_acampamentos_antigos_sairam(self):
        self.assertFalse([m.key for m in MAPS_BY_KEY.values() if m.key.startswith("acampamento_")])

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
            for d in phase.dungeons + (phase.middle,):
                arena = Arena(MAPS_BY_KEY[d.map_key], game().assets)
                for x, y in d.starts:
                    self.assertTrue(arena.is_free(x, y, 16), (d.map_key, x, y))
                self.assertTrue(arena.is_free(*d.exit_spot, 30), d.map_key)


class AcampamentoTest(unittest.TestCase):
    def test_fogueira_cura_ate_70_por_cento(self):
        match, inputs = acampamento(back=True)
        p1 = match.players[0]
        fire = next(p for p in match.props if isinstance(p, Campfire))
        juntar(match, fire.x + 50, fire.y + 30)
        p1.hp = 10
        passo(match, inputs, 60 * 30)
        self.assertEqual(p1.hp, round(p1.max_hp * Campfire.HEAL_TO))


class MasmorraTest(unittest.TestCase):
    def _masmorra(self, dungeon=0, chars=("guerreiro", "atirador")):
        g, run = corrida(chars, stage=DUNGEON_2 if dungeon else DUNGEON_1)
        match = CampaignMatch(g, run)
        inputs = {}
        for f in match.players:
            inputs[f.slot] = match.controllers[f] = _Input()
        return match, inputs

    def test_inimigos_esperam_o_botao_iniciar_batalha(self):
        match, inputs = self._masmorra()
        passo(match, inputs, 400)
        self.assertEqual(match.state, "ready")
        self.assertEqual(match.portals, [])                 # ninguém sai dos portais ainda
        self.assertEqual(match.alive_enemies, [])
        button = match.start_button
        p1 = match.players[0]
        p1.x, p1.y = button.x, button.y + 40
        p1.vx = p1.vy = 0
        inputs[1].tap("attack")
        passo(match, inputs, 2)
        self.assertEqual(match.state, "fight")
        self.assertTrue(match.portals or match.alive_enemies)
        self.assertEqual(match.bullets, [])                 # o ATACAR apertou o botão (não atirou)

    def test_portal_da_fase_leva_todos_juntos(self):
        match, inputs = self._masmorra(dungeon=1)
        match.state, match.state_timer, match.banner = "fight", 0, None
        match.wave = len(match.waves) - 1
        passo(match, inputs, 80)
        self.assertEqual(match.state, "portal")
        portal = match.exit
        p1, p2 = match.players
        p1.x, p1.y = portal.x, portal.y
        passo(match, inputs, PASSAGE_FRAMES + 10)
        self.assertEqual(match.state, "portal")             # falta o P2
        p2.x, p2.y = portal.x + 30, portal.y
        passo(match, inputs, PASSAGE_FRAMES + 2)
        self.assertEqual(match.state, "teleport")
        passo(match, inputs, TELEPORT_FRAMES + 2)
        self.assertTrue(match.finished and match.won)


class BauTest(unittest.TestCase):
    def _abrir(self, chars=("guerreiro", "atirador", "ninja")):
        match, inputs = acampamento(chars=chars, back=True)
        chest = match.chest
        self.assertIsNotNone(chest)
        juntar(match, chest.x - 40, chest.y + 10)
        passo(match, inputs, 3)
        inputs[1].tap("attack")
        passo(match, inputs, 1)
        self.assertEqual(chest.state, "opening")
        self.assertEqual(match.bullets, [])               # o ATACAR abriu o baú (não atirou)
        for k, p in enumerate(match.players):             # todo mundo sai de perto (não pega sem querer)
            p.x, p.y = chest.x - 300 - 40 * k, chest.y
        passo(match, inputs, DONE_AT + 30)
        self.assertEqual(chest.state, "open")
        return match, inputs

    def test_bau_joga_as_armas_no_chao_sem_trocar_sozinho(self):
        match, inputs = self._abrir()
        self.assertTrue(all(not any(w.rare for w in p.weapons) for p in match.players))    # ninguém trocou sozinho
        self.assertTrue(all(len(p.weapons) == 2 for p in match.players))
        items = list(match.ground)
        self.assertEqual(len(items), len(match.players) + 1)            # uma por jogador e mais uma
        self.assertTrue(all(g.weapon.rare and g.landed for g in items))
        self.assertEqual(len({g.weapon.name for g in items}), len(items))    # armas diferentes
        chest = match.chest
        for g in items:                                                 # caem na frente do baú
            self.assertGreater(g.y, chest.y)
            self.assertLess(math.hypot(g.x - chest.x, g.y - chest.y), 450)
        self.assertTrue(match.run.chest_open)

    def test_cada_um_escolhe_e_pega_a_sua(self):
        match, inputs = self._abrir(chars=("guerreiro", "atirador"))
        p1, p2 = match.players
        a, b = match.ground[0], match.ground[2]
        p1.x, p1.y = a.x + 20, a.y
        p2.x, p2.y = b.x + 20, b.y
        inputs[1].tap("attack")
        inputs[2].tap("attack")
        passo(match, inputs, 1)
        self.assertIs(p1.weapon, a.weapon)                    # já vem na mão
        self.assertIs(p2.weapon, b.weapon)
        for p in (p1, p2):
            self.assertEqual(len(p.weapons), 3)               # entrou na vaga livre da bolsa
            key = next(k for k, w in RARE_WEAPONS.items() if w is p.weapon)
            self.assertEqual(match.run.bags[p.slot][2], "rara:" + key)
        self.assertEqual(len(match.ground), 1)                # sobrou a outra no chão

    def test_arma_rara_continua_nas_proximas_etapas(self):
        g, run = corrida(stage=DUNGEON_2)
        com_rara(run, 1, "besta")
        run.held[1] = 2
        match = CampaignMatch(g, run)
        p1 = match.players[0]
        self.assertIs(p1.weapon, RARE_WEAPONS["besta"])
        p1.switch_weapon()
        self.assertEqual(p1.weapon_index, 0)                   # TROCAR ARMA passa pelas três

    def test_bau_aberto_nao_volta_e_tentar_de_novo_devolve(self):
        g, run = corrida(stage=LOBBY_BACK)
        run.chest_open = True
        self.assertIsNone(PhaseMatch(g, run).chest)
        run.retry_phase()
        self.assertEqual(run.stage, 0)
        self.assertFalse(run.chest_open)


class ArmaNoChaoTest(unittest.TestCase):
    """Bolsa cheia: pegando outra arma, a da mão fica no chão e dá para pegar de volta."""

    def _bau_com_besta(self):
        g, run = corrida(chars=("guerreiro", "atirador"), stage=LOBBY_BACK)
        com_rara(run, 1, "besta")                            # já tinha uma arma rara da fase anterior
        run.held[1] = 2                                      # e está com ela na mão
        match = PhaseMatch(g, run)
        inputs = {}
        for f in match.players:
            inputs[f.slot] = match.controllers[f] = _Input()
        p1 = match.players[0]
        self.assertIs(p1.weapon, RARE_WEAPONS["besta"])
        match.give_relic(p1, RARE_WEAPONS["canhao"])        # bolsa cheia: troca pela da mão, a besta cai
        passo(match, inputs, 40)
        return match, inputs, p1

    def test_quarta_arma_deixa_a_antiga_no_chao(self):
        match, inputs, p1 = self._bau_com_besta()
        self.assertNotIn(RARE_WEAPONS["besta"], p1.weapons)
        self.assertEqual(len(p1.weapons), 3)                   # continua com 3 armas
        self.assertEqual(len(match.ground), 1)
        item = match.ground[0]
        self.assertIs(item.weapon, RARE_WEAPONS["besta"])
        self.assertTrue(item.landed)

    def test_pega_de_volta_trocando(self):
        match, inputs, p1 = self._bau_com_besta()
        new = p1.weapon
        item = match.ground[0]
        spot = (item.x, item.y)
        p1.x, p1.y = item.x + 20, item.y
        match.players[1].x += 300                              # o companheiro longe
        inputs[1].tap("attack")
        passo(match, inputs, 1)
        self.assertIs(p1.weapon, RARE_WEAPONS["besta"])        # volta para a mão
        self.assertEqual(match.run.bags[1][2], "rara:besta")
        self.assertEqual(match.bullets, [])                    # o ATACAR pegou a arma (não atirou)
        self.assertEqual(len(match.ground), 1)
        swapped = match.ground[0]
        self.assertIs(swapped.weapon, new)                     # a outra ficou no lugar
        passo(match, inputs, swapped.TOSS + 2)
        self.assertLess(abs(swapped.x - spot[0]) + abs(swapped.y - spot[1]), 40)

    def test_companheiro_pode_pegar(self):
        match, inputs, p1 = self._bau_com_besta()
        p2 = match.players[1]
        match.give_relic(p2, RARE_WEAPONS["bumerangue"])
        mine = p2.weapon
        item = match.ground[0]
        p1.x += 300
        p2.x, p2.y = item.x - 20, item.y
        inputs[2].tap("attack")
        passo(match, inputs, 1)
        self.assertIs(p2.weapon, RARE_WEAPONS["besta"])
        self.assertIn("rara:besta", match.run.bags[2])

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
        com_rara(run, 1, weapon_key)
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
        self.assertLess(p1.energy, p1.energy_max)          # na campanha a rara gasta energia

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

    def test_rara_gasta_energia_e_a_do_heroi_tem_pente(self):
        match, p1 = self._campo("besta")
        p1.x, p1.y = 400, 600
        p1.attack_cd = 0
        target = self._inimigo(match, "golem", 800, 600)
        p1.attack(match, target)
        self.assertEqual(p1.mag, 0)                         # a besta não tem pente na campanha...
        self.assertEqual(p1.energy, p1.energy_max - 4)      # ...gasta 4 de energia por virote
        p1.weapon_index = 0
        self.assertEqual(p1.ammo, p1.mag)                   # o arco do herói continua com o pente cheio
        self.assertGreater(p1.mag, 0)


if __name__ == "__main__":
    unittest.main()
