import gc
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from limulus import db_ops
from limulus import jogo
from limulus import telegram_poller


def _assert_regras_puras():
    assert jogo.aderencia_rpe(8) == 1.0
    assert jogo.aderencia_rpe(9) == 1.0
    assert jogo.aderencia_rpe(7) == 0.5
    assert jogo.aderencia_rpe(10) == 0.3
    assert jogo.aderencia_rpe(None) == 0.5

    assert jogo.exp_para_nivel(1) == 0
    assert jogo.exp_para_nivel(2) == 100
    assert jogo.nivel_por_exp(0) == 1
    assert jogo.nivel_por_exp(99) == 1
    assert jogo.nivel_por_exp(100) == 2
    for nivel in range(1, 60):
        assert jogo.exp_para_nivel(nivel + 1) > jogo.exp_para_nivel(nivel)

    assert jogo.titulo_do_nivel(1) == "Aprendiz"
    assert jogo.titulo_do_nivel(4) == "Aprendiz"
    assert jogo.titulo_do_nivel(5) == "Escudeiro"
    assert jogo.titulo_do_nivel(99) == "Lenda"


def _sessao(sid, dia, logs):
    return {
        "id": sid,
        "data": dia,
        "logs": [
            {"id": sid * 100 + i, "nome": nome, "peso": peso, "rpe": rpe}
            for i, (nome, peso, rpe) in enumerate(logs)
        ],
    }


def _assert_exp_e_recordes():
    segunda = date(2026, 11, 2)
    sessoes = [
        _sessao(1, segunda, [("Supino", 50, 8), ("Remada", 40, 9)]),
        # Recorde com RPE 9 conta; recorde com RPE 10 nao conta.
        _sessao(2, segunda + timedelta(days=1), [("Supino", 52, 9), ("Remada", 42, 10)]),
        # Segundo recorde do mesmo exercicio na mesma semana nao conta.
        _sessao(3, segunda + timedelta(days=2), [("Supino", 54, 8)]),
    ]
    estado = jogo.calcular(sessoes, hoje=segunda + timedelta(days=2))
    s1, s2, s3 = (estado["por_sessao"][i] for i in (1, 2, 3))
    assert s1 == {"presenca": 50, "series": 20, "recordes": [], "semana_completa": False, "total": 70}
    assert s2["series"] == 13  # 10 + 3
    assert s2["recordes"] == ["Supino"]
    assert s2["total"] == 50 + 13 + 20
    assert s3["recordes"] == []
    assert estado["exp_total"] == 70 + 83 + 60
    assert estado["treinos_semana_atual"] == 3
    assert estado["sequencia"] == 0


def _semana(sid_inicial, segunda, treinos):
    return [
        _sessao(sid_inicial + i, segunda + timedelta(days=i), [("Supino", 50, 8)])
        for i in range(treinos)
    ]


def _assert_sequencia_e_coringas():
    inicio = date(2026, 9, 7)  # segunda-feira
    # 5/5, 3/5 (coringa 1 de setembro), 5/5, 2/5 (coringa 2), 5/5.
    sessoes = []
    sid = 1
    for indice, treinos in enumerate((5, 3, 5, 2, 5)):
        semana = _semana(sid, inicio + timedelta(weeks=indice), treinos)
        sessoes.extend(semana)
        sid += len(semana)
    hoje = inicio + timedelta(weeks=5)  # segunda seguinte, sem treino
    estado = jogo.calcular(sessoes, hoje=hoje)
    assert estado["sequencia"] == 3
    assert estado["treinos_semana_atual"] == 0
    # A semana completa da bonus exatamente no quinto treino.
    quinto = estado["por_sessao"][5]
    assert quinto["semana_completa"] is True
    assert quinto["total"] == 50 + 10 + jogo.EXP_SEMANA
    assert estado["por_sessao"][4]["semana_completa"] is False

    # Terceira semana incompleta no mesmo mes zera a sequencia.
    sessoes_mes = []
    sid = 1
    for indice, treinos in enumerate((5, 4, 4, 4, 5)):
        semana = _semana(sid, date(2026, 9, 7) + timedelta(weeks=indice), treinos)
        sessoes_mes.extend(semana)
        sid += len(semana)
    estado = jogo.calcular(sessoes_mes, hoje=date(2026, 10, 12))
    assert estado["sequencia"] == 1

    # Semana atual completa ja conta; coringas restantes sao do mes atual.
    estado = jogo.calcular(_semana(1, date(2026, 11, 16), 5), hoje=date(2026, 11, 21))
    assert estado["sequencia"] == 1
    assert estado["coringas_restantes"] == 2

    # Sem historico.
    vazio = jogo.calcular([], hoje=date(2026, 11, 23))
    assert vazio["nivel"] == 1 and vazio["sequencia"] == 0 and vazio["exp_total"] == 0


def _assert_banco_e_bot():
    original_db_path = db_ops.DB_PATH
    original_data_dir = db_ops.DATA_DIR
    original_send = telegram_poller.send
    mensagens = []

    with tempfile.TemporaryDirectory(prefix="limulus-jogo-") as temp_dir:
        temp_path = Path(temp_dir)
        try:
            db_ops.DATA_DIR = temp_path
            db_ops.DB_PATH = temp_path / "limulus.db"
            telegram_poller.send = lambda text, **kwargs: mensagens.append(text)
            db_ops.init_db()

            ids = []
            for indice, dia in enumerate(("2026-11-09", "2026-11-16")):
                sid = db_ops.create_session(dia, "A")
                log_id = db_ops.log_exercise(sid, "Supino reto (barra)", 3, 12, 0)
                db_ops.update_log_weight(log_id, 50 + indice * 2, 8)
                ids.append(sid)
            # Sessao incompleta nao entra no calculo.
            aberta = db_ops.create_session("2026-11-19", "B")
            db_ops.log_exercise(aberta, "Remada curvada (barra)", 3, 12, 0)

            sessoes = jogo.carregar_sessoes_concluidas()
            assert [s["id"] for s in sessoes] == ids

            resultado = jogo.resultado_da_sessao(ids[-1], hoje=date(2026, 11, 19))
            assert resultado["detalhe"]["recordes"] == ["Supino reto (barra)"]
            assert resultado["depois"]["exp_total"] > resultado["antes"]["exp_total"]
            assert jogo.resultado_da_sessao(aberta) is None

            texto = jogo.formatar_vitoria(resultado)
            assert "VITÓRIA" in texto and "EXP <b>+80</b>" in texto
            assert "LEVEL UP" in texto  # 60 + 80 cruza 100 EXP
            assert "Lv <b>2</b>" in texto

            telegram_poller.send_victory(ids[-1])
            assert "VITÓRIA" in mensagens[-1]
            telegram_poller.handle_profile()
            assert "FICHA DO PERSONAGEM" in mensagens[-1]
        finally:
            db_ops.DB_PATH = original_db_path
            db_ops.DATA_DIR = original_data_dir
            telegram_poller.send = original_send
            gc.collect()


def main():
    _assert_regras_puras()
    _assert_exp_e_recordes()
    _assert_sequencia_e_coringas()
    _assert_banco_e_bot()
    print("jogo_test: ok")


if __name__ == "__main__":
    main()
