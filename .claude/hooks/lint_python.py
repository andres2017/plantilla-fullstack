"""PostToolUse hook (matcher: Edit|Write). Tras editar un .py, corre ruff
sobre ese archivo usando el venv de backend/ si existe, e inyecta los
hallazgos como contexto adicional (no bloquea: el linteo es informativo)."""
import json
import os
import subprocess
import sys


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return

    file_path = data.get("tool_input", {}).get("file_path") or data.get("tool_response", {}).get("filePath", "")
    if not file_path or not file_path.endswith(".py"):
        return

    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    venv_python = os.path.join(root, "backend", "venv", "Scripts", "python.exe")
    if not os.path.exists(venv_python):
        venv_python = os.path.join(root, "backend", "venv", "bin", "python")
    if not os.path.exists(venv_python):
        return  # sin venv instalado todavia -> no-op silencioso

    try:
        result = subprocess.run(
            [venv_python, "-m", "ruff", "check", file_path],
            capture_output=True, text=True, timeout=20,
        )
    except Exception:
        return

    output = (result.stdout + result.stderr).strip()
    if output:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": f"ruff encontro problemas de lint en {file_path}:\n{output}",
            }
        }))


if __name__ == "__main__":
    main()
