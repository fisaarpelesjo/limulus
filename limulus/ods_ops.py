"""Operacoes de treino do Limulus."""

import json
import math
from datetime import date, datetime
from pathlib import Path

from . import db_ops

SESSION_FILE = Path(__file__).resolve().parents[1] / "session.json"

TRAINING_EXERCISES = range(0, 11)
TREINO_EXERCISES = TRAINING_EXERCISES
# Progressao cautelosa para series de 12-15 repeticoes: no maximo um passo de
# anilha (2 kg) por sessao, mesmo com RPE 7 ou menor.
RPE_PROGRESSION_KG = {
    7: 2.0,
    8: 2.0,
    9: 0.0,
    10: -2.0,
}

INITIAL_TARGET_WEIGHTS = {
    "Rosca martelo (barra H)": 16.0,
    "Rosca inversa (barra)": 11.0,
    "Rosca de punho atrás das costas (barra)": 11.0,
    "Supino inclinado (barra)": 41.0,
    "Elevação lateral": 4.0,
    "Remada apoiada no banco (barras 40 cm)": 14.0,
    "Crucifixo invertido apoiado (barras 40 cm)": 4.0,
}

TRAINING_B_RULES = (
    {
        "name": "Farmer walk ida e volta",
        "work": "45s",
        "source": "Levantamento Terra Romeno",
        "percent": 0.45,
        "rounding": "ceil",
        "equipment": "loose_pair",
    },
    {
        "name": "Marcha forte no lugar com joelho alto",
        "work": "45s",
        "source": None,
        "percent": None,
        "rounding": None,
        "equipment": None,
    },
    {
        "name": "Agachamento com pausa",
        "work": "15 a 20 reps",
        "source": None,
        "percent": None,
        "rounding": None,
        "equipment": None,
    },
    {
        "name": "Remada leve com barra",
        "work": "12 a 15 reps",
        "source": "Remada curvada (barra)",
        "percent": 0.60,
        "rounding": "ceil",
        "equipment": "straight_bar_250",
    },
    {
        "name": "Flexão",
        "work": "8 a 15 reps",
        "source": None,
        "percent": None,
        "rounding": None,
        "equipment": None,
    },
    {
        "name": "Sombra de boxe ou corda sem corda",
        "work": "45s",
        "source": None,
        "percent": None,
        "rounding": None,
        "equipment": None,
    },
)

DISPLAY_NAMES = {
    "Supino reto (barra)": "Supino reto",
    "Supino inclinado (barra)": "Supino inclinado",
    "Supino fechado (barra)": "Supino fechado",
    "Remada curvada (barra)": "Remada curvada",
    "Remada curvada alta no peito (barra)": "Remada curvada alta no peito",
    "Remada alta (barra)": "Remada alta",
    "Desenvolvimento (barra em pé)": "Desenvolvimento",
    "Desenvolvimento (barra em pe)": "Desenvolvimento",
    "Pullover (barra)": "Pullover",
    "Rosca martelo (barra H)": "Rosca martelo",
    "Rosca inversa (barra)": "Rosca inversa",
    "Rosca de punho atrás das costas (barra)": "Rosca de punho atrás das costas",
    "Remada apoiada no banco (barras 40 cm)": "Remada apoiada no banco",
    "Crucifixo invertido apoiado (barras 40 cm)": "Crucifixo invertido apoiado",
    "Tríceps testa": "Tríceps testa",
    "Triceps testa": "Tríceps testa",
}

REST_INTERVALS = {
    "Agachamento com barra nas costas": "3 min",
    "Agachamento Zercher": "2 min",
    "Agachamento sumô com barra à frente": "90 s",
    "Supino reto (barra)": "2 min",
    "Supino reto back-off": "3 min",
    "Supino inclinado (barra)": "90 s",
    "Remada curvada (barra)": "90 s",
    "Desenvolvimento (barra em pé)": "90 s",
    "Desenvolvimento (barra em pe)": "90 s",
    "Levantamento Terra Romeno": "2 min",
    "Pullover (barra)": "60 s",
    "Remada curvada alta no peito (barra)": "90 s",
    "Rosca direta": "60 s",
    "Elevação lateral": "60 s",
    "Remada apoiada no banco (barras 40 cm)": "90 s",
    "Crucifixo invertido apoiado (barras 40 cm)": "60 s",
    "Rosca martelo (barra H)": "60 s",
    "Rosca inversa (barra)": "60 s",
    "Rosca de punho atrás das costas (barra)": "60 s",
    "Tríceps testa": "60 s",
    "Triceps testa": "60 s",
}

