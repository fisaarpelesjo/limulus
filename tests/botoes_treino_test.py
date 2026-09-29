"""Fluxo por botões com SQLite temporário e Telegram simulado."""

import json
import gc
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from limulus import db_ops, ods_ops, telegram_poller as bot


def main():
    messages = []
    actions = []
    with tempfile.TemporaryDirectory(prefix="limulus-botoes-") as directory:
        root = Path(directory)
        with patch.object(db_ops, 'DB_PATH', root / 'teste.db'), \
             patch.object(db_ops, 'DATA_DIR', root), \
             patch.object(ods_ops, 'SESSION_FILE', root / 'session.json'), \
             patch.object(bot, 'SESSION_FILE', root / 'session.json'), \
             patch.object(bot, 'send', lambda text, **kw: messages.append((text, kw)) or True), \
             patch.object(bot, 'telegram_action', lambda method, payload: actions.append((method, payload)) or True):
            # Banco da versão anterior: migrar sem inventar horários históricos.
            with patch.object(db_ops, 'SCHEMA_VERSION', 12):
                db_ops.init_db()
                with db_ops._connect() as conn:
                    conn.execute("INSERT INTO training_sessions (date, training_type) VALUES ('2020-01-01', 'TREINO')")
                conn.close()
            db_ops.init_db()
            assert db_ops.get_schema_version() == 14
            nomes = {p['name']: p for p in db_ops.list_training_plans()}
            assert {'A', 'B'} <= set(nomes) and nomes['A']['active']
            assert db_ops.get_session_timing(1) == {'started_at': None, 'completed_at': None}
            # Concluir A ativa B, e concluir B volta para A.
            for plano in ('A', 'B'):
                assert db_ops.get_active_training_plan()['name'] == plano
                previous, previous_id = ods_ops.generate_training()
                for ex in previous:
                    db_ops.update_log_weight(ex['log_id'], 80, 8)
            assert db_ops.get_active_training_plan()['name'] == 'A'

            bot.handle_generate()
            assert len(messages) == 2
            assert messages[0][1]['reply_markup']['remove_keyboard']
            assert 'Horário:' in messages[0][0] and 'Brasília' in messages[0][0]
            assert 'Treino de hoje' not in messages[0][0]
            text, kwargs = messages[-1]
            assert '<b>AGACHAMENTO COM BARRA NAS COSTAS</b>\n\n' in text
            assert '1ª série: <b>54 kg</b> anilhas\n2ª série: <b>62 kg</b> anilhas\n3ª série: <b>71 kg</b> anilhas' in text
            assert 'Repetições: <b>8</b>' in text
            assert '<i>Barra: 2,20 m · 11 kg</i>' in text
            assert '<i>Total com barra: 65 · 73 · 82 kg</i>' in text
            keyboard = kwargs['reply_markup']['inline_keyboard'][0]
            assert [item['text'] for item in keyboard] == ['RPE ≤7', 'RPE 8', 'RPE 9', 'RPE ≥10']
            session = json.loads(bot.SESSION_FILE.read_text(encoding='utf-8'))
            ids = [ex['log_id'] for ex in session['exercises']]
            initial_id = session['session_id']
            bot.handle_generate()
            assert json.loads(bot.SESSION_FILE.read_text())['session_id'] == initial_id

            def click(data, sender=bot.CHAT_ID):
                bot.handle_rpe_callback({
                    'id': 'consulta', 'from': {'id': sender}, 'data': data,
                    'message': {'chat': {'id': bot.CHAT_ID}, 'message_id': 123},
                })

            first = keyboard[1]['callback_data']
            click(first, 'outro-usuario')
            assert db_ops.count_filled(ids) == 0
            future = db_ops.criar_botoes_rpe(ids[1], 82)
            click(f'rpe:{future}:8')
            assert db_ops.count_filled(ids) == 0
            click(first.replace(':8', ':11'))
            assert db_ops.count_filled(ids) == 0
            bot.SESSION_FILE.unlink()
            click(first)
            assert db_ops.count_filled(ids) == 1
            assert actions[-1][0] == 'editMessageText'
            assert actions[-1][1]['reply_markup'] == {'inline_keyboard': []}
            click(first)
            assert db_ops.count_filled(ids) == 1
            bot.handle('/desfazer', bot.load_session())
            click(first)
            assert db_ops.count_filled(ids) == 0

            for index in range(len(ids)):
                data = messages[-1][1]['reply_markup']['inline_keyboard'][0][1]['callback_data']
                click(data)
                assert db_ops.count_filled(ids) == index + 1
            assert 'TREINO CONCLUÍDO' in messages[-1][0]
            assert 'Duração:' in messages[-1][0]
            assert 'RPE médio: <b>8,0</b>' in messages[-1][0]
            assert 'Comparação com o treino anterior' in messages[-1][0]
            assert messages[-1][1]['reply_markup'] == bot.KEYBOARD_START
            timing = db_ops.get_session_timing(initial_id)
            assert timing['started_at'].endswith('-03:00') and timing['completed_at']
            click(data)
            assert db_ops.count_filled(ids) == len(ids)
            assert bot.load_session() is None
            bot.handle_generate()
            new_session = bot.load_session()
            assert new_session['session_id'] != initial_id
            click(first)
            assert db_ops.count_filled([ex['log_id'] for ex in new_session['exercises']]) == 0
        gc.collect()
    print('Teste de botões, migração, recuperação e cliques duplicados passou.')


if __name__ == '__main__':
    main()
