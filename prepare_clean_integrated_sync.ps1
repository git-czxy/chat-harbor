$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Upstream = Join-Path $Root 'Tampermonkey.efa1f0f.js'
$Output = Join-Path $Root 'ChatHarbor-IntegratedSync-0.0.11.1.user.js'
$Patcher = Join-Path $Root 'ChatHarbor_IntegratedSync_patch.py'
$Url = 'https://raw.githubusercontent.com/huhusmang/ChatGPT-Exporter/efa1f0f266d15c053af4ab4607b948a06332d9f7/Tampermonkey.js'

Write-Host 'Downloading fixed huhusmang baseline...'
Invoke-WebRequest -Uri $Url -OutFile $Upstream

$python = Get-Command python -ErrorAction SilentlyContinue
if ($python) {
    & $python.Source $Patcher $Upstream $Output
} else {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if (-not $py) { throw 'Python 3 was not found in PATH.' }
    & $py.Source -3 $Patcher $Upstream $Output
}

if ($LASTEXITCODE -ne 0) { throw "Patcher failed with exit code $LASTEXITCODE" }
Write-Host ''
Write-Host 'Generated:' $Output
Get-FileHash $Output -Algorithm SHA256 | Format-List