# Piramide crescente: a primeira serie usa 80% do alvo e a ultima e a serie
# de topo, onde vale o RPE registrado.
SET_RAMP_START = 0.80
PLATE_STEP_KG = 2.0

# Retorno apos pausa: exercicio parado ha RETURN_AFTER_DAYS dias ou mais volta
# com a ultima carga menos RETURN_REDUCTION_KG, sem somar a progressao por RPE.
RETURN_AFTER_DAYS = 10
RETURN_REDUCTION_KG = 4.0
# Pausa longa: parado ha RETURN_LONG_AFTER_DAYS dias ou mais, a carga volta a
# RETURN_LONG_FACTOR da ultima (ja convertida por reps), arredondada para baixo.
RETURN_LONG_AFTER_DAYS = 21
RETURN_LONG_FACTOR = 0.80

LOAD_EQUIPMENT = {
    "Agachamento com barra nas costas": {
        "name": "barra reta 2,20 m",
        "weight": 11.0,
    },
    "Agachamento Zercher": {"name": "barra reta 2,20 m", "weight": 11.0},
    "Agachamento sumô com barra à frente": {
        "name": "barra reta 2,20 m",
        "weight": 11.0,
    },
    "Supino reto (barra)": {"name": "barra reta 2,20 m", "weight": 11.0},
    "Supino reto back-off": {"name": "barra reta 2,20 m", "weight": 11.0},
    "Supino inclinado (barra)": {"name": "barra reta 2,20 m", "weight": 11.0},
    "Remada curvada (barra)": {"name": "barra reta 2,20 m", "weight": 11.0},
    "Desenvolvimento (barra em pé)": {
        "name": "barra reta 2,20 m",
        "weight": 11.0,
    },
    "Desenvolvimento (barra em pe)": {
        "name": "barra reta 2,20 m",
        "weight": 11.0,
    },
    "Levantamento Terra Romeno": {
        "name": "barra reta 2,20 m",
        "weight": 11.0,
    },
    "Pullover (barra)": {"name": "barra W", "weight": 6.0},
    "Remada curvada alta no peito (barra)": {
        "name": "barra reta 2,20 m",
        "weight": 11.0,
    },
    "Rosca martelo (barra H)": {"name": "barra H", "weight": 9.0},
    "Rosca inversa (barra)": {
        "name": "barra reta 2,20 m",
        "weight": 11.0,
    },
    "Rosca de punho atrás das costas (barra)": {
        "name": "barra reta 2,20 m",
        "weight": 11.0,
    },
    "Tríceps testa": {"name": "barra W", "weight": 6.0},
    "Triceps testa": {"name": "barra W", "weight": 6.0},
    "Rosca direta": {"name": "barra W", "weight": 6.0},
    # Uma barra oca de 40 cm em cada mao; a carga registrada e por mao.
    "Elevação lateral": {"name": "barra de 40 cm", "weight": 0.0, "per_hand": True},
    "Remada apoiada no banco (barras 40 cm)": {
        "name": "barra de 40 cm",
        "weight": 0.0,
        "per_hand": True,
    },
    "Crucifixo invertido apoiado (barras 40 cm)": {
        "name": "barra de 40 cm",
        "weight": 0.0,
        "per_hand": True,
    },
}

def read_exercises():
    db_ops.get_or_seed_exercises()
    plan = db_ops.get_active_training_plan()
    return plan["exercises"] if plan else []


def read_previous_weights():
    return db_ops.get_last_weights()


def read_previous_performance():
    return db_ops.get_last_performance()


def read_muscle_groups():
    return db_ops.list_muscle_groups()


def days_between(start_iso, end_iso):
    if not start_iso or not end_iso:
        return None
    start = datetime.strptime(str(start_iso)[:10], "%Y-%m-%d").date()
    end = datetime.strptime(str(end_iso)[:10], "%Y-%m-%d").date()
    return (end - start).days


