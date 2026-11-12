"""Segredos: detalhezinhos escondidos na Casa, na campanha e nos modos (reações a coisas que ninguém
espera que o jogador faça).

Tudo é discreto de propósito: nada de faixa no meio da tela, câmera lenta ou som alto. O jogo não
avisa que existe segredo; quem achou vê só um textinho pequeno perto do personagem, que some rápido.
Na primeira vez que a turma acha cada um, entram REWARD cacos no pote (o "+5" pequeno) e o segredo
vai para o CADERNO DE SEGREDOS, no computador do Cauanzera (os que faltam aparecem como ??? com uma
dica bem vaga).

Os achados ficam no progresso salvo (``progress``, chave KEY), numa lista só da turma.
"""
import time

from . import cacos, progress, theme

KEY = "segredos"
REWARD = 5                    # cacos na primeira vez que a turma acha cada segredo
POPUP_LIFE = 70               # quadros do textinho do segredo (o de dano dura 40)
PLACES = ("CASA", "CAMPANHA", "MODOS")

# (chave, lugar, nome que aparece no caderno depois de achado, dica vaga enquanto não acha)
SECRETS = (
    ("wifi", "CASA", "O WI-FI CAIU", "O ROTEADOR PARECE FRÁGIL"),
    ("madrugada", "CASA", "VAI DORMIR, RAPAZ", "A VITRINE TEM SONO"),
    ("de_novo", "CASA", "DE NOVO?!", "INSISTA NUMA CONVERSA"),
    ("cochilo", "CASA", "COCHILO NO SOFÁ", "O SOFÁ É CONFORTÁVEL"),
    ("espantalho", "CASA", "O ESPANTALHO SENTIU", "ELE NÃO ESPANTA NADA"),
    ("mangueira", "CASA", "MOLHOU O AMIGO", "A MANGUEIRA TEM PRESSÃO"),
    ("city", "CASA", "O CITY ENGASGOU", "NEM SEMPRE ELE PEGA DE PRIMEIRA"),
)
BY_KEY = {s[0]: s for s in SECRETS}


def _hour():
    return time.localtime().tm_hour


def madrugada():
    """Meia-noite às 5h no relógio do computador (a mesma hora que a luz da Casa usa)."""
    return 0 <= _hour() < 5


def found():
    """As chaves dos segredos que a turma já achou (só as que existem nesta versão)."""
    raw = progress.load().get(KEY)
    if not isinstance(raw, list):
        return set()
    return {k for k in raw if k in BY_KEY}


def is_found(key):
    return key in found()


def find(key, match=None, x=None, y=None):
    """Alguém achou o segredo ``key``. Na primeira vez: salva, põe REWARD cacos no pote e mostra o
    "+5" pequeno em (x, y), se der. Devolve True só na primeira vez."""
    if key not in BY_KEY:
        return False
    data = progress.load()
    raw = data.get(KEY)
    have = [k for k in raw if isinstance(k, str)] if isinstance(raw, list) else []
    if key in have:
        return False
    have.append(key)
    data[KEY] = have
    progress.save(data)
    cacos.add(REWARD)
    if match is not None and x is not None and y is not None:
        hint(match, x, y, f"+{REWARD} CACOS", theme.BRASS)
    return True


def hint(match, x, y, text, color=theme.BONE, life=POPUP_LIFE):
    """O textinho de um segredo: pequeno, perto de quem fez, e some sozinho."""
    match.popup(x, y, text, color, life=life)


def notebook():
    """As linhas do CADERNO DE SEGREDOS, por lugar: {lugar: [(achado, texto), ...]}."""
    have = found()
    pages = {place: [] for place in PLACES}
    for key, place, name, tip in SECRETS:
        pages[place].append((True, name) if key in have else (False, f"??? · {tip}"))
    return pages


def count():
    return len(found()), len(SECRETS)
