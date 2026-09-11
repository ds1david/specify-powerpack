<#
.SYNOPSIS
    Resolve / relaunch / start a CDP endpoint for the experimental Edge/CDP
    ChatGPT probe (scripts/homologation/probe_edge_chatgpt_cdp.py).

.DESCRIPTION
    Run on Windows, or let the Python probe invoke it. Endpoint detection is
    FILESYSTEM-based (the DevToolsActivePort file), never a slow HTTP poll.

    Modes:
      (default)   1. quick HTTP probe on -Port (127.0.0.1 / localhost).  -> CDP_URL=
                  2. DevToolsActivePort of your live Edge profile.        -> WS_URL=
                  3. -CheckOnly stops here.
      -Relaunch   kill every msedge.exe (loop until gone), relaunch YOUR
                  DEFAULT profile with --remote-debugging-port +
                  --remote-allow-origins=*. If Edge's process singleton /
                  startup-boost swallows the flags (no DevToolsActivePort),
                  fall back to a DEDICATED profile automatically.
      (else)      start a DEDICATED Edge (separate --user-data-dir,
                  --remote-allow-origins=*), wait for its DevToolsActivePort.

    Prints exactly one endpoint line (CDP_URL= / WS_URL=), then any
    /json/version JSON it could fetch.

.PARAMETER Port          Debugging port (default 9222).
.PARAMETER CheckOnly     Only probe; never launch/relaunch.
.PARAMETER Relaunch      Kill msedge, relaunch DEFAULT profile, fall back to dedicated.
.PARAMETER EdgeUserData  Live Edge profile dir. Default %LOCALAPPDATA%\Microsoft\Edge\User Data
.PARAMETER UserDataDir   DEDICATED Edge profile dir.
.PARAMETER StartUrl      URL opened on a fresh launch/relaunch.
#>
param(
    [int]$Port = 9222,
    [switch]$CheckOnly,
    [switch]$Relaunch,
    [string]$EdgeUserData = "$env:LOCALAPPDATA\Microsoft\Edge\User Data",
    [string]$UserDataDir = "$env:LOCALAPPDATA\SpeckitPowerpack\EdgeAutomation",
    [string]$StartUrl = "https://chatgpt.com"
)

try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
$ErrorActionPreference = "Continue"
$ProgressPreference = "SilentlyContinue"   # no <Objs> progress spam on stderr

# Diagnostics -> real stderr (no CLIXML wrapping under -NonInteractive interop).
# Only the endpoint line + JSON go to stdout via Write-Output.
function Say($m) { [Console]::Error.WriteLine("$m") }

function Get-Http($url) {
    try {
        $req = [System.Net.HttpWebRequest]::Create($url)
        $req.Proxy = $null; $req.Timeout = 1500; $req.ReadWriteTimeout = 1500
        $resp = $req.GetResponse()
        $body = (New-Object System.IO.StreamReader($resp.GetResponseStream())).ReadToEnd()
        $resp.Close()
        return @{ ok = $true; body = $body; status = 200 }
    } catch [System.Net.WebException] {
        $code = 0
        if ($_.Exception.Response) { $code = [int]$_.Exception.Response.StatusCode }
        return @{ ok = $false; body = $null; status = $code }
    } catch { return @{ ok = $false; body = $null; status = -1 } }
}

function Quick-HttpCdp($port) {
    foreach ($addr in @("127.0.0.1", "localhost")) {
        $r = Get-Http "http://${addr}:$port/json/version"
        if ($r.ok) {
            $ws = $null
            try { $ws = (ConvertFrom-Json $r.body).webSocketDebuggerUrl } catch {}
            return @{ base = "http://${addr}:$port"; ws = $ws; body = $r.body; status = 200 }
        }
        if ($r.status -eq 403) { return @{ base = $null; ws = $null; body = $null; status = 403 } }
    }
    return @{ base = $null; ws = $null; body = $null; status = 0 }
}

function Read-ActivePort($dir) {
    $f = Join-Path $dir "DevToolsActivePort"
    if (-not (Test-Path $f)) { return $null }
    $lines = Get-Content $f -ErrorAction SilentlyContinue
    if ($lines -and $lines.Count -ge 2 -and "$($lines[0])".Trim() -match '^\d+$') {
        return @{ port = "$($lines[0])".Trim(); path = "$($lines[1])".Trim() }
    }
    return $null
}

