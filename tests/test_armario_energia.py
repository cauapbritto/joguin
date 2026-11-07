"""v1.13.0: armário de armas do acampamento, energia finita da campanha e as cinco dificuldades."""
import unittest

from apoio import FakeInput, game

from soulstrike import energia
from soulstrike.ai import CAMPAIGN_ORDER, DIFFICULTIES
from soulstrike.armario import RACK_SIZE, token_of, weapon_of
from soulstrike.campaign import AFFIXES, DUNGEON_1, LEVELS, CampaignMatch, CampaignRun
from soulstrike.fase import PhaseMatch
from soulstrike.entities import Explosion, Pickup
from soulstrike.forged import FORGED
from soulstrike.data import CHARACTERS, RARE_WEAPONS
from soulstrike.session import Session, SlotSetup

KEYS = [c.key for c in CHARACTERS]


def corrida(chars=("guerreiro", "atirador"), phase=0, stage=0, difficulty="normal"):
    g = game()
    g.session = Session("campaign", [SlotSetup(i + 1, char=KEYS.index(c)) for i, c in enumerate(chars)],
                        difficulty=difficulty)
    run = CampaignRun(g.session)
    run.phase_index = phase
    run.begin_phase()
    run.stage = stage
    return g, run


def acampamento(run=None):
    g, r = corrida()
    run = run or r
    match = PhaseMatch(g, run)
    for f in match.players:
        match.controllers[f] = FakeInput()
    return match


def perto(match, p, thing):
    p.x, p.y = thing.x, thing.y + 40


class ArmarioTest(unittest.TestCase):
    def test_armario_fica_na_sala_de_recompensas(self):
        match = acampamento()
        self.assertEqual(match.layout.room_at(match.armario.x, match.armario.y).key, "recompensa")

    def test_guardar_e_pegar(self):
        match = acampamento()
        p, q = match.players
        match.give_relic(p, RARE_WEAPONS["besta"])
        perto(match, p, match.armario)
        self.assertTrue(match.interact(p))                      # ATACAR perto: guarda
        self.assertIsNone(p.relic)
        self.assertEqual(match.run.rack, ["rara:besta"])
        perto(match, q, match.armario)
        self.assertTrue(match.interact(q))                      # o amigo pega
        self.assertIs(q.relic, RARE_WEAPONS["besta"])
        self.assertEqual(match.run.rack, [])

    def test_largar_perto_guarda(self):
        match = acampamento()
        p = match.players[0]
        rifle = next(c for c in CHARACTERS if c.key == "atirador").weapons[0]
        match.give_common(p, rifle)
        perto(match, p, match.armario)
        n = len(match.ground)
        inp = match.controllers[p]
        inp.hold("drop")
        match.update()
        inp.release("drop")
        self.assertEqual(match.run.rack, [token_of(rifle)])
        self.assertEqual(len(match.ground), n)

    def test_trocar_com_o_armario(self):
        match = acampamento()
        p = match.players[0]
        match.run.rack = ["rara:canhao"]
        match.give_relic(p, RARE_WEAPONS["besta"])
        match.store_in_rack(p)                               # guarda a besta: fila canhão, besta
        match.take_from_rack(p)                              # pega o canhão
        self.assertIs(p.relic, RARE_WEAPONS["canhao"])
        self.assertEqual(match.run.rack, ["rara:besta"])
        match.take_from_rack(p)                              # pega a besta, o canhão volta para a fila
        self.assertIs(p.relic, RARE_WEAPONS["besta"])
        self.assertEqual(match.run.rack, ["rara:canhao"])

    def test_cheio(self):
        match = acampamento()
        p = match.players[0]
        match.run.rack = ["rara:canhao"] * RACK_SIZE
        match.give_relic(p, RARE_WEAPONS["besta"])
        self.assertFalse(match.store_in_rack(p))
        self.assertIs(p.relic, RARE_WEAPONS["besta"])

    def test_salvo_guarda_o_armario(self):
        _, run = corrida()
        run.rack = ["rara:besta", token_of(CHARACTERS[0].weapons[0])]
        run.begin_phase()
        loaded = CampaignRun.from_save(run.to_save())
        self.assertEqual(loaded.rack, run.rack)
        self.assertTrue(all(weapon_of(t) is not None for t in loaded.rack))


