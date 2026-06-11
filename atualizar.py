#!/usr/bin/env python3
"""
atualizar.py — Copa 2026
Busca resultados em football-data.org, atualiza resultados.json,
gera index.html e faz push para GitHub Pages.
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

import requests
from dotenv import load_dotenv

from dados_jogos import JOGOS, MAPA_NOMES
from gerar_html import gerar_html

load_dotenv()

API_KEY = os.getenv("FOOTBALL_API_KEY", "")
API_URL = "https://api.football-data.org/v4/competitions/WC/matches"
RESULTADOS_FILE = "resultados.json"

BRASILIA = timezone(timedelta(hours=-3))


def _hora_int(hora_str):
    if hora_str in ("?", ""):
        return -1
    s = hora_str.rstrip("h")
    if "h" in s:
        h, _ = s.split("h")
        return int(h)
    return int(s)


# Índice de jogos mata-mata para busca por data
_MATA_HORA: dict = {}  # (mes, dia, hora) → jogo
_MATA_DIA: dict = {}  # (mes, dia) → jogo  (apenas datas com 1 jogo)
_dias_count: dict = {}
for _j in JOGOS:
    if _j["fase"] == "Grupos":
        continue
    _d, _m = _j["data"].split("/")
    _d, _m = int(_d), int(_m)
    _h = _hora_int(_j["hora"])
    if _h >= 0:
        _MATA_HORA[(_m, _d, _h)] = _j
    _dia_key = (_m, _d)
    _dias_count[_dia_key] = _dias_count.get(_dia_key, 0) + 1
    _MATA_DIA[_dia_key] = _j  # sobrescreve; se > 1 jogo no dia, usamos o hora-based


def encontrar_jogo_por_data(utc_date_str):
    """Encontra jogo mata-mata pela data/hora UTC retornada pela API."""
    try:
        dt_utc = datetime.fromisoformat(utc_date_str.replace("Z", "+00:00"))
        dt_bra = dt_utc.astimezone(BRASILIA)
        jogo = _MATA_HORA.get((dt_bra.month, dt_bra.day, dt_bra.hour))
        if jogo is None and _dias_count.get((dt_bra.month, dt_bra.day), 0) == 1:
            jogo = _MATA_DIA.get((dt_bra.month, dt_bra.day))
        return jogo
    except Exception:
        return None


def normalizar(nome):
    """Normaliza nome para comparação fuzzy: minúsculas, sem acentos comuns."""
    return (
        nome.lower()
        .replace("á", "a")
        .replace("à", "a")
        .replace("ã", "a")
        .replace("â", "a")
        .replace("é", "e")
        .replace("ê", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ô", "o")
        .replace("õ", "o")
        .replace("ú", "u")
        .replace("ü", "u")
        .replace("ç", "c")
        .replace("ñ", "n")
        .replace("'", "")
        .replace("-", " ")
        .strip()
    )


def traduzir(nome_api):
    """Converte nome da API para português."""
    return MAPA_NOMES.get(nome_api, nome_api)


def encontrar_jogo(time1_pt, time2_pt):
    """Encontra o jogo nos dados fixos pelo nome dos dois times (fuzzy)."""
    n1 = normalizar(time1_pt)
    n2 = normalizar(time2_pt)
    for jogo in JOGOS:
        j1 = normalizar(jogo["time1"])
        j2 = normalizar(jogo["time2"])
        if (n1 in j1 or j1 in n1) and (n2 in j2 or j2 in n2):
            return jogo
        if (n2 in j1 or j1 in n2) and (n1 in j2 or j2 in n1):
            return jogo
    return None


def buscar_resultados():
    if not API_KEY:
        print("[ERRO] FOOTBALL_API_KEY não definida. Crie um .env com a chave.")
        sys.exit(1)

    headers = {"X-Auth-Token": API_KEY}
    print(f"[api] Buscando partidas em {API_URL} ...")
    resp = requests.get(API_URL, headers=headers, timeout=15)

    if resp.status_code == 403:
        print("[ERRO] Chave inválida ou sem permissão para este endpoint.")
        sys.exit(1)
    if resp.status_code == 429:
        print("[AVISO] Limite de requisições atingido. Tente novamente em 1 minuto.")
        sys.exit(1)
    if resp.status_code != 200:
        print(f"[ERRO] HTTP {resp.status_code}: {resp.text[:200]}")
        sys.exit(1)

    return resp.json()


def processar(dados_api, resultados_existentes):
    partidas = dados_api.get("matches", [])
    print(f"[api] {len(partidas)} partidas retornadas pela API.")

    atualizados = 0
    nao_encontrados = []

    for partida in partidas:
        status = partida.get("status", "")
        encerrado = status in ("FINISHED", "AWARDED")

        home_raw = partida["homeTeam"].get("name", "")
        away_raw = partida["awayTeam"].get("name", "")
        home = traduzir(home_raw) if home_raw else ""
        away = traduzir(away_raw) if away_raw else ""

        # Pula jogos futuros sem times definidos
        if not encerrado and (not home or not away):
            continue

        score = partida.get("score", {})
        ft = score.get("fullTime", {})
        gols_home = ft.get("home") if encerrado else None
        gols_away = ft.get("away") if encerrado else None

        # Tenta casar pelo nome dos times; fallback por data (mata-mata)
        jogo = encontrar_jogo(home, away) if home and away else None
        if jogo is None:
            utc_date = partida.get("utcDate", "")
            if utc_date:
                jogo = encontrar_jogo_por_data(utc_date)

        if jogo is None:
            if encerrado:
                nao_encontrados.append(f"{home} × {away}")
            continue

        rid = str(jogo["id"])
        res_atual = resultados_existentes.get(rid, {})

        if encerrado:
            resultado_novo = {
                **res_atual,
                "gols1": gols_home,
                "gols2": gols_away,
                "encerrado": True,
                "home_api": home,
                "away_api": away,
            }
        else:
            # Jogo futuro: salva times do bracket se for mata-mata
            if jogo["fase"] == "Grupos":
                continue
            resultado_novo = {
                **res_atual,
                "time1_real": home,
                "time2_real": away,
            }

        if resultados_existentes.get(rid) != resultado_novo:
            resultados_existentes[rid] = resultado_novo
            atualizados += 1
            if encerrado:
                print(f"  ✓ ID{rid}: {home} {gols_home}–{gols_away} {away}")
            else:
                print(f"  ✓ Bracket ID{rid}: {home} × {away}")

    return atualizados, nao_encontrados


def git_push():
    agora = datetime.now(BRASILIA).strftime("%d/%m/%Y %H:%M")
    cmds = [
        ["git", "add", "index.html", "resultados.json"],
        ["git", "commit", "--no-verify", "-m", f"Resultados atualizados - {agora}"],
        ["git", "push", "origin", "main"],
    ]
    for cmd in cmds:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            # "nothing to commit" não é erro real
            if "nothing to commit" in result.stdout or "nothing to commit" in result.stderr:
                print("[git] Nada novo para commitar.")
                return
            print(f"[git] Erro ao executar {' '.join(cmd)}:")
            print(result.stderr or result.stdout)
            return
        print(f"[git] {' '.join(cmd[:2])} — ok")


def main():
    no_git = "--no-git" in sys.argv

    # Carregar resultados existentes
    resultados = {}
    if os.path.exists(RESULTADOS_FILE):
        with open(RESULTADOS_FILE, "r", encoding="utf-8") as f:
            resultados = json.load(f)

    # Buscar dados da API
    dados_api = buscar_resultados()

    # Processar partidas encerradas
    atualizados, nao_encontrados = processar(dados_api, resultados)

    # Salvar resultados
    with open(RESULTADOS_FILE, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)

    total_encerrados = sum(1 for v in resultados.values() if v.get("encerrado"))
    print(f"\n[resumo] {atualizados} jogo(s) atualizados nesta execução.")
    print(f"[resumo] {total_encerrados} jogo(s) encerrados no total.")

    if nao_encontrados:
        print(f"[aviso] {len(nao_encontrados)} partida(s) não encontradas nos dados fixos:")
        for item in nao_encontrados:
            print(f"  - {item}")

    # Gerar HTML
    print("\n[html] Gerando index.html ...")
    gerar_html(resultados_path=RESULTADOS_FILE, output_path="index.html")

    # Git push (pulado quando rodando via GitHub Actions)
    if no_git:
        print("\n[git] Modo --no-git: push delegado ao GitHub Actions.")
    else:
        print("\n[git] Fazendo push para GitHub Pages ...")
        git_push()

    print("\n✅ Concluído! Site atualizado em https://meirelesti-lab.github.io/copa2026")


if __name__ == "__main__":
    main()
