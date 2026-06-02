import json
import os
from datetime import datetime, timezone, timedelta
from dados_jogos import JOGOS

BRASILIA = timezone(timedelta(hours=-3))

FASE_COR = {
    "Grupos":    "#10b981",
    "32avos":    "#60a5fa",
    "Oitavas":   "#a78bfa",
    "Quartas":   "#f472b6",
    "Semifinal": "#fbbf24",
    "3º Lugar":  "#fb923c",
    "Final":     "#f59e0b",
}

FASES_ORDEM = ["Grupos", "32avos", "Oitavas", "Quartas", "Semifinal", "3º Lugar", "Final"]

# Mapeia hora string "16h" / "20h30" para tuple (hora, minuto) para comparação
def parse_hora(hora_str):
    if hora_str in ("?", ""):
        return (23, 59)
    hora_str = hora_str.rstrip("h").replace("h", ":")
    if ":" in hora_str:
        h, m = hora_str.split(":")
        return (int(h), int(m))
    return (int(hora_str), 0)


def data_jogo_brasilia(jogo):
    """Retorna datetime naive representando hora de Brasília do jogo."""
    dia, mes = jogo["data"].split("/")
    h, m = parse_hora(jogo["hora"])
    return datetime(2026, int(mes), int(dia), h, m)


TIMES_DESTAQUE = [
    ("🇧🇷", "Brasil"),
    ("🇦🇷", "Argentina"),
    ("🇲🇽", "México"),
    ("🇧🇪", "Bélgica"),
]

