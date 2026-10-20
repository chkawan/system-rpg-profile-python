"""
Configuracao dos 6 atributos da ficha (Forca, Destreza, Constituicao,
Inteligencia, Sabedoria, Carisma). Edite os valores abaixo pra reorganizar
de onde cada atributo tira seu numero, sem precisar tocar no resto do
codigo (gerar_ficha.py so le esse dicionario, nao decide nada sozinho).

Cada atributo tem 4 campos:

  fonte  - qual dado alimenta esse atributo. Tem que ser uma das chaves
           que `derivar()` calcula (em gerar_ficha.py), depois de buscar
           tudo do GitHub. Fontes disponiveis hoje:
             total_repos        - repositorios (publicos + privados)
             media_commits_repo - media de commits por repositorio no ultimo ano
             anos               - anos de conta ativa no GitHub
             num_linguagens     - quantas linguagens principais distintas
             dias_ativos        - dias com pelo menos 1 contribuicao no ultimo ano
             seguidores         - numero de seguidores no GitHub
           Trocar a fonte de um atributo (ex: Destreza usar "dias_ativos"
           em vez de "media_commits_repo") muda de onde o numero vem, sem
           precisar editar nenhuma formula.

  rotulo - o texto que aparece do lado do numero na ficha, explicando de
           onde ele veio (ex: "repositórios erguidos"). So cosmetico, nao
           afeta o calculo.

  mx     - o "teto de referencia": o valor de `fonte` que voce considera
           ser 100% nesse atributo. Bater esse numero sempre da nota 100
           pro atributo, nao importa o peso (e matematico: nao tem jeito
           de escapar disso ajustando peso). Ex: mx=200 em Forca quer
           dizer "200 repositorios = Forca 100".

  peso   - o quao generosa ou exigente e a curva pra chegar no teto:
             peso > 1 -> generosa, sobe rapido mesmo com pouco input
             peso = 1 -> neutra, sobe junto com o log do valor bruto
             peso < 1 -> exigente, precisa de MUITO mais input pro mesmo
                         resultado
           Use peso baixo pra sinais faceis de "inflar" sem esforco real
           de verdade (ex: seguidor, ou commit em volume artificial).
           Use peso alto pra sinais dificeis de forjar (ex: anos de
           conta, que ninguem consegue acelerar).

IMPORTANTE sobre a ORDEM: a ordem das chaves neste dicionario tambem
decide o desempate na distribuicao de pontos (ver distribuir_pontos() e
RANKING_FATIAS em gerar_ficha.py) - quando dois ou mais atributos saem
com o mesmo valor bruto, quem aparece primeiro aqui ganha a fatia maior
do orcamento. Reordenar as chaves muda esse desempate.
"""

ATRIBUTOS_CONFIG = {
    "Força": {
        "fonte": "total_repos",
        "rotulo": "repositórios erguidos",
        "mx": 200,
        "peso": 0.5,
    },
    "Destreza": {
        "fonte": "media_commits_repo",
        "rotulo": "commits por repositório em média",
        "mx": 50,
        "peso": 0.5,
    },
    "Constituição": {
        "fonte": "anos",
        "rotulo": "anos de estrada sem parar",
        "mx": 15,
        "peso": 0.5,
    },
    "Inteligência": {
        "fonte": "num_linguagens",
        "rotulo": "linguagens estudadas",
        "mx": 20,
        "peso": 1.7,
    },
    "Sabedoria": {
        "fonte": "dias_ativos",
        "rotulo": "dias ativos no último ano",
        "mx": 365,
        "peso": 0.6,
    },
    "Carisma": {
        "fonte": "seguidores",
        "rotulo": "seguidores no reino",
        "mx": 6000,
        "peso": 0.1,
    },
}
