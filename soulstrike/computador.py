"""Os computadores da Casa da turma: o PC do Cauanzera (CAUANZERA OS) e o notebook do Albeguinio
(ALBEGUINIO OS, no modo hacker).

Abre com ATACAR perto da mesa. A janela aparece na TV, presa em cima do móvel, e no celular de quem
abriu, como uma cópia da tela: no celular a pessoa toca direto com o dedo; tocou na linha do terminal
(ou na barra do navegador, ou na senha), sobe o teclado do celular e o que ela digita vai para o
computador. O botão FECHAR TUDO do celular desliga na hora.

Sem o celular, uma setinha anda pela tela com o analógico (ou as setas) e ATACAR clica; para digitar,
aparece um teclado na tela, com sugestões. ESQUIVA volta um passo (sai da digitação, fecha a janela,
na área de trabalho desliga) e segurar ESQUIVA por 1 segundo fecha tudo.

Nos dois dá para LIBERAR TUDO: os 4 capítulos e os 4 corrompidos no duelo, para sempre, sem selo de
recorde. No PC é o ``liberar --tudo`` do terminal; no notebook, a invasão do cristal (mais longa e
com mais firula). Terminou, a tela fica branca com LIBERANDO... e a casa volta com tudo aberto."""
import io
import random
import unicodedata

import pygame

from . import config, progress, theme

STICK = 0.5
CURSOR_SPEED = 7            # px por quadro da setinha no analógico todo para um lado
CLOSE_HOLD = 60             # segurar ESQUIVA esse tanto fecha o computador
INNER_W, INNER_H = 500, 264  # a tela dentro da janela (o celular recebe esse tamanho)
TASKBAR = 20
OSK_H = 112
OSK_ROWS = ("1234567890", "qwertyuiop", "asdfghjkl-", "zxcvbnm./_")
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
    ("ajuda", (("  AJUDA  LS  CAT <ARQUIVO>  VER  DATA", HK), ("  PING LAGLOBBY  LIMPAR  NAVEGADOR", HK),
               ("  LIBERAR --TUDO  EXIT  DESLIGAR", HK))),
    ("ver", (("  CAUANZERA OS 1.0 (MOTOR DE UNO 1.0)", HK),)),
    ("data", (("  HOJE. 03:00. VAI DORMIR, RAPAZ.", HK),)),
    ("ping lagloby", (("  RESPOSTA DE LAGLOBBY: TEMPO=999MS", HK), ("  (ISSO É LAG)", AMBER))),
    ("ls", ()),
    ("limpar", ()),
    ("liberar --tudo", ()),
    ("exit", ()),
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
    ("SOULWIKI", "www.soulwiki.org", (110, 70, 170), ()),       # as linhas vêm do progresso (wiki_lines)
)
# palavras que levam a cada página quando digitadas na barra do navegador (sem acento, minúsculas)
PAGE_WORDS = (("mansao", "carimbo"), ("laglobby", "lag"), ("clepalovers", "clinica"), ("padaria", "joao"),
              ("soulwiki", "wiki"))
WIKI = ((1, "ARYEL CORROMPIDO", "CHEFE DA FLORESTA SOMBRIA"), (2, "BORBA JR CORROMPIDO", "CHEFE DA LAG LOBBY"),
        (3, "ALBEGUINIO CORROMPIDO", "CHEFE DA CLÍNICA CLEPALOVERS"),
        (4, "CAUANZERA CORROMPIDO", "CHEFE DA MANSÃO DO CARIMBO"))


def wiki_lines():
    """A SOULWIKI: os chefes já derrotados aparecem com o nome; os outros, como sombra."""
    lines = ["SOULWIKI · BESTIÁRIO DOS CORROMPIDOS"]
    for chapter, name, where in WIKI:
        lines.append(f"{name} · {where}" if progress.chapter_cleared(chapter) else f"??? · CAPÍTULO {chapter}")
    return tuple(lines)


def normalize(text):
    """Minúsculas, sem acento e sem espaço sobrando (para comparar o que foi digitado)."""
    text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode()
    return " ".join(text.lower().split())

