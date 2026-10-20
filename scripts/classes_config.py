"""
Configuracao das 6 classes da ficha. Edite os valores abaixo pra mudar o
requisito de cada classe, o quanto ela vale em Vida/Vigor/Mana, ou o
titulo/icone - sem precisar tocar no resto do codigo (gerar_ficha.py so
le este dicionario pra decidir classe e vitais).

Cada classe tem:

  titulo       - nome completo mostrado na ficha (ex: "Guerreiro, o Forjador")
  complemento  - frase curta que acompanha o titulo
  icone        - caminho do PNG em ficha/icones/ (retrato pequeno e boneco de fundo)

  requisito    - lista dos atributos (pelo nome, igual em atributos_config.py)
                 que essa classe exige. TODOS precisam bater o minimo (ver
                 'minimo' em determinar_classe(), hoje 4) pra classe
                 qualificar. Uma lista vazia [] significa "fallback": essa
                 classe so e escolhida se NENHUMA outra classe qualificar
                 (e o que o Aventureiro faz hoje).
                   - 1 atributo na lista = requisito simples (ex: Guerreiro
                     so precisa de Força).
                   - 2+ atributos = requisito duplo, igual ao pre-requisito
                     real de multiclasse do D&D 5e pro Patrulheiro (precisa
                     de Destreza E Sabedoria juntos). Quando uma classe com
                     requisito duplo qualifica, ela "absorve" a prioridade
                     sobre qualquer classe de requisito simples que seja um
                     subconjunto do dela (ex: Arqueiro, que pede Destreza+
                     Sabedoria, sempre ganha do Ladino, que pede so
                     Destreza, quando os dois qualificam).

  vida_base, vida_por_nivel       - Vida = vida_base + vida_por_nivel x (nivel-1) + Constituicao x 0.6
  vigor_base, vigor_por_nivel,
  vigor_attr                     - Vigor = vigor_base + vigor_por_nivel x (nivel-1) + [vigor_attr] x 0.6
  mana_base, mana_por_nivel,
  mana_attr                      - Mana = mana_base + mana_por_nivel x (nivel-1) + [mana_attr] x 0.6

  Os numeros de vida_base/vida_por_nivel vem do dado de vida real de cada
  classe no D&D 5E (Livro do Jogador, pag. 11/14): d12->base12/nivel7
  (Barbaro, o mais resistente - usado no Aventureiro, que nao tem classe
  real equivalente), d10->base10/nivel6 (Guerreiro, Patrulheiro), d8->
  base8/nivel5 (Clerigo, Ladino), d6->base6/nivel4 (Mago). Vigor nao
  existe no D&D (so tem Vida e Mana/Magia) - e invencao nossa pra classe
  fisica ter um recurso proprio, calibrada a mao pra ficar coerente com
  a Vida.
"""

CLASSES_CONFIG = {
    "guerreiro": {
        "titulo": "Guerreiro, o Forjador",
        "complemento": "ergue tudo na base da força bruta",
        "icone": "class/guerreiro.png",
        "requisito": ["Força"],
        "vida_base": 10, "vida_por_nivel": 6,
        "vigor_base": 14, "vigor_por_nivel": 6, "vigor_attr": "Força",
        "mana_base": 4, "mana_por_nivel": 1, "mana_attr": "Inteligência",
    },
    "arqueiro": {
        "titulo": "Arqueiro, o Caçador de Bugs",
        "complemento": "acerta de longe, sem falhar",
        "icone": "class/arqueiro.png",
        "requisito": ["Destreza", "Sabedoria"],
        "vida_base": 10, "vida_por_nivel": 6,
        "vigor_base": 12, "vigor_por_nivel": 5, "vigor_attr": "Destreza",
        "mana_base": 4, "mana_por_nivel": 1, "mana_attr": "Sabedoria",
    },
    "ladino": {
        "titulo": "Ladino, o Explorador",
        "complemento": "acha a brecha que ninguém viu",
        "icone": "class/ladino.png",
        "requisito": ["Destreza"],
        "vida_base": 8, "vida_por_nivel": 5,
        "vigor_base": 11, "vigor_por_nivel": 5, "vigor_attr": "Destreza",
        "mana_base": 5, "mana_por_nivel": 1, "mana_attr": "Inteligência",
    },
    "mago": {
        "titulo": "Mago, o Tecelão",
        "complemento": "tece lógica onde só havia caos",
        "icone": "class/mago.png",
        "requisito": ["Inteligência"],
        "vida_base": 6, "vida_por_nivel": 4,
        "vigor_base": 4, "vigor_por_nivel": 1, "vigor_attr": "Força",
        "mana_base": 13, "mana_por_nivel": 6, "mana_attr": "Inteligência",
    },
    "curandeiro": {
        "titulo": "Curandeiro, o Guardião",
        "complemento": "mantém tudo de pé",
        "icone": "class/healer.png",
        "requisito": ["Sabedoria"],
        "vida_base": 8, "vida_por_nivel": 5,
        "vigor_base": 5, "vigor_por_nivel": 2, "vigor_attr": "Força",
        "mana_base": 12, "mana_por_nivel": 5, "mana_attr": "Sabedoria",
    },
    "aventureiro": {
        "titulo": "Aventureiro, o Sobrevivente",
        "complemento": "sobrevive a qualquer legado",
        "icone": "class/aventureiro.png",
        "requisito": [],
        "vida_base": 12, "vida_por_nivel": 7,
        "vigor_base": 10, "vigor_por_nivel": 4, "vigor_attr": "Constituição",
        "mana_base": 5, "mana_por_nivel": 1, "mana_attr": "Inteligência",
    },
}
