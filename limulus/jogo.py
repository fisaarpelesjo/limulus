"""Camada de jogo (estilo JRPG) calculada a partir do historico de treino.

Nada aqui grava no banco: EXP, nivel, titulo e sequencia sao derivados das
sessoes concluidas em `training_sessions`/`training_logs`. Mudar uma regra
recalcula todo o historico sem migracao.

Regras da fase 1:

- sessao concluida (todos os exercicios registrados): EXP de presenca;
- cada exercicio registrado: EXP de serie vezes a aderencia ao RPE
  (8 ou 9 vale cheio; 7 ou menos vale metade; 10 vale pouco, para nao premiar
  carga exagerada; sem RPE vale metade, para incentivar o registro);
- recorde de carga com RPE ate 9 (ou sem RPE, no historico antigo): bonus,
  no maximo um por exercicio por semana;
- semana cumprida (5 treinos concluidos de segunda a domingo): bonus e +1 na
  sequencia;
- semana incompleta consome um coringa (2 por mes, contado pela segunda-feira
  da semana) e mantem a sequencia sem somar; sem coringa, a sequencia zera.
"""

import sqlite3
from collections import defaultdict
from datetime import date, timedelta

from . import db_ops

EXP_PRESENCA = 50
EXP_SERIE = 10
EXP_RECORDE = 20
EXP_SEMANA = 100
TREINOS_POR_SEMANA = 5
CORINGAS_POR_MES = 2
NIVEL_MAXIMO = 99

TITULOS = (
    (1, "Aprendiz"),
    (5, "Escudeiro"),
    (10, "Soldado"),
    (15, "Cavaleiro"),
    (25, "Paladino"),
    (40, "Campeão"),
    (60, "Herói"),
    (80, "Lenda"),
)


def aderencia_rpe(rpe):
    if rpe is None:
        return 0.5
    if rpe >= 10:
        return 0.3
    if rpe >= 8:
        return 1.0
    return 0.5


def exp_para_nivel(nivel):
    """EXP total acumulado necessario para alcancar o nivel."""
    if nivel <= 1:
        return 0
    return round(100 * (nivel - 1) ** 1.8)


def nivel_por_exp(exp_total):
    nivel = 1
    while nivel < NIVEL_MAXIMO and exp_total >= exp_para_nivel(nivel + 1):
        nivel += 1
    return nivel


def titulo_do_nivel(nivel):
    titulo = TITULOS[0][1]
    for minimo, nome in TITULOS:
        if nivel >= minimo:
            titulo = nome
    return titulo


def _segunda_feira(dia):
    return dia - timedelta(days=dia.weekday())


def _parse_data(texto):
    try:
        return date.fromisoformat(str(texto)[:10])
    except ValueError:
        return None


def carregar_sessoes_concluidas(conn=None):
    """Sessoes com todos os logs preenchidos, em ordem cronologica de id."""
    proprio = conn is None
    if proprio:
        db_ops.init_db()
        conn = sqlite3.connect(db_ops.DB_PATH)
    try:
        rows = conn.execute(
            """
            SELECT s.id, s.date, l.id, l.exercise_name, l.weight, l.rpe
            FROM training_sessions s
            JOIN training_logs l ON l.session_id = s.id
            WHERE NOT EXISTS (
                SELECT 1 FROM training_logs p
                WHERE p.session_id = s.id AND p.weight IS NULL
            )
            ORDER BY s.id, l.sort_order, l.id
            """
        ).fetchall()
    finally:
        if proprio:
            conn.close()

    sessoes = {}
    for session_id, data_txt, log_id, nome, peso, rpe in rows:
        dia = _parse_data(data_txt)
        if dia is None:
            continue
        sessao = sessoes.setdefault(
            session_id, {"id": session_id, "data": dia, "logs": []}
        )
        sessao["logs"].append(
            {
                "id": log_id,
                "nome": nome,
                "peso": float(peso) if peso is not None else 0.0,
                "rpe": float(rpe) if rpe is not None else None,
            }
        )
    return list(sessoes.values())


def calcular(sessoes, hoje=None):
    """Calcula EXP, nivel, sequencia e o detalhe de cada sessao."""
    hoje = hoje or db_ops.agora_brasilia().date()
    semana_atual = _segunda_feira(hoje)

    melhor_carga = {}
    recordes_semana = set()
    por_sessao = {}
    treinos_por_semana = defaultdict(int)
    exp_total = 0

    for sessao in sessoes:
        semana = _segunda_feira(sessao["data"])
        detalhe = {
            "presenca": EXP_PRESENCA,
            "series": 0,
            "recordes": [],
            "semana_completa": False,
        }
        exp_series = 0.0
        for log in sessao["logs"]:
            exp_series += EXP_SERIE * aderencia_rpe(log["rpe"])
            anterior = melhor_carga.get(log["nome"])
            if log["peso"] > 0:
                if (
                    anterior is not None
                    and log["peso"] > anterior
                    and (log["rpe"] is None or log["rpe"] <= 9)
                    and (log["nome"], semana) not in recordes_semana
                ):
                    recordes_semana.add((log["nome"], semana))
                    detalhe["recordes"].append(log["nome"])
                melhor_carga[log["nome"]] = max(anterior or 0.0, log["peso"])
        detalhe["series"] = round(exp_series)

        treinos_por_semana[semana] += 1
        if treinos_por_semana[semana] == TREINOS_POR_SEMANA:
            detalhe["semana_completa"] = True

        detalhe["total"] = (
            detalhe["presenca"]
            + detalhe["series"]
            + EXP_RECORDE * len(detalhe["recordes"])
            + (EXP_SEMANA if detalhe["semana_completa"] else 0)
        )
        exp_total += detalhe["total"]
        por_sessao[sessao["id"]] = detalhe

    sequencia, coringas_usados = _sequencia(treinos_por_semana, semana_atual)
    nivel = nivel_por_exp(exp_total)
    base = exp_para_nivel(nivel)
    proximo = exp_para_nivel(nivel + 1) if nivel < NIVEL_MAXIMO else base
    mes_atual = (semana_atual.year, semana_atual.month)

    return {
        "exp_total": exp_total,
        "nivel": nivel,
        "titulo": titulo_do_nivel(nivel),
        "exp_no_nivel": exp_total - base,
        "exp_do_nivel": proximo - base,
        "sequencia": sequencia,
        "treinos_semana_atual": treinos_por_semana.get(semana_atual, 0),
        "coringas_restantes": max(
            0, CORINGAS_POR_MES - coringas_usados.get(mes_atual, 0)
        ),
        "treinos_concluidos": len(sessoes),
        "por_sessao": por_sessao,
    }


