# PowerShell script: Dump Postgres DB from compose stack to local backups folder
# Requires: Podman + podman-compose.yml running with service name 'db'

param(
    [string]$ComposeFile = "podman-compose.yml",
    [string]$Database = "pca",
    [string]$User = "postgres"
)

# Ensure backups directory
$repoRoot = Get-Location
$backupDir = Join-Path $repoRoot "backups"
if (!(Test-Path $backupDir)) { New-Item -ItemType Directory -Path $backupDir | Out-Null }

# Timestamped file
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupFile = "pca_${timestamp}.dump"
$backupPath = Join-Path $backupDir $backupFile

Write-Host "Creating backup: $backupPath"

# Run pg_dump inside the 'db' service container, write to /tmp
$dumpCmd = "pg_dump -U $User -d $Database -F c -f /tmp/$backupFile"
$execResult = podman compose -f $ComposeFile exec -T db sh -lc $dumpCmd
if ($LASTEXITCODE -ne 0) {
    Write-Host "Backup failed while running pg_dump"; exit 1
}

# Find actual container name for 'db' service
# Prefer exact match including '-db-' pattern
$containers = podman ps --format "{{.Names}}"
$dbContainer = ($containers | Where-Object { $_ -match "-db-" }) | Select-Object -First 1
if (-not $dbContainer) {
    # Fallback: any container with 'db' in name
    $dbContainer = ($containers | Where-Object { $_ -match "db" }) | Select-Object -First 1
}
if (-not $dbContainer) {
    Write-Host "Could not find db container name"; exit 1
}

# Copy dump file out
podman cp "$dbContainer:/tmp/$backupFile" "$backupPath"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to copy backup from container"; exit 1
}

# Clean up temp file inside container
podman compose -f $ComposeFile exec -T db rm "/tmp/$backupFile" | Out-Null

Write-Host "Backup complete: $backupPath"