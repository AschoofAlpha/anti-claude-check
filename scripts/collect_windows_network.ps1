[CmdletBinding()]
param(
    [string]$ConfigDir = (Join-Path $env:APPDATA 'io.github.clash-verge-rev.clash-verge-rev'),
    [string]$PolicyGroupPattern = '(?i)(OpenAI|Claude|Anthropic|ChatGPT|Gemini|(?:^|[^A-Za-z0-9])AI(?:$|[^A-Za-z0-9]))',
    [switch]$SelfTest
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'

function Get-YamlScalar {
    param(
        [AllowEmptyString()][string]$Text,
        [Parameter(Mandatory)][string]$KeyPattern
    )

    $match = [regex]::Match($Text, "(?im)^\s*(?:$KeyPattern)\s*:\s*(?<value>[^#\r\n]+?)\s*$")
    if (-not $match.Success) {
        return $null
    }

    return $match.Groups['value'].Value.Trim().Trim("'`"")
}

function ConvertTo-NullableBoolean {
    param([AllowNull()][string]$Value)

    if ($null -eq $Value) {
        return $null
    }
    if ($Value -match '^(?i:true|yes|on|1)$') {
        return $true
    }
    if ($Value -match '^(?i:false|no|off|0)$') {
        return $false
    }
    return $null
}

function Get-YamlBlock {
    param(
        [AllowEmptyString()][string]$Text,
        [Parameter(Mandatory)][string]$Section
    )

    $pattern = "(?ms)^$([regex]::Escape($Section))\s*:\s*(?:#.*)?\r?\n(?<body>(?:(?:^[ \t]+.*|^\s*)\r?\n?)*)"
    $match = [regex]::Match($Text, $pattern)
    if (-not $match.Success) {
        return ''
    }
    return $match.Groups['body'].Value
}

function Read-TextIfPresent {
    param([Parameter(Mandatory)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return ''
    }
    return [System.IO.File]::ReadAllText($Path)
}

function Read-JsonIfPresent {
    param([Parameter(Mandatory)][string]$Path)

    $text = Read-TextIfPresent -Path $Path
    if (-not $text) {
        return $null
    }
    try {
        return $text | ConvertFrom-Json
    }
    catch {
        return $null
    }
}

function Get-PropertyValue {
    param(
        [AllowNull()]$Object,
        [Parameter(Mandatory)][string]$Name
    )

    if ($null -eq $Object) {
        return $null
    }
    $property = $Object.PSObject.Properties[$Name]
    if ($null -eq $property) {
        return $null
    }
    return $property.Value
}

function Get-BrowserWebRtcAudit {
    param(
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][string]$UserDataPath,
        [Parameter(Mandatory)][string[]]$ExecutablePaths,
        [Parameter(Mandatory)][string]$ProcessName,
        [Parameter(Mandatory)][string]$PolicyRegistryPath
    )

    $localState = Read-JsonIfPresent -Path (Join-Path $UserDataPath 'Local State')
    $localStateProfile = Get-PropertyValue -Object $localState -Name 'profile'
    $localStateIntl = Get-PropertyValue -Object $localState -Name 'intl'
    $lastUsedProfile = Get-PropertyValue -Object $localStateProfile -Name 'last_used'
    $applicationLocale = Get-PropertyValue -Object $localStateIntl -Name 'app_locale'
    $profiles = @()
    $profileAudits = @()
    $extensionMatches = @()
    if (Test-Path -LiteralPath $UserDataPath -PathType Container) {
        $profiles = @(Get-ChildItem -LiteralPath $UserDataPath -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -eq 'Default' -or $_.Name -like 'Profile *' })
        foreach ($profile in $profiles) {
            $preferences = Read-JsonIfPresent -Path (Join-Path $profile.FullName 'Preferences')
            $securePreferences = Read-JsonIfPresent -Path (Join-Path $profile.FullName 'Secure Preferences')
            $intl = Get-PropertyValue -Object $preferences -Name 'intl'
            $webrtc = Get-PropertyValue -Object $preferences -Name 'webrtc'
            $extensions = Get-PropertyValue -Object $securePreferences -Name 'extensions'
            $extensionSettings = Get-PropertyValue -Object $extensions -Name 'settings'
            if ($null -eq $extensionSettings) {
                $extensions = Get-PropertyValue -Object $preferences -Name 'extensions'
                $extensionSettings = Get-PropertyValue -Object $extensions -Name 'settings'
            }

            $profileAudits += [pscustomobject][ordered]@{
                Profile = $profile.Name
                AcceptLanguages = Get-PropertyValue -Object $intl -Name 'accept_languages'
                SelectedLanguages = Get-PropertyValue -Object $intl -Name 'selected_languages'
                WebRtcIpHandlingPreference = Get-PropertyValue -Object $webrtc -Name 'ip_handling_policy'
            }

            $extensionRoot = Join-Path $profile.FullName 'Extensions'
            $extensionDirs = @(Get-ChildItem -LiteralPath $extensionRoot -Directory -ErrorAction SilentlyContinue)
            foreach ($extensionDir in $extensionDirs) {
                $versionDir = Get-ChildItem -LiteralPath $extensionDir.FullName -Directory -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
                if ($null -eq $versionDir) {
                    continue
                }
                $manifestFile = Get-Item -LiteralPath (Join-Path $versionDir.FullName 'manifest.json') -ErrorAction SilentlyContinue
                if ($null -eq $manifestFile) {
                    continue
                }
                try {
                    $manifestText = [System.IO.File]::ReadAllText($manifestFile.FullName)
                    $manifest = $manifestText | ConvertFrom-Json
                    $searchText = $manifestText
                    $defaultLocaleProperty = $manifest.PSObject.Properties['default_locale']
                    if ($null -ne $defaultLocaleProperty) {
                        $messagesPath = Join-Path $manifestFile.DirectoryName "_locales\$($defaultLocaleProperty.Value)\messages.json"
                        $searchText += Read-TextIfPresent -Path $messagesPath
                    }
                    if ($searchText -notmatch '(?i)web[ -]?rtc|rtc[- _]?leak') {
                        continue
                    }
                    $nameProperty = $manifest.PSObject.Properties['name']
                    $displayName = if ($null -ne $nameProperty) { [string]$nameProperty.Value } else { 'Unknown' }
                    $extensionId = $extensionDir.Name
                    $extensionState = Get-PropertyValue -Object $extensionSettings -Name $extensionId
                    $state = Get-PropertyValue -Object $extensionState -Name 'state'
                    $disableReasons = @(Get-PropertyValue -Object $extensionState -Name 'disable_reasons')
                    $enabled = $null
                    $enabledAssessment = 'Unknown'
                    if ($null -ne $state) {
                        $enabled = ([int]$state -eq 1) -and ($disableReasons.Count -eq 0)
                        $enabledAssessment = if ($enabled) { 'Enabled' } else { 'Disabled' }
                    }
                    elseif ($null -ne $extensionState -and $disableReasons.Count -eq 0) {
                        $enabledAssessment = 'LikelyEnabled'
                    }
                    $extensionMatches += [pscustomobject][ordered]@{
                        Profile = $profile.Name
                        ExtensionId = $extensionId
                        Name = $displayName
                        Enabled = $enabled
                        EnabledAssessment = $enabledAssessment
                        DisableReasons = $disableReasons
                    }
                }
                catch {
                    continue
                }
            }
        }
    }

    $processLanguages = @()
    try {
        $browserProcesses = @(Get-CimInstance Win32_Process -Filter "Name='$ProcessName'" -ErrorAction SilentlyContinue)
        foreach ($process in $browserProcesses) {
            $languageMatch = [regex]::Match([string]$process.CommandLine, '(?i)(?:^|\s)--lang(?:=|\s+)(?:"(?<language>[^"]+)"|(?<language>\S+))')
            if ($languageMatch.Success) {
                $processLanguages += $languageMatch.Groups['language'].Value
            }
        }
    }
    catch {
        $processLanguages = @()
    }

    $managedPolicies = @()
    foreach ($scope in @('HKCU','HKLM')) {
        $registryPath = "${scope}:\SOFTWARE\Policies\$PolicyRegistryPath"
        $policy = Get-ItemProperty -LiteralPath $registryPath -ErrorAction SilentlyContinue
        if ($null -eq $policy) {
            continue
        }
        $managedPolicies += [pscustomobject][ordered]@{
            Scope = $scope
            WebRtcIPHandling = Get-PropertyValue -Object $policy -Name 'WebRtcIPHandling'
            WebRtcIPHandlingUrl = Get-PropertyValue -Object $policy -Name 'WebRtcIPHandlingUrl'
            WebRtcLocalhostIpHandling = Get-PropertyValue -Object $policy -Name 'WebRtcLocalhostIpHandling'
        }
    }

    $installed = $false
    $browserVersion = $null
    foreach ($path in $ExecutablePaths) {
        if ($path -and (Test-Path -LiteralPath $path -PathType Leaf)) {
            $installed = $true
            $browserVersion = (Get-Item -LiteralPath $path).VersionInfo.ProductVersion
            break
        }
    }

    return [pscustomobject][ordered]@{
        Name = $Name
        Installed = $installed
        Version = $browserVersion
        LastUsedProfile = $lastUsedProfile
        ApplicationLocale = $applicationLocale
        ProfilesChecked = $profiles.Count
        Profiles = $profileAudits
        ProcessLanguages = @($processLanguages | Sort-Object -Unique)
        ManagedWebRtcPolicies = $managedPolicies
        RestrictiveWebRtcPolicyDetected = (($managedPolicies | Out-String) -match 'disable_non_proxied_udp')
        WebRtcRelatedExtensionDetected = $extensionMatches.Count -gt 0
        WebRtcRelatedExtensions = @($extensionMatches | Sort-Object Profile,ExtensionId -Unique)
    }
}

function Get-DnsUpstreamAudit {
    param([AllowEmptyString()][string]$DnsConfig)

    $upstreams = @()
    $uriMatches = [regex]::Matches($DnsConfig, "(?im)(?<scheme>https|tls|quic|h3)://(?<host>[^/\s#'`"]+)")
    foreach ($uriMatch in $uriMatches) {
        $upstreams += [pscustomobject][ordered]@{
            Scheme = $uriMatch.Groups['scheme'].Value.ToLowerInvariant()
            Host = $uriMatch.Groups['host'].Value.ToLowerInvariant()
        }
    }
    return @($upstreams | Sort-Object Scheme,Host -Unique)
}

