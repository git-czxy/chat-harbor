$ErrorActionPreference = "Stop"

$Commit = "efa1f0f266d15c053af4ab4607b948a06332d9f7"
$Url = "https://raw.githubusercontent.com/huhusmang/ChatGPT-Exporter/$Commit/Tampermonkey.js"
$Upstream = Join-Path $PSScriptRoot "Tampermonkey.js"
$Output = Join-Path $PSScriptRoot "ChatHarbor-Gate3.user.js"
$Patcher = Join-Path $PSScriptRoot "ChatHarbor_Gate3_ManifestIdentity_patch.py"

Write-Host "[1/3] Downloading fixed clean upstream..."
Invoke-WebRequest -Uri $Url -OutFile $Upstream

Write-Host "[2/3] Applying ChatHarbor Gate-3 patch..."
python $Patcher $Upstream $Output
if ($LASTEXITCODE -ne 0) { throw "Patcher failed." }

Write-Host "[3/3] Done."
Write-Host "Generated: $Output"
Write-Host "Install it in Tampermonkey and test only against a copied/disposable archive directory."
