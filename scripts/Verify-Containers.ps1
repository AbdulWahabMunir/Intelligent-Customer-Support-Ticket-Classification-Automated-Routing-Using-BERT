$ErrorActionPreference = 'Stop'
$projectPath = Split-Path -Parent $PSScriptRoot
$dockerCommand = Get-Command docker -ErrorAction SilentlyContinue
$dockerPath = if ($dockerCommand) { $dockerCommand.Source } else { Join-Path $env:LOCALAPPDATA 'Programs\DockerDesktop\resources\bin\docker.exe' }
if (-not (Test-Path -LiteralPath $dockerPath)) { throw 'Docker Desktop is not installed.' }
Push-Location $projectPath
try {
    & $dockerPath info --format '{{.ServerVersion}}'
    if ($LASTEXITCODE -ne 0) { throw 'Docker engine is unavailable. Restart Windows if prerequisite setup requires it, then start Docker Desktop.' }
    & $dockerPath compose config --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Compose validation failed.' }
    & $dockerPath compose up --build -d --wait --wait-timeout 300
    if ($LASTEXITCODE -ne 0) { throw 'Container build or health check failed. Inspect docker compose logs.' }
    & (Join-Path $projectPath '.venv\Scripts\python.exe') scripts/verify_container_flow.py --docker $dockerPath
    if ($LASTEXITCODE -ne 0) { throw 'Container flow verification failed.' }
} finally { Pop-Location }
