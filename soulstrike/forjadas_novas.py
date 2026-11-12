"""As 41 forjadas novas do ferreiro: 14 híbridas, 10 secretas e 17 de assinatura.

Como o ferreiro escolhe a forjada (forged.recipe), na ordem:
1. SECRETA: a receita exata (ex.: Lança-chamas + Maçarico + Secador vira o Bafo do Dragão).
2. ASSINATURA: as 2 armas do próprio herói + qualquer rara ou roubada.
3. HÍBRIDA: duas armas de uma família e uma de outra (ex.: 2 de corte + 1 de fogo = Katana Brasa).
4. PURA: as 8 de antes (a família que mais aparece).

Os tiros das de longe ficam em tiros_novos.SHOTS (estilos "f_..."); as de perto têm um efeito em
cada golpe e um maior no 3º golpe seguido (MELEE).
"""
from .data import WeaponStats


def _f(name, kind, damage, style, note, **extra):
    return WeaponStats(name, kind, damage, style=style, note=note, rare=True, forjada=True, **extra)


def _melee(name, damage, reach, cooldown, note):
    return _f(name, "melee", damage, "fm", note, reach=reach, cooldown=cooldown)


def _ranged(name, damage, speed, cooldown, style, note, mag=0, reload=0, **extra):
    return _f(name, "ranged", damage, style, note, bullet_speed=speed, cooldown=cooldown, mag=mag, reload=reload,
              **extra)


