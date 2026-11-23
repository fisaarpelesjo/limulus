"""Sprites em pixel art e fonte bitmap da camada visual do jogo.

Tudo aqui e original: cada sprite e uma lista de strings (um caractere por
pixel) mais um dicionario de paleta que traduz o caractere em cor RGB. O ponto
(".") e sempre transparente. Os herois e os chefes simetricos sao escritos pela
metade esquerda e espelhados, o que evita erro de alinhamento.

A fonte bitmap existe porque a fonte padrao embutida no Pillow nao tem os
glifos acentuados do portugues (ç, ã, é, Ó saem como caixas). Os acentos sao
compostos: a letra base vem da tabela GLIFOS e a marca (agudo, til, cedilha...)
vem da tabela MARCAS, a partir da decomposicao Unicode NFD.
"""

import unicodedata

from PIL import ImageDraw

# --------------------------------------------------------------------------
# Cores compartilhadas
# --------------------------------------------------------------------------

CONTORNO = (14, 12, 30)
PELE = (246, 196, 150)
PELE_SOMBRA = (206, 140, 100)
OLHO = (30, 24, 50)
OURO = (252, 214, 64)
OURO_ESCURO = (196, 140, 30)
MADEIRA = (128, 78, 40)
MADEIRA_ESCURA = (86, 50, 26)
AURA = (255, 246, 170)


def _espelhar(metade):
    """Completa um sprite simetrico a partir da metade esquerda."""
    return [linha + linha[::-1] for linha in metade]


def _sobrepor(base, camada):
    """Copia os pixels nao transparentes de `camada` por cima de `base`."""
    largura = len(base[0])
    resultado = []
    for indice, linha in enumerate(base):
        extra = camada[indice] if indice < len(camada) else ""
        extra = extra.ljust(largura, ".")
        resultado.append(
            "".join(c if c != "." else b for b, c in zip(linha, extra))
        )
    return resultado


def _por_tras(base, camada):
    """Desenha `camada` atras de `base` (so aparece onde a base e transparente)."""
    largura = len(base[0])
    resultado = []
    for indice, linha in enumerate(base):
        extra = camada[indice] if indice < len(camada) else ""
        extra = extra.ljust(largura, ".")
        resultado.append(
            "".join(b if b != "." else c for b, c in zip(linha, extra))
        )
    return resultado


def _margem(linhas, n=1):
    largura = len(linhas[0]) + 2 * n
    vazio = ["." * largura] * n
    return vazio + ["." * n + linha + "." * n for linha in linhas] + vazio


def _aura(linhas, simbolo="G"):
    """Contorno de brilho de 1 pixel ao redor da silhueta (estagio 2)."""
    altura, largura = len(linhas), len(linhas[0])
    grade = [list(linha) for linha in linhas]
    for y in range(altura):
        for x in range(largura):
            if linhas[y][x] != ".":
                continue
            vizinhos = (
                linhas[y + dy][x + dx]
                for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1))
                if 0 <= y + dy < altura and 0 <= x + dx < largura
            )
            if any(v != "." for v in vizinhos):
                grade[y][x] = simbolo
    return ["".join(linha) for linha in grade]


# --------------------------------------------------------------------------
# Herois (20 x 22, espelhados a partir de 10 colunas)
# --------------------------------------------------------------------------

_GUERREIRO = _espelhar([
    "..........",
    "..........",
    "......KKKK",
    ".....KHHHH",
    "....KHHHHH",
    "....KHHSSS",
    "....KSSESS",
    "....KSSESS",
    "....KsSSSS",
    ".....KsSSS",
    "......KKKK",
    "....KKAAAA",
    "...KAAAaAA",
    "...KAKAAAA",
    "...KSKaAAA",
    "...KKKBBBY",
    ".....KaAAA",
    ".....KAAKK",
    ".....KAAK.",
    ".....KaaK.",
    "....KBBBK.",
    "....KKKKK.",
])

_GUERREIRO_ARMAS = [
    ".................KK.",
    "................KWwK",
    "................KWwK",
    "................KWwK",
    "................KWwK",
    "................KWwK",
    "................KWwK",
    "................KWwK",
    "................KWwK",
    "................KWwK",
    "...............KYYYK",
    "KKKKK..........KSSK.",
    "KRRRRK........KSSSK.",
    "KRYYRK........KKBK..",
    "KRYYRK.........KYK..",
    "KRRRRK..........K...",
    ".KRRK...............",
    "..KK................",
]

_BARBARO = _espelhar([
    "..........",
    "......K.K.",
    ".....KHKHK",
    "....KHHHHH",
    "...KHHHHHH",
    "...KHHSSSS",
    "...KHSSESS",
    "....KSSESS",
    "....KsSSSS",
    ".....KsSSS",
    "....KKSSSS",
    "..KKSSSSSS",
    ".KSSSsSSSs",
    ".KSKSSsSSs",
    ".KSKsSSSSS",
    ".KKKBBBBBY",
    ".....KFFFF",
    ".....KFfFK",
    ".....KSSK.",
    ".....KSSK.",
    "....KBBBK.",
    "....KKKKK.",
])

