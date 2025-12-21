$ErrorActionPreference = "Stop"

function Test-Frontend {
  try {
    $r = Invoke-WebRequest -Uri "http://localhost:3001/login.html" -UseBasicParsing
    return ($r.StatusCode -eq 200)
  } catch {
    Write-Host "Frontend error: $($_.Exception.Message)"
    return $false
  }
}

function Test-BackendLogin {
  param([string]$Username = "testuser", [string]$Password = "password")
  try {
    $body = @{ username = $Username; password = $Password } | ConvertTo-Json
    $resp = Invoke-RestMethod -Uri "http://localhost:8000/api/auth/login" -Method POST -ContentType "application/json" -Body $body
    return $resp.access_token
  } catch {
    Write-Host "Backend login error: $($_.Exception.Message)"
    return $null
  }
}

function Test-Metrics {
  param([string]$Token, [int]$ClientId = 1)
  try {
    $headers = @{ Authorization = "Bearer $Token" }
    $resp = Invoke-RestMethod -Uri "http://localhost:8000/api/metrics/resources/$ClientId" -Method GET -Headers $headers
    return $resp.summary
  } catch {
    Write-Host "Metrics error: $($_.Exception.Message)"
    return $null
  }
}

$okFrontend = Test-Frontend
if (-not $okFrontend) { Write-Host "Frontend failed"; exit 1 } else { Write-Host "Frontend OK" }

$token = Test-BackendLogin
if (-not $token) { Write-Host "Backend login failed"; exit 1 } else { Write-Host "Backend login OK" }

$summary = Test-Metrics -Token $token -ClientId 1
if ($summary -eq $null) { Write-Host "Metrics fetch failed"; exit 1 } else { Write-Host ("Metrics OK: " + ($summary | ConvertTo-Json)) }

Write-Host "Health OK"
exit 0
