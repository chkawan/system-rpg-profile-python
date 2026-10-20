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

from atributos_config import ATRIBUTOS_CONFIG, DISTRIBUICAO_CONFIG
from classes_config import CLASSES_CONFIG
from xp_config import XP_CONFIG, NIVEL_CONFIG
from conquistas_config import TIERS, SEM_TIER, CONQUISTAS

LOGIN = os.environ.get("FICHA_LOGIN")
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
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { contributionCount } }
      }
    }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false,
                 orderBy: {field: PUSHED_AT, direction: DESC}) {
      totalCount
      nodes {
        name pushedAt isPrivate stargazerCount homepageUrl description
        primaryLanguage { name }
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name } }
        }
      }
    }
    pinnedItems(first: 6, types: REPOSITORY) {
      nodes {
        ... on Repository {
          name stargazerCount
          primaryLanguage { name }
        }
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
        detalhes = "; ".join(
            f'{e["message"]} (campo: {".".join(str(p) for p in e.get("path", []))})'
            for e in dados["errors"]
        )
        raise SystemExit("GitHub recusou: " + detalhes)
    if "data" not in dados:
        raise SystemExit(
            f"Resposta inesperada da API (HTTP {r.status_code}): "
            + dados.get("message", str(dados))
        )
    u = dados["data"]["user"]
    calendario = u["contributionsCollection"]["contributionCalendar"]
    dias_contrib = [dia["contributionCount"]
                     for semana in calendario["weeks"] for dia in semana["contributionDays"]]
    return {
        "nome": u["name"] or u["login"],
        "login": u["login"],
        "criado": u["createdAt"],
        "local": u.get("location") or "",
        "seguidores": u["followers"]["totalCount"],
        "commits": calendario["totalContributions"],
        "dias_ativos": sum(1 for c in dias_contrib if c > 0),
        "repos_total": u["repositories"]["totalCount"],
        "repos": [{
            "nome": r["name"], "push": r["pushedAt"], "privado": r["isPrivate"],
            "estrelas": r["stargazerCount"], "tem_url": bool(r["homepageUrl"]),
            "descricao": r["description"],
            "ling": (r["primaryLanguage"] or {}).get("name"),
            "linguagens_bytes": [
                {"nome": e["node"]["name"], "bytes": e["size"]} for e in r["languages"]["edges"]
            ],
        } for r in u["repositories"]["nodes"]],
        "pinned": [{
            "nome": r["name"], "estrelas": r["stargazerCount"],
            "ling": (r["primaryLanguage"] or {}).get("name"),
        } for r in u["pinnedItems"]["nodes"]],
    }


def escala(v, mx, peso=1.0, teto=100):
    """peso>1: curva generosa (sobe rapido) pro atributo que pesa mais na
    carreira dev. peso<1: curva exigente (precisa de muito mais input pro
    mesmo valor) pro atributo que e sinal fraco e facil de inflar.

    teto=100 e so escala de exibicao (0-100%, bater o mx de um atributo
    sempre da 100, nao importa o peso - e matematico: log10(mx+1)/
    log10(mx+1) = 1 sempre). Formula antiga usava teto=30; quem depende
    do valor bruto do atributo (CLASSES_CONFIG, vida/vigor/mana) corrige o
    multiplicador na mesma proporcao (30/100 = 0.6 em vez de 2) pra nao
    inflar o resultado so por causa da troca de escala."""
    bruto = math.log10(v + 1) / math.log10(mx + 1)
    curvado = bruto ** (1 / peso)
    return max(1, min(teto, round(curvado * teto)))


# custo pra sair do nivel N (ir pro N+1): linear, veja NIVEL_CONFIG em
# xp_config.py - sair do nivel 1 custa 120, do nivel 2 custa 240, do
# nivel 3 custa 360... Sem limite de nivel (nivel_de_xp nao tem teto): o
# nivel sobe enquanto tiver XP pra isso, sem limitador artificial - so a
# exibicao do numero no medalhao da ficha encolhe a fonte pra nao vazar
# da borda (ver NIVEL_FONTE em montar_svg).
def custo_nivel(nivel):
    return nivel * NIVEL_CONFIG["custo_base"] * NIVEL_CONFIG["custo_multiplicador"]


def nivel_de_xp(xp):
    nivel = 1
    acumulado = 0
    while xp >= acumulado + custo_nivel(nivel):
        acumulado += custo_nivel(nivel)
        nivel += 1
    return nivel


def progresso_nivel(xp, nivel):
    """XP ja acumulado dentro do nivel atual e quanto falta pro proximo -
    pra barra de EXP mostrar progresso de verdade, nao só repetir o total."""
    acumulado = sum(custo_nivel(n) for n in range(1, nivel))
    return xp - acumulado, custo_nivel(nivel)


# fatia de "total" que cada posicao do ranking leva: 1o lugar fica com
# 40%, 2o com 30%, 3o com 15%, 4o com 10%, 5o e 6o ficam so no residual.
# Sinal de GitHub costuma vir parelho (13,14,15...) - exagerar o VALOR
# (peso**3) nao bastava pra separar; exagerar a POSICAO no ranking sim,
# porque garante 1o/2o/3o lugar sempre bem diferentes, nao importa o
# quao proximos os brutos estejam. Fatias, bonus inicial e tetos ficam
# em DISTRIBUICAO_CONFIG, em atributos_config.py.


def distribuir_pontos(pesos, total, minimo=1, maximo=DISTRIBUICAO_CONFIG["maximo_por_atributo"]):
    """Reparte 'total' pontos (o nivel, max 100) entre os atributos pela
    posicao no ranking de cada um (ver DISTRIBUICAO_CONFIG), nao pelo
    valor bruto. Nenhum atributo passa de 'maximo' mesmo que a fatia desse
    ranking desse mais que isso em nivel alto (40% de 100 = 40) - quem
    estoura o teto fica preso em 'maximo' e o excedente e repartido de
    novo so entre quem ainda nao estourou. Metodo dos restos maiores
    (Hamilton) fecha a soma exata no final."""
    fatias_ranking = DISTRIBUICAO_CONFIG["fatias_ranking"]
    n = len(pesos)
    if total <= n * minimo:
        por_peso = sorted(pesos, key=pesos.get, reverse=True)
        return {k: (minimo if i < total else 0) for i, k in enumerate(por_peso)}
    ordenados = sorted(pesos, key=pesos.get, reverse=True)
    fatias = {nome: fatias_ranking[i] for i, nome in enumerate(ordenados)}

    pontos = {k: minimo for k in pesos}
    pendente = total - minimo * n
    livres = set(pesos)
    while pendente > 0 and livres:
        soma_livres = sum(fatias[k] for k in livres)
        base = {k: pontos[k] + (fatias[k] / soma_livres) * pendente for k in livres}
        estourou = {k for k in livres if base[k] > maximo}
        if not estourou:
            inteiros = {k: int(base[k]) for k in livres}
            sobra = pendente - sum(inteiros[k] - pontos[k] for k in livres)
            fracionarios = sorted(livres, key=lambda k: base[k] - inteiros[k], reverse=True)
            for k in fracionarios[:sobra]:
                inteiros[k] += 1
            for k in livres:
                pontos[k] = inteiros[k]
            pendente = 0
        else:
            for k in estourou:
                pendente -= maximo - pontos[k]
                pontos[k] = maximo
                livres.discard(k)
    return pontos


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
    missoes = selecionar_missoes(repos, d["login"])

    # linguagem por contagem de repos onde aparece como principal (usado
    # pela Inteligencia e pelas barras de Habilidades). O bonus de XP por
    # linguagem (abaixo) usa o dado por repo (linguagens_bytes), que e
    # mais granular - exige token com permissao de leitura de conteudo.
    contagem = {}
    for r in repos:
        if r["ling"]:
            contagem[r["ling"]] = contagem.get(r["ling"], 0) + 1
    total = sum(contagem.values()) or 1
    lings = sorted(({"nome": k, "n": v, "fatia": v / total} for k, v in contagem.items()),
                   key=lambda x: -x["n"])

    # media de contribuicoes por repo que voce mantem - nao e o commit
    # daquele repo especifico (isso exigiria permissao de leitura de
    # conteudo do token, que o FICHA_TOKEN nao tem - foi o que quebrou o
    # workflow), mas usa dados que a API ja entrega de graca: total de
    # contribuicoes do ano dividido pelo total de repositorios.
    media_commits_repo = d["commits"] / (total_repos or 1)

    # XP recompensa esforco de verdade, nao popularidade - valores em
    # XP_CONFIG (xp_config.py). Teto de commits por projeto existe porque
    # sem ele, 5000 commits num unico repo valeriam mais que 10 anos de
    # carreira espalhados em 50 projetos - nao temos commit por repo
    # individual (exigiria permissao que ja quebrou o workflow antes),
    # entao aproximamos com total_repos x teto_commits_por_projeto.
    commits_xp = min(d["commits"], total_repos * XP_CONFIG["teto_commits_por_projeto"])
    xp_linguagens = sum(
        1 for r in repos for lb in r.get("linguagens_bytes", [])
        if lb["bytes"] >= XP_CONFIG["min_bytes_linguagem"]
    ) * XP_CONFIG["por_linguagem_no_projeto"]
    xp = round((
        anos * XP_CONFIG["por_ano"]
        + commits_xp * XP_CONFIG["por_commit"]
        + total_repos * XP_CONFIG["por_projeto"]
        + xp_linguagens
    ) * XP_CONFIG["multiplicador_final"])

    nivel = nivel_de_xp(xp)
    return {**d, "selados": selados, "estrelas": estrelas,
            "com_url": com_url, "total_repos": total_repos,
            "anos": anos, "lings": lings, "num_linguagens": len(lings),
            "media_commits_repo": media_commits_repo, "xp": xp,
            "missoes": missoes, "nivel": nivel,
            "pinned": d.get("pinned", [])[:5]}


def atributos(d):
    """Le a configuracao de atributos_config.py e calcula cada um - fonte,
    teto (mx) e peso vem de la, nao daqui. Pra reorganizar de onde um
    atributo tira o numero (ou o peso/teto dele), edite ATRIBUTOS_CONFIG
    em scripts/atributos_config.py, nao este arquivo."""
    resultado = []
    for nome, cfg in ATRIBUTOS_CONFIG.items():
        fonte = cfg["fonte"]
        if fonte not in d:
            raise SystemExit(
                f"atributos_config.py: '{nome}' aponta pra fonte '{fonte}', que nao existe "
                f"nos dados derivados. Fontes disponiveis: {', '.join(sorted(d))}"
            )
        valor_bruto = d[fonte]
        pontos = escala(valor_bruto, cfg["mx"], peso=cfg["peso"])
        texto_valor = f"{valor_bruto:.1f}" if isinstance(valor_bruto, float) else str(valor_bruto)
        porque = f'{texto_valor} {cfg["rotulo"]}'
        resultado.append((nome, pontos, porque))
    return resultado


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
def determinar_classe(pontos_ficha, minimo=DISTRIBUICAO_CONFIG["minimo_para_classe"]):
    """Le CLASSES_CONFIG (classes_config.py) pra decidir a classe. Uma
    classe qualifica se TODOS os atributos do seu 'requisito' baterem o
    minimo - igual ao pre-requisito real de multiclasse do D&D 5e (o
    Patrulheiro exige Destreza E Sabedoria juntos, nao um ou outro).
    'pontos_ficha' e o orcamento de pontos que soma ao nivel
    (distribuir_pontos), nao a escala crua - em nivel 1-2 o orcamento e
    pequeno demais pra bater o minimo em qualquer atributo, e quem nao se
    qualifica em nenhuma classe cai na classe de requisito vazio
    (Aventureiro): o "ainda nao se especializou".

    O score de cada classe qualificada e o MINIMO entre os atributos do
    seu requisito, nao a soma - soma deixava classe de requisito duplo
    artificialmente mais forte que qualquer classe de requisito simples
    (2o+3o lugar do ranking somados batia o 1o lugar sozinho), mesmo sem
    ela ser de fato a mais especializada nos dois.

    Quando o requisito de uma classe e subconjunto estrito do requisito
    de outra classe tambem qualificada (ex: Ladino=[Destreza] e
    Arqueiro=[Destreza,Sabedoria]), a mais especifica (Arqueiro) sempre
    vence, mesmo com score igual ou menor - ela "absorve" a mais generica."""
    qualificados = []
    for classe, cfg in CLASSES_CONFIG.items():
        requisito = cfg["requisito"]
        if requisito and all(pontos_ficha[attr] >= minimo for attr in requisito):
            score = min(pontos_ficha[attr] for attr in requisito)
            qualificados.append((classe, set(requisito), score))
    if not qualificados:
        return "aventureiro"
    finalistas = [
        (classe, score) for classe, requisito, score in qualificados
        if not any(requisito < outro_requisito for _, outro_requisito, _ in qualificados if outro_requisito != requisito)
    ]
    return max(finalistas, key=lambda item: item[1])[0]


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
# TIERS, SEM_TIER e CONQUISTAS vem de conquistas_config.py. Icones sao so
# o caminho (string) la, porque img_icone() precisa de ICONES_DIR (so
# existe aqui) - por isso cada entrada vira icone de verdade so aqui,
# na hora de montar a lista (ver lista_conquistas() abaixo).


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
    for c in CONQUISTAS:
        valor = d[c["fonte"]]
        icone = img_icone(c["icone"], 34)
        out.append((c["nome"], c["descricao"], valor, icone, tier_de(valor, c["limiares"]), c["limiares"]))
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
    """Um slot de equipamento preenchido: moldura + preenchimento na cor da
    linguagem do repo fixado + nome embaixo (sem icone por repo, o nome faz
    esse papel)."""
    cor = cor_hex if cor_hex.startswith("#") else "#" + cor_hex
    r = w / 2
    return (
        f'<rect x="{cx - r:.0f}" y="{cy - r:.0f}" width="{w}" height="{w}" rx="4" '
        f'fill="{v["DARK"]}" stroke="{v["GOLD"]}" stroke-width="1.5"/>'
        f'<rect x="{cx - r + 4:.0f}" y="{cy - r + 4:.0f}" width="{w - 8}" height="{w - 8}" rx="2" fill="{cor}"/>'
        f'<text x="{cx:.0f}" y="{cy + r + 11:.0f}" font-size="8.5" text-anchor="middle" '
        f'fill="{v["DIM"]}">{escapar(nome)}</text>'
    )


def svg_slot_vazio(cx, cy, w, v):
    """Slot sem repo fixado nessa posicao - convite pra equipar algo."""
    r = w / 2
    return (
        f'<rect x="{cx - r:.0f}" y="{cy - r:.0f}" width="{w}" height="{w}" rx="4" '
        f'fill="none" stroke="{v["DIM"]}" stroke-width="1.5" stroke-dasharray="4,3"/>'
        f'<text x="{cx:.0f}" y="{cy + 4:.0f}" font-size="16" text-anchor="middle" fill="{v["DIM"]}">+</text>'
        f'<text x="{cx:.0f}" y="{cy + r + 11:.0f}" font-size="8.5" text-anchor="middle" '
        f'fill="{v["DIM"]}">vazio</text>'
    )


def svg_equipamento(d, v, icone_classe_fundo):
    """Duas secoes lado a lado: EQUIPAMENTO - um boneco em cruz (elmo,
    arma, armadura, arma, bota) com o icone da classe atual desenhado
    atras, meio transparente, e cada slot preenchido por um dos seus repos
    fixados no perfil (equipar de verdade = dar pin no GitHub) - e
    HABILIDADES (linguagem = skill, nivel = % dos repos, dado real)."""
    x_hab = 452
    largura_col = 396
    out = []

    cx_arm, w_slot, gap_h = 214, 40, 14
    cy_elmo, cy_meio, cy_bota = 500, 556, 612
    posicoes = [
        (cx_arm, cy_elmo),
        (cx_arm - w_slot - gap_h, cy_meio),
        (cx_arm, cy_meio),
        (cx_arm + w_slot + gap_h, cy_meio),
        (cx_arm, cy_bota),
    ]
    out.append(f'<g opacity="0.16">{icone_classe_fundo(cx_arm, cy_meio, v["GOLD"], v["GOLD"])}</g>')
    for i, (sx, sy) in enumerate(posicoes):
        if i < len(d["pinned"]):
            repo = d["pinned"][i]
            cor = CORES.get(repo["ling"], "8a7c62")
            out.append(svg_slot(sx, sy, w_slot, truncar(nome_missao(repo["nome"]), 12), cor, v))
        else:
            out.append(svg_slot_vazio(sx, sy, w_slot, v))

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
        status = "CONCLUÍDA" if concluida else "EM PROGRESSO"
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

    # pontos exibidos na ficha somam nivel + bonus inicial (igual RPG de
    # mesa classico: todo personagem comeca com um punhado de pontos
    # livres de criacao, antes de qualquer nivel - ver Attributes.
    # CREATION_FREE_POINTS=10 no projeto "The Tower"). Vitais abaixo
    # continuam na escala crua (pontos), que ja é a mesma pra qualquer
    # nivel - mas a classe agora usa esse orcamento (pontos_ficha),
    # porque o requisito de classe (ver determinar_classe) e sobre
    # quanto voce investiu, nao sobre o sinal bruto - em nivel baixo o
    # orcamento (mesmo com o bonus) pode ainda ser pequeno demais pra
    # qualificar em qualquer classe, e cai em Aventureiro de proposito.
    pontos_ficha = distribuir_pontos(pontos, d["nivel"] + DISTRIBUICAO_CONFIG["bonus_inicial"])

    # classe vem do atributo (as vezes dois, ver determinar_classe) que
    # mais se destaca - decidida antes dos vitais porque agora os vitais
    # dependem da classe escolhida (ver CLASSES_CONFIG, em classes_config.py)
    classe_chave = determinar_classe(pontos_ficha)
    cfg = CLASSES_CONFIG[classe_chave]
    titulo_classe, complemento_classe, arquivo_classe = cfg["titulo"], cfg["complemento"], cfg["icone"]
    icone_classe = img_icone(arquivo_classe, 64)
    icone_classe_fundo = img_icone(arquivo_classe, 170)

    # vida/vigor/mana no molde classico de RPG, igual ao projeto "The
    # Tower" (eldrin/characters/classes.py + character.py): base +
    # crescimento por nivel, mais o atributo que alimenta aquele vital
    # vezes 0.6. Cada classe tem sua propria tabela nos 3 vitais (ver
    # CLASSES_CONFIG), entao guerreiro e mago nao convergem pro mesmo
    # numero so porque tem o mesmo nivel. Atual = maximo sempre: a ficha
    # retrata o personagem em pleno vigor (full), nao um estado de
    # "gastou X de Y" no meio de uma missao.
    # atributo bruto agora e escala 0-100 (era 0-30) - 0.6 em vez do 2
    # antigo mantem a mesma contribuicao maxima de antes (30*2 = 100*0.6)
    vida_max = cfg["vida_base"] + cfg["vida_por_nivel"] * (d["nivel"] - 1) + pontos["Constituição"] * 0.6
    vigor_max = cfg["vigor_base"] + cfg["vigor_por_nivel"] * (d["nivel"] - 1) + pontos[cfg["vigor_attr"]] * 0.6
    mana_max = cfg["mana_base"] + cfg["mana_por_nivel"] * (d["nivel"] - 1) + pontos[cfg["mana_attr"]] * 0.6
    vida_atual = vida_max
    mana_atual = mana_max
    vigor_atual = vigor_max
    # EXP e o unico vital que mostra progresso de verdade (nao cheio
    # como os outros 3) - faz sentido aqui porque agora existe um limiar
    # real de XP pro proximo nivel (ver nivel_de_xp/progresso_nivel)
    xp_no_nivel, xp_necessario = progresso_nivel(d["xp"], d["nivel"])
    vitais = [
        ("VIDA", vida_atual, vida_max, PAL_HP),
        ("MANA", mana_atual, mana_max, PAL_MP),
        ("VIGOR", vigor_atual, vigor_max, PAL_ST),
        ("EXP", xp_no_nivel, xp_necessario, gold),
    ]

    v = {
        "INK": ink, "STONE": stone, "LIT": lit, "DARK": dark,
        "GOLD": gold, "VELLUM": VELLUM, "DIM": DIM,
        "NOME": escapar(d["nome"]), "NIVEL": str(d["nivel"]),
        # medalhao de nivel tem largura fixa (72px uteis) - sem limite de
        # nivel, o numero pode crescer alem de 2 digitos e vazar da borda;
        # a fonte encolhe a cada dois digitos extras pra sempre caber.
        "NIVEL_FONTE": str(max(14, 34 - max(0, len(str(d["nivel"])) - 2) * 7)),
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
    for letra, (nome, _, porque) in zip("ABCDEF", attrs):
        valor = pontos_ficha[nome]
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
        ("HDR_MISSOES", 1089, "MISSÕES", img_icone("secoes/missoes.png", 26), 16, 848),
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
        if not LOGIN:
            raise SystemExit("defina a variavel de ambiente FICHA_LOGIN com o usuario do GitHub")
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
