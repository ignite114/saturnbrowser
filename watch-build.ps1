# Shows Saturn build progress as a percentage, refreshed every 5 seconds.
# Usage: powershell -ExecutionPolicy Bypass -File C:\Users\ignit\saturn_dev\watch-build.ps1 [-Log build-dev.log]
#   -Log  log to follow (relative to saturn_dev, or an absolute path). Default: build.log
#         build-dev.log = dev-build.cmd, build-release.log = build-saturn.cmd
param([string]$Log = 'build.log')
$log = if ([System.IO.Path]::IsPathRooted($Log)) { $Log } else { Join-Path $PSScriptRoot $Log }
$start = Get-Date

while ($true) {
    if (-not (Test-Path $log)) { Write-Host "No $log yet..."; Start-Sleep 5; continue }

    $tail = Get-Content $log -Tail 200
    $last = $tail | Where-Object { $_ -match '^\[(\d+)/(\d+)\]' } | Select-Object -Last 1

    if ($last -and $last -match '^\[(\d+)/(\d+)\]') {
        $done = [int]$Matches[1]; $total = [int]$Matches[2]
        $pct = [math]::Round(100 * $done / $total, 1)
        Write-Progress -Activity 'Compiling Saturn' -Status "$pct%  ($done / $total files)" -PercentComplete $pct
        $line = "Compiling: $pct%  ($done / $total)"
    } else {
        $stage = $tail | Where-Object { $_ -match 'INFO:|ERROR|FAILED|\[saturn\]' } | Select-Object -Last 1
        $line = "Preparing (not compiling yet): $stage"
    }

    $elapsed = (Get-Date) - $start
    Write-Host ("[{0:hh\:mm\:ss}] {1}" -f $elapsed, $line)

    if ($tail -match 'FAILED:|Traceback') { Write-Host "Build hit an error - check $log" -ForegroundColor Red; break }
    if ($tail -match '^\[saturn\] (ninja exit code 0|finished with exit code 0)') { Write-Host 'Build finished.' -ForegroundColor Green; break }
    Start-Sleep 5
}
