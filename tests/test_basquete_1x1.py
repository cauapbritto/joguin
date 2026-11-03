"""Basquete 1 x 1 com poder demais: regras do modo, orbes, ULTRAs e a esquiva que anula."""
import unittest

from apoio import FakeInput, game, run

from soulstrike import basket_ultra as U
from soulstrike import config
from soulstrike.arena import Court
from soulstrike.basketball import BasketballMatch
from soulstrike.data import CHARACTERS
from soulstrike.session import Session, SlotSetup

INDEX = {c.key: i for i, c in enumerate(CHARACTERS)}


class Parado:
    def update(self, me, match):
        me.steer(0, 0)


def um_contra_um(a="guerreiro", b="atirador", human=True):
    """1 x 1 com o P1 num controle falso e o P2 parado."""
    g = game()
    g.session = Session("basket1", [SlotSetup(1, char=INDEX[a]), SlotSetup(2, char=INDEX[b], cpu=True)])
    g.session.map_key = "quadra_ginasio"
    match = BasketballMatch(g, g.session)
    p1, p2 = match.fighters
    inp = FakeInput()
    match.controllers[p1] = inp if human else Parado()
    match.controllers[p2] = Parado()
    return match, p1, p2, inp


def com_bola(match, f, x=None, y=None):
    hx, hy = match.hoop_pos(match.hoop_of(f.team))
    f.x = hx + (-300 if hx > Court.W / 2 else 300) if x is None else x
    f.y = hy if y is None else y
    match.ball.reset(f.x, f.y)
    match._give(f)


def cesta(match, f, three=False, dunk=False):
    side = match.hoop_of(f.team)
    match.shot = {"team": f.team, "three": three, "shooter": f, "side": side, "dunk": dunk}
    match._basket(side)


class RegrasTest(unittest.TestCase):
    def test_um_tempo_de_3_minutos(self):
        match, *_ = um_contra_um()
        self.assertTrue(match.solo)
        self.assertEqual(match.clock, 180 * config.FPS)
        match.clock = 1
        match.score = [4, 2]
        run(match, 3)
        self.assertEqual(match.half, 1)
        self.assertEqual(match.result_team, 0)          # sem intervalo: acabou o tempo, acabou o jogo

    def test_21_pontos_acaba(self):
        match, p1, _, _ = um_contra_um()
        match.score = [19, 0]
        cesta(match, p1)
        self.assertEqual(match.result_team, 0)

    def test_super_volta_em_4s(self):
        match, p1, _, _ = um_contra_um("cauanzera")
        com_bola(match, p1)
        self.assertTrue(match.use_power(p1))                # Enterrada Voadora: na hora
        self.assertEqual(p1.super_cd, 4 * config.FPS)

    def test_super_que_dura_volta_4s_depois_do_efeito(self):
        match, p1, _, _ = um_contra_um("atirador")
        com_bola(match, p1)
        self.assertTrue(match.use_power(p1))                # Mão Quente: 5 s de efeito
        self.assertEqual(p1.super_cd, 9 * config.FPS)

    def test_2x2_continua_8s(self):
        g = game()
        g.session = Session("basket2", [SlotSetup(s, char=s, cpu=True) for s in (1, 2, 3, 4)])
        match = BasketballMatch(g, g.session)
        self.assertFalse(match.solo)
        f = match.fighters[0]
        self.assertEqual(match.super_cooldown(f.power), f.power.cooldown)

    def test_fogo_com_2_cestas(self):
        match, p1, _, _ = um_contra_um()
        cesta(match, p1)
        self.assertEqual(p1.fire_timer, 0)
        cesta(match, p1)
        self.assertGreater(p1.fire_timer, 0)

    def test_barra_de_ultra_enche(self):
        match, p1, p2, _ = um_contra_um()
        cesta(match, p1)
        self.assertAlmostEqual(p1.ultra, U.GAIN["cesta"])
        self.assertAlmostEqual(p2.ultra, U.GAIN["levou"])
        match._toco(p1, match.ball)
        match._toco(p1, match.ball)
        match._toco(p1, match.ball)
        self.assertEqual(p1.ultra, 1.0)


