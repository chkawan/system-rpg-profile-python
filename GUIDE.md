# Como funciona a ficha

Explica o sistema de RPG por trás da ficha: como o XP é calculado, como o
nível decide quanto ponto de atributo você tem, qual o requisito de cada
classe, e onde mexer em cada peça. Para instalar/configurar o projeto do
zero, veja o [START.md](START.md) — este arquivo é sobre as regras do jogo,
não sobre colocar o robô no ar.

Tudo isso vive em `scripts/gerar_ficha.py`. Os nomes entre parênteses ao
longo do texto são os nomes exatos de função/constante no arquivo, pra você
achar rápido com Ctrl+F.

## 1. XP — de onde vem e quanto vale cada coisa

XP mede esforço real, não popularidade (não existe XP por seguidor ou por
estrela recebida). Vem de 4 fontes, cada uma multiplicada por **3** no
final (`MULT_XP`):

| Fonte | Valor por unidade | Observação |
|---|---|---|
| Anos de conta ativa | 100 XP/ano | Direto, sem teto |
| Commits no último ano | 25 XP/commit | **Com teto** — veja abaixo |
| Repositórios que você tem | 100 XP/repo | Conta privados e públicos |
| Linguagens diferentes, por repositório | 10 XP/linguagem | Um repo com 5 linguagens dá 50 XP só de bônus, **com filtro** — veja abaixo |

Fórmula (`derivar()`):
```
commits_xp = min(commits_do_ano, total_de_repos × 50)
xp = (anos×100 + commits_xp×25 + total_repos×100 + bonus_linguagem) × 3
```

**Por que o teto nos commits (`TETO_COMMITS_POR_PROJETO = 50`)**: sem ele,
alguém com 5.000 commits espalhados em só 3 repos ganhava 10x mais XP que um
veterano de 10 anos com 50 projetos — commit em volume infinito dentro de
pouco projeto não deveria valer mais que uma carreira inteira diversificada.
Não temos o commit de cada repo individualmente (exigiria permissão de
token que já quebrou o workflow uma vez — veja o aviso no START.md), então
aproximamos: no máximo 50 commits "contam" por repositório que você tem. Se
você tem 50 repos, pode usar até 2.500 commits nessa conta; se tem 3, só
150. Isso não limita o nível nem esconde commits de verdade, só limita
quanto XP um volume desproporcional-pra-poucos-projetos pode gerar.

**Por que o filtro de bytes (`MIN_BYTES_LINGUAGEM = 500`)**: um repo com um
único arquivo de config em outra linguagem (tipo um `.gitignore` detectado
como shell) não deveria contar como "linguagem dominada" pra efeito de
bônus. Só linguagem com pelo menos 500 bytes de código naquele repositório
entra na conta.

**Esse campo de linguagens por repositório (`languages` no GraphQL) exige
permissão de leitura de conteúdo no token** — veja a seção de token no
START.md. Se o workflow falhar com "Resource not accessible by personal
access token" apontando pra esse campo, é isso.

## 2. Nível — como o XP se transforma em nível

Nível não tem teto artificial (`nivel_de_xp()`) — sobe enquanto houver XP
suficiente, sem limitador. O custo pra avançar de um nível pro próximo
cresce **linearmente**:

```
custo(nível) = nível × 100 × 1.2
```

Nível 1→2 custa 120, 2→3 custa 240, 3→4 custa 360, e assim por diante
(sempre +120 de custo a cada nível). O nível acumulado é a soma de todos os
custos já pagos. A barra de EXP na ficha mostra o **progresso dentro do
nível atual** — quanto XP sobrou depois de pagar todos os níveis anteriores,
sobre o custo do próximo (`progresso_nivel()`) — diferente de Vida/Mana/
Vigor, que sempre aparecem cheias.

O número do nível, no medalhão do banner, tem caixa de tamanho fixo — se o
nível ganhar muitos dígitos (3, 4+), a fonte encolhe automaticamente
(`NIVEL_FONTE`) pra não vazar da borda. O valor do nível em si nunca é
cortado, só o tamanho da letra.

## 3. Atributos — de onde vem cada um e o peso de cada

