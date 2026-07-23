# Worker de builds (v1 stub).
# Toma builds en estado "queued", simula progreso con eventos, genera un zip
# de ejemplo y marca el build como completed/failed. Sirve para probar toda
# la UI (SSE, historial, presupuesto, cancel) sin Claude Agent SDK todavia.
# Cuando se implemente el Agent real, se reemplaza solo la funcion run_stub_build.

from __future__ import annotations

import asyncio
import logging
import os
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from builds.config import BUILDS_WORK_ROOT, BUILDS_PER_BUILD_CAP_USD
from builds.repositories import build_repository as repo

logger = logging.getLogger("builds.worker")

# Registro en memoria de colas SSE por build_id: lista de asyncio.Queue
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
    """Envia un evento a todos los suscriptores SSE del build."""
    for q in list(_sse_subscribers.get(build_id, [])):
        try:
            q.put_nowait({"event": event, "data": data})
        except asyncio.QueueFull:
            pass


async def _next_queued_build() -> dict | None:
    items, _ = await repo.list_builds(page=1, limit=1, status="queued")
    return items[0] if items else None


async def run_stub_build(build: dict) -> None:
    """Simula un build realista: progreso por pasos, costo y zip de ejemplo."""
    build_id = build["id"]
    now = datetime.now(timezone.utc)

    await repo.update_build(build_id, status="running", started_at=now)
    await repo.append_event(build_id, f"[{now.isoformat()}] Worker tomo el build")
    await publish(build_id, "status", {"status": "running", "queue_position": None})
    await publish(build_id, "progress", {"ts": now.isoformat(), "message": "Iniciando working dir..."})

    work_root = Path(BUILDS_WORK_ROOT) / build_id
    work_root.mkdir(parents=True, exist_ok=True)
    await repo.update_build(build_id, work_dir=str(work_root))

    steps = [
        (1.0, "Copiando plantilla al working dir..."),
        (1.2, "Analizando prompt del usuario..."),
        (1.5, "Planificando cambios en backend y frontend..."),
        (2.0, "Aplicando ediciones (stub)..."),
        (1.0, "Escaneando secretos pre-zip..."),
        (0.8, "Generando archivo .zip..."),
    ]

    for delay, message in steps:
        # Permitir cancelacion entre pasos
        current = await repo.get_build(build_id)
        if current and current["status"] == "cancelled":
            await publish(build_id, "progress", {
                "ts": datetime.now(timezone.utc).isoformat(),
                "message": "Build cancelado por el usuario",
            })
            await publish(build_id, "done", {
                "status": "cancelled",
                "cost_real_usd": 0.0,
                "download_url": None,
            })
            return

        await asyncio.sleep(delay)
        ts = datetime.now(timezone.utc).isoformat()
        await repo.append_event(build_id, f"[{ts}] {message}")
        await publish(build_id, "progress", {"ts": ts, "message": message})

    # Generar zip de ejemplo
    zip_path = work_root / f"build-{build_id}.zip"
    readme = work_root / "README-FABRICA.txt"
    readme.write_text(
        f"Fábrica Cyberandres — build stub\n"
        f"Build ID: {build_id}\n"
        f"Prompt: {build.get('prompt', '')[:500]}\n"
        f"Generado: {datetime.now(timezone.utc).isoformat()}\n"
        f"\nEste es un ZIP de ejemplo del worker stub.\n"
        f"Cuando se active el Claude Agent SDK real, aqui ira el codigo generado.\n",
        encoding="utf-8",
    )
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(readme, arcname="README-FABRICA.txt")

    # Costo real simulado (un poco menor que el estimado)
    estimated = float(build.get("estimated_cost_usd") or 0.1)
    actual = round(min(estimated * 0.85, BUILDS_PER_BUILD_CAP_USD), 4)

    finished = datetime.now(timezone.utc)
    await repo.update_build(
        build_id,
        status="completed",
        actual_cost_usd=actual,
        finished_at=finished,
        zip_path=str(zip_path),
    )
    await repo.append_event(build_id, f"[{finished.isoformat()}] Build completado (stub). Costo: ${actual}")

    await publish(build_id, "progress", {
        "ts": finished.isoformat(),
        "message": f"Build completado. Costo real: ${actual}",
    })
    await publish(build_id, "done", {
        "status": "completed",
        "cost_real_usd": actual,
        "download_url": f"/api/builds/{build_id}/download",
    })
    logger.info("Build %s completado (stub), costo=$%.4f", build_id, actual)


async def _worker_loop(stop: asyncio.Event) -> None:
    logger.info("Worker de builds iniciado (modo stub)")
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
                # Re-verificar que sigue queued (otra instancia pudo tomarlo)
                current = await repo.get_build(build_id)
                if not current or current["status"] != "queued":
                    continue
                await run_stub_build(current)
            except Exception as exc:
                logger.exception("Error en build %s: %s", build_id, exc)
                now = datetime.now(timezone.utc)
                await repo.update_build(
                    build_id,
                    status="failed",
                    error_code="BUILD_009_WORKER_ERROR",
                    error_message=str(exc)[:500],
                    finished_at=now,
                    actual_cost_usd=0.0,
                )
                await publish(build_id, "done", {
                    "status": "failed",
                    "cost_real_usd": 0.0,
                    "download_url": None,
                })
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
