# Arquitetura

O Limulus e um pacote Python pequeno com entry points de script. A ideia e
manter tudo simples: Python, SQLite e API HTTP do Telegram.

## Estrutura

```text
.
├── start_bot.py
├── start_bot.bat
├── gerar_frames.py
├── gerenciar_dados.py
├── videos/
│   ├── entrada/
│   └── saida/
├── data/
│   └── limulus.db
├── docs/
│   └── app/index.html        # Mini App do jogo (GitHub Pages)
├── limulus/
│   ├── __init__.py
│   ├── backup_ops.py
│   ├── dashboard.py
│   ├── db_ops.py
│   ├── jogo.py
│   ├── jogo_sprites.py
│   ├── jogo_visual.py
│   ├── ods_ops.py
│   ├── telegram_poller.py
│   └── video_ops.py
└── tests/
    ├── backup_export_test.py
    ├── app_test.py
    ├── dashboard_test.py
    ├── jogo_test.py
    ├── jogo_visual_test.py
    ├── regras_treino_test.py
    ├── smoke_test.py
    ├── telegram_falhas_test.py
    ├── video_ops_test.py
    └── e2e_training_flow_test.py
```

## Regra De Imports

Codigo de aplicacao deve ser importado pelo pacote:

```python
from limulus import db_ops
from limulus import ods_ops
from limulus import telegram_poller
```

Evite novos modulos de aplicacao na raiz. A raiz deve ficar para launchers,
configuracao, docs e testes.

## Direcao De Dependencias

```text
start_bot.py
  -> limulus.telegram_poller
       -> limulus.ods_ops
       -> limulus.db_ops
       -> limulus.jogo
            -> limulus.db_ops
       -> limulus.jogo_visual (Pillow, carregado sob demanda)
            -> limulus.jogo
            -> limulus.jogo_sprites
  -> limulus.ods_ops
       -> limulus.db_ops

gerar_dashboard.py
  -> limulus.dashboard
       -> SQLite
       -> limulus.jogo (secao "Ficha do personagem")

gerenciar_dados.py
  -> limulus.backup_ops
       -> SQLite

gerar_frames.py
  -> limulus.video_ops
       -> ffmpeg
```

`db_ops.py` fica na base e nao deve importar a camada do bot. `jogo.py` so
depende de `db_ops`; `jogo_visual.py` e importado pelo bot apenas quando precisa
gerar uma imagem, e sem Pillow o jogo segue so em texto.

`db_ops.init_db()` tambem controla a evolucao do esquema. Cada migracao e
aplicada em ordem e registrada em `schema_migrations`; um banco com versao mais
nova que o codigo e rejeitado para evitar alteracoes incompativeis.

## Inicializacao

`python start_bot.py`:

1. importa o poller Telegram
2. chama `telegram_poller.main()`

A saida de terminal do launcher deve ser minimalista. O bot registra apenas logs
operacionais e erros uteis para diagnostico.

## Polling

O bot usa long polling. Isso significa:

- nao precisa de servidor publico
- nao precisa abrir porta
- precisa apenas de internet de saida
- chama `getUpdates` periodicamente

O Mini App do jogo (`docs/app/index.html`) e uma pagina estatica publicada pelo
GitHub Pages; o bot so envia o link com o estado no fragmento `#d=`, entao
continua sem servidor proprio.

Falhas temporarias de rede usam espera gradual de 3 ate 60 segundos. Erros
permanentes de token encerram o polling. Os logs registram horario, nivel,
comando e `session_id`, mas nunca devem incluir token ou URL completa da API.

## Estado Local

Versionado:

- codigo
- docs
- testes
- `requirements.txt`
- `data/limulus.db`

Nao versionado:

- `.env`
- `session.json`
- `pending_log.csv`
- `temp/`
- `backups/`
- `exportacoes/`
- `data/*.db-shm`
- `data/*.db-wal`
- `__pycache__/`
- `videos/`

## Por Que `session.json` Existe

O banco guarda o historico duravel. `session.json` so aponta qual sessao esta
ativa e quais `log_id` devem receber as proximas cargas.

O arquivo funciona como cache recuperavel. O carregamento valida `session_id` e
`log_id` no SQLite; quando o cache esta ausente, corrompido ou antigo,
`ods_ops.recover_active_session()` reconstrui a sessao mais recente com logs
pendentes. Sessoes completas nao sao reabertas.

## Por Que O Pacote Chama `limulus`

O app se chama Limulus no README e no banco `limulus.db`.
`limulus` tambem e um nome valido e limpo para pacote Python.

## O Que Evitar

Nao:

- tirar exercicios do SQLite para voltar a ODS
- versionar `.env`
- versionar `session.json`
- versionar sidecars SQLite
- recriar wrappers na raiz sem necessidade
- voltar a interface principal para ingles
- criar servidor web para Telegram sem motivo claro
- fazer teste mutar o banco real sem isolamento
