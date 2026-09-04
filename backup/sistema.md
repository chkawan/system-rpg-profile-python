# Sistema da Ficha — como tudo funciona

Documentação de referência do `scripts/gerar_ficha.py`: de onde vem cada
número, como cada seção é calculada, e quais são as regras/requisitos por
trás de cada mecânica. Serve tanto pra você lembrar a lógica quanto pra
qualquer edição futura no script.

---

## Índice

1. [Como o pipeline funciona](#1-como-o-pipeline-funciona)
2. [A fórmula base: `escala()`](#2-a-fórmula-base-escala)
3. [Banner (nome, classe, nível, linha)](#3-banner-nome-classe-nível-linha)
4. [Vitais — VIDA / MANA / VIGOR / EXP](#4-vitais--vida--mana--vigor--exp)
5. [Atributos](#5-atributos)
6. [Classe](#6-classe)
7. [Equipamento (repositórios fixados)](#7-equipamento-repositórios-fixados)
8. [Habilidades](#8-habilidades)
9. [Pergaminho do Aventureiro](#9-pergaminho-do-aventureiro)
10. [Conquistas](#10-conquistas)
11. [Missões](#11-missões)
12. [Juramento](#12-juramento)
13. [Taverna](#13-taverna)
14. [Paleta de cores](#14-paleta-de-cores)
15. [Ícones](#15-ícones)
16. [Atualização automática](#16-atualização-automática)
17. [Limitações conhecidas](#17-limitações-conhecidas)

---

## 1. Como o pipeline funciona

```
buscar()  →  derivar()  →  montar_svg()  →  preencher()
 (GitHub)     (contas)      (monta o SVG)   (carimbo no README)
```

- **`buscar(login)`** — faz uma única query GraphQL pra API do GitHub e
  traz: dados do perfil, todos os repositórios próprios (até 100, não-fork)
  e os repositórios **fixados** (pinned) no perfil.
- **`derivar(d)`** — pega o bruto e calcula tudo que é contagem/agregação:
  quantos repos são privados, total de estrelas, linguagens usadas, idade
  da conta, nível, lista de missões, etc.
- **`montar_svg(d)`** — usa os dados derivados pra calcular atributos,
  classe, vitais, e gera o SVG final substituindo os placeholders
  `{{...}}` do template `ficha/base.svg`.
- **`preencher()`** — só troca o carimbo de data no `README.md` entre os
  marcadores `<!-- ficha:carimbo:inicio -->` e `<!-- ficha:carimbo:fim -->`.

Roda em dois modos:
```
python scripts/gerar_ficha.py            # busca de verdade no GitHub (usa GH_TOKEN)
python scripts/gerar_ficha.py --previa   # usa scripts/previa.py, sem tocar na API
```

---

## 2. A fórmula base: `escala()`

Quase todo atributo/conquista usa essa função pra transformar uma
contagem bruta (que pode ir de 0 a milhares) num número pequeno e estável:

```python
def escala(v, mx, teto=20):
    return max(1, min(teto, round(math.log10(v + 1) / math.log10(mx + 1) * teto)))
```

- **`v`** = valor real (ex: número de repositórios)
- **`mx`** = valor de referência que representa "praticamente no teto"
- **`teto`** = nota máxima possível (padrão 20)

É uma escala **logarítmica**, não linear: os primeiros pontos custam pouco
(sair de 0 pra 5 repos já sobe bastante a nota), e cada ponto depois
fica progressivamente mais caro (sair de 100 pra 150 repos quase não
muda a nota). O resultado nunca é menor que 1 nem maior que `teto`.

---

## 3. Banner (nome, classe, nível, linha)

| Campo | Fonte | Cálculo |
|---|---|---|
| **Nome** | `user.name` do GitHub | se não tiver nome público, usa o login |
| **Classe** | calculada | ver [seção 6](#6-classe) |
| **Nível** | calculado | fórmula abaixo |
| **Linha** (subtítulo) | localização + data de criação da conta + total de obras | `"{local} . jornada iniciada em {ano da conta} . {total_repos} obras"` |

**Fórmula do Nível:**

```
nivel = clamp( escala(total_repos, 200, 40) + escala(estrelas, 5000, 35) + anos_de_conta × 2 , 1, 99 )
```

Ou seja: metade vem do volume de repositórios, um pouco menos da metade
vem de estrelas recebidas, e cada ano de conta soma 2 pontos direto (sem
escala logarítmica).

---

## 4. Vitais — VIDA / MANA / VIGOR / EXP

As três primeiras barras têm o **teto** (valor máximo) preso a um
atributo, e o **preenchimento atual** vem de um sinal de atividade
recente relacionado — sempre limitado a esse teto:

| Vital | Teto (máximo) | Preenchimento atual |
|---|---|---|
| **VIDA** | `Constituição × 25` | `min(teto, 40 + repos_com_push_recente × 15)` |
| **MANA** | `Inteligência × 25` | `min(teto, 30 + estrelas × 3)` |
| **VIGOR** | `Força × 25` | `min(teto, commits_no_ano)` |
| **EXP** | fixo em `1000` | `(nível % 10) × 100 + 40` |

A lógica é a mesma de um RPG de mesa: o atributo define seu **potencial**
(quanto você *pode* ter), e a atividade recente define o quanto desse
potencial está **preenchido agora**.

---

## 5. Atributos

Cada atributo físico/mental do RPG foi mapeado pro sinal de programação
mais parecido com o que ele mede numa mesa de RPG de verdade:

| Atributo | O que mede na mesa | Sinal usado | Fórmula (nota 1–20) |
|---|---|---|---|
| **Força** | músculo, volume erguido | total de repositórios | `escala(total_repos, 200)` |
| **Destreza** | reflexo, velocidade de reação | repositórios com push nos últimos 90 dias | `escala(recentes, 50)` |
| **Constituição** | fôlego, tempo aguentando o ritmo | anos desde a criação da conta | `escala(anos, 15)` |
| **Inteligência** | repertório de estudo | nº de linguagens diferentes usadas | `escala(nº linguagens, 20)` |
| **Sabedoria** | disciplina / força de vontade | commits no último ano | `escala(commits, 3000)` |
| **Carisma** | presença social | seguidores no GitHub | `escala(seguidores, 5000)` |

Cada um também tem uma frase-descrição embaixo do valor (ex: *"29
repositórios erguidos"*), que é só o número bruto por extenso.

---

## 6. Classe

A classe **não vem mais da linguagem principal** (isso era o sistema
antigo). Hoje ela é calculada: cada uma das 6 classes corresponde a um
atributo dominante, e as 3 classes ligadas a um Vital (Guerreiro, Mago,
Aventureiro) ganham um bônus de até 5 pontos proporcional ao quanto
aquele vital está preenchido:

| Classe | Fórmula de pontuação | Atributo base |
|---|---|---|
| **Guerreiro** | `Força + (% de VIGOR preenchido) × 5` | Força |
| **Arqueiro** | `Destreza` | Destreza |
| **Aventureiro** | `Constituição + (% de VIDA preenchida) × 5` | Constituição |
| **Mago** | `Inteligência + (% de MANA preenchida) × 5` | Inteligência |
| **Curandeiro** | `Sabedoria` | Sabedoria |
| **Ladino** | `Carisma` | Carisma |

A classe escolhida é sempre a de **maior pontuação**. Título, complemento
e ícone (retrato + boneco de fundo do Equipamento) de cada uma:

| Classe | Título | Complemento |
|---|---|---|
| Guerreiro | Guerreiro, o Forjador | ergue tudo na base da força bruta |
| Arqueiro | Arqueiro, o Caçador de Bugs | acerta de longe, sem falhar |
| Aventureiro | Aventureiro, o Sobrevivente | sobrevive a qualquer legado |
| Mago | Mago, o Tecelão | tece lógica onde só havia caos |
| Curandeiro | Curandeiro, o Guardião | mantém tudo de pé |
| Ladino | Ladino, o Explorador | acha a brecha que ninguém viu |

O ícone da classe atual aparece em dois tamanhos: pequeno (64px) como
retrato no banner, e grande (170px, 16% de opacidade) como o "boneco" de
fundo atrás dos slots de Equipamento.

---

## 7. Equipamento (repositórios fixados)

Layout em cruz — 5 slots imitando um boneco de equipamento de RPG:

```
              ( elmo )
( arma esq )( armadura )( arma dir )
              ( bota )
```

**Cada slot é um dos seus repositórios fixados (pin) no GitHub**, na
ordem em que foram fixados (1º pin → elmo, 2º → arma esquerda, 3º →
armadura, 4º → arma direita, 5º → bota). Repositórios além do 5º são
ignorados; slots sem repo correspondente ficam com moldura tracejada e
o texto "vazio".

- **Cor do slot** = cor da linguagem principal do repositório
- **Nome do slot** = nome do repo passado pelo mesmo humanizador das
  Missões ([ver seção 11](#11-missões)), truncado em 12 caracteres

**Requisito pra aparecer aqui:** ter um repositório fixado no seu perfil
GitHub (`github.com/<usuário>` → "Customize your pins" → marcar até 6,
salvar). Sem isso, os 5 slots aparecem vazios.

---

## 8. Habilidades

Lista as linguagens de programação **reais**, extraídas de
`primaryLanguage` de cada repositório próprio (até 100 mais recentes).
Mostra até 7 linguagens, ordenadas da mais usada pra menos usada.

```
fatia da linguagem = (nº de repos com essa linguagem) / (nº total de repos com alguma linguagem definida)
nível (barra + %) = fatia × 100, arredondado
```

Repositórios sem linguagem detectável (ex: só documentação) não entram
na contagem do total.

---

## 9. Pergaminho do Aventureiro

**Conteúdo 100% estático** — não vem da API do GitHub. É o texto de
bio/apresentação que você edita direto no script, nas constantes:

- `BIO_TEXTO` — o parágrafo de apresentação
- `BIO_TABELA` — os 4 pares rótulo/valor (Origem, Escola, Campo de
  batalha, Marca registrada)

Pra mudar o texto, edita essas duas constantes no topo de
`scripts/gerar_ficha.py` e roda o workflow de novo.

---

## 10. Conquistas

Sistema de tiers, igual ranqueado de jogo — 10 tiers, cada um com cor
própria:

| # | Tier | Cor |
|---|---|---|
| 1 | Ferro | `#53585c` |
| 2 | Bronze | `#8a5a3c` |
| 3 | Prata | `#9aa5ad` |
| 4 | Ouro | `#e0a526` |
| 5 | Platina | `#2fb8a6` |
| 6 | Esmeralda | `#1fae64` |
| 7 | Diamante | `#4f7fdb` |
| 8 | Mestre | `#a142c9` |
| 9 | Grão-Mestre | `#e0393e` |
| 10 | Desafiante | `#f4e04d` |

O tier de cada conquista é o **maior limiar que o valor atual alcança**
(`tier_de()` percorre os 10 limiares e fica com o último que o valor
ainda cobre). Se não alcançar nem o 1º limiar, aparece "Sem tier"
(cinza `#5a5245`).

A barra de progresso mostra `valor atual / próximo limiar` dentro do
tier corrente (ou "MAX" se já estiver no tier mais alto).

**As 5 conquistas e seus 10 limiares cada:**

| Conquista | Sinal usado | Fe | Br | Pr | Ou | Pl | Es | Di | Me | GM | De |
|---|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| **Ritmo de Forja** | commits no último ano | 1 | 50 | 150 | 300 | 500 | 750 | 1000 | 1500 | 2500 | 4000 |
| **Cofres Selados** | repositórios privados | 1 | 2 | 4 | 7 | 12 | 20 | 35 | 55 | 80 | 120 |
| **Magias Dominadas** | nº de linguagens diferentes | 1 | 2 | 3 | 4 | 6 | 8 | 10 | 13 | 16 | 20 |
| **Anos de Jornada** | anos de conta ativa | 0.5 | 1 | 2 | 3 | 4 | 5 | 7 | 9 | 12 | 15 |
| **Portais Abertos** | repos públicos com URL ativa | 1 | 2 | 4 | 6 | 9 | 13 | 18 | 25 | 35 | 50 |

As 5 medalhas aparecem **ordenadas do tier mais alto pro mais baixo** da
esquerda pra direita (empates mantêm a ordem da tabela acima).

Por que essas 5: são os sinais que mais pesam pra quem tá avaliando um
perfil pra contratação — consistência (Forja), trabalho
protegido/profissional (Cofres), ferramental (Magias), experiência
(Jornada) e projetos realmente publicados (Portais).

---

## 11. Missões

Cada missão é um repositório seu, tratado como uma "quest":

**Seleção** (`selecionar_missoes`):
- **Privados**: os até **6 mais recentes** (por data de push), todos
  entram — não importa se têm URL ou não. São os "projetos pessoais de
  verdade".
- **Públicos**: os até **4 mais recentes**, mas **só entram se tiverem
  uma URL ativa** (campo "Website" preenchido no GitHub). Repo público
  sem link não vira missão.
- O repositório de perfil (aquele com o mesmo nome do seu login) é
  sempre excluído.

**Ordem de exibição** (diferente da ordem de seleção): concluídas
primeiro, depois em andamento; dentro de cada grupo, ordem alfabética
pelo nome humanizado.

**Status:**
```
tem_url = True  → ícone de check dourado + "CONCLUÍDA"
tem_url = False → ícone de pergaminho + "EM PROGRESSO"
```

**Nome da missão** (`nome_missao`): como a maioria dos repos usa nome de
gerador (ex: `tool-password-generator-python`) em vez de um nome de
projeto de verdade, o humanizador:
1. remove um prefixo genérico do início, se houver
   (`tool`, `tools`, `system`, `systems`, `sistema`, `sistemas`, `api`,
   `bot`, `app`, `projeto`, `template`)
2. remove um sufixo técnico do final, se houver
   (`python`, `py`, `php`, `javascript`, `js`, `typescript`, `ts`,
   `django`, `node`, `html`, `css`, `shell`)
3. remove conectivo solto que sobrar no início (`de`, `da`, `do`, `das`,
   `dos`, `e`, `em`, `com`, `para`)
4. capitaliza o resto, mantendo conectivos internos em minúsculo

Exemplo: `tool-password-generator-python` → **Password Generator**.

**Descrição** (itálico, opcional): usa a `description` real do
repositório no GitHub, quando existe. Repos sem descrição preenchida no
GitHub simplesmente não mostram essa linha.

**Arma equipada**: a `primaryLanguage` do repositório, como um
quadradinho colorido + nome.

---

## 12. Juramento

**Conteúdo estático**, igual o Pergaminho — não vem da API. Texto na
constante `JURAMENTO_TEXTO`, no topo do script. Pra editar, muda a
constante e roda o workflow de novo.

---

## 13. Taverna

Seção só de **cabeçalho** dentro do SVG (ícone + título) — sem conteúdo
embutido nela. Os links de contato reais (LinkedIn, Email, Portfólio,
Instagram) ficam como badges clicáveis direto no `README.md`, logo
abaixo da imagem da ficha, porque um SVG carregado via `<img>` no
GitHub **não permite links clicáveis** dentro dele.

---

## 14. Paleta de cores

```python
ACENTO = "#986dff"   # fixo, a mesma cor do portfólio (kawandev.com.br)
```

Antes a cor de destaque mudava conforme a linguagem principal; hoje é
fixa, pra manter identidade visual com o portfólio.

A partir desse único tom, a função `tom(hexcor, saturação, luminosidade)`
gera toda a paleta derivada (reconvertendo o matiz do acento com
saturação/luminosidade diferentes):

| Token | Saturação | Luminosidade | Uso |
|---|---|---|---|
| `INK` | 0.28 | 6% | fundo geral do SVG |
| `STONE` | 0.24 | 12% | painéis/molduras |
| `LIT` | 0.22 | 22% | realce claro do banner |
| `DARK` | 0.30 | 3% | trilhos escuros das barras, moldura de slot |
| `GOLD` | 0.90 | 64% | destaque principal (títulos, réguas, bordas) |

`VELLUM` (`#e6d3a3`) e `DIM` (`#8a7c62`) são fixos, não derivados do
acento — são o texto principal e o texto secundário/dim, respectivamente.

---

## 15. Ícones

Dois sistemas convivem no script:

1. **`img_icone(caminho, tamanho)`** — o principal hoje. Lê um PNG de
   `ficha/icones/` (baixado do Flaticon, redimensionado e otimizado —
   64px pros ícones pequenos, 160–170px pros retratos de classe) e
   devolve uma função que embute a imagem via base64 direto no SVG,
   centralizada em `(cx, cy)`. Tem cache (`_CACHE_IMG`) pra não reler o
   arquivo do disco toda vez que o mesmo ícone é usado.
2. **Vetores desenhados à mão** — sobraram só em dois lugares: o
   contorno do brasão/escudo das medalhas de Conquista (`svg_medalha`) e
   o slot vazio de Equipamento (moldura tracejada + "+").

Pasta `ficha/icones/`:
```
class/        → retratos das 6 classes
conquistas/   → 5 ícones das medalhas
secoes/       → ícones de cabeçalho de cada seção + status de missão
```

---

## 16. Atualização automática

Workflow `.github/workflows/ficha.yml`, roda em 3 gatilhos:

| Gatilho | Quando |
|---|---|
| `schedule` | todo dia às **6h UTC** (cron `0 6 * * *`) |
| `push` | quando `scripts/gerar_ficha.py` ou o próprio workflow mudam, na branch `main` |
| `workflow_dispatch` | manual, em Actions → Forjar ficha → Run workflow |

Usa o secret `FICHA_TOKEN` (variável `GH_TOKEN` dentro do script) pra
autenticar na API GraphQL do GitHub. Se o token expirar/for revogado, o
script já detecta e falha com uma mensagem clara em vez de erro
genérico (`buscar()` valida se a resposta tem `data` antes de seguir).

---

## 17. Limitações conhecidas

- **Repositórios privados só aparecem se o token tiver escopo pra
  enxergá-los** (PAT clássico com `repo` completo, ou fine-grained com
  acesso explícito aos privados). Sem isso, ficam de fora de tudo:
  Habilidades, Atributos, Conquistas, Missões.
- **A API do GitHub não expõe framework/plataforma/stack** — só
  linguagem. Por isso o antigo "Armaduras curado à mão" foi trocado
  pelos repositórios fixados (que você controla direto no GitHub).
- **`repositories(first: 100)`** busca só os 100 repositórios mais
  recentes por push — se você tiver mais que isso, os mais antigos não
  entram nas contagens de linguagem/estrelas (mas o total de
  repositórios usa `repositories.totalCount`, que é exato).
- **Bio, tabela do Pergaminho e texto do Juramento são estáticos** —
  precisam ser editados manualmente no script quando sua história mudar.
