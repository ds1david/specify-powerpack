param(
    [int]$CdpPort = 9222,
    [string]$ChatUrl = "https://chatgpt.com/",
    [string]$Prompt = "@GitHub LISTE TODOS OS MEUS REPOSITORIOS E TERMINE A RESPOSTA COM POWERPACK_GITHUB_TOOL_OK",
    [int]$MentionTimeoutSec = 25,
    [int]$ResponseTimeoutSec = 240,
    [string]$ChromeProfile = "$env:LOCALAPPDATA\SpecKitPowerPack\cdp-github-probe",
    [switch]$NoLaunch,
    [switch]$IncludeAssistantText,
    [string]$Output
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

function Write-ProbeLog([string]$Message) {
    [Console]::Error.WriteLine("[cdp-github] $Message")
}

function Find-ChromeExe {
    $candidates = @(
        "$env:PROGRAMFILES\Google\Chrome\Application\chrome.exe",
        "${env:PROGRAMFILES(X86)}\Google\Chrome\Application\chrome.exe",
        "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
    )
    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path $candidate)) { return $candidate }
    }
    $command = Get-Command chrome.exe -ErrorAction SilentlyContinue
    if ($command) { return [string]$command.Source }
    throw "Google Chrome was not found on Windows. Install Chrome or launch an existing CDP-enabled Chrome and use -NoLaunch."
}

function Start-ProbeChrome {
    param([string]$ChromeExe, [string]$Profile, [int]$Port, [string]$Url)
    New-Item -ItemType Directory -Force -Path $Profile | Out-Null
    $arguments = @(
        "--remote-debugging-port=$Port",
        "--remote-allow-origins=*",
        "--user-data-dir=$Profile",
        "--no-first-run",
        "--no-default-browser-check",
        $Url
    )
    Write-ProbeLog "Launching dedicated Chrome profile with CDP on Windows localhost:$Port"
    Start-Process -FilePath $ChromeExe -ArgumentList $arguments | Out-Null
}

function Wait-CdpReady {
    param([int]$Port, [int]$TimeoutSec = 20)
    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSec)
    do {
        try {
            $version = Invoke-RestMethod -UseBasicParsing -Uri "http://127.0.0.1:$Port/json/version" -TimeoutSec 2
            if ($version.webSocketDebuggerUrl) { return $version }
        } catch {
            Start-Sleep -Milliseconds 400
        }
    } while ([DateTime]::UtcNow -lt $deadline)
    throw "Chrome CDP endpoint did not become ready on 127.0.0.1:$Port."
}

function New-ChatTarget {
    param([int]$Port, [string]$Url)
    $encoded = [Uri]::EscapeDataString($Url)
    try {
        return Invoke-RestMethod -UseBasicParsing -Method Put -Uri "http://127.0.0.1:$Port/json/new?$encoded" -TimeoutSec 10
    } catch {
        $targets = Invoke-RestMethod -UseBasicParsing -Uri "http://127.0.0.1:$Port/json/list" -TimeoutSec 10
        $target = @($targets) | Where-Object { $_.type -eq "page" -and $_.url -like "https://chatgpt.com/*" } | Select-Object -First 1
        if ($target) { return $target }
        throw
    }
}

function Send-CdpText {
    param([System.Net.WebSockets.ClientWebSocket]$WebSocket, [string]$Text)
    $bytes = [Text.Encoding]::UTF8.GetBytes($Text)
    $segment = [ArraySegment[byte]]::new($bytes)
    $WebSocket.SendAsync(
        $segment,
        [System.Net.WebSockets.WebSocketMessageType]::Text,
        $true,
        [Threading.CancellationToken]::None
    ).GetAwaiter().GetResult()
}

function Receive-CdpJson {
    param([System.Net.WebSockets.ClientWebSocket]$WebSocket, [int]$TimeoutMs = 750)
    $cts = [Threading.CancellationTokenSource]::new()
    $cts.CancelAfter($TimeoutMs)
    $stream = [IO.MemoryStream]::new()
    try {
        do {
            $buffer = New-Object byte[] 65536
            $segment = [ArraySegment[byte]]::new($buffer)
            try {
                $result = $WebSocket.ReceiveAsync($segment, $cts.Token).GetAwaiter().GetResult()
            } catch [System.OperationCanceledException] {
                return $null
            } catch [System.Threading.Tasks.TaskCanceledException] {
                return $null
            }
            if ($result.MessageType -eq [System.Net.WebSockets.WebSocketMessageType]::Close) {
                throw "Chrome CDP websocket closed unexpectedly."
            }
            if ($result.Count -gt 0) {
                $stream.Write($buffer, 0, $result.Count)
            }
        } while (-not $result.EndOfMessage)
        $text = [Text.Encoding]::UTF8.GetString($stream.ToArray())
        if (-not $text) { return $null }
        return $text | ConvertFrom-Json
    } finally {
        $stream.Dispose()
        $cts.Dispose()
    }
}

