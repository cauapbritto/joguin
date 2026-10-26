"""Tela ATUALIZAR: procura versão nova no GitHub e aplica (a única que usa a internet)."""
import threading
import webbrowser

import pygame

from .. import __version__, config, theme, updater
from ..ui import MenuList
from .menus import TitleScene, _InfoScene


class UpdateScene(_InfoScene):
    heading = "ATUALIZAR"
    PANEL = pygame.Rect(56, 92, config.SCREEN_W - 112, 300)
    RESTART_FRAMES = 90         # tempo para ler "Atualizado!" antes de reabrir

    def __init__(self, game, start=True):
        super().__init__(game)
        self.kind = updater.install_kind()
        self.state = "idle"     # idle, checking, checked, applying, done
        self.info = None
        self.result = None
        self._job = None
        self._restart_in = None
        self.menu = MenuList([("VOLTAR", "back")], (0, 0), 260)
        if start:
            self.start_check()

    # ── trabalho em segundo plano (a tela não trava esperando a internet) ──
    def _run(self, state, work):
        self.state = state
        box = {}

        def target():
            box["value"] = work()

        thread = threading.Thread(target=target, daemon=True)
        self._job = (thread, box)
        thread.start()

    def start_check(self):
        self._run("checking", updater.check)

    def start_apply(self):
        pygame.mixer.music.stop() if pygame.mixer.get_init() else None   # solta o arquivo da música
        info = self.info
        self._run("applying", lambda: updater.apply(info))

    def update(self):
        super().update()
        if self._job is not None and not self._job[0].is_alive():
            value = self._job[1].get("value")
            self._job = None
            if self.state == "checking":
                self.info = value
                self.state = "checked"
            else:
                self.result = value
                self.state = "done"
                if value is not None and value.restart and not self.game.headless:
                    self._restart_in = self.RESTART_FRAMES
                elif self.music:
                    self.assets.music(self.music)
            self._build_menu()
        if self._restart_in is not None:
            self._restart_in -= 1
            if self._restart_in <= 0:
                self._restart_in = None
                if updater.restart():
                    self.game.quit()

    def _build_menu(self):
        options = []
        info = self.info
        if self.state == "checked" and info is not None:
            if info.status == "nova" and self.kind == "fonte":
                options.append(("ATUALIZAR AGORA", "apply"))
            elif info.status == "nova":
                options.append(("ABRIR PÁGINA", "page"))
            elif info.status in ("offline", "erro"):
                options.append(("TENTAR DE NOVO", "retry"))
        elif self.state == "done" and self.result is not None and not self.result.ok:
            options.append(("ABRIR PÁGINA", "page"))
        options.append(("VOLTAR", "back"))
        self.menu = MenuList(options, (self.PANEL.x + 24, self.PANEL.bottom - 34 * len(options) - 10), 300)

    def handle(self, event):
        busy = self.state in ("checking", "applying") or self._restart_in is not None
        if self.is_back(event) or (event.type == pygame.MOUSEBUTTONDOWN and event.button == 3):
            if self.state != "applying":      # no meio da troca de arquivos não sai
                self.sfx("cancel", 0.4)
                self.game.change(TitleScene(self.game))
            return
        if busy:
            return
        choice = self.menu.handle(event, self.sfx)
        if choice is None:
            return
        self.sfx("confirm")
        if choice == "back":
            self.game.change(TitleScene(self.game))
        elif choice == "retry":
            self.start_check()
        elif choice == "apply":
            self.start_apply()
        elif choice == "page":
            url = (self.info.deb_url if self.info and self.info.deb_url and self.kind == "executavel"
                   else self.info.page_url if self.info else updater.page_url())
            webbrowser.open(url)

    # ── desenho ──
    def lines(self):
        """(texto, cor) do painel, conforme o estado."""
        dots = "." * (1 + (self.ticks // 15) % 3)
        out = [(f"VERSÃO INSTALADA: {__version__}", theme.MUTED)]
        if self.state == "checking":
            out.append(("PROCURANDO VERSÃO NOVA NO GITHUB" + dots, theme.BONE))
        elif self.state == "applying":
            out.append((f"BAIXANDO E INSTALANDO A {self.info.latest}" + dots, theme.BONE))
            out.append(("NÃO FECHE O JOGO.", theme.BRASS))
        elif self.state == "checked" and self.info is not None:
            info = self.info
            color = {"nova": theme.MOSS, "atual": theme.BONE}.get(info.status, theme.BLOOD)
            out.append((info.message, color))
            if info.status == "nova":
                if self.kind == "git":
                    out.append(("ESTA PASTA É UM CLONE DO GIT: USE  git pull", theme.MUTED))
                elif self.kind == "itch":
                    out.append(("O APP DO ITCH.IO ATUALIZA O JOGO SOZINHO,", theme.MUTED))
                    out.append(("OU BAIXE A VERSÃO NOVA NA PÁGINA DO ITCH.IO.", theme.MUTED))
                elif self.kind != "fonte":
                    out.append(("ESTA INSTALAÇÃO NÃO SE ATUALIZA SOZINHA:", theme.MUTED))
                    out.append(("BAIXE A VERSÃO NOVA NA PÁGINA DO GITHUB.", theme.MUTED))
                else:
                    out.append(("SEU PROGRESSO SALVO É MANTIDO.", theme.MUTED))
                notes = [ln.strip().lstrip("-*• ").strip() for ln in info.notes.splitlines()]
                notes = [ln for ln in notes if ln and not ln.startswith("#")]
                if notes:
                    out.append(("NOVIDADES:", theme.BRASS))
                    out += [("· " + ln[:90], theme.BONE) for ln in notes[:4]]
        elif self.state == "done" and self.result is not None:
            out.append((self.result.message, theme.MOSS if self.result.ok else theme.BLOOD))
        return out

    def draw_body(self, screen):
        self.ui.panel(screen, self.PANEL)
        y = self.PANEL.y + 24
        for text, color in self.lines():
            y = self.ui.paragraph(screen, text.upper(), theme.XS, color, (self.PANEL.x + 24, y),
                                  self.PANEL.w - 48, spacing=15) + 10
        self.menu.draw(screen, self.ui, self.ticks)
        self.ui.text(screen, "A ÚNICA FUNÇÃO DO JOGO QUE USA A INTERNET", theme.XS, theme.FAINT,
                     (config.SCREEN_W // 2, self.PANEL.bottom + 18))
        self.footer(screen, [("ENTER", "ESCOLHER"), ("ESC", "VOLTAR")])
