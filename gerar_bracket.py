"""gerar_bracket.py — Copa 2026

Gera bracket.html: visão de chaveamento (árvore do mata-mata com conectores),
tabelas de classificação dos grupos e abas por fase (GS/R32/R16/QF/SF/F).

Reaproveita o pipeline existente: lê os mesmos dados de dados_jogos.py e o mesmo
resultados.json que o index.html. As coordenadas da árvore são calculadas em
Python (posicionamento absoluto + conectores SVG) a partir de MATA_ARVORE, que é
a adjacência verificada dos resultados reais.
"""

import json
import os
from collections import OrderedDict

from dados_jogos import JOGOS, MATA_ARVORE
from gerar_html import NOME_PARA_FLAG, data_jogo_brasilia, utc_iso

# ── Dimensões do layout (px) ──────────────────────────────────────────────────
CARD_W = 168
CARD_H = 62
ROW_H = 78  # espaçamento vertical entre as 16 folhas (R32)
COL_W = 220  # largura de uma coluna de rodada (card + espaço do conector)
PAD_X = 20
PAD_Y = 20

# Cor de destaque por rodada (coerente com FASE_COR do gerar_html)
ROUND_COR = {
    "32avos": "#60a5fa",
    "Oitavas": "#a78bfa",
    "Quartas": "#f472b6",
    "Semifinal": "#fbbf24",
    "Final": "#f59e0b",
}

# Abas: (código exibido, fase interna, lista de ids da rodada)
ROUNDS = [
    ("R32", "32avos", list(range(73, 89))),
    ("R16", "Oitavas", list(range(89, 97))),
    ("QF", "Quartas", list(range(97, 101))),
    ("SF", "Semifinal", [101, 102]),
    ("F", "Final", [104]),
]
ROUND_INDEX = {fase: i for i, (_, fase, _) in enumerate(ROUNDS)}


def _enriquecer():
    """Aplica resultados.json sobre JOGOS (times reais, placar, pênaltis)."""
    resultados = {}
    if os.path.exists("resultados.json"):
        with open("resultados.json", "r", encoding="utf-8") as f:
            resultados = json.load(f)

    por_id = {}
    for jogo in JOGOS:
        j = dict(jogo)
        res = resultados.get(str(j["id"]), {})
        if res.get("time1_real"):
            j["time1"] = res["time1_real"]
            j["flag1"] = NOME_PARA_FLAG.get(res["time1_real"], "")
        if res.get("time2_real"):
            j["time2"] = res["time2_real"]
            j["flag2"] = NOME_PARA_FLAG.get(res["time2_real"], "")
        j["gols1"] = res.get("gols1")
        j["gols2"] = res.get("gols2")
        j["encerrado"] = bool(res.get("encerrado"))
        # Placar de exibição no bracket: em disputa de pênaltis usamos o tempo
        # normal (reg) + o placar dos pênaltis (pen); senão o placar cheio.
        if res.get("pen1") is not None:
            j["mostra1"] = res.get("reg1")
            j["mostra2"] = res.get("reg2")
            j["pen1"] = res.get("pen1")
            j["pen2"] = res.get("pen2")
        else:
            j["mostra1"] = res.get("gols1")
            j["mostra2"] = res.get("gols2")
            j["pen1"] = None
            j["pen2"] = None
        j["dt"] = data_jogo_brasilia(j)
        j["utc"] = utc_iso(j)
        por_id[j["id"]] = j
    return por_id


def _vencedor(j):
    """1, 2 ou None — qual lado venceu (considera pênaltis)."""
    if not j["encerrado"]:
        return None
    g1, g2 = j["mostra1"], j["mostra2"]
    if g1 is None or g2 is None:
        return None
    if g1 != g2:
        return 1 if g1 > g2 else 2
    if j["pen1"] is not None and j["pen2"] is not None and j["pen1"] != j["pen2"]:
        return 1 if j["pen1"] > j["pen2"] else 2
    return None


