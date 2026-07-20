#!/usr/bin/env bash
# PreToolUse (Bash, filtrado a "git commit*"): escanea el diff staged buscando
# patrones de secretos hardcodeados (api_key, password, token, etc). Excluye
# .env.example porque su proposito es documentar variables con valores demo.
# Nota: usa `python`, no `jq` (jq no esta disponible en este entorno).
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root" || exit 0

pattern='(api[_-]?key|secret|password|passwd|token|access[_-]?key|private[_-]?key)[[:space:]]*[:=][[:space:]]*["'"'"'][^"'"'"'[:space:]]{6,}'
hits=$(git diff --cached -U0 -- . ':(exclude)*.env.example' ':(exclude)**/.env.example' \
  | grep -E '^\+' | grep -vE '^\+\+\+' | grep -Ein "$pattern" || true)

[ -z "$hits" ] && exit 0

python -c "
import json, sys
print(json.dumps({'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'permissionDecision': 'deny', 'permissionDecisionReason': 'Posible secreto hardcodeado en el diff staged. Revisa antes de commitear:\n' + sys.argv[1]}}))
" "$hits"
