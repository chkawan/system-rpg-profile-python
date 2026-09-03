"""
Preenche os blocos da ficha dentro do README.md.

O design NAO mora aqui. Ele mora no README e no SVG. Este script busca os
dados, monta o SVG completo (banner, vitais, atributos, equipamento, feitos
e cronica) e troca o carimbo de data entre os marcadores
<!-- ficha:carimbo:inicio --> e <!-- ficha:carimbo:fim --> no README.

    python scripts/gerar_ficha.py            # busca no GitHub (usa GH_TOKEN)
    python scripts/gerar_ficha.py --previa   # roda com dados de exemplo
"""
import math
import os
import re
import sys
import textwrap
from datetime import datetime, timezone

LOGIN = os.environ.get("FICHA_LOGIN", "chkawan")
TOKEN = os.environ.get("GH_TOKEN", "")
README = os.path.join(os.path.dirname(__file__), "..", "README.md")

CLASSES = {
    "Python": ("Encantador de serpentes", "fala baixo e o sistema obedece"),
    "PHP": ("Necromante", "ergue sistemas que deviam ter morrido"),
    "JavaScript": ("Alquimista errante", "transmuta o que ninguem pediu"),
    "TypeScript": ("Escriba dos Tipos", "anota tudo antes que quebre"),
    "HTML": ("Pedreiro", "levanta a estrutura que os outros pintam"),
}
FALLBACK_CLASSE = ("Andarilho", "aprende no caminho")

CORES = {
    "Python": "3572A5", "PHP": "4F5D95", "JavaScript": "f1e05a",
    "TypeScript": "3178c6", "HTML": "e34c26", "CSS": "563d7c", "Shell": "89e051",
}

SLOTS = ["Arma principal", "Arma secundaria", "Armadura", "Reliquia"]

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
GRIMORIO = [
    ("Conjuração", [
        ("Python", "3572A5"), ("Django", "092E20"),
        ("PHP", "4F5D95"), ("APIs REST", "005571"),
    ]),
    ("Câmaras de dados", [
        ("MySQL", "4479A1"), ("PostgreSQL", "336791"),
    ]),
    ("Forja", [
        ("AWS", "232F3E"), ("Git", "F05032"), ("Power BI", "F2C811"),
    ]),
]

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
        name pushedAt isPrivate stargazerCount forkCount
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
            "estrelas": r["stargazerCount"], "forks": r["forkCount"],
            "ling": (r["primaryLanguage"] or {}).get("name"),
        } for r in u["repositories"]["nodes"]],
    }


def escala(v, mx, teto=20):
    return max(1, min(teto, round(math.log10(v + 1) / math.log10(mx + 1) * teto)))


def dias(iso):
    d = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return (datetime.now(timezone.utc) - d).days


def derivar(d):
    repos = d["repos"]
    selados = sum(1 for r in repos if r["privado"])
    estrelas = sum(r["estrelas"] for r in repos)
    forks = sum(r["forks"] for r in repos)
    max_estrelas = max((r["estrelas"] for r in repos), default=0)
    total_repos = d.get("repos_total", len(repos))
    anos = dias(d["criado"]) / 365.25
    recentes = sum(1 for r in repos if dias(r["push"]) < 90)

    contagem = {}
    for r in repos:
        if r["ling"]:
            contagem[r["ling"]] = contagem.get(r["ling"], 0) + 1
    total = sum(contagem.values()) or 1
    lings = sorted(({"nome": k, "n": v, "fatia": v / total} for k, v in contagem.items()),
                   key=lambda x: -x["n"])
    topo = lings[0]["nome"] if lings else None

    nivel = max(1, min(99, round(escala(len(repos), 200, 40) +
                                 escala(estrelas, 5000, 35) + anos * 2)))
    return {**d, "selados": selados, "estrelas": estrelas, "forks": forks,
            "max_estrelas": max_estrelas, "total_repos": total_repos,
            "anos": anos, "recentes": recentes, "lings": lings, "topo": topo,
            "nivel": nivel, "classe": CLASSES.get(topo, FALLBACK_CLASSE)}


