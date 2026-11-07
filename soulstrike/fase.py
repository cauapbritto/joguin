"""A partida da fase inteira num mapa só (mapa_fase): o grupo anda a pé da abertura até o portal.

* ABERTURA: o grupo chega pelo portal da Casa da turma; a lojinha e o altar ficam aqui.
* SALAS DE LUTA (as três masmorras da fase): quando alguém entra, as grades das portas descem, quem
  ficou para trás aparece do lado dele e as ondas começam. Sala limpa, as grades sobem.
* A sala FINAL fica trancada (grade roxa) até as outras duas ficarem limpas. Limpou a final, aparece
  o portal da próxima fase (na 3ª fase do capítulo, a sala do chefe).
* RECOMPENSAS (depois da sala do meio): baú, fogueira, loja, ferreiro e armário.

A luta em si (ondas, caídos, continues, perigos, chefes) é a de ``CampaignMatch``: a sala de luta
onde o grupo está vira a "masmorra" da vez e ``arena.room`` aponta para ela."""
import math
import random

import pygame

from . import config, crt, enfeites, hud, mascotes, theme
from .armario import RACK_SIZE, Armario
from .campaign import CampaignMatch, CoopMatch, _center, _spread
from .data import PHASE_RELICS, RARE_WEAPONS
from .dungeon import Campfire, Chest, RelicDrop
from .hazards import make_hazard
from .mapa_fase import PhaseArena, PhaseLayout, RoomDoor, draw_minimap, minimap_rect
from .market import MarketMenu, Stall
from .progress import chapter_cleared

ROOM_INTRO = 70               # quadros entre a grade descer e a primeira onda sair
ENTER_DEPTH = 70              # quanto o primeiro precisa entrar na sala para ela fechar
MINI_TOP = 44                 # o mapinha fica embaixo dos CONTINUES


