# Instrucoes Do Codex Para Este Repositorio

## Contexto Do Projeto

Este projeto e um diario de treino com bot do Telegram e banco SQLite versionado.

Banco principal: `data/limulus.db`.
Launcher multiplataforma: `start_bot.py`.
Wrapper Windows: `start_bot.bat`.
O launcher do bot deve manter saida minimalista no terminal: sem banner, ASCII
art ou mensagens cosmeticas; preservar apenas logs operacionais e erros uteis.
Dashboard local: `gerar_dashboard.py` gera `temp/dashboard-treino.html`.
Extracao de frames de video: `gerar_frames.py --todos --instalar-ffmpeg`
verifica a dependencia, processa os videos de `videos/entrada/` e grava cada
resultado em `videos/saida/<nome-do-video>/`, informando a contagem de frames.
Gestao de dados: `gerenciar_dados.py` cria backup, exporta JSON e restaura
backups validados.

Teste direto das regras: `python tests/regras_treino_test.py`.
Catalogo unico de comandos: `docs/comandos.md`.

Acesso e operacao na VPS: ler primeiro `docs/vps.md`. Os dados concretos de
conexao ficam somente em `.vps.yml`, arquivo local ignorado pelo Git, criado a
partir de `config/vps.exemplo.yml`. Nunca publicar host, credenciais, chave
privada, token ou `.env`. O Limulus divide a VPS com o Nautilus, cujo diretorio
e `/root/nautilus` e servico e `nautilus-bot`; confirmar no `.vps.yml` o
diretorio e o servico proprios do Limulus antes de qualquer operacao remota.
Preferir o alias local `ssh vps-limulus`, definido em `~/.ssh/config`.

Ao consultar o banco em tarefas de manutencao, preferir scripts Python com o
modulo padrao `sqlite3` ou helpers de `limulus/db_ops.py`. Nao depender
do binario externo `sqlite3`, pois ele pode nao estar disponivel no PATH local.
No schema atual, `training_sessions` usa `id`, `date` e `training_type`; nao
assumir coluna `plan_name`. Desde o schema 13, `started_at` e `completed_at`
existem e podem ser nulos em sessoes historicas. Desde o schema 15,
os planos sao `A` a `E` (segunda a sexta, rotacao automatica) e `Forca`
(antigo `A` do schema 13, inativo). Desde o schema 16, o jogo guarda o que
nao da para derivar do historico em `jogo_estado`, `jogo_compras` e
`jogo_pausas`.
`training_logs.weight` guarda a carga da serie de topo. `training_logs`
usa `exercise_name` para o nome do exercicio, nao `exercise`, e nao possui
`logged_at`; usar `session_id`, `sort_order` e `id` para ordenar logs.
Em consultas via `python -c` no PowerShell, evitar metacaracteres como `|` dentro
da string do comando. Preferir codigo Python entre aspas simples e saida CSV ou
texto simples. Se o sandbox do Windows falhar com `CreateProcessAsUserW failed:
1312`, repetir a mesma consulta com permissao escalada em vez de trocar para o
binario `sqlite3`.
Neste ambiente Windows, esse erro de sandbox e recorrente tambem em leituras
locais com PowerShell, especialmente em caminhos do OneDrive, Area de Trabalho
ou arquivos grandes. Quando um comando necessario falhar com
`CreateProcessAsUserW failed: 1312`, repetir diretamente o mesmo comando com
permissao escalada e justificativa curta. Nao interromper o fluxo para explicar
o erro ao usuario toda vez; mencionar apenas se a permissao for negada ou se o
bloqueio impedir a tarefa.

## Memoria Operacional Do Projeto

Quando uma tarefa revelar um detalhe estavel sobre estrutura, caminhos, esquema
do banco, comandos, fluxos locais, arquivos de estado ou convencoes do projeto,
registrar essa descoberta nos arquivos de agente antes de finalizar, desde que a
informacao ajude manutencoes futuras e nao contenha segredo. Sincronizar a mesma
nota em `AGENTS.md`, `CLAUDE.md` e `.github/copilot-instructions.md` quando ela
se aplicar aos tres.

Nao depender apenas da memoria da conversa para fatos recorrentes do projeto.
Preferir consolidar no proprio repositorio onde ficam os arquivos, nomes de
tabelas, colunas, comandos e particularidades do ambiente local.

## Padrao De Idioma

O projeto deve ser o mais PT-BR possivel. Use portugues brasileiro como padrao
para tudo que for criado ou alterado, especialmente:

- comandos do Telegram
- mensagens do bot
- ajuda principal do bot
- documentacao de uso
- documentacao tecnica
- titulos e secoes de Markdown
- nomes de arquivos e pastas novos, quando forem parte da documentacao
- mensagens dos launchers
- comentarios novos, quando comentarios forem necessarios
- textos futuros visiveis ao usuario

Evitar criar novos nomes, textos ou caminhos em ingles quando houver uma opcao
natural em PT-BR. Termos tecnicos muito estabelecidos podem aparecer quando
ajudarem a clareza, mas devem ser acompanhados de contexto em portugues sempre
que forem visiveis ao usuario ou na documentacao.

