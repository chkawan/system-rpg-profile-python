# Como configurar

Passo a passo pra sair do clone até a ficha sendo atualizada automaticamente
no seu perfil do GitHub.

## 1. Clonar o repositório

```
git clone https://github.com/<seu-usuario>/<seu-repo>.git
cd <seu-repo>
```

## 2. Requisitos

Só precisa de Python 3.12+ e da biblioteca `requests` (usada pra falar com a
API do GitHub):

```
pip install requests
```

Isso só é necessário pra rodar com dados reais. Pra testar com dados de
exemplo (passo 4) não precisa instalar nada.

## 3. Personalizar o conteúdo que não vem da API

Alguns textos são escritos à mão, porque a API do GitHub não tem esse nível
de detalhe (bio, antecedentes, juramento). Edite direto em
`scripts/gerar_ficha.py`:

- `BIO_TEXTO` e `BIO_TABELA` — a bio e a tabelinha do "Pergaminho do
  Aventureiro" (origem, escola, campo de batalha...)
- `JURAMENTO_TEXTO` — o texto da seção "Juramento"
- `CORES` — cores por linguagem, só precisa editar se usar uma linguagem que
  não está na lista

Também vale revisar o `README.md`: os badges de contato (LinkedIn, e-mail,
portfólio, Instagram) e o `alt` da imagem são hardcoded — troque pelos seus.
**Não remova** os marcadores `<!-- ficha:carimbo:inicio -->...<!-- ficha:carimbo:fim -->`
nem a tag `<img src="ficha/ficha.svg">`: o script edita o README em volta
deles, se sumirem a ficha para de atualizar.

## 4. Testar localmente com dados de exemplo (sem token)

```
python scripts/gerar_ficha.py --previa
```

Isso gera `ficha/ficha.svg` com dados fictícios (`scripts/previa.py`, que não
vai para o repositório — veja o `.gitignore`). Use pra ver o layout/visual
sem gastar chamada de API nem precisar de token. Se o arquivo não existir
mais no seu clone, recrie um `scripts/previa.py` com a mesma estrutura do
dicionário que `buscar()` retorna (veja o próprio `gerar_ficha.py`).

## 5. Gerar um token do GitHub

O script busca seus dados reais via GraphQL (repositórios, estrelas,
linguagens, contribuições). Para isso precisa de um token:

1. Acesse **github.com → Settings → Developer settings → Personal access
   tokens**.
2. Crie um **token clássico** (mais simples) com o escopo **`repo`** — isso
   dá acesso de leitura aos seus repositórios privados também (necessário
   pra ver quantos repos privados você tem, estrelas, etc).
   - Se preferir um **fine-grained token**, dê permissão de repositório
     **"Metadata: Read-only"** apenas. **Não** adicione "Contents" — o
     script não lê conteúdo de arquivo nenhum, e esse escopo extra já
     quebrou o workflow antes (erro "Resource not accessible by personal
     access token") quando tentamos usar campos que dependem dele
     (`languages`, histórico de commit).
3. Copie o token gerado (começa com `ghp_` ou `github_pat_`) — você só vê
   ele uma vez.

## 6. Testar localmente com dados reais

```
export GH_TOKEN="seu-token-aqui"
export FICHA_LOGIN="seu-usuario-do-github"
python scripts/gerar_ficha.py
```

(No Windows PowerShell: `$env:GH_TOKEN="..."` e `$env:FICHA_LOGIN="..."`.)

Isso sobrescreve `ficha/ficha.svg` e atualiza o carimbo de data no
`README.md` com seus dados reais. Confira o resultado antes de automatizar.

## 7. Configurar o repositório no GitHub pra automatizar

O workflow (`.github/workflows/ficha.yml`) já existe e roda sozinho todo dia
às 6h UTC, a cada push que toque em `scripts/gerar_ficha.py`, ou manualmente.
Ele precisa de uma configuração no repositório, em **Settings → Secrets and
variables → Actions → aba Secrets** → *New repository secret* → nome
`FICHA_TOKEN`, valor o token do passo 5.

O usuário do GitHub (`FICHA_LOGIN`) já vem direto no `env:` do workflow
(`FICHA_LOGIN: chkawan`) — se for usar este repo pra outro perfil, edite
essa linha em `.github/workflows/ficha.yml` em vez de criar uma variável
separada (uma variável de repositório funcionaria também, via
`${{ vars.FICHA_LOGIN }}`, mas sem o job declarar `environment:` é fácil
confundir a aba Secrets com a aba Variables e ela não ser enxergada - direto
no YAML é mais simples e não depende de configuração externa).

Sem o secret, o workflow falha porque a API recusa a chamada.

## 8. Dar push e conferir

```
git add .
git commit -m "Configura a ficha pro meu perfil"
git push
```

Esse push já dispara o workflow (ele roda em qualquer push que toque em
`scripts/gerar_ficha.py` ou no próprio workflow). Acompanhe em **Actions**,
na aba do repositório no GitHub. Se passar, `README.md` e `ficha/ficha.svg`
são commitados automaticamente pelo `github-actions[bot]` com os seus dados
reais.

## Ajustes finos (opcional)

Tudo isso já vem calibrado, mas se quiser mexer:

- **Pesos dos atributos** (`atributos()`, em `gerar_ficha.py`) — cada
  atributo tem um `peso` que controla o quanto ele pesa de verdade; e um
  teto (`mx`) de referência pro valor "máximo" daquele sinal.
- **Vida/Vigor/Mana por classe** (`CLASSE_VITAIS`) — base e crescimento por
  nível de cada classe, calibrado com dados reais de dado de vida do D&D 5E.
- **Requisito de classe** (`determinar_classe`) — hoje exige um mínimo de
  pontos no atributo principal (e, pro Arqueiro, também no secundário).
