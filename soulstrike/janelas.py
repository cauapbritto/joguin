"""As janelas pequenas da Casa da turma e da garagem.

Tudo o que se usa ali (computador, notebook, livro, loja de CACOS, armário, PARA ONDE? e a garagem)
abre numa janela do tamanho da lojinha da fase, presa perto de quem abriu (o computador fica ao lado
da mesa). Várias abertas juntas não se cobrem: a que chega depois desce (ou sobe, ou vai para o
lado) até achar espaço. Se a câmera foi embora com o resto da turma, a janela de quem ficou para
trás gruda em cima do quadro dele no HUD, com uma setinha da cor dele.

Quem está numa janela também sai da corda do grupo e do enquadramento da câmera (ver
``CoopMatch.leash_free``): os outros andam pela casa toda. Ao fechar, se estiver longe, aparece do
lado do grupo.

Os avisos (``warning``) passam por cima da janela de cada um: "A TURMA ESTÁ SAINDO · 3" e
"LIBERANDO EM 5"."""
import pygame

from . import config, crt, hud, theme

LEAVE_WARN = 3 * config.FPS    # a turma saindo: a janela de quem ficou fecha nesse tempo
FREE_WARN = 5 * config.FPS     # LIBERAR TUDO: os outros têm esse tempo antes da casa recarregar
TOP = 56                       # abaixo do título da fase
BOTTOM = 80                    # acima dos quadros dos jogadores
GAP = 6
HEAD_ROOM = 70                 # a janela de quem abriu fica acima da cabeça dele
WARN_H = 18


def on_screen(match, f):
    """O jogador aparece na tela agora? (a câmera pode ter ido com os outros)."""
    sx, sy = match.camera.to_screen(f.x, f.y)
    return 0 <= sx <= config.SCREEN_W and 30 <= sy <= config.SCREEN_H - 60


def _clamp(rect):
    rect.x = max(8, min(config.SCREEN_W - rect.w - 8, rect.x))
    rect.y = max(TOP, min(config.SCREEN_H - rect.h - BOTTOM, rect.y))
    return rect


def wanted(match, f, menu, ui):
    """Onde a janela de ``f`` quer ficar (antes de desviar das outras)."""
    cam = match.camera
    if not on_screen(match, f) and f in match.players:
        w, h = menu.size(ui)
        i, n = match.players.index(f), len(match.players)
        block = pygame.Rect(hud.campaign_block_rect(i, n))
        rect = pygame.Rect(0, 0, w, h)
        rect.midbottom = (block.centerx, block.y - 12)
        rect.x = max(8, min(config.SCREEN_W - w - 8, rect.x))
        rect.y = max(TOP, rect.y)
        return rect, True
    window_rect = getattr(menu, "window_rect", None)
    if window_rect is not None:
        return window_rect(cam), False
    w, h = menu.size(ui)
    sx, sy = cam.to_screen(f.x, f.y)
    rect = pygame.Rect(0, 0, w, h)
    rect.midbottom = (round(sx), round(sy) - HEAD_ROOM)
    return _clamp(rect), False


def _free(rect, placed):
    return not any(rect.colliderect(o.inflate(GAP, GAP)) for o in placed)


def _dodge(rect, placed):
    """Tira a janela de cima das que já estão na tela: embaixo, em cima, à direita ou à esquerda."""
    if _free(rect, placed):
        return rect
    tries = []
    for o in placed:
        for move in ((rect.x, o.bottom + GAP), (rect.x, o.y - rect.h - GAP),
                     (o.right + GAP, rect.y), (o.x - rect.w - GAP, rect.y)):
            r = _clamp(pygame.Rect(move, rect.size))
            if _free(r, placed):
                tries.append(r)
    if not tries:
        return rect                    # sem espaço nenhum (4 janelas grandes): fica onde queria
    return min(tries, key=lambda r: abs(r.x - rect.x) + abs(r.y - rect.y))


def layout(match, ui):
    """[(lutador, menu, retângulo, grudada no HUD)] na ordem dos jogadores."""
    out, placed = [], []
    order = sorted(match.menus.items(), key=lambda kv: kv[0].slot or 9)
    for f, menu in order:
        rect, docked = wanted(match, f, menu, ui)
        rect = _dodge(rect, placed)
        placed.append(rect)
        out.append((f, menu, rect, docked))
    return out


