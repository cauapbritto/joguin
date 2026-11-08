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


def rematch(game):
    """Começa de novo a última partida (revanche rápida do título)."""
    game.session = game.last_session
    if game.session.penalty:
        from .penalty import start_penalties
        game.change(start_penalties(game))
    else:
        from .play import VersusScene
        game.change(VersusScene(game))


class TitleScene(_MenuScene):
    menu_keys = True

    def __init__(self, game):
        super().__init__(game)
        game.session = None
        self.cast = roster()
        options = [("JOGAR", "play"), ("CONTROLES", "controls"), ("OPÇÕES", "options"),
                   ("ESTATÍSTICAS", "stats"), ("SOBRE O PROJETO", "about"), ("CRÉDITOS", "credits"), ("ATUALIZAR", "update"), ("SAIR", "quit")]
        last = getattr(game, "last_session", None)
        if last is not None:
            # revanche rápida: a última partida de novo, com os mesmos lutadores, sem passar pelos menus
            options.insert(1, ("REVANCHE: " + last.title, "rematch"))
        # com a revanche são 9 opções: o logo sobe um pouco para o elenco no chão não cobrir o SAIR
        self.logo_y = 112 if last is None else 96
        top, row_h = (176, 29) if last is None else (164, 26)
        self.menu = MenuList(options, topleft=(config.SCREEN_W // 2 - 150, top), width=300, row_h=row_h)

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
        elif choice == "rematch":
            rematch(self.game)
        elif choice == "controls":
            if self.game.gamepads.pads:
                from .pad import PadScene               # com controle conectado: a tela do controle
                self.game.change(PadScene(self.game))
            else:
                self.game.change(ControlsScene(self.game))
        elif choice == "options":
            self.game.change(OptionsScene(self.game))
        elif choice == "stats":
            from .stats import StatsScene
            self.game.change(StatsScene(self.game))
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
        self.ui.logo(screen, (W // 2, self.logo_y))
        self.ui.text(screen, "CAMPANHA  ·  DUELOS  ·  FUTEBOL  ·  BASQUETE", theme.XS, theme.MUTED,
                     (W // 2, self.logo_y + 44))
        self.menu.draw(screen, self.ui, self.ticks)

        # elenco no chão
        ground = H - 52
        cast = self.cast
        n = len(cast)
        _stage(screen, ground)
        for i, stats in enumerate(cast):
            x = 96 + i * (W - 192) // (n - 1)
            bob = 1 if (self.ticks // 24 + i) % 2 else 0
            img = self.assets.sprites[stats.key].portrait
            screen.blit(_reflection(img), _reflection(img).get_rect(midtop=(x, ground + 2)))
            pygame.draw.ellipse(screen, (4, 2, 8), (x - 18, ground - 5, 36, 10))
            pygame.draw.ellipse(screen, (16, 12, 22), (x - 12, ground - 3, 24, 6))
            screen.blit(img, img.get_rect(midbottom=(x, ground + bob)))

        if server.start_error:
            # outro Soul Strike aberto (ou outro programa) já está usando a porta do controle
            self.ui.text(screen, "CELULAR INDISPONÍVEL: " + server.start_error, theme.XS, theme.BLOOD,
                         (W - 16, H - 28), anchor="bottomright")
            self.ui.text(screen, "FECHE A OUTRA JANELA DO JOGO E ABRA DE NOVO", theme.XS, theme.MUTED,
                         (W - 16, H - 14), anchor="bottomright")
        else:
            hint = server.firewall_hint()
            if hint:
                # Linux com o firewall (ufw) ligado e nenhum celular chegou até agora
                self.ui.text(screen, "CELULAR NÃO CONECTA? FIREWALL LIGADO, NO TERMINAL: " + hint,
                             theme.XS, theme.BRASS,
                             (W - 16, H - 42), anchor="bottomright")
            self.ui.text(screen, "CELULAR COMO CONTROLE:", theme.XS, theme.FAINT, (W - 16, H - 28), anchor="bottomright")
            self.ui.text(screen, self.game.base_url, theme.XS, theme.MUTED, (W - 16, H - 14), anchor="bottomright")
        self.ui.text(screen, "F11 TELA CHEIA", theme.XS, theme.FAINT, (16, H - 14), anchor="bottomleft")


_STAGES = {}
_REFLECTIONS = {}


def _stage(screen, ground):
    """Palco do elenco no título: piso escuro com a beirada acesa e a luz caindo para a frente."""
    W, H = screen.get_size()
    key = (W, H, ground)
    if key not in _STAGES:
        s = pygame.Surface((W, H - ground + 8), pygame.SRCALPHA)
        for y in range(s.get_height()):
            k = y / s.get_height()
            s.fill((10, 8, 16, round(120 + 100 * k)), (0, y, W, 1))
        for x in range(0, W, 2):                      # beirada acesa, mais forte no meio
            mid = 1 - abs(x - W / 2) / (W / 2)
            a = round(40 + 120 * mid ** 1.5)
            s.fill((228, 170, 76, a), (x, 8, 2, 1))
            s.fill((120, 70, 40, a // 2), (x, 9, 2, 1))
        _STAGES[key] = s
    screen.blit(_STAGES[key], (0, ground - 8))


def _reflection(img):
    """Reflexo apagado do retrato no piso do palco."""
    key = id(img)
    if key not in _REFLECTIONS:
        r = pygame.transform.flip(img, False, True).copy()
        h = r.get_height()
        fade = pygame.Surface(r.get_size(), pygame.SRCALPHA)
        for y in range(h):
            fade.fill((255, 255, 255, max(0, round(54 * (1 - y / (h * 0.5))))), (0, y, r.get_width(), 1))
        r.blit(fade, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        _REFLECTIONS[key] = (img, r)
    return _REFLECTIONS[key][1]


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
    "basket1": ("Um contra um com poder demais: SUPER a cada 4 s, barra de ULTRA que enche com cesta, toco e "
                "roubo, fogo com 2 cestas seguidas e orbes de poder na quadra. 3 minutos ou 21 pontos. "
                "Sem o P2, joga contra a CPU.",
                "1 OU 2 JOGADORES"),
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
    "penaltis1": ("Você contra um amigo: cada um escolhe um herói, bate uma e defende a outra, 5 para cada "
                  "lado e depois morte súbita. Sem o P2, a CPU vai para o gol.",
                  "1 OU 2 JOGADORES"),
    "penaltis": ("Disputa de pênaltis em dupla com o gol de frente, sem partida antes: escolha os times, arrume a ordem "
                 "dos batedores e bata 5 para cada lado, depois morte súbita. Cada herói bate e defende do seu jeito.",
                 "1 A 4 JOGADORES"),
    "treino_penaltis": ("Treino sem fim contra a CPU: você bate uma e defende outra. O canto é a direção do "
                        "analógico na hora de soltar o CHUTE; o goleiro pula com a ESQUIVA.",
                        "1 JOGADOR"),
    "desafio_goleiro": ("Defenda 3 seguidas contra a CPU para passar de rodada. A CPU fica mais difícil a cada "
                        "rodada, e 3 gols tomados acabam o desafio.",
                        "1 JOGADOR"),
    "campaign": ("Juntos contra as sombras, em 4 capítulos, saindo da Casa da turma: cada fase é um mapa só, a pé, com salas "
                 "ligadas por corredores: três salas de luta, que trancam até ser limpas, e uma de recompensa (baú de armas raras, loja e ferreiro). O capítulo 1 acaba no Aryel Corrompido, o 2 "
                 "no Borba Jr Corrompido (Lag Lobby), o 3 no Albeguinio Corrompido (Clínica Clepalovers) e o 4 "
                 "no Cauanzera Corrompido (Mansão do Carimbo). Quem cair pode ser levantado.",
                 "1 A 4 JOGADORES"),
    "campaign2": ("Direto para a Lag Lobby, tomada pela Patrulha Cinza: drones, milicianos, torretas e soldados "
                  "de exo. Cada um começa com almas e 3 melhorias (2 sorteadas e 1 escolhida). Sem recorde de "
                  "tempo: ele vale só para a campanha inteira.",
                  "1 A 4 JOGADORES"),
    "campaign3": ("Direto para a Clínica Clepalovers, tomada pelo caco do fragmento: máscaras de argila, "
                  "seringuinhas, cadeiras que puxam, espelhos que copiam e o Albeguinio Corrompido no "
                  "administrativo. Cada um começa com mais almas e 5 melhorias (4 sorteadas e 1 escolhida). "
                  "Sem recorde de tempo.",
                  "1 A 4 JOGADORES"),
    "passeio": ("Só a Casa da turma, para andar e mexer em tudo: o computador, a roleta, a horta, a padaria, "
                "a garagem e a armadura de Uno. Sem fase, sem tempo e sem mexer no save da campanha. Para voltar "
                "ao menu, é pela pausa.",
                "1 A 4 JOGADORES"),
    "reuniao": ("Os quatro chefes da campanha, um atrás do outro, sem acampamento no meio: Aryel, Borba Jr, "
                "Albeguinio e Cauanzera Corrompidos. Cada um começa com 4 melhorias sorteadas e ganha mais uma "
                "depois de cada chefe. Vale um selo por dificuldade.",
                "1 A 4 JOGADORES"),
    "cinema": ("Reveja as histórias da campanha inteira, do prólogo no Templo Gelado até o fim na Mansão do "
               "Carimbo, com os selos de zerado de cada dificuldade.",
               "QUALQUER UM"),
    "campaign4": ("Direto para a Mansão do Carimbo, em Cuiabrasa (47 graus à sombra): processos que andam, "
                  "carimbos que pulam, a fila que arrasta, o CPD sem energia e o Cauanzera Corrompido com a IARA "
                  "no gabinete. Cada um começa com mais almas e 7 melhorias (6 sorteadas e 1 escolhida). "
                  "Sem recorde de tempo.",
                  "1 A 4 JOGADORES"),
}


# (modalidade, rótulo, cor, linha de baixo do cartão, modo da cena do cartão)
CATEGORIES = [
    ("campanha", "CAMPANHA", theme.EMBER, "4 CAPÍTULOS"),
    ("duelos", "DUELOS", theme.BLOOD, "CPU · 1X1 · 2X2"),
    ("futebol", "FUTEBOL", theme.MOSS, "PARTIDA · PÊNALTIS"),
    ("basquete", "BASQUETE", (226, 112, 36), "1X1 · 2X2 · TREINO"),
]
CATEGORY_KEYS = [c[0] for c in CATEGORIES]
# grupos de cada modalidade: (título do grupo, [modos])
MODE_GROUPS = {
    "campanha": [("CAPÍTULOS", ["continue", "campaign", "campaign2", "campaign3", "campaign4"]),
                 ("EXTRAS", ["passeio", "reuniao", "cinema"])],
    "duelos": [("LUTAR", ["cpu", "duel", "duel2"]), ("TREINAR", ["treino"])],
    "futebol": [("PARTIDA", ["soccer1", "soccer2"]), ("PÊNALTIS", ["penaltis1", "penaltis", "desafio_goleiro"]),
                ("TREINAR", ["treino_futebol", "treino_penaltis"])],
    "basquete": [("PARTIDA", ["basket1", "basket2"]), ("TREINAR", ["treino_basquete"])],
}
# nomes na lista (cabem na largura dela; o painel ao lado mostra o nome inteiro)
MODE_LABELS = {"continue": "CONTINUAR CAMPANHA", "campaign": "1 · AS SOMBRAS",
               "campaign2": "2 · LAG LOBBY", "campaign3": "3 · CLEPALOVERS",
               "campaign4": "4 · MANSÃO",
               "reuniao": "REUNIÃO DOS CHEFES", "cinema": "CINEMA", "passeio": "PASSEAR NA CASA",
               "cpu": "CONTRA A CPU", "duel": "DUELO LOCAL 1 x 1",
               "treino": "TREINO E ARSENAL", "penaltis": "DISPUTA DE PÊNALTI"}
# cena do cartão de cada modalidade: (chão, linhas, [(sprite, direção, dx)], extra)
_CARD_ART = {
    "campanha": ((24, 34, 22), (30, 44, 28), [("guerreiro", "direita", -46), ("diabrete", "esquerda", 46)],
                 "sombra"),
    "duelos": (theme.INK, theme.INK_2, [("aryel", "direita", -46), ("ninja", "esquerda", 46)], None),
    "futebol": ((34, 92, 46), (40, 104, 52), [("velocista", "direita", -46), ("atirador", "esquerda", 46)],
                "bola"),
    "basquete": ((120, 78, 44), (134, 88, 50), [("ninja", "direita", -46), ("tita", "esquerda", 46)], "basquete"),
}


# ── capas dos modos: um pedaço do cenário de verdade, com luz ─────────────
# (mapa, foco x, foco y, cor da luz, partículas)
COVER_SCENES = {
    "campanha": ("floresta", 0.5, 0.55, (170, 220, 120), "vagalume"),
    "duelos": ("arena_classica", 0.5, 0.5, (255, 190, 110), "brasa"),
    "futebol": ("campo_futebol", 0.5, 0.5, (255, 250, 220), None),
    "basquete": ("quadra_ginasio", 0.5, 0.5, (255, 220, 160), None),
    "chapter1": ("floresta", 0.45, 0.55, (170, 220, 120), "vagalume"),
    "chapter2": ("lag_openspace", 0.5, 0.5, (150, 200, 255), "pixel"),
    "chapter3": ("clinica_consultorios", 0.5, 0.5, (255, 170, 210), "brilho"),
    "chapter4": ("mansao_fila", 0.5, 0.5, (255, 200, 120), "brasa"),
    "reuniao": ("mansao_nucleo", 0.5, 0.5, (190, 120, 255), "alma"),
    "cinema": ("mansao_reuniao", 0.5, 0.5, (255, 220, 170), "brilho"),
    "cpu": ("arena_classica", 0.5, 0.5, (255, 190, 110), "brasa"),
    "duel": ("coliseu", 0.5, 0.5, (255, 180, 110), "brasa"),
    "duel2": ("coliseu", 0.5, 0.62, (255, 180, 110), "brasa"),
    "treino": ("calabouco", 0.5, 0.5, (255, 170, 90), "brasa"),
    "soccer1": ("campo_futebol", 0.5, 0.5, (255, 250, 220), None),
    "soccer2": ("campo_cuiabrasa", 0.5, 0.5, (255, 230, 170), None),
    "penaltis": ("campo_futebol", 0.93, 0.5, (255, 250, 220), None),
    "penaltis1": ("campo_futebol", 0.07, 0.5, (255, 250, 220), None),     # 1 x 1: o outro gol
    "desafio_goleiro": ("campo_futebol", 0.93, 0.5, (255, 250, 220), None),
    "treino_futebol": ("campo_futebol", 0.3, 0.5, (255, 250, 220), None),
    "treino_penaltis": ("campo_cuiabrasa", 0.93, 0.5, (255, 230, 170), None),
    "basket1": ("quadra_rua", 0.5, 0.5, (255, 220, 160), None),
    "basket2": ("quadra_soul", 0.5, 0.5, (200, 150, 255), "alma"),
    "treino_basquete": ("quadra_cuiabrasa", 0.5, 0.5, (255, 210, 140), None),
}
_COVER_CACHE = {}
_PARTICLE_COLORS = {"vagalume": (200, 255, 140), "brasa": (255, 170, 80), "pixel": (120, 200, 255),
                    "brilho": (255, 230, 245), "alma": (200, 170, 255)}


def _map_floor(assets, key):
    """Chão inteiro do mapa (só a parte barata: arte do fundo, campo ou cenário pintado pequeno)."""
    from .. import scenery
    from ..arena import BASKET_MAPS, MAPS_BY_KEY, SOCCER_MAPS, _basket_court, _soccer_pitch
    cfg = MAPS_BY_KEY[key]
    bg = assets.backgrounds.get(key)
    w, h = cfg.size
    if bg is not None:
        return pygame.transform.scale(bg, (w, h)) if bg.get_size() != (w, h) else bg
    surf = pygame.Surface((w, h))
    if key in SOCCER_MAPS:
        _soccer_pitch(surf, cfg.floor)
        return surf
    if key in BASKET_MAPS:
        _basket_court(surf, cfg.floor)
        return surf
    return None


def cover_image(assets, key, size):
    """Fundo da capa, pronto e guardado: o pedaço do mapa no foco, no dobro do tamanho (o mesmo
    tamanho de pixel dos bonecos da capa), mais escuro em cima, com uma poça de luz no chão e
    cantos escuros."""
    from .. import scenery
    from ..arena import MAPS_BY_KEY
    ck = (key, size)
    if ck in _COVER_CACHE:
        return _COVER_CACHE[ck]
    map_key, fx, fy, light, _ = COVER_SCENES[key]
    w, h = size
    half = (w // 2 + 1, h // 2 + 1)
    full = _map_floor(assets, map_key)
    if full is not None:
        fw, fh = full.get_size()
        cx = max(half[0] // 2, min(fw - half[0] // 2, round(fw * fx)))
        cy = max(half[1] // 2, min(fh - half[1] // 2, round(fh * fy)))
        piece = full.subsurface(pygame.Rect(cx - half[0] // 2, cy - half[1] // 2, *half)).copy()
    else:
        # cenário pintado: pinta só o pedaço (custa pouco) com a semente do próprio mapa
        cfg = MAPS_BY_KEY[map_key]
        piece = scenery.paint_floor(f"capa:{map_key}:{half}", half, cfg.scenery)
    img = pygame.transform.scale(piece, (half[0] * 2, half[1] * 2)).subsurface((0, 0, w, h)).copy()
    shade = pygame.Surface(size, pygame.SRCALPHA)
    for y in range(h):                                  # o alto escurece (fundo), o chão fica aceso
        k = 1 - y / h
        shade.fill((6, 4, 12, round(150 * k ** 1.6)), (0, y, w, 1))
    img.blit(shade, (0, 0))
    pool = pygame.Surface(size)                         # poça de luz onde os bonecos pisam
    for i in range(8, 0, -1):
        k = i / 8
        c = tuple(round(v * 0.11 * (1 - k) ** 0.8) for v in light)
        pygame.draw.ellipse(pool, c, (w / 2 - w * 0.55 * k, h * 0.86 - h * 0.28 * k, w * 1.1 * k, h * 0.56 * k))
    img.blit(pool, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
    edge = pygame.Surface(size, pygame.SRCALPHA)        # cantos escuros
    steps = 10
    for i in range(steps):
        a = round(90 * (1 - i / steps) ** 2)
        pygame.draw.rect(edge, (0, 0, 0, a), (i * 2, i * 2, w - i * 4, h - i * 4), 2)
    img.blit(edge, (0, 0))
    _COVER_CACHE[ck] = img
    return img


def draw_cover(screen, assets, key, area, ticks):
    """Capa animada: o fundo pronto e as partículas do lugar (vaga-lumes, brasas, pixels...)."""
    screen.blit(cover_image(assets, key, area.size), area)
    kind = COVER_SCENES[key][4]
    if kind is None:
        return
    color = _PARTICLE_COLORS[kind]
    t = ticks * 0.02
    for i in range(16):
        fx, fy = (i * 0.618) % 1, (i * 0.414) % 1
        if kind in ("brasa", "alma"):                   # sobem
            y = area.bottom - ((fy * area.h + t * (10 + i % 5 * 4)) % area.h)
            x = area.x + fx * area.w + math.sin(t + i) * 6
        else:                                           # flutuam no lugar
            x = area.x + fx * area.w + math.sin(t * 0.7 + i * 2) * 10
            y = area.y + area.h * (0.25 + 0.6 * fy) + math.cos(t * 0.9 + i) * 8
        k = 0.5 + 0.5 * math.sin(t * 3 + i * 1.7)
        if k < 0.2:
            continue
        c = tuple(round(v * k) for v in color)
        n = 2 if i % 3 == 0 else 1
        screen.fill(c, (round(x), round(y), n, n), special_flags=pygame.BLEND_RGB_ADD)


def category_of(mode):
    for cat, groups in MODE_GROUPS.items():
        if any(mode in modes for _, modes in groups):
            return cat
    return None


class ModeScene(_MenuScene):
    """Escolha do modo em dois níveis: primeiro a modalidade (4 cartões), depois os modos dela."""

    menu_keys = True
    CARD_W, CARD_H, CARD_GAP, CARD_Y = 196, 300, 20, 112
    PANEL_BOTTOM = 498                  # o painel de descrição cresce até aqui (o rodapé fica livre)

    def __init__(self, game, category=None):
        super().__init__(game)
        from .. import progress
        from ..campaign import CampaignRun
        saved = progress.saved_campaign()
        self.saved_run = CampaignRun.from_save(saved) if saved else None
        self.chapter2 = progress.campaign_cleared()
        self.chapter3 = progress.chapter_cleared(2)
        self.chapter4 = progress.chapter_cleared(3)
        self.cleared = progress.chapter_cleared(4)          # zerou tudo: Reunião dos Corrompidos e cinema
        last = settings.get("ultimo_modo")
        self.cat_index = CATEGORY_KEYS.index(category_of(last)) if category_of(last) else 0
        self.category = None
        self.menu = None
        self.headers = []
        x0 = (config.SCREEN_W - (self.CARD_W * 4 + self.CARD_GAP * 3)) // 2
        self.card_rects = [pygame.Rect(x0 + i * (self.CARD_W + self.CARD_GAP), self.CARD_Y, self.CARD_W, self.CARD_H)
                           for i in range(4)]
        self.continue_rect = pygame.Rect(x0, 436, self.CARD_W * 4 + self.CARD_GAP * 3, 34)
        self.tab_rects = []
        if category is not None:
            self.open(category)

    # ── navegação ────────────────────────────
    def modes_of(self, category):
        out = []
        for title, modes in MODE_GROUPS[category]:
            keep = [m for m in modes if (m != "continue" or self.saved_run is not None)
                    and (m != "campaign2" or self.chapter2) and (m != "campaign3" or self.chapter3)
                    and (m != "campaign4" or self.chapter4)
                    and (m not in ("reuniao", "cinema") or self.cleared)]
            if keep:
                out.append((title, keep))
        return out

    def open(self, category, select=None):
        """Abre o segundo nível (os modos da modalidade)."""
        self.category = category
        self.cat_index = CATEGORY_KEYS.index(category)
        options, rects, self.headers = [], [], []
        y = 128
        for title, modes in self.modes_of(category):
            self.headers.append((title, y))
            y += 14
            for m in modes:
                options.append((MODE_LABELS.get(m) or MODES[m]["title"], m))
                rects.append(pygame.Rect(56, y, 340, 30))
                y += 34
            y += 10
        self.menu = MenuList(options, topleft=(56, 128), width=340)
        self.menu.rects = rects
        values = [v for _, v in options]
        last = select or ("continue" if "continue" in values else settings.get("ultimo_modo"))
        if last in values:
            self.menu.index = values.index(last)

    def close(self):
        self.category = None
        self.menu = None

    def _shift_category(self, step):
        self.sfx("select", 0.25)
        self.open(CATEGORY_KEYS[(self.cat_index + step) % len(CATEGORY_KEYS)])

    def handle(self, event):
        if self.category is None:
            self._handle_cards(event)
        else:
            self._handle_modes(event)

    def _handle_cards(self, event):
        if self.is_back(event):
            self.sfx("cancel", 0.4)
            self.game.change(TitleScene(self.game))
            return
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_LEFT, pygame.K_a):
                self.cat_index = (self.cat_index - 1) % 4
                self.sfx("select", 0.25)
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self.cat_index = (self.cat_index + 1) % 4
                self.sfx("select", 0.25)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                self.sfx("confirm")
                self.open(CATEGORY_KEYS[self.cat_index])
            elif event.key == pygame.K_c and self.saved_run is not None:
                self.start("continue")
        elif event.type == pygame.MOUSEMOTION:
            for i, r in enumerate(self.card_rects):
                if r.collidepoint(event.pos) and i != self.cat_index:
                    self.cat_index = i
                    self.sfx("hover", 0.15)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, r in enumerate(self.card_rects):
                if r.collidepoint(event.pos):
                    self.sfx("confirm")
                    self.open(CATEGORY_KEYS[i])
                    return
            if self.saved_run is not None and self.continue_rect.collidepoint(event.pos):
                self.start("continue")
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            self.sfx("cancel", 0.4)
            self.game.change(TitleScene(self.game))

    def _handle_modes(self, event):
        if self.is_back(event) or (event.type == pygame.MOUSEBUTTONDOWN and event.button == 3):
            self.sfx("cancel", 0.4)
            self.close()
            return
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_PAGEUP, pygame.K_q):
            self._shift_category(-1)
            return
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_PAGEDOWN, pygame.K_e):
            self._shift_category(1)
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, r in enumerate(self.tab_rects):
                if r.collidepoint(event.pos):
                    if i != self.cat_index:
                        self.sfx("select", 0.25)
                        self.open(CATEGORY_KEYS[i])
                    return
        choice = self.menu.handle(event, self.sfx)
        if choice is not None:
            self.start(choice)

    def start(self, choice):
        self.sfx("confirm")
        if choice == "cinema":
            from .campaign import CinemaScene
            self.game.change(CinemaScene(self.game))
            return
        if choice == "continue":
            from .campaign import hub_scene
            run = self.saved_run
            self.game.session = run.session
            self.game.change(hub_scene(self.game, run, story=False))
            return
        settings.change("ultimo_modo", choice)
        start_mode(self.game, choice)

    # ── desenho ──────────────────────────────
    def draw(self, screen):
        self.draw_background(screen)
        if self.category is None:
            self._draw_cards(screen)
        else:
            self._draw_modes(screen)

    def _draw_cards(self, screen):
        W = config.SCREEN_W
        self.title(screen, "MODO DE JOGO", y=52)
        self.ui.text(screen, "ESCOLHA A MODALIDADE", theme.XS, theme.MUTED, (W - 64, 52), anchor="midright")
        for i, ((key, name, color, sub), rect) in enumerate(zip(CATEGORIES, self.card_rects)):
            chosen = i == self.cat_index
            r = rect.move(0, -8) if chosen else rect
            screen.fill(theme.SHADOW, r.move(4, 4))
            art = pygame.Rect(r.x, r.y, r.w, r.h - 92)
            screen.set_clip(art)
            self._card_art(screen, key, art)
            screen.set_clip(None)
            if not chosen:
                veil = pygame.Surface(art.size, pygame.SRCALPHA)
                veil.fill((8, 6, 14, 140))
                screen.blit(veil, art)
            base = pygame.Rect(r.x, art.bottom, r.w, r.h - art.h)
            screen.fill(theme.INK_3 if chosen else theme.INK_2, base)
            screen.fill(color, (r.x, art.bottom, r.w, 3))
            self.ui.text(screen, name, theme.S, theme.BRASS if chosen else theme.BONE, (base.centerx, base.y + 26))
            self.ui.text(screen, "1 A 4 JOGADORES", theme.XS, theme.MUTED, (base.centerx, base.y + 52))
            self.ui.text(screen, sub, theme.XS, theme.BONE if chosen else theme.FAINT, (base.centerx, base.y + 70),
                         shadow=False)
            pygame.draw.rect(screen, theme.BRASS if chosen else theme.LINE, r, 3 if chosen else 2)
            if chosen:
                nudge = 1 if (self.ticks // 20) % 2 else 0
                self.ui.arrow(screen, (r.centerx, r.y - 12 + nudge), "down", 7, theme.BRASS)
        if self.saved_run is not None:
            from ..campaign import PHASES
            cont = self.continue_rect
            screen.fill(theme.INK_2, cont)
            pygame.draw.rect(screen, theme.LINE, cont, 1)
            run = self.saved_run
            text = f"CAMPANHA SALVA: FASE {run.phase_index + 1} DE {len(PHASES)} · {run.phase.name.upper()}"
            self.ui.text(screen, text, theme.XS, theme.MUTED, (cont.x + 16, cont.centery), anchor="midleft",
                         shadow=False)
            cap = self.ui.keycap(screen, "Y / C", (cont.right - 170, cont.centery))
            self.ui.text(screen, "CONTINUAR", theme.XS, theme.BRASS, (cap.right + 8, cont.centery), anchor="midleft",
                         shadow=False)
        self.footer(screen, [("←→", "MODALIDADE"), ("A / ENTER", "ABRIR"), ("B / ESC", "VOLTAR")])

    def _card_art(self, screen, key, area):
        floor, line, cast, extra = _CARD_ART[key]
        draw_cover(screen, self.assets, key, area, self.ticks)
        ground = area.bottom - 30
        step = self.ticks // 4
        if extra == "sombra":
            from ..enemies import SHADOW_RIM
            from ..fighter import draw_aura
            img = self.assets.shadow_sprites("aryel").frame("frente", step).copy()
            img.set_alpha(170)
            rect = img.get_rect(midbottom=(area.centerx, ground - 70))
            draw_aura(screen, img, rect, SHADOW_RIM, self.ticks, 3)
            screen.blit(img, rect)
        for name, direction, dx in cast:
            img = self.assets.sprites[name].frame(direction, step)
            img = pygame.transform.scale(img, (img.get_width() * 2, img.get_height() * 2))
            x = area.centerx + dx
            pygame.draw.ellipse(screen, (0, 0, 0), (x - 26, ground - 7, 52, 12))
            screen.blit(img, img.get_rect(midbottom=(x, ground + 4)))
        if extra == "bola":
            bx = area.centerx + int(math.sin(self.ticks * 0.05) * 14)
            pygame.draw.circle(screen, (20, 18, 24), (bx, ground - 6), 9)
            pygame.draw.circle(screen, (238, 236, 228), (bx, ground - 6), 8)
        elif extra == "basquete":
            by = ground - 8 - int(abs(math.sin(self.ticks * 0.08)) * 46)
            pygame.draw.circle(screen, (60, 24, 8), (area.centerx, by), 10)
            pygame.draw.circle(screen, (226, 112, 36), (area.centerx, by), 9)
            screen.fill((60, 24, 8), (area.centerx - 9, by, 18, 1))
            screen.fill((60, 24, 8), (area.centerx, by - 9, 1, 18))

    def _draw_modes(self, screen):
        name = CATEGORIES[self.cat_index][1]
        self.title(screen, "MODO DE JOGO", y=48)
        x = 64 + self.assets.text_width("MODO DE JOGO", theme.M) + 14
        self.ui.text(screen, "›  " + name, theme.M, theme.BRASS, (x, 48), anchor="midleft")
        # abas das modalidades (LB/RB ou Q/E trocam sem voltar)
        x, self.tab_rects = 64, []
        for i, (_, label, color, _) in enumerate(CATEGORIES):
            w = self.assets.text_width(label, theme.XS) + 28
            r = pygame.Rect(x, 84, w, 24)
            self.tab_rects.append(r)
            on = i == self.cat_index
            screen.fill(theme.INK_3 if on else theme.INK_2, r)
            screen.fill(color if on else theme.LINE, (r.x, r.bottom - 3, r.w, 3))
            self.ui.text(screen, label, theme.XS, theme.BRASS if on else theme.MUTED, r.center, shadow=False)
            x += w + 6
        self.ui.keycap(screen, "LB", (x + 10, 96))
        self.ui.keycap(screen, "RB", (x + 44, 96))
        for title, y in self.headers:
            self.ui.text(screen, title, theme.XS, theme.FAINT, (60, y), anchor="midleft", shadow=False)
            w = self.assets.text_width(title, theme.XS)
            screen.fill(theme.LINE, (68 + w, y, 300 - w, 1))
        self.menu.draw(screen, self.ui, self.ticks)

        key = self.menu.value
        desc, players = MODE_TEXT[key] if key != "continue" else self._continue_text()
        # texto comprido: o painel cresce para baixo (até perto do rodapé) em vez de o texto vazar
        lines = len(self.ui.wrap(desc, theme.XS, 484 - 48))
        panel = pygame.Rect(420, 120, 484, max(330, min(self.PANEL_BOTTOM - 120, 250 + lines * 16)))
        self.ui.panel(screen, panel)
        self._illustration(screen, key, pygame.Rect(panel.x + 2, panel.y + 2, panel.w - 4, 170))
        title = ({"continue": "CONTINUAR CAMPANHA", "campaign2": "CAMPANHA: CAPÍTULO 2",
                  "campaign3": "CAMPANHA: CAPÍTULO 3", "campaign4": "CAMPANHA: CAPÍTULO 4",
                  "reuniao": "REUNIÃO DOS CORROMPIDOS", "cinema": "CINEMA",
                  "passeio": "PASSEAR NA CASA"}.get(key) or MODES[key]["title"])
        tr = self.ui.text(screen, title, theme.S, theme.BRASS, (panel.x + 24, panel.y + 196), anchor="topleft")
        pw = self.assets.text_width(players, theme.XS)
        y = panel.y + 232
        if tr is not None and tr.right + 16 + pw > panel.right - 24:
            # título comprido: o número de jogadores desce para a linha de baixo
            self.ui.text(screen, players, theme.XS, theme.MUTED, (panel.x + 24, panel.y + 222), anchor="topleft")
            y += 10
        else:
            self.ui.text(screen, players, theme.XS, theme.MUTED, (panel.right - 24, panel.y + 200), anchor="topright")
        self.ui.paragraph(screen, desc, theme.XS, theme.BONE, (panel.x + 24, y), panel.w - 48, spacing=16,
                          max_height=panel.bottom - 14 - y)
        self.footer(screen, [("↑↓", "ESCOLHER"), ("LB RB", "MODALIDADE"), ("A", "JOGAR"), ("B", "VOLTAR")])

    def _continue_text(self):
        from ..ai import DIFFICULTIES
        from ..campaign import PHASES
        run = self.saved_run
        n = run.players
        desc = (f"Volta pela Casa da turma para a fase {run.phase_index + 1} de {len(PHASES)}: "
                f"{run.phase.name}, dificuldade {DIFFICULTIES[run.session.difficulty]['label']}. As melhorias, as armas "
                "raras e a vida continuam como estavam. Quem jogava pelo celular ou controle precisa estar "
                "conectado antes.")
        return desc, f"{n} JOGADOR" + ("ES" if n > 1 else "")

    def _illustration(self, screen, key, area):
        if key in ("campaign", "continue", "campaign2", "campaign3", "campaign4", "reuniao", "cinema", "passeio"):
            chapter = (self.saved_run.chapter if key == "continue"
                       else {"campaign2": 2, "campaign3": 3, "campaign4": 4, "reuniao": 4}.get(key, 1))
            self._campaign_illustration(screen, area, chapter=chapter,
                                        cover=key if key in ("reuniao", "cinema") else None)
            if key in ("campaign", "cinema", "reuniao"):
                from .. import progress
                from .campaign import SEAL_ORDER, draw_seal
                earned = progress.rush_seals() if key == "reuniao" else progress.seals()
                for i, k in enumerate(SEAL_ORDER):
                    draw_seal(screen, self.ui, (area.x + 22 + i * 34, area.y + 22), k, k in earned, self.ticks, size=14)
            return
        draw_cover(screen, self.assets, key, area, self.ticks)
        sprites = self.assets.sprites
        ground = area.bottom - 22
        if MODES[key].get("penalty"):
            # gol de frente atrás do goleiro
            goal = pygame.Rect(area.centerx + 4, area.y + 30, 112, area.h - 50)
            screen.fill((10, 14, 12), goal.inflate(-4, -4))
            for x in range(goal.x + 8, goal.right, 10):
                screen.fill((150, 156, 166), (x, goal.y + 3, 1, goal.h - 3))
            pygame.draw.rect(screen, (246, 246, 240), goal, 3)
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
            "basket1": [("trovao", "direita", -100), ("cauanzera", "esquerda", 100)],
            "basket2": [("ninja", "direita", -150), ("velocista", "direita", -70),
                        ("pirata", "esquerda", 70), ("tita", "esquerda", 150)],
            "penaltis1": [("aryel", "costas", -60), ("ninja", "frente", 60)],
            "penaltis": [("matador", "costas", -60), ("paredao", "frente", 60)],
            "treino_penaltis": [("ginga", "costas", -60), ("tanque", "frente", 60)],
            "desafio_goleiro": [("trovao", "costas", -60), ("paredao", "frente", 60)],
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
        if MODES[key].get("penalty"):
            pygame.draw.circle(screen, (20, 18, 24), (area.centerx - 20, ground - 6), 9)
            pygame.draw.circle(screen, (238, 236, 228), (area.centerx - 20, ground - 6), 8)
        elif key.startswith("soccer"):
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


    def _campaign_illustration(self, screen, area, chapter=1, cover=None):
        draw_cover(screen, self.assets, cover or f"chapter{chapter}", area, self.ticks)
        sprites = self.assets.sprites
        ground = area.bottom - 22
        step = self.ticks // 4
        if cover == "reuniao":                        # os quatro chefes, um do lado do outro
            cast = [("aryel", "frente", -165, True), ("borba_exo", "frente", -55, True),
                    ("albeguinio_adm", "frente", 55, True), ("cauanzera_ti", "frente", 165, True)]
        elif cover == "cinema":                       # a turma na plateia
            cast = [("aryel", "costas", -150, False), ("borba", "costas", -50, False),
                    ("albeguinio", "costas", 50, False), ("cauanzera", "costas", 150, False)]
        elif chapter == 4:
            cast = [("albeguinio", "direita", -170, False), ("aryel", "direita", -100, False),
                    ("processo", "esquerda", 30, False), ("carimbador", "esquerda", 100, False),
                    ("cauanzera_ti", "esquerda", 180, True)]
        elif chapter == 3:
            cast = [("cauanzera", "direita", -170, False), ("borba", "direita", -100, False),
                    ("mascara_argila", "esquerda", 30, False), ("seringuinha", "esquerda", 100, False),
                    ("albeguinio_adm", "esquerda", 180, True)]
        elif chapter == 2:
            cast = [("borba", "direita", -170, False), ("albeguinio", "direita", -100, False),
                    ("drone", "esquerda", 30, False), ("miliciano", "esquerda", 100, False),
                    ("borba_exo", "esquerda", 180, True)]
        else:
            cast = [("guerreiro", "direita", -170, False), ("geada", "direita", -100, False),
                    ("diabrete", "esquerda", 40, False), ("esqueleto", "esquerda", 110, False),
                    ("aryel", "esquerda", 180, True)]
        for name, direction, dx, shadow in cast:
            sset = self.assets.shadow_sprites(name) if shadow else sprites[name]
            img = sset.frame(direction, step)
            factor = 3 if shadow and cover != "reuniao" else 2
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


def start_mode(game, choice):
    """Monta a sessão do modo e vai para a tela certa (lobby ou escolha de personagem)."""
    chapter = {"campaign2": 2, "campaign3": 3, "campaign4": 4}.get(choice, 1)
    rush = choice == "reuniao"
    walk = choice == "passeio"
    if chapter > 1 or rush or walk:
        choice = "campaign"
    count = MODES[choice]["slots"]
    teams = MODES[choice].get("teams", False) or MODES[choice].get("fill", False)
    training = choice.startswith("treino") or choice == "desafio_goleiro"
    slots = [SlotSetup(s, cpu=(choice == "cpu" and s == 2) or (training and s > 1) or (teams and s > 1))
             for s in range(1, count + 1)]
    if choice == "campaign":
        slots = slots[:1]           # P2 a P4 entram na tela de conexão
    previous = game.session
    game.session = Session(choice, slots, chapter=chapter, rush=rush, walk=walk)
    if previous is not None and MODES[choice].get("teams", False):
        game.session.layout = previous.layout      # mantém a divisão de times escolhida
    from .select import CharSelectScene, LobbyScene
    if choice == "cpu" or training:
        game.change(CharSelectScene(game))
    else:
        game.change(LobbyScene(game))


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
        "FUTEBOL: TOQUE EM CHUTAR = RASTEIRO. SEGURE E SOLTE = PELO ALTO.",
        "PASSE SAI NA HORA E VAI TELEGUIADO PARA QUEM VOCÊ APONTA. NA PONTA, NO 2X2, VIRA CRUZAMENTO.",
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
        if event.type == pygame.KEYDOWN and event.key == pygame.K_c:
            from .pad import PadScene
            self.sfx("confirm", 0.4)
            self.game.change(PadScene(self.game))
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
        rows = list(self.rows())
        # linhas de teclas, dicas e o DUPLO TOQUE dentro do painel: aperta os espaços se precisar
        row_h, tip_h = 21, 15
        room = panel.bottom - 16 - y
        while len(rows) * row_h + 2 + len(self.TIPS) * tip_h + 10 > room and (row_h > 18 or tip_h > 12):
            if row_h > 18:
                row_h -= 1
            else:
                tip_h -= 1
        for label, k1, k2 in rows:
            self.ui.text(screen, label, theme.XS, theme.BONE, (cols[0], y), anchor="midleft", shadow=False)
            self.ui.keycap(screen, k1, (cols[1], y))
            self.ui.keycap(screen, k2, (cols[2], y))
            y += row_h
        y += 2
        for tip in self.TIPS:
            self.ui.text(screen, tip, theme.XS, theme.MUTED, (cols[0], y), anchor="midleft", shadow=False)
            y += tip_h
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
        self.footer(screen, [("K", "TROCAR TECLAS"), ("C / Y", "CONTROLE"), ("T", "DUPLO TOQUE"), ("ESC", "VOLTAR")])


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
        ("vibracao", "VIBRAÇÃO", "CONTROLE E CELULAR (ANDROID)"),
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
            self.game.change(ArchiveScene(self.game))
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
     "CampaignMatch (a sala de luta) e HubMatch (a Casa da turma) herdam de CoopMatch, que junta o que elas "
     "têm em comum, e PhaseMatch (a fase inteira, num mapa só) herda de CampaignMatch (levantar quem caiu, a mira, os itens, o escurecer entre as etapas). TeamBattleMatch "
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


def _big(img, k):
    return pygame.transform.scale(img, (img.get_width() * k, img.get_height() * k))


def _scene_enterrada(screen, ui, rect, t):
    """Um herói enterra com as poses novas: corre, sobe com a bola atrás da cabeça e crava."""
    sprites = ui.assets.sprites["velocista"]
    k = t % 120
    hoop = (rect.right - 70, rect.y + 90)
    screen.fill((120, 80, 50), (rect.x, rect.bottom - 40, rect.w, 40))
    screen.fill(theme.BONE, (hoop[0] + 18, hoop[1] - 50, 6, 70))                   # tabela
    pygame.draw.line(screen, theme.EMBER, (hoop[0] - 22, hoop[1]), (hoop[0] + 18, hoop[1]), 4)
    stretch = 10 if 70 <= k < 82 else 0
    for i in range(5):                                                          # rede
        x = hoop[0] - 20 + i * 9
        pygame.draw.line(screen, theme.BONE, (x, hoop[1]), (hoop[0] - 2 + (i - 2) * 4, hoop[1] + 24 + stretch), 1)
    if k < 40:
        img, x, y = sprites.frame("direita", k // 4), rect.x + 40 + k * 3, rect.bottom - 36
    elif k < 70:
        f = (k - 40) / 30
        img = sprites.pose("direita", "enterrada", 0 if f < 0.7 else 1)
        x, y = rect.x + 160 + f * (hoop[0] - 40 - rect.x - 160), rect.bottom - 36 - math.sin(f * math.pi / 2) * 110
    elif k < 90:
        img, x, y = sprites.pose("direita", "enterrada", 2), hoop[0] - 40, rect.bottom - 146
    else:
        img, x, y = sprites.pose("frente", "comemora", (k // 8) % 2), hoop[0] - 60, rect.bottom - 36
    pygame.draw.ellipse(screen, (0, 0, 0), (x - 20, rect.bottom - 42, 40, 10))
    screen.blit(img, img.get_rect(midbottom=(round(x), round(y))))
    if 70 <= k < 90:
        ui.text(screen, "CRAVOU!", theme.S, theme.BRASS, (rect.centerx - 30, rect.y + 40))


def _scene_futebol(screen, ui, rect, t):
    """Chute com curva: a bola sai aberta e volta para o canto, com assobio e rastro."""
    sprites = ui.assets.sprites["trovao"]
    screen.fill((52, 128, 60), rect)
    goal = pygame.Rect(rect.right - 30, rect.centery - 50, 20, 100)
    pygame.draw.rect(screen, theme.BONE, goal, 2)
    k = t % 110
    kx, ky = rect.x + 60, rect.centery + 30
    img = sprites.pose("direita", "chute", min(2, k // 4)) if k < 16 else sprites.pose("direita", "parado", 0)
    if k > 80:
        img = sprites.pose("frente", "comemora", (k // 8) % 2)
    screen.blit(_big(img, 1), img.get_rect(midbottom=(kx, ky + 20)))
    for i in range(8 if k < 70 else 0):
        f = max(0.0, (min(k, 70) - i * 2) / 70)
        x = kx + 20 + f * (goal.x - kx - 14)
        y = ky - math.sin(f * math.pi) * 70 + f * (goal.y + 20 - ky)
        pygame.draw.circle(screen, (240, 220, 160) if i else (240, 240, 236), (round(x), round(y)), 5 if not i else 3)
    if k >= 70:
        ui.text(screen, "NO ÂNGULO!", theme.S, theme.BRASS, rect.center)
    ui.text(screen, "CURVA", theme.XS, theme.BONE, (kx + 40, rect.y + 24))


def _scene_penalti(screen, ui, rect, t):
    """A disputa de frente: o goleiro pula, a bola cresce vindo para a tela e a rede estufa."""
    keeper = ui.assets.sprites["paredao"]
    kicker = ui.assets.sprites["matador"]
    screen.fill((34, 30, 48), (rect.x, rect.y, rect.w, rect.h // 2))
    screen.fill((60, 140, 68), (rect.x, rect.centery, rect.w, rect.h // 2))
    goal = pygame.Rect(rect.centerx - 110, rect.y + 40, 220, rect.h // 2 - 40)
    for x in range(goal.x + 6, goal.right, 10):
        screen.fill((150, 156, 166), (x, goal.y, 1, goal.h))
    pygame.draw.rect(screen, (246, 246, 240), goal, 4)
    k = t % 140
    side = 1 if (t // 140) % 2 else -1
    if k < 50:
        img = keeper.pose("frente", "parado", (k // 20) % 2)
        screen.blit(img, img.get_rect(midbottom=(goal.centerx, goal.bottom)))
    else:
        f = min(1.0, (k - 50) / 14)
        img = pygame.transform.rotate(keeper.pose("frente", "esquiva", 0), 70 * f * -side)
        screen.blit(img, img.get_rect(center=(goal.centerx + side * 60 * f, goal.bottom - 30 - 10 * f)))
    if 50 <= k < 70:
        f = (k - 50) / 20
        bx, by = rect.centerx + (-side * 80) * f, rect.bottom - 40 + (goal.y + 30 - rect.bottom + 40) * f
        pygame.draw.circle(screen, (240, 240, 236), (round(bx), round(by)), round(9 - 4 * f))
    elif k >= 70:
        pygame.draw.circle(screen, (240, 240, 236), (goal.centerx - side * 80, goal.y + 30), 5)
        ui.text(screen, "GOOOL!", theme.M, theme.BRASS, (rect.centerx, rect.y + 20))
    kimg = _big(kicker.pose("costas", "chute" if 44 <= k < 60 else "parado", min(2, max(0, (k - 44) // 4))), 2)
    screen.blit(kimg, kimg.get_rect(midbottom=(rect.centerx - 60, rect.bottom + 6)))


def _scene_disputa(screen, ui, rect, t):
    """O placar da disputa em bolinhas e a pressão da cobrança decisiva."""
    beat = (math.sin(t * 0.2) + 1) / 2
    for team in (0, 1):
        y = rect.y + 50 + team * 26
        screen.fill(theme.TEAM_COLORS[team], (rect.x + 40, y - 6, 12, 12))
        marks = (1, 1, 0, 1, 1) if team == 0 else (1, 0, 1, 1)
        for i in range(5):
            r = marks[i] if i < len(marks) else None
            if team == 1 and i == 4 and (t // 30) % 2:
                r = 1 if (t // 60) % 2 else 0
            c = theme.MOSS if r == 1 else theme.BLOOD if r == 0 else (60, 56, 76)
            pygame.draw.circle(screen, c, (rect.x + 80 + i * 24, y), 8)
    hx, hy, r = rect.centerx, rect.y + 150, 14 + round(beat * 4)
    for dx in (-r * 0.75, r * 0.75):
        pygame.draw.circle(screen, (220, 40, 50), (round(hx + dx), hy), r)
    pygame.draw.polygon(screen, (220, 40, 50), [(hx - r * 1.7, hy + 4), (hx + r * 1.7, hy + 4), (hx, hy + r * 2.2)])
    ui.text(screen, "COBRANÇA DECISIVA", theme.XS, theme.BONE, (rect.centerx, rect.bottom - 40))
    paper = pygame.Rect(rect.right - 120, rect.y + 20, 100, 70)
    screen.fill((236, 228, 196), paper)
    ui.text(screen, "COLINHA", theme.XS, theme.INK, (paper.centerx, paper.y + 12), shadow=False)
    ui.text(screen, "DIR. ALTO", theme.XS, (170, 40, 40), (paper.centerx, paper.y + 34), shadow=False)
    ui.text(screen, "ESQ.", theme.XS, (170, 40, 40), (paper.centerx, paper.y + 52), shadow=False)


def _scene_lag(screen, ui, rect, t):
    """O prédio da Lag Lobby à noite: um drone mergulha pela linha vermelha e a patrulha atira."""
    screen.fill((22, 24, 34), rect)
    tower = pygame.Rect(rect.centerx - 60, rect.y + 20, 120, rect.h - 60)
    screen.fill((40, 46, 60), tower)
    for gy in range(tower.y + 10, tower.bottom - 10, 16):
        for gx in range(tower.x + 10, tower.right - 10, 20):
            lit = (gx * 7 + gy * 3 + t // 30) % 5 == 0
            screen.fill((120, 220, 240) if lit else (30, 60, 80), (gx, gy, 12, 8))
    ui.text(screen, "LAG LOBBY", theme.XS, (120, 220, 240), (tower.centerx, tower.y + 4))
    screen.fill((50, 52, 58), (rect.x, rect.bottom - 40, rect.w, 40))
    patrol = ui.assets.sprites.get("miliciano")
    drone = ui.assets.sprites.get("drone")
    k = t % 120
    hero = ui.assets.sprites["guerreiro"]
    hx, hy = rect.x + 60, rect.bottom - 14
    if patrol:
        img = patrol.frame("esquerda", 0)
        screen.blit(img, img.get_rect(midbottom=(rect.right - 50, rect.bottom - 14)))
        if k % 40 < 12 and (k // 4) % 2:
            screen.fill((255, 230, 140), (rect.right - 80 - (k % 40) * 8, rect.bottom - 40, 6, 2))
    if drone:
        start = (rect.right - 90, rect.y + 60)
        if k < 50:
            pygame.draw.line(screen, (255, 60, 70), start, (hx, hy - 20), 1)
            pos = start
        else:
            f = min(1.0, (k - 50) / 14)
            pos = (start[0] + (hx - start[0]) * f, start[1] + (hy - 20 - start[1]) * f)
        img = drone.frame("esquerda", (t // 4) % 2)
        screen.blit(img, img.get_rect(center=(round(pos[0]), round(pos[1]))))
    img = hero.frame("direita", 0) if k < 60 else hero.pose("direita", "esquiva", 0)
    screen.blit(img, img.get_rect(midbottom=(hx - (20 if k >= 60 else 0), hy)))


def _scene_perigos(screen, ui, rect, t):
    """Corredor de servidores: a linha pontilhada avisa e depois o laser queima."""
    screen.fill((34, 38, 50), rect)
    for x in range(rect.x + 10, rect.right, 70):
        screen.fill((20, 22, 30), (x, rect.y, 30, rect.h))
        for y in range(rect.y + 6, rect.bottom, 10):
            screen.fill((60, 200, 120) if (x + y + t // 6) % 3 else (230, 80, 80), (x + 4, y, 3, 2))
    k = t % 100
    y = rect.centery
    if k < 60:
        if (k // 5) % 2 == 0 or k > 45:
            for x in range(rect.x, rect.right, 16):
                screen.fill((255, 54, 70), (x, y - 1, 10, 2))
        ui.text(screen, "AVISO", theme.XS, (255, 120, 130), (rect.centerx, y - 30))
    elif k < 84:
        w = round(18 * (1 - (k - 60) / 48))
        pygame.draw.line(screen, (120, 20, 34), (rect.x, y), (rect.right, y), w + 6)
        pygame.draw.line(screen, (255, 54, 70), (rect.x, y), (rect.right, y), w)
        pygame.draw.line(screen, (255, 220, 226), (rect.x, y), (rect.right, y), max(1, w // 3))
    hero = ui.assets.sprites["atirador"]
    img = hero.frame("direita", (t // 6) % 4)
    screen.blit(img, img.get_rect(midbottom=(rect.x + 70, y + 60)))
    for i in range(6):                                           # vento soprando embaixo
        x = (rect.x + (t * 6 + i * 57) % rect.w)
        screen.fill((220, 232, 240), (x, rect.bottom - 30 + (i % 3) * 8, 18, 1))


def _scene_chefao_lag(screen, ui, rect, t):
    """Borba Jr Corrompido: a linha azul do Canhão de Pulso cresce e o tiro grande sai."""
    screen.fill((60, 64, 72), rect)
    screen.fill((90, 94, 100), (rect.x, rect.bottom - 60, rect.w, 60))
    boss = ui.assets.shadow_sprites("borba_exo")
    k = t % 130
    bx, by = rect.x + 90, rect.bottom - 30
    tired = k >= 100
    img = boss.frame("direita", 0) if not tired else boss.pose("direita", "dano", 0)
    big = _big(img, 2)
    screen.blit(big, big.get_rect(midbottom=(bx, by)))
    if k < 56:
        length = round((rect.right - bx) * k / 56)
        pygame.draw.line(screen, (90, 170, 255), (bx + 30, by - 50), (bx + 30 + length, by - 50), 2)
    elif k < 80:
        x = bx + 30 + (k - 56) * 12
        pygame.draw.circle(screen, (90, 170, 255), (x, by - 50), 12)
        pygame.draw.circle(screen, (230, 245, 255), (x, by - 50), 5)
    if tired:
        for i in range(5):
            screen.fill((210, 210, 230), (bx - 20 + i * 10, by - 110 - (k - 100 + i * 5) % 30, 4, 4))
        ui.text(screen, "SUPERAQUECIDO!", theme.XS, theme.BRASS, (rect.centerx + 40, rect.y + 30))


def _scene_armas_lag(screen, ui, rect, t):
    """As armas novas da Lag Lobby girando na vitrine."""
    from .. import weapon_art
    names = ("Taser de Rede", "Rifle de Plasma", "Drone de Bolso", "Teclado Mecânico", "Escudo de Choque",
             "Manopla do Exo")
    pick = (t // 50) % len(names)
    for i, name in enumerate(names):
        cell = pygame.Rect(rect.x + 20 + (i % 3) * 102, rect.y + 30 + (i // 3) * 100, 92, 84)
        on = i == pick
        screen.fill(theme.INK_3 if on else theme.INK_2, cell)
        pygame.draw.rect(screen, (120, 220, 240) if on else theme.LINE, cell, 1)
        img = weapon_art.icon(name)
        if img is not None:
            img = weapon_art.icon2x(name) if img.get_width() < 40 else img
            bob = round(math.sin(t * 0.1) * 3) if on else 0
            screen.blit(img, img.get_rect(center=(cell.centerx, cell.centery - 8 + bob)))
    ui.text(screen, names[pick].upper(), theme.XS, theme.BRASS, (rect.centerx, rect.bottom - 22))


def _scene_bate(screen, ui, rect, t):
    """O chute novo do pênalti: apoio, perna atrás, o pé na bola (que amassa) e a perna seguindo."""
    from .penalty import PenaltyScene
    ball = PenaltyScene._draw_mini_ball
    sprites = ui.assets.kit_sprites("matador", 0)
    screen.fill((52, 128, 60), rect)
    for y in range(rect.y, rect.bottom, 24):
        screen.fill((58, 138, 66), (rect.x, y, rect.w, 12))
    k = t % 90
    frame = 0 if k < 20 else 1 if k < 34 else 2 if k < 46 else 3
    img = _big(sprites.pose("costas", "bate", frame), 2)
    foot = (rect.centerx - 40, rect.bottom - 20)
    bx, by = rect.centerx + 6, rect.bottom - 64
    if k < 46:
        pygame.draw.ellipse(screen, (30, 70, 34), (bx - 22, by + 14, 44, 12))
        ball(screen, bx + (3 if 34 <= k < 46 else 0), by, 22, squash=0.25 if 34 <= k < 46 else 0.0)
    else:
        f = min(1.0, (k - 46) / 30)
        ball(screen, bx + 60 * f, by - 120 * f, 22 - 11 * f, spin=k * 0.4)
    pygame.draw.ellipse(screen, (30, 70, 34), (foot[0] - 40, foot[1] - 8, 80, 16))
    screen.blit(img, img.get_rect(midbottom=foot))
    if 34 <= k < 40:
        ui.text(screen, "TUM!", theme.S, theme.BRASS, (bx + 40, by - 40))


def _scene_agarra(screen, ui, rect, t):
    """O goleiro novo: quica, se estica, agarra a bola, cai abraçado e levanta com ela no alto."""
    from .penalty import PenaltyScene
    ball = PenaltyScene._draw_mini_ball
    sprites = ui.assets.kit_sprites("paredao", 1)
    screen.fill((52, 128, 60), (rect.x, rect.centery + 40, rect.w, rect.h))
    screen.fill((34, 30, 48), (rect.x, rect.y, rect.w, rect.h // 2 + 40))
    goal = pygame.Rect(rect.x + 20, rect.y + 40, rect.w - 40, rect.h // 2)
    for x in range(goal.x + 6, goal.right, 10):
        screen.fill((150, 156, 166), (x, goal.y, 1, goal.h))
    pygame.draw.rect(screen, (246, 246, 240), goal, 4)
    ground = goal.bottom
    k = t % 150
    cx = goal.centerx
    tx, ty = goal.right - 50, goal.y + 50
    if k < 30:
        img = _big(sprites.pose("frente", "espera", (k // 10) % 2), 2)
        screen.blit(img, img.get_rect(midbottom=(cx, ground)))
        ball(screen, cx - 30 + k * 0, rect.bottom - 30, 18)
        return
    if k < 46:
        f = (k - 30) / 16
        img = pygame.transform.rotate(_big(sprites.pose("frente", "mergulho", 0), 2), -85 * f)
        x, y = cx + (tx - cx) * f, ground - 60 + (ty - ground + 60) * f
        screen.blit(img, img.get_rect(center=(x, y)))
        bf = f
        ball(screen, cx + (tx + 20 - cx) * bf, rect.bottom - 30 + (ty - rect.bottom + 30) * bf, 18 - 7 * bf, spin=k * 0.3)
        return
    if k < 100:
        f = min(1.0, (k - 46) / 16)
        img = pygame.transform.rotate(_big(sprites.pose("frente", "mergulho", 1), 2), -85 - 5 * f)
        x, y = tx, ty + (ground - 24 - ty) * f * f
        screen.blit(img, img.get_rect(center=(x, y)))
        ball(screen, x - 4, y, 11, spin=1)
        if k < 60:
            ui.text(screen, "AGARROU!", theme.S, theme.BRASS, (rect.centerx, rect.y + 20))
        return
    img = _big(sprites.pose("frente", "comemora", (k // 10) % 2), 2)
    screen.blit(img, img.get_rect(midbottom=(tx - 20, ground)))
    ball(screen, tx - 20, ground - img.get_height() - 12, 11, spin=2)



def _scene_modos(screen, ui, rect, t):
    """Os quatro cartões das modalidades, um de cada vez aceso."""
    names = ("CAMPANHA", "DUELOS", "FUTEBOL", "BASQUETE")
    colors = (theme.BRASS, theme.SLOT_COLORS[2], theme.TEAM_COLORS[0], theme.TEAM_COLORS[1])
    hot = (t // 45) % 4
    w, gap = 74, 6
    x0 = rect.centerx - (4 * w + 3 * gap) // 2
    for i, (name, color) in enumerate(zip(names, colors)):
        card = pygame.Rect(x0 + i * (w + gap), rect.centery - 50 - (6 if i == hot else 0), w, 92)
        ui.panel(screen, card, fill=theme.INK_3 if i == hot else theme.INK_2, shadow=False)
        screen.fill(color if i == hot else theme.LINE, (card.x, card.y, card.w, 4))
        pygame.draw.circle(screen, color, (card.centerx, card.y + 38), 13 if i == hot else 10)
        ui.text(screen, name[:8], theme.XS, theme.BONE if i == hot else theme.MUTED, (card.centerx, card.bottom - 16),
                shadow=False)


def _scene_controle(screen, ui, rect, t):
    """O controle desenhado com um botão aceso por vez, como na tela CONTROLE."""
    from ..pad_art import draw_pad
    order = ("a", "b", "x", "y", "rb", "rt", "lb", "lt")
    fam = ("xbox", "playstation", "nintendo")[(t // 160) % 3]
    draw_pad(screen, ui, fam, (rect.centerx, rect.centery + 4), 2, lit=order[(t // 20) % len(order)],
             pulse=(t % 20) / 20)


def _scene_coroa(screen, ui, rect, t):
    """A coroa do P1 e o painel da partida abrindo."""
    from .base import crown
    k = min(1.0, (t % 150) / 40)
    box = pygame.Rect(0, 0, round(190 * k) or 1, 118)
    box.center = (rect.centerx, rect.centery + 6)
    ui.panel(screen, box, fill=theme.INK_2, shadow=False)
    if k >= 1:
        crown(screen, box.x + 18, box.y + 16)
        ui.text(screen, "PAINEL DA PARTIDA", theme.XS, theme.BRASS, (box.x + 32, box.y + 16), anchor="midleft",
                shadow=False)
        for i, label in enumerate(("CONTINUAR", "REGRAS", "SOM E TELA")):
            row = pygame.Rect(box.x + 10, box.y + 34 + i * 26, box.w - 20, 22)
            hot = i == (t // 30) % 3
            screen.fill(theme.INK if hot else theme.INK_2, row)
            if hot:
                screen.fill(theme.BRASS, (row.x, row.y, 3, row.h))
            ui.text(screen, label, theme.XS, theme.BONE if hot else theme.MUTED, (row.x + 12, row.centery),
                    anchor="midleft", shadow=False)



def _scene_ultra(screen, ui, rect, t):
    """Um herói na quadra com os quatro orbes girando em volta e a barra de ULTRA enchendo:
    cheia, ele brilha e comemora."""
    from ..basket_ultra import ORB_ORDER, ORBS
    sprites = ui.assets.sprites["trovao"]
    k = (t % 180) / 120
    full = k >= 1
    floor = rect.bottom - 64
    screen.fill((120, 80, 50), (rect.x, floor, rect.w, rect.bottom - floor))
    pygame.draw.line(screen, (150, 104, 68), (rect.x, floor), (rect.right - 1, floor), 2)
    hero = (rect.centerx, floor + 10)
    orbit = (rect.centerx, hero[1] - 62)
    orbs = []
    for i, kind in enumerate(ORB_ORDER):
        a = t * 0.03 + i * math.pi / 2
        orbs.append((math.sin(a), round(orbit[0] + math.cos(a) * 125), round(orbit[1] + math.sin(a) * 30), kind))

    def draw_orb(x, y, kind):
        color = ORBS[kind][1]
        pygame.draw.circle(screen, (20, 18, 24), (x, y), 13)
        pygame.draw.circle(screen, color, (x, y), 12)
        pygame.draw.circle(screen, (255, 255, 255), (x - 4, y - 4), 3)

    for i, kind in enumerate(ORB_ORDER):                # legenda fixa no alto: o nome de cada orbe
        x = rect.x + 14 + (rect.w - 28) * i // 4
        pygame.draw.circle(screen, ORBS[kind][1], (x + 6, rect.y + 20), 6)
        ui.text(screen, ORBS[kind][0], theme.XS, theme.BONE, (x + 18, rect.y + 20), anchor="midleft", shadow=False)

    for depth, x, y, kind in sorted(orbs):
        if depth < 0:
            draw_orb(x, y, kind)                       # os de trás passam atrás do herói
    pygame.draw.ellipse(screen, (0, 0, 0), (hero[0] - 40, hero[1] - 8, 80, 14))
    if full:
        glow = pygame.Surface((170, 190), pygame.SRCALPHA)
        alpha = 70 + 40 * ((t // 6) % 2)
        pygame.draw.ellipse(glow, (255, 236, 140, alpha), glow.get_rect())
        screen.blit(glow, glow.get_rect(midbottom=(hero[0], hero[1] + 8)))
        img = sprites.pose("frente", "comemora", (t // 8) % 2)
    else:
        img = sprites.frame("frente", 0)
    img = pygame.transform.scale(img, (img.get_width() * 2, img.get_height() * 2))
    screen.blit(img, img.get_rect(midbottom=hero))
    for depth, x, y, kind in sorted(orbs):
        if depth >= 0:
            draw_orb(x, y, kind)
    bar = pygame.Rect(0, 0, 220, 14)
    bar.midbottom = (rect.centerx, rect.bottom - 14)
    screen.fill(theme.INK, bar)
    fill = bar.inflate(-4, -4)
    fill.w = round(fill.w * min(1.0, k))
    screen.fill((255, 236, 140) if full and (t // 6) % 2 else theme.EMBER, fill)
    ui.text(screen, "ULTRA PRONTO: APERTE SUPER!" if full else "ULTRA", theme.XS,
            theme.BRASS if full else theme.BONE, (bar.centerx, bar.y - 12), shadow=False)


def _scene_clepalovers(screen, ui, rect, t):
    """Easter egg do capítulo 3: o letreiro rosa da clínica piscando no escuro e um caco roxo."""
    screen.fill((14, 10, 20), rect)
    for i in range(0, rect.w, 46):                                           # prédios no escuro
        h = 70 + (i * 37) % 60
        screen.fill((24, 18, 32), (rect.x + i, rect.bottom - h, 40, h))
    sign = pygame.Rect(0, 0, ui.assets.text_width("CLEPALOVERS", theme.M) + 36, 54)
    sign.center = (rect.centerx, rect.y + 70)
    flicker = (t // 4) % 23 not in (0, 2) and (t // 90) % 5 != 3
    pink = (255, 110, 190) if flicker else (90, 40, 70)
    pygame.draw.rect(screen, (30, 14, 28), sign)
    pygame.draw.rect(screen, pink, sign, 2)
    ui.text(screen, "CLEPALOVERS", theme.M, pink, sign.center, shadow=False)
    ui.text(screen, "CLÍNICA DE ESTÉTICA", theme.XS, (200, 150, 180) if flicker else (70, 40, 60),
            (sign.centerx, sign.bottom + 12), shadow=False)
    door = pygame.Rect(0, 0, 60, 80)
    door.midbottom = (rect.centerx, rect.bottom - 10)
    screen.fill((40, 22, 40), door)
    pulse = 4 + int(2 * abs(math.sin(t * 0.08)))
    shard = [(door.centerx, door.centery - 14 - pulse), (door.centerx + 8, door.centery),
             (door.centerx, door.centery + 12 + pulse // 2), (door.centerx - 7, door.centery)]
    pygame.draw.polygon(screen, (170, 90, 240), shard)
    pygame.draw.polygon(screen, (230, 200, 255), shard, 1)


def _scene_clinica(screen, ui, rect, t):
    """Capítulo 3: a sala de espera da Clepalovers, com a máscara de argila pulando e a seringuinha."""
    screen.fill((236, 214, 226), rect)
    for x in range(rect.x, rect.right, 32):
        screen.fill((246, 228, 238), (x, rect.y, 1, rect.h))
    panel = pygame.Rect(0, 0, 200, 30)
    panel.midtop = (rect.centerx, rect.y + 12)
    screen.fill((24, 14, 22), panel)
    lit = (t // 60) % 3 == 0 and (t // 6) % 2
    pygame.draw.rect(screen, (255, 110, 190), panel, 2)
    ui.text(screen, f"SENHA {40 + (t // 180) % 9:03d} · SALA 3", theme.XS, (255, 236, 120) if lit else (255, 170, 210),
            panel.center, shadow=False)
    ground = rect.bottom - 20
    sprites = ui.assets.sprites
    cast = [("guerreiro", "direita", rect.x + 70, 0), ("geada", "direita", rect.x + 130, 0),
            ("mascara_argila", "esquerda", rect.right - 160, abs(math.sin(t * 0.12)) * 16),
            ("seringuinha", "esquerda", rect.right - 90, 0)]
    for name, direction, x, hop in cast:
        sset = sprites.get(name)
        if sset is None:
            continue
        img = sset.frame(direction, t // 6)
        img = pygame.transform.scale(img, (img.get_width() * 2, img.get_height() * 2))
        pygame.draw.ellipse(screen, (180, 150, 170), (x - 24, ground - 6, 48, 10))
        screen.blit(img, img.get_rect(midbottom=(x, ground + 2 - round(hop))))


def _scene_oi_sumido(screen, ui, rect, t):
    """A Daiwone digitando e o balão do "oi sumido" tapando a tela de um herói."""
    screen.fill((40, 24, 40), rect)
    ground = rect.bottom - 20
    sprites = ui.assets.sprites
    hero = sprites.get("borba")
    k = t % 180
    if hero:
        img = hero.frame("direita", t // 6)
        img = pygame.transform.scale(img, (img.get_width() * 2, img.get_height() * 2))
        screen.blit(img, img.get_rect(midbottom=(rect.x + 120, ground)))
    dw = sprites.get("daiwone")
    if dw:
        img = dw.frame("esquerda", 0)
        img = pygame.transform.scale(img, (img.get_width() * 2, img.get_height() * 2))
        screen.blit(img, img.get_rect(midbottom=(rect.right - 110, ground)))
        if k < 80 and (t // 10) % 2:
            ui.text(screen, "DIGITANDO...", theme.XS, (255, 192, 226), (rect.right - 110, ground - 70), shadow=False)
    if 80 <= k < 160:
        box = pygame.Rect(0, 0, 220, 80)
        box.midbottom = (rect.x + 130, ground - 50)
        pygame.draw.rect(screen, (250, 248, 252), box, border_radius=14)
        pygame.draw.rect(screen, (255, 110, 190), box, 3, border_radius=14)
        ui.text(screen, "DAIWONE", theme.XS, (184, 56, 128), (box.x + 16, box.y + 16), anchor="midleft", shadow=False)
        ui.text(screen, "oi sumido", theme.S, (40, 30, 44), (box.centerx, box.y + 50), shadow=False)


def _scene_mansao(screen, ui, rect, t):
    """Capítulo 4: a fachada da Mansão do Carimbo no sol de Cuiabrasa, com o termômetro a 47°C."""
    screen.fill((250, 196, 120), rect)
    sun = (rect.right - 60, rect.y + 40)
    pygame.draw.circle(screen, (255, 236, 150), sun, 26 + int(3 * math.sin(t * 0.08)))
    for k in range(0, rect.w, 18):                                             # calor subindo do chão
        y = rect.bottom - 30 - (t + k * 7) % 40
        screen.fill((255, 220, 160), (rect.x + k, y, 6, 2))
    house = pygame.Rect(0, 0, 260, 110)
    house.midbottom = (rect.centerx, rect.bottom - 18)
    screen.fill((236, 226, 206), house)
    pygame.draw.polygon(screen, (176, 96, 70), [(house.x - 14, house.y), (house.centerx, house.y - 40),
                                                (house.right + 14, house.y)])
    for i in range(5):                                                         # colunas
        screen.fill((250, 244, 230), (house.x + 18 + i * 52, house.y + 6, 12, house.h - 6))
    sign = pygame.Rect(0, 0, ui.assets.text_width("MANSÃO DO CARIMBO", theme.XS) + 16, 20)
    sign.center = (house.centerx, house.y - 12)
    screen.fill((40, 92, 168), sign)
    ui.text(screen, "MANSÃO DO CARIMBO", theme.XS, (246, 244, 236), sign.center, shadow=False)
    ui.text(screen, "47°C", theme.S, (200, 50, 30) if (t // 20) % 2 else (240, 90, 40),
            (rect.x + 46, rect.y + 30), shadow=False)
    imp = ui.assets.sprites.get("carimbador")
    if imp is not None:
        img = imp.frame("esquerda", t // 8)
        screen.blit(img, img.get_rect(midbottom=(house.right + 40, rect.bottom - 14 - abs(math.sin(t * 0.1)) * 10)))


def _scene_iara(screen, ui, rect, t):
    """A IARA de água-viva flutuando e a tomada: o golpe final do capítulo 4."""
    screen.fill((10, 14, 26), rect)
    for k in range(0, rect.w, 40):                                             # racks do CPD
        screen.fill((24, 32, 48), (rect.x + k + 4, rect.y + 20, 30, rect.h - 40))
        if (t // 7 + k) % 5:
            screen.fill((60, 230, 255), (rect.x + k + 10, rect.y + 30 + (k * 3) % 50, 4, 2))
    iara = ui.assets.sprites.get("iara_nucleo")
    if iara is not None:
        img = iara.frame("frente", t // 10)
        screen.blit(img, img.get_rect(midbottom=(rect.centerx - 40, rect.bottom - 30 + round(math.sin(t * 0.06) * 8))))
    plug = pygame.Rect(0, 0, 34, 44)
    plug.midbottom = (rect.right - 90, rect.bottom - 26)
    screen.fill((230, 230, 222), plug)
    for dx in (-6, 6):                                                         # os furos da tomada
        screen.fill((40, 40, 46), (plug.centerx + dx - 2, plug.centery - 4, 4, 8))
    pulled = (t % 240) > 170
    pygame.draw.line(screen, (170, 90, 240), (rect.centerx - 10, rect.bottom - 60),
                     (plug.centerx, plug.y + (-30 if pulled else 18)), 3)
    if pulled:
        ui.text(screen, "TIROU DA TOMADA!", theme.XS, (140, 220, 120), (plug.centerx, plug.y - 46), shadow=False)


def _scene_casa(screen, ui, rect, t):
    """Hub: a sala da Casa da turma, com o livro do Cauanzera e um herói da vitrine falando."""
    from .. import casa, casa_art
    casa_art.use(ui.assets)
    screen.fill((96, 62, 38), rect)
    for y in range(rect.y, rect.bottom, 16):                                   # tábuas
        off = (y * 37) % 50
        for x in range(rect.x - off, rect.right, 70):
            screen.fill((104 + (x * 7 + y) % 13 - 6, 68, 42), (x, y, 66, 14))
        screen.fill((66, 42, 26), (rect.x, y + 14, rect.w, 2))
    screen.fill((70, 96, 74), (rect.x, rect.y, rect.w, 34))                   # parede
    screen.fill((122, 80, 48), (rect.x, rect.y + 22, rect.w, 12))
    book = casa._bake(casa_art.lectern_book)
    bx, by = rect.x + 90, rect.y + 150
    screen.blit(book.image, (bx + book.dx, by + book.dy))
    ref = casa.VERSES[(t // 90) % len(casa.VERSES)][0]
    ui.text(screen, ref, theme.XS, theme.BRASS, (bx, by - 50))
    key = ("cauanzera", "aryel", "albeguinio", "borba")[(t // 120) % 4]
    hero = casa._bake(casa_art.mannequin, key)
    hx, hy = rect.x + 250, rect.y + 200
    screen.blit(hero.image, (hx + hero.dx, hy + hero.dy))
    line = casa.FALAS[key][(t // 480) % 5]
    casa.draw_bubble(screen, ui, ui.assets, line, hx, hy - 96)


def _scene_computador(screen, ui, rect, t):
    """O terminal do CAUANZERA OS digitando ``liberar --tudo`` e a barra enchendo, e o notebook do
    Albeguinio do lado com a chuva verde."""
    from .. import computador
    pc = pygame.Rect(rect.x + 12, rect.y + 16, 200, 150)
    pygame.draw.rect(screen, (30, 30, 36), pc.inflate(10, 10))
    screen.fill((12, 12, 14), pc)
    screen.fill((40, 70, 120), (pc.x, pc.y, pc.w, 14))
    ui.text(screen, "TERMINAL", theme.XS, (255, 255, 255), (pc.x + 6, pc.y + 7), anchor="midleft", shadow=False)
    k = t % 300
    command = "liberar --tudo"
    typed = command[:max(0, min(len(command), (k - 10) // 4))]
    lines = [("C:\\> " + typed, (200, 200, 200))]
    if k > 80:
        lines.append(("  CONTINUAR? (S/N) S", computador.AMBER))
    for i, label in enumerate(("CAPÍTULOS", "CORROMPIDOS", "PORTAS")):
        n = max(0, min(10, (k - 100 - i * 40) // 4))
        if k > 100 + i * 40:
            lines.append((f"  [{'#' * n}{'-' * (10 - n)}] {label}", computador.HK))
    if k > 240:
        lines.append(("  TUDO LIBERADO.", computador.HK_L))
    for i, (text, color) in enumerate(lines):
        ui.text(screen, text, theme.XS, color, (pc.x + 6, pc.y + 26 + i * 15), anchor="midleft", shadow=False)
    pygame.draw.rect(screen, (60, 60, 70), (pc.centerx - 20, pc.bottom + 5, 40, 14))
    nb = pygame.Rect(rect.right - 132, rect.y + 120, 116, 74)
    pygame.draw.rect(screen, (34, 34, 42), nb.inflate(8, 8))
    screen.fill((2, 8, 4), nb)
    for col in range(nb.x + 6, nb.right - 4, 12):
        head = nb.y + (col * 7 + t * 2) % (nb.h + 40) - 20
        for j in range(5):
            y = head - j * 10
            if nb.y + 2 < y < nb.bottom - 6:
                ui.text(screen, "01AB"[(col + j) % 4], theme.XS, (180, 255, 190) if j == 0 else (40, 160 - j * 20, 60),
                        (col, y), shadow=False)
    if (t // 40) % 2:
        ui.text(screen, "oi sumido", theme.XS, computador.PINK, nb.center, shadow=False)
    screen.fill((60, 60, 70), (nb.x - 14, nb.bottom + 4, nb.w + 28, 8))
    if k > 250:
        from .campaign import draw_crystal
        draw_crystal(screen, (rect.x + 260, rect.y + 60), 30, t)


def _scene_cantos(screen, ui, rect, t):
    """A moto do Aryel dando grau, a roleta girando e a senha da padaria."""
    from .. import casa, casa_art
    casa_art.use(ui.assets)
    screen.fill((96, 62, 38), rect)
    for y in range(rect.y, rect.bottom, 16):
        screen.fill((66, 42, 26), (rect.x, y + 14, rect.w, 2))
    moto = casa._bake(casa_art.moto, ground=False)
    k = t % 160
    up = min(1.0, k / 14) * min(1.0, max(0, 120 - k) / 16) if k < 120 else 0
    angle = up * (24 + 4 * math.sin(k * 0.3))
    mx, my = rect.x + 110, rect.y + 92
    screen.blit(*casa.wheelie(moto, mx, my, angle))
    if angle > 5:
        ui.text(screen, "GRAU!", theme.S, (240, 150, 60), (mx, rect.y + 20))
        for j in range(4):
            pygame.draw.circle(screen, (170, 170, 176), (mx - 70 - j * 10 - (t * 2 + j * 7) % 14, my - 14 - j * 3), 5 - j)
    table = casa._bake(casa_art.roulette_table)
    rx, ry = rect.x + 270, rect.y + 70
    screen.blit(table.image, (rx + table.dx, ry + table.dy))
    spin = (t % 200)
    off = sum(max(0.0, 0.5 * 0.97 ** f) for f in range(min(spin, 150)))
    step = math.tau / 12
    for j in range(12):
        a0 = off + j * step
        pygame.draw.polygon(screen, (50, 170, 80) if j % 2 == 0 else (200, 50, 50),
                            [(rx, ry - 8), (rx + math.cos(a0) * 22, ry - 8 + math.sin(a0) * 10),
                             (rx + math.cos(a0 + step) * 22, ry - 8 + math.sin(a0 + step) * 10)])
    if spin > 150:
        ui.text(screen, "GREEN!" if (t // 200) % 2 == 0 else "RED...", theme.XS,
                (60, 220, 100) if (t // 200) % 2 == 0 else (240, 70, 70), (rx, ry - 40))
    bakery = casa._bake(casa_art.bakery)
    bx, by = rect.x + 20, rect.y + 196
    screen.blit(bakery.image, (bx + bakery.dx, by + bakery.dy))
    ticket = (t // 120) % 99 + 1
    ui.text(screen, f"SENHA {ticket:03d}" if (t % 120) < 60 else "PÃO SAINDO!", theme.XS, theme.BONE,
            (rect.x + 290, by - 40))


def _scene_mapa_fase(screen, ui, rect, t):
    """O mini mapa da fase em tamanho grande: o grupo passa de sala em sala e as salas acendem."""
    from .. import mapa_fase
    from ..campaign import PHASES
    layout = mapa_fase.PhaseLayout.of(PHASES[0])
    route = ("abertura", "luta1", "abertura", "luta2", "recompensa", "luta2", "abertura", "final")
    step = (t // 70) % (len(route) + 1)
    here = route[min(step, len(route) - 1)]
    visited = set(route[:step + 1])
    mini = pygame.Surface((mapa_fase.MINI_W, mapa_fase.MINI_H), pygame.SRCALPHA)
    mapa_fase.draw_minimap(mini, ui, layout, visited, here, mini.get_rect(), portal=step >= len(route))
    screen.fill((14, 14, 22), rect)
    k = min((rect.w - 40) / mini.get_width(), (rect.h - 50) / mini.get_height())
    big = pygame.transform.scale(mini, (round(mini.get_width() * k), round(mini.get_height() * k)))
    screen.blit(big, big.get_rect(center=(rect.centerx, rect.centery - 10)))
    names = {"abertura": "ABERTURA", "luta1": "MASMORRA 1", "luta2": "MASMORRA 2",
             "recompensa": "RECOMPENSA", "final": "ÚLTIMA SALA"}
    ui.text(screen, names[here], theme.XS, theme.BRASS, (rect.centerx, rect.bottom - 14))


def _scene_corredores(screen, ui, rect, t):
    """Os enfeites de cada capítulo, um capítulo por vez, com a placa da piada."""
    from .. import casa, casa_art, enfeites
    casa_art.use(ui.assets)
    chapter = 1 + (t // 150) % 4
    floor, wall, name = {1: ((52, 74, 44), (40, 90, 46), "TRILHA"), 2: ((58, 58, 62), (170, 170, 168), "LAG LOBBY"),
                         3: ((226, 222, 220), (246, 244, 246), "CLEPALOVERS"),
                         4: ((150, 150, 90), (226, 216, 190), "MANSÃO")}[chapter]
    screen.fill(floor, rect)
    screen.fill(wall, (rect.x, rect.y, rect.w, 56))
    screen.fill(casa_art.shade(wall, -50), (rect.x, rect.y + 56, rect.w, 4))
    walls, floors, lines, colors = enfeites.CHAPTERS[chapter]
    for x in (rect.x + 70, rect.x + 270):
        b = casa._bake(walls[0])
        screen.blit(b.image, (x + b.dx, rect.y + 56 + b.dy))
    for k, fn in enumerate(floors):
        b = casa._bake(fn)
        x, y = rect.x + 50 + k * 80, rect.y + (130 if k % 2 == 0 else 160)
        screen.blit(b.image, (x + b.dx, y + b.dy))
    sign = casa._bake(enfeites.joke_sign, lines, colors)
    screen.blit(sign.image, (rect.centerx + sign.dx, rect.y + 222 + sign.dy))
    screen.fill((20, 20, 26), (rect.x, rect.bottom - 22, rect.w, 22))
    ui.text(screen, f"CAPÍTULO {chapter} · {name}", theme.XS, theme.BONE, (rect.centerx, rect.bottom - 11))


NEWS_SCENES = {"almas": _scene_almas, "loja": _scene_loja, "hud": _scene_hud, "novidades": _scene_novidades,
               "enterrada": _scene_enterrada, "futebol": _scene_futebol, "penalti": _scene_penalti,
               "disputa": _scene_disputa, "lag": _scene_lag, "perigos": _scene_perigos,
               "chefao_lag": _scene_chefao_lag, "armas_lag": _scene_armas_lag,
               "bate": _scene_bate, "agarra": _scene_agarra, "modos": _scene_modos,
               "controle": _scene_controle, "coroa": _scene_coroa, "ultra": _scene_ultra,
               "clepalovers": _scene_clepalovers, "clinica": _scene_clinica, "oi_sumido": _scene_oi_sumido,
               "mansao": _scene_mansao, "iara": _scene_iara,
               "casa": _scene_casa, "computador": _scene_computador, "cantos": _scene_cantos,
               "corredores": _scene_corredores, "mapa_fase": _scene_mapa_fase}


from .plantao import ArchiveScene, NewsScene  # noqa: E402  (o plantão usa as cenas daqui)
