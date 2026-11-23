"""Camada de jogo (estilo JRPG) calculada a partir do historico de treino.

EXP, nivel, titulo, classe, atributos, chefes, conquistas, missoes, ouro,
sequencia e diario sao derivados das sessoes concluidas em
`training_sessions`/`training_logs`. Mudar uma regra recalcula o historico
inteiro sem migracao. So o que nao da para derivar fica nas tabelas do schema
16: compras na loja (`jogo_compras`), pausas declaradas (`jogo_pausas`) e
chaves simples (`jogo_estado`, por exemplo a mensagem fixada do HUD).

Regras principais:

- sessao concluida (todos os exercicios registrados): EXP de presenca e ouro;
- cada exercicio registrado: EXP de serie vezes a aderencia ao RPE
  (8 ou 9 vale cheio; 7 ou menos vale metade; 10 vale pouco, para nao premiar
  carga exagerada; sem RPE vale metade, para incentivar o registro);
- recorde de carga com RPE ate 9 (ou sem RPE, no historico antigo): bonus,
  no maximo um por exercicio por semana;
- semana cumprida (5 treinos concluidos de segunda a domingo): bonus e +1 na
  sequencia; semana incompleta consome um coringa (2 por mes, contado pela
  segunda-feira da semana, depois os coringas comprados na loja) e mantem a
  sequencia sem somar; sem coringa, a sequencia zera; semana com pausa
  declarada e neutra;
- missoes semanais premiam qualidade (RPE registrado, sessao no RPE certo,
  constancia), nunca "fazer mais".
"""

import json
import math
import sqlite3
from collections import defaultdict
from datetime import date, datetime, timedelta

from . import db_ops

EXP_PRESENCA = 50
EXP_SERIE = 10
EXP_RECORDE = 20
EXP_SEMANA = 100
EXP_MISSAO = 50
OURO_PRESENCA = 10
OURO_RECORDE = 5
OURO_SEMANA = 25
OURO_MISSAO = 20
TREINOS_POR_SEMANA = 5
CORINGAS_POR_MES = 2
NIVEL_MAXIMO = 99
PAUSA_MAXIMA_DIAS = 90

LOJA = {
    "coringa": {
        "nome": "Coringa extra",
        "preco": 150,
        "descricao": "Protege a sequencia numa semana incompleta, depois dos 2 do mes.",
    },
}

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

# Classe pelo atributo dominante; o nome evolui com o nivel (<10, <30, 30+).
CLASSES = {
    "FOR": ("Guerreiro", "Gladiador", "Senhor da Guerra"),
    "VIG": ("Bárbaro", "Berserker", "Titã"),
    "DIS": ("Monge", "Mestre", "Grão-Mestre"),
}

RANKS = ("Ferro", "Bronze", "Prata", "Ouro", "Platina", "Diamante")

# Chefes por padrao de movimento. Os limites sao a razao 1RM estimado / peso
# corporal para subir de Ferro a Bronze, Prata, Ouro, Platina e Diamante.
# Sao aproximacoes de padroes publicos de forca (strengthlevel.com,
# Symmetric Strength) para homens, ajustadas ao exercicio usado aqui; servem
# para o jogo, nao como avaliacao.
PADROES = {
    "Empurrar": {
        "chefe": "Golem de Ferro",
        "exercicios": ("Supino reto (barra)",),
        "limites": (0.50, 0.75, 1.00, 1.50, 2.00),
    },
    "Agachar": {
        "chefe": "Ogro da Montanha",
        "exercicios": (
            "Agachamento Zercher",
            "Agachamento com barra nas costas",
            "Agachamento (barra)",
            "Zercher squat",
        ),
        "limites": (0.75, 1.25, 1.50, 2.25, 2.75),
    },
    "Quadril": {
        "chefe": "Serpente do Abismo",
        "exercicios": ("Levantamento Terra Romeno",),
        "limites": (0.75, 1.00, 1.50, 2.00, 2.50),
    },
    "Puxar": {
        "chefe": "Grifo Sombrio",
        "exercicios": ("Remada curvada (barra)",),
        "limites": (0.50, 0.75, 1.00, 1.50, 1.75),
    },
    "Ombro": {
        "chefe": "Titã do Céu",
        "exercicios": ("Desenvolvimento (barra em pé)", "Desenvolvimento (barra em pe)"),
        "limites": (0.35, 0.55, 0.80, 1.05, 1.35),
    },
}

MISSOES = (
    {"id": "rpe_registrado", "nome": "Registrar o RPE em 15 exercícios", "meta": 15},
    {"id": "sessao_perfeita", "nome": "Uma sessão inteira no RPE 8–9", "meta": 1},
    {"id": "recorde", "nome": "Quebrar 1 recorde com RPE até 9", "meta": 1},
    {"id": "tres_seguidos", "nome": "Treinar 3 dias seguidos", "meta": 3},
    {"id": "controle", "nome": "3 sessões sem nenhum RPE 10", "meta": 3},
    {"id": "constancia", "nome": "Concluir 3 treinos na semana", "meta": 3},
    {"id": "semana_completa", "nome": "Fechar a semana (5 treinos)", "meta": 5},
)
MISSOES_POR_SEMANA = 3