function Find-ByteSequence {
    param(
        [Parameter(Mandatory)][byte[]]$Data,
        [Parameter(Mandatory)][byte[]]$Needle,
        [int]$Start = 0
    )

    for ($index = $Start; $index -le $Data.Length - $Needle.Length; $index++) {
        $found = $true
        for ($offset = 0; $offset -lt $Needle.Length; $offset++) {
            if ($Data[$index + $offset] -ne $Needle[$offset]) {
                $found = $false
                break
            }
        }
        if ($found) {
            return $index
        }
    }
    return -1
}

function ConvertFrom-HttpChunkedBody {
    param([Parameter(Mandatory)][byte[]]$Body)

    $crlf = [byte[]](13,10)
    $position = 0
    $output = [System.IO.MemoryStream]::new()
    try {
        while ($true) {
            $lineEnd = Find-ByteSequence -Data $Body -Needle $crlf -Start $position
            if ($lineEnd -lt 0) { throw 'Invalid chunk-size line.' }
            $sizeText = [Text.Encoding]::ASCII.GetString($Body, $position, $lineEnd - $position).Split(';')[0]
            $size = 0
            if (-not [int]::TryParse($sizeText, [Globalization.NumberStyles]::HexNumber, [Globalization.CultureInfo]::InvariantCulture, [ref]$size)) {
                throw 'Invalid chunk size.'
            }
            $position = $lineEnd + 2
            if ($size -eq 0) { break }
            if ($position + $size + 2 -gt $Body.Length) { throw 'Chunk exceeds response body.' }
            $output.Write($Body, $position, $size)
            $position += $size
            if ($Body[$position] -ne 13 -or $Body[$position + 1] -ne 10) { throw 'Missing chunk terminator.' }
            $position += 2
        }
        return $output.ToArray()
    }
    finally {
        $output.Dispose()
    }
}

