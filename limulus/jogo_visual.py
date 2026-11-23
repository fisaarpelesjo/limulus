"""Telas do jogo em imagem PNG, no estilo de janela de menu JRPG azul.

Cada tela e desenhada numa tela pequena (320 px de largura, ou 240 px no mapa
da semana) e ampliada com vizinho mais proximo, para manter o visual de pixel
art. O texto usa a fonte bitmap de `jogo_sprites`, que funciona sem fontes do
sistema e tem os acentos do portugues.

Funcoes publicas (todas retornam os bytes do PNG):

- `render_ficha(estado)`: ficha do personagem;
- `render_vitoria(resultado)`: tela de vitoria de uma sessao;
- `render_chefes(estado)`: chefes e HP restante ate o proximo rank;
- `render_semana(estado)`: mapa da semana em tamanho maior.

`estado` e o retorno de `jogo.calcular()`; `resultado` e o retorno de
`jogo.resultado_da_sessao()`.
"""

import io

from PIL import Image, ImageDraw

from . import jogo
from . import jogo_sprites as sp

LARGURA = 320
ESCALA_FINAL = 3
MARGEM = 4

FUNDO = (6, 8, 24)
JANELA_TOPO = (14, 22, 84)
JANELA_BASE = (40, 70, 178)
BORDA_CLARA = (244, 246, 252)
BORDA_CINZA = (176, 184, 206)
BORDA_ESCURA = (8, 8, 26)
BRANCO = (250, 250, 255)
CINZA = (176, 186, 214)
CINZA_ESCURO = (96, 104, 136)
SOMBRA = (6, 6, 22)
AMARELO = (255, 220, 80)
VERMELHO = (232, 64, 64)
VERDE = (96, 220, 120)
CIANO = (110, 220, 255)
LARANJA = (255, 160, 60)
TRILHO = (10, 14, 44)

CORES_ATRIBUTO = {
    "FOR": ((236, 84, 70), (255, 160, 140)),
    "VIG": ((80, 200, 100), (170, 250, 170)),
    "DIS": ((90, 150, 255), (170, 210, 255)),
}


# --------------------------------------------------------------------------
# Primitivas
# --------------------------------------------------------------------------


def _nova_tela(altura, largura=LARGURA):
    return Image.new("RGB", (largura, altura), FUNDO)


def _png(imagem, escala=ESCALA_FINAL):
    ampliada = imagem.resize(
        (imagem.width * escala, imagem.height * escala), Image.NEAREST
    )
    saida = io.BytesIO()
    ampliada.save(saida, format="PNG", optimize=True)
    return saida.getvalue()


