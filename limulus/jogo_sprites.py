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

import colorsys
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

def _metade(linhas):
    """Espelha meias linhas (completadas ate 12) e ajusta a grade 24 x 24."""
    return _ajustar(_espelhar([linha.ljust(12, ".")[:12] for linha in linhas]))


def _ajustar(linhas, tamanho=24):
    """Completa as linhas ate `tamanho` e apoia o desenho no chao.

    Linhas curtas ganham pontos a direita; faltando linhas, entram linhas
    vazias no topo, deixando uma linha vazia embaixo como nos chefes.
    """
    linhas = [linha.ljust(tamanho, ".")[:tamanho] for linha in linhas]
    while linhas and set(linhas[-1]) == {"."}:
        linhas.pop()
    linhas = linhas[-(tamanho - 1):]
    vazio = "." * tamanho
    return [vazio] * (tamanho - 1 - len(linhas)) + linhas + [vazio]


_TARTARUGA = _ajustar([
    "...KKKKKKKKKKKKKKKKKK",
    "KKKLLLLLLLLLLLLLLLLLLK",
    "KLLAAAAAAAAAAAAAAAAAAK",
    ".KKKKAAAAAAAAAAAAAAAK",
    ".....KaAAAAAAAAAAAaK",
    "......KaAAAAAAAAAaK",
    ".....KAAAAAAAAAAAAAK",
    "....KAAAAAAAAAAAAAAAK",
    "...KaaaaaaaaaaaaaaaaaK",
    "KKKKKKKKKKKKKKKKKKKKKKK",
    "KGGGGGKKGGGK...KGGGKKgK",
    "KGEGGGGKGGGK...KGGGK.K",
    "KGGGGGGKggGK...KggGK",
    "KgGGGGK.KKKK...KKKK",
    ".KKKKK",
])

_CAVALEIRO_OCO = _metade([
    "........KKKK",
    ".......KLLLL",
    "......KLMMMM",
    "......KMMMMM",
    "......KMKKKK",
    "......KMKEEK",
    "......KMKKKK",
    "......KMMMMM",
    ".......KKMMM",
    "...KKK..KKKK",
    "..KLLMK.KLLL",
    "..KMMMKKLMMM",
    "..KMMK.KMMRM",
    "...KK..KMMRM",
    "........KMMM",
    ".KK.....KKMM",
    "KLMK.....KKK",
    "KMMK......WW",
    ".KK......W.W",
    "..........W.",
])

_TROLL = _metade([
    "........KKKK",
    ".......KMMMM",
    "......KMMmMM",
    "......KTTTTT",
    "......KTEETT",
    "......KTTTTN",
    "......KtTTNN",
    ".......KtWTT",
    "....KKKKKTTT",
    "...KTTTTTTTT",
    "..KTTKTTtTTT",
    "..KTKKTTTTTT",
    ".KTK.KTTtTTT",
    ".KTK.KMMMMMM",
    ".KTK.KMmMMmM",
    "KTTTK.KTTKKK",
    "KtTtK.KTTK",
    ".KKK..KtTK",
    ".....KTTTK",
    ".....KKKKK",
])

_JAVALI = _ajustar([
    "..........K.K.K",
    ".........KCKCKCKK",
    ".......KKCCBBBBBBKK",
    ".....KKbBBBBBBBBBBBKK",
    "...KKbbBBBBBBBBBBBBBBK",
    "..KbEbbBBBBBBBBBBBBBBBK",
    ".KbbbbBBBBBBBBBBBBBBBBK",
    "KPPbbbBBBBBBBBBBBBBBBBK",
    "KPKPbbBBBBBBBBBBBBBBBK",
    "KPPPbWBBBBBBBBBBBBBBBK",
    ".KKKWWKbbbbbbbbbbbbbK",
    "...KWKKbbK.....KbbK",
    ".......KbbK....KbbK",
    ".......KKKK....KKKK",
])

_ESCORPIAO = _metade([
    "..........KK",
    ".........KRR",
    "..........KK",
    "..........KS",
    ".........KSS",
    "..........KS",
    ".KK......KSS",
    "KSSK......KS",
    "KSKSK....KSS",
    "KS.KSK....KS",
    ".KKKSK..KKSS",
    "....KSK.KSSS",
    ".....KSKSSsS",
    "......KSSsSS",
    "...KK.KSSSsS",
    "..KSSKKsSSSS",
    ".KS.KKSSsSSS",
    ".K..KSSSSsSS",
    "...KS.KSSSSS",
    "..KS...KSSsS",
    "..K.....KKKK",
])

_BASILISCO = _ajustar([
    "....KKK",
    "...KRRRK",
    "..KRRRRRK",
    ".KKGGGGGGK",
    "KGGEGGGGGGK",
    "KGGGGGGGGGGK",
    "KWKWKGGgGGGGK",
    ".KKKKKgGGGGGGK",
    "......KgGGGGGGK",
    ".......KgYYGGGGK",
    "........KgYYGGGGKK",
    "........KgYYYGGGGGKK",
    ".......KGKYYYGGGGGGGK",
    "......KGK.KYYYGGGGGGGK",
    ".....KKK...KKGGGgggGGGK",
    "...........KGK.KKKKgGGK",
    "..........KKK.....KgGK",
    "..................KgGK",
    "................KKgGK",
    "..........KKKKKKGGGK",
    "........KKGGGGGGKK",
    "........KKKKKKKK",
])

_HARPIA = _metade([
    "........KKKK",
    ".......KHHHH",
    "......KHHHHH",
    "K.....KHSSSS",
    "FK....KHSESS",
    "FFK...KHSSSS",
    "FFFK..KHSSKM",
    "FfFFK.KHSSKM",
    "FfFFFK.KKSSK",
    "FfFfFFKFFKKK",
    ".FfFfFFFFFFF",
    ".KFfFfFFFFFF",
    "..KFfFfFFfFF",
    "...KFfFFFFfF",
    "....KKFFFFFF",
    "......KFFfFF",
    ".......KFFFF",
    "........KYKK",
    "........KY",
    ".......KYY",
])

_KRAKEN = _metade([
    "...........K",
    "..........KP",
    ".........KPP",
    "........KPPP",
    ".......KPPpP",
    "......KPPPPP",
    "......KPpPPP",
    "......KPPPPP",
    ".....KPWWWPP",
    ".....KPWWEPP",
    ".....KPPPPPP",
    "......KPPPPP",
    "....KKPPKPPK",
    "...KPPKPKPPK",
    "..KPK.KPKKPK",
    "..KPK..KPKPK",
    "...KPK.KPK.K",
    "....KK..KPK",
    "..KK....KPK",
    "..KPKKKKPK",
    "...KKPPPK",
    ".....KKK",
])

