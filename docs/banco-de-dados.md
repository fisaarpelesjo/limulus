# Banco De Dados

O Limulus usa SQLite.

Arquivo principal:

```text
data/limulus.db
```

Esse banco e versionado e e a fonte da verdade para exercicios, sessoes, logs e
dados de dieta.

## Versao E Migracoes

O esquema atual usa `SCHEMA_VERSION = 15`. A tabela `schema_migrations` registra
uma linha por versao aplicada, com data e hora.

`db_ops.init_db()`:

1. le a maior versao registrada
2. rejeita bancos mais novos que o codigo
3. aplica cada migracao pendente em ordem
4. registra a versao somente depois de concluir suas operacoes

A versao 1 cria as tabelas principais. A versao 2 adiciona indices para localizar
logs pendentes por sessao e historico por exercicio. A versao 3 cria
`exercise_muscle_groups`. A versao 4 cria planos de treino, a versao 5 inclui
o agachamento sumô com barra à frente no catalogo e no plano ativo, a versao 6
cria o historico de peso corporal, a versao 7 cria o historico de
circunferencia da cintura, a versao 8 cria o perfil corporal usado pelos
indicadores derivados do dashboard, a versao 9 adiciona vitamina B6 aos
alimentos e metas de dieta e a versao 10 troca o primeiro exercicio ativo de
`Agachamento Zercher` para `Agachamento com barra nas costas`. As migracoes usam
`IF NOT EXISTS`, portanto tambem reconhecem bancos antigos que ja possuam as
tabelas, mas ainda nao tenham `schema_migrations`.

Antes de criar uma nova migracao, fazer backup do banco e adicionar um teste que
parta da versao anterior.

## Backup, Exportacao E Restauracao

A migracao 13 adiciona `started_at` e `completed_at` a `training_sessions`
(ISO 8601 com UTC-03:00) e a tabela `training_buttons` (`token`, `log_id`,
`weight`, `active`). Os horarios historicos permanecem nulos. O token guarda
a carga exibida e e consumido numa transacao que valida sessao, ordem e
registro pendente. `/desfazer` invalida os tokens do log e limpa o fim da
sessao. A exportacao JSON inclui a nova tabela. O banco vivo so deve ser
migrado apos backup; os testes usam bancos temporarios.

A migracao 14 renomeia o plano antigo `A` (11 exercicios, foco em forca) para
`Forca`, que fica inativo, e cria os planos `A` e `B` de hipertrofia e
emagrecimento, deixando `A` ativo. Nao cria tabelas nem colunas.

O launcher local usa a API de backup do SQLite, sem copiar o arquivo enquanto
uma transacao pode estar incompleta:

```bash
python gerenciar_dados.py backup
python gerenciar_dados.py exportar
```

O backup gera um arquivo `.db` validado em `backups/`. A exportacao gera JSON em
`exportacoes/` com a versao do esquema e o conteudo das tabelas conhecidas.

Para restaurar:

```bash
python gerenciar_dados.py restaurar backups/arquivo.db --confirmar
```

Pare o bot antes da restauracao. O arquivo de origem passa por
`PRAGMA integrity_check`; se o banco atual existir, um backup de seguranca e
criado antes da substituicao.

## Modulo SQLite

Todo acesso direto ao banco fica em:

```text
limulus/db_ops.py
```

`DB_PATH` aponta para `data/limulus.db` na raiz do repositorio.

## Tabelas

### `exercises`

Catalogo de exercicios.

```text
id          INTEGER PRIMARY KEY AUTOINCREMENT
name        TEXT NOT NULL UNIQUE
sets        INTEGER NOT NULL
reps        INTEGER NOT NULL
sort_order  INTEGER NOT NULL UNIQUE
active      INTEGER NOT NULL DEFAULT 1
```

### `exercise_muscle_groups`

Classificacao muscular compartilhada pelo bot e dashboard.