NEW_FORGED = {
    # ── híbridas (duas famílias) ──
    "katana_brasa": _melee("Katana Brasa", 36, 80, 16, "Cada golpe solta uma onda de fogo; o 3º gira em brasa."),
    "lamina_glacial": _melee("Lâmina Glacial", 36, 80, 18, "Onda de gelo a cada golpe; o 3º congela tudo em volta."),
    "espada_relampago": _melee("Espada Relâmpago", 34, 78, 14, "Onda elétrica a cada golpe; o 3º solta raios em 3."),
    "martelo_vulcanico": _melee("Martelo Vulcânico", 46, 72, 30, "Cada golpe queima; o 3º faz o chão explodir."),
    "maca_avalanche": _melee("Maça Avalanche", 44, 72, 28, "Cada golpe deixa lento; o 3º congela em volta."),
    "marreta_dinamite": _melee("Marreta de Dinamite", 48, 70, 30, "Empurra longe; o 3º golpe explode a dinamite."),
    "arco_fenix": _ranged("Arco Fênix", 15, 13, 26, "f_fenix", "3 flechas de fogo que atravessam e queimam."),
    "besta_boreal": _ranged("Besta Boreal", 22, 16, 30, "f_boreal", "Virote de gelo que atravessa 2 e congela."),
    "arco_espectral": _ranged("Arco Espectral", 18, 12, 24, "f_espectral",
                              "Flecha de alma que atravessa paredes e cura um pouco a cada acerto."),
    "granada_tesla": _ranged("Granada Tesla", 30, 9, 40, "f_tesla", "Explode num choque que deixa todo mundo tonto.",
                             close_bonus=False),
    "morteiro_neve": _ranged("Morteiro de Neve", 30, 8, 44, "f_morteiro", "Bola de neve que explode e congela em volta.",
                             close_bonus=False),
    "cetro_aurora": _ranged("Cetro Aurora", 12, 20, 12, "f_aurora", "Feixe de luz fria que atravessa e congela."),
    "lanterna_infernal": _ranged("Lanterna Infernal", 5, 13, 6, "f_infernal",
                                 "Fogo de alma: atravessa, queima e devolve vida.", close_bonus=False),
    "sino_almas": _ranged("Sino das Almas", 26, 0, 46, "f_sino", "Badalada que assusta todos em volta e cura você.",
                          close_bonus=False),
    # ── secretas (receita exata) ──
    "usina_ambulante": _ranged("Usina Ambulante", 30, 0, 40, "f_usina", "Descarga em volta que deixa todo mundo tonto.",
                               close_bonus=False),
    "era_do_gelo": _ranged("Era do Gelo", 24, 0, 60, "f_era", "Congela todo mundo num raio enorme.", close_bonus=False),
    "espada_fim_mundo": _melee("Espada do Fim do Mundo", 56, 230, 32,
                               "Enorme e flamejante: onda de fogo a cada golpe e o 3º explode."),
    "chuva_flechas": _ranged("Chuva de Flechas", 9, 13, 30, "f_chuva", "9 flechas em leque de uma vez."),
    "exercito_bolso": _ranged("Exército de Bolso", 8, 15, 8, "f_exercito",
                              "Rajada rápida; a cada 5 tiros nasce um drone aliado."),
    "furacao_laminas": _ranged("Furacão de Lâminas", 16, 11, 30, "f_furacao", "3 lâminas que vão e voltam."),
    "bafo_dragao": _ranged("Bafo do Dragão", 8, 8, 3, "chama", "Labareda enorme que atravessa todo mundo.",
                           close_bonus=False),
    "tempestade_completa": _ranged("Tempestade Completa", 12, 12, 18, "f_tempestade",
                                   "3 tiros em leque: cada um gela, molha ou dá choque."),
    "martelo_demolicao": _melee("Martelo de Demolição", 58, 76, 34, "Cada golpe empurra longe; o 3º explode o chão."),
    "duelo_meio_dia": _ranged("Duelo ao Meio-dia", 30, 20, 22, "f_duelo", "2 balas certeiras que atravessam."),
    # ── assinatura (as 2 do herói + uma rara) ──
    "espada_primeiro": _melee("Espada do Primeiro Guerreiro", 40, 84, 16, "Onda a cada golpe; o 3º gira em volta."),
    "rifle_sem_fim": _ranged("Rifle Sem Fim", 12, 16, 7, "f_semfim", "Nunca recarrega: rajada sem fim."),
    "ariete": _melee("Aríete", 42, 70, 26, "Cada golpe arremessa; o 3º deixa todo mundo em volta tonto."),
    "lamina_mil_sombras": _melee("Lâmina das Mil Sombras", 26, 70, 8, "Rapidíssima; o 3º golpe solta 5 sombras."),
    "garras_cometa": _melee("Garras do Cometa", 28, 62, 9, "Rápidas e elétricas; o 3º golpe gira."),
    "moto_bomba": _ranged("Moto-Bomba", 40, 10, 50, "f_moto", "Bomba que explode grande e empurra.",
                          close_bonus=False),
    "foice_morte": _melee("Foice da Morte", 38, 90, 18, "Cada golpe cura; o 3º puxa todo mundo para perto."),
    "corrente_tita": _melee("Corrente do Titã", 40, 124, 26, "Alcance enorme; o 3º puxa todo mundo para perto."),
    "canhao_navio": _ranged("Canhão do Navio", 44, 8, 56, "f_navio", "Bala de canhão que explode e arremessa.",
                            close_bonus=False),
    "zero_absoluto": _ranged("Cetro do Zero Absoluto", 18, 14, 22, "f_zero", "Gelo que atravessa todos e congela."),
    "roleta_sombria": _melee("Martelo da Roleta Sombria", 44, 72, 26, "Cada golpe sorteia um efeito; o 3º explode."),
    "servidor_mao": _ranged("Servidor de Mão", 9, 15, 16, "f_servidor", "4 pacotes de dados que deixam tonto."),
    "notebook_rgb": _melee("Notebook Gamer RGB", 38, 66, 18, "O 3º golpe espalha 5 ondas coloridas."),
    "exo_punho": _melee("Exo-Punho Mk II", 44, 64, 20, "Cada soco arremessa; o 3º abre uma explosão."),
    "punho_colapso": _melee("Punho do Colapso", 46, 64, 22, "O 3º soco puxa todo mundo e explode."),
    "carimbo_indeferido": _melee("Carimbo INDEFERIDO", 38, 62, 20, "INDEFERIDO: cada carimbada deixa tonto."),
    "tentaculos_lag": _ranged("Tentáculos do Lag", 12, 14, 30, "f_tentaculos", "8 cabos em volta que dão choque."),
}

