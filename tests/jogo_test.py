import gc
import json
import sys
import tempfile
from datetime import date, datetime, timedelta
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

    assert jogo.e1rm(60, 5) == 70.0
    assert jogo.e1rm(60, 0) == 60.0
    assert jogo.e1rm(0, 10) == 0.0
    assert jogo.rank_por_razao(0.2, (0.5, 1.0)) == 0
    assert jogo.rank_por_razao(0.5, (0.5, 1.0)) == 1
    assert jogo.rank_por_razao(1.2, (0.5, 1.0)) == 2

    # Inimigos: 24 unicos, 3 por familia, sorteio estavel no dia e variado entre dias.
    assert len(jogo.BASES_INIMIGOS) == 48 == len(set(jogo.BASES_INIMIGOS))
    assert len(jogo.TODOS_OS_INIMIGOS) == 192 == len(set(jogo.TODOS_OS_INIMIGOS))
    assert all(len(f) == 6 for f in jogo.FAMILIAS_INIMIGOS.values())
    assert jogo.separar_tier("Golem de Ferro · Elite") == ("Golem de Ferro", 1)
    assert jogo.separar_tier("Golem de Ferro") == ("Golem de Ferro", 0)
    assert jogo.nome_com_tier("Basilisco", 3) == "Basilisco · Lendário"
    assert [jogo.tier_maximo(n) for n in (1, 9, 10, 24, 25, 44, 45, 99)] == [0, 0, 1, 1, 2, 2, 3, 3]
    peito = [{"muscle_group": "Peitoral", "role": "principal"}]
    dia = date(2026, 11, 23)
    primeiro = jogo.inimigo_do_exercicio(peito, "Supino reto (barra)", dia)
    assert jogo.separar_tier(primeiro)[0] in jogo.FAMILIAS_INIMIGOS["peito"]
    # Nivel baixo: no maximo Elite (a versao rara); nivel 60 libera tudo.
    tiers_baixos = {
        jogo.separar_tier(jogo.inimigo_do_exercicio(peito, f"ex{i}", dia, 1))[1] for i in range(300)
    }
    assert tiers_baixos == {0, 1}
    tiers_altos = {
        jogo.separar_tier(jogo.inimigo_do_exercicio(peito, f"ex{i}", dia, 60))[1] for i in range(300)
    }
    assert tiers_altos == {0, 1, 2, 3}
    assert jogo.inimigo_do_exercicio(peito, "Supino reto (barra)", dia) == primeiro
    variados = {
        jogo.inimigo_do_exercicio(peito, "Supino reto (barra)", dia + timedelta(days=i))
        for i in range(30)
    }
    assert len({jogo.separar_tier(n)[0] for n in variados}) >= 3
    assert jogo.familia_do_exercicio([("Biceps", "principal")]) == "bracos"
    assert jogo.familia_do_exercicio([("Core", "secundario"), ("Triceps", "principal")]) == "triceps"
    assert jogo.familia_do_exercicio([]) == "outros"

    semana = date(2026, 11, 23)
    missoes = jogo.missoes_da_semana(semana)
    assert len(missoes) == jogo.MISSOES_POR_SEMANA
    assert len({m["id"] for m in missoes}) == jogo.MISSOES_POR_SEMANA
    assert missoes != jogo.missoes_da_semana(semana + timedelta(weeks=1))


def _log(sid, i, nome, peso, rpe, reps=12, sets=3):
    return {"id": sid * 100 + i, "nome": nome, "peso": peso, "rpe": rpe, "sets": sets, "reps": reps}


def _sessao(sid, dia, logs, tipo="A", inicio=None):
    return {
        "id": sid,
        "data": dia,
        "tipo": tipo,
        "inicio": inicio,
        "logs": [_log(sid, i, *log) for i, log in enumerate(logs)],
    }


