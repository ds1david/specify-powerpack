$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Harness = Join-Path $ScriptDir "homologate.py"

if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 $Harness @args
    exit $LASTEXITCODE
}
if (Get-Command python -ErrorAction SilentlyContinue) {
    & python $Harness @args
    exit $LASTEXITCODE
}
Write-Error "Python 3.11+ is required."
exit 127
