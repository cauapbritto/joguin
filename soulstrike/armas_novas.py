"""Armas novas da campanha: as do baú de cada fase, as redundantes de piada e as de tiro de graça.

Aqui ficam só os números (data.py junta as raras em RARE_WEAPONS). Os tiros e os efeitos dos
golpes ficam em tiros_novos.py. As que repetem um comportamento que já existe (bumerangue,
granada, crânio, escudo...) só usam o estilo daquela arma, com a arte e o número delas.
"""


def build(WeaponStats):
    """As armas novas prontas (data.py chama com a classe dele, para não dar import circular).
    Devolve (raras dos baús, armas de tiro de graça)."""
    def _ranged(name, damage, speed, cooldown, style, mag=0, reload=0, regen=0, **extra):
        return WeaponStats(name, "ranged", damage, bullet_speed=speed, cooldown=cooldown, style=style, mag=mag,
                           reload=reload, regen=regen, **extra)

    def _melee(name, damage, reach, cooldown=16, **extra):
        return WeaponStats(name, "melee", damage, reach=reach, cooldown=cooldown, **extra)

    # ── armas raras e roubadas dos baús (entram em RARE_WEAPONS) ─────────
    RARES = {
        # Floresta Sombria
        "estilingue": _ranged("Estilingue de Galho", 10, 11, 22, "n_pedra", mag=8, reload=70, rare=True,
                              note="Pedrinha que empurra. Não gasta energia."),
        "zarabatana": _ranged("Zarabatana", 6, 14, 20, "n_dardo", mag=6, reload=80, rare=True,
                              note="Dardo envenenado: quem leva perde vida aos poucos."),
        # Calabouço das Almas
        "tocha": _melee("Tocha", 16, 60, cooldown=18, rare=True, special="queima",
                        note="Cada golpe põe fogo no inimigo. Não gasta energia."),
        "mangual_ossos": _melee("Mangual de Ossos", 24, 78, cooldown=28, rare=True, spin=True,
                                note="Gira a bola de ossos em volta: acerta todo mundo perto."),
        # Templo Gelado (roubada)
        "sino_funebre": _ranged("Sino Fúnebre", 18, 0, 50, "n_sino", mag=3, regen=70, rare=True, roubada=True,
                                close_bonus=False, note="Badalada: machuca e assusta todo mundo em volta."),
        # Recepção (Lag Lobby)
        "grampeador": _ranged("Grampeador Industrial", 5, 16, 6, "n_grampo", mag=24, reload=80, rare=True,
                              note="Rajada de grampos rápidos. Não gasta energia."),
        "mouse_fio": _melee("Mouse com Fio", 14, 96, cooldown=20, rare=True, special="puxa",
                            note="Chicote de cabo comprido: puxa o inimigo para perto."),
        "taser_eletrizante": _ranged("Taser Elétrico Eletrizante", 9, 12, 30, "n_choque", mag=4, reload=80,
                                     rare=True, note="Dá choque elétrico eletrizante. Deixa tonto."),
        # Datacenter
        "impressora": _ranged("Impressora de Bolso", 8, 10, 30, "n_papel", mag=4, reload=90, rare=True,
                              note="Imprime 3 folhas em leque de uma vez."),
        "pistola_tiros": _ranged("Pistola Atiradora de Tiros", 11, 14, 14, "n_bala", mag=10, reload=70, rare=True,
                                 note="Atira tiros. Não gasta energia."),
        # Cobertura (roubadas)
        "cadeira_gamer": _melee("Cadeira Gamer", 30, 70, cooldown=30, rare=True, roubada=True, special="empurra",
                                note="Pancada de cadeira: arremessa o inimigo longe."),
        "rifle_spawner": _ranged("Rifle Spawner", 7, 15, 6, "n_spawner", mag=30, reload=90, rare=True, roubada=True,
                                 note="Rajada rápida. A cada 15 tiros, nasce um drone aliado do seu lado."),
        "bomba_explosiva": _ranged("Bomba Explosiva que Explode", 30, 9, 45, "granada", mag=3, reload=100,
                                   rare=True, roubada=True, note="É uma bomba. Ela explode. Explosivamente."),
        # Clínica: recepção
        "secador": _ranged("Secador de Cabelo", 3, 7, 5, "n_vento", mag=40, reload=100, rare=True, close_bonus=False,
                           note="Vento quente: atravessa todo mundo e empurra."),
        "pinca": _melee("Pinça Gigante", 18, 64, cooldown=18, rare=True, special="atordoa",
                        note="Belisca forte: deixa o inimigo tonto. Não gasta energia."),
        "pistola_agua": _ranged("Pistola de Água Molhada", 4, 12, 8, "n_agua", mag=20, reload=70, rare=True,
                                note="Jato de água molhada: quem leva fica lento."),
        "bisturi": _melee("Bisturi", 12, 50, cooldown=8, rare=True, special="sangra",
                          note="Cortes rápidos que sangram. Não gasta energia."),
        # Clínica: procedimentos
        "pistola_botox": _ranged("Pistola de Botox", 12, 12, 26, "n_botox", mag=5, reload=90, rare=True,
                                 note="Quem leva fica paralisado por um instante."),
        "espelho_selfie": _ranged("Espelho de Selfie", 14, 0, 40, "n_flash", mag=3, regen=60, rare=True,
                                  close_bonus=False, note="Flash na cara de todo mundo na frente: deixa tonto."),
        "macarico": _ranged("Maçarico Quente de Fogo", 5, 7, 5, "chama", mag=40, reload=110, rare=True,
                            close_bonus=False, note="Fogo quente que queima. Tipo um lança-chamas, só que maçarico."),
        "cajado_gelo": _ranged("Cajado do Gelo Gelado", 13, 10, 30, "n_gelo", mag=5, regen=55, rare=True,
                               note="Gelo gelado e frio: congela quem leva."),
        # Clínica: suíte VIP (roubadas e mais uma)
        "laser_depilador": _ranged("Laser Depilador", 20, 24, 26, "n_laser", mag=4, regen=50, rare=True, roubada=True,
                                   close_bonus=False, note="Laser que atravessa a fila inteira."),
        "fantasma_assustador": _ranged("Fantasma Assombrado Assustador", 14, 8, 36, "cranio", mag=3, regen=80,
                                       rare=True, roubada=True, note="Assombra e assusta de um jeito assustador."),
        "patins_gelo": _melee("Patins de Gelo", 14, 58, cooldown=12, rare=True, special="gelo",
                              note="Chute rápido de patins: quem leva fica lento."),
        "espada_afiada": _melee("Espada Afiada Cortante", 34, 80, cooldown=20, rare=True, roubada=True,
                                note="Corta afiadamente. Não gasta energia."),
        # Mansão: sede
        "carimbo_bolso": _melee("Carimbo de Bolso", 20, 56, cooldown=18, rare=True, special="atordoa",
                                note="DEFERIDO na testa: deixa tonto. Não gasta energia."),
        "boleto_bumerangue": _ranged("Boleto Bumerangue", 13, 11, 26, "n_boleto", mag=2, reload=60, rare=True,
                                     note="Sempre volta. Como todo boleto."),
        "caneta": _ranged("Caneta-Tinteiro", 9, 15, 18, "n_tinta", mag=6, reload=70, rare=True,
                          note="Jato de tinta: atravessa um e deixa lento."),
        "rifle_caca": _ranged("Rifle de Caça", 24, 18, 46, "n_caca", mag=4, reload=100, rare=True,
                              note="Tiro forte e longo que atravessa um inimigo."),
        # Mansão: pátio
        "fax": _ranged("Fax Lança-Papéis", 7, 11, 20, "n_fax", mag=4, reload=80, rare=True,
                       note="Solta 5 folhas em leque de uma vez."),
        "lanca_pastas": _ranged("Lança-Pastas", 16, 10, 34, "n_pasta", mag=4, reload=80, rare=True,
                                note="Pasta pesada: empurra longe."),
        "martelo_martelador": _melee("Martelo Martelador", 30, 62, cooldown=30, rare=True, special="atordoa",
                                     note="Martela martelando. Deixa tonto. Não gasta energia."),
        "besta_repeticao": _ranged("Besta de Repetição", 12, 15, 10, "virote", mag=8, reload=90, rare=True,
                                   note="8 virotes seguidos, mais leves que os da besta."),
        "martelo_pedra": _melee("Martelo de Pedra", 26, 64, cooldown=26, rare=True, special="empurra",
                                note="Pancada que empurra. Não gasta energia."),
        # Mansão: gabinete (roubadas)
        "guarda_chuva": _melee("Guarda-chuva Executivo", 16, 60, cooldown=24, rare=True, roubada=True,
                               special="escudo", note="Segure: abre e segura os tiros. Solte: empurrão."),
        "excalitora": _melee("Excalitora", 34, 200, cooldown=30, rare=True, roubada=True,
                             note="Tirada da pedra de inscrição. A pedra veio junto. Deixa o herói mais lento."),
        "escudo_protetor": _melee("Escudo Protetor Defensivo", 20, 56, cooldown=30, rare=True, roubada=True,
                                  special="escudo", note="Protege defensivamente. Segure para bloquear."),
        "sugador_almas": _ranged("Sugador de Almas", 4, 13, 8, "n_sugador", mag=40, reload=100, rare=True,
                                 roubada=True, close_bonus=False, note="Raio que atravessa e devolve energia."),
        "bateria_portatil": _melee("Bateria Portátil", 18, 58, cooldown=16, rare=True, roubada=True,
                                   special="bateria", note="Cada inimigo derrubado com ela dá +6 de energia."),
    }

    # ── armas de tiro de graça: caem dos inimigos como as comuns, mas não gastam energia ──
    FREE_GUNS = (
        _ranged("Rifle de Ferrolho", 26, 18, 44, "bala", mag=5, reload=120, note="5 tiros fortes. Recarga lenta."),
        _ranged("Submetralhadora", 5, 15, 5, "bala", mag=30, reload=90, note="30 tiros fracos e rápidos."),
        _ranged("Escopeta Serrada", 9, 12, 34, "n_escopeta", mag=2, reload=80, note="2 tiros: leque que empurra."),
        _ranged("Revólver do Xerife", 15, 15, 20, "bala", mag=6, reload=90, note="6 tiros, um de cada vez."),
        _ranged("Carabina", 8, 16, 26, "n_carabina", mag=9, reload=90, note="Rajada de 3 balas."),
        _ranged("Pistola de Pregos", 7, 14, 14, "n_prego", mag=12, reload=80, note="Prega o inimigo no chão por um instante."),
        _ranged("Arco Curto", 11, 13, 18, "flecha", mag=8, reload=80, note="Flecha rápida, sem precisar tensionar."),
    )
    return RARES, FREE_GUNS