def _misturar(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def janela(imagem, x, y, largura, altura):
    """Janela azul com degrade em faixas e borda dupla arredondada."""
    draw = ImageDraw.Draw(imagem)
    x2, y2 = x + largura - 1, y + altura - 1
    draw.rounded_rectangle((x, y, x2, y2), radius=5, fill=BORDA_ESCURA)
    draw.rounded_rectangle((x + 1, y + 1, x2 - 1, y2 - 1), radius=4, fill=BORDA_CLARA)
    draw.rounded_rectangle((x + 3, y + 3, x2 - 3, y2 - 3), radius=3, fill=BORDA_ESCURA)

    interno = (largura - 8, altura - 8)
    degrade = Image.new("RGB", interno)
    passos = max(1, interno[1] // 3)
    dd = ImageDraw.Draw(degrade)
    for faixa in range(passos + 1):
        cor = _misturar(JANELA_TOPO, JANELA_BASE, faixa / max(1, passos))
        dd.rectangle((0, faixa * 3, interno[0], faixa * 3 + 2), fill=cor)
    mascara = Image.new("L", interno, 0)
    ImageDraw.Draw(mascara).rounded_rectangle(
        (0, 0, interno[0] - 1, interno[1] - 1), radius=2, fill=255
    )
    imagem.paste(degrade, (x + 4, y + 4), mascara)
    # Fio cinza interno, a segunda linha da borda dupla.
    draw.rounded_rectangle(
        (x + 4, y + 4, x2 - 4, y2 - 4), radius=2, outline=BORDA_CINZA, width=1
    )


def texto(imagem, x, y, conteudo, cor=BRANCO, escala=1):
    return sp.desenhar_texto(imagem, x, y, str(conteudo), cor, escala=escala, sombra=SOMBRA)


def texto_centro(imagem, cx, y, conteudo, cor=BRANCO, escala=1):
    largura = sp.largura_texto(str(conteudo), escala)
    return texto(imagem, cx - largura // 2, y, conteudo, cor, escala)


def texto_direita(imagem, x_direita, y, conteudo, cor=BRANCO, escala=1):
    largura = sp.largura_texto(str(conteudo), escala)
    return texto(imagem, x_direita - largura, y, conteudo, cor, escala)


def cortar(conteudo, largura_max, escala=1):
    """Encurta o texto com reticencias para caber em `largura_max` pixels."""
    conteudo = str(conteudo)
    if sp.largura_texto(conteudo, escala) <= largura_max:
        return conteudo
    while conteudo and sp.largura_texto(conteudo + "...", escala) > largura_max:
        conteudo = conteudo[:-1]
    return conteudo.rstrip() + "..."


def barra(imagem, x, y, largura, altura, fracao, cor, cor_clara):
    """Medidor com contorno escuro, trilho e brilho no topo do preenchimento."""
    draw = ImageDraw.Draw(imagem)
    draw.rectangle((x, y, x + largura - 1, y + altura - 1), fill=BORDA_ESCURA)
    draw.rectangle((x + 1, y + 1, x + largura - 2, y + altura - 2), fill=TRILHO)
    fracao = max(0.0, min(1.0, fracao))
    cheio = round((largura - 2) * fracao)
    if cheio > 0:
        draw.rectangle((x + 1, y + 1, x + cheio, y + altura - 2), fill=cor)
        draw.line((x + 1, y + 1, x + cheio, y + 1), fill=cor_clara)
        if altura > 4:
            escura = _misturar(cor, (0, 0, 0), 0.35)
            draw.line((x + 1, y + altura - 2, x + cheio, y + altura - 2), fill=escura)


def cursor(imagem, x, y):
    sp.desenhar_sprite(imagem, sp.CURSOR, sp.PALETA_ICONES, x, y)


def moldura_sprite(imagem, x, y, tamanho):
    """Quadro escuro para destacar um sprite dentro da janela."""
    draw = ImageDraw.Draw(imagem)
    draw.rectangle((x, y, x + tamanho - 1, y + tamanho - 1), fill=BORDA_ESCURA)
    draw.rectangle((x + 1, y + 1, x + tamanho - 2, y + tamanho - 2), fill=(18, 26, 70))
    draw.line((x + 1, y + tamanho - 2, x + tamanho - 2, y + tamanho - 2), fill=(30, 44, 110))


def _heroi(imagem, estado, x, y, escala=2):
    estagio = sp.estagio_do_nivel(int(estado.get("nivel", 1) or 1))
    linhas, paleta = sp.sprite_do_heroi(estado.get("classe_base", "FOR"), estagio)
    sp.desenhar_sprite(imagem, linhas, paleta, x, y, escala)


def _medidor_exp(imagem, estado, x, y, largura):
    """Linha 'EXP' + barra + porcentagem, e o texto de quanto falta."""
    no_nivel = int(estado.get("exp_no_nivel", 0) or 0)
    do_nivel = int(estado.get("exp_do_nivel", 0) or 0)
    maximo = do_nivel <= 0
    fracao = 1.0 if maximo else no_nivel / do_nivel
    texto(imagem, x, y, "EXP", AMARELO)
    pct = "MAX" if maximo else f"{int(fracao * 100)}%"
    largura_pct = sp.largura_texto("100%")
    barra(imagem, x + 20, y + 4, largura - 24 - largura_pct, 8, fracao, (90, 220, 255), (210, 250, 255))
    texto_direita(imagem, x + largura, y, pct, BRANCO)
    if maximo:
        detalhe = f"Nível máximo · {estado.get('exp_total', 0)} EXP"
    else:
        detalhe = f"{no_nivel}/{do_nivel} para o Lv {int(estado.get('nivel', 1)) + 1}"
    texto(imagem, x, y + 13, cortar(detalhe, largura), CINZA)


# --------------------------------------------------------------------------
# Mapa da semana
# --------------------------------------------------------------------------


def _no_do_dia(imagem, cx, cy, raio, estado_dia):
    draw = ImageDraw.Draw(imagem)
    caixa = (cx - raio, cy - raio, cx + raio, cy + raio)
    interno = (cx - raio + 2, cy - raio + 2, cx + raio - 2, cy + raio - 2)
    if estado_dia == "feito":
        draw.ellipse(caixa, fill=BORDA_ESCURA)
        draw.ellipse((caixa[0] + 1, caixa[1] + 1, caixa[2] - 1, caixa[3] - 1), fill=sp.OURO_ESCURO)
        draw.ellipse(interno, fill=sp.OURO)
        brilho = max(1, raio // 3)
        draw.rectangle((cx - raio // 2, cy - raio // 2, cx - raio // 2 + brilho - 1, cy - raio // 2 + brilho - 1), fill=(255, 252, 220))
        # Marca de concluido.
        m = max(1, raio // 3)
        draw.line((cx - m - 1, cy, cx - 1, cy + m), fill=(120, 70, 10), width=max(1, raio // 5))
        draw.line((cx - 1, cy + m, cx + m + 1, cy - m), fill=(120, 70, 10), width=max(1, raio // 5))
    elif estado_dia == "hoje":
        # Anel tracejado (efeito de "piscando") em volta do no branco.
        for angulo in range(0, 360, 30):
            draw.arc((cx - raio - 3, cy - raio - 3, cx + raio + 3, cy + raio + 3), angulo, angulo + 15, fill=AMARELO, width=1)
        draw.ellipse(caixa, fill=BORDA_ESCURA)
        draw.ellipse((caixa[0] + 1, caixa[1] + 1, caixa[2] - 1, caixa[3] - 1), fill=BRANCO)
        draw.ellipse(interno, fill=(120, 200, 255))
        draw.ellipse((cx - raio // 3, cy - raio // 3, cx + raio // 3, cy + raio // 3), fill=BRANCO)
    elif estado_dia == "perdido":
        draw.ellipse(caixa, fill=BORDA_ESCURA)
        draw.ellipse((caixa[0] + 1, caixa[1] + 1, caixa[2] - 1, caixa[3] - 1), fill=(70, 20, 30))
        m = max(2, raio // 2)
        largura = max(1, raio // 4)
        draw.line((cx - m, cy - m, cx + m, cy + m), fill=VERMELHO, width=largura)
        draw.line((cx - m, cy + m, cx + m, cy - m), fill=VERMELHO, width=largura)
    elif estado_dia == "pausa":
        draw.ellipse(caixa, fill=BORDA_ESCURA)
        draw.ellipse((caixa[0] + 1, caixa[1] + 1, caixa[2] - 1, caixa[3] - 1), fill=(110, 114, 130))
        draw.ellipse(interno, fill=(80, 84, 100))
        draw.line((cx - raio // 2, cy, cx + raio // 2, cy), fill=(190, 194, 210), width=max(1, raio // 4))
    else:  # pendente ou descanso
        draw.ellipse(caixa, fill=BORDA_ESCURA)
        draw.ellipse((caixa[0] + 1, caixa[1] + 1, caixa[2] - 1, caixa[3] - 1), fill=(120, 150, 220))
        draw.ellipse(interno, fill=(20, 30, 90))


def desenhar_mapa(imagem, x, y, largura, estado, raio=7, escala_castelo=1):
    """Cinco nos (segunda a sexta) ligados por trilha ate o castelo.

    Ocupa `raio * 2 + 26` pixels de altura a partir de `y` (cursor de hoje
    acima, nos, nomes dos dias abaixo).
    """
    draw = ImageDraw.Draw(imagem)
    semana = list(estado.get("semana") or [])[:5]
    while len(semana) < 5:
        semana.append({"dia": ("Seg", "Ter", "Qua", "Qui", "Sex")[len(semana)], "estado": "pendente"})
    castelo_l, castelo_a = sp.tamanho_sprite(sp.CASTELO, escala_castelo)
    area = largura - castelo_l - 6
    passo = area / 5
    cy = y + 12 + raio
    centros = [round(x + passo * i + passo / 2) for i in range(5)]
    fim = x + largura - castelo_l

    # Trilha: dourada entre dias feitos, pontilhada no resto.
    pontos = centros + [fim + castelo_l // 2]
    for i in range(len(pontos) - 1):
        a, b = pontos[i], pontos[i + 1]
        feito = semana[i]["estado"] == "feito" and (i + 1 >= 5 or semana[i + 1]["estado"] == "feito")
        for px in range(a, b, 2 if feito else 4):
            cor = sp.OURO if feito else (120, 140, 200)
            draw.rectangle((px, cy - 1, px + (1 if feito else 0), cy), fill=cor)

    aceso = int(estado.get("treinos_semana_atual", 0) or 0) >= 5
    paleta = sp.PALETA_CASTELO_ACESO if aceso else sp.PALETA_ICONES
    topo_castelo = cy + raio - castelo_a + 2
    sp.desenhar_sprite(imagem, sp.CASTELO, paleta, fim, topo_castelo, escala_castelo)
    if aceso:
        # Brilhos em cruz em volta do castelo conquistado.
        for px, py in ((fim - 3, topo_castelo + 2), (fim + castelo_l - 2, topo_castelo - 3)):
            draw.point((px, py), fill=BRANCO)
            for ddx, ddy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                draw.point((px + ddx, py + ddy), fill=AMARELO)

    for i, (cx, dia) in enumerate(zip(centros, semana)):
        _no_do_dia(imagem, cx, cy, raio, dia["estado"])
        cor = BRANCO if dia["estado"] in ("feito", "hoje") else CINZA
        texto_centro(imagem, cx, cy + raio + 3, dia.get("dia", "")[:3], cor)
        if dia["estado"] == "hoje":
            sp.desenhar_sprite(imagem, sp.CURSOR_BAIXO, sp.PALETA_ICONES, cx - 4, cy - raio - 10)


# --------------------------------------------------------------------------
# Ficha
# --------------------------------------------------------------------------


def render_ficha(estado):
    """Ficha do personagem: heroi, nivel, EXP, atributos, recursos e semana."""
    altura = 232
    img = _nova_tela(altura)
    x0, w = MARGEM, LARGURA - 2 * MARGEM

    # Janela 1: heroi, nivel, titulo, classe e EXP.
    janela(img, x0, MARGEM, w, 78)
    moldura_sprite(img, x0 + 9, MARGEM + 9, 56)
    _heroi(img, estado, x0 + 13, MARGEM + 13)
    tx = x0 + 72
    largura_texto = x0 + w - 10 - tx
    fim = texto(img, tx, MARGEM + 6, f"Lv {estado.get('nivel', 1)}", BRANCO, escala=2)
    texto(img, fim + 8, MARGEM + 12, cortar(estado.get("titulo", ""), x0 + w - 10 - fim - 8), AMARELO)
    classe = f"{estado.get('classe', '')} ({estado.get('classe_base', '')})"
    if estado.get("em_pausa"):
        classe += " · em pausa"
    texto(img, tx, MARGEM + 30, cortar(classe, largura_texto), CIANO)
    _medidor_exp(img, estado, tx, MARGEM + 44, largura_texto)

    # Janela 2: atributos e recursos.
    y2 = MARGEM + 82
    janela(img, x0, y2, w, 62)
    atributos = estado.get("atributos") or {}
    for i, nome in enumerate(("FOR", "VIG", "DIS")):
        valor = max(0, min(99, int(atributos.get(nome, 0) or 0)))
        ly = y2 + 9 + i * 15
        cor, clara = CORES_ATRIBUTO[nome]
        texto(img, x0 + 12, ly, nome, clara)
        barra(img, x0 + 36, ly + 4, 108, 8, valor / 99, cor, clara)
        texto_direita(img, x0 + 166, ly, valor)
    rx = x0 + 178
    draw = ImageDraw.Draw(img)
    draw.line((rx - 6, y2 + 9, rx - 6, y2 + 52), fill=(80, 110, 200))
    sp.desenhar_sprite(img, sp.MOEDA, sp.PALETA_ICONES, rx, y2 + 13)
    texto(img, rx + 10, y2 + 9, "Ouro")
    texto_direita(img, x0 + w - 12, y2 + 9, estado.get("ouro", 0), AMARELO)
    sp.desenhar_sprite(img, sp.CHAMA, sp.PALETA_ICONES, rx, y2 + 27)
    texto(img, rx + 10, y2 + 24, "Sequência")
    texto_direita(img, x0 + w - 12, y2 + 24, estado.get("sequencia", 0), LARANJA)
    sp.desenhar_sprite(img, sp.ESTRELA, sp.PALETA_ICONES, rx - 1, y2 + 42)
    texto(img, rx + 10, y2 + 39, "Coringas")
    coringas = f"{estado.get('coringas_restantes', 0)}+{estado.get('coringas_extras', 0)}"
    texto_direita(img, x0 + w - 12, y2 + 39, coringas, VERDE)

    # Janela 3: mapa da semana.
    y3 = y2 + 66
    janela(img, x0, y3, w, altura - y3 - MARGEM)
    cursor(img, x0 + 10, y3 + 9)
    texto(img, x0 + 24, y3 + 6, "MAPA DA SEMANA", AMARELO)
    feitos = int(estado.get("treinos_semana_atual", 0) or 0)
    texto_direita(img, x0 + w - 12, y3 + 6, f"{feitos}/5 treinos", BRANCO)
    desenhar_mapa(img, x0 + 12, y3 + 18, w - 24, estado)
    return _png(img)


# --------------------------------------------------------------------------
# Vitoria
# --------------------------------------------------------------------------


def _secoes_da_vitoria(resultado):
    detalhe = resultado.get("detalhe") or {}
    antes = resultado.get("antes") or {}
    depois = resultado.get("depois") or {}
    secoes = []
    if detalhe.get("semana_completa"):
        secoes.append(("Semana completa!", [], LARANJA))
    if detalhe.get("missoes"):
        secoes.append(("Missões cumpridas", list(detalhe["missoes"]), CIANO))
    if detalhe.get("conquistas"):
        secoes.append(("Conquistas", list(detalhe["conquistas"]), AMARELO))
    if detalhe.get("recordes"):
        secoes.append(("Recordes", list(detalhe["recordes"]), VERDE))
    por_padrao = {c.get("padrao"): c for c in antes.get("chefes") or []}
    derrotas = []
    for chefe in depois.get("chefes") or []:
        anterior = por_padrao.get(chefe.get("padrao"))
        if anterior and chefe.get("rank_indice", 0) > anterior.get("rank_indice", 0):
            derrotas.append(f"{chefe.get('nome')} derrotado: rank {chefe.get('rank')}")
    if derrotas:
        secoes.append(("Chefes", derrotas, VERMELHO))
    return secoes


MAX_ITENS_SECAO = 3


def render_vitoria(resultado):
    """Tela de vitoria: EXP e ouro ganhos, level up e espolios da sessao."""
    detalhe = resultado.get("detalhe") or {}
    antes = resultado.get("antes") or {}
    depois = resultado.get("depois") or {}
    subiu = int(depois.get("nivel", 1)) > int(antes.get("nivel", 1))
    secoes = _secoes_da_vitoria(resultado)

    linhas_espolio = 0
    for _, itens, _ in secoes:
        linhas_espolio += 1 + min(len(itens), MAX_ITENS_SECAO) + (1 if len(itens) > MAX_ITENS_SECAO else 0)
    altura_espolios = 18 + max(1, linhas_espolio) * 12
    altura_topo = 104
    altura_level = 34 if subiu else 0
    altura = MARGEM + altura_topo + (altura_level + 4 if subiu else 0) + 4 + altura_espolios + MARGEM
    img = _nova_tela(altura)
    x0, w = MARGEM, LARGURA - 2 * MARGEM

    # Janela principal.
    janela(img, x0, MARGEM, w, altura_topo)
    moldura_sprite(img, x0 + 9, MARGEM + 9, 56)
    _heroi(img, depois, x0 + 13, MARGEM + 13)
    tx = x0 + 74
    texto(img, tx, MARGEM + 5, "VITÓRIA!", AMARELO, escala=3)
    y = MARGEM + 44
    fim = texto(img, tx, y, f"EXP +{detalhe.get('total', 0)}", BRANCO, escala=2)
    sp.desenhar_sprite(img, sp.MOEDA, sp.PALETA_ICONES, fim + 12, y + 9, escala=2)
    texto(img, fim + 28, y, f"+{detalhe.get('ouro', 0)}", AMARELO, escala=2)
    _medidor_exp(img, depois, x0 + 12, MARGEM + 68, w - 24)

    y = MARGEM + altura_topo + 4
    if subiu:
        draw = ImageDraw.Draw(img)
        draw.rectangle((x0, y, x0 + w - 1, y + altura_level - 1), fill=BORDA_ESCURA)
        draw.rectangle((x0 + 1, y + 1, x0 + w - 2, y + altura_level - 2), fill=sp.OURO_ESCURO)
        draw.rectangle((x0 + 3, y + 3, x0 + w - 4, y + altura_level - 4), fill=(120, 60, 10))
        for px in range(x0 + 6, x0 + w - 6, 8):
            draw.point((px, y + 5), fill=sp.OURO)
            draw.point((px + 4, y + altura_level - 6), fill=sp.OURO)
        faixa = f"LEVEL UP!  Lv {antes.get('nivel', 1)} → Lv {depois.get('nivel', 1)}"
        texto_centro(img, x0 + w // 2, y + 5, faixa, AMARELO, escala=2)
        y += altura_level + 4

    # Espolios.
    janela(img, x0, y, w, altura_espolios)
    ly = y + 7
    largura_item = w - 40
    if not secoes:
        texto(img, x0 + 14, ly, "Sem espólios extras desta vez.", CINZA)
    for titulo, itens, cor in secoes:
        cursor(img, x0 + 10, ly + 3)
        texto(img, x0 + 24, ly, titulo, cor)
        ly += 12
        for item in itens[:MAX_ITENS_SECAO]:
            texto(img, x0 + 30, ly, "· " + cortar(item, largura_item - 10), BRANCO)
            ly += 12
        if len(itens) > MAX_ITENS_SECAO:
            texto(img, x0 + 30, ly, f"+{len(itens) - MAX_ITENS_SECAO} mais", CINZA)
            ly += 12
    if subiu and depois.get("titulo") and depois.get("titulo") != antes.get("titulo"):
        texto_direita(img, x0 + w - 12, y + 7, f"Novo título: {depois['titulo']}", AMARELO)
    return _png(img)


# --------------------------------------------------------------------------
# Chefes
# --------------------------------------------------------------------------


def _nome_do_sprite(chefe):
    """Nome do sprite do chefe; se o nome mudar, cai no chefe do padrao."""
    nome = chefe.get("nome", "")
    if nome in sp.CHEFES:
        return nome
    return jogo.PADROES.get(chefe.get("padrao"), {}).get("chefe", nome)


def render_chefes(estado):
    """Uma linha por chefe: sprite, padrao, rank atual -> proximo e HP."""
    chefes = list(estado.get("chefes") or [])
    altura_linha = 64
    altura = MARGEM + 22 + max(1, len(chefes)) * (altura_linha + 2) + MARGEM
    img = _nova_tela(altura)
    x0, w = MARGEM, LARGURA - 2 * MARGEM

    janela(img, x0, MARGEM, w, 22)
    cursor(img, x0 + 10, MARGEM + 9)
    texto(img, x0 + 24, MARGEM + 5, "CHEFES", AMARELO)
    derrotados = sum(1 for c in chefes if c.get("proximo_rank") is None)
    texto_direita(img, x0 + w - 12, MARGEM + 5, f"{derrotados}/{len(chefes)} no rank máximo", CINZA)

    if not chefes:
        y = MARGEM + 24
        janela(img, x0, y, w, altura_linha)
        texto(img, x0 + 14, y + 22, "Nenhum chefe à vista.", CINZA)
        return _png(img)

    for i, chefe in enumerate(chefes):
        y = MARGEM + 24 + i * (altura_linha + 2)
        janela(img, x0, y, w, altura_linha)
        moldura_sprite(img, x0 + 8, y + 7, 50)
        linhas, paleta = sp.sprite_do_chefe(_nome_do_sprite(chefe))
        maximo = chefe.get("proximo_rank") is None
        if maximo:
            paleta = {k: _misturar(v, (40, 40, 60), 0.6) for k, v in paleta.items()}
        sp.desenhar_sprite(img, linhas, paleta, x0 + 9, y + 8, 2)
        if maximo:
            sp.desenhar_sprite(img, sp.CAVEIRA, sp.PALETA_ICONES, x0 + 24, y + 23, 2)

        tx = x0 + 64
        largura_txt = x0 + w - 12 - tx
        texto(img, tx, y + 6, cortar(chefe.get("nome", "?"), largura_txt - 60), AMARELO)
        texto_direita(img, x0 + w - 12, y + 6, chefe.get("padrao", ""), CINZA)
        rank = chefe.get("rank", "?")
        if maximo:
            texto(img, tx, y + 19, f"Rank {rank}", BRANCO)
            texto_direita(img, x0 + w - 12, y + 19, "DERROTADO", VERMELHO)
            barra(img, tx, y + 35, largura_txt, 8, 0, VERMELHO, (255, 160, 160))
            texto(img, tx, y + 44, cortar(f"1RM {chefe.get('e1rm', 0):.0f} kg · todos os ranks", largura_txt), CINZA)
            continue
        texto(img, tx, y + 19, f"{rank} → {chefe['proximo_rank']}", BRANCO)
        hp = max(0, min(100, int(chefe.get("hp_pct", 100) or 0)))
        texto(img, tx, y + 31, "HP", VERMELHO)
        largura_pct = sp.largura_texto("100%")
        barra(img, tx + 14, y + 35, largura_txt - 18 - largura_pct, 8, hp / 100, VERMELHO, (255, 160, 160))
        texto_direita(img, x0 + w - 12, y + 31, f"{hp}%", BRANCO)
        e1rm = float(chefe.get("e1rm", 0) or 0)
        alvo = chefe.get("alvo_e1rm")
        if e1rm <= 0:
            rodape = "Sem registro deste padrão ainda"
        elif alvo:
            rodape = f"1RM {e1rm:.0f} kg · alvo {float(alvo):.0f} kg"
        else:
            rodape = f"1RM {e1rm:.0f} kg · registre o peso corporal"
        texto(img, tx, y + 44, cortar(rodape, largura_txt), CINZA)
    return _png(img)


# --------------------------------------------------------------------------
# Semana
# --------------------------------------------------------------------------


def render_semana(estado):
    """Mapa da semana sozinho, em tamanho maior (240 px ampliados 4x)."""
    largura = 240
    altura = 112
    img = _nova_tela(altura, largura)
    x0, w = MARGEM, largura - 2 * MARGEM
    janela(img, x0, MARGEM, w, altura - 2 * MARGEM)
    cursor(img, x0 + 10, MARGEM + 9)
    texto(img, x0 + 24, MARGEM + 5, "MAPA DA SEMANA", AMARELO)
    feitos = int(estado.get("treinos_semana_atual", 0) or 0)
    texto_direita(img, x0 + w - 12, MARGEM + 5, f"{feitos}/5", BRANCO)
    desenhar_mapa(img, x0 + 10, MARGEM + 22, w - 20, estado, raio=9, escala_castelo=2)

    y = MARGEM + 72
    if estado.get("em_pausa"):
        rodape = "Em pausa: a semana não conta."
        cor = CINZA
    elif feitos >= 5:
        rodape = "Castelo conquistado!"
        cor = AMARELO
    else:
        faltam = 5 - feitos
        rodape = f"Faltam {faltam} treino{'s' if faltam > 1 else ''} até o castelo."
        cor = BRANCO
    texto(img, x0 + 12, y, cortar(rodape, w - 24), cor)
    texto(
        img,
        x0 + 12,
        y + 12,
        cortar(f"Sequência {estado.get('sequencia', 0)} · coringas {estado.get('coringas_restantes', 0)}+{estado.get('coringas_extras', 0)}", w - 24),
        CINZA,
    )
    return _png(img, escala=4)


# --------------------------------------------------------------------------
# Batalha e encontro (um exercicio = um inimigo)
# --------------------------------------------------------------------------

ALTURA_CENA = 180
CHAO = 112
CEU_TOPO = (12, 10, 40)
CEU_BASE = (58, 52, 120)
MONTANHA = (34, 30, 78)
GRAMA = (58, 120, 60)
GRAMA_ESCURA = (40, 88, 46)
TERRA = (96, 70, 44)


def _cenario(imagem, chao=CHAO):
    """Ceu em faixas, estrelas fixas, montanhas ao fundo e chao gramado."""
    draw = ImageDraw.Draw(imagem)
    largura = imagem.width
    for y in range(0, chao, 4):
        draw.rectangle((0, y, largura, y + 3), fill=_misturar(CEU_TOPO, CEU_BASE, y / chao))
    for i in range(18):
        sx, sy = (i * 73 + 11) % largura, (i * 37 + 5) % (chao - 40)
        draw.point((sx, sy), fill=BRANCO if i % 3 else AMARELO)
    picos = [(0, chao - 18), (40, chao - 40), (82, chao - 22), (130, chao - 48),
             (176, chao - 24), (220, chao - 44), (268, chao - 20), (largura, chao - 36)]
    draw.polygon(picos + [(largura, chao), (0, chao)], fill=MONTANHA)
    draw.rectangle((0, chao, largura, imagem.height), fill=GRAMA)
    draw.line((0, chao, largura, chao), fill=(120, 190, 110))
    for y in range(chao + 4, imagem.height, 5):
        for x in range((y * 7) % 13, largura, 13):
            draw.line((x, y, x + 2, y), fill=GRAMA_ESCURA)


def _sombra(imagem, cx, cy, largura):
    ImageDraw.Draw(imagem).ellipse(
        (cx - largura // 2, cy - 3, cx + largura // 2, cy + 3), fill=GRAMA_ESCURA
    )


def _pips(imagem, x_direita, cy, posicao, total, espaco_max=150):
    """Bolinhas de progresso: feitos (ouro), atual (branco), proximos (escuro)."""
    total = max(1, int(total))
    passo = max(4, min(10, espaco_max // total))
    raio = 3 if passo >= 8 else 1
    draw = ImageDraw.Draw(imagem)
    x0 = x_direita - (total - 1) * passo - raio
    for i in range(total):
        cx = x0 + i * passo
        numero = i + 1
        caixa = (cx - raio, cy - raio, cx + raio, cy + raio)
        if numero < posicao:
            draw.ellipse(caixa, fill=sp.OURO, outline=BORDA_ESCURA)
        elif numero == posicao:
            draw.ellipse((cx - raio - 1, cy - raio - 1, cx + raio + 1, cy + raio + 1), fill=AMARELO)
            draw.ellipse(caixa, fill=BRANCO, outline=BORDA_ESCURA)
        else:
            draw.ellipse(caixa, fill=TRILHO, outline=CINZA_ESCURO)


def render_batalha(inimigo, posicao, total, classe_base="FOR", nivel=1):
    """Cena de batalha de um exercicio: inimigo a esquerda, heroi a direita.

    `inimigo` e o nome de exibicao (chefe ou inimigo menor; nome desconhecido
    vira o Cogumelo Bravo). A imagem nao mostra cargas; elas vao no texto.
    """
    total = max(1, int(total or 1))
    posicao = max(1, min(total, int(posicao or 1)))
    img = _nova_tela(ALTURA_CENA)
    _cenario(img)

    linhas, paleta = sp.sprite_do_inimigo(inimigo)
    _sombra(img, 36 + 36, CHAO + 4, 56)
    sp.desenhar_sprite(img, linhas, paleta, 36, CHAO - 66, 3)

    estagio = sp.estagio_do_nivel(int(nivel or 1))
    heroi, paleta_heroi = sp.sprite_do_heroi(classe_base, estagio)
    largura_heroi, altura_heroi = sp.tamanho_sprite(heroi, 3)
    hx = LARGURA - 36 - largura_heroi
    _sombra(img, hx + largura_heroi // 2, CHAO + 4, 44)
    sp.desenhar_sprite(img, heroi, paleta_heroi, hx, CHAO - altura_heroi + 6, 3, espelhar=True)

    x0, w = MARGEM, LARGURA - 2 * MARGEM
    y = ALTURA_CENA - 50 - MARGEM
    janela(img, x0, y, w, 50)
    cursor(img, x0 + 10, y + 9)
    texto(img, x0 + 24, y + 6, f"INIMIGO {posicao}/{total}", AMARELO)
    _pips(img, x0 + w - 14, y + 12, posicao, total)
    nome = str(inimigo or sp.INIMIGO_PADRAO)
    texto(img, x0 + 12, y + 21, cortar(nome, w - 24, 2), BRANCO, escala=2)
    return _png(img)


def _quebrar_nome(nome, largura_max):
    """Ate duas linhas, quebrando por palavra; o resto e cortado."""
    palavras = str(nome).split()
    if not palavras:
        return [""]
    linhas = [palavras[0]]
    for palavra in palavras[1:]:
        tentativa = f"{linhas[-1]} {palavra}"
        if sp.largura_texto(tentativa) <= largura_max:
            linhas[-1] = tentativa
        elif len(linhas) < 2:
            linhas.append(palavra)
        else:
            linhas[-1] = tentativa
    return [cortar(linha, largura_max) for linha in linhas[:2]]


MAX_INIMIGOS_ENCONTRO = 6


def render_encontro(inimigos, plano):
    """Tela 'INIMIGOS APARECERAM!' com a fila de inimigos do treino."""
    inimigos = [str(n) for n in (inimigos or [])]
    mostrados = inimigos[:MAX_INIMIGOS_ENCONTRO]
    extras = len(inimigos) - len(mostrados)
    img = _nova_tela(ALTURA_CENA)
    chao = 92
    _cenario(img, chao)
    x0, w = MARGEM, LARGURA - 2 * MARGEM

    janela(img, x0, MARGEM, w, 24)
    texto_centro(img, LARGURA // 2, MARGEM + 6, "INIMIGOS APARECERAM!", AMARELO)
    if extras > 0:
        texto_direita(img, x0 + w - 10, MARGEM + 6, f"+{extras}", BRANCO)

    if mostrados:
        vaga = w / len(mostrados)
        escala = 2
        for i, nome in enumerate(mostrados):
            cx = round(x0 + vaga * i + vaga / 2)
            linhas, paleta = sp.sprite_do_inimigo(nome)
            largura, altura = sp.tamanho_sprite(linhas, escala)
            _sombra(img, cx, chao + 2, 36)
            sp.desenhar_sprite(img, linhas, paleta, cx - largura // 2, chao - altura + 6, escala)
            for j, linha in enumerate(_quebrar_nome(nome, int(vaga) - 4)):
                texto_centro(img, cx, chao + 6 + j * 11, linha, BRANCO)
    else:
        texto_centro(img, LARGURA // 2, chao - 30, "Nenhum inimigo à vista.", CINZA)

    y = ALTURA_CENA - 46 - MARGEM
    janela(img, x0, y, w, 46)
    cursor(img, x0 + 10, y + 17)
    texto(img, x0 + 24, y + 9, cortar(f"Treino {plano}", w - 120, 2), BRANCO, escala=2)
    quantidade = len(inimigos)
    texto_direita(img, x0 + w - 12, y + 15, f"{quantidade} inimigo{'s' if quantidade != 1 else ''}", CIANO)
    return _png(img)