CONQUISTAS = (
    ("primeiro_treino", "Primeiro passo", "Concluir o primeiro treino"),
    ("treinos_10", "Aventureiro", "Concluir 10 treinos"),
    ("treinos_50", "Veterano", "Concluir 50 treinos"),
    ("treinos_100", "Centurião", "Concluir 100 treinos"),
    ("treinos_250", "Imortal", "Concluir 250 treinos"),
    ("semana_1", "Semana cheia", "Fechar uma semana com 5 treinos"),
    ("sequencia_4", "Ritmo de batalha", "Sequência de 4 semanas"),
    ("sequencia_12", "Estação de ferro", "Sequência de 12 semanas"),
    ("recorde_1", "Primeiro recorde", "Quebrar um recorde de carga"),
    ("recordes_10", "Quebra-limites", "Quebrar 10 recordes"),
    ("recordes_50", "Lenda viva", "Quebrar 50 recordes"),
    ("nivel_10", "Nível 10", "Chegar ao nível 10"),
    ("nivel_20", "Nível 20", "Chegar ao nível 20"),
    ("nivel_30", "Nível 30", "Chegar ao nível 30"),
    ("nivel_50", "Nível 50", "Chegar ao nível 50"),
    ("chefe_1", "Caçador", "Derrotar o primeiro chefe (rank Bronze)"),
    ("chefes_5", "Matador de chefes", "Somar 5 ranks entre os chefes"),
    ("perfeita_1", "Golpe preciso", "Uma sessão inteira no RPE 8–9"),
    ("perfeitas_10", "Mestre do RPE", "10 sessões inteiras no RPE 8–9"),
    ("madrugador_5", "Madrugador", "5 treinos começados antes das 7h"),
    ("coruja_5", "Coruja", "5 treinos começados depois das 21h"),
    ("missoes_10", "Caçador de missões", "Cumprir 10 missões semanais"),
)

DIAS_SEMANA = ("Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom")
DIAS_SEMANA_LONGOS = (
    "Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo",
)

# Cada exercicio do treino e uma quest contra um inimigo, escolhido pelo
# primeiro grupo muscular principal do exercicio.
INIMIGOS_POR_GRUPO = {
    "Peitoral": "Golem de Ferro",
    "Quadriceps": "Ogro da Montanha",
    "Adutores": "Ogro da Montanha",
    "Posteriores": "Serpente do Abismo",
    "Gluteos": "Serpente do Abismo",
    "Dorsais": "Grifo Sombrio",
    "Trapezio": "Grifo Sombrio",
    "Deltoide anterior": "Titã do Céu",
    "Deltoide lateral": "Titã do Céu",
    "Deltoide posterior": "Titã do Céu",
    "Triceps": "Diabrete Rúnico",
    "Biceps": "Morcego de Ferro",
    "Antebraco": "Morcego de Ferro",
}
INIMIGO_PADRAO = "Cogumelo Bravo"

# Botoes de RPE como golpes: (rotulo, valor gravado, nome do golpe).
GOLPES_RPE = (
    ("🛡 Leve · RPE ≤7", 7, "Golpe leve"),
    ("⚔ Certeiro · RPE 8", 8, "Golpe certeiro"),
    ("🔥 Crítico · RPE 9", 9, "Golpe crítico"),
    ("💀 No limite · RPE 10", 10, "Golpe no limite"),
)


def inimigo_do_exercicio(grupos):
    """Recebe a lista de grupos do exercicio [{muscle_group, role}] e devolve o inimigo."""
    principais = [g["muscle_group"] for g in grupos if g.get("role") == "principal"]
    for grupo in principais + [g["muscle_group"] for g in grupos]:
        if grupo in INIMIGOS_POR_GRUPO:
            return INIMIGOS_POR_GRUPO[grupo]
    return INIMIGO_PADRAO


def nome_do_golpe(rpe):
    rpe = int(rpe)
    if rpe <= 7:
        return GOLPES_RPE[0][2]
    if rpe == 8:
        return GOLPES_RPE[1][2]
    if rpe == 9:
        return GOLPES_RPE[2][2]
    return GOLPES_RPE[3][2]

ABERTURAS = (
    "o herói encarou",
    "a jornada seguiu com",
    "mais uma batalha:",
    "o guerreiro voltou para",
    "a espada cantou no",
)


# --------------------------------------------------------------------------
# Regras puras
# --------------------------------------------------------------------------


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


def e1rm(peso, reps):
    """1RM estimado pela formula de Epley, igual ao resto do projeto."""
    if not peso or peso <= 0:
        return 0.0
    if not reps or reps <= 1:
        return float(peso)
    return float(peso) * (1 + reps / 30)


def rank_por_razao(razao, limites):
    return sum(1 for limite in limites if razao >= limite)