_ELEMENTAL = _metade([
    ".....KKKK",
    "....KCCCCK.K",
    "..KKCCCcCCKC",
    ".KCCCCCCCCCC",
    "KCCcCCCCCCCC",
    "KCCCCKKCCCCC",
    "KCCCCCKYYCCC",
    "KCcCCCCCCCCC",
    ".KCCCCCKKKKC",
    "..KKCCCCCCCC",
    "....KKKKKKKK",
    "...Y......Y",
    "...YY.....Y",
    "....Y....YY",
    "...YY....Y",
    "...Y.....YY",
    "....Y.....Y",
])

_GARGULA = _metade([
    "K",
    "KK.....K",
    "KSK....KK",
    "KSSK...KSKKK",
    "KSsSK..KSSSS",
    "KSSsSK.KSESS",
    "KSSSsSKKSSSS",
    ".KSSSsSKSKWW",
    "..KSSSSKKSSS",
    "...KSSKSSSSS",
    "....KKSSSsSS",
    "....KSSKSSsS",
    "...KSSK.KSSS",
    "...KSK.KSSSS",
    "..KSSK.KSsSS",
    "..KSSSKKSSSS",
    "..KSSSSSKKSS",
    "..KsSSSSK.KS",
    "..KKKKKKK.KK",
    "....KPPPPPPP",
    "....KpPPPPPP",
    "....KKKKKKKK",
])

_FOGO_FATUO = _metade([
    "......K",
    ".....KCK...K",
    ".....KCK..KC",
    "....KCBCK.KC",
    "....KCBCKKCB",
    "...KCBBCCKCB",
    "...KCBBBBCBB",
    "..KCBBWWWBBB",
    "..KCBWWWWWWW",
    "..KCBWWWKWWW",
    "..KCBWWWKWWW",
    "..KCBWWWWWWW",
    "..KCBBWWWKKK",
    "...KCBBWWWWW",
    "....KCBBBWWW",
    ".....KCBBBBB",
    "......KKCCCC",
    "........KKKK",
    "",
    ".........B",
    "",
    "...........C",
])

_ESQUELETO = _metade([
    "........KKKK",
    ".......KWWWW",
    "......KWWWWW",
    "......KWKKWW",
    "......KWKKWW",
    "......KWWWWK",
    ".......KWKWK",
    "........KWWW",
    ".........KKW",
    "......KWWWWW",
    ".....KWKKKKK",
    ".....KWKWWWW",
    ".....KWKKKKK",
    ".....KWKWWWW",
    ".......KKKWW",
    "........KWWW",
    "........KWKK",
    "........KWK",
    "........KWK",
    ".......KWWK",
    ".......KKKK",
])

_ESQUELETO = _sobrepor(_ESQUELETO, [
    "",
    "",
    "",
    "",
    "...KK",
    "..KBS",
    ".KB.S",
    ".KB.S",
    "KB..S",
    "KB..S",
    "KB..S",
    "KB..SK",
    "KB..S",
    "KB..S",
    ".KB.S",
    ".KB.S",
    "..KBS",
    "...KK",
])

_LOBO = _metade([
    "..K",
    "..KK",
    "..KDK",
    "..KDdK",
    "..KDddKKKKKK",
    "..KDDDDDDDDD",
    ".KDDDDDDDDDD",
    ".KDDDYYKDDDD",
    ".KDDDDDDDDLL",
    "..KDDDDDDLLL",
    "...KDDDDLLKK",
    "....KDDLLLLL",
    ".....KDDKWKK",
    ".....KDDDDDD",
    "....KDDDDLLL",
    "...KDDDDDLLL",
    "..KDDdDDDDLL",
    "..KDDDDDdDDL",
    "..KDdDDKDDDD",
    "..KDDDKDDDKD",
    "..KKKKKKKKKK",
])

_ARANHA = _metade([
    "..........KK",
    ".........KCW",
    "........KCWW",
    "...K....KCCW",
    "..KLK...KCCW",
    ".KL.KK.KCCWW",
    "KL...KKCCCWC",
    "KL..KLLKCCCC",
    "K..KL..KcCCC",
    "..KL.KKKcCCC",
    ".KL.KLLKKKKK",
    "K..KL.KCEECE",
    "..KL..KCCCCC",
    ".KL..KLKKKKK",
    "KL..KL",
    "K..KL",
    "..KL",
    "..K",
])

_BAU = _metade([
    "...KKKKKKKKK",
    "..KBBBYBBBBB",
    ".KBBBBYBBEBB",
    ".KbBBBYBBBBB",
    ".KKKKKKKKKKK",
    ".KWMWMWMWMWM",
    ".KMMMMMMMMMM",
    ".KMMMMMMMMRR",
    ".KMMMMMMMRRR",
    ".KMWMWMWMRRR",
    ".KKKKKKKKKRR",
    ".KBBBBYBBBRR",
    ".KBBBBYBBBRR",
    ".KbBBBYBBBKR",
    ".KKKKKKKKKKK",
])

_PLANTA = _metade([
    ".......KKKKK",
    ".....KKGGgGG",
    "....KGGGGGGG",
    "...KGGgGGGGG",
    "...KKWKWKWKW",
    "....KPPPPPPP",
    "....KPPPpPPP",
    "....KKWKWKWK",
    "...KGGGGGGGG",
    "....KKGGgGGG",
    "......KKKKGG",
    "..........KG",
    "..KKK.....KG",
    ".KLLLK....KG",
    ".KLlLLKK..KG",
    "..KLLLLLKKKG",
    "...KKKLLLKGG",
    "......KKKKKG",
    ".....KTTTTTT",
    ".....KTtTTTT",
    "......KTTTTT",
    "......KKKKKK",
])