# ── como cada uma sai ─────────────────────────────────────────────────
HYBRIDS = {
    ("corte", "fogo"): "katana_brasa", ("corte", "gelo"): "lamina_glacial", ("corte", "raio"): "espada_relampago",
    ("impacto", "fogo"): "martelo_vulcanico", ("impacto", "gelo"): "maca_avalanche",
    ("impacto", "explosao"): "marreta_dinamite", ("flecha", "fogo"): "arco_fenix", ("flecha", "gelo"): "besta_boreal",
    ("flecha", "alma"): "arco_espectral", ("explosao", "raio"): "granada_tesla", ("explosao", "gelo"): "morteiro_neve",
    ("raio", "gelo"): "cetro_aurora", ("fogo", "alma"): "lanterna_infernal", ("alma", "impacto"): "sino_almas",
}
# receitas secretas: os nomes exatos (ordem não importa); "gelo*3" = as três da família gelo
SECRETS = {
    "usina_ambulante": {"Taser de Rede", "Cajado do Raio", "Escudo de Choque"},
    "era_do_gelo": "gelo*3",
    "espada_fim_mundo": {"Excalitora", "Espada", "Katana"},
    "chuva_flechas": {"Arco", "Besta", "Arco Curto"},
    "exercito_bolso": {"Drone de Bolso", "Rifle Spawner", "Grampeador Industrial"},
    "furacao_laminas": {"Bumerangue", "Boleto Bumerangue", "Foice Espectral"},
    "bafo_dragao": {"Lança-chamas", "Maçarico Quente de Fogo", "Secador de Cabelo"},
    "tempestade_completa": {"Pistola de Água Molhada", "Taser Elétrico Eletrizante", "Cajado do Gelo Gelado"},
    "martelo_demolicao": {"Maça", "Martelo", "Martelo Martelador"},
    "duelo_meio_dia": {"Pistola", "Revólver do Xerife", "Rifle de Ferrolho"},
}
SIGNATURES = {
    "guerreiro": "espada_primeiro", "atirador": "rifle_sem_fim", "tanque": "ariete", "ninja": "lamina_mil_sombras",
    "velocista": "garras_cometa", "aryel": "moto_bomba", "fantasma": "foice_morte", "tita": "corrente_tita",
    "pirata": "canhao_navio", "geada": "zero_absoluto", "aryel_corrompido": "roleta_sombria",
    "cauanzera": "servidor_mao", "albeguinio": "notebook_rgb", "borba": "exo_punho",
    "borba_corrompido": "punho_colapso", "albeguinio_corrompido": "carimbo_indeferido",
    "cauanzera_corrompido": "tentaculos_lag",
}
# família das armas novas (as de antes estão em forged.FAMILIES)
FAMILIES = {
    "corte": ("Espada Afiada Cortante", "Bisturi", "Excalitora", "Patins de Gelo", "Guarda-chuva Executivo"),
    "impacto": ("Mangual de Ossos", "Mouse com Fio", "Cadeira Gamer", "Pinça Gigante", "Carimbo de Bolso",
                "Martelo Martelador", "Martelo de Pedra", "Escudo Protetor Defensivo", "Lança-Pastas"),
    "flecha": ("Estilingue de Galho", "Zarabatana", "Rifle de Caça", "Besta de Repetição", "Grampeador Industrial",
               "Pistola Atiradora de Tiros", "Rifle Spawner", "Caneta-Tinteiro", "Boleto Bumerangue",
               "Fax Lança-Papéis", "Impressora de Bolso", "Rifle de Ferrolho", "Submetralhadora", "Escopeta Serrada",
               "Revólver do Xerife", "Carabina", "Pistola de Pregos", "Arco Curto", "Pistola de Botox"),
    "explosao": ("Bomba Explosiva que Explode",),
    "gelo": ("Cajado do Gelo Gelado", "Pistola de Água Molhada"),
    "fogo": ("Tocha", "Maçarico Quente de Fogo", "Secador de Cabelo"),
    "raio": ("Taser Elétrico Eletrizante", "Laser Depilador", "Bateria Portátil", "Espelho de Selfie"),
    "alma": ("Sino Fúnebre", "Fantasma Assombrado Assustador", "Sugador de Almas"),
}

