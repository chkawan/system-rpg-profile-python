"""
Preenche os blocos da ficha dentro do README.md.

O design NAO mora aqui. Ele mora no README e no SVG. Este script busca os
dados, monta o SVG completo (banner, vitais, atributos, equipamento,
pergaminho e conquistas) e troca o carimbo de data entre os marcadores
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
        name pushedAt isPrivate stargazerCount homepageUrl
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
    com_url = sum(1 for r in repos if r["tem_url"])
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

    nivel = max(1, min(99, round(escala(total_repos, 200, 40) +
                                 escala(estrelas, 5000, 35) + anos * 2)))
    return {**d, "selados": selados, "estrelas": estrelas,
            "com_url": com_url, "total_repos": total_repos,
            "anos": anos, "recentes": recentes, "lings": lings, "topo": topo,
            "nivel": nivel, "classe": CLASSES.get(topo, FALLBACK_CLASSE)}


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
# funcao), descricao curta do que faz upar, simbolo gravado na medalha,
# limiares dos 10 tiers
CONQUISTAS = [
    ("Ritmo de Forja", "commits", "commits no ultimo ano", "⚡", [1, 50, 150, 300, 500, 750, 1000, 1500, 2500, 4000]),
    ("Cofres Selados", "selados", "repositorios privados", "⚿", [1, 2, 4, 7, 12, 20, 35, 55, 80, 120]),
    ("Magias Dominadas", lambda d: len(d["lings"]), "linguagens diferentes", "⬡", [1, 2, 3, 4, 6, 8, 10, 13, 16, 20]),
    ("Anos de Jornada", "anos", "anos de conta ativa", "⌛", [0.5, 1, 2, 3, 4, 5, 7, 9, 12, 15]),
    ("Portais Abertos", "com_url", "repos com link no ar", "↗", [1, 2, 4, 6, 9, 13, 18, 25, 35, 50]),
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
    for nome, campo, descricao, simbolo, limiares in CONQUISTAS:
        valor = campo(d) if callable(campo) else d[campo]
        out.append((nome, descricao, valor, simbolo, tier_de(valor, limiares), limiares))
    return out

# ------------------------------------------------------------------ svg

BASE_SVG = os.path.join(os.path.dirname(__file__), "..", "ficha", "base.svg")
SAIDA_SVG = os.path.join(os.path.dirname(__file__), "..", "ficha", "ficha.svg")

PAL_HP, PAL_MP, PAL_ST = "#8c2f2f", "#3f7a8c", "#6b8f3a"
VELLUM, DIM = "#e6d3a3", "#8a7c62"

EQUIP_CARDS_Y, EQUIP_CARD_H = 458, 68
PERG_TEXT_Y0, PERG_LINE_H = 580, 20
PERG_TABLE_Y0, PERG_ROW_H = 660, 22
CONQ_MEDALHA_CY = 816


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


def svg_medalha(cx, cy, simbolo, tier_cor, dark):
    """Brasao de condecoracao: escudo com aro na cor do tier, face preenchida
    e simbolo gravado (tom mais escuro do mesmo matiz da face)."""
    escuro = tom(tier_cor, 1.0, 16)
    fora = (f'M {cx - 28},{cy - 32} L {cx + 28},{cy - 32} L {cx + 28},{cy + 6} '
            f'Q {cx + 28},{cy + 30} {cx},{cy + 40} Q {cx - 28},{cy + 30} {cx - 28},{cy + 6} Z')
    dentro = (f'M {cx - 23},{cy - 27} L {cx + 23},{cy - 27} L {cx + 23},{cy + 3} '
              f'Q {cx + 23},{cy + 24} {cx},{cy + 33} Q {cx - 23},{cy + 24} {cx - 23},{cy + 3} Z')
    return (
        f'<path d="{fora}" fill="{dark}" stroke="{tier_cor}" stroke-width="3"/>'
        f'<path d="{dentro}" fill="{tier_cor}"/>'
        f'<text x="{cx}" y="{cy + 2}" font-size="26" text-anchor="middle" fill="{escuro}">{simbolo}</text>'
    )


def svg_conquistas(d, v):
    itens = sorted(lista_conquistas(d), key=lambda item: item[4], reverse=True)
    slot = 848 / len(itens)
    cy = CONQ_MEDALHA_CY
    barra_w = 110
    out = []
    for i, (nome, descricao, valor, simbolo, tier_idx, limiares) in enumerate(itens):
        cx = round(16 + slot * (i + 0.5))
        tier_nome, tier_cor = TIERS[tier_idx] if tier_idx >= 0 else SEM_TIER
        out.append(svg_medalha(cx, cy, simbolo, tier_cor, v["DARK"]))
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


def montar_svg(d):
    acento = CORES.get(d["topo"], "4f9ad8")
    acento = acento if acento.startswith("#") else "#" + acento
    ink, stone = tom(acento, 0.28, 6), tom(acento, 0.24, 12)
    lit, dark = tom(acento, 0.22, 22), tom(acento, 0.3, 3)
    gold = tom(acento, 0.9, 64)

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
    vitais = [
        ("VIDA", min(vida_max, 40 + d["recentes"] * 15), vida_max, PAL_HP),
        ("MANA", min(mana_max, 30 + d["estrelas"] * 3), mana_max, PAL_MP),
        ("VIGOR", min(vigor_max, d["commits"]), vigor_max, PAL_ST),
        ("EXP", d["nivel"] % 10 * 100 + 40, 1000, gold),
    ]

    v = {
        "INK": ink, "STONE": stone, "LIT": lit, "DARK": dark,
        "GOLD": gold, "VELLUM": VELLUM, "DIM": DIM,
        "NOME": escapar(d["nome"]), "NIVEL": str(d["nivel"]),
        "CLASSE": f'{escapar(d["classe"][0])} - {escapar(d["classe"][1])}',
        "LINHA": " . ".join(filter(None, [
            escapar(d["local"]), f'jornada iniciada em {d["criado"][:4]}',
            f'{d["total_repos"]} obras',
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
    v["BLOCO_PERGAMINHO"] = svg_pergaminho(v)
    v["BLOCO_FEITOS"] = svg_conquistas(d, v)

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