INIMIGOS_MENORES.update({
    "Tartaruga Bigorna": (
        _TARTARUGA,
        {"L": (200, 206, 220), "A": (96, 102, 120), "a": (60, 64, 80), "G": (110, 170, 80), "g": (70, 120, 50), "E": (20, 20, 30)},
    ),
    "Cavaleiro Oco": (
        _CAVALEIRO_OCO,
        {"L": (200, 190, 230), "M": (120, 100, 160), "E": (120, 255, 160), "R": (60, 40, 90), "W": (140, 255, 190)},
    ),
    "Troll do Pântano": (
        _TROLL,
        {"T": (110, 150, 140), "t": (70, 104, 98), "M": (90, 130, 40), "m": (60, 90, 26), "E": (255, 200, 40), "N": (140, 170, 150), "W": (240, 236, 210)},
    ),
    "Javali Colossal": (
        _JAVALI,
        {"B": (140, 90, 56), "b": (96, 58, 34), "C": (70, 40, 24), "P": (230, 150, 150), "E": (250, 60, 40), "W": (250, 246, 226)},
    ),
    "Escorpião de Areia": (
        _ESCORPIAO,
        {"S": (232, 190, 100), "s": (180, 136, 60), "R": (220, 60, 60)},
    ),
    "Basilisco": (
        _BASILISCO,
        {"G": (90, 160, 70), "g": (50, 104, 44), "Y": (230, 210, 110), "R": (220, 50, 70), "E": (255, 230, 40), "W": (255, 255, 255)},
    ),
    "Harpia Uivante": (
        _HARPIA,
        {"F": (70, 150, 160), "f": (40, 96, 110), "H": (236, 236, 250), "S": (220, 200, 230), "E": (200, 30, 60), "M": (120, 20, 40), "Y": (240, 190, 60)},
    ),
    "Kraken Mirim": (
        _KRAKEN,
        {"P": (232, 110, 150), "p": (180, 70, 110), "W": (255, 255, 255), "E": (20, 20, 60)},
    ),
    "Elemental da Tempestade": (
        _ELEMENTAL,
        {"C": (90, 88, 120), "c": (60, 58, 90), "Y": (255, 236, 80)},
    ),
    "Gárgula de Pedra": (
        _GARGULA,
        {"S": (196, 170, 130), "s": (150, 124, 90), "E": (255, 120, 40), "W": (250, 246, 230), "P": (110, 100, 96), "p": (80, 72, 70)},
    ),
    "Fogo-Fátuo": (
        _FOGO_FATUO,
        {"C": (90, 230, 255), "B": (60, 140, 240), "W": (230, 250, 255)},
    ),
    "Esqueleto Arqueiro": (
        _ESQUELETO,
        {"W": (236, 232, 214), "B": (140, 90, 50), "S": (200, 200, 210)},
    ),
    "Lobo das Sombras": (
        _LOBO,
        {"D": (70, 56, 100), "d": (44, 34, 66), "L": (130, 116, 160), "Y": (255, 230, 60), "W": (255, 255, 255)},
    ),
    "Aranha de Cristal": (
        _ARANHA,
        {"C": (120, 220, 240), "c": (70, 160, 200), "W": (240, 255, 255), "L": (150, 110, 200), "E": (255, 60, 120)},
    ),
    "Baú Mordedor": (
        _BAU,
        {"B": (170, 100, 50), "b": (120, 66, 30), "Y": (252, 214, 64), "E": (255, 50, 50), "W": (255, 255, 255), "M": (40, 10, 20), "R": (230, 90, 120)},
    ),
    "Planta Carnívora": (
        _PLANTA,
        {"G": (80, 180, 70), "g": (240, 240, 120), "W": (255, 255, 255), "P": (230, 80, 120), "p": (170, 40, 80), "L": (60, 140, 60), "l": (40, 100, 40), "T": (200, 110, 60), "t": (150, 76, 40)},
    ),
})

# --------------------------------------------------------------------------
# Segunda leva de inimigos (24 x 24), tres novos por grupo muscular
# --------------------------------------------------------------------------

_RINOCERONTE = _ajustar([
    "...K....................",
    "..KWK...................",
    "..KWK.......KKKKKKKKK...",
    "..KWWK...KKKAAAKAAAAAK..",
    "..KWWK.K.KHKAAAKAAAAAAK.",
    "..KWWKKWKKHKAAAKAAAAAAAK",
    ".KHWWKKWKHHKaAAKaAAAAAaK",
    "KHHHHHHHHHHKaaaKaaaaaaaK",
    "KHHHHHHHEHHHKKKKKKKKKKKK",
    "KHHHHHHHHHHHHHHHHHHHHHHK",
    "KhHHHHHHHHHHHHHHHHHHHHHK",
    ".KhhHHHHHHHHHHHHHHHHHHHK",
    "..KKhhHHHHHHHHHHHHHHHHK.",
    "....KKHHHHHHHHHHHHHHHHK.",
    ".....KhHHHhhHHHHHHHhHK..",
    ".....KHHHKKhHHKKKHHHKK..",
    ".....KHHHK.KHHK.KHHHK...",
    ".....KhhhK.KhhK.KhhhK...",
    ".....KKKKK.KKKK.KKKKK...",
])

_MURALHA = _metade([
    "..KKKK..KKKK",
    "..KBBK..KBBB",
    "..KBbKKKKBbB",
    "..KMMMMMMMMM",
    "..KBBMBBBMBB",
    "..KbBMbBBMbB",
    "..KMMMMMMMMM",
    "..KBBBMKKKKB",
    "..KbBBMKEEKB",
    "..KMMMMMMMMM",
    "KKKBMBBBBMBB",
    "KBBKMbBKKKKK",
    "KbBKMMMKWKWK",
    "KBBKBBBKKKKK",
    "KKKKBMBBBMBB",
    "...KbMbBBMbB",
    "...KMMMMMMMM",
    "...KBBMBKKKK",
    "...KbBMBK...",
    "..KKKKKKK...",
])

_CARANGUEJO = _metade([
    ".KKK........",
    "KCCCK.......",
    "KCKKCK......",
    "KCK..K..KK..",
    "KCKKCK.KEWK.",
    ".KCCCK.KEEK.",
    "..KCcK..KCK.",
    "...KCK..KCK.",
    "...KCCKKKCKK",
    "....KCCSSSSS",
    "...KSSsSSSSS",
    "..KSSSSSSsSS",
    "..KSsSSSSSSS",
    ".KCKSSSSsSSS",
    "KCCKsSSSSSSS",
    "KCK.KsssssKK",
    "KK.KCKKCK.KC",
    "..KCK.KCK..K",
    "..KK..KK....",
])

_MINOTAURO = _metade([
    "K...........",
    "KK..........",
    "KWK.........",
    ".KWK...KKKKK",
    ".KWWKKKRRRRR",
    "..KWWKRRRRRR",
    "...KKRRERRRR",
    "....KRRRRRRR",
    "....KrRRRKRR",
    ".....KrRRRRR",
    "..KKKKKKRRRW",
    ".KRRRRRrKKKK",
    "KRRrRRRRRRRR",
    "KRRKRRRrRRRR",
    "KRKKRRRRRRRR",
    "KRK.KRRRRBBB",
    "KrK.KbBBBBYY",
    ".KK.KRRRKRRR",
    "....KRRRKKRR",
    "....KRRrK.KR",
    "...KRRRRK.KR",
    "...KKKKKK.KK",
])