def atributos(d):
    return [
        ("Forca", escala(len(d["repos"]), 200),
         f'{len(d["repos"])} repositorios erguidos' +
         (f', {d["selados"]} selados' if d["selados"] else "")),
        ("Destreza", escala(len(d["lings"]), 20), f'{len(d["lings"])} linguagens empunhadas'),
        ("Constituicao", escala(d["anos"], 15), f'{d["anos"]:.1f} anos de estrada'),
        ("Inteligencia", escala(d["estrelas"], 5000), f'{d["estrelas"]} estrelas recebidas'),
        ("Sabedoria", escala(d["forks"], 1000), f'{d["forks"]} obras copiadas por outros'),
        ("Carisma", escala(d["seguidores"], 5000), f'{d["seguidores"]} seguidores no reino'),
    ]


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

# nome, campo em d (ou funcao), unidade, limiares dos 10 tiers
CONQUISTAS = [
    ("Repositorios Proprios", "total_repos", "repositorios", [1, 5, 10, 20, 35, 50, 75, 100, 150, 250]),
    ("Estrelas Recebidas", "estrelas", "estrelas", [1, 5, 15, 35, 75, 150, 300, 600, 1200, 2500]),
    ("Forks Recebidos", "forks", "forks", [1, 3, 8, 15, 30, 60, 120, 250, 500, 1000]),
    ("Seguidores", "seguidores", "seguidores", [1, 5, 15, 30, 60, 120, 250, 500, 1000, 2500]),
    ("Linguagens Dominadas", lambda d: len(d["lings"]), "linguagens", [1, 2, 3, 4, 6, 8, 10, 13, 16, 20]),
    ("Anos de Estrada", "anos", "anos", [0.5, 1, 2, 3, 4, 5, 7, 9, 12, 15]),
    ("Cofres Selados", "selados", "selados", [1, 2, 4, 7, 12, 20, 35, 55, 80, 120]),
    ("Vigilia Ativa", "recentes", "ativos", [1, 2, 4, 6, 9, 13, 18, 25, 35, 50]),
    ("Contribuicoes no Ano", "commits", "commits", [1, 50, 150, 300, 500, 750, 1000, 1500, 2500, 4000]),
    ("Repositorio Mais Popular", "max_estrelas", "estrelas no top", [1, 5, 15, 40, 100, 250, 600, 1500, 4000, 10000]),
]


def tier_de(valor, limiares):
    idx = -1
    for i, limite in enumerate(limiares):
        if valor >= limite:
            idx = i
    return idx


def lista_conquistas(d):
    out = []
    for nome, campo, unidade, limiares in CONQUISTAS:
        valor = campo(d) if callable(campo) else d[campo]
        out.append((nome, unidade, valor, tier_de(valor, limiares), limiares))
    return out


def cronica_recente(d):
    return sorted(d["repos"], key=lambda r: r["push"], reverse=True)[:6]

# ------------------------------------------------------------------ svg

BASE_SVG = os.path.join(os.path.dirname(__file__), "..", "ficha", "base.svg")
SAIDA_SVG = os.path.join(os.path.dirname(__file__), "..", "ficha", "ficha.svg")

PAL_HP, PAL_MP, PAL_ST = "#8c2f2f", "#3f7a8c", "#6b8f3a"
VELLUM, DIM = "#e6d3a3", "#8a7c62"

EQUIP_CARDS_Y, EQUIP_CARD_H = 458, 68
FEITOS_ROWS_Y0, FEITOS_ROW_H = 584, 25
CRONICA_ROWS_Y0, CRONICA_ROW_H = 882, 22
PERG_TEXT_Y0, PERG_LINE_H = 1052, 20
PERG_TABLE_Y0, PERG_ROW_H = 1112, 22
GRIM_GROUPS_Y0 = 1238
GRIM_LABEL_TO_PILLS, GRIM_PILL_H, GRIM_GROUP_GAP = 10, 24, 22


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


def selo(login, x, y, cell, cor):
    """Selo pixelado deterministico, espelhado, a partir do hash do login."""
    import hashlib
    h = hashlib.sha256(login.encode()).digest()
    out = []
    for linha in range(8):
        for col in range(4):
            if h[linha * 4 + col] & 1:
                for cx in (col, 7 - col):
                    out.append(f'<rect x="{x + cx * cell}" y="{y + linha * cell}" '
                               f'width="{cell}" height="{cell}" fill="{cor}"/>')
    return "".join(out)


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


