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
    "-o", "BatchMode=yes",
    "-o", "ConnectTimeout=15",
    "-o", "ServerAliveInterval=15",
    "-o", "ServerAliveCountMax=3"
)
if ($IdentityFile) {
    $resolvedIdentity = (Resolve-Path -LiteralPath $IdentityFile).Path
    $connectionOptions += @("-i", $resolvedIdentity)
}

$remoteCommand = @"
latest=`$(find '$RemoteBackupDir' -maxdepth 1 -type f -name 'pancake-data-hub-????????T??????Z.dump' -printf '%T@ %f\n' | sort -nr | head -n 1 | cut -d' ' -f2-)
[ -n "`$latest" ] && [ -f '$RemoteBackupDir/'"`$latest"'.sha256' ] || exit 3
printf '%s\n' "`$latest"
"@

Write-Host "Đang xác định backup mới nhất trên VPS..." -ForegroundColor Cyan
$latestOutput = & ssh.exe @connectionOptions $Server $remoteCommand
if ($LASTEXITCODE -ne 0) {
    throw "Không tìm thấy backup hoàn chỉnh trên VPS hoặc không thể kết nối SSH."
}
$latestName = ($latestOutput | Select-Object -Last 1).Trim()
if ($latestName -notmatch '^pancake-data-hub-[0-9]{8}T[0-9]{6}Z\.dump$') {
    throw "VPS trả về tên backup không hợp lệ."
}

$destinationPath = [System.IO.Path]::GetFullPath($Destination)
New-Item -ItemType Directory -Force -Path $destinationPath | Out-Null
$localBackup = Join-Path $destinationPath $latestName
$localChecksum = "$localBackup.sha256"
$partialBackup = "$localBackup.partial"
$partialChecksum = "$localChecksum.partial"

try {
    Write-Host "Đang tải checksum..." -ForegroundColor Cyan
    & scp.exe @connectionOptions "${Server}:${RemoteBackupDir}/${latestName}.sha256" $partialChecksum
    if ($LASTEXITCODE -ne 0) {
        throw "Không thể tải checksum từ VPS."
    }

    $expectedHash = ((Get-Content -LiteralPath $partialChecksum -Raw).Trim() -split '\s+')[0]
    if ($expectedHash -notmatch '^[A-Fa-f0-9]{64}$') {
        throw "Checksum trên VPS không hợp lệ."
    }

    if (Test-Path -LiteralPath $localBackup) {
        $existingHash = (Get-FileHash -LiteralPath $localBackup -Algorithm SHA256).Hash
        if ($existingHash -ieq $expectedHash) {
            Move-Item -Force -LiteralPath $partialChecksum -Destination $localChecksum
            Write-Host "Backup mới nhất đã có sẵn và checksum chính xác: $localBackup" -ForegroundColor Green
        } else {
            throw "Đã có file cùng tên nhưng checksum không đúng. Không ghi đè để tránh mất bằng chứng kiểm tra."
        }
    } else {
        Write-Host "Đang tải $latestName. Quá trình có thể mất vài phút..." -ForegroundColor Cyan
        & scp.exe @connectionOptions "${Server}:${RemoteBackupDir}/${latestName}" $partialBackup
        if ($LASTEXITCODE -ne 0) {
            throw "Không thể tải backup từ VPS."
        }

        Write-Host "Đang xác minh SHA-256..." -ForegroundColor Cyan
        $actualHash = (Get-FileHash -LiteralPath $partialBackup -Algorithm SHA256).Hash
        if ($actualHash -ine $expectedHash) {
            throw "Checksum không khớp. File tải về không được công nhận là backup hợp lệ."
        }

        Move-Item -LiteralPath $partialBackup -Destination $localBackup
        Move-Item -Force -LiteralPath $partialChecksum -Destination $localChecksum
        Write-Host "Đã tải và xác minh thành công: $localBackup" -ForegroundColor Green
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
Write-Host "Hoàn tất. Máy đang giữ $keptCount/$Keep bản backup trong: $destinationPath" -ForegroundColor Green
Write-Host "Lưu ý: nên đặt thư mục này trên ổ đĩa có BitLocker." -ForegroundColor Yellow