_BARBARO_ARMAS = [
    "....................",
    "...............KKK..",
    "..............KWWWK.",
    ".............KWWwwBK",
    ".............KWwwKBK",
    "..............KKK.BK",
    "..................BK",
    "..................BK",
    "..................BK",
    "..................BK",
    "..................BK",
    "................KSSK",
    "................KSSK",
    "................KKBK",
    "..................BK",
    "..................BK",
    "..................KK",
]

_MONGE = _espelhar([
    "..........",
    "..........",
    "......KKKK",
    ".....KSSSS",
    "....KSSSSS",
    "....KSSSSS",
    "....KSSESS",
    "....KSSESS",
    "....KsSSSS",
    ".....KsSSS",
    "......KKKK",
    "....KKAAAA",
    "...KAAAaAa",
    "...KAKAAaA",
    "...KSKAaAA",
    "...KKKBBBB",
    "....KAAAaA",
    "....KAAaAA",
    "....KAaAAa",
    "....KAAAAA",
    "....KKBBKK",
    ".....KKKK.",
])

_MONGE_ARMAS = [
    "..................K.",
    ".................KYK",
    ".................KYK",
    "..................B.",
    ".................KBK",
    ".................KBK",
    ".................KBK",
    ".................KBK",
    ".................KBK",
    ".................KBK",
    ".................KBK",
    "................KSSK",
    "................KSSK",
    ".................KBK",
    ".................KBK",
    ".................KBK",
    ".................KBK",
    ".................KBK",
    ".................KBK",
    ".................KBK",
    ".................KYK",
    "..................K.",
]

# Acessorios do estagio 1 (elmo, chifres, faixa) e capa por tras.
_ELMO_GUERREIRO = [
    "",
    ".........KK.........",
    "......KKKRRKKK......",
    ".....KLLLLLLLLK.....",
    "....KLAAAAAAAALK....",
    "....KAAAAAAAAAAK....",
]

_ELMO_BARBARO = [
    "..K..............K..",
    "..KK.....KK.....KK..",
    "..KWK..KKMMKK..KWK..",
    "...KWKKMMMMMMKKWK...",
    "....KWMMMMMMMMWK....",
    "....KMMMMMMMMMMK....",
]

_FAIXA_MONGE = [
    "",
    "",
    "",
    "",
    "",
    "....KRRRRRRRRRRK....",
    "...KRK..............",
    "...KRK..............",
]

_CAPA = [
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "..KCCCCCCCCCCCCCCK..",
    "..KCCCCCCCCCCCCCCK..",
    "..KCCCCCCCCCCCCCCK..",
    "..KCCCCCCCCCCCCCCK..",
    "..KCCCCCCCCCCCCCCK..",
    "..KCcCCCCCCCCCCcCK..",
    ".KCCcCCCCCCCCCCcCCK.",
    ".KCCcCCCCCCCCCCcCCK.",
    ".KCcCCCCCCCCCCCCcCK.",
    ".KCcCCCCCCCCCCCCcCK.",
    ".KKKKKKKKKKKKKKKKKK.",
]

# Acessorios do estagio 2: coroa (guerreiro, barbaro) e aureola (monge).
_COROA = [
    "......Y.Y..Y.Y......",
    "......YYYYYYYY......",
    "......KYRYYRYK......",
]

_AUREOLA = [
    ".....KYYYYYYYYK.....",
    "....Y..........Y....",
    ".....KYYYYYYYYK.....",
]

_PALETA_BASE = {
    "K": CONTORNO,
    "S": PELE,
    "s": PELE_SOMBRA,
    "E": OLHO,
    "B": MADEIRA,
    "Y": OURO,
    "W": (236, 240, 252),
    "w": (150, 164, 196),
    "R": (206, 52, 60),
    "L": (226, 232, 246),
    "M": (150, 156, 176),
    "G": AURA,
}

