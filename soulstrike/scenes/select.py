"""Conexão dos celulares e seleção de personagens."""
import random

import pygame

from .. import config, settings, theme
from ..ai import CAMPAIGN_ORDER, DIFFICULTIES, DIFFICULTY_ORDER
from ..controls import key_label
from ..arena import MAPS_BY_KEY, basket_maps, battle_maps, soccer_maps
from ..data import CHARACTERS, MAX_DAMAGE, MAX_HP, MAX_SPEED, roster_indices
from ..soccer_assist import ASSIST_LEVELS, ASSIST_ORDER
from ..basket_powers import BASKET_POWERS
from ..soccer_powers import SOCCER_POWERS
from .. import weapon_art
from ..progress import chapter_cleared
from ..net import server
from ..net.remote import hub
from ..ui import mix
from ..host import host_slot
from .base import crown
from .menus import ModeScene, _MenuScene, category_of


def _button(screen, ui, rect, label, hot):
    ui.panel(screen, rect, fill=theme.INK_3 if hot else theme.INK_2, border=theme.BRASS if hot else theme.LINE_HI)
    ui.text(screen, label, theme.XS, theme.BRASS if hot else theme.BONE, rect.center)


class LobbyScene(_MenuScene):
    """Mostra um QR code por jogador para usar o celular como controle."""

    phase = "lobby"

    def __init__(self, game):
        super().__init__(game)
        session = game.session
        self.campaign = session.campaign
        self.teams = session.team_mode           # 2 x 2 (duelo ou futebol)
        self.fill = session.fill_cpu             # vaga sem ninguém vira CPU (2 x 2 e basquete 1 x 1)
        if self.campaign or self.fill:
            # P1 sempre joga; P2 entra pelo teclado (;) ou celular; P3 e P4 pelo celular.
            # Na campanha quem não entrou fica de fora; no 2x2 a CPU completa os times.
            self.setups = {s.slot: s for s in session.slots}
            self.joined = {s.slot for s in session.slots if not s.cpu} | {1}
            self.slots = [1, 2, 3, 4] if self.campaign or self.teams else [s.slot for s in session.slots]
        else:
            self.slots = [s.slot for s in session.slots]
        self.card_w = 200
        self._layout_cards()
        self.button = pygame.Rect(0, 0, 220, 36)
        self.button.center = (config.SCREEN_W // 2, 432)
        self.layout_button = pygame.Rect(0, 0, 300, 24)
        self.layout_button.center = (config.SCREEN_W // 2, 396)

    def _layout_cards(self):
        """Cartões lado a lado; no 2 x 2, agrupados por time (azul à esquerda, vermelho à direita)."""
        session = self.game.session
        n = len(self.slots)
        if self.teams:
            order = session.teammates(0) + session.teammates(1)
            inner, middle = 12, 56
            total = n * self.card_w + 2 * inner + middle
            x = (config.SCREEN_W - total) // 2
            self.cards = {}
            for i, slot in enumerate(order):
                self.cards[slot] = pygame.Rect(x, 104, self.card_w, 262)
                x += self.card_w + (middle if i == 1 else inner)
            return
        gap = 40 if n == 2 else 16
        total = n * self.card_w + (n - 1) * gap
        x0 = (config.SCREEN_W - total) // 2
        self.cards = {s: pygame.Rect(x0 + i * (self.card_w + gap), 104, self.card_w, 262)
                      for i, s in enumerate(self.slots)}

    def _toggle_layout(self):
        from ..session import TEAM_LAYOUT_ORDER
        session = self.game.session
        i = TEAM_LAYOUT_ORDER.index(session.layout) if session.layout in TEAM_LAYOUT_ORDER else 0
        session.layout = TEAM_LAYOUT_ORDER[(i + 1) % len(TEAM_LAYOUT_ORDER)]
        self._layout_cards()
        self.sfx("click", 0.4)

    def layout_label(self):
        session = self.game.session
        a, b = session.teammates(0), session.teammates(1)
        return f"P{a[0]}+P{a[1]} x P{b[0]}+P{b[1]}"

    def handle(self, event):
        if self.is_back(event):
            self.sfx("cancel", 0.4)
            self.game.change(ModeScene(self.game, category_of(self.game.session.mode)))
        elif event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
            self._continue()
        elif self.teams and event.type == pygame.KEYDOWN and event.key == pygame.K_TAB:
            self._toggle_layout()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.button.collidepoint(event.pos):
            self._continue()
        elif (self.teams and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
              and self.layout_button.collidepoint(event.pos)):
            self._toggle_layout()

    def update(self):
        super().update()
        connected = self.game.connected_slots()
        if self.campaign or self.fill:
            self._update_joined(connected)
        # qualquer jogador no celular pode avançar
        if any(self.game.inputs[s].pressed("confirm") for s in self.slots if s in connected):
            self._continue()

    def _update_joined(self, connected):
        for s in self.slots[1:]:
            if s in connected and s not in self.joined:
                self.joined.add(s)
                self.sfx("select", 0.4)
            elif s not in connected and s in self.joined and s != 2:
                self.joined.discard(s)
        p2 = self.game.inputs[2]
        if 2 not in connected:
            if p2.pressed("confirm") and 2 not in self.joined:
                self.joined.add(2)
                self.sfx("select", 0.4)
            elif p2.pressed("cancel") and 2 in self.joined:
                self.joined.discard(2)
                self.sfx("cancel", 0.3)

    def _continue(self):
        self.sfx("confirm")
        from ..session import SlotSetup
        if self.campaign:
            self.game.session.slots = [self.setups.get(s) or SlotSetup(s) for s in sorted(self.joined)]
        elif self.fill:
            slots = []
            for s in self.slots:
                setup = self.setups.get(s) or SlotSetup(s)
                setup.cpu = s not in self.joined          # vaga sem ninguém: a CPU fecha o time
                slots.append(setup)
            self.game.session.slots = slots
        self.game.change(CharSelectScene(self.game))

    def draw(self, screen):
        W = config.SCREEN_W
        self.draw_background(screen)
        self.title(screen, "QUEM VAI JOGAR?" if self.campaign else "CONECTE OS CELULARES", y=52)
        if self.campaign:
            sub = "ATÉ 4 JOGADORES · CELULAR NA MESMA REDE WI-FI · P1 E P2 TAMBÉM NO TECLADO"
        elif self.fill:
            sub = f"MESMA REDE WI-FI · O P2 ENTRA COM {key_label(2, 'attack')} NO TECLADO · VAGA SEM NINGUÉM VIRA CPU"
        else:
            sub = "MESMA REDE WI-FI · QUEM NÃO CONECTAR JOGA NO TECLADO"
        self.ui.text(screen, sub, theme.XS, theme.MUTED, (64, 84), anchor="midleft")
        connected = self.game.connected_slots()
        if self.teams:
            self._draw_teams(screen)
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
            if self.campaign or self.fill:
                on = slot in self.joined
                empty = "CPU" if self.fill else "AGUARDANDO"
                status = f"NO JOGO · {self.game.device_of(slot)}" if on else empty
                scolor = theme.MOSS if on else theme.MUTED
                phone_only = "SEM CELULAR: CPU" if self.fill else "CELULAR OU CONTROLE"
                p2_keys = f"{key_label(2, 'attack')} ENTRA · {key_label(2, 'special')} SAI"
                hint = {1: "SEMPRE JOGA", 2: p2_keys if slot not in connected else "",
                        3: phone_only, 4: phone_only}[slot]
            else:
                status, scolor = ("CONECTADO", theme.MOSS) if on else ("AGUARDANDO", theme.MUTED)
                hint = "OU TECLADO" if slot <= 2 else ""
            if not on and (self.ticks // 30) % 2:
                scolor = theme.FAINT
            self.ui.text(screen, status, theme.XS, scolor, (rect.centerx, rect.bottom - 40))
            self.ui.text(screen, hint, theme.XS, theme.FAINT, (rect.centerx, rect.bottom - 22))
        hot = self.button.collidepoint(pygame.mouse.get_pos())
        _button(screen, self.ui, self.button, "CONTINUAR", hot or (self.ticks // 40) % 2 == 0)
        fw = server.firewall_hint() if not connected else None
        if fw and (self.ticks // 120) % 2:
            # Linux com o firewall ligado: sem liberar a porta, o celular nunca abre a página
            self.ui.text(screen, f"CELULAR NÃO ABRE? FIREWALL LIGADO, NO TERMINAL: {fw}", theme.XS,
                         theme.BRASS, (W // 2, 470))
        else:
            self.ui.text(screen, f"OU ABRA {self.game.base_url}/?player=N", theme.XS, theme.FAINT, (W // 2, 470))
        items = [("ENTER", "CONTINUAR"), ("ESC", "VOLTAR")]
        if self.teams:
            items.insert(0, ("TAB", "TROCAR TIMES"))
        self.footer(screen, items)

    def _draw_teams(self, screen):
        """Faixa de cada time em volta dos dois cartões e o botão de trocar a divisão."""
        session = self.game.session
        for team in (0, 1):
            rects = [self.cards[s] for s in session.teammates(team)]
            area = rects[0].union(rects[1]).inflate(12, 12)
            color = theme.TEAM_COLORS[team]
            pygame.draw.rect(screen, mix(color, theme.INK, 0.65), area, 2)
            label = pygame.Rect(0, 0, 150, 16)
            label.midtop = (area.centerx, area.bottom - 1)
            screen.fill(mix(color, theme.INK, 0.45), label)
            self.ui.text(screen, f"TIME {theme.TEAM_NAMES[team]}", theme.XS, theme.BONE, label.center, shadow=False)
        left = self.cards[session.teammates(0)[1]]
        self.ui.text(screen, "x", theme.S, theme.MUTED, (left.right + 28, left.centery))
        hot = self.layout_button.collidepoint(pygame.mouse.get_pos())
        self.ui.panel(screen, self.layout_button, fill=theme.INK_3 if hot else theme.INK_2,
                      border=theme.BRASS if hot else theme.LINE)
        self.ui.text(screen, "TIMES: " + self.layout_label(), theme.XS, theme.BRASS if hot else theme.BONE,
                     self.layout_button.center)


_CARD_STAGES = {}


def _card_stage(size, color):
    """Fundo do boneco no card: canhão de luz na cor do jogador caindo do alto e um piso redondo
    aceso embaixo dele, com o fundo escurecendo para as bordas."""
    key = (size, tuple(color[:3]))
    if key in _CARD_STAGES:
        return _CARD_STAGES[key]
    w, h = size
    s = pygame.Surface(size)
    base = mix(theme.INK_2, color, 0.05)
    for y in range(h):                                 # escurece para baixo
        s.fill(mix(base, (0, 0, 0), 0.25 * y / h), (0, y, w, 1))
    cone = pygame.Surface(size)                        # luz em cone (soma na tela)
    cx = w // 2
    for y in range(h - 8):
        half = round(14 + (w * 0.36) * y / h)
        k = 0.10 * (1 - 0.4 * y / h)
        cone.fill(tuple(round(c * k) for c in color[:3]), (cx - half, y, half * 2, 1))
        cone.fill(tuple(round(c * k * 0.5) for c in color[:3]), (cx - half - 4, y, 4, 1))
        cone.fill(tuple(round(c * k * 0.5) for c in color[:3]), (cx + half, y, 4, 1))
    s.blit(cone, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
    floor_y = h - 10
    for i, (rw, k) in enumerate(((96, 0.10), (76, 0.16), (54, 0.24))):   # piso redondo aceso
        disc = pygame.Surface((rw, rw // 4))
        pygame.draw.ellipse(disc, tuple(round(c * k) for c in color[:3]), disc.get_rect())
        s.blit(disc, disc.get_rect(center=(cx, floor_y)), special_flags=pygame.BLEND_RGB_ADD)
    pygame.draw.ellipse(s, mix(color, theme.BONE, 0.3), (cx - 48, floor_y - 12, 96, 24), 1)
    _CARD_STAGES[key] = s
    return s


class _Card:
    def __init__(self, setup, choices):
        self.setup = setup
        self.choices = choices          # índices (em CHARACTERS) que dá para escolher neste modo
        self.ready = setup.cpu
        if setup.char not in choices:
            setup.char = choices[0]
        if setup.cpu:
            self.randomize()

    def randomize(self):
        self.setup.char = random.choice(self.choices)
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
        self.teams = session.team_mode
        slots = session.slots
        if self.teams:
            # 2 x 2: os dois de cada time lado a lado (azul à esquerda)
            slots = sorted(slots, key=lambda s: (session.team_of(s.slot), s.slot))
        # no futebol entram também os craques (só do futebol); o índice é sempre o de CHARACTERS
        self.choices = roster_indices(soccer=self.soccer)
        self.roster = [CHARACTERS[i] for i in self.choices]
        self.cards = [_Card(s, self.choices) for s in slots]
        self.countdown = 0
        self.battle_maps = battle_maps()
        self.basket_maps = basket_maps()
        self.soccer_maps = soccer_maps()
        self.uniform_ok = chapter_cleared(4)      # UNIFORME nas regras (recompensa do capítulo 4)
        self.pitch_index = self.soccer_maps.index(session.map_key) if session.map_key in self.soccer_maps else 0
        keys = [m.key for m in self.battle_maps]
        self.map_index = keys.index(session.map_key) if session.map_key in keys else 0
        # basquete: a quadra é escolhida aqui (fica a última escolhida)
        self.basket = session.basket
        self.court_index = self.basket_maps.index(session.map_key) if session.map_key in self.basket_maps else 0
        n = len(self.cards)
        count = len(self.roster)
        # muitos personagens (futebol): os quadradinhos encolhem para caber na tela
        gap = self.TILE_GAP
        size = min(self.TILE, (config.SCREEN_W - 32 - (count - 1) * gap) // count)
        total = count * size + (count - 1) * gap
        x0 = (config.SCREEN_W - total) // 2
        self.tiles = [pygame.Rect(x0 + i * (size + gap), self.TILE_Y + (self.TILE - size), size, size)
                      for i in range(count)]
        self.campaign = session.campaign
        self.center = pygame.Rect(356, 158, 248, 328)
        if n == 2:
            self.card_rects = [pygame.Rect(40, 158, 300, 328), pygame.Rect(620, 158, 300, 328)]
        elif n == 1:
            # campanha sozinho: cartão + painel da campanha lado a lado
            self.card_rects = [pygame.Rect(198, 158, 300, 328)]
            self.center = pygame.Rect(514, 158, 248, 328)
        elif n == 3:
            w, gap = 206, 12
            x0 = (config.SCREEN_W - (3 * w + 2 * gap + 12 + 248)) // 2
            self.card_rects = [pygame.Rect(x0 + i * (w + gap), 158, w, 328) for i in range(3)]
            self.center = pygame.Rect(self.card_rects[-1].right + 12, 158, 248, 328)
        else:
            w, gap = 206, 12
            x0 = (config.SCREEN_W - (4 * w + 3 * gap)) // 2
            self.card_rects = [pygame.Rect(x0 + i * (w + gap), 158, w, 328) for i in range(4)]
        self.map_arrows = (pygame.Rect(self.center.x + 4, self.center.y + 104, 28, 28),
                           pygame.Rect(self.center.right - 32, self.center.y + 104, 28, 28))
        self.diff_arrows = (pygame.Rect(self.center.x + 4, self.center.y + 254, 28, 28),
                            pygame.Rect(self.center.right - 32, self.center.y + 254, 28, 28))
        self.assist_arrows = (pygame.Rect(self.center.x + 4, self.center.y + 288, 28, 28),
                              pygame.Rect(self.center.right - 32, self.center.y + 288, 28, 28))
        # a assistência escolhida vale para as próximas partidas também
        session.assist = getattr(game, "assist_level", session.assist)
        self.rules_open = False             # START do P1 (ou R): as regras da partida
        self.rules_row = 0
        self._sync_phone_slots()

    # ── estado ───────────────────────────────
    @property
    def _has_difficulty(self):
        return self.game.session.mode in ("cpu", "campaign", "duel2")

    @property
    def _cpu_level_mode(self):
        """Modos em que 1, 2 e 3 escolhem a dificuldade da CPU."""
        return self.game.session.mode in ("cpu", "duel2", "soccer1", "soccer2", "basket1", "basket2", "penaltis1")

    @property
    def _length_mode(self):
        """Futebol (não o basquete): dá para escolher o tamanho da partida."""
        return self.soccer and not self.basket and not self.game.session.penalty

    @staticmethod
    def _length_label():
        length = settings.get("futebol_partida")
        if length == "tempo":
            return f"{config.SOCCER_MINUTES} MINUTOS (EMPATE: GOL DE OURO)"
        if length == "penaltis":
            return f"{config.SOCCER_MINUTES} MINUTOS (EMPATE: PÊNALTIS)"
        return f"PRIMEIRO A {length} GOLS"

    def _cycle_length(self, step=1):
        order = config.SOCCER_LENGTHS
        now = settings.get("futebol_partida")
        i = order.index(now) if now in order else 0
        settings.change("futebol_partida", order[(i + step) % len(order)])
        self.sfx("click", 0.4)

    @property
    def _weapon_pick_mode(self):
        """Duelos (contra a CPU, local e 2 x 2): dá para escolher as armas antes de cada round."""
        return self.game.session.mode in ("cpu", "duel", "duel2")

    @property
    def map_key(self):
        return self.battle_maps[self.map_index].key

    def _humans(self):
        return [c for c in self.cards if not c.setup.cpu]

    def _sync_phone_slots(self):
        """No 2x2, quem não está jogando é CPU: o 2 assume apertando ; (ou conectando o celular)
        e sai com /; o 3 e o 4 entram e saem com o celular."""
        if not self.game.session.fill_cpu:
            return
        before = self.active_slots()
        connected = self.game.connected_slots()
        self._joined_now = set()
        for card in self.cards:
            if card.slot == 1:
                continue
            if card.slot == 2 and card.slot not in connected:
                p2 = self.game.inputs[2]
                if card.setup.cpu and p2.pressed("confirm"):
                    card.setup.cpu = False
                    card.ready = False
                    self._joined_now.add(card)      # o mesmo toque não confirma o personagem
                    self.sfx("select", 0.4)
                elif not card.setup.cpu and not card.ready and p2.pressed("cancel"):
                    card.setup.cpu = True
                    card.ready = True
                    card.randomize()
                    self.sfx("cancel", 0.3)
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
        pos = self.choices.index(card.setup.char) if card.setup.char in self.choices else 0
        card.setup.char = self.choices[(pos + step) % len(self.choices)]
        card.setup.weapon = 0
        self.sfx("select", 0.3)

    def _confirm(self, card):
        if not card.ready:
            card.ready = True
            self.sfx("confirm", 0.5)

    @property
    def court_key(self):
        return self.basket_maps[self.court_index]

    def _cycle_court(self, step):
        self.court_index = (self.court_index + step) % len(self.basket_maps)
        self.sfx("click", 0.4)

    @property
    def pitch_key(self):
        return self.soccer_maps[self.pitch_index]

    def _cycle_pitch(self, step):
        self.pitch_index = (self.pitch_index + step) % len(self.soccer_maps)
        self.sfx("click", 0.4)

    def _cycle_map(self, step):
        self.map_index = (self.map_index + step) % len(self.battle_maps)
        self.sfx("click", 0.4)

    def _cycle_difficulty(self, step):
        s = self.game.session
        order = CAMPAIGN_ORDER if self.campaign else DIFFICULTY_ORDER     # Ibrahim e Borba só na campanha
        i = order.index(s.difficulty) if s.difficulty in order else 1
        s.difficulty = order[(i + step) % len(order)]
        self.sfx("click", 0.4)

    def _cycle_assist(self, step):
        s = self.game.session
        i = ASSIST_ORDER.index(s.assist) if s.assist in ASSIST_ORDER else 1
        s.assist = ASSIST_ORDER[(i + step) % len(ASSIST_ORDER)]
        self.game.assist_level = s.assist
        self.sfx("click", 0.4)

    # ── regras do P1 (a coroa) ───────────────
    @property
    def host(self):
        return host_slot(self.game.session)

    def _toggle_weapons(self, step=1):
        settings.change("armas_por_round", not settings.get("armas_por_round"))
        self.sfx("click", 0.4)

    def rule_rows(self):
        """[(rótulo, valor, trocar(step))] que o P1 pode mexer aqui."""
        s = self.game.session
        rows = []
        if self.basket:
            rows.append(("QUADRA", MAPS_BY_KEY[self.court_key].name.upper(), self._cycle_court))
        elif not self.soccer and not self.campaign:
            rows.append(("MAPA", self.battle_maps[self.map_index].name.upper(), self._cycle_map))
        if self.campaign or s.mode == "cpu":
            rows.append(("DIFICULDADE", DIFFICULTIES[s.difficulty]["label"], self._cycle_difficulty))
        elif self._cpu_level_mode:
            rows.append(("CPU", DIFFICULTIES[s.difficulty]["label"], self._cycle_difficulty))
        if self.soccer and not self.basket:
            rows.append(("ASSISTÊNCIA", ASSIST_LEVELS[s.assist].label, self._cycle_assist))
            if len(self.soccer_maps) > 1 and s.mode in ("soccer1", "soccer2"):
                rows.append(("ESTÁDIO", MAPS_BY_KEY[self.pitch_key].name.upper(), self._cycle_pitch))
        if self._length_mode:
            length = settings.get("futebol_partida")
            label = {"tempo": "3 MIN", "penaltis": "3 MIN + PÊNALTIS"}.get(length, f"{length} GOLS")
            rows.append(("PARTIDA", label, self._cycle_length))
        if self._weapon_pick_mode:
            rows.append(("ARMAS", "A CADA ROUND" if settings.get("armas_por_round") else "FIXAS", self._toggle_weapons))
        if self.uniform_ok:                 # recompensa do capítulo 4: o crachá da Mansão do Carimbo
            rows.append(("UNIFORME", "CRACHÁ DA MANSÃO" if settings.get("uniforme") else "NORMAL",
                         self._toggle_uniform))
        return rows

    def _toggle_uniform(self, step=1):
        settings.change("uniforme", not settings.get("uniforme"))
        self.sfx("click", 0.4)

    def _set_rules(self, value):
        if value and (self.countdown or not self.rule_rows()):
            return
        self.rules_open = value
        self.rules_row = 0
        self.sfx("select" if value else "cancel", 0.4)

    def _update_rules(self, inp):
        rows = self.rule_rows()
        if inp.pressed("pause") or inp.pressed("cancel"):
            self._set_rules(False)
            return
        if inp.pressed("up"):
            self.rules_row = (self.rules_row - 1) % len(rows)
            self.sfx("click", 0.3)
        if inp.pressed("down"):
            self.rules_row = (self.rules_row + 1) % len(rows)
            self.sfx("click", 0.3)
        self.rules_row = min(self.rules_row, len(rows) - 1)
        for action, step in (("char_left", -1), ("char_right", 1), ("confirm", 1)):
            if inp.pressed(action):
                rows[self.rules_row][2](step)

    def _first_open(self):
        for card in self._humans():
            if not card.ready:
                return card
        return None

    # ── entrada ──────────────────────────────
    def handle(self, event):
        if self.rules_open:
            if self.is_back(event) or (event.type == pygame.KEYDOWN and event.key == pygame.K_r):
                self._set_rules(False)
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
            self._set_rules(True)
            return
        if self.is_back(event):
            self.sfx("cancel", 0.4)
            training = self.game.session.mode.startswith("treino")
            back_to_modes = self.game.session.mode == "cpu" or training
            nxt = ModeScene(self.game, category_of(self.game.session.mode)) if back_to_modes else LobbyScene(self.game)
            self.game.change(nxt)
            return
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                card = self._first_open()
                if card:
                    self._confirm(card)
            elif self.basket and event.key in (pygame.K_TAB, pygame.K_RIGHTBRACKET):
                self._cycle_court(1)
            elif self.basket and event.key == pygame.K_LEFTBRACKET:
                self._cycle_court(-1)
            elif self.soccer and event.key == pygame.K_TAB:
                self._cycle_assist(1)
            elif self.campaign and event.key == pygame.K_TAB:
                self._cycle_difficulty(1)
            elif not self.soccer and not self.campaign and event.key in (pygame.K_TAB, pygame.K_RIGHTBRACKET):
                self._cycle_map(1)
            elif not self.soccer and not self.campaign and event.key == pygame.K_LEFTBRACKET:
                self._cycle_map(-1)
            elif self._weapon_pick_mode and event.key == pygame.K_v:
                settings.change("armas_por_round", not settings.get("armas_por_round"))
                self.sfx("click", 0.4)
            elif self._length_mode and event.key == pygame.K_t:
                self._cycle_length()
            elif self._cpu_level_mode and event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                self.game.session.difficulty = DIFFICULTY_ORDER[event.key - pygame.K_1]
                self.sfx("click", 0.4)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            for i, tile in enumerate(self.tiles):
                if tile.collidepoint(pos):
                    card = self._first_open()
                    if card is None:
                        return
                    if card.setup.char == self.choices[i]:
                        self._confirm(card)
                    else:
                        card.setup.char, card.setup.weapon = self.choices[i], 0
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
            if self.basket and pos[1] < 70 and pos[0] > config.SCREEN_W - 320:
                self._cycle_court(1)                   # clique no nome da quadra
                return
            if self.soccer and len(self.cards) == 2:
                for step, r in zip((-1, 1), self.assist_arrows):
                    if r.collidepoint(pos):
                        self._cycle_assist(step)
            if not self.soccer:
                if not self.campaign:
                    for step, r in zip((-1, 1), self.map_arrows):
                        if r.collidepoint(pos):
                            self._cycle_map(step)
                if self._has_difficulty and len(self.cards) < 4:
                    for step, r in zip((-1, 1), self.diff_arrows):
                        if r.collidepoint(pos):
                            self._cycle_difficulty(step)

    def update(self):
        super().update()
        self._sync_phone_slots()
        host = self.game.inputs.get(self.host)
        if self.rules_open and host is not None:
            self._update_rules(host)
        elif host is not None and host.pressed("pause") and not self.countdown:
            self._set_rules(True)
        for card in self._humans():
            if card in getattr(self, "_joined_now", ()):
                continue
            if self.rules_open and card.slot == self.host:
                continue                        # o P1 está mexendo nas regras
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
            if inp.pressed("weapon") and self.basket:
                self._cycle_court(1)                   # no controle/celular: o botão de arma troca a quadra
            if inp.pressed("weapon") and not self.soccer:
                card.setup.weapon = 1 - card.setup.weapon
                self.sfx("select", 0.3)
            if inp.pressed("confirm"):
                self._confirm(card)
        for card in self.cards:
            hub.publish_slot(card.slot, char=card.setup.char, weapon=card.setup.weapon, ready=card.ready,
                             team=self.game.session.team_of(card.slot) if self.teams or self.soccer else None)

        if all(c.ready for c in self.cards) and not self.rules_open:
            self.countdown += 1
            if self.countdown >= 50:
                if self.campaign:
                    from .campaign import start_campaign
                    self.game.change(start_campaign(self.game))
                    return
                session = self.game.session
                session.map_key = (self.court_key if session.basket else
                                   self.pitch_key if self.soccer else self.map_key)
                session.weapon_pick = self._weapon_pick_mode and settings.get("armas_por_round")
                if settings.get("futebol_partida") in config.SOCCER_LENGTHS:
                    session.soccer_length = settings.get("futebol_partida")
                if session.penalty:
                    from .penalty import start_penalties
                    self.game.change(start_penalties(self.game))
                    return
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
        if self.basket:
            self.ui.text(screen, "QUADRA: " + MAPS_BY_KEY[self.court_key].name.upper(), theme.XS, theme.BRASS,
                         (config.SCREEN_W - 64, 56), anchor="midright")
        self._draw_roster(screen)
        for card, rect in zip(self.cards, self.card_rects):
            self._draw_card(screen, card, rect)
        if len(self.cards) < 4:
            self._draw_center(screen)
        if self.countdown:
            veil = pygame.Surface((config.SCREEN_W, 40), pygame.SRCALPHA)
            veil.fill((0, 0, 0, 180))
            screen.blit(veil, (0, config.SCREEN_H - 44))
            self.ui.text(screen, "PREPARANDO A PARTIDA...", theme.S, theme.BRASS,
                         (config.SCREEN_W // 2, config.SCREEN_H - 24))
        elif not self.rules_open:
            items = [("ENTER", "CONFIRMAR"), ("ESC", "VOLTAR")]
            if self.campaign:
                label = DIFFICULTIES[self.game.session.difficulty]["label"]
                items.insert(0, ("TAB", "DIFICULDADE: " + label))
            elif self.basket:
                items.insert(0, ("TAB", "QUADRA: " + MAPS_BY_KEY[self.court_key].name.upper()))
            elif not self.soccer:
                label = "MAPA"
                if len(self.cards) == 4:            # sem o painel do meio: o nome do mapa vai no rodapé
                    label += ": " + self.battle_maps[self.map_index].name.upper()
                items.insert(0, ("TAB", label))
            else:
                items.insert(0, ("TAB", "ASSISTÊNCIA: " + ASSIST_LEVELS[self.game.session.assist].label))
            if self._weapon_pick_mode:
                items.insert(1, ("V", "ARMAS: " + ("A CADA ROUND" if settings.get("armas_por_round") else "FIXAS")))
            if self._length_mode:
                length = settings.get("futebol_partida")
                label = {"tempo": "3 MIN", "penaltis": "3 MIN + PÊNALTIS"}.get(length, f"{length} GOLS")
                items.insert(1, ("T", "PARTIDA: " + label))
            if self.rule_rows():
                items.insert(-1, ("START / R", "REGRAS (P%d)" % self.host))
            if self.game.session.mode == "cpu":
                items.insert(1, ("1 2 3", "DIFICULDADE"))
            elif self._cpu_level_mode and any(c.setup.cpu for c in self.cards):
                items.insert(1, ("1 2 3", "CPU: " + DIFFICULTIES[self.game.session.difficulty]["label"]))
            self.footer(screen, items)
        if self.rules_open:
            self._draw_rules(screen)

    def _draw_rules(self, screen):
        """Painel das regras que só o dono da partida (coroa) mexe."""
        rows = self.rule_rows()
        veil = pygame.Surface((config.SCREEN_W, config.SCREEN_H), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 150))
        screen.blit(veil, (0, 0))
        w, h = 440, 62 + 40 * len(rows)
        box = pygame.Rect((config.SCREEN_W - w) // 2, (config.SCREEN_H - h) // 2 - 10, w, h)
        self.ui.panel(screen, box, fill=theme.INK_2)
        crown(screen, box.x + 26, box.y + 24)
        self.ui.text(screen, "REGRAS DA PARTIDA", theme.S, theme.BRASS, (box.x + 44, box.y + 24), anchor="midleft")
        self.ui.text(screen, f"SÓ O P{self.host}", theme.XS, theme.MUTED, (box.right - 16, box.y + 24),
                     anchor="midright")
        for i, (label, value, _) in enumerate(rows):
            r = pygame.Rect(box.x + 14, box.y + 50 + i * 40, box.w - 28, 34)
            hot = i == self.rules_row
            screen.fill(mix(theme.INK_2, theme.BRASS, 0.18) if hot else theme.INK, r)
            if hot:
                screen.fill(theme.BRASS, (r.x, r.y, 3, r.h))
            self.ui.text(screen, label, theme.XS, theme.MUTED, (r.x + 14, r.centery), anchor="midleft")
            color = theme.BONE if hot else mix(theme.BONE, theme.MUTED, 0.4)
            self.ui.text(screen, ("◀  " if hot else "") + value + ("  ▶" if hot else ""), theme.XS, color,
                         (r.right - 14, r.centery), anchor="midright")
        self.footer(screen, [("↑ ↓", "ESCOLHER"), ("← →", "TROCAR"), ("START / R / ESC", "FECHAR")])

    def _draw_roster(self, screen):
        for i, (tile, stats) in enumerate(zip(self.tiles, self.roster)):
            pickers = [c for c in self.cards if c.setup.char == self.choices[i]]
            screen.fill(theme.SHADOW, tile.move(3, 3))
            fill = theme.INK_3 if pickers else theme.INK_2
            if stats.soccer_only:
                fill = mix(fill, theme.MOSS, 0.22)      # craques do futebol: fundo de gramado
            screen.fill(fill, tile)
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
        if not setup.cpu and setup.slot == self.host and len(self._humans()) > 1:
            crown(screen, head.x + 20 + self.assets.text_width(setup.name, theme.XS), head.centery)
        if setup.cpu:
            source = (DIFFICULTIES[self.game.session.difficulty]["label"]
                      if self._cpu_level_mode
                      else "BONECO" if self.game.session.mode.startswith("treino") else "AUTO")
        else:
            source = self.game.device_of(setup.slot)
        ui.text(screen, source, theme.XS, mix(setup.color, theme.BONE, 0.5), (head.right - 8, head.centery), anchor="midright")

        # sprite andando no lugar
        stage = pygame.Rect(rect.x + 2, head.bottom, rect.w - 4, 138)
        screen.blit(_card_stage(stage.size, setup.color), stage)
        sprites = self.assets.sprites[stats.key]
        if self.soccer:                                  # no futebol o card já mostra o uniforme do time
            sprites = self.assets.kit_sprites(stats.key, self.game.session.team_of(setup.slot))
        if card.ready:
            img = sprites.pose("frente", "parado", (self.ticks // 30) % 2)
        else:
            img = sprites.frame("frente", self.ticks // 5)
        img = pygame.transform.scale(img, (img.get_width() * 2, img.get_height() * 2))
        ground = stage.bottom - 10
        pygame.draw.ellipse(screen, theme.SHADOW, (stage.centerx - 30, ground - 6, 60, 12))
        screen.blit(img, img.get_rect(midbottom=(stage.centerx, ground + 2)))
        if self.teams:
            # etiqueta do time por cima do boneco, no canto de baixo (o chapéu/cabeça fica livre)
            team = self.game.session.team_of(setup.slot)
            color = theme.TEAM_COLORS[team]
            screen.fill(color, (stage.x, stage.y, 3, stage.h))
            label = self.assets.text(theme.TEAM_NAMES[team], theme.XS, theme.BONE)
            chip = label.get_rect(bottomleft=(stage.x + 7, stage.bottom - 5)).inflate(8, 4)
            screen.fill(mix(theme.INK_2, color, 0.55), chip)
            pygame.draw.rect(screen, color, chip, 1)
            screen.blit(label, label.get_rect(center=chip.center))
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
            basket = self.game.session.basket
            power = (BASKET_POWERS if basket else SOCCER_POWERS)[stats.key]
            extra = power.passive if basket else (stats.ability_desc if stats.soccer_only else "")
            y += 4
            ui.text(screen, "SUPER: " + power.name, theme.XS, theme.BRASS, (rect.x + 14, y), anchor="midleft")
            for line in ui.wrap(power.description, theme.XS, rect.w - 28)[:2 if extra else 3]:
                y += 12
                ui.text(screen, line, theme.XS, theme.MUTED, (rect.x + 14, y), anchor="midleft", shadow=False)
            if basket and extra:
                y += 15
                ui.text(screen, "SEMPRE:", theme.XS, theme.MOSS, (rect.x + 14, y), anchor="midleft")
                for line in ui.wrap(extra, theme.XS, rect.w - 28)[:2]:
                    y += 12
                    ui.text(screen, line, theme.XS, theme.MUTED, (rect.x + 14, y), anchor="midleft", shadow=False)
            elif stats.soccer_only:
                # craque: além do SUPER, uma habilidade que vale o jogo todo
                y += 15
                ui.text(screen, "SEMPRE: " + stats.ability_name.upper(), theme.XS, theme.MOSS,
                        (rect.x + 14, y), anchor="midleft")
                for line in ui.wrap(stats.ability_desc, theme.XS, rect.w - 28)[:2]:
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
            if weapon.is_melee:
                kind = "CORPO" if rect.w < 260 else "CORPO A CORPO"     # cartão estreito: rótulo curto
            else:
                kind = f"{weapon.mag} TIROS" if weapon.mag else "À DISTÂNCIA"
            ui.text(screen, "ARMA", theme.XS, theme.MUTED, (rect.x + 14, y), anchor="midleft", shadow=False)
            name_rect = ui.text(screen, weapon.name.upper(), theme.XS, theme.BONE, (rect.x + 60, y), anchor="midleft")
            kind_rect = ui.text(screen, kind, theme.XS, theme.FAINT, (rect.right - 14, y), anchor="midright", shadow=False)
            art = weapon_art.icon(weapon.name)
            if art is not None:
                screen.blit(art, art.get_rect(center=((name_rect.right + kind_rect.left) // 2, y)))

        # rodapé do cartão
        foot = pygame.Rect(rect.x + 8, rect.bottom - 30, rect.w - 16, 22)
        if setup.cpu and self.game.session.fill_cpu:
            # vaga sem ninguém: a CPU joga, mas dá para assumir
            if setup.slot == 2:
                ui.hints(screen, [(key_label(2, "attack"), "ASSUMIR A VAGA")], foot.center, gap=8)
            else:
                ui.text(screen, "CELULAR OU CONTROLE", theme.XS, theme.FAINT, foot.center, shadow=False)
        elif card.ready:
            screen.fill(mix(theme.MOSS, theme.INK, 0.55), foot)
            ui.text(screen, "PRONTO", theme.XS, theme.BONE, foot.center)
        elif setup.slot in hub.connected_slots():
            ui.text(screen, "ESCOLHA PELO CELULAR", theme.XS, theme.MUTED, foot.center, shadow=False)
        elif setup.slot in self.game.gamepads.slots():
            keys = [("← →", ""), ("↑", ""), ("A", "OK")]
            ui.hints(screen, [keys[0], keys[2]] if self.soccer else keys, foot.center, gap=8)
        elif setup.slot <= 2:
            s = setup.slot
            keys = [(f"{key_label(s, 'left')} {key_label(s, 'right')}", ""), (key_label(s, "up"), ""),
                    (key_label(s, "attack"), "OK")]
            if self.soccer:
                keys = [keys[0], keys[2]]
            ui.hints(screen, keys, foot.center, gap=8)

    def _draw_center(self, screen):
        ui = self.ui
        c = self.center
        if self.campaign:
            self._draw_campaign_panel(screen, c)
            return
        if self.soccer:
            ui.panel(screen, c, fill=theme.INK_2)
            if self.basket:                              # basquete: a quadra escolhida e a regra dele
                ui.text(screen, "QUADRA", theme.S, theme.BONE, (c.centerx, c.y + 30))
                thumb = self.game.thumbnail(MAPS_BY_KEY[self.court_key], (220, 124))
                mode = self.game.session.mode
                rule = ("3 MINUTOS OU 21 PONTOS" if mode == "basket1"
                        else "2 TEMPOS DE 2 MINUTOS" if mode == "basket2" else "TREINO LIVRE")
            else:
                ui.text(screen, "ESTÁDIO", theme.S, theme.BONE, (c.centerx, c.y + 30))
                thumb = self.game.thumbnail(MAPS_BY_KEY["campo_futebol"], (220, 124))
                training = self.game.session.mode.startswith("treino")
                rule = "TREINO LIVRE" if training or not self._length_mode else self._length_label()
            screen.blit(thumb, thumb.get_rect(midtop=(c.centerx, c.y + 56)))
            ui.text(screen, rule, theme.XS, theme.BRASS, (c.centerx, c.y + 188))
            ui.paragraph(screen, "Cada personagem tem um poder próprio no botão SUPER.", theme.XS,
                         theme.MUTED, (c.x + 16, c.y + 204), c.w - 32, spacing=14)
            screen.fill(theme.LINE, (c.x + 16, c.y + 258, c.w - 32, 1))
            ui.text(screen, "ASSISTÊNCIA", theme.XS, theme.MUTED, (c.centerx, c.y + 272))
            ui.text(screen, ASSIST_LEVELS[self.game.session.assist].label, theme.S, theme.BRASS,
                    (c.centerx, c.y + 302))
            mouse = pygame.mouse.get_pos()
            for direction, r in zip(("left", "right"), self.assist_arrows):
                ui.arrow(screen, r.center, direction, 7, theme.BRASS if r.collidepoint(mouse) else theme.MUTED)
            return
        ui.panel(screen, c, fill=theme.INK_2)
        ui.text(screen, "ARENA", theme.XS, theme.MUTED, (c.centerx, c.y + 20))
        cfg = self.battle_maps[self.map_index]
        ui.text(screen, cfg.name.upper(), theme.XS, theme.BONE, (c.centerx, c.y + 40))
        thumb = self.game.thumbnail(cfg, (180, 124))
        tr = thumb.get_rect(midtop=(c.centerx, c.y + 56))
        screen.fill(theme.SHADOW, tr.inflate(4, 4))
        screen.blit(thumb, tr)
        mouse = pygame.mouse.get_pos()
        for direction, r in zip(("left", "right"), self.map_arrows):
            ui.arrow(screen, r.center, direction, 7, theme.BRASS if r.collidepoint(mouse) else theme.MUTED)
        dots_y = tr.bottom + 14
        n = len(self.battle_maps)
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
            text = ("Escolha o seu lutador. O boneco fica parado e não ataca."
                    if self.game.session.mode.startswith("treino") else "Os dois confirmam e a luta começa.")
            ui.paragraph(screen, text, theme.XS, theme.MUTED,
                         (c.x + 16, c.y + 236), c.w - 32, spacing=14)

    def _draw_campaign_panel(self, screen, c):
        ui = self.ui
        ui.panel(screen, c, fill=theme.INK_2)
        ui.text(screen, "CAMPANHA", theme.S, theme.BONE, (c.centerx, c.y + 26))
        thumb = self.game.thumbnail(MAPS_BY_KEY["floresta"], (200, 100))
        tr = thumb.get_rect(midtop=(c.centerx, c.y + 48))
        screen.fill(theme.SHADOW, tr.inflate(4, 4))
        screen.blit(thumb, tr)
        ui.text(screen, "3 FASES · CHEFÃO NO FIM", theme.XS, theme.BRASS, (c.centerx, tr.bottom + 16))
        ui.paragraph(screen, "Levantem quem cair. Melhorias a cada fase.", theme.XS,
                     theme.MUTED, (c.x + 16, tr.bottom + 32), c.w - 32, spacing=14)
        screen.fill(theme.LINE, (c.x + 16, c.y + 226, c.w - 32, 1))
        ui.text(screen, "DIFICULDADE", theme.XS, theme.MUTED, (c.centerx, c.y + 244))
        level = DIFFICULTIES[self.game.session.difficulty]
        hard = self.game.session.difficulty in ("ibrahim", "borba")
        ui.text(screen, level["label"], theme.S, theme.BLOOD if hard else theme.BRASS, (c.centerx, c.y + 268))
        if level.get("tagline"):
            for k, line in enumerate(ui.wrap(level["tagline"], theme.XS, c.w - 32)):
                ui.text(screen, line, theme.XS, theme.BONE, (c.centerx, c.y + 290 + 12 * k))
        mouse = pygame.mouse.get_pos()
        for direction, r in zip(("left", "right"), self.diff_arrows):
            ui.arrow(screen, r.center, direction, 7, theme.BRASS if r.collidepoint(mouse) else theme.MUTED)