FREE_NAMES = {"Rifle de Ferrolho", "Submetralhadora", "Escopeta Serrada", "Revólver do Xerife", "Carabina",
              "Pistola de Pregos", "Arco Curto"}

# custo de energia por tiro (as de perto: o efeito do golpe; 0 = de graça)
COSTS = {
    "Estilingue de Galho": 0, "Zarabatana": 1, "Sino Fúnebre": 6, "Grampeador Industrial": 0,
    "Taser Elétrico Eletrizante": 1, "Impressora de Bolso": 2, "Pistola Atiradora de Tiros": 0,
    "Rifle Spawner": 1, "Bomba Explosiva que Explode": 3, "Secador de Cabelo": 1, "Pistola de Água Molhada": 0,
    "Pistola de Botox": 2, "Espelho de Selfie": 2, "Maçarico Quente de Fogo": 1, "Cajado do Gelo Gelado": 2,
    "Laser Depilador": 5, "Fantasma Assombrado Assustador": 2, "Boleto Bumerangue": 1, "Caneta-Tinteiro": 1,
    "Rifle de Caça": 2, "Fax Lança-Papéis": 2, "Lança-Pastas": 2, "Besta de Repetição": 1, "Sugador de Almas": 0,
}
COSTS.update({name: 0 for name in FREE_NAMES})
# de perto: (golpe comum, 3º golpe). Sem energia, o golpe sai sem o efeito.
SPECIAL_COSTS = {
    "Tocha": (0, 0), "Mangual de Ossos": (1, 1), "Mouse com Fio": (0, 0), "Cadeira Gamer": (2, 2),
    "Pinça Gigante": (0, 0), "Bisturi": (0, 0), "Patins de Gelo": (1, 1), "Espada Afiada Cortante": (0, 0),
    "Carimbo de Bolso": (0, 0), "Martelo Martelador": (0, 0), "Martelo de Pedra": (0, 0),
    "Guarda-chuva Executivo": (0, 0), "Excalitora": (0, 0), "Escudo Protetor Defensivo": (0, 0),
    "Bateria Portátil": (0, 0),
}
# arma pesada na mão: o herói anda mais devagar
HEAVY = {"Excalitora": 0.75}
BATTERY_KILL = 6

