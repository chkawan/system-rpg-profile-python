"""
Conteudo pessoal da ficha que a API do GitHub nao sabe te contar (bio,
antecedentes, juramento). Edite esses textos pra falar sobre voce - nada
aqui afeta calculo de atributo, classe, XP ou conquista.

BIO_TEXTO    - paragrafo que aparece no "Pergaminho do Aventureiro"
BIO_TABELA   - lista de (rotulo, valor) que aparece na tabela do mesmo
               pergaminho (ex: origem, escola, campo de batalha...)
JURAMENTO_TEXTO - frase que aparece na secao "Juramento"
"""

BIO_TEXTO = (
    "Back-end com foco em dados e sistemas que aguentam carga. Construo de ponta a ponta: "
    "modelagem, API REST, deploy e o painel que alguém vai abrir de manhã. Antes de escrever "
    "código, pergunto que decisão o dado precisa sustentar."
)
BIO_TABELA = [
    ("Origem", "Rio de Janeiro, BR"),
    ("Escola", "Back-end, dados e automação"),
    ("Campo de batalha", "Sistemas completos, do banco à tela"),
    ("Marca registrada", "Deploy em cloud e domínio próprio por projeto"),
]

JURAMENTO_TEXTO = (
    "Atuar como desenvolvedor back-end construindo soluções orientadas a dados, "
    "com foco em performance, escalabilidade e impacto real no negócio."
)
