"""Teste leve do Mini App (docs/app/index.html) e do JSON que vai no fragmento."""

import base64
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from limulus import jogo


APP = ROOT_DIR / "docs" / "app" / "index.html"
LIMITE_FRAGMENTO = 4000

# Treinos A a E com exercicios reais dos planos, para o estado ficar realista.
PLANOS = {
    "A": [("Supino reto (barra)", 50), ("Supino inclinado (barra)", 41),
          ("Desenvolvimento (barra em pé)", 30), ("Elevação lateral", 2), ("Tríceps testa", 16)],
    "B": [("Remada curvada (barra)", 45), ("Remada curvada alta no peito (barra)", 31),
          ("Pullover (barra)", 16), ("Rosca direta", 16), ("Rosca inversa (barra)", 11)],
    "C": [("Agachamento Zercher", 50), ("Levantamento Terra Romeno", 60),
          ("Agachamento sumô com barra à frente", 40),
          ("Rosca de punho atrás das costas (barra)", 11)],
    "D": [("Supino inclinado (barra)", 41), ("Supino reto (barra)", 50),
          ("Desenvolvimento (barra em pé)", 30), ("Elevação lateral", 2), ("Tríceps testa", 16)],
    "E": [("Remada apoiada no banco (barras 40 cm)", 12), ("Pullover (barra)", 16),
          ("Levantamento Terra Romeno", 60), ("Crucifixo invertido apoiado (barras 40 cm)", 2),
          ("Rosca direta", 16)],
}
GRUPOS = {
    "Supino reto (barra)": [("Peitoral", "principal"), ("Tríceps", "secundario")],
    "Supino inclinado (barra)": [("Peitoral", "principal"), ("Deltoides", "secundario")],
    "Desenvolvimento (barra em pé)": [("Deltoides", "principal"), ("Tríceps", "secundario")],
    "Elevação lateral": [("Deltoides", "principal")],
    "Tríceps testa": [("Tríceps", "principal")],
    "Remada curvada (barra)": [("Dorsais", "principal"), ("Bíceps", "secundario")],
    "Remada curvada alta no peito (barra)": [("Trapézio", "principal")],
    "Pullover (barra)": [("Dorsais", "principal"), ("Peitoral", "secundario")],
    "Rosca direta": [("Bíceps", "principal")],
    "Rosca inversa (barra)": [("Antebraços", "principal")],
    "Agachamento Zercher": [("Quadríceps", "principal"), ("Glúteos", "secundario")],
    "Levantamento Terra Romeno": [("Isquiotibiais", "principal"), ("Glúteos", "secundario")],
    "Agachamento sumô com barra à frente": [("Adutores", "principal"), ("Glúteos", "secundario")],
    "Rosca de punho atrás das costas (barra)": [("Antebraços", "principal")],
    "Remada apoiada no banco (barras 40 cm)": [("Dorsais", "principal")],
    "Crucifixo invertido apoiado (barras 40 cm)": [("Deltoide posterior", "principal")],
}
MARCAS_PESSOAIS = ("filip", "@gmail", "@hotmail", "bot_token", "chat_id", "api.telegram.org/bot")


def _b64url(texto):
    return base64.urlsafe_b64encode(texto.encode("utf-8")).decode("ascii").rstrip("=")


def _de_b64url(valor):
    return base64.urlsafe_b64decode(valor + "=" * (-len(valor) % 4)).decode("utf-8")


def _sessoes_sinteticas(total=70):
    """~14 semanas de 5 treinos, com cargas subindo e RPE variado."""
    sessoes = []
    segunda = date(2026, 8, 17)
    sid = 1
    rpes = (8, 9, 8, 7, 9, 10, 8, 9)
    while len(sessoes) < total:
        for i, plano in enumerate("ABCDE"):
            if len(sessoes) >= total:
                break
            dia = segunda + timedelta(days=i)
            semana_n = (dia - date(2026, 8, 17)).days // 7
            logs = []
            for j, (nome, base) in enumerate(PLANOS[plano]):
                logs.append({
                    "id": sid * 100 + j,
                    "nome": nome,
                    "peso": float(base + 2 * (semana_n // 2)),
                    "rpe": rpes[(sid + j) % len(rpes)],
                    "sets": 4 if nome == "Elevação lateral" else 3,
                    "reps": 15 if "Rosca" in nome or "Tríceps" in nome else 12,
                })
            hora = 6 if sid % 9 == 0 else 22 if sid % 11 == 0 else 18
            sessoes.append({
                "id": sid,
                "data": dia,
                "tipo": plano,
                "inicio": datetime.combine(dia, datetime.min.time()).replace(hour=hora),
                "logs": logs,
            })
            sid += 1
        segunda += timedelta(days=7)
    return sessoes


def _assert_pagina():
    assert APP.exists(), f"Mini App ausente: {APP}"
    html = APP.read_text(encoding="utf-8")
    baixo = html.lower()
    for marca in MARCAS_PESSOAIS:
        assert marca not in baixo, f"marca pessoal no Mini App: {marca}"
    assert "#d=" in html
    assert '"d="' in html  # le o parametro d do fragmento
    assert "atob(" in html and "TextDecoder" in html
    assert 'replace(/-/g, "+")' in html and 'replace(/_/g, "/")' in html
    assert "telegram-web-app.js" in html
    assert "fetch(" not in html and "localStorage" not in html
    # Todos os codigos de dia exportados precisam ser reconhecidos pela pagina.
    for codigo in jogo.CODIGOS_DIA.values():
        assert f"{codigo}: " in html, f"codigo de dia sem tratamento: {codigo}"
    for cid, _, _ in jogo.CONQUISTAS:
        assert f'"{cid}"' in html, f"conquista fora do catalogo do Mini App: {cid}"
    for rank in jogo.RANKS:
        assert f'"{rank}"' in html


def _assert_fragmento():
    hoje = date(2026, 11, 23)

    vazio = jogo.exportar_json_app(jogo.calcular([], hoje=hoje))
    assert json.loads(_de_b64url(_b64url(vazio))) == json.loads(vazio)

    extras = {
        "pesos": [(date(2026, 8, 1), 82.0), (date(2026, 10, 1), 79.5)],
        "grupos": GRUPOS,
        "compras": [],
        "pausas": [],
    }
    estado = jogo.calcular(_sessoes_sinteticas(70), hoje=hoje, extras=extras)
    texto = jogo.exportar_json_app(estado)
    dados = json.loads(texto)
    assert dados["v"] == 1 and dados["treinos"] == 70
    assert len(dados["sem"]) == 7 and set(dados["sem"]) <= set(jogo.CODIGOS_DIA.values())
    assert dados["chefes"] and dados["mus"] and dados["hist"]
    fragmento = "#d=" + _b64url(texto)
    assert json.loads(_de_b64url(fragmento[3:])) == dados
    assert len(fragmento) < LIMITE_FRAGMENTO, f"fragmento grande demais: {len(fragmento)}"
    return len(fragmento)


def main():
    _assert_pagina()
    tamanho = _assert_fragmento()
    print(f"app_test: ok (fragmento de {tamanho} caracteres)")


if __name__ == "__main__":
    main()
