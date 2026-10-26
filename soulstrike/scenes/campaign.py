"""Telas da campanha: história, escolha de melhorias, fim de jogo e final."""
import math
import random

import pygame

from .. import config, progress, theme
from ..ai import DIFFICULTIES
from ..arena import MAPS_BY_KEY
from ..enemies import SHADOW_RIM
from ..fighter import draw_aura
from ..campaign import BROKEN, CRYSTAL, PHASE_HEAL, PHASES, STORY, CampaignMatch, CampaignRun, LobbyMatch
from ..net.remote import hub
from ..ui import MenuList, darken, mix
from ..upgrades import ICONS, UPGRADES, choices
from .menus import TitleScene, _MenuScene


# ── fluxo ────────────────────────────────────
def start_campaign(game):
    run = CampaignRun(game.session)
    return StoryScene(game, "prologo", lambda: start_phase(game, run))


def start_phase(game, run, story=True):
    """Começa a fase no acampamento (depois da história dela)."""
    run.begin_phase()
    progress.save_campaign(run.to_save())      # dá para continuar daqui depois de fechar o jogo

    def play():
        return stage_scene(game, run)
    return StoryScene(game, run.phase.key, play) if story else play()


def stage_scene(game, run):
    """A etapa atual da fase: acampamento ou masmorra."""
    from .play import PlayScene
    match = LobbyMatch(game, run) if run.in_lobby else CampaignMatch(game, run)
    return PlayScene(game, match)


def next_stage(game, run, stage):
    run.stage = stage
    return stage_scene(game, run)


def after_phase(game, run):
    if run.last_phase:
        return StoryScene(game, "final", lambda: CampaignEndScene(game, run))

    def next_phase():
        run.advance()
        return start_phase(game, run)
    return UpgradeScene(game, run, next_phase)


def game_over(game, run):
    return GameOverScene(game, run)


def _pressed(game, slots, *actions):
    return any(game.inputs[s].pressed(a) for s in slots for a in actions)


