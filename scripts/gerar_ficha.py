"""
Preenche os blocos da ficha dentro do README.md.

O design NAO mora aqui. Ele mora no README e no SVG. Este script busca os
dados, monta o SVG completo (banner, vitais, atributos, equipamento,
pergaminho e conquistas) e troca o carimbo de data entre os marcadores
<!-- ficha:carimbo:inicio --> e <!-- ficha:carimbo:fim --> no README.

    python scripts/gerar_ficha.py            # busca no GitHub (usa GH_TOKEN)
    python scripts/gerar_ficha.py --previa   # roda com dados de exemplo
"""
import base64
import math
import os
import re
import sys
import textwrap
from datetime import datetime, timezone

LOGIN = os.environ.get("FICHA_LOGIN", "chkawan")
TOKEN = os.environ.get("GH_TOKEN", "")
README = os.path.join(os.path.dirname(__file__), "..", "README.md")
ICONES_DIR = os.path.join(os.path.dirname(__file__), "..", "ficha", "icones")

CORES = {
    "Python": "3572A5", "PHP": "4F5D95", "JavaScript": "f1e05a",
    "TypeScript": "3178c6", "HTML": "e34c26", "CSS": "563d7c", "Shell": "89e051",
}

# armaduras: ferramentas/plataformas do dia a dia - curado a mao porque a
# API do GitHub nao da esse nivel de detalhe (framework, nuvem, BI...),
# diferente de habilidades (linguagem), que vem direto dos repos
# boneco de equipamento: 5 slots num "+" (elmo em cima, arma de cada lado,
# armadura e bota no centro/baixo), igual o paper-doll de RPG - cada slot
# mapeado pra uma ferramenta do dia a dia, curado a mao (a API do GitHub
# nao da esse nivel de detalhe de stack)
ARMADURAS = [
    ("elmo", "AWS", "232F3E"),
    ("arma_esq", "Git", "F05032"),
    ("armadura", "Django", "092E20"),
    ("arma_dir", "APIs REST", "005571"),
    ("bota", "PostgreSQL", "336791"),
]

# conteudo estatico do "Pergaminho do aventureiro" e do "Grimorio" - nao vem
# da API do GitHub, e o texto de bio/skills que edita direto aqui.
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

# texto do "Juramento" - veio da secao homonima que existia solta no README
JURAMENTO_TEXTO = (
    "Atuar como desenvolvedor back-end construindo soluções orientadas a dados, "
    "com foco em performance, escalabilidade e impacto real no negócio."
)

QUERY = """
query($login: String!) {
  user(login: $login) {
    name login createdAt location
    followers { totalCount }
    contributionsCollection { contributionCalendar { totalContributions } }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false,
                 orderBy: {field: PUSHED_AT, direction: DESC}) {
      totalCount
      nodes {
        name pushedAt isPrivate stargazerCount homepageUrl description
        primaryLanguage { name }
      }
    }
  }
}
"""

# ------------------------------------------------------------------ dados

def buscar(login):
    import requests
    r = requests.post(
        "https://api.github.com/graphql",
        json={"query": QUERY, "variables": {"login": login}},
        headers={"Authorization": f"bearer {TOKEN}"},
        timeout=15,
    )
    dados = r.json()
    if dados.get("errors"):
        raise SystemExit("GitHub recusou: " + dados["errors"][0]["message"])
    if "data" not in dados:
        raise SystemExit(
            f"Resposta inesperada da API (HTTP {r.status_code}): "
            + dados.get("message", str(dados))
        )
    u = dados["data"]["user"]
    return {
        "nome": u["name"] or u["login"],
        "login": u["login"],
        "criado": u["createdAt"],
        "local": u.get("location") or "",
        "seguidores": u["followers"]["totalCount"],
        "commits": u["contributionsCollection"]["contributionCalendar"]["totalContributions"],
        "repos_total": u["repositories"]["totalCount"],
        "repos": [{
            "nome": r["name"], "push": r["pushedAt"], "privado": r["isPrivate"],
            "estrelas": r["stargazerCount"], "tem_url": bool(r["homepageUrl"]),
            "descricao": r["description"],
            "ling": (r["primaryLanguage"] or {}).get("name"),
        } for r in u["repositories"]["nodes"]],
    }


def escala(v, mx, teto=20):
    return max(1, min(teto, round(math.log10(v + 1) / math.log10(mx + 1) * teto)))


def dias(iso):
    d = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return (datetime.now(timezone.utc) - d).days


