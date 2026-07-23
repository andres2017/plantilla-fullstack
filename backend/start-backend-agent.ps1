# Arranca el backend en modo AGENT SDK real (gasta tokens de Anthropic).
#
# IMPORTANTE (Windows): corre SIN --reload y con --loop none a proposito.
# --reload en Windows fuerza asyncio.SelectorEventLoop en el proceso real de
# la app (uvicorn: use_subprocess=True con --reload), y ese loop NO soporta
# subprocesos. El Agent SDK necesita spawnear el CLI `claude` como
# subproceso, asi que con --reload falla con BUILD_011_WINDOWS_EVENTLOOP
# ("Failed to start Claude Code: " vacio). Detalle: docs/BUILDS.md y
# docs/DECISIONS.md (entrada 2026-07-23).
$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

if (-not $env:ANTHROPIC_API_KEY) {
    Write-Warning "ANTHROPIC_API_KEY no esta definida en esta sesion. El worker arrancara en modo STUB aunque uses este script."
    Write-Warning "Definila en esta sesion de PowerShell (env:ANTHROPIC_API_KEY) antes de correr este script."
}

Write-Host "Backend -> modo AGENT SDK real (SIN --reload, --loop none)." -ForegroundColor Yellow

# Si tu entorno usa un venv propio, reemplaza 'python' por la ruta a su
# interprete, ej: & ".\venv\Scripts\python.exe" -m uvicorn ...
python -m uvicorn server:app --host 0.0.0.0 --port 8001 --loop none