class OrbesTest(unittest.TestCase):
    def test_aparece_a_cada_12s(self):
        match, *_ = um_contra_um()
        match.orb_clock = 1
        run(match, 2)
        self.assertEqual(len(match.orbs), 1)

    def test_cada_orbe(self):
        match, p1, p2, _ = um_contra_um()
        for kind in U.ORB_ORDER:
            orb = U.spawn_orb(match, kind)
            p1.x, p1.y = orb.x, orb.y
            run(match, 2)
            self.assertNotIn(orb, match.orbs)
        self.assertGreater(p1.fire_timer, 0)
        self.assertGreater(p1.magnet_timer, 0)
        self.assertGreater(p1.speed_timer, 0)
        self.assertGreater(p1.shield_timer, 0)

    def test_escudo_aguenta_um_roubo(self):
        match, p1, p2, _ = um_contra_um()
        com_bola(match, p1)
        p1.shield_timer = 100
        p2.x, p2.y = p1.x + 20, p1.y
        p2.steal_timer = 10
        self.assertFalse(match._check_steal(p2))
        self.assertIs(match.holder, p1)
        self.assertEqual(p1.shield_timer, 0)


class UltrasTest(unittest.TestCase):
    def test_todos_os_herois_tem_ultra_e_rodam(self):
        for key in INDEX:
            with self.subTest(key):
                match, p1, p2, _ = um_contra_um(key, "atirador" if key != "atirador" else "tanque")
                self.assertIsNotNone(p1.ultra_power)
                com_bola(match, p1)
                p2.x, p2.y = p1.x + 60, p1.y
                p1.ultra = 1.0
                if not p1.ultra_power.ready(p1, match):
                    match._release(p1)            # Âncora: sem a bola
                self.assertTrue(match.use_power(p1), key)
                self.assertEqual(p1.ultra, 0.0)
                run(match, 240)

    def test_super_com_barra_cheia_sai_o_ultra(self):
        match, p1, _, inp = um_contra_um("atirador")
        com_bola(match, p1)
        p1.ultra = 1.0
        inp.tap("super")
        run(match, 2, [inp])
        self.assertGreater(p1.rain_timer, 0)              # Chuva de Três, não a Mão Quente
        self.assertEqual(p1.super_cd, 0)

    def test_chuva_de_tres_vale_4(self):
        match, p1, _, _ = um_contra_um("atirador")
        p1.rain_timer = 100
        cesta(match, p1, three=True)
        self.assertEqual(match.score[0], 4)

    def test_enterrada_do_meio_vale_3(self):
        match, p1, _, _ = um_contra_um("cauanzera")
        com_bola(match, p1, x=Court.W / 2)
        p1.ultra = 1.0
        self.assertTrue(match.use_power(p1))
        run(match, 200)
        self.assertEqual(match.score[0], 3)

    def test_matador_no_verde_vale_1_a_mais(self):
        match, p1, _, _ = um_contra_um("matador", human=False)
        p1.killer_timer = 100
        com_bola(match, p1)
        match.start_shot(p1)
        run(match, 10)
        match.release_shot(p1, 0.5)
        self.assertEqual(match.shot.get("bonus"), 1)

    def test_ancora_puxa_e_a_esquiva_anula(self):
        match, p1, p2, _ = um_contra_um("pirata")
        com_bola(match, p2, x=p1.x + 300, y=p1.y)
        p1.ultra = 1.0
        self.assertTrue(match.use_power(p1))
        self.assertIsNotNone(match.casting)               # o aviso: dá tempo de esquivar
        run(match, U.CAST_FRAMES + 2)
        self.assertIs(match.holder, p1)
        self.assertTrue(p2.stunned)
        # de novo, agora esquivando na hora
        match, p1, p2, _ = um_contra_um("pirata")
        com_bola(match, p2, x=p1.x + 300, y=p1.y)
        p1.ultra = 1.0
        match.use_power(p1)
        run(match, U.CAST_FRAMES - 6)
        U.mark_dodge(p2)
        run(match, 10)
        self.assertIs(match.holder, p2)
        self.assertFalse(p2.stunned)

    def test_ultra_de_defesa_segura(self):
        match, p1, p2, _ = um_contra_um("albeguinio", "guerreiro")
        p2.guard_timer = 100
        p1.ultra = 1.0
        match.use_power(p1)
        run(match, U.CAST_FRAMES + 2)
        self.assertFalse(p2.hacked)

    def test_tela_azul_trava_e_inverte(self):
        match, p1, p2, _ = um_contra_um("albeguinio")
        p1.ultra = 1.0
        match.use_power(p1)
        run(match, U.CAST_FRAMES + 2)
        self.assertTrue(p2.hacked)
        self.assertGreater(p2.invert_timer, 3 * config.FPS - 10)

    def test_muralha_do_aro_toca_ate_enterrada(self):
        match, p1, p2, _ = um_contra_um("cauanzera", "paredao")
        p2.ultra = 1.0
        com_bola(match, p2)
        match._release(p2)
        match.use_power(p2)
        self.assertGreater(p2.wall_ultra, 0)
        p2.no_catch = {}
        com_bola(match, p1)
        hx, hy = match.hoop_pos(match.hoop_of(p1.team))
        p1.x = hx + (-150 if hx > Court.W / 2 else 150)
        match.ball.reset(p1.x, p1.y)
        match.dunk(p1)
        run(match, 120)
        self.assertEqual(match.score, [0, 0])
        self.assertGreater(p2.blocks, 0)

    def test_assombracao_atravessa_a_tampa(self):
        match, p1, p2, _ = um_contra_um("fantasma", "tanque", human=False)
        match.lids[match.hoop_of(p1.team)] = 400
        p1.haunt_shots = 2
        com_bola(match, p1)
        match.start_shot(p1)
        run(match, 10)
        match.release_shot(p1, 0.5)
        self.assertTrue(match.shot.get("haunt"))
        self.assertEqual(p1.haunt_shots, 1)
        run(match, 200)
        self.assertGreater(match.score[0], 0)

    def test_cofre_devolve_a_bola(self):
        match, p1, p2, _ = um_contra_um("atirador", "tanque", human=False)
        p2.ultra = 1.0
        match.use_power(p2)
        com_bola(match, p1)
        match.start_shot(p1)
        run(match, 10)
        match.release_shot(p1, 0.5)
        for _ in range(200):
            run(match, 1)
            if match.holder is not None:
                break
        self.assertEqual(match.score[0], 0)
        self.assertIs(match.holder, p2)                    # a bola bateu na tampa e voltou para ele

    def test_trovao_sozinho_crava_na_tabela(self):
        match, p1, _, _ = um_contra_um("trovao")
        com_bola(match, p1)
        self.assertTrue(match.use_power(p1))            # SUPER: alley-oop para ele mesmo
        self.assertTrue(p1.alley_dunk)
        run(match, 200)
        self.assertEqual(match.score[0], 2)

    def test_hack_trava_o_unico_por_2s(self):
        match, p1, p2, _ = um_contra_um("albeguinio")
        self.assertTrue(match.use_power(p1))
        run(match, round(0.6 * config.FPS) + 40)
        self.assertTrue(p2.hacked)
        self.assertLessEqual(p2.hack_timer, 2 * config.FPS)
        self.assertEqual(p1.super_total, U.SOLO_SUPER + round(0.6 * config.FPS) + U.SOLO_HACK_FREEZE)

    def test_ninja_teleporta_com_a_bola(self):
        match, p1, _, _ = um_contra_um("ninja")
        com_bola(match, p1, x=Court.W / 2)
        x0 = p1.x
        self.assertTrue(match.use_power(p1))
        self.assertNotEqual(p1.x, x0)
        self.assertIs(match.holder, p1)

    def test_cpu_usa_o_ultra(self):
        g = game()
        g.session = Session("basket1", [SlotSetup(1, char=INDEX["guerreiro"], cpu=True),
                                        SlotSetup(2, char=INDEX["tanque"], cpu=True)])
        match = BasketballMatch(g, g.session)
        p1, p2 = match.fighters
        match.controllers[p2] = Parado()
        com_bola(match, p2)
        p1.ultra = 1.0
        for _ in range(600):
            match.update()
            if p1.ultra < 1.0:
                break
        self.assertLess(p1.ultra, 1.0)


class MenuTest(unittest.TestCase):
    def test_sem_p2_vira_cpu(self):
        import pygame
        from soulstrike.scenes.menus import start_mode
        from soulstrike.scenes.select import CharSelectScene, LobbyScene
        g = game()
        start_mode(g, "basket1")
        self.assertIsInstance(g.scene, LobbyScene)
        self.assertEqual(g.scene.slots, [1, 2])
        g.scene.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=0, unicode="\r"))
        self.assertIsInstance(g.scene, CharSelectScene)
        self.assertEqual([s.cpu for s in g.session.slots], [False, True])
        self.assertEqual(g.session.team_of(1), 0)
        self.assertEqual(g.session.team_of(2), 1)
