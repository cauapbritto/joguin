"""A turma do Aryel: Cauanzera, Albeguinio e Borba Jr. Lutam em todos os modos, com arma,
habilidade do duelo e poder do futebol próprios."""
import math
import unittest

from apoio import FakeInput, MEIO, GOL_D, futebol, game, run

from soulstrike import config
from soulstrike import projectiles as P
from soulstrike.data import CHARACTERS, FIGHTERS, roster
from soulstrike.fighter import BOW_FULL
from soulstrike.matches import BattleMatch, TeamBattleMatch
from soulstrike.session import Session, SlotSetup

KEYS = [c.key for c in CHARACTERS]
TURMA = ("cauanzera", "albeguinio", "borba")


def duelo(a, b="guerreiro"):
    g = game()
    g.session = Session("duel", [SlotSetup(1, char=KEYS.index(a)), SlotSetup(2, char=KEYS.index(b))])
    match = BattleMatch(g, g.session)
    match.intro = 0
    p1, p2 = match.fighters
    match.controllers.clear()
    match.controllers[p1] = FakeInput()
    match.controllers[p2] = FakeInput()
    p1.x, p1.y, p2.x, p2.y = 600, 700, 1000, 700
    return match, p1, p2


def passo(match, frames):
    for _ in range(frames):
        match.update()


class ElencoTest(unittest.TestCase):
    def test_lutam_em_todos_os_modos(self):
        batalha = [c.key for c in roster()]
        bola = [c.key for c in roster(soccer=True)]
        for key in TURMA:
            self.assertIn(key, batalha)
            self.assertIn(key, bola)
            self.assertFalse(CHARACTERS[KEYS.index(key)].soccer_only)

    def test_aparecem_junto_dos_outros_herois(self):
        keys = [c.key for c in roster(soccer=True)]
        geada = keys.index("geada")
        self.assertEqual(keys[geada + 1:geada + 4], list(TURMA))       # logo depois da Geada
        self.assertLess(keys.index("borba"), keys.index("faisca"))     # antes dos craques

    def test_nomes(self):
        names = {c.key: c.name for c in CHARACTERS}
        self.assertEqual((names["cauanzera"], names["albeguinio"], names["borba"]),
                         ("Cauanzera", "Albeguinio", "Borba Jr"))

    def test_armas_novas(self):
        stats = {c.key: c for c in CHARACTERS if c.key in TURMA}
        guns = {k: c.weapons[0] for k, c in stats.items()}
        self.assertIs(P.projectile_class(guns["cauanzera"].style), P.FloppyDisk)
        self.assertIs(P.projectile_class(guns["albeguinio"].style), P.Pendrive)
        self.assertIs(P.projectile_class(guns["borba"].style), P.PulseShot)
        self.assertEqual([c.weapons[1].name for c in stats.values()], ["Cabo de Rede", "Notebook", "Punho Mecânico"])

    def test_habilidades(self):
        names = {c.key: c.ability_name for c in CHARACTERS if c.key in TURMA}
        self.assertEqual(names, {"cauanzera": "Multiesportista", "albeguinio": "Hacker", "borba": "Exoesqueleto"})


