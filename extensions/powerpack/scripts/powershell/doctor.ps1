param([Parameter(ValueFromRemainingArguments = $true)][string[]] $DoctorArgs)
$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$doctor = Join-Path $scriptDir "../common/doctor.py"
$python = Get-Command python -ErrorAction SilentlyContinue
if ($python) {
  & $python.Source $doctor --launcher-runtime ps @DoctorArgs
  exit $LASTEXITCODE
}
$py = Get-Command py -ErrorAction SilentlyContinue
if ($py) {
  & $py.Source -3 $doctor --launcher-runtime ps @DoctorArgs
  exit $LASTEXITCODE
}
Write-Error "PowerPack doctor requires Python, which is also required by Spec Kit."
exit 127