HEROIS = {
    "FOR": {
        "nome": "Guerreiro",
        "corpo": _GUERREIRO,
        "armas": _GUERREIRO_ARMAS,
        "acessorio_1": _ELMO_GUERREIRO,
        "acessorio_2": _COROA,
        "paletas": (
            {"H": (120, 74, 40), "A": (104, 140, 214), "a": (58, 80, 150), "C": (176, 40, 52), "c": (120, 24, 36)},
            {"H": (120, 74, 40), "A": (150, 170, 196), "a": (90, 104, 130), "C": (176, 40, 52), "c": (120, 24, 36)},
            {"H": (120, 74, 40), "A": (250, 236, 180), "a": (210, 168, 70), "C": (110, 40, 170), "c": (70, 24, 120)},
        ),
    },
    "VIG": {
        "nome": "Bárbaro",
        "corpo": _BARBARO,
        "armas": _BARBARO_ARMAS,
        "acessorio_1": _ELMO_BARBARO,
        "acessorio_2": _COROA,
        "paletas": (
            {"H": (214, 84, 40), "F": (150, 104, 60), "f": (100, 66, 36), "C": (110, 80, 56), "c": (74, 52, 36)},
            {"H": (214, 84, 40), "F": (150, 104, 60), "f": (100, 66, 36), "C": (110, 80, 56), "c": (74, 52, 36)},
            {"H": (240, 120, 50), "F": (240, 240, 250), "f": (180, 186, 210), "C": (190, 40, 40), "c": (130, 24, 24)},
        ),
    },
    "DIS": {
        "nome": "Monge",
        "corpo": _MONGE,
        "armas": _MONGE_ARMAS,
        "acessorio_1": _FAIXA_MONGE,
        "acessorio_2": _AUREOLA,
        "paletas": (
            {"A": (236, 140, 40), "a": (180, 92, 20), "C": (60, 130, 120), "c": (36, 90, 84)},
            {"A": (236, 140, 40), "a": (180, 92, 20), "C": (60, 130, 120), "c": (36, 90, 84)},
            {"A": (250, 246, 236), "a": (214, 190, 130), "C": (240, 190, 60), "c": (190, 130, 30)},
        ),
    },
}


def estagio_do_nivel(nivel):
    """0 abaixo do nivel 10, 1 abaixo do 30, 2 do 30 em diante."""
    return 0 if nivel < 10 else 1 if nivel < 30 else 2


def sprite_do_heroi(classe_base, estagio):
    """Monta o heroi da classe no estagio (0, 1 ou 2). Retorna (linhas, paleta).

    Estagio 1 acrescenta capa e elmo (ou faixa); estagio 2 troca a cor da
    armadura, poe coroa (ou aureola) e uma aura de brilho em volta.
    """
    heroi = HEROIS.get(classe_base, HEROIS["FOR"])
    estagio = max(0, min(2, int(estagio)))
    linhas = _sobrepor(heroi["corpo"], heroi["armas"])
    if estagio >= 1:
        linhas = _por_tras(linhas, _CAPA)
    if estagio == 1:
        linhas = _sobrepor(linhas, heroi["acessorio_1"])
    elif estagio == 2:
        linhas = _sobrepor(linhas, heroi["acessorio_2"])
    linhas = _margem(linhas)
    if estagio == 2:
        linhas = _aura(linhas)
    paleta = dict(_PALETA_BASE)
    paleta.update(heroi["paletas"][estagio])
    return linhas, paleta


# --------------------------------------------------------------------------
# Chefes (24 x 24, espelhados a partir de 12 colunas)
# --------------------------------------------------------------------------

_GOLEM = _espelhar([
    "............",
    "............",
    "........KKKK",
    ".......KLLLL",
    ".......KLGGG",
    ".......KGEEG",
    ".......KGGGG",
    "...KKKKKgKKK",
    "..KLLLKKGGGG",
    ".KLGGGLKGLGG",
    ".KGGRGGKGGGG",
    ".KGGGGGKLGGg",
    ".KgGGGgKGGRG",
    "..KgggKKGGGG",
    "..KLGLKgGGGg",
    ".KLGGGLKgggg",
    ".KGGGGGKKKKK",
    ".KgGGGgK.KLG",
    "..KKKKK..KGG",
    ".........KGg",
    "........KLGG",
    "........KGGG",
    "........KKKK",
    "............",
])

_OGRO = _espelhar([
    "............",
    "........KKKK",
    ".......KOOOO",
    "......KOOOOO",
    "......KOOEOO",
    "......KOOOOO",
    "......KoOTOO",
    ".......KoTKK",
    "....KKKKOOOO",
    "...KOOOoOOOO",
    "..KOOOKOOOOO",
    "..KOOKOOooOO",
    ".KOOK.KOOOOO",
    ".KOOK.KOOOOO",
    ".KoOK.KoOOOO",
    "KOOOK..KoOOO",
    "KOOOK..KBBBB",
    ".KKK...KBbBB",
    ".......KBBbB",
    "......KOOOKK",
    "......KOOOK.",
    ".....KoOOOK.",
    ".....KKKKKK.",
    "............",
])

_SERPENTE = _espelhar([
    "............",
    "........KKKK",
    "......KKPPPP",
    ".....KPPPPPP",
    "....KPpPPPPE",
    "....KPpPPPPP",
    "....KPpPPPPP",
    ".....KPpPPKY",
    "......KPPKYY",
    ".......KPKYY",
    ".......KPKYY",
    "........KPKY",
    "........KPKY",
    ".......KPPKY",
    "......KPPKYY",
    ".....KPPKYYY",
    "....KPPKKKKK",
    "...KPPPPPPPP",
    "..KPpPPPPPPP",
    "..KPpppppppp",
    "...KPPPPPPPP",
    "....KKKKKKKK",
    "............",
    "............",
])

