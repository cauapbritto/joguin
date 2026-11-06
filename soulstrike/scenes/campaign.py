"""Telas da campanha: história, escolha de melhorias, fim de jogo e final."""
import math
import random

import pygame

from .. import config, progress, theme
from ..ai import DIFFICULTIES
from ..arena import MAPS_BY_KEY
from ..enemies import SHADOW_RIM
from ..fighter import draw_aura
from ..campaign import (BROKEN, CRYSTAL, DUNGEON_2, FRAGMENT, PHASE_HEAL, PHASES, STORY, CampaignMatch,
                        CampaignRun, LobbyMatch)
from ..net.remote import hub
from ..ui import MenuList, darken, mix
from ..upgrades import ICONS, UPGRADES, choices
from .menus import TitleScene, _MenuScene


# ── fluxo ────────────────────────────────────
def start_campaign(game):
    run = CampaignRun(game.session)
    if run.rush:
        run.start_rush()
        return StoryScene(game, "reuniao_corrompidos", lambda: start_phase(game, run))
    chapter = getattr(game.session, "chapter", 1)
    if chapter > 1:
        # direto no capítulo 2 ou 3: almas, melhorias sorteadas e mais uma escolhida antes de entrar
        run.start_at_chapter(chapter)
        return UpgradeScene(game, run, lambda: hub_scene(game, run), intro=True)
    return StoryScene(game, "prologo", lambda: hub_scene(game, run))


def hub_scene(game, run, story=True):
    """A Casa da turma: a campanha (e o CONTINUAR) começa aqui; a saída do quintal leva à fase."""
    from ..casa import HubMatch
    from .play import PlayScene
    return PlayScene(game, HubMatch(game, run, story))


def start_phase(game, run, story=True):
    """Começa a fase na sala inicial (depois da história dela)."""
    if run.rush:
        # Reunião dos Corrompidos: direto na sala do chefe (sem acampamento, história nem save)
        run.begin_phase()
        run.stage = DUNGEON_2
        run._snapshot = run._state()
        return stage_scene(game, run)
    run.begin_phase()
    progress.save_campaign(run.to_save())      # dá para continuar daqui depois de fechar o jogo

    def play():
        return stage_scene(game, run)
    return StoryScene(game, run.phase.key, play) if story else play()


def stage_scene(game, run):
    """A etapa atual da fase: sala inicial, masmorra ou corredor."""
    from .play import PlayScene
    match = LobbyMatch(game, run) if run.in_lobby else CampaignMatch(game, run)
    return PlayScene(game, match)


def next_stage(game, run, stage):
    run.stage = stage
    return stage_scene(game, run)


def after_phase(game, run):
    if run.rush:
        if run.rush_last:
            return CampaignEndScene(game, run)

        def next_boss():
            run.next_rush()
            return start_phase(game, run)
        return UpgradeScene(game, run, next_boss)
    if run.last_phase:
        return StoryScene(game, "final", lambda: CreditsScene(game, lambda: CampaignEndScene(game, run)))

    def next_phase():
        run.advance()
        return start_phase(game, run)

    if run.chapter_end:
        # fim do capítulo 1 ou 2: a história do capítulo, a melhoria da fase e a tela do capítulo
        def chapter_break():
            run.advance()
            return ChapterEndScene(game, run)
        return StoryScene(game, f"fim_capitulo{run.chapter}", lambda: UpgradeScene(game, run, chapter_break))
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