$script:CdpMessageId = 0
$script:CdpEvents = New-Object System.Collections.ArrayList

function Add-CdpEvent($Message) {
    if ($Message -and $Message.method) { [void]$script:CdpEvents.Add($Message) }
}

function Invoke-Cdp {
    param(
        [System.Net.WebSockets.ClientWebSocket]$WebSocket,
        [string]$Method,
        [hashtable]$Params = @{},
        [int]$TimeoutSec = 12
    )
    $script:CdpMessageId += 1
    $id = $script:CdpMessageId
    $wire = @{ id = $id; method = $Method; params = $Params } | ConvertTo-Json -Depth 40 -Compress
    Send-CdpText -WebSocket $WebSocket -Text $wire
    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSec)
    do {
        $message = Receive-CdpJson -WebSocket $WebSocket -TimeoutMs 750
        if (-not $message) { continue }
        if ($message.method) {
            Add-CdpEvent $message
            continue
        }
        if ($message.id -eq $id) {
            if ($message.error) {
                throw "CDP $Method failed: $($message.error.message)"
            }
            return $message.result
        }
    } while ([DateTime]::UtcNow -lt $deadline)
    throw "Timed out waiting for CDP response to $Method."
}

function Invoke-JsValue {
    param(
        [System.Net.WebSockets.ClientWebSocket]$WebSocket,
        [string]$Expression,
        [int]$TimeoutSec = 12
    )
    $result = Invoke-Cdp -WebSocket $WebSocket -Method "Runtime.evaluate" -Params @{
        expression = $Expression
        returnByValue = $true
        awaitPromise = $true
    } -TimeoutSec $TimeoutSec
    if (-not $result.result) { return $null }
    return $result.result.value
}

function Take-CdpEvents {
    $events = @($script:CdpEvents)
    $script:CdpEvents.Clear()
    return $events
}

function Get-PostBody($Event) {
    if (-not $Event -or $Event.method -ne "Network.requestWillBeSent") { return $null }
    $request = $Event.params.request
    if (-not $request -or -not $request.postData) { return $null }
    try { return $request.postData | ConvertFrom-Json } catch { return $null }
}

function Inspect-GitHubContextChange($Event) {
    if (-not $Event -or $Event.method -ne "Network.requestWillBeSent") { return $null }
    $request = $Event.params.request
    if (-not $request -or [string]$request.method -ne "POST") { return $null }
    if ([string]$request.url -notmatch "/backend-api/f/conversation/prepare(?:\?|$)") { return $null }
    $body = Get-PostBody $Event
    if (-not $body -or [string]$body.client_prepare_source -ne "context_change") { return $null }
    $hints = @($body.system_hints)
    $hasConnector = @($hints | Where-Object { [string]$_ -match "^plugin:connector_" }).Count -gt 0
    $partial = ""
    try { $partial = [string]$body.partial_query.content.parts[0] } catch { }
    return [ordered]@{
        observed = $true
        connector_hint_present = $hasConnector
        partial_query_starts_with_github = $partial.StartsWith("GitHub ", [StringComparison]::OrdinalIgnoreCase)
        client_prepare_state = [string]$body.client_prepare_state
        client_prepare_dispatch = [string]$body.client_prepare_dispatch
    }
}

function Inspect-FinalSubmitRequest($Event) {
    if (-not $Event -or $Event.method -ne "Network.requestWillBeSent") { return $null }
    $request = $Event.params.request
    if (-not $request -or [string]$request.method -ne "POST") { return $null }
    $url = [string]$request.url
    if ($url -notmatch "/backend-api/f/conversation(?:\?|$)" -or $url -match "/prepare(?:\?|$)") { return $null }
    $body = Get-PostBody $Event
    if (-not $body) { return $null }
    $topHints = @($body.system_hints)
    $messageHints = @()
    $offsets = @()
    try { $messageHints = @($body.messages[0].metadata.system_hints) } catch { }
    try { $offsets = @($body.messages[0].metadata.serialization_metadata.custom_symbol_offsets) } catch { }
    $hasTopConnector = @($topHints | Where-Object { [string]$_ -match "^plugin:connector_" }).Count -gt 0
    $hasMessageConnector = @($messageHints | Where-Object { [string]$_ -match "^plugin:connector_" }).Count -gt 0
    $hasMention = @($offsets | Where-Object { [string]$_.symbol -eq "ecosystemMention" }).Count -gt 0
    return [ordered]@{
        observed = $true
        request_id = [string]$Event.params.requestId
        top_level_connector_hint = $hasTopConnector
        message_connector_hint = $hasMessageConnector
        ecosystem_mention_present = $hasMention
        client_prepare_state = [string]$body.client_prepare_state
    }
}

