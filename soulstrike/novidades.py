"""Novidades de cada versão: aparecem uma vez quando o jogo abre numa versão nova.

Vale para qualquer instalação (pasta, .deb ou .exe), porque o texto vem junto com o código.
Ao subir a versão em __init__.py, acrescente aqui o que mudou, em frases curtas.

Uma versão pode ser só uma lista de frases (uma página) ou uma lista de páginas, cada uma
um dicionário com título, cena animada (ver NEWS_SCENES em scenes/menus.py) e frases.
"""
from . import __version__, settings
from .updater import parse_version

NEWS = {
    "1.7.0": [
        {"title": "ANIMAÇÕES NOVAS", "scene": "enterrada", "lines": [
            "Todos os heróis ganharam poses de pulo, arremesso, enterrada, toco, chute, carrinho e comemoração.",
            "Basquete: câmera lenta ao cravar, SWISH, PREGADO NA TABELA e poeira na queda.",
            "Futebol: chute com rastro, carrinho deitado, bola no pé e rede que estufa no gol.",
        ]},
        {"title": "FUTEBOL MAIS JOGADO", "scene": "futebol", "lines": [
            "Chute com curva (analógico de lado ao soltar), domínio orientado e tabela (PASSE de novo).",
            "Goleiro com luvas e área tracejada; a ESQUIVA vira ponte. Anel e alvo na mira do passe.",
            "Replay do gol em câmera lenta, e a CPU abre espaço, faz tabela e vira goleiro.",
        ]},
        {"title": "PÊNALTIS DE FRENTE", "scene": "penalti", "lines": [
            "Novo desempate do futebol (tecla T: 3 MIN + PÊNALTIS), com a câmera atrás de quem bate.",
            "O canto não aparece na TV: é a direção do analógico ao soltar o CHUTE, ou a grade no celular.",
            "Cada herói bate e defende do seu jeito, e toda vantagem tem um preço.",
        ]},
        {"title": "DISPUTA DE PÊNALTIS", "scene": "disputa", "lines": [
            "Modos novos: DISPUTA DE PÊNALTIS, TREINO DE PÊNALTIS e DESAFIO DO GOLEIRO.",
            "Ordem dos batedores, colinha do goleiro, catimba com cartão, pressão na decisiva e narração.",
            "Comemoração e som próprios de cada herói, e estatísticas com recordes salvos.",
        ]},
    ],
    "1.6.0": [
        {"title": "ALMAS DE CADA UM", "scene": "almas", "lines": [
            "Cada jogador tem a sua carteira de almas, ao lado da vida no HUD.",
            "Quem dá o golpe final leva mais; os outros vivos ganham um pouco. No chefão, todos ganham igual.",
            "Na loja dá para DOAR almas para um companheiro.",
        ]},
        {"title": "LOJA NO CELULAR", "scene": "loja", "lines": [
            "O saldo aparece no celular e sobe um +N a cada inimigo.",
            "Perto da banca, ATACAR abre a loja também no celular: toque para marcar, COMPRAR para comprar.",
            "Vale para a loja, o ferreiro e o altar das maldições.",
        ]},
        {"title": "CONFIGURAR HUD", "scene": "hud", "lines": [
            "No celular, o botão HUD deixa arrastar e mudar o tamanho dos botões e do analógico.",
            "Transparência, analógico fixo ou solto, lado de canhoto e vibração.",
            "Fica salvo no celular, separado para duelo, futebol e basquete.",
        ]},
        {"title": "E MAIS", "scene": "novidades", "lines": [
            "Esta tela nova de novidades, com páginas. Em OPÇÕES > NOVIDADES dá para ver de novo.",
            "O celular mostra o resumo das novidades enquanto a tela está aberta.",
            "Sons novos de almas, de compra e da loja.",
        ]},
    ],
    "1.5.2": [
        "Martelo do Trovão Eterno: o arremesso vai mais longe e persegue até 3 inimigos, um depois do outro, antes de voltar.",
    ],
    "1.5.1": [
        "Treino: o arsenal tem todas as armas do jogo para testar, até as roubadas e as 8 forjadas.",
        "Chegue perto do suporte de armas e aperte ATACAR. HABILIDADE devolve as armas do herói.",
        "Arte nova para as 8 forjadas e para várias raras e roubadas.",
        "As armas raras brilham na mão, soltam faíscas e deixam rastro de luz nos tiros e nos golpes.",
        "Raios com galhos e clarão, feixes que brilham, onda solar e dragão de fogo mais bonitos.",
    ],
    "1.5.0": [
        "Duelo: antes de cada round, escolha a arma de tiro e a de perto. Quem perdeu ganha mais uma opção.",
        "Esquiva perfeita: esquive bem na hora do golpe e a esquiva volta na hora, com a habilidade mais carregada.",
        "Futebol e basquete: CPU com dificuldade, tamanho da partida de futebol (tecla T) e reação para quem toma lavada.",
        "Basquete: empurrão no arremesso e ponte aérea sem SUPER para quem corta para a cesta.",
        "Treino novo de futebol e de basquete, com lições passo a passo.",
        "Campanha: inimigos derrubam armas de outros heróis, com cor de raridade.",
        "Almas, mercado com loja e ferreiro, encantos de fogo, gelo e raio.",
        "Ferreiro: funda as três armas numa das 8 armas forjadas, novas e muito fortes.",
        "O Martelo do Trovão Eterno é arremessado no 3º golpe e volta para a mão, soltando raios.",
        "Altar das maldições: aceite um desafio e ganhe uma melhoria a mais.",
        "Em grupo, a câmera afasta mais e a coleira ficou maior e visível.",
    ],
    "1.4.1": [
        "Basquete: o passe agora é teleguiado e vai certinho na mão do companheiro, mesmo no contra-ataque.",
        "Apontou para o lado errado? O passe vai para o companheiro do mesmo jeito.",
        "Quem estiver na frente de quem recebe ainda pode cortar o passe.",
    ],
    "1.4.0": [
        "Basquete: 1 minuto de aquecimento antes da bola ao alto, cada time no seu lado e cada um com a sua bola.",
        "No aquecimento, a cesta não conta: é para treinar a barrinha, a enterrada e a finta.",
        "Aperte SUPER para dizer que está pronto: quando todos estiverem, a partida começa na hora.",
    ],
    "1.3.0": [
        "Basquete: o SUPER agora funciona! Cada personagem tem o seu, e ele volta a cada 8 segundos.",
        "Defesa: Marcação Colada, Toco Voador, Tampa no Aro, Gigante, Congelar, Gancho e Hack.",
        "Ataque: Mão Quente, Enterrada Voadora (da linha de 3), Bola Fantasma, Alley-oop Trovão e mais.",
        "Todo SUPER de ataque tem um contra. Ex.: a enterrada do Exo arranca a Tampa no Aro.",
        "Enterradas novas: Giro 360 e Pendurado no Aro. Pegando fogo ou com SUPER: Moinho e Cambalhota.",
        "Escolha a quadra antes da partida com TAB: Ginásio, Quadra de Rua ou Arena Soul Strike.",
        "Quem pega fogo deixa o aro em chamas. Sons novos de quique, aro, rede, toco e buzina.",
        "No fim, o placar mostra os pontos de cada um, o que mais ele fez (enterradas, tocos ou roubos) e o destaque.",
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


def pages_of(version, entry):
    """[(versão, título, cena, frases)]: uma versão só com frases vira uma página sem cena."""
    if all(isinstance(item, str) for item in entry):
        return [(version, f"VERSÃO {version}", None, list(entry))]
    return [(version, page["title"], page.get("scene"), list(page["lines"])) for page in entry]


def summary(entry):
    """Uma frase por página (para o celular): o título, ou as frases de uma versão antiga."""
    if all(isinstance(item, str) for item in entry):
        return list(entry)
    return [page["title"] + ": " + page["lines"][0] for page in entry]


def history():
    """Todas as versões, da mais nova para a mais velha (OPÇÕES > NOVIDADES)."""
    return sorted(NEWS.items(), key=lambda item: parse_version(item[0]), reverse=True)


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
