"""
Preenche os blocos da ficha dentro do README.md.

O design NAO mora aqui. Ele mora no README. Este script so troca o
conteudo entre os marcadores <!-- ficha:X:inicio --> e <!-- ficha:X:fim -->.

    python scripts/gerar_ficha.py            # busca no GitHub (usa GH_TOKEN)
    python scripts/gerar_ficha.py --previa   # roda com dados de exemplo
"""
import math
import os
import re
import sys
from datetime import datetime, timezone

LOGIN = os.environ.get("FICHA_LOGIN", "chkawan")
TOKEN = os.environ.get("GH_TOKEN", "")
README = os.path.join(os.path.dirname(__file__), "..", "README.md")

CHEIO, VAZIO = "\u2588", "\u2591"
CELULAS = 22

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

QUERY = """
query($login: String!) {
  user(login: $login) {
    name login createdAt location
    followers { totalCount }
    contributionsCollection { contributionCalendar { totalContributions } }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false,
                 orderBy: {field: PUSHED_AT, direction: DESC}) {
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
    u = dados["data"]["user"]
    return {
        "nome": u["name"] or u["login"],
        "login": u["login"],
        "criado": u["createdAt"],
        "local": u.get("location") or "",
        "seguidores": u["followers"]["totalCount"],
        "commits": u["contributionsCollection"]["contributionCalendar"]["totalContributions"],
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
            "anos": anos, "recentes": recentes, "lings": lings, "topo": topo,
            "nivel": nivel, "classe": CLASSES.get(topo, FALLBACK_CLASSE)}

# ------------------------------------------------------------------ blocos

def barra(atual, maximo):
    cheio = max(0, min(CELULAS, round(atual / maximo * CELULAS))) if maximo else 0
    return CHEIO * cheio + VAZIO * (CELULAS - cheio)


def bloco_banner(d):
    cor = CORES.get(d["topo"], "4f9ad8")
    linha = " &middot; ".join(filter(None, [
        d["local"],
        f'jornada iniciada em {d["criado"][:4]}',
        f'{len(d["repos"])} obras' + (f', {d["selados"]} seladas' if d["selados"] else ""),
    ]))
    return "\n".join([
        '<div align="center">',
        "",
        f'<h1>{d["nome"]}</h1>',
        f'<p><b>{d["classe"][0]}</b><br><sub>{d["classe"][1]}</sub></p>',
        "",
        f'![Nivel](https://img.shields.io/badge/N%C3%8DVEL-{d["nivel"]}-{cor}'
        f'?style=for-the-badge "Cresce com repositorios, estrelas e anos de estrada")',
        "",
        f"<sub>{linha}</sub>",
        "",
        "</div>",
    ])


def bloco_vitais(d):
    vida_max = 40 + len(d["repos"]) * 4
    mana_max = 30 + max(d["estrelas"], 20) * 2
    linhas = [
        ("Vida", 40 + d["recentes"] * 4, vida_max, "repositorios com push nos ultimos 90 dias"),
        ("Mana", 30 + d["estrelas"] * 2, mana_max, "estrelas recebidas nos repositorios"),
        ("Vigor", min(d["commits"], 1000), 1000, "contribuicoes no ultimo ano"),
        ("Exper.", d["nivel"] % 10 * 100 + 40, 1000, "progresso ate o proximo nivel"),
    ]
    out = ["| | | |", "|:--|:--|--:|"]
    for nome, atual, mx, _ in linhas:
        out.append(f"| **{nome}** | `{barra(atual, mx)}` | `{round(atual)}/{round(mx)}` |")
    return "\n".join(out)


def bloco_atributos(d):
    attrs = [
        ("Forca", escala(len(d["repos"]), 200),
         f'{len(d["repos"])} repositorios erguidos' +
         (f', {d["selados"]} selados' if d["selados"] else "")),
        ("Destreza", escala(len(d["lings"]), 20), f'{len(d["lings"])} linguagens empunhadas'),
        ("Constituicao", escala(d["anos"], 15), f'{d["anos"]:.1f} anos de estrada'),
        ("Inteligencia", escala(d["estrelas"], 5000), f'{d["estrelas"]} estrelas recebidas'),
        ("Sabedoria", escala(d["forks"], 1000), f'{d["forks"]} obras copiadas por outros'),
        ("Carisma", escala(d["seguidores"], 5000), f'{d["seguidores"]} seguidores no reino'),
    ]
    out = ["| Atributo | | Valor | De onde vem |", "|:--|:--|:--:|:--|"]
    for nome, v, porque in attrs:
        pips = CHEIO * v + VAZIO * (20 - v)
        out.append(f"| **{nome}** | `{pips}` | **{v}** | <sub>{porque}</sub> |")
    return "\n".join(out)


def bloco_equipamento(d):
    if not d["lings"]:
        return "_Maos vazias._"
    out = ["| Slot | Item | Raridade |", "|:--|:--|:--|"]
    raridade = ["Comum", "Incomum", "Raro", "Epico", "Lendario"]
    for i, l in enumerate(d["lings"][:4]):
        cor = CORES.get(l["nome"], "8a7c62")
        r = raridade[min(4, int(l["fatia"] * 5))]
        selo = (f'![{l["nome"]}](https://img.shields.io/badge/{l["nome"].replace(" ", "_")}'
                f'-{cor}?style=flat-square "{l["n"]} repositorios, '
                f'{round(l["fatia"]*100)}% do arsenal")')
        out.append(f'| <sub>{SLOTS[i]}</sub> | {selo} | <sub>{r} &middot; '
                   f'{l["n"]} repos &middot; {round(l["fatia"]*100)}%</sub> |')
    return "\n".join(out)


def bloco_feitos(d):
    feitos = [
        ("Primeiro passo", len(d["repos"]) >= 1, "Ergueu o primeiro repositorio"),
        ("Guarda de dez portoes", len(d["repos"]) >= 10, "Mantem 10 ou mais repositorios proprios"),
        ("Senhor de vinte torres", len(d["repos"]) >= 20, "Passou de 20 repositorios entre publicos e selados"),
        ("Poliglota", len(d["lings"]) >= 4, "Empunha 4 ou mais linguagens em projetos reais"),
        ("Veterano", d["anos"] >= 3, "Mais de 3 anos desde o primeiro commit"),
        ("Anciao do reino", d["anos"] >= 8, "Exige 8 anos desde o primeiro commit"),
        ("Guardiao de segredos", d["selados"] >= 5, "5 ou mais repositorios selados"),
        ("Vigilia ativa", d["recentes"] >= 5, "5 ou mais repositorios com push nos ultimos 90 dias"),
        ("Primeira estrela", d["estrelas"] >= 1, "Recebeu a primeira estrela"),
        ("Constelacao", d["estrelas"] >= 25, "Exige 25 estrelas recebidas"),
        ("Obra copiada", d["forks"] >= 5, "5 ou mais forks feitos por outras pessoas"),
        ("Reunidor de tropas", d["seguidores"] >= 10, "10 ou mais seguidores"),
    ]
    selos = []
    for nome, ganho, dica in feitos:
        marca = "%E2%9C%A6" if ganho else "%E2%9C%A7"
        cor = "4f9ad8" if ganho else "2b3341"
        rotulo = nome.replace(" ", "_").replace("-", "--")
        estado = "" if ganho else "Bloqueado &mdash; "
        selos.append(f'![{nome}](https://img.shields.io/badge/{marca}_{rotulo}-{cor}'
                     f'?style=flat-square "{estado}{dica}")')
    return "\n".join(["<sub>Passe o mouse sobre cada selo para ver o que ele exige.</sub>",
                      "", " ".join(selos)])


def bloco_cronica(d):
    recentes = sorted(d["repos"], key=lambda r: r["push"], reverse=True)[:6]
    out = ["| Quando | Feito |", "|:--|:--|"]
    for r in recentes:
        quando = datetime.fromisoformat(r["push"].replace("Z", "+00:00")).strftime("%d/%m")
        nome = f'`{r["nome"]}`'
        out.append(f"| <sub>{quando}</sub> | forjou em {nome} |")
    return "\n".join(out)


BLOCOS = {
    "equipamento": bloco_equipamento,
    "feitos": bloco_feitos,
    "cronica": bloco_cronica,
}


# ------------------------------------------------------------------ svg

BASE_SVG = os.path.join(os.path.dirname(__file__), "..", "ficha", "base.svg")
SAIDA_SVG = os.path.join(os.path.dirname(__file__), "..", "ficha", "ficha.svg")

PAL_HP, PAL_MP, PAL_ST = "#8c2f2f", "#3f7a8c", "#6b8f3a"
VELLUM, DIM = "#e6d3a3", "#8a7c62"


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
        "NOME": d["nome"], "NIVEL": str(d["nivel"]),
        "CLASSE": f'{d["classe"][0]} - {d["classe"][1]}',
        "LINHA": " . ".join(filter(None, [
            d["local"], f'jornada iniciada em {d["criado"][:4]}',
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
        v[f"N_{letra}"], v[f"V_{letra}"], v[f"D_{letra}"] = nome, str(valor), porque

    with open(BASE_SVG, encoding="utf-8") as f:
        svg = f.read()
    for chave, valor in v.items():
        svg = svg.replace("{{" + chave + "}}", str(valor).replace("&", "e"))
    faltando = re.findall(r"\{\{(\w+)\}\}", svg)
    if faltando:
        raise SystemExit("placeholder sem valor no template: " + ", ".join(set(faltando)))
    with open(SAIDA_SVG, "w", encoding="utf-8") as f:
        f.write(svg)
    return svg


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

# ------------------------------------------------------------------ escrita


def preencher(texto, d):
    faltando = []
    for chave, fn in BLOCOS.items():
        padrao = re.compile(
            rf"(<!-- ficha:{chave}:inicio -->)(.*?)(<!-- ficha:{chave}:fim -->)", re.S)
        if not padrao.search(texto):
            faltando.append(chave)
            continue
        texto = padrao.sub(lambda m: f"{m.group(1)}\n\n{fn(d)}\n\n{m.group(3)}", texto)
    if faltando:
        print("aviso: marcadores ausentes no README:", ", ".join(faltando), file=sys.stderr)
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
    novo = preencher(antigo, d)
    if novo == antigo:
        print("markdown sem alteracao (svg regravado)")
        return
    with open(README, "w", encoding="utf-8") as f:
        f.write(novo)
    print("ficha atualizada")


if __name__ == "__main__":
    main()
