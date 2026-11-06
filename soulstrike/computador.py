"""Os computadores da Casa da turma: o PC do Cauanzera (CAUANZERA OS) e o notebook do Albeguinio
(ALBEGUINIO OS, no modo hacker).

Abre com ATACAR perto da mesa. A janela aparece na TV, presa em cima do móvel, e no celular de quem
abriu (na mesma tela da loja: as opções viram a lista e o que está na tela vira o quadro ao lado).
Analógico escolhe, ATACAR abre, ESQUIVA volta (na área de trabalho, desliga).

Nos dois dá para LIBERAR TUDO: os 4 capítulos e os 4 corrompidos no duelo, para sempre, sem selo de
recorde. No PC é o ``liberar --tudo`` do terminal; no notebook, a invasão do cristal (mais longa e
com mais firula). Terminou, a tela fica branca com LIBERANDO... e a casa volta com tudo aberto."""
import random

import pygame

from . import config, progress, theme

STICK = 0.5
CAU = (84, 162, 222)
HK, HK_D, HK_L = (90, 240, 120), (30, 90, 50), (190, 255, 200)
PINK, AMBER, RED = (240, 120, 180), (240, 200, 90), (240, 80, 80)
GRAY = (200, 200, 200)
FREED = "liberado_tudo"
MAX_LINES = 13
LINE_CHARS = 40             # letras por linha do terminal


def _wrap(text, width):
    if len(text) <= width:
        return [text]
    indent = text[:len(text) - len(text.lstrip(" "))]
    words, lines, cur = text.split(" "), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > width:
            lines.append(cur)
            cur = indent + w
        else:
            cur = f"{cur} {w}" if cur else w
    lines.append(cur)
    lines[0] = lines[0] if lines[0].startswith(indent) else indent + lines[0]
    return lines


def freed():
    return bool(progress.load().get(FREED))


def free_everything():
    """LIBERAR TUDO: os capítulos 1 a 4 contam como zerados (libera os corrompidos no duelo e as
    portas da casa), mas sem selo, sem tempo e sem contar como campanha zerada."""
    data = progress.load()
    for k in range(1, progress.LAST_CHAPTER + 1):
        data[f"capitulo{k}_zerado"] = True
    data[FREED] = True
    progress.save(data)


class Option:
    def __init__(self, key, label, desc="", action=None, color=None):
        self.key, self.label, self.desc, self.action, self.color = key, label, desc, action, color


# ── conteúdo do CAUANZERA OS ─────────────────
FILES = (
    ("LEIA-ME.TXT", "ACHOU? ABRA O TERMINAL E DIGITE AJUDA."),
    ("TERMOS_IARA.TXT", "47 PÁGINAS. LIDAS: 0. ACEITO: SIM."),
    ("ORCAMENTO_UNO.TXT", "PNEU, ÓLEO, PARA-CHOQUE... TOTAL: MAIS QUE O CARRO."),
    ("SENHA_WIFI.TXT", "PERGUNTA PRO ALBEGUINIO."),
    ("PRINT_3H_DA_MANHA.PNG", "UMA CONVERSA SÓ: \"oi sumido\""),
    ("RECEITA_PAO_DE_QUEIJO.TXT", "DO JOÃO. NÃO PASSAR ADIANTE. (JÁ PASSOU.)"),
    ("BACKUP_DO_CRISTAL.ZIP", "ARQUIVO CORROMPIDO. COMO TUDO NESSA HISTÓRIA."),
)
PC_COMMANDS = (
    ("ajuda", (("  AJUDA  VER  DATA  PING  CLS  LIBERAR", HK),)),
    ("ver", (("  CAUANZERA OS 1.0 (MOTOR DE UNO 1.0)", HK),)),
    ("data", (("  HOJE. 03:00. VAI DORMIR, RAPAZ.", HK),)),
    ("ping lagloby", (("  RESPOSTA DE LAGLOBBY: TEMPO=999MS", HK), ("  (ISSO É LAG)", AMBER))),
    ("cls", ()),
    ("liberar --tudo", ()),
)
PAGES = (
    ("MANSÃO", "www.mansaodocarimbo.mgr.gov", (60, 110, 80), (
        "MANSÃO DO CARIMBO · PORTAL DO CIDADÃO", "PROTOCOLO: 0047/2026", "SITUAÇÃO: EM ANÁLISE",
        "PRAZO ESTIMADO: NUNCA", "FALTAM 3 CARIMBOS E 1 ASSINATURA.", "CUIABRASA AGORA: 47°C")),
    ("LAG LOBBY", "www.laglobby.com.br", (40, 150, 200), (
        "LAG LOBBY · INTERNET DE OUTRO MUNDO", "VELOCIDADE CONTRATADA: 500 MEGA", "VELOCIDADE ENTREGUE: 5",
        "SUPORTE: SUA LIGAÇÃO É IMPORTANTE", "POSIÇÃO NA FILA: 4.712")),
    ("CLEPALOVERS", "www.clepalovers.med.br", (200, 90, 150), (
        "CLÍNICA CLEPALOVERS", "AGENDE SUA CONSULTA", "PRÓXIMO HORÁRIO: DAQUI A 8 MESES",
        "CONVÊNIO: NÃO ACEITAMOS O SEU", "ESTACIONAMENTO: R$ 40 A HORA")),
    ("PADARIA DO JOÃO", "www.padariadojoao.com", (180, 110, 50), (
        "PADARIA DO JOÃO · DESDE SEMPRE", "PÃO FRANCÊS SAINDO: 6H, 11H E 17H", "PÃO DE QUEIJO: RECEITA SECRETA",
        "ENTREGA DE CITY: SÓ NO BAIRRO", "FIADO: SÓ PARA O CAUANZERA")),
)

