# ADR-0001: Python scripts generate static HTML (no server)

**Status:** accepted
**Date:** 2026-06-06
**Deciders:** André

## Context

The Copa 2026 tracker needs to display fixtures, results, and standings for the World Cup. It must run locally and be shareable as a single file — no server, no database, no cloud hosting required.

## Decision

Python scripts (`gerar_html.py`, `dados_jogos.py`) read match data from `resultados.json` and generate a static `index.html` file. The HTML file is fully self-contained and can be opened in any browser or hosted as a static site.

## Alternatives considered

- **Flask/Django web app** — rejected; would require a running server and can't be shared as a single file
- **JavaScript-only (no Python)** — rejected; Python is better for data transformation and JSON manipulation in this context

## Consequences

- Output is a single portable HTML file — easy to share or host anywhere
- Updating results = edit `resultados.json` + re-run the Python script
- No live data; manual update required after each match