_ELEFANTE = _ajustar([
    "...........KKKKKKK......",
    "..........KYRRRRRYK.....",
    "........KKKKKKKKKKKK....",
    "....KKKKKBBBBBBBBBBBKK..",
    "...KGGGGKBYBBBBBYBBBBBK.",
    "..KGGGGKgKBBBBBBBBBBBBGK",
    "..KGEGKggKKKKKKKKKKKKGGK",
    "..KGGGKgggKGGGGGGGGGGGGK",
    "..KGGGKgggKGGGGGGGGGGGGK",
    ".KWKGGKggKGGGGGGGGGGGGgK",
    "KWWKGGGKKGGGGGGGGGGGGGgK",
    "KWKKGGKGGGGGGGGGGGGGGgK.",
    ".K.KGK.KGGGGGGGGGGGGgK..",
    "...KGK.KgGGKKGGGGKGGGK..",
    "...KGK.KGGK.KGGK.KGGK...",
    "..KGGK.KGGK.KGGK.KGGK...",
    "..KKKK.KggK.KggK.KggK...",
    ".......KKKK.KKKK.KKKK...",
])

_GIGANTE_GELO = _metade([
    "....K..K..K.",
    "...KCK.KCKCK",
    "...KCCKKCCCC",
    "....KSSSSSSS",
    "....KSSESSSS",
    "....KSsSSSSS",
    "....KCCSSSSC",
    "..KKKCCCCCCC",
    ".KSSSKCCWCCC",
    "KSSSSSKCCCCC",
    "KSSKSSSKCCWC",
    "KSSKSSSSKCCC",
    "KSK.KSSSSKCC",
    "KCK.KSSSSSKK",
    "KCK.KAAAAAAA",
    "KCK.KAaAAAaA",
    ".K..KSSSKSSS",
    "....KSSSKKSS",
    "....KSSsK.KS",
    "...KCCCCK.KK",
    "...KKKKKK...",
])

_CENTOPEIA = _ajustar([
    ".K...K..................",
    "..K.K...................",
    ".KKKKK..................",
    "KHHHHHK.................",
    "KHEHEHK.................",
    "KHHHHHK.................",
    "MKHHHKM.................",
    "MMKKKMM.................",
    "LKSSSKL.................",
    "LKSsSKL.................",
    ".KKKKK..................",
    "LKSSSKL.................",
    "LKSsSSK.KKKKKKKKKKKKK...",
    ".KKSSSSKSSSKSSSKSSSSKK..",
    "L.KSsSSKSsSKSsSKSsSSSSK.",
    "L..KSSSKSSSKSSSKSSSSSSSK",
    "....KKKKKKKKKKKKKKKKKKKK",
    ".....L.L.L.L.L.L.L.L.L..",
    "....L.L.L.L.L.L.L.L.L...",
])

_SERPE = _ajustar([
    "..........K.............",
    "..........KK...........K",
    "....KK....KMK.........KK",
    "...KSSKK..KMMK......KKMK",
    "..KSESSSK.KMmMK...KKMMMK",
    ".KSSSSSSSKKMmMMKKKMMmMMK",
    "KWSWSKKSSSKMmMMMMMMmMMK.",
    ".KKKK.KSSSKMmMmMMMmMMK..",
    "......KSSSSKmMmMMmMMMK..",
    ".......KSSSSKKmMmMMMK...",
    ".......KSSSSSSKKKKKK....",
    "........KSSsSSSSSSK.....",
    "........KSSSsSSSSSSKK...",
    ".........KSSSsSSSSSSSK..",
    "..........KSSSSSSKKSSSK.",
    "...........KSSKSSK.KSSK.",
    "..........KYKKKYK...KSK.",
    "..........KK..KK....KSSK",
    "....................KKSK",
    "......................KK",
])

_NAJA = _metade([
    "............",
    ".........KKK",
    "........KYYY",
    "......KKYEYY",
    "....KKhKYYYY",
    "...KhhhKYYYY",
    "..KhhRhhKYYY",
    "..KhRhhhhKKY",
    ".KhhRhhhhhKR",
    ".KhhRhhhhhRh",
    ".KhhhRhhhhhh",
    "..KhhhhhhhKY",
    "...KhhhhhKYy",
    "....KKhhhKYY",
    "......KKKKYy",
    "........KYYy",
    "........KyYY",
    ".......KYYyK",
    "....KKKYyYYY",
    "..KKYYYYYyyy",
    ".KYYyyyyYYYY",
    "..KKKKKKKKKK",
])

_CORVO = _ajustar([
    "................Y.......",
    "...............YY.......",
    "....KKKK......YY........",
    "...KBBBBK....YYYY.......",
    "..KBBEBBBK.....YY.......",
    "KKKBBBBBBK.....Y........",
    "KYYKBBBBBBK....Y........",
    ".KKKbBBBBBBKK...........",
    "....KbBBBBBBBKK.........",
    "....KBbBBBBBBBBKK.......",
    "....KBBbbBBBBBBBBKK.....",
    "....KBBBBbbbbBBBBBBKK...",
    ".....KBBBBBBBbbbbBBBBKK.",
    "......KBBBBBBBBBBbbbBBBK",
    ".......KKBBBBBBBBBKKKKK.",
    ".........KKKKKKKKK......",
    "..........KYK.KYK.......",
    "..........KYK.KYK.......",
    ".........KYYK.KYYK......",
])

_ARRAIA = _metade([
    "........KK..",
    "........KCK.",
    "........KCCK",
    "......KKCCCC",
    "....KKCCCcCC",
    "..KKCCCcCCCC",
    ".KCCCcCCCCEC",
    "KCCCcCCCCCCC",
    "KCcCCCCCCWCC",
    ".KKCCCCCCCCC",
    "...KKCCCWCCC",
    ".....KKCCCCC",
    ".......KKCCC",
    ".........KKC",
    "...........K",
    "...........K",
    "...........K",
])

_MARIPOSA = _metade([
    ".KKKK.......",
    "KMMMMKK...K.",
    "KMmmMMMK..K.",
    "KMmOOmMMK.KK",
    "KMmOOmMMMKKB",
    "KMMmmMMMMKEB",
    ".KMMMMMMMKBB",
    "..KKMMMMMKBB",
    "...KMMMMMKBb",
    "..KMMmMMKKBB",
    ".KMMmOmMKKBb",
    ".KMmOOmMK.KB",
    ".KMMmmMK..KB",
    "..KMMMK....K",
    "...KKK......",
])