def suggest_next_weight(previous_weight, previous_rpe=None, previous_reps=None,
                        target_reps=None, exercise_name=None, days_since=None):
    if previous_weight is None:
        return None
    reps_changed = (
        previous_reps and target_reps and int(previous_reps) != int(target_reps)
    )
    if days_since is not None and days_since >= RETURN_AFTER_DAYS:
        base = (
            convert_weight_for_reps(previous_weight, previous_reps, target_reps, exercise_name)
            if reps_changed else float(previous_weight)
        )
        equipment = LOAD_EQUIPMENT.get(exercise_name)
        floor = equipment["weight"] if equipment else 0.0
        if days_since >= RETURN_LONG_AFTER_DAYS:
            return round_down_to_plates(base * RETURN_LONG_FACTOR, exercise_name)
        return max(base - RETURN_REDUCTION_KG, floor)
    if reps_changed:
        return convert_weight_for_reps(
            previous_weight, previous_reps, target_reps, exercise_name
        )
    if previous_rpe is None:
        return float(previous_weight)

    rpe = int(previous_rpe)
    if rpe <= 7:
        delta = RPE_PROGRESSION_KG[7]
    elif rpe >= 10:
        delta = RPE_PROGRESSION_KG[10]
    else:
        delta = RPE_PROGRESSION_KG.get(rpe, 0.0)
    return float(previous_weight) + delta


def round_down_to_plates(weight, exercise_name=None):
    """Arredonda para baixo em passos de anilha, sem ficar abaixo da barra."""
    equipment = LOAD_EQUIPMENT.get(exercise_name)
    bar_weight = equipment["weight"] if equipment else 0.0
    plates = max(float(weight) - bar_weight, 0.0)
    return bar_weight + math.floor(plates / PLATE_STEP_KG) * PLATE_STEP_KG


def convert_weight_for_reps(weight, from_reps, to_reps, exercise_name=None):
    """Converte a carga entre faixas de repeticao pelo 1RM estimado (Epley)."""
    one_rm = float(weight) * (1 + int(from_reps) / 30)
    converted = one_rm / (1 + int(to_reps) / 30)
    return round_down_to_plates(converted, exercise_name)


def get_set_weights(exercise_name, target_weight, sets):
    """Retorna a carga de cada serie da piramide crescente ate o alvo."""
    if target_weight is None:
        return []
    sets = max(int(sets), 1)
    if sets == 1:
        return [float(target_weight)]
    weights = []
    for idx in range(sets):
        ratio = SET_RAMP_START + (1 - SET_RAMP_START) * idx / (sets - 1)
        if idx == sets - 1:
            weights.append(float(target_weight))
        else:
            weights.append(round_down_to_plates(target_weight * ratio, exercise_name))
    return weights


def get_initial_target_weight(exercise_name):
    return INITIAL_TARGET_WEIGHTS.get(exercise_name)


def get_display_name(exercise_name):
    return DISPLAY_NAMES.get(exercise_name, exercise_name)


def get_rest_interval(exercise_name):
    return REST_INTERVALS.get(exercise_name, "2 min")


def format_weight(weight):
    return str(int(weight) if weight == int(weight) else weight)


def format_loading_note(exercise_name, target_weight):
    equipment = LOAD_EQUIPMENT.get(exercise_name)
    if not equipment or target_weight is None:
        return None

    bar_weight = equipment["weight"]
    plates_weight = max(float(target_weight) - bar_weight, 0.0)
    if equipment.get("per_hand"):
        return (
            f"{equipment['name']} em cada mao"
            f" + {format_weight(plates_weight)}kg de anilhas por mao"
        )
    return (
        f"{equipment['name']} {format_weight(bar_weight)}kg"
        f" + {format_weight(plates_weight)}kg de anilhas"
    )


def round_training_b_weight(weight, mode="nearest", increment=2):
    if weight is None:
        return None

    value = float(weight)
    step = float(increment)
    if mode == "ceil":
        rounded = math.ceil(value / step) * step
    else:
        rounded = math.floor((value / step) + 0.5) * step
    return float(rounded)


def format_training_b_loading_note(equipment, target_weight):
    if target_weight is None or equipment is None:
        return None

    if equipment == "straight_bar_250":
        bar_weight = 9.0
        plates_weight = max(float(target_weight) - bar_weight, 0.0)
        return (
            f"barra reta 2,50 m {format_weight(bar_weight)}kg"
            f" + {format_weight(plates_weight)}kg de anilhas"
        )
    if equipment == "loose_pair":
        per_hand = float(target_weight) / 2
        return (
            "2 barras de 40 cm"
            f" + {format_weight(per_hand)}kg por mao"
        )
    if equipment == "loose_single":
        return f"barra de 40 cm + {format_weight(target_weight)}kg de anilhas"
    if equipment == "loose_load":
        return f"anilha de {format_weight(target_weight)}kg abracada no peito"
    return None