# ── Layout da árvore ──────────────────────────────────────────────────────────
def _ordem_folhas(node):
    """Ordem vertical (topo→base) das folhas R32 que dá uma árvore sem cruzamento."""
    if node not in MATA_ARVORE:
        return [node]
    a, b = MATA_ARVORE[node]
    return _ordem_folhas(a) + _ordem_folhas(b)


def _posicoes():
    """id do jogo → (x, y) do canto superior-esquerdo do card."""
    folhas = _ordem_folhas(104)  # 16 ids de R32 em ordem sem cruzamento
    ypos = {rid: i * ROW_H for i, rid in enumerate(folhas)}

    def y_de(node):
        if node in ypos:
            return ypos[node]
        a, b = MATA_ARVORE[node]
        y = (y_de(a) + y_de(b)) / 2
        ypos[node] = y
        return y

    for node in (89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 104):
        y_de(node)

    def x_de(rid):
        for _, fase, ids in ROUNDS:
            if rid in ids:
                return ROUND_INDEX[fase] * COL_W
        return 0

    pos = {rid: (x_de(rid) + PAD_X, y + PAD_Y) for rid, y in ypos.items()}
    # 3º lugar (103): abaixo da Final, na mesma coluna da Final.
    altura_folhas = (len(folhas) - 1) * ROW_H
    pos[103] = (ROUND_INDEX["Final"] * COL_W + PAD_X, altura_folhas + PAD_Y)
    return pos


def _svg_conectores(pos):
    linhas = []
    for pai, (a, b) in MATA_ARVORE.items():
        if pai == 103:  # 3º lugar não é conectado na árvore principal
            continue
        px = pos[pai][0]
        py = pos[pai][1] + CARD_H / 2
        for filho in (a, b):
            cx = pos[filho][0] + CARD_W
            cy = pos[filho][1] + CARD_H / 2
            midx = (cx + px) / 2
            linhas.append(
                f'<path d="M{cx:.0f},{cy:.0f} H{midx:.0f} V{py:.0f} H{px:.0f}" '
                'fill="none" stroke="#1e3a2a" stroke-width="2"/>'
            )
    return "\n".join(linhas)


# ── Cards ─────────────────────────────────────────────────────────────────────
def _linha_time(nome, flag, placar, pen, venceu, encerrado):
    placeholder = nome == "A definir"
    nome_txt = "A definir" if placeholder else nome
    flag_html = (
        '<span class="bm-dot"></span>'
        if placeholder or not flag
        else f'<span class="bm-flag">{flag}</span>'
    )
    classes = "bm-team"
    if encerrado and venceu is False:
        classes += " perdeu"
    elif encerrado and venceu is True:
        classes += " venceu"
    if placar is None:
        sc = ""
    elif pen is not None:
        sc = f'<span class="bm-score">{placar}<span class="bm-pen">({pen})</span></span>'
    else:
        sc = f'<span class="bm-score">{placar}</span>'
    return f'<div class="{classes}">{flag_html}<span class="bm-name">{nome_txt}</span>{sc}</div>'


def _card(j, pos):
    x, y = pos[j["id"]]
    venc = _vencedor(j)
    encerrado = j["encerrado"] and venc is not None
    if encerrado:
        cabecalho = f"{j['dia']}, {j['data']} · Fim"
    else:
        cabecalho = f"{j['dia']}, {j['data']} · {j['hora']}"
    l1 = _linha_time(j["time1"], j["flag1"], j["mostra1"], j["pen1"], venc == 1, encerrado)
    l2 = _linha_time(j["time2"], j["flag2"], j["mostra2"], j["pen2"], venc == 2, encerrado)
    return (
        f'<div class="bm" style="left:{x:.0f}px;top:{y:.0f}px;">'
        f'<div class="bm-head">{cabecalho}</div>{l1}{l2}</div>'
    )


