# Worker de builds — BYOK + learn/implement
from __future__ import annotations

import asyncio
import logging
import os
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from builds.config import (
    BUILDS_WORK_ROOT,
    BUILDS_PER_BUILD_CAP_USD,
)
from builds.repositories import build_repository as repo
from builds.services import llm_settings_service as llm

logger = logging.getLogger("builds.worker")

_sse_subscribers: dict[str, list[asyncio.Queue]] = {}
_worker_task: asyncio.Task | None = None
_stop_event: asyncio.Event | None = None


def subscribe(build_id: str) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue()
    _sse_subscribers.setdefault(build_id, []).append(q)
    return q


def unsubscribe(build_id: str, q: asyncio.Queue) -> None:
    subs = _sse_subscribers.get(build_id)
    if not subs:
        return
    try:
        subs.remove(q)
    except ValueError:
        pass
    if not subs:
        _sse_subscribers.pop(build_id, None)


async def publish(build_id: str, event: str, data: dict) -> None:
    for q in list(_sse_subscribers.get(build_id, [])):
        try:
            q.put_nowait({"event": event, "data": data})
        except asyncio.QueueFull:
            pass


async def _emit_progress(build_id: str, message: str) -> None:
    ts = datetime.now(timezone.utc).isoformat()
    await repo.append_event(build_id, f"[{ts}] {message}")
    await publish(build_id, "progress", {"ts": ts, "message": message})


async def _next_queued_build() -> dict | None:
    items, _ = await repo.list_builds(page=1, limit=1, status="queued")
    return items[0] if items else None


async def run_stub_build(build: dict) -> None:
    build_id = build["id"]
    now = datetime.now(timezone.utc)
    mode = build.get("mode") or "implement"

    await repo.update_build(build_id, status="running", started_at=now)
    await publish(build_id, "status", {"status": "running", "queue_position": None})
    await _emit_progress(build_id, "Modo prueba (sin Claude conectado)…")

    work_root = Path(BUILDS_WORK_ROOT) / build_id
    work_root.mkdir(parents=True, exist_ok=True)
    await repo.update_build(build_id, work_dir=str(work_root))

    await asyncio.sleep(0.8)
    await _emit_progress(build_id, "Generando entrega de ejemplo…")

    zip_path = work_root / f"build-{build_id}.zip"
    if mode == "learn":
        guia = work_root / "GUIA.md"
        guia.write_text(
            f"# Guía de ejemplo (STUB)\n\n"
            f"Prompt: {build.get('prompt', '')[:800]}\n\n"
            f"Conecta tu API key de Claude para una guía real.\n",
            encoding="utf-8",
        )
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(guia, arcname="GUIA.md")
    else:
        readme = work_root / "README-FABRICA.txt"
        readme.write_text(
            f"Fabrica STUB\nBuild: {build_id}\n{build.get('prompt', '')[:500]}\n",
            encoding="utf-8",
        )
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(readme, arcname="README-FABRICA.txt")

    estimated = float(build.get("estimated_cost_usd") or 0.1)
    actual = round(min(estimated * 0.85, BUILDS_PER_BUILD_CAP_USD), 4)
    finished = datetime.now(timezone.utc)
    await repo.update_build(
        build_id, status="completed", actual_cost_usd=actual,
        finished_at=finished, zip_path=str(zip_path),
    )
    await publish(build_id, "done", {
        "status": "completed", "cost_real_usd": actual,
        "download_url": f"/api/builds/{build_id}/download",
    })


