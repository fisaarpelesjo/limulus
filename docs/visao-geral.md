# Visao Geral Do Sistema

O Limulus e um diario de treino controlado pelo Telegram.

Responsabilidades principais:

1. manter o SQLite versionado em `data/limulus.db`
2. rodar um bot Telegram com long polling
3. guardar a sessao ativa em `session.json`
4. gerar um dashboard HTML local com a evolucao do volume de treino
5. extrair frames de videos locais para analise de execucao

## Fluxo Principal

```text
Usuario envia /gerar
  -> bot cria uma sessao no SQLite
  -> bot cria um log por exercicio ativo
  -> bot escreve session.json
  -> bot envia o exercicio atual com a carga de cada serie e descanso

Usuario conclui o ultimo exercicio de uma sessao de um plano de A a E
  -> bot envia o resumo
  -> o plano seguinte da sequencia (A, B, C, D, E e volta para A) passa a ser o ativo

Usuario envia /prever
  -> bot monta o treino em texto com alvo e descanso
  -> bot nao cria sessao, logs nem session.json

Usuario envia 80 ou 80 8
  -> bot carrega session.json
  -> bot conta logs preenchidos
  -> bot atualiza o proximo exercicio pendente
  -> bot responde com progresso

Usuario envia /desfazer
  -> bot encontra o ultimo log preenchido
  -> bot limpa carga e RPE

Usuario roda python gerar_dashboard.py
  -> dashboard le training_sessions e training_logs
  -> calcula volume = series x repeticoes x carga
  -> consolida carga, RPE, 1RM estimado, PRs, grupos musculares e periodos
  -> cruza volume x RPE, carga x RPE e ultima sessao contra media recente
  -> renderiza graficos de dados com Chart.js, mantendo o mapa anatomico em SVG
  -> organiza as secoes em pagina unica com layout escuro usando Carbon Web
     Components oficiais e adiciona filtros rapidos
  -> escreve temp/dashboard-treino.html

Usuario roda python gerar_frames.py --todos --instalar-ffmpeg
  -> launcher verifica e instala ffmpeg quando necessario
  -> localiza todos os videos em videos/entrada/
  -> modulo chama ffmpeg sem interacao
  -> cria uma pasta por video em videos/saida/
  -> informa a quantidade de frames gerada
```

## Entry Points

```bash
python start_bot.py
python gerar_dashboard.py
python gerar_frames.py --todos --instalar-ffmpeg
```

No Windows:

```bat
start_bot.bat
```

## Arquivos Principais

`start_bot.py`: launcher multiplataforma.

`gerar_dashboard.py`: gera `temp/dashboard-treino.html`.

`gerar_frames.py`: extrai frames de videos locais usando `ffmpeg`.

`limulus/telegram_poller.py`: comandos, polling e mensagens Telegram.

`limulus/ods_ops.py`: gera sessoes e escreve `session.json`.

`limulus/video_ops.py`: valida e executa a extracao de frames.

`limulus/dashboard.py`: consolida logs de treino e renderiza HTML local.

`limulus/db_ops.py`: acesso SQLite.

`tests/`: testes locais.

## Fonte Da Verdade

SQLite e a fonte da verdade para exercicios e logs.

`session.json` nao e fonte da verdade; ele so guarda o contexto da sessao ativa.
Ao carregar o estado, o bot valida os IDs contra o SQLite. Se o arquivo estiver
ausente, corrompido ou antigo, ele reconstrui a sessao mais recente com logs
pendentes. Uma sessao completa nao e recuperada como ativa.

## Catalogo Atual

Cinco planos, de segunda a sexta, com cerca de 32-37 min cada e foco em
emagrecimento e definicao. Eles alternam automaticamente em sequencia ao
concluir cada sessao. O agachamento e o Zercher, sem barra atras da nuca:

```text
Plano A (segunda, empurrar)
1. Supino reto (barra)                      3x12
2. Supino inclinado (barra)                 3x12
3. Desenvolvimento (barra em pé)            3x12
4. Elevação lateral                         4x15
5. Tríceps testa                            3x15

Plano B (terca, puxar)
1. Remada curvada (barra)                   3x12
2. Remada curvada alta no peito (barra)     3x15
3. Pullover (barra)                         3x15
4. Rosca direta                             3x15
5. Rosca inversa (barra)                    3x15

Plano C (quarta, inferior)
1. Agachamento Zercher                      3x12
2. Levantamento Terra Romeno                3x12
3. Agachamento sumô com barra à frente      3x12
4. Rosca de punho atrás das costas (barra)  3x15

Plano D (quinta, empurrar)
1. Supino inclinado (barra)                 3x12
2. Supino reto (barra)                      3x12
3. Desenvolvimento (barra em pé)            3x12
4. Elevação lateral                         4x15
5. Tríceps testa                            3x15

Plano E (sexta, puxar)
1. Remada apoiada no banco (barras 40 cm)    3x12
2. Pullover (barra)                         3x15
3. Levantamento Terra Romeno                3x12
4. Crucifixo invertido apoiado (barras 40 cm)  3x15
5. Rosca direta                             3x15
```

Cada exercicio usa piramide crescente (80% -> 90% -> 100% do alvo); o RPE vale
para a ultima serie. O antigo plano de forca, com 11 exercicios, virou o plano
`Forca`, inativo e selecionavel com `/plano Forca`. `Supino fechado (barra)` e
`Remada alta (barra)` estao inativos; historico antigo permanece como historico.

## Idioma

A interface principal deve ser em PT-BR:

- comandos principais do Telegram
- mensagens do bot
- docs de uso
- mensagens de launcher

Comandos textuais do Telegram exigem `/` e usam somente os nomes oficiais em
PT-BR.