function Get-MihomoNamedPipeProxies {
    param(
        [Parameter(Mandatory)][string]$PipePath,
        [AllowEmptyString()][string]$Secret
    )

    $pipeName = $PipePath -replace '^\\\\\.\\pipe\\', ''
    if (-not $pipeName -or $pipeName -match '[\\/]') { throw 'Unsupported named-pipe path.' }
    $pipe = [System.IO.Pipes.NamedPipeClientStream]::new('.', $pipeName, [System.IO.Pipes.PipeDirection]::InOut, [System.IO.Pipes.PipeOptions]::Asynchronous)
    $memory = [System.IO.MemoryStream]::new()
    try {
        $pipe.Connect(3000)
        $authorization = if ($Secret) { "Authorization: Bearer $Secret`r`n" } else { '' }
        $request = [Text.Encoding]::ASCII.GetBytes("GET /proxies HTTP/1.1`r`nHost: localhost`r`n${authorization}Connection: close`r`n`r`n")
        $pipe.Write($request, 0, $request.Length)
        $pipe.Flush()

        $buffer = New-Object byte[] 8192
        while ($true) {
            $readTask = $pipe.ReadAsync($buffer, 0, $buffer.Length)
            if (-not $readTask.Wait(5000)) { throw 'Named-pipe response timed out.' }
            $count = $readTask.Result
            if ($count -eq 0) { break }
            $memory.Write($buffer, 0, $count)
            if ($memory.Length -gt 8MB) { throw 'Named-pipe response exceeded 8 MB.' }
        }

        $response = $memory.ToArray()
        $headerEnd = Find-ByteSequence -Data $response -Needle ([byte[]](13,10,13,10))
        if ($headerEnd -lt 0) { throw 'Invalid named-pipe HTTP response.' }
        $headers = [Text.Encoding]::ASCII.GetString($response, 0, $headerEnd)
        if ($headers -notmatch '^HTTP/\S+\s+200\b') { throw 'Mihomo named-pipe request failed.' }
        $body = New-Object byte[] ($response.Length - $headerEnd - 4)
        [Array]::Copy($response, $headerEnd + 4, $body, 0, $body.Length)
        if ($headers -match '(?im)^Transfer-Encoding:\s*chunked') {
            $body = ConvertFrom-HttpChunkedBody -Body $body
        }
        $json = [Text.Encoding]::UTF8.GetString($body) | ConvertFrom-Json
        return Get-PropertyValue -Object $json -Name 'proxies'
    }
    finally {
        $memory.Dispose()
        $pipe.Dispose()
    }
}

