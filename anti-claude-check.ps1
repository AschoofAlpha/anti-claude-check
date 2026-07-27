param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ArgsList
)

$ErrorActionPreference = 'Stop'

if (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonVersion = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
    if ($LASTEXITCODE -eq 0 -and [version]$pythonVersion -ge [version]'3.8') {
        & python -m claude_shield @ArgsList
        exit $LASTEXITCODE
    }
}

$command = if ($ArgsList.Count -gt 0) { $ArgsList[0] } else { 'audit' }
if ($command -ne 'audit') {
    Write-Error "Command '$command' requires Python 3.8 or newer."
    exit 1
}

$shell = Get-Command pwsh -ErrorAction SilentlyContinue
if ($null -eq $shell) { $shell = Get-Command powershell.exe -ErrorAction SilentlyContinue }
if ($null -eq $shell) { Write-Error 'PowerShell is unavailable.'; exit 1 }
& $shell.Source -NoProfile -File "$PSScriptRoot\scripts\collect_windows_network.ps1"
exit $LASTEXITCODE