def build_training_plan(persist=True):
    """
    Monta o treino atual com carga alvo e descanso.
    Se persist=True, cria sessao e logs no SQLite.
    """
    db_ops.get_or_seed_exercises()
    plan = db_ops.get_active_training_plan()
    if plan is None or not plan["exercises"]:
        raise RuntimeError("Nenhum plano de treino ativo com exercicios.")
    exercises = plan["exercises"]
    previous_performance = read_previous_performance()

    session_id = None
    today = date.today().strftime("%Y-%m-%d")
    if persist:
        session_id = db_ops.create_session(today, plan["name"])

    session_exercises = []
    for idx, ex in enumerate(exercises):
        log_id = None
        if persist:
            log_id = db_ops.log_exercise(session_id, ex["name"], ex["sets"], ex["reps"], idx)
        previous = previous_performance.get(ex["name"], {})
        target_weight = suggest_next_weight(
            previous.get("weight"),
            previous.get("rpe"),
            previous.get("reps"),
            ex["reps"],
            ex["name"],
            days_between(previous.get("date"), today),
        )
        if target_weight is None:
            target_weight = get_initial_target_weight(ex["name"])
        item = {
            "name": ex["name"],
            "sets": ex["sets"],
            "reps": ex["reps"],
            "target_weight": target_weight,
            "rest_interval": get_rest_interval(ex["name"]),
        }
        loading_note = format_loading_note(ex["name"], target_weight)
        if loading_note:
            item["loading_note"] = loading_note
        if log_id is not None:
            item["log_id"] = log_id
        session_exercises.append(item)

    return session_exercises, session_id


def build_training_b():
    """
    Monta o Treino B de garagem a partir dos alvos atuais do treino principal.
    Nao cria sessao, logs nem session.json.
    """
    # Os exercicios de origem podem estar em planos diferentes da rotacao A/B.
    performance = read_previous_performance()
    targets = {}
    for rule in TRAINING_B_RULES:
        if rule["source"]:
            previous = performance.get(rule["source"], {})
            target = suggest_next_weight(previous.get("weight"), previous.get("rpe"))
            if target is None:
                target = get_initial_target_weight(rule["source"])
            targets[rule["source"]] = target

    training_b = []
    for rule in TRAINING_B_RULES:
        target_weight = None
        if rule["source"]:
            source_target = targets.get(rule["source"])
            if source_target is not None:
                target_weight = round_training_b_weight(
                    source_target * rule["percent"],
                    rule["rounding"],
                )
        training_b.append(
            {
                "name": rule["name"],
                "work": rule["work"],
                "target_weight": target_weight,
                "source": rule["source"],
                "loading_note": format_training_b_loading_note(
                    rule["equipment"],
                    target_weight,
                ),
            }
        )
    return training_b


def generate_training():
    """
    Cria uma sessao de treino no SQLite.
    Retorna (exercises, session_id), onde exercises e uma lista de
    {log_id, name, sets, reps}.
    """
    return build_training_plan(persist=True)


def preview_training():
    return build_training_plan(persist=False)[0]


def gerar_treino():
    return generate_training()


def write_session(exercises, session_id=None):
    data = {
        "date": date.today().strftime("%Y-%m-%d"),
        "exercises": exercises,
    }
    if session_id is not None:
        data["session_id"] = session_id
    with open(SESSION_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def recover_active_session():
    """Reconstrui o cache da sessao ativa a partir do SQLite."""
    stored = db_ops.get_latest_incomplete_session()
    if stored is None:
        return None

    exercises = []
    for row in stored["exercises"]:
        target_weight = suggest_next_weight(
            row["previous_weight"],
            row["previous_rpe"],
            row.get("previous_reps"),
            row["reps"],
            row["name"],
            days_between(row.get("previous_date"), stored["date"]),
        )
        if target_weight is None:
            target_weight = get_initial_target_weight(row["name"])
        item = {
            "log_id": row["log_id"],
            "name": row["name"],
            "sets": row["sets"],
            "reps": row["reps"],
            "target_weight": target_weight,
            "rest_interval": get_rest_interval(row["name"]),
        }
        loading_note = format_loading_note(row["name"], target_weight)
        if loading_note:
            item["loading_note"] = loading_note
        exercises.append(item)

    data = {
        "date": stored["date"],
        "session_id": stored["session_id"],
        "exercises": exercises,
    }
    with open(SESSION_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data