_FENIX = _metade([
    "O...........",
    "KO.......K..",
    "KAO.....KOK.",
    "KAAO...KOK..",
    "KAAAO..KAKK.",
    "KAaAAO.KAAAK",
    "KAaAAAOKAEAA",
    ".KAaAAAKAAAY",
    ".KAAaAAAKAAY",
    "..KAAaAAKAAA",
    "...KAAaAKAAA",
    "....KAAAKAaA",
    ".....KKKAAAA",
    "......KAAaAA",
    ".......KAAAA",
    "......KOKOOK",
    ".....KOYK.OY",
    "....KO.KO..Y",
])

_DJINN = _metade([
    "........KKK.",
    ".......KTTTK",
    "......KTTTTT",
    ".....KTTTTTY",
    ".....KTtTTTT",
    "....KKKKKKKK",
    "....KSKSSSSS",
    ".....KSEESSS",
    "......KSSSSS",
    ".......KSSKK",
    "....KKKKSSSS",
    "...KSSSSSSSS",
    "..KSSsKKKKKK",
    "..KSSKssssss",
    "..KSSKKKKKKK",
    "...KKSSSSSSS",
    "....KVVVVVVV",
    ".....KWWwWWW",
    ".....KwWWWwW",
    "......KWWwWW",
    ".......KwWWW",
    "........KWwW",
    ".........KWW",
    "..........Kw",
])

_AGUIA = _metade([
    "............",
    "............",
    "........KKKK",
    ".......KWWWW",
    ".......KWEWW",
    "........KWWY",
    "KK.......KWY",
    "KBK....KKKBB",
    "KBBKKKKBBBBB",
    "KBbBBBBBbBBB",
    ".KBbBbBBBBBB",
    "..KbBbBbBBbB",
    "...KKbBbBBBB",
    ".....KKKbBBB",
    ".......KBBBB",
    ".......KBbBB",
    "......KYKKKB",
])

_DUENDE = _sobrepor(_metade([
    "............",
    "........KKKK",
    ".......KHHHH",
    "......KHHHHH",
    "K....KHHHHHH",
    "KGK..KHGGGGG",
    ".KGKKHGMMMMM",
    "..KGGGGMEMMM",
    "...KKKGGGGGG",
    ".....KGGgKKK",
    "......KGGWKW",
    ".....KHHKKKK",
    "....KHHHHHHH",
    "...KHHKHHHBB",
    "..KGGKHHHHBY",
    "..KGKKHHHHHH",
    "...K.KHHHHHH",
    ".....KHHKKKK",
    ".....KGGK...",
    "....KBBBK...",
    "....KKKKK...",
]), [
    "", "", "", "", "", "", "", "", "", "", "",
    "....................KK",
    "...................KSK",
    "..KKK.............KSK",
    ".KBYBK...........KSK",
    "KBYyYBK.........KKK",
    "KBBYBBK........KYK",
    "KBBBBBK",
    ".KKKKK",
])

_BRUXA = _ajustar([
    ".............KK.........",
    "............KHHK........",
    "...........KHHK.........",
    "..........KHHHK.........",
    ".........KHHHHHK........",
    "........KHHhHHHHK.......",
    "......KKHHHhHHHHHKK.....",
    "....KKYKKKKKKKKKKKKKK...",
    "...KKKKSSSSSSSSSSKKKK...",
    "......KSSESSSSESSK......",
    "......KSSSSSSSSSSK......",
    "......KSSSSSNSSSSK......",
    "......KHKSSSSSSKHK......",
    ".....KHHHKSSSSKHHHK.....",
    "....KHHKRRRRRRRRKHHK..K.",
    "...KHHKRRRRRRRRRRKHHKBK.",
    "...KHK.KRRRRYRRRRKKSKBK.",
    "....K.KSKRRRRRRRRK.KBK..",
    "......KRRRRRRRRRRK..KBK.",
    ".....KRRRRRRRRRRRRK.KBK.",
    "....KRRrRRRRRRrRRRRKbbK.",
    "....KKKKKKKKKKKKKKKKbbbK",
])

_LANTERNA = _metade([
    "..........KK",
    ".........K..",
    ".........K..",
    "..........KK",
    "........KKMM",
    "......KKMMMM",
    ".....KMMMMMM",
    ".....KKKKKKK",
    "..W..KMKGGGG",
    ".W...KMKGGYG",
    ".W...KMKGYYY",
    "..W..KMKGYEY",
    "...W.KMKGYYY",
    "..W..KMKGGYK",
    ".....KMKGGGG",
    ".....KKKKKKK",
    "......KMMMMM",
    ".......KKKKK",
    "........W..W",
    ".........W.W",
])

_URSO = _metade([
    "...KKK......",
    "..KBbBK.KKKK",
    "..KBbBKKBBBB",
    "...KBBBBBBBB",
    "...KBBBBBBBB",
    "...KBBKEBBBB",
    "...KBBBBBWWW",
    "...KBBBBWWKK",
    "....KBBBWWWK",
    "....KKBBBWWW",
    "..KKAAKKKKKK",
    ".KAAaAKBBBBB",
    "KAAAaAKBAAAA",
    "KAAAAKBBARAA",
    "KBBKKBBBAaAA",
    "KBBK.KBBAAAA",
    "KWBK.KBBBBBB",
    ".KK..KBBBKBB",
    ".....KBBBKKB",
    "....KBBBBK.K",
    "....KWBWBK..",
    "....KKKKKK..",
])

_LOUVA = _metade([
    "......K.....",
    ".......K....",
    "........KKKK",
    ".......KEGGG",
    ".......KEEGG",
    "........KKGG",
    "..KK.....KGG",
    ".KWK.....KGg",
    "KWWK....KKGG",
    "KWK..KKKGGKG",
    "KWK.KGGGKGGG",
    "KWKKGKK.KGGG",
    ".KWGK...KGgG",
    "..KK....KGGG",
    ".......KGGgG",
    "......KGgGGG",
    "......KGGGgG",
    ".....KK.KGGG",
    "....KK...KGG",
    "...KK....KKK",
])