def _sem_missoes(detalhe):
    return detalhe["total"] - jogo.EXP_MISSAO * len(detalhe["missoes"])


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
    assert (s1["presenca"], s1["series"], s1["recordes"]) == (50, 20, [])
    assert _sem_missoes(s1) == 70
    assert s2["series"] == 13  # 10 + 3
    assert s2["recordes"] == ["Supino"]
    assert _sem_missoes(s2) == 50 + 13 + 20
    assert s3["recordes"] == []
    assert _sem_missoes(s3) == 60
    assert estado["exp_total"] == sum(d["total"] for d in estado["por_sessao"].values())
    assert s2["ouro"] >= jogo.OURO_PRESENCA + jogo.OURO_RECORDE
    assert estado["treinos_semana_atual"] == 3
    assert estado["sequencia"] == 0
    assert estado["recordes_total"] == 1
    # Mapa da semana: segunda a quarta feitas, quarta e hoje.
    estados = [d["estado"] for d in estado["semana"]]
    assert estados[:3] == ["feito", "feito", "feito"]
    assert estados[3:5] == ["pendente", "pendente"]
    assert estados[5:] == ["descanso", "descanso"]


def _semana(sid_inicial, segunda, treinos):
    return [
        _sessao(sid_inicial + i, segunda + timedelta(days=i), [("Supino", 50, 8)])
        for i in range(treinos)
    ]


def _historico(inicio, por_semana):
    sessoes = []
    sid = 1
    for indice, treinos in enumerate(por_semana):
        semana = _semana(sid, inicio + timedelta(weeks=indice), treinos)
        sessoes.extend(semana)
        sid += len(semana)
    return sessoes


def _assert_sequencia_e_coringas():
    inicio = date(2026, 9, 7)  # segunda-feira
    # 5/5, 3/5 (coringa 1 de setembro), 5/5, 2/5 (coringa 2), 5/5.
    sessoes = _historico(inicio, (5, 3, 5, 2, 5))
    estado = jogo.calcular(sessoes, hoje=inicio + timedelta(weeks=5))
    assert estado["sequencia"] == 3
    assert estado["melhor_sequencia"] == 3
    assert estado["treinos_semana_atual"] == 0
    quinto = estado["por_sessao"][5]
    assert quinto["semana_completa"] is True
    assert _sem_missoes(quinto) == 50 + 10 + jogo.EXP_SEMANA
    assert estado["por_sessao"][4]["semana_completa"] is False
    assert "Semana cheia" in quinto["conquistas"]

    # Terceira semana incompleta no mesmo mes zera a sequencia.
    sessoes_mes = _historico(inicio, (5, 4, 4, 4, 5))
    estado = jogo.calcular(sessoes_mes, hoje=date(2026, 10, 12))
    assert estado["sequencia"] == 1
    assert estado["melhor_sequencia"] == 1

    # Um coringa comprado antes cobre a terceira falha do mes.
    extras = {"compras": [{"item": "coringa", "ouro": 150, "data": date(2026, 9, 1)}]}
    estado = jogo.calcular(sessoes_mes, hoje=date(2026, 10, 12), extras=extras)
    assert estado["sequencia"] == 2
    assert estado["coringas_extras"] == 0
    assert estado["ouro"] == estado["ouro_ganho"] - 150

    # Coringa comprado depois da falha nao vale para tras.
    extras = {"compras": [{"item": "coringa", "ouro": 150, "data": date(2026, 10, 10)}]}
    estado = jogo.calcular(sessoes_mes, hoje=date(2026, 10, 12), extras=extras)
    assert estado["sequencia"] == 1
    assert estado["coringas_extras"] == 1

    # Pausa declarada deixa a semana neutra (sem gastar coringa).
    extras = {"pausas": [{"inicio": date(2026, 9, 21), "fim": date(2026, 10, 4)}]}
    estado = jogo.calcular(sessoes_mes, hoje=date(2026, 10, 12), extras=extras)
    assert estado["sequencia"] == 2

    # Semana atual completa ja conta; coringas restantes sao do mes atual.
    estado = jogo.calcular(_semana(1, date(2026, 11, 16), 5), hoje=date(2026, 11, 21))
    assert estado["sequencia"] == 1
    assert estado["coringas_restantes"] == 2

    vazio = jogo.calcular([], hoje=date(2026, 11, 23))
    assert vazio["nivel"] == 1 and vazio["sequencia"] == 0 and vazio["exp_total"] == 0
    assert vazio["atributos"] == {"FOR": 1, "VIG": 1, "DIS": 1}
    assert all(c["data"] is None for c in vazio["conquistas"])
    assert vazio["semana"][0]["estado"] == "hoje"


