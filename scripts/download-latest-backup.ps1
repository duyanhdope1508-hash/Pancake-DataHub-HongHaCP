[CmdletBinding()]
param(
    [string]$Server = "deploy@129.212.233.231",
    [string]$RemoteBackupDir = "/opt/pancake-data-hub/backups",
    [string]$Destination = "",
    [string]$IdentityFile = "",
    [ValidateRange(1, 52)]
    [int]$Keep = 4
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$scriptDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $Destination) {
    $Destination = Join-Path $scriptDirectory "..\backups\windows-copy"
}

if ($Server -notmatch '^[A-Za-z0-9._-]+@[A-Za-z0-9.-]+$') {
    throw "Server must have the form user@hostname or user@IPv4."
}
if ($RemoteBackupDir -notmatch '^/[A-Za-z0-9._/-]+$') {
    throw "RemoteBackupDir contains unsupported characters."
}

foreach ($command in @("ssh.exe", "scp.exe")) {
    if (-not (Get-Command $command -ErrorAction SilentlyContinue)) {
        throw "$command is not available. Install Windows OpenSSH Client first."
    }
}

$connectionOptions = @(
    "-o", "BatchMode=no",
    "-o", "PreferredAuthentications=publickey",
    "-o", "PasswordAuthentication=no",
    "-o", "KbdInteractiveAuthentication=no",
    "-o", "ConnectTimeout=15",
    "-o", "ServerAliveInterval=15",
    "-o", "ServerAliveCountMax=3"
)
if ($IdentityFile) {
    $resolvedIdentity = (Resolve-Path -LiteralPath $IdentityFile).Path
    $connectionOptions += @("-o", "IdentitiesOnly=yes", "-i", $resolvedIdentity)
}

$remoteCommand = @"
latest=`$(find '$RemoteBackupDir' -maxdepth 1 -type f -name 'pancake-data-hub-????????T??????Z.dump' -printf '%T@ %f\n' | sort -nr | head -n 1 | cut -d' ' -f2-)
[ -n "`$latest" ] && [ -f '$RemoteBackupDir/'"`$latest"'.sha256' ] || exit 3
printf '%s\n' "`$latest"
"@

Write-Host "Finding the latest backup on the VPS..." -ForegroundColor Cyan
$latestOutput = & ssh.exe @connectionOptions $Server $remoteCommand
if ($LASTEXITCODE -ne 0) {
    throw "Could not connect through SSH or find a complete backup on the VPS."
}
$latestName = ($latestOutput | Select-Object -Last 1).Trim()
if ($latestName -notmatch '^pancake-data-hub-[0-9]{8}T[0-9]{6}Z\.dump$') {
    throw "The VPS returned an invalid backup filename."
}

$destinationPath = [System.IO.Path]::GetFullPath($Destination)
New-Item -ItemType Directory -Force -Path $destinationPath | Out-Null
$localBackup = Join-Path $destinationPath $latestName
$localChecksum = "$localBackup.sha256"
$partialBackup = "$localBackup.partial"
$partialChecksum = "$localChecksum.partial"

try {
    Write-Host "Downloading the checksum..." -ForegroundColor Cyan
    & scp.exe @connectionOptions "${Server}:${RemoteBackupDir}/${latestName}.sha256" $partialChecksum
    if ($LASTEXITCODE -ne 0) {
        throw "Could not download the checksum from the VPS."
    }

    $expectedHash = ((Get-Content -LiteralPath $partialChecksum -Raw).Trim() -split '\s+')[0]
    if ($expectedHash -notmatch '^[A-Fa-f0-9]{64}$') {
        throw "The checksum stored on the VPS is invalid."
    }

    if (Test-Path -LiteralPath $localBackup) {
        $existingHash = (Get-FileHash -LiteralPath $localBackup -Algorithm SHA256).Hash
        if ($existingHash -ieq $expectedHash) {
            Move-Item -Force -LiteralPath $partialChecksum -Destination $localChecksum
            Write-Host "The latest backup is already present and verified: $localBackup" -ForegroundColor Green
        } else {
            throw "A file with the same name has a different checksum. It will not be overwritten."
        }
    } else {
        Write-Host "Downloading $latestName. This can take several minutes..." -ForegroundColor Cyan
        & scp.exe @connectionOptions "${Server}:${RemoteBackupDir}/${latestName}" $partialBackup
        if ($LASTEXITCODE -ne 0) {
            throw "Could not download the backup from the VPS."
        }

        Write-Host "Verifying SHA-256..." -ForegroundColor Cyan
        $actualHash = (Get-FileHash -LiteralPath $partialBackup -Algorithm SHA256).Hash
        if ($actualHash -ine $expectedHash) {
            throw "Checksum mismatch. The downloaded file is not a valid backup."
        }

        Move-Item -LiteralPath $partialBackup -Destination $localBackup
        Move-Item -Force -LiteralPath $partialChecksum -Destination $localChecksum
        Write-Host "Backup downloaded and verified successfully: $localBackup" -ForegroundColor Green
    }
}
finally {
    Remove-Item -Force -ErrorAction SilentlyContinue -LiteralPath $partialBackup, $partialChecksum
}

$verifiedBackups = Get-ChildItem -LiteralPath $destinationPath -File |
    Where-Object { $_.Name -match '^pancake-data-hub-[0-9]{8}T[0-9]{6}Z\.dump$' } |
    Sort-Object LastWriteTimeUtc -Descending

foreach ($obsolete in ($verifiedBackups | Select-Object -Skip $Keep)) {
    Remove-Item -Force -LiteralPath $obsolete.FullName
    Remove-Item -Force -ErrorAction SilentlyContinue -LiteralPath "$($obsolete.FullName).sha256"
}

$keptCount = @(Get-ChildItem -LiteralPath $destinationPath -File |
    Where-Object { $_.Name -match '^pancake-data-hub-[0-9]{8}T[0-9]{6}Z\.dump$' }).Count
Write-Host "Completed. This computer keeps $keptCount/$Keep backups in: $destinationPath" -ForegroundColor Green
Write-Host "Security note: store this folder on a BitLocker-protected drive." -ForegroundColor Yellow