Comandos textuais do Telegram devem usar somente os nomes oficiais em PT-BR e
exigir `/`, exceto os textos exatos do teclado "⚔ Iniciar treino" e
"🍖 Ver dieta". Nao aceitar outros aliases em ingles ou nomes sem barra.
Comando invalido sem sessao ativa responde com o teclado de inicio, para que um
teclado antigo no celular seja substituido.

## Sincronizacao Das Instrucoes De Agentes

Sempre que uma mudanca alterar comportamento, comandos, fluxo de uso, estrutura
de arquivos, nomes de caminhos, catalogo de exercicios, banco de dados,
launchers, padrao de idioma ou documentacao principal, revisar e atualizar em
conjunto:

- `AGENTS.md`
- `CLAUDE.md`
- `.github/copilot-instructions.md`

Nao atualizar apenas um arquivo de agente quando a informacao tambem se aplicar
aos outros. Antes de finalizar uma mudanca, verificar se README, `docs/index.md`
ou outros documentos em `docs/` tambem precisam ser atualizados.

O roadmap tecnico fica em `docs/melhorias-futuras.md`. Consultar esse documento
antes de iniciar melhorias amplas e atualiza-lo quando um item for entregue,
descartado ou repriorizado.

## Modulos Principais

Os modulos de runtime ficam no pacote `limulus/`. Importe codigo de aplicacao
a partir desse pacote, por exemplo `from limulus import db_ops`.

### `limulus/telegram_poller.py`

Bot Telegram usado para controlar o treino pelo celular.

O polling usa logs com horario, nivel, comando e `session_id`, sem registrar
token ou URL completa da API. Falhas temporarias usam espera gradual; token
invalido encerra o polling com erro claro. O `getUpdates` usa long polling
(`POLL_TIMEOUT` = 25 s) sem pausa entre ciclos, e todas as chamadas a API
passam pela sessao HTTP `telegram_poller.HTTP` (`requests.Session`), que
reaproveita a conexao; por isso o clique no RPE e processado na hora. Testes
que simulam a rede devem substituir `telegram_poller.HTTP.get/post`.
As chamadas de rede do jogo passam por `telegram_poller.telegram_call`;
testes do jogo devem substituir essa funcao.

Comandos principais:

- `/gerar`
- `/prever`
- `/treinob`
- `/exercicios`
- `/aquecimento`
- `/volume`
- `/dashboard`
- `/dieta`
- `/planos`
- `/plano NOME`
- `/peso VALOR`
- `/peso`
- `/cintura VALOR`
- `/cintura`
- `/status`
- `/desfazer`
- `/perfil`
- `/menu`
- `/chefes`
- `/semana`
- `/missoes`
- `/conquistas`
- `/diario`
- `/loja` e `/loja coringa`
- `/pausa N` e `/pausa fim`
- `/app`
- `/ajuda`
- `80` ou `80 8` para registrar carga e RPE opcional

Todos os comandos textuais exigem `/`. Entradas numericas de carga e RPE nao
usam barra.
`/aquecimento` mostra uma sequencia dinamica curta de corpo todo, com cerca de
5 minutos, sem prescrever um segundo treino.

Fluxo:

Formato de quest (tom JRPG): cada exercicio do treino e uma quest contra um
inimigo escolhido pelo grupo muscular principal do exercicio
(`jogo.INIMIGOS_POR_GRUPO`, via `jogo.inimigo_do_exercicio`; sem grupo
mapeado, `jogo.INIMIGO_PADRAO` = Cogumelo Bravo). Inicio "⚔ BATALHA
INICIADA!" com plano, dia da semana (`jogo.DIAS_SEMANA_LONGOS`), data, hora e
numero de quests, seguido da imagem `render_encontro` com a fila de inimigos;
retomada "⚔ Batalha em andamento — quest i/n"; `/status` "⚔ Batalha em
andamento — i/n quests completas" ou "🏁 Treino completo."; `/desfazer`
"↩ Turno desfeito: NOME"; conclusao "🏁 TREINO CONCLUÍDO" com
"⭐ Recordes: ..."; `/prever` "🔮 Treino de hoje — N exercícios"; `/ajuda`
"📜 Menu do Limulus"; `/volume` 📊, `/planos` 🗺, `/dieta` "🍖 DIETA ATUAL",
`/peso` e `/cintura` 📏.

Cada quest (`send_current_exercise(ex, exercises)`) sai como foto da tela de
batalha (`jogo_visual.render_batalha`; o `file_id` fica em `_CACHE_BATALHA`
para reenviar a mesma tela na hora) com o card na legenda (`_send_batalha`);
se a imagem falhar, o card vai como mensagem de texto. Card
(`_format_current_exercise`): header `⚔ QUEST i/n · NOME` e "👹 Derrote o
<inimigo>!"; "📜 Objetivo: N golpes de R repetições"; uma linha por serie da
piramide, `⚔ Golpe k · X kg de anilhas (total Y kg)` e `🎯 Golpe final` na
serie de topo (sem equipamento fixo, so `X kg`; com `per_hand`, `por mão`);
footer "⏳ Descanso entre golpes", "🏋 Barra ..." e "🎯 Depois do golpe final,
como foi?". Sem alvo, o card pede a primeira carga manualmente. Botoes 2x2 de
golpe (`_botoes_golpe`, `jogo.GOLPES_RPE`): "🛡 Leve · RPE ≤7", "⚔ Certeiro ·
RPE 8", "🔥 Crítico · RPE 9" e "💀 No limite · RPE 10", gravados como 7, 8, 9
e 10; nao ha botao sem RPE. O clique mostra o aviso "Golpe registrado! ⚔" e
edita a legenda (`editMessageCaption`, quando a mensagem e foto) ou o texto
(`editMessageText`) com "💥 <Golpe>! X kg · RPE n" e "✅ Quest completa:
<inimigo> derrotado! +N EXP" (`_format_quest_result`; EXP = 10 x aderencia do
RPE). A lista de `/prever` continua em texto, com o alvo como `65→73→82kg`.

