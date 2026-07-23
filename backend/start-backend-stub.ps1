# Arranca el backend en modo STUB de la Fabrica de builds: simula el pipeline
# completo (working dir, "ediciones", zip) SIN llamar al Agent SDK real, asi
# que no gasta tokens de Anthropic. Sirve para probar UI/historial/descarga.
# Detalle completo: docs/BUILDS.md
$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

# Limpia la clave de esta sesion para forzar modo STUB aunque el sistema
# tenga ANTHROPIC_API_KEY definida a nivel de usuario/maquina.
Remove-Item Env:\ANTHROPIC_API_KEY -ErrorAction SilentlyContinue

Write-Host "Backend -> modo STUB (builds simulados, sin costo real). --reload activo." -ForegroundColor Cyan

# Si tu entorno usa un venv propio, reemplaza 'python' por la ruta a su
# interprete, ej: & ".\venv\Scripts\python.exe" -m uvicorn ...
python -m uvicorn server:app --host 0.0.0.0 --port 8001 --reload