Os 6 atributos vêm de sinais do GitHub, passados pela função `escala()`:

```
bruto   = log10(valor + 1) / log10(teto_de_referencia + 1)
curva   = bruto ^ (1 / peso)
valor   = round(curva × 100), entre 1 e 100
```

`peso` controla a dificuldade da curva: **peso > 1** sobe rápido (curva
generosa, pouco esforço já dá nota boa); **peso < 1** exige muito mais
input pro mesmo resultado (curva exigente — serve pra sinal fácil de
inflar sem esforço real).

Bater exatamente o teto de referência sempre dá **100**, pra qualquer
atributo, não importa o peso — é matemático (`log10(mx+1)/log10(mx+1) = 1`
sempre). O peso só decide o quão rápido você chega lá, não o valor no topo.

| Atributo | Fonte do valor | Teto de referência | Peso |
|---|---|---|---|
| Força | nº de repositórios | 200 | 0,8 |
| Destreza | commits por repositório em média | 50 | 0,4 |
| Constituição | anos de conta ativa | 15 | 1,0 |
| Inteligência | nº de linguagens principais estudadas | 20 | 1,3 |
| Sabedoria | dias ativos no calendário do último ano | 365 | 1,2 |
| Carisma | nº de seguidores | 6.000 | 0,3 |

Tudo isso está em `atributos()`. Dá pra ler esses 6 valores (1 a 100) como
"quantos % do teto daquele sinal você já bateu" — eles **não** são o
número final mostrado na ficha (isso é o próximo passo), e também não são
os mesmos pontos usados em Vida/Vigor/Mana: lá o valor bruto entra
multiplicado por `0.6` em vez de `2` (ver seção 6), pra manter a mesma
contribuição máxima de antes da escala virar 0-100.

## 4. Distribuição de pontos — como o nível vira atributo na ficha

O número mostrado em cada atributo na ficha **não** é o valor bruto do
passo 3. É um orçamento de pontos que soma exatamente a `nível + 10`
(os 10 são o bônus de criação de personagem, igual a todo RPG de mesa
clássico — `BONUS_INICIAL`), repartido pelo **ranking** de cada atributo,
não pelo valor bruto (`distribuir_pontos()`):

| Posição no ranking | Fatia do orçamento |
|---|---|
| 1º lugar | 40% |
| 2º lugar | 30% |
| 3º lugar | 15% |
| 4º lugar | 10% |
| 5º lugar | 1% |
| 6º lugar | 1% |

Por que por **posição**, não por valor: sinal de GitHub costuma vir
parecido entre os 6 atributos (13, 14, 15...) — repartir proporcional ao
valor bruto não separava nada de verdade. Garantir que o 1º lugar sempre
leva bem mais que o 6º, independente de quão perto os valores brutos
estavam, cria separação de verdade.

Nenhum atributo passa de **30 pontos** nessa distribuição (`maximo=30` em
`distribuir_pontos()`), mesmo que a fatia desse mais — quem estoura o teto
fica preso em 30 e o excedente é repartido de novo só entre quem ainda não
estourou, pelo método dos restos maiores (Hamilton), que garante a soma
final bater exato com o orçamento.

## 5. Classe — requisito de cada uma

A classe é decidida por `determinar_classe()`, usando o orçamento de pontos
do passo 4 (não o valor bruto do passo 3). Cada classe exige um mínimo
(`minimo=4`) no seu atributo principal:

| Classe | Requisito |
|---|---|
| Guerreiro | Força ≥ 4 |
| Arqueiro | Destreza ≥ 4 **e** Sabedoria ≥ 4 (os dois) |
| Ladino | Destreza ≥ 4 (e Sabedoria < 4 — senão vira Arqueiro) |
| Mago | Inteligência ≥ 4 |
| Curandeiro | Sabedoria ≥ 4 |
| Aventureiro | Nenhum dos acima bateu o mínimo (fallback) |

Isso é o mesmo molde do requisito de multiclasse do D&D 5e: a maioria das
classes pede só um atributo, mas o Arqueiro (Patrulheiro) pede dois ao
mesmo tempo, igual ao requisito real de Destreza 13 e Sabedoria 13. Carisma
não é requisito de nenhuma classe.

