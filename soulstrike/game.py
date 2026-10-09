"""Loop principal: janela, troca de telas e leitura de entrada."""
import pygame

from . import config
from .assets import Assets
from .controls import PlayerInput
from .net import server
from .net.remote import SLOTS, hub
from .ui import UI


class Game:
    def __init__(self, fullscreen=True, headless=False):
        pygame.init()
        pygame.display.set_caption(config.TITLE)
        from .assets import window_icon
        pygame.display.set_icon(window_icon(32))
        self.headless = headless
        flags = pygame.SCALED | (pygame.FULLSCREEN if fullscreen else 0)
        self.screen = pygame.display.set_mode((config.SCREEN_W, config.SCREEN_H), flags)
        self.clock = pygame.time.Clock()
        self.clock_ticks = 0
        self.assets = Assets()
        self.ui = UI(self.assets)
        self.inputs = {s: PlayerInput(s) for s in SLOTS}
        self.session = None
        self.backdrop = None
        self.base_url = f"http://{server.local_ip()}:{config.WEB_PORT}"
        self._thumbs = {}
        self.running = True
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
        events = pygame.event.get() if events is None else events
        keys_pressed = set()
        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                keys_pressed.add(event.key)
                if event.key == pygame.K_F11:
                    pygame.display.toggle_fullscreen()
        held, pressed = hub.poll()
        axes = hub.axes()
        keys_down = pygame.key.get_pressed()
        now = pygame.time.get_ticks()
        for slot, inp in self.inputs.items():
            inp.update(keys_down, keys_pressed, held, pressed, now, axes.get(slot))
        for event in events:
            self.scene.handle(event)
        self.scene.update()
        self.scene.draw(self.screen)
        if self._fade > 0:
            self._fade -= 1
            self._fade_from.set_alpha(round(255 * self._fade / self.FADE_FRAMES))
            self.screen.blit(self._fade_from, (0, 0))
        self.clock_ticks += 1

    def run(self):
        while self.running:
            self.step()
            pygame.display.flip()
            self.clock.tick(config.FPS)
        pygame.quit()