```text
id             INTEGER PRIMARY KEY AUTOINCREMENT
exercise_name  TEXT NOT NULL
muscle_group   TEXT NOT NULL
role           TEXT NOT NULL (`principal` ou `secundario`)
sort_order     INTEGER NOT NULL
```

Os grupos dos exercicios atuais e aliases historicos sao inseridos de forma
idempotente por `init_db()`. Exercicios sem classificacao aparecem como
`Outros`, mas nenhum exercicio ativo deve permanecer nesse estado.

### `training_plans`

Modelos de treino cadastrados. Apenas um plano fica ativo por vez.

```text
id          INTEGER PRIMARY KEY AUTOINCREMENT
name        TEXT NOT NULL UNIQUE
active      INTEGER NOT NULL
sort_order  INTEGER NOT NULL
```

### `training_plan_exercises`

Sequencia, series e repeticoes de cada plano.

```text
id             INTEGER PRIMARY KEY AUTOINCREMENT
plan_id        INTEGER NOT NULL
exercise_name  TEXT NOT NULL
sets           INTEGER NOT NULL
reps           INTEGER NOT NULL
sort_order     INTEGER NOT NULL
```

Desde a versao 14 existem os planos `A`, `B` e `Forca`. Outros planos podem
ser cadastrados com `db_ops.replace_training_plan()`. O bot seleciona com
`/plano NOME`.

Rotacao automatica: quando o ultimo log de uma sessao e registrado e o
`training_type` da sessao e o plano ativo `A` ou `B`, `db_ops._alternar_plano()`
ativa o outro (`PLAN_ROTATION = {"A": "B", "B": "A"}`). Sessoes de outros
planos, como `Forca`, nao alternam o plano ativo.

### `training_sessions`

Uma linha por sessao gerada.

```text
id             INTEGER PRIMARY KEY AUTOINCREMENT
date           TEXT NOT NULL
training_type  TEXT NOT NULL DEFAULT 'TREINO'
```

### `training_logs`

Uma linha por exercicio dentro de uma sessao.

```text
id             INTEGER PRIMARY KEY AUTOINCREMENT
session_id     INTEGER NOT NULL REFERENCES training_sessions(id)
exercise_name  TEXT NOT NULL
sets           INTEGER NOT NULL
reps           INTEGER NOT NULL
weight         REAL
rpe            REAL
sort_order     INTEGER NOT NULL DEFAULT 0
```

`weight` e `rpe` comecam como `NULL`. A entrada `80 8` preenche a proxima linha
pendente da sessao ativa.

O dashboard local considera apenas linhas com `weight IS NOT NULL` e calcula o
volume de treino de cada linha assim:

```text
volume = sets x reps x weight
```

Com a piramide crescente, `weight` e a carga de topo, entao esse volume fica
superestimado em cerca de 10% nas sessoes novas.

`python gerar_dashboard.py` consolida esse volume por sessao, exercicio, semana
e grupo muscular. O HTML exibe uma pagina unica rolavel com indicadores de resumo,
treino ativo do plano selecionado, grafico de evolucao, mapa muscular, carga e RPE e 1RM estimado por exercicio,
comparacao da ultima sessao com a anterior, equilibrio muscular, calendario de
carga, grupos musculares, volume semanal, maiores evolucoes, recordes pessoais,
PRs expandidos, carga vs RPE, alertas simples, filtros rapidos por segmento,
relatorio semanal e a dieta atual no final da pagina.

A secao de dieta usa `diet_entries`, `foods` e `diet_targets`. Uma tabela unica
consolida alimentos repetidos, somando quantidades, calorias, macros e
micronutrientes. O resumo mostra calorias e macros na primeira linha de cards e
micros em uma segunda linha; a tabela mostra fibra, omega 3, potassio, magnesio,
zinco e vitaminas D e B6 por alimento e no total. O resumo compara os totais
diarios com as metas cadastradas quando elas existem.

