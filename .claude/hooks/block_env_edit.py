"""PreToolUse hook (matcher: Edit|Write). Bloquea ediciones a archivos .env
reales; .env.example queda permitido porque es la plantilla documentada que
SI se versiona (ver .gitignore: '!.env.example')."""
import json
import os
import re
import sys


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return

    file_path = data.get("tool_input", {}).get("file_path", "")
    if not file_path:
        return

    base = os.path.basename(file_path)
    if re.match(r"^\.env(\..+)?$", base) and base != ".env.example":
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    f"Edicion bloqueada: '{base}' es un archivo .env real (protegido por hook). "
                    "Solo .env.example es editable desde Claude Code. Edita el .env local a mano "
                    "fuera del asistente si necesitas cambiar una variable."
                ),
            }
        }))


if __name__ == "__main__":
    main()