def _assert_chefes_atributos_conquistas():
    segunda = date(2026, 11, 2)
    madrugada = datetime(2026, 11, 2, 6, 10)
    sessoes = [
        _sessao(
            i + 1,
            segunda + timedelta(days=i),
            [
                ("Supino reto (barra)", 60 + i, 9, 5),
                ("Levantamento Terra Romeno", 80, 8, 8),
                ("Remada curvada (barra)", 50, 8, 8),
            ],
            inicio=madrugada + timedelta(days=i),
        )
        for i in range(5)
    ]
    extras = {
        "pesos": [(date(2026, 10, 1), 100.0)],
        "grupos": {
            "Supino reto (barra)": [("Peitoral", "principal")],
            "Remada curvada (barra)": [("Dorsais", "principal"), ("Biceps", "secundario")],
        },
    }
    estado = jogo.calcular(sessoes, hoje=segunda + timedelta(days=4), extras=extras)
    chefes = {c["padrao"]: c for c in estado["chefes"]}
    supino = chefes["Empurrar"]
    # Melhor supino: 64 x5 -> 1RM 74,7 -> razao 0,747 -> Bronze, quase Prata.
    assert supino["rank"] == "Bronze" and supino["proximo_rank"] == "Prata"
    assert supino["alvo_e1rm"] == 75.0
    assert 0 < supino["hp_pct"] <= 100
    assert chefes["Agachar"]["rank"] == "Ferro" and chefes["Agachar"]["e1rm"] == 0
    assert chefes["Agachar"]["hp_pct"] == 100
    for nome in ("FOR", "VIG", "DIS"):
        assert 1 <= estado["atributos"][nome] <= 99
    assert {m["nome"] for m in estado["musculos"]} == {"Peitoral", "Dorsais", "Biceps"}
    conquistas = {c["id"]: c["data"] for c in estado["conquistas"]}
    assert conquistas["primeiro_treino"] == "2026-11-02"
    assert conquistas["madrugador_5"] == "2026-11-06"
    assert conquistas["chefe_1"] == "2026-11-02"
    assert conquistas["perfeita_1"] == "2026-11-02"
    assert conquistas["recorde_1"] == "2026-11-03"
    assert conquistas["coruja_5"] is None
    assert estado["classe"] in {nome for nomes in jogo.CLASSES.values() for nome in nomes}
    assert len(estado["diario"]) == 5 and "Treino A" in estado["diario"][-1]["texto"]

    # Exportacao compacta para o Mini App.
    pacote = jogo.exportar_para_app(estado)
    assert pacote["v"] == 1 and pacote["nivel"] == estado["nivel"]
    assert set(pacote["sem"]) <= set(jogo.CODIGOS_DIA.values())
    assert len(jogo.exportar_json_app(estado)) < 3000
    json.loads(jogo.exportar_json_app(estado))

    # Textos.
    assert "CHEFES" in jogo.formatar_chefes(estado)
    assert "CONQUISTAS" in jogo.formatar_conquistas(estado)
    assert "MISSÕES" in jogo.formatar_missoes(estado)
    assert "DIÁRIO" in jogo.formatar_diario(estado)
    assert "LOJA" in jogo.formatar_loja(estado)
    assert "Lv" in jogo.formatar_hud(estado)
    assert "FICHA" in jogo.formatar_perfil(estado)


