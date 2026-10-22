# scripts/check_ports.ps1
# Verifies ports 8000 (Backend) and 5173 (Frontend) are available.
# Safely terminates previous JobPulse AI processes, or warns if external programs occupy ports.

param(
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 5173
)

$backendConflict = $false
$frontendConflict = $false

# 1. Inspect Port 8000 (Backend)
$bConn = Get-NetTCPConnection -LocalPort $BackendPort -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($bConn) {
    $proc = Get-Process -Id $bConn.OwningProcess -ErrorAction SilentlyContinue
    if ($proc) {
        if ($proc.ProcessName -match "python" -or $proc.ProcessName -match "uvicorn") {
            Write-Host "    [INFO] Stopping previous JobPulse AI backend process (PID $($proc.Id))..."
            Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
            Start-Sleep -Milliseconds 500
            Write-Host "    [OK] Released port $BackendPort."
        } else {
            Write-Host "    [WARNING] Port $BackendPort is occupied by external process: $($proc.ProcessName) (PID $($proc.Id))"
            $backendConflict = $true
        }
    }
} else {
    Write-Host "    [OK] Port $BackendPort is available."
}

# 2. Inspect Port 5173 (Frontend)
$fConn = Get-NetTCPConnection -LocalPort $FrontendPort -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($fConn) {
    $proc = Get-Process -Id $fConn.OwningProcess -ErrorAction SilentlyContinue
    if ($proc) {
        if ($proc.ProcessName -match "node" -or $proc.ProcessName -match "vite") {
            Write-Host "    [INFO] Stopping previous JobPulse AI frontend process (PID $($proc.Id))..."
            Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
            Start-Sleep -Milliseconds 500
            Write-Host "    [OK] Released port $FrontendPort."
        } else {
            Write-Host "    [WARNING] Port $FrontendPort is occupied by external process: $($proc.ProcessName) (PID $($proc.Id))"
            $frontendConflict = $true
        }
    }
} else {
    Write-Host "    [OK] Port $FrontendPort is available."
}

if ($backendConflict -or $frontendConflict) {
    exit 2
} else {
    exit 0
}
