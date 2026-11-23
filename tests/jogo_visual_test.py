import io
import os
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from PIL import Image

from limulus import jogo
from limulus import jogo_sprites
from limulus import jogo_visual


PNG_ASSINATURA = b"\x89PNG\r\n\x1a\n"
HOJE = date(2026, 11, 19)  # quinta-feira

# Com LIMULUS_AMOSTRAS apontando para uma pasta, o teste grava as imagens
# geradas para inspecao visual.
PASTA_AMOSTRAS = os.environ.get("LIMULUS_AMOSTRAS")


def _extras():
    return {"pesos": [(date(2026, 1, 1), 114.3)], "grupos": {}, "compras": [], "pausas": []}


def _sessao(sid, dia, logs):
    return {
        "id": sid,
        "data": dia,
        "tipo": "A",
        "inicio": datetime(dia.year, dia.month, dia.day, 6, 30),
        "logs": [
            {"id": sid * 100 + i, "nome": nome, "peso": peso, "rpe": rpe, "sets": 3, "reps": 12}
            for i, (nome, peso, rpe) in enumerate(logs)
        ],
    }


def _historico(semanas):
    """Semanas de 5 treinos com carga subindo, terminando antes de HOJE."""
    sessoes = []
    sid = 1
    segunda = jogo._segunda_feira(HOJE) - timedelta(weeks=semanas)
    for semana in range(semanas + 1):
        for dia in range(5):
            data = segunda + timedelta(weeks=semana, days=dia)
            if data >= HOJE or (semana == semanas and dia == 1):
                continue
            passo = semana * 2
            sessoes.append(
                _sessao(
                    sid,
                    data,
                    [
                        ("Supino reto (barra)", 50 + passo, 8),
                        ("Agachamento Zercher", 60 + passo, 9),
                        ("Remada curvada (barra)", 45 + passo, 8),
                        ("Levantamento Terra Romeno", 70 + passo, 9),
                        ("Desenvolvimento (barra em pé)", 30 + passo, 8),
                    ],
                )
            )
            sid += 1
    return sessoes


def _verificar_png(dados, largura_esperada=960):
    assert isinstance(dados, bytes)
    assert dados.startswith(PNG_ASSINATURA)
    assert len(dados) < 1_000_000, len(dados)
    imagem = Image.open(io.BytesIO(dados))
    imagem.load()
    assert imagem.format == "PNG"
    assert imagem.width == largura_esperada, imagem.size
    assert 200 <= imagem.height <= 3000, imagem.size
    return imagem


def _salvar(nome, dados):
    if PASTA_AMOSTRAS:
        pasta = Path(PASTA_AMOSTRAS)
        pasta.mkdir(parents=True, exist_ok=True)
        (pasta / nome).write_bytes(dados)


def _todas(estado, resultado, sufixo=""):
    imagens = {
        f"ficha{sufixo}.png": jogo_visual.render_ficha(estado),
        f"vitoria{sufixo}.png": jogo_visual.render_vitoria(resultado),
        f"chefes{sufixo}.png": jogo_visual.render_chefes(estado),
        f"semana{sufixo}.png": jogo_visual.render_semana(estado),
    }
    for nome, dados in imagens.items():
        _verificar_png(dados)
        _salvar(nome, dados)
    return imagens


def _assert_fonte_e_sprites():
    # Acentos do portugues sao compostos e ocupam largura.
    for texto in ("VITÓRIA", "ação", "Titã do Céu", "Missões", "Ç"):
        assert jogo_visual.sp.largura_texto(texto) > 0
    assert jogo_sprites.largura_texto("ã") == jogo_sprites.largura_texto("a")
    assert jogo_visual.cortar("x" * 200, 50).endswith("...")
    assert jogo_sprites.largura_texto(jogo_visual.cortar("x" * 200, 50)) <= 50

    assert [jogo_sprites.estagio_do_nivel(n) for n in (1, 9, 10, 29, 30, 99)] == [0, 0, 1, 1, 2, 2]
    for classe in ("FOR", "VIG", "DIS"):
        tamanhos = set()
        for estagio in range(3):
            linhas, paleta = jogo_sprites.sprite_do_heroi(classe, estagio)
            assert len({len(l) for l in linhas}) == 1
            assert all(c == "." or c in paleta for l in linhas for c in l)
            tamanhos.add((len(linhas[0]), len(linhas)))
        assert len(tamanhos) == 1
    for info in jogo.PADROES.values():
        assert info["chefe"] in jogo_sprites.CHEFES
        linhas, paleta = jogo_sprites.sprite_do_chefe(info["chefe"])
        assert len(linhas) == 24 and all(len(l) == 24 for l in linhas)
        assert all(c == "." or c in paleta for l in linhas for c in l)