# a maioria dos repos usa nome de gerador tipo "tool-password-generator-python"
# em vez de um nome de projeto de verdade. como nao da pra saber o nome real,
# a missao vira o slug sem o prefixo de categoria e o sufixo de linguagem/
# framework, virado titulo - fica "Password Generator" em vez do slug cru.
PREFIXOS_GENERICOS = {"tool", "tools", "system", "systems", "sistema", "sistemas",
                       "api", "bot", "app", "projeto", "template"}
SUFIXOS_TECNICOS = {"python", "py", "php", "javascript", "js", "typescript", "ts",
                     "django", "node", "html", "css", "shell"}
CONECTIVOS = {"de", "da", "do", "das", "dos", "e", "em", "com", "para"}


def nome_missao(nome_repo):
    partes = [p for p in re.split(r"[-_.]+", nome_repo) if p]
    while len(partes) > 1 and partes[0].lower() in PREFIXOS_GENERICOS:
        partes.pop(0)
    while len(partes) > 1 and partes[-1].lower() in SUFIXOS_TECNICOS:
        partes.pop()
    while len(partes) > 1 and partes[0].lower() in CONECTIVOS:
        partes.pop(0)
    if not partes:
        return nome_repo
    return " ".join(p.lower() if i > 0 and p.lower() in CONECTIVOS else p.capitalize()
                     for i, p in enumerate(partes))


def selecionar_missoes(repos, login, max_privadas=6, max_publicas=4):
    """Repos privados viram as missoes principais (projetos pessoais de
    verdade), todos entram. Publico so entra se tiver URL - sem link no ar
    nao conta como missao publica. Exclui o repo de perfil (README)."""
    candidatos = [r for r in repos if r["nome"].lower() != login.lower()]
    privadas = sorted((r for r in candidatos if r["privado"]),
                       key=lambda r: r["push"], reverse=True)[:max_privadas]
    publicas = sorted((r for r in candidatos if not r["privado"] and r["tem_url"]),
                       key=lambda r: r["push"], reverse=True)[:max_publicas]
    return privadas + publicas


def derivar(d):
    repos = d["repos"]
    selados = sum(1 for r in repos if r["privado"])
    estrelas = sum(r["estrelas"] for r in repos)
    com_url = sum(1 for r in repos if r["tem_url"])
    total_repos = d.get("repos_total", len(repos))
    anos = dias(d["criado"]) / 365.25
    recentes = sum(1 for r in repos if dias(r["push"]) < 90)
    missoes = selecionar_missoes(repos, d["login"])

    contagem = {}
    for r in repos:
        if r["ling"]:
            contagem[r["ling"]] = contagem.get(r["ling"], 0) + 1
    total = sum(contagem.values()) or 1
    lings = sorted(({"nome": k, "n": v, "fatia": v / total} for k, v in contagem.items()),
                   key=lambda x: -x["n"])

    nivel = max(1, min(99, round(escala(total_repos, 200, 40) +
                                 escala(estrelas, 5000, 35) + anos * 2)))
    return {**d, "selados": selados, "estrelas": estrelas,
            "com_url": com_url, "total_repos": total_repos,
            "anos": anos, "recentes": recentes, "lings": lings,
            "missoes": missoes, "nivel": nivel}


def atributos(d):
    # cada atributo fisico/mental do RPG mapeado pro sinal de programacao
    # mais parecido com o que ele mede na mesa: forca e musculo (volume
    # erguido), destreza e reflexo (velocidade de reacao), constituicao e
    # folego (tempo aguentando o ritmo), inteligencia e estudo (repertorio
    # de linguagens), sabedoria e disciplina/forca de vontade (constancia
    # de commits) e carisma e presenca social (quem te segue).
    return [
        ("Forca", escala(d["total_repos"], 200),
         f'{d["total_repos"]} repositorios erguidos'),
        ("Destreza", escala(d["recentes"], 50), f'{d["recentes"]} repositorios com push recente'),
        ("Constituicao", escala(d["anos"], 15), f'{d["anos"]:.1f} anos de estrada sem parar'),
        ("Inteligencia", escala(len(d["lings"]), 20), f'{len(d["lings"])} linguagens estudadas'),
        ("Sabedoria", escala(d["commits"], 3000), f'{d["commits"]} commits de disciplina no ano'),
        ("Carisma", escala(d["seguidores"], 5000), f'{d["seguidores"]} seguidores no reino'),
    ]


