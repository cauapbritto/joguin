"""Novidades de cada versão: aparecem uma vez quando o jogo abre numa versão nova.

Vale para qualquer instalação (pasta, .deb ou .exe), porque o texto vem junto com o código.
Ao subir a versão em __init__.py, acrescente aqui o que mudou, em frases curtas.

Uma versão pode ser só uma lista de frases (uma página) ou uma lista de páginas, cada uma
um dicionário com título, cena animada (ver NEWS_SCENES em scenes/menus.py) e frases.
"""
from . import __version__, settings
from .updater import parse_version

NEWS = {
    "1.18.0": [
        {"title": "A FASE VAI EM FRENTE", "scene": "lag", "lines": [
            "Ninguém volta mais para o acampamento: a fase começa numa sala inicial com a lojinha e o altar.",
            "Depois da masmorra 1 vem um corredor com o baú, a fogueira, a loja, o ferreiro e o armário.",
            "A masmorra 2 termina num portal que leva o grupo direto para a próxima fase.",
        ]},
        {"title": "TODOS JUNTOS NA PORTA", "scene": "hud", "lines": [
            "Portas e portal só levam o grupo com todo mundo dentro: aí corre uma contagem de 2 segundos.",
            "Quem sair zera a contagem. Celular desconectado não trava ninguém, e o herói vai junto.",
            "Se alguém travar por 20 segundos, o P1 pode ir assim mesmo com ATACAR.",
        ]},
        {"title": "INICIAR BATALHA", "scene": "perigos", "lines": [
            "Na entrada de cada masmorra tem um botão: os inimigos só saem quando alguém aperta.",
            "Dá tempo de o grupo se arrumar, trocar de arma e respirar antes da luta.",
        ]},
    ],
    "1.16.0": [
        {"title": "LOJA E FERREIRO NO CELULAR", "scene": "loja", "lines": [
            "Cada linha da loja e do ferreiro no celular mostra a imagem da arma.",
            "No ferreiro, o celular mostra no que a arma vira: o nível, o dano e o pente de antes e depois.",
            "Os três encantos viram botões, e a fusão mostra a forjada que sai (ou a silhueta, se for segredo).",
        ]},
        {"title": "VITRINE DA LOJA", "scene": "loja", "lines": [
            "A loja mostra duas armas de outros heróis, uma de tiro e uma de perto, por 40 almas cada.",
            "Ela vai direto para a mão; a que ela troca fica no chão, na frente da banca.",
            "A ARMA SURPRESA (25) entra no lugar da arma sorteada. A energia aparece ao lado das almas.",
        ]},
    ],
    "1.15.0": [
        {"title": "TUDO EM DOBRO DE DETALHE", "scene": "modos", "lines": [
            "Todos os personagens, criaturas e as 68 armas redesenhados com o dobro de detalhe.",
            "Mais volume: sombra fria, brilho quente e contorno fino. Nenhum desenho cortado na borda.",
            "Chão, paredes, explosões e itens também foram lapidados.",
        ]},
        {"title": "TELAS NOVAS", "scene": "novidades", "lines": [
            "Logo em degradê com brilho, brasas subindo nos menus e o elenco num palco no início.",
            "Na escolha de lutadores, cada um ganha um canhão de luz na cor do jogador.",
            "No basquete a escolha mostra a quadra e o SUPER certo, também no celular.",
        ]},
        {"title": "TV ANTIGA", "scene": "loja", "lines": [
            "Loja, pausa, menus de cada jogador e a escolha de armas abrem e fecham como TV de tubo.",
        ]},
    ],
    "1.14.0": [
        {"title": "CAPÍTULO 4: MANSÃO DO CARIMBO", "scene": "mansao", "lines": [
            "O último capítulo: Cuiabrasa, estado de Mato Grelhado, 47°C na sombra.",
            "O Cauanzera ligou a lasquinha do caco no servidor e nasceu a IARA. Deu ruim.",
            "Três fases novas: Sede, Pátio e CPD, Gabinete. Dez monstros da repartição.",
        ]},
        {"title": "PERIGOS DA MANSÃO", "scene": "perigos", "lines": [
            "A fila anda e arrasta quem está nela. Pilhas de processo caem do alto.",
            "No pátio, fique na sombra. No CPD, ATACAR perto dos no-breaks traz a luz de volta.",
            "Na sala de reunião, a apresentação puxa todo mundo para o meio.",
        ]},
        {"title": "O CHEFE FINAL", "scene": "iara", "lines": [
            "Cauanzera Corrompido em 3 etapas: ele, a IARA presa por 4 cabos e a fusão dos dois.",
            "Quando a vida dele baixar, a turma chega para ajudar. O golpe final é tirar da tomada.",
        ]},
        {"title": "ZEROU? TEM PRESENTE", "scene": "novidades", "lines": [
            "Cauanzera Corrompido jogável, mapas de Cuiabrasa no duelo, futebol e basquete.",
            "REUNIÃO DOS CORROMPIDOS: os 4 chefes em sequência. CINEMA: todas as histórias.",
            "Selos de zerado por dificuldade, o crachá da Mansão nas regras e a IARA mascote.",
        ]},
    ],
    "1.13.0": [
        {"title": "CINCO DIFICULDADES", "scene": "perigos", "lines": [
            "A campanha agora tem FÁCIL, NORMAL, DIFÍCIL, IBRAHIM e BORBA.",
            "IBRAHIM: toma cuidado jovi, esse é difícil. Inimigos com poderes extras e só 1 continue.",
            "BORBA: fenomenal. Sem cura entre as fases e cada um só é levantado uma vez por masmorra.",
        ]},
        {"title": "ENERGIA", "scene": "almas", "lines": [
            "Armas raras, roubadas e forjadas gastam energia (barra azul de 200) em vez de pente.",
            "A energia não volta sozinha: pegue os orbes azuis que os inimigos soltam.",
            "Sem energia, a arma de tiro vira arma de bater. A arma do seu herói é sempre de graça.",
        ]},
        {"title": "LARGAR A ARMA", "scene": "loja", "lines": [
            "LARGAR ARMA agora é um botão: LB, touchpad do PlayStation, R no teclado ou LARGAR no celular.",
            "No acampamento, o ARMÁRIO guarda até 4 armas do grupo para quem quiser pegar depois.",
        ]},
    ],
    "1.12.0": [
        {"title": "CAPÍTULO 3: CLEPALOVERS", "scene": "clinica", "lines": [
            "A campanha ganhou o capítulo 3: a Clínica Clepalovers, tomada pelo caco do fragmento.",
            "Três fases novas: Recepção, Ala de Procedimentos e Suíte VIP, com dez monstros novos.",
            "Zerou o capítulo 2? CAMPANHA: CAPÍTULO 3 no menu começa direto nele, com almas e melhorias.",
        ]},
        {"title": "PERIGOS DA CLÍNICA", "scene": "clinica", "lines": [
            "Piso molhado faz escorregar, o laser acende ladrilhos rosa e o vapor do spa tapa a sala.",
            "No spa, ATACAR perto dos três registros fecha o vapor.",
            "Espelhos vivos soltam o reflexo de um herói: quebrem antes.",
        ]},
        {"title": "OI SUMIDO", "scene": "oi_sumido", "lines": [
            "A Daiwone aparece em algumas salas digitando. Se a mensagem chegar, o balão tapa a tela.",
            "Bater nela enquanto digita cancela. Com 3 acertos ela vai embora e deixa almas.",
        ]},
        {"title": "LARGAR A ARMA", "scene": "loja", "lines": [
            "Na campanha, segure TROCAR ARMA por meio segundo para largar a arma da mão no chão.",
            "A rara do baú sai da 3ª vaga; a de outro herói volta a ser a arma do seu herói.",
            "Toque rápido continua só trocando de arma.",
        ]},
        {"title": "ALBEGUINIO CORROMPIDO", "scene": "clepalovers", "lines": [
            "O chefe do administrativo: boletos em leque, carimbo gigante e a agenda cheia de argila.",
            "Com metade da vida ele se HARMONIZA: cortem os 3 cabos da máquina para ele voltar a sentir dano.",
            "Zerou o capítulo 3? Ele fica liberado em todos os modos, com Boleto e Carimbo.",
        ]},
    ],
    "1.11.0": [
        {"title": "PASSE TELEGUIADO", "scene": "futebol", "lines": [
            "No futebol, o passe agora é igual ao do basquete: aperte e a bola sai na hora, sem barra de força.",
            "A bola vai teleguiada até o pé do companheiro, mesmo se ele estiver correndo.",
            "Com a bola no pé, um anel mostra quem vai receber.",
        ]},
        {"title": "POR CIMA SOZINHO", "scene": "futebol", "lines": [
            "Companheiro longe ou adversário no meio: o passe vira lançamento sem você segurar nada.",
            "O lançamento cai no pé dele, e o cruzamento na ponta escolhe a altura do mesmo jeito.",
            "Quem entrar na frente do passe ainda corta.",
        ]},
    ],
    "1.10.2": [
        {"title": "VIBRAÇÃO", "scene": "controle", "lines": [
            "Controles de PlayStation pelo Bluetooth agora vibram.",
            "Se o controle não aceitar a vibração de um jeito, o jogo tenta de outro.",
            "Apanhar vibra um pouco mais forte.",
        ]},
        {"title": "TESTE A VIBRAÇÃO", "scene": "controle", "lines": [
            "OPÇÕES > CONTROLES: aperte o gatilho direito (R2/RT) ou VIBRAR FORTE para uma vibração no máximo.",
            "No modo teste (Y), cada botão apertado também dá uma vibrada.",
            "Embaixo aparece VIBRAÇÃO: OK ou se o controle não aceitou.",
        ]},
    ],
    "1.10.1": [
        {"title": "???", "scene": "clepalovers", "lines": [
            "Terminou o capítulo 2? Leia a história do final até a última página.",
            "Alguém guardou um caquinho do fragmento...",
        ]},
        {"title": "ULTRA NA QUADRA", "scene": "ultra", "lines": [
            "A página do ULTRA e dos orbes nas novidades ganhou um herói na quadra, sem textos encavalados.",
        ]},
    ],
    "1.10.0": [
        {"title": "BASQUETE 1 x 1", "scene": "enterrada", "lines": [
            "Modo novo no cartão do Basquete: um contra um com poder demais. Sem o P2, joga contra a CPU.",
            "O SUPER volta 4 s depois que o efeito acaba, e 2 cestas seguidas já pegam fogo.",
            "Um tempo de 3 minutos ou 21 pontos, o que vier primeiro.",
        ]},
        {"title": "ULTRA E ORBES", "scene": "ultra", "lines": [
            "Cada herói tem um ULTRA: a barra enche com cesta, toco e roubo. Barra cheia, aperte SUPER.",
            "ESQUIVA (CORTE) bem na hora anula o ULTRA de ataque; o de defesa também segura.",
            "A cada 12 s aparece um orbe: FOGO, ÍMÃ (o rebote vem para você), TURBO ou ESCUDO (aguenta um roubo).",
        ]},
    ],
    "1.9.0": [
        {"title": "MODOS ORGANIZADOS", "scene": "modos", "lines": [
            "JOGAR agora mostra quatro cartões: Campanha, Duelos, Futebol e Basquete.",
            "Cada um abre os seus modos, com os treinos dentro da modalidade. LB e RB trocam de cartão.",
            "O jogo lembra o último modo jogado, e o Y continua a campanha salva.",
        ]},
        {"title": "TELA DO CONTROLE", "scene": "controle", "lines": [
            "CONTROLES com um controle ligado mostra ele desenhado: Xbox, PlayStation, Nintendo ou Joy-Con.",
            "Troque o que cada botão faz na luta e nos esportes, ou escolha um perfil pronto.",
            "Modo teste mostra o botão apertado e ajusta a zona morta do analógico. O controle vibra (dá para desligar).",
        ]},
        {"title": "P1 MANDA NA PARTIDA", "scene": "coroa", "lines": [
            "O P1 tem a coroa: só ele pausa e navega os menus (no treino ou sozinho, qualquer um pausa).",
            "Na escolha de personagens, START do P1 abre as regras. Na pausa, troque regras com a bola rolando.",
            "START dos outros: pedir pausa ou sair (vira CPU). Um controle novo assume uma CPU no meio do jogo.",
        ]},
        {"title": "REVANCHE E RECORDES", "scene": "novidades", "lines": [
            "O título oferece a REVANCHE da última partida, direto, sem passar pelos menus.",
            "ESTATÍSTICAS: partidas por modalidade, vitórias contra a CPU, heróis mais usados e recordes.",
        ]},
    ],
    "1.8.1": [
        {"title": "PÊNALTIS COM CARA DE FIFA", "scene": "bate", "lines": [
            "A bola ficou bem maior, com gomos que giram no chute.",
            "Quem bate leva a perna para trás e o pé encosta na bola: o jogo congela um instante no contato.",
            "A câmera aproxima do gol enquanto a bola voa.",
        ]},
        {"title": "GOLEIRO SEM CORTES", "scene": "agarra", "lines": [
            "O goleiro quica na ponta dos pés, dá o impulso e se estica no ar.",
            "Na defesa, agarra a bola, cai abraçado com ela e levanta com a bola no alto.",
            "Tomou o gol? Cai na grama e levanta de cabeça baixa.",
        ]},
    ],
    "1.8.0": [
        {"title": "CAPÍTULO 2: LAG LOBBY", "scene": "lag", "lines": [
            "Depois do Templo Gelado, a campanha continua dentro da Lag Lobby, tomada pela Patrulha Cinza.",
            "Três fases novas: Recepção, Data Center e Cobertura, com acampamentos, cofres e lojas da empresa.",
            "Zerou o capítulo 1? CAMPANHA: CAPÍTULO 2 no menu começa direto nele, com almas e melhorias.",
        ]},
        {"title": "INIMIGOS E PERIGOS", "scene": "perigos", "lines": [
            "Drone que mergulha pela linha vermelha, miliciano que recarrega exposto e torreta que mira antes.",
            "O Miliciano Exo investe e fica PRESO na parede: é a hora de bater.",
            "Laser no corredor de servidores (a linha pontilhada avisa) e vento no heliponto: se escondam atrás das paredes.",
        ]},
        {"title": "CHEFÃO: BORBA JR CORROMPIDO", "scene": "chefao_lag", "lines": [
            "Canhão de Pulso com a linha azul de aviso, três socos com onda de choque e o salto do exo.",
            "A blindagem quase não deixa passar dano: esperem ele SUPERAQUECER e ataquem.",
            "Zerou o capítulo 2? O Borba Jr Corrompido fica liberado nos outros modos.",
        ]},
        {"title": "ARMAS DA LAG LOBBY", "scene": "armas_lag", "lines": [
            "Taser de Rede (prende), Rifle de Plasma (carregado atravessa) e Drone de Bolso (atira sozinho).",
            "Teclado Mecânico e Manopla do Exo: o 3º golpe seguido solta teclas ou abre uma onda.",
            "Escudo de Choque: segure para segurar os tiros e solte para o empurrão. Sons e música novos.",
        ]},
    ],
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