# ── Tabelas de grupo ──────────────────────────────────────────────────────────
def _classificacao(por_id):
    grupos = OrderedDict()
    for j in por_id.values():
        if j["fase"] != "Grupos":
            continue
        g = j["grupo"]
        grupos.setdefault(g, OrderedDict())
        for nome, flag in ((j["time1"], j["flag1"]), (j["time2"], j["flag2"])):
            grupos[g].setdefault(
                nome,
                {"flag": flag, "j": 0, "v": 0, "e": 0, "d": 0, "gp": 0, "gc": 0, "pts": 0},
            )
    for j in por_id.values():
        if j["fase"] != "Grupos" or not j["encerrado"]:
            continue
        g1, g2 = j["gols1"], j["gols2"]
        if g1 is None or g2 is None:
            continue
        g = j["grupo"]
        t1 = grupos[g][j["time1"]]
        t2 = grupos[g][j["time2"]]
        t1["j"] += 1
        t2["j"] += 1
        t1["gp"] += g1
        t1["gc"] += g2
        t2["gp"] += g2
        t2["gc"] += g1
        if g1 > g2:
            t1["v"] += 1
            t2["d"] += 1
            t1["pts"] += 3
        elif g2 > g1:
            t2["v"] += 1
            t1["d"] += 1
            t2["pts"] += 3
        else:
            t1["e"] += 1
            t2["e"] += 1
            t1["pts"] += 1
            t2["pts"] += 1

    def ordenar(times):
        return sorted(
            times.items(),
            key=lambda kv: (-kv[1]["pts"], -(kv[1]["gp"] - kv[1]["gc"]), -kv[1]["gp"]),
        )

    blocos = []
    for g in sorted(grupos):
        linhas = []
        for pos_i, (nome, s) in enumerate(ordenar(grupos[g]), start=1):
            classificado = "class='classif'" if pos_i <= 2 else ""
            sg = s["gp"] - s["gc"]
            sg_txt = f"+{sg}" if sg > 0 else str(sg)
            linhas.append(
                f"<tr {classificado}><td class='cl-pos'>{pos_i}</td>"
                f"<td class='cl-flag'>{s['flag']}</td>"
                f"<td class='cl-nome'>{nome}</td>"
                f"<td>{s['j']}</td><td class='cl-sg'>{sg_txt}</td>"
                f"<td class='cl-pts'>{s['pts']}</td></tr>"
            )
        blocos.append(
            f"<div class='grupo-card'><div class='grupo-titulo'>Grupo {g}</div>"
            "<table class='grupo-tab'><thead><tr>"
            "<th></th><th></th><th class='cl-nome'></th>"
            "<th>J</th><th>SG</th><th>P</th></tr></thead><tbody>"
            + "".join(linhas)
            + "</tbody></table></div>"
        )
    return "".join(blocos)


