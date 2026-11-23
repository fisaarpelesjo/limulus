import requests
import base64
import json
import logging
import time
from html import escape
from datetime import datetime
from pathlib import Path

from . import dashboard
from . import db_ops
from . import jogo
from . import ods_ops

BASE_DIR = Path(__file__).resolve().parents[1]
SESSION_FILE = BASE_DIR / "session.json"
CHAT_ID = "6575275306"
DASHBOARD_OUTPUT = dashboard.DEFAULT_OUTPUT
LOGGER = logging.getLogger("limulus.telegram")
SEND_RETRY_DELAYS = (1, 2)
POLL_RETRY_INITIAL = 3
POLL_RETRY_MAX = 60
# Long polling: o Telegram segura a requisicao ate chegar uma atualizacao (ou
# ate o tempo limite) e responde na hora em que o botao e tocado.
POLL_TIMEOUT = 25
# Sessao HTTP unica reaproveita a conexao TLS com a API entre as chamadas,
# evitando um novo handshake a cada mensagem, edicao ou resposta de botao.
HTTP = requests.Session()


class TelegramTemporaryError(RuntimeError):
    pass


class TelegramConfigurationError(RuntimeError):
    pass


def configure_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def read_token():
    env_file = BASE_DIR / ".env"
    if not env_file.exists():
        return None
    with open(env_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if "=" in line and line.split("=", 1)[0].upper() == "TELEGRAM_TOKEN":
                return line.split("=", 1)[1]
    return None


TOKEN = read_token()
API = f"https://api.telegram.org/bot{TOKEN}"


def send(text, reply_markup=None):
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    attempts = len(SEND_RETRY_DELAYS) + 1
    for attempt in range(1, attempts + 1):
        try:
            response = HTTP.post(
                f"{API}/sendMessage",
                json=payload,
                timeout=10,
            )
            if response.status_code in (401, 404):
                LOGGER.error("Falha permanente ao enviar mensagem: token invalido.")
                return False
            response.raise_for_status()
            return True
        except requests.RequestException as exc:
            if attempt >= attempts:
                LOGGER.error(
                    "Falha temporaria ao enviar mensagem tentativa=%s tipo=%s",
                    attempt,
                    type(exc).__name__,
                )
                return False
            delay = SEND_RETRY_DELAYS[attempt - 1]
            LOGGER.warning(
                "Falha temporaria ao enviar mensagem tentativa=%s tipo=%s espera=%ss",
                attempt,
                type(exc).__name__,
                delay,
            )
            time.sleep(delay)


def load_session():
    db_ops.init_db()
    session = None
    if SESSION_FILE.exists():
        try:
            with open(SESSION_FILE, encoding="utf-8") as f:
                session = json.load(f)
        except (OSError, json.JSONDecodeError):
            session = None

    if session:
        exercises = session.get("exercises", [])
        log_ids = [ex.get("log_id") for ex in exercises]
        if all(log_ids) and db_ops.is_session_incomplete(
            session.get("session_id"),
            log_ids,
        ):
            return session

    return ods_ops.recover_active_session()


def get_updates(offset=0):
    try:
        r = HTTP.get(
            f"{API}/getUpdates",
            params={"offset": offset, "timeout": POLL_TIMEOUT,
                    "allowed_updates": json.dumps(["message", "callback_query"])},
            timeout=POLL_TIMEOUT + 10,
        )
        if r.status_code in (401, 404):
            raise TelegramConfigurationError(
                "Token do Telegram invalido ou bot nao encontrado."
            )
        r.raise_for_status()
        payload = r.json()
        result = payload.get("result", [])
        if not isinstance(result, list):
            raise ValueError("Resposta sem lista de atualizacoes.")
        return result
    except TelegramConfigurationError:
        raise
    except (requests.RequestException, ValueError, json.JSONDecodeError) as exc:
        raise TelegramTemporaryError(type(exc).__name__) from None


def _command_name(text):
    normalized = text.strip().lower()
    if normalized.startswith("/"):
        return normalized.split(maxsplit=1)[0]
    return "registro_carga"


def _is_session_input(text):
    normalized = text.strip().lower()
    if normalized in {"/status", "/desfazer"}:
        return True
    try:
        float(normalized.replace(",", ".").split()[0])
        return True
    except (ValueError, IndexError):
        return False


def _format_weight(weight):
    if weight is None:
        return "-"
    return str(int(weight) if weight == int(weight) else weight)


def _format_body_weight(weight):
    return f"{float(weight):.1f}".replace(".", ",")


def _format_weight_date(recorded_at):
    return datetime.fromisoformat(recorded_at).strftime("%d/%m/%Y %H:%M")


def _format_target_suffix(ex):
    target_weight = ex.get("target_weight")
    if target_weight is None:
        return ""
    return f" - alvo {_format_weight(target_weight)}kg"


def _display_exercise_name(name):
    return ods_ops.get_display_name(name)


def _inimigo(ex):
    try:
        return jogo.inimigo_do_exercicio(db_ops.get_muscle_groups(ex["name"]))
    except Exception:
        return jogo.INIMIGO_PADRAO


def _posicao(ex, exercises):
    """(posicao, total) do exercicio na sessao, pelo log_id."""
    if not exercises:
        return None, None
    for indice, item in enumerate(exercises, start=1):
        if item.get("log_id") is not None and item.get("log_id") == ex.get("log_id"):
            return indice, len(exercises)
    return None, len(exercises)


def _format_current_exercise(ex, exercises=None):
    """Card da quest: cada exercicio e uma batalha contra um inimigo."""
    display_name = _display_exercise_name(ex["name"])
    target = ex.get("target_weight")
    equipment = ods_ops.LOAD_EQUIPMENT.get(ex["name"])
    posicao, total = _posicao(ex, exercises)
    numero = f" {posicao}/{total}" if posicao else ""
    header = (
        f"⚔ <b>QUEST{numero} · {escape(display_name.upper())}</b>\n"
        f"👹 Derrote o <b>{escape(_inimigo(ex))}</b>!"
    )
    set_weights = ods_ops.get_set_weights(ex["name"], target, ex["sets"])
    bar_weight = equipment["weight"] if equipment else 0.0
    per_hand = bool(equipment and equipment.get("per_hand"))
    sufixo_mao = " por mão" if per_hand else ""
    body = [f"📜 Objetivo: <b>{ex['sets']} golpes de {ex['reps']} repetições</b>"]
    for idx, weight in enumerate(set_weights, start=1):
        final = idx == len(set_weights)
        rotulo = "🎯 Golpe final" if final else f"⚔ Golpe {idx}"
        if equipment:
            load = max(weight - bar_weight, 0.0)
            body.append(
                f"{rotulo} · <b>{_format_weight(load)} kg</b> de anilhas{sufixo_mao}"
                f" <i>(total {_format_weight(weight)} kg{sufixo_mao})</i>"
            )
        else:
            body.append(f"{rotulo} · <b>{_format_weight(weight)} kg</b>")
    footer = [f"⏳ Descanso entre golpes: <b>{escape(ex.get('rest_interval', '2 min'))}</b>"]
    if equipment:
        bar_name = (
            equipment['name'].replace('barra reta ', '').removeprefix('barra ').removeprefix('de ')
        )
        footer.append(
            f"🏋 Barra {escape(bar_name)} · {_format_weight(equipment['weight'])} kg"
            f"{' (uma em cada mão)' if per_hand else ''}"
        )
    if target is not None:
        footer.append("🎯 <i>Depois do golpe final, como foi?</i>")
    else:
        footer.append("Carga alvo ainda não definida. Envie a carga total para este exercício.")
    return "\n\n".join([header, "\n".join(body), "\n".join(footer)])


def _format_quest_result(ex, weight, rpe):
    exp = round(jogo.EXP_SERIE * jogo.aderencia_rpe(int(rpe)))
    return (
        f"💥 <b>{jogo.nome_do_golpe(rpe)}!</b> {_format_weight(weight)} kg · RPE {rpe}\n"
        f"✅ <b>Quest completa:</b> {escape(_inimigo(ex))} derrotado! <b>+{exp} EXP</b>"
    )


def _format_exercise_line(idx, ex):
    set_weights = ods_ops.get_set_weights(ex["name"], ex.get("target_weight"), ex["sets"])
    target = "→".join(_format_weight(w) for w in set_weights) or "-"
    rest = ex.get("rest_interval", "2 min")
    display_name = _display_exercise_name(ex["name"])
    return (
        f"{idx}. <b>{display_name}</b>\n"
            f"   {ex['sets']}x{ex['reps']} | alvo: {target}kg | descanso: {rest}"
    )


def _format_training_msg(exercises):
    lines = [f"🔮 <b>Treino de hoje — {len(exercises)} exercícios</b>"]
    lines.extend(_format_exercise_line(idx, ex) for idx, ex in enumerate(exercises, start=1))
    return "\n\n".join(lines)


def _format_training_b_msg(exercises):
    lines = ["10 voltas | descanso 60s no fim da volta"]
    for idx, ex in enumerate(exercises, start=1):
        target = ex.get("target_weight")
        weight_line = (
            "peso corporal"
            if target is None
            else f"peso: {_format_weight(target)}kg"
        )
        lines.append(
            f"{idx}. <b>{ex['name']}</b>\n"
            f"   {ex['work']} | {weight_line}"
        )
        if ex.get("loading_note"):
            lines.append(f"   {ex['loading_note']}")
    return "\n\n".join(lines)


def _format_summary_names(items, limit=4):
    names = [_display_exercise_name(item["name"]) for item in items[:limit]]
    suffix = f" e mais {len(items) - limit}" if len(items) > limit else ""
    return ", ".join(names) + suffix


def _format_training_summary(session_id):
    summary = db_ops.get_session_summary(session_id)
    if summary is None:
        return "Resumo indisponivel."

    lines = [
        f"Volume total: <b>{summary['volume']:,.0f} kg</b>".replace(",", "."),
    ]
    if summary["rpe_average"] is not None:
        lines.append(f"RPE médio: <b>{summary['rpe_average']:.1f}</b>".replace(".", ","))
    if summary["volume_delta"] is not None:
        delta = summary["volume_delta"]
        signal = "+" if delta > 0 else ""
        lines.append("\n<b>Comparação com o treino anterior</b>")
        lines.append(
            f"Volume vs. sessao anterior: <b>{signal}{delta:,.0f} kg</b>".replace(
                ",", "."
            )
        )
    if summary["increases"]:
        lines.append(f"Aumentos de carga: {len(summary['increases'])} exercícios — {_format_summary_names(summary['increases'])}")
    if summary["reductions"]:
        lines.append(f"Reducoes: {_format_summary_names(summary['reductions'])}")
    if summary["consolidations"]:
        lines.append(
            f"Consolidacoes: {_format_summary_names(summary['consolidations'])}"
        )
    if summary["maintained_rpe9"]:
        lines.append(
            f"Cargas mantidas em RPE 9: "
            f"{_format_summary_names(summary['maintained_rpe9'])}"
        )
    if summary["records"]:
        lines.append(f"⭐ Recordes: {len(summary['records'])} — {_format_summary_names(summary['records'])}")
    return "\n".join(lines)


def _format_exercises_msg(exercises):
    display_names = [_display_exercise_name(ex["name"]) for ex in exercises]
    name_width = max([22, *(len(name) for name in display_names)])
    lines = ["<pre>Lista de exercicios\n"]
    lines.append(f"{'#':>2} {'Exercicio':<{name_width}} {'S':>2} {'R':>3}\n")
    lines.append("-" * (name_width + 12) + "\n")
    for idx, (ex, display_name) in enumerate(
        zip(exercises, display_names),
        start=1,
    ):
        lines.append(
            f"{idx:>2} {display_name:<{name_width}} {ex['sets']:>2} {ex['reps']:>3}\n"
        )
    lines.append("</pre>")
    return "".join(lines)


TECLADO_TREINO = "⚔ Iniciar treino"
TECLADO_DIETA = "🍖 Ver dieta"

KEYBOARD_START = {
    "keyboard": [[{"text": TECLADO_TREINO}, {"text": TECLADO_DIETA}]],
    "resize_keyboard": True,
    "is_persistent": True,
}


def telegram_action(method, payload):
    """Executa ações auxiliares sem expor URL ou token nos erros."""
    try:
        response = HTTP.post(f"{API}/{method}", json=payload, timeout=10)
        return response.status_code == 200 and response.json().get("ok", False)
    except (requests.RequestException, ValueError):
        LOGGER.warning("Falha na ação Telegram metodo=%s", method)
        return False


def telegram_call(method, payload, files=None):
    """Chama a API e devolve (ok, resultado ou descricao do erro).

    Todas as chamadas do jogo (fotos, audio, edicoes, mensagem fixada) passam
    por aqui; os testes substituem esta funcao para nunca falar com a rede.
    """
    try:
        if files:
            data = {
                chave: json.dumps(valor) if isinstance(valor, (dict, list)) else valor
                for chave, valor in payload.items()
            }
            response = HTTP.post(f"{API}/{method}", data=data, files=files, timeout=30)
        else:
            response = HTTP.post(f"{API}/{method}", json=payload, timeout=10)
        corpo = response.json()
        if corpo.get("ok"):
            return True, corpo.get("result")
        return False, str(corpo.get("description", response.status_code))
    except (requests.RequestException, ValueError):
        LOGGER.warning("Falha na chamada Telegram metodo=%s", method)
        return False, "falha de rede"


def _botoes_golpe(token):
    botoes = [
        {"text": rotulo, "callback_data": f"rpe:{token}:{valor}"}
        for rotulo, valor, _ in jogo.GOLPES_RPE
    ]
    return {"inline_keyboard": [botoes[:2], botoes[2:]]}


# file_id das telas de batalha ja enviadas: reenviar pelo id e instantaneo.
_CACHE_BATALHA = {}


def _send_batalha(ex, exercises, caption, markup):
    """Envia a tela de batalha com o card na legenda; devolve False se nao der."""
    visual = _visual()
    if visual is None or not hasattr(visual, "render_batalha"):
        return False
    try:
        posicao, total = _posicao(ex, exercises)
        estado = jogo.estado_atual()
        inimigo = _inimigo(ex)
        nivel = estado["nivel"]
        estagio = 0 if nivel < 10 else 1 if nivel < 30 else 2
        chave = (inimigo, posicao, total, estado["classe_base"], estagio)
        payload = {"chat_id": CHAT_ID, "caption": caption, "parse_mode": "HTML"}
        if markup:
            payload["reply_markup"] = markup
        if chave in _CACHE_BATALHA:
            ok, resultado = telegram_call("sendPhoto", dict(payload, photo=_CACHE_BATALHA[chave]))
            if ok:
                return True
        png = visual.render_batalha(inimigo, posicao or 1, total or 1, estado["classe_base"], estado["nivel"])
        ok, resultado = telegram_call("sendPhoto", payload, files={"photo": ("batalha.png", png, "image/png")})
        if ok and isinstance(resultado, dict) and resultado.get("photo"):
            _CACHE_BATALHA[chave] = resultado["photo"][-1]["file_id"]
        return ok
    except Exception as exc:
        LOGGER.error("Falha na tela de batalha tipo=%s", type(exc).__name__)
        return False


def send_current_exercise(ex, exercises=None):
    markup = None
    target = ex.get("target_weight")
    if target is not None and target > 0:
        token = db_ops.criar_botoes_rpe(ex['log_id'], target)
        markup = _botoes_golpe(token)
    texto = _format_current_exercise(ex, exercises)
    if not _send_batalha(ex, exercises, texto, markup):
        send(texto, reply_markup=markup)


def send_completion(session):
    timing = db_ops.get_session_timing(session['session_id'])
    lines = ["🏁 <b>TREINO CONCLUÍDO</b>"]
    start = datetime.fromisoformat(timing['started_at']) if timing.get('started_at') else None
    end = datetime.fromisoformat(timing['completed_at']) if timing.get('completed_at') else None
    if start:
        lines.extend([f"Data: <b>{start:%d/%m/%Y}</b>", f"Início: <b>{start:%H:%M}</b>"])
    if end:
        lines.append(f"Fim: <b>{end:%d/%m/%Y %H:%M}</b>")
    if start and end:
        minutes = max(0, int((end - start).total_seconds() // 60))
        lines.append(f"Duração: <b>{minutes // 60}h{minutes % 60:02d}</b>")
    total = len(session['exercises'])
    lines.extend(["", f"Exercícios: <b>{total}/{total}</b>", "", _format_training_summary(session['session_id'])])
    send("\n".join(lines), reply_markup=KEYBOARD_START)
    send_victory(session['session_id'])


# --------------------------------------------------------------------------
# Jogo estilo JRPG: tela de vitoria, imagens, HUD fixado, menu e Mini App
# --------------------------------------------------------------------------

# Efeito de mensagem do Telegram (confete) reservado a level up e semana
# completa; se o Telegram recusar o efeito, a mensagem sai sem ele.
EFEITO_FESTA = "5046509860389126442"
SOM_LEVEL_UP = BASE_DIR / "limulus" / "assets" / "jogo" / "level_up.ogg"
APP_URL = "https://fisaarpelesjo.github.io/limulus/app/"
PAUSA_ANIMACAO = 0.35

MENU_JOGO = {
    "inline_keyboard": [
        [
            {"text": "📜 Status", "callback_data": "menu:perfil"},
            {"text": "👹 Chefes", "callback_data": "menu:chefes"},
            {"text": "🗺 Semana", "callback_data": "menu:semana"},
        ],
        [
            {"text": "📋 Missões", "callback_data": "menu:missoes"},
            {"text": "🏆 Conquistas", "callback_data": "menu:conquistas"},
            {"text": "📖 Diário", "callback_data": "menu:diario"},
        ],
        [
            {"text": "🏪 Loja", "callback_data": "menu:loja"},
            {"text": "🎮 Abrir app", "callback_data": "menu:app"},
        ],
    ]
}


def _visual():
    """Carrega o modulo de imagens so quando preciso; sem Pillow, segue em texto."""
    try:
        from . import jogo_visual
        return jogo_visual
    except Exception as exc:
        LOGGER.warning("Imagens do jogo indisponiveis tipo=%s", type(exc).__name__)
        return None


def send_message(text, reply_markup=None, effect=None, silent=False):
    """Envia texto e devolve o objeto da mensagem (ou None)."""
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    if silent:
        payload["disable_notification"] = True
    if effect:
        ok, result = telegram_call("sendMessage", dict(payload, message_effect_id=effect))
        if ok:
            return result
    ok, result = telegram_call("sendMessage", payload)
    return result if ok else None


def send_image(render, *args, caption=None):
    """Gera a imagem com a funcao `render` do modulo visual e envia como foto."""
    visual = _visual()
    if visual is None:
        return False
    try:
        png = getattr(visual, render)(*args)
    except Exception as exc:
        LOGGER.error("Falha ao gerar imagem %s tipo=%s", render, type(exc).__name__)
        return False
    payload = {"chat_id": CHAT_ID}
    if caption:
        payload.update(caption=caption, parse_mode="HTML")
    ok, _ = telegram_call("sendPhoto", payload, files={"photo": (f"{render}.png", png, "image/png")})
    return ok


def send_level_up_sound():
    if not SOM_LEVEL_UP.exists():
        return False
    ok, _ = telegram_call(
        "sendVoice",
        {"chat_id": CHAT_ID, "disable_notification": True},
        files={"voice": ("level_up.ogg", SOM_LEVEL_UP.read_bytes(), "audio/ogg")},
    )
    return ok


def atualizar_hud(estado=None):
    """Mantem uma mensagem fixada no topo do chat com nivel, semana e ouro."""
    try:
        estado = estado or jogo.estado_atual()
        texto = jogo.formatar_hud(estado)
        mensagem_id = jogo.ler_estado("hud_mensagem")
        if mensagem_id:
            ok, erro = telegram_call(
                "editMessageText",
                {"chat_id": CHAT_ID, "message_id": int(mensagem_id), "text": texto, "parse_mode": "HTML"},
            )
            if ok or "not modified" in str(erro):
                return True
        mensagem = send_message(texto, silent=True)
        if not mensagem:
            return False
        telegram_call(
            "pinChatMessage",
            {"chat_id": CHAT_ID, "message_id": mensagem["message_id"], "disable_notification": True},
        )
        jogo.gravar_estado("hud_mensagem", mensagem["message_id"])
        return True
    except Exception as exc:
        LOGGER.error("Falha ao atualizar HUD tipo=%s", type(exc).__name__)
        return False


def _quadro_vitoria(detalhe, nivel, pct, level_up=False):
    barra = jogo._barra(pct, 100, 10)
    linhas = ["⚔ <b>VITÓRIA!</b>", f"EXP <b>+{detalhe['total']}</b>", f"Lv {nivel} {barra} {pct}%"]
    if level_up:
        linhas.append("✨ <b>LEVEL UP!</b>")
    return "\n".join(linhas)


def _animar_vitoria(resultado, texto_final):
    """Barra de EXP enchendo em poucas edicoes; sem id de mensagem, envia so o texto."""
    antes, depois, detalhe = resultado["antes"], resultado["depois"], resultado["detalhe"]
    festa = jogo.subiu_de_nivel(resultado) or detalhe["semana_completa"]
    pct_antes = jogo._pct(antes)
    mensagem = send_message(
        _quadro_vitoria(detalhe, antes["nivel"], pct_antes),
        effect=EFEITO_FESTA if festa else None,
    )
    if not mensagem:
        send(texto_final)
        return
    quadros = []
    if jogo.subiu_de_nivel(resultado):
        quadros.append(_quadro_vitoria(detalhe, antes["nivel"], (pct_antes + 100) // 2))
        quadros.append(_quadro_vitoria(detalhe, antes["nivel"], 100, level_up=True))
        quadros.append(_quadro_vitoria(detalhe, depois["nivel"], jogo._pct(depois), level_up=True))
    else:
        pct_depois = jogo._pct(depois)
        quadros.append(_quadro_vitoria(detalhe, depois["nivel"], (pct_antes + pct_depois) // 2))
        quadros.append(_quadro_vitoria(detalhe, depois["nivel"], pct_depois))
    quadros.append(texto_final)
    for quadro in quadros:
        time.sleep(PAUSA_ANIMACAO)
        telegram_call(
            "editMessageText",
            {"chat_id": CHAT_ID, "message_id": mensagem["message_id"], "text": quadro, "parse_mode": "HTML"},
        )


def send_victory(session_id):
    """Envia a tela de vitoria do jogo; falha aqui nunca afeta o treino."""
    try:
        resultado = jogo.resultado_da_sessao(session_id)
    except Exception as exc:
        LOGGER.error("Falha ao calcular EXP session_id=%s tipo=%s", session_id, type(exc).__name__)
        return
    if resultado is None:
        return
    try:
        _animar_vitoria(resultado, jogo.formatar_vitoria(resultado))
        send_image("render_vitoria", resultado)
        if jogo.subiu_de_nivel(resultado):
            send_level_up_sound()
        atualizar_hud(resultado["depois"])
    except Exception as exc:
        LOGGER.error("Falha na tela de vitoria session_id=%s tipo=%s", session_id, type(exc).__name__)


def _link_app(estado):
    dados = base64.urlsafe_b64encode(jogo.exportar_json_app(estado).encode("utf-8"))
    return APP_URL + "#d=" + dados.decode("ascii").rstrip("=")


def handle_profile():
    estado = jogo.estado_atual()
    send_image("render_ficha", estado)
    send(jogo.formatar_perfil(estado), reply_markup=MENU_JOGO)
    atualizar_hud(estado)


def handle_bosses():
    estado = jogo.estado_atual()
    send_image("render_chefes", estado)
    send(jogo.formatar_chefes(estado))


def handle_week():
    estado = jogo.estado_atual()
    send_image("render_semana", estado)
    send(
        "🗺 <b>MAPA DA SEMANA</b>\n\n"
        f"{jogo.formatar_semana(estado)}\n"
        f"Treinos: <b>{estado['treinos_semana_atual']}/{jogo.TREINOS_POR_SEMANA}</b>"
        f" · Sequência: <b>{estado['sequencia']}</b> sem.\n\n"
        + jogo.formatar_missoes(estado)
    )


def handle_app():
    estado = jogo.estado_atual()
    send(
        "🎮 <b>Ficha completa no app</b>\nToque no botão para abrir dentro do Telegram.",
        reply_markup={"inline_keyboard": [[{"text": "🎮 Abrir ficha", "web_app": {"url": _link_app(estado)}}]]},
    )


def handle_shop(text):
    partes = text.strip().split(maxsplit=1)
    if len(partes) == 2:
        ok, mensagem = jogo.comprar(partes[1].strip().lower())
        send(("🪙 " if ok else "⚠ ") + mensagem)
        if ok:
            atualizar_hud()
        return
    send(jogo.formatar_loja(jogo.estado_atual()))


def handle_pause(text):
    partes = text.strip().split(maxsplit=1)
    argumento = partes[1].strip().lower() if len(partes) == 2 else ""
    if argumento == "fim":
        if jogo.encerrar_pausa():
            send("▶ Pausa encerrada. Bem-vindo de volta à aventura!")
            atualizar_hud()
        else:
            send("Nenhuma pausa ativa.")
        return
    if not argumento:
        send(
            "⏸ <b>Pausa</b>\nUse <code>/pausa 7</code> para pausar 7 dias "
            f"(até {jogo.PAUSA_MAXIMA_DIAS}) por lesão, doença ou viagem, e "
            "<code>/pausa fim</code> para voltar. Semanas em pausa não gastam "
            "coringa nem quebram a sequência."
        )
        return
    try:
        dias = int(argumento)
    except ValueError:
        send("Use <code>/pausa 7</code> ou <code>/pausa fim</code>.")
        return
    fim = jogo.iniciar_pausa(dias)
    send(f"⏸ Pausa registrada até <b>{fim:%d/%m/%Y}</b>. A sequência fica protegida.")
    atualizar_hud()


def handle_menu():
    send("📜 <b>MENU DO HERÓI</b>\nEscolha uma opção:", reply_markup=MENU_JOGO)


def handle_menu_callback(query, opcao):
    telegram_action("answerCallbackQuery", {"callback_query_id": query["id"]})
    acoes = {
        "perfil": handle_profile,
        "chefes": handle_bosses,
        "semana": handle_week,
        "missoes": lambda: send(jogo.formatar_missoes(jogo.estado_atual())),
        "conquistas": lambda: send(jogo.formatar_conquistas(jogo.estado_atual())),
        "diario": lambda: send(jogo.formatar_diario(jogo.estado_atual())),
        "loja": lambda: send(jogo.formatar_loja(jogo.estado_atual())),
        "app": handle_app,
    }
    acao = acoes.get(opcao)
    if acao:
        acao()


def handle_rpe_callback(query):
    message = query.get('message', {})
    if str(message.get('chat', {}).get('id', '')) != CHAT_ID or str(query.get('from', {}).get('id', '')) != CHAT_ID:
        return
    if query.get('data', '').startswith('menu:'):
        handle_menu_callback(query, query['data'].split(':', 1)[1])
        return
    parts = query.get('data', '').split(':')
    if len(parts) != 3 or parts[0] != 'rpe' or parts[2] not in {'7', '8', '9', '10'}:
        telegram_action('answerCallbackQuery', {'callback_query_id': query['id'], 'text': 'Botão de demonstração ou inválido.'})
        return
    session = load_session()
    result = db_ops.registrar_rpe_botao(parts[1], int(parts[2])) if session else None
    telegram_action('answerCallbackQuery', {
        'callback_query_id': query['id'],
        'text': 'Golpe registrado! ⚔' if result else 'Este botão já foi usado ou não é do exercício atual. Use /status.',
    })
    if not result:
        return
    ex = next(ex for ex in session['exercises'] if ex['log_id'] == result['log_id'])
    ex = dict(ex, target_weight=result['weight'])
    confirmation = _format_quest_result(ex, result['weight'], int(parts[2]))
    texto = _format_current_exercise(ex, session['exercises']) + '\n\n' + confirmation
    if message.get('photo'):
        edited = telegram_action('editMessageCaption', {
            'chat_id': CHAT_ID, 'message_id': message['message_id'], 'parse_mode': 'HTML',
            'caption': texto, 'reply_markup': {'inline_keyboard': []},
        })
    else:
        edited = telegram_action('editMessageText', {
            'chat_id': CHAT_ID, 'message_id': message['message_id'], 'parse_mode': 'HTML',
            'text': texto, 'reply_markup': {'inline_keyboard': []},
        })
    if not edited:
        send(confirmation)
    filled = db_ops.count_filled([ex['log_id'] for ex in session['exercises']])
    if filled == len(session['exercises']):
        send_completion(session)
    else:
        send_current_exercise(session['exercises'][filled], session['exercises'])


def handle_generate():
    session = load_session()
    if session:
        filled = db_ops.count_filled([ex['log_id'] for ex in session['exercises']])
        total = len(session['exercises'])
        send(
            f"⚔ Batalha em andamento — quest {filled + 1}/{total}. Continue abaixo.",
            reply_markup={"remove_keyboard": True},
        )
        send_current_exercise(session['exercises'][filled], session['exercises'])
        return
    try:
        exercises, session_id = ods_ops.generate_training()
    except Exception as e:
        LOGGER.error(
            "Falha ao gerar sessao tipo=%s",
            type(e).__name__,
        )
        send(f"Erro ao gerar sessao de treino: {e}")
        return

    ods_ops.write_session(exercises, session_id)

    if not exercises:
        send("O plano não tem exercícios. Consulte /planos.", reply_markup=KEYBOARD_START)
        return
    start = datetime.fromisoformat(db_ops.get_session_timing(session_id)['started_at'])
    plano = (db_ops.get_active_training_plan() or {}).get("name", "")
    send(
        f"⚔ <b>BATALHA INICIADA!</b>\n"
        f"🗺 Treino {escape(plano)} · {jogo.DIAS_SEMANA_LONGOS[start.weekday()]}, "
        f"{start:%d/%m} · {start:%H:%M}\n"
        f"👹 <b>{len(exercises)} quests</b> pela frente\n\n"
        "Em cada quest, faça os golpes e toque no botão do golpe final.",
        reply_markup={"remove_keyboard": True},
    )
    send_image("render_encontro", [_inimigo(ex) for ex in exercises], plano)
    send_current_exercise(exercises[0], exercises)


def handle_preview():
    try:
        exercises = ods_ops.preview_training()
    except Exception as e:
        LOGGER.error(
            "Falha ao gerar previa tipo=%s",
            type(e).__name__,
        )
        send(f"Erro ao gerar previa do treino: {e}")
        return

    msg = _format_training_msg(exercises)
    send(msg)
    send("Previa do treino. Nada foi salvo. Use /gerar para iniciar uma sessao real.")


def handle_training_b():
    try:
        exercises = ods_ops.build_training_b()
    except Exception as e:
        LOGGER.error(
            "Falha ao gerar treino B tipo=%s",
            type(e).__name__,
        )
        send(f"Erro ao gerar treino B: {e}")
        return

    send(_format_training_b_msg(exercises))


def handle_exercises():
    try:
        exercises = ods_ops.read_exercises()
        send(_format_exercises_msg(exercises))
    except Exception as exc:
        LOGGER.error("Falha ao listar exercicios tipo=%s", type(exc).__name__)
        send("Erro ao listar exercicios. Consulte o terminal.")


def handle_volume():
    try:
        exercises = ods_ops.read_exercises()
        muscle_groups = ods_ops.read_muscle_groups()
        muscle_sets = {}
        for ex in exercises:
            groups = muscle_groups.get(ex["name"], [])
            muscles = [group["muscle_group"] for group in groups] or ["Outros"]
            for muscle in muscles:
                muscle_sets[muscle] = muscle_sets.get(muscle, 0) + ex["sets"]
        lines = [
            "📊 <b>Volume por musculo</b>\n",
            "<i>series/sessao → series/semana (~3.5x)</i>\n",
        ]
        for muscle, sets in sorted(muscle_sets.items()):
            weekly = round(sets * 3.5, 1)
            lines.append(f"{muscle}: <b>{sets}</b> → ~{weekly:.0f}/sem")
        send("\n".join(lines))
    except Exception as exc:
        LOGGER.error("Falha ao calcular volume tipo=%s", type(exc).__name__)
        send("Erro ao calcular volume. Consulte o terminal.")


def handle_plans():
    plans = db_ops.list_training_plans()
    if not plans:
        send("Nenhum plano de treino cadastrado.")
        return
    lines = ["🗺 <b>Planos de treino</b>"]
    for plan in plans:
        marker = " ✓ ativo" if plan["active"] else ""
        lines.append(
            f"{plan['name']}: {plan['exercise_count']} exercicios{marker}"
        )
    lines.append("\nUse <code>/plano NOME</code> para selecionar.")
    send("\n".join(lines))


def handle_select_plan(text):
    parts = text.strip().split(maxsplit=1)
    if len(parts) < 2:
        handle_plans()
        return
    name = parts[1].strip()
    if db_ops.set_active_training_plan(name):
        send(f"Plano ativo: <b>{name}</b>.")
    else:
        send(f"Plano nao encontrado ou vazio: <b>{name}</b>.")


def handle_dashboard():
    try:
        dashboard.salvar_dashboard(DASHBOARD_OUTPUT)
        data = dashboard.carregar_dados()
        summary = data["resumo"]
        updated_at = datetime.now().strftime("%d/%m/%Y %H:%M")
        lines = [f"Dashboard atualizado em <b>{updated_at}</b>."]
        if summary["sessoes"]:
            lines.extend(
                [
                    f"Ultima sessao: <b>{summary['ultima_data']}</b>",
                    f"Volume: <b>{summary['ultimo_volume']:,.0f} kg</b>".replace(
                        ",", "."
                    ),
                ]
            )
            if summary["rpe_medio"] is not None:
                lines.append(
                    f"RPE medio geral: <b>{summary['rpe_medio']:.1f}</b>".replace(
                        ".", ","
                    )
                )
        else:
            lines.append("Ainda nao existem sessoes preenchidas.")
        send("\n".join(lines))
    except Exception as exc:
        LOGGER.error("Falha ao atualizar dashboard tipo=%s", type(exc).__name__)
        send("Erro ao atualizar o dashboard. Consulte o terminal.")


def _format_diet_meal(meal, items):
    lines = [f"<b>{escape(meal)}</b>"]
    lines.extend(
        f"• {escape(item['name'])} — {dashboard._fmt_quantidade(item['quantity'], item['unit'])}"
        for item in items
    )
    return "\n".join(lines)


def _format_diet_macro_line(label, key, unit, totals, targets, casas=0):
    total = float(totals.get(key) or 0)
    target = targets.get(key) if targets else None
    formatar = dashboard._fmt_decimal
    if target:
        percentual = total / target * 100
        return (
            f"{label}: <b>{formatar(total, casas)}/{formatar(target, casas)} {unit}</b> "
            f"({formatar(percentual, 0)}%)"
        )
    return f"{label}: <b>{formatar(total, casas)} {unit}</b>"


def handle_diet():
    entries = db_ops.list_diet_entries()
    if not entries:
        send("Nenhum alimento cadastrado na dieta atual.")
        return

    meals = {}
    for entry in entries:
        meals.setdefault(entry["meal"], []).append(entry)

    lines = ["🍖 <b>DIETA ATUAL</b>"]
    for meal, items in meals.items():
        lines.append("")
        lines.append(_format_diet_meal(meal, items))

    totals_and_targets = db_ops.get_diet_totals()
    totals = totals_and_targets["totals"]
    targets = totals_and_targets["targets"] or {}

    lines.append("")
    lines.append(_format_diet_macro_line("Calorias", "calories", "kcal", totals, targets))
    lines.append(_format_diet_macro_line("Proteína", "protein_g", "g", totals, targets))
    lines.append(_format_diet_macro_line("Carboidrato", "carbo_g", "g", totals, targets))
    lines.append(_format_diet_macro_line("Gordura", "fat_g", "g", totals, targets))
    send("\n".join(lines))


def handle_weight(text):
    parts = text.strip().split(maxsplit=1)
    if len(parts) == 2:
        try:
            weight = float(parts[1].strip().replace(",", "."))
            entry = db_ops.add_body_weight(weight)
        except ValueError as exc:
            send(f"{exc}\nUse <code>/peso 118,5</code>.")
            return
        send(
            f"📏 Peso registrado: <b>{_format_body_weight(entry['weight_kg'])} kg</b>."
        )
        return

    history = db_ops.list_body_weights(limit=5)
    if not history:
        send("Nenhum peso registrado. Use <code>/peso 118,5</code>.")
        return

    latest = history[0]
    lines = [
        "📏 <b>Peso corporal</b>",
        f"Atual: <b>{_format_body_weight(latest['weight_kg'])} kg</b>",
        f"Registrado em: {_format_weight_date(latest['recorded_at'])}",
    ]
    if len(history) > 1:
        delta = latest["weight_kg"] - history[1]["weight_kg"]
        signal = "+" if delta > 0 else ""
        lines.append(
            f"Desde a medicao anterior: "
            f"<b>{signal}{_format_body_weight(delta)} kg</b>"
        )
    lines.append("\n<b>Ultimas medicoes</b>")
    lines.extend(
        f"{_format_weight_date(item['recorded_at'])}: "
        f"{_format_body_weight(item['weight_kg'])} kg"
        for item in history
    )
    send("\n".join(lines))


def handle_waist(text):
    parts = text.strip().split(maxsplit=1)
    if len(parts) == 2:
        try:
            circumference = float(parts[1].strip().replace(",", "."))
            entry = db_ops.add_waist_measurement(circumference)
        except ValueError as exc:
            send(f"{exc}\nUse <code>/cintura 110,5</code>.")
            return
        send(
            "📏 Cintura registrada: "
            f"<b>{_format_body_weight(entry['circumference_cm'])} cm</b>."
        )
        return

    history = db_ops.list_waist_measurements(limit=5)
    if not history:
        send("Nenhuma medida de cintura registrada. Use <code>/cintura 110,5</code>.")
        return

    latest = history[0]
    lines = [
        "📏 <b>Circunferencia da cintura</b>",
        f"Atual: <b>{_format_body_weight(latest['circumference_cm'])} cm</b>",
        f"Registrada em: {_format_weight_date(latest['recorded_at'])}",
    ]
    if len(history) > 1:
        delta = latest["circumference_cm"] - history[1]["circumference_cm"]
        signal = "+" if delta > 0 else ""
        lines.append(
            f"Desde a medicao anterior: "
            f"<b>{signal}{_format_body_weight(delta)} cm</b>"
        )
    lines.append("\n<b>Ultimas medicoes</b>")
    lines.extend(
        f"{_format_weight_date(item['recorded_at'])}: "
        f"{_format_body_weight(item['circumference_cm'])} cm"
        for item in history
    )
    send("\n".join(lines))


def handle(text, session):
    text = text.strip()
    exercises = session.get("exercises", [])

    if not exercises or "log_id" not in exercises[0]:
        send("Formato de sessao antigo. Use /gerar para iniciar uma nova sessao de treino.")
        return

    log_ids = [ex["log_id"] for ex in exercises]
    total = len(exercises)
    filled = db_ops.count_filled(log_ids)

    if text.lower() == "/status":
        latest_weight = db_ops.get_latest_body_weight()
        weight_line = (
            f"\nPeso atual: {_format_body_weight(latest_weight['weight_kg'])} kg"
            if latest_weight
            else ""
        )
        if filled >= total:
            send(f"🏁 Treino completo. {total}/{total} ✓{weight_line}", reply_markup=KEYBOARD_START)
        else:
            ex = exercises[filled]
            done = "\n".join(
                f"✓ {_display_exercise_name(exercises[i]['name'])}"
                for i in range(filled)
            )
            msg = f"⚔ Batalha em andamento — {filled}/{total} quests completas\n"
            if done:
                msg += done + "\n"
            msg += weight_line
            send(msg, reply_markup={"remove_keyboard": True})
            send_current_exercise(ex, exercises)
        return

    if text.lower() == "/desfazer":
        if filled == 0:
            send("Nada para desfazer.")
            return
        last_ex = exercises[filled - 1]
        db_ops.update_log_weight(last_ex["log_id"], None, None)
        send(f"↩ Turno desfeito: <b>{_display_exercise_name(last_ex['name'])}</b>", reply_markup={"remove_keyboard": True})
        send_current_exercise(last_ex, exercises)
        return

    if filled >= total:
        send("O treino ja esta completo. Use /status.")
        return

    parts = text.replace(",", ".").split()
    try:
        weight = float(parts[0])
        rpe = int(parts[1]) if len(parts) > 1 else None
    except (ValueError, IndexError):
        send("Formato: <code>80 8</code> (carga + RPE) ou <code>80</code> (somente carga)")
        return

    ex = exercises[filled]
    db_ops.update_log_weight(ex["log_id"], weight, rpe)
    new_filled = filled + 1

    rpe_str = f" RPE {rpe}" if rpe is not None else ""
    send(
        f"<b>{escape(_display_exercise_name(ex['name']))}</b> ✓ {weight}kg{rpe_str} ({new_filled}/{total})"
    )
    if new_filled >= total:
        send_completion(session)
    else:
        nxt = exercises[new_filled]
        send_current_exercise(nxt, exercises)


def main():
    configure_logging()
    if not TOKEN:
        LOGGER.error("TELEGRAM_TOKEN nao encontrado no .env")
        return

    offset = 0
    retry_delay = POLL_RETRY_INITIAL
    LOGGER.info("Bot Limulus em polling. Use Ctrl+C para parar.")

    try:
        while True:
            try:
                updates = get_updates(offset)
                retry_delay = POLL_RETRY_INITIAL
            except TelegramConfigurationError as exc:
                LOGGER.error("Polling encerrado: %s", exc)
                return
            except TelegramTemporaryError as exc:
                LOGGER.warning(
                    "Falha temporaria no polling tipo=%s espera=%ss",
                    exc,
                    retry_delay,
                )
                time.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, POLL_RETRY_MAX)
                continue

            for update in updates:
                offset = update["update_id"] + 1
                if 'callback_query' in update:
                    try:
                        handle_rpe_callback(update['callback_query'])
                    except Exception as exc:
                        LOGGER.error("Falha no clique RPE tipo=%s", type(exc).__name__)
                        send("Não foi possível concluir a ação. Use /status para continuar.")
                    continue
                msg = update.get("message", {})
                chat_id = str(msg.get("chat", {}).get("id", ""))
                text = msg.get("text", "")

                if chat_id != CHAT_ID or not text:
                    continue

                lower = text.strip().lower()
                command = _command_name(text)
                LOGGER.info("Comando recebido comando=%s", command)

                if lower == "/ajuda":
                    send(
                        "📜 <b>Menu do Limulus</b>\n\n"
                        "/gerar — inicia ou retoma o treino\n"
                        "/prever — mostra uma previa sem salvar\n"
                        "/treinob — mostra o treino B de garagem\n"
                        "/exercicios — lista os exercicios atuais\n"
                        "/aquecimento — mostra o aquecimento\n"
                        "/volume — volume por grupo muscular\n"
                        "/dashboard — atualiza o dashboard local\n"
                        "/dieta — mostra a dieta atual e as metas\n"
                        "/planos — lista planos de treino\n"
                        "/plano NOME — seleciona o plano ativo\n"
                        "/peso VALOR — registra o peso corporal\n"
                        "/peso — mostra o peso atual e o historico\n"
                        "/cintura VALOR — registra a circunferencia em cm\n"
                        "/cintura — mostra a cintura atual e o historico\n"
                        "/status — exercicio atual e progresso\n"
                        "/desfazer — apaga o ultimo registro\n"
                        "/ajuda — esta mensagem\n\n"
                        "<b>Jogo</b>\n"
                        "/menu — menu do herói em botões\n"
                        "/perfil — ficha: nivel, classe, atributos e ouro\n"
                        "/chefes — chefes de cada movimento e o HP restante\n"
                        "/semana — mapa da semana e missões\n"
                        "/missoes — missões da semana\n"
                        "/conquistas — conquistas desbloqueadas\n"
                        "/diario — diário de aventura\n"
                        "/loja — loja; <code>/loja coringa</code> compra\n"
                        "/pausa N — pausa de N dias; <code>/pausa fim</code> volta\n"
                        "/app — abre a ficha completa no app\n\n"
                        "<b>Registrar treino:</b> toque no RPE abaixo do exercício.\n"
                        "O botão usa a carga total indicada.\n\n"
                        "<b>Registro manual, se necessário:</b>\n"
                        "<code>80</code> — somente carga\n"
                        "<code>80 8</code> — carga + RPE"
                    )
                    if load_session() is None:
                        send("Toque abaixo para iniciar.", reply_markup=KEYBOARD_START)
                    continue

                comandos_jogo = {
                    "/perfil": handle_profile,
                    "/chefes": handle_bosses,
                    "/semana": handle_week,
                    "/menu": handle_menu,
                    "/app": handle_app,
                    "/missoes": lambda: send(jogo.formatar_missoes(jogo.estado_atual())),
                    "/conquistas": lambda: send(jogo.formatar_conquistas(jogo.estado_atual())),
                    "/diario": lambda: send(jogo.formatar_diario(jogo.estado_atual())),
                }
                acao_jogo = comandos_jogo.get(lower)
                if acao_jogo is None and command in {"/loja", "/pausa"}:
                    acao_jogo = (handle_shop if command == "/loja" else handle_pause)
                    acao_jogo = (lambda f=acao_jogo: f(text))
                if acao_jogo is not None:
                    try:
                        acao_jogo()
                    except Exception as exc:
                        LOGGER.error("Falha no comando do jogo comando=%s tipo=%s", command, type(exc).__name__)
                        send("Não foi possível concluir o comando do jogo. Consulte o terminal.")
                    continue

                if lower == "/exercicios":
                    handle_exercises()
                    continue

                if lower == "/volume":
                    handle_volume()
                    continue

                if lower == "/dashboard":
                    handle_dashboard()
                    continue

                if lower == "/planos":
                    handle_plans()
                    continue

                if lower == "/plano" or lower.startswith("/plano "):
                    handle_select_plan(text)
                    continue

                if lower == "/peso" or lower.startswith("/peso "):
                    handle_weight(text)
                    continue

                if lower == "/cintura" or lower.startswith("/cintura "):
                    handle_waist(text)
                    continue

                if lower == "/aquecimento":
                    send(
                        "<b>Aquecimento</b>\n\n"
                        "5 minutos, sem transformar em outro treino:\n\n"
                        "1. Marcha rapida ou polichinelo leve — 60s\n"
                        "2. Circulos de braco e abrir/fechar bracos — 30s\n"
                        "3. Rotacao de tronco — 30s\n"
                        "4. Agachamento livre — 1x10\n"
                        "5. Afundo alternado ou passada para tras — 1x6 por perna\n"
                        "6. Bom dia sem peso ou com barra vazia — 1x10\n"
                        "7. Flexao facil — 1x5-8\n"
                        "8. Prancha com toque no ombro — 10 toques"
                    )
                    continue

                if lower in {"/gerar", TECLADO_TREINO.lower()}:
                    try:
                        handle_generate()
                    except Exception as exc:
                        LOGGER.error("Falha ao iniciar treino tipo=%s", type(exc).__name__)
                        send("Não foi possível iniciar ou retomar o treino. Use /status para conferir a sessão.")
                    continue

                if lower == "/prever":
                    handle_preview()
                    continue

                if lower == "/treinob":
                    handle_training_b()
                    continue

                if lower in {"/dieta", TECLADO_DIETA.lower()}:
                    try:
                        handle_diet()
                    except Exception as exc:
                        LOGGER.error("Falha ao mostrar dieta tipo=%s", type(exc).__name__)
                        send("Não foi possível mostrar a dieta. Consulte o terminal.")
                    continue

                if not _is_session_input(text):
                    try:
                        sem_sessao = load_session() is None
                    except Exception:
                        sem_sessao = False
                    send(
                        "Comando invalido. Use /ajuda.",
                        reply_markup=KEYBOARD_START if sem_sessao else None,
                    )
                    continue

                try:
                    session = load_session()
                except Exception as exc:
                    LOGGER.error(
                        "Falha ao carregar sessao comando=%s tipo=%s",
                        command,
                        type(exc).__name__,
                    )
                    send("Erro ao carregar a sessao. Consulte o terminal.")
                    continue
                if session is None:
                    LOGGER.info("Comando sem sessao ativa comando=%s", command)
                    send("Nenhuma sessão ativa. Toque em ⚔ Iniciar treino.", reply_markup=KEYBOARD_START)
                    continue

                LOGGER.info(
                    "Comando associado a sessao comando=%s session_id=%s",
                    command,
                    session.get("session_id"),
                )
                try:
                    handle(text, session)
                except Exception as exc:
                    LOGGER.error(
                        "Falha ao processar comando=%s session_id=%s tipo=%s",
                        command,
                        session.get("session_id"),
                        type(exc).__name__,
                    )
                    send("Erro ao processar o comando. Consulte o terminal.")
    except KeyboardInterrupt:
        LOGGER.info("Bot encerrado pelo usuario.")


if __name__ == "__main__":
    main()
