"""Telas de menu: carregamento, título, modos e telas de informação."""
import math
import webbrowser

import pygame

from .. import config, theme
from ..controls import KEY_LABELS, SOCCER_KEY_LABELS, PlayerInput
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
            self.game.change(TitleScene(self.game))

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

    def __init__(self, game):
        super().__init__(game)
        if game.backdrop is None:
            game.backdrop = Backdrop(game.assets)
        self.backdrop = game.backdrop

    def draw_background(self, screen):
        self.backdrop.draw(screen, self.game.clock_ticks)


class TitleScene(_MenuScene):
    def __init__(self, game):
        super().__init__(game)
        game.session = None
        self.cast = roster()
        self.menu = MenuList(
            [("JOGAR", "play"), ("CONTROLES", "controls"), ("SOBRE O PROJETO", "about"),
             ("CRÉDITOS", "credits"), ("SAIR", "quit")],
            topleft=(config.SCREEN_W // 2 - 130, 206), width=260, row_h=34)

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
        elif choice == "about":
            self.game.change(AboutScene(self.game))
        elif choice == "credits":
            self.game.change(CreditsScene(self.game))
        elif choice == "quit":
            self.game.quit()

    def draw(self, screen):
        W, H = config.SCREEN_W, config.SCREEN_H
        self.draw_background(screen)
        self.ui.logo(screen, (W // 2, 112))
        self.ui.text(screen, "DUELO DE ARENA  ·  FUTEBOL", theme.XS, theme.MUTED, (W // 2, 158))
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
    "campaign": ("Juntos contra as sombras: em cada fase, um acampamento e duas masmorras, com um baú "
                 "escondido de armas raras no caminho. No fim, o chefão Aryel Corrompido. Quem cair pode "
                 "ser levantado por um companheiro.",
                 "1 A 4 JOGADORES"),
}


class ModeScene(_MenuScene):
    def __init__(self, game):
        super().__init__(game)
        options = [(MODES[k]["title"], k) for k in ("campaign", "cpu", "duel", "duel2", "soccer1", "soccer2")]
        options.append(("VOLTAR", "back"))
        self.menu = MenuList(options, topleft=(56, 104), width=320, row_h=38)

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
        count = MODES[choice]["slots"]
        teams = MODES[choice].get("teams", False)
        slots = [SlotSetup(s, cpu=(choice == "cpu" and s == 2) or (teams and s > 1))
                 for s in range(1, count + 1)]
        if choice == "campaign":
            slots = slots[:1]           # P2 a P4 entram na tela de conexão
        previous = self.game.session
        self.game.session = Session(choice, slots)
        if previous is not None and teams:
            self.game.session.layout = previous.layout      # mantém a divisão de times escolhida
        from .select import CharSelectScene, LobbyScene
        if choice == "cpu":
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
            desc, players = MODE_TEXT[key]
            self._illustration(screen, key, pygame.Rect(panel.x + 2, panel.y + 2, panel.w - 4, 170))
            self.ui.text(screen, MODES[key]["title"], theme.S, theme.BRASS, (panel.x + 24, panel.y + 196), anchor="topleft")
            self.ui.text(screen, players, theme.XS, theme.MUTED, (panel.right - 24, panel.y + 200), anchor="topright")
            self.ui.paragraph(screen, desc, theme.XS, theme.BONE, (panel.x + 24, panel.y + 232), panel.w - 48, spacing=16)
        self.footer(screen, [("↑↓", "ESCOLHER"), ("ENTER", "CONFIRMAR"), ("ESC", "VOLTAR")])

    def _illustration(self, screen, key, area):
        if key == "campaign":
            self._campaign_illustration(screen, area)
            return
        battle = key in ("cpu", "duel", "duel2")
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
            "duel": [("aryel", "direita", -90), ("ninja", "esquerda", 90)],
            "duel2": [("pirata", "direita", -150), ("geada", "direita", -70),
                      ("atirador", "esquerda", 70), ("tanque", "esquerda", 150)],
            "soccer1": [("velocista", "direita", -110), ("atirador", "esquerda", 110)],
            "soccer2": [("tita", "direita", -150), ("fantasma", "direita", -70),
                        ("guerreiro", "esquerda", 70), ("aryel", "esquerda", 150)],
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

    # (ação, tecla do jogador 1, tecla do jogador 2) — None = mesma tecla do duelo
    ROWS = [
        ("MOVER", KEY_LABELS[1]["move"], KEY_LABELS[2]["move"]),
        ("ATACAR / CHUTAR", KEY_LABELS[1]["attack"], KEY_LABELS[2]["attack"]),
        ("HABILIDADE / PASSE", KEY_LABELS[1]["special"], KEY_LABELS[2]["special"]),
        ("ESQUIVA (DUELO)", KEY_LABELS[1]["dodge"], KEY_LABELS[2]["dodge"]),
        ("TROCAR ARMA / SUPER", KEY_LABELS[1]["switch"], KEY_LABELS[2]["switch"]),
        ("CORTE / CARRINHO (FUTEBOL)", SOCCER_KEY_LABELS[1]["dodge"], SOCCER_KEY_LABELS[2]["dodge"]),
        ("CORRER (FUTEBOL)", SOCCER_KEY_LABELS[1]["sprint"], SOCCER_KEY_LABELS[2]["sprint"]),
        ("MARCAR (FUTEBOL)", SOCCER_KEY_LABELS[1]["mark"], SOCCER_KEY_LABELS[2]["mark"]),
        ("CONDUZIR COLADO (FUTEBOL)", SOCCER_KEY_LABELS[1]["dribble"], SOCCER_KEY_LABELS[2]["dribble"]),
    ]
    TIPS = [
        "DUELO: A MUNIÇÃO RECARREGA SOZINHA. ARCO: SEGURE ATACAR PARA TENSIONAR.",
        "FUTEBOL: TOQUE EM CHUTAR/PASSE = RASTEIRO. SEGURE E SOLTE = PELO ALTO.",
        "PASSE VAI NA DIREÇÃO QUE VOCÊ APONTA. NA PONTA, NO 2X2, VIRA CRUZAMENTO.",
        "NO SEU CAMPO, CHUTAR COM A BOLA SOLTA = CHUTÃO PARA LONGE DO GOL.",
        "CORTE COM UM CHUTE VINDO = CARRINHO DE BLOQUEIO.",
    ]

    def __init__(self, game):
        super().__init__(game)
        self.toggle_rect = pygame.Rect(0, 0, 0, 0)

    def _toggle_double_tap(self):
        PlayerInput.double_tap_enabled = not PlayerInput.double_tap_enabled
        self.sfx("click", 0.4)

    def handle(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_t:
            self._toggle_double_tap()
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
        for label, k1, k2 in self.ROWS:
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
        self.footer(screen, [("T", "DUPLO TOQUE"), ("ESC", "VOLTAR")])


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
     "power.use() de uma subclasse de SoccerPower (Carrinho, ChuteCerteiro, MuralhaDoGol, Sombra, Arrancada, "
     "Bomba, BombaSombria, BolaFantasma, Gigante, GanchoNaBola e Congelar). Na campanha, cada inimigo tem um "
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