function Get-MihomoPolicyAudit {
    param(
        [AllowEmptyString()][string]$RuntimeConfig,
        [AllowEmptyString()][string]$ControllerConfig,
        [Parameter(Mandatory)][string]$GroupPattern
    )

    $staticGroups = @()
    $groupMatches = [regex]::Matches($RuntimeConfig, '(?ms)^[ \t]*-[ \t]*name:\s*(?<name>[^\r\n#]+)\r?\n[ \t]+type:\s*(?<type>[^\r\n#]+)')
    foreach ($groupMatch in $groupMatches) {
        $groupName = $groupMatch.Groups['name'].Value.Trim().Trim("'`"")
        if ($groupName -notmatch $GroupPattern) {
            continue
        }
        $staticGroups += [pscustomobject][ordered]@{
            Name = $groupName
            Type = $groupMatch.Groups['type'].Value.Trim().Trim("'`"")
            ReferencedByRule = $RuntimeConfig -match "(?im),\s*$([regex]::Escape($groupName))\s*$"
        }
    }

    $controllerValue = Get-YamlScalar -Text $ControllerConfig -KeyPattern 'external[-_]controller'
    $controllerPipe = Get-YamlScalar -Text ($ControllerConfig + [Environment]::NewLine + $RuntimeConfig) -KeyPattern 'external[-_]controller[-_]pipe'
    $secret = Get-YamlScalar -Text $ControllerConfig -KeyPattern 'secret'
    $controllerReachable = $false
    $controllerSkipped = $false
    $controllerTransport = $null
    $runtimeGroups = @()
    $proxyObjects = $null

    if ($controllerValue) {
        try {
            $controllerUri = if ($controllerValue -match '^https?://') { [uri]$controllerValue } else { [uri]("http://$controllerValue") }
            if ($controllerUri.Host -notin @('127.0.0.1','localhost','0.0.0.0','::1')) {
                $controllerSkipped = $true
            }
            else {
                $hostName = if ($controllerUri.Host -eq '0.0.0.0') { '127.0.0.1' } else { $controllerUri.Host }
                $baseUri = "http://${hostName}:$($controllerUri.Port)"
                $headers = @{}
                if ($secret) {
                    $headers.Authorization = "Bearer $secret"
                }
                $response = Invoke-RestMethod -Uri "$baseUri/proxies" -Headers $headers -Method Get -TimeoutSec 3 -ErrorAction Stop
                $proxyObjects = Get-PropertyValue -Object $response -Name 'proxies'
                $controllerReachable = $null -ne $proxyObjects
                if ($controllerReachable) { $controllerTransport = 'Http' }
            }
        }
        catch {
            $controllerReachable = $false
        }
    }

    if (-not $controllerReachable -and $controllerPipe) {
        try {
            $proxyObjects = Get-MihomoNamedPipeProxies -PipePath $controllerPipe -Secret $secret
            $controllerReachable = $null -ne $proxyObjects
            if ($controllerReachable) { $controllerTransport = 'NamedPipe' }
        }
        catch {
            $controllerReachable = $false
        }
    }

    if ($controllerReachable) {
        $groupNames = @($staticGroups | ForEach-Object Name)
        $groupNames += @($proxyObjects.PSObject.Properties.Name | Where-Object { $_ -match $GroupPattern })
        foreach ($groupName in @($groupNames | Sort-Object -Unique)) {
            $chain = @()
            $seen = @{}
            $currentName = $groupName
            $usesAutomaticSelection = $false
            while ($currentName -and -not $seen.ContainsKey($currentName) -and $chain.Count -lt 12) {
                $seen[$currentName] = $true
                $proxy = Get-PropertyValue -Object $proxyObjects -Name $currentName
                if ($null -eq $proxy) {
                    break
                }
                $type = [string](Get-PropertyValue -Object $proxy -Name 'type')
                $next = [string](Get-PropertyValue -Object $proxy -Name 'now')
                if ($type -match '(?i)URLTest|Fallback|LoadBalance|Smart') {
                    $usesAutomaticSelection = $true
                }
                $chain += [pscustomobject][ordered]@{ Name = $currentName; Type = $type; Selected = $next }
                $currentName = $next
            }
            $staticGroup = $staticGroups | Where-Object Name -eq $groupName | Select-Object -First 1
            $runtimeGroups += [pscustomobject][ordered]@{
                Name = $groupName
                ReferencedByRule = if ($null -ne $staticGroup) { $staticGroup.ReferencedByRule } else { $null }
                UsesAutomaticSelection = $usesAutomaticSelection
                SelectionChain = $chain
            }
        }
    }

    $selectionAssessment = if (-not $controllerReachable -and $staticGroups.Count -eq 0) {
        'MatchedGroupNotFound'
    }
    elseif (-not $controllerReachable) {
        'ManualCheckRequired'
    }
    elseif ($runtimeGroups.Count -eq 0) {
        'MatchedGroupNotFound'
    }
    elseif (@($runtimeGroups | Where-Object UsesAutomaticSelection).Count -gt 0) {
        'AutomaticSelectionDetected'
    }
    else {
        'FixedSelection'
    }

    return [pscustomobject][ordered]@{
        Pattern = $GroupPattern
        StaticGroups = $staticGroups
        LocalControllerConfigured = [bool]$controllerValue
        NamedPipeControllerConfigured = [bool]$controllerPipe
        LocalControllerReachable = $controllerReachable
        NonLocalControllerSkipped = $controllerSkipped
        ControllerTransport = $controllerTransport
        SelectionAssessment = $selectionAssessment
        RuntimeGroups = $runtimeGroups
    }
}

if ($SelfTest) {
    $sample = @'
mode: rule
allow-lan: false
mixed-port: 7897
tun:
  strict-route: true
'@
    if ((Get-YamlScalar -Text $sample -KeyPattern 'mode') -ne 'rule') { throw 'Scalar parsing failed.' }
    if ((ConvertTo-NullableBoolean (Get-YamlScalar -Text $sample -KeyPattern 'allow-lan')) -ne $false) { throw 'Boolean parsing failed.' }
    if ((Get-YamlScalar -Text $sample -KeyPattern 'mixed[-_]port') -ne '7897') { throw 'Hyphenated key parsing failed.' }
    $sampleTun = Get-YamlBlock -Text $sample -Section 'tun'
    if ((ConvertTo-NullableBoolean (Get-YamlScalar -Text $sampleTun -KeyPattern 'strict-route')) -ne $true) { throw 'Section parsing failed.' }
    $extensionSample = '{"name":"WebRTC Leak Test","description":"Controls Web RTC behavior"}'
    if ($extensionSample -notmatch '(?i)web[ -]?rtc|rtc[- _]?leak') { throw 'WebRTC extension matching failed.' }
    $dnsSample = 'nameserver: [https://dns.example/dns-query, tls://resolver.example]'
    if ((Get-DnsUpstreamAudit -DnsConfig $dnsSample).Count -ne 2) { throw 'DNS upstream parsing failed.' }
    if ('Hawaiian residential' -match $PolicyGroupPattern) { throw 'Policy-group pattern produced a false positive.' }
    if ('group AI service' -notmatch $PolicyGroupPattern) { throw 'Policy-group pattern missed an AI group.' }
    $unicodeName = ([char]0x65E5).ToString() + ([char]0x672C)
    $chunkText = '{"name":"' + $unicodeName + '"}'
    $chunkPayload = [Text.Encoding]::UTF8.GetBytes($chunkText)
    $chunkStream = [System.IO.MemoryStream]::new()
    try {
        $chunkPrefix = [Text.Encoding]::ASCII.GetBytes($chunkPayload.Length.ToString('X') + "`r`n")
        $chunkSuffix = [Text.Encoding]::ASCII.GetBytes("`r`n0`r`n`r`n")
        $chunkStream.Write($chunkPrefix, 0, $chunkPrefix.Length)
        $chunkStream.Write($chunkPayload, 0, $chunkPayload.Length)
        $chunkStream.Write($chunkSuffix, 0, $chunkSuffix.Length)
        $decodedChunk = ConvertFrom-HttpChunkedBody -Body $chunkStream.ToArray()
        if ([Text.Encoding]::UTF8.GetString($decodedChunk) -ne $chunkText) { throw 'Chunked UTF-8 decoding failed.' }
    }
    finally {
        $chunkStream.Dispose()
    }
    'Self-test passed.'
    return
}

$appConfigPath = Join-Path $ConfigDir 'config.yaml'
$runtimeConfigPath = Join-Path $ConfigDir 'clash-verge.yaml'
$appConfig = Read-TextIfPresent -Path $appConfigPath
$runtimeConfig = Read-TextIfPresent -Path $runtimeConfigPath
$combinedConfig = $appConfig + [Environment]::NewLine + $runtimeConfig
$tunConfig = Get-YamlBlock -Text $combinedConfig -Section 'tun'
$dnsConfig = Get-YamlBlock -Text $runtimeConfig -Section 'dns'
$dnsUpstreams = Get-DnsUpstreamAudit -DnsConfig $dnsConfig

$mixedPortText = Get-YamlScalar -Text $combinedConfig -KeyPattern 'mixed[-_]port'
$mixedPort = 7897
if ($mixedPortText -match '^\d{1,5}$') {
    $mixedPort = [int]$mixedPortText
}

$portListening = $false
if (Get-Command Get-NetTCPConnection -ErrorAction SilentlyContinue) {
    $portListening = $null -ne (Get-NetTCPConnection -State Listen -LocalPort $mixedPort -ErrorAction SilentlyContinue | Select-Object -First 1)
}

$internetSettings = Get-ItemProperty -LiteralPath 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -ErrorAction SilentlyContinue
$proxyEnabled = $false
$proxyPointsToLoopback = $false
if ($null -ne $internetSettings) {
    $proxyEnabledProperty = $internetSettings.PSObject.Properties['ProxyEnable']
    $proxyServerProperty = $internetSettings.PSObject.Properties['ProxyServer']
    if ($null -ne $proxyEnabledProperty) {
        $proxyEnabled = [bool]$proxyEnabledProperty.Value
    }
    $proxyServer = ''
    if ($null -ne $proxyServerProperty) {
        $proxyServer = [string]$proxyServerProperty.Value
    }
    $proxyPointsToLoopback = $proxyServer -match '(?i)(127\.0\.0\.1|localhost|\[::1\])'
}

$teredo = [ordered]@{ Available = $false; Type = $null; Disabled = $null }
if (Get-Command Get-NetTeredoConfiguration -ErrorAction SilentlyContinue) {
    $teredoConfig = Get-NetTeredoConfiguration -ErrorAction SilentlyContinue
    if ($null -ne $teredoConfig) {
        $teredo.Available = $true
        $teredo.Type = [string]$teredoConfig.Type
        $teredo.Disabled = $teredo.Type -match '(?i)disabled'
    }
}

$isAdministrator = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
$deviceContext = [ordered]@{
    OperatingSystem = $null
    LogicalProcessors = $null
    PhysicalMemoryGiB = $null
    Graphics = @()
}
try {
    $operatingSystem = Get-CimInstance Win32_OperatingSystem -ErrorAction SilentlyContinue
    if ($null -ne $operatingSystem) {
        $deviceContext.OperatingSystem = [pscustomobject][ordered]@{
            Caption = $operatingSystem.Caption
            Version = $operatingSystem.Version
            BuildNumber = $operatingSystem.BuildNumber
            Architecture = $operatingSystem.OSArchitecture
        }
    }
    $computerSystem = Get-CimInstance Win32_ComputerSystem -ErrorAction SilentlyContinue
    if ($null -ne $computerSystem) {
        $deviceContext.LogicalProcessors = $computerSystem.NumberOfLogicalProcessors
        $deviceContext.PhysicalMemoryGiB = [math]::Round([double]$computerSystem.TotalPhysicalMemory / 1GB, 1)
    }
    $graphicsControllers = @(Get-CimInstance Win32_VideoController -ErrorAction SilentlyContinue)
    foreach ($graphicsController in $graphicsControllers) {
        $deviceContext.Graphics += [pscustomobject][ordered]@{
            Name = $graphicsController.Name
            DriverVersion = $graphicsController.DriverVersion
            CurrentResolution = if ($graphicsController.CurrentHorizontalResolution -and $graphicsController.CurrentVerticalResolution) {
                "$($graphicsController.CurrentHorizontalResolution)x$($graphicsController.CurrentVerticalResolution)"
            }
            else {
                $null
            }
        }
    }
}
catch {
    $deviceContext = [ordered]@{ OperatingSystem = $null; LogicalProcessors = $null; PhysicalMemoryGiB = $null; Graphics = @() }
}
$serviceMatches = @()
try {
    $services = @(Get-CimInstance Win32_Service -ErrorAction SilentlyContinue | Where-Object {
        $_.Name -match '(?i)clash|mihomo|verge' -or $_.DisplayName -match '(?i)clash|mihomo|verge' -or $_.PathName -match '(?i)clash|mihomo|verge'
    })
    foreach ($service in $services) {
        $serviceMatches += [pscustomobject][ordered]@{
            Name = $service.Name
            DisplayName = $service.DisplayName
            State = $service.State
            StartMode = $service.StartMode
        }
    }
}
catch {
    $serviceMatches = @()
}

$userLanguages = @()
if (Get-Command Get-WinUserLanguageList -ErrorAction SilentlyContinue) {
    $languageList = Get-WinUserLanguageList
    foreach ($language in $languageList) {
        $userLanguages += [string]$language.LanguageTag
    }
}
$systemLocale = if (Get-Command Get-WinSystemLocale -ErrorAction SilentlyContinue) { (Get-WinSystemLocale).Name } else { $null }
$uiLanguageOverride = if (Get-Command Get-WinUILanguageOverride -ErrorAction SilentlyContinue) { [string](Get-WinUILanguageOverride) } else { $null }
$homeGeoId = $null
$homeLocationName = $null
if (Get-Command Get-WinHomeLocation -ErrorAction SilentlyContinue) {
    $homeLocation = Get-WinHomeLocation
    $homeGeoId = Get-PropertyValue -Object $homeLocation -Name 'GeoId'
    $homeLocationName = Get-PropertyValue -Object $homeLocation -Name 'HomeLocation'
}

$ipv6Bindings = @()
if ((Get-Command Get-NetAdapter -ErrorAction SilentlyContinue) -and (Get-Command Get-NetAdapterBinding -ErrorAction SilentlyContinue)) {
    $activeAdapters = Get-NetAdapter -ErrorAction SilentlyContinue | Where-Object Status -eq 'Up'
    foreach ($adapter in $activeAdapters) {
        $binding = Get-NetAdapterBinding -Name $adapter.Name -ComponentID ms_tcpip6 -ErrorAction SilentlyContinue
        if ($null -ne $binding) {
            $description = [string]$adapter.InterfaceDescription
            $hardwareInterface = Get-PropertyValue -Object $adapter -Name 'HardwareInterface'
            $classification = if ("$($adapter.Name) $description" -match '(?i)mihomo|clash|wintun|wireguard|tap|vpn') {
                'TunnelOrVpn'
            }
            elseif ($hardwareInterface -eq $true) {
                'Physical'
            }
            else {
                'VirtualOrOther'
            }
            $ipv6Bindings += [pscustomobject][ordered]@{
                Interface = $adapter.Name
                Description = $description
                Classification = $classification
                Enabled = [bool]$binding.Enabled
                CandidateForIPv6Disable = ($classification -eq 'Physical' -and [bool]$binding.Enabled)
            }
        }
    }
}

$localDns = @()
if (Get-Command Get-DnsClientServerAddress -ErrorAction SilentlyContinue) {
    $dnsRows = Get-DnsClientServerAddress -ErrorAction SilentlyContinue | Where-Object { $_.ServerAddresses.Count -gt 0 }
    foreach ($row in $dnsRows) {
        $localDns += [ordered]@{ Interface = $row.InterfaceAlias; Family = [string]$row.AddressFamily; Servers = @($row.ServerAddresses) }
    }
}

$proxyEnvironmentVariables = @()
foreach ($scope in @('Process','User','Machine')) {
    foreach ($variableName in @('HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','NO_PROXY')) {
        $value = [Environment]::GetEnvironmentVariable($variableName, $scope)
        if ($value) {
            $proxyEnvironmentVariables += [pscustomobject][ordered]@{ Scope = $scope; Name = $variableName; Present = $true }
        }
    }
}

function Get-EnvironmentValueRows {
    param([Parameter(Mandatory = $true)][string]$Name)
    $rows = @()
    foreach ($scope in @('Process','User','Machine')) {
        $value = [Environment]::GetEnvironmentVariable($Name, $scope)
        if ($null -ne $value -and $value -ne '') {
            $rows += [pscustomobject][ordered]@{ Scope = $scope; Value = $value }
        }
    }
    return $rows
}

$claudeDisableTelemetry = @(Get-EnvironmentValueRows -Name 'DISABLE_TELEMETRY')
$claudeDisableErrorReporting = @(Get-EnvironmentValueRows -Name 'DISABLE_ERROR_REPORTING')
$claudeDisableNonessentialTraffic = @(Get-EnvironmentValueRows -Name 'CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC')

$cloudProviders = [ordered]@{
    UseBedrock = [bool]([Environment]::GetEnvironmentVariable('CLAUDE_CODE_USE_BEDROCK', 'Process') -or [Environment]::GetEnvironmentVariable('CLAUDE_CODE_USE_BEDROCK', 'User') -or [Environment]::GetEnvironmentVariable('CLAUDE_CODE_USE_BEDROCK', 'Machine'))
    UseVertex = [bool]([Environment]::GetEnvironmentVariable('CLAUDE_CODE_USE_VERTEX', 'Process') -or [Environment]::GetEnvironmentVariable('CLAUDE_CODE_USE_VERTEX', 'User') -or [Environment]::GetEnvironmentVariable('CLAUDE_CODE_USE_VERTEX', 'Machine'))
    HasAnthropicApiKey = [bool]([Environment]::GetEnvironmentVariable('ANTHROPIC_API_KEY', 'Process') -or [Environment]::GetEnvironmentVariable('ANTHROPIC_API_KEY', 'User') -or [Environment]::GetEnvironmentVariable('ANTHROPIC_API_KEY', 'Machine'))
}

$multiClientProcesses = @()
$clientNames = @('sing-box','v2rayN','v2ray','xray','nekobox')
foreach ($cn in $clientNames) {
    $proc = Get-Process -Name $cn -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -ne $proc) {
        $multiClientProcesses += [pscustomobject][ordered]@{ Name = $cn; Running = $true; ProcessId = $proc.Id }
    }
}

$claudeAudit = [ordered]@{
    DisableTelemetryVars = $claudeDisableTelemetry
    DisableTelemetryActive = (@($claudeDisableTelemetry | Where-Object Value -eq '1').Count -gt 0)
    DisableErrorReportingVars = $claudeDisableErrorReporting
    DisableErrorReportingActive = (@($claudeDisableErrorReporting | Where-Object Value -eq '1').Count -gt 0)
    DisableNonessentialTrafficVars = $claudeDisableNonessentialTraffic
    DisableNonessentialTrafficActive = (@($claudeDisableNonessentialTraffic | Where-Object Value -eq '1').Count -gt 0)
    CloudProviders = $cloudProviders
}

$dnsHijackAny53 = $combinedConfig -match "(?im)^\s*-\s*['`"]?any:53['`"]?\s*(?:#.*)?$"
$processRunning = $null -ne (Get-Process -Name 'verge-mihomo','mihomo','clash-meta','clash' -ErrorAction SilentlyContinue | Select-Object -First 1)
$chromeAudit = Get-BrowserWebRtcAudit -Name 'Google Chrome' -UserDataPath (Join-Path $env:LOCALAPPDATA 'Google\Chrome\User Data') -ProcessName 'chrome.exe' -PolicyRegistryPath 'Google\Chrome' -ExecutablePaths @(
    (Join-Path $env:LOCALAPPDATA 'Google\Chrome\Application\chrome.exe'),
    (Join-Path $env:ProgramFiles 'Google\Chrome\Application\chrome.exe'),
    (Join-Path ${env:ProgramFiles(x86)} 'Google\Chrome\Application\chrome.exe')
)
$edgeAudit = Get-BrowserWebRtcAudit -Name 'Microsoft Edge' -UserDataPath (Join-Path $env:LOCALAPPDATA 'Microsoft\Edge\User Data') -ProcessName 'msedge.exe' -PolicyRegistryPath 'Microsoft\Edge' -ExecutablePaths @(
    (Join-Path $env:ProgramFiles 'Microsoft\Edge\Application\msedge.exe'),
    (Join-Path ${env:ProgramFiles(x86)} 'Microsoft\Edge\Application\msedge.exe')
)
$policyAudit = Get-MihomoPolicyAudit -RuntimeConfig $runtimeConfig -ControllerConfig $appConfig -GroupPattern $PolicyGroupPattern

$result = [ordered]@{
    SchemaVersion = 6
    CollectedAt = (Get-Date).ToUniversalTime().ToString('o')
    System = [ordered]@{
        IsAdministrator = $isAdministrator
        DeviceContext = $deviceContext
        MihomoProcessRunning = $processRunning
        OtherProxyClientsRunning = $multiClientProcesses
        ClashVergeServices = $serviceMatches
        ServiceModeActive = @($serviceMatches | Where-Object State -eq 'Running').Count -gt 0
        MixedPort = $mixedPort
        MixedPortListening = $portListening
        SystemProxy = [ordered]@{
            Enabled = $proxyEnabled
            PointsToLoopback = $proxyPointsToLoopback
        }
        TimeZone = (Get-TimeZone).Id
        Culture = (Get-Culture).Name
        UICulture = (Get-UICulture).Name
        UILanguageOverride = $uiLanguageOverride
        UserLanguageList = $userLanguages
        SystemLocale = $systemLocale
        HomeGeoId = $homeGeoId
        HomeLocation = $homeLocationName
        Teredo = $teredo
        ActiveAdapterIPv6Bindings = $ipv6Bindings
        LocalDnsServers = $localDns
        ProxyEnvironmentVariables = $proxyEnvironmentVariables
    }
    Mihomo = [ordered]@{
        AppConfigPresent = [bool]$appConfig
        RuntimeConfigPresent = [bool]$runtimeConfig
        Mode = Get-YamlScalar -Text $combinedConfig -KeyPattern 'mode'
        AllowLan = ConvertTo-NullableBoolean (Get-YamlScalar -Text $combinedConfig -KeyPattern 'allow[-_]lan')
        IPv6 = ConvertTo-NullableBoolean (Get-YamlScalar -Text $appConfig -KeyPattern 'ipv6')
        TunEnabled = ConvertTo-NullableBoolean (Get-YamlScalar -Text $tunConfig -KeyPattern 'enable')
        StrictRoute = ConvertTo-NullableBoolean (Get-YamlScalar -Text $tunConfig -KeyPattern 'strict[-_]route')
        TunStack = Get-YamlScalar -Text $tunConfig -KeyPattern 'stack'
        DnsEnabled = ConvertTo-NullableBoolean (Get-YamlScalar -Text $dnsConfig -KeyPattern 'enable')
        DnsRespectRules = ConvertTo-NullableBoolean (Get-YamlScalar -Text $dnsConfig -KeyPattern 'respect[-_]rules')
        DnsMode = Get-YamlScalar -Text $dnsConfig -KeyPattern 'enhanced[-_]mode'
        DnsIPv6 = ConvertTo-NullableBoolean (Get-YamlScalar -Text $dnsConfig -KeyPattern 'ipv6')
        DnsHijackAny53 = $dnsHijackAny53
        EncryptedDnsUpstreams = $dnsUpstreams
        PolicyGroups = $policyAudit
    }
    Browsers = [ordered]@{
        Chrome = $chromeAudit
        Edge = $edgeAudit
    }
    ClaudeCode = $claudeAudit
}

$result | ConvertTo-Json -Depth 10