def svg_equipamento(d, v):
    largura = (848 - 3 * 16) // 4
    if not d["lings"]:
        return (f'<text x="16" y="{EQUIP_CARDS_Y + 30}" font-size="12" '
                f'fill="{v["DIM"]}">Maos vazias.</text>')
    raridade = ["Comum", "Incomum", "Raro", "Epico", "Lendario"]
    out = []
    for i, l in enumerate(d["lings"][:4]):
        x = 16 + i * (largura + 16)
        cor = CORES.get(l["nome"], "8a7c62")
        cor = cor if cor.startswith("#") else "#" + cor
        r = raridade[min(4, int(l["fatia"] * 5))]
        sub = f'{r} · {l["n"]} repos · {round(l["fatia"] * 100)}%'
        out.append(
            f'<rect x="{x}" y="{EQUIP_CARDS_Y}" width="{largura}" height="{EQUIP_CARD_H}" fill="{v["DARK"]}"/>'
            f'<rect x="{x + 2}" y="{EQUIP_CARDS_Y + 2}" width="{largura - 4}" height="{EQUIP_CARD_H - 4}" fill="{v["STONE"]}"/>'
            f'<text x="{x + 10}" y="{EQUIP_CARDS_Y + 16}" font-size="9.5" fill="{v["DIM"]}">{escapar(SLOTS[i]).upper()}</text>'
            f'<rect x="{x + 10}" y="{EQUIP_CARDS_Y + 24}" width="14" height="14" fill="{cor}"/>'
            f'<text x="{x + 30}" y="{EQUIP_CARDS_Y + 35}" font-size="12.5" font-weight="bold" fill="{v["VELLUM"]}">{truncar(escapar(l["nome"]), 15)}</text>'
            f'<text x="{x + 10}" y="{EQUIP_CARDS_Y + 52}" font-size="9.5" fill="{v["DIM"]}">{truncar(sub, 24)}</text>'
        )
    return "".join(out)


def svg_tier_pill(x, y, texto, cor_hex):
    r, g, b = (int(cor_hex[i:i + 2], 16) for i in (1, 3, 5))
    luminancia = 0.299 * r + 0.587 * g + 0.114 * b
    texto_cor = "#1b1f22" if luminancia > 150 else "#f2ead2"
    largura = round(16 + len(texto) * 6)
    svg = (f'<rect x="{x}" y="{y}" width="{largura}" height="16" rx="3" fill="{cor_hex}"/>'
           f'<text x="{x + largura / 2:.0f}" y="{y + 12}" font-size="9.5" font-weight="bold" '
           f'text-anchor="middle" fill="{texto_cor}">{texto.upper()}</text>')
    return svg, largura


def svg_conquistas(d, v):
    out = []
    for i, (nome, unidade, valor, tier_idx, limiares) in enumerate(lista_conquistas(d)):
        y = FEITOS_ROWS_Y0 + i * FEITOS_ROW_H
        tier_nome, tier_cor = TIERS[tier_idx] if tier_idx >= 0 else SEM_TIER
        pill_svg, pill_w = svg_tier_pill(16, y - 12, tier_nome, tier_cor)
        out.append(pill_svg)
        valor_fmt = f"{valor:.1f}" if isinstance(valor, float) else str(valor)
        out.append(
            f'<text x="{16 + pill_w + 10}" y="{y}" font-size="11.5" fill="{v["VELLUM"]}">{escapar(nome)}'
            f'<tspan fill="{v["DIM"]}"> - {valor_fmt} {escapar(unidade)}</tspan></text>'
        )
        if tier_idx < len(limiares) - 1:
            prox = f"prox: {TIERS[tier_idx + 1][0]}"
        else:
            prox = "tier maximo"
        out.append(f'<text x="864" y="{y}" font-size="10" text-anchor="end" fill="{v["DIM"]}">{escapar(prox)}</text>')
    return "".join(out)


