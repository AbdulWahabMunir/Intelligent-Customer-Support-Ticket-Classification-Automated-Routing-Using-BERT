$ErrorActionPreference = 'Stop'
$projectPath = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectPath '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Create .venv and install requirements-dashboard.txt first; see README.md.' }
function Test-ProjectEndpoint([string]$Address) {
    try { return (Invoke-WebRequest -Uri $Address -UseBasicParsing -TimeoutSec 2).StatusCode -eq 200 } catch { return $false }
}
if (-not (Test-ProjectEndpoint 'http://127.0.0.1:8000/health')) {
    Start-Process -FilePath $pythonPath -ArgumentList '-m','uvicorn','app.api:app','--host','127.0.0.1','--port','8000' -WorkingDirectory $projectPath -WindowStyle Hidden
}
if (-not (Test-ProjectEndpoint 'http://127.0.0.1:8501/_stcore/health')) {
    Start-Process -FilePath $pythonPath -ArgumentList '-m','streamlit','run','app/dashboard.py' -WorkingDirectory $projectPath -WindowStyle Hidden
}
$projectReady = $false
for ($attempt = 0; $attempt -lt 90; $attempt++) {
    if ((Test-ProjectEndpoint 'http://127.0.0.1:8000/health') -and (Test-ProjectEndpoint 'http://127.0.0.1:8501/_stcore/health')) { $projectReady = $true; break }
    Start-Sleep -Seconds 1
}
if (-not $projectReady) { throw 'Services did not become ready. Start them in visible terminals using the README commands to inspect the error.' }
Write-Output 'Dashboard: http://127.0.0.1:8501'
Write-Output 'API docs:  http://127.0.0.1:8000/docs'
