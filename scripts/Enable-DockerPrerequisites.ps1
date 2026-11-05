#Requires -RunAsAdministrator
$ErrorActionPreference = 'Stop'
$projectPath = Split-Path -Parent $PSScriptRoot
$results = @()
foreach ($featureName in @('Microsoft-Windows-Subsystem-Linux', 'VirtualMachinePlatform')) {
    $result = Enable-WindowsOptionalFeature -Online -FeatureName $featureName -All -NoRestart
    $results += [pscustomobject]@{ Feature = $featureName; RestartNeeded = $result.RestartNeeded }
}
$reportDirectory = Join-Path $projectPath 'reports\installation'
New-Item -ItemType Directory -Path $reportDirectory -Force | Out-Null
$results | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $reportDirectory 'windows-features.json') -Encoding UTF8
Write-Output 'Docker prerequisites enabled. Restart Windows if the report says RestartNeeded, then rerun the verified Docker installer.'
