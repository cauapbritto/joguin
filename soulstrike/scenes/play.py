"""Tela de apresentação (VS), a partida em si e o resultado."""
import math

import pygame

from .. import config, crt, settings, theme
from ..stats import record as record_stats
from ..arena import MAPS_BY_KEY
from ..host import IdleInput, anyone_pauses, change_rule, fighter_of, host_slot, make_cpu, make_human, rules
from ..data import CHARACTERS
from ..matches import create_match
from ..net.remote import hub
from ..ui import MenuList, darken, mix
from .base import Scene, crown
from .menus import TitleScene, _MenuScene


def _scaled(img, factor):
    return pygame.transform.scale(img, (img.get_width() * factor, img.get_height() * factor))


class VersusScene(Scene):
    phase = "select"
    music = None
    show_cursor = False
    DURATION = 150

    def __init__(self, game):
        super().__init__(game)
        self.session = game.session
        self.match = create_match(game, self.session)
        self.assets.stop_music(800)

    def handle(self, event):
        skip = event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE)
        if skip and self.ticks > 30:
            self._start()

    def update(self):
        super().update()
        if self.ticks == 22:
            self.sfx("confirm", 0.6)
        if self.ticks >= self.DURATION:
            self._start()

    def _start(self):
        self.game.change(PlayScene(self.game, self.match))

    def draw(self, screen):
        W, H = config.SCREEN_W, config.SCREEN_H
        t = self.ticks
        soccer = self.session.soccer
        teams = soccer or self.session.team_mode
        sides = [[s for s in self.session.slots if self.session.team_of(s.slot) == team] for team in (0, 1)] \
            if teams else [[self.session.slots[0]], [self.session.slots[1]]]
        colors = [theme.TEAM_COLORS[0], theme.TEAM_COLORS[1]] if teams else [sides[0][0].color, sides[1][0].color]

        screen.fill(theme.INK)
        tilt = 60
        left = [(0, 0), (W // 2 + tilt, 0), (W // 2 - tilt, H), (0, H)]
        right = [(W // 2 + tilt, 0), (W, 0), (W, H), (W // 2 - tilt, H)]
        pygame.draw.polygon(screen, mix(colors[0], theme.INK, 0.72), left)
        pygame.draw.polygon(screen, mix(colors[1], theme.INK, 0.72), right)
        pygame.draw.line(screen, theme.BONE, (W // 2 + tilt, 0), (W // 2 - tilt, H), 4)

        ease = 1 - (1 - min(1.0, t / 24)) ** 3
        ground = H // 2 + 96
        for side, slots in enumerate(sides):
            direction = 1 if side == 0 else -1
            for k, setup in enumerate(slots):
                stats = CHARACTERS[setup.char]
                sprites = self.assets.kit_sprites(stats.key, side) if soccer else self.assets.sprites[stats.key]
                img = sprites.pose("direita" if side == 0 else "esquerda", "parado", 0)
                factor = 3 if len(slots) == 1 else 2
                img = _scaled(img, factor)
                spread = 0 if len(slots) == 1 else (k * 2 - 1) * 70
                base_x = W // 4 if side == 0 else W * 3 // 4
                x = base_x + spread - direction * int((1 - ease) * W // 2)
                gy = ground + (k * 20 if len(slots) > 1 else 0)
                pygame.draw.ellipse(screen, theme.SHADOW, (x - 40, gy - 8, 80, 16))
                screen.blit(img, img.get_rect(midbottom=(x, gy + 4)))
                if len(slots) == 1:
                    self.ui.text(screen, stats.name.upper(), theme.M, theme.BONE, (base_x, ground + 44))
                    self.ui.text(screen, setup.name, theme.XS, colors[side], (base_x, ground + 70))
                else:
                    self.ui.text(screen, setup.label, theme.XS, setup.color, (x, gy + 24))
            if teams and len(slots) > 1:
                self.ui.text(screen, f"TIME {theme.TEAM_NAMES[side]}", theme.S, theme.BONE,
                             (W // 4 if side == 0 else W * 3 // 4, 80))

        if t > 20:
            pop = 1 + max(0.0, 0.6 - (t - 20) * 0.06)
            size = theme.XL
            vs = self.assets.text("VS", size, theme.BRASS)
            ink = self.assets.text("VS", size, theme.SHADOW)
            if pop > 1:
                vs = pygame.transform.scale(vs, (int(vs.get_width() * pop), int(vs.get_height() * pop)))
                ink = pygame.transform.scale(ink, vs.get_size())
            r = vs.get_rect(center=(W // 2, H // 2 - 30))
            for dx, dy in ((-3, 0), (3, 0), (0, -3), (0, 4), (3, 4), (-3, 4)):
                screen.blit(ink, r.move(dx, dy))
            screen.blit(vs, r)

        if self.session.basket:
            place = MAPS_BY_KEY[self.session.map_key].name.upper() if self.session.map_key in MAPS_BY_KEY else "QUADRA"
        else:
            place = "ESTÁDIO" if soccer else MAPS_BY_KEY[self.session.map_key].name.upper()
        self.ui.text(screen, place, theme.XS, theme.MUTED, (W // 2, H - 24))


class PlayScene(Scene):
    """A partida. O START do dono da partida (P1, a coroa) abre o PAINEL DA PARTIDA e pausa; o dos
    outros abre um menu só para quem apertou, e a partida continua (no treino ou com um jogador só,
    qualquer um pausa). Um controle novo que aperta START assume uma CPU sem reiniciar."""

    phase = "playing"
    music = "arena"
    show_cursor = False
    REQUEST_FRAMES = 4 * config.FPS

    def __init__(self, game, match):
        super().__init__(game)
        self.match = match
        self.music = getattr(match, "music", "arena")     # acampamento tem a sua música calma
        self.paused = False
        self.panel = "main"             # main | rules | som | confirm
        self.row = 0                    # linha das regras / do som
        self.personal = {}              # vaga → MenuList do menu pessoal (aberto sem pausar)
        self.request = None             # (vaga que pediu pausa, quadros restantes)
        self.joined = None              # (texto, quadros) quando alguém entra no meio
        self.confirm_menu = MenuList([("NÃO, CONTINUAR", "back"), ("SIM, SAIR", "quit_now")],
                                     topleft=(config.SCREEN_W // 2 - 156, 266), width=312)
        self.main_menu = self._build_main()
        self.pause_menu = self.main_menu

    # ── quem manda ───────────────────────────
    @property
    def host(self):
        return host_slot(self.game.session)

    def _build_main(self):
        session = self.game.session
        campaign = bool(session and session.campaign)
        options = [("CONTINUAR", "resume"), ("REINICIAR FASE" if campaign else "REINICIAR", "restart")]
        if rules(self.game, self.match):
            options.append(("REGRAS DA PARTIDA", "rules"))
        if session is not None and not campaign:
            options.append(("TROCAR PERSONAGENS", "select"))
        options += [("SOM E TELA", "som"), ("SAIR PARA O MENU", "quit")]
        return MenuList(options, topleft=(config.SCREEN_W // 2 - 300, 166), width=330, row_h=34)

    @property
    def confirming(self):
        return self.paused and self.panel == "confirm"

    def _set_paused(self, value):
        self.paused = value
        pygame.mouse.set_visible(value)       # mouse só aparece no menu de pausa (e no teletransporte)
        self._cursor = value
        self.main_menu = self._build_main()
        self.panel, self.row = "main", 0
        self.pause_menu = self.main_menu
        self.request = None
        hub.set_phase("paused" if value else "playing", active=self.active_slots())
        self.sfx("click", 0.5)
        self.assets.pause_music(value)

    # ── comandos (teclado, mouse, controle e celular viram a mesma coisa) ──
    def handle(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_p and not self.paused:
            self._set_paused(True)
            return
        if not self.paused:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self._set_paused(True)
            return
        if event.type == pygame.KEYDOWN:
            cmd = {pygame.K_UP: "up", pygame.K_w: "up", pygame.K_DOWN: "down", pygame.K_s: "down",
                   pygame.K_LEFT: "left", pygame.K_a: "left", pygame.K_RIGHT: "right", pygame.K_d: "right",
                   pygame.K_RETURN: "ok", pygame.K_SPACE: "ok", pygame.K_KP_ENTER: "ok",
                   pygame.K_ESCAPE: "back", pygame.K_p: "back", pygame.K_BACKSPACE: "back"}.get(event.key)
            if cmd:
                self._command(cmd)
        elif self.panel in ("main", "confirm"):
            choice = self.pause_menu.handle(event, self.sfx)
            if choice:
                self._choose(choice)

    def _command(self, cmd):
        if self.panel in ("main", "confirm"):
            if cmd == "up":
                self.pause_menu.move(-1)
                self.sfx("select", 0.25)
            elif cmd == "down":
                self.pause_menu.move(1)
                self.sfx("select", 0.25)
            elif cmd == "ok":
                self._choose(self.pause_menu.value)
            elif cmd == "back":
                if self.panel == "confirm":
                    self._choose("back")
                else:
                    self._set_paused(False)
            return
        rows = self._rows()
        if cmd == "back" or (cmd == "ok" and self.panel == "rules"):
            self.panel = "main"
            self.sfx("cancel", 0.3)
            return
        if not rows:
            return
        if cmd in ("up", "down"):
            self.row = (self.row + (1 if cmd == "down" else -1)) % len(rows)
            self.sfx("select", 0.25)
        elif cmd in ("left", "right", "ok"):
            self._change_row(rows[self.row], -1 if cmd == "left" else 1)

    def _rows(self):
        if self.panel == "rules":
            return rules(self.game, self.match)
        if self.panel == "som":
            return [("volume_geral", "VOLUME GERAL"), ("volume_musica", "MÚSICA"), ("volume_efeitos", "EFEITOS"),
                    ("tremor", "TREMOR DE TELA")]
        return []

    def _change_row(self, row, step):
        if self.panel == "rules":
            key, _, options, current = row
            values = [v for v, _ in options]
            i = values.index(current) if current in values else 0
            change_rule(self.game, self.match, key, values[(i + step) % len(values)])
            self.sfx("click", 0.4)
            return
        key = row[0]
        if key in settings.VOLUME_KEYS:
            value = settings.get(key)
            settings.change(key, round(value + step * settings.VOLUME_STEP, 2))
            self.assets.apply_music_volume()
            self.sfx("hit", 0.4)
        else:
            settings.change(key, not settings.get(key))
            self.sfx("click", 0.4)

    def _choose(self, choice):
        session = self.game.session
        if choice == "resume":
            self._set_paused(False)
        elif choice == "restart":
            self.assets.pause_music(False)
            self.game.change(self.match.restart_scene() or VersusScene(self.game))
        elif choice in ("rules", "som"):
            self.panel, self.row = choice, 0
            self.sfx("confirm", 0.4)
        elif choice == "select":
            self.assets.pause_music(False)
            from .select import CharSelectScene
            self.game.change(CharSelectScene(self.game))
        elif choice == "quit" and session and session.campaign:
            self.panel = "confirm"
            self.pause_menu = self.confirm_menu
            self.pause_menu.index = 0
        elif choice == "back":
            self.panel = "main"
            self.pause_menu = self.main_menu
            self.pause_menu.index = len(self.main_menu.options) - 1
        elif choice in ("quit", "quit_now"):
            self.assets.pause_music(False)
            self.game.change(TitleScene(self.game))

    # ── menu pessoal (START de quem não é o dono) ──
    def _open_personal(self, slot):
        options = [("PEDIR PAUSA", "ask")]
        session = self.game.session
        if session is not None and not session.campaign and fighter_of(self.match, slot) is not None:
            options.append(("SAIR (VIRA CPU)", "leave"))
        options.append(("FECHAR", "close"))
        box = self._personal_rect(slot)
        self.personal[slot] = MenuList(options, topleft=(box.x + 4, box.y + 30), width=box.w - 8, row_h=28,
                                       size=theme.XS)
        fighter = fighter_of(self.match, slot)
        if fighter is not None and not isinstance(self.match.controllers.get(fighter), IdleInput):
            self.match.controllers[fighter] = IdleInput(self.game.inputs[slot])    # fica parado no menu
        self.sfx("click", 0.4)

    def _close_personal(self, slot):
        self.personal.pop(slot, None)
        fighter = fighter_of(self.match, slot)
        if fighter is not None and isinstance(self.match.controllers.get(fighter), IdleInput):
            self.match.controllers[fighter] = self.game.inputs[slot]

    def _personal_choice(self, slot, choice):
        self._close_personal(slot)
        if choice == "ask":
            self.request = (slot, self.REQUEST_FRAMES)
            self.sfx("confirm", 0.4)
        elif choice == "leave":
            if make_cpu(self.game, self.match, slot):
                self.joined = (f"P{slot} SAIU: AGORA É CPU", 2 * config.FPS)
                hub.set_phase("playing", active=self.active_slots())
            self.sfx("cancel", 0.4)

    def _personal_rect(self, slot):
        W = config.SCREEN_W
        x = 16 if slot in (1, 3) else W - 16 - 250
        y = 70 if slot in (1, 2) else 300
        return pygame.Rect(x, y, 250, 30 + 28 * 3 + 6)

    def update(self):
        super().update()
        if self.ticks == 1 and self.game.session.soccer:
            self.sfx("apito", 0.35)                       # apito do começo do jogo
        humans = [s for s in self.active_slots()]
        session = self.game.session
        free = anyone_pauses(session)
        host = self.host
        if self.request:
            slot, left = self.request
            self.request = (slot, left - 1) if left > 1 else None
        if self.joined:
            text, left = self.joined
            self.joined = (text, left - 1) if left > 1 else None
        if self.paused:
            # só o dono da partida mexe no painel (no treino, qualquer um)
            for s in humans:
                if not free and s != host:
                    continue
                inp = self.game.inputs[s]
                if inp.pressed("pause"):
                    self._command("back")
                    return
                for action, cmd in (("up", "up"), ("down", "down"), ("left", "left"), ("right", "right")):
                    if inp.pressed(action):
                        self._command(cmd)
                if inp.pressed("attack") or inp.pressed("confirm"):
                    self._command("ok")
                    return
                if inp.pressed("cancel"):
                    self._command("back")
                    return
            return
        # entrar no meio: controle ou celular de uma vaga que está com CPU aperta START
        if session is not None and not session.campaign:
            connected = self.game.connected_slots()
            for setup in list(session.slots):
                if setup.cpu and setup.slot in connected and self.game.inputs[setup.slot].pressed("pause"):
                    if make_human(self.game, self.match, setup.slot):
                        self.joined = (f"P{setup.slot} ENTROU NA PARTIDA", 2 * config.FPS)
                        hub.set_phase("playing", active=self.active_slots())
                        self.sfx("confirm", 0.5)
                        return
        for s in humans:
            inp = self.game.inputs[s]
            menu = self.personal.get(s)
            if menu is not None:
                if inp.pressed("up"):
                    menu.move(-1)
                if inp.pressed("down"):
                    menu.move(1)
                if inp.pressed("attack") or inp.pressed("confirm"):
                    self._personal_choice(s, menu.value)
                elif inp.pressed("pause") or inp.pressed("cancel"):
                    self._close_personal(s)
                continue
            if inp.pressed("pause"):
                if free or s == host:
                    self._set_paused(True)
                    return
                self._open_personal(s)
        cursor = self.paused or getattr(self.match, "wants_cursor", False)
        if cursor != getattr(self, "_cursor", False):
            self._cursor = cursor
            pygame.mouse.set_visible(cursor)
        self.match.update()
        if self.match.finished:
            for s in list(self.personal):
                self._close_personal(s)
            record_stats(self.game.session, self.match)
            self.game.change(self.match.next_scene() or ResultsScene(self.game, self.match.result))

    # ── desenho ──────────────────────────────
    def draw(self, screen):
        self.match.draw(screen, self.ui)
        W, H = config.SCREEN_W, config.SCREEN_H
        if self.game.session.soccer and self.ticks < 70 and not self.paused:
            word = "VALENDO!"
            alpha_t = self.ticks / 70
            x = W // 2 + int((1 - min(1, self.ticks / 10)) * W)
            if alpha_t < 0.85 or self.ticks % 4 < 2:
                band = pygame.Rect(0, H // 2 - 34, W, 68)
                veil = pygame.Surface(band.size, pygame.SRCALPHA)
                veil.fill((0, 0, 0, 150))
                screen.blit(veil, band)
                self.ui.text(screen, word, theme.XL, theme.BRASS, (x, H // 2))
        for slot, menu in self.personal.items():
            crt.panel(screen, ("pessoal", slot), lambda s, slot=slot, menu=menu: self._draw_personal(s, slot, menu))
        if self.request and not self.paused:
            crt.panel(screen, "pedido_pausa", self._draw_request)
        if self.joined:
            self.ui.text(screen, self.joined[0], theme.S, theme.BRASS, (W // 2, 96))
        if self.paused:
            crt.panel(screen, "pausa", self._draw_pause)

    def _draw_pause(self, screen):
        """Pausa: tela escurecida com o painel da partida (ou a confirmação de sair)."""
        W = config.SCREEN_W
        darken(screen, 170)
        if self.confirming:
            panel = pygame.Rect(0, 0, 360, 200)
            panel.midtop = (W // 2, 180)
            self.ui.panel(screen, panel)
            self.ui.text(screen, "SAIR DA CAMPANHA?", theme.M, theme.BONE, (W // 2, panel.y + 30))
            self.ui.text(screen, "O PROGRESSO DESTA CORRIDA SE PERDE", theme.XS, theme.BLOOD,
                         (W // 2, panel.y + 58))
            self.pause_menu.draw(screen, self.ui, self.ticks)
        else:
            self._draw_panel(screen)

    def _draw_panel(self, screen):
        W = config.SCREEN_W
        menu = self.main_menu
        panel = pygame.Rect(0, 0, 354, 112 + 34 * len(menu.options))
        panel.topleft = (W // 2 - 312, 80)
        self.ui.panel(screen, panel)
        crown(screen, panel.x + 24, panel.y + 26)
        self.ui.text(screen, "PAINEL DA PARTIDA", theme.S, theme.BONE, (panel.x + 44, panel.y + 26), anchor="midleft")
        host = self.host
        self.ui.text(screen, f"P{host} · CONTROLADOR", theme.XS, theme.SLOT_COLORS.get(host, theme.MUTED),
                     (panel.x + 44, panel.y + 48), anchor="midleft", shadow=False)
        menu.draw(screen, self.ui, self.ticks)
        side = pygame.Rect(panel.right + 16, panel.y, 300, 0)
        rows = self._rows()
        if self.panel in ("rules", "som") and rows:
            box = pygame.Rect(side.x, side.y, side.w, 64 + 30 * len(rows))
            self.ui.panel(screen, box, fill=theme.INK_2)
            title = "REGRAS DA PARTIDA" if self.panel == "rules" else "SOM E TELA"
            self.ui.text(screen, title, theme.XS, theme.BRASS, (box.x + 16, box.y + 18), anchor="midleft")
            y = box.y + 46
            for i, row in enumerate(rows):
                on = i == self.row
                if on:
                    screen.fill(theme.INK_3, (box.x + 8, y - 12, box.w - 16, 24))
                    screen.fill(theme.BRASS, (box.x + 8, y - 12, 3, 24))
                if self.panel == "rules":
                    _, label, options, current = row
                    value = dict(options).get(current, "")
                else:
                    label = row[1]
                    v = settings.get(row[0])
                    value = f"{round(v * 100)}%" if row[0] in settings.VOLUME_KEYS else ("LIGADO" if v else "DESLIGADO")
                self.ui.text(screen, label, theme.XS, theme.BONE if on else theme.MUTED, (box.x + 18, y),
                             anchor="midleft", shadow=False)
                self.ui.arrow(screen, (box.right - 134, y), "left", 4, theme.BRASS if on else theme.FAINT)
                self.ui.text(screen, value, theme.XS, theme.BRASS if on else theme.BONE, (box.right - 76, y),
                             shadow=False)
                self.ui.arrow(screen, (box.right - 18, y), "right", 4, theme.BRASS if on else theme.FAINT)
                y += 30
            if self.panel == "rules":
                self.ui.text(screen, "VALE NA HORA: O PLACAR CONTINUA", theme.XS, theme.FAINT,
                             (box.x + 18, box.bottom - 12), anchor="midleft", shadow=False)
            side.y = box.bottom + 10
        # quem está jogando e por onde
        session = self.game.session
        if session is not None:
            slots = session.slots
            box = pygame.Rect(side.x, side.y, side.w, 20 + 24 * len(slots))
            self.ui.panel(screen, box, fill=theme.INK_2)
            y = box.y + 22
            for setup in slots:
                f = fighter_of(self.match, setup.slot)
                hero = f.stats.name.upper() if f is not None else ""
                if setup.cpu:
                    who, color, how = f"CPU · {hero}", theme.CPU_COLOR, ""
                else:
                    who, color = f"P{setup.slot} · {hero}", theme.SLOT_COLORS.get(setup.slot, theme.BONE)
                    how = self.game.device_of(setup.slot)
                self.ui.text(screen, who, theme.XS, color, (box.x + 16, y), anchor="midleft", shadow=False)
                if setup.slot == self.host and not setup.cpu:
                    crown(screen, box.x + 30 + self.assets.text_width(who, theme.XS), y)
                self.ui.text(screen, how, theme.XS, theme.FAINT, (box.right - 16, y), anchor="midright", shadow=False)
                y += 24
        if self.panel in ("rules", "som"):
            self.footer(screen, [("↑↓", "ESCOLHER"), ("←→", "MUDAR"), ("B", "VOLTAR")])
        else:
            self.footer(screen, [("↑↓", "ESCOLHER"), ("A", "ABRIR"), ("START", "CONTINUAR")])

    def _draw_personal(self, screen, slot, menu):
        box = self._personal_rect(slot)
        screen.fill(theme.SHADOW, box.move(3, 3))
        self.ui.panel(screen, box, fill=theme.INK_2)
        color = theme.SLOT_COLORS.get(slot, theme.BONE)
        screen.fill(color, (box.x, box.y, box.w, 3))
        self.ui.text(screen, f"P{slot} · SÓ PARA VOCÊ", theme.XS, color, (box.x + 12, box.y + 16), anchor="midleft")
        menu.draw(screen, self.ui, self.ticks)

    def _draw_request(self, screen):
        W = config.SCREEN_W
        slot, _ = self.request
        toast = pygame.Rect(0, 0, 420, 36)
        toast.midtop = (W // 2, 64)
        screen.fill(theme.SHADOW, toast.move(3, 3))
        screen.fill(theme.INK_3, toast)
        pygame.draw.rect(screen, theme.BRASS, toast, 2)
        crown(screen, toast.x + 20, toast.centery)
        self.ui.text(screen, f"P{slot} PEDIU PAUSA", theme.XS, theme.BONE, (toast.x + 40, toast.centery),
                     anchor="midleft")
        cap = self.ui.keycap(screen, "START", (toast.right - 150, toast.centery))
        self.ui.text(screen, f"P{self.host} PAUSA", theme.XS, theme.BRASS, (cap.right + 6, toast.centery),
                     anchor="midleft", shadow=False)


class ResultsScene(_MenuScene):
    phase = "results"
    GRACE = 30                  # quadros antes de o celular/controle poder escolher

    def __init__(self, game, result):
        super().__init__(game)
        self.result = result
        session = game.session
        if session is not None and not session.campaign and not session.mode.startswith("treino"):
            game.last_session = session             # o título oferece a REVANCHE desta partida
        self.menu = MenuList([("REVANCHE", "rematch"), ("TROCAR PERSONAGENS", "select"), ("MENU PRINCIPAL", "menu")],
                             topleft=(64, 330), width=320)

    def enter(self):
        super().enter()
        hub.set_phase("results", active=self.active_slots(), banner=self.result.title)

    def handle(self, event):
        choice = self.menu.handle(event, self.sfx)
        if choice:
            self._choose(choice)
        elif self.is_back(event):
            self._choose("menu")

    def update(self):
        super().update()
        for s in self.active_slots():
            inp = self.game.inputs[s]
            if inp.pressed("up"):
                self.menu.move(-1)
            if inp.pressed("down"):
                self.menu.move(1)
            # meio segundo de espera: quem ainda estava apertando ATACAR/CHUTAR no fim da partida
            # caía direto na REVANCHE sem ver o resultado
            if self.ticks > self.GRACE and (inp.pressed("confirm") or inp.pressed("attack")):
                self._choose(self.menu.value)
                return

    def _choose(self, choice):
        self.sfx("confirm")
        if choice == "rematch" and self.game.session.penalty:
            from .penalty import start_penalties
            self.game.change(start_penalties(self.game))
        elif choice == "rematch":
            self.game.change(VersusScene(self.game))
        elif choice == "select":
            from .select import CharSelectScene
            self.game.change(CharSelectScene(self.game))
        else:
            self.game.change(TitleScene(self.game))

    def draw(self, screen):
        W, H = config.SCREEN_W, config.SCREEN_H
        self.draw_background(screen)
        r = self.result
        self.ui.text(screen, "FIM DE JOGO", theme.XS, theme.MUTED, (64, 64), anchor="midleft")
        self.ui.text(screen, r.title, theme.L, r.color, (64, 100), anchor="midleft")
        screen.fill(r.color, (64, 124, 120, 3))
        if r.score:
            self.ui.text(screen, f"{r.score[0]}  x  {r.score[1]}", theme.M, theme.BONE, (64, 164), anchor="midleft")

        # vencedores
        stage_x = W - 250
        ground = 300
        n = len(r.winners)
        for i, f in enumerate(r.winners):
            img = (f.sprites.frame("frente", self.ticks // 5) if (self.ticks // 60) % 2
                   else f.sprites.pose("frente", "ataque", 1 if (self.ticks // 15) % 2 else 2))
            img = _scaled(img, 3 if n == 1 else 2)
            x = stage_x + (i - (n - 1) / 2) * 120
            bob = int(abs(math.sin(self.ticks * 0.08)) * 6)
            pygame.draw.ellipse(screen, theme.SHADOW, (x - 44, ground - 8, 88, 16))
            screen.blit(img, img.get_rect(midbottom=(x, ground + 4 - bob)))

        panel = pygame.Rect(stage_x - 200, 330, 400, 24 + 22 * len(r.lines))
        self.ui.panel(screen, panel)
        y = panel.y + 22
        for label, value in r.lines:
            self.ui.text(screen, label, theme.XS, theme.MUTED, (panel.x + 18, y), anchor="midleft", shadow=False)
            self.ui.text(screen, value, theme.XS, theme.BONE, (panel.right - 18, y), anchor="midright")
            y += 22
        self.menu.draw(screen, self.ui, self.ticks)
        self.footer(screen, [("↑↓", "ESCOLHER"), ("ENTER", "CONFIRMAR")])
