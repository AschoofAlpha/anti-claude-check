param(
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$ArgsList
)

$ErrorActionPreference = 'Stop'

if (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonVersion = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
    if ($LASTEXITCODE -eq 0 -and [double]$pythonVersion -ge 3.7) {
        # Python 3 is available, pass arguments to the unified CLI
        & python -m claude_shield @ArgsList
        exit $LASTEXITCODE
    }
}

# Fallback when Python is not available
Write-Host "[- WARNING] Python 3 not detected or version too low. Limited local audit mode active." -ForegroundColor Yellow
Write-Host "[i] The following features will be skipped: Advanced redaction, Dry Run, Transaction/Rollback manifests, Credential scanning." -ForegroundColor Gray

$command = if ($ArgsList.Count -gt 0) { $ArgsList[0] } else { 'audit' }

if ($command -eq 'audit') {
    # Run legacy PS1 collector
    & pwsh -NoProfile -File "$PSScriptRoot\scripts\collect_windows_network.ps1"
} elseif ($command -eq 'remediate') {
    Write-Host "[- ERROR] Remediation without Python is unsupported because of lack of rollback and dry-run safety mechanisms. Please install Python 3." -ForegroundColor Red
    exit 1
} else {
    Write-Host "[- ERROR] Command '$command' is unsupported in fallback mode." -ForegroundColor Red
    exit 1
}