def masmorra(relic=None, difficulty="normal", chars=("guerreiro", "atirador")):
    g, run = corrida(chars=chars, stage=DUNGEON_1, difficulty=difficulty)
    if relic:
        run.relics[1] = relic
        run.held[1] = 2
    match = CampaignMatch(g, run)
    match.state, match.state_timer, match.banner = "fight", 0, None
    match.wave = len(match.waves) - 1
    for f in match.players:
        match.controllers[f] = FakeInput()
    return match, match.players[0]


def inimigo(match, kind="golem", x=700, y=600, hp=5000):
    e = match._spawn(kind, x, y)
    match.controllers.pop(e)
    e.hp = e.max_hp = hp
    e.shield = 0
    return e


class EnergiaTest(unittest.TestCase):
    def test_barra_cheia_em_cada_etapa(self):
        match, p = masmorra()
        self.assertEqual(p.energy, energia.ENERGY_MAX)
        self.assertEqual(acampamento().players[0].energy, energia.ENERGY_MAX)

    def test_fora_da_campanha_nao_tem_energia(self):
        from soulstrike.fighter import Fighter
        f = Fighter(CHARACTERS[0], 1, 0, 0, None, "P1", (255, 255, 255))
        self.assertIsNone(f.energy)
        self.assertEqual(energia.cost(f, RARE_WEAPONS["besta"]), 0)
        self.assertGreater(f.mag_of(RARE_WEAPONS["besta"]), 0)       # no duelo a besta tem pente

    def test_arma_do_heroi_e_de_graca(self):
        match, p = masmorra(chars=("atirador", "guerreiro"))
        e = inimigo(match)
        p.weapon_index = 0
        for _ in range(5):
            p.attack_cd = 0
            p.attack(match, e)
        self.assertEqual(p.energy, p.energy_max)

    def test_mil_almas_gasta_10_por_disparo(self):
        match, p = masmorra("arco_mil_almas")
        self.assertIs(p.weapon, FORGED["arco_mil_almas"])
        e = inimigo(match)
        p.attack_cd = 0
        p.attack(match, e)                                  # começa a puxar a corda
        p.bow_draw = 999
        p._release_bow(match)
        self.assertEqual(p.energy, p.energy_max - 10)

    def test_sem_energia_vira_arma_de_bater(self):
        match, p = masmorra("besta")
        e = inimigo(match, x=p.x + 40, y=p.y)
        p.energy = 2
        hp = e.hp
        n = len(match.bullets)
        p.attack_cd = 0
        self.assertTrue(p.attack(match, e))
        self.assertEqual(len(match.bullets), n)             # não atirou
        self.assertLess(e.hp, hp)                           # bateu com a besta
        self.assertGreater(p.bash_timer, 0)
        self.assertEqual(p.energy, 2)

    def test_orbe_e_item_enchem(self):
        match, p = masmorra()
        p.energy = 100
        orb = energia.EnergyOrb(p.x, p.y)
        orb.apply(p, match)
        self.assertEqual(p.energy, 100 + energia.ORB_ENERGY)
        Pickup("energia", p.x, p.y).apply(p, match)
        self.assertEqual(p.energy, 100 + energia.ORB_ENERGY + energia.ITEM_ENERGY)

    def test_orbe_vem_ate_o_jogador(self):
        match, p = masmorra()
        p.energy = 10
        orb = energia.EnergyOrb(p.x + 100, p.y)
        match.pickups.append(orb)
        for _ in range(80):
            match.update()
        self.assertFalse(orb.alive)
        self.assertGreater(p.energy, 10)

    def test_inimigos_soltam_orbes(self):
        import random
        random.seed(3)
        match, p = masmorra()
        e = inimigo(match, "golem")                          # elite: sempre solta
        match._drop_orbs(e)
        self.assertGreaterEqual(sum(isinstance(i, energia.EnergyOrb) for i in match.pickups), 3)

    def test_melhoria_energia(self):
        from soulstrike.upgrades import UPGRADES
        _, run = corrida(stage=DUNGEON_1)
        run.upgrades[1] = ["energia"]
        match = CampaignMatch(game(), run)
        self.assertEqual(match.players[0].energy_max, energia.ENERGY_MAX + 50)
        self.assertIn("energia", UPGRADES)

    def test_facil_volta_sozinha(self):
        match, p = masmorra(difficulty="facil")
        p.energy = 0
        for _ in range(120):
            match.update()
        self.assertGreater(p.energy, 0)
        match, p = masmorra(difficulty="normal")
        p.energy = 0
        for _ in range(120):
            match.update()
        self.assertEqual(p.energy, 0)


