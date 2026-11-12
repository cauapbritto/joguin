"""Os computadores da Casa da turma: o PC do Cauanzera (CAUANZERA OS) e o notebook do Albeguinio
(ALBEGUINIO OS, no modo hacker).

Abre com ATACAR perto da mesa, numa janela pequena (metade do tamanho antigo) presa ao lado do móvel,
e a mesma tela vai para o celular de quem abriu, onde dá para tocar direto. Nada se digita: tudo é
uma lista, igual à lojinha. O analógico (ou as setas) escolhe, ATACAR roda, ESQUIVA volta um passo
(na tela inicial, desliga) e segurar ESQUIVA por 1 segundo fecha tudo. No terminal os comandos já vêm
prontos na lista; a senha do notebook é escolher entre os palpites.

Nos dois dá para LIBERAR TUDO: os 4 capítulos e os 4 corrompidos no duelo, para sempre, sem selo de
recorde. No PC é o ``liberar --tudo`` do terminal; no notebook, a invasão do cristal (mais longa e
com mais firula). Terminou, a tela fica branca com LIBERANDO... e a casa volta com tudo aberto."""
import io
import random
import unicodedata

import pygame

from . import config, progress, theme

STICK = 0.5
REPEAT = 9                  # quadros entre um passo e outro da lista com o analógico segurado
CLOSE_HOLD = 60             # segurar ESQUIVA esse tanto fecha o computador
INNER_W, INNER_H = 240, 126  # a tela dentro da janela (o celular recebe esse tamanho)
ROW_H = 17                  # altura de uma linha da lista
LINE_H = 12                 # altura de uma linha de texto (terminal, arquivo, site)
CAU = (84, 162, 222)
HK, HK_D, HK_L = (90, 240, 120), (30, 90, 50), (190, 255, 200)
PINK, AMBER, RED = (240, 120, 180), (240, 200, 90), (240, 80, 80)
GRAY = (200, 200, 200)
FREED = "liberado_tudo"
MAX_LINES = 13
LINE_CHARS = 27             # letras por linha do terminal (a letra XS tem 8 px)


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
    ("ajuda", (("  OS COMANDOS ESTÃO NA LISTA.", HK), ("  ESCOLHA E APERTE ATACAR.", HK),
               ("  LIBERAR --TUDO ABRE TUDO.", AMBER))),
    ("ver", (("  CAUANZERA OS 1.0 (MOTOR DE UNO 1.0)", HK),)),
    ("data", (("  HOJE. 03:00. VAI DORMIR, RAPAZ.", HK),)),
    ("ping lagloby", (("  LAGLOBBY: TEMPO=999MS", HK), ("  (ISSO É LAG)", AMBER))),
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
    ("ajuda", (("  ESCOLHA NA LISTA. OU NÃO.", HK), ("  INVASAO.SH: CUIDADO.", AMBER))),
    ("wifi --reiniciar", (("  DESLIGANDO O ROTEADOR...", HK), ("  LIGANDO... FUNCIONOU.", HK))),
    ("rastrear daiwone", (("  LOCALIZAÇÃO: DIGITANDO...", PINK),)),
    ("fechar_caixa --mes", (("  [#########-] 97%", AMBER), ("  FALTA UM BOLETO.", AMBER))),
    ("hackear tv", (("  ACESSO NEGADO.", RED), ("  A TV É DO CAUANZERA.", RED))),
    ("sudo ./invasao.sh --alvo=cristal --capitulos=1-4 --corrompidos", ()),
    ("limpar", ()),
    ("exit", ()),
)
HACK = "sudo ./invasao.sh --alvo=cristal --capitulos=1-4 --corrompidos"
PASSWORD = "oi sumido"
GUESSES = ("123456", "albeguinio", "senha123", PASSWORD, "wifi_da_casa")   # a senha é escolher o palpite
# os comandos prontos do terminal (o que aparece na lista; o texto é o comando que roda)
PC_MENU = ("ajuda", "ls", "cat leia-me.txt", "cat termos_iara.txt", "cat senha_wifi.txt", "ver", "data",
           "ping lagloby", "navegador", "limpar", "liberar --tudo", "exit")