def draw_crystal(screen, center, size, ticks, broken=False):
    """O Cristal das Almas, desenhado em pixels grandes (inteiro e pulsando, ou em pedaços)."""
    cx, cy = center
    u = max(2, size // 12)
    glow = 0.5 + 0.5 * math.sin(ticks * 0.06)
    halo = pygame.Surface((size * 3, size * 3), pygame.SRCALPHA)
    for r in range(size * 3 // 2, 0, -u * 2):
        a = int(40 * (1 - r / (size * 1.5)) * (0.6 + 0.4 * glow))
        pygame.draw.circle(halo, (170, 90, 230, a), (size * 3 // 2, size * 3 // 2), r)
    screen.blit(halo, (cx - size * 3 // 2, cy - size * 3 // 2))
    body = (150, 80, 220)
    light = (220, 180, 255)
    dark = (90, 40, 140)
    rows = [1, 2, 3, 4, 5, 5, 5, 5, 4, 3, 2, 1]
    pieces = []
    for i, half in enumerate(rows):
        y = cy - len(rows) * u // 2 + i * u
        for k in range(-half, half):
            x = cx + k * u
            color = light if k == -half or (k == -half + 1 and i < 4) else dark if k == half - 1 else body
            pieces.append((x, y, color, k, i))
    if broken and ticks < 14:
        flash = pygame.Surface((size * 4, size * 4), pygame.SRCALPHA)
        pygame.draw.circle(flash, (255, 240, 255, 230 - ticks * 16), (size * 2, size * 2), size + ticks * 6)
        screen.blit(flash, (cx - size * 2, cy - size * 2))
    for n, (x, y, color, k, i) in enumerate(pieces):
        if broken:
            # cada pedaço voa para um lado (sempre o mesmo, pelo índice) e cai
            if ticks > 170:
                continue
            ang = math.atan2(y - cy + 0.5, x - cx + 0.5) + ((n * 37) % 11 - 5) * 0.06
            speed = 1.4 + (n * 53 % 17) / 8
            x = x + math.cos(ang) * speed * ticks
            y = y + math.sin(ang) * speed * ticks + 0.025 * ticks * ticks
        screen.fill(theme.SHADOW, (round(x) + 1, round(y) + 1, u, u))
        screen.fill(color, (round(x), round(y), u, u))


class StoryScene(_MenuScene):
    """Páginas de história com retrato, texto aparecendo aos poucos e botão de pular."""

    phase = "story"
    music = "menu"
    CHARS_PER_FRAME = 1.4

    def __init__(self, game, key, then):
        super().__init__(game)
        self.heading, map_key, self.pages = STORY[key]
        self.then = then
        self.page = 0
        self.shown = 0.0
        self.page_ticks = 0
        self.done = False
        bg = game.thumbnail(MAPS_BY_KEY[map_key], (config.SCREEN_W, config.SCREEN_H)).copy()
        darken(bg, 150)
        self.background = bg

    def enter(self):
        super().enter()
        hub.set_phase("story", mode="campaign", active=self.active_slots(), banner=self.heading)

    @property
    def text(self):
        return self.pages[self.page][2]

    def _advance(self):
        if self.shown < len(self.text):
            self.shown = len(self.text)
            return
        self.sfx("click", 0.4)
        if self.page + 1 < len(self.pages):
            self.page += 1
            self.shown = 0.0
            self.page_ticks = 0
        else:
            self._finish()

    def _finish(self):
        if not self.done:
            self.done = True
            self.game.change(self.then())

    def handle(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_TAB):
                self.sfx("cancel", 0.4)
                self._finish()
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                self._advance()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._advance()

    def update(self):
        super().update()
        self.page_ticks += 1
        self.shown = min(len(self.text), self.shown + self.CHARS_PER_FRAME)
        slots = self.active_slots()
        if self.ticks > 10 and _pressed(self.game, slots, "confirm", "attack"):
            self._advance()
        elif self.ticks > 10 and _pressed(self.game, slots, "pause"):
            self._finish()

    def draw(self, screen):
        W = config.SCREEN_W
        screen.blit(self.background, (0, 0))
        self.ui.text(screen, self.heading, theme.S, theme.BRASS, (W // 2, 44))
        portrait, speaker, text = self.pages[self.page]

        # retrato grande no meio da tela
        stage_y = 250
        if portrait in (CRYSTAL, BROKEN):
            draw_crystal(screen, (W // 2, stage_y - 30), 96, self.page_ticks if portrait == BROKEN else self.ticks,
                         broken=portrait == BROKEN)
        else:
            sprites = (self.assets.shadow_sprites(portrait.split(":", 1)[1]) if portrait.startswith("sombra:")
                       else self.assets.sprites[portrait])
            img = (sprites.frame("frente", self.ticks // 7) if self.page_ticks < 60
                   else sprites.pose("frente", "parado", (self.ticks // 36) % 2))
            factor = 3 if img.get_height() > 50 else 4
            img = pygame.transform.scale(img, (img.get_width() * factor, img.get_height() * factor))
            pygame.draw.ellipse(screen, theme.SHADOW, (W // 2 - 70, stage_y + 30, 140, 22))
            rect = img.get_rect(midbottom=(W // 2, stage_y + 42))
            if portrait.startswith("sombra:"):
                draw_aura(screen, img, rect, SHADOW_RIM, self.ticks, 3)
            screen.blit(img, rect)

        # caixa de texto
        box = pygame.Rect(80, 330, W - 160, 136)
        self.ui.panel(screen, box, fill=theme.INK_2)
        y = box.y + 18
        if speaker:
            self.ui.text(screen, speaker, theme.XS, (200, 150, 250) if "CORROMPIDO" in speaker or "SOMBRIO" in speaker
                         else theme.BRASS, (box.x + 24, y + 4), anchor="midleft")
            y += 18
        visible = text[:int(self.shown)]
        # quebra as linhas com o texto inteiro (as palavras não pulam de linha enquanto aparecem)
        lines = self.ui.wrap(text, theme.S, box.w - 48)
        left = len(visible)
        for line in lines:
            part = line[:max(0, left)]
            left -= len(line) + 1
            if part:
                self.ui.text(screen, part, theme.S, theme.BONE, (box.x + 24, y), anchor="topleft")
            y += 26
        if self.shown >= len(text) and (self.ticks // 20) % 2:
            self.ui.arrow(screen, (box.right - 24, box.bottom - 18), "down", 6, theme.BRASS)
        # páginas
        n = len(self.pages)
        for i in range(n):
            x = W // 2 - (n - 1) * 8 + i * 16
            screen.fill(theme.BRASS if i == self.page else theme.LINE, (x - 3, box.bottom + 14, 6, 6))
        self.footer(screen, [("ENTER", "AVANÇAR"), ("ESC", "PULAR")])


class UpgradeScene(_MenuScene):
    """Fim de fase: cada jogador escolhe 1 de 3 melhorias."""

    phase = "choose"

    def __init__(self, game, run, then):
        super().__init__(game)
        self.run = run
        self.then = then
        self.options = {s: choices(run.upgrades[s]) for s in run.slots}
        self.index = {s: 1 for s in run.slots}
        self.locked = {s: False for s in run.slots}
        self.countdown = 0
        n = len(run.slots)
        self.row_h = 150 if n <= 2 else 98
        top = 120 if n <= 2 else 92
        self.rows = {s: pygame.Rect(40, top + i * (self.row_h + 8), config.SCREEN_W - 80, self.row_h)
                     for i, s in enumerate(run.slots)}
        self._publish()

    def _cards(self, slot):
        row = self.rows[slot]
        w = (row.w - 210 - 2 * 12) // 3
        return [pygame.Rect(row.x + 200 + i * (w + 12), row.y + 8, w, row.h - 16) for i in range(3)]

    def _publish(self):
        for s in self.run.slots:
            opts = self.options[s]
            hub.publish_slot(s, ready=self.locked[s], options=[
                {"name": UPGRADES[k].name, "desc": UPGRADES[k].description,
                 "color": list(UPGRADES[k].color)} for k in opts], choice=self.index[s])

    def _move(self, slot, step):
        if not self.locked[slot]:
            self.index[slot] = (self.index[slot] + step) % 3
            self.sfx("select", 0.3)

    def _lock(self, slot, value=True):
        if self.locked[slot] != value:
            self.locked[slot] = value
            self.sfx("confirm" if value else "cancel", 0.4)

    def handle(self, event):
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            for s in self.run.slots:
                if not self.locked[s]:
                    self._lock(s)
                    break
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for s in self.run.slots:
                for i, card in enumerate(self._cards(s)):
                    if card.collidepoint(event.pos) and not self.locked[s]:
                        self.index[s] = i
                        self._lock(s)

    def update(self):
        super().update()
        for s in self.run.slots:
            inp = self.game.inputs[s]
            if self.locked[s]:
                if inp.pressed("cancel"):
                    self._lock(s, False)
                continue
            if inp.pressed("switch") and self.run.rerolls.get(s, 0) > 0:
                self.run.rerolls[s] -= 1              # comprado na loja: sorteia as 3 de novo
                self.options[s] = choices(self.run.upgrades[s])
                self.sfx("select", 0.4)
            for i in range(3):
                if inp.pressed(f"opt{i + 1}") and self.index[s] != i:
                    self.index[s] = i                     # tocou no cartão pelo celular
                    self.sfx("select", 0.3)
            if inp.pressed("left") or inp.pressed("char_left"):
                self._move(s, -1)
            if inp.pressed("right") or inp.pressed("char_right"):
                self._move(s, 1)
            if self.ticks > 20 and (inp.pressed("confirm") or inp.pressed("attack")):
                self._lock(s)
        self._publish()
        if all(self.locked.values()):
            self.countdown += 1
            if self.countdown == 45:
                for s in self.run.slots:
                    self.run.add_upgrade(s, self.options[s][self.index[s]])
                    if self.run.curse:              # venceu a maldição: mais uma, sorteada entre as outras
                        others = [k for i, k in enumerate(self.options[s]) if i != self.index[s]]
                        self.run.add_upgrade(s, random.choice(others))
                self.run.curse = None
                self.game.change(self.then())
        else:
            self.countdown = 0

    def draw(self, screen):
        W, H = config.SCREEN_W, config.SCREEN_H
        self.draw_background(screen)
        done = self.run.phase_index + 1
        self.title(screen, "ESCOLHA UMA MELHORIA", y=40)
        if self.run.curse:
            self.ui.text(screen, "MALDIÇÃO VENCIDA: +1 MELHORIA", theme.XS, (190, 90, 230),
                         (W - 64, 72), anchor="midright")
        self.ui.text(screen, f"FASE {done} CONCLUÍDA · TODO MUNDO RECUPERA {round(PHASE_HEAL * 100)}% DA VIDA",
                     theme.XS, theme.MOSS, (64, 72), anchor="midleft")
        self.ui.text(screen, f"PRÓXIMA: {PHASES[done].name}", theme.XS, theme.MUTED, (W - 64, 40), anchor="midright")
        for s in self.run.slots:
            self._draw_row(screen, s)
        if self.countdown:
            self.ui.text(screen, "PREPARANDO A PRÓXIMA FASE...", theme.S, theme.BRASS, (W // 2, H - 24))
        else:
            self.footer(screen, [("◀ ▶", "ESCOLHER"), ("OK", "CONFIRMAR"), ("CANCELAR", "TROCAR")])

    def _draw_row(self, screen, slot):
        ui = self.ui
        row = self.rows[slot]
        color = theme.SLOT_COLORS[slot]
        ui.panel(screen, row, fill=theme.INK_2, border=color if self.locked[slot] else theme.LINE)
        setup = next(s for s in self.run.session.slots if s.slot == slot)
        from ..data import CHARACTERS
        stats = CHARACTERS[setup.char]
        sprites = self.assets.sprites[stats.key]
        img = sprites.pose("frente", "parado", 0) if self.locked[slot] else sprites.frame("frente", self.ticks // 5)
        factor = 2 if self.row_h > 120 else 1
        img = pygame.transform.scale(img, (img.get_width() * factor, img.get_height() * factor))
        screen.blit(img, img.get_rect(midbottom=(row.x + 48, row.bottom - 10)))
        ui.text(screen, f"JOGADOR {slot}", theme.XS, color, (row.x + 92, row.y + 20), anchor="midleft")
        ui.text(screen, stats.name.upper(), theme.XS, theme.BONE, (row.x + 92, row.y + 36), anchor="midleft")
        owned = self.run.upgrades[slot]
        for i, key in enumerate(owned[-6:]):
            _icon(screen, UPGRADES[key], (row.x + 98 + (i % 3) * 22, row.y + 58 + (i // 3) * 22), 2)
        if self.locked[slot]:
            ui.text(screen, "PRONTO", theme.XS, theme.MOSS, (row.x + 92, row.bottom - 16), anchor="midleft")
        elif self.run.rerolls.get(slot, 0):
            ui.text(screen, f"TROCAR ARMA: SORTEAR ({self.run.rerolls[slot]})", theme.XS, theme.BRASS,
                    (row.x + 92, row.bottom - 16), anchor="midleft")
        for i, (card, key) in enumerate(zip(self._cards(slot), self.options[slot])):
            up = UPGRADES[key]
            hot = i == self.index[slot]
            fill = mix(theme.INK_3, up.color, 0.18) if hot else theme.INK
            ui.panel(screen, card, fill=fill, border=(theme.BONE if self.locked[slot] else color) if hot else theme.LINE,
                     shadow=False)
            big = self.row_h > 120
            _icon(screen, up, (card.x + 30, card.y + (34 if big else card.h // 2)), 4 if big else 3)
            tx = card.x + (64 if big else 58)
            ui.text(screen, up.name, theme.XS, up.color if hot else theme.BONE, (tx, card.y + 20), anchor="midleft")
            lines = ui.wrap(up.description, theme.XS, card.right - tx - 10)
            for k, line in enumerate(lines[:3]):
                ui.text(screen, line, theme.XS, theme.BONE if hot else theme.MUTED, (tx, card.y + 38 + k * 13),
                        anchor="midleft", shadow=False)
            count = owned.count(key)
            if count:
                ui.text(screen, f"VOCÊ TEM {count}", theme.XS, theme.FAINT, (tx, card.bottom - 12), anchor="midleft",
                        shadow=False)


def _icon(screen, upgrade, center, scale):
    rows = ICONS.get(upgrade.key)
    if not rows:
        return
    light = mix(upgrade.color, (255, 255, 255), 0.55)
    x0 = center[0] - 7 * scale // 2
    y0 = center[1] - 7 * scale // 2
    for y, line in enumerate(rows):
        for x, ch in enumerate(line):
            if ch in "#+":
                screen.fill(theme.SHADOW, (x0 + x * scale + 1, y0 + y * scale + 1, scale, scale))
    for y, line in enumerate(rows):
        for x, ch in enumerate(line):
            if ch in "#+":
                screen.fill(upgrade.color if ch == "#" else light, (x0 + x * scale, y0 + y * scale, scale, scale))


class _RunMenuScene(_MenuScene):
    """Tela com menu que todos os jogadores podem usar (teclado ou celular)."""

    phase = "results"

    def update(self):
        super().update()
        for s in self.active_slots():
            inp = self.game.inputs[s]
            if inp.pressed("up"):
                self.menu.move(-1)
            if inp.pressed("down"):
                self.menu.move(1)
            if self.ticks > 30 and (inp.pressed("confirm") or inp.pressed("attack")):
                self._choose(self.menu.value)
                return

    def handle(self, event):
        choice = self.menu.handle(event, self.sfx)
        if choice:
            self._choose(choice)

    def _stats_panel(self, screen, rect, run):
        ui = self.ui
        ui.panel(screen, rect)
        y = rect.y + 22
        secs = run.frames // config.FPS
        lines = [("TEMPO", f"{secs // 60}:{secs % 60:02d}"),
                 ("DIFICULDADE", DIFFICULTIES[run.session.difficulty]["label"])]
        for s in run.slots:
            lines.append((f"JOGADOR {s} · ABATES", str(run.kills[s])))
        for label, value in lines:
            ui.text(screen, label, theme.XS, theme.MUTED, (rect.x + 18, y), anchor="midleft", shadow=False)
            ui.text(screen, value, theme.XS, theme.BONE, (rect.right - 18, y), anchor="midright")
            y += 22


class GameOverScene(_RunMenuScene):
    def __init__(self, game, run):
        super().__init__(game)
        self.run = run
        self.menu = MenuList([("TENTAR DE NOVO", "retry"), ("RECOMEÇAR CAMPANHA", "restart"),
                              ("MENU PRINCIPAL", "menu")], topleft=(64, 300), width=340)

    def enter(self):
        super().enter()
        hub.set_phase("results", mode="campaign", active=self.active_slots(), banner="FIM DE JOGO")

    def _choose(self, choice):
        self.sfx("confirm")
        if choice == "retry":
            self.run.retry_phase()
            self.game.change(start_phase(self.game, self.run, story=False))
        elif choice == "restart":
            run = CampaignRun(self.game.session)
            self.game.change(start_phase(self.game, run))
        else:
            self.game.change(TitleScene(self.game))

    def draw(self, screen):
        W = config.SCREEN_W
        self.draw_background(screen)
        self.ui.text(screen, "CAMPANHA", theme.XS, theme.MUTED, (64, 64), anchor="midleft")
        self.ui.text(screen, "FIM DE JOGO", theme.L, theme.BLOOD, (64, 100), anchor="midleft")
        screen.fill(theme.BLOOD, (64, 124, 120, 3))
        phase = self.run.phase
        self.ui.text(screen, f"VOCÊS CAÍRAM NA FASE {self.run.phase_index + 1}: {phase.name}", theme.XS, theme.BONE,
                     (64, 160), anchor="midleft")
        self.ui.paragraph(screen, "Tentar de novo recomeça esta fase com as melhorias que vocês já têm.",
                          theme.XS, theme.MUTED, (64, 190), 380, spacing=16)
        draw_crystal(screen, (W - 230, 190), 70, self.ticks)
        self._stats_panel(screen, pygame.Rect(W - 400, 300, 340, 44 + 22 * (1 + len(self.run.slots))), self.run)
        self.menu.draw(screen, self.ui, self.ticks)
        self.footer(screen, [("↑↓", "ESCOLHER"), ("ENTER", "CONFIRMAR")])


class CampaignEndScene(_RunMenuScene):
    music = "menu"

    def __init__(self, game, run):
        super().__init__(game)
        self.run = run
        secs = run.frames // config.FPS
        self.best_before = progress.best_time(run.session.difficulty)
        self.record, self.unlocked = progress.record_campaign(secs, run.session.difficulty, run.players)
        progress.clear_campaign()
        self.menu = MenuList([("MENU PRINCIPAL", "menu"), ("JOGAR DE NOVO", "again")],
                             topleft=(64, 356), width=300)
        self.banner = "CAMPANHA CONCLUÍDA"

    def enter(self):
        super().enter()
        hub.set_phase("results", mode="campaign", active=self.active_slots(), banner=self.banner)
        self.sfx("victory", 0.5)

    def _choose(self, choice):
        self.sfx("confirm")
        if choice == "again":
            from .select import CharSelectScene
            self.game.change(CharSelectScene(self.game))
        else:
            self.game.change(TitleScene(self.game))

    def draw(self, screen):
        W = config.SCREEN_W
        self.draw_background(screen)
        self.ui.text(screen, "CAMPANHA", theme.XS, theme.MUTED, (64, 64), anchor="midleft")
        self.ui.text(screen, "VOCÊS VENCERAM!", theme.L, theme.MOSS, (64, 100), anchor="midleft")
        screen.fill(theme.MOSS, (64, 124, 120, 3))
        secs = self.run.frames // config.FPS
        best = self.best_before
        if self.record:
            line, color = "NOVO RECORDE DE TEMPO!", theme.BRASS
        else:
            line, color = f"RECORDE: {best // 60}:{best % 60:02d}", theme.MUTED
        self.ui.text(screen, f"TEMPO {secs // 60}:{secs % 60:02d}", theme.S, theme.BONE, (64, 150), anchor="midleft")
        self.ui.text(screen, line, theme.XS, color, (64, 172), anchor="midleft")

        # heróis comemorando
        from ..data import CHARACTERS
        for i, setup in enumerate(self.run.session.slots):
            img = self.assets.sprites[CHARACTERS[setup.char].key].frame("frente", self.ticks // 5 + i * 2)
            img = pygame.transform.scale(img, (img.get_width() * 2, img.get_height() * 2))
            x = 110 + i * 90
            bob = int(abs(math.sin(self.ticks * 0.08 + i)) * 6)
            pygame.draw.ellipse(screen, theme.SHADOW, (x - 30, 318 - 8, 60, 14))
            screen.blit(img, img.get_rect(midbottom=(x, 318 + 2 - bob)))

        if self.unlocked or progress.campaign_cleared():
            box = pygame.Rect(W - 400, 70, 340, 200)
            self.ui.panel(screen, box, fill=theme.INK_2, border=(170, 90, 230))
            title = "NOVO LUTADOR LIBERADO!" if self.unlocked else "LUTADOR LIBERADO"
            self.ui.text(screen, title, theme.XS, theme.BRASS, (box.centerx, box.y + 22))
            sprites = self.assets.shadow_sprites("aryel")
            img = sprites.frame("frente", self.ticks // 6)
            img = pygame.transform.scale(img, (img.get_width() * 2, img.get_height() * 2))
            rect = img.get_rect(midbottom=(box.centerx, box.y + 160))
            draw_aura(screen, img, rect, SHADOW_RIM, self.ticks, 3)
            screen.blit(img, rect)
            self.ui.text(screen, "ARYEL CORROMPIDO", theme.S, (200, 150, 250), (box.centerx, box.y + 178))
        self._stats_panel(screen, pygame.Rect(W - 400, 300, 340, 44 + 22 * (1 + len(self.run.slots))), self.run)
        self.menu.draw(screen, self.ui, self.ticks)
        self.footer(screen, [("↑↓", "ESCOLHER"), ("ENTER", "CONFIRMAR")])
