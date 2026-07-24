# Launcher del backend en modo AGENT SDK real para Windows.
#
# Fuerza WindowsProactorEventLoopPolicy ANTES de que uvicorn cree el loop, en
# vez de confiar unicamente en el flag `--loop none` (que depende de como
# uvicorn interprete ese flag version a version). SelectorEventLoop no
# soporta subprocesos en Windows, y el Agent SDK necesita spawnear el CLI
# `claude` como subproceso. Ver docs/BUILDS.md y docs/DECISIONS.md
# (entrada 2026-07-23) para el detalle completo del bug que esto evita.
#
# Uso: python run_agent_server.py   (en vez de "python -m uvicorn ...")
import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import uvicorn

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8001, reload=False, loop="none")