# brilho das raras novas (rare_fx.ACCENT): a cor das faíscas e do rastro
ACCENT = {
    "Estilingue de Galho": (200, 190, 170), "Zarabatana": (150, 230, 110), "Tocha": (255, 160, 60),
    "Mangual de Ossos": (230, 220, 190), "Sino Fúnebre": (240, 210, 120), "Grampeador Industrial": (210, 214, 224),
    "Mouse com Fio": (130, 200, 255), "Taser Elétrico Eletrizante": (255, 236, 90),
    "Impressora de Bolso": (240, 236, 222), "Pistola Atiradora de Tiros": (250, 220, 120),
    "Cadeira Gamer": (240, 80, 90), "Rifle Spawner": (120, 240, 200), "Bomba Explosiva que Explode": (255, 140, 50),
    "Secador de Cabelo": (255, 190, 220), "Pinça Gigante": (210, 214, 224), "Pistola de Água Molhada": (90, 180, 240),
    "Bisturi": (230, 240, 255), "Pistola de Botox": (240, 130, 180), "Espelho de Selfie": (255, 220, 240),
    "Maçarico Quente de Fogo": (255, 130, 40), "Cajado do Gelo Gelado": (170, 225, 255),
    "Laser Depilador": (255, 90, 100), "Fantasma Assombrado Assustador": (200, 230, 255),
    "Patins de Gelo": (170, 225, 255), "Espada Afiada Cortante": (230, 240, 255), "Carimbo de Bolso": (240, 90, 90),
    "Boleto Bumerangue": (240, 236, 222), "Caneta-Tinteiro": (90, 110, 220), "Rifle de Caça": (230, 190, 120),
    "Fax Lança-Papéis": (240, 236, 222), "Lança-Pastas": (220, 170, 110), "Martelo Martelador": (220, 230, 255),
    "Besta de Repetição": (190, 210, 255), "Martelo de Pedra": (190, 184, 180),
    "Guarda-chuva Executivo": (130, 200, 255), "Excalitora": (255, 236, 150),
    "Escudo Protetor Defensivo": (130, 200, 255), "Sugador de Almas": (160, 130, 255),
    "Bateria Portátil": (120, 255, 140),
}

# som do disparo de cada tiro novo (data.SHOT_SOUNDS)
SOUNDS = {
    "n_pedra": "arremesso", "n_dardo": "arco", "n_sino": "magia", "n_grampo": "arremesso", "n_choque": "eletrico",
    "n_papel": "arremesso", "n_bala": "tiro_forte", "n_spawner": "plasma", "n_vento": "fogo", "n_agua": "gelo",
    "n_botox": "arco", "n_flash": "magia", "n_gelo": "gelo", "n_laser": "plasma", "n_boleto": "arremesso",
    "n_tinta": "arco", "n_caca": "tiro_forte", "n_fax": "arremesso", "n_pasta": "arremesso", "n_sugador": "magia",
    "n_escopeta": "tiro_forte", "n_carabina": "tiro_forte", "n_prego": "arremesso",
}