_GRIFO = _espelhar([
    "............",
    "............",
    "K.........KK",
    "KK.......KDD",
    "KDK.....KDDD",
    "KDDK....KDED",
    "KDDdK...KDDY",
    ".KDDdK...KYY",
    ".KDDDdK.KDKY",
    "..KDDDdKDDDK",
    "..KdDDDdDDdD",
    "...KdDDDDddD",
    "....KdDDDDdD",
    ".....KKdDDdD",
    ".......KDDDD",
    ".......KDdDD",
    "......KDDKdD",
    "......KDK.KD",
    ".....KYK..KD",
    ".....KYYK.KK",
    "......KK....",
    "............",
    "............",
    "............",
])

_TITA = _espelhar([
    "......Y.....",
    ".....YK..Y..",
    "......Y.KY..",
    "..C.....KKKK",
    ".CcC...KBBBB",
    "CcCcC.KBBBBB",
    ".CcCCCKBEEBB",
    "..CCCCKBBBBB",
    "...CCKbBBBBB",
    "....KbBBBBBB",
    "...KBBKBBBBB",
    "..KBBKbBBBBB",
    "..KBKKbBBBbB",
    "..KBK.KbBBBB",
    "..KBK.KbBbBB",
    "..KWK.KbBBBB",
    "...K..KCCCCC",
    "....CCCcCCCC",
    "...CcCCCCcCC",
    "..CcCCcCCCCC",
    "...CCCCCCCcC",
    ".....CCCCCCC",
    "............",
    "............",
])

_PALETA_CHEFE = {"K": CONTORNO, "Y": OURO}

CHEFES = {
    "Golem de Ferro": (
        _GOLEM,
        {"L": (200, 208, 222), "G": (130, 140, 160), "g": (78, 86, 104), "E": (90, 240, 255), "R": (176, 92, 50)},
    ),
    "Ogro da Montanha": (
        _OGRO,
        {"O": (112, 176, 70), "o": (66, 116, 44), "E": (240, 50, 40), "T": (250, 246, 226), "B": (130, 84, 46), "b": (90, 56, 30)},
    ),
    "Serpente do Abismo": (
        _SERPENTE,
        {"P": (140, 70, 200), "p": (90, 40, 140), "E": (255, 60, 60), "Y": (240, 200, 90)},
    ),
    "Grifo Sombrio": (
        _GRIFO,
        {"D": (80, 70, 110), "d": (46, 40, 70), "E": (255, 220, 60), "Y": (236, 170, 40)},
    ),
    "Titã do Céu": (
        _TITA,
        {"B": (90, 150, 236), "b": (50, 96, 190), "E": (255, 255, 255), "C": (236, 242, 255), "c": (170, 196, 236), "W": (255, 255, 255)},
    ),
}


def sprite_do_chefe(nome):
    """Retorna (linhas, paleta) do chefe; nome desconhecido usa o golem.

    Tambem aceita o nome de um inimigo menor (ver INIMIGOS_MENORES).
    """
    linhas, cores = CHEFES.get(nome) or INIMIGOS_MENORES.get(nome) or CHEFES["Golem de Ferro"]
    paleta = dict(_PALETA_CHEFE)
    paleta.update(cores)
    return linhas, paleta


# --------------------------------------------------------------------------
# Inimigos menores (24 x 24, espelhados), usados nos encontros do treino
# --------------------------------------------------------------------------

_DIABRETE = _espelhar([
    "............",
    "............",
    "............",
    "....K.......",
    "....KHK.....",
    ".....KHK....",
    ".....KHKKKKK",
    "......KRRRRR",
    ".....KRRRRRR",
    ".....KRREERR",
    ".....KRRRRRR",
    "......KRrKKK",
    "..K....KRRRR",
    ".KrK..KRRURR",
    ".KrrKKRRRUUR",
    "..KrrKRRRRUR",
    "...KKRRrRRRR",
    ".....KRRRRRR",
    "......KRRrRR",
    "......KRRK..",
    "......KRRK..",
    ".....KHHHK..",
    ".....KKKKK..",
    "............",
])

_MORCEGO = _espelhar([
    "............",
    "............",
    "............",
    "............",
    "............",
    "........K...",
    "........KK..",
    "........KLKK",
    ".KK.....KGGG",
    "KLLKK...KGEG",
    "KLGGLKK.KGGG",
    "KGGRGGLKKGTG",
    "KGgGGGGGLKGG",
    "KGggGGGRGGLG",
    "KgK.KgGGGGGG",
    "KK...KgKgGGG",
    "......K.KgGG",
    "........KKgG",
    ".........KKK",
    "............",
    "............",
    "............",
    "............",
    "............",
])