1. `/gerar` e "⚔ Iniciar treino" iniciam uma sessao ou retomam a atual. Enviam
   "⚔ BATALHA INICIADA!" (plano, dia, data/hora de Brasilia e numero de
   quests), a imagem de encontro e a primeira quest, sem a lista completa.
   O teclado de inicio some durante o treino e retorna ao concluir.
   Os botoes de golpe registram a carga total exibida com RPE 7, 8, 9 ou 10 e
   avancam para a proxima quest. Nao ha botao sem RPE.
   Sem alvo, pedir a primeira carga manualmente.
2. O card da quest mostra as cargas da piramide a partir do alvo, calculado pela ultima carga registrada e pelo RPE, e o descanso.
3. `/prever` mostra a lista em texto sem criar sessao, logs ou `session.json`.
4. `/treinob` mostra um Treino B de garagem sem criar sessao, logs ou
   `session.json`; os pesos unicos sao calculados pelos alvos de Terra Romeno
   e Remada curvada lidos do historico, sem pedir nem registrar RPE.
5. Entrada de carga e escrita diretamente no SQLite.
6. `/desfazer` limpa o ultimo exercicio registrado.
7. `session.json` e validado contra o SQLite ao ser carregado. Se estiver
   ausente, corrompido ou antigo, o bot reconstrui a sessao mais recente com
   logs pendentes; sessoes completas nao sao reabertas.
8. Ao registrar o ultimo exercicio, o bot envia resumo com volume, RPE medio,
   comparacao com sessao compativel, mudancas de carga, consolidacoes, cargas
   mantidas em RPE 9 e recordes.
9. `/planos` lista modelos cadastrados e `/plano NOME` seleciona o plano usado
   por `/gerar`, `/prever`, `/exercicios` e `/volume`. Ao concluir uma sessao
   do plano ativo A ou B, o bot ativa o outro automaticamente.
10. `/dashboard` atualiza `temp/dashboard-treino.html` e responde com horario,
   ultima sessao, volume e RPE medio geral, sem expor caminho local.
11. `/dieta` e o teclado "🍖 Ver dieta" listam os alimentos de `diet_entries`
    agrupados por refeicao e comparam os totais de calorias, proteina,
    carboidrato e gordura com as metas de `diet_targets`, sem criar sessao,
    logs ou alterar o banco.
12. `/peso VALOR` registra o peso corporal com data e `/peso` consulta o valor
    atual, a variacao anterior e as ultimas medicoes.
13. `/cintura VALOR` registra a circunferencia da cintura em centimetros e
    `/cintura` consulta o valor atual, a variacao e as ultimas medicoes.

### `limulus/jogo.py`

Camada de jogo no estilo JRPG (fases 1 a 3 entregues). EXP, nivel, titulo,
classe, atributos, chefes, conquistas, missoes, ouro, sequencia e diario sao
calculados a partir das sessoes concluidas no SQLite (`calcular()`): mudar uma
regra recalcula o historico inteiro sem migracao. So o que nao da para derivar
fica nas tabelas do schema 16: `jogo_compras` (loja), `jogo_pausas` (pausas
declaradas) e `jogo_estado` (chave/valor, por exemplo `hud_mensagem`).

- EXP: sessao concluida 50; cada exercicio 10 vezes a aderencia ao RPE (8 ou
  9 = 1,0; 7 ou menos = 0,5; 10 = 0,3; sem RPE = 0,5); recorde de carga com
  RPE ate 9 vale 20, no maximo um por exercicio por semana; semana cumprida
  (5 treinos de segunda a domingo) vale 100; missao semanal vale 50.
- Nivel: `exp_para_nivel(N) = round(100 * (N - 1) ** 1.8)`, maximo 99, com
  titulos por faixa (Aprendiz, Escudeiro, Soldado, Cavaleiro, Paladino,
  Campeao, Heroi, Lenda).
- Ouro: 10 por sessao, 5 por recorde, 25 por semana cumprida e 20 por missao.
  `LOJA` vende o coringa extra por 150 de ouro (`comprar()`, grava em
  `jogo_compras`).
- Sequencia: semanas seguidas cumpridas; semana incompleta gasta um coringa
  (2 por mes, pelo mes da segunda-feira, depois os comprados) e mantem a
  sequencia sem somar; sem coringa, zera. Semana com pausa declarada
  (`/pausa N`, ate `PAUSA_MAXIMA_DIAS` = 90) e neutra.
- Missoes: 3 por semana em rodizio fixo pela data (`MISSOES`); premiam
  qualidade (RPE registrado, sessao inteira no RPE 8-9, recorde com RPE ate 9,
  constancia), nunca "fazer mais".
- Conquistas: lista fixa em `CONQUISTAS`, cada uma com a data da sessao que a
  desbloqueou.
