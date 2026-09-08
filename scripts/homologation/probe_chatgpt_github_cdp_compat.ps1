$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$sourcePath = Join-Path $PSScriptRoot "probe_chatgpt_github_cdp.ps1"
if (-not (Test-Path $sourcePath)) {
    [Console]::Error.WriteLine("CDP probe source not found: $sourcePath")
    exit 2
}

$source = [IO.File]::ReadAllText($sourcePath)

# Windows PowerShell 5.1 rejects a derived exception catch that follows its
# base exception catch. TaskCanceledException derives from
# OperationCanceledException, so the second handler is unreachable and must be
# removed before the probe is parsed.
$fixed = [Text.RegularExpressions.Regex]::Replace(
    $source,
    '(?ms)\s*catch \[System\.Threading\.Tasks\.TaskCanceledException\]\s*\{\s*return \$null\s*\}',
    ''
)

# Invoke-RestMethod does not need -UseBasicParsing. Removing it makes the same
# probe source usable across Windows PowerShell 5.1 and PowerShell 7+.
$fixed = $fixed.Replace(' -UseBasicParsing', '')

if ($fixed -eq $source) {
    [Console]::Error.WriteLine("CDP compatibility shim did not find the expected PowerShell 5.1 compatibility patterns.")
    exit 3
}

$tempPath = Join-Path ([IO.Path]::GetTempPath()) ("speckit-powerpack-cdp-probe-{0}.ps1" -f ([Guid]::NewGuid().ToString("N")))
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[IO.File]::WriteAllText($tempPath, $fixed, $utf8NoBom)

try {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $tempPath @args
    $exitCode = $LASTEXITCODE
} finally {
    Remove-Item -LiteralPath $tempPath -Force -ErrorAction SilentlyContinue
}

exit $exitCode