def gerar_html(resultados_path="resultados.json", output_path="index.html"):
    resultados = {}
    if os.path.exists(resultados_path):
        with open(resultados_path, "r", encoding="utf-8") as f:
            resultados = json.load(f)

    agora_brasilia = datetime.now(BRASILIA).replace(tzinfo=None)
    atualizado_em = agora_brasilia.strftime("%d/%m/%Y %H:%M")

    jogos_enriquecidos = []
    proximo_idx = None

    for i, jogo in enumerate(JOGOS):
        j = dict(jogo)
        rid = str(j["id"])
        res = resultados.get(rid, {})
        j["gols1"] = res.get("gols1")
        j["gols2"] = res.get("gols2")
        j["encerrado"] = res.get("encerrado", False)

        dt = data_jogo_brasilia(j)
        j["dt"] = dt

        if not j["encerrado"] and dt > agora_brasilia and proximo_idx is None:
            proximo_idx = i

        jogos_enriquecidos.append(j)

    def card_html(j, is_proximo=False):
        cor = FASE_COR.get(j["fase"], "#10b981")
        grp_label = f"Grupo {j['grupo']} · " if j["grupo"] else ""
        fase_label = j["fase"]
        encerrado = j["encerrado"]
        opacity = "opacity:0.55;" if encerrado else ""
        borda = "border:2px solid #22c55e;box-shadow:0 0 18px #22c55e44;" if is_proximo else f"border:1px solid #1a2a20;"
        placar_html = ""
        if encerrado and j["gols1"] is not None and j["gols2"] is not None:
            placar_html = f'<div class="placar">{j["gols1"]} – {j["gols2"]}</div>'
        proximo_badge = '<div class="badge-proximo">⚡ PRÓXIMO JOGO</div>' if is_proximo else ""

        time1_class = "time-nome"
        time2_class = "time-nome"

        return f"""
        <div class="card" data-fase="{j['fase']}" data-times="{j['time1'].lower()} {j['time2'].lower()}" style="{opacity}{borda}border-radius:12px;background:#0d1a12;padding:16px 18px;margin-bottom:12px;position:relative;">
          {proximo_badge}
          <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap;">
            <div style="display:flex;align-items:center;gap:10px;flex:1;min-width:0;">
              <span style="font-size:1.6rem;">{j['flag1']}</span>
              <span class="{time1_class}" style="color:#e2f0e8;font-family:'Space Mono',monospace;font-size:0.92rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{j['time1']}</span>
            </div>
            {placar_html if encerrado else '<div style="color:#4a7a5a;font-family:Space Mono,monospace;font-size:0.8rem;padding:0 8px;">vs</div>'}
            <div style="display:flex;align-items:center;gap:10px;flex:1;min-width:0;justify-content:flex-end;">
              <span class="{time2_class}" style="color:#e2f0e8;font-family:'Space Mono',monospace;font-size:0.92rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;text-align:right;">{j['time2']}</span>
              <span style="font-size:1.6rem;">{j['flag2']}</span>
            </div>
          </div>
          <div style="margin-top:10px;display:flex;flex-wrap:wrap;gap:8px;align-items:center;">
            <span style="background:{cor}22;color:{cor};border:1px solid {cor}44;border-radius:6px;padding:2px 8px;font-size:0.72rem;font-family:'Space Mono',monospace;">{grp_label}{fase_label}</span>
            <span style="color:#4a7a5a;font-size:0.75rem;font-family:'Space Mono',monospace;">📅 {j['dia']} {j['data']} {j['hora']} · 📍 {j['local']}</span>
          </div>
        </div>"""

    # Separar jogos em seções
    grupos_jogos = [j for j in jogos_enriquecidos if j["fase"] == "Grupos"]
    mata_jogos = [j for j in jogos_enriquecidos if j["fase"] != "Grupos"]

    encerrados = [j for j in grupos_jogos if j["encerrado"]]
    proximos = [j for j in grupos_jogos if not j["encerrado"]]

    # Próximo jogo (pode ser grupos ou mata-mata)
    proximo_jogo = jogos_enriquecidos[proximo_idx] if proximo_idx is not None else None

    # Montar lista de times para o dropdown (todos exceto os de destaque e "A definir")
    destaque_nomes = {t[1].lower() for t in TIMES_DESTAQUE}
    todos_times = sorted({
        j[campo]
        for j in jogos_enriquecidos
        for campo in ("time1", "time2")
        if j[campo] != "A definir" and j[campo].lower() not in destaque_nomes
    })

    # Cards de grupos encerrados
    resultados_cards = "\n".join(card_html(j) for j in reversed(encerrados))
    proximos_cards = "\n".join(
        card_html(j, is_proximo=(j["id"] == proximo_jogo["id"])) if proximo_jogo else card_html(j)
        for j in proximos
    )
    mata_cards = "\n".join(card_html(j) for j in mata_jogos)

    # Pré-computar HTML dos filtros de time (evita backslash em f-string no Python 3.9)
    btns_destaque = "".join(
        f'<button class="btn" onclick="filtrarBtn(this,\'{t[1].lower()}\')">{t[0]} {t[1]}</button>'
        for t in TIMES_DESTAQUE
    )
    options_dropdown = "".join(
        f'<option value="{t.lower()}">{t}</option>'
        for t in todos_times
    )

    # Montar HTML completo
    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>Copa do Mundo 2026 🏆</title>
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
    header h1 {{
      font-size: clamp(1.6rem, 5vw, 2.4rem);
      font-weight: 800;
      color: #f0fdf4;
      letter-spacing: -0.5px;
    }}
    header p {{
      color: #4a7a5a;
      font-family: 'Space Mono', monospace;
      font-size: 0.78rem;
      margin-top: 6px;
    }}
    .filtros {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      padding: 16px 20px;
      background: #0a140d;
      border-bottom: 1px solid #1a2a20;
      justify-content: center;
    }}
    .filtros-group {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      justify-content: center;
    }}
    .filtros-sep {{
      width: 1px;
      background: #1a2a20;
      margin: 0 4px;
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
    .select-time {{
      background: #0d1a12;
      color: #6b9a7b;
      border: 1px solid #1a2a20;
      border-radius: 8px;
      padding: 6px 14px;
      font-family: 'Space Mono', monospace;
      font-size: 0.75rem;
      cursor: pointer;
      appearance: none;
      -webkit-appearance: none;
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M0 0l5 6 5-6z' fill='%236b9a7b'/%3E%3C/svg%3E");
      background-repeat: no-repeat;
      background-position: right 10px center;
      padding-right: 28px;
      transition: all 0.15s;
    }}
    .select-time:hover {{ background-color: #142a1c; color: #a8d4b4; }}
    .select-time.ativo {{ background-color: #10b98122; color: #10b981; border-color: #10b98166; }}
    .main {{ max-width: 780px; margin: 0 auto; padding: 24px 16px 0; }}
    .secao-titulo {{
      font-size: 0.72rem;
      font-family: 'Space Mono', monospace;
      color: #4a7a5a;
      letter-spacing: 2px;
      text-transform: uppercase;
      margin: 28px 0 12px;
      padding-left: 4px;
      border-left: 3px solid #10b981;
      padding-left: 10px;
    }}
    .card {{ transition: opacity 0.2s; }}
    .card:hover {{ opacity: 1 !important; }}
    .placar {{
      font-family: 'Space Mono', monospace;
      font-size: 1.3rem;
      font-weight: 700;
      color: #10b981;
      padding: 0 12px;
      white-space: nowrap;
    }}
    .badge-proximo {{
      position: absolute;
      top: -10px;
      left: 14px;
      background: #22c55e;
      color: #052e16;
      font-family: 'Space Mono', monospace;
      font-size: 0.65rem;
      font-weight: 700;
      padding: 2px 10px;
      border-radius: 4px;
      letter-spacing: 0.5px;
    }}
    details summary {{
      cursor: pointer;
      user-select: none;
      color: #6b9a7b;
      font-family: 'Space Mono', monospace;
      font-size: 0.72rem;
      letter-spacing: 2px;
      text-transform: uppercase;
      margin: 28px 0 12px;
      padding-left: 10px;
      border-left: 3px solid #60a5fa;
      list-style: none;
    }}
    details summary::after {{ content: " ▶"; }}
    details[open] summary::after {{ content: " ▼"; }}
    footer {{
      text-align: center;
      color: #2d5a3d;
      font-family: 'Space Mono', monospace;
      font-size: 0.7rem;
      margin-top: 48px;
      padding: 0 16px;
      line-height: 1.8;
    }}
    @media (max-width: 480px) {{
      .filtros {{ padding: 12px; gap: 6px; }}
      .btn {{ padding: 5px 10px; font-size: 0.7rem; }}
    }}
  </style>
</head>
<body>

<header>
  <h1>Copa do Mundo 2026 🏆</h1>
  <p>Horários em Brasília · 48 seleções · EUA, Canadá e México</p>
</header>

<div class="filtros">
  <div class="filtros-group" id="filtro-times">
    <button class="btn ativo" onclick="filtrarBtn(this,'todos')">Todos</button>
    {btns_destaque}
    <select class="select-time" id="select-outro" onchange="filtrarSelect(this)">
      <option value="">Outro time ▾</option>
      {options_dropdown}
    </select>
  </div>
  <div class="filtros-sep"></div>
  <div class="filtros-group" id="filtro-fases">
    <button class="btn ativo" onclick="filtrar(this,'fase','todos')">Todos</button>
    <button class="btn" onclick="filtrar(this,'fase','grupos')">Grupos</button>
    <button class="btn" onclick="filtrar(this,'fase','32avos')">32 avos</button>
    <button class="btn" onclick="filtrar(this,'fase','oitavas')">Oitavas</button>
    <button class="btn" onclick="filtrar(this,'fase','quartas')">Quartas</button>
    <button class="btn" onclick="filtrar(this,'fase','semifinal')">Semifinal</button>
    <button class="btn" onclick="filtrar(this,'fase','final')">Final</button>
  </div>
</div>

<div class="main" id="conteudo">

  {"<div class='secao-titulo'>Próximo jogo</div>" + card_html(proximo_jogo, is_proximo=True) if proximo_jogo else ""}

  {"<div class='secao-titulo'>Próximos jogos — Grupos</div>" if proximos else ""}
  {proximos_cards}

  {"<div class='secao-titulo'>Resultados — Grupos</div>" if encerrados else ""}
  {resultados_cards}

  <details>
    <summary>Mata-mata</summary>
    <div style="margin-top:12px;">{mata_cards}</div>
  </details>

</div>

<footer>
  Horários em Brasília · Fonte: football-data.org · Atualizado em {atualizado_em}
</footer>

<script>
  let filtroTime = 'todos';
  let filtroFase = 'todos';

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

  function filtrar(btn, tipo, valor) {{
    filtroFase = valor;
    document.querySelectorAll('#filtro-fases .btn').forEach(b => b.classList.remove('ativo'));
    btn.classList.add('ativo');
    aplicarFiltros();
  }}

  function aplicarFiltros() {{
    document.querySelectorAll('.card').forEach(card => {{
      const times = card.dataset.times || '';
      const fase = (card.dataset.fase || '').toLowerCase();
      const okTime = filtroTime === 'todos' || times.includes(filtroTime);
      const okFase = filtroFase === 'todos' || fase === filtroFase || (filtroFase === 'final' && fase === '3º lugar');
      card.style.display = (okTime && okFase) ? '' : 'none';
    }});
  }}
</script>

</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[gerar_html] index.html gerado com {len(jogos_enriquecidos)} jogos.")


if __name__ == "__main__":
    gerar_html()
