# Registers a daily Windows Task Scheduler job for WebScraperForNews.
# Run in elevated PowerShell if needed:
#   powershell -ExecutionPolicy Bypass -File .\scripts\register_daily_task.ps1

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Runner = Join-Path $ProjectRoot "run.py"
$TaskName = "WebScraperForNews-DailyDigest"
$Hour = 8
$Minute = 0

if (-not (Test-Path $Python)) {
    throw "Python venv not found: $Python"
}
if (-not (Test-Path $Runner)) {
    throw "Runner not found: $Runner"
}

$Action = New-ScheduledTaskAction `
    -Execute $Python `
    -Argument "`"$Runner`"" `
    -WorkingDirectory $ProjectRoot

$Trigger = New-ScheduledTaskTrigger -Daily -At ("{0:D2}:{1:D2}" -f $Hour, $Minute)

$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "Daily AI news digest for WebScraperForNews" `
    -Force | Out-Null

Write-Host "Task registered: $TaskName"
Write-Host "Schedule: daily at ${Hour}:$("{0:D2}" -f $Minute) local time"
Write-Host "Command: $Python $Runner"
Write-Host "WorkingDirectory: $ProjectRoot"
Write-Host "Check: Get-ScheduledTask -TaskName $TaskName"
