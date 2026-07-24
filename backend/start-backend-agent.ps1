# Arranca el backend en modo AGENT SDK real (gasta tokens de Anthropic).
#
# IMPORTANTE (Windows): corre SIN --reload y garantiza WindowsProactorEvent-
# LoopPolicy via run_agent_server.py (no confia solo en --loop none: --reload
# en Windows fuerza asyncio.SelectorEventLoop en el proceso real de la app,
# y ese loop NO soporta subprocesos. El Agent SDK necesita spawnear el CLI
# `claude` como subproceso, asi que con --reload falla con
# BUILD_011_WINDOWS_EVENTLOOP ("Failed to start Claude Code: " vacio).
# Detalle: docs/BUILDS.md y docs/DECISIONS.md (entrada 2026-07-23).
$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

if (-not $env:ANTHROPIC_API_KEY) {
    Write-Warning "ANTHROPIC_API_KEY no esta definida en esta sesion. El worker arrancara en modo STUB aunque uses este script."
    Write-Warning "Definila en esta sesion de PowerShell (env:ANTHROPIC_API_KEY) antes de correr este script."
}

# Un proceso viejo (ej. una corrida anterior con --reload) que haya quedado
# escuchando en el puerto 8001 puede quedarse atendiendo pedidos con
# SelectorEventLoop aunque este script arranque uno nuevo correctamente.
$portInUse = Get-NetTCPConnection -LocalPort 8001 -ErrorAction SilentlyContinue
if ($portInUse) {
    $pids = ($portInUse | Select-Object -ExpandProperty OwningProcess -Unique) -join ", "
    Write-Warning "El puerto 8001 ya tiene proceso(s) escuchando (PID: $pids). Puede ser una corrida anterior (ej. con --reload) que quedo viva."
    Write-Warning "Si los builds fallan con BUILD_011_WINDOWS_EVENTLOOP, cierra esos procesos primero: Stop-Process -Id <PID> -Force"
}

Write-Host "Backend -> modo AGENT SDK real (SIN --reload, WindowsProactorEventLoopPolicy forzada)." -ForegroundColor Yellow

# Si tu entorno usa un venv propio, reemplaza 'python' por la ruta a su
# interprete, ej: & ".\venv\Scripts\python.exe" run_agent_server.py
python run_agent_server.py