_MACACO = _metade([
    "........KKKK",
    ".......KFFFF",
    "......KFFFFF",
    "......KFSSSS",
    "......KFSESS",
    "......KFSSSS",
    ".......KSSWW",
    ".......KSWKK",
    "....KKKKKSSS",
    "...KFFFFKKKK",
    "..KFFKFFFFFF",
    "..KFKFFFFUFF",
    ".KFFKFFFFUUF",
    ".KFK.KFFFFUF",
    "KFFK.KFFFFFF",
    "KFFK.KFfFFFF",
    "KSSK.KFFFKFF",
    "KSSK..KFFKFF",
    ".KK..KFFFKFF",
    ".....KSSSKSS",
    ".....KKKKKKK",
])

_PEDRA = _metade([
    "........KKKK",
    "......KKMMGG",
    ".....KGGMMMG",
    "....KGGGGGGG",
    "...KGGgGGGGG",
    "...KGGKKKGGG",
    "..KGGGKEWKGG",
    "..KGgGGGGGGG",
    "..KGGGGGGGGG",
    "..KGGgGKKKKK",
    "..KGGGGKRRRR",
    "..KgGGGGKKKK",
    "...KgGGGGGGG",
    "....KKggggGG",
    "......KKKKKK",
])

_FANTASMA = _metade([
    "........KKKK",
    "......KKWWWW",
    ".....KWWWWWW",
    "....KWWWWWWW",
    "....KWWKKWWW",
    "....KWWKKWWW",
    "....KWWWWWWW",
    "..KKWWWWWKKW",
    ".KWWWWWWWKKW",
    "KWWKWWWWWWWW",
    "KWK.KWWWWWWW",
    ".K..KWwWWWWW",
    "....KWwWWWWW",
    "....KWWwWWWW",
    "...KWWWwWWWW",
    "...KWWWWwWWW",
    "..KWWKWWWKWW",
    "..KWK.KWK.KW",
    "..KK..KK..KK",
])

_CORUJA = _metade([
    "....K.......",
    "....KK......",
    "....KOKKKKKK",
    "....KOOOOOOO",
    "...KOOKKKOOO",
    "...KOKYYYKOO",
    "...KOKYEYKOO",
    "...KOKYYYKOO",
    "...KOOKKKOKK",
    "...KOOOOOOKB",
    "..KOoOOOOOOK",
    "..KOoKKLLLLL",
    ".KOoOKLLUULL",
    ".KOoOKLLLULL",
    ".KOooKLULLLL",
    ".KOoOKLLLLLL",
    "..KOoKKLLLLL",
    "...KKKOKKLLL",
    ".....KOOOKKK",
    "......KBBKBK",
    "......KKKKKK",
])

INIMIGOS_MENORES.update({
    "Rinoceronte Blindado": (
        _RINOCERONTE,
        {"H": (150, 140, 130), "h": (100, 92, 88), "A": (190, 200, 216), "a": (120, 130, 150), "W": (250, 244, 220), "E": (255, 220, 60)},
    ),
    "Muralha Viva": (
        _MURALHA,
        {"B": (186, 92, 60), "b": (130, 56, 38), "M": (200, 194, 176), "E": (255, 200, 40), "W": (250, 246, 230)},
    ),
    "Caranguejo Couraçado": (
        _CARANGUEJO,
        {"C": (230, 96, 60), "c": (160, 56, 36), "S": (240, 150, 70), "s": (190, 100, 50), "E": (20, 20, 30), "W": (255, 255, 255)},
    ),
    "Minotauro Rochoso": (
        _MINOTAURO,
        {"R": (150, 130, 110), "r": (100, 86, 72), "W": (240, 232, 200), "E": (255, 80, 40), "B": (110, 70, 40), "b": (76, 46, 26), "Y": OURO},
    ),
    "Elefante de Guerra": (
        _ELEFANTE,
        {"G": (140, 150, 170), "g": (96, 104, 124), "B": (190, 50, 60), "Y": OURO, "R": (60, 90, 200), "E": (20, 20, 30), "W": (250, 246, 226)},
    ),
    "Gigante de Gelo": (
        _GIGANTE_GELO,
        {"S": (176, 210, 240), "s": (120, 160, 210), "C": (120, 230, 255), "W": (255, 255, 255), "A": (140, 110, 80), "a": (100, 76, 56), "E": (40, 60, 160)},
    ),
    "Centopeia Gigante": (
        _CENTOPEIA,
        {"L": (250, 210, 110), "S": (200, 90, 50), "s": (140, 56, 30), "H": (90, 50, 40), "A": (240, 200, 90), "M": (250, 230, 180), "E": (255, 240, 80)},
    ),
    "Serpe do Deserto": (
        _SERPE,
        {"S": (220, 180, 110), "s": (170, 130, 70), "M": (200, 120, 70), "m": (150, 80, 50), "E": (230, 40, 40), "Y": (250, 246, 226), "W": (250, 246, 226)},
    ),
    "Naja Dourada": (
        _NAJA,
        {"Y": (244, 204, 70), "y": (186, 136, 34), "h": (150, 96, 40), "E": (30, 30, 20), "R": (230, 50, 70)},
    ),
    "Corvo Tempestuoso": (
        _CORVO,
        {"B": (80, 84, 120), "b": (52, 54, 86), "E": (255, 60, 60), "Y": (255, 236, 80)},
    ),
    "Arraia Celeste": (
        _ARRAIA,
        {"C": (90, 140, 230), "c": (60, 96, 180), "W": (230, 240, 255), "E": (255, 240, 120)},
    ),
    "Mariposa Lunar": (
        _MARIPOSA,
        {"M": (170, 230, 200), "m": (110, 180, 160), "O": (250, 246, 190), "B": (230, 224, 210), "b": (180, 170, 150), "E": (40, 30, 60)},
    ),
    "Fênix Cinzenta": (
        _FENIX,
        {"A": (150, 146, 150), "a": (100, 96, 104), "O": (255, 120, 40), "Y": (255, 220, 80), "E": (255, 200, 40)},
    ),
    "Djinn do Vento": (
        _DJINN,
        {"T": (240, 236, 220), "t": (190, 180, 160), "Y": (230, 50, 90), "S": (110, 170, 230), "s": (70, 120, 190), "E": (255, 255, 255), "V": (200, 60, 110), "W": (200, 240, 250), "w": (140, 200, 220)},
    ),
    "Águia de Trovão": (
        _AGUIA,
        {"W": (246, 246, 250), "E": (255, 200, 40), "Y": (250, 190, 50), "B": (130, 80, 50), "b": (90, 54, 34)},
    ),
    "Duende Ladrão": (
        _DUENDE,
        {"H": (70, 110, 70), "M": (50, 40, 60), "G": (140, 190, 90), "g": (100, 140, 60), "E": (255, 236, 80), "Y": OURO, "y": OURO_ESCURO, "S": (200, 206, 220), "B": (150, 110, 70), "W": (250, 246, 230)},
    ),
    "Bruxa do Pântano": (
        _BRUXA,
        {"H": (80, 60, 110), "h": (56, 40, 80), "Y": OURO, "S": (140, 190, 110), "s": (100, 150, 80), "E": (255, 60, 60), "N": (100, 150, 80), "R": (110, 40, 60), "r": (76, 26, 42), "B": (130, 90, 50), "b": (180, 150, 90)},
    ),
    "Lanterna Assombrada": (
        _LANTERNA,
        {"M": (120, 110, 90), "G": (60, 120, 80), "Y": (190, 255, 150), "E": (20, 40, 20), "W": (150, 255, 170)},
    ),
    "Urso de Batalha": (
        _URSO,
        {"B": (130, 86, 50), "b": (90, 58, 34), "W": (220, 190, 150), "E": (20, 20, 20), "A": (180, 190, 206), "a": (120, 128, 150), "R": (200, 50, 50)},
    ),
    "Louva-a-deus Lâmina": (
        _LOUVA,
        {"G": (120, 210, 90), "g": (70, 150, 60), "E": (255, 70, 70), "W": (230, 236, 246)},
    ),
    "Macaco Rúnico": (
        _MACACO,
        {"F": (120, 90, 140), "f": (84, 60, 100), "S": (220, 190, 170), "E": (20, 20, 30), "W": (190, 160, 140), "U": (90, 250, 255)},
    ),
    "Pedra Falante": (
        _PEDRA,
        {"G": (150, 150, 140), "g": (100, 100, 96), "M": (90, 170, 70), "E": (20, 20, 30), "W": (255, 255, 255), "R": (200, 80, 90)},
    ),
    "Fantasma Errante": (
        _FANTASMA,
        {"W": (236, 240, 255), "w": (180, 190, 230), "E": (20, 20, 40)},
    ),
    "Coruja Arcana": (
        _CORUJA,
        {"O": (140, 100, 170), "o": (100, 70, 130), "Y": (255, 220, 80), "E": (20, 20, 30), "L": (220, 200, 230), "U": (110, 240, 255), "B": (250, 190, 60)},
    ),
})

