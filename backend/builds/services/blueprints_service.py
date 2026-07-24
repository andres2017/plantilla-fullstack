"""Carga y resuelve blueprints JSON (ES/EN). Fuente: shared/blueprints/."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("builds.blueprints")

# repo_root/shared/blueprints — desde backend/builds/services → parents[3]
_BLUEPRINTS_DIR = Path(__file__).resolve().parents[3] / "shared" / "blueprints"


def _resolve_locale_value(value: Any, locale: str) -> Any:
    if isinstance(value, dict) and ("es" in value or "en" in value):
        return value.get(locale) or value.get("es") or value.get("en")
    if isinstance(value, list):
        return [_resolve_locale_value(v, locale) for v in value]
    if isinstance(value, dict):
        return {k: _resolve_locale_value(v, locale) for k, v in value.items()}
    return value


def _load_raw(blueprint_id: str) -> dict | None:
    path = _BLUEPRINTS_DIR / f"{blueprint_id}.json"
    if not path.is_file():
        return None
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def list_blueprints(locale: str = "es") -> list[dict]:
    locale = "en" if locale == "en" else "es"
    items = []
    if not _BLUEPRINTS_DIR.is_dir():
        logger.warning("Blueprints dir no existe: %s", _BLUEPRINTS_DIR)
        return items
    for path in sorted(_BLUEPRINTS_DIR.glob("*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error("Blueprint inválido %s: %s", path.name, e)
            continue
        items.append({
            "id": raw.get("id") or path.stem,
            "version": raw.get("version", "1.0.0"),
            "titulo": _resolve_locale_value(raw.get("titulo", path.stem), locale),
            "descripcion": _resolve_locale_value(raw.get("descripcion", ""), locale),
            "pasos_count": len(raw.get("pasos") or []),
            "local_hint": _resolve_locale_value(raw.get("local_hint", ""), locale),
            "publish_hint": _resolve_locale_value(raw.get("publish_hint", ""), locale),
        })
    return items


def get_blueprint(blueprint_id: str, locale: str = "es") -> dict | None:
    locale = "en" if locale == "en" else "es"
    raw = _load_raw(blueprint_id)
    if not raw:
        return None
    return _resolve_locale_value(raw, locale)


def compute_progress(blueprint_id: str, builds: list[dict], locale: str = "es") -> dict:
    bp = get_blueprint(blueprint_id, locale)
    if not bp:
        return {"blueprint_id": blueprint_id, "steps": []}

    steps_out = []
    completed_impl = set()
    completed_learn = set()
    failed_steps = set()
    active_steps = set()

    for b in builds:
        sid = b.get("blueprint_step_id")
        if not sid or b.get("template_type") not in (None, blueprint_id):
            # permitir template_type == blueprint_id
            if b.get("template_type") and b.get("template_type") != blueprint_id:
                continue
        if not sid:
            continue
        st = b.get("status")
        mode = b.get("mode") or "implement"
        if st in ("queued", "running"):
            active_steps.add(sid)
        elif st == "completed":
            if mode == "learn":
                completed_learn.add(sid)
            else:
                completed_impl.add(sid)
        elif st == "failed":
            failed_steps.add(sid)

    done_impl = set(completed_impl)
    for step in bp.get("pasos") or []:
        sid = step["id"]
        deps = step.get("depende_de") or []
        deps_ok = all(d in done_impl for d in deps)

        if sid in active_steps:
            state = "en_curso"
        elif sid in completed_impl:
            state = "hecho"
        elif sid in completed_learn:
            state = "aprendido"
        elif sid in failed_steps and sid not in completed_impl:
            state = "fallido"
        elif not deps_ok and (bp.get("orden_estricto") or deps):
            # bloquear solo si hay deps y no están hechos en implement
            state = "bloqueado" if not deps_ok else "pendiente"
        else:
            state = "pendiente"

        steps_out.append({
            "id": sid,
            "titulo": step.get("titulo"),
            "state": state,
            "depende_de": deps,
        })

    done_count = sum(1 for s in steps_out if s["state"] == "hecho")
    return {
        "blueprint_id": blueprint_id,
        "version": bp.get("version"),
        "done": done_count,
        "total": len(steps_out),
        "steps": steps_out,
    }