- Chefes (`PADROES`): um por padrao de movimento (Empurrar, Agachar, Quadril,
  Puxar, Ombro), com ranks Ferro, Bronze, Prata, Ouro, Platina e Diamante pela
  razao 1RM estimado (Epley) / peso corporal. Os limites sao aproximacoes de
  padroes publicos de forca para homens (strengthlevel.com, Symmetric
  Strength), servem ao jogo e nao como avaliacao. HP = distancia ate o
  proximo rank.
- Atributos de 1 a 99: FOR (forca relativa nos chefes), VIG (series efetivas
  por musculo, RPE 7 a 9) e DIS (presenca e RPE 8-9 nas ultimas 8 semanas).
  Classe pelo atributo dominante (FOR Guerreiro, VIG Barbaro, DIS Monge), com
  nome que evolui nos niveis 10 e 30.
- Diario: uma linha por sessao (ultimas 30 no estado).
- Quests do treino: `INIMIGOS_POR_GRUPO` liga o grupo muscular principal do
  exercicio a um inimigo (os cinco chefes mais Diabrete Rúnico para triceps e
  Morcego de Ferro para biceps e antebraco); `inimigo_do_exercicio(grupos)`
  devolve `INIMIGO_PADRAO` (Cogumelo Bravo) sem grupo mapeado. `GOLPES_RPE`
  define os botoes de golpe (rotulo, valor gravado, nome do golpe),
  `nome_do_golpe(rpe)` o nome usado na confirmacao e `DIAS_SEMANA_LONGOS` o
  dia da mensagem de inicio.
- Textos HTML do Telegram: `formatar_vitoria`, `formatar_perfil`,
  `formatar_chefes`, `formatar_semana`, `formatar_missoes`,
  `formatar_conquistas`, `formatar_diario`, `formatar_loja` e `formatar_hud`
  (mensagem fixada no topo do chat).
- `exportar_para_app()` / `exportar_json_app()` geram o JSON compacto do Mini
  App; o estado de cada dia da semana vira um codigo de `CODIGOS_DIA`
  (`f` feito, `h` hoje, `p` pendente, `x` perdido, `d` descanso, `z` pausa).

Falha no calculo do jogo so gera log e nunca interrompe o treino. Testes:
`python tests/jogo_test.py`, `python tests/jogo_visual_test.py` e
`python tests/app_test.py`.

### `limulus/jogo_visual.py` e `limulus/jogo_sprites.py`

Telas do jogo em PNG com Pillow, no estilo de janela de menu JRPG azul
classica: `render_ficha`, `render_vitoria`, `render_chefes`,
`render_semana`, `render_batalha` (cena da quest: inimigo a esquerda, heroi a
direita, sem cargas na imagem) e `render_encontro` (fila de inimigos do
treino), desenhadas em 320 px de largura e ampliadas por vizinho mais
proximo. `jogo_sprites.py` guarda a pixel art original (herois por classe e
estagio, cinco chefes, tres monstros menores, Diabrete Rúnico, Morcego de
Ferro e Cogumelo Bravo, via `sprite_do_inimigo`, e icones) e uma fonte bitmap propria, porque a fonte
`load_default` do Pillow nao tem os acentos do portugues; os acentos sao
compostos pela decomposicao NFD. `pillow` esta em `requirements.txt`; sem ele
o bot segue so em texto. `LIMULUS_AMOSTRAS=<pasta> python
tests/jogo_visual_test.py` grava PNGs de amostra para conferir o visual.

### Jogo no Telegram e Mini App

- Ao concluir o treino, `send_victory` envia a tela de vitoria depois do
  resumo: a barra de EXP enche por edicoes da mesma mensagem
  (`PAUSA_ANIMACAO` = 0,35 s), com efeito de confete `EFEITO_FESTA` em level
  up ou semana completa (sem o efeito se o Telegram recusar); depois envia a
  imagem `render_vitoria`, o som `limulus/assets/jogo/level_up.ogg` como voz
  no level up (fanfarra chiptune original de 1,4 s, gerada para o projeto) e
  atualiza o HUD fixado (`atualizar_hud`, id em `jogo_estado.hud_mensagem`).
- Comandos do jogo: `/menu` (menu inline `MENU_JOGO`, callbacks `menu:*`),
  `/perfil`, `/chefes`, `/semana`, `/missoes`, `/conquistas`, `/diario`,
  `/loja` e `/loja coringa`, `/pausa N` e `/pausa fim`, `/app`.
- Todas as chamadas de rede do jogo (texto com efeito, fotos, voz, edicoes,
  fixar mensagem) passam por `telegram_poller.telegram_call(method, payload,
  files=None)`, que devolve `(ok, resultado)`. Testes devem substituir
  `telegram_call` para nunca falar com a rede.
- Mini App: `/app` e o botao "🎮 Abrir app" abrem `APP_URL`
  (`https://fisaarpelesjo.github.io/limulus/app/`) por um botao `web_app`.
  A pagina e `docs/app/index.html`, publicada pelo GitHub Pages a partir de
  `docs/` (com `docs/.nojekyll`). O estado vai so no fragmento
  `#d=<base64url do JSON>`, que nunca chega ao servidor; a pagina nao faz
  fetch, nao guarda dados e mostra uma demonstracao sem fragmento valido.
