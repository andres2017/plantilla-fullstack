# Ejecuta un build real con Claude Agent SDK sobre una copia aislada de la plantilla.
# Respetando DECISIONS.md:
# - cwd dedicado por build
# - env minimo (solo ANTHROPIC_API_KEY), nunca os.environ.copy()
# - tools: Read/Write/Edit/Glob/Grep — Bash deshabilitado
# - max_turns + max_budget_usd + timeout duro
# - denylist al copiar + escaneo de secretos pre-zip

from __future__ import annotations

import asyncio
import logging
import re
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Awaitable, Callable

from builds.config import (
    ANTHROPIC_API_KEY,
    BUILDS_MAX_TURNS,
    BUILDS_PER_BUILD_CAP_USD,
    BUILDS_TIMEOUT_SECONDS,
    BUILDS_WORK_ROOT,
    BUILDS_TEMPLATE_ROOT,
)

logger = logging.getLogger("builds.agent_runner")

ProgressCb = Callable[[str], Awaitable[None]]
IsCancelledCb = Callable[[], Awaitable[bool]]

# Carpetas/archivos que NUNCA se copian al working dir del agente
_COPY_DENYLIST = {
    ".git", ".env", ".env.local", ".env.production",
    "node_modules", "venv", ".venv", "__pycache__",
    ".next", "dist", "build", ".turbo", ".cache",
    "coverage", ".pytest_cache", ".ruff_cache",
    "test_reports", "memory",
}

_SECRET_PATTERNS = [
    re.compile(r"sk-ant-[A-Za-z0-9\-_]{20,}"),
    re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[=:]\s*['\"][^'\"]{12,}['\"]"),
    re.compile(r"mongodb(\+srv)?://[^\s/:]+:[^\s/@]+@"),
    re.compile(r"(?i)JWT_SECRET\s*[=:]\s*['\"]?[^'\"\s]{16,}"),
]

_SYSTEM_PROMPT = """Eres un ingeniero senior trabajando sobre la plantilla full-stack plantilla-fullstack
(FastAPI + Mongo + React + Tailwind + Shadcn).

Reglas obligatorias:
1. Respeta las capas existentes: routers → services → repositories → models.
2. Frontend: features/ con los 4 estados (loading/empty/error/success).
3. No inventes dependencias nuevas si se puede resolver con lo que ya hay.
4. No toques archivos .env ni secretos.
5. No ejecutes comandos de shell (no tienes Bash).
6. Responde y trabaja en español cuando el usuario escriba en español.
7. Al terminar, deja el codigo listo para correr (imports, rutas registradas si aplica).

Trabaja solo dentro del directorio de trabajo actual."""


def _repo_root() -> Path:
    if BUILDS_TEMPLATE_ROOT:
        return Path(BUILDS_TEMPLATE_ROOT).resolve()
    # backend/builds/services/agent_runner.py → repo root = parents[3]
    return Path(__file__).resolve().parents[3]


def _should_skip(name: str) -> bool:
    return name in _COPY_DENYLIST or name.endswith(".pyc")


def copy_template(work_dir: Path) -> None:
    """Copia la plantilla al working dir respetando denylist."""
    src = _repo_root()
    if not src.is_dir():
        raise RuntimeError(f"Template root no existe: {src}")

    if work_dir.exists():
        shutil.rmtree(work_dir, ignore_errors=True)
    work_dir.mkdir(parents=True, exist_ok=True)

    for item in src.iterdir():
        if _should_skip(item.name):
            continue
        dest = work_dir / item.name
        if item.is_dir():
            shutil.copytree(
                item, dest,
                ignore=shutil.ignore_patterns(*_COPY_DENYLIST, "*.pyc", "__pycache__"),
                dirs_exist_ok=True,
            )
        else:
            shutil.copy2(item, dest)


def scan_secrets(work_dir: Path) -> list[str]:
    """Escaneo basico pre-zip. Retorna hallazgos legibles."""
    findings: list[str] = []
    for path in work_dir.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".zip", ".jar", ".woff", ".woff2"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for pat in _SECRET_PATTERNS:
            if pat.search(text):
                findings.append(str(path.relative_to(work_dir)))
                break
    return findings


