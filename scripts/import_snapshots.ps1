# Import JSON files from resource_outputs/ into metric_snapshots table
# Usage: powershell -ExecutionPolicy Bypass -File .\scripts\import_snapshots.ps1

param(
    [string]$ComposeFile = "podman-compose.yml",
    [string]$InputDir = "resource_outputs"
)

$files = Get-ChildItem -Path $InputDir -Filter *_resources.json -File -ErrorAction SilentlyContinue
if (-not $files) { Write-Host "No snapshot files found in $InputDir"; exit 0 }

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$converter = Join-Path -Path $scriptDir -ChildPath "convert_to_json.py"

foreach ($f in $files) {
    Write-Host "Processing $($f.Name)"
    $json = Get-Content -Path $f.FullName -Raw
    $obj = $null

    # Try native JSON parse first
    try {
        $obj = $json | ConvertFrom-Json
    } catch {
        Write-Warning "File $($f.Name) is not valid JSON, attempting conversion using Python helper..."

        if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
            Write-Warning "Python not available in PATH. Skipping $($f.Name)."; continue
        }

        if (-not (Test-Path $converter)) {
            Write-Warning "Converter script not found at $converter. Skipping $($f.Name)."; continue
        }

        $converted = & python $converter $f.FullName 2>&1
        if ($LASTEXITCODE -ne 0 -or -not $converted) {
            Write-Warning "Auto-conversion failed for $($f.Name): $converted"; continue
        }

        $json = $converted
        try { $obj = $json | ConvertFrom-Json } catch { Write-Warning "Converted content still invalid for $($f.Name): $($_.Exception.Message)"; continue }
    }

    $tenant_id = $obj.client_id
    $provider = $obj.provider

    # Encode JSON as base64 to avoid shell/quoting issues when passing through compose/docker
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($json)
    $b64 = [System.Convert]::ToBase64String($bytes)

    $sql = "INSERT INTO metric_snapshots (tenant_id, provider, data) VALUES ($tenant_id, '$provider', convert_from(decode('$b64','base64'),'UTF8')::json);"
    Write-Host "Inserting snapshot for tenant $tenant_id provider $provider"

    podman compose -f $ComposeFile exec -T db psql -U postgres -d pca -c $sql
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Failed to insert snapshot for $($f.Name)"
    } else {
        Write-Host "Inserted snapshot for $($f.Name)"
    }
}

Write-Host "Done."