def draw(match, screen, ui):
    """Desenha todas as janelas abertas (com o efeito de TV de tubo) e os avisos por cima."""
    cam = match.camera
    for f, menu, rect, docked in layout(match, ui):
        key = (getattr(menu, "kind", "janela"), f.slot)
        crt.panel(screen, key, lambda s, menu=menu, rect=rect: menu.draw(s, ui, cam, rect=rect))
        if docked:
            color = f.color
            x = rect.centerx
            pygame.draw.polygon(screen, color, [(x - 7, rect.bottom), (x + 7, rect.bottom), (x, rect.bottom + 8)])
        text = match.window_warning(f)
        if text:
            band = pygame.Rect(rect.x, rect.bottom - WARN_H, rect.w, WARN_H)
            screen.fill((120, 40, 40) if (match.frame // 10) % 2 else (90, 30, 30), band)
            ui.text(screen, text, theme.XS, (255, 240, 230), band.center, shadow=False)


def default_rect(size, where, f):
    """Sem o organizador (testes, prévias): acima de quem abriu. ``where`` é a câmera ou um ponto
    da tela."""
    if hasattr(where, "to_screen"):
        where = where.to_screen(f.x, f.y)
    rect = pygame.Rect((0, 0), size)
    rect.midbottom = (round(where[0]), round(where[1]) - HEAD_ROOM)
    return _clamp(rect)


def panel(screen, ui, rect, f, title, right="", accent=None):
    """A moldura padrão: fundo, faixa com a cor do jogador, P1 · TÍTULO e um texto à direita.
    Devolve a área de dentro."""
    pygame.draw.rect(screen, theme.SHADOW, rect.move(3, 3))
    ui.panel(screen, rect, fill=theme.INK_2, accent=accent or f.color)
    ui.text(screen, f"{f.label} · {title}", theme.XS, theme.BONE, (rect.x + 10, rect.y + 13), anchor="midleft")
    if right:
        ui.text(screen, right, theme.XS, theme.MUTED, (rect.right - 10, rect.y + 13), anchor="midright")
    return pygame.Rect(rect.x + 8, rect.y + 24, rect.w - 16, rect.h - 40)


def footer(screen, ui, rect, text):
    ui.text(screen, text, theme.XS, theme.FAINT, (rect.centerx, rect.bottom - 10))


class Janelas:
    """Mistura para a Casa e a garagem: corda solta para quem está numa janela, a volta ao grupo
    quando fecha e os avisos com contagem (a turma saindo, o LIBERAR TUDO)."""

    leaving_in = 0                 # quadros até a turma sair (as janelas fecham sozinhas)
    leaving_action = None
    freeing_in = 0                 # quadros até o LIBERAR TUDO recarregar a casa
    freeing_by = None

    def leash_free(self, p):
        return p in self.menus

    def menu_closed(self, f):
        """Fechou a janela longe da turma: some na fumaça e aparece do lado do grupo."""
        if not f.alive_in_match or not self.far_from_group(f):
            return
        others = [q for q in self.players if q is not f and not self.leash_free(q)]
        if others:
            self._pull_to_group(f, others)

    def close_windows(self, keep=None):
        for f in [g for g in self.menus if g is not keep]:
            del self.menus[f]

    def window_warning(self, f):
        if self.freeing_in and f is not self.freeing_by:
            return f"LIBERANDO TUDO EM {_secs(self.freeing_in)}"
        if self.leaving_in:
            return f"A TURMA ESTÁ SAINDO · {_secs(self.leaving_in)}"
        return None

    def leave_soon(self, action):
        """A turma vai embora: sem ninguém em janela, na hora; senão, as janelas avisam e fecham em 3 s."""
        if self.leaving_in:
            return
        if not self.menus:
            action()
            return
        self.leaving_in = LEAVE_WARN
        self.leaving_action = action
        self.assets.play("select", 0.4)

    def free_soon(self, fighter):
        """LIBERAR TUDO terminou no computador de ``fighter``: os outros ganham o aviso antes de a
        casa recarregar (sem ninguém em outra janela, recarrega na hora)."""
        if self.freeing or self.freeing_in:
            return
        if any(g is not fighter for g in self.menus):
            self.freeing_in = FREE_WARN
            self.freeing_by = fighter
            return
        self.close_windows(keep=fighter)
        self.freeing = 1
        self.assets.play("confirm", 0.7)

    def update_windows(self):
        """Um quadro das contagens."""
        if self.freeing_in:
            self.freeing_in -= 1
            if self.freeing_in <= 0:
                self.close_windows(keep=self.freeing_by)
                self.freeing = 1
                self.assets.play("confirm", 0.7)
        if self.leaving_in:
            self.leaving_in -= 1
            if self.leaving_in <= 0:
                action, self.leaving_action = self.leaving_action, None
                self.close_windows()
                if action is not None:
                    action()


def _secs(frames):
    return max(1, -(-frames // config.FPS))


__all__ = ("Janelas", "default_rect", "draw", "footer", "layout", "on_screen", "panel", "wanted")
