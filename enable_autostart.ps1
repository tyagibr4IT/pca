# Auto-start Podman containers on Windows system startup
# This script creates a scheduled task that runs .\start_all.bat after every reboot

param(
    [string]$TaskName = "PCA-Stack-AutoStart",
    [string]$RepoPath = (Get-Location).Path
)

$startScript = Join-Path $RepoPath "start_all.bat"

if (!(Test-Path $startScript)) {
    Write-Host "ERROR: start_all.bat not found at $startScript"
    exit 1
}

# Check if task already exists
$existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host "Task '$TaskName' already exists. Removing it..."
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# Create trigger: At startup
$trigger = New-ScheduledTaskTrigger -AtStartup

# Create action: Run start_all.bat with cmd /c to wait for completion
# Note: Using cmd /c ensures the batch file fully executes before task exits
$action = New-ScheduledTaskAction `
    -Execute "cmd.exe" `
    -Argument "/c `"$startScript`"" `
    -WorkingDirectory $RepoPath

# Create principal: Run with highest privileges (required to manage containers)
$principal = New-ScheduledTaskPrincipal `
    -UserID "SYSTEM" `
    -LogonType ServiceAccount `
    -RunLevel Highest

# Create settings: Allow task to run on demand, restart on failure
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)

# Register task
Write-Host "Creating scheduled task: $TaskName"
Register-ScheduledTask `
    -TaskName $TaskName `
    -Trigger $trigger `
    -Action $action `
    -Principal $principal `
    -Settings $settings `
    -Description "Auto-start PCA stack (backend, frontend, db, redis) on system boot" `
    -Force | Out-Null

Write-Host "Task created successfully!"
Write-Host ""
Write-Host "Auto-start is now enabled. On next system reboot:"
Write-Host "  1. Containers will automatically start"
Write-Host "  2. All data in Postgres and Redis will be restored from volumes"
Write-Host ""
Write-Host "To verify the task:"
Write-Host "  Get-ScheduledTask -TaskName '$TaskName'"
Write-Host ""
Write-Host "To disable auto-start:"
Write-Host "  Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"