class DificuldadesTest(unittest.TestCase):
    def test_cinco_cada_vez_mais_dificeis(self):
        self.assertEqual(CAMPAIGN_ORDER, ("facil", "normal", "dificil", "ibrahim", "borba"))
        hp = [LEVELS[k].hp for k in CAMPAIGN_ORDER]
        dmg = [LEVELS[k].dmg for k in CAMPAIGN_ORDER]
        self.assertEqual(hp, sorted(hp))
        self.assertEqual(dmg, sorted(dmg))
        self.assertEqual(DIFFICULTIES["ibrahim"]["label"], "IBRAHIM")
        self.assertIn("TOMA CUIDADO JOVI", DIFFICULTIES["ibrahim"]["tagline"])
        self.assertIn("SENSACIONAL", DIFFICULTIES["borba"]["tagline"])

    def test_continues(self):
        for key, n in (("normal", 3), ("ibrahim", 1), ("borba", 1)):
            _, run = corrida(difficulty=key)
            self.assertEqual(run.continues, n)
            run.retry_phase()
            self.assertEqual(run.continues, n)

    def test_borba_salva_e_carrega(self):
        _, run = corrida(difficulty="borba")
        run.begin_phase()
        loaded = CampaignRun.from_save(run.to_save())
        self.assertEqual(loaded.session.difficulty, "borba")
        self.assertEqual(loaded.continues, 1)

    def test_inimigos_mais_fortes(self):
        normal, _ = masmorra(difficulty="normal")
        borba, _ = masmorra(difficulty="borba")
        a = normal._spawn("esqueleto", 700, 600)
        b = borba._spawn("esqueleto", 700, 600)
        self.assertGreater(b.max_hp, a.max_hp * 2)

    def test_explosivo_explode_ao_morrer(self):
        match, p = masmorra(difficulty="borba")
        e = inimigo(match, "esqueleto", p.x + 40, p.y, hp=1)
        match._give_affix(e, "explosivo")
        self.assertEqual(e.aura, AFFIXES["explosivo"][1])
        e.take_damage(50, p.x, p.y, attacker=p, match=match)
        match._update_corpses()
        self.assertTrue(any(isinstance(x, Explosion) for x in match.effects))

    def test_borba_levanta_uma_vez(self):
        match, p = masmorra(difficulty="borba")
        q = match.players[1]
        q.x, q.y = p.x + 20, p.y
        inimigo(match, "golem", 1400, 300)                 # segura a onda (sem sala limpa)
        p.hp = 0
        match.revived_once.add(p)
        for _ in range(600):
            match.update()
        self.assertFalse(p.alive_in_match)

    def test_chefao_furioso_mais_cedo(self):
        from soulstrike.boss import BossAI
        self.assertEqual(BossAI("normal").enrage_at, 0.2)
        self.assertEqual(BossAI("borba").enrage_at, 0.5)

    def test_loja_mais_cara(self):
        from soulstrike.market import MarketMenu, Stall
        for key, mult in (("normal", 1.0), ("ibrahim", 1.25)):
            g, run = corrida(difficulty=key)
            m = PhaseMatch(g, run)
            stall = next(s for s in m.stalls if s.kind == "loja" and not s.mini)
            menu = MarketMenu(m, m.players[0], stall)
            potion = next(e for e in menu.entries() if e.key == "pocao")
            self.assertEqual(potion.cost, round(20 * mult))

    def test_escolha_na_campanha_tem_cinco(self):
        from soulstrike.scenes.select import CharSelectScene as SelectScene
        g = game()
        g.session = Session("campaign", [SlotSetup(1, char=0)])
        scene = SelectScene(g)
        seen = set()
        for _ in range(5):
            seen.add(g.session.difficulty)
            scene._cycle_difficulty(1)
        self.assertEqual(seen, set(CAMPAIGN_ORDER))
        g.session = Session("cpu", [SlotSetup(1, char=0)])
        scene = SelectScene(g)
        seen = set()
        for _ in range(6):
            seen.add(g.session.difficulty)
            scene._cycle_difficulty(1)
        self.assertEqual(seen, {"facil", "normal", "dificil"})


if __name__ == "__main__":
    unittest.main()
