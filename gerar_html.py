import json
import os
from datetime import datetime, timedelta, timezone

from dados_jogos import JOGOS

# Mapa nome → flag construído a partir dos dados fixos
NOME_PARA_FLAG: dict = {}
for _j in JOGOS:
    NOME_PARA_FLAG[_j["time1"]] = _j["flag1"]
    NOME_PARA_FLAG[_j["time2"]] = _j["flag2"]

BRASILIA = timezone(timedelta(hours=-3))

FASE_COR = {
    "Grupos": "#10b981",
    "32avos": "#60a5fa",
    "Oitavas": "#a78bfa",
    "Quartas": "#f472b6",
    "Semifinal": "#fbbf24",
    "3º Lugar": "#fb923c",
    "Final": "#f59e0b",
}

TIMES_DESTAQUE = [
    ("🇧🇷", "Brasil"),
    ("🇦🇷", "Argentina"),
    ("🇲🇽", "México"),
    ("🇧🇪", "Bélgica"),
]

FUSOS = [
    ("🇧🇷", "Brasil", "America/Sao_Paulo"),
    ("🇲🇽", "México", "America/Monterrey"),
    ("🇧🇪", "Bélgica", "Europe/Brussels"),
    ("🇺🇸", "EUA", "America/New_York"),
]


def parse_hora(hora_str):
    if hora_str in ("?", ""):
        return (23, 59)
    hora_str = hora_str.rstrip("h").replace("h", ":")
    if ":" in hora_str:
        h, m = hora_str.split(":")
        return (int(h), int(m))
    return (int(hora_str), 0)


def data_jogo_brasilia(jogo):
    dia, mes = jogo["data"].split("/")
    h, m = parse_hora(jogo["hora"])
    return datetime(2026, int(mes), int(dia), h, m)


