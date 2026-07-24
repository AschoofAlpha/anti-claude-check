[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [switch]$DisableTelemetry,
    [switch]$ResetDeviceFingerprint,
    [switch]$ClearTelemetryCache,
    [switch]$DisablePhysicalIPv6,
    [switch]$All,
    [switch]$Force
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'

Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "  Anti-Claude-Check PowerShell Remediation & Hardening" -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host ""

$remediationsApplied = 0

# 1. Disable Telemetry
if ($All -or $DisableTelemetry -or (-not $Force -and (Read-Host "Set DISABLE_TELEMETRY=1 in User Environment? (y/N)") -eq 'y')) {
    if ($PSCmdlet.ShouldProcess("User Environment Variable: DISABLE_TELEMETRY", "Set value to 1")) {
        [Environment]::SetEnvironmentVariable('DISABLE_TELEMETRY', '1', 'User')
        $env:DISABLE_TELEMETRY = '1'
        Write-Host "[+ SUCCESS] Set DISABLE_TELEMETRY=1 in User environment." -ForegroundColor Green
        $remediationsApplied++
    }
}

# 2. Reset Device Fingerprint in ~/.claude.json
$claudeJsonPath = Join-Path $env:USERPROFILE '.claude.json'
if (Test-Path -LiteralPath $claudeJsonPath -PathType Leaf) {
    if ($All -or $ResetDeviceFingerprint -or (-not $Force -and (Read-Host "Backup ~/.claude.json and reset userID/deviceId fingerprint? (y/N)") -eq 'y')) {
        if ($PSCmdlet.ShouldProcess($claudeJsonPath, "Backup and remove userID/deviceId fields")) {
            $bakPath = "$claudeJsonPath.bak"
            Copy-Item -LiteralPath $claudeJsonPath -Destination $bakPath -Force
            Write-Host "[i] Created backup at $bakPath" -ForegroundColor Gray

            try {
                $rawJson = [System.IO.File]::ReadAllText($claudeJsonPath)
                $jsonObj = $rawJson | ConvertFrom-Json
                $modified = $false
                if ($null -ne $jsonObj.PSObject.Properties['userID']) {
                    $jsonObj.PSObject.Properties.Remove('userID')
                    $modified = $true
                }
                if ($null -ne $jsonObj.PSObject.Properties['deviceId']) {
                    $jsonObj.PSObject.Properties.Remove('deviceId')
                    $modified = $true
                }
                if ($modified) {
                    $newJson = $jsonObj | ConvertTo-Json -Depth 10
                    [System.IO.File]::WriteAllText($claudeJsonPath, $newJson, [System.Text.Encoding]::UTF8)
                    Write-Host "[+ SUCCESS] Reset device fingerprint fields in $claudeJsonPath" -ForegroundColor Green
                    $remediationsApplied++
                } else {
                    Write-Host "[i] No userID or deviceId found in $claudeJsonPath" -ForegroundColor Yellow
                }
            } catch {
                Write-Host "[- ERROR] Failed to update ${claudeJsonPath}: $_" -ForegroundColor Red
            }
        }
    }
}

# 3. Clear Telemetry Cache
$telemetryDir = Join-Path (Join-Path $env:USERPROFILE '.claude') 'telemetry'
if (Test-Path -LiteralPath $telemetryDir -PathType Container) {
    if ($All -or $ClearTelemetryCache -or (-not $Force -and (Read-Host "Clear telemetry cache in ~/.claude/telemetry/? (y/N)") -eq 'y')) {
        if ($PSCmdlet.ShouldProcess($telemetryDir, "Delete cached telemetry files")) {
            try {
                $files = Get-ChildItem -LiteralPath $telemetryDir -File -Recurse -ErrorAction SilentlyContinue
                $count = $files.Count
                Remove-Item -Path "$telemetryDir\*" -Recurse -Force -ErrorAction SilentlyContinue
                Write-Host "[+ SUCCESS] Cleared $count cached telemetry files from $telemetryDir" -ForegroundColor Green
                $remediationsApplied++
            } catch {
                Write-Host "[- ERROR] Failed to clear telemetry cache: $_" -ForegroundColor Red
            }
        }
    }
}

# 4. Disable Physical IPv6
if ($DisablePhysicalIPv6 -or ($All -and -not $Force -and (Read-Host "Disable IPv6 on physical network adapters? (Requires Administrator) (y/N)") -eq 'y')) {
    $isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if (-not $isAdmin) {
        Write-Host "[- WARNING] Administrator privileges required to disable physical IPv6. Please relaunch PowerShell as Administrator." -ForegroundColor Yellow
    } else {
        if (Get-Command Disable-NetAdapterBinding -ErrorAction SilentlyContinue) {
            $physicalAdapters = Get-NetAdapter -ErrorAction SilentlyContinue | Where-Object {
                $_.Status -eq 'Up' -and $_.HardwareInterface -eq $true -and $_.Name -notmatch '(?i)mihomo|clash|wintun|wireguard|tap|vpn'
            }
            foreach ($adapter in $physicalAdapters) {
                if ($PSCmdlet.ShouldProcess($adapter.Name, "Disable-NetAdapterBinding -ComponentID ms_tcpip6")) {
                    Disable-NetAdapterBinding -Name $adapter.Name -ComponentID ms_tcpip6 -Confirm:$false
                    Write-Host "[+ SUCCESS] Disabled IPv6 on physical adapter: $($adapter.Name)" -ForegroundColor Green
                    $remediationsApplied++
                }
            }
        }
    }
}

Write-Host ""
Write-Host "Remediation complete. Total actions taken: $remediationsApplied" -ForegroundColor Cyan
