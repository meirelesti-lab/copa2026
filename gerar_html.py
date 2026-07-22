"""Gera o index.html — a retrospectiva da Copa do Mundo 2026.

O torneio acabou: a página é um arquivo, não um acompanhamento. Não existe mais
"ao vivo", "próximo jogo" nem auto-correção por tempo. Tudo vem de arquivos
versionados (`resultados.json` + `dados/`), então a geração é determinística e
offline — rodar duas vezes produz exatamente o mesmo HTML.
"""

import json
import os
from datetime import datetime, timedelta, timezone

import estatisticas as est
from dados_jogos import JOGOS

# Mapa nome → flag construído a partir dos dados fixos
NOME_PARA_FLAG: dict = {}
for _j in JOGOS:
    NOME_PARA_FLAG[_j["time1"]] = _j["flag1"]
    NOME_PARA_FLAG[_j["time2"]] = _j["flag2"]

BRASILIA = timezone(timedelta(hours=-3))

CAMPEA = "Espanha"
VICE = "Argentina"
TERCEIRO = "Inglaterra"

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

MARCA_GOL = {"penalti": " (p)", "contra": " (gc)"}


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


def _fmt_media(v):
    return f"{v:.2f}".replace(".", ",")


def gerar_html(resultados_path="resultados.json", output_path="index.html"):
    resultados = {}
    if os.path.exists(resultados_path):
        with open(resultados_path, "r", encoding="utf-8") as f:
            resultados = json.load(f)

    eventos = est.carregar("eventos")
    arbitros = est.carregar("arbitros")
    artilheiros = est.carregar("artilheiros")

    jogos_enriquecidos = []
    for jogo in JOGOS:
        j = dict(jogo)
        res = resultados.get(str(j["id"]), {})
        j["gols1"] = res.get("gols1")
        j["gols2"] = res.get("gols2")
        j["encerrado"] = res.get("encerrado", False)
        for campo in ("reg1", "reg2", "pen1", "pen2"):
            j[campo] = res.get(campo)
        if res.get("time1_real"):
            j["time1"] = res["time1_real"]
            j["flag1"] = NOME_PARA_FLAG.get(res["time1_real"], "🏳")
        if res.get("time2_real"):
            j["time2"] = res["time2_real"]
            j["flag2"] = NOME_PARA_FLAG.get(res["time2_real"], "🏳")
        j["dt"] = data_jogo_brasilia(j)
        j["utc"] = utc_iso(j)
        j["eventos"] = eventos.get(str(j["id"]), {})
        j["arbitro"] = arbitros.get(str(j["id"]), {})
        jogos_enriquecidos.append(j)

    stats = est.calcular(jogos_enriquecidos, eventos)

    def gols_html(j):
        ev = j["eventos"]
        if not ev or not (ev["gols_casa"] or ev["gols_fora"]):
            return ""

        def lista(gols, classe):
            linhas = "".join(
                f'<span class="gol">{g["jogador"]} '
                f"<em>{g['minuto']}'{MARCA_GOL.get(g['tipo'], '')}</em></span>"
                for g in gols
            )
            return f'<div class="gols-lado {classe}">{linhas}</div>'

        return (
            '<div class="card-gols">'
            + lista(ev["gols_casa"], "gols-casa")
            + lista(ev["gols_fora"], "gols-fora")
            + "</div>"
        )

    def card_html(j):
        cor = FASE_COR.get(j["fase"], "#10b981")
        if j["pen1"] is not None:
            placar = f"{j['reg1']} <small>({j['pen1']})</small> – <small>({j['pen2']})</small> {j['reg2']}"
        elif j["gols1"] is not None:
            placar = f"{j['gols1']} – {j['gols2']}"
        else:
            placar = "— · —"
        tag_label = f"Grupo {j['grupo']}" if j["grupo"] else j["fase"]

        arb = j["arbitro"]
        extra = f" · 🧑‍⚖️ {arb['nome']}" if arb.get("nome") else ""
        prorrogacao = (
            ' · <span class="tag-aet">prorrogação</span>' if j["eventos"].get("prorrogacao") else ""
        )
        utc_attr = f'data-utc="{j["utc"]}"' if j["utc"] else ""
        hora_default = f"{j['dia']} · {j['data']} · {j['hora']}"

        return f"""
        <div class="card" data-fase="{j["fase"]}" data-times="{j["time1"].lower()} {j["time2"].lower()}" style="border:1px solid #1a2a20;border-radius:12px;background:#0d1a12;padding:12px 16px;margin-bottom:10px;position:relative;">
          <div class="fase-tag" style="background:{cor};color:#052e16;">{tag_label}</div>
          <div class="card-times">
            <div class="card-time">
              <span class="card-flag">{j["flag1"]}</span>
              <span class="card-name">{j["time1"]}</span>
            </div>
            <div class="card-vs"><span class="placar">{placar}</span></div>
            <div class="card-time card-time-away">
              <span class="card-flag">{j["flag2"]}</span>
              <span class="card-name">{j["time2"]}</span>
            </div>
          </div>
          {gols_html(j)}
          <div class="card-meta">
            <span class="card-fase-badge" style="background:{cor}22;color:{cor};border:1px solid {cor}44;border-radius:6px;padding:2px 8px;font-size:0.72rem;font-family:'Space Mono',monospace;">{tag_label}</span>
            <span style="color:#4a7a5a;font-size:0.75rem;font-family:'Space Mono',monospace;">📅 <span class="hora-display" {utc_attr}>{hora_default}</span> · 📍 {j["local"]}{extra}{prorrogacao}</span>
          </div>
        </div>"""

    cronologico = sorted(jogos_enriquecidos, key=lambda j: (j["dt"], j["id"]))
    mata = [j for j in cronologico if j["fase"] != "Grupos"]
    grupos = [j for j in cronologico if j["fase"] == "Grupos"]

    # ── hero da campeã ────────────────────────────────────────────────────────
    final = next(j for j in jogos_enriquecidos if j["fase"] == "Final")
    camp = stats["times"][CAMPEA]
    hero = f"""
    <div class="hero">
      <div class="hero-tag">Campeã do mundo</div>
      <div class="hero-time">{NOME_PARA_FLAG.get(CAMPEA, "🏳")} {CAMPEA}</div>
      <div class="hero-final">{final["gols1"]} – {final["gols2"]} na {VICE} · Final, {final["data"]} · {final["local"]}</div>
      <div class="hero-campanha">
        <span><b>{camp["j"]}</b> jogos</span>
        <span><b>{camp["v"]}</b> vitórias</span>
        <span><b>{camp["e"]}</b> empate</span>
        <span><b>{camp["gp"]}</b> gols pró</span>
        <span><b>{camp["gc"]}</b> gol sofrido</span>
      </div>
      <div class="hero-podio">🥈 {VICE} · 🥉 {TERCEIRO}</div>
    </div>"""

    # ── a Copa em números ─────────────────────────────────────────────────────
    numeros = [
        (stats["jogos"], "jogos"),
        (stats["gols"], "gols"),
        (_fmt_media(stats["media"]), "gols por jogo"),
        (stats["selecoes"], "seleções"),
        (stats["por_tempo"]["1º tempo"], "gols no 1º tempo"),
        (stats["por_tempo"]["2º tempo"], "gols no 2º tempo"),
        (stats["gols_penalti"], "gols de pênalti"),
        (stats["gols_contra"], "gols contra"),
        (stats["zero_a_zero"], "jogos sem gols"),
        (stats["penaltis_disputa"], "decisões nos pênaltis"),
        (16, "cidades-sede"),
        (3, "países"),
    ]
    grade_numeros = "".join(
        f'<div class="num"><b>{v}</b><span>{rot}</span></div>' for v, rot in numeros
    )

    # ── recordes ──────────────────────────────────────────────────────────────
    def placar_curto(j):
        g1, g2 = (j["reg1"], j["reg2"]) if j["reg1"] is not None else (j["gols1"], j["gols2"])
        return f"{j['flag1']} {j['time1']} {g1}–{g2} {j['time2']} {j['flag2']}"

    rapido, tardio = stats["gol_mais_rapido"], stats["gol_mais_tardio"]
    jogo_rapido = next(j for j in jogos_enriquecidos if str(j["id"]) == rapido["jogo"])
    jogo_tardio = next(j for j in jogos_enriquecidos if str(j["id"]) == tardio["jogo"])
    ataque_nome, ataque = stats["melhor_ataque"]
    defesa_nome, defesa = stats["melhor_defesa"]
    artilheiro = artilheiros[0] if artilheiros else None

    recordes = [
        ("Maior goleada", placar_curto(stats["maior_goleada"])),
        (
            "Jogo com mais gols",
            f"{placar_curto(stats['mais_gols'])} · {stats['mais_gols']['fase']}",
        ),
        (
            "Gol mais rápido",
            f"{rapido['jogador']} aos {rapido['minuto']}' — {placar_curto(jogo_rapido)}",
        ),
        (
            "Gol mais tardio",
            f"{tardio['jogador']} aos {tardio['minuto']}' — {placar_curto(jogo_tardio)}",
        ),
        ("Melhor ataque", f"{ataque_nome} — {ataque['gp']} gols em {ataque['j']} jogos"),
        (
            "Melhor defesa",
            f"{defesa_nome} — {defesa['gc']} gol sofrido em {defesa['j']} jogos",
        ),
    ]
    if artilheiro:
        recordes.append(
            (
                "Artilheiro",
                f"{artilheiro['nome']} ({artilheiro['selecao']}) — {artilheiro['gols']} gols",
            )
        )
    lista_recordes = "".join(
        f'<div class="rec"><span class="rec-k">{k}</span><span class="rec-v">{v}</span></div>'
        for k, v in recordes
    )

    # ── artilharia ────────────────────────────────────────────────────────────
    def linha_artilheiro(i, a):
        flag = NOME_PARA_FLAG.get(a["selecao"], "🏳")
        pen = f" <em>({a['penaltis']} p)</em>" if a["penaltis"] else ""
        return (
            f'<tr><td class="pos">{i}</td><td>{a["nome"]}</td>'
            f'<td class="sel">{flag} {a["selecao"]}</td>'
            f'<td class="gols">{a["gols"]}{pen}</td></tr>'
        )

    top = "".join(linha_artilheiro(i, a) for i, a in enumerate(artilheiros[:10], 1))
    resto = "".join(linha_artilheiro(i, a) for i, a in enumerate(artilheiros[10:], 11))
    tabela_artilharia = (
        f"""
    <table class="tabela-art"><tbody>{top}</tbody></table>
    <details class="mais-art"><summary>Ver os {len(artilheiros)} goleadores</summary>
      <table class="tabela-art"><tbody>{resto}</tbody></table>
    </details>"""
        if artilheiros
        else ""
    )

    # ── filtros ───────────────────────────────────────────────────────────────
    destaque_nomes = {t[1].lower() for t in TIMES_DESTAQUE}
    todos_times = sorted(
        {
            j[campo]
            for j in jogos_enriquecidos
            for campo in ("time1", "time2")
            if j[campo] != "A definir" and j[campo].lower() not in destaque_nomes
        }
    )
    btns_destaque = "".join(
        f'<button class="btn" onclick="filtrarBtn(this,\'{t[1].lower()}\')">{t[0]} {t[1]}</button>'
        for t in TIMES_DESTAQUE
    )
    options_dropdown = "".join(f'<option value="{t.lower()}">{t}</option>' for t in todos_times)
    btns_fusos = "".join(
        f'<button class="btn{" ativo" if i == 0 else ""}" data-tz="{f[2]}" onclick="mudarFuso(this,\'{f[2]}\')">{f[0]} {f[1]}</button>'
        for i, f in enumerate(FUSOS)
    )

    cards_mata = "\n".join(card_html(j) for j in mata)
    cards_grupos = "\n".join(card_html(j) for j in grupos)

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>Copa do Mundo 2026 · Retrospectiva 🏆</title>
  <meta name="description" content="Todos os {stats["jogos"]} jogos da Copa do Mundo 2026 com placares, autores dos gols e minutos. {stats["gols"]} gols, média de {_fmt_media(stats["media"])} por jogo. Espanha campeã."/>
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

    /* ── hero da campeã ── */
    .hero {{
      max-width: 580px; margin: 24px auto 0; padding: 22px 18px;
      background: linear-gradient(160deg, #0e2a18 0%, #0d1a12 100%);
      border: 1px solid #1d4a2c; border-radius: 16px; text-align: center;
    }}
    .hero-tag {{
      font-family: 'Space Mono', monospace; font-size: 0.65rem; letter-spacing: 2px;
      text-transform: uppercase; color: #f59e0b;
    }}
    .hero-time {{ font-size: clamp(1.8rem, 7vw, 2.6rem); font-weight: 800; color: #f0fdf4; margin: 6px 0 2px; }}
    .hero-final {{ font-family: 'Space Mono', monospace; font-size: 0.78rem; color: #6b9a7b; }}
    .hero-campanha {{
      display: flex; flex-wrap: wrap; justify-content: center; gap: 6px 16px; margin-top: 14px;
      font-family: 'Space Mono', monospace; font-size: 0.72rem; color: #4a7a5a;
    }}
    .hero-campanha b {{ color: #10b981; font-size: 0.95rem; }}
    .hero-podio {{ margin-top: 12px; font-family: 'Space Mono', monospace; font-size: 0.75rem; color: #6b9a7b; }}

    /* ── números ── */
    .numeros {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(88px, 1fr)); gap: 8px; }}
    .num {{
      background: #0d1a12; border: 1px solid #1a2a20; border-radius: 10px;
      padding: 12px 6px; text-align: center;
    }}
    .num b {{ display: block; font-size: 1.35rem; color: #10b981; font-family: 'Space Mono', monospace; }}
    .num span {{ display: block; margin-top: 3px; font-size: 0.62rem; color: #4a7a5a; font-family: 'Space Mono', monospace; line-height: 1.3; }}

    /* ── recordes ── */
    .rec {{
      display: flex; justify-content: space-between; gap: 12px; padding: 9px 0;
      border-bottom: 1px solid #14231a; font-size: 0.8rem;
    }}
    .rec:last-child {{ border-bottom: none; }}
    .rec-k {{ color: #4a7a5a; font-family: 'Space Mono', monospace; font-size: 0.7rem; white-space: nowrap; }}
    .rec-v {{ color: #d8ece0; text-align: right; }}

    /* ── artilharia ── */
    .tabela-art {{ width: 100%; border-collapse: collapse; font-size: 0.8rem; }}
    .tabela-art td {{ padding: 7px 4px; border-bottom: 1px solid #14231a; }}
    .tabela-art .pos {{ color: #2d5a3d; font-family: 'Space Mono', monospace; width: 24px; }}
    .tabela-art .sel {{ color: #6b9a7b; font-size: 0.72rem; text-align: right; }}
    .tabela-art .gols {{ color: #10b981; font-family: 'Space Mono', monospace; font-weight: 700; text-align: right; width: 52px; }}
    .tabela-art .gols em {{ color: #2d5a3d; font-style: normal; font-size: 0.65rem; }}
    .mais-art summary {{ border-left-color: #10b981; }}

    .filtros {{
      display: flex; flex-direction: column; gap: 10px; padding: 14px 20px;
      background: #0a140d; border-bottom: 1px solid #1a2a20; align-items: center;
      position: sticky; top: 0; z-index: 20;
    }}
    .filtros-row {{ display: flex; flex-wrap: wrap; gap: 6px; justify-content: center; align-items: center; width: 100%; }}
    .filtros-divider {{ width: 100%; height: 1px; background: #1a2a20; }}
    .filtros-label {{
      color: #2d5a3d; font-family: 'Space Mono', monospace; font-size: 0.65rem;
      letter-spacing: 1px; text-transform: uppercase; padding-right: 4px;
    }}
    .btn {{
      background: #0d1a12; color: #6b9a7b; border: 1px solid #1a2a20; border-radius: 8px;
      padding: 6px 14px; font-family: 'Space Mono', monospace; font-size: 0.75rem;
      cursor: pointer; transition: all 0.15s;
    }}
    .btn:hover {{ background: #142a1c; color: #a8d4b4; }}
    .btn.ativo {{ background: #10b98122; color: #10b981; border-color: #10b98166; }}
    .select-time {{
      background: #0d1a12; color: #6b9a7b; border: 1px solid #1a2a20; border-radius: 8px;
      padding: 6px 28px 6px 14px; font-family: 'Space Mono', monospace; font-size: 0.75rem;
      cursor: pointer; appearance: none; -webkit-appearance: none;
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M0 0l5 6 5-6z' fill='%236b9a7b'/%3E%3C/svg%3E");
      background-repeat: no-repeat; background-position: right 10px center; transition: all 0.15s;
    }}
    .select-time:hover {{ background-color: #142a1c; color: #a8d4b4; }}
    .select-time.ativo {{ background-color: #10b98122; color: #10b981; border-color: #10b98166; }}
    .main {{ max-width: 580px; margin: 0 auto; padding: 24px 16px 0; }}
    .secao-titulo {{
      font-size: 0.72rem; font-family: 'Space Mono', monospace; color: #4a7a5a;
      letter-spacing: 2px; text-transform: uppercase; margin: 32px 0 12px;
      border-left: 3px solid #10b981; padding-left: 10px;
    }}
    .placar {{ font-family: 'Space Mono', monospace; font-size: 1.3rem; font-weight: 700; color: #10b981; white-space: nowrap; }}
    .placar small {{ font-size: 0.72rem; color: #6b9a7b; }}
    .card-times {{ display:flex; align-items:center; justify-content:space-between; gap:8px; }}
    .card-time {{ display:flex; align-items:center; gap:10px; flex:1; min-width:0; }}
    .fase-tag {{ display:none; }}
    .card-flag {{ font-size:1.6rem; flex-shrink:0; line-height:1; }}
    .card-name {{ color:#e2f0e8; font-family:'Space Mono',monospace; font-size:0.88rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; flex:1; min-width:0; }}
    .card-vs {{ color:#4a7a5a; font-family:'Space Mono',monospace; font-size:0.78rem; padding:0 10px; flex-shrink:0; }}

    /* ── gols do jogo ── */
    .card-gols {{
      display: flex; justify-content: space-between; gap: 10px;
      margin-top: 10px; padding-top: 9px; border-top: 1px solid #14231a;
    }}
    .gols-lado {{ display: flex; flex-direction: column; gap: 2px; flex: 1; min-width: 0; }}
    .gols-fora {{ text-align: right; }}
    .gol {{
      font-family: 'Space Mono', monospace; font-size: 0.7rem; color: #a8d4b4;
      overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    }}
    .gol em {{ color: #2d5a3d; font-style: normal; }}
    .tag-aet {{ color: #a78bfa; }}

    .card-meta {{ margin-top:8px; display:flex; flex-wrap:wrap; gap:8px; align-items:center; justify-content:center; }}
    details summary {{
      cursor: pointer; user-select: none; color: #6b9a7b; font-family: 'Space Mono', monospace;
      font-size: 0.72rem; letter-spacing: 2px; text-transform: uppercase;
      margin: 28px 0 12px; padding-left: 10px; border-left: 3px solid #60a5fa; list-style: none;
    }}
    details summary::after {{ content: " ▶"; }}
    details[open] summary::after {{ content: " ▼"; }}
    footer {{ text-align: center; color: #2d5a3d; font-family: 'Space Mono', monospace; font-size: 0.7rem; margin-top: 48px; padding: 0 16px; line-height: 1.8; }}
    footer a {{ color: #4a7a5a; }}
    @media (min-width: 1024px) {{
      .card-time-away {{ flex-direction:row-reverse; }}
      .card-time-away .card-name {{ text-align:right; }}
    }}
    @media (max-width: 480px), (max-height: 500px) and (orientation: landscape) {{
      .filtros {{ padding: 10px 12px; position: static; }}
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
      .gols-lado, .gols-fora {{ text-align: center; }}
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
  <p>48 seleções · EUA, Canadá e México · 11/06 a 19/07</p>
  <div class="header-links">
    <a href="bracket.html" class="header-link">🏆 Chaveamento</a>
    <a href="mundiais.html" class="header-link">🌍 Histórico de Mundiais</a>
    <a href="#jogos" class="header-link">📋 Todos os jogos</a>
  </div>
</header>

{hero}

<div class="main">
  <div class="secao-titulo">A Copa em números</div>
  <div class="numeros">{grade_numeros}</div>

  <div class="secao-titulo">Recordes</div>
  <div class="recordes">{lista_recordes}</div>

  <div class="secao-titulo">Artilharia</div>
  {tabela_artilharia}
</div>

<div class="filtros" id="jogos">
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

  <div class="secao-titulo" id="secao-mata">Mata-mata · 32 jogos</div>
  {cards_mata}

  <div class="secao-titulo" id="secao-grupos">Fase de grupos · 72 jogos</div>
  {cards_grupos}

</div>

<footer>
  <span id="footer-fuso">Horários em Brasília</span> · Torneio encerrado em 19/07/2026<br/>
  Placares e artilharia: <a href="https://www.football-data.org">football-data.org</a> ·
  Autores dos gols: <a href="https://github.com/openfootball/worldcup">openfootball/worldcup</a>
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

  // Uma seção sem nenhum card visível vira só um título órfão — esconde junto.
  function aplicarFiltros() {{
    document.querySelectorAll('.card').forEach(card => {{
      const times  = card.dataset.times || '';
      const fase   = (card.dataset.fase || '').toLowerCase();
      const okTime = filtroTime === 'todos' || times.includes(filtroTime);
      const okFase = filtroFase === 'todos' || fase === filtroFase || (filtroFase === 'final' && fase === '3º lugar');
      card.style.display = (okTime && okFase) ? '' : 'none';
    }});
    ['secao-mata', 'secao-grupos'].forEach(id => {{
      const titulo = document.getElementById(id);
      let visiveis = 0;
      let el = titulo.nextElementSibling;
      while (el && !el.classList.contains('secao-titulo')) {{
        if (el.classList.contains('card') && el.style.display !== 'none') visiveis++;
        el = el.nextElementSibling;
      }}
      titulo.style.display = visiveis ? '' : 'none';
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

  // ── voltar ao topo ───────────────────────────────────────────────────────
  function voltarAoTopo() {{
    window.scrollTo({{top: 0, behavior: 'smooth'}});
  }}

  const _btnTopo = document.getElementById('voltar-topo');
  window.addEventListener('scroll', () => {{
    _btnTopo.classList.toggle('visivel', window.scrollY > 400);
  }}, {{passive: true}});

  // ── fuso automático: mostra os horários no fuso de quem está acessando ────
  function offsetDoFuso(tz, d) {{
    const fmt = new Intl.DateTimeFormat('en-US', {{
      timeZone: tz, hour12: false,
      year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit', second: '2-digit',
    }});
    const p = {{}};
    fmt.formatToParts(d).forEach(x => p[x.type] = x.value);
    const asUTC = Date.UTC(p.year, p.month - 1, p.day, p.hour, p.minute, p.second);
    return Math.round((asUTC - d.getTime()) / 60000);
  }}

  function autoSelecionarFuso() {{
    const agora = new Date();
    const meuOffset = -agora.getTimezoneOffset();
    let alvo = null;
    document.querySelectorAll('#filtro-fusos .btn').forEach(btn => {{
      const tz = btn.getAttribute('data-tz');
      if (tz && offsetDoFuso(tz, agora) === meuOffset) alvo = btn;
    }});
    if (alvo) {{
      mudarFuso(alvo, alvo.getAttribute('data-tz'));
    }} else {{
      atualizarHorarios(); // fallback Brasília, mas renderizado pelo JS
    }}
  }}

  autoSelecionarFuso();
</script>

</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[gerar_html] index.html gerado — {stats['jogos']} jogos, {stats['gols']} gols.")


if __name__ == "__main__":
    gerar_html()