Se mais de uma classe bate o requisito, vence a de maior pontuação. O
Arqueiro usa o **menor** entre Destreza e Sabedoria pra essa comparação
(não a soma) — senão a classe dupla ganhava vantagem injusta sobre as de
atributo único só por somar dois valores médios.

Em nível muito baixo (1-2), o orçamento de pontos (mesmo com o bônus de 10)
costuma ser pequeno demais pra bater o mínimo de 4 em qualquer atributo —
todo personagem recém-criado cai em **Aventureiro** até se especializar.

## 6. Vida, Vigor e Mana — como cada classe escala

Cada classe tem sua própria tabela de base + crescimento por nível, em
`CLASSES_CONFIG` (`scripts/classes_config.py`):

```
vida_max  = vida_base  + vida_por_nivel  × (nível − 1) + Constituição × 0.6
vigor_max = vigor_base + vigor_por_nivel × (nível − 1) + atributo_de_vigor × 0.6
mana_max  = mana_base  + mana_por_nivel  × (nível − 1) + atributo_de_mana × 0.6
```

| Classe | Vida (base/nível) | Vigor (base/nível, atributo) | Mana (base/nível, atributo) |
|---|---|---|---|
| Guerreiro | 10 / 6 | 14 / 6, Força | 4 / 1, Inteligência |
| Arqueiro | 10 / 6 | 12 / 5, Destreza | 4 / 1, Sabedoria |
| Ladino | 8 / 5 | 11 / 5, Destreza | 5 / 1, Inteligência |
| Aventureiro | 12 / 7 | 10 / 4, Constituição | 5 / 1, Inteligência |
| Mago | 6 / 4 | 4 / 1, Força | 13 / 6, Inteligência |
| Curandeiro | 8 / 5 | 5 / 2, Força | 12 / 5, Sabedoria |

Os números de Vida vêm direto do dado de vida real de cada classe no D&D
5E (d10 pro Guerreiro/Patrulheiro, d8 pro Clérigo/Ladino, d6 pro Mago,
d12 pro Aventureiro — que não tem equivalente real, então usa o dado mais
resistente, por ser "o sobrevivente"). Vigor não existe no D&D (lá só tem
Vida e Magia) — é invenção nossa pra classe física ter recurso próprio,
calibrada à mão pra ficar coerente com a Vida.

**Atual sempre é igual ao máximo** em Vida/Vigor/Mana — a ficha retrata o
personagem em pleno vigor, não no meio de uma missão com recurso gasto.
(Diferente do EXP, que mostra progresso de verdade — ver seção 2.)

## 7. Onde configurar cada coisa

Tudo isso é editável sem tocar no `gerar_ficha.py`, em arquivos de
configuração separados (todos em `scripts/`):

| Quero mudar... | Arquivo | O quê |
|---|---|---|
| Fonte/peso/teto de cada atributo, e a ordem de desempate | `atributos_config.py` | `ATRIBUTOS_CONFIG` |
| Fatia do ranking, bônus inicial, teto por atributo na distribuição | `atributos_config.py` | `DISTRIBUICAO_CONFIG` |
| Requisito, Vida/Vigor/Mana, título e flavor text de cada classe | `classes_config.py` | `CLASSES_CONFIG` |
| Quanto XP vale cada coisa (ano/commit/projeto/linguagem) | `xp_config.py` | `XP_CONFIG` |
| Custo de nível | `xp_config.py` | `NIVEL_CONFIG` |
| Tiers (patentes) e limiares das 5 conquistas | `conquistas_config.py` | `TIERS`, `CONQUISTAS` |
| Bio, antecedentes, juramento (texto que não vem da API) | `gerar_ficha.py` | `BIO_TEXTO`, `BIO_TABELA`, `JURAMENTO_TEXTO` |

O último item (bio/juramento) continua direto no `gerar_ficha.py` de
propósito — é conteúdo pessoal do seu perfil, não balanceamento de jogo.

Pra instalar o projeto do zero (token, secrets, workflow), veja o
[START.md](START.md).