async def run_agent_build(build: dict, api_key: str) -> None:
    from builds.services.agent_runner import run_agent_build as _run

    build_id = build["id"]
    now = datetime.now(timezone.utc)
    await repo.update_build(build_id, status="running", started_at=now)
    await publish(build_id, "status", {"status": "running", "queue_position": None})
    await _emit_progress(
        build_id,
        f"Worker AGENT mode={build.get('mode') or 'implement'} "
        f"model={build.get('model') or 'sonnet'}",
    )

    async def on_progress(msg: str):
        await _emit_progress(build_id, msg)

    async def is_cancelled() -> bool:
        current = await repo.get_build(build_id)
        return bool(current and current["status"] == "cancelled")

    try:
        result = await _run(
            build_id=build_id,
            prompt=build.get("prompt") or "",
            on_progress=on_progress,
            is_cancelled=is_cancelled,
            template_type=build.get("template_type") or "full_stack",
            agent=build.get("agent") or "implementer",
            model=build.get("model") or "sonnet",
            api_key=api_key,
            mode=build.get("mode") or "implement",
        )
    except RuntimeError as exc:
        if str(exc) == "CANCELLED":
            await publish(build_id, "done", {"status": "cancelled", "cost_real_usd": 0.0, "download_url": None})
            return
        raise

    finished = datetime.now(timezone.utc)
    actual = float(result["actual_cost_usd"])
    await repo.update_build(
        build_id, status="completed", actual_cost_usd=actual,
        finished_at=finished, zip_path=result["zip_path"], work_dir=result["work_dir"],
    )
    await publish(build_id, "done", {
        "status": "completed", "cost_real_usd": actual,
        "download_url": f"/api/builds/{build_id}/download",
    })


async def _process_build(build: dict) -> None:
    user_id = build.get("created_by")
    api_key = await llm.resolve_api_key_for_user(user_id)
    if api_key:
        await run_agent_build(build, api_key)
    else:
        await run_stub_build(build)


async def _worker_loop(stop: asyncio.Event) -> None:
    logger.info("Worker de builds iniciado (BYOK + learn/implement)")
    while not stop.is_set():
        try:
            build = await _next_queued_build()
            if not build:
                await asyncio.sleep(1.5)
                continue

            build_id = build["id"]
            holder = f"worker-{os.getpid()}-{build_id[:8]}"
            acquired = await repo.try_acquire_lock(holder)
            if not acquired:
                await asyncio.sleep(1.0)
                continue

            try:
                current = await repo.get_build(build_id)
                if not current or current["status"] != "queued":
                    continue
                await _process_build(current)
            except Exception as exc:
                logger.exception("Error en build %s: %s", build_id, exc)
                now = datetime.now(timezone.utc)
                current = await repo.get_build(build_id)
                if current and current["status"] == "cancelled":
                    await publish(build_id, "done", {"status": "cancelled", "cost_real_usd": 0.0, "download_url": None})
                else:
                    msg = str(exc)[:500]
                    if "TIMEOUT" in msg.upper():
                        code = "BUILD_001_TIMEOUT"
                    elif "WINDOWS_EVENTLOOP" in msg.upper():
                        code = "BUILD_011_WINDOWS_EVENTLOOP"
                    else:
                        code = "BUILD_009_WORKER_ERROR"
                    await repo.update_build(
                        build_id, status="failed", error_code=code,
                        error_message=msg, finished_at=now, actual_cost_usd=0.0,
                    )
                    await _emit_progress(build_id, f"Error: {msg}")
                    await publish(build_id, "done", {"status": "failed", "cost_real_usd": 0.0, "download_url": None})
            finally:
                await repo.release_lock()
        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("Error en loop del worker")
            await asyncio.sleep(2.0)
    logger.info("Worker de builds detenido")


async def start_worker() -> None:
    global _worker_task, _stop_event
    if _worker_task and not _worker_task.done():
        return
    _stop_event = asyncio.Event()
    _worker_task = asyncio.create_task(_worker_loop(_stop_event))


async def stop_worker() -> None:
    global _worker_task, _stop_event
    if _stop_event:
        _stop_event.set()
    if _worker_task:
        _worker_task.cancel()
        try:
            await _worker_task
        except asyncio.CancelledError:
            pass
    _worker_task = None
    _stop_event = None