O mapa muscular usa a classificacao de `exercise_muscle_groups` e soma o volume
dos exercicios da ultima sessao para cada grupo associado. No dashboard, grupos
amplos como peitoral, dorsais, trapezio, biceps, triceps, antebraco, core,
quadriceps, adutores, gluteos e posteriores sao distribuidos em segmentos anatomicos
visuais para o desenho e a legenda lateral. Quando houver regra especifica para
o exercicio, o dashboard usa pesos por segmento em vez de dividir o grupo
igualmente. A opacidade vermelha e normalizada pelo segmento de maior volume
daquele treino; uma regiao sem volume fica transparente. O desenho
representa volume atribuido pelo catalogo, nao ativacao muscular medida,
recrutamento por EMG ou estimativa de hipertrofia.
As regioes musculares sao renderizadas diretamente dos paths vetoriais de
`body-muscles`, de Ivan Vulovic, sob Apache-2.0, numa SVG unica por vista.
Os SVGs anatomicos de Termininja (CC BY-SA 3.0) ficam preservados em
`limulus/assets/`. Os ativos e os textos das licencas ficam em
`docs/licencas/`.

Os alertas consideram RPE 9 uma fase valida de consolidacao. O dashboard destaca
queda de RPE com a mesma carga como evolucao, acompanha RPE 10 persistente e
explica reducoes de carga feitas depois de RPE 10. Alertas por exercicio usam
somente exercicios do plano ativo atual; historico de exercicios inativos
continua aparecendo em graficos e PRs, mas nao gera alerta. `Maiores evolucoes`
tambem considera apenas exercicios do plano ativo atual.

### Dieta

Tambem existem:

- `foods`
- `diet_targets`
- `diet_entries`

Essas tabelas guardam alimentos, metas e entradas de dieta.

### Peso Corporal

`body_weights` guarda cada medicao sem sobrescrever o historico:

- `weight_kg`: peso entre 30 e 400 kg
- `recorded_at`: data e horario do registro
- `source`: origem da medicao, como `telegram`

O indice `idx_body_weights_recorded_at` acelera a consulta do peso mais recente.

### Circunferencia Da Cintura

`waist_measurements` guarda cada medicao sem sobrescrever o historico:

- `circumference_cm`: circunferencia entre 40 e 250 cm
- `recorded_at`: data e horario do registro
- `source`: origem da medicao, como `telegram`

O indice `idx_waist_measurements_recorded_at` acelera a consulta da medida mais
recente.

`body_profile` guarda um unico registro com `height_cm`, `age_years` e
`updated_at`. O dashboard combina a altura com o peso mais recente para
calcular o IMC e com a cintura mais recente para calcular a relacao
cintura/altura. Esses valores sao indicadores derivados e nao diagnosticos.

## Catalogo Atual

Planos do schema 15, divisao de segunda a sexta com cerca de 32-37 min por
sessao, foco em emagrecimento e definicao. Rotacao automatica A, B, C, D, E e
volta para A ao concluir cada sessao:

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

Cada exercicio usa as mesmas series e repeticoes em todos os dias em que
aparece, para a progressao por RPE nao ser trocada pela conversao por
repeticoes.

O plano `Forca` guarda a sequencia antiga de 11 exercicios (agachamento 3x5,
sumô 3x10, supino reto 3x5, back-off 3x8, supino inclinado 3x8, remada curvada
3x8, remada alta no peito 3x10, desenvolvimento 3x5, terra romeno 3x8, rosca
inversa 3x8 e rosca de punho 3x12). Fica inativo e pode ser selecionado com
`/plano Forca`.

O agachamento dos planos A a E e o Zercher (barra na dobra dos cotovelos);
`Agachamento com barra nas costas` so aparece no plano `Forca` e no historico.
Logs antigos de `Agachamento Zercher` voltam a alimentar a progressao.
`Supino fechado (barra)` e `Remada alta (barra)` estao inativos para sessoes
futuras. Historico antigo de `Rosca direta`, `Rosca martelo (barra H)`, `Supino
fechado (barra)` e `Remada alta (barra)` permanece como historico salvo no
SQLite.

Ao mudar o catalogo para frente, atualize:

