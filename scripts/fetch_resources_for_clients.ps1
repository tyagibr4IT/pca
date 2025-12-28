# Fetch resources for named tenants and save outputs
# Usage: Run from repo root: powershell -ExecutionPolicy Bypass -File .\scripts\fetch_resources_for_clients.ps1

param(
    [string[]]$Clients = @('HLLMMu','DOP_test','GCP_test'),
    [string]$Username = 'testuser',
    [string]$Password = 'password',
    [string]$ComposeFile = 'podman-compose.yml'
)

function Get-TenantId($name) {
    $q1 = "SELECT id FROM tenant WHERE name = '$name' LIMIT 1;"
    $q2 = "SELECT id FROM tenants WHERE name = '$name' LIMIT 1;"

    $id = podman compose -f $ComposeFile exec -T db psql -U postgres -d pca -tAc $q1 2>$null
    if (-not $id) {
        $id = podman compose -f $ComposeFile exec -T db psql -U postgres -d pca -tAc $q2 2>$null
    }
    return $id.Trim()
}

# Obtain token
Write-Host "Logging in as $Username..."
$loginBody = @{ username = $Username; password = $Password } | ConvertTo-Json
$loginResp = Invoke-RestMethod -Uri http://localhost:8000/api/auth/login -Method POST -Body $loginBody -ContentType 'application/json' -ErrorAction Stop
$token = $loginResp.access_token
if (-not $token) { Write-Error "Login failed, no token returned"; exit 1 }
Write-Host "Obtained token."

# Create output folder
$outDir = Join-Path (Get-Location) 'resource_outputs'
if (!(Test-Path $outDir)) { New-Item -ItemType Directory -Path $outDir | Out-Null }

foreach ($c in $Clients) {
    Write-Host "Processing client: $c"
    $id = Get-TenantId $c
    if (-not $id) {
        Write-Warning "Could not find tenant id for $c. Skipping."
        continue
    }
    Write-Host "Found tenant id: $id"
    $url = "http://localhost:8000/api/metrics/resources/$id"
    try {
        $resp = Invoke-RestMethod -Uri $url -Method GET -Headers @{ Authorization = "Bearer $token" } -ErrorAction Stop
        $outFile = Join-Path $outDir "$($c)_resources.json"
        $resp | ConvertTo-Json -Depth 50 | Out-File -FilePath $outFile -Encoding UTF8
        Write-Host "Saved resources to $outFile"
    } catch {
        $msg = $_.Exception.Message
        Write-Warning ("Failed to fetch resources for {0}" -f $c + ": " + $msg)
        Write-Host "Tailing backend logs for recent errors (last 200 lines):"
        podman compose -f $ComposeFile logs --tail 200 backend
    }
}

Write-Host "Done."