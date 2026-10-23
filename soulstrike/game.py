"""Loop principal: janela, troca de telas e leitura de entrada."""
import pygame

from . import config, settings, theme
from .assets import Assets
from .controls import PlayerInput
from .gamepads import Gamepads
from .net import server
from .net.remote import SLOTS, hub
from .ui import UI


class Game:
    def __init__(self, fullscreen=True, headless=False, vsync=True):
        pygame.init()
        pygame.display.set_caption(config.TITLE)
        from .assets import window_icon
        pygame.display.set_icon(window_icon(32))
        self.headless = headless
        self.fullscreen = fullscreen
        PlayerInput.double_tap_enabled = settings.get("duplo_toque")
        flags = pygame.SCALED | (pygame.FULLSCREEN if fullscreen else 0)
        size = (config.SCREEN_W, config.SCREEN_H)
        self.vsync = False
        if vsync and not headless:
            # sincronia vertical: a imagem troca junto com o monitor (sem "rasgo" quando a câmera desliza)
            try:
                self.screen = pygame.display.set_mode(size, flags, vsync=1)
                self.vsync = True
            except pygame.error:
                pass
        if not self.vsync:
            self.screen = pygame.display.set_mode(size, flags)
        self.clock = pygame.time.Clock()
        self.clock_ticks = 0
        self.assets = Assets()
        self.ui = UI(self.assets)
        self.inputs = {s: PlayerInput(s) for s in SLOTS}
        self.gamepads = Gamepads(enabled=not headless)
        self.session = None
        self.assist_level = "media"     # assistência do futebol escolhida no menu
        self.backdrop = None
        self.base_url = f"http://{server.local_ip()}:{config.WEB_PORT}"
        self._thumbs = {}
        self.running = True
        self.show_fps = False           # F3 mostra os quadros por segundo
        self._fade = 0
        self._fade_from = None
        from .scenes.menus import LoadingScene
        self.scene = None
        self.change(LoadingScene(self))

    FADE_FRAMES = 12

    def change(self, scene):
        # guarda o último quadro para misturar com a tela nova (transição suave)
        if self.scene is not None:
            self._fade_from = self.screen.copy()
            self._fade = self.FADE_FRAMES
        self.scene = scene
        scene.enter()

    def toggle_fullscreen(self):
        """Alterna tela cheia (F11 ou opções) e lembra a escolha para a próxima vez."""
        if not self.headless:
            pygame.display.toggle_fullscreen()
        self.fullscreen = not self.fullscreen
        settings.change("tela_cheia", self.fullscreen)

    def connected_slots(self):
        """Vagas com celular ou controle USB (quem não está aqui joga no teclado ou é CPU)."""
        return hub.connected_slots() | self.gamepads.slots()

    def device_of(self, slot):
        if slot in hub.connected_slots():
            return "CELULAR"
        if slot in self.gamepads.slots():
            return "CONTROLE"
        return "TECLADO"

    def quit(self):
        self.running = False

    def thumbnail(self, cfg, size):
        key = (cfg.key, size)
        if key not in self._thumbs:
            from .arena import Arena
            self._thumbs[key] = Arena(cfg, self.assets).thumbnail(size)
        return self._thumbs[key]

    def step(self, events=None):
        """Um quadro do jogo (separado de run() para facilitar testes)."""
        self.update(events)
        self.draw()

    def update(self, events=None):
        """Lógica de um quadro (entrada, cena). run() chama sem desenhar quando o PC atrasa."""
        events = pygame.event.get() if events is None else events
        keys_pressed = set()
        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                keys_pressed.add(event.key)
                if event.key == pygame.K_F11:
                    self.toggle_fullscreen()
                elif event.key == pygame.K_F3:
                    self.show_fps = not self.show_fps
            self.gamepads.handle(event)
        held, pressed = hub.poll()
        axes = hub.axes()
        # controles USB entram como se fossem celulares (o celular conectado manda no analógico)
        pad_held, pad_pressed, pad_axes = self.gamepads.poll()
        held, pressed = held | pad_held, pressed | pad_pressed
        axes = {**pad_axes, **axes}
        keys_down = pygame.key.get_pressed()
        now = pygame.time.get_ticks()
        for slot, inp in self.inputs.items():
            inp.update(keys_down, keys_pressed, held, pressed, now, axes.get(slot))
        if getattr(self.scene, "menu_keys", False):
            events = list(events) + self.gamepads.menu_events()     # menus só de teclado: controle vira setas
        for event in events:
            self.scene.handle(event)
        self.scene.update()
        if self._fade > 0:
            self._fade -= 1
        self.clock_ticks += 1

    def draw(self):
        self.scene.draw(self.screen)
        if self._fade > 0:
            self._fade_from.set_alpha(round(255 * self._fade / self.FADE_FRAMES))
            self.screen.blit(self._fade_from, (0, 0))
        if self.show_fps:
            self.ui.text(self.screen, f"{self.clock.get_fps():.0f} FPS", theme.XS, theme.BRASS, (8, 8),
                         anchor="topleft")

    def run(self):
        budget = FrameBudget(config.FPS)
        while self.running:
            self.step()
            pygame.display.flip()
            # PC atrasado (quadro demorou mais que 1/60 s): roda a lógica de novo sem desenhar,
            # para o jogo não ficar em câmera lenta
            for _ in range(budget.spend(self.clock.tick(config.FPS))):
                if not self.running:
                    break
                self.update([])
        pygame.quit()


class FrameBudget:
    """Conta o tempo real contra o tempo do jogo (60 quadros por segundo).

    spend(ms do último quadro) devolve quantas atualizações extras a lógica precisa para
    alcançar o relógio. No máximo MAX_CATCHUP por quadro: num PC lento demais o jogo fica mais
    lento em vez de travar tentando alcançar.
    """

    MAX_CATCHUP = 3

    def __init__(self, fps):
        self.frame_ms = 1000 / fps
        self.behind = 0.0

    def spend(self, ms):
        self.behind += ms - self.frame_ms
        extra = 0
        while self.behind >= self.frame_ms - 1e-6 and extra < self.MAX_CATCHUP:
            self.behind -= self.frame_ms
            extra += 1
        # muito atrás: esquece o resto. E um quadro adiantado não vira "crédito" acumulado.
        self.behind = max(-self.frame_ms, min(self.behind, self.frame_ms))
        return extra