# ── conteúdo do ALBEGUINIO OS ────────────────
NB_COMMANDS = (
    ("ajuda", (("  WIFI  RASTREAR  FECHAR_CAIXA", HK), ("  HACKEAR  SUDO (CUIDADO)", HK),)),
    ("wifi --reiniciar", (("  DESLIGANDO O ROTEADOR...", HK), ("  LIGANDO... FUNCIONOU.", HK))),
    ("rastrear daiwone", (("  LOCALIZAÇÃO: DIGITANDO...", PINK),)),
    ("fechar_caixa --mes", (("  [#########-] 97%  FALTA UM BOLETO.", AMBER),)),
    ("hackear tv", (("  ACESSO NEGADO. A TV É DO CAUANZERA.", RED),)),
    ("sudo ./invasao.sh --alvo=cristal --capitulos=1-4 --corrompidos", ()),
)
HACK = "sudo ./invasao.sh --alvo=cristal --capitulos=1-4 --corrompidos"
PASSWORD = "oi sumido"


class Computer:
    """Janela de um dos computadores, aberta por um jogador. Mesmo jeito do menu da loja:
    ``handle`` (controle), ``pick``/``buy`` (celular), ``snapshot`` (o que o celular mostra) e ``draw``."""

    kind = "pc"
    title = "CAUANZERA OS"
    device = "COMPUTADOR"
    prompt = "C:\\CAUANZERA> "

    def __init__(self, match, fighter, anchor):
        self.match = match
        self.fighter = fighter
        self.anchor = anchor                  # ponto do móvel no mundo (a janela fica em cima dele)
        self.screen = self.first_screen()
        self.index = 0
        self.lines = []
        self.queue = []
        self.wait = 0
        self.age = 0
        self.page = 0
        self.asking = False                   # liberar --tudo esperando o S/N
        self.done = False
        self._last = 0

    def first_screen(self):
        return "desktop"

    # ── opções da tela atual ─────────────────
    @property
    def busy(self):
        return bool(self.queue)

    def options(self):
        if self.screen == "desktop":
            return [Option("arquivos", "ARQUIVOS", "OS DOCUMENTOS DO CAUANZERA"),
                    Option("terminal", "TERMINAL", "DIGITE AJUDA PARA COMEÇAR"),
                    Option("navegador", "NAVEGADOR", "OS FAVORITOS DO CAUANZERA"),
                    Option("desligar", "DESLIGAR", "FECHA O COMPUTADOR")]
        if self.screen == "arquivos":
            return [Option(f"arq:{i}", name, text) for i, (name, text) in enumerate(FILES)]
        if self.screen == "navegador":
            return [Option(f"pag:{i}", name, url) for i, (name, url, _, _) in enumerate(PAGES)]
        if self.screen == "terminal":
            if self.asking:
                return [Option("sim", "S  SIM, LIBERAR", "SIM, LIBERAR TUDO"), Option("nao", "N  NÃO", "NÃO, DEIXA QUIETO")]
            return [Option(f"cmd:{c}", c, "DIGITA E ENTER") for c, _ in self.commands()]
        return []

    def commands(self):
        return PC_COMMANDS

    def picked(self):
        opts = self.options()
        return opts[self.index % len(opts)] if opts else None

    # ── controle ─────────────────────────────
    def handle(self, inp):
        """Controle de quem abriu. Devolve False quando fecha."""
        self.age += 1
        self.step()
        if self.done:
            return False
        if self.age <= 1:
            return True                       # o ATACAR que abriu não clica
        if inp.pressed("dodge") or inp.pressed("special") or inp.pressed("cancel"):
            return self.back()
        _, y = inp.axis()
        sy = 1 if y > STICK else -1 if y < -STICK else 0
        n = len(self.options())
        if sy and sy != self._last and n and not self.busy:
            self.index = (self.index + sy) % n
            self.match.assets.play("click", 0.25)
            if self.screen == "navegador":
                self.page = self.index % len(PAGES)
        self._last = sy
        if inp.pressed("attack") or inp.pressed("confirm"):
            self.buy()
        return True

    def back(self):
        self.match.assets.play("cancel", 0.3)
        if self.busy:
            return True                       # no meio do comando não dá para sair
        if self.screen in ("desktop", "login"):
            return False
        self.asking = False
        self.screen = "desktop"
        self.index = 0
        return True

    def pick(self, key):
        for k, o in enumerate(self.options()):
            if o.key == key:
                self.index = k
                if self.screen == "navegador":
                    self.page = k % len(PAGES)
                return True
        if key == "voltar":                   # botão VOLTAR do celular: volta uma tela, sem clicar
            self.back()
        return False

    def buy(self):
        """ATACAR (ou ABRIR no celular) na opção marcada."""
        if self.busy:
            return False
        o = self.picked()
        if o is None:
            return False
        self.match.assets.play("select", 0.35)
        self.activate(o)
        return True

    def activate(self, o):
        if self.screen == "desktop":
            if o.key == "desligar":
                self.done = True
                return
            self.screen = o.key
            self.index = 0
            self.page = 0
            if o.key == "terminal" and not self.lines:
                self.say("CAUANZERA OS 1.0 · DIGITE AJUDA", GRAY)
            return
        if self.screen == "navegador":
            self.page = self.index % len(PAGES)
            return
        if self.screen == "terminal":
            if self.asking:
                self.asking = False
                self.index = 0
                if o.key == "sim":
                    self.say("  S", GRAY)
                    self.run_unlock()
                else:
                    self.say("  N", GRAY)
                    self.say("  NADA FOI MUDADO.", HK)
                return
            command = o.key.split(":", 1)[1]
            self.type_command(command)
            self.run(command)

    # ── terminal ─────────────────────────────
    def say(self, text, color=HK, delay=6, replace=False, action=None):
        """Põe uma linha na fila do terminal; linha comprida quebra em mais de uma (cabe ao lado da
        lista de comandos)."""
        parts = _wrap(text, LINE_CHARS)
        for k, part in enumerate(parts):
            last = k == len(parts) - 1
            self.queue.append((part, color, delay if last else 2, replace and k == 0, action if last else None))

    def type_command(self, command):
        """O comando aparece letra por letra depois do prompt."""
        self.say(self.prompt, GRAY, 1)
        step = max(1, len(command) // 16)
        for k in range(step, len(command), step):      # digitando: o excesso some atrás da lista
            self.queue.append((self.prompt + command[:k], GRAY, 2, True, None))
        self.say(self.prompt + command, GRAY, 2, replace=True)

    def run(self, command):
        if command == "cls":
            self.say("", GRAY, 1, action=self.lines.clear)
            return
        if command == "liberar --tudo":
            if freed():
                self.say("  JÁ ESTÁ TUDO LIBERADO.", HK)
                return
            self.say("  ISSO LIBERA OS 4 CAPÍTULOS, OS 4", AMBER, 8)
            self.say("  CORROMPIDOS NO DUELO E AS PORTAS DA", AMBER, 8)
            self.say("  CASA. SEM SELO DE RECORDE.", AMBER, 8)
            self.say("  CONTINUAR? (S/N)", AMBER, 8, action=self._ask)
            return
        for text, color in dict(self.commands()).get(command, ()):
            self.say(text, color, 10)

    def _ask(self):
        self.asking = True
        self.index = 0

    def run_unlock(self):
        for label in ("CAPÍTULOS 1-4", "CORROMPIDOS", "PORTAS"):
            self.say(f"  [----------] {label}", HK, 2)
            for k in range(1, 11):
                self.say(f"  [{'#' * k}{'-' * (10 - k)}] {label}{' OK' if k == 10 else ''}", HK, 4, replace=True)
        self.say("  TUDO LIBERADO. SEM SELO DE RECORDE.", HK, 50, action=self.unlock)

    def unlock(self):
        free_everything()
        self.match.free_everything(self.fighter)

    def step(self):
        """Um quadro do terminal: a próxima linha da fila aparece quando a anterior terminou."""
        if self.wait > 0:
            self.wait -= 1
            return
        while self.queue and self.wait <= 0:
            text, color, delay, replace, action = self.queue.pop(0)
            if replace and self.lines:
                self.lines[-1] = (text, color)
            else:
                self.lines.append((text, color))
                del self.lines[:-MAX_LINES * 3]
            self.wait = delay
            if action is not None:
                action()

    # ── celular ──────────────────────────────
    def screen_lines(self):
        """O que está na tela agora, em linhas curtas (o quadro ao lado da lista no celular)."""
        o = self.picked()
        if self.screen == "terminal":
            return [t for t, _ in self.lines[-8:]]
        if self.screen == "arquivos" and o is not None:
            return [o.label, "", o.desc]
        if self.screen == "navegador":
            _, url, _, lines = PAGES[self.page % len(PAGES)]
            return [url, ""] + list(lines)
        return [o.desc] if o is not None else []

    def snapshot(self):
        opts = self.options()
        picked = self.picked()
        tela = {"type": "tela", "lines": self.screen_lines(), "look": self.kind}
        items = [{"id": o.key, "label": o.label.upper(), "cost": 0, "desc": o.desc, "ok": not self.busy,
                  "afford": True, "color": "#%02x%02x%02x" % (o.color or self.accent()), "info": tela}
                 for o in opts]
        if self.screen not in ("desktop", "login"):
            items.append({"id": "voltar", "label": "< VOLTAR", "cost": 0, "desc": "VOLTA PARA A ÁREA DE TRABALHO",
                          "ok": False, "afford": True, "color": "#8c8c96", "info": tela})
        return {
            "kind": self.kind,
            "title": f"{self.title} · {self.screen.upper()}",
            "souls": 0,
            "picked": picked.key if picked else None,
            "action": "AGUARDE" if self.busy else "ABRIR",
            "mates": [],
            "items": items,
        }

    def accent(self):
        return CAU

    # ── desenho ──────────────────────────────
    W, H = 520, 316

    def window_rect(self, cam):
        sx, sy = cam.to_screen(*self.anchor)
        rect = pygame.Rect(0, 0, self.W, self.H)
        rect.midbottom = (round(sx), round(sy) - 20)
        if rect.top < 56:                     # sem espaço em cima (móvel lá no alto): fica do lado
            rect.midleft = (round(sx) + 90, round(sy) + 60)
            if rect.right > config.SCREEN_W - 8:
                rect.midright = (round(sx) - 90, round(sy) + 60)
        rect.x = max(8, min(config.SCREEN_W - self.W - 8, rect.x))
        rect.y = max(56, min(config.SCREEN_H - self.H - 80, rect.y))
        return rect

    def draw(self, screen, ui, cam):
        rect = self.window_rect(cam)
        f = self.fighter
        ui.panel(screen, rect, fill=theme.INK_2, accent=f.color)
        ui.text(screen, f"{f.label} · {self.device}", theme.XS, theme.BONE, (rect.x + 12, rect.y + 14), anchor="midleft")
        ui.text(screen, self.title, theme.XS, theme.MUTED, (rect.right - 12, rect.y + 14), anchor="midright")
        inner = pygame.Rect(rect.x + 10, rect.y + 26, rect.w - 20, rect.h - 52)
        clip = screen.get_clip()
        screen.set_clip(inner)
        self.draw_inner(screen, ui, inner)
        screen.set_clip(clip)
        foot = "ANALÓGICO: ESCOLHER  ATACAR: ABRIR  ESQUIVA: " + ("DESLIGAR" if self.screen in ("desktop", "login")
                                                                 else "VOLTAR")
        ui.text(screen, foot, theme.XS, theme.FAINT, (rect.centerx, rect.bottom - 13))
        line = pygame.Surface((inner.w, 1), pygame.SRCALPHA)        # linhas de TV antiga
        line.fill((0, 0, 0, 40))
        for yy in range(inner.y, inner.bottom, 3):
            screen.blit(line, (inner.x, yy))

    def draw_inner(self, s, ui, r):
        self.wallpaper(s, ui, r)
        if self.screen == "desktop":
            self.draw_desktop(s, ui, r)
        elif self.screen == "arquivos":
            self.draw_files(s, ui, r)
        elif self.screen == "navegador":
            self.draw_browser(s, ui, r)
        elif self.screen == "terminal":
            self.draw_terminal(s, ui, r)
        self.taskbar(s, ui, r)

    def wallpaper(self, s, ui, r):
        for i in range(0, r.h, 4):
            k = i / r.h
            s.fill((16 + round(14 * k), 26 + round(8 * k), 46 + round(20 * k)), (r.x, r.y + i, r.w, 4))
        from .scenes.campaign import draw_crystal
        draw_crystal(s, (r.right - 100, r.y + 100), 44, self.match.frame)
        ui.text(s, "CAUANZERA OS", theme.XS, (140, 170, 220), (r.right - 100, r.y + 170))

    def taskbar(self, s, ui, r):
        bar = pygame.Rect(r.x, r.bottom - 20, r.w, 20)
        s.fill((24, 24, 34), bar)
        s.fill((60, 60, 80), (bar.x, bar.y, bar.w, 1))
        s.fill(CAU, (bar.x + 4, bar.y + 3, 66, 14))
        ui.text(s, "INICIAR", theme.XS, (255, 255, 255), (bar.x + 37, bar.centery), shadow=False)
        if self.screen != "desktop":
            s.fill((50, 60, 90), (bar.x + 76, bar.y + 3, 96, 14))
            ui.text(s, self.screen.upper(), theme.XS, theme.BONE, (bar.x + 124, bar.centery), shadow=False)
        ui.text(s, "03:00", theme.XS, theme.BONE, (bar.right - 26, bar.centery), shadow=False)

    def draw_desktop(self, s, ui, r):
        for i, o in enumerate(self.options()):
            x, y = r.x + 46, r.y + 12 + i * 54
            if i == self.index % len(self.options()):
                s.fill((60, 100, 160), (x - 36, y - 4, 72, 50))
                pygame.draw.rect(s, (120, 170, 230), (x - 36, y - 4, 72, 50), 1)
            _icon(s, o.key, x, y)
            ui.text(s, o.label, theme.XS, theme.BONE, (x, y + 36))
        box = pygame.Rect(r.x + 120, r.y + 20, 230, 64)
        s.fill((24, 32, 54), box)
        pygame.draw.rect(s, (90, 120, 180), box, 1)
        ui.text(s, "BEM-VINDO, CAUANZERA", theme.XS, theme.BONE, (box.centerx, box.y + 16))
        ui.text(s, f"{len(FILES)} ARQUIVOS EM DOCUMENTOS", theme.XS, theme.MUTED, (box.centerx, box.y + 34))
        ui.text(s, "LEMBRETE: LER OS TERMOS", theme.XS, theme.BRASS, (box.centerx, box.y + 50))

    def app(self, s, ui, rect, title):
        s.fill((10, 10, 14), rect.move(3, 3))
        s.fill((230, 228, 222), rect)
        s.fill((40, 70, 120), (rect.x, rect.y, rect.w, 16))
        ui.text(s, title, theme.XS, (255, 255, 255), (rect.x + 6, rect.y + 8), anchor="midleft", shadow=False)
        for i, c in enumerate(((200, 60, 60), (220, 190, 60), (80, 180, 90))):
            s.fill(c, (rect.right - 13 - i * 12, rect.y + 4, 8, 8))
        return pygame.Rect(rect.x + 2, rect.y + 18, rect.w - 4, rect.h - 20)

    def draw_files(self, s, ui, r):
        win = self.app(s, ui, pygame.Rect(r.x + 10, r.y + 8, r.w - 20, r.h - 36), "ARQUIVOS · C:\\CAUANZERA\\DOCUMENTOS")
        sel = self.index % len(FILES)
        for i, (name, _) in enumerate(FILES):
            y = win.y + 4 + i * 20
            if i == sel:
                s.fill((150, 180, 230), (win.x + 2, y - 2, win.w - 4, 18))
            color = (210, 180, 90) if name.endswith(".ZIP") else (120, 180, 230) if name.endswith(".PNG") else (250, 250, 248)
            s.fill(color, (win.x + 8, y, 10, 14))
            pygame.draw.rect(s, (120, 120, 130), (win.x + 8, y, 10, 14), 1)
            ui.text(s, name, theme.XS, (30, 30, 40), (win.x + 26, y + 7), anchor="midleft", shadow=False)
        prev = pygame.Rect(win.x + 4, win.bottom - 40, win.w - 8, 36)
        s.fill((250, 248, 240), prev)
        pygame.draw.rect(s, (160, 160, 170), prev, 1)
        name, text = FILES[sel]
        ui.text(s, name, theme.XS, (40, 70, 120), (prev.x + 8, prev.y + 11), anchor="midleft", shadow=False)
        ui.text(s, text, theme.XS, (30, 30, 40), (prev.x + 8, prev.y + 26), anchor="midleft", shadow=False)

    def draw_browser(self, s, ui, r):
        win = self.app(s, ui, pygame.Rect(r.x + 10, r.y + 8, r.w - 20, r.h - 36), "NAVEGADOR")
        name, url, color, lines = PAGES[self.page % len(PAGES)]
        bar = pygame.Rect(win.x + 4, win.y + 3, win.w - 8, 16)
        s.fill((255, 255, 255), bar)
        pygame.draw.rect(s, (160, 160, 170), bar, 1)
        ui.text(s, url, theme.XS, (40, 40, 60), (bar.x + 6, bar.centery), anchor="midleft", shadow=False)
        x = win.x + 4
        for i, (n, _, _, _) in enumerate(PAGES):
            w = ui.assets.text_width(n, theme.XS) + 12
            on = i == self.page % len(PAGES)
            s.fill((170, 190, 230) if on else (210, 214, 224), (x, win.y + 22, w, 14))
            ui.text(s, n, theme.XS, (40, 40, 60), (x + w // 2, win.y + 29), shadow=False)
            x += w + 4
        page = pygame.Rect(win.x + 4, win.y + 40, win.w - 8, win.h - 44)
        s.fill((244, 238, 220), page)
        s.fill(color, (page.x, page.y, page.w, 22))
        ui.text(s, lines[0], theme.XS, (255, 255, 255), (page.centerx, page.y + 11), shadow=False)
        for i, line in enumerate(lines[1:]):
            ui.text(s, line, theme.XS, (40, 40, 50), (page.x + 12, page.y + 36 + i * 18), anchor="midleft", shadow=False)

    def draw_terminal(self, s, ui, r):
        win = self.app(s, ui, pygame.Rect(r.x + 6, r.y + 6, r.w - 12, r.h - 32), "TERMINAL")
        self.draw_console(s, ui, win, (12, 12, 14))

    def draw_console(self, s, ui, win, bg):
        s.fill(bg, win)
        side = pygame.Rect(win.right - 150, win.y, 150, win.h)
        out = pygame.Rect(win.x, win.y, win.w - 152, win.h)
        shown = self.lines[-MAX_LINES:]
        for i, (text, color) in enumerate(shown):
            cursor = i == len(shown) - 1 and (self.match.frame // 15) % 2 and not self.busy
            ui.text(s, text + ("_" if cursor else ""), theme.XS, color, (out.x + 6, out.y + 8 + i * 15),
                    anchor="midleft", shadow=False)
        s.fill(self.panel_color(), side)
        ui.text(s, "COMANDOS" if not self.asking else "RESPONDA", theme.XS, theme.MUTED, (side.centerx, side.y + 9),
                shadow=False)
        for i, o in enumerate(self.options()):
            y = side.y + 20 + i * 16
            on = i == self.index % len(self.options())
            if on:
                s.fill((40, 70, 50) if self.kind == "notebook" else (40, 60, 100), (side.x + 2, y - 1, side.w - 4, 15))
            label = o.label if len(o.label) <= 20 else o.label[:18] + ".."
            ui.text(s, label, theme.XS, (HK_L if on else HK) if self.kind == "notebook" else (theme.BONE if on else GRAY),
                    (side.x + 6, y + 7), anchor="midleft", shadow=False)

    def panel_color(self):
        return (20, 22, 32)


class HackerNotebook(Computer):
    """O notebook do Albeguinio: pede a senha, mostra o alerta da mensagem e tem o terminal hacker,
    com a invasão do cristal que libera tudo (uns 6 segundos de animação)."""

    kind = "notebook"
    title = "ALBEGUINIO OS"
    device = "NOTEBOOK"
    prompt = "root@albeguinio:~# "

    def first_screen(self):
        return "desktop" if getattr(self.match, "notebook_open", False) else "login"

    def options(self):
        if self.screen == "login":
            return [Option("senha", "DIGITAR A SENHA", "DICA: O QUE ELE MAIS OUVE")]
        if self.screen == "desktop":
            return [Option("terminal", "TERMINAL", "root@albeguinio"),
                    Option("alerta", "ALERTA", "MENSAGEM NOVA DETECTADA"),
                    Option("desligar", "DESLIGAR", "FECHA O NOTEBOOK")]
        if self.screen == "alerta":
            return [Option("vacuo", "DEIXAR NO VÁCUO", "RECOMENDAÇÃO DO SISTEMA")]
        if self.screen == "terminal":
            return [Option(f"cmd:{c}", c if c != HACK else "sudo ./invasao.sh", "DIGITA E ENTER") for c, _ in NB_COMMANDS]
        return []

    def commands(self):
        return NB_COMMANDS

    def accent(self):
        return HK

    def activate(self, o):
        if self.screen == "login":
            self.screen = "senha"
            self.lines = []
            self.say("SENHA: ", GRAY, 4)
            for k in range(1, len(PASSWORD) + 1):
                self.say("SENHA: " + "*" * k, GRAY, 4, replace=True)
            self.say("ACESSO LIBERADO. BEM-VINDO, ALBEGUINIO.", HK, 40, action=self._logged)
            return
        if self.screen == "alerta":
            self.screen = "desktop"
            self.index = 1
            self.match.popup(self.fighter.x, self.fighter.y - 80, "VÁCUO!", PINK)
            return
        if self.screen == "desktop" and o.key == "terminal" and not self.lines:
            self.screen = "terminal"
            self.index = 0
            self.say("ALBEGUINIO OS · MODO HACKER", HK)
            self.say("DIGITE AJUDA. OU NÃO.", HK_D)
            return
        super().activate(o)

    def _logged(self):
        self.match.notebook_open = True
        self.screen = "desktop"
        self.index = 0
        self.lines = []

    def run(self, command):
        if command == HACK:
            if freed():
                self.say("  [!] O CRISTAL JÁ ESTÁ ABERTO. NADA A FAZER.", HK)
                return
            self.run_unlock()
            return
        super().run(command)

    def run_unlock(self):
        """A invasão do cristal: conexão, despejo de memória, quebra da senha, capítulos um a um e os
        corrompidos. Uns 6 segundos."""
        rng = random.Random(47)
        self.say("[*] CONECTANDO AO CRISTAL DAS ALMAS...", HK, 30)
        self.say("[*] PORTA 4747 ABERTA. INJETANDO PAYLOAD", HK, 16)
        for _ in range(8):
            hexes = " ".join(f"{rng.randrange(256):02X}" for _ in range(8))
            self.say(f"  0x{rng.randrange(16 ** 4):04X}  {hexes}", HK_D if rng.random() < 0.5 else HK, 5)
        self.say("[*] QUEBRANDO A CRIPTOGRAFIA...", AMBER, 10)
        for k in range(1, 9):
            guess = "".join(rng.choice("abcdefghijklmnopqrstuvwxyz ") for _ in range(9))
            self.say(f"    TENTATIVA {k:02d}: {guess}", RED, 3, replace=k > 1)
        self.say(f"    SENHA ENCONTRADA: {PASSWORD}", PINK, 20, replace=True)
        for chapter in range(1, 5):
            label = f"CAPÍTULO {chapter}"
            self.say(f"[+] {label} [----------]", HK, 2)
            for k in range(1, 11):
                self.say(f"[+] {label} [{'#' * k}{'-' * (10 - k)}]{' LIBERADO' if k == 10 else ''}", HK, 3,
                         replace=True)
        for name in ("ARYEL", "BORBA JR", "ALBEGUINIO", "CAUANZERA"):
            self.say(f"[+] {name} CORROMPIDO ...... NO DUELO", PINK, 11)
        self.say("[+] ACESSO AO CRISTAL: CONCEDIDO", HK_L, 30, action=self._crystal)
        self.say("[+] TUDO LIBERADO. SEM SELO DE RECORDE.", HK_L, 50, action=self.unlock)

    def _crystal(self):
        self.crystal_at = self.match.frame

    # ── desenho ──────────────────────────────
    def wallpaper(self, s, ui, r):
        s.fill((4, 10, 6), r)
        rng = random.Random(9)
        t = self.match.frame
        for col in range(r.x + 6, r.right - 6, 14):                     # chuva de caracteres
            speed = rng.uniform(1.5, 3.5)
            head = r.y + (rng.randrange(r.h) + t * speed) % (r.h + 120) - 60
            for k in range(rng.randrange(4, 12)):
                y = head - k * 12
                if r.y < y < r.bottom - 24:
                    c = (180, 255, 190) if k == 0 else (40, max(60, 200 - k * 16), 70)
                    ui.text(s, "01ABEGUINO$#%"[(col + k + t // 6) % 13], theme.XS, c, (col, round(y)), shadow=False)
        at = getattr(self, "crystal_at", None)
        if at is not None:
            from .scenes.campaign import draw_crystal
            draw_crystal(s, (r.right - 80, r.y + 70), 36, self.match.frame - at)

    def taskbar(self, s, ui, r):
        bar = pygame.Rect(r.x, r.bottom - 20, r.w, 20)
        s.fill((6, 16, 8), bar)
        s.fill(HK, (bar.x, bar.y, bar.w, 1))
        ui.text(s, "root@albeguinio", theme.XS, HK, (bar.x + 8, bar.centery), anchor="midleft", shadow=False)
        ui.text(s, self.screen.upper(), theme.XS, HK_L, (bar.centerx, bar.centery), shadow=False)
        ui.text(s, "VPN: LIGADA · 03:00", theme.XS, HK, (bar.right - 8, bar.centery), anchor="midright", shadow=False)

    def window(self, s, ui, rect, title):
        s.fill((0, 0, 0), rect)
        pygame.draw.rect(s, HK, rect, 1)
        s.fill(HK_D, (rect.x, rect.y, rect.w, 16))
        ui.text(s, title, theme.XS, (200, 255, 210), (rect.x + 6, rect.y + 8), anchor="midleft", shadow=False)
        return pygame.Rect(rect.x + 1, rect.y + 17, rect.w - 2, rect.h - 18)

    def draw_inner(self, s, ui, r):
        self.wallpaper(s, ui, r)
        if self.screen in ("login", "senha"):
            win = self.window(s, ui, pygame.Rect(r.centerx - 150, r.y + 50, 300, 120), "ALBEGUINIO OS · ENTRAR")
            ui.text(s, "USUÁRIO: albeguinio", theme.XS, HK, (win.x + 14, win.y + 18), anchor="midleft", shadow=False)
            text, color = self.lines[-1] if self.lines else ("SENHA: _", GRAY)
            ui.text(s, text, theme.XS, color, (win.x + 14, win.y + 40), anchor="midleft", shadow=False)
            if self.screen == "login":
                color = HK_L if (self.match.frame // 15) % 2 else HK
                ui.text(s, "ATACAR: DIGITAR A SENHA", theme.XS, color, (win.centerx, win.y + 76), shadow=False)
        elif self.screen == "desktop":
            for i, o in enumerate(self.options()):
                x, y = r.x + 46, r.y + 14 + i * 58
                if i == self.index % len(self.options()):
                    s.fill(HK_D, (x - 36, y - 4, 72, 52))
                    pygame.draw.rect(s, HK, (x - 36, y - 4, 72, 52), 1)
                s.fill((0, 0, 0), (x - 16, y, 32, 26))
                pygame.draw.rect(s, HK, (x - 16, y, 32, 26), 1)
                ui.text(s, {"terminal": ">_", "alerta": "!", "desligar": "X"}[o.key], theme.XS, HK, (x, y + 13),
                        shadow=False)
                ui.text(s, o.label, theme.XS, HK, (x, y + 38), shadow=False)
        elif self.screen == "alerta":
            win = self.window(s, ui, pygame.Rect(r.x + 120, r.y + 30, 300, 130), "ALERTA")
            for i, (line, c) in enumerate((("> MENSAGEM NOVA DETECTADA", HK), ("> REMETENTE: DAIWONE", PINK),
                                           ("> CONTEÚDO: \"oi sumido\"", PINK),
                                           ("> RECOMENDAÇÃO: NÃO RESPONDER", AMBER))):
                ui.text(s, line, theme.XS, c, (win.x + 10, win.y + 14 + i * 22), anchor="midleft", shadow=False)
            ui.text(s, "ATACAR: DEIXAR NO VÁCUO", theme.XS, HK_L, (win.centerx, win.bottom - 12), shadow=False)
        elif self.screen == "terminal":
            win = self.window(s, ui, pygame.Rect(r.x + 6, r.y + 6, r.w - 12, r.h - 32), "root@albeguinio: ~")
            self.draw_console(s, ui, win, (0, 0, 0))
        self.taskbar(s, ui, r)

    def panel_color(self):
        return (6, 20, 10)


def _icon(s, kind, x, y):
    """Ícone da área de trabalho do CAUANZERA OS (x, y = meio em cima)."""
    if kind == "arquivos":
        s.fill((220, 170, 60), (x - 14, y + 6, 28, 20))
        s.fill((240, 200, 90), (x - 14, y + 2, 12, 6))
        s.fill((250, 210, 110), (x - 14, y + 10, 28, 3))
    elif kind == "terminal":
        s.fill((20, 20, 24), (x - 14, y + 2, 28, 24))
        s.fill((60, 60, 70), (x - 14, y + 2, 28, 4))
        s.fill(HK, (x - 9, y + 12, 6, 2))
        s.fill(HK, (x - 1, y + 18, 8, 2))
    elif kind == "navegador":
        pygame.draw.circle(s, (60, 140, 220), (x, y + 14), 13)
        pygame.draw.circle(s, (90, 200, 120), (x - 4, y + 10), 5)
        pygame.draw.circle(s, (90, 200, 120), (x + 5, y + 18), 4)
        pygame.draw.circle(s, (200, 230, 255), (x, y + 14), 13, 2)
    else:
        pygame.draw.circle(s, (200, 70, 60), (x, y + 14), 12)
        pygame.draw.circle(s, (255, 255, 255), (x, y + 14), 7, 2)
        s.fill((200, 70, 60), (x - 2, y + 4, 4, 6))
        s.fill((255, 255, 255), (x - 1, y + 5, 2, 9))


def make(match, fighter, kind, anchor):
    cls = HackerNotebook if kind == "notebook" else Computer
    return cls(match, fighter, anchor)


__all__ = ("Computer", "HackerNotebook", "free_everything", "freed", "make")
