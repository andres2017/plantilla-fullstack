"""PreToolUse hook (matcher: Bash). Antes de un 'git commit', escanea el
diff staged de archivos fuente (.py/.js/.jsx/.ts/.tsx) buscando patrones de
secretos hardcodeados (api_key/secret/password/token = "valor literal").
No revisa .md/docs/.env.example: esos archivos documentan credenciales de
ejemplo a proposito (ver memory/test_credentials.md)."""
import json
import re
import subprocess
import sys

SECRET_RE = re.compile(
    r"""(api[_-]?key|secret|password|token)\s*[:=]\s*["'][A-Za-z0-9+/=_.\-]{8,}["']""",
    re.IGNORECASE,
)
SOURCE_EXT = (".py", ".js", ".jsx", ".ts", ".tsx")


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return

    cmd = data.get("tool_input", {}).get("command", "") or ""
    if "git commit" not in cmd:
        return

    try:
        names_out = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            capture_output=True, text=True, timeout=15,
        ).stdout
    except Exception:
        return

    files = [f for f in names_out.splitlines() if f.endswith(SOURCE_EXT)]
    if not files:
        return

    try:
        diff = subprocess.run(
            ["git", "diff", "--cached", "-U0", "--"] + files,
            capture_output=True, text=True, timeout=15,
        ).stdout
    except Exception:
        return

    hits = []
    for line in diff.splitlines():
        if line.startswith("+") and not line.startswith("+++") and SECRET_RE.search(line):
            hits.append(line.strip())

    if hits:
        reason = (
            "Commit bloqueado: posibles secretos hardcodeados "
            "(patron api_key/secret/password/token con valor literal) en:\n"
            + "\n".join(hits[:10])
        )
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }))


if __name__ == "__main__":
    main()