def draw_fragment(screen, center, ticks):
    """O fragmento do cristal dentro de um tubo de vidro, preso por cabos (capítulo 2)."""
    cx, cy = center
    for k, color in enumerate(((40, 150, 200), (200, 80, 60), (220, 200, 70), (40, 150, 200))):
        x = cx - 60 + k * 40
        pygame.draw.line(screen, color, (x, cy + 90), (cx - 12 + k * 8, cy + 46), 4)
    tube = pygame.Rect(0, 0, 70, 130)
    tube.center = (cx, cy)
    screen.fill((40, 44, 56), (tube.x - 6, tube.bottom - 8, tube.w + 12, 16))
    screen.fill((40, 44, 56), (tube.x - 6, tube.y - 8, tube.w + 12, 12))
    glass = pygame.Surface(tube.size, pygame.SRCALPHA)
    glass.fill((120, 190, 230, 60))
    screen.blit(glass, tube)
    draw_crystal(screen, (cx, cy + 4), 42, ticks)
    pygame.draw.rect(screen, (170, 220, 240), tube, 2)
    screen.fill((210, 240, 250), (tube.x + 8, tube.y + 10, 3, tube.h - 24))
    for k in range(3):
        y = tube.y + 30 + k * 30
        screen.fill((150, 70, 220), (tube.x - 12, y, 8, 2))
        screen.fill((150, 70, 220), (tube.right + 4, y + 10, 8, 2))


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
        elif portrait == FRAGMENT:
            draw_fragment(screen, (W // 2, stage_y - 20), self.ticks)
        else:
            sprites = (self.assets.shadow_sprites(portrait.split(":", 1)[1]) if portrait.startswith("sombra:")
                       else self.assets.sheet_sprites(portrait))
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

    def __init__(self, game, run, then, intro=False):
        super().__init__(game)
        self.run = run
        self.then = then
        self.intro = intro              # começando do capítulo 2: a melhoria é antes da primeira fase
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
        if self.intro:
            from ..campaign import CHAPTER2_SOULS, CHAPTER2_UPGRADES
            ch = self.run.chapter
            self.ui.text(screen, f"CAPÍTULO {ch} · CADA UM COMEÇA COM {CHAPTER2_SOULS * (ch - 1)} ALMAS E "
                                 f"{CHAPTER2_UPGRADES * (ch - 1)} MELHORIAS SORTEADAS",
                         theme.XS, theme.MOSS, (64, 72), anchor="midleft")
            nxt = PHASES[self.run.phase_index]
        else:
            self.ui.text(screen, f"FASE {done} CONCLUÍDA · TODO MUNDO RECUPERA {round(PHASE_HEAL * 100)}% DA VIDA",
                         theme.XS, theme.MOSS, (64, 72), anchor="midleft")
            from ..campaign import RUSH_PHASES
            later = [i for i in RUSH_PHASES if i > self.run.phase_index]
            nxt = PHASES[later[0]] if self.run.rush and later else PHASES[min(done, len(PHASES) - 1)]
        self.ui.text(screen, f"PRÓXIMA: {nxt.name}", theme.XS, theme.MUTED, (W - 64, 40), anchor="midright")
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
            if self.run.rush:
                self.game.change(start_campaign(self.game))
                return
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


def draw_unlock(scene, screen, box, sprite, name, now):
    """Quadro do lutador liberado, com a sombra dele se mexendo."""
    scene.ui.panel(screen, box, fill=theme.INK_2, border=(170, 90, 230))
    title = "NOVO LUTADOR LIBERADO!" if now else "LUTADOR LIBERADO"
    scene.ui.text(screen, title, theme.XS, theme.BRASS, (box.centerx, box.y + 22))
    img = scene.assets.shadow_sprites(sprite).frame("frente", scene.ticks // 6)
    img = pygame.transform.scale(img, (img.get_width() * 2, img.get_height() * 2))
    rect = img.get_rect(midbottom=(box.centerx, box.y + 160))
    draw_aura(screen, img, rect, SHADOW_RIM, scene.ticks, 3)
    screen.blit(img, rect)
    scene.ui.text(screen, name, theme.S, (200, 150, 250), (box.centerx, box.y + 178))


SEAL_ORDER = ("facil", "normal", "dificil", "ibrahim", "borba")
SEAL_COLORS = {"facil": (110, 200, 120), "normal": (90, 170, 255), "dificil": (255, 170, 60),
               "ibrahim": (230, 70, 70), "borba": (170, 90, 230)}


def draw_seal(screen, ui, center, key, earned, ticks=0, size=26):
    """Selo de zerado de uma dificuldade: o carimbo redondo (cinza se ainda não tem)."""
    cx, cy = center
    color = SEAL_COLORS.get(key, theme.BRASS) if earned else (70, 70, 80)
    pygame.draw.circle(screen, (20, 18, 26), (cx, cy), size + 3)
    pygame.draw.circle(screen, color, (cx, cy), size)
    pygame.draw.circle(screen, (20, 18, 26), (cx, cy), size - 5, 2)
    for k in range(12):
        a = k * math.tau / 12 + (ticks * 0.01 if earned else 0)
        screen.fill((20, 18, 26), (round(cx + math.cos(a) * (size - 2)) - 1, round(cy + math.sin(a) * (size - 2)) - 1, 2, 2))
    label = DIFFICULTIES[key]["label"].upper()[:3] if key in DIFFICULTIES else key[:3].upper()
    ui.text(screen, label, theme.XS, (20, 18, 26) if earned else (120, 120, 130), (cx, cy), shadow=False)


def draw_seals(scene, screen, box, earned, title, new=None):
    scene.ui.panel(screen, box)
    scene.ui.text(screen, title, theme.XS, theme.MUTED, (box.centerx, box.y + 22))
    step = (box.w - 40) // len(SEAL_ORDER)
    for i, key in enumerate(SEAL_ORDER):
        cx = box.x + 20 + step // 2 + i * step
        pulse = key == new and (scene.ticks // 10) % 2 == 0
        draw_seal(screen, scene.ui, (cx, box.y + 90), key, key in earned or pulse, scene.ticks, size=24)
    if new:
        scene.ui.text(screen, "SELO NOVO: " + DIFFICULTIES[new]["label"].upper(), theme.S, theme.BRASS,
                      (box.centerx, box.y + 150))


# cinema: (rótulo, histórias em sequência)
CINEMA = (("CAPÍTULO 1 · AS SOMBRAS", ("prologo", "floresta", "calabouco", "templo", "fim_capitulo1")),
          ("CAPÍTULO 2 · LAG LOBBY", ("recepcao", "datacenter", "cobertura", "fim_capitulo2")),
          ("CAPÍTULO 3 · CLEPALOVERS", ("clinica_recepcao", "procedimentos", "suite_vip", "fim_capitulo3")),
          ("CAPÍTULO 4 · MANSÃO DO CARIMBO", ("mansao_sede", "mansao_patio", "mansao_gabinete", "final")),
          ("REUNIÃO DOS CORROMPIDOS", ("reuniao_corrompidos",)),
          ("CRÉDITOS", ("creditos",)))


def _play_stories(game, keys, then):
    """Uma história atrás da outra (ESC pula só a que está passando)."""
    if not keys:
        return then()
    if keys[0] == "creditos":
        return CreditsScene(game, lambda: _play_stories(game, keys[1:], then))
    return StoryScene(game, keys[0], lambda: _play_stories(game, keys[1:], then))


class CinemaScene(_RunMenuScene):
    """Cinema (liberado ao zerar a campanha): escolhe uma história e assiste de novo."""

    phase = "story"
    music = "menu"

    def __init__(self, game, index=0):
        super().__init__(game)
        self.menu = MenuList([(label, str(i)) for i, (label, _) in enumerate(CINEMA)] + [("VOLTAR", "back")],
                             topleft=(64, 96), width=380)
        self.menu.index = min(index, len(CINEMA))

    def _choose(self, choice):
        self.sfx("confirm")
        index = self.menu.index
        if choice == "back":
            from .menus import ModeScene
            self.game.change(ModeScene(self.game, "campanha"))
        else:
            keys = CINEMA[int(choice)][1]
            self.game.change(_play_stories(self.game, keys, lambda: CinemaScene(self.game, index)))

    def draw(self, screen):
        W = config.SCREEN_W
        self.draw_background(screen)
        self.title(screen, "CINEMA", y=48)
        self.menu.draw(screen, self.ui, self.ticks)
        box = pygame.Rect(W - 420, 96, 356, 160)
        draw_seals(self, screen, box, progress.seals(), "SELOS DE ZERADO")
        self.footer(screen, [("↑↓", "ESCOLHER"), ("ENTER", "ASSISTIR")])


# créditos do fim da campanha: (sprite, nome de verdade, personagem)
CAST = (("cauanzera", "Cauã Pedrozo Brito", "CAUANZERA"),
        ("aryel", "Adryel Assunção Rocha", "ARYEL"),
        ("borba", "João Francisco da Silva Malaquias", "BORBA JR"),
        ("albeguinio", "Alber Alberguini Cabral", "ALBEGUINIO"))
CREDITS_SPEED = 0.9


class CreditsScene(_MenuScene):
    """Créditos depois do fim da campanha: o elenco de verdade (com o sprite de cada um) subindo
    pela tela. ATACAR, ENTER ou ESC pulam."""

    phase = "story"
    music = "menu"

    def __init__(self, game, then):
        super().__init__(game)
        self.then = then
        self.offset = 0.0
        self.done = False
        bg = game.thumbnail(MAPS_BY_KEY["mansao_nucleo"], (config.SCREEN_W, config.SCREEN_H)).copy()
        darken(bg, 190)
        self.background = bg
        self.lines = self._build()

    def _build(self):
        rows = [("title", "SOUL STRIKE"), ("sub", "A CAMPANHA"), ("gap", 30), ("head", "ELENCO")]
        for sprite, name, role in CAST:
            rows.append(("cast", (sprite, name, role)))
        rows += [("gap", 20), ("head", "IDEIA E DIREÇÃO"), ("text", "Cauã Pedrozo Brito"),
                 ("gap", 20), ("head", "VILÕES"),
                 ("text", "Aryel Corrompido · Borba Jr Corrompido"),
                 ("text", "Albeguinio Corrompido · Cauanzera Corrompido e a IARA"),
                 ("text", "a Patrulha Cinza, a Daiwone e o comitê da Mansão do Carimbo"),
                 ("gap", 20),
                 ("small", "Mato Grelhado, Cuiabrasa e a Mansão do Carimbo são de mentira."),
                 ("small", "Os 47 graus à sombra, infelizmente, não."),
                 ("gap", 60), ("title", "OBRIGADO POR JOGAR!")]
        return rows

    @staticmethod
    def _height(kind, value):
        return {"title": 60, "sub": 34, "head": 44, "cast": 92, "text": 30, "small": 26}.get(kind, value or 0)

    @property
    def total(self):
        return sum(self._height(k, v) for k, v in self.lines)

    def enter(self):
        super().enter()
        hub.set_phase("story", mode="campaign", active=self.active_slots(), banner="CRÉDITOS")

    def _finish(self):
        if not self.done:
            self.done = True
            self.game.change(self.then())

    def handle(self, event):
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE,
                                                          pygame.K_KP_ENTER, pygame.K_TAB):
            self._finish()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._finish()

    def update(self):
        super().update()
        self.offset += CREDITS_SPEED
        if self.ticks > 30 and _pressed(self.game, self.active_slots(), "confirm", "attack", "pause"):
            self._finish()
        elif self.offset > self.total + config.SCREEN_H * 0.6:
            self._finish()

    def draw(self, screen):
        W, H = config.SCREEN_W, config.SCREEN_H
        screen.blit(self.background, (0, 0))
        y = H - self.offset
        for kind, value in self.lines:
            h = self._height(kind, value)
            if -100 < y < H + 100:
                if kind == "title":
                    self.ui.text(screen, value, theme.L, theme.BRASS, (W // 2, round(y + h / 2)))
                elif kind == "sub":
                    self.ui.text(screen, value, theme.S, theme.MUTED, (W // 2, round(y + h / 2)))
                elif kind == "head":
                    self.ui.text(screen, value, theme.S, (200, 150, 250), (W // 2, round(y + h / 2)))
                elif kind == "text":
                    self.ui.text(screen, value, theme.S, theme.BONE, (W // 2, round(y + h / 2)))
                elif kind == "small":
                    self.ui.text(screen, value, theme.XS, theme.MUTED, (W // 2, round(y + h / 2)))
                elif kind == "cast":
                    sprite, name, role = value
                    img = self.assets.sprites[sprite].frame("frente", self.ticks // 6)
                    screen.blit(img, img.get_rect(midbottom=(W // 2 - 190, round(y + h - 8))))
                    self.ui.text(screen, name, theme.S, theme.BONE, (W // 2 - 120, round(y + h / 2 - 10)),
                                 anchor="midleft")
                    self.ui.text(screen, "como " + role, theme.XS, theme.BRASS, (W // 2 - 120, round(y + h / 2 + 16)),
                                 anchor="midleft")
            y += h
        self.ui.text(screen, "ATACAR PULA", theme.XS, theme.MUTED, (W - 24, H - 20), anchor="midright")


# o que a tela de fim de capítulo mostra: texto, sprite e nome do lutador liberado
CHAPTER_END = {
    1: ("O cristal quebrou, mas um fragmento sumiu. A próxima parada é a LAG LOBBY, "
        "a empresa tomada pela Patrulha Cinza.", "aryel", "ARYEL CORROMPIDO"),
    2: ("O fragmento se partiu, mas um caco sumiu no bolso de alguém. A próxima parada é a CLÍNICA "
        "CLEPALOVERS, estética avançada.", "borba_exo", "BORBA JR CORROMPIDO"),
    3: ("O caco virou pó, mas uma lasca foi parar no bolso do Cauanzera. A próxima parada é a MANSÃO DO "
        "CARIMBO, em Cuiabrasa, onde a lasca virou a IARA.", "albeguinio_adm", "ALBEGUINIO CORROMPIDO"),
}


class ChapterEndScene(_RunMenuScene):
    """Fim do capítulo 1 ou 2: libera o lutador secreto dele e guarda a campanha no começo do
    próximo capítulo (dá para parar aqui e continuar depois pelo CONTINUAR CAMPANHA)."""

    music = "menu"

    def __init__(self, game, run):
        super().__init__(game)
        self.run = run
        self.done = max(1, run.chapter - 1)          # o capítulo que acabou (o run já avançou)
        self.unlocked = progress.record_chapter(self.done)
        run.begin_phase()
        progress.save_campaign(run.to_save())
        self.menu = MenuList([(f"IR PARA O CAPÍTULO {self.done + 1}", "next"), ("PARAR AQUI (FICA SALVO)", "menu")],
                             topleft=(64, 356), width=360)

    def enter(self):
        super().enter()
        hub.set_phase("results", mode="campaign", active=self.active_slots(),
                      banner=f"CAPÍTULO {self.done} CONCLUÍDO")
        self.sfx("victory", 0.5)

    def _choose(self, choice):
        self.sfx("confirm")
        if choice == "next":
            self.game.change(start_phase(self.game, self.run))
        else:
            self.game.change(TitleScene(self.game))

    def draw(self, screen):
        W = config.SCREEN_W
        self.draw_background(screen)
        self.ui.text(screen, "CAMPANHA", theme.XS, theme.MUTED, (64, 64), anchor="midleft")
        text, sprite, name = CHAPTER_END[self.done]
        self.ui.text(screen, f"CAPÍTULO {self.done} CONCLUÍDO!", theme.L, theme.MOSS, (64, 100), anchor="midleft")
        screen.fill(theme.MOSS, (64, 124, 120, 3))
        self.ui.paragraph(screen, text, theme.XS, theme.BONE, (64, 156), 420, spacing=16)
        self.ui.paragraph(screen, "Se pararem aqui, o CONTINUAR CAMPANHA do menu volta no começo do "
                                  f"capítulo {self.done + 1}.",
                          theme.XS, theme.MUTED, (64, 236), 420, spacing=16)
        draw_unlock(self, screen, pygame.Rect(W - 400, 70, 340, 200), sprite, name, self.unlocked)
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
        self.full = run.start_chapter == 1
        self.rush = run.rush
        self.seal_new = False
        if self.rush:
            # Reunião dos Corrompidos: não mexe na campanha salva nem nos capítulos, só no selo dela
            self.record, self.unlocked = False, False
            self.seal_new = progress.record_rush(run.session.difficulty)
            self.banner = "REUNIÃO ENCERRADA"
        else:
            had = run.session.difficulty in progress.seals()
            self.record, self.unlocked = progress.record_campaign(secs, run.session.difficulty, run.players,
                                                                  full=self.full)
            self.seal_new = not had
            progress.clear_campaign()
            self.banner = "CAMPANHA CONCLUÍDA"
        self.menu = MenuList([("MENU PRINCIPAL", "menu"), ("JOGAR DE NOVO", "again")],
                             topleft=(64, 356), width=300)

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
        if self.rush:
            line, color = "REUNIÃO DOS CORROMPIDOS: OS 4 CHEFES EM SEQUÊNCIA", theme.BRASS
        elif self.record:
            line, color = "NOVO RECORDE DE TEMPO!", theme.BRASS
        elif not self.full:
            line, color = f"COMEÇARAM NO CAPÍTULO {self.run.start_chapter}: SEM RECORDE", theme.MUTED
        elif best is None:
            line, color = "", theme.MUTED
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

        if self.rush:
            draw_seals(self, screen, pygame.Rect(W - 400, 70, 340, 200), progress.rush_seals(),
                       "SELOS DA REUNIÃO", self.run.session.difficulty if self.seal_new else None)
        else:
            draw_unlock(self, screen, pygame.Rect(W - 400, 70, 340, 200), "cauanzera_ti", "CAUANZERA CORROMPIDO",
                        self.unlocked)
            if self.seal_new:
                label = DIFFICULTIES[self.run.session.difficulty]["label"].upper()
                self.ui.text(screen, f"SELO DE ZERADO NO {label}!", theme.XS, theme.BRASS, (64, 194),
                             anchor="midleft")
        self._stats_panel(screen, pygame.Rect(W - 400, 300, 340, 44 + 22 * (1 + len(self.run.slots))), self.run)
        self.menu.draw(screen, self.ui, self.ticks)
        self.footer(screen, [("↑↓", "ESCOLHER"), ("ENTER", "CONFIRMAR")])
