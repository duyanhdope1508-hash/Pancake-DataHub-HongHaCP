[CmdletBinding()]
param(
    [switch]$Force,
    [switch]$Probe
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $projectRoot ".env"

if ((Test-Path -LiteralPath $envPath) -and -not $Force) {
    throw ".env already exists. Run again with -Force only if you intend to replace it."
}

Write-Host "Paste the Pancake POS API key. It will not be displayed:"
$secureKey = Read-Host -AsSecureString
$keyPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)

try {
    $apiKey = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($keyPointer)
}
finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($keyPointer)
}

if ([string]::IsNullOrWhiteSpace($apiKey) -or $apiKey.Length -lt 10) {
    throw "The API key is empty or unexpectedly short. No .env file was written."
}

$randomBytes = New-Object byte[] 24
$random = [Security.Cryptography.RandomNumberGenerator]::Create()
try {
    $random.GetBytes($randomBytes)
}
finally {
    $random.Dispose()
}

$databasePassword = [Convert]::ToBase64String($randomBytes).TrimEnd("=").Replace("+", "-").Replace("/", "_")
$lines = @(
    "POSTGRES_DB=pancake_data"
    "POSTGRES_USER=pancake_app"
    "POSTGRES_PASSWORD=$databasePassword"
    "DATABASE_URL=postgresql+psycopg://pancake_app:$databasePassword@db:5432/pancake_data"
    "PANCAKE_API_BASE_URL=https://pos.pages.fm/api/v1"
    "PANCAKE_API_KEY=$apiKey"
    "PANCAKE_SHOP_IDS="
    "PANCAKE_PAGE_SIZE=100"
)

$utf8WithoutBom = New-Object System.Text.UTF8Encoding($false)
[IO.File]::WriteAllLines($envPath, $lines, $utf8WithoutBom)

# Minimize the lifetime of the plaintext value after the file is written.
$apiKey = $null
$secureKey.Dispose()

Write-Host ".env created locally. The file is excluded from Git."

if ($Probe) {
    $pythonPath = Join-Path $projectRoot ".venv\Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $pythonPath)) {
        throw "Python environment not found at .venv. Create it before using -Probe."
    }

    Push-Location $projectRoot
    try {
        & $pythonPath -m app.cli probe
        if ($LASTEXITCODE -ne 0) {
            throw "Pancake API probe failed with exit code $LASTEXITCODE."
        }
    }
    finally {
        Pop-Location
    }
}

