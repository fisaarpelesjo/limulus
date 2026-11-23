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


def main():
    _assert_fonte_e_sprites()
    _assert_estado_vazio()
    _assert_historico_e_level_up()
    _assert_batalha_e_encontro()
    print("jogo_visual_test: ok")


if __name__ == "__main__":
    main()
