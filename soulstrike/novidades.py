"""Novidades de cada versão: aparecem uma vez quando o jogo abre numa versão nova.

Vale para qualquer instalação (pasta, .deb ou .exe), porque o texto vem junto com o código.
Ao subir a versão em __init__.py, acrescente aqui o que mudou, em frases curtas.

Uma versão pode ser só uma lista de frases (uma página) ou uma lista de páginas, cada uma
um dicionário com título, cena animada (ver NEWS_SCENES em scenes/menus.py) e frases.
Opcional: "tv" escolhe uma imagem feita para o plantão (FOOTAGE em scenes/plantao.py, ou
"estudio" para a bancada dos âncoras).
"""
from . import __version__, settings
from .updater import parse_version

NEWS = {
    "1.45.0": [
        {"title": "ENERGIA NA LOJA", "scene": "loja", "lines": [
            "A loja da fase agora vende ENERGIA: 20 almas enchem 100 da barra, metade dela.",
            "Tem na lojinha da sala inicial e na loja completa, logo abaixo da poção de vida.",
            "Barra cheia, a loja não deixa comprar. No Ibrahim e no Borba, fica mais cara como o resto.",
            "Pelo celular também: o item aparece com um frasco azul.",
        ]},
        {"title": "FORJADA COM COMPANHIA", "scene": "loja", "lines": [
            "Fundiu as três armas? Agora dá para pegar arma comum de novo, ao lado da forjada.",
            "Cabe uma de tiro e uma de perto junto com ela: chão, vitrine ou armário.",
            "Largou a forjada? As comuns que estavam com ela ficam no lugar das do herói.",
        ]},
        {"title": "UM PET POR JOGADOR", "scene": "casa", "lines": [
            "Cada jogador leva um pet só: adotar outro bicho da Casa devolve o que você tinha.",
            "Pegar um pet da loja no armário manda o bicho da Casa de volta para o cantinho dele.",
        ]},
    ],
    "1.44.0": [
        {"title": "PETS NA LOJA DE CACOS", "scene": "casa", "lines": [
            "A seção PETS da loja abriu: capivara, mico-leão-dourado, tuiuiú filhote e jabuti.",
            "E dois que voam do seu lado: o mini-drone da Lag Lobby e o Caquinho, um caco que ganhou vida.",
            "Cada pet custa 250 cacos e é só enfeite: não bate, não apanha, não muda nada na luta.",
        ]},
        {"title": "O PET NO ARMÁRIO", "scene": "casa", "lines": [
            "Comprou? Vá ao seu armário: embaixo das roupas tem a linha PET. Escolha e ele já vem atrás.",
            "O pet fica com o jogador (P1 a P4) e vai junto para as fases, mesmo trocando de herói.",
            "Dois jogadores podem levar o mesmo bicho, e o gato, o cachorro e o papagaio continuam na Casa.",
        ]},
    ],
    "1.43.0": [
        {"title": "LOJA DE CACOS", "scene": "casa", "lines": [
            "Tem banca nova no quintal da Casa: a LOJA DE CACOS. Chegue perto e ATACAR abre.",
            "Ela abre com as seções SKINS e PETS (os pets chegam em breve). Dentro, as skins viram cartas.",
            "Cacos são os caquinhos do cristal da IARA. Ficam salvos no computador, num pote só da turma.",
            "Zerar a campanha inteira paga uns cacos, mais na dificuldade alta, e o dobro na primeira vez.",
            "Na loja só tem enfeite: skin não muda dano, vida, energia nem arma.",
        ]},
        {"title": "SKINS NOVAS", "scene": "loja", "lines": [
            "Por 300 cacos: Fantasma Lençol da Vó, Atirador Cangaceiro, Tanque de Obsidiana e Titã Rei Momo.",
            "Cada skin vem com um efeito em volta do herói: poeira, confete, brasa de obsidiana...",
            "A loja já abre na skin do herói que você está jogando. Comprou, ela é da turma.",
            "Para vestir, vá ao seu ARMÁRIO (P1 a P4, ao lado da loja) e escolha a roupa do seu herói.",
            "Armário piscando: tem skin nova esperando. Trocar de roupa lá é sempre de graça.",
            "A skin fica no herói e vale na Casa e na campanha. No futebol e no basquete, o uniforme.",
        ]},
        {"title": "CUPONS", "scene": "casa", "lines": [
            "O botão INSERIR CUPOM fica lá em cima: digite pelo teclado da TV ou direto no celular.",
            "Cada cupom vale uma vez por save e pode dar cacos e até uma skin rara que não se compra.",
            "As quatro raras são da turma original: Albeguinio, Cauanzera, Aryel e Borba Jr.",
        ]},
    ],
    "1.42.0": [
        {"title": "O BAÚ NÃO ESCOLHE POR VOCÊ", "scene": "corredores", "lines": [
            "Abrindo o baú, as armas raras saltam para o chão, na frente dele: uma por jogador e mais uma.",
            "Ninguém troca de arma sozinho: vá até a que quiser, veja o nome e ATACAR pega.",
            "A rara que você tinha fica no chão no lugar, e o amigo pode pegar.",
        ]},
        {"title": "CORREÇÕES", "scene": "mapa_fase", "lines": [
            "Trocar de arma não duplica mais: a arma do seu herói volta para a mochila, não para o chão.",
            "Os drones e os outros chamados do chefe nascem dentro da sala, e não mais no corredor.",
            "Inimigo que escapar da sala de luta volta para dentro: a sala sempre dá para limpar.",
        ]},
        {"title": "FUSÃO DE VERDADE", "scene": "loja", "lines": [
            "No ferreiro, FUNDIR AS 3 ARMAS agora junta as três numa só: sobra só a forjada na mão.",
            "Quer as armas do herói de volta? LARGAR ARMA solta a forjada no chão.",
            "Com a forjada na mão não dá para pegar arma comum: largue ela antes.",
        ]},
    ],
    "1.41.0": [
        {"title": "CRÉDITOS NOVOS", "scene": "mansao", "lines": [
            "Os créditos do fim da campanha e do cinema agora abrem com CRIADO POR: Cauã Pedrozo Brito.",
            "Os amigos ganharam a seção QUEM TESTOU PRIMEIRO, cada um com o personagem que inspirou.",
            "O jogo nasceu como projeto de faculdade e ganhou corpo. Valeu, turma, por estar junto desde o começo!",
        ]},
    ],
    "1.40.0": [
        {"title": "PARA ONDE?", "scene": "casa", "lines": [
            "No começo da campanha, ATACAR no carro do quintal abre o PARA ONDE?.",
            "Escolha o capítulo da viagem: só aparecem liberados os que vocês já alcançaram.",
            "Começar mais adiante dá almas e melhorias, como no menu da campanha.",
            "Mudou de ideia? Escolha de novo: o bônus não soma duas vezes.",
            "Enquanto alguém escolhe, o carro espera. No CONTINUAR e no passeio não tem.",
        ]},
    ],
    "1.39.0": [
        {"title": "A HISTÓRIA COSTURADA", "scene": "iara", "lines": [
            "Uma voz roxa sai do cristal e tenta cada amigo: o Aryel, o Borba Jr, o Albeguinio.",
            "No capítulo 4 ela entra no servidor e ganha nome: é a IARA.",
            "A Patrulha Cinza volta na Mansão do Carimbo, com contrato assinado pela IARA.",
            "Albeguinio e Cauanzera agora acordam no fim do capítulo 2, e dá para ver quem pega o caco.",
        ]},
        {"title": "COMEÇA E TERMINA NA CASA", "scene": "casa", "lines": [
            "A campanha abre numa noite de encontro na Casa, com o Aryel saindo de moto.",
            "Depois dos créditos vem o epílogo: pão da padaria da família, City consertado e café com a IARA.",
            "No final, a turma chega a pé depois da luta. O City quebrou de novo.",
        ]},
        {"title": "OS CHEFES FALAM", "scene": "mansao", "lines": [
            "Cada chefe solta três falas na luta: ao entrar, quando cansa e quando a vida está acabando.",
        ]},
        {"title": "A HISTÓRIA VIROU FILME", "scene": "casa", "lines": [
            "Cada cena da campanha agora é animada: câmera andando, gente entrando, clarão e chuva.",
            "As cenas passam sozinhas, com legenda. ATACAR adianta, ESC pula.",
        ]},
        {"title": "SALA DE CINEMA", "scene": "casa", "lines": [
            "No CINEMA, a turma entra, senta nas poltronas e a luz apaga.",
            "O telão vem chegando até ocupar a tela inteira, e o filme passa sozinho.",
            "FILME COMPLETO vai da abertura ao epílogo, com a plateia reagindo e aplaudindo no fim.",
            "Segure ESC para sair no meio.",
        ]},
    ],
    "1.38.0": [
        {"title": "SALAS MOBILIADAS", "scene": "mapa_fase", "lines": [
            "As salas de luta ganharam móveis do capítulo, desenhados no mesmo capricho dos heróis.",
            "Na floresta: árvores, tronco caído, pedras e moitas. No Lag Lobby: rack, mesa com PC e caixas.",
            "Na clínica: cadeiras de espera, biombo e carrinho de spa. Na Mansão: relógio, poltronas e busto.",
            "Poças de luz no chão de cada sala, e nenhum móvel fecha porta ou caminho.",
        ]},
    ],
    "1.37.0": [
        {"title": "MASCOTES DA CASA", "scene": "casa", "lines": [
            "O gato laranja dorme no sofá, o Caramelo mora na casinha do quintal e o papagaio no poleiro.",
            "Chegue perto do cantinho e aperte ATACAR para adotar. Ele passa a te seguir, nas fases também.",
            "Cada bicho tem um dono só, e fica guardado de uma vez para a outra.",
            "Para devolver, leve o bicho até o cantinho dele e aperte ATACAR.",
        ]},
        {"title": "CASA ACONCHEGANTE", "scene": "casa", "lines": [
            "A luz das janelas segue o relógio: dourada de manhã, alaranjada à tarde e luar de noite.",
            "De noite o vidro escurece e aparecem a lua e as estrelas.",
            "Padaria com pão francês, sonho, baguete, pão de queijo e croissant, e o forno soltando fumaça.",
            "O exoesqueleto do Borba Jr ganhou pistões, núcleo aceso e capacete com viseira.",
        ]},
    ],
    "1.36.0": [
        {"title": "GARAGEM CAPRICHADA", "scene": "casa", "lines": [
            "Lá embaixo, a garagem ganhou piso de epóxi com placas, marcas de pneu e manchas de óleo.",
            "Parede de bloco com a faixa de aviso, placa de neon GARAGEM DA TURMA e painel de ferramentas.",
            "Cada vaga tem faixa amarela, batente e o nome do carro pintado no chão.",
            "Estante com um troféu para cada selo da campanha, carrinho de ferramentas, pneus e tambor.",
        ]},
    ],
    "1.35.0": [
        {"title": "OS CARROS DA TURMA", "scene": "casa", "lines": [
            "O City do João agora é o sedã 2026, azul acinzentado, com farol de LED e roda de 5 raios.",
            "O Uno Mille branco ficou quadradinho de verdade, com a calota de 4 furos.",
            "A moto do Aryel ganhou carenagem laranja, garfo dourado e escapamento cromado.",
        ]},
        {"title": "A ESTRADA DA VIAGEM", "scene": "casa", "lines": [
            "Céu em degradê com nuvens, morros em duas camadas e o bairro com casinhas e árvores.",
            "Calçada com postes e asfalto granulado. Depois vem o cenário do capítulo.",
            "Dá para ver a turma pelo vidro do carro, e as rodas giram de verdade.",
        ]},
    ],
    "1.34.0": [
        {"title": "QUEM ATENDE A LOJA", "scene": "loja", "lines": [
            "A loja e o ferreiro agora têm gente atrás do balcão, desenhada como os heróis.",
            "Cap. 1: o mascate de chapéu e o ferreiro ruivo martelando a bigorna.",
            "Cap. 2: o técnico do lado da máquina de venda e o soldador de máscara.",
            "Cap. 3: a atendente de jaleco rosa e o técnico dos aparelhos de estética.",
            "Cap. 4: o mordomo com a bandeja e o ourives de lupa no olho.",
        ]},
        {"title": "SALA DE RECOMPENSAS", "scene": "loja", "lines": [
            "Cada capítulo tem o seu baú: baú de madeira, cofre, maleta de beleza e arca de mogno.",
            "O armário de armas também muda: madeira, rack de servidor, armário rosa e cristaleira.",
            "A fogueira vira tambor com fogo na Lag Lobby, difusor de vapor na clínica",
            "e lareira de mármore na mansão. Todas continuam curando do mesmo jeito.",
        ]},
    ],
    "1.33.0": [
        {"title": "CANTOS FECHADOS", "scene": "casa", "lines": [
            "As paredes que se encostam agora são uma peça só, na Casa e em todas as fases.",
            "Em cima aparece o topo da parede, embaixo a frente, com um contorno só em volta.",
            "Cada sala virou um quadrado fechado de verdade, sem emenda nos cantos.",
        ]},
        {"title": "CASA MAIS BONITA", "scene": "casa", "lines": [
            "Chão de carvalho claro e tapete persa vinho com franja na sala.",
            "Vasos diferentes, placa GREEN! com moldura, roleta vermelha e creme.",
            "Os craques do quintal ganharam pódio de pedra com plaquinha e holofote.",
            "Horta com espantalho e mangueira, alçapão do porão com corrente e cadeado.",
            "A garagem do quintal tem telhado de telha, portão de enrolar e placa.",
        ]},
    ],
    "1.31.0": [
        {"title": "UM MAPA POR CAPÍTULO", "scene": "casa", "lines": [
            "Cada capítulo tem o seu formato de mapa.",
            "Capítulo 1: a cruz de sempre, com a abertura no meio.",
            "Capítulo 2: a torre da Lag Lobby, subindo andar por andar até a cobertura.",
            "Capítulo 3: o corredor da clínica, da recepção até o fim, com a farmácia de lado.",
            "Capítulo 4: o pátio da mansão, com as salas em volta e o chefe no salão do fundo.",
        ]},
        {"title": "FASES ESPELHADAS", "scene": "casa", "lines": [
            "As três fases do capítulo usam o mesmo formato, mas espelhado.",
            "A segunda vira de lado, e a terceira vira também de cima para baixo (a torre sempre sobe).",
            "O mapinha do canto acompanha o formato novo.",
        ]},
    ],
    "1.30.0": [
        {"title": "GARAGEM LÁ EMBAIXO", "scene": "casa", "lines": [
            "A garagem virou um lugar de verdade: ATACAR no portão e a turma desce a rampa.",
            "Lá embaixo ficam três vagas: o City, o Uno e a moto.",
            "Ande até um carro e aperte ATACAR para ir com ele. O menu da lista continua na estante.",
            "Carro que ainda não foi liberado fica coberto com a lona.",
            "Para voltar, é só subir a rampa: vocês saem na porta da garagem.",
        ]},
        {"title": "SALÃO DOS CORROMPIDOS", "scene": "casa", "lines": [
            "Descendo a escada no fundo da garagem tem o salão dos corrompidos.",
            "Zerou o capítulo, o corrompido dele ganha um lugar lá, e dá para conversar com ele.",
            "Pedestal vazio mostra qual capítulo falta zerar.",
            "A estante de troféus fica do lado das vagas.",
        ]},
    ],
    "1.29.0": [
        {"title": "PASSEAR NA CASA", "scene": "casa", "lines": [
            "Modo novo na campanha, em EXTRAS: PASSEAR NA CASA.",
            "Entra direto na Casa da turma, sem fase, sem tempo e sem mexer no save.",
            "Dá para usar tudo: computador, roleta, padaria, horta, garagem e a armadura de Uno.",
            "O City fica parado. Para voltar ao menu, é pela pausa.",
        ]},
        {"title": "O MAPINHA DA CASA", "scene": "casa", "lines": [
            "A Casa agora tem um mapinha no canto, como o das fases.",
            "Ele mostra a casa, o quintal e o canto de cada um.",
            "Cada jogador é um ponto na cor dele. As portas trancadas ficam em cinza.",
        ]},
    ],
    "1.28.0": [
        {"title": "O COMPUTADOR NO CELULAR", "scene": "casa", "lines": [
            "Abriu o PC do Cauanzera ou o notebook do Albeguinio, o celular mostra a tela dele.",
            "Toque direto nela para clicar. Tocou no terminal, no endereço ou na senha, sobe o teclado.",
            "O celular mostra só a linha digitada. O que você escreve aparece na TV na hora.",
            "FECHAR TUDO fica sempre no alto do celular.",
        ]},
        {"title": "SETINHA E TECLADO NA TELA", "scene": "casa", "lines": [
            "No controle ou no teclado, o analógico move uma setinha e ATACAR clica.",
            "Para digitar, aparece um teclado na tela, com sugestões dos comandos.",
            "Cada janela tem um X. Segurar ESQUIVA por 1 segundo fecha tudo.",
        ]},
        {"title": "COMANDOS DE VERDADE", "scene": "casa", "lines": [
            "O terminal entende LS, CAT, LIMPAR, EXIT e DESLIGAR, além do AJUDA.",
            "No navegador dá para digitar o endereço: SOULWIKI, PADARIA, LAGLOBBY e mais.",
            "Endereço que não existe dá página 404, com o cristal quebrado.",
        ]},
    ],
    "1.27.0": [
        {"title": "A GARAGEM ABRIU", "scene": "casa", "lines": [
            "A garagem da Casa agora abre desde o começo. ATACAR na porta escolhe com o que a turma sai.",
            "City do João sempre. Uno branco depois do capítulo 1. Moto do Aryel depois do capítulo 2.",
            "O Uno perde a porta no caminho. De moto, o P1 vai na frente empinando.",
            "Lá dentro ficam os troféus de cada dificuldade e quantos corrompidos já foram liberados.",
        ]},
        {"title": "ARMADURA DE UNO", "scene": "casa", "lines": [
            "No capítulo 1, a armadura de Uno do canto do Cauanzera dá para vestir. Só um jogador veste.",
            "Ela segura 8 golpes inteiros. A cada 2, cai uma peça: retrovisor, porta, capô e para-choque.",
            "Quem veste anda um pouco mais devagar. No capítulo 2 ela fica para trás: PERDA TOTAL.",
        ]},
    ],
    "1.26.0": [
        {"title": "TODOS NO CITY", "scene": "casa", "lines": [
            "A saída da Casa agora é o City do João, estacionado no quintal.",
            "Com todo mundo em volta do carro, a contagem começa e o grupo pega a estrada.",
            "O caminho de terra do quintal leva direto até ele.",
        ]},
        {"title": "O CITY QUEBROU", "scene": "casa", "lines": [
            "A viagem passa pelo bairro e chega no cenário do capítulo, com os quatro nas janelas.",
            "No meio do caminho o carro falha, solta fumaça e faz PUFF. Daqui é a pé.",
            "ESQUIVA pula a cena.",
        ]},
    ],
    "1.25.0": [
        {"title": "CONVERSA NO BOTÃO", "scene": "casa", "lines": [
            "Na Casa da turma, ninguém fala mais sozinho quando você passa perto.",
            "Chegou perto de alguém da vitrine ou de um retrato, aparece um balão com ... em cima dele.",
            "ATACAR conversa: uma frase por toque. Apertou de novo, vem a próxima.",
        ]},
        {"title": "UM DE CADA VEZ", "scene": "casa", "lines": [
            "Perto da mesa, da moto, da roleta ou da padaria, o ATACAR continua usando essas coisas.",
            "Com dois por perto, conversa quem estiver mais perto. O balão do vizinho some.",
        ]},
    ],
    "1.24.0": [
        {"title": "A FASE É UM MAPA SÓ", "scene": "mapa_fase", "lines": [
            "Cada fase agora é um mapa inteiro, a pé, com as salas ligadas por corredores.",
            "Saindo da Casa pelo portal, o grupo chega na abertura, com a lojinha e o altar.",
            "No fim da fase, um portal leva para a próxima. Na 3ª de cada capítulo, depois do chefe.",
        ]},
        {"title": "SALAS QUE TRANCAM", "scene": "mapa_fase", "lines": [
            "Entrou numa sala de luta, as portas fecham até a última onda cair.",
            "Cada fase tem uma sala de luta nova no meio do caminho e uma sala de recompensa.",
            "A sala do chefe só abre depois que as outras duas salas de luta forem limpas.",
        ]},
        {"title": "O MINI MAPA", "scene": "mapa_fase", "lines": [
            "No canto da tela, um mapinha mostra onde o grupo está, em dourado.",
            "As salas já visitadas ficam cinza. As que faltam aparecem com um ?.",
        ]},
    ],
    "1.23.0": [
        {"title": "PLANTÃO SOUL STRIKE", "scene": "novidades", "tv": "estudio", "lines": [
            "As novidades viraram um telejornal: cada versão é uma edição e cada novidade é uma notícia.",
            "Cada notícia tem a sua imagem ao vivo, e a lista do lado marca o que você já viu.",
            "Atualizou depois de muito tempo? Aparecem todas as versões que você ainda não viu.",
        ]},
        {"title": "NO CELULAR E NO ARQUIVO", "scene": "hud", "lines": [
            "No celular, os botões < PULAR > viram as notícias de qualquer jogador.",
            "Em OPÇÕES > NOVIDADES fica o arquivo com todas as edições, desde a 1.1.0.",
        ]},
    ],
    "1.22.0": [
        {"title": "CORREDORES DECORADOS", "scene": "corredores", "lines": [
            "A sala inicial e o corredor de cada capítulo ganharam enfeites nos cantos, sem fechar o caminho.",
            "Trilha com tochas, barris e cogumelos. Lag Lobby com racks, cones e bebedouro.",
            "Clepalovers com cadeiras de espera. Mansão com retratos, bustos e pilhas de papel.",
        ]},
        {"title": "A PLACA DO CORREDOR", "scene": "corredores", "lines": [
            "Todo corredor tem uma placa perto de onde o grupo chega. Leia antes de seguir.",
            "Os acampamentos antigos saíram do jogo: a fase só vai em frente.",
        ]},
    ],
    "1.21.0": [
        {"title": "O PC DO CAUANZERA", "scene": "computador", "lines": [
            "Na Casa da turma, ATACAR na mesa do Cauanzera liga o CAUANZERA OS: arquivos, navegador e terminal.",
            "O notebook do Albeguinio abre no modo hacker. A senha todo mundo já sabe.",
            "A janela aparece na TV, em cima da mesa, e no celular de quem abriu.",
        ]},
        {"title": "LIBERAR TUDO", "scene": "computador", "lines": [
            "No terminal do PC, liberar --tudo libera os 4 capítulos, os 4 corrompidos no duelo e as portas da casa.",
            "No notebook é a invasão do cristal, com mais firula. Fica salvo para sempre, sem selo de recorde.",
            "A tela fica branca com LIBERANDO... e a casa volta com tudo aberto.",
        ]},
        {"title": "OS CANTOS DA TURMA", "scene": "cantos", "lines": [
            "A moto do Aryel dá grau. A roleta gira e para no GREEN ou no RED.",
            "Na padaria do João, pegue a senha e espere o pão quentinho sair do forno.",
        ]},
    ],
    "1.20.0": [
        {"title": "CASA DA TURMA", "scene": "casa", "lines": [
            "A campanha começa na casa da turma. O CONTINUAR também volta por ela.",
            "Cada amigo tem o seu canto. A saída do quintal leva o grupo para a fase.",
            "O livro do Cauanzera mostra um versículo diferente cada vez que é aberto.",
        ]},
        {"title": "A VITRINE FALA", "scene": "casa", "lines": [
            "Chegue perto de um herói da vitrine e ele fala, cada vez uma frase.",
            "Regue a horta com ATACAR. Com os quatro canteiros regados juntos, nasce uma flor grande.",
            "As portas trancadas abrem conforme a campanha avança.",
        ]},
    ],
    "1.19.0": [
        {"title": "O CELULAR VIBRA", "scene": "hud", "lines": [
            "O celular vibra quando o seu herói apanha, no gol, na cesta e no SUPER.",
            "Funciona no Android. O botão VIBRAR do celular e a opção VIBRAÇÃO desligam tudo.",
        ]},
        {"title": "CHAMADA NA PORTA", "scene": "lag", "lines": [
            "Na campanha, quando o grupo está na porta e falta você, o celular chama a cada 3 segundos.",
            "Ele também vibra em cada segundo da contagem e na hora em que o grupo vai.",
        ]},
    ],
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
    "1.17.0": [
        {"title": "PÊNALTIS 1 x 1", "scene": "penalti", "lines": [
            "No menu do futebol, PÊNALTIS 1 x 1: um herói de cada lado, que bate e defende.",
            "5 cobranças para cada um e morte súbita. Sem o P2, a CPU vai para o gol (1 2 3 escolhe a dificuldade).",
            "A disputa de antes continua lá, agora com o nome PÊNALTIS 2 x 2.",
        ]},
        {"title": "CAPAS DOS MODOS", "scene": "modos", "lines": [
            "As capas da lista de modos mostram o cenário de verdade, com luz e partículas.",
            "Os nomes dos modos não saem mais cortados.",
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
            "BORBA: sensacional. Sem cura entre as fases e cada um só é levantado uma vez por masmorra.",
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
