#!/usr/bin/env bash
# PostToolUse (Write|Edit): corre ruff sobre .py editados dentro de backend/
# y devuelve los hallazgos como additionalContext para que Claude los corrija.
# Nota: usa `python`, no `jq` (jq no esta disponible en este entorno).
input=$(cat)
file=$(printf '%s' "$input" | python -c "
import json, sys
d = json.load(sys.stdin)
print(d.get('tool_response', {}).get('filePath') or d.get('tool_input', {}).get('file_path') or '')
")

case "$file" in
  *.py) ;;
  *) exit 0 ;;
esac
case "$file" in
  *backend[/\\]*) ;;
  *) exit 0 ;;
esac

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
backend_dir="$repo_root/backend"
py="$backend_dir/venv/Scripts/python.exe"
[ -x "$py" ] || py="$backend_dir/venv/bin/python"
[ -x "$py" ] || exit 0

output=$(cd "$backend_dir" && "$py" -m ruff check "$file" 2>&1)
[ -z "$output" ] && exit 0

python -c "
import json, sys
print(json.dumps({'hookSpecificOutput': {'hookEventName': 'PostToolUse', 'additionalContext': sys.argv[1]}}))
" "ruff encontro problemas en $(basename "$file"):
$output"