# ── Montagem final ────────────────────────────────────────────────────────────
def gerar_bracket(output_path="bracket.html"):
    por_id = _enriquecer()
    pos = _posicoes()

    cards = "\n".join(_card(por_id[rid], pos) for rid in list(range(73, 105)))
    conectores = _svg_conectores(pos)

    n_folhas = 16
    largura = len(ROUNDS) * COL_W + CARD_W + PAD_X
    altura = (n_folhas - 1) * ROW_H + CARD_H + PAD_Y * 2 + 90  # +90 p/ o 3º lugar

    # Rótulo "3º lugar" acima do card 103
    x103, y103 = pos[103]
    label_103 = (
        f'<div class="bm-rotulo" style="left:{x103:.0f}px;top:{y103 - 22:.0f}px;">3º lugar</div>'
    )

    abas = "".join(
        f'<button class="aba{" ativa" if i == 0 else ""}" '
        f"onclick=\"mostrarAba(this,'{fase}')\">{cod}</button>"
        for i, (cod, fase, _) in enumerate([("GS", "Grupos", [])] + ROUNDS)
    )

    grupos_html = _classificacao(por_id)

    # Posições de scroll (px) de cada rodada, para a aba centralizar a coluna
    scroll_por_fase = {fase: ROUND_INDEX[fase] * COL_W for _, fase, _ in ROUNDS}

    template = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>Chaveamento — Copa 2026 🏆</title>
  <link rel="apple-touch-icon" href="icon.png"/>
  <link rel="preconnect" href="https://fonts.googleapis.com"/>
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
  <link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet"/>
  <style>
    *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
    body{background:#080e0a;color:#c8e6d0;font-family:'Syne',sans-serif;min-height:100vh;padding-bottom:40px}
    header{background:linear-gradient(135deg,#0a1a0e 0%,#0d2515 50%,#0a1a0e 100%);border-bottom:1px solid #1a3020;padding:22px 20px 16px;text-align:center}
    header h1{font-size:clamp(1.3rem,4.5vw,2rem);font-weight:800;color:#f0fdf4;letter-spacing:-0.5px}
    header p{color:#4a7a5a;font-family:'Space Mono',monospace;font-size:0.72rem;margin-top:5px}
    .header-links{margin-top:12px;display:flex;gap:8px;justify-content:center;flex-wrap:wrap}
    .header-link{display:inline-block;background:transparent;color:#4a7a5a;border:1px solid #1a3020;border-radius:8px;padding:5px 16px;font-family:'Space Mono',monospace;font-size:0.72rem;text-decoration:none;transition:all .15s;cursor:pointer}
    .header-link:hover{color:#a8d4b4;border-color:#2a4a30}
    /* abas de fase */
    .abas{position:sticky;top:0;z-index:30;display:flex;gap:4px;justify-content:center;padding:12px;background:#0a140dee;backdrop-filter:blur(6px);border-bottom:1px solid #1a2a20;flex-wrap:wrap}
    .aba{background:#0d1a12;color:#6b9a7b;border:1px solid #1a2a20;border-radius:8px;padding:7px 16px;font-family:'Space Mono',monospace;font-size:0.8rem;font-weight:700;cursor:pointer;transition:all .15s}
    .aba:hover{background:#142a1c;color:#a8d4b4}
    .aba.ativa{background:#10b98122;color:#10b981;border-color:#10b98166}
    .aviso{max-width:760px;margin:14px auto 0;padding:0 16px;color:#4a7a5a;font-family:'Space Mono',monospace;font-size:0.68rem;text-align:center}
    /* ── bracket ── */
    #bracket-wrap{overflow:auto;padding:16px 8px 24px;-webkit-overflow-scrolling:touch}
    #bracket{position:relative}
    #bracket svg{position:absolute;top:0;left:0;pointer-events:none}
    .bm{position:absolute;width:__CARD_W__px;background:#0d1a12;border:1px solid #1a2a20;border-radius:10px;padding:6px 8px;box-shadow:0 2px 8px #00000044}
    .bm-head{font-family:'Space Mono',monospace;font-size:0.6rem;color:#4a7a5a;margin-bottom:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .bm-team{display:flex;align-items:center;gap:7px;padding:2px 0}
    .bm-flag{font-size:1.05rem;flex-shrink:0;line-height:1}
    .bm-dot{width:16px;height:16px;border-radius:50%;background:#16281d;flex-shrink:0}
    .bm-name{font-family:'Space Mono',monospace;font-size:0.78rem;color:#e2f0e8;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;flex:1;min-width:0}
    .bm-score{font-family:'Space Mono',monospace;font-size:0.82rem;font-weight:700;color:#c8e6d0;flex-shrink:0}
    .bm-pen{font-size:0.62rem;color:#6b9a7b;margin-left:1px}
    .bm-team.perdeu .bm-name,.bm-team.perdeu .bm-score{color:#4a6a55}
    .bm-team.perdeu .bm-flag{opacity:0.5}
    .bm-team.venceu .bm-name{color:#f0fdf4;font-weight:700}
    .bm-team.venceu .bm-score{color:#10b981}
    .bm-rotulo{position:absolute;font-family:'Space Mono',monospace;font-size:0.66rem;color:#fb923c;letter-spacing:1px;text-transform:uppercase}
    /* ── grupos ── */
    #grupos-wrap{max-width:900px;margin:0 auto;padding:18px 16px;display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:14px}
    .grupo-card{background:#0d1a12;border:1px solid #1a2a20;border-radius:12px;padding:12px 14px}
    .grupo-titulo{font-family:'Space Mono',monospace;font-size:0.72rem;color:#10b981;letter-spacing:1px;text-transform:uppercase;margin-bottom:8px}
    .grupo-tab{width:100%;border-collapse:collapse;font-family:'Space Mono',monospace;font-size:0.76rem}
    .grupo-tab th{color:#2d5a3d;font-weight:400;font-size:0.62rem;text-align:center;padding:2px 3px;border-bottom:1px solid #1a2a20}
    .grupo-tab td{padding:5px 3px;text-align:center;color:#a8d4b4}
    .grupo-tab td.cl-pos{color:#4a7a5a;width:16px}
    .grupo-tab td.cl-flag{width:20px;font-size:1rem}
    .grupo-tab td.cl-nome{text-align:left;color:#e2f0e8;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:110px}
    .grupo-tab th.cl-nome{text-align:left}
    .grupo-tab td.cl-sg{color:#6b9a7b}
    .grupo-tab td.cl-pts{color:#f0fdf4;font-weight:700}
    .grupo-tab tr.classif td.cl-pos{color:#10b981;font-weight:700}
    .grupo-tab tr.classif{background:#10b98108}
    footer{text-align:center;color:#2d5a3d;font-family:'Space Mono',monospace;font-size:0.7rem;margin-top:28px;padding:0 16px;line-height:1.8}
  </style>
</head>
<body>
<header>
  <h1>Chaveamento — Copa 2026 🏆</h1>
  <p>Fase de grupos e mata-mata</p>
  <div class="header-links">
    <a href="index.html" class="header-link">← Jogos e resultados</a>
    <a href="mundiais.html" class="header-link">🌍 Histórico</a>
  </div>
</header>

<div class="abas" id="abas">__ABAS__</div>

<div id="grupos-wrap">__GRUPOS__</div>

<div id="bracket-wrap" style="display:none">
  <div class="aviso">Deslize para os lados para ver todo o chaveamento →</div>
  <div id="bracket" style="width:__LARGURA__px;height:__ALTURA__px;margin-top:8px">
    <svg width="__LARGURA__" height="__ALTURA__">__CONECTORES__</svg>
    __CARDS__
    __LABEL103__
  </div>
</div>

<footer>Fonte: football-data.org · Horários em Brasília</footer>

<script>
  var SCROLL_FASE = __SCROLL_JSON__;
  var wrap = document.getElementById('bracket-wrap');
  var grupos = document.getElementById('grupos-wrap');
  function mostrarAba(btn, fase){
    document.querySelectorAll('.aba').forEach(function(b){b.classList.remove('ativa')});
    btn.classList.add('ativa');
    if(fase === 'Grupos'){
      grupos.style.display = 'grid';
      wrap.style.display = 'none';
    } else {
      grupos.style.display = 'none';
      wrap.style.display = 'block';
      var x = SCROLL_FASE[fase] || 0;
      wrap.scrollTo({left: x, behavior: 'smooth'});
    }
  }
</script>
</body>
</html>"""

    html = (
        template.replace("__CARD_W__", str(CARD_W))
        .replace("__ABAS__", abas)
        .replace("__GRUPOS__", grupos_html)
        .replace("__LARGURA__", str(largura))
        .replace("__ALTURA__", str(altura))
        .replace("__CONECTORES__", conectores)
        .replace("__CARDS__", cards)
        .replace("__LABEL103__", label_103)
        .replace("__SCROLL_JSON__", json.dumps(scroll_por_fase))
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[gerar_bracket] {output_path} gerado.")


if __name__ == "__main__":
    gerar_bracket()
