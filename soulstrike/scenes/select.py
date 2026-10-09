"""Conexão dos celulares e seleção de personagens."""
import random

import pygame

from .. import config, theme
from ..ai import DIFFICULTIES, DIFFICULTY_ORDER
from ..arena import BATTLE_MAPS, MAPS_BY_KEY
from ..data import CHARACTERS, MAX_DAMAGE, MAX_HP, MAX_SPEED
from ..soccer_powers import SOCCER_POWERS
from .. import weapon_art
from ..net.remote import hub
from ..ui import mix
from .menus import ModeScene, _MenuScene


def _button(screen, ui, rect, label, hot):
    ui.panel(screen, rect, fill=theme.INK_3 if hot else theme.INK_2, border=theme.BRASS if hot else theme.LINE_HI)
    ui.text(screen, label, theme.XS, theme.BRASS if hot else theme.BONE, rect.center)


class LobbyScene(_MenuScene):
    """Mostra um QR code por jogador para usar o celular como controle."""

    phase = "lobby"

    def __init__(self, game):
        super().__init__(game)
        self.slots = [s.slot for s in game.session.slots]
        n = len(self.slots)
        self.card_w = 200
        gap = 40 if n == 2 else 16
        total = n * self.card_w + (n - 1) * gap
        x0 = (config.SCREEN_W - total) // 2
        self.cards = {s: pygame.Rect(x0 + i * (self.card_w + gap), 104, self.card_w, 262)
                      for i, s in enumerate(self.slots)}
        self.button = pygame.Rect(0, 0, 220, 36)
        self.button.center = (config.SCREEN_W // 2, 432)

    def handle(self, event):
        if self.is_back(event):
            self.sfx("cancel", 0.4)
            self.game.change(ModeScene(self.game))
        elif event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
            self._continue()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.button.collidepoint(event.pos):
            self._continue()

    def update(self):
        super().update()
        # qualquer jogador no celular pode avançar
        connected = hub.connected_slots()
        if any(self.game.inputs[s].pressed("confirm") for s in self.slots if s in connected):
            self._continue()

    def _continue(self):
        self.sfx("confirm")
        self.game.change(CharSelectScene(self.game))

    def draw(self, screen):
        W = config.SCREEN_W
        self.draw_background(screen)
        self.title(screen, "CONECTE OS CELULARES", y=52)
        self.ui.text(screen, "MESMA REDE WI-FI · QUEM NÃO CONECTAR JOGA NO TECLADO", theme.XS, theme.MUTED,
                     (64, 84), anchor="midleft")
        connected = hub.connected_slots()
        soccer2 = self.game.session.mode == "soccer2"
        for slot, rect in self.cards.items():
            color = theme.SLOT_COLORS[slot]
            self.ui.panel(screen, rect)
            head = pygame.Rect(rect.x + 2, rect.y + 2, rect.w - 4, 22)
            screen.fill(theme.SLOT_COLORS_DARK[slot], head)
            screen.fill(color, (head.x, head.bottom - 2, head.w, 2))
            self.ui.text(screen, f"JOGADOR {slot}", theme.XS, theme.BONE, head.center)
            qr = self.assets.qr(f"{self.game.base_url}/?player={slot}", module=4)
            if qr is not None:
                qr_rect = qr.get_rect(midtop=(rect.centerx, head.bottom + 12))
                screen.blit(qr, qr_rect)
            on = slot in connected
            status, scolor = ("CONECTADO", theme.MOSS) if on else ("AGUARDANDO", theme.MUTED)
            if not on and (self.ticks // 30) % 2:
                scolor = theme.FAINT
            self.ui.text(screen, status, theme.XS, scolor, (rect.centerx, rect.bottom - 40))
            hint = "OU TECLADO" if slot <= 2 else ("SEM CELULAR: CPU" if soccer2 else "")
            self.ui.text(screen, hint, theme.XS, theme.FAINT, (rect.centerx, rect.bottom - 22))
        hot = self.button.collidepoint(pygame.mouse.get_pos())
        _button(screen, self.ui, self.button, "CONTINUAR", hot or (self.ticks // 40) % 2 == 0)
        self.ui.text(screen, f"OU ABRA {self.game.base_url}/?player=N", theme.XS, theme.FAINT, (W // 2, 470))
        self.footer(screen, [("ENTER", "CONTINUAR"), ("ESC", "VOLTAR")])


class _Card:
    def __init__(self, setup):
        self.setup = setup
        self.ready = setup.cpu
        if setup.cpu:
            self.randomize()

    def randomize(self):
        self.setup.char = random.randrange(len(CHARACTERS))
        self.setup.weapon = random.randrange(2)

    @property
    def slot(self):
        return self.setup.slot


class CharSelectScene(_MenuScene):
    phase = "select"
    TILE = 60
    TILE_GAP = 8
    TILE_Y = 84

    def __init__(self, game):
        super().__init__(game)
        session = game.session
        self.soccer = session.soccer
        self.cards = [_Card(s) for s in session.slots]
        self.countdown = 0
        keys = [m.key for m in BATTLE_MAPS]
        self.map_index = keys.index(session.map_key) if session.map_key in keys else 0
        n = len(self.cards)
        total = len(CHARACTERS) * self.TILE + (len(CHARACTERS) - 1) * self.TILE_GAP
        x0 = (config.SCREEN_W - total) // 2
        self.tiles = [pygame.Rect(x0 + i * (self.TILE + self.TILE_GAP), self.TILE_Y, self.TILE, self.TILE)
                      for i in range(len(CHARACTERS))]
        if n == 2:
            self.card_rects = [pygame.Rect(40, 158, 300, 328), pygame.Rect(620, 158, 300, 328)]
        else:
            w, gap = 206, 12
            x0 = (config.SCREEN_W - (4 * w + 3 * gap)) // 2
            self.card_rects = [pygame.Rect(x0 + i * (w + gap), 158, w, 328) for i in range(4)]
        self.center = pygame.Rect(356, 158, 248, 328)
        self.map_arrows = (pygame.Rect(self.center.x + 4, self.center.y + 104, 28, 28),
                           pygame.Rect(self.center.right - 32, self.center.y + 104, 28, 28))
        self.diff_arrows = (pygame.Rect(self.center.x + 4, self.center.y + 254, 28, 28),
                            pygame.Rect(self.center.right - 32, self.center.y + 254, 28, 28))
        self._sync_phone_slots()

    # ── estado ───────────────────────────────
    @property
    def map_key(self):
        return BATTLE_MAPS[self.map_index].key

    def _humans(self):
        return [c for c in self.cards if not c.setup.cpu]

    def _sync_phone_slots(self):
        """No 2x2, as vagas 3 e 4 são CPU até alguém conectar o celular."""
        if self.game.session.mode != "soccer2":
            return
        before = self.active_slots()
        connected = hub.connected_slots()
        for card in self.cards:
            if card.slot <= 2:
                continue
            online = card.slot in connected
            if online and card.setup.cpu:
                card.setup.cpu = False
                card.ready = False
            elif not online and not card.setup.cpu and not card.ready:
                card.setup.cpu = True
                card.ready = True
                card.randomize()
        if self.active_slots() != before:
            hub.set_phase(self.phase, active=self.active_slots())

    def _change_char(self, card, step):
        card.setup.char = (card.setup.char + step) % len(CHARACTERS)
        card.setup.weapon = 0
        self.sfx("select", 0.3)

    def _confirm(self, card):
        if not card.ready:
            card.ready = True
            self.sfx("confirm", 0.5)

    def _cycle_map(self, step):
        self.map_index = (self.map_index + step) % len(BATTLE_MAPS)
        self.sfx("click", 0.4)

    def _cycle_difficulty(self, step):
        s = self.game.session
        i = DIFFICULTY_ORDER.index(s.difficulty)
        s.difficulty = DIFFICULTY_ORDER[(i + step) % len(DIFFICULTY_ORDER)]
        self.sfx("click", 0.4)

    def _first_open(self):
        for card in self._humans():
            if not card.ready:
                return card
        return None

    # ── entrada ──────────────────────────────
    def handle(self, event):
        if self.is_back(event):
            self.sfx("cancel", 0.4)
            nxt = ModeScene(self.game) if self.game.session.mode == "cpu" else LobbyScene(self.game)
            self.game.change(nxt)
            return
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                card = self._first_open()
                if card:
                    self._confirm(card)
            elif not self.soccer and event.key in (pygame.K_TAB, pygame.K_RIGHTBRACKET):
                self._cycle_map(1)
            elif not self.soccer and event.key == pygame.K_LEFTBRACKET:
                self._cycle_map(-1)
            elif self.game.session.mode == "cpu" and event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                self.game.session.difficulty = DIFFICULTY_ORDER[event.key - pygame.K_1]
                self.sfx("click", 0.4)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            for i, tile in enumerate(self.tiles):
                if tile.collidepoint(pos):
                    card = self._first_open()
                    if card is None:
                        return
                    if card.setup.char == i:
                        self._confirm(card)
                    else:
                        card.setup.char, card.setup.weapon = i, 0
                        self.sfx("select", 0.3)
                    return
            for card, rect in zip(self.cards, self.card_rects):
                if rect.collidepoint(pos) and not card.setup.cpu:
                    if card.ready:
                        card.ready = False
                    elif not self.soccer and rect.y + 270 < pos[1] < rect.y + 296:
                        card.setup.weapon = 1 - card.setup.weapon
                        self.sfx("select", 0.3)
                    else:
                        self._confirm(card)
                    return
            if not self.soccer:
                for step, r in zip((-1, 1), self.map_arrows):
                    if r.collidepoint(pos):
                        self._cycle_map(step)
                if self.game.session.mode == "cpu":
                    for step, r in zip((-1, 1), self.diff_arrows):
                        if r.collidepoint(pos):
                            self._cycle_difficulty(step)

    def update(self):
        super().update()
        self._sync_phone_slots()
        for card in self._humans():
            inp = self.game.inputs[card.slot]
            if card.ready:
                if inp.pressed("cancel"):
                    card.ready = False
                    self.sfx("cancel", 0.3)
                continue
            if inp.pressed("char_left"):
                self._change_char(card, -1)
            if inp.pressed("char_right"):
                self._change_char(card, 1)
            if inp.pressed("weapon") and not self.soccer:
                card.setup.weapon = 1 - card.setup.weapon
                self.sfx("select", 0.3)
            if inp.pressed("confirm"):
                self._confirm(card)
        for card in self.cards:
            hub.publish_slot(card.slot, char=card.setup.char, weapon=card.setup.weapon, ready=card.ready,
                             team=self.game.session.team_of(card.slot) if self.soccer else None)

        if all(c.ready for c in self.cards):
            self.countdown += 1
            if self.countdown >= 50:
                self.game.session.map_key = self.map_key
                from .play import VersusScene
                self.game.change(VersusScene(self.game))
        else:
            self.countdown = 0

    # ── desenho ──────────────────────────────
    def draw(self, screen):
        self.draw_background(screen)
        self.title(screen, "ESCOLHA OS LUTADORES", y=40)
        self.ui.text(screen, self.game.session.title, theme.XS, theme.MUTED,
                     (config.SCREEN_W - 64, 40), anchor="midright")
        self._draw_roster(screen)
        for card, rect in zip(self.cards, self.card_rects):
            self._draw_card(screen, card, rect)
        if len(self.cards) == 2:
            self._draw_center(screen)
        if self.countdown:
            veil = pygame.Surface((config.SCREEN_W, 40), pygame.SRCALPHA)
            veil.fill((0, 0, 0, 180))
            screen.blit(veil, (0, config.SCREEN_H - 44))
            self.ui.text(screen, "PREPARANDO A PARTIDA...", theme.S, theme.BRASS,
                         (config.SCREEN_W // 2, config.SCREEN_H - 24))
        else:
            items = [("ENTER", "CONFIRMAR"), ("ESC", "VOLTAR")]
            if not self.soccer:
                items.insert(0, ("TAB", "MAPA"))
            if self.game.session.mode == "cpu":
                items.insert(1, ("1 2 3", "DIFICULDADE"))
            self.footer(screen, items)

    def _draw_roster(self, screen):
        for i, (tile, stats) in enumerate(zip(self.tiles, CHARACTERS)):
            pickers = [c for c in self.cards if c.setup.char == i]
            screen.fill(theme.SHADOW, tile.move(3, 3))
            screen.fill(theme.INK_3 if pickers else theme.INK_2, tile)
            img = self.assets.sprites[stats.key].portrait
            clip = screen.get_clip()
            screen.set_clip(tile.inflate(-4, -4))
            screen.blit(img, img.get_rect(midtop=(tile.centerx, tile.y + 6)))
            screen.set_clip(clip)
            if len(pickers) == 1:
                border = pickers[0].setup.color
            else:
                border = theme.BONE if pickers else theme.LINE
            pygame.draw.rect(screen, border, tile if not pickers else tile.inflate(4, 4), 2)
            # uma etiqueta por jogador, em fila acima do quadro (número da vaga; CPU em cinza)
            size, gap = 13, 2
            total = len(pickers) * size + (len(pickers) - 1) * gap
            x = tile.centerx - total // 2
            for card in pickers:
                pip = pygame.Rect(x, tile.y - size - 5, size, size)
                screen.fill(theme.SHADOW, pip.move(1, 1))
                screen.fill(card.setup.color, pip)
                digit = self.assets.text(str(card.slot), theme.XS, theme.INK)
                screen.blit(digit, digit.get_rect(center=(pip.centerx + 1, pip.centery)))
                x += size + gap

    def _draw_card(self, screen, card, rect):
        setup = card.setup
        stats = CHARACTERS[setup.char]
        ui = self.ui
        ui.panel(screen, rect, fill=theme.INK_2)
        head = pygame.Rect(rect.x + 2, rect.y + 2, rect.w - 4, 22)
        dark = theme.SLOT_COLORS_DARK.get(setup.slot) if not setup.cpu else (52, 48, 60)
        screen.fill(dark, head)
        screen.fill(setup.color, (head.x, head.bottom - 2, head.w, 2))
        ui.text(screen, setup.name, theme.XS, theme.BONE, (head.x + 8, head.centery), anchor="midleft")
        if setup.cpu:
            source = DIFFICULTIES[self.game.session.difficulty]["label"] if self.game.session.mode == "cpu" else "AUTO"
        else:
            source = "CELULAR" if setup.slot in hub.connected_slots() else "TECLADO"
        ui.text(screen, source, theme.XS, mix(setup.color, theme.BONE, 0.5), (head.right - 8, head.centery), anchor="midright")

        # sprite andando no lugar
        stage = pygame.Rect(rect.x + 2, head.bottom, rect.w - 4, 138)
        screen.fill(mix(theme.INK_2, setup.color, 0.06), stage)
        frame = 0 if card.ready else (self.ticks // 9) % 4
        img = self.assets.sprites[stats.key].frame("frente", frame)
        img = pygame.transform.scale(img, (img.get_width() * 2, img.get_height() * 2))
        ground = stage.bottom - 10
        pygame.draw.ellipse(screen, theme.SHADOW, (stage.centerx - 30, ground - 6, 60, 12))
        screen.blit(img, img.get_rect(midbottom=(stage.centerx, ground + 2)))
        if not card.ready and not setup.cpu:
            nudge = (self.ticks // 15) % 2
            ui.arrow(screen, (stage.x + 16 - nudge, stage.centery), "left", 7, setup.color)
            ui.arrow(screen, (stage.right - 16 + nudge, stage.centery), "right", 7, setup.color)

        y = stage.bottom + 14
        ui.text(screen, stats.name.upper(), theme.S, theme.BONE, (rect.centerx, y))
        y += 22
        bars = [("VELOCIDADE", stats.speed / MAX_SPEED)]
        if not self.soccer:
            dmg = max(w.damage for w in stats.weapons)
            bars = [("VIDA", stats.max_hp / MAX_HP), ("VELOCIDADE", stats.speed / MAX_SPEED), ("DANO", dmg / MAX_DAMAGE)]
        label_w = 88
        for label, ratio in bars:
            ui.text(screen, label, theme.XS, theme.MUTED, (rect.x + 14, y), anchor="midleft", shadow=False)
            ui.bar(screen, (rect.x + 14 + label_w, y - 4, rect.w - 28 - label_w, 8), ratio, setup.color, ticks=5)
            y += 14
        if self.soccer:
            power = SOCCER_POWERS[stats.key]
            y += 4
            ui.text(screen, "SUPER: " + power.name, theme.XS, theme.BRASS, (rect.x + 14, y), anchor="midleft")
            for line in ui.wrap(power.description, theme.XS, rect.w - 28)[:3]:
                y += 12
                ui.text(screen, line, theme.XS, theme.MUTED, (rect.x + 14, y), anchor="midleft", shadow=False)
        else:
            y += 4
            ui.text(screen, stats.ability_name.upper(), theme.XS, theme.BRASS, (rect.x + 14, y), anchor="midleft")
            for line in ui.wrap(stats.ability_desc, theme.XS, rect.w - 28)[:2]:
                y += 12
                ui.text(screen, line, theme.XS, theme.MUTED, (rect.x + 14, y), anchor="midleft", shadow=False)
            y = rect.y + 284
            screen.fill(theme.LINE, (rect.x + 14, y - 12, rect.w - 28, 1))
            weapon = stats.weapons[setup.weapon]
            kind = "CORPO A CORPO" if weapon.is_melee else "À DISTÂNCIA"
            ui.text(screen, "ARMA", theme.XS, theme.MUTED, (rect.x + 14, y), anchor="midleft", shadow=False)
            name_rect = ui.text(screen, weapon.name.upper(), theme.XS, theme.BONE, (rect.x + 60, y), anchor="midleft")
            kind_rect = ui.text(screen, kind, theme.XS, theme.FAINT, (rect.right - 14, y), anchor="midright", shadow=False)
            art = weapon_art.icon(weapon.name)
            if art is not None:
                screen.blit(art, art.get_rect(center=((name_rect.right + kind_rect.left) // 2, y)))

        # rodapé do cartão
        foot = pygame.Rect(rect.x + 8, rect.bottom - 30, rect.w - 16, 22)
        if card.ready:
            screen.fill(mix(theme.MOSS, theme.INK, 0.55), foot)
            ui.text(screen, "PRONTO", theme.XS, theme.BONE, foot.center)
        elif setup.slot in hub.connected_slots():
            ui.text(screen, "ESCOLHA PELO CELULAR", theme.XS, theme.MUTED, foot.center, shadow=False)
        elif setup.slot <= 2:
            keys = {1: [("A D", ""), ("W", ""), ("G", "OK")], 2: [("← →", ""), ("↑", ""), (";", "OK")]}[setup.slot]
            if self.soccer:
                keys = [keys[0], keys[2]]
            ui.hints(screen, keys, foot.center, gap=8)

    def _draw_center(self, screen):
        ui = self.ui
        c = self.center
        if self.soccer:
            ui.panel(screen, c, fill=theme.INK_2)
            ui.text(screen, "ESTÁDIO", theme.S, theme.BONE, (c.centerx, c.y + 30))
            thumb = self.game.thumbnail(MAPS_BY_KEY["campo_futebol"], (220, 124))
            screen.blit(thumb, thumb.get_rect(midtop=(c.centerx, c.y + 56)))
            ui.text(screen, f"PRIMEIRO A {config.WIN_SCORE} GOLS", theme.XS, theme.BRASS, (c.centerx, c.y + 204))
            ui.paragraph(screen, "Cada personagem tem um poder próprio no botão SUPER.", theme.XS,
                         theme.MUTED, (c.x + 16, c.y + 228), c.w - 32, spacing=14)
            return
        ui.panel(screen, c, fill=theme.INK_2)
        ui.text(screen, "ARENA", theme.XS, theme.MUTED, (c.centerx, c.y + 20))
        cfg = BATTLE_MAPS[self.map_index]
        ui.text(screen, cfg.name.upper(), theme.XS, theme.BONE, (c.centerx, c.y + 40))
        thumb = self.game.thumbnail(cfg, (180, 124))
        tr = thumb.get_rect(midtop=(c.centerx, c.y + 56))
        screen.fill(theme.SHADOW, tr.inflate(4, 4))
        screen.blit(thumb, tr)
        mouse = pygame.mouse.get_pos()
        for direction, r in zip(("left", "right"), self.map_arrows):
            ui.arrow(screen, r.center, direction, 7, theme.BRASS if r.collidepoint(mouse) else theme.MUTED)
        dots_y = tr.bottom + 14
        n = len(BATTLE_MAPS)
        for i in range(n):
            x = c.centerx - (n - 1) * 6 + i * 12
            screen.fill(theme.BRASS if i == self.map_index else theme.LINE, (x - 2, dots_y - 2, 5, 5))
        if self.game.session.mode == "cpu":
            screen.fill(theme.LINE, (c.x + 16, c.y + 222, c.w - 32, 1))
            ui.text(screen, "DIFICULDADE DA CPU", theme.XS, theme.MUTED, (c.centerx, c.y + 240))
            label = DIFFICULTIES[self.game.session.difficulty]["label"]
            ui.text(screen, label, theme.S, theme.BRASS, (c.centerx, c.y + 268))
            for direction, r in zip(("left", "right"), self.diff_arrows):
                ui.arrow(screen, r.center, direction, 7, theme.BRASS if r.collidepoint(mouse) else theme.MUTED)
        else:
            ui.paragraph(screen, "Os dois confirmam e a luta começa.", theme.XS, theme.MUTED,
                         (c.x + 16, c.y + 236), c.w - 32, spacing=14)