def make_zip(work_dir: Path, zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in work_dir.rglob("*"):
            if path.is_file() and path != zip_path:
                zf.write(path, arcname=str(path.relative_to(work_dir)))


def _message_to_progress(msg) -> str | None:
    """Extrae texto legible de un mensaje del SDK para el log SSE."""
    try:
        # ResultMessage
        if hasattr(msg, "result") and msg.result:
            text = str(msg.result)
            return text[:300] + ("…" if len(text) > 300 else "")

        # AssistantMessage con content blocks
        content = getattr(msg, "content", None)
        if content:
            parts = []
            for block in content:
                btype = getattr(block, "type", None) or getattr(block, "kind", None)
                if btype == "text" or hasattr(block, "text"):
                    t = getattr(block, "text", "") or ""
                    if t.strip():
                        parts.append(t.strip()[:200])
                elif btype == "tool_use" or hasattr(block, "name"):
                    name = getattr(block, "name", "tool")
                    parts.append(f"Tool: {name}")
            if parts:
                return " | ".join(parts)

        # Fallback: subtype de system messages
        subtype = getattr(msg, "subtype", None)
        if subtype:
            return f"[{subtype}]"
    except Exception:
        return None
    return None


async def run_agent_build(
    build_id: str,
    prompt: str,
    on_progress: ProgressCb,
    is_cancelled: IsCancelledCb,
) -> dict:
    """
    Corre el Agent SDK y retorna:
      { actual_cost_usd, zip_path, work_dir }
    Lanza Exception si falla o timeout.
    """
    if not ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY requerida para el Agent SDK real")

    work_dir = Path(BUILDS_WORK_ROOT) / build_id
    zip_path = work_dir / f"build-{build_id}.zip"

    await on_progress("Preparando working dir aislado…")
    copy_template(work_dir)
    await on_progress(f"Plantilla copiada en {work_dir}")

    if await is_cancelled():
        raise RuntimeError("CANCELLED")

    # Import diferido: si el paquete no esta, el stub sigue funcionando
    try:
        from claude_agent_sdk import query, ClaudeAgentOptions
    except ImportError as e:
        raise RuntimeError(
            "claude-agent-sdk no instalado. Corre: pip install claude-agent-sdk"
        ) from e

    # env MINIMO — nunca os.environ.copy()
    agent_env = {
        "ANTHROPIC_API_KEY": ANTHROPIC_API_KEY,
        "API_TIMEOUT_MS": str(BUILDS_TIMEOUT_SECONDS * 1000),
    }

    options = ClaudeAgentOptions(
        cwd=str(work_dir),
        allowed_tools=["Read", "Write", "Edit", "Glob", "Grep"],
        disallowed_tools=["Bash", "WebSearch", "WebFetch"],
        max_turns=BUILDS_MAX_TURNS,
        max_budget_usd=BUILDS_PER_BUILD_CAP_USD,
        permission_mode="acceptEdits",
        env=agent_env,
        system_prompt=_SYSTEM_PROMPT,
        setting_sources=[],  # no cargar ~/.claude ni settings del host
    )

    full_prompt = (
        f"Mision de la Fabrica Cyberandres:\n\n"
        f"{prompt.strip()}\n\n"
        f"Implementa los cambios necesarios sobre esta copia de la plantilla. "
        f"No uses Bash. Solo edita archivos con las herramientas permitidas."
    )

    await on_progress("Iniciando Claude Agent SDK…")
    actual_cost = 0.0

    async def _run_query():
        nonlocal actual_cost
        async for message in query(prompt=full_prompt, options=options):
            if await is_cancelled():
                raise RuntimeError("CANCELLED")

            # Intentar capturar costo si el SDK lo expone
            for attr in ("total_cost_usd", "cost_usd", "total_cost"):
                val = getattr(message, attr, None)
                if isinstance(val, (int, float)) and val > 0:
                    actual_cost = float(val)

            data = getattr(message, "data", None)
            if isinstance(data, dict):
                for key in ("total_cost_usd", "cost_usd"):
                    if key in data and isinstance(data[key], (int, float)):
                        actual_cost = float(data[key])

            text = _message_to_progress(message)
            if text:
                await on_progress(text)

    try:
        await asyncio.wait_for(_run_query(), timeout=BUILDS_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        raise RuntimeError(f"Timeout tras {BUILDS_TIMEOUT_SECONDS}s (BUILD_001_TIMEOUT)")

    if await is_cancelled():
        raise RuntimeError("CANCELLED")

    await on_progress("Escaneando secretos pre-zip…")
    findings = scan_secrets(work_dir)
    if findings:
        # No bloquear el zip, pero avisar (el admin ve el log)
        await on_progress(
            f"ADVERTENCIA: posibles secretos en {len(findings)} archivo(s): "
            + ", ".join(findings[:5])
        )

    await on_progress("Generando archivo .zip…")
    make_zip(work_dir, zip_path)

    if actual_cost <= 0:
        # Fallback: usar una fraccion del tope si el SDK no reporto costo
        actual_cost = round(BUILDS_PER_BUILD_CAP_USD * 0.5, 4)

    actual_cost = round(min(actual_cost, BUILDS_PER_BUILD_CAP_USD), 4)

    await on_progress(f"Build completado. Costo reportado: ${actual_cost}")
    return {
        "actual_cost_usd": actual_cost,
        "zip_path": str(zip_path),
        "work_dir": str(work_dir),
    }