def _assert_banco_e_bot():
    original_db_path = db_ops.DB_PATH
    original_data_dir = db_ops.DATA_DIR
    original_send = telegram_poller.send
    original_telegram_call = telegram_poller.telegram_call
    original_preco = jogo.LOJA["coringa"]["preco"]
    mensagens = []

    with tempfile.TemporaryDirectory(prefix="limulus-jogo-", ignore_cleanup_errors=True) as temp_dir:
        temp_path = Path(temp_dir)
        try:
            db_ops.DATA_DIR = temp_path
            db_ops.DB_PATH = temp_path / "limulus.db"
            telegram_poller.send = lambda text, **kwargs: mensagens.append(text) or True
            telegram_poller.telegram_call = lambda *args, **kwargs: (False, "teste sem rede")
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
            assert sessoes[0]["tipo"] == "A" and sessoes[0]["logs"][0]["reps"] == 12

            hoje = date(2026, 11, 19)
            resultado = jogo.resultado_da_sessao(ids[-1], hoje=hoje)
            assert resultado["detalhe"]["recordes"] == ["Supino reto (barra)"]
            assert resultado["depois"]["exp_total"] > resultado["antes"]["exp_total"]
            assert jogo.resultado_da_sessao(aberta) is None
            texto = jogo.formatar_vitoria(resultado)
            assert "VITÓRIA" in texto and f"EXP <b>+{resultado['detalhe']['total']}</b>" in texto
            assert ("LEVEL UP" in texto) == jogo.subiu_de_nivel(resultado)

            # Estado simples (HUD).
            assert jogo.ler_estado("hud") is None
            jogo.gravar_estado("hud", 123)
            jogo.gravar_estado("hud", 456)
            assert jogo.ler_estado("hud") == "456"

            # Loja: sem ouro suficiente, depois com preco baixo.
            ok, msg = jogo.comprar("coringa", hoje=hoje)
            assert not ok and "insuficiente" in msg
            assert not jogo.comprar("espada", hoje=hoje)[0]
            jogo.LOJA["coringa"]["preco"] = 10
            ouro_antes = jogo.estado_atual(hoje=hoje)["ouro"]
            ok, msg = jogo.comprar("coringa", hoje=hoje)
            assert ok, msg
            depois = jogo.estado_atual(hoje=hoje)
            assert depois["ouro"] == ouro_antes - 10
            assert depois["coringas_extras"] == 1

            # Pausa.
            fim = jogo.iniciar_pausa(7, "viagem", hoje=hoje)
            assert fim == hoje + timedelta(days=6)
            assert jogo.estado_atual(hoje=hoje)["em_pausa"] == fim.isoformat()
            assert jogo.encerrar_pausa(hoje=hoje + timedelta(days=2))
            assert jogo.estado_atual(hoje=hoje + timedelta(days=2))["em_pausa"] is None
            assert not jogo.encerrar_pausa(hoje=hoje + timedelta(days=2))
        finally:
            jogo.LOJA["coringa"]["preco"] = original_preco
            db_ops.DB_PATH = original_db_path
            db_ops.DATA_DIR = original_data_dir
            telegram_poller.send = original_send
            telegram_poller.telegram_call = original_telegram_call
            gc.collect()


class _ApiFalsa:
    """Imita a API do Telegram: registra chamadas e devolve ids de mensagem."""

    def __init__(self, recusar_efeito=False):
        self.chamadas = []
        self.proximo_id = 100
        self.recusar_efeito = recusar_efeito

    def __call__(self, method, payload, files=None):
        self.chamadas.append((method, payload, files))
        if self.recusar_efeito and "message_effect_id" in payload:
            return False, "Bad Request: EFFECT_ID_INVALID"
        if method in {"sendMessage", "sendPhoto", "sendVoice"}:
            self.proximo_id += 1
            return True, {"message_id": self.proximo_id}
        if method == "editMessageText" and payload.get("message_id") == 999:
            return False, "Bad Request: message to edit not found"
        return True, True

    def metodos(self):
        return [c[0] for c in self.chamadas]


class _VisualFalso:
    def __getattr__(self, nome):
        return lambda *args: b"\x89PNG falso " + nome.encode()


