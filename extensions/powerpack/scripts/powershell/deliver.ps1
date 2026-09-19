param([Parameter(ValueFromRemainingArguments = $true)][string[]] $TargetParts)
$ErrorActionPreference = "Stop"
$target = ($TargetParts -join " ").Trim()
if ([string]::IsNullOrWhiteSpace($target)) {
  Write-Error "Usage: deliver.ps1 <existing-spec-id-or-feature-description>"
  exit 2
}
$argsList = @(
  "workflow", "run", "powerpack-delivery",
  "--input", "target=$target",
  "--input", "integration=auto",
  "--input", "script_runtime=ps"
)
& specify @argsList
exit $LASTEXITCODE