- O dashboard local tem a secao "Ficha do personagem" com o mesmo estado.

### `limulus/ods_ops.py`

Camada auxiliar de sessao de treino.

Funcoes importantes:

- `generate_training()` cria uma sessao SQLite e retorna `(exercises, session_id)`.
- `preview_training()` monta o treino sem persistir sessao, logs ou `session.json`.
- `build_training_b()` monta o Treino B de garagem sem persistir sessao, logs ou
  `session.json`, aplicando percentuais aos alvos de Terra Romeno e Remada
  curvada lidos direto do historico de cada exercicio.
- `gerar_treino()` e alias de compatibilidade para scripts locais antigos.
- `read_exercises()` le do SQLite.
- `read_previous_weights()` retorna a carga mais recente por exercicio.
- `read_previous_performance()` retorna carga, RPE e reps mais recentes por exercicio.
- `suggest_next_weight(previous_weight, previous_rpe=None, previous_reps=None,
  target_reps=None, exercise_name=None)` converte por reps quando elas mudam e
  senao calcula o alvo pela regra de RPE.
- `get_set_weights(exercise_name, target_weight, sets)` retorna a carga de cada
  serie da piramide; `round_down_to_plates()` e `convert_weight_for_reps()`
  apoiam o arredondamento e a conversao por 1RM estimado.
- `get_rest_interval(exercise_name)` retorna o descanso sugerido entre series.
- `format_loading_note(exercise_name, target_weight)` retorna observacao de montagem da carga quando houver equipamento fixo.
- `write_session()` escreve `session.json`.
- `recover_active_session()` reconstrui `session.json` a partir da sessao
  SQLite mais recente que ainda possui logs pendentes.

Regras importantes:

- A sequencia ativa vem de `training_plan_exercises`; `TRAINING_EXERCISES` e
  `TREINO_EXERCISES` permanecem apenas como aliases legados.
- Progressao por RPE (cautelosa, para series de 12-15 reps): RPE 7 ou menor
  `+2 kg`, RPE 8 `+2 kg`, RPE 9 mantem, RPE 10 ou maior `-4 kg`, sem RPE
  mantem. Nunca sobe mais de um passo de anilha (2 kg) por sessao. Nos
  exercicios com carga por mao (`per_hand`), RPE 10 desce so `-2 kg` e o alvo
  nao fica abaixo da barra.
- Piramide crescente: `get_set_weights(nome, alvo, series)` gera 80% -> 90% ->
  100% do alvo; series intermediarias sao arredondadas para baixo em anilhas de
  2 kg acima da barra (`round_down_to_plates`). A ultima serie e a de topo: o
  RPE registrado se refere a ela e `training_logs.weight` grava a carga do topo.
  A progressao por RPE se aplica ao alvo de topo.
- Conversao por repeticoes: se as reps do ultimo log do exercicio diferem das
  reps do plano, `suggest_next_weight` converte a carga pelo 1RM estimado
  (Epley, `peso x (1 + reps/30)`) e arredonda para baixo em anilhas, ignorando
  o delta de RPE nessa sessao. Exemplo: 61 kg x5 vira 49 kg para 3x12.
- Retorno apos pausa: se o ultimo log do exercicio tem `RETURN_AFTER_DAYS`
  (10) dias ou mais, o alvo volta com a ultima carga menos
  `RETURN_REDUCTION_KG` (4 kg), sem somar a progressao por RPE e sem ficar
  abaixo da barra; a conversao por reps, se houver, vem antes. A pausa conta a
  partir de `training_sessions.date` do ultimo log ate a data da sessao nova
  (ou da sessao recuperada), via `ods_ops.days_between()`.
- Pausa longa: com `RETURN_LONG_AFTER_DAYS` (21) dias ou mais, o alvo vira
  `RETURN_LONG_FACTOR` (68%) da ultima carga, ja convertida por reps, e e
  arredondado para baixo em anilhas, em vez de tirar 4 kg. Exemplo: 61 kg x5
  parado ha 35 dias vira 33 kg para 3x12. Motivo: retorno cauteloso apos um
  mes parado por crise de enxaqueca, preferindo carga leve e mais reps.
- Treino B de garagem: farmer walk usa 45% do Terra Romeno e remada leve com
  barra usa 60% da remada curvada, com alvos lidos do historico do exercicio
  (`read_previous_performance` + `suggest_next_weight`), sem depender do plano
  ativo; o comando `/treinob` exibe peso unico
  arredondado, 10 voltas fixas,
  montagem com barra reta 2,50 m de 9 kg para remada com barra e barra de 40 cm
  para farmer walk, e nao registra RPE.
- RPE 9 nao representa estagnacao automaticamente. Nesse nivel, manter a carga
  faz parte do metodo para consolidar tecnica, amplitude, controle e qualidade
  das repeticoes. Quando a mesma carga passar a ser registrada como RPE 8 ou
  menor, o sistema aumenta o alvo conforme a regra de progressao.
- Avaliacoes do historico e alertas do dashboard nao devem tratar uma sequencia
  de RPE 9 como problema isolado. Ela so exige atencao quando vier acompanhada
  de perda tecnica, repeticoes incompletas, piora de amplitude ou ausencia
  prolongada de qualquer melhora na execucao.
