"""Duelo 2 x 2: times, sem fogo amigo, fim de round por time, levantar o companheiro,
escolha da divisão dos times no lobby e a CPU completando as vagas."""
import unittest

import pygame

from apoio import FakeInput, game

from soulstrike import config
from soulstrike.ai import FighterAI
from soulstrike.matches import REVIVE_FRAMES, REVIVE_HP, BattleMatch, SoccerMatch, TeamBattleMatch, create_match
from soulstrike.session import Session, SlotSetup


def dupla(layout="alternado", humans=(1,), map_key="arena_classica"):
    g = game()
    slots = [SlotSetup(s, char=s - 1, cpu=s not in humans) for s in (1, 2, 3, 4)]
    g.session = Session("duel2", slots, map_key=map_key, layout=layout)
    match = create_match(g, g.session)
    match.intro = 0
    inputs = {}
    for f in match.fighters:
        inp = FakeInput()
        match.controllers[f] = inp          # todo mundo parado, a não ser que o teste mexa
        inputs[f.slot] = inp
    return match, {f.slot: f for f in match.fighters}, inputs


def passo(match, inputs, frames=1):
    for _ in range(frames):
        match.update()
        for inp in inputs.values():
            inp.end_frame()


class TimesTest(unittest.TestCase):
    def test_cria_partida_de_times(self):
        match, f, _ = dupla()
        self.assertIsInstance(match, TeamBattleMatch)
        self.assertEqual(len(match.fighters), 4)
        self.assertEqual(f[1].team, f[3].team)
        self.assertEqual(f[2].team, f[4].team)
        self.assertNotEqual(f[1].team, f[2].team)
        # time azul começa à esquerda, vermelho à direita, sem ninguém dentro de parede
        for p in match.fighters:
            self.assertEqual(p.x < match.arena.width / 2, p.team == 0)
            self.assertFalse(any(w.rect.inflate(-2, -2).collidepoint(p.x, p.y) for w in match.arena.walls))

    def test_divisao_juntos(self):
        match, f, _ = dupla("juntos")
        self.assertEqual(f[1].team, f[2].team)
        self.assertEqual(f[3].team, f[4].team)
        self.assertNotEqual(f[1].team, f[3].team)

    def test_duelo_1x1_continua_igual(self):
        g = game()
        g.session = Session("duel", [SlotSetup(1), SlotSetup(2, char=1)])
        match = create_match(g, g.session)
        self.assertIs(type(match), BattleMatch)
        self.assertEqual(set(match.wins), set(match.fighters))

    def test_sem_fogo_amigo(self):
        match, f, inputs = dupla()
        ally, foe = f[3], f[2]
        ally.x, ally.y = f[1].x + 60, f[1].y
        match.spawn_bullet(f[1], 1.0, 0.0, 6, 20)
        passo(match, inputs, 20)
        self.assertEqual(ally.hp, ally.max_hp)
        # o golpe corpo a corpo também não pega no companheiro, só no adversário
        f[1].weapon_index = 1
        f[1].attack_cd = 0
        ally.x, ally.y = f[1].x + 30, f[1].y
        foe.x, foe.y = f[1].x + 34, f[1].y + 6
        f[1].attack(match, foe)
        self.assertEqual(ally.hp, ally.max_hp)
        self.assertLess(foe.hp, foe.max_hp)

    def test_round_so_acaba_quando_o_time_inteiro_cai(self):
        match, f, inputs = dupla()
        f[2].hp = 0
        passo(match, inputs, 3)
        self.assertEqual(match.round_end, 0)
        f[4].hp = 0
        passo(match, inputs, 3)
        self.assertGreater(match.round_end, 0)
        self.assertEqual(match.wins, {0: 1, 1: 0})
        self.assertIn("AZUL", match.round_banner[1])

    def test_tempo_esgotado_ganha_quem_tem_mais_vida_somada(self):
        match, f, inputs = dupla()
        f[1].hp = 10                      # azul: 10 + cheio
        f[2].hp = f[2].max_hp // 2        # vermelho: metade + metade
        f[4].hp = f[4].max_hp // 2
        match.time_left = 1
        passo(match, inputs, 2)
        azul = (10 + f[3].max_hp) / (f[1].max_hp + f[3].max_hp)
        vermelho = (f[2].hp + f[4].hp) / (f[2].max_hp + f[4].max_hp)
        self.assertEqual(match.wins[0] == 1, azul > vermelho)
        self.assertEqual(sum(match.wins.values()), 1)

    def test_vence_a_partida_e_resultado_do_time(self):
        match, f, inputs = dupla()
        match.wins[1] = config.ROUNDS_TO_WIN - 1
        f[1].hp = f[3].hp = 0
        passo(match, inputs, 2)
        passo(match, inputs, config.ROUND_END_FRAMES + 60)
        self.assertTrue(match.finished)
        self.assertEqual(match.result.title, "TIME VERMELHO VENCEU")
        self.assertEqual({w.slot for w in match.result.winners}, {2, 4})


