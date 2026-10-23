"""Novidades de cada versão: aparecem uma vez quando o jogo abre numa versão nova.

Vale para qualquer instalação (pasta, .deb ou .exe), porque o texto vem junto com o código.
Ao subir a versão em __init__.py, acrescente aqui o que mudou, em frases curtas.
"""
from . import __version__, settings
from .updater import parse_version

NEWS = {
    "1.3.0": [
        "Basquete: o SUPER agora funciona! Cada personagem tem o seu, e ele volta a cada 8 segundos.",
        "Defesa: Marcação Colada, Toco Voador, Tampa no Aro, Gigante, Congelar, Gancho e Hack.",
        "Ataque: Mão Quente, Enterrada Voadora (da linha de 3), Bola Fantasma, Alley-oop Trovão e mais.",
        "Todo SUPER de ataque tem um contra. Ex.: a enterrada do Exo arranca a Tampa no Aro.",
        "A caixa do SUPER aparece no canto da tela, e a escolha de personagem mostra o poder do basquete.",
    ],
    "1.2.0": [
        "Basquete: segure CHUTAR para pular e solte na faixa verde da barrinha. De 3, a faixa é estreita.",
        "Dentro do garrafão, CHUTAR enterra sozinho, voando até o aro.",
        "Sem a bola, CHUTAR pula para dar toco ou pegar o rebote mais alto.",
        "CORTE com a bola faz a finta; sem a bola, rouba (melhor de lado ou por trás).",
        "MARCAR com a bola protege; sem a bola, cola no adversário.",
        "Três cestas seguidas do mesmo jogador: PEGANDO FOGO, com a faixa verde quase inteira.",
        "Esta tela de novidades aparece sempre que o jogo for atualizado.",
    ],
    "1.1.0": [
        "Novo modo BASQUETE 2 x 2, com três quadras: Ginásio, Quadra de Rua e Arena Soul Strike.",
        "Cesta de 2 e de 3, enterrada no garrafão, posse de 10 segundos e dois tempos de 2 minutos.",
        "No empate, quem fizer a próxima cesta vence.",
    ],
}


def pending(seen, current=__version__):
    """Versões com novidade que o jogador ainda não viu, da mais nova para a mais velha.

    Sem registro (jogo instalado antes desta tela existir, ou instalado agora), mostra só a
    da versão atual."""
    now = parse_version(current)
    if not seen:
        return [(current, NEWS[current])] if current in NEWS else []
    last = parse_version(seen)
    found = [(v, lines) for v, lines in NEWS.items() if last < parse_version(v) <= now]
    return sorted(found, key=lambda item: parse_version(item[0]), reverse=True)


def to_show():
    return pending(settings.get("versao_vista"))


def mark_seen(current=__version__):
    settings.change("versao_vista", current)