- `data/limulus.db`
- `limulus/db_ops.py`, em `DEFAULT_EXERCISES` (plano A) ou `WEEKLY_PLANS`
  (planos A a E)

## Criacao De Sessao

```text
ods_ops.generate_training()
  -> ods_ops.read_exercises()
     -> db_ops.get_or_seed_exercises()
  -> le a sequencia do plano ativo em training_plan_exercises
  -> db_ops.create_session(today)
  -> db_ops.log_exercise(...) para cada exercicio
```

`session.json` guarda `session_id` e `log_id` para o bot saber qual linha
atualizar quando o usuario envia carga. Ele tambem guarda `target_weight`, que
e a carga alvo calculada para a sessao atual, e `rest_interval`, que e o
descanso sugerido entre series. Quando o exercicio usa equipamento de peso fixo,
tambem pode guardar `loading_note`, uma observacao de montagem da carga para o
bot mostrar no exercicio atual/proximo.

O SQLite tambem permite recuperar esse contexto. A consulta procura a sessao
mais recente que possui logs e pelo menos um `weight IS NULL`, preserva a ordem
por `sort_order` e reconstrui os alvos usando o desempenho anterior a cada log.
Sessoes sem pendencias nao sao consideradas ativas.

## Progressao De Carga

`db_ops.get_last_performance()` busca a ultima carga valida, o RPE e as reps
mais recentes por exercicio. Durante `ods_ops.generate_training()`, cada exercicio recebe um
`target_weight` calculado assim:

```text
RPE 7 ou menor  -> ultima carga + 2 kg
RPE 8           -> ultima carga + 2 kg
RPE 9           -> ultima carga
RPE 10 ou maior -> ultima carga - 2 kg
Sem RPE         -> ultima carga
```

RPE 9 mantem `target_weight` de forma intencional. Essa fase permite consolidar
tecnica, amplitude, controle e qualidade das repeticoes com a carga atual; ela
nao deve ser classificada automaticamente como estagnacao. Quando a mesma carga
for registrada como RPE 8 ou menor, `suggest_next_weight()` aplica o aumento
correspondente.

Analises derivadas do banco devem interpretar uma sequencia de RPE 9 junto com
a qualidade da execucao. Sem dados de tecnica, repeticoes incompletas ou
amplitude, o valor isolado nao comprova falta de evolucao.

Conversao por repeticoes: se as reps do ultimo log do exercicio diferem das reps
do plano, `suggest_next_weight()` converte a carga pelo 1RM estimado (Epley:
`1RM = peso x (1 + reps/30)`) e arredonda para baixo em anilhas de 2 kg acima
da barra, ignorando o delta de RPE nessa sessao. Exemplo: 61 kg x5 vira 49 kg
para 3x12.

Retorno apos pausa: se o exercicio esta parado ha 10 dias ou mais
(`RETURN_AFTER_DAYS`), o alvo volta com a ultima carga menos 4 kg
(`RETURN_REDUCTION_KG`), sem somar a progressao por RPE e sem ficar abaixo da
barra. Com 21 dias ou mais (`RETURN_LONG_AFTER_DAYS`), o alvo vira 80%
(`RETURN_LONG_FACTOR`) da ultima carga, arredondado para baixo em anilhas.
Exemplo: 61 kg x5 parado ha 35 dias vira 39 kg para 3x12. Se as reps mudaram,
a conversao vem antes. Na sessao seguinte a progressao por RPE volta ao normal.

Piramide crescente: `ods_ops.get_set_weights()` divide o alvo em 80% -> 90% ->
100%, com as series intermediarias arredondadas para baixo em anilhas. A ultima
serie e a serie de topo; o RPE registrado se refere a ela e
`training_logs.weight` grava a carga de topo. A carga de cada serie nao e
persistida.

Se nao houver historico de carga para o exercicio, `target_weight` fica `None` e
a tabela do bot mostra `-`.

