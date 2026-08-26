<#
.SYNOPSIS
    Enter an API key for the loop-closure experiment without echoing it.

.DESCRIPTION
    Reads the key with masked input, sets it for this PowerShell session, and
    optionally persists it to your Windows user environment.

    The key is never printed, never written into the repository, and never passed
    as a command-line argument (where it would land in your shell history).

    Verification is delegated to `run_loop_closure.py --check`, so this script and
    the experiment always agree on which endpoint and model are used.

.PARAMETER Name
    Which variable to set. Default OPENROUTER_API_KEY, which selects the
    OpenRouter endpoint. The model is chosen separately, with --model or a
    preset (LOOP_API_PRESET / --preset); no model is assumed by this script.

.PARAMETER Persist
    Also save to your user environment so new terminals inherit it.

.PARAMETER Remove
    Clear the variable instead of setting it.

.PARAMETER NoCheck
    Skip the live verification round-trip.

.EXAMPLE
    .\scripts\set_api_key.ps1

.EXAMPLE
    .\scripts\set_api_key.ps1 -Persist

.EXAMPLE
    .\scripts\set_api_key.ps1 -Remove -Persist
#>
[CmdletBinding()]
param(
    [ValidateSet('OPENROUTER_API_KEY', 'OPENAI_API_KEY', 'LOOP_API_KEY')]
    [string]$Name = 'OPENROUTER_API_KEY',
    [switch]$Persist,
    [switch]$Remove,
    [switch]$NoCheck,
    [string]$Model,
    [string]$BaseUrl
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot

if ($Remove) {
    Remove-Item -Path "env:$Name" -ErrorAction SilentlyContinue
    if ($Persist) {
        [Environment]::SetEnvironmentVariable($Name, $null, 'User')
        Write-Host "Cleared $Name from this session and your user environment."
    }
    else {
        Write-Host "Cleared $Name from this session."
        Write-Host "Add -Persist to also clear it from your user environment."
    }
    return
}

Write-Host ""
Write-Host "Paste your key for $Name. Input is hidden."
if ($Name -eq 'OPENROUTER_API_KEY') {
    Write-Host "Get one at https://openrouter.ai/keys  (format: sk-or-v1-...)"
}
$secure = Read-Host "Key" -AsSecureString

$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try {
    $key = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr).Trim()
}
finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
}

if ([string]::IsNullOrWhiteSpace($key)) {
    Write-Host "No key entered; nothing changed." -ForegroundColor Yellow
    return
}
if ($Name -eq 'OPENROUTER_API_KEY' -and -not $key.StartsWith('sk-or-')) {
    Write-Host "Note: OpenRouter keys normally start with 'sk-or-v1-'." -ForegroundColor Yellow
    Write-Host "Continuing anyway - the check below will tell you if it is wrong."
}

Set-Item -Path "env:$Name" -Value $key

$tail = '****'
if ($key.Length -ge 4) { $tail = $key.Substring($key.Length - 4) }
$len = $key.Length
Write-Host ""
Write-Host "Set $Name for this session (ends ...$tail, $len chars)."

if ($Persist) {
    [Environment]::SetEnvironmentVariable($Name, $key, 'User')
    Write-Host "Persisted to your user environment; new terminals inherit it."
}
else {
    Write-Host "Session only. Re-run with -Persist to keep it across terminals."
}

$key = $null
[GC]::Collect()

if ($NoCheck) {
    Write-Host ""
    Write-Host "Skipped verification. Run it yourself with:"
    Write-Host "  python experiments/run_loop_closure.py --check"
    return
}

Write-Host ""
Write-Host "Verifying (one round-trip)..."
$checkArgs = @((Join-Path $repo 'experiments\run_loop_closure.py'), '--check')
if ($Model) { $checkArgs += @('--model', $Model) }
if ($BaseUrl) { $checkArgs += @('--base-url', $BaseUrl) }
& python @checkArgs

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "Ready. Run the experiment with:" -ForegroundColor Green
    Write-Host "  python experiments/run_loop_closure.py --api"
}
else {
    Write-Host ""
    Write-Host "Key is set but the check failed - see the message above." -ForegroundColor Yellow
    Write-Host "Common causes: typo in the key, no quota, or the free window closed."
}