# Os 48 inimigos base, seis por grupo muscular (os tres da primeira leva e
# depois os tres novos): peitoral, pernas, posterior, costas, ombros,
# triceps, biceps/antebraco e genericos.
BASES_INIMIGOS = (
    "Golem de Ferro", "Tartaruga Bigorna", "Cavaleiro Oco",
    "Rinoceronte Blindado", "Muralha Viva", "Caranguejo Couraçado",
    "Ogro da Montanha", "Troll do Pântano", "Javali Colossal",
    "Minotauro Rochoso", "Elefante de Guerra", "Gigante de Gelo",
    "Serpente do Abismo", "Escorpião de Areia", "Basilisco",
    "Centopeia Gigante", "Serpe do Deserto", "Naja Dourada",
    "Grifo Sombrio", "Harpia Uivante", "Kraken Mirim",
    "Corvo Tempestuoso", "Arraia Celeste", "Mariposa Lunar",
    "Titã do Céu", "Elemental da Tempestade", "Gárgula de Pedra",
    "Fênix Cinzenta", "Djinn do Vento", "Águia de Trovão",
    "Diabrete Rúnico", "Fogo-Fátuo", "Esqueleto Arqueiro",
    "Duende Ladrão", "Bruxa do Pântano", "Lanterna Assombrada",
    "Morcego de Ferro", "Lobo das Sombras", "Aranha de Cristal",
    "Urso de Batalha", "Louva-a-deus Lâmina", "Macaco Rúnico",
    "Cogumelo Bravo", "Baú Mordedor", "Planta Carnívora",
    "Pedra Falante", "Fantasma Errante", "Coruja Arcana",
)

# Alias mantido por compatibilidade: antes eram os 24 da primeira leva.
TODOS_OS_INIMIGOS = BASES_INIMIGOS

INIMIGO_PADRAO = "Cogumelo Bravo"


# --------------------------------------------------------------------------
# Tiers (troca de paleta, como nos JRPGs classicos)
# --------------------------------------------------------------------------

# Indice 0 e o inimigo comum; o nome completo dos demais e "Base · Tier".
TIERS = ("", "Elite", "Ancestral", "Lendário")
SEPARADOR_TIER = " · "

# Cor de destaque de cada tier (etiquetas e marcadores das telas).
CORES_TIER = {
    0: (214, 220, 236),
    1: (236, 64, 80),
    2: (176, 110, 255),
    3: (255, 206, 60),
}

# Por tier: matiz alvo (0 a 1), saturacao alvo, brilho minimo somado, ganho
# de brilho e rampa de matiz (quanto as sombras desviam do matiz alvo, como
# no hue shifting da pixel art: o dourado escurece para o laranja).
_ALVO_TIER = {
    1: (354 / 360, 0.74, 0.04, 1.00, 0.04),
    2: (272 / 360, 0.60, 0.04, 1.00, -0.05),
    3: (44 / 360, 0.86, 0.26, 0.86, 0.08),
}

# Olhos claros ganham uma cor que contrasta com o corpo recolorido.
_OLHO_TIER = {
    1: (255, 236, 90),
    2: (120, 255, 210),
    3: (255, 70, 50),
}

# Brilho ao redor da silhueta do tier Lendario (simbolo exclusivo). O tom e
# um dourado medio para nao competir com o corpo, que ja e claro.
SIMBOLO_AURA_LENDARIA = "@"
AURA_LENDARIA = (206, 150, 40)


def _aura_externa(linhas, simbolo):
    """Como `_aura`, mas so do lado de fora: buracos e vaos fechados do
    desenho (entre pernas, dentro de garras) ficam transparentes."""
    altura, largura = len(linhas), len(linhas[0])
    fora = set()
    pilha = [(y, x) for y in range(altura) for x in (0, largura - 1)]
    pilha += [(y, x) for x in range(largura) for y in (0, altura - 1)]
    while pilha:
        y, x = pilha.pop()
        if (y, x) in fora or linhas[y][x] != ".":
            continue
        fora.add((y, x))
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            if 0 <= y + dy < altura and 0 <= x + dx < largura:
                pilha.append((y + dy, x + dx))
    contorno = _aura(linhas, simbolo)
    return [
        "".join(
            c if c != simbolo or (y, x) in fora and _vizinhos_opacos(linhas, y, x) >= 1 and _vao_largo(linhas, y, x) else linhas[y][x]
            for x, c in enumerate(linha)
        )
        for y, linha in enumerate(contorno)
    ]