def utc_iso(jogo):
    if jogo["hora"] in ("?", ""):
        return None
    dt = data_jogo_brasilia(jogo).replace(tzinfo=BRASILIA)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def gerar_html(resultados_path="resultados.json", output_path="index.html"):
    resultados = {}
    if os.path.exists(resultados_path):
        with open(resultados_path, "r", encoding="utf-8") as f:
            resultados = json.load(f)

    agora_brasilia = datetime.now(BRASILIA).replace(tzinfo=None)
    atualizado_em = agora_brasilia.strftime("%d/%m/%Y %H:%M")

    jogos_enriquecidos = []

    for i, jogo in enumerate(JOGOS):
        j = dict(jogo)
        rid = str(j["id"])
        res = resultados.get(rid, {})
        j["gols1"] = res.get("gols1")
        j["gols2"] = res.get("gols2")
        j["encerrado"] = res.get("encerrado", False)
        j["ao_vivo"] = res.get("ao_vivo", False) and not j["encerrado"]
        # Preenche times reais do bracket mata-mata quando a API já os definiu
        if res.get("time1_real"):
            j["time1"] = res["time1_real"]
            j["flag1"] = NOME_PARA_FLAG.get(res["time1_real"], "🏳")
        if res.get("time2_real"):
            j["time2"] = res["time2_real"]
            j["flag2"] = NOME_PARA_FLAG.get(res["time2_real"], "🏳")
        j["dt"] = data_jogo_brasilia(j)
        j["utc"] = utc_iso(j)
        jogos_enriquecidos.append(j)

    # Próximo jogo = jogo futuro não-encerrado mais cedo no tempo.
    # JOGOS não está em ordem cronológica, então selecionamos por menor data
    # (antes pegávamos o primeiro da lista, o que pulava dias inteiros).
    def _eh_futuro(j):
        if j["encerrado"] or j["ao_vivo"]:
            return False
        if j["hora"] in ("?", ""):
            return j["dt"].date() >= agora_brasilia.date()
        return j["dt"] > agora_brasilia

    futuros = [i for i, j in enumerate(jogos_enriquecidos) if _eh_futuro(j)]
    proximo_idx = min(futuros, key=lambda i: jogos_enriquecidos[i]["dt"]) if futuros else None

    def card_html(j, is_proximo=False):
        cor = FASE_COR.get(j["fase"], "#10b981")
        encerrado = j["encerrado"]
        ao_vivo = j["ao_vivo"]
        opacity = "opacity:0.55;" if encerrado else ""
        if ao_vivo:
            borda = "border:2px solid #ef4444;box-shadow:0 0 18px #ef444455;"
        elif is_proximo:
            borda = "border:2px solid #22c55e;box-shadow:0 0 18px #22c55e44;"
        else:
            borda = "border:1px solid #1a2a20;"
        if (encerrado or ao_vivo) and j["gols1"] is not None and j["gols2"] is not None:
            estilo_placar = ' style="color:#ef4444;"' if ao_vivo else ""
            center_html = f'<span class="placar"{estilo_placar}>{j["gols1"]} – {j["gols2"]}</span>'
        else:
            center_html = "vs"
        if ao_vivo:
            proximo_badge = '<div class="badge-aovivo">🔴 AO VIVO</div>'
        elif is_proximo:
            proximo_badge = '<div class="badge-proximo">⚡ PRÓXIMO JOGO</div>'
        else:
            proximo_badge = ""
        tag_label = f"Grupo {j['grupo']}" if j["grupo"] else j["fase"]
        fase_tag = (
            f'<div class="fase-tag" style="background:{cor};color:#052e16;">{tag_label}</div>'
        )

        utc_attr = f'data-utc="{j["utc"]}"' if j["utc"] else ""
        hora_default = f"{j['dia']} · {j['data']} · {j['hora']}"

        return f"""
        <div class="card" data-fase="{j["fase"]}" data-times="{j["time1"].lower()} {j["time2"].lower()}" style="{opacity}{borda}border-radius:12px;background:#0d1a12;padding:12px 16px;margin-bottom:10px;position:relative;">
          {proximo_badge}
          {fase_tag}
          <div class="card-times">
            <div class="card-time">
              <span class="card-flag">{j["flag1"]}</span>
              <span class="card-name">{j["time1"]}</span>
            </div>
            <div class="card-vs">{center_html}</div>
            <div class="card-time card-time-away">
              <span class="card-flag">{j["flag2"]}</span>
              <span class="card-name">{j["time2"]}</span>
            </div>
          </div>
          <div class="card-meta">
            <span class="card-fase-badge" style="background:{cor}22;color:{cor};border:1px solid {cor}44;border-radius:6px;padding:2px 8px;font-size:0.72rem;font-family:'Space Mono',monospace;">{tag_label}</span>
            <span style="color:#4a7a5a;font-size:0.75rem;font-family:'Space Mono',monospace;">📅 <span class="hora-display" {utc_attr}>{hora_default}</span> · 📍 {j["local"]}</span>
          </div>
        </div>"""

    # Separar jogos em seções
    proximo_jogo = jogos_enriquecidos[proximo_idx] if proximo_idx is not None else None
    proximo_id = proximo_jogo["id"] if proximo_jogo else None

    # Jogos em andamento (começaram, API ainda não encerrou) ganham seção própria
    ao_vivo_jogos = sorted(
        (j for j in jogos_enriquecidos if j["ao_vivo"]),
        key=lambda j: j["dt"],
    )

    grupos_jogos = [j for j in jogos_enriquecidos if j["fase"] == "Grupos"]
    # Próximo jogo e jogos ao vivo já aparecem em seções dedicadas — excluir das outras
    mata_jogos = [
        j
        for j in jogos_enriquecidos
        if j["fase"] != "Grupos" and j["id"] != proximo_id and not j["ao_vivo"]
    ]

    encerrados_grupos = [j for j in grupos_jogos if j["encerrado"]]
    proximos_grupos = sorted(
        (
            j
            for j in grupos_jogos
            if not j["encerrado"] and not j["ao_vivo"] and j["id"] != proximo_id
        ),
        key=lambda j: j["dt"],
    )
    mata_encerrados = [j for j in mata_jogos if j["encerrado"]]
    mata_proximos = sorted(
        (
            j
            for j in mata_jogos
            if not j["encerrado"] and j["time1"] != "A definir" and j["time2"] != "A definir"
        ),
        key=lambda j: j["dt"],
    )
    mata_a_definir = [
        j
        for j in mata_jogos
        if not j["encerrado"] and (j["time1"] == "A definir" or j["time2"] == "A definir")
    ]

    # Montar lista de times para o dropdown
    destaque_nomes = {t[1].lower() for t in TIMES_DESTAQUE}
    todos_times = sorted(
        {
            j[campo]
            for j in jogos_enriquecidos
            for campo in ("time1", "time2")
            if j[campo] != "A definir" and j[campo].lower() not in destaque_nomes
        }
    )

    # Pré-computar blocos de cards e seções condicionais
    secao_aovivo = (
        (
            "<div class='secao-titulo'>🔴 Ao vivo</div>\n"
            + "\n".join(card_html(j) for j in ao_vivo_jogos)
        )
        if ao_vivo_jogos
        else ""
    )
    secao_proximo = (
        ("<div class='secao-titulo'>Próximo jogo</div>" + card_html(proximo_jogo, is_proximo=True))
        if proximo_jogo
        else ""
    )
    secao_mata_enc = (
        (
            "<div class='secao-titulo' id='resultados-mata'>Resultados — Mata-mata</div>\n"
            + "\n".join(card_html(j) for j in reversed(mata_encerrados))
        )
        if mata_encerrados
        else ""
    )
    secao_mata_prox = (
        (
            "<div class='secao-titulo'>Próximos — Mata-mata</div>\n"
            + "\n".join(card_html(j) for j in mata_proximos)
        )
        if mata_proximos
        else ""
    )
    secao_grp_prox = (
        (
            "<div class='secao-titulo'>Próximos jogos — Grupos</div>\n"
            + "\n".join(card_html(j) for j in proximos_grupos)
        )
        if proximos_grupos
        else ""
    )
    secao_mata_adef = (
        (
            "<details><summary>A definir — Mata-mata</summary><div style='margin-top:12px;'>"
            + "\n".join(card_html(j) for j in mata_a_definir)
            + "</div></details>"
        )
        if mata_a_definir
        else ""
    )
    secao_grp_enc = (
        (
            "<details id='resultados-grupos'><summary>Resultados — Grupos</summary><div style='margin-top:12px;'>"
            + "\n".join(card_html(j) for j in reversed(encerrados_grupos))
            + "</div></details>"
        )
        if encerrados_grupos
        else ""
    )

    # Pré-computar strings para evitar backslash em f-string (Python 3.9)
    btns_destaque = "".join(
        f'<button class="btn" onclick="filtrarBtn(this,\'{t[1].lower()}\')">{t[0]} {t[1]}</button>'
        for t in TIMES_DESTAQUE
    )
    options_dropdown = "".join(f'<option value="{t.lower()}">{t}</option>' for t in todos_times)
    btns_fusos = "".join(
        f'<button class="btn{" ativo" if i == 0 else ""}" onclick="mudarFuso(this,\'{f[2]}\')">{f[0]} {f[1]}</button>'
        for i, f in enumerate(FUSOS)
    )
    btn_resultados = (
        '<a href="#" onclick="irParaResultados();return false;" class="header-link">📊 Resultados</a>'
        if (mata_encerrados or encerrados_grupos)
        else ""
    )

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>Copa do Mundo 2026 🏆</title>
  <link rel="manifest" href="manifest.json"/>
  <link rel="apple-touch-icon" href="icon.png"/>
  <meta name="apple-mobile-web-app-capable" content="yes"/>
  <meta name="apple-mobile-web-app-title" content="Copa2026"/>
  <link rel="preconnect" href="https://fonts.googleapis.com"/>
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
  <link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet"/>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: #080e0a;
      color: #c8e6d0;
      font-family: 'Syne', sans-serif;
      min-height: 100vh;
      padding-bottom: 60px;
    }}
    header {{
      background: linear-gradient(135deg, #0a1a0e 0%, #0d2515 50%, #0a1a0e 100%);
      border-bottom: 1px solid #1a3020;
      padding: 28px 20px 22px;
      text-align: center;
    }}
    header h1 {{ font-size: clamp(1.6rem, 5vw, 2.4rem); font-weight: 800; color: #f0fdf4; letter-spacing: -0.5px; }}
    header p  {{ color: #4a7a5a; font-family: 'Space Mono', monospace; font-size: 0.78rem; margin-top: 6px; }}
    .header-links {{ margin-top: 14px; display: flex; gap: 8px; justify-content: center; flex-wrap: wrap; }}
    .header-link {{
      display: inline-block; background: transparent; color: #4a7a5a;
      border: 1px solid #1a3020; border-radius: 8px; padding: 5px 16px;
      font-family: 'Space Mono', monospace; font-size: 0.72rem;
      text-decoration: none; transition: all 0.15s; cursor: pointer;
    }}
    .header-link:hover {{ color: #a8d4b4; border-color: #2a4a30; }}
    .filtros {{
      display: flex;
      flex-direction: column;
      gap: 10px;
      padding: 14px 20px;
      background: #0a140d;
      border-bottom: 1px solid #1a2a20;
      align-items: center;
    }}
    .filtros-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      justify-content: center;
      align-items: center;
      width: 100%;
    }}
    .filtros-divider {{
      width: 100%;
      height: 1px;
      background: #1a2a20;
    }}
    .filtros-label {{
      color: #2d5a3d;
      font-family: 'Space Mono', monospace;
      font-size: 0.65rem;
      letter-spacing: 1px;
      text-transform: uppercase;
      padding-right: 4px;
    }}
    .btn {{
      background: #0d1a12;
      color: #6b9a7b;
      border: 1px solid #1a2a20;
      border-radius: 8px;
      padding: 6px 14px;
      font-family: 'Space Mono', monospace;
      font-size: 0.75rem;
      cursor: pointer;
      transition: all 0.15s;
    }}
    .btn:hover {{ background: #142a1c; color: #a8d4b4; }}
    .btn.ativo {{ background: #10b98122; color: #10b981; border-color: #10b98166; }}
    .btn-fuso.ativo {{ background: #60a5fa22; color: #60a5fa; border-color: #60a5fa66; }}
    .select-time {{
      background: #0d1a12;
      color: #6b9a7b;
      border: 1px solid #1a2a20;
      border-radius: 8px;
      padding: 6px 28px 6px 14px;
      font-family: 'Space Mono', monospace;
      font-size: 0.75rem;
      cursor: pointer;
      appearance: none;
      -webkit-appearance: none;
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M0 0l5 6 5-6z' fill='%236b9a7b'/%3E%3C/svg%3E");
      background-repeat: no-repeat;
      background-position: right 10px center;
      transition: all 0.15s;
    }}
    .select-time:hover {{ background-color: #142a1c; color: #a8d4b4; }}
    .select-time.ativo {{ background-color: #10b98122; color: #10b981; border-color: #10b98166; }}
    .main {{ max-width: 580px; margin: 0 auto; padding: 24px 16px 0; }}
    .secao-titulo {{
      font-size: 0.72rem;
      font-family: 'Space Mono', monospace;
      color: #4a7a5a;
      letter-spacing: 2px;
      text-transform: uppercase;
      margin: 28px 0 12px;
      border-left: 3px solid #10b981;
      padding-left: 10px;
    }}
    .card {{ transition: opacity 0.2s; }}
    .card:hover {{ opacity: 1 !important; }}
    .placar {{ font-family: 'Space Mono', monospace; font-size: 1.3rem; font-weight: 700; color: #10b981; white-space: nowrap; }}
    .card-times {{ display:flex; align-items:center; justify-content:space-between; gap:8px; }}
    .card-time {{ display:flex; align-items:center; gap:10px; flex:1; min-width:0; }}
    .fase-tag {{ display:none; }}
    .card-flag {{ font-size:1.6rem; flex-shrink:0; line-height:1; }}
    .card-name {{ color:#e2f0e8; font-family:'Space Mono',monospace; font-size:0.88rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; flex:1; min-width:0; }}
    .card-vs {{ color:#4a7a5a; font-family:'Space Mono',monospace; font-size:0.78rem; padding:0 10px; flex-shrink:0; }}
    .card-meta {{ margin-top:8px; display:flex; flex-wrap:wrap; gap:8px; align-items:center; justify-content:center; }}
    .badge-proximo {{
      position: absolute; top: -10px; left: 14px;
      background: #22c55e; color: #052e16;
      font-family: 'Space Mono', monospace; font-size: 0.65rem; font-weight: 700;
      padding: 2px 10px; border-radius: 4px; letter-spacing: 0.5px;
    }}
    .badge-aovivo {{
      position: absolute; top: -10px; left: 14px;
      background: #ef4444; color: #fff;
      font-family: 'Space Mono', monospace; font-size: 0.65rem; font-weight: 700;
      padding: 2px 10px; border-radius: 4px; letter-spacing: 0.5px;
      animation: pulse-aovivo 1.4s ease-in-out infinite;
    }}
    @keyframes pulse-aovivo {{
      0%, 100% {{ opacity: 1; box-shadow: 0 0 0 0 #ef444466; }}
      50% {{ opacity: 0.85; box-shadow: 0 0 0 5px #ef444400; }}
    }}
    details summary {{
      cursor: pointer; user-select: none;
      color: #6b9a7b; font-family: 'Space Mono', monospace;
      font-size: 0.72rem; letter-spacing: 2px; text-transform: uppercase;
      margin: 28px 0 12px; padding-left: 10px;
      border-left: 3px solid #60a5fa; list-style: none;
    }}
    details summary::after {{ content: " ▶"; }}
    details[open] summary::after {{ content: " ▼"; }}
    footer {{ text-align: center; color: #2d5a3d; font-family: 'Space Mono', monospace; font-size: 0.7rem; margin-top: 48px; padding: 0 16px; line-height: 1.8; }}
    @media (min-width: 1024px) {{
      .card-time-away {{ flex-direction:row-reverse; }}
      .card-time-away .card-name {{ text-align:right; }}
    }}
    @media (max-width: 480px), (max-height: 500px) and (orientation: landscape) {{
      .filtros {{ padding: 10px 12px; }}
      .btn {{ padding: 5px 10px; font-size: 0.7rem; }}
      .card-times {{ flex-direction:column; align-items:center; gap:6px; }}
      .card-time, .card-time-away {{ flex:none; flex-direction:row; justify-content:center; width:100%; }}
      .card-name {{ flex:none; font-size:0.85rem; }}
      .card-vs {{ width:100%; text-align:center; padding:5px 0; border-top:1px solid #1a2a20; border-bottom:1px solid #1a2a20; margin:1px 0; }}
      .placar {{ display:block; text-align:center; padding:2px 0; font-size:1.15rem; }}
      .card-meta {{ text-align:center; }}
      .card-fase-badge {{ display:none; }}
      .card-times {{ padding-top:22px; }}
      .fase-tag {{ display:block; position:absolute; top:10px; right:12px; font-family:'Space Mono',monospace; font-size:0.62rem; font-weight:700; padding:2px 10px; border-radius:4px; letter-spacing:0.5px; }}
    }}
    #voltar-topo {{
      position: fixed; bottom: 20px; right: 20px; z-index: 50;
      width: 44px; height: 44px; border-radius: 50%;
      background: #0d1a12; color: #6b9a7b; border: 1px solid #1a3020;
      font-size: 1.2rem; line-height: 1; cursor: pointer;
      display: flex; align-items: center; justify-content: center;
      opacity: 0; visibility: hidden; transition: opacity 0.2s, background 0.15s, color 0.15s;
      box-shadow: 0 2px 12px #00000066;
    }}
    #voltar-topo.visivel {{ opacity: 1; visibility: visible; }}
    #voltar-topo:hover {{ background: #142a1c; color: #a8d4b4; }}
  </style>
</head>
<body>

<header>
  <h1>Copa do Mundo 2026 🏆</h1>
  <p>48 seleções · EUA, Canadá e México</p>
  <div class="header-links">
    <a href="mundiais.html" class="header-link">🌍 Histórico de Mundiais</a>
    {btn_resultados}
  </div>
</header>

<div class="filtros">
  <div class="filtros-row" id="filtro-times">
    <span class="filtros-label">Time</span>
    <button class="btn ativo" onclick="filtrarBtn(this,'todos')">Todos</button>
    {btns_destaque}
    <select class="select-time" id="select-outro" onchange="filtrarSelect(this)">
      <option value="">Outro time ▾</option>
      {options_dropdown}
    </select>
  </div>
  <div class="filtros-divider"></div>
  <div class="filtros-row" id="filtro-fases">
    <span class="filtros-label">Fase</span>
    <button class="btn ativo" onclick="filtrarFase(this,'todos')">Todos</button>
    <button class="btn" onclick="filtrarFase(this,'grupos')">Grupos</button>
    <button class="btn" onclick="filtrarFase(this,'32avos')">32 avos</button>
    <button class="btn" onclick="filtrarFase(this,'oitavas')">Oitavas</button>
    <button class="btn" onclick="filtrarFase(this,'quartas')">Quartas</button>
    <button class="btn" onclick="filtrarFase(this,'semifinal')">Semifinal</button>
    <button class="btn" onclick="filtrarFase(this,'final')">Final</button>
  </div>
  <div class="filtros-divider"></div>
  <div class="filtros-row" id="filtro-fusos">
    <span class="filtros-label">🕐 Fuso</span>
    {btns_fusos}
  </div>
</div>

<div class="main" id="conteudo">

  {secao_aovivo}

  {secao_proximo}

  {secao_mata_enc}

  {secao_mata_prox}

  {secao_grp_prox}

  {secao_mata_adef}

  {secao_grp_enc}

</div>

<div style="text-align:center;margin-top:36px;">
  <a href="mundiais.html" style="display:inline-block;margin-bottom:14px;background:#0d1a12;color:#6b9a7b;border:1px solid #1a2a20;border-radius:8px;padding:7px 18px;font-family:'Space Mono',monospace;font-size:0.75rem;text-decoration:none;transition:all 0.15s;" onmouseover="this.style.background='#142a1c';this.style.color='#a8d4b4'" onmouseout="this.style.background='#0d1a12';this.style.color='#6b9a7b'">🌍 Histórico de Mundiais</a>
</div>

<footer>
  <span id="footer-fuso">Horários em Brasília</span> · Fonte: football-data.org · Atualizado em {atualizado_em}
</footer>

<button id="voltar-topo" onclick="voltarAoTopo()" aria-label="Voltar ao topo" title="Voltar ao topo">↑</button>

<script>
  let filtroTime = 'todos';
  let filtroFase = 'todos';
  let fusoAtual  = 'America/Sao_Paulo';

  const NOMES_FUSO = {{
    'America/Sao_Paulo': 'Brasil',
    'America/Monterrey': 'México',
    'Europe/Brussels':   'Bélgica',
    'America/New_York':  'EUA',
  }};

  // ── filtros de time ──────────────────────────────────────────────────────
  function filtrarBtn(btn, valor) {{
    filtroTime = valor;
    document.querySelectorAll('#filtro-times .btn').forEach(b => b.classList.remove('ativo'));
    btn.classList.add('ativo');
    const sel = document.getElementById('select-outro');
    sel.value = '';
    sel.classList.remove('ativo');
    aplicarFiltros();
  }}

  function filtrarSelect(sel) {{
    filtroTime = sel.value || 'todos';
    document.querySelectorAll('#filtro-times .btn').forEach(b => b.classList.remove('ativo'));
    if (sel.value) {{
      sel.classList.add('ativo');
    }} else {{
      sel.classList.remove('ativo');
      document.querySelector('#filtro-times .btn').classList.add('ativo');
    }}
    aplicarFiltros();
  }}

  // ── filtros de fase ──────────────────────────────────────────────────────
  function filtrarFase(btn, valor) {{
    filtroFase = valor;
    document.querySelectorAll('#filtro-fases .btn').forEach(b => b.classList.remove('ativo'));
    btn.classList.add('ativo');
    aplicarFiltros();
  }}

  function aplicarFiltros() {{
    document.querySelectorAll('.card').forEach(card => {{
      const times  = card.dataset.times || '';
      const fase   = (card.dataset.fase || '').toLowerCase();
      const okTime = filtroTime === 'todos' || times.includes(filtroTime);
      const okFase = filtroFase === 'todos' || fase === filtroFase || (filtroFase === 'final' && fase === '3º lugar');
      card.style.display = (okTime && okFase) ? '' : 'none';
    }});
  }}

  // ── fuso horário ─────────────────────────────────────────────────────────
  function mudarFuso(btn, tz) {{
    fusoAtual = tz;
    document.querySelectorAll('#filtro-fusos .btn').forEach(b => b.classList.remove('ativo'));
    btn.classList.add('ativo');
    atualizarHorarios();
    document.getElementById('footer-fuso').textContent = 'Horários em ' + NOMES_FUSO[tz];
  }}

  function atualizarHorarios() {{
    document.querySelectorAll('.hora-display[data-utc]').forEach(el => {{
      const d = new Date(el.dataset.utc);
      const parts = {{}};
      new Intl.DateTimeFormat('pt-BR', {{
        timeZone: fusoAtual,
        weekday: 'short',
        day: '2-digit',
        month: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
      }}).formatToParts(d).forEach(p => parts[p.type] = p.value);

      const min   = parts.minute;
      const hora  = min === '00' ? parts.hour + 'h' : parts.hour + 'h' + min;
      const dia   = (parts.weekday || '').replace('.', '');
      el.textContent = dia + ' ' + parts.day + '/' + parts.month + ' ' + hora;
    }});
  }}

  // ── atalho para resultados ───────────────────────────────────────────────
  function irParaResultados() {{
    const grupos = document.getElementById('resultados-grupos');
    if (grupos) grupos.open = true;
    const alvo = document.getElementById('resultados-mata') || grupos;
    if (alvo) alvo.scrollIntoView({{behavior: 'smooth'}});
  }}

  // ── voltar ao topo ───────────────────────────────────────────────────────
  function voltarAoTopo() {{
    window.scrollTo({{top: 0, behavior: 'smooth'}});
  }}

  const _btnTopo = document.getElementById('voltar-topo');
  window.addEventListener('scroll', () => {{
    _btnTopo.classList.toggle('visivel', window.scrollY > 400);
  }}, {{passive: true}});
</script>

</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[gerar_html] index.html gerado com {len(jogos_enriquecidos)} jogos.")


if __name__ == "__main__":
    gerar_html()
