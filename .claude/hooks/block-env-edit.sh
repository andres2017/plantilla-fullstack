#!/usr/bin/env bash
# PreToolUse (Write|Edit): bloquea escritura/edicion de archivos .env reales.
# Solo .env.example queda permitido (es el que se documenta y versiona).
# Nota: usa `python`, no `jq` (jq no esta disponible en este entorno).
input=$(cat)
file=$(printf '%s' "$input" | python -c "
import json, sys
d = json.load(sys.stdin)
print(d.get('tool_input', {}).get('file_path') or '')
")
base=$(basename -- "$file")

case "$base" in
  .env.example) exit 0 ;;
  .env|.env.*)
    python -c "
import json, sys
print(json.dumps({'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'permissionDecision': 'deny', 'permissionDecisionReason': 'Edicion bloqueada: ' + sys.argv[1] + ' es un archivo de secretos reales (gitignored). Solo .env.example puede editarse.'}}))
" "$file"
    ;;
  *) exit 0 ;;
esac