def _vizinhos_opacos(linhas, y, x):
    altura, largura = len(linhas), len(linhas[0])
    return sum(
        1
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1))
        if 0 <= y + dy < altura and 0 <= x + dx < largura and linhas[y + dy][x + dx] != "."
    )


def _vao_largo(linhas, y, x):
    """Falso quando o pixel fica num vao de 1 pixel entre duas partes do
    desenho (acima e abaixo, ou dos dois lados): ali o brilho viraria ruido."""
    altura, largura = len(linhas), len(linhas[0])

    def opaco(yy, xx):
        return 0 <= yy < altura and 0 <= xx < largura and linhas[yy][xx] != "."

    return not ((opaco(y - 1, x) and opaco(y + 1, x)) or (opaco(y, x - 1) and opaco(y, x + 1)))


def _sem_acento(texto):
    decomposto = unicodedata.normalize("NFD", str(texto))
    return "".join(c for c in decomposto if not unicodedata.combining(c)).casefold().strip()


_TIER_POR_CHAVE = {_sem_acento(t): i for i, t in enumerate(TIERS) if t}


def separar_tier(nome):
    """Divide "Base · Tier" em (base, indice_tier); sem tier valido, indice 0.

    O tier e reconhecido sem diferenciar maiusculas e acentos
    ("Lendario" vale como "Lendário").
    """
    nome = str(nome or "").strip()
    if SEPARADOR_TIER.strip() in nome:
        base, _, tier = nome.rpartition(SEPARADOR_TIER.strip())
        indice = _TIER_POR_CHAVE.get(_sem_acento(tier))
        if indice is not None and base.strip():
            return base.strip(), indice
    return nome, 0


def nome_com_tier(base, indice):
    """Nome completo: a base sozinha no tier 0, senao "Base · Tier"."""
    indice = max(0, min(len(TIERS) - 1, int(indice or 0)))
    base = str(base)
    return base if indice == 0 else f"{base}{SEPARADOR_TIER}{TIERS[indice]}"


def _matiz_dominante(linhas, paleta):
    """Matiz da cor que mais pesa no sprite (pixels x saturacao).

    Retorna None quando o sprite e todo cinza ou branco.
    """
    contagem = {}
    for linha in linhas:
        for c in linha:
            if c not in ".K" and c in paleta:
                contagem[c] = contagem.get(c, 0) + 1
    melhor, peso_melhor = None, 0.0
    for simbolo, quantidade in contagem.items():
        h, s, v = colorsys.rgb_to_hsv(*(x / 255 for x in paleta[simbolo]))
        if s < 0.1 or v < 0.2:
            continue
        peso = quantidade * s
        if peso > peso_melhor:
            melhor, peso_melhor = h, peso
    return melhor


def paleta_do_tier(linhas, paleta, tier):
    """Troca de paleta do tier: gira os matizes para a cor do tier.

    O contorno fica igual; olhos escuros ficam iguais e olhos claros ganham a
    cor de contraste do tier; brancos so recebem um toque da cor. As demais
    cores vao para o matiz alvo, guardando parte da diferenca de matiz entre
    elas (para as partes do corpo continuarem distintas) e o brilho original.
    """
    if not tier:
        return dict(paleta)
    h_alvo, s_alvo, piso, ganho, rampa = _ALVO_TIER[tier]
    dominante = _matiz_dominante(linhas, paleta)
    if dominante is not None and tier in (1, 2):
        # Inimigo que ja nasceu na cor do tier (diabrete vermelho, lobo
        # violeta): afasta o matiz alvo para a troca continuar visivel.
        distancia = ((h_alvo - dominante + 0.5) % 1.0) - 0.5
        if abs(distancia) < 0.05:
            h_alvo = (h_alvo + (0.07 if distancia >= 0 else -0.07)) % 1.0
    tinta = colorsys.hsv_to_rgb(h_alvo, s_alvo, 1.0)
    nova = {}
    for simbolo, cor in paleta.items():
        if simbolo == "K":
            nova[simbolo] = cor
            continue
        h, s, v = colorsys.rgb_to_hsv(*(x / 255 for x in cor))
        if simbolo == "E":
            nova[simbolo] = cor if v < 0.45 else _OLHO_TIER[tier]
            continue
        if s < 0.12 and v > 0.85:
            # Branco: so um toque da cor do tier.
            mistura = tuple(c * (1 - 0.18) + t * 0.18 for c, t in zip((r / 255 for r in cor), tinta))
            nova[simbolo] = tuple(round(min(1.0, x) * 255) for x in mistura)
            continue
        nv = min(1.0, piso + v * ganho)
        if s < 0.2 or dominante is None:
            nh, ns = h_alvo, s_alvo * 0.9
        else:
            diferenca = ((h - dominante + 0.5) % 1.0) - 0.5
            nh = h_alvo + max(-0.035, min(0.035, diferenca * 0.3))
            ns = min(1.0, 0.3 * s + 0.7 * s_alvo)
        nh = nh + (nv - 0.7) * rampa
        # Tudo fica na familia de cor do tier (o dourado nao vira verde).
        nh = (h_alvo + max(-0.045, min(0.045, nh - h_alvo))) % 1.0
        nova[simbolo] = tuple(round(x * 255) for x in colorsys.hsv_to_rgb(nh, ns, nv))
    return nova


def sprite_do_inimigo(nome):
    """Sprite de qualquer inimigo, com tier; desconhecido vira cogumelo.

    Aceita o nome base ("Golem de Ferro") ou com tier ("Golem de Ferro ·
    Elite"). Tiers 1 a 3 recolorem a paleta (Elite carmesim, Ancestral
    violeta, Lendario dourado); o Lendario ganha ainda um brilho de 1 pixel
    em volta da silhueta.
    """
    base, tier = separar_tier(nome)
    if base not in CHEFES and base not in INIMIGOS_MENORES:
        base = INIMIGO_PADRAO
    linhas, paleta = sprite_do_chefe(base)
    if not tier:
        return linhas, paleta
    paleta = paleta_do_tier(linhas, paleta, tier)
    if tier == 3:
        linhas = _aura_externa(linhas, SIMBOLO_AURA_LENDARIA)
        paleta[SIMBOLO_AURA_LENDARIA] = AURA_LENDARIA
    return linhas, paleta


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
