"""Congela em disco todos os dados da Copa 2026.

O torneio acabou: nada muda mais. Este script roda UMA vez, baixa tudo de que o
site precisa e grava em `dados/`. A partir daí a geração do site é offline —
`gerar_html.py` e `gerar_bracket.py` leem só arquivos versionados.

Fontes:
  - football-data.org v4 (chave em .env): artilheiros, árbitros, escudos.
    O plano gratuito NÃO devolve eventos de gol; por isso a segunda fonte.
  - openfootball/worldcup (CC0, sem chave): autor e minuto dos 308 gols.

Uso: python3 snapshot.py
"""

import json
import os
import re
import sys
import urllib.request
from pathlib import Path

from dados_jogos import JOGOS, MAPA_NOMES

DIR_DADOS = Path(__file__).parent / "dados"
API = "https://api.football-data.org/v4"
OPENFOOTBALL = "https://raw.githubusercontent.com/openfootball/worldcup/master/2026--usa"

# openfootball usa nomes que o MAPA_NOMES (alimentado pela football-data) não cobre.
ALIAS_OPENFOOTBALL = {
    "Czech Republic": "República Tcheca",
    "Turkey": "Turquia",
    "USA": "Estados Unidos",
    "Korea Republic": "Coreia do Sul",
    "IR Iran": "Irã",
}


def _pt(nome):
    nome = nome.strip()
    return ALIAS_OPENFOOTBALL.get(nome) or MAPA_NOMES.get(nome) or nome


# ─────────────────────────────── football-data ────────────────────────────────


def _chave():
    chave = os.environ.get("FOOTBALL_API_KEY")
    if chave:
        return chave
    env = Path(__file__).parent / ".env"
    if env.exists():
        for linha in env.read_text().splitlines():
            if linha.startswith("FOOTBALL_API_KEY"):
                return linha.split("=", 1)[1].strip().strip("\"'")
    sys.exit("FOOTBALL_API_KEY não encontrada (env ou .env)")


def _get(url, chave):
    req = urllib.request.Request(url, headers={"X-Auth-Token": chave})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def _indice_pares():
    """(casa, fora) → id do jogo. Único para os 104 jogos do torneio.

    A football-data usa IDs próprios (537390 = a final), então o par de times é
    a única chave estável entre as duas fontes — o horário não serve: 12 slots
    da 3ª rodada de grupos são simultâneos.
    """
    resultados = json.loads((Path(__file__).parent / "resultados.json").read_text("utf-8"))
    idx = {}
    for j in JOGOS:
        r = resultados.get(str(j["id"]), {})
        casa = r.get("time1_real") or j["time1"]
        fora = r.get("time2_real") or j["time2"]
        idx[(casa, fora)] = j["id"]
    return idx


def baixar_api():
    """4 requests — cabe folgado no limite de 10/min do plano gratuito."""
    chave = _chave()
    pares = _indice_pares()
    partidas = _get(f"{API}/competitions/WC/matches", chave)["matches"]
    # O default de `scorers` é 10; sem o limit explícito a artilharia vem truncada.
    artilheiros = _get(f"{API}/competitions/WC/scorers?limit=500", chave)["scorers"]
    times = _get(f"{API}/competitions/WC/teams", chave)["teams"]

    arbitros = {}
    escudos = {}
    for p in partidas:
        for lado in ("homeTeam", "awayTeam"):
            t = p[lado]
            if t.get("crest"):
                escudos[_pt(t["name"])] = t["crest"]
        principal = next((r for r in p.get("referees", []) if r.get("type") == "REFEREE"), None)
        jid = pares.get((_pt(p["homeTeam"]["name"]), _pt(p["awayTeam"]["name"])))
        if principal and jid:
            arbitros[str(jid)] = {
                "nome": principal["name"],
                "pais": principal.get("nationality", ""),
            }

    return {
        "partidas": partidas,
        "artilheiros": [
            {
                "nome": a["player"]["name"],
                "pais": a["player"].get("nationality", ""),
                "selecao": _pt(a["team"]["name"]),
                "gols": a["goals"],
                "jogos": a.get("playedMatches"),
                "penaltis": a.get("penalties") or 0,
                "assistencias": a.get("assists"),
            }
            for a in artilheiros
        ],
        "arbitros": arbitros,
        "escudos": escudos,
        "tecnicos": {
            _pt(t["name"]): (t.get("coach") or {}).get("name") for t in times if t.get("coach")
        },
    }


# ─────────────────────────── openfootball (eventos) ───────────────────────────

LINHA_JOGO = re.compile(
    r"^\s*(?:\((?P<num>\d+)\)\s*)?"
    r"(?P<hora>\d{1,2}:\d{2})\s+UTC[+-]\d+\s+"
    r"(?P<resto>.+)$"
)

PLACAR = re.compile(
    r"^(?P<casa>.+?)\s+(?P<g1>\d+)-(?P<g2>\d+)\s*(?P<aet>a\.e\.t\.)?\s*"
    r"\((?P<parciais>[^)]*)\)\s*"
    r"(?:,\s*(?P<p1>\d+)-(?P<p2>\d+)\s*pen\.)?\s*"
    r"(?P<fora>.+?)\s*$"
)