# ------------------------------------------------------------- iconografia
# icones vetoriais pequenos (cx,cy = centro, cor = traco/preenchimento,
# furo = cor usada em recortes tipo buraco de fechadura). Usados tanto nas
# medalhas de conquista quanto nos cabecalhos de secao.

_CACHE_IMG = {}


def img_icone(caminho, tamanho=32):
    """Fabrica: le um PNG (relativo a ICONES_DIR) e devolve uma funcao
    icone(cx,cy,cor,furo) que embute a imagem centralizada em (cx,cy) via
    base64. cor/furo sao ignorados - a imagem ja vem com cor propria."""
    if caminho not in _CACHE_IMG:
        with open(os.path.join(ICONES_DIR, caminho), "rb") as f:
            _CACHE_IMG[caminho] = base64.b64encode(f.read()).decode("ascii")
    b64 = _CACHE_IMG[caminho]

    def render(cx, cy, cor, furo):
        return (f'<image x="{cx - tamanho / 2:.1f}" y="{cy - tamanho / 2:.1f}" '
                f'width="{tamanho}" height="{tamanho}" href="data:image/png;base64,{b64}"/>')
    return render






# classe agora nao vem mais da linguagem principal (por isso o guerreiro
# nao carrega mais titulo de "encantador de serpentes"): vem de qual
# atributo (somado ao vital que ele sustenta, onde existir) mais se
# destaca. cada chave: titulo, complemento e icone proprios.
# o arquivo (nao um icone(cx,cy,cor,furo) ja pronto) porque a classe
# ilustra tanto o retrato pequeno no banner quanto o "boneco" de fundo,
# grande, atras do equipamento - dois tamanhos, mesmo desenho
CLASSE_TITULOS = {
    "guerreiro": ("Guerreiro, o Forjador",
                  "ergue tudo na base da forca bruta", "class/guerreiro.png"),
    "arqueiro": ("Arqueiro, o Cacador de Bugs",
                 "acerta de longe, sem falhar", "class/arqueiro.png"),
    "aventureiro": ("Aventureiro, o Sobrevivente",
                     "sobrevive a qualquer legado", "class/aventureiro.png"),
    "mago": ("Mago, o Tecelao",
             "tece logica onde so havia caos", "class/mago.png"),
    "curandeiro": ("Curandeiro, o Guardiao",
                   "mantem tudo de pe", "class/healer.png"),
    "ladino": ("Ladino, o Explorador",
               "acha a brecha que ninguem viu", "class/ladino.png"),
}


def determinar_classe(pontos, vida_pct, mana_pct, vigor_pct):
    """Forca+Vigor -> Guerreiro, Destreza -> Arqueiro, Constituicao+Vida ->
    Aventureiro, Inteligencia+Mana -> Mago, Sabedoria -> Curandeiro,
    Carisma -> Ladino. O vital só entra pra quem tem um vital associado."""
    candidatos = {
        "guerreiro": pontos["Forca"] + vigor_pct * 5,
        "arqueiro": pontos["Destreza"],
        "aventureiro": pontos["Constituicao"] + vida_pct * 5,
        "mago": pontos["Inteligencia"] + mana_pct * 5,
        "curandeiro": pontos["Sabedoria"],
        "ladino": pontos["Carisma"],
    }
    return max(candidatos, key=candidatos.get)


def svg_cabecalho(y, titulo, icone, gold, x0=16, largura=848):
    """Padrao de cabecalho de secao: icone a esquerda, titulo que abre com
    a primeira letra maior, linha divisoria embutida logo abaixo. x0/largura
    permitem um cabecalho de meia largura (duas secoes lado a lado)."""
    primeira, resto = titulo[0], titulo[1:]
    return (
        icone(x0 + 16, y - 6, gold, gold)
        + f'<text x="{x0 + 36}" y="{y}" font-weight="bold" fill="{gold}">'
        f'<tspan font-size="20">{primeira}</tspan><tspan font-size="14">{resto}</tspan></text>'
        f'<rect x="{x0}" y="{y + 8}" width="{largura}" height="2" fill="{gold}"/>'
    )


# tiers de ranqueado, do mais baixo ao mais alto - cada um com cor propria
TIERS = [
    ("Ferro", "#53585c"),
    ("Bronze", "#8a5a3c"),
    ("Prata", "#9aa5ad"),
    ("Ouro", "#e0a526"),
    ("Platina", "#2fb8a6"),
    ("Esmeralda", "#1fae64"),
    ("Diamante", "#4f7fdb"),
    ("Mestre", "#a142c9"),
    ("Grao-Mestre", "#e0393e"),
    ("Desafiante", "#f4e04d"),
]
SEM_TIER = ("Sem tier", "#5a5245")