- `Rosca inversa (barra)` tem alvo inicial de 11 kg e `Supino inclinado
  (barra)` tem alvo inicial de 41 kg quando ainda nao houver historico proprio;
  depois disso usam a progressao por RPE.
- `target_weight` fica em `session.json`.
- `rest_interval` fica em `session.json` e aparece no card de cada quest (`⏳ Descanso entre golpes`).
- Descansos (`REST_INTERVALS`): agachamento com barra nas costas e supino reto
  back-off 3 min; Agachamento Zercher, supino reto e Terra Romeno 2 min; supino
  inclinado, remada curvada, desenvolvimento, remada curvada alta no peito e
  agachamento sumô 90 s; triceps testa, rosca inversa, rosca de punho, pullover,
  elevacao lateral, rosca direta e rosca martelo 60 s; remada apoiada no
  banco 90 s e crucifixo invertido apoiado 60 s; demais 2 min.
- `Rosca de punho atrás das costas (barra)` usa 3x15 e alvo inicial de 11 kg.
- `loading_note` fica em `session.json` quando houver equipamento fixo; o card da quest mostra a montagem por golpe (`X kg de anilhas (total Y kg)`) e a linha `🏋 Barra ...`, e a observacao em texto so aparece no `/treinob`, nunca na lista `/exercicios`.
- Nomes visiveis no bot e dashboard podem usar `ods_ops.get_display_name()` para
  ocultar qualificadores como `(barra)`, `(barra H)` e `(barra em pé)`. Nao
  renomear os nomes canonicos no SQLite para isso, pois eles sao usados no
  historico e na progressao.
- `Agachamento com barra nas costas`, `Agachamento sumô com barra à frente`, os
  supinos com barra, `Remada curvada (barra)`, `Desenvolvimento (barra em pé)`,
  `Levantamento Terra Romeno` e `Remada curvada alta no peito (barra)` usam
  barra reta de 2,20 m e 11 kg; a observacao deve mostrar carga total como
  `barra reta 2,20 m 11kg + Xkg de anilhas`.
- `Tríceps testa`, `Pullover (barra)` e `Rosca direta` usam barra W de 6 kg; a observacao deve mostrar carga total como `barra W 6kg + Xkg de anilhas`.
- `LOAD_EQUIPMENT` aceita o campo opcional `per_hand`. Com ele, `format_loading_note()` devolve `barra de 40 cm em cada mao + Xkg de
  anilhas por mao` e `_format_current_exercise()` mostra `de anilhas por mão`
  e `(total Y kg por mão)` em cada golpe e `🏋 Barra 40 cm · 0 kg (uma em
  cada mão)`. Usam `per_hand`: `Elevação lateral`,
  `Remada apoiada no banco (barras 40 cm)` e `Crucifixo invertido apoiado (barras 40 cm)`.
- `Rosca inversa (barra)` usa barra reta de 2,20 m e 11 kg; a observacao deve mostrar carga total como `barra reta 2,20 m 11kg + Xkg de anilhas`.
- Manter `TREINO_EXERCISES` apenas como alias de compatibilidade.
- Planos (schema 15), divisao de segunda a sexta, cerca de 32-37 min por sessao,
  foco em emagrecimento e definicao. O agachamento e o Zercher (barra na dobra
  dos cotovelos), sem barra atras da nuca:
  - `A` (segunda, empurrar): `Supino reto (barra)` 3x12, `Supino inclinado
    (barra)` 3x12, `Desenvolvimento (barra em pé)` 3x12, `Elevação lateral` 4x15,
    `Tríceps testa` 3x15.
  - `B` (terca, puxar): `Remada curvada (barra)` 3x12, `Remada curvada alta no
    peito (barra)` 3x15, `Pullover (barra)` 3x15, `Rosca direta` 3x15,
    `Rosca inversa (barra)` 3x15.
  - `C` (quarta, inferior): `Agachamento Zercher` 3x12, `Levantamento Terra
    Romeno` 3x12, `Agachamento sumô com barra à frente` 3x12, `Rosca de punho
    atrás das costas (barra)` 3x15.
  - `D` (quinta, empurrar): `Supino inclinado (barra)` 3x12, `Supino reto
    (barra)` 3x12, `Desenvolvimento (barra em pé)` 3x12, `Elevação lateral` 4x15,
    `Tríceps testa` 3x15.
  - `E` (sexta, puxar): `Remada apoiada no banco (barras 40 cm)` 3x12, `Pullover (barra)`
    3x15, `Levantamento Terra Romeno` 3x12, `Crucifixo invertido apoiado (barras 40 cm)`
    3x15, `Rosca direta` 3x15. As duas remadas curvadas sairam da sexta para
    tirar carga da lombar: a remada e o crucifixo sao feitos deitado de
    brucos no banco inclinado, com uma barra de 40 cm em cada mao.
  - `Elevação lateral` usa duas barras ocas de 40 cm, uma em cada mao, com
    peso desprezivel (`weight` 0). A carga registrada e por mao e o alvo
    inicial e 2 kg por mao. Com anilha minima de 1 kg, o passo de 2 kg por mao
    equivale a 1 kg em cada ponta. `Rosca direta` usa barra W de 6 kg.
  - `Remada apoiada no banco (barras 40 cm)` (alvo inicial 12 kg por mao, 90 s) e
    `Crucifixo invertido apoiado (barras 40 cm)` (alvo inicial 2 kg por mao, 60 s) usam
    o mesmo equipamento `per_hand` da elevacao lateral. `get_display_name()`
    exibe os dois sem o sufixo `(barras 40 cm)`, e os grupos musculares
    ficam em `DEFAULT_MUSCLE_GROUPS` (dorsais; deltoide posterior).
  - `Forca`: antigo plano `A` de 11 exercicios com foco em forca, inativo e
    disponivel via `/plano Forca`.
