$ports = @(8000, 5173)
$labels = @{ 8000 = "Backend"; 5173 = "Frontend" }

foreach ($port in $ports) {
    $label = $labels[$port]
    $found = $false
    $targets = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
        Where-Object { $_.OwningProcess -gt 0 } |
        ForEach-Object { $_.OwningProcess } |
        Select-Object -Unique

    foreach ($target in $targets) {
        $found = $true
        cmd /c "taskkill /f /t /pid $target" > $null 2>&1
    }

    if ($found) {
        Write-Host "[OK] $label stopped."
    } else {
        Write-Host "[INFO] $label was not running."
    }
}
Write-Host ""
Write-Host "Cleanup complete. Window will close in 3 seconds..."
Start-Sleep -Seconds 3