def _assert_estado_vazio():
    vazio = jogo.calcular([], hoje=HOJE, extras=_extras())
    resultado = {
        "antes": vazio,
        "depois": vazio,
        "detalhe": {
            "presenca": 0, "series": 0, "recordes": [], "semana_completa": False,
            "missoes": [], "conquistas": [], "ouro": 0, "total": 0,
        },
    }
    _todas(vazio, resultado, "_vazio")
    # Sem chefes nem semana, sem quebrar.
    minimo = dict(vazio, chefes=[], semana=[], atributos={})
    jogo_visual.render_chefes(minimo)
    jogo_visual.render_ficha(minimo)
    jogo_visual.render_semana(minimo)


def _assert_historico_e_level_up():
    sessoes = _historico(8)
    estado = jogo.calcular(sessoes, hoje=HOJE, extras=_extras())
    assert estado["nivel"] > 1
    ultima = sessoes[-1]["id"]
    antes = jogo.calcular(sessoes[:-1], hoje=HOJE, extras=_extras())
    detalhe = dict(estado["por_sessao"][ultima])
    # Forca listas longas para testar o corte gracioso.
    detalhe["missoes"] = [m["nome"] for m in jogo.MISSOES][:5]
    detalhe["conquistas"] = ["Primeiro passo", "Aventureiro"]
    detalhe["recordes"] = ["Desenvolvimento (barra em pé) com um nome bem comprido demais"]
    detalhe["semana_completa"] = True
    antes_menor = dict(antes, nivel=estado["nivel"] - 1, titulo="Aprendiz")
    resultado = {"antes": antes_menor, "depois": estado, "detalhe": detalhe}
    _todas(estado, resultado)

    # Nivel 99, alvo ausente, chefe no rank maximo e nomes longos.
    extremo = dict(estado)
    extremo.update(
        nivel=99, titulo="Lenda", classe="Grão-Mestre de Nome Extremamente Comprido",
        classe_base="DIS", exp_no_nivel=0, exp_do_nivel=0, em_pausa="aberta",
        treinos_semana_atual=5,
        semana=[dict(d, estado=e) for d, e in zip(estado["semana"], ("feito", "perdido", "pausa", "hoje", "pendente", "descanso", "descanso"))],
    )
    chefes = [dict(c) for c in estado["chefes"]]
    chefes[0].update(proximo_rank=None, rank="Diamante", rank_indice=5, hp_pct=0, alvo_e1rm=None)
    chefes[1].update(alvo_e1rm=None)
    chefes[2].update(e1rm=0.0, alvo_e1rm=None, nome="Serpente do Abismo Ancestral das Profundezas")
    extremo["chefes"] = chefes
    resultado_extremo = {"antes": extremo, "depois": extremo, "detalhe": detalhe}
    _todas(extremo, resultado_extremo, "_extremo")
    for classe in ("FOR", "VIG"):
        _verificar_png(jogo_visual.render_ficha(dict(extremo, classe_base=classe, nivel=15)))


def _verificar_cena(dados):
    imagem = _verificar_png(dados)
    assert imagem.height <= 540, imagem.size
    assert len(dados) < 25_000, len(dados)
    return imagem