_COGUMELO = _espelhar([
    "............",
    "............",
    "............",
    "........KKKK",
    "......KKRRRR",
    ".....KRRWWRR",
    "....KRRWWWRR",
    "...KRRRRWRRR",
    "..KRWWRRRRRR",
    "..KWWWRRRRWW",
    ".KRWWRRRRRWW",
    ".KrRRRRRRRRR",
    ".KKKKKKKKKKK",
    "....KSKSSSSS",
    "....KSSKKSSS",
    "....KSSSESSS",
    "....KSSSESSS",
    "....KsSSSKKK",
    "....KsSSKSSS",
    "....KssSSSSS",
    "...KBBKsSSSS",
    "...KKKKKKKKK",
    "............",
    "............",
])

INIMIGOS_MENORES = {
    "Diabrete Rúnico": (
        _DIABRETE,
        {"R": (200, 56, 64), "r": (120, 28, 44), "H": (240, 230, 200), "E": (255, 230, 60), "U": (90, 250, 255)},
    ),
    "Morcego de Ferro": (
        _MORCEGO,
        {"L": (214, 222, 236), "G": (132, 142, 164), "g": (78, 86, 106), "E": (255, 60, 50), "T": (255, 255, 255), "R": (176, 96, 52)},
    ),
    "Cogumelo Bravo": (
        _COGUMELO,
        {"R": (220, 50, 50), "r": (150, 26, 36), "W": (252, 248, 236), "S": (244, 226, 190), "s": (200, 172, 130), "E": (30, 20, 30), "B": (120, 80, 50)},
    ),
}

INIMIGO_PADRAO = "Cogumelo Bravo"


def sprite_do_inimigo(nome):
    """Sprite de qualquer inimigo (chefe ou menor); desconhecido vira cogumelo."""
    if nome not in CHEFES and nome not in INIMIGOS_MENORES:
        nome = INIMIGO_PADRAO
    return sprite_do_chefe(nome)


# --------------------------------------------------------------------------
# Icones pequenos
# --------------------------------------------------------------------------

# Mao enluvada apontando para a direita (cursor de menu).
CURSOR = [
    "..KKK.....",
    ".KWWWKKKK.",
    "KWWWWWWWWK",
    "KWWWWKKKK.",
    "KWWWWWWK..",
    "KwWWWKK...",
    ".KwWWWK...",
    "..KKKK....",
]

# Seta apontando para baixo (marcador do dia de hoje).
CURSOR_BAIXO = [
    "KKKKKKKKK",
    "KWWWWWWwK",
    ".KWWWWwK.",
    "..KWWwK..",
    "...KwK...",
    "....K....",
]

CAVEIRA = [
    "..KKKKK..",
    ".KWWWWWK.",
    "KWWWWWWWK",
    "KWKKWKKWK",
    "KWKKWKKWK",
    "KWWWKWWWK",
    ".KWWWWWK.",
    "..KWKWK..",
    "..KKKKK..",
]

CASTELO = [
    "K.K.K...........K.K.K",
    "KMKMK.....KK....KMKMK",
    "KMMMK....KRRK...KMMMK",
    "KMMMK....KRK....KMMMK",
    "KMMMK.K.K.K.K.K.KMMMK",
    "KMJMKKMKMKMKMKMKKMJMK",
    "KMMMKMMMMMMMMMMMKMMMK",
    "KMMMKMMJMMMMMJMMKMMMK",
    "KMMMKMMMMMMMMMMMKMMMK",
    "KmMMKMMMMKKKMMMMKMMmK",
    "KmMMKMMMKJJJKMMMKMMmK",
    "KmmMKmMMKJJJKMMmKMmmK",
    "KKKKKKKKKKKKKKKKKKKKK",
]

MOEDA = [
    ".KKKK.",
    "KYYYyK",
    "KYKYyK",
    "KYKYyK",
    "KYYyyK",
    ".KKKK.",
]

CHAMA = [
    "..K...",
    ".KRK..",
    ".KRRK.",
    "KRYRK.",
    "KRYYRK",
    "KRYYRK",
    ".KKKK.",
]

ESTRELA = [
    "...K...",
    "..KYK..",
    "KKKYKKK",
    "KYYYYYK",
    ".KYYYK.",
    ".KYKYK.",
    ".KK.KK.",
]

PALETA_ICONES = {
    "K": CONTORNO,
    "W": (250, 250, 255),
    "w": (180, 186, 210),
    "Y": OURO,
    "y": OURO_ESCURO,
    "R": (230, 70, 40),
    "M": (120, 128, 150),
    "m": (84, 90, 110),
    "J": (40, 40, 60),
}

