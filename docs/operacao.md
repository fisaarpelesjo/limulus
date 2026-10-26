# Operacao

Este documento explica como rodar, manter e depurar a Limulus.

## Uso Diario

1. Inicie o bot.
2. Abra o Telegram.
3. Envie `/gerar`.
4. Siga a carga de cada serie (piramide 80% -> 90% -> 100% do alvo) e use
   `descanso` como intervalo entre series.
5. Ao terminar cada exercicio, toque no RPE da ultima serie (a de topo) ou
   envie a carga total dela.
6. Use `/status` para ver progresso.
7. Use `/desfazer` se registrou algo errado.
8. Pare o bot com `Ctrl+C`.

## Iniciar O Bot

Multiplataforma:

```bash
python start_bot.py
```

Linux/macOS se necessario:

```bash
python3 start_bot.py
```

Windows:

```bat
start_bot.bat
```

## Primeiro Setup

```bash
pip install -r requirements.txt
copy .env.example .env
python tests/smoke_test.py
python tests/e2e_training_flow_test.py
```

Linux/macOS:

```bash
python3 -m pip install -r requirements.txt
cp .env.example .env
python3 tests/smoke_test.py
python3 tests/e2e_training_flow_test.py
```

Edite `.env` e configure:

```text
TELEGRAM_TOKEN=seu_token_real
```

## Comandos Do Bot

```text
/gerar          Cria uma nova sessao de treino
/prever         Mostra o treino sem salvar sessao ou logs
/treinob        Mostra o Treino B de garagem com pesos calculados
/exercicios     Lista exercicios ativos
/aquecimento    Mostra aquecimento
/volume         Mostra estimativa de volume
/status         Mostra progresso
/desfazer       Limpa o ultimo registro
/ajuda          Mostra ajuda
```

Entrada de carga:

```text
80
80 8
80,5
80,5 8
```

Use `/prever` quando quiser conferir formato, alvo e descanso sem iniciar uma
sessao real.

Use `/treinob` nos dias sem treino principal para receber o treino de garagem
com 10 voltas e peso unico por exercicio. Ele calcula os pesos a partir do
historico de Terra Romeno e Remada curvada, sem depender do plano ativo, mostra
a montagem da carga e nao cria sessao, logs, `session.json` nem registros de
RPE.

Ao registrar o ultimo exercicio, o bot envia automaticamente o resumo da sessao.
Nao e necessario executar outro comando.

Planos de treino:

```text
/planos
/plano A
/plano C
/plano Forca
```

Os planos `A` a `E` (segunda a sexta, cerca de 32-37 min, emagrecimento e
definicao) alternam sozinhos: ao concluir uma sessao do plano ativo, o seguinte
da sequencia A, B, C, D, E passa a ser o ativo, e depois do E volta o A. Se um
dia for perdido, o proximo treino continua de onde parou. `/plano NOME` troca manualmente. `Forca` e o antigo plano
`A` de 11 exercicios com foco em forca; fica inativo e nao entra na rotacao.

Para atualizar o dashboard pelo celular:

```text
/dashboard
```

O HTML continua salvo localmente em `temp/dashboard-treino.html`.

## Gerar Frames De Video

Quando quiser revisar uma execucao gravada, use o launcher local:

1. coloque o video em `videos/entrada/`
2. processe todos os arquivos com verificacao e instalacao do `ffmpeg`

```bash
python gerar_frames.py --todos --instalar-ffmpeg
```

Sem `--fps`, todos os frames sao extraidos. Use `--fps 1` para gerar uma imagem
por segundo. O launcher cria `videos/saida/<nome-do-video>/` para cada arquivo e
informa a quantidade gerada. JPG, JPEG, PNG, WebP e BMP sao aceitos.

No Windows, `--instalar-ffmpeg` usa o `winget` se a dependencia estiver ausente.
Frames anteriores daquele video sao removidos antes da nova extracao, evitando
arquivos obsoletos e contagem incorreta.

## Progressao De Carga Por RPE

Ao gerar treino, o bot sugere a proxima carga usando a ultima carga registrada
no exercicio e o RPE:

```text
RPE 7 ou menor  -> +2 kg
RPE 8           -> +2 kg
RPE 9           -> manter
RPE 10 ou maior -> -2 kg
Sem RPE         -> manter
```

RPE 9 e uma etapa de consolidacao, nao uma indicacao automatica de estagnacao.
Enquanto a carga ainda estiver em RPE 9, mantenha-a para melhorar tecnica,
amplitude, controle e qualidade das repeticoes. Quando a mesma carga passar a
RPE 8 ou menor, o proximo treino recebe o aumento previsto pela regra.

Considere uma sequencia de RPE 9 um ponto de atencao apenas se ela vier
acompanhada de perda tecnica, repeticoes incompletas, piora de amplitude ou
ausencia prolongada de melhora na execucao.

```text
Hoje: 40 8
Proximo /gerar: alvo 42 kg

Hoje: 40 10
Proximo /gerar: alvo 38 kg
```

O alvo e a carga da ultima serie (topo); as anteriores usam cerca de 80% e 90%
dele, arredondadas para baixo em anilhas de 2 kg. Se as repeticoes do plano
mudaram desde o ultimo registro (por exemplo de 3x5 para 3x12), o alvo e
convertido pelo 1RM estimado: 61 kg x5 vira 49 kg para 3x12.

Depois de uma pausa, o alvo fica mais leve: de 10 a 20 dias parado, a ultima
carga menos 4 kg; com 21 dias ou mais, 80% da ultima carga, arredondada para
baixo em anilhas. Exemplo: 61 kg x5 parado ha 35 dias vira 39 kg para 3x12.

