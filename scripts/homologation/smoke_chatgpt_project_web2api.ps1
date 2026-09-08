param(
    [Parameter(Mandatory=$true)]
    [string]$HelperPath,
    [Parameter(Mandatory=$true)]
    [string]$ProjectId,
    [int]$Port = 8097,
    [int]$CdpPort = 9231,
    [string]$Profile = "web2api-github-probe",
    [string]$Model = "auto",
    [string]$Prompt = "me diga qual é o nome do projeto e sua principal missão, produza uma resposta simplificada de no máximo 100 palavras. e me responda quanto é 1 +1",
    [double]$ResponseTimeoutSec = 240,
    [switch]$NoInstall,
    [switch]$IncludeAssistantText
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$OutputEncoding = [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$Web2ApiRevision = "497527dceabfa3f95961e23c291e618c5570f1ac"
$Web2ApiUrl = "https://github.com/Octo-Lex/ChatGPT-Web2API/archive/$Web2ApiRevision.zip"

function Write-SmokeLog([string]$Message) {
    [Console]::Error.WriteLine("[web2api-project-smoke] $Message")
}

function Find-Python {
    foreach ($name in @("py.exe", "python.exe", "python")) {
        $candidate = Get-Command $name -ErrorAction SilentlyContinue
        if ($candidate) {
            return $(if ($candidate.Source) { [string]$candidate.Source } else { [string]$candidate.Name })
        }
    }
    throw "Python 3.11+ is required on Windows."
}

function Assert-Python311([string]$PythonExe) {
    $version = (& $PythonExe -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" | Out-String).Trim()
    $parts = $version.Split(".")
    if ($parts.Count -lt 2 -or [int]$parts[0] -lt 3 -or ([int]$parts[0] -eq 3 -and [int]$parts[1] -lt 11)) {
        throw "Python 3.11+ is required on Windows; detected $version"
    }
}

function Test-Service([int]$ServicePort) {
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$ServicePort/health" -TimeoutSec 3
        return ([int]$response.StatusCode -ge 200 -and [int]$response.StatusCode -lt 300)
    } catch {
        return $false
    }
}

function Wait-Service([int]$ServicePort, [int]$TimeoutSec = 300) {
    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSec)
    do {
        if (Test-Service $ServicePort) { return }
        Start-Sleep -Milliseconds 750
    } while ([DateTime]::UtcNow -lt $deadline)
    throw "ChatGPT-Web2API did not become ready on 127.0.0.1:$ServicePort."
}

function Safe-Name([string]$Value) {
    $safe = [Text.RegularExpressions.Regex]::Replace($Value, "[^A-Za-z0-9_.-]+", "-")
    $safe = $safe.Trim([char[]]"-._")
    if (-not $safe) { return "web2api-github-probe" }
    return $safe
}

if (-not (Test-Path -LiteralPath $HelperPath)) {
    throw "Web2API project smoke helper not found: $HelperPath"
}
if (-not $ProjectId.StartsWith("g-p-")) {
    throw "ProjectId must be a ChatGPT Project id (g-p-...)."
}
if ($CdpPort -lt 1024 -or $CdpPort -gt 65535 -or $Port -lt 1024 -or $Port -gt 65535) {
    throw "REST/CDP ports must be between 1024 and 65535."
}

$python = Find-Python
Assert-Python311 $python
$safeProfile = Safe-Name $Profile
$root = Join-Path $env:LOCALAPPDATA "SpecKitPowerPack\reviewers\$safeProfile"
$venv = Join-Path $root "venv"
$chromeProfile = Join-Path $root "chrome-profile"
$logs = Join-Path $root "logs"
$servicePython = Join-Path $venv "Scripts\python.exe"
New-Item -ItemType Directory -Force -Path $root,$chromeProfile,$logs | Out-Null

if (-not (Test-Path $servicePython)) {
    if ($NoInstall) {
        throw "Dedicated Web2API venv is missing: $servicePython"
    }
    Write-SmokeLog "Creating dedicated Windows venv"
    & $python -m venv $venv
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $servicePython)) {
        throw "Could not create dedicated ChatGPT-Web2API virtual environment."
    }
}

if (-not $NoInstall) {
    Write-SmokeLog "Installing pinned ChatGPT-Web2API revision $Web2ApiRevision"
    $previous = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $pipOutput = (& $servicePython -m pip install --disable-pip-version-check --no-warn-script-location --upgrade $Web2ApiUrl 2>&1 | Out-String)
        $pipExit = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previous
    }
    if ($pipExit -ne 0) {
        throw "Could not install pinned ChatGPT-Web2API.`n$($pipOutput.Trim())"
    }
}

& $servicePython -c "import chatgpt_web2api" 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "Pinned ChatGPT-Web2API is not importable from $servicePython"
}

if (-not (Test-Service $Port)) {
    $stdout = Join-Path $logs "web2api.out.log"
    $stderr = Join-Path $logs "web2api.err.log"
    $serviceArgs = @(
        "-m", "chatgpt_web2api", "start",
        "--host", "127.0.0.1",
        "--port", [string]$Port,
        "--cdp-port", [string]$CdpPort,
        "--user-data-dir", $chromeProfile
    )
    Write-SmokeLog "Starting ChatGPT-Web2API service and dedicated Chrome"
    Write-SmokeLog "Chrome profile: $chromeProfile"
    Start-Process -FilePath $servicePython -ArgumentList $serviceArgs -RedirectStandardOutput $stdout -RedirectStandardError $stderr | Out-Null
    Write-SmokeLog "If ChatGPT asks for login, authenticate normally in the dedicated Chrome window."
    Wait-Service -ServicePort $Port -TimeoutSec 300
} else {
    Write-SmokeLog "Reusing running ChatGPT-Web2API service on 127.0.0.1:$Port"
}

$helperArgs = @(
    $HelperPath,
    "--port", [string]$Port,
    "--cdp-port", [string]$CdpPort,
    "--project-id", $ProjectId,
    "--model", $Model,
    "--prompt", $Prompt,
    "--response-timeout", [string]$ResponseTimeoutSec
)
if ($IncludeAssistantText) {
    $helperArgs += "--include-assistant-text"
}

Write-SmokeLog "Running historical Project-context smoke through Web2API REST"
& $servicePython @helperArgs
$code = $LASTEXITCODE
exit $code