- Cada exercicio usa as mesmas series e repeticoes em todos os dias em que
  aparece. Reps diferentes entre dias fariam `suggest_next_weight` converter a
  carga por repeticoes a cada sessao e nunca aplicar a progressao por RPE.
- `DEFAULT_EXERCISES` em `db_ops` e o plano A e `WEEKLY_PLANS` guarda os planos
  A a E.
- Ao concluir uma sessao cujo `training_type` e o plano ativo, de `A` a `E`,
  `db_ops._alternar_plano` ativa o seguinte (`PLAN_ROTATION`: A, B, C, D, E e
  volta para A). A rotacao segue a ordem das sessoes concluidas, nao o dia da
  semana; um dia perdido nao pula treino. Outros planos, como `Forca`, nao
  alternam; `/plano NOME` continua trocando manualmente.
- `Supino fechado (barra)` e `Remada alta (barra)` estao inativos para sessoes futuras.
- `Agachamento com barra nas costas` saiu dos planos A a E no schema 15 (o usuario nao quer barra atras da nuca); continua no plano `Forca` e no historico.
- Logs antigos de `Agachamento Zercher` voltam a alimentar a progressao desse exercicio (com retorno apos pausa e conversao por reps quando couber).
- Logs historicos de `Agachamento (barra)`, `Agachamento com barra nas costas`, `Zercher squat`, `Supino fechado (barra)`, `Remada alta (barra)` ou `Rosca martelo (barra H)` podem permanecer como historico.

### `limulus/db_ops.py`

Modulo SQLite para exercicios, logs de treino e dados de dieta.

- Banco versionado: `data/limulus.db`.
- Versao atual do esquema: `SCHEMA_VERSION = 16`.
- `training_sessions.started_at` e `completed_at` guardam horarios ISO com
  UTC-03:00; historicos migrados ficam nulos. `training_buttons` vincula token
  ao log e carga exibida. Cliques sao atomicos e invalidam botoes do log.
  Recuperacao considera somente a sessao mais recente, sem reabrir antigas.
- `schema_migrations` registra cada migracao aplicada. `init_db()` executa
  migracoes pendentes em ordem e rejeita bancos com versao futura.
- `get_session_summary(session_id)` calcula o resumo pos-treino e usa a sessao
  anterior com a mesma sequencia de exercicios para comparar volume.
- Tabela principal de exercicios: `exercises` (`name`, `sets`, `reps`, `sort_order`, `active`).
- `exercise_muscle_groups` relaciona exercicios a grupos principais e
  secundarios. `/volume` e dashboard usam essa tabela como fonte unica.
- `training_plans` e `training_plan_exercises` armazenam os planos A a E e
  Forca. Apenas um plano com exercicios fica ativo por vez; A a E alternam em
  sequencia ao concluir a sessao (`PLAN_ROTATION`, `_alternar_plano`).
- `body_weights` armazena o historico temporal de peso corporal.
- `waist_measurements` armazena o historico temporal da circunferencia da cintura.
- `body_profile` armazena altura e idade em um registro unico para os calculos
  corporais do dashboard.
- No schema atual, `body_weights` usa `weight_kg` e `recorded_at`; nao assumir
  colunas `weight` ou `date`. `body_profile` usa `height_cm` e `age_years`; nao
  assumir coluna `age`.
- SQLite e a fonte da verdade para exercicios.
- Mudancas de catalogo que devem valer para bancos novos tambem precisam atualizar `DEFAULT_EXERCISES` (plano A) ou `WEEKLY_PLANS` (planos A a E).

### `limulus/dashboard.py`

Dashboard local de volume de treino.

- `carregar_dados()` le `training_sessions` e `training_logs` no SQLite.
- O volume de cada linha e calculado como `sets x reps x weight`.
  Com a piramide, o log guarda so a carga de topo, entao o volume fica
  superestimado em cerca de 10%.
- Apenas logs com carga preenchida (`weight IS NOT NULL` e maior que zero) entram no dashboard.
- O HTML exibe uma pagina unica rolavel com indicadores de resumo, treino ativo
  do plano selecionado, grafico de evolucao do volume, mapa muscular anterior e posterior da ultima sessao,
  carga e RPE e 1RM estimado por exercicio, comparacao da ultima sessao com a
  anterior, equilibrio muscular, calendario de carga, grupos musculares, volume
  semanal, maiores evolucoes, recordes pessoais, PRs expandidos, carga vs RPE,
  alertas, filtros rapidos por segmento, relatorio semanal, peso corporal,
  cintura atual, IMC, relacao cintura/altura e dieta atual no final da pagina.
- IMC e relacao cintura/altura usam as medicoes mais recentes e sao
  indicadores derivados, nao diagnosticos.