Se nao houver historico para o exercicio, o alvo aparece como `-`. Registre
sempre a carga real feita; ela sera a base do proximo alvo.

## Descanso Entre Series

O `/gerar` mostra descanso fixo sugerido por exercicio. Use esses tempos como
base para preservar a qualidade tecnica:

```text
Agachamento com barra nas costas e back-off: 3 min
Agachamento Zercher, supino reto e terra romeno: 2 min
Supino inclinado, remada curvada, desenvolvimento, remada curvada alta no peito, remada apoiada no banco e agachamento sumô: 90 s
Triceps testa, roscas, pullover e elevacao lateral: 60 s
Demais exercicios: 2 min
```

## Arquivos Para Backup

Principal:

```text
data/limulus.db
```

Criar backup consistente:

```bash
python gerenciar_dados.py backup
```

Exportar o conteudo para JSON:

```bash
python gerenciar_dados.py exportar
```

Restaurar um backup:

```bash
python gerenciar_dados.py restaurar backups/arquivo.db --confirmar
```

Pare o bot antes de restaurar. A operacao valida o backup e cria uma copia de
seguranca do banco atual.

Estado local opcional:

```text
session.json
```

Se `session.json` for apagado ou corrompido durante um treino, envie `/status`
ou a proxima carga normalmente. O bot tenta reconstruir a sessao mais recente
que ainda possui logs pendentes no SQLite.

Segredo local:

```text
.env
```

Nao publique `.env`.

## Arquivos Que Ficam Locais

Nao commitar:

```text
.env
session.json
pending_log.csv
temp/
backups/
exportacoes/
data/*.db-shm
data/*.db-wal
__pycache__/
*.pyc
```

## Atualizar Exercicios

O catalogo de exercicios fica no SQLite.

Codigo:

```text
limulus/db_ops.py
  -> tabela exercises
```

Use os helpers quando possivel:

```python
from limulus import db_ops

db_ops.list_exercises()
db_ops.replace_exercises([...])
```

Nao substituir a fonte da verdade SQLite por planilha.

Catalogo atual:

- Plano `A` (segunda, empurrar): `Supino reto (barra)` 3x12, `Supino inclinado
  (barra)` 3x12, `Desenvolvimento (barra em pé)` 3x12, `Elevação lateral` 4x15 e
  `Tríceps testa` 3x15.
- Plano `B` (terca, puxar): `Remada curvada (barra)` 3x12, `Remada curvada alta
  no peito (barra)` 3x15, `Pullover (barra)` 3x15, `Rosca direta` 3x15 e
  `Rosca inversa (barra)` 3x15.
- Plano `C` (quarta, inferior): `Agachamento Zercher` 3x12, `Levantamento Terra
  Romeno` 3x12, `Agachamento sumô com barra à frente` 3x12 e `Rosca de punho
  atrás das costas (barra)` 3x15.
- Plano `D` (quinta, empurrar): `Supino inclinado (barra)` 3x12, `Supino reto
  (barra)` 3x12, `Desenvolvimento (barra em pé)` 3x12, `Elevação lateral` 4x15 e
  `Tríceps testa` 3x15.
- Plano `E` (sexta, puxar): `Remada apoiada no banco (barras 40 cm)` 3x12,
  `Pullover (barra)` 3x15, `Levantamento Terra Romeno` 3x12,
  `Crucifixo invertido apoiado (barras 40 cm)` 3x15 e `Rosca direta` 3x15. A remada
  e o crucifixo sao feitos deitado de brucos no banco inclinado, com uma
  barra de 40 cm em cada mao, para poupar a lombar.
- Plano `Forca`: antigo plano `A` de 11 exercicios, inativo.
- O agachamento dos planos A a E e o Zercher, sem barra atras da nuca.
- Cada exercicio usa as mesmas series e repeticoes em todos os dias.
- `Supino fechado (barra)` e `Remada alta (barra)` estao inativos para sessoes futuras.
- Historico antigo pode continuar com nomes antigos ou inativos.
- Se o catalogo mudar de novo, atualizar `data/limulus.db` e `limulus/db_ops.py`
  (`DEFAULT_EXERCISES` para o plano A, `WEEKLY_PLANS` para A a E).

## Problemas Comuns

### Falha De Rede No Telegram

O bot registra a falha e aumenta gradualmente a espera entre tentativas, ate 60
segundos. Nao e necessario reiniciar para uma interrupcao temporaria.

### Token Invalido

O polling encerra com uma mensagem clara. Corrija `TELEGRAM_TOKEN` em `.env` e
inicie novamente. O token nunca deve aparecer no terminal ou em arquivos de log.

### `TELEGRAM_TOKEN nao encontrado no .env`

Crie `.env` a partir de `.env.example` e configure o token.

### Bot inicia mas ignora mensagens

Possiveis causas:

- `CHAT_ID` diferente
- token de outro bot
- updates antigos no Telegram

### `Nenhuma sessao ativa. Use /gerar.`

Voce enviou carga antes de gerar treino, ou `session.json` foi apagado.

### SQLite travado

Feche DB Browser, outros processos Python e pause sincronizacao de OneDrive se
isso persistir.

## Checklist De Manutencao

Antes de push:

```bash
python tests/smoke_test.py
python tests/e2e_training_flow_test.py
```

Checagem de sintaxe:

```bash
python -m py_compile start_bot.py limulus/*.py tests/*.py
```

Antes de commitar:

```bash
git status --short
git diff --check
```