PALETA_CASTELO_ACESO = dict(
    PALETA_ICONES,
    M=(214, 206, 186),
    m=(170, 158, 132),
    J=OURO,
    R=(230, 50, 60),
)


# --------------------------------------------------------------------------
# Desenho
# --------------------------------------------------------------------------


def desenhar_sprite(imagem, linhas, paleta, x, y, escala=1, espelhar=False):
    """Desenha o sprite na imagem PIL a partir de (x, y), pixel a pixel."""
    draw = ImageDraw.Draw(imagem)
    for dy, linha in enumerate(linhas):
        if espelhar:
            linha = linha[::-1]
        for dx, caractere in enumerate(linha):
            cor = paleta.get(caractere)
            if caractere == "." or cor is None:
                continue
            px, py = x + dx * escala, y + dy * escala
            if escala == 1:
                draw.point((px, py), fill=cor)
            else:
                draw.rectangle((px, py, px + escala - 1, py + escala - 1), fill=cor)


def tamanho_sprite(linhas, escala=1):
    return len(linhas[0]) * escala, len(linhas) * escala


# --------------------------------------------------------------------------
# Fonte bitmap (altura de maiuscula 7, descendente 2, acento acima)
# --------------------------------------------------------------------------

# Cada glifo tem 7 linhas da altura da maiuscula (linha 6 e a base) e ate 2
# linhas extras de descendente. A largura e a do proprio glifo.
GLIFOS = {
    " ": ["...", "...", "...", "...", "...", "...", "..."],
    "A": [".XXX.", "X...X", "X...X", "XXXXX", "X...X", "X...X", "X...X"],
    "B": ["XXXX.", "X...X", "X...X", "XXXX.", "X...X", "X...X", "XXXX."],
    "C": [".XXX.", "X...X", "X....", "X....", "X....", "X...X", ".XXX."],
    "D": ["XXXX.", "X...X", "X...X", "X...X", "X...X", "X...X", "XXXX."],
    "E": ["XXXXX", "X....", "X....", "XXXX.", "X....", "X....", "XXXXX"],
    "F": ["XXXXX", "X....", "X....", "XXXX.", "X....", "X....", "X...."],
    "G": [".XXX.", "X...X", "X....", "X.XXX", "X...X", "X...X", ".XXXX"],
    "H": ["X...X", "X...X", "X...X", "XXXXX", "X...X", "X...X", "X...X"],
    "I": ["XXX", ".X.", ".X.", ".X.", ".X.", ".X.", "XXX"],
    "J": ["..XXX", "...X.", "...X.", "...X.", "...X.", "X..X.", ".XX.."],
    "K": ["X...X", "X..X.", "X.X..", "XX...", "X.X..", "X..X.", "X...X"],
    "L": ["X....", "X....", "X....", "X....", "X....", "X....", "XXXXX"],
    "M": ["X...X", "XX.XX", "X.X.X", "X.X.X", "X...X", "X...X", "X...X"],
    "N": ["X...X", "XX..X", "X.X.X", "X..XX", "X...X", "X...X", "X...X"],
    "O": [".XXX.", "X...X", "X...X", "X...X", "X...X", "X...X", ".XXX."],
    "P": ["XXXX.", "X...X", "X...X", "XXXX.", "X....", "X....", "X...."],
    "Q": [".XXX.", "X...X", "X...X", "X...X", "X.X.X", "X..X.", ".XX.X"],
    "R": ["XXXX.", "X...X", "X...X", "XXXX.", "X.X..", "X..X.", "X...X"],
    "S": [".XXXX", "X....", "X....", ".XXX.", "....X", "....X", "XXXX."],
    "T": ["XXXXX", "..X..", "..X..", "..X..", "..X..", "..X..", "..X.."],
    "U": ["X...X", "X...X", "X...X", "X...X", "X...X", "X...X", ".XXX."],
    "V": ["X...X", "X...X", "X...X", "X...X", ".X.X.", ".X.X.", "..X.."],
    "W": ["X...X", "X...X", "X...X", "X.X.X", "X.X.X", "XX.XX", "X...X"],
    "X": ["X...X", "X...X", ".X.X.", "..X..", ".X.X.", "X...X", "X...X"],
    "Y": ["X...X", "X...X", ".X.X.", "..X..", "..X..", "..X..", "..X.."],
    "Z": ["XXXXX", "....X", "...X.", "..X..", ".X...", "X....", "XXXXX"],
    "a": ["....", "....", ".XXX", "...X", ".XXX", "X..X", ".XXX"],
    "b": ["X...", "X...", "XXX.", "X..X", "X..X", "X..X", "XXX."],
    "c": ["....", "....", ".XXX", "X...", "X...", "X...", ".XXX"],
    "d": ["...X", "...X", ".XXX", "X..X", "X..X", "X..X", ".XXX"],
    "e": ["....", "....", ".XX.", "X..X", "XXXX", "X...", ".XXX"],
    "f": ["..XX", ".X..", "XXX.", ".X..", ".X..", ".X..", ".X.."],
    "g": ["....", "....", ".XXX", "X..X", "X..X", "X..X", ".XXX", "...X", "XXX."],
    "h": ["X...", "X...", "XXX.", "X..X", "X..X", "X..X", "X..X"],
    "i": [".X.", "...", "XX.", ".X.", ".X.", ".X.", "XXX"],
    "ı": ["...", "...", "XX.", ".X.", ".X.", ".X.", "XXX"],
    "j": ["..X", "...", ".XX", "..X", "..X", "..X", "..X", "..X", "XX."],
    "k": ["X...", "X...", "X..X", "X.X.", "XX..", "X.X.", "X..X"],
    "l": ["XX.", ".X.", ".X.", ".X.", ".X.", ".X.", "XXX"],
    "m": [".....", ".....", "XX.X.", "X.X.X", "X.X.X", "X.X.X", "X.X.X"],
    "n": ["....", "....", "XXX.", "X..X", "X..X", "X..X", "X..X"],
    "o": ["....", "....", ".XX.", "X..X", "X..X", "X..X", ".XX."],
    "p": ["....", "....", "XXX.", "X..X", "X..X", "X..X", "XXX.", "X...", "X..."],
    "q": ["....", "....", ".XXX", "X..X", "X..X", "X..X", ".XXX", "...X", "...X"],
    "r": ["...", "...", "X.X", "XX.", "X..", "X..", "X.."],
    "s": ["....", "....", ".XXX", "X...", ".XX.", "...X", "XXX."],
    "t": [".X..", ".X..", "XXX.", ".X..", ".X..", ".X..", "..XX"],
    "u": ["....", "....", "X..X", "X..X", "X..X", "X..X", ".XXX"],
    "v": [".....", ".....", "X...X", "X...X", ".X.X.", ".X.X.", "..X.."],
    "w": [".....", ".....", "X...X", "X...X", "X.X.X", "X.X.X", ".X.X."],
    "x": ["....", "....", "X..X", "X..X", ".XX.", "X..X", "X..X"],
    "y": ["....", "....", "X..X", "X..X", "X..X", "X..X", ".XXX", "...X", "XXX."],
    "z": ["....", "....", "XXXX", "...X", ".XX.", "X...", "XXXX"],
    "0": [".XXX.", "X...X", "X..XX", "X.X.X", "XX..X", "X...X", ".XXX."],
    "1": ["..X..", ".XX..", "..X..", "..X..", "..X..", "..X..", ".XXX."],
    "2": [".XXX.", "X...X", "....X", "...X.", "..X..", ".X...", "XXXXX"],
    "3": ["XXXX.", "....X", "....X", ".XXX.", "....X", "....X", "XXXX."],
    "4": ["...X.", "..XX.", ".X.X.", "X..X.", "XXXXX", "...X.", "...X."],
    "5": ["XXXXX", "X....", "XXXX.", "....X", "....X", "X...X", ".XXX."],
    "6": [".XXX.", "X....", "X....", "XXXX.", "X...X", "X...X", ".XXX."],
    "7": ["XXXXX", "....X", "...X.", "..X..", ".X...", ".X...", ".X..."],
    "8": [".XXX.", "X...X", "X...X", ".XXX.", "X...X", "X...X", ".XXX."],
    "9": [".XXX.", "X...X", "X...X", ".XXXX", "....X", "....X", ".XXX."],
    "!": ["X", "X", "X", "X", "X", ".", "X"],
    "?": [".XXX.", "X...X", "....X", "...X.", "..X..", ".....", "..X.."],
    ".": [".", ".", ".", ".", ".", ".", "X"],
    ",": ["..", "..", "..", "..", "..", "..", ".X", "X."],
    ":": [".", ".", "X", ".", ".", ".", "X"],
    ";": ["..", "..", ".X", "..", "..", "..", ".X", "X."],
    "'": ["X", "X", ".", ".", ".", ".", "."],
    '"': ["X.X", "X.X", "...", "...", "...", "...", "..."],
    "-": ["....", "....", "....", "XXXX", "....", "....", "...."],
    "+": [".....", "..X..", "..X..", "XXXXX", "..X..", "..X..", "....."],
    "=": ["....", "....", "XXXX", "....", "XXXX", "....", "...."],
    "/": ["....X", "....X", "...X.", "..X..", ".X...", "X....", "X...."],
    "%": ["XX...", "XX..X", "...X.", "..X..", ".X...", "X..XX", "...XX"],
    "(": [".X", "X.", "X.", "X.", "X.", "X.", ".X"],
    ")": ["X.", ".X", ".X", ".X", ".X", ".X", "X."],
    "[": ["XX", "X.", "X.", "X.", "X.", "X.", "XX"],
    "]": ["XX", ".X", ".X", ".X", ".X", ".X", "XX"],
    "<": ["...X", "..X.", ".X..", "X...", ".X..", "..X.", "...X"],
    ">": ["X...", ".X..", "..X.", "...X", "..X.", ".X..", "X..."],
    "_": ["....", "....", "....", "....", "....", "....", "XXXX"],
    "#": [".X.X.", ".X.X.", "XXXXX", ".X.X.", "XXXXX", ".X.X.", ".X.X."],
    "&": [".XX..", "X..X.", "X.X..", ".X...", "X.X.X", "X..X.", ".XX.X"],
    "*": [".....", "X.X.X", ".XXX.", "XXXXX", ".XXX.", "X.X.X", "....."],
    "·": [".", ".", ".", "X", ".", ".", "."],
    "→": ["......", "...X..", "....X.", "XXXXXX", "....X.", "...X..", "......"],
    "º": ["XXX", "X.X", "XXX", "...", "XXX", "...", "..."],
    "ª": ["XXX", "X.X", "XXX", "...", "XXX", "...", "..."],
}