class LevantarTest(unittest.TestCase):
    def test_companheiro_levanta_quem_caiu(self):
        match, f, inputs = dupla()
        f[2].x, f[2].y = 1500, 1000             # adversários longe
        f[4].x, f[4].y = 1500, 1100
        f[3].hp = 0
        f[1].x, f[1].y = f[3].x + 20, f[3].y
        passo(match, inputs, REVIVE_FRAMES + 5)
        self.assertTrue(f[3].alive_in_match)
        self.assertEqual(f[3].hp, round(f[3].max_hp * REVIVE_HP))
        # só uma vez por round
        f[3].hp = 0
        passo(match, inputs, REVIVE_FRAMES + 5)
        self.assertFalse(f[3].alive_in_match)
        self.assertFalse(match.can_revive(f[3]))

    def test_longe_nao_levanta(self):
        match, f, inputs = dupla()
        f[3].hp = 0
        f[1].x, f[1].y = f[3].x + 300, f[3].y
        passo(match, inputs, REVIVE_FRAMES + 5)
        self.assertFalse(f[3].alive_in_match)

    def test_novo_round_zera_os_levantamentos(self):
        match, f, inputs = dupla()
        match.revives[f[3]] = 1
        f[2].hp = f[4].hp = 0
        passo(match, inputs, config.ROUND_END_FRAMES + 30)
        self.assertEqual(match.round_no, 2)
        self.assertEqual(match.revives[f[3]], 0)

    def test_cpu_vai_levantar_o_companheiro(self):
        match, f, inputs = dupla(humans=())
        ai = FighterAI("normal")
        match.controllers[f[3]] = ai
        f[1].hp = 0
        f[3].x, f[3].y = f[1].x + 220, f[1].y
        f[2].x, f[2].y = f[1].x + 700, f[1].y + 300
        f[4].hp = 0                              # só um adversário em pé, longe
        start = f[3].distance_to(f[1])
        passo(match, inputs, 90)                 # (o Tanque é lento)
        self.assertLess(f[3].distance_to(f[1]), start - 120)


class AlvoTest(unittest.TestCase):
    def test_mira_no_adversario_para_onde_aponta(self):
        match, f, _ = dupla()
        me = f[1]
        me.x, me.y = 800, 600
        f[2].x, f[2].y = 1000, 600      # à direita, mais perto
        f[4].x, f[4].y = 800, 840       # embaixo, um pouco mais longe
        me.input = (0.0, 0.0)
        me.facing = (1.0, 0.0)
        self.assertIs(match.target_of(me), f[2])
        me.input = (0.0, 1.0)            # apontando para baixo
        self.assertIs(match.target_of(me), f[4])

    def test_caido_nao_e_alvo(self):
        match, f, _ = dupla()
        f[2].hp = 0
        self.assertIs(match.target_of(f[1]), f[4])


class MenusTest(unittest.TestCase):
    def test_lobby_completa_com_cpu_e_troca_os_times(self):
        from soulstrike.scenes.select import CharSelectScene, LobbyScene
        g = game()
        g.session = Session("duel2", [SlotSetup(1)] + [SlotSetup(s, cpu=True) for s in (2, 3, 4)])
        lobby = LobbyScene(g)
        self.assertEqual(lobby.layout_label(), "P1+P3 x P2+P4")
        lobby.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB, mod=0, unicode="\t"))
        self.assertEqual(g.session.layout, "juntos")
        self.assertEqual(lobby.layout_label(), "P1+P2 x P3+P4")
        lobby.joined.add(2)
        lobby._continue()
        self.assertEqual([s.cpu for s in g.session.slots], [False, False, True, True])
        scene = g.scene if isinstance(getattr(g, "scene", None), CharSelectScene) else CharSelectScene(g)
        teams = [g.session.team_of(c.slot) for c in scene.cards]
        self.assertEqual(teams, sorted(teams))           # cartões agrupados por time
        g.session.layout = "alternado"

    def test_futebol_respeita_a_divisao(self):
        g = game()
        slots = [SlotSetup(s, char=s - 1, cpu=True) for s in (1, 2, 3, 4)]
        g.session = Session("soccer2", slots, layout="juntos")
        match = SoccerMatch(g, g.session)
        by_slot = {p.slot: p for p in match.fighters}
        self.assertEqual(by_slot[1].team, by_slot[2].team)
        self.assertLess(by_slot[1].x, 800)
        self.assertLess(by_slot[2].x, 800)
        self.assertGreater(by_slot[3].x, 800)

    def test_modo_no_menu(self):
        from soulstrike.scenes.menus import ModeScene
        g = game()
        scene = ModeScene(g)
        self.assertIn("duel2", [v for _, v in scene.menu.options])


if __name__ == "__main__":
    unittest.main()
