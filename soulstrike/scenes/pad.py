"""Tela CONTROLE: o controle desenhado, o que cada botão faz, troca de botões, perfis e modo teste.

Feita para ser usada com o próprio controle: as setas escolhem o botão, A abre a lista de ações,
LB/RB trocam a aba (luta ou esportes), X troca o perfil e Y entra no modo teste. Quem edita é o
controle que apertou o último botão, então cada um arruma o seu.
"""
import pygame

from .. import config, pad_profiles, theme
from ..pad_art import draw_pad, face_positions, keycap
from .menus import ControlsScene, TitleScene, _MenuScene

LEFT = ["lt", "lb"]
FIXED_LEFT = [("ls", "MOVER"), ("dpad", "MOVER / ARMA")]
BOTTOM = [("back", "VOLTAR"), ("start", "PAUSA")]
BOX_W, BOX_H = 190, 30
EXIT_HOLD = 40                  # segurar START no modo teste por ~0,7 s para sair


class PadScene(_MenuScene):
    every_pad = True                    # qualquer controle navega aqui (cada um configura o seu)
    menu_keys = True
    show_cursor = True

    def __init__(self, game, back=None):
        super().__init__(game)
        self.back = back or TitleScene
        self.pad_index = 0
        self.context = 0                # 0 = luta, 1 = bola
        self.side, self.row = 1, 0      # coluna (0 esquerda, 1 direita) e linha do botão escolhido
        self.picking = None             # índice na lista de ações, quando ela está aberta
        self.testing = False
        self.start_hold = 0
        self.last_test = None           # último botão apertado no modo teste
        self.message = ""
        self.boxes = {}                 # botão → retângulo (para o mouse)
        self.preset_rects = {}
        self.pick_rects = []

    # ── qual controle ────────────────────────
    @property
    def pads(self):
        return self.game.gamepads.pads

    @property
    def pad(self):
        pads = self.pads
        if not pads:
            return None
        self.pad_index = min(self.pad_index, len(pads) - 1)
        return pads[self.pad_index]

    @property
    def name(self):
        return self.pad.name if self.pad else ""

    @property
    def family(self):
        return pad_profiles.family(self.name)

    @property
    def ctx(self):
        return pad_profiles.CONTEXTS[self.context]

    @property
    def joycon(self):
        return self.family == "joycon"

    def right_column(self):
        face = face_positions(self.family)
        order = sorted(face, key=lambda b: (face[b][1], face[b][0]))     # de cima para baixo
        return (["rb"] if self.joycon else ["rt", "rb"]) + order

    def columns(self):
        return [["lb"] if self.joycon else LEFT, self.right_column()]

    @property
    def button(self):
        col = self.columns()[self.side]
        self.row = min(self.row, len(col) - 1)
        return col[self.row]

    # ── ações ────────────────────────────────
    def _open_picker(self):
        if self.pad is None:
            self.message = "CONECTE UM CONTROLE PARA TROCAR OS BOTÕES"
            self.sfx("cancel", 0.3)
            return
        actions = [a for a, _ in pad_profiles.ACTIONS[self.ctx]]
        current = pad_profiles.mapping(self.name, self.ctx)[self.button]
        self.picking = actions.index(current) if current in actions else 0
        self.message = ""
        self.sfx("click", 0.4)

    def _pick(self, index):
        action = pad_profiles.ACTIONS[self.ctx][index][0]
        pad_profiles.set_action(self.name, self.ctx, self.button, action)
        self.picking = None
        self.sfx("confirm", 0.4)

    def _cycle_preset(self, step=1):
        if self.pad is None:
            return
        order = pad_profiles.presets(self.name)
        i = order.index(pad_profiles.preset(self.name))
        pad_profiles.set_preset(self.name, order[(i + step) % len(order)])
        self.sfx("click", 0.4)

    def _move(self, dx, dy):
        cols = self.columns()
        if dx:
            self.side = 1 - self.side
            self.row = min(self.row, len(cols[self.side]) - 1)
        if dy:
            self.row = (self.row + dy) % len(cols[self.side])
        self.sfx("select", 0.25)

    def _leave(self):
        self.sfx("cancel", 0.4)
        self.game.change(self.back(self.game))

    # ── eventos ──────────────────────────────
    def handle(self, event):
        if self.testing:
            self._handle_test(event)
            return
        if self.picking is not None:
            self._handle_picker(event)
            return
        if event.type == pygame.KEYDOWN:
            key = event.key
            if key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                self._leave()
            elif key in (pygame.K_UP, pygame.K_w):
                self._move(0, -1)
            elif key in (pygame.K_DOWN, pygame.K_s):
                self._move(0, 1)
            elif key in (pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d):
                self._move(1, 0)
            elif key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                self._open_picker()
            elif key in (pygame.K_PAGEUP, pygame.K_PAGEDOWN, pygame.K_q, pygame.K_e):
                self.context = 1 - self.context
                self.sfx("select", 0.25)
            elif key == pygame.K_TAB:
                self._cycle_preset()
            elif key == pygame.K_c:
                if self.pad is not None:
                    self.testing, self.last_test, self.start_hold = True, None, 0
                    self.sfx("confirm", 0.4)
            elif key == pygame.K_k and not getattr(event, "from_pad", False):
                self.sfx("confirm", 0.4)
                self.game.change(ControlsScene(self.game))
            elif key == pygame.K_n and len(self.pads) > 1:
                self.pad_index = (self.pad_index + 1) % len(self.pads)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for b, r in self.boxes.items():
                if r.collidepoint(event.pos):
                    for side, col in enumerate(self.columns()):
                        if b in col:
                            self.side, self.row = side, col.index(b)
                    self._open_picker()
                    return
            for p, r in self.preset_rects.items():
                if r.collidepoint(event.pos) and self.pad is not None:
                    pad_profiles.set_preset(self.name, p)
                    self.sfx("click", 0.4)
                    return
            for i, r in enumerate(getattr(self, "tab_rects", [])):
                if r.collidepoint(event.pos):
                    self.context = i
                    return
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            self._leave()

    def _handle_picker(self, event):
        n = len(pad_profiles.ACTIONS[self.ctx])
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.picking = (self.picking - 1) % n
                self.sfx("select", 0.25)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.picking = (self.picking + 1) % n
                self.sfx("select", 0.25)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                self._pick(self.picking)
            elif event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                self.picking = None
                self.sfx("cancel", 0.3)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, r in enumerate(self.pick_rects):
                if r.collidepoint(event.pos):
                    self._pick(i)
                    return
            self.picking = None
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            self.picking = None

    def _handle_test(self, event):
        # no modo teste os botões do controle não navegam: só o teclado e o mouse
        if getattr(event, "from_pad", False):
            return
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                self.testing = False
                self.sfx("cancel", 0.3)
            elif event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                self._nudge_deadzone(-1 if event.key == pygame.K_LEFT else 1)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            self.testing = False

    def _nudge_deadzone(self, step):
        if self.pad is None:
            return
        pad_profiles.set_deadzone(self.name, pad_profiles.deadzone(self.name) + step * 0.02)
        self.sfx("click", 0.3)

    def update(self):
        super().update()
        # quem apertou o último botão é o controle que a tela mostra (cada um arruma o seu)
        if not self.testing:
            for i, pad in enumerate(self.pads):
                if pad.pressed:
                    self.pad_index = i
            return
        pad = self.pad
        if pad is None:
            self.testing = False
            return
        for b in ("a", "b", "x", "y", "lb", "rb", "lt", "rt", "back", "start"):
            if b in pad.pressed and not (self.joycon and b in ("lt", "rt")):
                self.last_test = b
                self.sfx("click", 0.25)
        if "back" in pad.held:              # BACK + ←→ ajusta a zona morta pelo controle
            if "left" in pad.pressed:
                self._nudge_deadzone(-1)
            elif "right" in pad.pressed:
                self._nudge_deadzone(1)
        self.start_hold = self.start_hold + 1 if "start" in pad.held else 0
        if self.start_hold >= EXIT_HOLD:
            self.testing = False
            self.sfx("cancel", 0.3)

    # ── desenho ──────────────────────────────
    def draw(self, screen):
        self.draw_background(screen)
        self._header(screen)
        if self.testing:
            self._draw_test(screen)
        else:
            self._draw_config(screen)

    def _header(self, screen):
        W = config.SCREEN_W
        self.title(screen, "CONTROLE", y=44)
        chip = pygame.Rect(0, 0, 300, 26)
        chip.midright = (W - 64, 44)
        screen.fill(theme.INK_2, chip)
        pad = self.pad
        if pad is None:
            pygame.draw.rect(screen, theme.LINE, chip, 1)
            self.ui.text(screen, "NENHUM CONTROLE CONECTADO", theme.XS, theme.MUTED, chip.center, shadow=False)
            return
        slot = self.game.gamepads.slot_of(self.pad_index)
        color = theme.SLOT_COLORS.get(slot, theme.MUTED)
        pygame.draw.rect(screen, color, chip, 2)
        self.ui.text(screen, f"P{slot}" if slot else "--", theme.XS, color, (chip.x + 12, chip.centery),
                     anchor="midleft")
        name = pad.name.upper()
        if len(name) > 26:
            name = name[:25] + "…"
        self.ui.text(screen, name, theme.XS, theme.BONE, (chip.x + 44, chip.centery), anchor="midleft", shadow=False)
        if len(self.pads) > 1:
            self.ui.text(screen, f"{self.pad_index + 1}/{len(self.pads)}", theme.XS, theme.MUTED,
                         (chip.right - 10, chip.centery), anchor="midright", shadow=False)

    def _tabs(self, screen):
        x = config.SCREEN_W // 2 - 190
        self.tab_rects = []
        for i, ctx in enumerate(pad_profiles.CONTEXTS):
            name = pad_profiles.CONTEXT_LABELS[ctx]
            w = self.assets.text_width(name, theme.XS) + 28
            r = pygame.Rect(x, 82, w, 24)
            self.tab_rects.append(r)
            on = i == self.context
            screen.fill(theme.INK_3 if on else theme.INK_2, r)
            screen.fill(theme.BRASS if on else theme.LINE, (r.x, r.bottom - 3, r.w, 3))
            self.ui.text(screen, name, theme.XS, theme.BRASS if on else theme.MUTED, r.center, shadow=False)
            x += w + 8

    def _box(self, screen, button, rect, text, on, changed=False, fixed=False):
        labels = pad_profiles.LABELS[self.family]
        screen.fill(theme.SHADOW, rect.move(2, 2))
        screen.fill(theme.INK_3 if on else theme.INK_2, rect)
        pygame.draw.rect(screen, theme.BRASS if on else theme.LINE, rect, 2 if on else 1)
        cap = keycap(screen, self.ui, self.family, button, (rect.x + 8, rect.centery), labels)
        if text == "—":
            color = theme.FAINT
        elif changed:
            color = theme.BRASS
        else:
            color = theme.MUTED if fixed else theme.BONE
        self.ui.text(screen, text, theme.XS, color, (cap.right + 8, rect.centery), anchor="midleft", shadow=False)
        if changed:
            pygame.draw.circle(screen, theme.BRASS, (rect.right - 9, rect.centery), 3)

    def _line(self, screen, start, end, on, side):
        col = theme.BRASS if on else theme.LINE_HI
        width = 2 if on else 1
        elbow = (start[0] + 14 * side, start[1])
        pygame.draw.line(screen, col, start, elbow, width)
        pygame.draw.line(screen, col, elbow, end, width)
        pygame.draw.circle(screen, col, end, 3)

    def _draw_config(self, screen):
        W = config.SCREEN_W
        self._tabs(screen)
        name, ctx = self.name, self.ctx
        mapping = pad_profiles.mapping(name, ctx)
        changed = pad_profiles.changed(name, ctx) if self.pad else set()
        words = pad_profiles.ACTION_LABELS[ctx]
        chosen = self.button
        anchors = draw_pad(screen, self.ui, self.family, (W // 2, 262), 4, lit=chosen,
                           pulse=0.3 + 0.3 * ((self.ticks // 10) % 2))
        self.boxes = {}
        # coluna da esquerda: gatilho e ombro trocáveis, analógico e direcional fixos
        left = [(b, words[mapping[b]] if mapping[b] != "none" else "—", False) for b in self.columns()[0]]
        left += [(b, t, True) for b, t in (FIXED_LEFT[:1] if self.joycon else FIXED_LEFT)]
        for i, (b, text, fixed) in enumerate(left):
            rect = pygame.Rect(64, 126 + i * 52, BOX_W, BOX_H)
            on = b == chosen
            self._line(screen, rect.midright, anchors[b], on, 1)
            self._box(screen, b, rect, text, on, b in changed, fixed)
            if not fixed:
                self.boxes[b] = rect
        for i, b in enumerate(self.right_column()):
            rect = pygame.Rect(W - 64 - BOX_W, 106 + i * 40, BOX_W, BOX_H)
            on = b == chosen
            self._line(screen, rect.midleft, anchors[b], on, -1)
            text = words[mapping[b]] if mapping[b] != "none" else "—"
            self._box(screen, b, rect, text, on, b in changed)
            self.boxes[b] = rect
        bottom = [("start", "PAUSA")] if self.joycon else BOTTOM
        for i, (b, text) in enumerate(bottom):
            rect = pygame.Rect(0, 0, 150, 26)
            rect.midtop = (W // 2 + (0 if self.joycon else -84 if i == 0 else 84), 398)
            ax, ay = anchors[b]
            pygame.draw.line(screen, theme.LINE_HI, (ax, ay), (ax, 382), 1)
            pygame.draw.line(screen, theme.LINE_HI, (ax, 382), (rect.centerx, 382), 1)
            pygame.draw.line(screen, theme.LINE_HI, (rect.centerx, 382), rect.midtop, 1)
            pygame.draw.circle(screen, theme.LINE_HI, (ax, ay), 3)
            self._box(screen, b, rect, text, False, fixed=True)
        # perfis
        y = 446
        self.ui.text(screen, "PERFIL", theme.XS, theme.MUTED, (W // 2 - 258, y), anchor="midleft")
        x = W // 2 - 200
        current = pad_profiles.preset(name) if self.pad else "padrao"
        self.preset_rects = {}
        for p in pad_profiles.presets(self.name):
            text = pad_profiles.PRESET_LABELS[p]
            w = self.assets.text_width(text, theme.XS) + 22
            r = pygame.Rect(x, y - 11, w, 22)
            self.preset_rects[p] = r
            on = p == current
            screen.fill(theme.INK_3 if on else theme.INK_2, r)
            pygame.draw.rect(screen, theme.BRASS if on else theme.LINE, r, 1)
            self.ui.text(screen, text, theme.XS, theme.BRASS if on else theme.MUTED, r.center, shadow=False)
            x += w + 8
        if self.message:
            self.ui.text(screen, self.message, theme.XS, theme.BLOOD, (W // 2, 476))
        if self.picking is not None:
            self._draw_picker(screen)
            self.footer(screen, [("↑↓", "AÇÃO"), (pad_profiles.text_label(self.name, "a"), "CONFIRMAR"),
                                 (pad_profiles.text_label(self.name, "b"), "CANCELAR")])
        else:
            t = lambda b: pad_profiles.text_label(self.name, b)         # noqa: E731
            self.footer(screen, [("SETAS", "BOTÃO"), (t("a"), "TROCAR"), (f"{t('lb')} {t('rb')}", "ABA"),
                                 (t("x"), "PERFIL"), (t("y"), "TESTAR"), ("K", "TECLADO"), (t("b"), "VOLTAR")])

    def _draw_picker(self, screen):
        W = config.SCREEN_W
        box = self.boxes[self.button]
        items = pad_profiles.ACTIONS[self.ctx]
        h = 8 + 26 * len(items)
        lst = pygame.Rect(0, 0, BOX_W + 20, h)
        if self.side == 1:
            lst.topright = (box.right, box.bottom + 4)
        else:
            lst.topleft = (box.left, box.bottom + 4)
        lst.bottom = min(lst.bottom, config.SCREEN_H - 44)
        screen.fill(theme.SHADOW, lst.move(3, 3))
        screen.fill(theme.INK_3, lst)
        pygame.draw.rect(screen, theme.BRASS, lst, 2)
        self.pick_rects = []
        labels = pad_profiles.LABELS[self.family]
        for i, (action, text) in enumerate(items):
            r = pygame.Rect(lst.x + 4, lst.y + 4 + i * 26, lst.w - 8, 24)
            self.pick_rects.append(r)
            on = i == self.picking
            if on:
                screen.fill(theme.INK, r)
                screen.fill(theme.BRASS, (r.x, r.y, 3, r.h))
            self.ui.text(screen, text, theme.XS, theme.BRASS if on else theme.BONE, (r.x + 12, r.centery),
                         anchor="midleft", shadow=False)
            if action != "none":
                where = pad_profiles.buttons_with(self.name, self.ctx, action)
                text = " ".join(labels.get(b) or b.upper() for b in where if labels.get(b))
                self.ui.text(screen, text, theme.XS, theme.FAINT, (r.right - 8, r.centery), anchor="midright",
                             shadow=False)
        what = pad_profiles.text_label(self.name, self.button)
        veil = pygame.Surface((W, 30), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 190))
        screen.blit(veil, (0, 468))
        self.ui.text(screen, f"O QUE O {what} VAI FAZER?  UMA AÇÃO PODE FICAR EM DOIS BOTÕES", theme.XS,
                     theme.BRASS, (W // 2, 483))

    def _draw_test(self, screen):
        W, H = config.SCREEN_W, config.SCREEN_H
        pad = self.pad
        self.ui.text(screen, "MODO TESTE", theme.S, theme.BRASS, (W // 2, 92))
        self.ui.text(screen, "APERTE QUALQUER BOTÃO: ELE ACENDE E MOSTRA O QUE FAZ", theme.XS, theme.MUTED,
                     (W // 2, 112), shadow=False)
        held = pad.held if pad else set()
        anchors = draw_pad(screen, self.ui, self.family, (W // 2, 280), 4, lit=self.last_test,
                           pulse=0.4, pressed=held)
        b = self.last_test
        if b:
            ax, ay = anchors[b]
            name = pad_profiles.text_label(self.name, b)
            if b in pad_profiles.buttons(self.name):
                luta = pad_profiles.mapping(self.name, "luta")[b]
                bola = pad_profiles.mapping(self.name, "bola")[b]
                top = pad_profiles.ACTION_LABELS["luta"].get(luta, "") if luta != "none" else "NADA"
                low = pad_profiles.ACTION_LABELS["bola"].get(bola, "") if bola != "none" else "NADA"
                lines = (f"{name} = {top}", f"NO FUTEBOL E BASQUETE: {low}")
            else:
                lines = (f"{name} = {'PAUSA' if b == 'start' else 'VOLTAR'}", "SEMPRE IGUAL")
            bal = pygame.Rect(0, 0, max(250, self.assets.text_width(lines[0], theme.S) + 30), 50)
            bal.midbottom = (max(bal.w // 2 + 8, min(W - bal.w // 2 - 8, ax)), 186)
            screen.fill(theme.SHADOW, bal.move(3, 3))
            screen.fill(theme.INK_3, bal)
            pygame.draw.rect(screen, theme.BRASS, bal, 2)
            pygame.draw.line(screen, theme.BRASS, (ax, bal.bottom), (ax, ay - 14), 2)
            self.ui.text(screen, lines[0], theme.S, theme.BONE, (bal.centerx, bal.y + 17))
            self.ui.text(screen, lines[1], theme.XS, theme.MUTED, (bal.centerx, bal.y + 37), shadow=False)
        # analógico e zona morta
        box = pygame.Rect(96, 380, 150, 100)
        self.ui.panel(screen, box)
        self.ui.text(screen, "ANALÓGICO", theme.XS, theme.MUTED, (box.centerx, box.y + 14), shadow=False)
        c = (box.centerx, box.y + 58)
        dz = pad_profiles.deadzone(self.name)
        pygame.draw.circle(screen, theme.LINE_HI, c, 30, 1)
        pygame.draw.circle(screen, theme.FAINT, c, max(2, round(30 * dz)), 1)
        if pad:
            raw = (pad.reader.axis("lx"), pad.reader.axis("ly"))
            pygame.draw.circle(screen, theme.BRASS if pad.stick != (0.0, 0.0) else theme.MUTED,
                               (c[0] + round(raw[0] * 30), c[1] + round(raw[1] * 30)), 4)
        box2 = pygame.Rect(W - 246, 380, 150, 100)
        self.ui.panel(screen, box2)
        self.ui.text(screen, "ZONA MORTA", theme.XS, theme.MUTED, (box2.centerx, box2.y + 14), shadow=False)
        bar = pygame.Rect(0, 0, 110, 8)
        bar.center = (box2.centerx, box2.y + 50)
        lo, hi = pad_profiles.DEADZONE_RANGE
        self.ui.bar(screen, bar, (dz - lo) / (hi - lo), theme.BRASS, ticks=10)
        self.ui.text(screen, f"{round(dz * 100)}%", theme.XS, theme.BONE, (box2.centerx, box2.y + 70), shadow=False)
        self.ui.text(screen, pad_profiles.text_label(self.name, "back") + " + ←→", theme.XS, theme.FAINT, (box2.centerx, box2.y + 86), shadow=False)
        hold = self.start_hold / EXIT_HOLD
        self.footer(screen, [("SEGURE START" if hold == 0 else f"SAINDO {round(hold * 100)}%", "SAIR DO TESTE"),
                             ("ESC", "SAIR")])