NB_MENU = ("ajuda", "ls", "wifi --reiniciar", "rastrear daiwone", "fechar_caixa --mes", "hackear tv", HACK,
           "limpar", "exit")


class Computer:
    """Janela de um dos computadores, aberta por um jogador.

    Cada tela é uma lista (``rows``): o analógico marca, ATACAR (ou o toque no celular) roda o que está
    marcado. ``handle`` (controle), ``pick`` (celular: toque na cópia da tela e VOLTAR), ``snapshot``
    (o que o celular mostra) e ``draw``. Tudo o que dá para tocar vira um ``spot`` quando a tela é
    desenhada, em coordenadas da tela de dentro (INNER_W x INNER_H)."""

    kind = "pc"
    title = "CAUANZERA OS"
    device = "COMPUTADOR"
    prompt = "C:\\> "
    W, H = INNER_W + 20, INNER_H + 46

    def __init__(self, match, fighter, anchor):
        self.match = match
        self.fighter = fighter
        self.anchor = anchor                  # ponto do móvel no mundo (a janela fica ao lado dele)
        self.screen = self.first_screen()
        self.sel = 0                          # linha marcada na lista da tela
        self.top = 0                          # primeira linha visível (lista que não cabe rola)
        self.reading = None                   # (título, linhas, cor): arquivo, site ou alerta aberto
        self.lines = []
        self.queue = []
        self.wait = 0
        self.age = 0
        self.asking = False                   # liberar --tudo esperando o SIM/NÃO
        self.done = False
        self.spots = []                       # (retângulo na tela de dentro, o que faz)
        self.version = 0                      # muda quando a tela muda (o celular pede a imagem nova)
        self._dodge = 0
        self._repeat = 0
        self._last_dir = 0

    def first_screen(self):
        return "inicio"

    @property
    def busy(self):
        return bool(self.queue)

    def commands(self):
        return PC_COMMANDS

    def menu_commands(self):
        return PC_MENU

    # ── listas ───────────────────────────────
    def rows(self):
        """As linhas da tela atual: (o que faz, texto, texto da direita)."""
        if self.reading is not None:
            return [("ler:voltar", "VOLTAR", "")]
        if self.screen == "inicio":
            return [("open:arquivos", "ARQUIVOS", f"{len(FILES)}"), ("open:navegador", "NAVEGADOR", "SITES"),
                    ("open:terminal", "TERMINAL", ">_"), ("desligar", "DESLIGAR", "")]
        if self.screen == "arquivos":
            return [(f"arq:{i}", name, "") for i, (name, _) in enumerate(FILES)] + [("close", "VOLTAR", "")]
        if self.screen == "navegador":
            return [(f"pag:{i}", name, "") for i, (name, *_rest) in enumerate(PAGES)] + [("close", "VOLTAR", "")]
        if self.screen == "terminal":
            if self.busy:
                return []
            if self.asking:
                return [("cmd:s", "SIM", ""), ("cmd:n", "NÃO", "")]
            return [(f"cmd:{c}", c.upper() if len(c) <= 24 else c[:22].upper() + "..", "")
                    for c in self.menu_commands()]
        return []

    def move(self, step):
        rows = self.rows()
        if not rows:
            return
        self.sel = (self.sel + step) % len(rows)
        self.version += 1
        self.match.assets.play("click", 0.2)

    def go(self, screen):
        self.screen = screen
        self.sel = 0
        self.top = 0
        self.reading = None
        self.version += 1

    # ── cliques ──────────────────────────────
    def spot(self, rect, key, origin):
        self.spots.append((pygame.Rect(rect).move(-origin[0], -origin[1]), key))

    def _layout(self):
        """Desenha a tela de dentro fora da vista, só para saber onde fica cada coisa tocável."""
        surf = pygame.Surface((INNER_W, INNER_H))
        self.draw_inner(surf, self.match.game.ui, surf.get_rect())

    def click(self, x, y):
        """Toque do celular no ponto x, y da tela de dentro: marca e roda a linha tocada."""
        self._layout()
        for rect, key in reversed(self.spots):
            if rect.collidepoint(x, y):
                rows = [k for k, _, _ in self.rows()]
                if key in rows:
                    self.sel = rows.index(key)
                self.press(key)
                return key
        return None

    def confirm(self):
        """ATACAR: roda a linha marcada."""
        rows = self.rows()
        if rows:
            self.press(rows[min(self.sel, len(rows) - 1)][0])

    def press(self, key):
        """O que cada linha faz."""
        self.version += 1
        if self.busy:
            return
        self.match.assets.play("click", 0.3)
        if key == "ler:voltar":
            self.reading = None
        elif key.startswith("open:"):
            self.open_app(key[5:])
        elif key == "desligar":
            self.done = True
        elif key == "close":
            self.close_app()
        elif key.startswith("arq:"):
            name, text = FILES[int(key[4:]) % len(FILES)]
            self.reading = (name, (text,), (40, 70, 120))
        elif key.startswith("pag:"):
            i = int(key[4:]) % len(PAGES)
            name, url, color, _ = PAGES[i]
            self.reading = (name, (url,) + tuple(self.page_lines(i)[1:]), color)
        elif key.startswith("cmd:"):
            self.enter_command(key[4:])

    def open_app(self, name):
        self.go(name)
        if name == "terminal" and not self.lines:
            self.say(f"{self.title} · ESCOLHA ABAIXO", GRAY)

    def close_app(self):
        self.asking = False
        self.go(self.first_screen() if self.screen != "login" else "login")

    def page_lines(self, i):
        name, _url, _color, lines = PAGES[i % len(PAGES)]
        return wiki_lines() if name == "SOULWIKI" else lines

    def enter_command(self, text):
        command = normalize(text)
        if self.asking:
            self.say(self.prompt + ("S" if command in ("s", "sim") else "N"), GRAY, 2)
            self.asking = False
            self.sel = 0
            if command in ("s", "sim"):
                self.run_unlock()
            else:
                self.say("  NADA FOI MUDADO.", HK)
            return
        self.say(self.prompt + text, GRAY, 2)
        if command:
            self.run(command)

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
        _, y = inp.axis()
        d = 1 if y > STICK else -1 if y < -STICK else 0
        if d and (d != self._last_dir or self._repeat <= 0):
            self.move(d)
            self._repeat = REPEAT * (2 if d != self._last_dir else 1)
        self._repeat -= 1
        self._last_dir = d
        if inp.pressed("attack") or inp.pressed("confirm"):
            self.confirm()
        return True

    def back(self):
        """ESQUIVA (ou VOLTAR): fecha o arquivo/site, depois volta à tela inicial; nela, desliga."""
        self.match.assets.play("cancel", 0.3)
        self.version += 1
        if self.busy:
            return True                       # no meio do comando não dá para sair
        if self.reading is not None:
            self.reading = None
            return True
        if self.screen in ("inicio", "login"):
            return False
        self.close_app()
        return True

    def pick(self, key):
        """Pedido do celular: ``pc:tap:x,y`` (0 a 1 na cópia da tela) ou ``voltar``."""
        if key.startswith("pc:tap:"):
            try:
                u, v = (float(n) for n in key[7:].split(","))
            except ValueError:
                return False
            if 0 <= u <= 1 and 0 <= v <= 1:
                self.click(u * INNER_W, v * INNER_H)
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
            self.say("  ARQUIVO NÃO ENCONTRADO.", AMBER)
            return
        if command == "liberar --tudo":
            if freed():
                self.say("  JÁ ESTÁ TUDO LIBERADO.", HK)
                return
            self.say("  LIBERA OS 4 CAPÍTULOS, OS", AMBER, 8)
            self.say("  4 CORROMPIDOS NO DUELO E", AMBER, 8)
            self.say("  AS PORTAS. SEM RECORDE.", AMBER, 8)
            self.say("  CONTINUAR? (S/N)", AMBER, 8, action=self._ask)
            return
        known = dict(self.commands())
        if command in known:
            for text, color in known[command]:
                self.say(text, color, 10)
            return
        self.say("  COMANDO NÃO ENCONTRADO.", AMBER)

    def _off(self):
        self.done = True

    def _ask(self):
        self.asking = True
        self.sel = 0

    def run_unlock(self):
        for label in ("CAPÍTULOS", "CORROMPIDOS", "PORTAS"):
            self.say(f" [----------] {label}", HK, 2)
            for k in range(1, 11):
                self.say(f" [{'#' * k}{'-' * (10 - k)}] {label}{' OK' if k == 10 else ''}", HK, 4, replace=True)
        self.say("  TUDO LIBERADO.", HK, 50, action=self.unlock)

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
            "typing": False,                   # nada se digita: tudo é lista
            "focus": "",
            "buffer": "",
            "version": self.version,
            "ratio": round(INNER_W / INNER_H, 3),
            "fields": [],
            "souls": 0,
            "picked": None,
            "action": "",
            "mates": [],
            "items": [],
        }

    def png(self, ui):
        """A tela de dentro em PNG, para o celular."""
        surf = pygame.Surface((INNER_W, INNER_H))
        self.draw_inner(surf, ui, surf.get_rect())
        out = io.BytesIO()
        pygame.image.save(surf, out, "tela.png")
        return out.getvalue()

    def accent(self):
        return CAU

    # ── desenho ──────────────────────────────
    def size(self, ui):
        return self.W, self.H

    def window_rect(self, cam):
        """Ao lado do móvel (à direita; sem espaço, à esquerda), sem sair da tela nem cobrir o HUD."""
        sx, sy = cam.to_screen(*self.anchor)
        rect = pygame.Rect(0, 0, self.W, self.H)
        rect.midleft = (round(sx) + 84, round(sy) + 20)
        if rect.right > config.SCREEN_W - 8:
            rect.midright = (round(sx) - 84, round(sy) + 20)
        rect.x = max(8, min(config.SCREEN_W - self.W - 8, rect.x))
        rect.y = max(56, min(config.SCREEN_H - self.H - 80, rect.y))
        return rect

    def draw(self, screen, ui, cam, rect=None):
        rect = rect or self.window_rect(cam)
        f = self.fighter
        ui.panel(screen, rect, fill=theme.INK_2, accent=f.color)
        ui.text(screen, f"{f.label} · {self.device}", theme.XS, theme.BONE, (rect.x + 10, rect.y + 13), anchor="midleft")
        inner = pygame.Rect(rect.x + 10, rect.y + 24, INNER_W, INNER_H)
        clip = screen.get_clip()
        screen.set_clip(inner)
        self.draw_inner(screen, ui, inner)
        screen.set_clip(clip)
        foot = "ATACAR: ABRIR  ESQUIVA: VOLTAR"
        ui.text(screen, foot, theme.XS, theme.FAINT, (rect.centerx, rect.bottom - 11))
        line = pygame.Surface((inner.w, 1), pygame.SRCALPHA)        # linhas de TV antiga
        line.fill((0, 0, 0, 40))
        for yy in range(inner.y, inner.bottom, 3):
            screen.blit(line, (inner.x, yy))

    # cores da lista (o notebook troca para o verde hacker)
    ROW_BG, ROW_ON, ROW_EDGE, ROW_TEXT, ROW_DIM = (24, 32, 54), (60, 100, 160), (120, 170, 230), (235, 235, 240), (150, 160, 190)

    def draw_rows(self, s, ui, area, origin):
        """A lista da tela em ``area``; rola para a linha marcada ficar sempre à vista."""
        rows = self.rows()
        if not rows:
            return
        self.sel = min(self.sel, len(rows) - 1)
        fit = max(1, area.h // ROW_H)
        if self.sel < self.top:
            self.top = self.sel
        elif self.sel >= self.top + fit:
            self.top = self.sel - fit + 1
        self.top = max(0, min(self.top, len(rows) - fit))
        for i, (key, label, right) in enumerate(rows[self.top:self.top + fit]):
            row = pygame.Rect(area.x, area.y + i * ROW_H, area.w, ROW_H - 2)
            on = self.top + i == self.sel
            s.fill(self.ROW_ON if on else self.ROW_BG, row)
            if on:
                pygame.draw.rect(s, self.ROW_EDGE, row, 1)
            ui.text(s, label, theme.XS, self.ROW_TEXT, (row.x + 6, row.centery), anchor="midleft", shadow=False)
            if right:
                ui.text(s, right, theme.XS, self.ROW_DIM, (row.right - 6, row.centery), anchor="midright", shadow=False)
            self.spot(row, key, origin)
        x = area.right - 8                    # setinhas: tem mais linha em cima / embaixo
        if self.top > 0:
            pygame.draw.polygon(s, self.ROW_EDGE, [(x - 4, area.y + 5), (x + 4, area.y + 5), (x, area.y + 1)])
        if self.top + fit < len(rows):
            y = area.y + fit * ROW_H - 6
            pygame.draw.polygon(s, self.ROW_EDGE, [(x - 4, y), (x + 4, y), (x, y + 4)])

    def bar(self, s, ui, r, text, color):
        s.fill(color, (r.x, r.y, r.w, 14))
        ui.text(s, text, theme.XS, (255, 255, 255), (r.x + 6, r.y + 7), anchor="midleft", shadow=False)
        return pygame.Rect(r.x, r.y + 16, r.w, r.h - 16)

    def draw_inner(self, s, ui, r):
        self.spots = []
        self.wallpaper(s, ui, r)
        if self.reading is not None:
            self.draw_reading(s, ui, r)
        elif self.screen == "terminal":
            self.draw_terminal(s, ui, r)
        else:
            title = {"inicio": self.title, "arquivos": "ARQUIVOS", "navegador": "NAVEGADOR"}.get(self.screen, self.title)
            body = self.bar(s, ui, r, title, (40, 70, 120))
            self.draw_rows(s, ui, body.inflate(-8, -4), r.topleft)

    def draw_reading(self, s, ui, r):
        title, lines, color = self.reading
        body = self.bar(s, ui, r, title, color)
        n = len(self.rows())
        page = pygame.Rect(body.x + 4, body.y, body.w - 8, body.h - n * ROW_H - 4)
        s.fill((244, 238, 220), page)
        y = page.y + 8
        for text in lines:
            for part in ui.wrap(text, theme.XS, page.w - 12):
                if y < page.bottom - 4:
                    ui.text(s, part, theme.XS, (40, 40, 50), (page.x + 6, y), anchor="midleft", shadow=False)
                y += LINE_H
        self.draw_rows(s, ui, pygame.Rect(body.x + 4, page.bottom + 3, body.w - 8, n * ROW_H), r.topleft)

    def wallpaper(self, s, ui, r):
        for i in range(0, r.h, 4):
            k = i / r.h
            s.fill((16 + round(14 * k), 26 + round(8 * k), 46 + round(20 * k)), (r.x, r.y + i, r.w, 4))

    def console_colors(self):
        return (12, 12, 14), theme.BONE

    def draw_terminal(self, s, ui, r):
        body = self.bar(s, ui, r, "TERMINAL", (40, 70, 120))
        self.draw_console(s, ui, body)
        self.draw_rows(s, ui, pygame.Rect(body.x + 4, body.bottom - 3 * ROW_H - 2, body.w - 8, 3 * ROW_H), r.topleft)

    def draw_console(self, s, ui, body):
        bg, prompt_color = self.console_colors()
        busy = self.busy
        out = pygame.Rect(body.x, body.y, body.w, body.h - (0 if busy else 3 * ROW_H + 4))
        s.fill(bg, out)
        room = max(1, (out.h - 4) // LINE_H)
        shown = self.lines[-room:]
        for i, (text, color) in enumerate(shown):
            ui.text(s, text, theme.XS, color, (out.x + 4, out.y + 7 + i * LINE_H), anchor="midleft", shadow=False)


class HackerNotebook(Computer):
    """O notebook do Albeguinio: pede a senha (escolher o palpite certo), tem o alerta da mensagem e o
    terminal hacker, com a invasão do cristal que libera tudo (uns 6 segundos de animação)."""

    kind = "notebook"
    title = "ALBEGUINIO OS"
    device = "NOTEBOOK"
    prompt = "root# "
    ROW_BG, ROW_ON, ROW_EDGE, ROW_TEXT, ROW_DIM = (0, 0, 0), HK_D, HK, HK_L, HK

    def first_screen(self):
        return "inicio" if getattr(self.match, "notebook_open", False) else "login"

    def commands(self):
        return NB_COMMANDS

    def menu_commands(self):
        return NB_MENU

    def accent(self):
        return HK

    def rows(self):
        if self.reading is not None and self.reading[0] == "ALERTA":
            return [("vacuo", "DEIXAR NO VÁCUO", ""), ("ler:voltar", "VOLTAR", "")]
        if self.reading is None and self.screen == "login":
            return [] if self.busy else [(f"senha:{g}", g.upper(), "") for g in GUESSES]
        if self.reading is None and self.screen == "inicio":
            return [("open:terminal", "TERMINAL", ">_"), ("open:alerta", "ALERTA", "!"), ("desligar", "DESLIGAR", "")]
        rows = super().rows()
        if self.screen == "terminal" and not self.busy and not self.asking:
            rows = [(k, "SUDO ./INVASAO.SH" if k == f"cmd:{HACK}" else label, r) for k, label, r in rows]
        return rows

    def open_app(self, name):
        if name == "alerta":
            self.reading = ("ALERTA", ("> MENSAGEM NOVA DETECTADA", "> REMETENTE: DAIWONE",
                                       "> CONTEÚDO: \"oi sumido\"", "> RECOMENDAÇÃO: NÃO RESPONDER"), HK_D)
            self.sel = 0
            self.version += 1
            return
        if name == "terminal" and not self.lines:
            self.go("terminal")
            self.say("ALBEGUINIO OS · MODO HACKER", HK)
            self.say("ESCOLHA ABAIXO. OU NÃO.", HK_D)
            return
        super().open_app(name)

    def press(self, key):
        if key == "vacuo":
            self.version += 1
            self.reading = None
            self.match.popup(self.fighter.x, self.fighter.y - 80, "VÁCUO!", PINK)
            return
        if key.startswith("senha:"):
            self.version += 1
            if self.busy:
                return
            if normalize(key[6:]) == PASSWORD:
                self.say("ACESSO LIBERADO.", HK, 40, action=self._logged)
            else:
                self.say("SENHA ERRADA.", RED, 2)
                self.say("DICA: O QUE ELE MAIS OUVE.", AMBER, 10)
            return
        super().press(key)

    def _logged(self):
        self.match.notebook_open = True
        self.lines = []
        self.go("inicio")

    def run(self, command):
        if command.startswith("sudo ./invasao.sh") or command == "hackear cristal":
            if freed():
                self.say("  [!] O CRISTAL JÁ ESTÁ ABERTO.", HK)
                return
            self.run_unlock()
            return
        if command in ("ls", "dir"):
            self.say("  invasao.sh  (O RESTO É SEGREDO.)", HK)
            return
        super().run(command)

    def run_unlock(self):
        """A invasão do cristal: conexão, despejo de memória, quebra da senha, capítulos um a um e os
        corrompidos. Uns 6 segundos."""
        rng = random.Random(47)
        self.say("[*] CONECTANDO AO CRISTAL...", HK, 30)
        self.say("[*] PORTA 4747 ABERTA.", HK, 16)
        for _ in range(8):
            hexes = " ".join(f"{rng.randrange(256):02X}" for _ in range(5))
            self.say(f" 0x{rng.randrange(16 ** 4):04X} {hexes}", HK_D if rng.random() < 0.5 else HK, 5)
        self.say("[*] QUEBRANDO A SENHA...", AMBER, 10)
        for k in range(1, 9):
            guess = "".join(rng.choice("abcdefghijklmnopqrstuvwxyz ") for _ in range(9))
            self.say(f"    TENTATIVA {k:02d}: {guess}", RED, 3, replace=k > 1)
        self.say(f" SENHA ENCONTRADA: {PASSWORD}", PINK, 20, replace=True)
        for chapter in range(1, 5):
            label = f"CAP {chapter}"
            self.say(f"[+] {label} [----------]", HK, 2)
            for k in range(1, 11):
                self.say(f"[+] {label} [{'#' * k}{'-' * (10 - k)}]{' OK' if k == 10 else ''}", HK, 3,
                         replace=True)
        for name in ("ARYEL", "BORBA JR", "ALBEGUINIO", "CAUANZERA"):
            self.say(f"[+] {name}: DUELO", PINK, 11)
        self.say("[+] CRISTAL: CONCEDIDO", HK_L, 30, action=self._crystal)
        self.say("[+] TUDO LIBERADO.", HK_L, 50, action=self.unlock)

    def _crystal(self):
        self.crystal_at = self.match.frame

    # ── desenho ──────────────────────────────
    def wallpaper(self, s, ui, r):
        s.fill((4, 10, 6), r)
        rng = random.Random(9)
        t = self.match.frame
        for col in range(r.x + 6, r.right - 6, 14):                     # chuva de caracteres
            speed = rng.uniform(1.5, 3.5)
            head = r.y + (rng.randrange(r.h) + t * speed) % (r.h + 60) - 30
            for k in range(rng.randrange(3, 8)):
                y = head - k * 10
                if r.y < y < r.bottom:
                    c = (120, 200, 130) if k == 0 else (30, max(50, 140 - k * 16), 50)
                    ui.text(s, "01ABEGUINO$#%"[(col + k + t // 6) % 13], theme.XS, c, (col, round(y)), shadow=False)

    def bar(self, s, ui, r, text, color):
        s.fill(HK_D, (r.x, r.y, r.w, 14))
        ui.text(s, text, theme.XS, (200, 255, 210), (r.x + 6, r.y + 7), anchor="midleft", shadow=False)
        return pygame.Rect(r.x, r.y + 16, r.w, r.h - 16)

    def console_colors(self):
        return (0, 0, 0), HK_L

    def draw_inner(self, s, ui, r):
        if self.screen == "login" and self.reading is None:
            self.spots = []
            self.wallpaper(s, ui, r)
            body = self.bar(s, ui, r, "ENTRAR · SENHA?", HK_D)
            shown = self.lines[-2:] or [("QUAL É A SENHA?", HK)]
            s.fill((0, 0, 0), (body.x, body.y, body.w, 26))
            for i, (text, color) in enumerate(shown):
                ui.text(s, text[:LINE_CHARS], theme.XS, color, (body.x + 4, body.y + 7 + i * LINE_H), anchor="midleft",
                        shadow=False)
            self.draw_rows(s, ui, pygame.Rect(body.x + 4, body.y + 30, body.w - 8, body.h - 32), r.topleft)
            return
        super().draw_inner(s, ui, r)
        at = getattr(self, "crystal_at", None)
        if at is not None and self.screen == "terminal":
            from .scenes.campaign import draw_crystal
            draw_crystal(s, (r.right - 30, r.y + 40), 16, self.match.frame - at)

    def draw_terminal(self, s, ui, r):
        body = self.bar(s, ui, r, "root@albeguinio: ~", HK_D)
        self.draw_console(s, ui, body)
        self.draw_rows(s, ui, pygame.Rect(body.x + 4, body.bottom - 3 * ROW_H - 2, body.w - 8, 3 * ROW_H), r.topleft)


def make(match, fighter, kind, anchor):
    cls = HackerNotebook if kind == "notebook" else Computer
    return cls(match, fighter, anchor)


__all__ = ("Computer", "HackerNotebook", "free_everything", "freed", "make")