# "Kylian Mbappé 45', 74'" → 2 gols do mesmo jogador; o 2º casa com nome vazio.
GOL = re.compile(r"(?P<nome>[^,;]*?)\s*(?P<min>\d{1,3}(?:\+\d{1,2})?)'\s*(?P<marca>\((?:p|og)\))?")

TIPO = {"(p)": "penalti", "(og)": "contra"}


def _parse_gols(texto):
    """'(Casemiro 56' Martinelli 90+5'; Kaishu Sano 29')' → (gols_casa, gols_fora)."""
    texto = texto.strip()
    if texto.startswith("(") and texto.endswith(")"):
        texto = texto[1:-1]
    partes = texto.split(";")

    def lado(trecho):
        gols, ultimo = [], None
        for m in GOL.finditer(trecho):
            nome = m.group("nome").strip()
            if nome:
                ultimo = nome
            if not ultimo:
                continue
            gols.append(
                {
                    "jogador": ultimo,
                    "minuto": m.group("min"),
                    "tipo": TIPO.get(m.group("marca") or "", "normal"),
                }
            )
        return gols

    if len(partes) == 1:
        return lado(partes[0]), []
    return lado(partes[0]), lado(partes[1])


def _blocos(linhas):
    """Varre o arquivo e devolve (dados_da_partida, texto_dos_gols)."""
    i = 0
    while i < len(linhas):
        linha = linhas[i]
        i += 1
        if linha.lstrip().startswith("#"):
            continue
        m = LINHA_JOGO.match(linha)
        if not m:
            continue
        esquerda = m.group("resto").split("@")[0]
        p = PLACAR.match(esquerda.strip())
        if not p:
            continue

        # O bloco de gols vem nas linhas seguintes, entre parênteses, podendo
        # quebrar em várias linhas — acumula até os parênteses fecharem.
        texto, profundidade = "", 0
        while i < len(linhas):
            seguinte = linhas[i].strip()
            if not texto and not seguinte.startswith("("):
                break
            texto += " " + seguinte
            profundidade += seguinte.count("(") - seguinte.count(")")
            i += 1
            if profundidade <= 0:
                break

        yield m.group("num"), p, texto


def _indice_grupos():
    """(casa, fora) em português → id do jogo, só para a fase de grupos."""
    idx = {}
    for j in JOGOS:
        if j["fase"] == "Grupos":
            idx[(j["time1"], j["time2"])] = j["id"]
    return idx


def baixar_eventos():
    idx = _indice_grupos()
    eventos, sem_casar = {}, []

    for arquivo in ("cup.txt", "cup_finals.txt"):
        with urllib.request.urlopen(f"{OPENFOOTBALL}/{arquivo}", timeout=30) as r:
            linhas = r.read().decode("utf-8").splitlines()

        for num, p, texto_gols in _blocos(linhas):
            casa, fora = _pt(p.group("casa")), _pt(p.group("fora"))
            if num:
                jid = int(num)
            else:
                jid = idx.get((casa, fora)) or idx.get((fora, casa))
            if not jid:
                sem_casar.append(f"{casa} x {fora}")
                continue

            g_casa, g_fora = _parse_gols(texto_gols) if texto_gols else ([], [])
            # Sem ';' o bloco tem um lado só: é de quem marcou.
            if g_casa and not g_fora and int(p.group("g1")) == 0:
                g_casa, g_fora = [], g_casa

            eventos[str(jid)] = {
                "casa": casa,
                "fora": fora,
                "gols_casa": g_casa,
                "gols_fora": g_fora,
                "prorrogacao": bool(p.group("aet")),
            }

    return eventos, sem_casar


# ─────────────────────────────────── main ─────────────────────────────────────


def main():
    DIR_DADOS.mkdir(exist_ok=True)

    print("openfootball: baixando eventos de gol…")
    eventos, sem_casar = baixar_eventos()
    total = sum(len(e["gols_casa"]) + len(e["gols_fora"]) for e in eventos.values())
    print(f"  {len(eventos)} jogos, {total} gols")
    if sem_casar:
        print(f"  ⚠ não casaram: {sem_casar}")

    print("football-data: baixando artilharia, árbitros e escudos…")
    api = baixar_api()
    print(f"  {len(api['artilheiros'])} artilheiros, {len(api['arbitros'])} árbitros")

    (DIR_DADOS / "eventos.json").write_text(
        json.dumps(eventos, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    for nome in ("artilheiros", "arbitros", "escudos", "tecnicos"):
        (DIR_DADOS / f"{nome}.json").write_text(
            json.dumps(api[nome], ensure_ascii=False, indent=1), encoding="utf-8"
        )
    (DIR_DADOS / "api_partidas.json").write_text(
        json.dumps(api["partidas"], ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(f"✓ gravado em {DIR_DADOS}")


if __name__ == "__main__":
    main()