# ── conteúdo do ALBEGUINIO OS ────────────────
NB_COMMANDS = (
    ("ajuda", (("  WIFI --REINICIAR  RASTREAR DAIWONE", HK), ("  FECHAR_CAIXA --MES  HACKEAR TV", HK),
               ("  SUDO ./INVASAO.SH (CUIDADO)  LIMPAR", HK), ("  EXIT  DESLIGAR", HK))),
    ("wifi --reiniciar", (("  DESLIGANDO O ROTEADOR...", HK), ("  LIGANDO... FUNCIONOU.", HK))),
    ("rastrear daiwone", (("  LOCALIZAÇÃO: DIGITANDO...", PINK),)),
    ("fechar_caixa --mes", (("  [#########-] 97%  FALTA UM BOLETO.", AMBER),)),
    ("hackear tv", (("  ACESSO NEGADO. A TV É DO CAUANZERA.", RED),)),
    ("sudo ./invasao.sh --alvo=cristal --capitulos=1-4 --corrompidos", ()),
    ("limpar", ()),
    ("exit", ()),
)
HACK = "sudo ./invasao.sh --alvo=cristal --capitulos=1-4 --corrompidos"
PASSWORD = "oi sumido"


class Computer:
    """Janela de um dos computadores, aberta por um jogador.

    ``handle`` (controle: setinha, ATACAR clica, ESQUIVA volta), ``pick`` (celular: toque na cópia da
    tela, texto digitado e VOLTAR), ``snapshot`` (o que o celular mostra) e ``draw``. Tudo o que dá
    para clicar vira um ``spot`` quando a tela é desenhada, em coordenadas da tela de dentro
    (INNER_W x INNER_H): o toque do celular e a setinha usam a mesma lista."""

    kind = "pc"
    title = "CAUANZERA OS"
    device = "COMPUTADOR"
    prompt = "C:\\CAUANZERA> "

    def __init__(self, match, fighter, anchor):
        self.match = match
        self.fighter = fighter
        self.anchor = anchor                  # ponto do móvel no mundo (a janela fica em cima dele)
        self.screen = self.first_screen()
        self.index = 0                        # arquivo marcado
        self.lines = []
        self.queue = []
        self.wait = 0
        self.age = 0
        self.page = 0                         # página do navegador (None: endereço que não existe)
        self.missing = ""                     # o endereço digitado que não existe (página 404)
        self.asking = False                   # liberar --tudo esperando o S/N
        self.done = False
        self.focus = None                     # digitando em: "terminal", "url" ou "senha"
        self.buffer = ""
        self.cursor = [INNER_W * 0.5, INNER_H * 0.45]
        self.spots = []                       # (retângulo na tela de dentro, o que faz)
        self.version = 0                      # muda quando a tela muda (o celular pede a imagem nova)
        self._dodge = 0
        self._drawn = None

    def first_screen(self):
        return "desktop"

    @property
    def busy(self):
        return bool(self.queue)

    def commands(self):
        return PC_COMMANDS

    # ── cliques ──────────────────────────────
    def spot(self, rect, key, origin):
        self.spots.append((pygame.Rect(rect).move(-origin[0], -origin[1]), key))

    def _layout(self):
        """Desenha a tela de dentro fora da vista, só para saber onde fica cada coisa clicável."""
        surf = pygame.Surface((INNER_W, INNER_H))
        self.draw_inner(surf, self.match.game.ui, surf.get_rect())

    def click(self, x, y):
        """Clique (setinha ou dedo) no ponto x, y da tela de dentro."""
        self.cursor = [max(0, min(INNER_W - 1, x)), max(0, min(INNER_H - 1, y))]
        self._layout()
        for rect, key in reversed(self.spots):          # o que foi desenhado por cima ganha
            if rect.collidepoint(x, y):
                self.press(key)
                return key
        return None

    def press(self, key):
        """O que cada coisa clicável faz."""
        self.version += 1
        if self.busy and not key.startswith("osk:"):
            return
        self.match.assets.play("click", 0.3)
        if key.startswith("osk:"):
            self.key_in(key[4:])
        elif key.startswith("open:"):
            self.open_app(key[5:])
        elif key == "desligar":
            self.done = True
        elif key == "close":
            self.close_app()
        elif key.startswith("focus:"):
            self.focus = key[6:]
            self.buffer = ""
        elif key.startswith("arq:"):
            self.index = int(key[4:])
        elif key.startswith("pag:"):
            self.page = int(key[4:])
        elif key.startswith("cmd:"):                     # sugestão clicada: digita e roda
            self.focus = "terminal"
            self.buffer = key[4:]
            self.submit()

    def open_app(self, name):
        self.screen = name
        self.focus = None
        self.buffer = ""
        if name == "navegador":
            self.page = 0
        if name == "terminal":
            self.focus = "terminal"
            if not self.lines:
                self.say(f"{self.title} · DIGITE AJUDA", GRAY)

    def close_app(self):
        self.asking = False
        self.focus = None
        self.buffer = ""
        self.screen = "desktop"

    # ── digitação ────────────────────────────
    def key_in(self, key):
        """Uma tecla do teclado da tela."""
        if key == "espaco":
            self.buffer += " "
        elif key == "apagar":
            self.buffer = self.buffer[:-1]
        elif key == "enter":
            self.submit()
        elif key.startswith("sug:"):
            self.buffer = key[4:]
        else:
            self.buffer += key
        self.buffer = self.buffer[:70]

    def type_text(self, text):
        """O que a pessoa digitou no teclado do celular (ENVIAR)."""
        if self.focus is None or self.busy:
            return False
        self.buffer = str(text)[:70]
        self.submit()
        return True

    def submit(self):
        text, focus = self.buffer.strip(), self.focus
        self.buffer = ""
        self.version += 1
        if focus == "url":
            self.focus = None
            self.go_to(text)
        elif focus == "terminal":
            self.enter_command(text)

    def go_to(self, text):
        words = normalize(text).replace("www.", "").replace("https://", "").replace("http://", "")
        for i, keys in enumerate(PAGE_WORDS):
            if any(k in words for k in keys):
                self.page = i
                return
        self.page = None
        self.missing = text[:30] or "?"

    def enter_command(self, text):
        self.say(self.prompt + text, GRAY, 2)
        command = normalize(text)
        if self.asking:
            self.asking = False
            if command in ("s", "sim"):
                self.run_unlock()
            else:
                self.say("  NADA FOI MUDADO.", HK)
            return
        if command:
            self.run(command)

    def suggestions(self):
        """Comandos que começam com o que já foi digitado (no máximo 3), para o teclado da tela."""
        if self.focus != "terminal":
            return []
        if self.asking:
            return ["s", "n"]
        typed = normalize(self.buffer)
        return [c for c, _ in self.commands() if c.startswith(typed)][:3]

    # ── controle ─────────────────────────────
    def handle(self, inp):
        """Controle de quem abriu. Devolve False quando fecha."""
        self.age += 1
        self.step()
        if self.done:
            return False
        if self.age <= 1:
            return True                       # o ATACAR que abriu não clica
        self._dodge = self._dodge + 1 if inp.held("dodge") else 0
        if self._dodge >= CLOSE_HOLD:
            self.match.assets.play("cancel", 0.3)
            return False                      # segurou ESQUIVA: fecha tudo
        if inp.pressed("dodge") or inp.pressed("special") or inp.pressed("cancel"):
            return self.back()
        x, y = inp.axis()
        if abs(x) > 0.2 or abs(y) > 0.2:
            self.cursor[0] = max(0, min(INNER_W - 1, self.cursor[0] + x * CURSOR_SPEED))
            self.cursor[1] = max(0, min(INNER_H - 1, self.cursor[1] + y * CURSOR_SPEED))
        if inp.pressed("attack") or inp.pressed("confirm"):
            self.click(*self.cursor)
        return True

    def back(self):
        """ESQUIVA (ou VOLTAR): sai da digitação, depois fecha a janela; na área de trabalho, desliga."""
        self.match.assets.play("cancel", 0.3)
        self.version += 1
        if self.busy:
            return True                       # no meio do comando não dá para sair
        if self.focus is not None and self.screen != "terminal":
            self.focus = None
            return True
        if self.screen in ("desktop", "login"):
            return False
        self.close_app()
        return True

    def pick(self, key):
        """Pedido do celular: ``pc:tap:x,y`` (0 a 1 na cópia da tela), ``pc:buf:...`` (o que está sendo
        digitado), ``pc:text:...`` (ENVIAR) ou ``voltar``."""
        if key.startswith("pc:tap:"):
            try:
                u, v = (float(n) for n in key[7:].split(","))
            except ValueError:
                return False
            if 0 <= u <= 1 and 0 <= v <= 1:
                self.click(u * INNER_W, v * INNER_H)
            return False
        if key.startswith("pc:text:"):
            self.type_text(key[8:])
            return False
        if key.startswith("pc:buf:"):                  # digitando no celular: a TV mostra na hora
            if self.focus is not None:
                self.buffer = key[7:][:70]
                self.version += 1
            return False
        if key == "voltar" and not self.back():
            self.done = True
        return False

    def buy(self):
        return False

    # ── terminal ─────────────────────────────
    def say(self, text, color=HK, delay=6, replace=False, action=None):
        """Põe uma linha na fila do terminal; linha comprida quebra em mais de uma."""
        parts = _wrap(text, LINE_CHARS)
        for k, part in enumerate(parts):
            last = k == len(parts) - 1
            self.queue.append((part, color, delay if last else 2, replace and k == 0, action if last else None))

    def run(self, command):
        if command in ("cls", "limpar", "clear"):
            self.say("", GRAY, 1, action=self.lines.clear)
            return
        if command == "exit":
            self.say("  ATÉ MAIS.", GRAY, 12, action=self.close_app)
            return
        if command == "desligar":
            self.say("  DESLIGANDO...", GRAY, 20, action=self._off)
            return
        if command in ("navegador", "browser"):
            self.say("  ABRINDO O NAVEGADOR...", GRAY, 12, action=lambda: self.open_app("navegador"))
            return
        if command in ("ls", "dir"):
            for name, _ in FILES:
                self.say(f"  {name}", HK, 3)
            return
        if command.startswith("cat"):
            wanted = command[3:].strip()
            for name, text in FILES:
                if wanted and normalize(name).startswith(wanted):
                    self.say(f"  {text}", HK, 10)
                    return
            self.say("  ARQUIVO NÃO ENCONTRADO. TENTE LS.", AMBER)
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
        known = dict(self.commands())
        if command in known:
            for text, color in known[command]:
                self.say(text, color, 10)
            return
        self.say("  COMANDO NÃO ENCONTRADO. TENTE AJUDA.", AMBER)

    def _off(self):
        self.done = True

    def _ask(self):
        self.asking = True

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
            self.version += 1
            if action is not None:
                action()

    # ── celular ──────────────────────────────
    def snapshot(self):
        return {
            "kind": self.kind,
            "screen": True,                    # o celular mostra a cópia da tela (/api/tela.png)
            "title": f"{self.title} · {self.screen.upper()}",
            "typing": self.focus is not None and not self.busy,
            "focus": self.focus or "",
            "buffer": self.buffer,
            "version": self.version,
            "ratio": round(INNER_W / INNER_H, 3),
            "fields": self.fields(),
            "souls": 0,
            "picked": None,
            "action": "",
            "mates": [],
            "items": [],
        }

    def fields(self):
        """Onde ficam os campos de texto na cópia da tela (0 a 1): tocou num deles, o celular já
        sobe o teclado no mesmo toque (o navegador só abre o teclado com o dedo na tela)."""
        if not self.spots:
            self._layout()
        out = []
        for rect, key in self.spots:
            if key.startswith("focus:"):
                out.append([round(rect.x / INNER_W, 4), round(rect.y / INNER_H, 4),
                            round(rect.w / INNER_W, 4), round(rect.h / INNER_H, 4), key[6:]])
        return out

    def png(self, ui):
        """A tela de dentro em PNG, para o celular (sem a setinha: lá é o dedo)."""
        surf = pygame.Surface((INNER_W, INNER_H))
        self.draw_inner(surf, ui, surf.get_rect())
        out = io.BytesIO()
        pygame.image.save(surf, out, "tela.png")
        return out.getvalue()

    def accent(self):
        return CAU

    # ── desenho ──────────────────────────────
    W, H = INNER_W + 20, INNER_H + 52

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
        inner = pygame.Rect(rect.x + 10, rect.y + 26, INNER_W, INNER_H)
        clip = screen.get_clip()
        screen.set_clip(inner)
        self.draw_inner(screen, ui, inner)
        self.draw_cursor(screen, inner)
        screen.set_clip(clip)
        if self.focus is not None:
            foot = "ATACAR: TECLA  ESQUIVA: " + ("SAIR" if self.screen == "terminal" else "PARAR DE DIGITAR")
        else:
            foot = "ANALÓGICO: SETINHA  ATACAR: CLICAR  SEGURAR ESQUIVA: FECHAR"
        ui.text(screen, foot, theme.XS, theme.FAINT, (rect.centerx, rect.bottom - 13))
        line = pygame.Surface((inner.w, 1), pygame.SRCALPHA)        # linhas de TV antiga
        line.fill((0, 0, 0, 40))
        for yy in range(inner.y, inner.bottom, 3):
            screen.blit(line, (inner.x, yy))

    def draw_cursor(self, s, inner):
        x, y = round(inner.x + self.cursor[0]), round(inner.y + self.cursor[1])
        arrow = [(x, y), (x, y + 14), (x + 4, y + 10), (x + 7, y + 16), (x + 9, y + 15), (x + 6, y + 9), (x + 11, y + 9)]
        pygame.draw.polygon(s, (255, 255, 255), arrow)
        pygame.draw.polygon(s, (10, 10, 14), arrow, 1)

    def draw_inner(self, s, ui, r):
        self.spots = []
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
        if self.focus is not None:
            self.draw_keyboard(s, ui, r)

    def wallpaper(self, s, ui, r):
        for i in range(0, r.h, 4):
            k = i / r.h
            s.fill((16 + round(14 * k), 26 + round(8 * k), 46 + round(20 * k)), (r.x, r.y + i, r.w, 4))
        from .scenes.campaign import draw_crystal
        draw_crystal(s, (r.right - 100, r.y + 100), 44, self.match.frame)
        ui.text(s, "CAUANZERA OS", theme.XS, (140, 170, 220), (r.right - 100, r.y + 170))

    def taskbar(self, s, ui, r):
        bar = pygame.Rect(r.x, r.bottom - TASKBAR, r.w, TASKBAR)
        s.fill((24, 24, 34), bar)
        s.fill((60, 60, 80), (bar.x, bar.y, bar.w, 1))
        s.fill(CAU, (bar.x + 4, bar.y + 3, 66, 14))
        ui.text(s, "INICIAR", theme.XS, (255, 255, 255), (bar.x + 37, bar.centery), shadow=False)
        if self.screen != "desktop":
            s.fill((50, 60, 90), (bar.x + 76, bar.y + 3, 96, 14))
            ui.text(s, self.screen.upper(), theme.XS, theme.BONE, (bar.x + 124, bar.centery), shadow=False)
        off = pygame.Rect(bar.right - 112, bar.y + 3, 66, 14)
        s.fill((170, 50, 50), off)
        ui.text(s, "DESLIGAR", theme.XS, (255, 255, 255), off.center, shadow=False)
        self.spot(off, "desligar", r.topleft)
        ui.text(s, "03:00", theme.XS, theme.BONE, (bar.right - 18, bar.centery), shadow=False)

    def desktop_items(self):
        return (("arquivos", "ARQUIVOS"), ("terminal", "TERMINAL"), ("navegador", "NAVEGADOR"))

    def draw_desktop(self, s, ui, r):
        for i, (key, label) in enumerate(self.desktop_items()):
            x, y = r.x + 46, r.y + 12 + i * 60
            box = pygame.Rect(x - 36, y - 4, 72, 52)
            if box.collidepoint(r.x + self.cursor[0], r.y + self.cursor[1]):
                s.fill((60, 100, 160), box)
                pygame.draw.rect(s, (120, 170, 230), box, 1)
            _icon(s, key, x, y)
            ui.text(s, label, theme.XS, theme.BONE, (x, y + 36))
            self.spot(box, f"open:{key}", r.topleft)
        box = pygame.Rect(r.x + 120, r.y + 20, 230, 64)
        s.fill((24, 32, 54), box)
        pygame.draw.rect(s, (90, 120, 180), box, 1)
        ui.text(s, "BEM-VINDO, CAUANZERA", theme.XS, theme.BONE, (box.centerx, box.y + 16))
        ui.text(s, f"{len(FILES)} ARQUIVOS EM DOCUMENTOS", theme.XS, theme.MUTED, (box.centerx, box.y + 34))
        ui.text(s, "LEMBRETE: LER OS TERMOS", theme.XS, theme.BRASS, (box.centerx, box.y + 50))

    def app(self, s, ui, rect, title, origin):
        s.fill((10, 10, 14), rect.move(3, 3))
        s.fill((230, 228, 222), rect)
        s.fill((40, 70, 120), (rect.x, rect.y, rect.w, 16))
        ui.text(s, title, theme.XS, (255, 255, 255), (rect.x + 6, rect.y + 8), anchor="midleft", shadow=False)
        for i, c in enumerate(((200, 60, 60), (220, 190, 60), (80, 180, 90))):
            s.fill(c, (rect.right - 13 - i * 12, rect.y + 4, 8, 8))
        ui.text(s, "x", theme.XS, (255, 255, 255), (rect.right - 9, rect.y + 8), shadow=False)
        self.spot((rect.right - 18, rect.y, 18, 16), "close", origin)
        return pygame.Rect(rect.x + 2, rect.y + 18, rect.w - 4, rect.h - 20)

    def app_rect(self, r):
        return pygame.Rect(r.x + 8, r.y + 6, r.w - 16, r.h - TASKBAR - 10)

    def draw_files(self, s, ui, r):
        win = self.app(s, ui, self.app_rect(r), "ARQUIVOS · C:\\CAUANZERA\\DOCUMENTOS", r.topleft)
        sel = self.index % len(FILES)
        for i, (name, _) in enumerate(FILES):
            y = win.y + 4 + i * 20
            row = pygame.Rect(win.x + 2, y - 2, win.w - 4, 18)
            if i == sel:
                s.fill((150, 180, 230), row)
            color = (210, 180, 90) if name.endswith(".ZIP") else (120, 180, 230) if name.endswith(".PNG") else (250, 250, 248)
            s.fill(color, (win.x + 8, y, 10, 14))
            pygame.draw.rect(s, (120, 120, 130), (win.x + 8, y, 10, 14), 1)
            ui.text(s, name, theme.XS, (30, 30, 40), (win.x + 26, y + 7), anchor="midleft", shadow=False)
            self.spot(row, f"arq:{i}", r.topleft)
        prev = pygame.Rect(win.x + 4, win.bottom - 40, win.w - 8, 36)
        s.fill((250, 248, 240), prev)
        pygame.draw.rect(s, (160, 160, 170), prev, 1)
        name, text = FILES[sel]
        ui.text(s, name, theme.XS, (40, 70, 120), (prev.x + 8, prev.y + 11), anchor="midleft", shadow=False)
        ui.text(s, text, theme.XS, (30, 30, 40), (prev.x + 8, prev.y + 26), anchor="midleft", shadow=False)

    def page_lines(self):
        if self.page is None:
            return ("PÁGINA NÃO ENCONTRADA", f"ENDEREÇO: {self.missing}", "",
                    "ERRO 404: O CRISTAL QUEBROU AQUI TAMBÉM.", "TENTE: SOULWIKI, PADARIA, LAGLOBBY...")
        name, _url, _color, lines = PAGES[self.page % len(PAGES)]
        return wiki_lines() if name == "SOULWIKI" else lines

    def draw_browser(self, s, ui, r):
        win = self.app(s, ui, self.app_rect(r), "NAVEGADOR", r.topleft)
        if self.page is None:
            url, color = self.missing, (120, 60, 70)
        else:
            _, url, color, _ = PAGES[self.page % len(PAGES)]
        bar = pygame.Rect(win.x + 4, win.y + 3, win.w - 8, 16)
        s.fill((255, 255, 255), bar)
        pygame.draw.rect(s, (60, 110, 200) if self.focus == "url" else (160, 160, 170), bar, 1)
        if self.focus == "url":
            caret = "_" if (self.match.frame // 15) % 2 else ""
            ui.text(s, self.buffer + caret, theme.XS, (20, 20, 30), (bar.x + 6, bar.centery), anchor="midleft", shadow=False)
        else:
            ui.text(s, url, theme.XS, (40, 40, 60), (bar.x + 6, bar.centery), anchor="midleft", shadow=False)
        self.spot(bar, "focus:url", r.topleft)
        x = win.x + 4
        for i, (n, _, _, _) in enumerate(PAGES):
            w = ui.assets.text_width(n, theme.XS) + 12
            on = self.page is not None and i == self.page % len(PAGES)
            tab = pygame.Rect(x, win.y + 22, w, 14)
            s.fill((170, 190, 230) if on else (210, 214, 224), tab)
            ui.text(s, n, theme.XS, (40, 40, 60), (x + w // 2, win.y + 29), shadow=False)
            self.spot(tab, f"pag:{i}", r.topleft)
            x += w + 4
        page = pygame.Rect(win.x + 4, win.y + 40, win.w - 8, win.h - 44)
        s.fill((244, 238, 220), page)
        lines = self.page_lines()
        s.fill(color, (page.x, page.y, page.w, 22))
        ui.text(s, lines[0], theme.XS, (255, 255, 255), (page.centerx, page.y + 11), shadow=False)
        for i, line in enumerate(lines[1:]):
            ui.text(s, line, theme.XS, (40, 40, 50), (page.x + 12, page.y + 36 + i * 18), anchor="midleft", shadow=False)
        if self.page is None:
            from .scenes.campaign import draw_crystal
            draw_crystal(s, (page.right - 60, page.bottom - 50), 26, self.match.frame, broken=True)

    def draw_terminal(self, s, ui, r):
        win = self.app(s, ui, self.app_rect(r), "TERMINAL", r.topleft)
        self.draw_console(s, ui, win, (12, 12, 14), r.topleft)

    def draw_console(self, s, ui, win, bg, origin):
        s.fill(bg, win)
        typing = self.focus == "terminal"
        room = max(3, (win.h - (OSK_H if typing else 0) - 22) // 15)
        shown = self.lines[-room:]
        for i, (text, color) in enumerate(shown):
            ui.text(s, text, theme.XS, color, (win.x + 6, win.y + 8 + i * 15), anchor="midleft", shadow=False)
        line_y = win.y + 8 + len(shown) * 15
        if not self.busy:
            caret = "_" if (self.match.frame // 15) % 2 else ""
            ask = "(S/N) " if self.asking else ""
            ui.text(s, self.prompt + ask + self.buffer + caret, theme.XS,
                    HK_L if self.kind == "notebook" else theme.BONE, (win.x + 6, line_y), anchor="midleft",
                    shadow=False)
        self.spot(win, "focus:terminal", origin)

    def draw_keyboard(self, s, ui, r):
        """O teclado da tela (para quem não está no celular): sugestões em cima e as teclas."""
        area = pygame.Rect(r.x + 4, r.bottom - TASKBAR - OSK_H - 2, r.w - 8, OSK_H)
        s.fill((14, 14, 22), area)
        pygame.draw.rect(s, (90, 90, 120), area, 1)
        kw = (area.w - 8) // 10
        y = area.y + 4
        x = area.x + 4
        sugs = self.suggestions()
        for sug in sugs:
            label = sug if len(sug) <= 22 else sug[:20] + ".."
            w = min(area.w // 3 - 6, ui.assets.text_width(label, theme.XS) + 14)
            chip = pygame.Rect(x, y, w, 14)
            self._key(s, ui, chip, label, f"osk:sug:{sug}", r, (40, 70, 60))
            x += w + 4
        if not sugs:
            ui.text(s, "DIGITANDO: " + {"url": "ENDEREÇO", "senha": "SENHA"}.get(self.focus, "COMANDO"), theme.XS,
                    theme.MUTED, (area.x + 8, y + 7), anchor="midleft", shadow=False)
        for row, keys in enumerate(OSK_ROWS):
            for col, ch in enumerate(keys):
                key = pygame.Rect(area.x + 4 + col * kw, area.y + 22 + row * 17, kw - 2, 15)
                self._key(s, ui, key, ch.upper(), f"osk:{ch}", r)
        y = area.y + 22 + len(OSK_ROWS) * 17
        third = (area.w - 8) // 3
        for i, (label, key) in enumerate((("ESPAÇO", "espaco"), ("APAGAR", "apagar"), ("ENTER", "enter"))):
            rect = pygame.Rect(area.x + 4 + i * third, y, third - 2, 15)
            self._key(s, ui, rect, label, f"osk:{key}", r, (50, 70, 110) if key == "enter" else None)

    def _key(self, s, ui, rect, label, key, r, color=None):
        hover = rect.collidepoint(r.x + self.cursor[0], r.y + self.cursor[1])
        s.fill((90, 120, 170) if hover else color or (40, 40, 52), rect)
        ui.text(s, label, theme.XS, (240, 240, 245), rect.center, shadow=False)
        self.spot(rect, key, r.topleft)


class HackerNotebook(Computer):
    """O notebook do Albeguinio: pede a senha (digitada de verdade), mostra o alerta da mensagem e tem
    o terminal hacker, com a invasão do cristal que libera tudo (uns 6 segundos de animação)."""

    kind = "notebook"
    title = "ALBEGUINIO OS"
    device = "NOTEBOOK"
    prompt = "root@albeguinio:~# "

    def first_screen(self):
        return "desktop" if getattr(self.match, "notebook_open", False) else "login"

    def commands(self):
        return NB_COMMANDS

    def accent(self):
        return HK

    def desktop_items(self):
        return (("terminal", "TERMINAL"), ("alerta", "ALERTA"))

    def open_app(self, name):
        if name == "terminal" and not self.lines:
            self.screen = "terminal"
            self.focus = "terminal"
            self.buffer = ""
            self.say("ALBEGUINIO OS · MODO HACKER", HK)
            self.say("DIGITE AJUDA. OU NÃO.", HK_D)
            return
        super().open_app(name)

    def press(self, key):
        if key == "vacuo":
            self.version += 1
            self.close_app()
            self.match.popup(self.fighter.x, self.fighter.y - 80, "VÁCUO!", PINK)
            return
        super().press(key)

    def submit(self):
        if self.focus == "senha":
            typed = self.buffer
            self.buffer = ""
            self.version += 1
            if normalize(typed) == PASSWORD:
                self.focus = None
                self.say("ACESSO LIBERADO. BEM-VINDO, ALBEGUINIO.", HK, 40, action=self._logged)
            else:
                self.say("SENHA ERRADA. DICA: O QUE ELE MAIS OUVE.", RED, 10)
            return
        super().submit()

    def _logged(self):
        self.match.notebook_open = True
        self.screen = "desktop"
        self.lines = []

    def run(self, command):
        if command.startswith("sudo ./invasao.sh") or command == "hackear cristal":
            if freed():
                self.say("  [!] O CRISTAL JÁ ESTÁ ABERTO. NADA A FAZER.", HK)
                return
            self.run_unlock()
            return
        if command in ("ls", "dir"):
            self.say("  invasao.sh  (SÓ ISSO. O RESTO É SEGREDO.)", HK)
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
        bar = pygame.Rect(r.x, r.bottom - TASKBAR, r.w, TASKBAR)
        s.fill((6, 16, 8), bar)
        s.fill(HK, (bar.x, bar.y, bar.w, 1))
        ui.text(s, "root@albeguinio", theme.XS, HK, (bar.x + 8, bar.centery), anchor="midleft", shadow=False)
        ui.text(s, self.screen.upper(), theme.XS, HK_L, (bar.centerx - 30, bar.centery), shadow=False)
        off = pygame.Rect(bar.right - 70, bar.y + 3, 62, 14)
        s.fill((0, 0, 0), off)
        pygame.draw.rect(s, RED, off, 1)
        ui.text(s, "DESLIGAR", theme.XS, RED, off.center, shadow=False)
        self.spot(off, "desligar", r.topleft)

    def window(self, s, ui, rect, title, origin, closable=True):
        s.fill((0, 0, 0), rect)
        pygame.draw.rect(s, HK, rect, 1)
        s.fill(HK_D, (rect.x, rect.y, rect.w, 16))
        ui.text(s, title, theme.XS, (200, 255, 210), (rect.x + 6, rect.y + 8), anchor="midleft", shadow=False)
        if closable:
            ui.text(s, "[x]", theme.XS, HK_L, (rect.right - 14, rect.y + 8), shadow=False)
            self.spot((rect.right - 26, rect.y, 26, 16), "close", origin)
        return pygame.Rect(rect.x + 1, rect.y + 17, rect.w - 2, rect.h - 18)

    def draw_inner(self, s, ui, r):
        self.spots = []
        self.wallpaper(s, ui, r)
        if self.screen == "login":
            win = self.window(s, ui, pygame.Rect(r.centerx - 150, r.y + 30, 300, 110), "ALBEGUINIO OS · ENTRAR",
                              r.topleft, closable=False)
            ui.text(s, "USUÁRIO: albeguinio", theme.XS, HK, (win.x + 14, win.y + 16), anchor="midleft", shadow=False)
            field = pygame.Rect(win.x + 10, win.y + 30, win.w - 20, 18)
            pygame.draw.rect(s, HK_L if self.focus == "senha" else HK_D, field, 1)
            caret = "_" if self.focus == "senha" and (self.match.frame // 15) % 2 else ""
            ui.text(s, "SENHA: " + "*" * len(self.buffer) + caret, theme.XS, GRAY, (field.x + 6, field.centery),
                    anchor="midleft", shadow=False)
            self.spot(field, "focus:senha", r.topleft)
            if self.lines:
                text, color = self.lines[-1]
                ui.text(s, text, theme.XS, color, (win.centerx, win.y + 64), shadow=False)
            elif self.focus is None:
                color = HK_L if (self.match.frame // 15) % 2 else HK
                ui.text(s, "CLIQUE NA SENHA PARA DIGITAR", theme.XS, color, (win.centerx, win.y + 64), shadow=False)
        elif self.screen == "desktop":
            for i, (key, label) in enumerate(self.desktop_items()):
                x, y = r.x + 46, r.y + 14 + i * 64
                box = pygame.Rect(x - 36, y - 4, 72, 54)
                if box.collidepoint(r.x + self.cursor[0], r.y + self.cursor[1]):
                    s.fill(HK_D, box)
                    pygame.draw.rect(s, HK, box, 1)
                s.fill((0, 0, 0), (x - 16, y, 32, 26))
                pygame.draw.rect(s, HK, (x - 16, y, 32, 26), 1)
                ui.text(s, {"terminal": ">_", "alerta": "!"}[key], theme.XS, HK, (x, y + 13), shadow=False)
                ui.text(s, label, theme.XS, HK, (x, y + 38), shadow=False)
                self.spot(box, f"open:{key}", r.topleft)
        elif self.screen == "alerta":
            win = self.window(s, ui, pygame.Rect(r.x + 110, r.y + 24, 300, 140), "ALERTA", r.topleft)
            for i, (line, c) in enumerate((("> MENSAGEM NOVA DETECTADA", HK), ("> REMETENTE: DAIWONE", PINK),
                                           ("> CONTEÚDO: \"oi sumido\"", PINK),
                                           ("> RECOMENDAÇÃO: NÃO RESPONDER", AMBER))):
                ui.text(s, line, theme.XS, c, (win.x + 10, win.y + 12 + i * 20), anchor="midleft", shadow=False)
            button = pygame.Rect(win.centerx - 80, win.bottom - 26, 160, 18)
            s.fill(HK_D, button)
            pygame.draw.rect(s, HK, button, 1)
            ui.text(s, "DEIXAR NO VÁCUO", theme.XS, HK_L, button.center, shadow=False)
            self.spot(button, "vacuo", r.topleft)
        elif self.screen == "terminal":
            win = self.window(s, ui, self.app_rect(r), "root@albeguinio: ~", r.topleft)
            self.draw_console(s, ui, win, (0, 0, 0), r.topleft)
        self.taskbar(s, ui, r)
        if self.focus is not None:
            self.draw_keyboard(s, ui, r)


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
