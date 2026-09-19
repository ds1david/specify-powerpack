$ErrorActionPreference = 'Stop'
$python = if ($env:PYTHON) { $env:PYTHON } else { 'python' }
& $python (Join-Path $PSScriptRoot 'install.py') @args
exit $LASTEXITCODE