class MultiesportistaTest(unittest.TestCase):
    def test_esportes_em_ordem(self):
        match, p1, p2 = duelo("cauanzera")
        seen = []
        for _ in range(4):
            seen.append(p1.ability.name)
            p1.ability_cd = 0
            self.assertTrue(p1.use_ability(match, p2))
            passo(match, 2)
        self.assertEqual(seen, ["BASQUETE", "VÔLEI", "ATLETISMO", "BASQUETE"])
        p1.reset_round(600, 700, (1.0, 0.0))
        self.assertEqual(p1.ability.name, "BASQUETE")              # novo round: começa do basquete

    def test_basquete_passa_por_cima_e_nao_erra(self):
        match, p1, p2 = duelo("cauanzera")
        p1.x, p1.y, p2.x, p2.y = 500, 600, 1000, 600               # parede no meio (750..850, 570..630)
        hp = p2.hp
        p1.use_ability(match, p2)
        passo(match, 10)
        p2.x, p2.y = 1100, 700                                     # correu: a bola vai atrás
        passo(match, 60)
        self.assertLess(p2.hp, hp)

    def test_volei_volta_da_parede_no_um_contra_um(self):
        match, p1, p2 = duelo("cauanzera")
        p1.ability.next = 1
        p1.use_ability(match, p2)
        hits = []
        for _ in range(160):
            before = p2.hp
            match.update()
            if p2.hp < before:
                hits.append(match.frame)
        self.assertGreaterEqual(len(hits), 2)                      # acertou, bateu na parede e voltou

    def test_volei_quica_entre_os_adversarios(self):
        g = game()
        chars = (KEYS.index("cauanzera"), KEYS.index("guerreiro"), KEYS.index("aryel"), KEYS.index("tita"))
        g.session = Session("duel2", [SlotSetup(i + 1, char=c) for i, c in enumerate(chars)])
        match = TeamBattleMatch(g, g.session)
        match.intro = 0
        match.controllers.clear()
        for f in match.fighters:
            match.controllers[f] = FakeInput()
        me = next(f for f in match.fighters if f.slot == 1)
        foes = match.opponents_of(me)
        me.x, me.y = 500, 450
        foes[0].x, foes[0].y = 900, 450
        foes[1].x, foes[1].y = 900, 780
        me.ability.next = 1
        hp = [f.hp for f in foes]
        me.use_ability(match, foes[0])
        passo(match, 120)
        self.assertTrue(all(f.hp < h for f, h in zip(foes, hp)))

    def test_cem_metros_corre_e_atropela(self):
        match, p1, p2 = duelo("cauanzera")
        p1.x, p2.x, p2.y = 400, 560, 700
        p1.facing = (1.0, 0.0)
        p1.ability.next = 2
        hp, x0 = p2.hp, p1.x
        self.assertTrue(p1.use_ability(match, p2))
        passo(match, 40)
        self.assertGreater(p1.x - x0, 300)                         # sem tocar no direcional, saiu correndo
        self.assertLess(p2.hp, hp)

    def test_alto_alcanca_mais_longe(self):
        match, p1, p2 = duelo("cauanzera")
        p2.x = p1.x + 95                                           # a espada (70) não chegaria
        p1.weapon_index = 1
        hp = p2.hp
        p1.attack(match, p2)
        self.assertLess(p2.hp, hp)
        cabo = CHARACTERS[KEYS.index("cauanzera")].weapons[1]
        self.assertEqual(cabo.reach, max(w.reach for c in FIGHTERS for w in c.weapons))   # o maior alcance


class HackerTest(unittest.TestCase):
    def test_digita_e_trava_todo_mundo(self):
        match, p1, p2 = duelo("albeguinio")
        self.assertTrue(p1.use_ability(match, p2))
        passo(match, p1.ability.TYPING - 4)
        self.assertGreater(p1.type_timer, 0)                       # digitando: parado
        self.assertFalse(p2.hacked)
        passo(match, 8)
        self.assertTrue(p2.hacked)
        self.assertTrue(p2.stunned)
        self.assertFalse(p2.attack(match, p1))                     # nem atira
        self.assertFalse(p2.use_ability(match, p1))
        passo(match, 5 * config.FPS)
        self.assertFalse(p2.hacked)

    def test_apanhar_digitando_falha(self):
        match, p1, p2 = duelo("albeguinio")
        p1.use_ability(match, p2)
        passo(match, 10)
        p1.take_damage(5, p2.x, p2.y, attacker=p2, match=match)
        passo(match, config.FPS)
        self.assertFalse(p2.hacked)
        self.assertEqual(p1.type_timer, 0)

    def test_chefao_fica_menos_tempo(self):
        match, p1, p2 = duelo("albeguinio")
        p2.unstoppable = True
        self.assertTrue(p2.hack(5 * config.FPS))
        self.assertLess(p2.hack_timer, 3 * config.FPS)

    def test_pendrive_passa_virus(self):
        match, p1, p2 = duelo("albeguinio")
        p2.x = p1.x + 300
        p1.attack(match, p2)
        for _ in range(60):
            match.update()
            if p2.virus_timer > 0:
                break
        self.assertGreater(p2.virus_timer, 0)
        hp = p2.hp
        passo(match, 60)
        self.assertLess(p2.hp, hp)                                 # perde vida aos poucos


