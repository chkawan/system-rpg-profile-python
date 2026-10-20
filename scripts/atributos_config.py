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
decide o desempate na distribuicao de pontos (ver DISTRIBUICAO_CONFIG
abaixo) - quando dois ou mais atributos saem com o mesmo valor bruto,
quem aparece primeiro aqui ganha a fatia maior do orcamento. Reordenar
as chaves muda esse desempate.

IMPORTANTE sobre PESO x DISTRIBUICAO: mudar o peso de um atributo so
muda o resultado final se isso tambem mudar a ORDEM do ranking (quem
fica em 1o, 2o...) - a fatia de cada posicao (ver DISTRIBUICAO_CONFIG)
e fixa, nao depende de quao mais alto ou baixo o valor bruto ficou. Se
voce mudar um peso e o 1o lugar continuar sendo o mesmo atributo, os
pontos finais na ficha NAO mudam, mesmo que o valor bruto (escala 0-100)
tenha mudado.
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


# Como o orcamento de pontos (nivel + bonus_inicial) e repartido entre os
# 6 atributos pra exibir na ficha - fica junto com ATRIBUTOS_CONFIG porque
# os dois se afetam na hora de testar (ver o aviso "PESO x DISTRIBUICAO"
# no comentario acima).
#
#   fatias_ranking      - fatia do orcamento que cada posicao do ranking
#                          leva: [0]=1o lugar, [1]=2o lugar, etc. Tem que
#                          ter 6 valores (um por atributo). Nao precisa
#                          somar 1.0 - e so repartido proporcionalmente.
#   bonus_inicial       - pontos extras somados ao nivel antes de
#                          repartir, iguais pra todo mundo (os "pontos
#                          livres de criacao de personagem" de qualquer
#                          RPG de mesa).
#   maximo_por_atributo - nenhum atributo pode passar desse valor na
#                          distribuicao final, mesmo que a fatia do
#                          ranking desse mais - o excedente e repartido
#                          de novo so entre quem ainda nao estourou.
#   minimo_para_classe  - quantos pontos (depois de repartido) um
#                          atributo precisa pra contar como requisito de
#                          classe (ver classes_config.py).
DISTRIBUICAO_CONFIG = {
    "fatias_ranking": [0.50, 0.30, 0.15, 0.10, 0.01, 0.01],
    "bonus_inicial": 10,
    "maximo_por_atributo": 30,
    "minimo_para_classe": 4,
}