def _assert_batalha_e_encontro():
    for nome in ("Diabrete Rúnico", "Morcego de Ferro", "Cogumelo Bravo"):
        linhas, paleta = jogo_sprites.sprite_do_inimigo(nome)
        assert len(linhas) == 24 and all(len(l) == 24 for l in linhas)
        assert all(c == "." or c in paleta for l in linhas for c in l)
        assert jogo_sprites.sprite_do_chefe(nome) == (linhas, paleta)
    # Chefes servem de inimigo comum; nome desconhecido vira cogumelo.
    assert jogo_sprites.sprite_do_inimigo("Golem de Ferro") == jogo_sprites.sprite_do_chefe("Golem de Ferro")
    assert jogo_sprites.sprite_do_inimigo("Lagarto Qualquer") == jogo_sprites.sprite_do_inimigo("Cogumelo Bravo")

    batalha = jogo_visual.render_batalha("Golem de Ferro", 2, 5, "FOR", 12)
    _verificar_cena(batalha)
    _salvar("batalha.png", batalha)
    for classe, nivel in (("VIG", 1), ("DIS", 45)):
        _verificar_cena(jogo_visual.render_batalha("Diabrete Rúnico", 5, 5, classe, nivel))
    longa = jogo_visual.render_batalha("Inimigo Desconhecido de Nome Gigantesco Demais", 1, 1, "XYZ", 99)
    _verificar_cena(longa)
    _salvar("batalha_desconhecido.png", longa)
    _verificar_cena(jogo_visual.render_batalha("Morcego de Ferro", 9, 11, "FOR", 30))

    cinco = ["Golem de Ferro", "Morcego de Ferro", "Titã do Céu", "Diabrete Rúnico", "Cogumelo Bravo"]
    _salvar("encontro.png", jogo_visual.render_encontro(cinco, "A"))
    _verificar_cena(jogo_visual.render_encontro(cinco, "A"))
    _verificar_cena(jogo_visual.render_encontro(["Serpente do Abismo"], "C"))
    oito = cinco + ["Ogro da Montanha", "Grifo Sombrio", "Serpente do Abismo Ancestral Muito Comprida"]
    dados = jogo_visual.render_encontro(oito, "Força com nome de plano bem comprido")
    _verificar_cena(dados)
    _salvar("encontro_oito.png", dados)
    _verificar_cena(jogo_visual.render_encontro([], "B"))

    inicio = time.perf_counter()
    jogo_visual.render_batalha("Golem de Ferro", 3, 5, "FOR", 12)
    assert time.perf_counter() - inicio < 0.5

    # Nomes com tier: etiqueta na batalha e no encontro, nome base cortado.
    elite = jogo_visual.render_batalha("Golem de Ferro · Elite", 2, 5, "FOR", 12)
    _verificar_cena(elite)
    assert elite != batalha
    _salvar("batalha_elite.png", elite)
    for nome in ("Caranguejo Couraçado · Lendário", "Louva-a-deus Lâmina · Ancestral", "Nome Inventado · Elite"):
        _verificar_cena(jogo_visual.render_batalha(nome, 30, 30, "DIS", 45))
    _salvar("batalha_lendario.png", jogo_visual.render_batalha("Caranguejo Couraçado · Lendário", 3, 5, "VIG", 30))
    tiers = [
        "Rinoceronte Blindado", "Muralha Viva · Elite", "Naja Dourada · Ancestral",
        "Águia de Trovão · Lendário", "Fantasma Errante · Elite",
    ]
    encontro = jogo_visual.render_encontro(tiers, "A")
    _verificar_cena(encontro)
    _salvar("encontro_tiers.png", encontro)
    seis = [jogo_sprites.nome_com_tier(n, 2) for n in jogo_sprites.BASES_INIMIGOS[3:9]]
    seis_png = jogo_visual.render_encontro(seis, "B")
    _verificar_cena(seis_png)
    _salvar("encontro_seis_ancestrais.png", seis_png)


