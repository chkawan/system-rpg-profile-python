"""
Configuracao de quanto XP cada coisa vale, e do custo de nivel. Edite os
valores abaixo pra ajustar o jogo sem tocar em gerar_ficha.py.

XP_CONFIG:
  por_ano                   - XP por ano de conta ativa no GitHub
  por_commit                - XP por commit (contribuicoes do ultimo ano,
                               ja limitado por teto_commits_por_projeto)
  por_projeto                - XP por repositorio que voce tem
  por_linguagem_no_projeto   - XP por linguagem diferente DENTRO de cada
                               repositorio (um repo com 5 linguagens da
                               5x esse valor so de bonus, alem do
                               "por_projeto")
  teto_commits_por_projeto   - quantos commits no maximo contam por
                               repositorio que voce tem, antes de aplicar
                               "por_commit". Sem isso, 5000 commits num
                               unico repo valeriam mais que 10 anos de
                               carreira espalhados em 50 projetos - nao
                               temos commit por repo individual (exigiria
                               permissao de token que ja quebrou o
                               workflow), entao aproxima com
                               total_repos x teto_commits_por_projeto.
  min_bytes_linguagem        - bytes minimos de codigo numa linguagem,
                               dentro de um repositorio, pra ela contar
                               no bonus "por_linguagem_no_projeto". Filtra
                               linguagem que so apareceu de raspao (tipo
                               1 arquivo de config detectado errado).
  multiplicador_final        - multiplica a soma de tudo no final, pra
                               premiar quem tem mais projeto/commit de
                               verdade.

NIVEL_CONFIG:
  custo_base          - custo (em XP) pra sair do nivel 1 pro nivel 2.
  custo_multiplicador - o quanto o custo cresce por nivel, de forma
                        linear: custo(nivel) = nivel x custo_base x
                        custo_multiplicador. Sair do nivel 1 custa
                        1x100x1.2=120, do nivel 2 custa 2x100x1.2=240,
                        e assim por diante. Nao tem limite de nivel -
                        sobe enquanto tiver XP suficiente.
"""

XP_CONFIG = {
    "por_ano": 100,
    "por_commit": 25,
    "por_projeto": 100,
    "por_linguagem_no_projeto": 10,
    "teto_commits_por_projeto": 50,
    "min_bytes_linguagem": 500,
    "multiplicador_final": 3,
}

NIVEL_CONFIG = {
    "custo_base": 100,
    "custo_multiplicador": 1.2,
}