class ExoesqueletoTest(unittest.TestCase):
    def test_armadura_metade_do_dano_e_maior(self):
        match, p1, p2 = duelo("borba")
        normal = p1.sprites
        self.assertTrue(p1.use_ability(match, p2))
        self.assertIsNot(p1.sprites, normal)                       # sprite de armadura
        self.assertGreater(p1.radius, p1.base_radius)
        hp = p1.hp
        p1.take_damage(20, p2.x, p2.y, attacker=p2, match=match)
        self.assertEqual(hp - p1.hp, 10)
        self.assertEqual(p1.knock, [0.0, 0.0])                     # não é empurrado
        passo(match, 6 * config.FPS + 20)                          # (+ pausas de impacto)
        self.assertIs(p1.sprites, normal)                          # acabou: volta ao normal
        self.assertEqual(p1.radius, p1.base_radius)

    def test_soco_arremessa_e_parede_deixa_tonto(self):
        match, p1, p2 = duelo("borba")
        p1.x, p1.y, p2.x, p2.y = 1380, 700, 1430, 700              # parede da direita perto
        p1.weapon_index = 1
        p1.use_ability(match, p2)
        p1.attack(match, p2)
        self.assertGreater(math.hypot(*p2.knock), 15)
        for _ in range(40):
            match.update()
            if p2.stunned:
                break
        self.assertTrue(p2.stunned)

    def test_canhao_carregado_sai_maior(self):
        match, p1, p2 = duelo("borba")
        p2.x = p1.x + 360
        for _ in range(BOW_FULL):
            p1.attack(match, p2)
            p1.update(match)
        shots = [b for b in match.bullets if b.owner is p1]
        self.assertEqual(len(shots), 1)
        self.assertGreaterEqual(shots[0].radius, 9)


class FutebolTest(unittest.TestCase):
    def _com_bola(self, key, foe="aryel", x=900):
        match, inputs = futebol(chars=(KEYS.index(key), KEYS.index(foe)), humans=(1,))
        p1, p2 = match.fighters
        p1.x, p1.y = x, MEIO
        p2.x, p2.y = 300, MEIO + 450
        match.ball.x, match.ball.y = p1.x + 28, p1.y
        run(match, 3, inputs)
        assert match.possessor is p1
        return match, inputs, p1, p2

    def test_enterrada_nao_da_para_defender(self):
        match, inputs, p1, p2 = self._com_bola("cauanzera", x=GOL_D - 450)
        p2.x, p2.y = GOL_D - 50, MEIO                              # goleiro na frente do gol
        self.assertTrue(match.use_power(p1))
        self.assertEqual(p1.super_cd, 25 * config.FPS)             # recarga longa
        for _ in range(120):
            run(match, 1, inputs)
            if match.score[0]:
                break
        self.assertEqual(match.score[0], 1)

    def test_enterrada_longe_do_gol_nao_gasta(self):
        match, inputs, p1, p2 = self._com_bola("cauanzera")
        self.assertFalse(match.use_power(p1))
        self.assertEqual(p1.super_cd, 0)

    def test_hack_trava_e_tira_a_bola(self):
        match, inputs = futebol(chars=(KEYS.index("albeguinio"), KEYS.index("aryel")), humans=(1,))
        p1, p2 = match.fighters
        p1.x, p1.y = 900, MEIO
        p2.x, p2.y = 1100, MEIO
        match.ball.x, match.ball.y = p2.x + 26, p2.y
        run(match, 3, inputs)
        self.assertIs(match.possessor, p2)
        self.assertTrue(match.use_power(p1))
        run(match, p1.power.TYPING + 3, inputs)
        self.assertTrue(p2.hacked)
        self.assertIsNot(match.possessor, p2)

    def test_exoesqueleto_ninguem_toma_e_quem_tromba_cai(self):
        match, inputs, p1, p2 = self._com_bola("borba")
        self.assertTrue(match.use_power(p1))
        p2.x, p2.y = p1.x + 30, p1.y
        run(match, 2, inputs)
        self.assertTrue(p2.stunned)                                # trombou e caiu
        for _ in range(60):
            p1.x, p1.y = 900, MEIO
            match.ball.x, match.ball.y = 930, MEIO
            p2.stun_timer = 0
            p2.x, p2.y = 936, MEIO
            match._update_possession()
            self.assertIs(match.possessor, p1)

    def test_exoesqueleto_segura_o_chute(self):
        match, inputs = futebol(chars=(KEYS.index("borba"), KEYS.index("aryel")), humans=(1,))
        p1, p2 = match.fighters
        p1.x, p1.y = 600, MEIO
        p2.x, p2.y = 1200, MEIO + 400
        match.use_power(p1)
        ball = match.ball
        ball.x, ball.y = 900, MEIO
        ball.vx, ball.vy = -13.0, 0.0
        run(match, 30, inputs)
        self.assertLess(abs(ball.vx), 3)
        self.assertGreater(ball.x, p1.x)                           # morreu na frente dele


if __name__ == "__main__":
    unittest.main()