# Equivalentes para caracteres sem glifo proprio.
SUBSTITUTOS = {
    "–": "-",
    "—": "-",
    "−": "-",
    "×": "x",
    "…": "...",
    "“": '"',
    "”": '"',
    "‘": "'",
    "’": "'",
    "•": "·",
}

# Marcas de acento (linhas, posicao). "cima" fica acima da letra; "baixo",
# abaixo da linha de base.
MARCAS = {
    "́": ([".X", "X."], "cima"),
    "̀": (["X.", ".X"], "cima"),
    "̂": ([".X.", "X.X"], "cima"),
    "̃": ([".X.X", "X.X."], "cima"),
    "̈": (["X.X"], "cima"),
    "̧": ([".X", "XX"], "baixo"),
}

ACIMA = 3  # linhas reservadas para acento de maiuscula
ALTURA_LINHA = ACIMA + 9  # acento + maiuscula (7) + descendente (2)


def _glifos_do_texto(texto):
    """Lista de (glifo, marcas) para cada caractere visivel do texto."""
    texto = "".join(SUBSTITUTOS.get(c, c) for c in texto)
    resultado = []
    for caractere in unicodedata.normalize("NFD", texto):
        if caractere in MARCAS:
            if resultado:
                resultado[-1][1].append(caractere)
            continue
        if unicodedata.combining(caractere):
            continue
        glifo = GLIFOS.get(caractere)
        if glifo is None:
            base = unicodedata.normalize("NFKD", caractere)[:1]
            glifo = GLIFOS.get(base, GLIFOS["?"])
            caractere = base if base in GLIFOS else "?"
        resultado.append([caractere, []])
    return resultado


