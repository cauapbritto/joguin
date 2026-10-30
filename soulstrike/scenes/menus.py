"""Telas de menu: carregamento, título, modos e telas de informação."""
import math
import webbrowser

import pygame

from .. import config, settings, theme
from ..controls import (REBINDABLE, PlayerInput, bind_key, current_key, default_key, key_label, move_label,
                        reset_keys)
from ..data import CHARACTERS, SHADOW_CHARACTERS, roster
from ..net import server
from ..session import MODES, Session, SlotSetup
from ..ui import Backdrop, MenuList
from .base import Scene


class LoadingScene(Scene):
    music = None

    def __init__(self, game):
        super().__init__(game)
        self.progress = 0.0
        self._steps = None

    def update(self):
        super().update()
        if self._steps is None:
            self._steps = self._load()
        try:
            next(self._steps)
        except StopIteration:
            server.set_previews(self.assets.portrait_pngs())
            from ..net.remote import hub
            hub.roster_size = len(CHARACTERS)          # o celular recebe todos (acha o escolhido pelo índice)
            if not self.game.headless:
                server.start_in_background()
            from .. import novidades
            news = novidades.to_show()
            novidades.mark_seen()
            self.game.change(NewsScene(self.game, news) if news else TitleScene(self.game))

    def _load(self):
        for progress in self.assets.load_steps():
            self.progress = progress
            yield
        # os QR codes da tela de conexão também ficam prontos aqui (gerar na hora dava um tranco)
        for slot in (1, 2, 3, 4):
            self.assets.qr(f"{self.game.base_url}/?player={slot}", module=4)
            yield
        # e o cenário pintado dos mapas (chão e paredes ficam guardados)
        from ..arena import MAPS, Arena
        from ..scenery import THEMED_MAPS
        for cfg in MAPS:                 # arenas, variações e acampamentos da campanha
            if cfg.scenery in THEMED_MAPS:
                Arena(cfg, self.assets)
                yield
        # e as almas corrompidas de cada herói (campanha)
        for stats in CHARACTERS:
            if stats.key not in SHADOW_CHARACTERS and not stats.soccer_only:
                self.assets.shadow_sprites(stats.sprite)
                yield

    def draw(self, screen):
        screen.fill(theme.INK)
        W, H = config.SCREEN_W, config.SCREEN_H
        self.ui.logo(screen, (W // 2, H // 2 - 30))
        bar = pygame.Rect(0, 0, 320, 10)
        bar.center = (W // 2, H // 2 + 40)
        self.ui.bar(screen, bar, self.progress, theme.BRASS)
        self.ui.text(screen, "CARREGANDO", theme.XS, theme.MUTED, (W // 2, bar.bottom + 18))


class _MenuScene(Scene):
    """Tela com o fundo animado da arena."""

    menu_keys = False       # True: a tela só lê o teclado, então o controle USB vira setas/Enter/Esc

    def __init__(self, game):
        super().__init__(game)
        if game.backdrop is None:
            game.backdrop = Backdrop(game.assets)
        self.backdrop = game.backdrop

    def draw_background(self, screen):
        self.backdrop.draw(screen, self.game.clock_ticks)


class TitleScene(_MenuScene):
    menu_keys = True

    def __init__(self, game):
        super().__init__(game)
        game.session = None
        self.cast = roster()
        self.menu = MenuList(
            [("JOGAR", "play"), ("CONTROLES", "controls"), ("OPÇÕES", "options"),
             ("SOBRE O PROJETO", "about"), ("CRÉDITOS", "credits"), ("ATUALIZAR", "update"), ("SAIR", "quit")],
            topleft=(config.SCREEN_W // 2 - 130, 184), width=260, row_h=32)

    def handle(self, event):
        if self.is_back(event):
            if self.menu.value == "quit":
                self.game.quit()
            self.menu.index = len(self.menu.options) - 1
            self.sfx("cancel", 0.3)
            return
        choice = self.menu.handle(event, self.sfx)
        if choice is None:
            return
        self.sfx("confirm")
        if choice == "play":
            self.game.change(ModeScene(self.game))
        elif choice == "controls":
            self.game.change(ControlsScene(self.game))
        elif choice == "options":
            self.game.change(OptionsScene(self.game))
        elif choice == "about":
            self.game.change(AboutScene(self.game))
        elif choice == "credits":
            self.game.change(CreditsScene(self.game))
        elif choice == "update":
            from .update import UpdateScene
            self.game.change(UpdateScene(self.game))
        elif choice == "quit":
            self.game.quit()

    def draw(self, screen):
        W, H = config.SCREEN_W, config.SCREEN_H
        self.draw_background(screen)
        self.ui.logo(screen, (W // 2, 112))
        self.ui.text(screen, "CAMPANHA  ·  DUELO DE ARENA  ·  FUTEBOL", theme.XS, theme.MUTED, (W // 2, 158))
        self.menu.draw(screen, self.ui, self.ticks)

        # elenco no chão
        ground = H - 52
        cast = self.cast
        n = len(cast)
        for i, stats in enumerate(cast):
            x = 96 + i * (W - 192) // (n - 1)
            bob = 1 if (self.ticks // 24 + i) % 2 else 0
            img = self.assets.sprites[stats.key].portrait
            pygame.draw.ellipse(screen, (6, 4, 10), (x - 18, ground - 5, 36, 10))
            screen.blit(img, img.get_rect(midbottom=(x, ground + bob)))

        if server.start_error:
            # outro Soul Strike aberto (ou outro programa) já está usando a porta do controle
            self.ui.text(screen, "CELULAR INDISPONÍVEL: " + server.start_error, theme.XS, theme.BLOOD,
                         (W - 16, H - 28), anchor="bottomright")
            self.ui.text(screen, "FECHE A OUTRA JANELA DO JOGO E ABRA DE NOVO", theme.XS, theme.MUTED,
                         (W - 16, H - 14), anchor="bottomright")
        else:
            self.ui.text(screen, "CELULAR COMO CONTROLE:", theme.XS, theme.FAINT, (W - 16, H - 28), anchor="bottomright")
            self.ui.text(screen, self.game.base_url, theme.XS, theme.MUTED, (W - 16, H - 14), anchor="bottomright")
        self.ui.text(screen, "F11 TELA CHEIA", theme.XS, theme.FAINT, (16, H - 14), anchor="bottomleft")


MODE_TEXT = {
    "cpu": ("Você contra o computador. Escolha a dificuldade na seleção de personagem.",
            "1 JOGADOR"),
    "duel": ("Dois jogadores no mesmo teclado, ou cada um com o celular como controle.",
             "2 JOGADORES"),
    "duel2": ("Times de dois, sem fogo amigo: o round acaba quando o time inteiro cai, e dá para levantar "
              "o companheiro caído. Quem faltar vira CPU.",
              "1 A 4 JOGADORES"),
    "soccer1": ("Futebol com habilidades: passe, corte, condução e super chute. Primeiro a 3 gols vence.",
                "2 JOGADORES"),
    "soccer2": ("Times de dois. O jogador 2 entra pelo teclado (;) ou celular; o 3 e o 4, pelo celular. "
                "Quem faltar vira CPU para fechar o time.",
                "1 A 4 JOGADORES"),
    "basket2": ("Basquete 2 x 2 no caos: a bola quica sozinha, cesta de 2 ou de 3 e dois tempos de 2 minutos. "
                "No empate, a próxima cesta vence. Quem faltar vira CPU.",
                "1 A 4 JOGADORES"),
    "treino": ("Para quem está começando: um boneco de treino parado e uma lição por vez na tela "
               "(andar, atacar, trocar de arma, esquivar, habilidade e itens) e um arsenal com todas as armas, "
               "até as mais raras. Ninguém perde.",
               "1 JOGADOR"),
    "treino_futebol": ("Treino com bola contra um boneco parado: corte, chute, chute alto, marcar e gol, "
                       "uma lição por vez.",
                       "1 JOGADOR"),
    "treino_basquete": ("Treino de basquete com bonecos parados: a barrinha do arremesso, a finta, o toco e a "
                        "cesta, uma lição por vez.",
                        "1 JOGADOR"),
    "campaign": ("Juntos contra as sombras: em cada fase, um acampamento e duas masmorras, com um baú "
                 "escondido de armas raras no caminho. No fim, o chefão Aryel Corrompido. Quem cair pode "
                 "ser levantado por um companheiro.",
                 "1 A 4 JOGADORES"),
}


class ModeScene(_MenuScene):
    menu_keys = True

    def __init__(self, game):
        super().__init__(game)
        from .. import progress
        from ..campaign import CampaignRun
        saved = progress.saved_campaign()
        self.saved_run = CampaignRun.from_save(saved) if saved else None
        options = [(MODES[k]["title"], k) for k in ("campaign", "cpu", "duel", "duel2", "soccer1", "soccer2", "basket2", "treino",
                                                     "treino_futebol", "treino_basquete")]
        if self.saved_run is not None:
            options.insert(0, ("CONTINUAR CAMPANHA", "continue"))
        options.append(("VOLTAR", "back"))
        self.menu = MenuList(options, topleft=(56, 96), width=320, row_h=30 if len(options) > 11 else 36)

    def handle(self, event):
        if self.is_back(event):
            self.sfx("cancel", 0.4)
            self.game.change(TitleScene(self.game))
            return
        choice = self.menu.handle(event, self.sfx)
        if choice is None:
            return
        if choice == "back":
            self.sfx("cancel", 0.4)
            self.game.change(TitleScene(self.game))
            return
        self.sfx("confirm")
        if choice == "continue":
            from .campaign import start_phase
            run = self.saved_run
            self.game.session = run.session
            self.game.change(start_phase(self.game, run, story=False))
            return
        count = MODES[choice]["slots"]
        teams = MODES[choice].get("teams", False)
        training = choice.startswith("treino")
        slots = [SlotSetup(s, cpu=(choice == "cpu" and s == 2) or (training and s > 1) or (teams and s > 1))
                 for s in range(1, count + 1)]
        if choice == "campaign":
            slots = slots[:1]           # P2 a P4 entram na tela de conexão
        previous = self.game.session
        self.game.session = Session(choice, slots)
        if previous is not None and teams:
            self.game.session.layout = previous.layout      # mantém a divisão de times escolhida
        from .select import CharSelectScene, LobbyScene
        if choice == "cpu" or training:
            self.game.change(CharSelectScene(self.game))
        else:
            self.game.change(LobbyScene(self.game))

    def draw(self, screen):
        W, H = config.SCREEN_W, config.SCREEN_H
        self.draw_background(screen)
        self.title(screen, "MODO DE JOGO", y=64)
        self.menu.draw(screen, self.ui, self.ticks)

        key = self.menu.value
        panel = pygame.Rect(420, 112, 484, 330)
        self.ui.panel(screen, panel)
        if key == "back":
            self.ui.text(screen, "VOLTAR AO MENU", theme.S, theme.MUTED, panel.center)
        else:
            desc, players = MODE_TEXT[key] if key != "continue" else self._continue_text()
            self._illustration(screen, key, pygame.Rect(panel.x + 2, panel.y + 2, panel.w - 4, 170))
            title = MODES[key]["title"] if key != "continue" else "CONTINUAR CAMPANHA"
            self.ui.text(screen, title, theme.S, theme.BRASS, (panel.x + 24, panel.y + 196), anchor="topleft")
            self.ui.text(screen, players, theme.XS, theme.MUTED, (panel.right - 24, panel.y + 200), anchor="topright")
            self.ui.paragraph(screen, desc, theme.XS, theme.BONE, (panel.x + 24, panel.y + 232), panel.w - 48, spacing=16)
        self.footer(screen, [("↑↓", "ESCOLHER"), ("ENTER", "CONFIRMAR"), ("ESC", "VOLTAR")])

    def _continue_text(self):
        from ..ai import DIFFICULTIES
        from ..campaign import PHASES
        run = self.saved_run
        n = run.players
        desc = (f"Volta para o acampamento da fase {run.phase_index + 1} de {len(PHASES)}: "
                f"{run.phase.name}, dificuldade {DIFFICULTIES[run.session.difficulty]['label']}. As melhorias, as armas "
                "raras e a vida continuam como estavam. Quem jogava pelo celular ou controle precisa estar "
                "conectado antes.")
        return desc, f"{n} JOGADOR" + ("ES" if n > 1 else "")

    def _illustration(self, screen, key, area):
        if key in ("campaign", "continue"):
            self._campaign_illustration(screen, area)
            return
        battle = key in ("cpu", "duel", "duel2", "treino")
        floor = theme.INK if battle else (34, 92, 46)
        screen.fill(floor, area)
        if not battle:
            for i, x in enumerate(range(area.x, area.right, 40)):
                if i % 2:
                    screen.fill((40, 104, 52), (x, area.y, 40, area.h))
            screen.fill((210, 220, 200), (area.centerx - 1, area.y, 2, area.h))
        else:
            for x in range(area.x, area.right, 32):
                screen.fill(theme.INK_2, (x, area.y, 1, area.h))
            for y in range(area.y, area.bottom, 32):
                screen.fill(theme.INK_2, (area.x, y, area.w, 1))
        sprites = self.assets.sprites
        ground = area.bottom - 22
        cast = {
            "cpu": [("guerreiro", "direita", -90), ("tanque", "esquerda", 90)],
            "treino": [("aryel", "direita", -70), ("tanque", "esquerda", 70)],
            "treino_futebol": [("velocista", "direita", -70), ("tanque", "esquerda", 70)],
            "treino_basquete": [("ninja", "direita", -70), ("tanque", "esquerda", 70)],
            "duel": [("aryel", "direita", -90), ("ninja", "esquerda", 90)],
            "duel2": [("pirata", "direita", -150), ("geada", "direita", -70),
                      ("atirador", "esquerda", 70), ("tanque", "esquerda", 150)],
            "soccer1": [("velocista", "direita", -110), ("atirador", "esquerda", 110)],
            "soccer2": [("tita", "direita", -150), ("fantasma", "direita", -70),
                        ("guerreiro", "esquerda", 70), ("aryel", "esquerda", 150)],
            "basket2": [("ninja", "direita", -150), ("velocista", "direita", -70),
                        ("pirata", "esquerda", 70), ("tita", "esquerda", 150)],
        }[key]
        step = self.ticks // 4
        for name, direction, dx in cast:
            img = sprites[name].frame(direction, step)
            img = pygame.transform.scale(img, (img.get_width() * 2, img.get_height() * 2))
            x = area.centerx + dx
            pygame.draw.ellipse(screen, (0, 0, 0), (x - 30, ground - 8, 60, 14))
            if MODES[key].get("teams"):
                pygame.draw.ellipse(screen, theme.TEAM_COLORS[0 if dx < 0 else 1], (x - 33, ground - 10, 66, 18), 2)
            screen.blit(img, img.get_rect(midbottom=(x, ground + 4)))
        if key.startswith("soccer"):
            bx = area.centerx + int(math.sin(self.ticks * 0.05) * 20)
            pygame.draw.circle(screen, (20, 18, 24), (bx, ground - 6), 9)
            pygame.draw.circle(screen, (238, 236, 228), (bx, ground - 6), 8)
        elif key.startswith("basket"):
            # bola de basquete quicando no meio
            by = ground - 8 - int(abs(math.sin(self.ticks * 0.08)) * 46)
            pygame.draw.circle(screen, (60, 24, 8), (area.centerx, by), 10)
            pygame.draw.circle(screen, (226, 112, 36), (area.centerx, by), 9)
            screen.fill((60, 24, 8), (area.centerx - 9, by, 18, 1))
            screen.fill((60, 24, 8), (area.centerx, by - 9, 1, 18))
        screen.fill(theme.LINE, (area.x, area.bottom, area.w, 2))


    def _campaign_illustration(self, screen, area):
        screen.fill((24, 34, 22), area)
        for x in range(area.x, area.right, 32):
            screen.fill((30, 44, 28), (x, area.y, 1, area.h))
        for y in range(area.y, area.bottom, 32):
            screen.fill((30, 44, 28), (area.x, y, area.w, 1))
        sprites = self.assets.sprites
        ground = area.bottom - 22
        step = self.ticks // 4
        cast = [("guerreiro", "direita", -170, False), ("geada", "direita", -100, False),
                ("diabrete", "esquerda", 40, False), ("esqueleto", "esquerda", 110, False),
                ("aryel", "esquerda", 180, True)]
        for name, direction, dx, shadow in cast:
            sset = self.assets.shadow_sprites(name) if shadow else sprites[name]
            img = sset.frame(direction, step)
            factor = 3 if shadow else 2
            img = pygame.transform.scale(img, (img.get_width() * factor, img.get_height() * factor))
            x = area.centerx + dx
            pygame.draw.ellipse(screen, (0, 0, 0), (x - 30, ground - 8, 60, 14))
            rect = img.get_rect(midbottom=(x, ground + 4))
            if shadow:
                from ..enemies import SHADOW_RIM
                from ..fighter import draw_aura
                draw_aura(screen, img, rect, SHADOW_RIM, self.ticks, 3)
            screen.blit(img, rect)
        screen.fill(theme.LINE, (area.x, area.bottom, area.w, 2))


class _InfoScene(_MenuScene):
    heading = ""
    menu_keys = True

    def handle(self, event):
        if self.is_back(event) or (event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN) \
                or (event.type == pygame.MOUSEBUTTONDOWN and event.button == 3):
            self.sfx("cancel", 0.4)
            self.game.change(TitleScene(self.game))

    def draw(self, screen):
        self.draw_background(screen)
        self.title(screen, self.heading, y=52)
        self.draw_body(screen)

    def draw_body(self, screen):
        pass


class ControlsScene(_InfoScene):
    heading = "CONTROLES"

    @staticmethod
    def rows():
        """(ação, tecla do jogador 1, tecla do jogador 2), já com as teclas trocadas."""
        rows = [("MOVER", move_label(1), move_label(2))]
        for row_id, label, _, _ in REBINDABLE[4:]:
            rows.append((label, key_label(1, row_id), key_label(2, row_id)))
        return rows
    TIPS = [
        "DUELO: A MUNIÇÃO RECARREGA SOZINHA. ARCO: SEGURE ATACAR PARA TENSIONAR.",
        "FUTEBOL: TOQUE EM CHUTAR/PASSE = RASTEIRO. SEGURE E SOLTE = PELO ALTO.",
        "PASSE VAI NA DIREÇÃO QUE VOCÊ APONTA. NA PONTA, NO 2X2, VIRA CRUZAMENTO.",
        "NO SEU CAMPO, CHUTAR COM A BOLA SOLTA = CHUTÃO PARA LONGE DO GOL.",
        "CORTE COM UM CHUTE VINDO = CARRINHO DE BLOQUEIO.",
        "BASQUETE: SEGURE CHUTAR PARA PULAR E SOLTE NA FAIXA VERDE. CORTE = FINTA OU ROUBO.",
    ]

    def __init__(self, game):
        super().__init__(game)
        self.toggle_rect = pygame.Rect(0, 0, 0, 0)

    def _toggle_double_tap(self):
        PlayerInput.double_tap_enabled = settings.change("duplo_toque", not PlayerInput.double_tap_enabled)
        self.sfx("click", 0.4)

    def handle(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_t:
            self._toggle_double_tap()
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_k:
            self.sfx("confirm", 0.4)
            self.game.change(RebindScene(self.game))
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.toggle_rect.collidepoint(event.pos):
            self._toggle_double_tap()
            return
        super().handle(event)

    def draw_body(self, screen):
        W = config.SCREEN_W
        panel = pygame.Rect(48, 80, W - 96, 344)
        self.ui.panel(screen, panel)
        cols = (panel.x + 20, panel.x + 470, panel.x + 640)
        y = panel.y + 18
        self.ui.text(screen, "AÇÃO", theme.XS, theme.MUTED, (cols[0], y), anchor="midleft")
        self.ui.text(screen, "JOGADOR 1", theme.XS, theme.SLOT_COLORS[1], (cols[1], y), anchor="midleft")
        self.ui.text(screen, "JOGADOR 2", theme.XS, theme.SLOT_COLORS[2], (cols[2], y), anchor="midleft")
        y += 12
        screen.fill(theme.LINE, (panel.x + 16, y, panel.w - 32, 2))
        y += 18
        for label, k1, k2 in self.rows():
            self.ui.text(screen, label, theme.XS, theme.BONE, (cols[0], y), anchor="midleft", shadow=False)
            self.ui.keycap(screen, k1, (cols[1], y))
            self.ui.keycap(screen, k2, (cols[2], y))
            y += 21
        y += 2
        for tip in self.TIPS:
            self.ui.text(screen, tip, theme.XS, theme.MUTED, (cols[0], y), anchor="midleft", shadow=False)
            y += 15
        state = "LIGADO" if PlayerInput.double_tap_enabled else "DESLIGADO"
        self.toggle_rect = self.ui.keycap(screen, "T", (cols[0], y + 6))
        self.ui.text(screen, f"DUPLO TOQUE NAS SETAS = ESQUIVA/CORTE: {state}", theme.XS,
                     theme.BRASS if PlayerInput.double_tap_enabled else theme.MUTED,
                     (self.toggle_rect.right + 8, y + 6), anchor="midleft", shadow=False)
        self.toggle_rect = self.toggle_rect.union(pygame.Rect(self.toggle_rect.right, y - 2, 420, 16))

        phone = pygame.Rect(48, 432, W - 96, 64)
        self.ui.panel(screen, phone, fill=theme.INK_2)
        self.ui.text(screen, "CELULAR", theme.XS, theme.BRASS, (phone.x + 20, phone.y + 18), anchor="midleft")
        self.ui.paragraph(screen, "Na mesma rede Wi-Fi, escaneie o QR code da tela de conexão ou abra "
                          f"{self.game.base_url} e escolha o número do jogador. No futebol, empurre "
                          "o analógico até a borda para correr.",
                          theme.XS, theme.BONE, (phone.x + 20, phone.y + 32), phone.w - 40, spacing=13)
        self.footer(screen, [("K", "TROCAR TECLAS"), ("T", "DUPLO TOQUE"), ("ESC", "VOLTAR")])


class OptionsScene(_InfoScene):
    """Volume, tela cheia, vsync, tremor de tela e duplo toque. Tudo fica salvo (settings.py)."""

    heading = "OPÇÕES"
    # (chave em settings, rótulo, observação)
    ROWS = [
        ("volume_geral", "VOLUME GERAL", ""),
        ("volume_musica", "MÚSICA", ""),
        ("volume_efeitos", "EFEITOS", ""),
        ("tela_cheia", "TELA CHEIA", "F11 TAMBÉM ALTERNA"),
        ("vsync", "SINCRONIA VERTICAL", "VALE AO ABRIR O JOGO DE NOVO"),
        ("tremor", "TREMOR DE TELA", "NOS IMPACTOS E EXPLOSÕES"),
        ("duplo_toque", "DUPLO TOQUE = ESQUIVA", "DUAS VEZES NA MESMA SETA"),
        ("controle_comeca_no_p2", "1º CONTROLE USB É O P2", "DESLIGADO: É O P1"),
        ("novidades", "NOVIDADES", "O QUE MUDOU EM CADA VERSÃO"),
    ]
    ROW_H = 36

    def __init__(self, game):
        super().__init__(game)
        self.index = 0
        self.rects = []

    @property
    def key(self):
        return self.ROWS[self.index][0]

    def change(self, key, step):
        """step = -1 / +1 nos volumes; nos liga/desliga qualquer passo alterna."""
        if key == "novidades":
            from .. import novidades
            self.sfx("confirm", 0.4)
            self.game.change(NewsScene(self.game, novidades.history(), back=OptionsScene))
            return
        value = settings.get(key)
        if key in settings.VOLUME_KEYS:
            new = settings.change(key, round(value + step * settings.VOLUME_STEP, 2))
            if new == value:
                return
            if key == "volume_efeitos" or key == "volume_geral":
                self.sfx("hit", 0.5)            # amostra do volume novo
            self.assets.apply_music_volume()
            return
        if key == "tela_cheia":
            self.game.toggle_fullscreen()
        else:
            settings.change(key, not value)
            if key == "duplo_toque":
                PlayerInput.double_tap_enabled = settings.get(key)
        self.sfx("click", 0.4)

    def handle(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.index = (self.index - 1) % len(self.ROWS)
                self.sfx("select", 0.25)
                return
            if event.key in (pygame.K_DOWN, pygame.K_s):
                self.index = (self.index + 1) % len(self.ROWS)
                self.sfx("select", 0.25)
                return
            if event.key in (pygame.K_LEFT, pygame.K_a):
                self.change(self.key, -1)
                return
            if event.key in (pygame.K_RIGHT, pygame.K_d, pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                self.change(self.key, 1)
                return
        elif event.type == pygame.MOUSEMOTION:
            for i, r in enumerate(self.rects):
                if r.collidepoint(event.pos):
                    self.index = i
            return
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button in (1, 4, 5):
            for i, r in enumerate(self.rects):
                if r.collidepoint(event.pos):
                    self.index = i
                    # clique na metade esquerda abaixa o volume, na direita aumenta (rodinha também)
                    if event.button == 1:
                        step = -1 if event.pos[0] < r.centerx else 1
                    else:
                        step = 1 if event.button == 4 else -1
                    self.change(self.key, step)
                    return
            if event.button != 1:
                return
        if self.is_back(event) or (event.type == pygame.MOUSEBUTTONDOWN and event.button == 3):
            self.sfx("cancel", 0.4)
            self.game.change(TitleScene(self.game))

    def draw_body(self, screen):
        W = config.SCREEN_W
        panel = pygame.Rect(120, 92, W - 240, 24 + self.ROW_H * len(self.ROWS))
        self.ui.panel(screen, panel)
        self.rects = []
        y = panel.y + 12
        for i, (key, label, note) in enumerate(self.ROWS):
            row = pygame.Rect(panel.x + 10, y, panel.w - 20, self.ROW_H - 4)
            self.rects.append(row)
            chosen = i == self.index
            if chosen:
                screen.fill(theme.INK, row)
                screen.fill(theme.BRASS, (row.x, row.y, 3, row.h))
            color = theme.BONE if chosen else theme.MUTED
            self.ui.text(screen, label, theme.XS, color, (row.x + 16, row.y + 12), anchor="midleft", shadow=False)
            if note:
                self.ui.text(screen, note, theme.XS, theme.FAINT, (row.x + 16, row.y + 26), anchor="midleft",
                             shadow=False)
            right = row.right - 16
            if key == "novidades":
                self.ui.text(screen, "ABRIR >", theme.XS, theme.BRASS if chosen else theme.MUTED,
                             (right, row.centery), anchor="midright", shadow=False)
                y += self.ROW_H
                continue
            value = settings.get(key)
            if key in settings.VOLUME_KEYS:
                bar = pygame.Rect(0, 0, 200, 10)
                bar.midright = (right - 64, row.centery)
                self.ui.bar(screen, bar, value, theme.BRASS if chosen else theme.MUTED, ticks=10)
                self.ui.text(screen, f"{round(value * 100)}%", theme.XS, color, (right, row.centery),
                             anchor="midright", shadow=False)
            else:
                word = "LIGADO" if value else "DESLIGADO"
                self.ui.text(screen, word, theme.XS, theme.BRASS if value else theme.MUTED, (right, row.centery),
                             anchor="midright", shadow=False)
            y += self.ROW_H
        self.footer(screen, [("↑↓", "ESCOLHER"), ("←→", "MUDAR"), ("ESC", "VOLTAR")])


class RebindScene(_InfoScene):
    """Trocar as teclas do jogador 1 e do jogador 2 (fica salvo nas opções)."""

    heading = "TROCAR TECLAS"
    ROW_H = 24

    def __init__(self, game):
        super().__init__(game)
        self.row = 0                    # linha de REBINDABLE; len(REBINDABLE) = RESTAURAR PADRÃO
        self.col = 0                    # 0 = jogador 1, 1 = jogador 2
        self.waiting = False            # esperando a tecla nova
        self.message = ""
        self.cells = {}

    @property
    def slot(self):
        return self.col + 1

    def _start(self):
        if self.row == len(REBINDABLE):
            reset_keys(self.slot)
            self._apply()
            self.message = f"TECLAS DO JOGADOR {self.slot} VOLTARAM AO PADRÃO"
            self.sfx("confirm", 0.4)
            return
        self.waiting = True
        self.message = ""
        self.sfx("click", 0.4)

    def _apply(self):
        for inp in self.game.inputs.values():
            inp.set_layout(inp.layout)          # as partidas já usam as teclas novas

    def _bind(self, code):
        self.waiting = False
        row_id = REBINDABLE[self.row][0]
        ok, msg = bind_key(self.slot, row_id, code)
        self.message = msg
        if ok:
            self._apply()
            self.sfx("confirm", 0.4)
        else:
            self.sfx("cancel", 0.4)

    def handle(self, event):
        if self.waiting:
            if event.type == pygame.KEYDOWN and not getattr(event, "from_pad", False):
                if event.key == pygame.K_ESCAPE:
                    self.waiting = False
                    self.sfx("cancel", 0.3)
                else:
                    self._bind(event.key)
            return
        n = len(REBINDABLE) + 1
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.row = (self.row - 1) % n
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.row = (self.row + 1) % n
            elif event.key in (pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d):
                self.col = 1 - self.col
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                self._start()
            elif self.is_back(event):
                self.sfx("cancel", 0.4)
                self.game.change(ControlsScene(self.game))
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for (row, col), rect in self.cells.items():
                if rect.collidepoint(event.pos):
                    self.row, self.col = row, col
                    self._start()
                    return
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            self.sfx("cancel", 0.4)
            self.game.change(ControlsScene(self.game))

    def draw_body(self, screen):
        W = config.SCREEN_W
        panel = pygame.Rect(64, 78, W - 128, 46 + self.ROW_H * (len(REBINDABLE) + 1))
        self.ui.panel(screen, panel)
        cols = (panel.x + 20, panel.x + 470, panel.x + 640)
        y = panel.y + 16
        self.ui.text(screen, "AÇÃO", theme.XS, theme.MUTED, (cols[0], y), anchor="midleft")
        for i in (0, 1):
            self.ui.text(screen, f"JOGADOR {i + 1}", theme.XS, theme.SLOT_COLORS[i + 1], (cols[1 + i], y),
                         anchor="midleft")
        y += 22
        self.cells = {}
        for r, (row_id, label, _, _) in enumerate(REBINDABLE + (("reset", "RESTAURAR PADRÃO", "", ()),)):
            chosen_row = r == self.row
            if chosen_row:
                screen.fill(theme.INK, (panel.x + 10, y - 10, panel.w - 20, self.ROW_H - 2))
            color = theme.BONE if chosen_row else theme.MUTED
            self.ui.text(screen, label, theme.XS, color, (cols[0], y), anchor="midleft", shadow=False)
            for c in (0, 1):
                cell = pygame.Rect(cols[1 + c] - 6, y - 10, 150, self.ROW_H - 2)
                self.cells[(r, c)] = cell
                here = chosen_row and c == self.col
                if row_id == "reset":
                    text, kc = "RESTAURAR", theme.BRASS if here else theme.FAINT
                    self.ui.text(screen, text, theme.XS, kc, (cols[1 + c], y), anchor="midleft", shadow=False)
                elif here and self.waiting:
                    if (self.ticks // 15) % 2:
                        self.ui.text(screen, "APERTE A TECLA", theme.XS, theme.BRASS, (cols[1 + c], y),
                                     anchor="midleft", shadow=False)
                else:
                    changed = current_key(c + 1, row_id) != default_key(c + 1, row_id)
                    cap = self.ui.keycap(screen, key_label(c + 1, row_id), (cols[1 + c], y),
                                         color=theme.BRASS if changed else theme.BONE)
                    if here:
                        pygame.draw.rect(screen, theme.BRASS, cap.inflate(6, 6), 1)
            y += self.ROW_H
        if self.message:
            self.ui.text(screen, self.message, theme.XS, theme.BLOOD, (W // 2, panel.bottom + 16))
        if self.waiting:
            self.footer(screen, [("ESC", "CANCELAR")])
        else:
            self.footer(screen, [("↑↓", "ESCOLHER"), ("←→", "JOGADOR"), ("ENTER", "TROCAR"), ("ESC", "VOLTAR")])


ABOUT = [
    ("OS 4 PILARES DA ORIENTAÇÃO A OBJETOS NO SOUL STRIKE", None),
    ("ENCAPSULAMENTO", "Fighter guarda vida, posição, tempos de recarga e a munição. Ninguém altera a vida "
     "diretamente: quem causa dano chama take_damage(), que confere esquiva e invulnerabilidade antes "
     "de descontar. Do mesmo jeito, só attack() gasta tiro e só start_reload() e refill_ammo() enchem o pente. RemoteHub esconde a trava entre a thread do servidor web e o jogo; o resto do código "
     "só usa apply_input(), poll() e status()."),
    ("ABSTRAÇÃO", "Entity e Ability são classes abstratas (ABC): dizem o que toda entidade e toda "
     "habilidade faz (update, draw, activate) sem dizer como. Arena.resolve() esconde a colisão de "
     "círculo com retângulo e Camera esconde o zoom e a conversão do mundo para a tela."),
    ("HERANÇA", "Fighter, Bullet, Explosion, Barrier, FrostNova, Wall, Pickup, Ball, Portal e Shockwave herdam "
     "de Entity e ganham posição, distance_to() e direction_to(). Hook (o gancho do Pirata) herda de Bullet: "
     "voa e colide como um tiro e só muda o que acontece ao acertar (on_hit puxa o alvo). Os projéteis das "
     "armas (Arrow, Grenade, ChainBall...) herdam de Projectile, que herda de Bullet. ShadowBomb herda "
     "de GroundMark: é o mesmo aviso no chão, só que explode no fim. BattleMatch, SoccerMatch e "
     "CampaignMatch herdam de Match, que já cuida de câmera, tiros, partículas e desenho. Na campanha, "
     "CampaignMatch (a masmorra) e LobbyMatch (o acampamento) herdam de CoopMatch, que junta o que as duas "
     "têm em comum (levantar quem caiu, a mira, os itens, o escurecer entre as etapas). TeamBattleMatch "
     "(o duelo 2 x 2) herda de BattleMatch e só troca o que é um \"lado\": em vez de um lutador, um time "
     "inteiro, que precisa cair todo para perder o round. Os inimigos da "
     "campanha são Fighters do time das sombras. Todas as telas herdam de Scene."),
    ("POLIMORFISMO", "Cada arma de tiro dispara a sua subclasse de Projectile: Arrow (a flecha que finca na "
     "parede), Tracer, Spear, ShurikenStar (ricocheteia), ThrowingStar, Grenade (vai por cima das paredes), "
     "Orb (persegue e atravessa paredes), ChainBall (vai e volta), LeadBall e IceShard (deixa lento). A partida "
     "só chama update(), on_hit() e on_wall() e cada uma responde do seu jeito. "
     "Cada personagem tem uma subclasse de Ability: Investida, Rajada, Muralha, "
     "ShurikenTripla, Turbo, Explosao, Teletransporte, Invulneravel, Gancho, Nevasca e ChuvaSombria. O "
     "lutador só chama ability.use() e cada classe responde do seu jeito. No futebol, o botão SUPER chama "
     "power.use() de uma subclasse de SoccerPower (Zagueirao, ChuteCerteiro, MuralhaDoGol, Sombra, Arrancada, "
     "GrauDeMoto, Bomba, BombaSombria, BolaFantasma, Gigante, GanchoNaBola, Congelar, Antecipacao...). Na campanha, cada inimigo tem um "
     "cérebro (DiabreteAI, EsqueletoAI, GolemAI, BossAI) e cada melhoria é uma subclasse de Upgrade com "
     "apply(). Nos mapas, cada estilo de parede (Hedge, DungeonStone, IceBlock) e cada ambiente (Fireflies, "
     "Torches, Snow) responde ao mesmo paint() ou draw(). E a cena de jogo chama match.step() sem saber se "
     "é duelo, duelo 2 x 2, futebol ou campanha."),
]


class AboutScene(_InfoScene):
    heading = "SOBRE O PROJETO"

    def __init__(self, game):
        super().__init__(game)
        self.scroll = 0
        self.content_h = 0

    def handle(self, event):
        if event.type == pygame.MOUSEWHEEL:
            self.scroll -= event.y * 24
        elif event.type == pygame.KEYDOWN and event.key in (pygame.K_UP, pygame.K_w):
            self.scroll -= 24
        elif event.type == pygame.KEYDOWN and event.key in (pygame.K_DOWN, pygame.K_s):
            self.scroll += 24
        else:
            super().handle(event)
        self.scroll = max(0, min(self.scroll, max(0, self.content_h - 360)))

    def draw_body(self, screen):
        W = config.SCREEN_W
        panel = pygame.Rect(56, 92, W - 112, 380)
        self.ui.panel(screen, panel)
        clip = panel.inflate(-8, -12)
        screen.set_clip(clip)
        y = panel.y + 20 - self.scroll
        start = y
        for heading, body in ABOUT:
            if body is None:
                self.ui.text(screen, heading, theme.XS, theme.MUTED, (panel.x + 24, y), anchor="topleft")
                y += 28
                continue
            self.ui.text(screen, heading, theme.S, theme.BRASS, (panel.x + 24, y), anchor="topleft")
            y = self.ui.paragraph(screen, body, theme.XS, theme.BONE, (panel.x + 24, y + 26), panel.w - 48, spacing=15)
            y += 18
        screen.set_clip(None)
        self.content_h = y - start
        if self.content_h > 360:
            track = pygame.Rect(panel.right - 10, panel.y + 10, 4, panel.h - 20)
            screen.fill(theme.INK, track)
            frac = self.scroll / max(1, self.content_h - 360)
            thumb_h = max(20, track.h * 360 // self.content_h)
            screen.fill(theme.LINE_HI, (track.x, track.y + (track.h - thumb_h) * frac, 4, thumb_h))
        self.footer(screen, [("↑↓", "ROLAR"), ("ESC", "VOLTAR")])


CREDITS = [
    ("Cauã Pedrozo Brito", "https://github.com/cauapbritto",
     "https://www.linkedin.com/in/cau%C3%A3-pedrozo-brito-8a685b358/"),
]


VERSE = ("Porque Deus amou o mundo de tal maneira que deu o seu Filho unigênito, para que todo "
         "aquele que nele crê não pereça, mas tenha a vida eterna.")
VERSE_REF = "JOÃO 3:16"
DEDICATION = ("TODA A HONRA", "E GLÓRIA A JESUS")


class CreditsScene(_InfoScene):
    heading = "CRÉDITOS"
    PANEL = pygame.Rect(56, 92, config.SCREEN_W - 112, 290)

    @classmethod
    def _top(cls):
        """Altura do "DESENVOLVIDO POR": nomes e links ficam no meio do painel, na vertical."""
        return cls.PANEL.centery - 42 - (len(CREDITS) - 1) * 55

    def __init__(self, game):
        super().__init__(game)
        options = []
        for name, gh, li in CREDITS:
            options.append(("GITHUB", gh))
            options.append(("LINKEDIN", li))
        options.append(("VOLTAR", "back"))
        self.menu = MenuList(options, (0, 0), 200)
        # posiciona cada link embaixo do nome do autor; VOLTAR fica no pé do painel
        top = self._top()
        for i in range(len(CREDITS)):
            y = top + i * 110
            self.menu.rects[i * 2] = pygame.Rect(120, y + 56, 200, 28)
            self.menu.rects[i * 2 + 1] = pygame.Rect(340, y + 56, 220, 28)
        self.menu.rects[-1] = pygame.Rect(120, self.PANEL.bottom - 50, 200, 28)

    def handle(self, event):
        if self.is_back(event):
            super().handle(event)
            return
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_LEFT, pygame.K_a):
            self.menu.move(-1)
            return
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_RIGHT, pygame.K_d):
            self.menu.move(1)
            return
        choice = self.menu.handle(event, self.sfx)
        if choice == "back":
            self.sfx("cancel", 0.4)
            self.game.change(TitleScene(self.game))
        elif choice:
            self.sfx("click")
            webbrowser.open(choice)

    def _draw_verse(self, screen, box):
        """Dedicatória a Jesus e João 3:16 ao lado dos nomes."""
        screen.fill(theme.LINE, (box.x - 24, box.y, 2, box.h))
        cx = box.centerx
        lines = self.ui.wrap(VERSE, theme.XS, box.w)
        total = len(DEDICATION) * 24 + 12 + len(lines) * 17 + 20
        y = box.centery - total // 2 + 12
        for line in DEDICATION:
            self.ui.text(screen, line, theme.S, theme.BRASS, (cx, y))
            y += 24
        y += 12
        for line in lines:
            self.ui.text(screen, line, theme.XS, theme.BONE, (cx, y), shadow=False)
            y += 17
        self.ui.text(screen, VERSE_REF, theme.XS, theme.MUTED, (cx, y + 6), shadow=False)

    def draw_body(self, screen):
        panel = self.PANEL
        self.ui.panel(screen, panel)
        top = self._top()
        self.ui.text(screen, "DESENVOLVIDO POR", theme.XS, theme.MUTED, (120, top), anchor="midleft")
        for i, (name, _, _) in enumerate(CREDITS):
            y = top + i * 110
            self.ui.text(screen, name.upper(), theme.S, theme.BONE, (120, y + 36), anchor="midleft")
        self._draw_verse(screen, pygame.Rect(596, panel.y + 24, 276, panel.h - 48))
        self.menu.draw(screen, self.ui, self.ticks)
        self.footer(screen, [("←→", "ESCOLHER"), ("ENTER", "ABRIR LINK"), ("ESC", "VOLTAR")])


SOUL = (200, 170, 255)


def _phone(screen, rect, t):
    """Moldura de celular deitado, com a tela escura dentro. Devolve o retângulo da tela."""
    pygame.draw.rect(screen, (40, 36, 50), rect, border_radius=14)
    pygame.draw.rect(screen, theme.LINE_HI, rect, 2, border_radius=14)
    inner = rect.inflate(-24, -14)
    screen.fill(theme.INK, inner)
    return inner


def _scene_almas(screen, ui, rect, t):
    """Um inimigo vira almas: a maior parte voa para quem deu o golpe, um pouco para o outro."""
    cycle, k = divmod(t, 150)
    cx, cy = rect.centerx, rect.y + 70
    p1, p2 = (rect.x + 60, rect.bottom - 40), (rect.right - 60, rect.bottom - 40)
    if k < 40:                                                   # o inimigo, piscando no golpe
        flash = k > 28 and k % 4 < 2
        body = theme.BONE if flash else (60, 40, 80)
        pygame.draw.ellipse(screen, body, (cx - 26, cy - 30, 52, 60))
        screen.fill(theme.BLOOD, (cx - 12, cy - 10, 6, 6))
        screen.fill(theme.BLOOD, (cx + 6, cy - 10, 6, 6))
    def travel(target, n, done):
        for i in range(n):
            f = max(0.0, min(1.0, (k - 40 - i * 3) / 50))
            if 0 < f < 1:
                x = cx + (target[0] - cx) * f + math.sin(f * 6 + i) * 12 * (1 - f)
                y = cy + (target[1] - 20 - cy) * f - math.sin(f * math.pi) * 40
                pygame.draw.circle(screen, SOUL, (round(x), round(y)), 4)
                pygame.draw.circle(screen, theme.BONE, (round(x), round(y)), 2)
        return done if k >= 40 + n * 3 + 50 else 0
    got1 = travel(p1, 12, 12)
    got2 = travel(p2, 4, 4)
    for (x, y), label, color, total, gain in ((p1, "P1", theme.SLOT_COLORS[1], 12 * cycle + got1, 12),
                                              (p2, "P2", theme.SLOT_COLORS[2], 4 * cycle + got2, 4)):
        box = pygame.Rect(0, 0, 96, 26)
        box.center = (x, y)
        ui.panel(screen, box, accent=color, shadow=False)
        ui.text(screen, label, theme.XS, color, (box.x + 14, box.centery), anchor="midleft", shadow=False)
        ui.text(screen, str(total), theme.XS, SOUL, (box.right - 10, box.centery), anchor="midright", shadow=False)
        if 110 <= k < 140:
            ui.text(screen, f"+{gain}", theme.XS, SOUL, (x, y - 26 - (k - 110) // 3))


def _scene_loja(screen, ui, rect, t):
    """O celular com a loja aberta: toca num item, aperta COMPRAR e o saldo desce."""
    phone = _phone(screen, rect.inflate(-20, -40), t)
    items = (("POÇÃO DE VIDA", 20), ("ARMA SORTEADA", 30), ("TROCAR MELHORIAS", 25), ("DOAR 20 ALMAS", 20))
    k = t % 240
    pick = 1 if k < 120 else 3
    bought = 80 <= k < 120 or k >= 200
    souls = 143 - (30 if 80 <= k else 0) - (20 if k >= 200 else 0)
    ui.text(screen, f"{souls} ALMAS", theme.XS, SOUL, (phone.right - 8, phone.y + 12), anchor="midright", shadow=False)
    for i, (name, cost) in enumerate(items):
        row = pygame.Rect(phone.x + 8, phone.y + 26 + i * 22, phone.w * 0.6, 18)
        on = i == pick
        screen.fill(theme.INK_3 if on else theme.INK_2, row)
        pygame.draw.rect(screen, theme.SLOT_COLORS[1] if on else theme.LINE, row, 1)
        ui.text(screen, name, theme.XS, theme.BONE, (row.x + 6, row.centery), anchor="midleft", shadow=False)
        ui.text(screen, str(cost), theme.XS, SOUL, (row.right - 6, row.centery), anchor="midright", shadow=False)
    buy = pygame.Rect(phone.right - 86, phone.bottom - 30, 78, 22)
    pressed = 70 <= k < 80 or 190 <= k < 200
    screen.fill((60, 110, 50) if pressed else (47, 74, 42), buy.move(0, 2 if pressed else 0))
    pygame.draw.rect(screen, theme.MOSS, buy.move(0, 2 if pressed else 0), 1)
    ui.text(screen, "COMPRAR", theme.XS, theme.BONE, buy.move(0, 2 if pressed else 0).center, shadow=False)
    if bought:
        ui.text(screen, "-30" if k < 120 else "-20", theme.XS, (240, 164, 158), (phone.right - 40, phone.y + 30))
    tip = (phone.right - 47, phone.bottom - 19) if pressed else (phone.x + 60, phone.y + 48 + pick * 22)
    pygame.draw.circle(screen, (230, 200, 170), tip, 7)          # o dedo
    pygame.draw.circle(screen, (180, 140, 120), tip, 7, 2)


def _scene_hud(screen, ui, rect, t):
    """O botão de ATACAR sendo arrastado para outro lugar e crescendo."""
    phone = _phone(screen, rect.inflate(-20, -40), t)
    f = (math.sin(t * 0.03) + 1) / 2
    stick = (phone.x + 50, phone.bottom - 40)
    pygame.draw.circle(screen, theme.INK_3, stick, 28)
    pygame.draw.circle(screen, theme.LINE_HI, stick, 28, 2)
    pygame.draw.circle(screen, theme.SLOT_COLORS[1], stick, 11)
    for (x, y), r in (((phone.right - 80, phone.bottom - 70), 15), ((phone.right - 40, phone.bottom - 86), 15)):
        pygame.draw.circle(screen, theme.INK_3, (x, y), r)
        pygame.draw.circle(screen, theme.LINE_HI, (x, y), r, 2)
    ax = phone.right - 34 - f * 70
    ay = phone.bottom - 32 - f * 8
    r = round(20 + f * 8)
    pygame.draw.circle(screen, (30, 50, 100), (round(ax), round(ay)), r)
    pygame.draw.circle(screen, theme.SLOT_COLORS[1], (round(ax), round(ay)), r, 2)
    for a in range(0, 360, 30):                                  # contorno tracejado de "editando"
        rad = math.radians(a + t * 2)
        px, py = ax + math.cos(rad) * (r + 6), ay + math.sin(rad) * (r + 6)
        screen.fill(theme.BRASS, (round(px) - 1, round(py) - 1, 3, 3))
    ui.text(screen, f"ATACAR · {round(100 + f * 40)}%", theme.XS, theme.BRASS, (phone.x + 10, phone.y + 10),
            anchor="midleft", shadow=False)


def _scene_novidades(screen, ui, rect, t):
    """Páginas passando, como nesta tela."""
    k = (t % 120) / 120
    for i in range(3):
        slide = max(0.0, min(1.0, (k - 0.6) / 0.3)) if i == 0 else 0.0
        page = pygame.Rect(0, 0, 150, 110)
        page.center = (rect.centerx + i * 14 - slide * 200, rect.centery - i * 10)
        if i == 0 and slide >= 1:
            continue
        ui.panel(screen, page, fill=theme.INK_3 if i == 0 else theme.INK_2, shadow=False)
        screen.fill(theme.BRASS, (page.x + 12, page.y + 14, 60, 4))
        for line in range(3):
            screen.fill(theme.MUTED, (page.x + 12, page.y + 34 + line * 16, 110 - line * 20, 3))


NEWS_SCENES = {"almas": _scene_almas, "loja": _scene_loja, "hud": _scene_hud, "novidades": _scene_novidades}


class NewsScene(_InfoScene):
    """Novidades em páginas, cada uma com uma cena animada. Abre sozinha uma vez quando o jogo
    é atualizado, e em OPÇÕES > NOVIDADES quando quiser."""
    heading = "NOVIDADES"
    phase = "news"
    PANEL = pygame.Rect(56, 92, config.SCREEN_W - 112, 360)

    def __init__(self, game, news, back=None):
        from .. import novidades
        super().__init__(game)
        self.news = news if back is not None else news[:2]     # sozinha: só as duas versões mais novas
        self.back = back
        self.pages = [p for version, entry in self.news for p in novidades.pages_of(version, entry)]
        self.page = 0
        self.age = 0
        self.summary = [line for _, entry in self.news[:1] for line in novidades.summary(entry)]

    def enter(self):
        from ..net.remote import hub
        hub.news = self.summary
        super().enter()
        if self.news:
            hub.set_phase("news", banner=f"NOVIDADES DA {self.news[0][0]}")

    def leave(self):
        self.sfx("confirm", 0.4)
        self.game.change(self.back(self.game) if self.back else TitleScene(self.game))

    def turn(self, step):
        page = max(0, min(len(self.pages) - 1, self.page + step))
        if page != self.page:
            self.page, self.age = page, 0
            self.sfx("select", 0.3)

    def update(self):
        super().update()
        self.age += 1

    def handle(self, event):
        if self.is_back(event) or not self.pages:
            if self.is_back(event) or event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                self.leave()
            return
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_LEFT, pygame.K_a):
                self.turn(-1)
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self.turn(1)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                if self.page >= len(self.pages) - 1:
                    self.leave()
                else:
                    self.turn(1)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 3:
                self.turn(-1)
            elif self.page >= len(self.pages) - 1:
                self.leave()
            else:
                self.turn(1)

    def draw_body(self, screen):
        panel = self.PANEL
        self.ui.panel(screen, panel)
        if not self.pages:
            self.footer(screen, [("ENTER", "CONTINUAR")])
            return
        version, title, scene, lines = self.pages[self.page]
        n = len(self.pages)
        self.ui.text(screen, f"VERSÃO {version}", theme.XS, theme.MUTED, (panel.right - 20, panel.y + 18),
                     anchor="midright", shadow=False)
        draw = NEWS_SCENES.get(scene)
        x = panel.x + 24
        if draw is not None:
            stage = pygame.Rect(panel.x + 20, panel.y + 40, 340, 250)
            screen.fill(theme.INK, stage)
            pygame.draw.rect(screen, theme.LINE, stage, 1)
            clip = screen.get_clip()
            screen.set_clip(stage)
            draw(screen, self.ui, stage, self.ticks)
            screen.set_clip(clip)
            x = stage.right + 28
        width = panel.right - 24 - x
        slide = max(0, 12 - self.age) * 3                        # o texto entra deslizando ao virar a página
        y = panel.y + 52
        self.ui.text(screen, title, theme.S, theme.BRASS, (x + slide, y), anchor="midleft")
        y += 28
        for line in lines:
            if y > panel.bottom - 40:
                break
            screen.fill(theme.MOSS, (x + 2 + slide, y + 2, 5, 5))
            y = self.ui.paragraph(screen, line.upper(), theme.XS, theme.BONE, (x + 16 + slide, y),
                                  width - 16, spacing=15) + 10
        # bolinhas das páginas
        if n > 1:
            gap = 14
            left = panel.centerx - (n - 1) * gap // 2
            for i in range(min(n, 40)):
                color = theme.BRASS if i == self.page else theme.LINE_HI
                size = 6 if i == self.page else 4
                screen.fill(color, (left + i * gap - size // 2, panel.bottom - 18 - size // 2, size, size))
        last = self.page >= n - 1
        self.footer(screen, [("←→", "PÁGINAS"), ("ENTER", "SAIR" if last else "PRÓXIMA"), ("ESC", "SAIR")])