function Inspect-ResponseStatus($Event, [string]$RequestId) {
    if (-not $Event -or $Event.method -ne "Network.responseReceived") { return $null }
    if ([string]$Event.params.requestId -ne $RequestId) { return $null }
    return [int]$Event.params.response.status
}

function Wait-Composer {
    param([System.Net.WebSockets.ClientWebSocket]$WebSocket, [int]$TimeoutSec = 120)
    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSec)
    $expression = @'
(function(){
  const composer = document.querySelector('div[role="textbox"]#prompt-textarea, div[role="textbox"].ProseMirror, textarea#prompt-textarea');
  const login = !!document.querySelector('a[href*="/auth/login"], a[href*="/login"], button[data-testid*="login"]');
  return { ready: !!composer, loginVisible: login, url: location.href };
})()
'@
    do {
        try {
            $value = Invoke-JsValue -WebSocket $WebSocket -Expression $expression -TimeoutSec 5
            if ($value.ready) { return $value }
        } catch { }
        Start-Sleep -Milliseconds 500
    } while ([DateTime]::UtcNow -lt $deadline)
    return $null
}

function Focus-And-InsertPrompt {
    param([System.Net.WebSockets.ClientWebSocket]$WebSocket, [string]$Text)
    $focus = Invoke-JsValue -WebSocket $WebSocket -Expression @'
(function(){
  const el = document.querySelector('div[role="textbox"]#prompt-textarea, div[role="textbox"].ProseMirror, textarea#prompt-textarea');
  if (!el) return {ok:false};
  el.focus();
  return {ok:true, tag:el.tagName, contenteditable:el.getAttribute('contenteditable')};
})()
'@
    if (-not $focus.ok) { throw "ChatGPT composer could not be focused." }

    foreach ($event in @(
        @{ type = "rawKeyDown"; key = "a"; code = "KeyA"; windowsVirtualKeyCode = 65; modifiers = 2 },
        @{ type = "keyUp"; key = "a"; code = "KeyA"; windowsVirtualKeyCode = 65; modifiers = 2 },
        @{ type = "rawKeyDown"; key = "Backspace"; code = "Backspace"; windowsVirtualKeyCode = 8 },
        @{ type = "keyUp"; key = "Backspace"; code = "Backspace"; windowsVirtualKeyCode = 8 }
    )) {
        [void](Invoke-Cdp -WebSocket $WebSocket -Method "Input.dispatchKeyEvent" -Params $event)
    }
    Start-Sleep -Milliseconds 100
    [void](Invoke-Cdp -WebSocket $WebSocket -Method "Input.insertText" -Params @{ text = $Text })
}

function Click-Send {
    param([System.Net.WebSockets.ClientWebSocket]$WebSocket)
    $expression = @'
(function(){
  const selectors = [
    'button[aria-label*="Send" i]:not([data-testid="stop-button"])',
    'button[data-testid="send-button"]',
    'form:has(#prompt-textarea) button[type="submit"]',
    'form:has(.ProseMirror) button[type="submit"]'
  ];
  for (const selector of selectors) {
    const button = document.querySelector(selector);
    if (button && !button.disabled) {
      button.click();
      return {clicked:true, selector};
    }
  }
  return {clicked:false};
})()
'@
    return Invoke-JsValue -WebSocket $WebSocket -Expression $expression
}

function Get-AssistantState {
    param([System.Net.WebSockets.ClientWebSocket]$WebSocket)
    $expression = @'
(function(){
  const nodes = Array.from(document.querySelectorAll('[data-message-author-role="assistant"]'));
  const latest = nodes.length ? nodes[nodes.length - 1] : null;
  const text = latest ? (latest.innerText || latest.textContent || '') : '';
  const stop = !!document.querySelector('button[data-testid="stop-button"], button[aria-label*="Stop" i]');
  return { text, generating: stop, assistantCount: nodes.length, url: location.href };
})()
'@
    return Invoke-JsValue -WebSocket $WebSocket -Expression $expression -TimeoutSec 8
}