def _sequencia(treinos_por_semana, semana_atual):
    """Semanas seguidas cumpridas, com coringas cobrindo semanas incompletas."""
    coringas_usados = defaultdict(int)
    if not treinos_por_semana:
        return 0, coringas_usados

    sequencia = 0
    semana = min(treinos_por_semana)
    while semana < semana_atual:
        if treinos_por_semana.get(semana, 0) >= TREINOS_POR_SEMANA:
            sequencia += 1
        else:
            mes = (semana.year, semana.month)
            if coringas_usados[mes] < CORINGAS_POR_MES:
                coringas_usados[mes] += 1
            else:
                sequencia = 0
        semana += timedelta(days=7)

    if treinos_por_semana.get(semana_atual, 0) >= TREINOS_POR_SEMANA:
        sequencia += 1
    return sequencia, coringas_usados


def estado_atual(hoje=None):
    return calcular(carregar_sessoes_concluidas(), hoje=hoje)


def resultado_da_sessao(session_id, hoje=None):
    """Estado antes e depois da sessao, para a tela de vitoria."""
    sessoes = carregar_sessoes_concluidas()
    depois = calcular(sessoes, hoje=hoje)
    detalhe = depois["por_sessao"].get(session_id)
    if detalhe is None:
        return None
    antes = calcular([s for s in sessoes if s["id"] != session_id], hoje=hoje)
    return {"antes": antes, "depois": depois, "detalhe": detalhe}


def _barra(atual, total, largura=10):
    if total <= 0:
        return "▰" * largura
    cheios = min(largura, int(largura * atual / total))
    return "▰" * cheios + "▱" * (largura - cheios)


def _linhas_status(estado):
    pct = (
        int(100 * estado["exp_no_nivel"] / estado["exp_do_nivel"])
        if estado["exp_do_nivel"]
        else 100
    )
    falta = estado["exp_do_nivel"] - estado["exp_no_nivel"]
    return [
        f"<b>{estado['titulo']}</b> · Lv <b>{estado['nivel']}</b>",
        f"{_barra(estado['exp_no_nivel'], estado['exp_do_nivel'])} {pct}%"
        f" (faltam {falta} EXP)",
        f"Semana: <b>{estado['treinos_semana_atual']}/{TREINOS_POR_SEMANA}</b>"
        f" · Sequência: <b>{estado['sequencia']}</b> sem. 🔥"
        f" · Coringas: <b>{estado['coringas_restantes']}</b>",
    ]


def formatar_vitoria(resultado):
    detalhe = resultado["detalhe"]
    antes = resultado["antes"]
    depois = resultado["depois"]

    partes = [f"presença {detalhe['presenca']}", f"séries {detalhe['series']}"]
    if detalhe["recordes"]:
        partes.append(f"recordes {EXP_RECORDE * len(detalhe['recordes'])}")
    if detalhe["semana_completa"]:
        partes.append(f"semana {EXP_SEMANA}")

    linhas = [
        "⚔ <b>VITÓRIA!</b>",
        f"EXP <b>+{detalhe['total']}</b> ({' · '.join(partes)})",
    ]
    if detalhe["semana_completa"]:
        linhas.append("🏁 <b>Semana completa!</b>")
    if depois["nivel"] > antes["nivel"]:
        linhas.append(
            f"✨ <b>LEVEL UP!</b> Lv {antes['nivel']} → Lv {depois['nivel']}"
        )
        if depois["titulo"] != antes["titulo"]:
            linhas.append(f"🎖 Novo título: <b>{depois['titulo']}</b>")
    linhas.append("")
    linhas.extend(_linhas_status(depois))
    return "\n".join(linhas)


def formatar_perfil(estado):
    linhas = ["<b>FICHA DO PERSONAGEM</b>", ""]
    linhas.extend(_linhas_status(estado))
    linhas.extend(
        [
            "",
            f"EXP total: <b>{estado['exp_total']}</b>",
            f"Treinos concluídos: <b>{estado['treinos_concluidos']}</b>",
            "",
            "<i>Semana cumprida = 5 treinos. Semana incompleta gasta um "
            "coringa (2 por mês) sem zerar a sequência.</i>",
        ]
    )
    return "\n".join(linhas)
