"""Números da Copa 2026, computados dos dados congelados em `dados/`.

Tudo aqui é derivado — nenhuma estatística é digitada à mão. Se um placar mudar
em `resultados.json`, os números se recalculam sozinhos na próxima geração.
"""

import json
from pathlib import Path

DIR_DADOS = Path(__file__).parent / "dados"


def carregar(nome):
    caminho = DIR_DADOS / f"{nome}.json"
    if not caminho.exists():
        return {}
    return json.loads(caminho.read_text(encoding="utf-8"))


def minuto(m):
    """'90+5' → (90, 5). Serve para ordenar e para separar por tempo de jogo."""
    if "+" in m:
        base, extra = m.split("+")
        return int(base), int(extra)
    return int(m), 0


def tempo_do_gol(m):
    base, _ = minuto(m)
    if base <= 45:
        return "1º tempo"
    if base <= 90:
        return "2º tempo"
    return "prorrogação"


def _placar_regular(jogo):
    """Placar sem os pênaltis da disputa (o fullTime da API já os soma)."""
    if jogo.get("reg1") is not None:
        return jogo["reg1"], jogo["reg2"]
    return jogo["gols1"], jogo["gols2"]


def calcular(jogos, eventos):
    """`jogos` são os jogos já enriquecidos com placar e times reais."""
    encerrados = [j for j in jogos if j["encerrado"]]

    gols_por_jogo = []
    zero_a_zero = 0
    penaltis_disputa = 0
    times = {}

    for j in encerrados:
        g1, g2 = _placar_regular(j)
        gols_por_jogo.append((g1 + g2, j))
        if g1 == 0 and g2 == 0:
            zero_a_zero += 1
        if j.get("pen1") is not None:
            penaltis_disputa += 1

        for time, pro, contra in ((j["time1"], g1, g2), (j["time2"], g2, g1)):
            t = times.setdefault(time, {"j": 0, "v": 0, "e": 0, "d": 0, "gp": 0, "gc": 0})
            t["j"] += 1
            t["gp"] += pro
            t["gc"] += contra
            if pro > contra:
                t["v"] += 1
            elif pro == contra:
                t["e"] += 1
            else:
                t["d"] += 1

    total_gols = sum(g for g, _ in gols_por_jogo)
    n = len(encerrados)

    # ── eventos de gol ────────────────────────────────────────────────────────
    todos_gols = []
    for jid, ev in eventos.items():
        for lado in ("gols_casa", "gols_fora"):
            for g in ev[lado]:
                todos_gols.append({**g, "jogo": jid})

    por_tempo = {"1º tempo": 0, "2º tempo": 0, "prorrogação": 0}
    for g in todos_gols:
        por_tempo[tempo_do_gol(g["minuto"])] += 1

    ordenados = sorted(todos_gols, key=lambda g: minuto(g["minuto"]))
    penalti = sum(1 for g in todos_gols if g["tipo"] == "penalti")
    contra = sum(1 for g in todos_gols if g["tipo"] == "contra")

    # ── extremos ──────────────────────────────────────────────────────────────
    def saldo(par):
        _, j = par
        g1, g2 = _placar_regular(j)
        return abs(g1 - g2)

    maior_goleada = max(gols_por_jogo, key=saldo)[1] if gols_por_jogo else None
    mais_gols = max(gols_por_jogo, key=lambda p: p[0])[1] if gols_por_jogo else None

    com_jogos = {k: v for k, v in times.items() if v["j"] >= 3}
    melhor_ataque = max(com_jogos.items(), key=lambda kv: kv[1]["gp"]) if com_jogos else None
    melhor_defesa = (
        min(com_jogos.items(), key=lambda kv: kv[1]["gc"] / kv[1]["j"]) if com_jogos else None
    )

    return {
        "jogos": n,
        "gols": total_gols,
        "media": total_gols / n if n else 0,
        "selecoes": len(times),
        "zero_a_zero": zero_a_zero,
        "penaltis_disputa": penaltis_disputa,
        "gols_penalti": penalti,
        "gols_contra": contra,
        "por_tempo": por_tempo,
        "gol_mais_rapido": ordenados[0] if ordenados else None,
        "gol_mais_tardio": ordenados[-1] if ordenados else None,
        "maior_goleada": maior_goleada,
        "mais_gols": mais_gols,
        "melhor_ataque": melhor_ataque,
        "melhor_defesa": melhor_defesa,
        "times": times,
    }