function Wait-And-Emit($dir, $seconds) {
    for ($i = 0; $i -lt ($seconds * 2); $i++) {
        Start-Sleep -Milliseconds 500
        $ap = Read-ActivePort $dir
        if (-not $ap) { continue }
        Say "DevToolsActivePort ready (port $($ap.port))"
        $ws = "ws://localhost:$($ap.port)$($ap.path)"; $body = $null
        foreach ($addr in @("127.0.0.1", "localhost")) {
            $v = Get-Http "http://${addr}:$($ap.port)/json/version"
            if ($v.ok) {
                $body = $v.body
                try { $u = (ConvertFrom-Json $v.body).webSocketDebuggerUrl; if ($u) { $ws = $u } } catch {}
                break
            }
        }
        Write-Output "WS_URL=$ws"
        if ($body) { Write-Output $body }
        return $true
    }
    return $false
}

function Find-Edge {
    $c = @("$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
           "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe") |
        Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $c) {
        $c = (Get-Command msedge.exe -ErrorAction SilentlyContinue).Source
    }
    return $c
}

function Test-PortFree($port) {
    try {
        $l = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $port)
        $l.Start(); $l.Stop(); return $true
    } catch { return $false }
}

function Kill-Edge {
    for ($k = 0; $k -lt 12; $k++) {
        $p = Get-Process msedge -ErrorAction SilentlyContinue
        if (-not $p) { return $true }
        $p | Stop-Process -Force -ErrorAction SilentlyContinue
        Start-Sleep -Milliseconds 700
    }
    return $false
}

function Launch-Dedicated($edge) {
    $lp = $Port
    while (-not (Test-PortFree $lp) -and $lp -lt ($Port + 20)) { $lp++ }
    New-Item -ItemType Directory -Force -Path $UserDataDir | Out-Null
    Remove-Item (Join-Path $UserDataDir "DevToolsActivePort") -Force -ErrorAction SilentlyContinue
    Say "Launching DEDICATED Edge on port $lp (profile: $UserDataDir)"
    Say "  -> a new Edge window opens; sign in to ChatGPT once, then re-run."
    Start-Process -FilePath $edge -ArgumentList @(
        "--remote-debugging-port=$lp", "--remote-debugging-address=127.0.0.1",
        "--remote-allow-origins=*", "--user-data-dir=`"$UserDataDir`"",
        "--no-first-run", "--no-default-browser-check", "--disable-sync", $StartUrl
    )
    if (Wait-And-Emit $UserDataDir 30) { return $true }
    Say "Dedicated Edge produced no DevToolsActivePort in 30s."
    return $false
}

$edge = Find-Edge
if (-not $edge) {
    Say "msedge.exe not found (Program Files or PATH)."
    exit 1
}

# ---- -Relaunch: default profile, then dedicated fallback ----------------------
if ($Relaunch) {
    Say "Closing all Edge processes ..."
    $gone = Kill-Edge
    if (-not $gone) { Say "  (some msedge processes survived - startup boost?)" }
    Start-Sleep -Seconds 2
    Remove-Item (Join-Path $EdgeUserData "DevToolsActivePort") -Force -ErrorAction SilentlyContinue
    Say "Relaunching your DEFAULT Edge profile with remote debugging ..."
    Start-Process -FilePath $edge -ArgumentList @(
        "--remote-debugging-port=$Port", "--remote-allow-origins=*",
        "--no-default-browser-check", $StartUrl
    )
    if (Wait-And-Emit $EdgeUserData 25) { exit 0 }
    Say "Default-profile relaunch produced no debug port (Edge singleton / startup boost)."
    Say "Falling back to a dedicated profile ..."
    if (Launch-Dedicated $edge) { exit 0 }
    exit 1
}

# ---- 1. quick HTTP probe ----------------------------------------------------------
$q = Quick-HttpCdp $Port
if ($q.base) {
    Say "Reusing CDP endpoint at $($q.base)"
    if ($q.ws) { Write-Output "WS_URL=$($q.ws)" } else { Write-Output "CDP_URL=$($q.base)" }
    if ($q.body) { Write-Output $q.body }
    exit 0
}
if ($q.status -eq 403) {
    Say "Port $Port answers 403 - Edge lacks --remote-allow-origins=*."
    if ($CheckOnly) { Say "Re-run the probe with --relaunch-my-edge or --launch."; exit 3 }
}

# ---- 2. DevToolsActivePort of the live profile ---------------------------------
$ap = Read-ActivePort $EdgeUserData
if ($ap -and $q.status -ne 403) {
    Say "Found live Edge via DevToolsActivePort (port $($ap.port))"
    Write-Output "WS_URL=ws://localhost:$($ap.port)$($ap.path)"
    $v = Get-Http "http://localhost:$($ap.port)/json/version"
    if ($v.ok) { Write-Output $v.body }
    exit 0
}

if ($CheckOnly) { Say "No usable CDP endpoint on port $Port."; exit 1 }

# ---- dedicated -------------------------------------------------------------------
if (Launch-Dedicated $edge) { exit 0 }
exit 1
