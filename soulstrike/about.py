"""Conteúdo da tela Sobre o projeto: as páginas dos 4 pilares e os trechos de código mostrados.

Os trechos são cópias enxutas do código de verdade (com "..." onde há corte). O teste
tests/test_sobre.py confere que cada linha mostrada ainda existe no arquivo de origem.
"""
import re

from . import theme

CODE_COLS = 62          # cabe na caixa de código da tela sem passar da borda


class Page:
    def __init__(self, tab, idea, in_game, path, code, sprite):
        self.tab = tab              # nome na aba (e título da página)
        self.idea = idea            # o conceito em uma frase
        self.in_game = in_game      # onde ele aparece no Soul Strike
        self.path = path            # arquivo de onde o trecho veio
        self.code = code.strip("\n").split("\n")
        self.sprite = sprite        # personagem desenhado ao lado


PAGES = [
    Page("ENCAPSULAMENTO",
         "Cada objeto cuida dos próprios dados. Quem está de fora pede, não mexe direto.",
         "Ninguém tira vida de um lutador mexendo no hp. Quem causa dano chama take_damage(), que "
         "confere invulnerabilidade, armadura e escudo antes de descontar.",
         "soulstrike/fighter.py", '''
def take_damage(self, amount, sx=None, sy=None,
                attacker=None, match=None):
    if self.invulnerable or self.hp <= 0:
        return False
    ...
    if self.shield > 0:
        absorbed = min(self.shield, amount)
        self.shield -= absorbed
        amount -= absorbed
        ...
        if amount <= 0:
            self.hit_flash = 3
            return True
    dealt = min(amount, self.hp)
    self.hp -= dealt
    ...
    if attacker is not None:
        attacker.damage_dealt += dealt
        attacker.hits += 1
''', "tanque"),
    Page("ABSTRAÇÃO",
         "Dizer o que uma coisa faz, sem dizer como. Os detalhes ficam escondidos atrás de um contrato.",
         "Entity é uma classe abstrata: toda coisa da arena precisa saber update() e draw(). A partida "
         "só chama esses dois, seja um lutador, um tiro ou a bola.",
         "soulstrike/entities.py", '''
class Entity(ABC):
    """Tudo que existe na arena: tem posição,
    atualiza a cada quadro e se desenha."""
    ...
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.alive = True

    def distance_to(self, other):
        return math.hypot(self.x - other.x, self.y - other.y)
    ...
    @abstractmethod
    def update(self, match):
        """Avança um quadro de simulação."""

    @abstractmethod
    def draw(self, surf, camera):
        """Desenha no espaço do mundo (já deslocado
        pela câmera)."""
''', "guerreiro"),
    Page("HERANÇA",
         "Uma classe nova aproveita tudo de uma que já existe e muda só o que precisa.",
         "O gancho do Pirata é um tiro: herda de Bullet o voo e a colisão. Só reescreve on_hit() para "
         "puxar e atordoar quem acertou.",
         "soulstrike/entities.py", '''
class Hook(Bullet):
    """Gancho do Pirata: voa reto preso a uma
    corrente e puxa quem acertar."""

    SPEED = 15
    ...
    def on_hit(self, target, match):
        owner = self.owner
        dx, dy = owner.x - target.x, owner.y - target.y
        d = math.hypot(dx, dy)
        if d > 60:
            # para logo na frente do pirata,
            # no alcance do sabre
            target.pull(owner.x - dx / d * 48,
                        owner.y - dy / d * 48, frames=10)
        target.stun(26)
        match.popup(target.x, target.y - 62, "PUXOU",
                    theme.BRASS)
''', "pirata"),
    Page("POLIMORFISMO",
         "A mesma chamada, respostas diferentes. Quem chama não precisa saber qual classe está do "
         "outro lado.",
         "No futebol, o botão SUPER sempre chama power.use(). Cada poder responde com o seu "
         "activate(): a Arrancada dispara na corrida, o Gigante cresce e fica difícil de passar.",
         "soulstrike/soccer_powers.py", '''
class SoccerPower(ABC):
    ...
    def use(self, user, match):
        if user.super_cd > 0 or user.stunned:
            return False
        if self.needs_ball and not match.touching(user, 20):
            return False
        if not self.activate(user, match):
            return False
        user.super_cd = self.cooldown
        ...
        return True

class Arrancada(SoccerPower):
    def activate(self, user, match):
        user.sprint_timer = 3 * config.FPS
        return True

class Gigante(SoccerPower):
    def activate(self, user, match):
        user.giant_timer = 5 * config.FPS
        user.radius = 24
        match.camera.shake(5)
        return True
''', "geada"),
    Page("BASTIDORES",
         "O controle pelo celular chega por uma thread do servidor web, enquanto o jogo roda em outra.",
         "A trava (lock) impede as duas de mexerem nos dados juntas. E o número de sequência descarta "
         "pedido atrasado do Wi-Fi sem perder nenhum botão apertado.",
         "soulstrike/net/remote.py", '''
def apply_input(self, slot, sid, seq, held, counts,
                x=0.0, y=0.0):
    """Aplica um estado completo do controle.
    Devolve False se foi ignorado."""
    pad = self._pads.get(slot)
    ...
    with self._lock:
        if sid != pad.sid:                # página nova
            pad.sid, pad.seq, pad.counts = sid, -1, {}
        # apertos: contadores só sobem, então qualquer
        # pedido (mesmo atrasado) serve
        for action, n in counts.items():
            ...
            if n > pad.counts.get(action, 0):
                pad.counts[action] = n
                self._pressed.add(prefix + action)
        if seq <= pad.seq:
            return False                  # pedido atrasado
        pad.seq = seq
        ...
        return True
''', "velocista"),
]

# ── cores de sintaxe ─────────────────────────
KEYWORD = (198, 120, 221)
NAME = theme.SKY
STRING = theme.MOSS
COMMENT = theme.FAINT
NUMBER = theme.EMBER
SELF = (226, 132, 120)
DECORATOR = theme.BRASS
PUNCT = theme.MUTED
PLAIN = theme.BONE

KEYWORDS = {"def", "class", "if", "elif", "else", "return", "for", "in", "not", "or", "and", "with",
            "is", "None", "True", "False"}
_TOKEN = re.compile(r'(#.*$)|("""|"[^"]*")|(@\w+)|(\b\d+(?:\.\d+)?\b)|(\w+)|(\s+)|(.)')


def highlight(lines):
    """Lista de linhas de Python → para cada linha, lista de (texto, cor)."""
    result = []
    in_doc = False
    for line in lines:
        parts = []
        pos = 0
        while pos < len(line):
            if in_doc:
                end = line.find('"""', pos)
                stop = len(line) if end < 0 else end + 3
                parts.append((line[pos:stop], STRING))
                in_doc = end < 0
                pos = stop
                continue
            m = _TOKEN.match(line, pos)
            comment, string, deco, number, word, space, _ = m.groups()
            text = m.group(0)
            if comment:
                color = COMMENT
            elif string:
                color = STRING
                if string == '"""':
                    in_doc = True
            elif deco:
                color = DECORATOR
            elif number:
                color = NUMBER
            elif word:
                before = line[:pos].split()
                if word in KEYWORDS:
                    color = KEYWORD
                elif word == "self":
                    color = SELF
                elif (before and before[-1] in ("def", "class")) or line[m.end():m.end() + 1] == "(":
                    color = NAME
                else:
                    color = PLAIN
            elif space:
                color = PLAIN
            else:
                color = PUNCT
            parts.append((text, color))
            pos = m.end()
        result.append(parts)
    return result