# custo de energia por tiro das de longe (as de perto: só o efeito, como as outras forjadas)
COSTS = {
    "Arco Fênix": 4, "Besta Boreal": 4, "Arco Espectral": 4, "Granada Tesla": 8, "Morteiro de Neve": 8,
    "Cetro Aurora": 2, "Lanterna Infernal": 1, "Sino das Almas": 8, "Usina Ambulante": 10, "Era do Gelo": 12,
    "Chuva de Flechas": 6, "Exército de Bolso": 1, "Furacão de Lâminas": 5, "Bafo do Dragão": 1,
    "Tempestade Completa": 4, "Duelo ao Meio-dia": 4, "Rifle Sem Fim": 1, "Moto-Bomba": 10, "Canhão do Navio": 10,
    "Cetro do Zero Absoluto": 4, "Servidor de Mão": 3, "Tentáculos do Lag": 8,
}
HEAVY = {"Espada do Fim do Mundo": 0.8}

# de perto: (efeito em cada golpe, efeito no 3º golpe seguido)
# cada golpe: "onda_<elemento>" solta uma onda que atravessa; ou um efeito direto em quem levou
# 3º golpe: giro, gelo (congela em volta), raio (3 raios), explode, atordoa, puxa, sombras, cores
MELEE = {
    "Katana Brasa": ("onda_fogo", "giro"), "Lâmina Glacial": ("onda_gelo", "gelo"),
    "Espada Relâmpago": ("onda_raio", "raio"), "Martelo Vulcânico": ("burn", "explode"),
    "Maça Avalanche": ("slow", "gelo"), "Marreta de Dinamite": ("knock", "explode"),
    "Espada do Fim do Mundo": ("onda_fogo", "explode"), "Martelo de Demolição": ("knock", "explode"),
    "Espada do Primeiro Guerreiro": ("onda_corte", "giro"), "Aríete": ("knock", "atordoa"),
    "Lâmina das Mil Sombras": ("", "sombras"), "Garras do Cometa": ("stun_leve", "giro"),
    "Foice da Morte": ("heal", "puxa"), "Corrente do Titã": ("", "puxa"),
    "Martelo da Roleta Sombria": ("random", "explode"), "Notebook Gamer RGB": ("", "cores"),
    "Exo-Punho Mk II": ("knock", "explode"), "Punho do Colapso": ("", "puxa_explode"),
    "Carimbo INDEFERIDO": ("stun", ""),
}

# livro de receitas do ferreiro: a dica de cada secreta (as outras a dica sai da regra)
SECRET_HINTS = {
    "usina_ambulante": "três armas que dão choque, da Lag Lobby",
    "era_do_gelo": "três armas de gelo, quaisquer",
    "espada_fim_mundo": "a espada da pedra com duas espadas de herói",
    "chuva_flechas": "arco, besta e o arco mais curto",
    "exercito_bolso": "drone, rifle que faz drone e grampeador",
    "furacao_laminas": "três coisas que vão e voltam",
    "bafo_dragao": "três armas de ar quente",
    "tempestade_completa": "água molhada, taser eletrizante e gelo gelado",
    "martelo_demolicao": "maça, martelo e o martelo martelador",
    "duelo_meio_dia": "pistola, revólver e rifle de ferrolho",
}
