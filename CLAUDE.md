# Copa2026

## What
Site estático com todos os 90 jogos da Copa do Mundo FIFA 2026 — placares, filtros por time e fase, design dark. Publicado em https://meirelesti-lab.github.io/copa2026

## Tech
- Python 3 (`atualizar.py`, `gerar_html.py`, `dados_jogos.py`)
- API: football-data.org (plano gratuito, código `WC`)
- Hospedagem: GitHub Pages (repo `meirelesti-lab/copa2026`)
- CI/CD: GitHub Actions — roda a cada hora, atualiza `index.html` e faz push automático
- Chave da API: secret `FOOTBALL_API_KEY` no GitHub + `.env` local

## Status
Ativo — funcionando em produção.

## Current State
Projeto completo e em produção (01/06/2026):
- 90 jogos cadastrados em `dados_jogos.py` (grupos + mata-mata)
- GitHub Actions configurado para rodar a cada hora automaticamente (sem depender do Mac)
- Site público sem login em https://meirelesti-lab.github.io/copa2026
- Filtros de time: botões rápidos (Brasil, Argentina, México, Bélgica) + dropdown com todos os países
- Filtros de fase: Todos, Grupos, 32 avos, Oitavas, Quartas, Semifinal, Final
- Toggle de fuso horário: 🇧🇷 Rio de Janeiro · 🇲🇽 Monterrey · 🇧🇪 Bélgica · 🇺🇸 Miami
- Fix: próximo jogo não duplica mais nas seções
- PWA configurado: `manifest.json` + `apple-touch-icon` — ícone oficial da Copa 2026 aparece na tela inicial (iOS e Android), nome curto "Copa2026"