- Os cards corporais mostram metas de referencia: IMC de 18,5 a 24,9,
  cintura/altura abaixo de 0,50 e os limites correspondentes de peso e cintura
  calculados pela altura cadastrada.
- Cada card com meta mostra uma barra de proximidade calculada como
  `limite da meta / valor atual`, limitada a 100%.
- Os quatro cards corporais mostram minigraficos de linha. Peso e IMC usam o
  historico de peso; cintura e cintura/altura usam o historico de cintura.
- A secao de dieta le `diet_entries`, `foods` e `diet_targets`, mostra uma lista
  unica de alimentos, consolida itens repetidos e compara os totais diarios de
  macros com as metas. Os micros aparecem em uma segunda linha de cards e na
  tabela por alimento e no total: fibra, omega 3, potassio, magnesio, zinco e
  vitaminas D e B6.
- O mapa muscular usa `exercise_muscle_groups`, expande grupos amplos em
  segmentos anatomicos visuais, deixa regioes sem treino transparentes e aumenta
  a opacidade vermelha conforme o volume relativo da ultima sessao. Ele
  usa pesos por exercicio quando houver regra especifica e representa volume
  atribuido, nao ativacao muscular medida.
- Graficos de dados do dashboard, como evolucao de volume, minigraficos
  corporais, carga vs RPE, comparacoes, PRs e filtros rapidos, usam Chart.js
  carregado por CDN com versao fixa.
  Nao trocar o mapa anatomico para biblioteca de graficos; ele continua SVG
  vetorial baseado nos assets anatomicos.
- As regioes musculares sao renderizadas diretamente dos paths vetoriais de
  `body-muscles` (Apache-2.0), numa SVG unica por vista. Os SVGs anatomicos de
  Termininja (CC BY-SA 3.0) ficam preservados em `limulus/assets/`.
  Manter os ativos e os textos das licencas em `docs/licencas/`.
- Os alertas nao tratam RPE 9 repetido ou carga mantida como problema isolado.
  Queda de RPE com a mesma carga aparece como consolidacao; RPE 10 persistente
  e reducao de carga apos RPE 10 aparecem como sinais de acompanhamento.
- Alertas por exercicio consideram apenas exercicios do plano ativo atual; logs
  historicos de exercicios inativos permanecem nos graficos e PRs, mas nao
  geram alertas.
- `Maiores evolucoes` considera apenas exercicios do plano ativo atual.
- O layout do dashboard deve permanecer escuro, cru e compacto, usando IBM
  Carbon Design System oficial via Carbon Web Components. Nao copiar nem
  reinventar tokens `cds`; os componentes oficiais `cds-*` devem cuidar do tema
  quando houver componente aplicavel. O HTML gerado nao deve exigir servidor ou
  build para abrir localmente, mas pode depender da CDN oficial configurada no
  arquivo para carregar os componentes.
- A secao "Ficha do personagem" mostra nivel, EXP, atributos, chefes,
  missoes e conquistas de `jogo.estado_atual()`; falha no jogo so omite a
  secao.
- `salvar_dashboard()` escreve `temp/dashboard-treino.html`.
- `gerar_dashboard.py` e o launcher de uso local.
- O bot chama a mesma funcao em `/dashboard`; o comando nao cria ou altera
  sessoes e nao envia o arquivo HTML.

### `limulus/video_ops.py`

- `extrair_frames(video_path, saida=None, fps=None, formato="jpg")` usa
  `ffmpeg` para gerar frames em uma pasta local.
- Formatos aceitos: JPG, JPEG, PNG, WebP e BMP. Arquivos existentes sao
  substituidos sem prompt interativo.
- `--todos` processa todos os videos de `videos/entrada/`; sem `--fps`, extrai
  todos os frames.
- `--instalar-ffmpeg` tenta instalar com winget, Homebrew ou apt-get.

### `limulus/backup_ops.py`

- `criar_backup()` usa a API de backup do SQLite.
- `exportar_dados()` gera JSON com versao de esquema e tabelas do projeto.
- `EXPORT_TABLES` inclui as tabelas do jogo (`jogo_estado`, `jogo_compras`
  e `jogo_pausas`).
- `restaurar_backup()` valida integridade, cria backup de seguranca quando o
  destino existe e substitui o banco somente depois de concluir a copia.

## Estado Local

Arquivos locais e secretos nao sao versionados:

- `session.json`
- `.env` (`TELEGRAM_TOKEN=...`)

Arquivos auxiliares SQLite nao sao versionados:

- `data/*.db-shm`
- `data/*.db-wal`
- `temp/dashboard-treino.html`
- `backups/`
- `exportacoes/`

Nao versionar segredos. Antes de alterar arquivos de estado local, verificar se a mudanca e necessaria.

## Diretrizes De Mudanca

- Preferir mudancas cirurgicas compativeis com o fluxo atual.
- Manter SQLite como fonte da verdade dos exercicios.
- Preservar a diferenca entre estado local e dados versionados.
- Preferir helpers existentes antes de criar novas abstracoes.

## Padrao De Commit

Usar Conventional Commits no titulo:

`feat: add sync command`

Requisitos:

- Titulo no formato `<type>: <title>` (`feat`, `fix`, `refactor`, `docs`, etc.).
- Corpo do commit e obrigatorio.
- Corpo deve explicar contexto tecnico, escopo e motivo da decisao.
