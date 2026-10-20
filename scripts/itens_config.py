"""
Set de equipamento de cada classe: qual icone usar em cada slot do
boneco (elmo, armadura, arma principal, arma secundaria, bota) e o nome
base de cada arma/escudo, usado pra gerar o nome completo do item
mostrado na ficha.

Os icones ficam em ficha/icones/itens/. Se um arquivo listado aqui nao
existir nesse diretorio, img_icone_item() (gerar_ficha.py) cai num
placeholder generico no slot em vez de quebrar a geracao da ficha.

Cada classe tem um set completo (os 5 slots preenchidos), mesmo quando
o icone e compartilhado com outra classe parecida (ex: Mago e
Curandeiro usam a mesma vestimenta arcana, Guerreiro e Aventureiro
usam a mesma familia "pesada" de elmo/bota) - a ideia e nunca deixar
uma classe sem set proprio definido.

Slots:
  elmo, armadura, bota     - so o nome do arquivo do icone
  arma_principal            - dict com "icone" e "nome_base". O nome
                              completo do item fica "{nome_base} de
                              {linguagem}" (linguagem vem do repo
                              fixado naquele slot, ex: "Espada Longa de
                              JavaScript")
  arma_secundaria           - mesma estrutura de arma_principal. Pode
                              ser uma segunda arma (Arqueiro/Ladino
                              usam a mesma arma nos dois slots, visual
                              de "par") ou um escudo (Guerreiro,
                              Aventureiro)

A arma_principal sempre fica no slot da ESQUERDA do boneco, a
arma_secundaria no da DIREITA (ver svg_equipamento() em gerar_ficha.py).
"""

ITENS_CONFIG = {
    "guerreiro": {
        "elmo": "elmo_pesado.png",
        "armadura": "armadura_placas.png",
        "arma_principal": {"icone": "espada_longa.png", "nome_base": "Espada Longa"},
        "arma_secundaria": {"icone": "escudo_guerreiro.png", "nome_base": "Escudo do Guerreiro"},
        "bota": "bota_pesada.png",
    },
    "arqueiro": {
        "elmo": "elmo_leve.png",
        "armadura": "armadura_couro.png",
        "arma_principal": {"icone": "arco_longo.png", "nome_base": "Arco Longo"},
        "arma_secundaria": {"icone": "flechas.png", "nome_base": "Aljava de Flechas"},
        "bota": "bota_leve.png",
    },
    "ladino": {
        "elmo": "elmo_leve.png",
        "armadura": "armadura_couro.png",
        "arma_principal": {"icone": "adaga.png", "nome_base": "Adaga"},
        "arma_secundaria": {"icone": "adaga.png", "nome_base": "Adaga"},
        "bota": "bota_leve.png",
    },
    "mago": {
        "elmo": "elmo_arcano.png",
        "armadura": "vestimenta_arcana.png",
        "arma_principal": {"icone": "cajado_arcano.png", "nome_base": "Cajado Arcano"},
        "arma_secundaria": {"icone": "orbe.png", "nome_base": "Orbe Arcano"},
        "bota": "bota_arcana.png",
    },
    "curandeiro": {
        "elmo": "elmo_arcano.png",
        "armadura": "vestimenta_arcana.png",
        "arma_principal": {"icone": "cajado_simples.png", "nome_base": "Cajado Sagrado"},
        "arma_secundaria": {"icone": "livro_sagrado.png", "nome_base": "Livro Sagrado"},
        "bota": "bota_arcana.png",
    },
    "aventureiro": {
        "elmo": "elmo_leve.png",
        "armadura": "roupas_viagem.png",
        "arma_principal": {"icone": "espada_curta.png", "nome_base": "Espada Curta"},
        "arma_secundaria": {"icone": "escudo_inicial.png", "nome_base": "Escudo Inicial"},
        "bota": "bota_leve.png",
    },
}