def _assert_fluxo_telegram():
    original_db_path = db_ops.DB_PATH
    original_data_dir = db_ops.DATA_DIR
    original_send = telegram_poller.send
    original_call = telegram_poller.telegram_call
    original_action = telegram_poller.telegram_action
    original_visual = telegram_poller._visual
    original_pausa = telegram_poller.PAUSA_ANIMACAO
    mensagens = []

    with tempfile.TemporaryDirectory(prefix="limulus-fluxo-", ignore_cleanup_errors=True) as temp_dir:
        temp_path = Path(temp_dir)
        try:
            db_ops.DATA_DIR = temp_path
            db_ops.DB_PATH = temp_path / "limulus.db"
            telegram_poller.send = lambda text, **kwargs: mensagens.append((text, kwargs)) or True
            telegram_poller.telegram_action = lambda method, payload: True
            telegram_poller._visual = lambda: _VisualFalso()
            telegram_poller.PAUSA_ANIMACAO = 0
            db_ops.init_db()

            # Primeiro treino: sobe do Lv 1 para o 2 e ganha confete.
            sid = db_ops.create_session("2026-11-23", "A")
            for ordem in range(3):
                log_id = db_ops.log_exercise(sid, f"Exercicio {ordem}", 3, 12, ordem)
                db_ops.update_log_weight(log_id, 20, 8)

            api = _ApiFalsa(recusar_efeito=True)
            telegram_poller.telegram_call = api
            telegram_poller.send_victory(sid)
            metodos = api.metodos()
            # Efeito recusado -> reenvia sem efeito; depois edita os quadros.
            assert metodos[0] == "sendMessage" and "message_effect_id" in api.chamadas[0][1]
            assert metodos[1] == "sendMessage" and "message_effect_id" not in api.chamadas[1][1]
            assert metodos.count("editMessageText") >= 3
            ultimo_quadro = [c for c in api.chamadas if c[0] == "editMessageText"][-1][1]["text"]
            assert "VITÓRIA" in ultimo_quadro and "LEVEL UP" in ultimo_quadro
            assert "sendPhoto" in metodos and "sendVoice" in metodos and "sendAnimation" in metodos
            assert "pinChatMessage" in metodos
            hud_id = jogo.ler_estado("hud_mensagem")
            assert hud_id is not None

            # HUD existente e editado, sem fixar de novo.
            api = _ApiFalsa()
            telegram_poller.telegram_call = api
            assert telegram_poller.atualizar_hud()
            assert api.metodos() == ["editMessageText"]
            assert api.chamadas[0][1]["message_id"] == int(hud_id)

            # HUD apagado no chat: cria e fixa outro.
            jogo.gravar_estado("hud_mensagem", 999)
            assert telegram_poller.atualizar_hud()
            assert "pinChatMessage" in api.metodos()

            # Sem rede: tela de vitoria cai no texto simples.
            telegram_poller.telegram_call = lambda *a, **k: (False, "sem rede")
            mensagens.clear()
            telegram_poller.send_victory(sid)
            assert "VITÓRIA" in mensagens[-1][0]

            # Comandos e menu.
            api = _ApiFalsa()
            telegram_poller.telegram_call = api
            mensagens.clear()
            telegram_poller.handle_profile()
            assert "FICHA" in mensagens[-1][0] and mensagens[-1][1]["reply_markup"] == telegram_poller.MENU_JOGO
            assert "sendPhoto" in api.metodos()
            telegram_poller.handle_bosses()
            assert "CHEFES" in mensagens[-1][0]
            telegram_poller.handle_week()
            assert "MAPA DA SEMANA" in mensagens[-1][0]
            telegram_poller.handle_menu_callback({"id": "1"}, "conquistas")
            assert "CONQUISTAS" in mensagens[-1][0]
            telegram_poller.handle_menu_callback({"id": "1"}, "inexistente")
            telegram_poller.handle_app()
            botao = mensagens[-1][1]["reply_markup"]["inline_keyboard"][0][0]
            url = botao["web_app"]["url"]
            assert url.startswith(telegram_poller.APP_URL + "#d=")
            dados = url.split("#d=", 1)[1]
            pacote = json.loads(
                __import__("base64").urlsafe_b64decode(dados + "=" * (-len(dados) % 4)).decode("utf-8")
            )
            assert pacote["treinos"] == 1

            telegram_poller.handle_bestiary()
            assert "BESTIÁRIO" in mensagens[-1][0] and "/192" in mensagens[-1][0]
            telegram_poller.handle_menu_callback({"id": "1"}, "bestiario")
            assert "BESTIÁRIO" in mensagens[-1][0]

            telegram_poller.handle_shop("/loja")
            assert "LOJA" in mensagens[-1][0]
            telegram_poller.handle_shop("/loja coringa")
            assert "insuficiente" in mensagens[-1][0]
            telegram_poller.handle_pause("/pausa")
            assert "/pausa 7" in mensagens[-1][0]
            telegram_poller.handle_pause("/pausa abc")
            assert "Use" in mensagens[-1][0]
            telegram_poller.handle_pause("/pausa 5")
            assert "descansa na estalagem" in mensagens[-1][0]
            telegram_poller.handle_pause("/pausa fim")
            assert "deixou a estalagem" in mensagens[-1][0]
            telegram_poller.handle_pause("/pausa fim")
            assert "nenhuma pausa ativa" in mensagens[-1][0]

            # Valor que nao e numero nao vaza erro do Python em ingles.
            telegram_poller.handle_weight("/peso abc")
            assert "Não entendi o peso" in mensagens[-1][0] and "could not" not in mensagens[-1][0]
            telegram_poller.handle_waist("/cintura xyz")
            assert "Não entendi a medida" in mensagens[-1][0]
            telegram_poller.handle_weight("/peso 10")
            assert "entre 30 e 400 kg" in mensagens[-1][0]

            # Quest enviada como tela de batalha com o card na legenda.
            api = _ApiFalsa()
            telegram_poller.telegram_call = api
            quest_sid = db_ops.create_session("2026-11-24", "A")
            quest_log = db_ops.log_exercise(quest_sid, "Supino reto (barra)", 3, 12, 0)
            ex = {"log_id": quest_log, "name": "Supino reto (barra)", "sets": 3, "reps": 12,
                  "target_weight": 35, "rest_interval": "2 min"}
            telegram_poller.send_current_exercise(ex, [ex])
            metodo, payload, arquivos = api.chamadas[-1]
            assert metodo == "sendPhoto" and arquivos is not None
            assert "QUEST 1/1" in payload["caption"]
            assert any(nome in payload["caption"] for nome in jogo.FAMILIAS_INIMIGOS["peito"])
            linhas = payload["reply_markup"]["inline_keyboard"]
            assert [len(linha) for linha in linhas] == [2, 2]
            assert linhas[0][1]["text"].startswith("⚔ Certeiro")
            assert "Quest completa" in telegram_poller._format_quest_result(ex, 35, 8)
            assert "Golpe crítico" in telegram_poller._format_quest_result(ex, 35, 9)
            assert jogo.nome_do_golpe(6) == "Golpe leve" and jogo.nome_do_golpe(11) == "Golpe no limite"

            # Sem modulo de imagens, os comandos seguem em texto.
            telegram_poller._visual = lambda: None
            telegram_poller.handle_profile()
            assert "FICHA" in mensagens[-1][0]
        finally:
            db_ops.DB_PATH = original_db_path
            db_ops.DATA_DIR = original_data_dir
            telegram_poller.send = original_send
            telegram_poller.telegram_call = original_call
            telegram_poller.telegram_action = original_action
            telegram_poller._visual = original_visual
            telegram_poller.PAUSA_ANIMACAO = original_pausa
            gc.collect()


def main():
    _assert_regras_puras()
    _assert_exp_e_recordes()
    _assert_sequencia_e_coringas()
    _assert_chefes_atributos_conquistas()
    _assert_banco_e_bot()
    _assert_fluxo_telegram()
    print("jogo_test: ok")


if __name__ == "__main__":
    main()
