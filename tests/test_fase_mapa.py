"""A fase num mapa só (como no Soul Knight): abertura, três salas de luta e a sala de recompensas
ligadas por corredores, as grades das salas de luta, o portal no fim e o mini mapa."""
import math
import unittest
from collections import deque

import pygame

from apoio import FakeInput, game

from soulstrike import config
from soulstrike.campaign import (FORCE_WAIT, PASSAGE_FRAMES, PHASES, TELEPORT_FRAMES, CampaignMatch, CampaignRun)
from soulstrike.data import CHARACTERS
from soulstrike.fase import ROOM_INTRO, PhaseMatch
from soulstrike.lobbies import LOBBY_SCENERY
from soulstrike.mapa_fase import MINI_H, MINI_W, T, PhaseLayout, cells_px
from soulstrike.session import Session, SlotSetup

KEYS = [c.key for c in CHARACTERS]


class _Input(FakeInput):
    def set_layout(self, name):
        pass


def fase(phase=0, chars=("guerreiro", "atirador")):
    g = game()
    g.session = Session("campaign", [SlotSetup(i + 1, char=KEYS.index(c)) for i, c in enumerate(chars)])
    run = CampaignRun(g.session)
    run.phase_index = phase
    run.begin_phase()
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
        p.x, p.y = match.arena.free_spot(x - 15 + 30 * (k % 2), y + 30 * (k // 2), p.radius)


def entrar(match, inputs, key):
    """O grupo todo entra na sala de luta ``key`` (pelo meio dela)."""
    room = match.layout.rooms[key]
    juntar(match, *room.rect.center)
    passo(match, inputs, 2)
    return room


def limpar(match, inputs, limit=4000):
    """Acaba com as ondas da sala onde o grupo está (até a sala abrir ou o portal aparecer)."""
    for _ in range(limit):
        passo(match, inputs)
        if match.state in ("fight", "between"):
            match.portals.clear()
            for e in match.alive_enemies:
                e.hp = 0
        if match.state in ("explore", "portal"):
            return True
    return False


def no_portal(match, inputs):
    for key in ("luta1", "luta2", "final"):
        entrar(match, inputs, key)
        limpar(match, inputs)
    return match.exit


def alcance(arena, start, radius=14, step=20):
    """Pontos do mapa (de ``step`` em ``step``) que dá para alcançar andando a partir de ``start``."""
    sx, sy = round(start[0] / step), round(start[1] / step)
    seen, todo = {(sx, sy)}, deque([(sx, sy)])
    w, h = arena.width // step, arena.height // step
    while todo:
        x, y = todo.popleft()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in seen and arena.is_free(nx * step, ny * step, radius):
                seen.add((nx, ny))
                todo.append((nx, ny))
    return seen


class DesenhoTest(unittest.TestCase):
    def test_cinco_salas_do_desenho(self):
        for phase in PHASES:
            layout = PhaseLayout.of(phase)
            rooms = layout.rooms
            self.assertEqual(list(rooms), ["abertura", "luta1", "luta2", "recompensa", "final"])
            boxes = [r.rect for r in rooms.values()]
            for i, r in enumerate(boxes):
                self.assertEqual(r.collidelist(boxes[:i] + boxes[i + 1:]), -1, phase.key)
            self.assertEqual([r.key for r in layout.fight_rooms], ["luta1", "luta2", "final"])
            self.assertEqual(layout.fight_rooms[0].dungeon, phase.dungeons[0])
            self.assertEqual(layout.fight_rooms[1].dungeon, phase.middle)
            self.assertEqual(layout.fight_rooms[2].dungeon, phase.dungeons[1])
            for room in layout.fight_rooms:                 # cada porta fica na borda da própria sala
                self.assertTrue(room.doors, (phase.key, room.key))
                for side, rect in room.doors:
                    edge = {"cima": rect.top == room.rect.top, "baixo": rect.bottom == room.rect.bottom,
                            "esquerda": rect.left == room.rect.left, "direita": rect.right == room.rect.right}
                    self.assertTrue(edge[side], (phase.key, room.key, side))
                    self.assertTrue(room.rect.contains(rect), (phase.key, room.key, side))

    def test_cruz_do_capitulo_1(self):
        """A 1ª fase do capítulo 1 continua o desenho do Cauã."""
        rooms = PhaseLayout.of(PHASES[0]).rooms
        a, l1, l2, rew, fin = (rooms[k].rect for k in rooms)
        self.assertLess(l1.bottom, a.top)                   # masmorra 1 em cima
        self.assertGreater(l2.left, a.right)                # a do meio à direita
        self.assertGreater(rew.top, l2.bottom)              # recompensa embaixo dela
        self.assertLess(fin.right, a.left)                  # a final embaixo à esquerda
        self.assertGreater(fin.bottom, a.bottom)
        self.assertEqual([side for side, _ in rooms["final"].doors], ["direita"])

    def test_um_formato_por_capitulo_espelhado(self):
        shapes = {1: "cruz", 2: "torre", 3: "corredor", 4: "patio"}
        for chapter, shape in shapes.items():
            layouts = [PhaseLayout.of(p) for p in PHASES if p.chapter == chapter]
            self.assertEqual(len(layouts), 3)
            self.assertEqual({lay.shape for lay in layouts}, {shape})
            self.assertEqual(layouts[0].flip, (False, False))
            self.assertEqual(layouts[1].flip, (True, False))       # a 2ª fase, espelhada de lado
            if shape != "torre":                                     # alguma sala trocou de lado
                side = [{k: r.rect.centerx < lay.rooms["abertura"].rect.centerx for k, r in lay.rooms.items()}
                        for lay in layouts[:2]]
                self.assertNotEqual(side[0], side[1], chapter)

    def test_torre_sobe_em_linha_reta(self):
        for phase in PHASES:
            if phase.chapter != 2:
                continue
            rooms = PhaseLayout.of(phase).rooms
            floors = [rooms[k].rect for k in ("abertura", "luta1", "recompensa", "luta2", "final")]
            for low, high in zip(floors, floors[1:]):
                self.assertLess(high.bottom, low.top, phase.key)       # cada andar em cima do outro
            self.assertEqual(sorted(s for s, _ in rooms["luta1"].doors), ["baixo", "cima"])
            self.assertEqual([s for s, _ in rooms["final"].doors], ["baixo"])

    def test_corredor_da_clinica_com_a_farmacia_de_lado(self):
        for phase in PHASES:
            if phase.chapter != 3:
                continue
            layout = PhaseLayout.of(phase)
            rooms = layout.rooms
            line = [rooms[k].rect for k in ("abertura", "luta1", "luta2", "final")]
            xs = [r.centerx for r in line]
            self.assertIn(xs, (sorted(xs), sorted(xs, reverse=True)), phase.key)   # tudo numa linha
            ys = {r.centery // T for r in line}
            self.assertLessEqual(max(ys) - min(ys), 1, phase.key)
            pharmacy = rooms["recompensa"].rect
            l1, l2 = rooms["luta1"].rect, rooms["luta2"].rect
            self.assertTrue(min(l1.centerx, l2.centerx) < pharmacy.centerx < max(l1.centerx, l2.centerx))
            self.assertFalse(l1.top < pharmacy.centery < l1.bottom, phase.key)    # de lado, fora da linha

    def test_patio_da_mansao_com_o_chefe_no_fundo(self):
        for phase in PHASES:
            if phase.chapter != 4:
                continue
            layout = PhaseLayout.of(phase)
            rooms = layout.rooms
            patio = cells_px(*layout.corridors[0])
            self.assertGreater(patio.w, 10 * T)
            for k in ("luta1", "luta2", "final", "abertura"):
                self.assertFalse(rooms[k].rect.colliderect(patio), (phase.key, k))
            l1, l2 = rooms["luta1"].rect, rooms["luta2"].rect
            self.assertLess(min(l1.right, l2.right), patio.centerx)              # uma de cada lado
            self.assertGreater(max(l1.left, l2.left), patio.centerx)
            gate, boss = rooms["abertura"].rect, rooms["final"].rect
            self.assertTrue(gate.top > patio.bottom > boss.bottom or gate.bottom < patio.top < boss.top,
                            phase.key)                                           # portão e salão opostos

    def test_tudo_se_alcanca_a_pe(self):
        for k, phase in enumerate(PHASES):
            match, _ = fase(k)
            for door in match.doors:                       # com todas as grades abertas
                door.state, door.bars = "open", 0.0
                door.sync_wall(match.arena)
            reach = alcance(match.arena, (match.players[0].x, match.players[0].y))
            for room in match.layout.rooms.values():
                inside = [(x, y) for x, y in reach if room.rect.collidepoint(x * 20, y * 20)]
                self.assertGreater(len(inside), 100, (phase.key, room.key))
            for stall in match.stalls:                     # dá para chegar perto de cada banca
                self.assertTrue(any(math.hypot(x * 20 - stall.x, y * 20 - stall.y) < stall.REACH
                                    for x, y in reach), (phase.key, stall.kind))
            for thing in (match.chest, match.armario):
                self.assertTrue(any(math.hypot(x * 20 - thing.x, y * 20 - thing.y) < 70 for x, y in reach),
                                (phase.key, type(thing).__name__))

    def test_largada_livre_e_cenario_do_acampamento(self):
        for k, phase in enumerate(PHASES):
            match, _ = fase(k, ("guerreiro", "atirador", "ninja", "geada"))
            for p in match.players:
                self.assertTrue(match.arena.is_free(p.x, p.y, 12), phase.key)
                self.assertEqual(match.layout.room_at(p.x, p.y).key, "abertura")
            self.assertEqual(match.arena.cfg.scenery, LOBBY_SCENERY.get(phase.theme, phase.theme))


class ComecoTest(unittest.TestCase):
    def test_comeca_na_abertura_em_paz(self):
        match, inputs = fase()
        passo(match, inputs, 3)
        self.assertTrue(match.lobby)
        self.assertEqual(match.state, "explore")
        self.assertEqual(match.here, "abertura")
        self.assertEqual(match.enemies, [])
        kinds = sorted((s.kind, s.mini) for s in match.stalls)
        self.assertEqual(kinds, [("altar", False), ("ferreiro", False), ("loja", False), ("loja", True)])
        self.assertIsNotNone(match.chest)
        self.assertIsNotNone(match.campfire)
        self.assertIsNotNone(match.armario)
        final = match.layout.rooms["final"]
        for door in match.doors:
            if door.room is final:
                self.assertEqual(door.state, "sealed")
                self.assertIn(door.wall, match.arena.walls)
            else:
                self.assertEqual(door.state, "open")
                self.assertNotIn(door.wall, match.arena.walls)
        self.assertIn("SALAS DE LUTA", match.objective_text)
        self.assertIsNotNone(match.objective())


class SalaDeLutaTest(unittest.TestCase):
    def test_entrar_fecha_as_grades_e_traz_quem_ficou(self):
        match, inputs = fase()
        p1, p2 = match.players
        room = match.layout.rooms["luta1"]
        door = match.doors_of(room)[0]
        p2.x, p2.y = door.front[0], door.front[1] + 100          # ficou no corredor
        p1.x, p1.y = room.rect.centerx, room.rect.bottom - 200   # entrou
        passo(match, inputs, 2)
        self.assertIs(match.fight_room, room)
        self.assertFalse(match.lobby)
        self.assertEqual(match.arena.room, room.rect)
        self.assertTrue(room.rect.collidepoint(p2.x, p2.y))     # apareceu do lado do P1
        self.assertEqual(door.state, "closed")
        passo(match, inputs, 30)
        self.assertIn(door.wall, match.arena.walls)              # a grade desceu: ninguém sai
        passo(match, inputs, ROOM_INTRO)
        self.assertEqual(match.state, "fight")
        self.assertTrue(match.portals or match.alive_enemies)
        for portal in match.portals:                             # os inimigos saem dentro da sala
            self.assertTrue(room.rect.collidepoint(portal.x, portal.y))

    def test_sala_limpa_abre_e_a_final_so_depois_das_outras(self):
        match, inputs = fase()
        final = match.layout.rooms["final"]
        entrar(match, inputs, "luta1")
        self.assertEqual(match.banner[:2], ("MASMORRA 1", PHASES[0].dungeons[0].name))
        self.assertTrue(limpar(match, inputs))
        self.assertEqual(match.state, "explore")
        self.assertIn("luta1", match.cleared)
        self.assertTrue(all(d.state == "open" for d in match.doors_of(match.layout.rooms["luta1"])))
        self.assertEqual(match.arena.room, pygame.Rect(0, 0, *match.arena.size))
        self.assertTrue(all(d.state == "sealed" for d in match.doors_of(final)))
        entrar(match, inputs, "luta2")
        self.assertTrue(limpar(match, inputs))
        self.assertTrue(all(d.state == "open" for d in match.doors_of(final)))
        self.assertIn("BAÚ", match.objective_text)
        juntar(match, *match.layout.rooms["luta1"].rect.center)   # sala limpa não fecha de novo
        passo(match, inputs, 5)
        self.assertIsNone(match.fight_room)

    def test_final_abre_o_portal(self):
        match, inputs = fase()
        portal = no_portal(match, inputs)
        self.assertEqual(match.state, "portal")
        self.assertTrue(match.layout.rooms["final"].rect.collidepoint(portal.x, portal.y))
        juntar(match, portal.x, portal.y)
        passo(match, inputs, PASSAGE_FRAMES + 2)
        self.assertEqual(match.state, "teleport")
        passo(match, inputs, TELEPORT_FRAMES + 2)
        self.assertTrue(match.finished and match.won)
        self.assertEqual(type(match.next_scene()).__name__, "UpgradeScene")

    def test_chefe_na_terceira_fase(self):
        match, inputs = fase(2)
        for key in ("luta1", "luta2"):
            entrar(match, inputs, key)
            limpar(match, inputs)
        room = entrar(match, inputs, "final")
        passo(match, inputs, ROOM_INTRO + 60)
        self.assertIsNotNone(match.boss)
        self.assertTrue(room.rect.collidepoint(match.boss.x, match.boss.y))
        self.assertIn("ARYEL", match.boss.stats.name.upper())


class PassagemDoPortalTest(unittest.TestCase):
    def test_falta_alguem_nao_vai(self):
        match, inputs = fase()
        portal = no_portal(match, inputs)
        p1, p2 = match.players
        p1.x, p1.y = portal.x, portal.y
        p2.x, p2.y = portal.x + 300, portal.y + 150
        passo(match, inputs, PASSAGE_FRAMES + 20)
        self.assertEqual(match.state, "portal")
        self.assertEqual(match.passage.missing, [p2])

    def test_p1_forca_depois_de_20_segundos(self):
        match, inputs = fase()
        portal = no_portal(match, inputs)
        p1, p2 = match.players
        p1.x, p1.y = portal.x, portal.y
        p2.x, p2.y = portal.x + 300, portal.y + 150
        passo(match, inputs, FORCE_WAIT + 5)
        self.assertTrue(match.passage.can_force)
        self.assertFalse(match.passage.try_force(match, p2))     # só o P1 (a coroa)
        inputs[1].tap("attack")
        passo(match, inputs, 1)
        self.assertEqual(match.state, "teleport")

    def test_sozinho_e_celular_caido(self):
        match, inputs = fase(chars=("guerreiro",))
        portal = no_portal(match, inputs)
        juntar(match, portal.x, portal.y)
        passo(match, inputs, 62)
        self.assertEqual(match.state, "teleport")
        match, inputs = fase(chars=("guerreiro", "atirador", "ninja"))
        portal = no_portal(match, inputs)
        juntar(match, portal.x, portal.y)
        p3 = match.players[2]
        self.assertNotIn(3, match.present_slots())                # vaga 3 sem celular
        p3.x, p3.y = portal.x + 300, portal.y + 100
        passo(match, inputs, PASSAGE_FRAMES + 2)
        self.assertEqual(match.state, "teleport")


class PerigosNaSalaTest(unittest.TestCase):
    def test_laser_so_dentro_da_sala(self):
        k = next(i for i, p in enumerate(PHASES) if p.dungeons[0].hazard == "laser")
        match, inputs = fase(k)
        room = entrar(match, inputs, "luta1")
        passo(match, inputs, ROOM_INTRO + 2)
        hazard = match.hazard
        self.assertIsNotNone(hazard)
        for _ in range(400):
            passo(match, inputs)
            if hazard.beams:
                break
        for beam in hazard.beams:
            span = (room.rect.x, room.rect.w) if beam.axis == "h" else (room.rect.y, room.rect.h)
            self.assertEqual((beam.start, beam.length), span)
            pos = beam.pos
            self.assertTrue((room.rect.top if beam.axis == "h" else room.rect.left) < pos
                            < (room.rect.bottom if beam.axis == "h" else room.rect.right))

    def test_registros_e_cabos_dentro_da_sala(self):
        k = next(i for i, p in enumerate(PHASES) if p.dungeons[1].hazard == "vapor")
        match, inputs = fase(k)
        for key in ("luta1", "luta2"):
            entrar(match, inputs, key)
            limpar(match, inputs)
        room = entrar(match, inputs, "final")
        for valve in match.hazard.valves:
            self.assertTrue(room.rect.collidepoint(valve.x, valve.y))


class InimigoPresoForaTest(unittest.TestCase):
    """Os drones do chefe do capítulo 2 nasciam no corredor, atrás da grade: ninguém alcançava e a
    sala nunca ficava limpa."""

    def _sala(self, phase=0):
        match, inputs = fase(phase)
        room = entrar(match, inputs, "luta1")
        passo(match, inputs, ROOM_INTRO + 2)
        return match, inputs, room

    def test_chamado_do_chefe_abre_portais_dentro_da_sala(self):
        match, inputs, room = self._sala()
        match.portals.clear()
        for x, y in (room.rect.topleft, room.rect.bottomright, (room.rect.right - 20, room.rect.centery)):
            near = type("P", (), {"x": x, "y": y})()
            match.summon(("drone",) * 4, near)
        self.assertTrue(match.portals)
        for portal in match.portals:
            self.assertTrue(room.rect.inflate(-20, -20).collidepoint(portal.x, portal.y), (portal.x, portal.y))

    def test_ponto_livre_nao_sai_da_sala(self):
        match, inputs, room = self._sala()
        for x, y in ((room.rect.left - 200, room.rect.top - 200), (room.rect.right + 150, room.rect.centery)):
            fx, fy = match.arena.free_spot(x, y, 20)
            self.assertTrue(room.rect.collidepoint(fx, fy))
        for x, y in ((room.rect.left - 300, room.rect.top - 300), (-500, -500)):   # nem no vazio de fora
            match.arena.reset_room()
            fx, fy = match.arena.free_spot(x, y, 20)
            if match.arena.is_free(fx, fy, 20):
                self.assertIsNotNone(next((r for r in match.arena.walkable if r.collidepoint(fx, fy)), None))

    def test_inimigo_que_escapa_volta_para_dentro(self):
        match, inputs, room = self._sala()
        match.portals.clear()
        e = match.spawn_now("drone", *room.rect.center)
        e.x, e.y = room.rect.right + 120, room.rect.centery      # foi parar no corredor
        passo(match, inputs, 2)
        self.assertTrue(room.rect.collidepoint(e.x, e.y))


class MiniMapaTest(unittest.TestCase):
    def test_pequeno_no_canto_e_marca_onde_foi(self):
        match, inputs = fase()
        passo(match, inputs, 2)
        rect = match.minimap_rect()
        self.assertLessEqual(rect.w, MINI_W)
        self.assertLessEqual(rect.h, MINI_H)
        self.assertEqual(rect.right, config.SCREEN_W - 12)
        self.assertGreaterEqual(rect.top, 40)                    # embaixo dos CONTINUES
        self.assertEqual(match.visited, {"abertura"})
        entrar(match, inputs, "luta1")
        self.assertEqual(match.here, "luta1")
        self.assertIn("luta1", match.visited)
        match.draw(match.game.screen, match.game.ui)


class FluxoTest(unittest.TestCase):
    def test_tres_fases_de_ponta_a_ponta(self):
        """Casa → abertura → salas a pé → portal, nas 3 fases do capítulo 1."""
        from soulstrike.scenes.campaign import StoryScene, UpgradeScene, start_phase
        match, _ = fase()
        g, run = match.game, match.run
        real = g.inputs
        g.inputs = {s: _Input() for s in (1, 2, 3, 4)}
        try:
            for phase in range(3):
                run.phase_index = phase
                scene = start_phase(g, run, story=False)
                m = scene.match
                self.assertIsInstance(m, PhaseMatch)
                ins = {f.slot: m.controllers[f] for f in m.players}
                for key in ("luta1", "luta2"):
                    entrar(m, ins, key)
                    limpar(m, ins)
                juntar(m, m.chest.x - 40, m.chest.y + 30)
                passo(m, ins, 2)
                ins[1].tap("attack")
                passo(m, ins, 120)
                for f, item in zip(m.players, list(m.ground)):    # cada um pega uma arma do chão
                    f.x, f.y = item.x + 10, item.y
                    ins[f.slot].tap("attack")
                    passo(m, ins, 1)
                portal = no_portal(m, ins)
                juntar(m, portal.x, portal.y)
                passo(m, ins, PASSAGE_FRAMES + TELEPORT_FRAMES + 10)
                self.assertTrue(m.finished and m.won, phase)
                self.assertIsInstance(m.next_scene(), StoryScene if phase == 2 else UpgradeScene)
                self.assertTrue(all(run.relics.values()))
        finally:
            g.inputs = real

    def test_reuniao_dos_corrompidos_vai_direto_ao_chefe(self):
        from soulstrike.scenes.campaign import start_phase
        match, _ = fase()
        g, run = match.game, match.run
        run.start_rush()
        scene = start_phase(g, run)
        self.assertIsInstance(scene.match, CampaignMatch)
        self.assertNotIsInstance(scene.match, PhaseMatch)


if __name__ == "__main__":
    unittest.main()