function Pump-OneEvent([System.Net.WebSockets.ClientWebSocket]$WebSocket, [int]$TimeoutMs = 500) {
    $message = Receive-CdpJson -WebSocket $WebSocket -TimeoutMs $TimeoutMs
    if (-not $message) { return $null }
    if ($message.method) { Add-CdpEvent $message; return $message }
    return $message
}

$report = [ordered]@{
    ok = $false
    stage = "cdp-github-flow"
    classification = "NOT_STARTED"
    request = [ordered]@{
        prompt_starts_with_github = $Prompt.TrimStart().StartsWith("@GitHub", [StringComparison]::OrdinalIgnoreCase)
        direct_backend_submit_used = $false
        sentinel_or_proof_fabricated = $false
        network_headers_logged = $false
    }
    evidence = [ordered]@{}
    raw_secrets_included = $false
}

$ws = $null
try {
    if (-not $report.request.prompt_starts_with_github) {
        throw "Prompt must begin with @GitHub for this probe."
    }

    if (-not $NoLaunch) {
        $chrome = Find-ChromeExe
        Start-ProbeChrome -ChromeExe $chrome -Profile $ChromeProfile -Port $CdpPort -Url $ChatUrl
    }
    [void](Wait-CdpReady -Port $CdpPort -TimeoutSec 25)
    $target = New-ChatTarget -Port $CdpPort -Url $ChatUrl
    if (-not $target.webSocketDebuggerUrl) { throw "No page websocket debugger URL was returned by Chrome." }

    $ws = [System.Net.WebSockets.ClientWebSocket]::new()
    $ws.ConnectAsync([Uri]$target.webSocketDebuggerUrl, [Threading.CancellationToken]::None).GetAwaiter().GetResult()
    $report.evidence.cdp_connected = $true
    Write-ProbeLog "Connected to Chrome page target through CDP."

    [void](Invoke-Cdp -WebSocket $ws -Method "Page.enable")
    [void](Invoke-Cdp -WebSocket $ws -Method "Runtime.enable")
    [void](Invoke-Cdp -WebSocket $ws -Method "Network.enable" -Params @{ maxPostDataSize = 4194304 })

    [void](Invoke-Cdp -WebSocket $ws -Method "Page.navigate" -Params @{ url = $ChatUrl })
    $composer = Wait-Composer -WebSocket $ws -TimeoutSec 120
    if (-not $composer) {
        $report.classification = "BLOCKED_AUTHENTICATION_OR_COMPOSER"
        $report.evidence.composer_ready = $false
        throw "ChatGPT composer did not become ready. Complete login in the dedicated Chrome profile, then rerun with -NoLaunch."
    }
    $report.evidence.composer_ready = $true
    Write-ProbeLog "Composer ready; inserting @GitHub prompt through CDP Input.insertText."

    [void](Take-CdpEvents)
    Focus-And-InsertPrompt -WebSocket $ws -Text $Prompt
    $report.evidence.input_insert_text_used = $true

    $contextEvidence = $null
    $mentionDeadline = [DateTime]::UtcNow.AddSeconds($MentionTimeoutSec)
    do {
        foreach ($event in (Take-CdpEvents)) {
            $candidate = Inspect-GitHubContextChange $event
            if ($candidate -and $candidate.connector_hint_present -and $candidate.partial_query_starts_with_github) {
                $contextEvidence = $candidate
                break
            }
        }
        if ($contextEvidence) { break }
        $incoming = Pump-OneEvent -WebSocket $ws -TimeoutMs 500
        if ($incoming -and $incoming.method) {
            $candidate = Inspect-GitHubContextChange $incoming
            if ($candidate -and $candidate.connector_hint_present -and $candidate.partial_query_starts_with_github) {
                $contextEvidence = $candidate
                break
            }
        }
    } while ([DateTime]::UtcNow -lt $mentionDeadline)

    if (-not $contextEvidence) {
        $report.classification = "CDP_GITHUB_MENTION_NOT_RESOLVED"
        $report.evidence.github_context_change_prepare = $false
        Write-ProbeLog "@GitHub was not materialized as a connector context change; Send will NOT be clicked."
    } else {
        $report.evidence.github_context_change_prepare = $true
        $report.evidence.connector_hint_present = [bool]$contextEvidence.connector_hint_present
        $report.evidence.partial_query_starts_with_github = [bool]$contextEvidence.partial_query_starts_with_github
        $report.evidence.context_prepare_state = $contextEvidence.client_prepare_state
        $report.evidence.context_prepare_dispatch = $contextEvidence.client_prepare_dispatch
        Write-ProbeLog "GitHub connector context change observed; clicking the real ChatGPT Send button."

        [void](Take-CdpEvents)
        $send = Click-Send -WebSocket $ws
        if (-not $send.clicked) {
            $report.classification = "CDP_SEND_BUTTON_NOT_READY"
            $report.evidence.send_clicked = $false
        } else {
            $report.evidence.send_clicked = $true
            $finalRequest = $null
            $finalStatus = $null
            $networkDeadline = [DateTime]::UtcNow.AddSeconds(45)
            do {
                foreach ($event in (Take-CdpEvents)) {
                    if (-not $finalRequest) {
                        $candidate = Inspect-FinalSubmitRequest $event
                        if ($candidate) { $finalRequest = $candidate }
                    }
                    if ($finalRequest -and $null -eq $finalStatus) {
                        $status = Inspect-ResponseStatus $event $finalRequest.request_id
                        if ($null -ne $status) { $finalStatus = $status }
                    }
                }
                if ($finalRequest -and $null -ne $finalStatus) { break }
                [void](Pump-OneEvent -WebSocket $ws -TimeoutMs 500)
            } while ([DateTime]::UtcNow -lt $networkDeadline)

            if (-not $finalRequest) {
                $report.classification = "CDP_FINAL_SUBMIT_NOT_OBSERVED"
                $report.evidence.final_submit_observed = $false
            } else {
                $report.evidence.final_submit_observed = $true
                $report.evidence.final_top_level_connector_hint = [bool]$finalRequest.top_level_connector_hint
                $report.evidence.final_message_connector_hint = [bool]$finalRequest.message_connector_hint
                $report.evidence.final_ecosystem_mention = [bool]$finalRequest.ecosystem_mention_present
                $report.evidence.final_client_prepare_state = $finalRequest.client_prepare_state
                $report.evidence.final_http_status = $finalStatus

                if ($finalStatus -ne 200) {
                    $report.classification = "CDP_FINAL_SUBMIT_REJECTED"
                } else {
                    Write-ProbeLog "Native frontend submit returned HTTP 200; waiting for assistant completion through the DOM."
                    $assistant = $null
                    $responseDeadline = [DateTime]::UtcNow.AddSeconds($ResponseTimeoutSec)
                    do {
                        try { $assistant = Get-AssistantState -WebSocket $ws } catch { $assistant = $null }
                        if ($assistant -and -not $assistant.generating -and [string]$assistant.text -match "POWERPACK_GITHUB_TOOL_OK") {
                            break
                        }
                        Start-Sleep -Milliseconds 750
                    } while ([DateTime]::UtcNow -lt $responseDeadline)

                    $text = if ($assistant) { [string]$assistant.text } else { "" }
                    $marker = $text.Contains("POWERPACK_GITHUB_TOOL_OK")
                    $complete = [bool]($assistant -and -not $assistant.generating -and $marker)
                    $report.evidence.assistant_response_complete = $complete
                    $report.evidence.marker_seen = $marker
                    $report.evidence.assistant_text_length = $text.Length
                    if ($IncludeAssistantText) { $report.evidence.assistant_text = $text }

                    $nativeEvidence = [bool](
                        $finalRequest.top_level_connector_hint -and
                        $finalRequest.message_connector_hint -and
                        $finalRequest.ecosystem_mention_present -and
                        $finalStatus -eq 200
                    )
                    if ($nativeEvidence -and $complete) {
                        $report.ok = $true
                        $report.classification = "CDP_GITHUB_FLOW_ACCEPTED"
                    } else {
                        $report.classification = "CDP_RESPONSE_INCOMPLETE_OR_MARKER_MISSING"
                    }
                }
            }
        }
    }
} catch {
    if ($report.classification -eq "NOT_STARTED") {
        $report.classification = "CDP_PROBE_ERROR"
    }
    $report.error = [string]$_.Exception.Message
} finally {
    if ($ws) {
        try {
            if ($ws.State -eq [System.Net.WebSockets.WebSocketState]::Open) {
                $ws.CloseAsync(
                    [System.Net.WebSockets.WebSocketCloseStatus]::NormalClosure,
                    "probe complete",
                    [Threading.CancellationToken]::None
                ).GetAwaiter().GetResult()
            }
        } catch { }
        $ws.Dispose()
    }
}

$rendered = $report | ConvertTo-Json -Depth 20
if ($Output) {
    $parent = Split-Path -Parent $Output
    if ($parent) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
    [IO.File]::WriteAllText($Output, $rendered + [Environment]::NewLine, [Text.UTF8Encoding]::new($false))
}
[Console]::Out.WriteLine($rendered)
if ($report.ok) { exit 0 }
exit 2
