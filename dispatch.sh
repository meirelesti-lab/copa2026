#!/usr/bin/env bash
# Dispara manualmente o workflow "Atualizar Copa 2026" via API do GitHub.
# Uso: GITHUB_PAT=ghp_xxx ./dispatch.sh
# Serve para testar o PAT antes de plugar no cron-job.org.
set -euo pipefail

REPO="meirelesti-lab/copa2026"
WORKFLOW="atualizar.yml"
PAT="${GITHUB_PAT:-}"

if [ -z "$PAT" ]; then
  echo "Erro: defina GITHUB_PAT (PAT fine-grained com Actions: read+write no repo)." >&2
  exit 1
fi

HTTP_CODE=$(curl -s -o /tmp/dispatch_resp.txt -w "%{http_code}" \
  -X POST \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer ${PAT}" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  "https://api.github.com/repos/${REPO}/actions/workflows/${WORKFLOW}/dispatches" \
  -d '{"ref":"main"}')

if [ "$HTTP_CODE" = "204" ]; then
  echo "OK (204): workflow disparado. Veja em https://github.com/${REPO}/actions"
else
  echo "Falhou (HTTP ${HTTP_CODE}):" >&2
  cat /tmp/dispatch_resp.txt >&2
  exit 1
fi
