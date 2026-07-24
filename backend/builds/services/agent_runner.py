# Ejecuta un build real con Claude Agent SDK sobre una copia aislada de la plantilla.
from __future__ import annotations

import asyncio
import logging
import re
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Awaitable, Callable, Optional

from builds.config import (
    ANTHROPIC_API_KEY,
    BUILDS_MAX_TURNS,
    BUILDS_PER_BUILD_CAP_USD,
    BUILDS_TIMEOUT_SECONDS,
    BUILDS_WORK_ROOT,
    BUILDS_TEMPLATE_ROOT,
    BUILDS_MODEL_MAP,
)

logger = logging.getLogger("builds.agent_runner")

ProgressCb = Callable[[str], Awaitable[None]]
IsCancelledCb = Callable[[], Awaitable[bool]]

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
6. Responde y trabaja en el idioma del usuario.
7. Al terminar, deja el codigo listo para correr (imports, rutas registradas si aplica).

Trabaja solo dentro del directorio de trabajo actual."""

_TEMPLATE_ADDENDA = {
    "full_stack": (
        "\n\nAlcance: App Full Stack. Podes tocar backend/ Y frontend/src/features/."
    ),
    "web_landing": (
        "\n\nAlcance: Pagina web / Landing. Enfocate en frontend/src/."
    ),
    "mobile_apk": (
        "\n\nAlcance: App movil (Capacitor/Android)."
    ),
    "backend_only": (
        "\n\nAlcance: Solo API. Toca unicamente backend/."
    ),
    "custom": (
        "\n\nAlcance: libre/avanzado segun el prompt del usuario."
    ),
}

_AGENT_ADDENDA = {
    "architect": "\n\nRol: arquitecto. Disena estructura; poco codigo de implementacion.",
    "implementer": "",
    "reviewer": "\n\nRol: revisor. NO agregues features nuevas.",
    "mobile": "\n\nRol: movil. Prioriza Capacitor/Android.",
    "docs": "\n\nRol: documentacion. Prioriza README y comentarios.",
}


def _build_system_prompt(template_type: str, agent: str) -> str:
    return _SYSTEM_PROMPT + _TEMPLATE_ADDENDA.get(template_type, "") + _AGENT_ADDENDA.get(agent, "")


def _resolve_model(model: str) -> str:
    return BUILDS_MODEL_MAP.get(model, BUILDS_MODEL_MAP["sonnet"])


def _repo_root() -> Path:
    if BUILDS_TEMPLATE_ROOT:
        return Path(BUILDS_TEMPLATE_ROOT).resolve()
    return Path(__file__).resolve().parents[3]


def _should_skip(name: str) -> bool:
    return name in _COPY_DENYLIST or name.endswith(".pyc")


def copy_template(work_dir: Path) -> None:
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
    try:
        if hasattr(msg, "result") and msg.result:
            text = str(msg.result)
            return text[:300] + ("…" if len(text) > 300 else "")
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
        subtype = getattr(msg, "subtype", None)
        if subtype:
            return f"[{subtype}]"
    except Exception:
        return None
    return None


async def _assert_subprocess_capable() -> None:
    if sys.platform != "win32":
        return
    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-c", "pass",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()
    except NotImplementedError as e:
        raise RuntimeError(
            "WINDOWS_EVENTLOOP: usa backend/start-backend-agent.ps1 sin --reload."
        ) from e


async def run_agent_build(
    build_id: str,
    prompt: str,
    on_progress: ProgressCb,
    is_cancelled: IsCancelledCb,
    template_type: str = "full_stack",
    agent: str = "implementer",
    model: str = "sonnet",
    api_key: Optional[str] = None,
) -> dict:
    key = (api_key or ANTHROPIC_API_KEY or "").strip()
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY requerida (conecta tu Claude en la Fábrica)")

    await _assert_subprocess_capable()

    work_dir = Path(BUILDS_WORK_ROOT) / build_id
    zip_path = work_dir / f"build-{build_id}.zip"

    await on_progress("Preparando working dir aislado…")
    copy_template(work_dir)
    await on_progress(f"Plantilla copiada en {work_dir}")

    if await is_cancelled():
        raise RuntimeError("CANCELLED")

    try:
        from claude_agent_sdk import query, ClaudeAgentOptions
    except ImportError as e:
        raise RuntimeError(
            "claude-agent-sdk no instalado. Corre: pip install claude-agent-sdk"
        ) from e

    agent_env = {
        "ANTHROPIC_API_KEY": key,
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
        system_prompt=_build_system_prompt(template_type, agent),
        model=_resolve_model(model),
        setting_sources=[],
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
            for attr in ("total_cost_usd", "cost_usd", "total_cost"):
                val = getattr(message, attr, None)
                if isinstance(val, (int, float)) and val > 0:
                    actual_cost = float(val)
            data = getattr(message, "data", None)
            if isinstance(data, dict):
                for k in ("total_cost_usd", "cost_usd"):
                    if k in data and isinstance(data[k], (int, float)):
                        actual_cost = float(data[k])
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
        await on_progress(
            f"ADVERTENCIA: posibles secretos en {len(findings)} archivo(s): "
            + ", ".join(findings[:5])
        )

    await on_progress("Generando archivo .zip…")
    make_zip(work_dir, zip_path)

    if actual_cost <= 0:
        actual_cost = round(BUILDS_PER_BUILD_CAP_USD * 0.5, 4)
    actual_cost = round(min(actual_cost, BUILDS_PER_BUILD_CAP_USD), 4)

    await on_progress(f"Build completado. Costo reportado: ${actual_cost}")
    return {
        "actual_cost_usd": actual_cost,
        "zip_path": str(zip_path),
        "work_dir": str(work_dir),
    }
