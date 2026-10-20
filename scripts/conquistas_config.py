"""
Configuracao dos tiers (patentes) e das 5 conquistas da ficha. Edite os
valores abaixo sem precisar tocar em gerar_ficha.py.

TIERS - os 10 níveis de patente, do mais baixo ao mais alto, cada um com
sua cor. Quando uma conquista bate o ultimo limiar, ela fica no tier mais
alto (Desafiante).

CONQUISTAS - lista de dicionarios, um por conquista:
  nome      - titulo mostrado na ficha
  fonte     - qual dado usar (tem que ser uma chave que `derivar()`
              calcula em gerar_ficha.py - as mesmas fontes disponiveis
              pra atributos_config.py: total_repos, anos, num_linguagens,
              dias_ativos, seguidores, media_commits_repo, commits,
              selados, com_url, estrelas, xp, nivel...)
  descricao - frase curta embaixo da medalha, explicando o que faz subir
  icone     - caminho do PNG em ficha/icones/conquistas/
  limiares  - lista de 10 valores, um por tier (Ferro a Desafiante). Bater
              o valor do tier N (ou mais) classifica a conquista nesse
              tier. Tem que ter exatamente 10 valores, crescentes.
"""

TIERS = [
    ("Ferro", "#53585c"),
    ("Bronze", "#8a5a3c"),
    ("Prata", "#9aa5ad"),
    ("Ouro", "#e0a526"),
    ("Platina", "#2fb8a6"),
    ("Esmeralda", "#1fae64"),
    ("Diamante", "#4f7fdb"),
    ("Mestre", "#a142c9"),
    ("Grão-Mestre", "#e0393e"),
    ("Desafiante", "#f4e04d"),
]
SEM_TIER = ("Sem tier", "#5a5245")

# as 5 conquistas que mais pesam pra quem esta avaliando um perfil pra
# contratacao: consistencia, trabalho protegido/profissional, ferramental,
# experiencia e projetos realmente publicados.
CONQUISTAS = [
    {
        "nome": "Ritmo de Forja",
        "fonte": "commits",
        "descricao": "commits no último ano",
        "icone": "conquistas/forja.png",
        "limiares": [1, 50, 150, 300, 500, 750, 1000, 1500, 2500, 4000],
    },
    {
        "nome": "Cofres Selados",
        "fonte": "selados",
        "descricao": "repositórios privados",
        "icone": "conquistas/cofre.png",
        "limiares": [1, 2, 4, 7, 12, 20, 35, 55, 80, 120],
    },
    {
        "nome": "Magias Dominadas",
        "fonte": "num_linguagens",
        "descricao": "linguagens diferentes",
        "icone": "conquistas/magias.png",
        "limiares": [1, 2, 3, 4, 6, 8, 10, 13, 16, 20],
    },
    {
        "nome": "Anos de Jornada",
        "fonte": "anos",
        "descricao": "anos de conta ativa",
        "icone": "conquistas/ano.png",
        "limiares": [0.5, 1, 2, 3, 4, 5, 7, 9, 12, 15],
    },
    {
        "nome": "Portais Abertos",
        "fonte": "com_url",
        "descricao": "repos com link no ar",
        "icone": "conquistas/portal.png",
        "limiares": [1, 2, 4, 6, 9, 13, 18, 25, 35, 50],
    },
]