def missoes_da_semana(segunda):
    """Tres missoes por semana, em rodizio fixo pela data."""
    inicio = (segunda.toordinal() // 7) % len(MISSOES)
    return [MISSOES[(inicio + i) % len(MISSOES)] for i in range(MISSOES_POR_SEMANA)]


def _segunda_feira(dia):
    return dia - timedelta(days=dia.weekday())


def _parse_data(texto):
    try:
        return date.fromisoformat(str(texto)[:10])
    except ValueError:
        return None


def _parse_datahora(texto):
    if not texto:
        return None
    try:
        return datetime.fromisoformat(str(texto))
    except ValueError:
        return None


# --------------------------------------------------------------------------
# Carga do banco
# --------------------------------------------------------------------------


def _abrir(conn):
    if conn is not None:
        return conn, False
    db_ops.init_db()
    return sqlite3.connect(db_ops.DB_PATH), True


def carregar_sessoes_concluidas(conn=None):
    """Sessoes com todos os logs preenchidos, em ordem cronologica de id."""
    conn, proprio = _abrir(conn)
    try:
        rows = conn.execute(
            """
            SELECT s.id, s.date, s.training_type, s.started_at,
                   l.id, l.exercise_name, l.weight, l.rpe, l.sets, l.reps
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
    for sid, data_txt, tipo, inicio, log_id, nome, peso, rpe, sets, reps in rows:
        dia = _parse_data(data_txt)
        if dia is None:
            continue
        sessao = sessoes.setdefault(
            sid,
            {
                "id": sid,
                "data": dia,
                "tipo": tipo,
                "inicio": _parse_datahora(inicio),
                "logs": [],
            },
        )
        sessao["logs"].append(
            {
                "id": log_id,
                "nome": nome,
                "peso": float(peso) if peso is not None else 0.0,
                "rpe": float(rpe) if rpe is not None else None,
                "sets": int(sets or 0),
                "reps": int(reps or 0),
            }
        )
    return list(sessoes.values())


def carregar_extras(conn=None):
    """Peso corporal, grupos musculares, compras e pausas usados no calculo."""
    conn, proprio = _abrir(conn)
    try:
        pesos = [
            (_parse_data(recorded_at), float(kg))
            for kg, recorded_at in conn.execute(
                "SELECT weight_kg, recorded_at FROM body_weights ORDER BY recorded_at, id"
            )
        ]
        grupos = defaultdict(list)
        for exercicio, grupo, papel in conn.execute(
            "SELECT exercise_name, muscle_group, role FROM exercise_muscle_groups"
        ):
            grupos[exercicio].append((grupo, papel))
        compras = [
            {"item": item, "ouro": int(ouro), "data": _parse_data(criado_em)}
            for item, ouro, criado_em in conn.execute(
                "SELECT item, ouro, criado_em FROM jogo_compras ORDER BY id"
            )
        ]
        pausas = [
            {"inicio": _parse_data(inicio), "fim": _parse_data(fim) if fim else None}
            for inicio, fim in conn.execute(
                "SELECT inicio, fim FROM jogo_pausas ORDER BY id"
            )
        ]
    finally:
        if proprio:
            conn.close()
    return {
        "pesos": [p for p in pesos if p[0] is not None],
        "grupos": dict(grupos),
        "compras": compras,
        "pausas": pausas,
    }


# --------------------------------------------------------------------------
# Calculo principal
# --------------------------------------------------------------------------


class _Sequencia:
    """Processa semanas fechadas em ordem: coringas, pausas e quebra."""

    def __init__(self, compras_coringa, pausas, hoje):
        self.compras = sorted(d for d in compras_coringa if d is not None)
        self.pausas = pausas
        self.hoje = hoje
        self.valor = 0
        self.melhor = 0
        self.coringas_mes = defaultdict(int)
        self.extras_usados = 0
        self.proxima = None
        self.contadas = set()

    def em_pausa(self, segunda):
        fim_semana = segunda + timedelta(days=6)
        for pausa in self.pausas:
            inicio = pausa["inicio"]
            fim = pausa["fim"] or self.hoje
            if inicio and inicio <= fim_semana and fim >= segunda:
                return True
        return False

    def extras_disponiveis(self, ate):
        return sum(1 for d in self.compras if d <= ate) - self.extras_usados

    def fechar_ate(self, semana_alvo, treinos):
        if self.proxima is None:
            self.proxima = semana_alvo
        while self.proxima < semana_alvo:
            semana = self.proxima
            if semana not in self.contadas and not self.em_pausa(semana):
                mes = (semana.year, semana.month)
                if self.coringas_mes[mes] < CORINGAS_POR_MES:
                    self.coringas_mes[mes] += 1
                elif self.extras_disponiveis(semana + timedelta(days=6)) > 0:
                    self.extras_usados += 1
                else:
                    self.valor = 0
            self.proxima += timedelta(days=7)

    def semana_cumprida(self, semana):
        if semana not in self.contadas:
            self.contadas.add(semana)
            self.valor += 1
            self.melhor = max(self.melhor, self.valor)


def _peso_corporal_em(pesos, dia):
    escolhido = None
    for data_peso, kg in pesos:
        if data_peso <= dia:
            escolhido = kg
    if escolhido is None and pesos:
        escolhido = pesos[0][1]
    return escolhido


def _chefes(melhores_e1rm, peso_corporal):
    chefes = []
    for padrao, info in PADROES.items():
        melhor = melhores_e1rm.get(padrao, 0.0)
        limites = info["limites"]
        razao = melhor / peso_corporal if peso_corporal and melhor else 0.0
        indice = rank_por_razao(razao, limites)
        if indice < len(limites):
            anterior = limites[indice - 1] if indice > 0 else 0.0
            proximo = limites[indice]
            hp = round(100 * (proximo - razao) / (proximo - anterior))
            alvo = round(proximo * peso_corporal, 1) if peso_corporal else None
            proximo_rank = RANKS[indice + 1]
        else:
            hp, alvo, proximo_rank = 0, None, None
        chefes.append(
            {
                "padrao": padrao,
                "nome": info["chefe"],
                "rank": RANKS[indice],
                "rank_indice": indice,
                "proximo_rank": proximo_rank,
                "hp_pct": max(0, min(100, hp)),
                "e1rm": round(melhor, 1),
                "alvo_e1rm": alvo,
                "razao": round(razao, 2),
                "derrotados": indice,
            }
        )
    return chefes


def _padrao_do_exercicio(nome):
    for padrao, info in PADROES.items():
        if nome in info["exercicios"]:
            return padrao
    return None


def _texto_diario(sessao, detalhe, nivel_novo):
    abertura = ABERTURAS[sessao["id"] % len(ABERTURAS)]
    tipo = sessao.get("tipo") or "TREINO"
    partes = [f"{sessao['data']:%d/%m} · {abertura} o Treino {tipo}"]
    if detalhe["recordes"]:
        partes.append(f"recorde em {detalhe['recordes'][0]}")
    if detalhe["semana_completa"]:
        partes.append("semana completa!")
    if nivel_novo:
        partes.append(f"subiu para o Lv {nivel_novo}")
    if detalhe["missoes"]:
        partes.append(f"missão cumprida: {detalhe['missoes'][0]}")
    if detalhe["conquistas"]:
        partes.append(f"conquista: {detalhe['conquistas'][0]}")
    return " · ".join(partes)


def calcular(sessoes, hoje=None, extras=None):
    """Calcula o estado completo do personagem e o detalhe de cada sessao."""
    hoje = hoje or db_ops.agora_brasilia().date()
    extras = extras or {}
    pesos = extras.get("pesos", [])
    grupos = extras.get("grupos", {})
    compras = extras.get("compras", [])
    pausas = extras.get("pausas", [])
    semana_atual = _segunda_feira(hoje)

    sequencia = _Sequencia(
        [c["data"] for c in compras if c["item"] == "coringa"], pausas, hoje
    )
    nomes_conquistas = {cid: nome for cid, nome, _ in CONQUISTAS}

    melhor_carga = {}
    melhores_e1rm = {}
    recordes_semana = set()
    treinos_por_semana = defaultdict(int)
    progresso_semana = defaultdict(lambda: defaultdict(int))
    dias_semana = defaultdict(set)
    missoes_feitas = set()
    conquistas = {}
    contadores = defaultdict(int)
    por_sessao = {}
    historico_nivel = []
    diario = []
    exp_total = 0
    ouro = 0

    for sessao in sessoes:
        semana = _segunda_feira(sessao["data"])
        sequencia.fechar_ate(semana, treinos_por_semana)
        nivel_antes = nivel_por_exp(exp_total)
        detalhe = {
            "presenca": EXP_PRESENCA,
            "series": 0,
            "recordes": [],
            "semana_completa": False,
            "missoes": [],
            "conquistas": [],
            "ouro": OURO_PRESENCA,
        }
        exp_series = 0.0
        rpes = []
        for log in sessao["logs"]:
            exp_series += EXP_SERIE * aderencia_rpe(log["rpe"])
            if log["rpe"] is not None:
                rpes.append(log["rpe"])
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
                padrao = _padrao_do_exercicio(log["nome"])
                if padrao:
                    estimado = e1rm(log["peso"], log.get("reps"))
                    melhores_e1rm[padrao] = max(melhores_e1rm.get(padrao, 0.0), estimado)
        detalhe["series"] = round(exp_series)
        detalhe["ouro"] += OURO_RECORDE * len(detalhe["recordes"])

        perfeita = bool(sessao["logs"]) and len(rpes) == len(sessao["logs"]) and all(
            8 <= r <= 9 for r in rpes
        )
        treinos_por_semana[semana] += 1
        if treinos_por_semana[semana] == TREINOS_POR_SEMANA:
            detalhe["semana_completa"] = True
            detalhe["ouro"] += OURO_SEMANA
            sequencia.semana_cumprida(semana)
            contadores["semanas"] += 1

        # Missoes da semana (todas monotonicas: uma vez cumpridas, ficam).
        progresso = progresso_semana[semana]
        progresso["rpe_registrado"] += len(rpes)
        progresso["sessao_perfeita"] += 1 if perfeita else 0
        progresso["recorde"] += len(detalhe["recordes"])
        progresso["controle"] += 0 if any(r >= 10 for r in rpes) else 1
        progresso["constancia"] += 1
        progresso["semana_completa"] = treinos_por_semana[semana]
        dias_semana[semana].add(sessao["data"])
        progresso["tres_seguidos"] = _maior_corrida(dias_semana[semana])
        exp_missoes = 0
        for missao in missoes_da_semana(semana):
            chave = (semana, missao["id"])
            if chave not in missoes_feitas and progresso[missao["id"]] >= missao["meta"]:
                missoes_feitas.add(chave)
                detalhe["missoes"].append(missao["nome"])
                exp_missoes += EXP_MISSAO
                detalhe["ouro"] += OURO_MISSAO

        detalhe["total"] = (
            detalhe["presenca"]
            + detalhe["series"]
            + EXP_RECORDE * len(detalhe["recordes"])
            + (EXP_SEMANA if detalhe["semana_completa"] else 0)
            + exp_missoes
        )
        exp_total += detalhe["total"]
        ouro += detalhe["ouro"]
        nivel_depois = nivel_por_exp(exp_total)

        contadores["treinos"] += 1
        contadores["recordes"] += len(detalhe["recordes"])
        contadores["perfeitas"] += 1 if perfeita else 0
        contadores["missoes"] += len(detalhe["missoes"])
        inicio = sessao.get("inicio")
        if inicio is not None:
            contadores["madrugador"] += 1 if inicio.hour < 7 else 0
            contadores["coruja"] += 1 if inicio.hour >= 21 else 0
        peso_corporal = _peso_corporal_em(pesos, sessao["data"])
        ranks = sum(c["rank_indice"] for c in _chefes(melhores_e1rm, peso_corporal))
        condicoes = {
            "primeiro_treino": contadores["treinos"] >= 1,
            "treinos_10": contadores["treinos"] >= 10,
            "treinos_50": contadores["treinos"] >= 50,
            "treinos_100": contadores["treinos"] >= 100,
            "treinos_250": contadores["treinos"] >= 250,
            "semana_1": contadores["semanas"] >= 1,
            "sequencia_4": sequencia.valor >= 4,
            "sequencia_12": sequencia.valor >= 12,
            "recorde_1": contadores["recordes"] >= 1,
            "recordes_10": contadores["recordes"] >= 10,
            "recordes_50": contadores["recordes"] >= 50,
            "nivel_10": nivel_depois >= 10,
            "nivel_20": nivel_depois >= 20,
            "nivel_30": nivel_depois >= 30,
            "nivel_50": nivel_depois >= 50,
            "chefe_1": ranks >= 1,
            "chefes_5": ranks >= 5,
            "perfeita_1": contadores["perfeitas"] >= 1,
            "perfeitas_10": contadores["perfeitas"] >= 10,
            "madrugador_5": contadores["madrugador"] >= 5,
            "coruja_5": contadores["coruja"] >= 5,
            "missoes_10": contadores["missoes"] >= 10,
        }
        for cid, atingida in condicoes.items():
            if atingida and cid not in conquistas:
                conquistas[cid] = sessao["data"]
                detalhe["conquistas"].append(nomes_conquistas[cid])

        por_sessao[sessao["id"]] = detalhe
        historico_nivel.append(
            {"data": sessao["data"].isoformat(), "nivel": nivel_depois, "exp": exp_total}
        )
        diario.append(
            {
                "data": sessao["data"].isoformat(),
                "texto": _texto_diario(
                    sessao, detalhe, nivel_depois if nivel_depois > nivel_antes else None
                ),
            }
        )

    if sessoes:
        sequencia.fechar_ate(semana_atual, treinos_por_semana)

    gasto = sum(c["ouro"] for c in compras)
    peso_atual = _peso_corporal_em(pesos, hoje)
    chefes = _chefes(melhores_e1rm, peso_atual)
    atributos, musculos = _atributos(sessoes, grupos, chefes, hoje)
    nivel = nivel_por_exp(exp_total)
    base = exp_para_nivel(nivel)
    proximo = exp_para_nivel(nivel + 1) if nivel < NIVEL_MAXIMO else base
    mes_atual = (semana_atual.year, semana_atual.month)
    em_pausa = _pausa_ativa(pausas, hoje)

    return {
        "exp_total": exp_total,
        "nivel": nivel,
        "titulo": titulo_do_nivel(nivel),
        "classe": _classe(atributos, nivel),
        "classe_base": max(atributos, key=lambda k: (atributos[k], k == "DIS")),
        "exp_no_nivel": exp_total - base,
        "exp_do_nivel": proximo - base,
        "atributos": atributos,
        "musculos": musculos,
        "ouro": max(0, ouro - gasto),
        "ouro_ganho": ouro,
        "sequencia": sequencia.valor,
        "melhor_sequencia": sequencia.melhor,
        "treinos_semana_atual": treinos_por_semana.get(semana_atual, 0),
        "coringas_restantes": max(
            0, CORINGAS_POR_MES - sequencia.coringas_mes.get(mes_atual, 0)
        ),
        "coringas_extras": max(0, sequencia.extras_disponiveis(date.max)),
        "em_pausa": em_pausa,
        "semana": _mapa_semana(sessoes, semana_atual, hoje, em_pausa),
        "chefes": chefes,
        "peso_corporal": peso_atual,
        "conquistas": [
            {
                "id": cid,
                "nome": nome,
                "descricao": descricao,
                "data": conquistas[cid].isoformat() if cid in conquistas else None,
            }
            for cid, nome, descricao in CONQUISTAS
        ],
        "missoes": [
            {
                "id": m["id"],
                "nome": m["nome"],
                "meta": m["meta"],
                "progresso": min(m["meta"], progresso_semana[semana_atual][m["id"]]),
                "feita": (semana_atual, m["id"]) in missoes_feitas,
            }
            for m in missoes_da_semana(semana_atual)
        ],
        "diario": diario[-30:],
        "historico_nivel": historico_nivel,
        "treinos_concluidos": len(sessoes),
        "recordes_total": contadores["recordes"],
        "por_sessao": por_sessao,
    }


def _maior_corrida(dias):
    ordenados = sorted(dias)
    maior = atual = 0
    anterior = None
    for dia in ordenados:
        atual = atual + 1 if anterior and (dia - anterior).days == 1 else 1
        maior = max(maior, atual)
        anterior = dia
    return maior


def _pausa_ativa(pausas, hoje):
    for pausa in pausas:
        fim = pausa["fim"]
        if pausa["inicio"] and pausa["inicio"] <= hoje and (fim is None or fim >= hoje):
            return (fim or hoje).isoformat() if fim else "aberta"
    return None


def _mapa_semana(sessoes, semana_atual, hoje, em_pausa):
    feitos = {s["data"] for s in sessoes if _segunda_feira(s["data"]) == semana_atual}
    mapa = []
    for indice, nome in enumerate(DIAS_SEMANA):
        dia = semana_atual + timedelta(days=indice)
        if dia in feitos:
            estado = "feito"
        elif em_pausa and dia >= hoje:
            estado = "pausa"
        elif dia == hoje:
            estado = "hoje"
        elif dia < hoje:
            estado = "perdido" if indice < 5 else "descanso"
        else:
            estado = "pendente" if indice < 5 else "descanso"
        mapa.append({"dia": nome, "data": dia.isoformat(), "estado": estado})
    return mapa


def _atributos(sessoes, grupos, chefes, hoje):
    # FOR: media da forca relativa nos padroes com historico, 1 a 99.
    pontos = []
    for chefe in chefes:
        if chefe["e1rm"] > 0:
            limite_max = PADROES[chefe["padrao"]]["limites"][-1]
            pontos.append(min(99, round(99 * chefe["razao"] / limite_max)))
    forca = max(1, round(sum(pontos) / len(pontos))) if pontos else 1

    # VIG: series efetivas por musculo (RPE 7 a 9, ou sem RPE no historico).
    series = defaultdict(float)
    for sessao in sessoes:
        for log in sessao["logs"]:
            if log["rpe"] is not None and not (7 <= log["rpe"] <= 9):
                continue
            for grupo, papel in grupos.get(log["nome"], []):
                series[grupo] += log.get("sets", 3) * (1.0 if papel == "principal" else 0.5)
    musculos = sorted(
        (
            {"nome": grupo, "nivel": min(99, 1 + int(math.sqrt(total)))}
            for grupo, total in series.items()
            if total > 0
        ),
        key=lambda m: (-m["nivel"], m["nome"]),
    )
    vigor = (
        max(1, round(sum(m["nivel"] for m in musculos) / len(musculos))) if musculos else 1
    )

    # DIS: presenca e RPE certo nas ultimas 8 semanas, incluindo a atual.
    inicio_janela = _segunda_feira(hoje) - timedelta(weeks=7)
    janela = [s for s in sessoes if inicio_janela <= s["data"] <= hoje]
    presenca = min(1.0, len(janela) / (TREINOS_POR_SEMANA * 8))
    rpes = [log["rpe"] for s in janela for log in s["logs"] if log["rpe"] is not None]
    acerto = sum(1 for r in rpes if 8 <= r <= 9) / len(rpes) if rpes else 0.0
    disciplina = max(1, round(99 * (0.6 * presenca + 0.4 * acerto)))

    return {"FOR": forca, "VIG": vigor, "DIS": disciplina}, musculos


def _classe(atributos, nivel):
    base = max(atributos, key=lambda k: (atributos[k], k == "DIS"))
    estagio = 0 if nivel < 10 else 1 if nivel < 30 else 2
    return CLASSES[base][estagio]


# --------------------------------------------------------------------------
# Acesso de alto nivel
# --------------------------------------------------------------------------


def estado_atual(hoje=None):
    db_ops.init_db()
    conn = sqlite3.connect(db_ops.DB_PATH)
    try:
        return calcular(carregar_sessoes_concluidas(conn), hoje=hoje, extras=carregar_extras(conn))
    finally:
        conn.close()


def resultado_da_sessao(session_id, hoje=None):
    """Estado antes e depois da sessao, para a tela de vitoria."""
    db_ops.init_db()
    conn = sqlite3.connect(db_ops.DB_PATH)
    try:
        sessoes = carregar_sessoes_concluidas(conn)
        extras = carregar_extras(conn)
    finally:
        conn.close()
    depois = calcular(sessoes, hoje=hoje, extras=extras)
    detalhe = depois["por_sessao"].get(session_id)
    if detalhe is None:
        return None
    antes = calcular([s for s in sessoes if s["id"] != session_id], hoje=hoje, extras=extras)
    return {"antes": antes, "depois": depois, "detalhe": detalhe}


def ler_estado(chave):
    db_ops.init_db()
    conn = sqlite3.connect(db_ops.DB_PATH)
    try:
        row = conn.execute("SELECT valor FROM jogo_estado WHERE chave = ?", (chave,)).fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def gravar_estado(chave, valor):
    db_ops.init_db()
    conn = sqlite3.connect(db_ops.DB_PATH)
    try:
        with conn:
            conn.execute(
                "INSERT INTO jogo_estado (chave, valor) VALUES (?, ?) "
                "ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor",
                (chave, None if valor is None else str(valor)),
            )
    finally:
        conn.close()


def comprar(item, hoje=None):
    """Compra um item da loja. Retorna (ok, mensagem)."""
    produto = LOJA.get(item)
    if produto is None:
        return False, "Item não existe na loja."
    estado = estado_atual(hoje=hoje)
    if estado["ouro"] < produto["preco"]:
        return False, (
            f"Ouro insuficiente: você tem {estado['ouro']} e o "
            f"{produto['nome'].lower()} custa {produto['preco']}."
        )
    agora = db_ops.agora_brasilia()
    if hoje is not None:
        agora = datetime.combine(hoje, agora.time())
    conn = sqlite3.connect(db_ops.DB_PATH)
    try:
        with conn:
            conn.execute(
                "INSERT INTO jogo_compras (item, ouro, criado_em) VALUES (?, ?, ?)",
                (item, produto["preco"], agora.isoformat()),
            )
    finally:
        conn.close()
    return True, f"{produto['nome']} comprado por {produto['preco']} de ouro."


def iniciar_pausa(dias, motivo=None, hoje=None):
    hoje = hoje or db_ops.agora_brasilia().date()
    dias = max(1, min(PAUSA_MAXIMA_DIAS, int(dias)))
    fim = hoje + timedelta(days=dias - 1)
    db_ops.init_db()
    conn = sqlite3.connect(db_ops.DB_PATH)
    try:
        with conn:
            conn.execute(
                "UPDATE jogo_pausas SET fim = ? WHERE fim IS NULL OR fim >= ?",
                ((hoje - timedelta(days=1)).isoformat(), hoje.isoformat()),
            )
            conn.execute(
                "INSERT INTO jogo_pausas (inicio, fim, motivo) VALUES (?, ?, ?)",
                (hoje.isoformat(), fim.isoformat(), motivo),
            )
    finally:
        conn.close()
    return fim


def encerrar_pausa(hoje=None):
    hoje = hoje or db_ops.agora_brasilia().date()
    db_ops.init_db()
    conn = sqlite3.connect(db_ops.DB_PATH)
    try:
        with conn:
            cur = conn.execute(
                "UPDATE jogo_pausas SET fim = ? WHERE inicio <= ? AND (fim IS NULL OR fim >= ?)",
                ((hoje - timedelta(days=1)).isoformat(), hoje.isoformat(), hoje.isoformat()),
            )
            return cur.rowcount > 0
    finally:
        conn.close()


CODIGOS_DIA = {
    "feito": "f",
    "hoje": "h",
    "pendente": "p",
    "perdido": "x",
    "descanso": "d",
    "pausa": "z",
}


def exportar_para_app(estado):
    """Versao compacta do estado para o Mini App (vai no fragmento da URL)."""
    historico = estado["historico_nivel"]
    if len(historico) > 30:
        passo = len(historico) / 30
        historico = [historico[int(i * passo)] for i in range(30)] + [historico[-1]]
    return {
        "v": 1,
        "nivel": estado["nivel"],
        "titulo": estado["titulo"],
        "classe": estado["classe"],
        "classe_base": estado["classe_base"],
        "exp": [estado["exp_total"], estado["exp_no_nivel"], estado["exp_do_nivel"]],
        "atr": estado["atributos"],
        "ouro": estado["ouro"],
        "seq": [estado["sequencia"], estado["melhor_sequencia"]],
        "cor": [estado["coringas_restantes"], estado["coringas_extras"]],
        "sem": [CODIGOS_DIA[d["estado"]] for d in estado["semana"]],
        "chefes": [
            [c["padrao"], c["nome"], c["rank_indice"], c["hp_pct"], c["e1rm"], c["alvo_e1rm"]]
            for c in estado["chefes"]
        ],
        "conq": [[c["id"], c["data"]] for c in estado["conquistas"] if c["data"]],
        "miss": [[m["nome"], m["progresso"], m["meta"], int(m["feita"])] for m in estado["missoes"]],
        "mus": [[m["nome"], m["nivel"]] for m in estado["musculos"][:12]],
        "hist": [[h["data"], h["nivel"]] for h in historico],
        "diario": [d["texto"] for d in estado["diario"][-5:]],
        "treinos": estado["treinos_concluidos"],
        "recordes": estado["recordes_total"],
    }


def exportar_json_app(estado):
    return json.dumps(exportar_para_app(estado), ensure_ascii=False, separators=(",", ":"))


# --------------------------------------------------------------------------
# Textos (legenda das imagens e alternativa quando a imagem falha)
# --------------------------------------------------------------------------


def _barra(atual, total, largura=10):
    if total <= 0:
        return "▰" * largura
    cheios = min(largura, int(largura * atual / total))
    return "▰" * cheios + "▱" * (largura - cheios)


def _pct(estado):
    if not estado["exp_do_nivel"]:
        return 100
    return int(100 * estado["exp_no_nivel"] / estado["exp_do_nivel"])


ICONES_DIA = {
    "feito": "✅",
    "hoje": "⚔",
    "pendente": "⬜",
    "perdido": "❌",
    "descanso": "💤",
    "pausa": "⏸",
}


def formatar_semana(estado):
    dias = " ".join(
        f"{d['dia'][:1]}{ICONES_DIA[d['estado']]}" for d in estado["semana"][:5]
    )
    castelo = "🏰" if estado["treinos_semana_atual"] >= TREINOS_POR_SEMANA else "🏯"
    return f"{dias} → {castelo}"


def _linhas_status(estado):
    falta = estado["exp_do_nivel"] - estado["exp_no_nivel"]
    linhas = [
        f"<b>{estado['titulo']}</b> · {estado['classe']} · Lv <b>{estado['nivel']}</b>",
        f"{_barra(estado['exp_no_nivel'], estado['exp_do_nivel'])} {_pct(estado)}%"
        f" (faltam {falta} EXP)",
        f"Semana: <b>{estado['treinos_semana_atual']}/{TREINOS_POR_SEMANA}</b>"
        f" · Sequência: <b>{estado['sequencia']}</b> sem. 🔥"
        f" · Coringas: <b>{estado['coringas_restantes'] + estado['coringas_extras']}</b>"
        f" · 🪙 <b>{estado['ouro']}</b>",
    ]
    if estado["em_pausa"]:
        linhas.append(
            "⏸ Em pausa"
            + (f" até {date.fromisoformat(estado['em_pausa']):%d/%m}" if estado["em_pausa"] != "aberta" else "")
        )
    return linhas


def formatar_hud(estado):
    return "\n".join(
        [
            f"⚔ <b>Lv {estado['nivel']}</b> {estado['titulo']} · {estado['classe']}"
            f"  {_barra(estado['exp_no_nivel'], estado['exp_do_nivel'], 8)} {_pct(estado)}%",
            formatar_semana(estado),
            f"🔥 {estado['sequencia']} sem. · 🃏 {estado['coringas_restantes'] + estado['coringas_extras']}"
            f" · 🪙 {estado['ouro']}"
            f" · FOR {estado['atributos']['FOR']} VIG {estado['atributos']['VIG']}"
            f" DIS {estado['atributos']['DIS']}",
        ]
    )


def _dano_em_chefes(antes, depois):
    danos = []
    por_padrao = {c["padrao"]: c for c in antes["chefes"]}
    for chefe in depois["chefes"]:
        anterior = por_padrao.get(chefe["padrao"])
        if anterior is None:
            continue
        if chefe["rank_indice"] > anterior["rank_indice"]:
            danos.append(f"💀 <b>{chefe['nome']}</b> derrotado! Rank {chefe['rank']}")
        elif chefe["hp_pct"] < anterior["hp_pct"]:
            danos.append(
                f"💥 {chefe['nome']} −{anterior['hp_pct'] - chefe['hp_pct']}% HP"
            )
    return danos


def formatar_vitoria(resultado):
    detalhe = resultado["detalhe"]
    antes = resultado["antes"]
    depois = resultado["depois"]

    partes = [f"presença {detalhe['presenca']}", f"séries {detalhe['series']}"]
    if detalhe["recordes"]:
        partes.append(f"recordes {EXP_RECORDE * len(detalhe['recordes'])}")
    if detalhe["semana_completa"]:
        partes.append(f"semana {EXP_SEMANA}")
    if detalhe["missoes"]:
        partes.append(f"missões {EXP_MISSAO * len(detalhe['missoes'])}")

    linhas = [
        "⚔ <b>VITÓRIA!</b>",
        f"EXP <b>+{detalhe['total']}</b> ({' · '.join(partes)})",
        f"🪙 Ouro <b>+{detalhe['ouro']}</b>",
    ]
    if detalhe["semana_completa"]:
        linhas.append("🏁 <b>Semana completa!</b>")
    for missao in detalhe["missoes"]:
        linhas.append(f"📜 Missão cumprida: {missao}")
    linhas.extend(_dano_em_chefes(antes, depois))
    for conquista in detalhe["conquistas"]:
        linhas.append(f"🏆 Conquista: <b>{conquista}</b>")
    if depois["nivel"] > antes["nivel"]:
        linhas.append(f"✨ <b>LEVEL UP!</b> Lv {antes['nivel']} → Lv {depois['nivel']}")
        if depois["titulo"] != antes["titulo"]:
            linhas.append(f"🎖 Novo título: <b>{depois['titulo']}</b>")
    if depois["classe"] != antes["classe"]:
        linhas.append(f"🔄 Nova classe: <b>{depois['classe']}</b>")
    ganhos = [
        f"{nome} +{depois['atributos'][nome] - antes['atributos'][nome]}"
        for nome in ("FOR", "VIG", "DIS")
        if depois["atributos"][nome] > antes["atributos"][nome]
    ]
    if ganhos:
        linhas.append("📈 " + " · ".join(ganhos))
    linhas.append("")
    linhas.extend(_linhas_status(depois))
    return "\n".join(linhas)


def subiu_de_nivel(resultado):
    return resultado["depois"]["nivel"] > resultado["antes"]["nivel"]


def formatar_perfil(estado):
    atr = estado["atributos"]
    linhas = ["📜 <b>FICHA DO PERSONAGEM</b>", ""]
    linhas.extend(_linhas_status(estado))
    linhas.extend(
        [
            "",
            f"FOR <b>{atr['FOR']}</b> · VIG <b>{atr['VIG']}</b> · DIS <b>{atr['DIS']}</b>",
            formatar_semana(estado),
            "",
            f"EXP total: <b>{estado['exp_total']}</b>",
            f"Treinos concluídos: <b>{estado['treinos_concluidos']}</b>",
            f"Recordes: <b>{estado['recordes_total']}</b>",
            f"Melhor sequência: <b>{estado['melhor_sequencia']}</b> sem.",
            "",
            "<i>FOR = força relativa ao seu peso · VIG = séries efetivas por "
            "músculo · DIS = presença e RPE certo nas últimas 8 semanas.</i>",
        ]
    )
    return "\n".join(linhas)


def formatar_chefes(estado):
    linhas = ["👹 <b>CHEFES</b>", ""]
    for chefe in estado["chefes"]:
        if chefe["proximo_rank"] is None:
            linhas.append(f"💀 <b>{chefe['nome']}</b> ({chefe['padrao']}) — todos derrotados")
            continue
        barra = _barra(chefe["hp_pct"], 100, 10)
        linhas.append(
            f"<b>{chefe['nome']}</b> ({chefe['padrao']}) · rank {chefe['rank']}"
        )
        alvo = (
            f" · alvo {chefe['alvo_e1rm']:.0f} kg de 1RM estimado"
            if chefe["alvo_e1rm"]
            else ""
        )
        linhas.append(
            f"HP {barra} {chefe['hp_pct']}% → {chefe['proximo_rank']}"
            f" (atual {chefe['e1rm']:.0f} kg{alvo})"
        )
        linhas.append("")
    linhas.append(
        "<i>Recorde com RPE até 9 tira HP. O rank usa o 1RM estimado dividido "
        "pelo seu peso (/peso).</i>"
    )
    return "\n".join(linhas)


def formatar_conquistas(estado):
    feitas = [c for c in estado["conquistas"] if c["data"]]
    linhas = [f"🏆 <b>CONQUISTAS</b> {len(feitas)}/{len(estado['conquistas'])}", ""]
    for conquista in estado["conquistas"]:
        if conquista["data"]:
            dia = date.fromisoformat(conquista["data"])
            linhas.append(f"🏆 <b>{conquista['nome']}</b> — {conquista['descricao']} ({dia:%d/%m/%Y})")
        else:
            linhas.append(f"🔒 {conquista['nome']} — {conquista['descricao']}")
    return "\n".join(linhas)


def formatar_missoes(estado):
    linhas = ["📜 <b>MISSÕES DA SEMANA</b>", ""]
    for missao in estado["missoes"]:
        marca = "✅" if missao["feita"] else "⬜"
        linhas.append(f"{marca} {missao['nome']} ({missao['progresso']}/{missao['meta']})")
    linhas.extend(
        ["", f"<i>Cada missão vale +{EXP_MISSAO} EXP e +{OURO_MISSAO} de ouro. Trocam toda segunda.</i>"]
    )
    return "\n".join(linhas)


def formatar_diario(estado, limite=10):
    if not estado["diario"]:
        return "📖 <b>DIÁRIO DE AVENTURA</b>\n\nNenhuma página ainda. Conclua um treino."
    linhas = ["📖 <b>DIÁRIO DE AVENTURA</b>", ""]
    linhas.extend(d["texto"] for d in reversed(estado["diario"][-limite:]))
    return "\n".join(linhas)


def formatar_loja(estado):
    linhas = ["🏪 <b>LOJA</b>", f"Seu ouro: 🪙 <b>{estado['ouro']}</b>", ""]
    for chave, item in LOJA.items():
        linhas.append(f"<b>{item['nome']}</b> — 🪙 {item['preco']}")
        linhas.append(f"{item['descricao']}")
        linhas.append(f"Comprar: <code>/loja {chave}</code>")
    return "\n".join(linhas)