def _assert_tiers():
    assert jogo_sprites.TIERS == ("", "Elite", "Ancestral", "Lendário")
    assert jogo_sprites.TIERS == jogo.TIERS
    for base in ("Golem de Ferro", "Louva-a-deus Lâmina", "Fênix Cinzenta"):
        for indice in range(4):
            completo = jogo_sprites.nome_com_tier(base, indice)
            assert completo == jogo.nome_com_tier(base, indice)
            assert jogo_sprites.separar_tier(completo) == (base, indice)
    assert jogo_sprites.nome_com_tier("Basilisco", 0) == "Basilisco"
    assert jogo_sprites.nome_com_tier("Golem de Ferro", 1) == "Golem de Ferro · Elite"
    assert jogo_sprites.separar_tier("Golem de Ferro · lendario") == ("Golem de Ferro", 3)
    assert jogo_sprites.separar_tier("Golem de Ferro · Rei") == ("Golem de Ferro · Rei", 0)
    assert jogo_sprites.separar_tier("") == ("", 0)

    # Base desconhecida (com ou sem tier) cai no cogumelo.
    cogumelo = jogo_sprites.sprite_do_inimigo("Cogumelo Bravo")
    assert jogo_sprites.sprite_do_inimigo("Lagarto Qualquer") == cogumelo
    assert jogo_sprites.sprite_do_inimigo("Lagarto · Elite") == jogo_sprites.sprite_do_inimigo("Cogumelo Bravo · Elite")

    for base in jogo_sprites.BASES_INIMIGOS:
        linhas0, paleta0 = jogo_sprites.sprite_do_inimigo(base)
        for indice in range(1, 4):
            linhas, paleta = jogo_sprites.sprite_do_inimigo(jogo_sprites.nome_com_tier(base, indice))
            assert len(linhas) == 24 and all(len(l) == 24 for l in linhas), base
            assert all(c == "." or c in paleta for l in linhas for c in l), base
            # Contorno igual; a maior parte do resto da paleta muda.
            assert paleta["K"] == paleta0["K"], base
            mudadas = [k for k in paleta0 if k != "K" and paleta[k] != paleta0[k]]
            assert len(mudadas) >= max(1, (len(paleta0) - 1) // 2), (base, indice, mudadas)
            if indice < 3:
                assert linhas == linhas0, base
            else:
                # Lendario: mesmo desenho com brilho em volta.
                assert jogo_sprites.SIMBOLO_AURA_LENDARIA in "".join(linhas), base
                assert all(
                    a == b or b == "." for la, lb in zip(linhas, linhas0) for a, b in zip(la, lb)
                ), base
        cores = {
            tuple(sorted(jogo_sprites.sprite_do_inimigo(jogo_sprites.nome_com_tier(base, i))[1].items()))
            for i in range(4)
        }
        assert len(cores) == 4, base


def _folha(nomes, colunas, escala=3):
    """Folha de sprites com nome embaixo, para conferir o desenho a olho."""
    largura_celula, altura_celula = 64, 46
    linhas_grade = -(-len(nomes) // colunas)
    imagem = Image.new("RGB", (colunas * largura_celula, linhas_grade * altura_celula), (18, 26, 70))
    for i, nome in enumerate(nomes):
        x, y = (i % colunas) * largura_celula, (i // colunas) * altura_celula
        linhas, paleta = jogo_sprites.sprite_do_inimigo(nome)
        jogo_sprites.desenhar_sprite(imagem, linhas, paleta, x + 20, y + 2, 1)
        jogo_visual.texto(imagem, x + 2, y + 28, jogo_visual.cortar(nome, largura_celula - 4), jogo_visual.BRANCO)
    imagem = imagem.resize((imagem.width * escala, imagem.height * escala), Image.NEAREST)
    saida = io.BytesIO()
    imagem.save(saida, format="PNG")
    return saida.getvalue()


def _assert_bestiario():
    bases = jogo_sprites.BASES_INIMIGOS
    assert len(bases) == 48 and len(set(bases)) == 48
    assert jogo_sprites.TODOS_OS_INIMIGOS == bases
    # Mesma ordem das familias do jogo: seis por grupo, uma linha da grade.
    assert bases == tuple(jogo.BASES_INIMIGOS)
    for grupo, familia in enumerate(jogo.FAMILIAS_INIMIGOS.values()):
        assert bases[grupo * 6:grupo * 6 + 6] == tuple(familia), familia
    sprites = set()
    for nome in bases:
        assert nome in jogo_sprites.CHEFES or nome in jogo_sprites.INIMIGOS_MENORES, nome
        linhas, paleta = jogo_sprites.sprite_do_inimigo(nome)
        assert len(linhas) == 24 and all(len(l) == 24 for l in linhas), nome
        assert all(c == "." or c in paleta for l in linhas for c in l), nome
        assert jogo_sprites.sprite_do_chefe(nome) == (linhas, paleta), nome
        # Desenho com corpo: ao menos 120 pixels opacos.
        assert sum(c != "." for l in linhas for c in l) >= 120, nome
        sprites.add(tuple(linhas))
    # Cada nome tem desenho proprio (nenhum caiu no cogumelo por engano).
    assert len(sprites) == 48

    completo = jogo_visual.render_bestiario(bases, vistos=set(jogo.TODOS_OS_INIMIGOS))
    imagem = _verificar_png(completo)
    assert len(completo) < 120_000, len(completo)
    assert completo == jogo_visual.render_bestiario(bases)
    _salvar("bestiario_192.png", completo)

    alguns = set(bases[::4]) | {
        "Golem de Ferro · Elite", "Golem de Ferro · Ancestral", "Naja Dourada · Lendário",
        "Mariposa Lunar · Ancestral", "Basilisco · Elite", "Nome Inventado · Elite",
    }
    parcial = jogo_visual.render_bestiario(bases, vistos=alguns)
    _verificar_png(parcial)
    assert len(parcial) < 120_000, len(parcial)
    _salvar("bestiario_parcial.png", parcial)

    nenhum = jogo_visual.render_bestiario(bases, vistos=set())
    _verificar_png(nenhum)
    assert len(nenhum) < 120_000, len(nenhum)
    _salvar("bestiario_vazio.png", nenhum)
    assert len({completo, parcial, nenhum}) == 3

    # Uma lista menor de bases tambem funciona.
    _verificar_png(jogo_visual.render_bestiario(list(bases[:24]), vistos=set(bases[:6])))
    vazio = jogo_visual.render_bestiario([])
    assert Image.open(io.BytesIO(vazio)).width == 960
    _verificar_png(jogo_visual.render_bestiario(["Nome Inventado Qualquer"], vistos=set()))

    inicio = time.perf_counter()
    jogo_visual.render_bestiario(bases, vistos=alguns)
    assert time.perf_counter() - inicio < 1.5

    _salvar("folha_48_bases.png", _folha(bases, 6))
    for base in ("Golem de Ferro", "Caranguejo Couraçado"):
        arquivo = "tiers_" + base.split()[0].lower() + ".png"
        _salvar(arquivo, _folha([jogo_sprites.nome_com_tier(base, t) for t in range(4)], 4, escala=4))
    return imagem


def _verificar_gif(dados):
    assert dados.startswith(b"GIF89a")
    assert len(dados) < 600_000, len(dados)
    imagem = Image.open(io.BytesIO(dados))
    assert imagem.format == "GIF"
    assert imagem.width == 480, imagem.size
    assert imagem.n_frames > 8
    assert imagem.info.get("loop") == 0
    duracoes = []
    for quadro in range(imagem.n_frames):
        imagem.seek(quadro)
        duracoes.append(imagem.info.get("duration", 0))
    assert 1500 <= sum(duracoes) <= 2500, duracoes
    assert duracoes[-1] >= 700, duracoes
    return imagem


def _assert_gif_level_up():
    com_titulo = jogo_visual.render_level_up_gif(9, 10, "FOR", "Soldado", titulo_novo=True)
    _verificar_gif(com_titulo)
    _salvar("level_up.gif", com_titulo)
    _verificar_gif(jogo_visual.render_level_up_gif(3, 4, "VIG", "Aprendiz"))
    _verificar_gif(jogo_visual.render_level_up_gif(98, 99, "DIS", "Lenda", titulo_novo=True))
    _verificar_gif(jogo_visual.render_level_up_gif(5, 6, "XYZ", "Título de nome muito comprido mesmo", True))


def main():
    _assert_fonte_e_sprites()
    _assert_estado_vazio()
    _assert_historico_e_level_up()
    _assert_batalha_e_encontro()
    _assert_tiers()
    _assert_bestiario()
    _assert_gif_level_up()
    print("jogo_visual_test: ok")


if __name__ == "__main__":
    main()