def largura_texto(texto, escala=1):
    larguras = []
    for caractere, _ in _glifos_do_texto(texto):
        larguras.append(len(GLIFOS[caractere][0]))
    if not larguras:
        return 0
    return (sum(larguras) + len(larguras) - 1) * escala


def desenhar_texto(imagem, x, y, texto, cor, escala=1, sombra=None):
    """Escreve o texto com a fonte bitmap; `y` e o topo da area de acento.

    Com `sombra`, desenha antes uma copia deslocada 1 pixel (na escala) para
    baixo e para a direita, como nas janelas de menu classicas.
    """
    if sombra is not None:
        desenhar_texto(imagem, x + escala, y + escala, texto, sombra, escala)
    draw = ImageDraw.Draw(imagem)

    def ponto(px, py):
        if escala == 1:
            draw.point((px, py), fill=cor)
        else:
            draw.rectangle((px, py, px + escala - 1, py + escala - 1), fill=cor)

    cursor = x
    for caractere, marcas in _glifos_do_texto(texto):
        if caractere == "i" and marcas:
            caractere = "ı"
        glifo = GLIFOS[caractere]
        largura = len(glifo[0])
        topo = y + ACIMA * escala
        for linha_idx, linha in enumerate(glifo):
            for col, pixel in enumerate(linha):
                if pixel == "X":
                    ponto(cursor + col * escala, topo + linha_idx * escala)
        maiuscula = caractere.isupper() or caractere.isdigit()
        for marca in marcas:
            desenho, posicao = MARCAS[marca]
            larg_marca = len(desenho[0])
            mx = cursor + ((largura - larg_marca) // 2) * escala
            if posicao == "cima":
                linha0 = -len(desenho) - 1 if maiuscula else 2 - len(desenho) - 1
                linha0 = max(linha0, -ACIMA)
            else:
                linha0 = 7
            for linha_idx, linha in enumerate(desenho):
                for col, pixel in enumerate(linha):
                    if pixel == "X":
                        ponto(mx + col * escala, topo + (linha0 + linha_idx) * escala)
        cursor += (largura + 1) * escala
    return cursor - escala
