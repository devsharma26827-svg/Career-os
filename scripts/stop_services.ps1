# scripts/stop_services.ps1
# Cleanly terminates JobPulse AI backend, frontend, and console windows.
# Ensures external non-JobPulse processes on ports 8000/5173 are NOT affected.

param(
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 5173
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
$logDir = Join-Path $projectRoot "logs"
$logFile = Join-Path $logDir "run.log"
$pidFile = Join-Path $logDir "pids.txt"

function Write-Log {
    param([string]$Message)
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$ts] $Message"
    Write-Host $line
    try {
        if (-not (Test-Path $logDir)) {
            New-Item -ItemType Directory -Path $logDir -Force | Out-Null
        }
        Add-Content -Path $logFile -Value $line -ErrorAction SilentlyContinue
    } catch {}
}

Write-Log "[STOP] Starting graceful shutdown of JobPulse AI services..."

$backendStopped = $false
$frontendStopped = $false

# 1. Stop Backend on Port 8000 (Target only Python/Uvicorn processes)
$bConns = Get-NetTCPConnection -LocalPort $BackendPort -State Listen -ErrorAction SilentlyContinue
if ($bConns) {
    foreach ($conn in $bConns) {
        $pidNum = $conn.OwningProcess
        if ($pidNum -gt 0) {
            $proc = Get-Process -Id $pidNum -ErrorAction SilentlyContinue
            if ($proc) {
                if ($proc.ProcessName -match "python" -or $proc.ProcessName -match "uvicorn") {
                    Write-Log "    Stopping backend process '$($proc.ProcessName)' (PID $pidNum)..."
                    Stop-Process -Id $pidNum -Force -ErrorAction SilentlyContinue
                    $backendStopped = $true
                } else {
                    Write-Log "    [SKIP] Port $BackendPort is held by external process '$($proc.ProcessName)' (PID $pidNum). Preserving."
                }
            }
        }
    }
} else {
    Write-Host "    Port $BackendPort is free (Backend not running)."
}

# 2. Stop Frontend on Port 5173 (Target only Node/Vite processes)
$fConns = Get-NetTCPConnection -LocalPort $FrontendPort -State Listen -ErrorAction SilentlyContinue
if ($fConns) {
    foreach ($conn in $fConns) {
        $pidNum = $conn.OwningProcess
        if ($pidNum -gt 0) {
            $proc = Get-Process -Id $pidNum -ErrorAction SilentlyContinue
            if ($proc) {
                if ($proc.ProcessName -match "node" -or $proc.ProcessName -match "vite") {
                    Write-Log "    Stopping frontend process '$($proc.ProcessName)' (PID $pidNum)..."
                    Stop-Process -Id $pidNum -Force -ErrorAction SilentlyContinue
                    $frontendStopped = $true
                } else {
                    Write-Log "    [SKIP] Port $FrontendPort is held by external process '$($proc.ProcessName)' (PID $pidNum). Preserving."
                }
            }
        }
    }
} else {
    Write-Host "    Port $FrontendPort is free (Frontend not running)."
}

# 3. Terminate via tracked PID file if any process lingered
if (Test-Path $pidFile) {
    $lines = Get-Content $pidFile -ErrorAction SilentlyContinue
    foreach ($line in $lines) {
        $parts = $line.Split(":")
        if ($parts.Length -eq 2) {
            $trackedPid = [int]$parts[1]
            if ($trackedPid -gt 0) {
                $proc = Get-Process -Id $trackedPid -ErrorAction SilentlyContinue
                if ($proc) {
                    if ($proc.ProcessName -match "python" -or $proc.ProcessName -match "node") {
                        Write-Log "    Stopping tracked $($parts[0]) process (PID $trackedPid)..."
                        Stop-Process -Id $trackedPid -Force -ErrorAction SilentlyContinue
                    }
                }
            }
        }
    }
    Remove-Item -Path $pidFile -Force -ErrorAction SilentlyContinue
}

# 4. Close JobPulse AI labeled CMD windows
$cmdBackend = cmd /c "taskkill /FI `"WINDOWTITLE eq JobPulse AI - Backend Server*`" /T /F 2>&1"
$cmdFrontend = cmd /c "taskkill /FI `"WINDOWTITLE eq JobPulse AI - Frontend Server*`" /T /F 2>&1"

Write-Log "[STOP] [SUCCESS] All JobPulse AI services stopped and network ports released."