def svg_cronica(d, v):
    out = []
    for i, r in enumerate(cronica_recente(d)):
        y = CRONICA_ROWS_Y0 + i * CRONICA_ROW_H
        quando = datetime.fromisoformat(r["push"].replace("Z", "+00:00")).strftime("%d/%m")
        if r["privado"]:
            nome = (f'<tspan filter="url(#borrao)">{truncar(escapar(r["nome"]), 60)}</tspan>'
                    f'<tspan fill="{v["DIM"]}"> (selado)</tspan>')
        else:
            nome = truncar(escapar(r["nome"]), 60)
        out.append(
            f'<text x="16" y="{y}" font-size="12" fill="{v["DIM"]}">{quando}'
            f'<tspan fill="{v["VELLUM"]}"> forjou em {nome}</tspan></text>'
        )
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


def svg_pill(x, y, texto, cor_hex):
    cor = cor_hex if cor_hex.startswith("#") else "#" + cor_hex
    r, g, b = (int(cor[i:i + 2], 16) for i in (1, 3, 5))
    luminancia = 0.299 * r + 0.587 * g + 0.114 * b
    texto_cor = "#1b1f22" if luminancia > 150 else "#f2ead2"
    largura = round(20 + len(texto) * 6.6)
    svg = (f'<rect x="{x}" y="{y}" width="{largura}" height="{GRIM_PILL_H}" rx="4" fill="{cor}"/>'
           f'<text x="{x + largura / 2:.0f}" y="{y + 16}" font-size="11" text-anchor="middle" '
           f'fill="{texto_cor}">{texto}</text>')
    return svg, largura


def svg_grimorio(v):
    out = []
    y_label = GRIM_GROUPS_Y0
    for nome_grupo, itens in GRIMORIO:
        out.append(f'<text x="16" y="{y_label}" font-size="12" font-weight="bold" '
                   f'fill="{v["VELLUM"]}">{escapar(nome_grupo)}</text>')
        y_pill = y_label + GRIM_LABEL_TO_PILLS
        x = 16
        for nome, cor in itens:
            pill_svg, largura = svg_pill(x, y_pill, escapar(nome), cor)
            out.append(pill_svg)
            x += largura + 8
        y_label = y_pill + GRIM_PILL_H + GRIM_GROUP_GAP
    return "".join(out)


def montar_svg(d):
    acento = CORES.get(d["topo"], "4f9ad8")
    acento = acento if acento.startswith("#") else "#" + acento
    ink, stone = tom(acento, 0.28, 6), tom(acento, 0.24, 12)
    lit, dark = tom(acento, 0.22, 22), tom(acento, 0.3, 3)
    gold = tom(acento, 0.9, 64)

    vida_max = 40 + len(d["repos"]) * 4
    mana_max = 30 + max(d["estrelas"], 20) * 2
    vitais = [
        ("VIDA", 40 + d["recentes"] * 4, vida_max, PAL_HP),
        ("MANA", 30 + d["estrelas"] * 2, mana_max, PAL_MP),
        ("VIGOR", min(d["commits"], 1000), 1000, PAL_ST),
        ("EXP", d["nivel"] % 10 * 100 + 40, 1000, gold),
    ]
    attrs = atributos(d)

    v = {
        "INK": ink, "STONE": stone, "LIT": lit, "DARK": dark,
        "GOLD": gold, "VELLUM": VELLUM, "DIM": DIM,
        "NOME": escapar(d["nome"]), "NIVEL": str(d["nivel"]),
        "CLASSE": f'{escapar(d["classe"][0])} - {escapar(d["classe"][1])}',
        "LINHA": " . ".join(filter(None, [
            escapar(d["local"]), f'jornada iniciada em {d["criado"][:4]}',
            f'{len(d["repos"])} obras' + (f', {d["selados"]} seladas' if d["selados"] else ""),
        ])),
        "SELO": selo(d["login"], 34, 30, 8, gold),
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

    v["BLOCO_EQUIP"] = svg_equipamento(d, v)
    v["BLOCO_FEITOS"] = svg_conquistas(d, v)
    v["BLOCO_CRONICA"] = svg_cronica(d, v)
    v["BLOCO_PERGAMINHO"] = svg_pergaminho(v)
    v["BLOCO_GRIMORIO"] = svg_grimorio(v)

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