Na `Elevação lateral`, o equipamento tem `per_hand`: sao duas barras ocas de
40 cm (peso 0), uma em cada mao, e a carga registrada e por mao, com alvo
inicial de 4 kg por mao. A observacao fica `barra de 40 cm em cada mao + Xkg de
anilhas por mao`. `Remada apoiada no banco (barras 40 cm)` (alvo inicial 14 kg
por mao) e `Crucifixo invertido apoiado (barras 40 cm)` (alvo inicial 4 kg por
mao) usam o mesmo equipamento `per_hand`.

Excecoes atuais: `Rosca inversa (barra)` recebe alvo inicial de 11 kg e
`Supino inclinado (barra)` recebe alvo inicial de 41 kg quando ainda nao houver
historico proprio. Depois do primeiro registro real, a funcao usa o historico e
a progressao por RPE.

A carga alvo nao altera `training_logs.weight` ao gerar a sessao. `weight`
continua `NULL` ate o usuario registrar a carga real pelo Telegram.

Nomes exibidos no bot e no dashboard podem ser simplificados por
`ods_ops.get_display_name()`, mas os nomes salvos em `training_logs`,
`training_plan_exercises` e `exercises` permanecem canonicos para preservar
historico, progressao e relacoes musculares.

## Resumo Pos-Treino

`db_ops.get_session_summary(session_id)` calcula volume, RPE medio, mudancas de
carga, consolidacoes e recordes. Para comparar volume, procura a sessao anterior
com a mesma sequencia de exercicios preenchidos. Isso evita comparar diretamente
modelos de treino diferentes.

Para `Tríceps testa`, `Pullover (barra)` e `Rosca direta`, `ods_ops.format_loading_note()` usa
barra W de 6 kg e calcula as anilhas como
`target_weight - 6`. Exemplo: `target_weight = 18` gera
`barra W 6kg + 12kg de anilhas`.

Para os supinos com barra, `Agachamento com barra nas costas`, `Agachamento
sumô com barra à frente`, `Remada curvada (barra)`, `Desenvolvimento (barra em
pé)`, `Levantamento Terra Romeno` e `Remada curvada alta no peito (barra)`, a
funcao usa a barra reta de 2,20 m e 11 kg. Exemplo: `target_weight = 40` gera
`barra reta 2,20 m 11kg + 29kg de anilhas`.

Para `Rosca inversa (barra)`, a funcao usa barra reta de 2,20 m e 11 kg e calcula as
anilhas como `target_weight - 11`. Exemplo: `target_weight = 18` gera
`barra reta 2,20 m 11kg + 7kg de anilhas`.

## Descanso Entre Series

O descanso sugerido fica em `session.json`, nao em uma tabela SQLite. Ele e
derivado do nome do exercicio por `ods_ops.get_rest_interval()` durante a geracao
da sessao. Agachamento com barra nas costas e supino reto back-off usam 3 min;
Agachamento Zercher, supino reto e Terra Romeno, 2 min; supino inclinado,
remada curvada, desenvolvimento, remada curvada alta no peito e agachamento
sumô, 90 s; triceps
testa, rosca inversa, rosca de punho, pullover, elevacao lateral, rosca direta
e rosca martelo, 60 s. Os demais usam 2 min.

## Progresso

`count_filled(log_ids)` conta quantos logs tem `weight IS NOT NULL`.

```text
filled = 0  -> proximo exercicio exercises[0]
filled = 1  -> proximo exercicio exercises[1]
filled = 5  -> treino completo (planos A, B, D e E; o C tem 4 exercicios)
```

## Inspecao Segura

```bash
sqlite3 data/limulus.db ".tables"
sqlite3 data/limulus.db ".schema exercises"
sqlite3 data/limulus.db "SELECT name, sets, reps FROM exercises ORDER BY sort_order;"
python gerar_dashboard.py
```

## Nao Versionar

```text
data/*.db-shm
data/*.db-wal
session.json
.env
temp/
```

## Isolamento Dos Testes

O E2E troca temporariamente `DB_PATH`, `DATA_DIR`, `SESSION_FILE` e `send` para
nao tocar no banco real nem chamar Telegram.