# as 5 conquistas que mais pesam pra quem esta avaliando um perfil pra
# contratacao: consistencia, trabalho protegido/profissional, ferramental,
# experiencia e projetos realmente publicados. nome, campo em d (ou
# funcao), descricao curta do que faz upar, icone gravado na medalha,
# limiares dos 10 tiers
CONQUISTAS = [
    ("Ritmo de Forja", "commits", "commits no ultimo ano", img_icone("conquistas/forja.png", 34), [1, 50, 150, 300, 500, 750, 1000, 1500, 2500, 4000]),
    ("Cofres Selados", "selados", "repositorios privados", img_icone("conquistas/cofre.png", 34), [1, 2, 4, 7, 12, 20, 35, 55, 80, 120]),
    ("Magias Dominadas", lambda d: len(d["lings"]), "linguagens diferentes", img_icone("conquistas/magias.png", 34), [1, 2, 3, 4, 6, 8, 10, 13, 16, 20]),
    ("Anos de Jornada", "anos", "anos de conta ativa", img_icone("conquistas/ano.png", 34), [0.5, 1, 2, 3, 4, 5, 7, 9, 12, 15]),
    ("Portais Abertos", "com_url", "repos com link no ar", img_icone("conquistas/portal.png", 34), [1, 2, 4, 6, 9, 13, 18, 25, 35, 50]),
]


def tier_de(valor, limiares):
    idx = -1
    for i, limite in enumerate(limiares):
        if valor >= limite:
            idx = i
    return idx


def formatar(n):
    return f"{n:.1f}" if isinstance(n, float) else str(round(n))


def progresso(valor, tier_idx, limiares):
    """Fracao (0-1) e rotulo tipo '14/18' do avanco dentro do tier atual."""
    if tier_idx >= len(limiares) - 1:
        return 1.0, "MAX"
    baixo = limiares[tier_idx] if tier_idx >= 0 else 0
    alto = limiares[tier_idx + 1]
    pct = max(0.0, min(1.0, (valor - baixo) / (alto - baixo))) if alto > baixo else 1.0
    return pct, f"{formatar(valor)}/{formatar(alto)}"


def lista_conquistas(d):
    out = []
    for nome, campo, descricao, icone, limiares in CONQUISTAS:
        valor = campo(d) if callable(campo) else d[campo]
        out.append((nome, descricao, valor, icone, tier_de(valor, limiares), limiares))
    return out

# ------------------------------------------------------------------ svg

BASE_SVG = os.path.join(os.path.dirname(__file__), "..", "ficha", "base.svg")
SAIDA_SVG = os.path.join(os.path.dirname(__file__), "..", "ficha", "ficha.svg")

PAL_HP, PAL_MP, PAL_ST = "#8c2f2f", "#3f7a8c", "#6b8f3a"
VELLUM, DIM = "#e6d3a3", "#8a7c62"
# cor de destaque fixa, igual a do portfolio (kawandev.com.br) - nao muda
# mais conforme a linguagem principal
ACENTO = "#986dff"

EQUIP_ROWS_Y0, EQUIP_ROW_H = 480, 26
PERG_TEXT_Y0, PERG_LINE_H = 705, 20
PERG_TABLE_Y0, PERG_ROW_H = 785, 22
CONQ_MEDALHA_CY = 941
MISSOES_Y0, MISSOES_ROW_H = 1119, 24
JURAMENTO_TEXT_Y0, JURAMENTO_LINE_H = 1395, 22