class PhaseMatch(CampaignMatch):
    """A fase inteira. Fora das salas de luta é acampamento (sem ondas); dentro de uma, é masmorra."""

    music = "camp"

    def __init__(self, game, run):
        self.layout = PhaseLayout.of(run.phase)
        arena = PhaseArena(self.layout, game.assets)
        markers = self.layout.markers
        starts = _spread(markers["S"], len(run.session.slots))
        CoopMatch.__init__(self, game, run, None, starts, (0.0, -1.0), arena=arena)
        self.dungeon = None
        self.dungeon_index = 0
        self._setup_combat()
        self.state = "explore"
        self.fight_room = None
        self.cleared = set()
        self.visited = {"abertura"}
        self.here = "abertura"
        self.style = "lag" if run.phase.chapter == 2 else None     # cofre e bancas da Lag Lobby
        self.doors = []
        for room in self.layout.fight_rooms:
            for side, rect in room.doors:
                door = RoomDoor(room, side, rect, "sealed" if room.final else "open")
                self.doors.append(door)
                door.sync_wall(self.arena)
        self.props += self.doors
        self.stalls = []
        lojinha, loja = sorted(markers["L"], key=lambda p: p[1])     # a da abertura fica mais em cima
        self._stall("loja", lojinha, mini=True)                     # a lojinha: só o básico
        self._stall("altar", markers["X"][0])                       # desafio opcional da fase
        self._stall("loja", loja)
        self._stall("ferreiro", markers["R"][0])
        fx, fy = _center(markers["F"])
        self.campfire = Campfire(fx, fy, run.phase.chapter)
        self.arena.walls.append(self.campfire.wall)
        self.props.append(self.campfire)
        self.chest = None
        if not run.chest_open:
            cx, cy = markers["C"][0]
            self.chest = Chest(cx, cy, self.style, run.phase.chapter)
            self.arena.walls.append(self.chest.wall)
            self.props.append(self.chest)
        x, y = markers["K"][0]
        self.armario = Armario(x, y, run, self.style, run.phase.chapter)
        self.arena.walls.append(self.armario.wall)
        self.props.append(self.armario)
        enfeites.furnish(self, self.layout.rows, run.phase.chapter, joke=True)
        mascotes.join(self)                 # os bichos adotados na Casa vêm junto com os donos
        if chapter_cleared(4) and self.players:    # recompensa do capítulo 4: a IARA mascote
            from .mansao import IaraMascot
            self.add_effect(IaraMascot(self.players[0], self.assets.sprites.get("iara_nucleo")))
        for p in self.players:              # chegando pelo portal
            self.burst(p.x, p.y - 20, (200, 180, 255), 14, speed=3)

    def _stall(self, kind, at, mini=False):
        stall = Stall(kind, *at, self.style, mini=mini, chapter=self.run.phase.chapter)
        self.stalls.append(stall)
        self.arena.walls.append(stall.wall)
        self.props.append(stall)
        return stall

    # ── consultas ────────────────────────────
    @property
    def lobby(self):
        """Fora das salas de luta: acampamento (música calma, energia não volta sozinha...)."""
        return self.fight_room is None

    @property
    def last(self):
        return self.fight_room is not None and self.fight_room.final

    @property
    def waves(self):
        return self.dungeon.waves if self.dungeon is not None else ()

    @property
    def locked(self):
        return CoopMatch.locked.fget(self) or self.state in ("gameover", "teleport")

    def rooms_left(self):
        """Salas de luta que faltam antes da final."""
        return [r for r in self.layout.fight_rooms if not r.final and r.key not in self.cleared]

    def doors_of(self, room):
        return [d for d in self.doors if d.room is room]

    def objective(self):
        if self.fight_room is not None:
            return super().objective()
        left = self.rooms_left()
        if left:
            room = left[0]
        elif self.chest is not None and self.chest.state == "closed":
            return self.chest.x, self.chest.y
        else:
            room = self.layout.rooms["final"]
        door = min(self.doors_of(room), key=lambda d: math.hypot(d.x - self.players[0].x, d.y - self.players[0].y))
        return door.front

    @property
    def objective_text(self):
        if self.fight_room is not None:
            return super().objective_text
        if self.rooms_left():
            return "NAS SALAS DE LUTA AS PORTAS FECHAM ATÉ DERROTAREM TODOS"
        if self.chest is not None and self.chest.state == "closed":
            return f"ABRAM {'O COFRE' if self.style == 'lag' else 'O BAÚ'} NA SALA DE RECOMPENSAS"
        final = self.layout.rooms["final"]
        return "A SALA DO CHEFE ABRIU" if final.dungeon.boss_spot else "A ÚLTIMA SALA ABRIU: O PORTAL ESTÁ LÁ"

    # ── ciclo ────────────────────────────────
    def update_stage(self):
        if self.frame == 1:
            self._set_banner(f"FASE {self.run.phase_index + 1}", self.phase.name, theme.BRASS)
        if self.fight_room is None and self.banner and self.banner[3] > 110:
            self.banner = None
        self._track()
        if self.fight_room is None and not self.leaving:
            room = self._entering()
            if room is not None:
                self._enter(room)
        super().update_stage()

    def _track(self):
        """Sala onde o grupo está (o mapinha) e as que ele já viu."""
        alive = self.alive_players or self.players
        x = sum(p.x for p in alive) / len(alive)
        y = sum(p.y for p in alive) / len(alive)
        room = self.layout.room_at(x, y)
        self.here = room.key if room is not None else None
        for p in alive:
            seen = self.layout.room_at(p.x, p.y)
            if seen is not None:
                self.visited.add(seen.key)

    def _entering(self):
        for room in self.layout.fight_rooms:
            if room.key in self.cleared:
                continue
            inside = room.rect.inflate(-2 * ENTER_DEPTH, -2 * ENTER_DEPTH)
            for p in self.alive_players:
                if inside.collidepoint(p.x, p.y):
                    return room
        return None

    def _enter(self, room):
        """Alguém entrou numa sala de luta: as grades descem, quem ficou fora aparece do lado dele e,
        daqui a pouco, a primeira onda sai."""
        leader = next(p for p in self.alive_players if room.rect.inflate(-2 * ENTER_DEPTH, -2 * ENTER_DEPTH)
                      .collidepoint(p.x, p.y))
        self.fight_room = room
        self.dungeon = room.dungeon
        self.dungeon_index = room.order
        self.arena.room = pygame.Rect(room.rect)
        self._reset_room()
        self.hazard = make_hazard(self.dungeon.hazard, self.arena)
        inside = room.rect.inflate(-80, -80)
        for p in self.players:
            if not inside.collidepoint(p.x, p.y):
                self._bring(p, leader)
        for door in self.doors_of(room):
            door.state = "closed"
        self.state, self.state_timer = "intro", ROOM_INTRO
        title = room.dungeon.name if not room.final or not room.dungeon.boss_spot else "SALA DO CHEFE"
        self._set_banner(f"MASMORRA {room.order + 1}", title, theme.BLOOD if room.final else theme.BRASS)
        self.visited.add(room.key)
        self.assets.play("barrier", 0.5)
        self.assets.music("battle")
        self.camera.shake(4)

    def _bring(self, p, leader):
        """Quem ficou fora da sala aparece do lado de quem entrou (na fumaça)."""
        self.burst(p.x, p.y - 16, (200, 200, 210), 14, speed=4)
        x, y = self.arena.free_spot(leader.x + random.uniform(-40, 40), leader.y + random.uniform(-30, 30), p.radius)
        p.x, p.y = x, y
        p.prev_pos = (x, y)
        p.vx = p.vy = 0.0
        p.teleport_flash = 20
        self.burst(x, y - 16, p.color, 14, speed=4)

    def _update_state(self):
        if self.state == "explore":
            return
        if self.state == "intro":
            if self.state_timer == 0:
                self.state = "ready"
                self.start_battle()
            return
        super()._update_state()

    def start_battle(self, f=None):
        if self.state != "ready":
            return False
        self._set_banner("VALENDO!", None, theme.BLOOD)
        self._start_wave(0)
        self.state = "fight"
        return True

    def _open_exit(self):
        """Sala limpa: a final abre o portal; as outras levantam as grades."""
        room = self.fight_room
        if room.final:
            super()._open_exit()
            return
        self.cleared.add(room.key)
        for door in self.doors_of(room):
            door.state = "open"
        self.fight_room = None
        self.dungeon = None
        self.hazard = None
        self.arena.reset_room()
        self.state = "explore"
        self.banner = None
        self.assets.play("barrier", 0.4)
        self.assets.music("camp")
        if not self.rooms_left():
            final = self.layout.rooms["final"]
            for door in self.doors_of(final):
                door.state = "open"
                self.popup(door.x, door.y - 60, "ABRIU!", theme.MOSS)
            self._set_banner("A ÚLTIMA SALA ABRIU", self.phase.name, theme.MOSS)

    def _clear(self):
        super()._clear()
        if not self.last:
            self.cleared.add(self.fight_room.key)

    # ── botão de ação ────────────────────────
    def rack_near(self, f):
        return self.armario if self.armario.can_use(f) else None

    def interact(self, f):
        if self.fight_room is not None:
            if super().interact(f):
                return True
        if self.chest is not None and self.chest.can_open(f):
            self.chest.open(self)
            self.run.chest_open = True
            return True
        if self.armario.can_use(f):
            if self.droppable(f) and len(self.run.rack) < RACK_SIZE:
                return self.store_in_rack(f)
            return self.take_from_rack(f) or True
        stall = next((s for s in self.stalls if s.can_use(f)), None)
        if stall is not None:
            self.menus[f] = MarketMenu(self, f, stall)
            self.assets.play("loja", 0.45)
            return True
        return self.pick_ground(f)

    def launch_relics(self, chest):
        """O baú solta uma arma rara para cada jogador: armas diferentes entre si e, se der, que
        ninguém do grupo já tenha (a que cada um tinha fica no chão)."""
        held = {p.relic for p in self.players if p.relic is not None}
        phase = [RARE_WEAPONS[k] for k in PHASE_RELICS.get(self.run.phase.key, RARE_WEAPONS)]
        pool = [w for w in phase if w not in held]
        random.shuffle(pool)
        for p in self.players:
            choices = [w for w in pool if w is not p.relic] or \
                [w for w in phase if w is not p.relic] or \
                [w for w in RARE_WEAPONS.values() if w is not p.relic and not w.forjada]
            weapon = choices[0]
            if weapon in pool:
                pool.remove(weapon)
            self.props.append(RelicDrop(chest, p, weapon))

    # ── desenho ──────────────────────────────
    def draw_screen_layer(self, screen, ui):
        super().draw_screen_layer(screen, ui)
        cam = self.camera
        if self.chest is not None:
            near = any(self.chest.can_open(p) for p in self.alive_players)
            self.chest.draw_prompt(screen, cam, ui, self.frame, near)
        near = [p for p in self.alive_players if self.armario.can_use(p) and p not in self.menus]
        self.armario.draw_prompt(screen, cam, ui, self.frame, self.rack_prompt(near[0]) if near else "")
        for stall in self.stalls:
            near = any(stall.can_use(p) and p not in self.menus for p in self.alive_players)
            stall.draw_prompt(screen, cam, ui, self.frame, near)
        for f, menu in self.menus.items():
            at = cam.to_screen(f.x, f.y)
            crt.panel(screen, ("loja", f.slot), lambda s, menu=menu, at=at: menu.draw(s, ui, at))
        for door in self.doors:
            if door.state == "sealed" and any(math.hypot(p.x - door.x, p.y - door.y) < 220 for p in self.alive_players):
                sx, sy = cam.to_screen(*door.front)
                ui.text(screen, "TRANCADA: LIMPEM AS OUTRAS SALAS", theme.XS, (200, 150, 250), (round(sx), round(sy) - 30))

    def minimap_rect(self):
        return minimap_rect(self.layout, config.SCREEN_W - 12, MINI_TOP)

    def draw_hud(self, screen, ui):
        hud.draw_campaign(screen, ui, self)
        portal = self.state in ("portal", "teleport")
        draw_minimap(screen, ui, self.layout, self.visited, self.here, self.minimap_rect(), portal)

    def hud_regions(self):
        return super().hud_regions() + [self.minimap_rect().inflate(4, 4)]
