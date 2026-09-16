$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

$node = Get-Command node -ErrorAction SilentlyContinue
if (-not $node) { throw 'Node.js is required for the regression suite.' }

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    $python = Get-Command py -ErrorAction SilentlyContinue
    if (-not $python) { throw 'Python 3 is required for the UI/static regression suite.' }
    & $python.Source -3 (Join-Path $Root 'tests\test_ui_0120.py')
    if ($LASTEXITCODE -ne 0) { throw 'UI/static regression failed.' }
    & $python.Source -3 (Join-Path $Root 'tests\test_release_0120.py')
} else {
    & $python.Source (Join-Path $Root 'tests\test_ui_0120.py')
    if ($LASTEXITCODE -ne 0) { throw 'UI/static regression failed.' }
    & $python.Source (Join-Path $Root 'tests\test_release_0120.py')
}
if ($LASTEXITCODE -ne 0) { throw 'Release invariant regression failed.' }

foreach ($test in @(
    'test_layout_v2_migration.js',
    'test_preflight_planner.js',
    'test_integrated_sync.js',
    'test_conservative_policy.js',
    'test_sleep_deadline.js'
)) {
    & $node.Source (Join-Path $Root "tests\$test")
    if ($LASTEXITCODE -ne 0) { throw "Regression failed: $test" }
}

Write-Host 'All ChatHarbor 0.0.12.0 automated regressions passed.' -ForegroundColor Green