def tom(hexcor, sat_mul, luz):
    """Recolore no matiz do acento, controlando saturacao e luminosidade."""
    h = hexcor.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    mx, mn = max(r, g, b), min(r, g, b)
    d = mx - mn
    if d == 0:
        matiz = 0
    elif mx == r:
        matiz = ((g - b) / d % 6) * 60
    elif mx == g:
        matiz = ((b - r) / d + 2) * 60
    else:
        matiz = ((r - g) / d + 4) * 60
    li = luz / 100
    s = min(0.8, (d / (1 - abs(2 * ((mx + mn) / 2) - 1)) if d else 0) * sat_mul)
    c = (1 - abs(2 * li - 1)) * s
    x = c * (1 - abs((matiz / 60) % 2 - 1))
    m = li - c / 2
    seg = [(c, x, 0), (x, c, 0), (0, c, x), (0, x, c), (x, 0, c), (c, 0, x)][int(matiz // 60) % 6]
    return "#" + "".join(f"{round((v + m) * 255):02x}" for v in seg)


def segmentos(x, y, largura, cor, passo=12):
    """Celulas da barra. O clip do template decide quantas aparecem."""
    n = int(largura // passo)
    return "".join(f'<rect x="{x + i * passo}" y="{y + 3}" width="{passo - 2}" '
                   f'height="8" fill="{cor}"/>' for i in range(n))


def pips(x, y, cor, n=20, passo=19):
    return "".join(f'<rect x="{x + i * passo}" y="{y}" width="{passo - 4}" '
                   f'height="10" fill="{cor}"/>' for i in range(n))


def truncar(texto, maximo):
    return texto if len(texto) <= maximo else texto[:maximo - 1].rstrip() + "…"


def escapar(texto):
    return str(texto).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def svg_slot(cx, cy, w, nome, cor_hex, v):
    """Um slot de equipamento: moldura + preenchimento na cor da ferramenta
    + nome embaixo. Sem icone proprio (nao temos um por ferramenta), entao
    o nome faz esse papel."""
    cor = cor_hex if cor_hex.startswith("#") else "#" + cor_hex
    r = w / 2
    return (
        f'<rect x="{cx - r:.0f}" y="{cy - r:.0f}" width="{w}" height="{w}" rx="4" '
        f'fill="{v["DARK"]}" stroke="{v["GOLD"]}" stroke-width="1.5"/>'
        f'<rect x="{cx - r + 4:.0f}" y="{cy - r + 4:.0f}" width="{w - 8}" height="{w - 8}" rx="2" fill="{cor}"/>'
        f'<text x="{cx:.0f}" y="{cy + r + 11:.0f}" font-size="8.5" text-anchor="middle" '
        f'fill="{v["DIM"]}">{escapar(nome)}</text>'
    )


def svg_equipamento(d, v, icone_classe_fundo):
    """Duas secoes lado a lado: EQUIPAMENTO - um boneco em cruz (elmo,
    arma, armadura, arma, bota) com o icone da classe atual desenhado
    atras, meio transparente, como o personagem que veste tudo isso - e
    HABILIDADES (linguagem = skill, nivel = % dos repos, dado real)."""
    x_hab = 452
    largura_col = 396
    out = []

    cx_arm, w_slot, gap_h = 214, 40, 14
    cy_elmo, cy_meio, cy_bota = 500, 556, 612
    ferramenta = {slot: (nome, cor) for slot, nome, cor in ARMADURAS}
    out.append(f'<g opacity="0.16">{icone_classe_fundo(cx_arm, cy_meio, v["GOLD"], v["GOLD"])}</g>')
    out.append(svg_slot(cx_arm, cy_elmo, w_slot, *ferramenta["elmo"], v))
    out.append(svg_slot(cx_arm - w_slot - gap_h, cy_meio, w_slot, *ferramenta["arma_esq"], v))
    out.append(svg_slot(cx_arm, cy_meio, w_slot, *ferramenta["armadura"], v))
    out.append(svg_slot(cx_arm + w_slot + gap_h, cy_meio, w_slot, *ferramenta["arma_dir"], v))
    out.append(svg_slot(cx_arm, cy_bota, w_slot, *ferramenta["bota"], v))

    if not d["lings"]:
        out.append(f'<text x="{x_hab}" y="{EQUIP_ROWS_Y0}" font-size="11.5" '
                    f'fill="{v["DIM"]}">Sem linguagens registradas.</text>')
    else:
        barra_w = largura_col - 60
        for i, l in enumerate(d["lings"][:7]):
            y = EQUIP_ROWS_Y0 + i * EQUIP_ROW_H
            cor = CORES.get(l["nome"], "8a7c62")
            cor = cor if cor.startswith("#") else "#" + cor
            out.append(
                f'<rect x="{x_hab}" y="{y - 9}" width="10" height="10" fill="{cor}"/>'
                f'<text x="{x_hab + 16}" y="{y}" font-size="11.5" fill="{v["VELLUM"]}">{truncar(escapar(l["nome"]), 14)}</text>'
                f'<text x="{x_hab + largura_col}" y="{y}" font-size="11" font-weight="bold" text-anchor="end" '
                f'fill="{v["GOLD"]}">{round(l["fatia"] * 100)}%</text>'
                f'<rect x="{x_hab + 16}" y="{y + 4}" width="{barra_w}" height="3" fill="{v["DARK"]}"/>'
                f'<rect x="{x_hab + 16}" y="{y + 4}" width="{barra_w * l["fatia"]:.0f}" height="3" fill="{cor}"/>'
            )
    return "".join(out)


def svg_medalha(cx, cy, icone, tier_cor, dark):
    """Brasao de condecoracao: escudo com aro na cor do tier, face preenchida
    e icone gravado (tom mais escuro do mesmo matiz da face)."""
    escuro = tom(tier_cor, 1.0, 16)
    fora = (f'M {cx - 28},{cy - 32} L {cx + 28},{cy - 32} L {cx + 28},{cy + 6} '
            f'Q {cx + 28},{cy + 30} {cx},{cy + 40} Q {cx - 28},{cy + 30} {cx - 28},{cy + 6} Z')
    dentro = (f'M {cx - 23},{cy - 27} L {cx + 23},{cy - 27} L {cx + 23},{cy + 3} '
              f'Q {cx + 23},{cy + 24} {cx},{cy + 33} Q {cx - 23},{cy + 24} {cx - 23},{cy + 3} Z')
    return (
        f'<path d="{fora}" fill="{dark}" stroke="{tier_cor}" stroke-width="3"/>'
        f'<path d="{dentro}" fill="{tier_cor}"/>'
        + icone(cx, cy - 3, escuro, tier_cor)
    )


def svg_conquistas(d, v):
    itens = sorted(lista_conquistas(d), key=lambda item: item[4], reverse=True)
    slot = 848 / len(itens)
    cy = CONQ_MEDALHA_CY
    barra_w = 110
    out = []
    for i, (nome, descricao, valor, icone, tier_idx, limiares) in enumerate(itens):
        cx = round(16 + slot * (i + 0.5))
        tier_nome, tier_cor = TIERS[tier_idx] if tier_idx >= 0 else SEM_TIER
        out.append(svg_medalha(cx, cy, icone, tier_cor, v["DARK"]))
        pct, rotulo = progresso(valor, tier_idx, limiares)
        bx = cx - barra_w / 2
        out.append(
            f'<text x="{cx}" y="{cy + 56}" font-size="12" font-weight="bold" '
            f'text-anchor="middle" fill="{v["VELLUM"]}">{escapar(nome)}</text>'
            f'<text x="{cx}" y="{cy + 70}" font-size="10" font-weight="bold" '
            f'text-anchor="middle" fill="{tier_cor}">{tier_nome.upper()}</text>'
            f'<text x="{cx}" y="{cy + 84}" font-size="9" font-weight="bold" '
            f'text-anchor="middle" fill="{v["DIM"]}">{rotulo}</text>'
            f'<rect x="{bx:.0f}" y="{cy + 90}" width="{barra_w}" height="6" fill="{v["DARK"]}"/>'
            f'<rect x="{bx:.0f}" y="{cy + 90}" width="{barra_w * pct:.0f}" height="6" fill="{tier_cor}"/>'
            f'<text x="{cx}" y="{cy + 112}" font-size="8.5" font-style="italic" '
            f'text-anchor="middle" fill="{v["DIM"]}">{escapar(descricao)}</text>'
        )
    return "".join(out)


ICONE_MISSAO_COMPLETA = img_icone("secoes/missoes_completas.png", 16)
ICONE_MISSAO_PENDENTE = img_icone("secoes/missoes_pendentes.png", 16)


def svg_icone_missao(x, y, concluida):
    icone = ICONE_MISSAO_COMPLETA if concluida else ICONE_MISSAO_PENDENTE
    return icone(x + 8, y - 5, None, None)


def svg_missoes(d, v):
    # concluidas primeiro, depois em andamento; alfabetico dentro de cada grupo
    missoes = sorted(d["missoes"], key=lambda r: (not r["tem_url"], nome_missao(r["nome"]).lower()))
    out = []
    for i, r in enumerate(missoes):
        y = MISSOES_Y0 + i * MISSOES_ROW_H
        concluida = r["tem_url"]
        # linha concluida usa uma cor so em todas as colunas (dourado);
        # em andamento usa a paleta neutra padrao
        cor_forte = v["GOLD"] if concluida else v["VELLUM"]
        cor_fraca = v["GOLD"] if concluida else v["DIM"]
        out.append(svg_icone_missao(16, y, concluida))
        nome = truncar(nome_missao(r["nome"]), 24)
        out.append(f'<text x="40" y="{y}" font-size="12" font-weight="bold" fill="{cor_forte}">{escapar(nome)}</text>')
        ling = r["ling"] or "-"
        cor_arma = CORES.get(ling, "8a7c62")
        cor_arma = cor_arma if cor_arma.startswith("#") else "#" + cor_arma
        out.append(f'<rect x="230" y="{y - 9}" width="10" height="10" fill="{cor_arma}"/>')
        out.append(f'<text x="246" y="{y}" font-size="9.5" fill="{cor_fraca}">{escapar(truncar(ling, 12))}</text>')
        if r["descricao"]:
            desc = escapar(truncar(r["descricao"], 55))
            out.append(f'<text x="340" y="{y}" font-size="10" font-style="italic" fill="{cor_fraca}">{desc}</text>')
        status = "CONCLUIDA" if concluida else "EM PROGRESSO"
        out.append(f'<text x="864" y="{y}" font-size="9.5" font-weight="bold" text-anchor="end" '
                    f'fill="{cor_fraca}">{status}</text>')
    return "".join(out)


def svg_pergaminho(v):
    out = []
    linhas = textwrap.wrap(BIO_TEXTO, width=90)
    for i, linha in enumerate(linhas):
        y = PERG_TEXT_Y0 + i * PERG_LINE_H
        out.append(f'<text x="16" y="{y}" font-size="13" fill="{v["VELLUM"]}">{escapar(linha)}</text>')
    for i, (rotulo, valor) in enumerate(BIO_TABELA):
        y = PERG_TABLE_Y0 + i * PERG_ROW_H
        out.append(
            f'<text x="16" y="{y}" font-size="10.5" fill="{v["DIM"]}">{escapar(rotulo).upper()}</text>'
            f'<text x="210" y="{y}" font-size="12" fill="{v["VELLUM"]}">{escapar(valor)}</text>'
        )
    return "".join(out)


def svg_juramento(v):
    out = []
    linhas = textwrap.wrap(JURAMENTO_TEXTO, width=62)
    for i, linha in enumerate(linhas):
        y = JURAMENTO_TEXT_Y0 + i * JURAMENTO_LINE_H
        out.append(f'<text x="440" y="{y}" font-size="14" font-style="italic" '
                    f'text-anchor="middle" fill="{v["GOLD"]}">{escapar(linha)}</text>')
    return "".join(out)


def montar_svg(d):
    ink, stone = tom(ACENTO, 0.28, 6), tom(ACENTO, 0.24, 12)
    lit, dark = tom(ACENTO, 0.22, 22), tom(ACENTO, 0.3, 3)
    gold = tom(ACENTO, 0.9, 64)

    attrs = atributos(d)
    pontos = {nome: valor for nome, valor, _ in attrs}

    # vida/mana/vigor sobem de teto junto com o atributo que os sustenta,
    # igual em RPG de mesa: VIDA vem de Constituicao (folego), MANA vem de
    # Inteligencia (repertorio de linguagens) e VIGOR vem de Forca (musculo
    # pra sustentar o ritmo). O preenchimento atual usa um sinal recente
    # relacionado, sempre limitado a esse teto.
    vida_max = pontos["Constituicao"] * 25
    mana_max = pontos["Inteligencia"] * 25
    vigor_max = pontos["Forca"] * 25
    vida_atual = min(vida_max, 40 + d["recentes"] * 15)
    mana_atual = min(mana_max, 30 + d["estrelas"] * 3)
    vigor_atual = min(vigor_max, d["commits"])
    vitais = [
        ("VIDA", vida_atual, vida_max, PAL_HP),
        ("MANA", mana_atual, mana_max, PAL_MP),
        ("VIGOR", vigor_atual, vigor_max, PAL_ST),
        ("EXP", d["nivel"] % 10 * 100 + 40, 1000, gold),
    ]

    # classe vem do atributo (+ vital que ele sustenta) que mais se destaca,
    # nao da linguagem principal
    classe_chave = determinar_classe(
        pontos,
        vida_atual / vida_max if vida_max else 0,
        mana_atual / mana_max if mana_max else 0,
        vigor_atual / vigor_max if vigor_max else 0,
    )
    titulo_classe, complemento_classe, arquivo_classe = CLASSE_TITULOS[classe_chave]
    icone_classe = img_icone(arquivo_classe, 64)
    icone_classe_fundo = img_icone(arquivo_classe, 170)

    v = {
        "INK": ink, "STONE": stone, "LIT": lit, "DARK": dark,
        "GOLD": gold, "VELLUM": VELLUM, "DIM": DIM,
        "NOME": escapar(d["nome"]), "NIVEL": str(d["nivel"]),
        "CLASSE": escapar(truncar(f'{titulo_classe} - {complemento_classe}', 60)),
        "ICONE_CLASSE": icone_classe(68, 64, gold, gold),
        "LINHA": " . ".join(filter(None, [
            escapar(d["local"]), f'jornada iniciada em {d["criado"][:4]}',
            f'{d["total_repos"]} obras',
        ])),
    }
    for i, (tag, atual, mx, cor) in enumerate(vitais):
        y = 136 + i * 24
        pct = max(0.0, min(1.0, atual / mx)) if mx else 0
        v[f"W_{tag}"] = f"{640 * pct:.0f}"
        v[f"SEG_{tag}"] = segmentos(84, y, 640, cor)
        v[f"T_{tag}"] = f"{round(atual)} / {round(mx)}"
    for letra, (nome, valor, porque) in zip("ABCDEF", attrs):
        col = 16 if letra in "ACE" else 452
        y = {"A": 298, "B": 298, "C": 342, "D": 342, "E": 386, "F": 386}[letra]
        v[f"W_{letra}"] = str(valor * 19)
        v[f"PIP_{letra}"] = pips(col, y, gold)
        v[f"N_{letra}"], v[f"V_{letra}"], v[f"D_{letra}"] = escapar(nome), str(valor), escapar(porque)

    v["BLOCO_EQUIP"] = svg_equipamento(d, v, icone_classe_fundo)
    v["BLOCO_PERGAMINHO"] = svg_pergaminho(v)
    v["BLOCO_FEITOS"] = svg_conquistas(d, v)
    v["BLOCO_MISSOES"] = svg_missoes(d, v)
    v["BLOCO_JURAMENTO"] = svg_juramento(v)

    cabecalhos = [
        ("HDR_ATRIBUTOS", 256, "ATRIBUTOS", img_icone("secoes/atributos.png", 26), 16, 848),
        ("HDR_EQUIPAMENTO", 436, "EQUIPAMENTO", img_icone("secoes/equipamento.png", 26), 16, 396),
        ("HDR_HABILIDADES", 436, "HABILIDADES", img_icone("secoes/habilidades.png", 26), 452, 396),
        ("HDR_PERGAMINHO", 681, "PERGAMINHO DO AVENTUREIRO", img_icone("secoes/pergaminho.png", 26), 16, 848),
        ("HDR_CONQUISTAS", 887, "CONQUISTAS", img_icone("secoes/conquista.png", 26), 16, 848),
        ("HDR_MISSOES", 1089, "MISSOES", img_icone("secoes/missoes.png", 26), 16, 848),
        ("HDR_JURAMENTO", 1371, "JURAMENTO", img_icone("secoes/juramento.png", 26), 16, 848),
        ("HDR_TAVERNA", 1475, "TAVERNA", img_icone("secoes/taverna.png", 26), 16, 848),
    ]
    for chave, y, titulo, icone, x0, largura in cabecalhos:
        v[chave] = svg_cabecalho(y, titulo, icone, gold, x0, largura)

    with open(BASE_SVG, encoding="utf-8") as f:
        svg = f.read()
    for chave, valor in v.items():
        svg = svg.replace("{{" + chave + "}}", str(valor))
    faltando = re.findall(r"\{\{(\w+)\}\}", svg)
    if faltando:
        raise SystemExit("placeholder sem valor no template: " + ", ".join(set(faltando)))
    with open(SAIDA_SVG, "w", encoding="utf-8") as f:
        f.write(svg)
    return svg

# ------------------------------------------------------------------ escrita


def preencher(texto):
    carimbo = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
    return re.sub(r"(<!-- ficha:carimbo:inicio -->).*?(<!-- ficha:carimbo:fim -->)",
                  rf"\g<1>{carimbo}\g<2>", texto, flags=re.S)


def main():
    if "--previa" in sys.argv:
        from previa import PREVIA
        dados = PREVIA
    else:
        dados = buscar(LOGIN)
    with open(README, encoding="utf-8") as f:
        antigo = f.read()
    d = derivar(dados)
    montar_svg(d)
    novo = preencher(antigo)
    if novo == antigo:
        print("markdown sem alteracao (svg regravado)")
        return
    with open(README, "w", encoding="utf-8") as f:
        f.write(novo)
    print("ficha atualizada")


if __name__ == "__main__":
    main()
