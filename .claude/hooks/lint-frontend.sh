#!/usr/bin/env bash
# PostToolUse (Write|Edit): corre eslint sobre .js/.jsx/.ts/.tsx editados dentro
# de frontend/src y devuelve los hallazgos como additionalContext.
# Nota: usa `python`, no `jq` (jq no esta disponible en este entorno).
input=$(cat)
file=$(printf '%s' "$input" | python -c "
import json, sys
d = json.load(sys.stdin)
print(d.get('tool_response', {}).get('filePath') or d.get('tool_input', {}).get('file_path') or '')
")

case "$file" in
  *.js|*.jsx|*.ts|*.tsx) ;;
  *) exit 0 ;;
esac
case "$file" in
  *frontend[/\\]src[/\\]*) ;;
  *) exit 0 ;;
esac

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
frontend_dir="$repo_root/frontend"
[ -d "$frontend_dir/node_modules" ] || exit 0

output=$(cd "$frontend_dir" && npx --no-install eslint "$file" 2>&1)
[ -z "$output" ] && exit 0

python -c "
import json, sys
print(json.dumps({'hookSpecificOutput': {'hookEventName': 'PostToolUse', 'additionalContext': sys.argv[1]}}))
" "eslint encontro problemas en $(basename "$file"):
$output"
